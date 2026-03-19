"""
우주커넥트 SKT 공통지원금 크롤러 서버
FastAPI + Playwright → Supabase support_amount 자동 저장
"""

from fastapi import FastAPI, BackgroundTasks, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from playwright.sync_api import sync_playwright
import json, re, urllib.request, urllib.parse, os
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://duclnvlwvzhwhhglaxwr.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImR1Y2xudmx3dnpod2hoZ2xheHdyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM1NDkwNjcsImV4cCI6MjA4OTEyNTA2N30.8BwrdcSnBlDWmKNR8L5nX2jbOj1qkVODI_-qnH42lFU")
CRAWL_SECRET = os.environ.get("CRAWL_SECRET", "woozoo-crawl-secret")

JOIN_TYPES  = ["MNP", "CHG", "NEW"]
JOIN_LABELS = {"MNP": "번호이동", "CHG": "기기변경", "NEW": "신규가입"}

crawl_status = {"running": False, "last_run": None, "last_result": None}


def supabase_get(path):
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    req = urllib.request.Request(url, headers={
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    })
    with urllib.request.urlopen(req, timeout=15) as res:
        return json.loads(res.read().decode())


def supabase_upsert(table, data, on_conflict):
    url = f"{SUPABASE_URL}/rest/v1/{table}?on_conflict={on_conflict}"
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    })
    with urllib.request.urlopen(req, timeout=15) as res:
        return res.status


def supabase_insert_ignore(table, data):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=ignore-duplicates,return=minimal",
    })
    with urllib.request.urlopen(req, timeout=15) as res:
        return res.status


def parse_table(page):
    results = []
    try:
        rows = page.query_selector_all("table tbody tr")
        seen = set()
        for row in rows:
            cols = row.query_selector_all("td")
            if len(cols) < 4:
                continue
            raw    = cols[0].inner_text().strip()
            name   = ' '.join(raw.split())
            name   = re.sub(r'구매하기.*', '', name).strip()
            support = int(re.sub(r"[^\d]", "", cols[3].inner_text())) if cols[3].inner_text().strip() else 0
            if support == 0 or not name or name in seen:
                continue
            seen.add(name)
            results.append({"skt_name": name, "support_amount": support})
    except:
        pass
    return results


def run_crawl():
    crawl_status["running"] = True
    log = []
    try:
        mappings = supabase_get("plan_mapping?select=skt_plan_id,skt_plan_name,plan_id&is_active=eq.true")
        log.append(f"요금제 {len(mappings)}개 로드")

        model_mappings_raw = supabase_get("model_mapping?select=skt_model_name,model_code&is_active=eq.true")
        model_map = {m["skt_model_name"]: m["model_code"] for m in model_mappings_raw if m["model_code"]}
        log.append(f"모델매핑 {len(model_map)}개 로드")

        all_items = []
        new_skt_names = set()

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            for mapping in mappings:
                skt_id   = mapping["skt_plan_id"]
                skt_name = mapping["skt_plan_name"]
                plan_id  = mapping["plan_id"]
                for join_type in JOIN_TYPES:
                    try:
                        page = browser.new_context(
                            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
                        ).new_page()
                        url = (
                            f"https://shop.tworld.co.kr/notice"
                            f"?modelNwType=5G&saleMonth=24"
                            f"&prodId={skt_id}"
                            f"&prodNm={urllib.parse.quote(skt_name)}"
                            f"&joinType={join_type}&saleYn=Y&order=SUPPORT_HIGH"
                        )
                        page.goto(url, wait_until="networkidle", timeout=30000)
                        page.wait_for_timeout(4000)
                        items = parse_table(page)
                        for item in items:
                            item["plan_id"]   = plan_id
                            item["join_type"] = join_type
                            all_items.append(item)
                            if item["skt_name"] not in model_map:
                                new_skt_names.add(item["skt_name"])
                        log.append(f"[{skt_name}] {JOIN_LABELS[join_type]} → {len(items)}개")
                        page.close()
                    except Exception as e:
                        log.append(f"[{skt_name}] {JOIN_LABELS[join_type]} 오류: {str(e)}")
            browser.close()

        # 신규 모델명 model_mapping에 등록
        if new_skt_names:
            entries = [{"skt_model_name": n, "model_code": None, "is_active": False} for n in new_skt_names]
            try:
                supabase_insert_ignore("model_mapping", entries)
                log.append(f"신규 모델명 {len(new_skt_names)}개 등록 (웹에서 매핑 필요)")
            except Exception as e:
                log.append(f"신규 모델명 등록 실패: {str(e)}")

        # support_amount upsert (번호이동 기준 최고금액)
        deduped = {}
        for item in all_items:
            model_code = model_map.get(item["skt_name"])
            if not model_code:
                continue
            key = (model_code, item["plan_id"])
            if key not in deduped or item["support_amount"] > deduped[key]["amount"]:
                deduped[key] = {"model_code": model_code, "plan_id": item["plan_id"], "amount": item["support_amount"]}

        saved = 0
        upsert_list = list(deduped.values())
        if upsert_list:
            for i in range(0, len(upsert_list), 100):
                supabase_upsert("support_amount", upsert_list[i:i+100], "model_code,plan_id")
                saved += len(upsert_list[i:i+100])
            log.append(f"{saved}건 저장 완료")

        result = {
            "success": True,
            "crawled": len(all_items),
            "saved": saved,
            "new_model_names": len(new_skt_names),
            "log": log,
        }
    except Exception as e:
        result = {"success": False, "error": str(e), "log": log}

    crawl_status["running"] = False
    crawl_status["last_run"] = datetime.now().isoformat()
    crawl_status["last_result"] = result
    return result


@app.get("/")
def root():
    return {"service": "우주커넥트 크롤러", "status": "running"}

@app.get("/status")
def status():
    return crawl_status

@app.post("/crawl")
def crawl(background_tasks: BackgroundTasks, x_crawl_secret: str = Header(None)):
    if x_crawl_secret != CRAWL_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if crawl_status["running"]:
        return {"message": "이미 크롤링 중", "running": True}
    background_tasks.add_task(run_crawl)
    return {"message": "크롤링 시작!", "running": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
