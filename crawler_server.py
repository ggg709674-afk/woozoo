from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from playwright.async_api import async_playwright
import asyncio
from datetime import datetime
import os
from supabase import create_client

app = FastAPI()

# ✅ CORS 설정 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Vercel 도메인 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPABASE_URL = "https://duclnvlwvzhwhhglaxwr.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImR1Y2xudmx3dnpod2hoZ2xheHdyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM1NDkwNjcsImV4cCI6MjA4OTEyNTA2N30.8BwrdcSnBlDWmKNR8L5nX2jbOj1qkVODI_-qnH42lFU"
CRAWL_SECRET = "woozoo-crawl-secret"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 크롤링 상태 저장
crawl_state = {
    "running": False,
    "last_run": None,
    "last_result": None
}

@app.get("/")
async def root():
    return {"service": "우주커넥트 크롤러", "status": "running"}

@app.get("/status")
async def get_status():
    return crawl_state

@app.post("/crawl")
async def crawl(x_crawl_secret: str = Header(None)):
    # Secret 검증
    if x_crawl_secret != CRAWL_SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")
    
    if crawl_state["running"]:
        raise HTTPException(status_code=400, detail="Already running")
    
    # 백그라운드 태스크로 크롤링 시작
    asyncio.create_task(run_crawl())
    
    return {"status": "started"}

async def run_crawl():
    crawl_state["running"] = True
    crawl_state["last_run"] = datetime.now().isoformat()
    
    try:
        # 1. plan_mapping에서 활성화된 요금제 가져오기
        plans_res = supabase.table("plan_mapping").select("*").eq("is_active", True).execute()
        active_plans = plans_res.data
        
        if not active_plans:
            crawl_state["last_result"] = {"success": False, "error": "활성화된 요금제 없음"}
            crawl_state["running"] = False
            return
        
        # 2. model_mapping 로드
        models_res = supabase.table("model_mapping").select("*").execute()
        model_map = {m["skt_model_name"]: m["model_code"] for m in models_res.data if m.get("model_code")}
        
        results = []
        new_models = set()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-software-rasterizer',
                    '--disable-extensions',
                    '--single-process'
                ]
            )
            page = await browser.new_page()
            
            # 각 요금제별 크롤링
            for plan in active_plans:
                skt_plan_id = plan["skt_plan_id"]
                
                # 가입유형별 (MNP, CHG, NEW)
                for join_type in ["MNP", "CHG", "NEW"]:
                    url = f"https://www.sktelecom.com/index_renew.html?plan={skt_plan_id}&joinType={join_type}"
                    
                    try:
                        await page.goto(url, timeout=30000)
                        await page.wait_for_timeout(3000)
                        
                        # 모델 목록 크롤링
                        items = await page.query_selector_all(".model-item")  # 실제 셀렉터로 수정 필요
                        
                        for item in items:
                            model_name = await item.text_content()
                            model_name = model_name.strip()
                            
                            # 신규 모델 체크
                            if model_name not in model_map:
                                new_models.add(model_name)
                                # model_mapping에 추가 (비활성)
                                supabase.table("model_mapping").insert({
                                    "skt_model_name": model_name,
                                    "is_active": False
                                }).execute()
                            
                            # 지원금 크롤링
                            amount_el = await item.query_selector(".support-amount")  # 실제 셀렉터
                            if amount_el and model_name in model_map:
                                amount_text = await amount_el.text_content()
                                amount = int(amount_text.replace(",", "").replace("원", ""))
                                
                                model_code = model_map[model_name]
                                plan_id = plan["plan_id"]
                                
                                # 번호이동 기준 최고금액만 저장
                                if join_type == "MNP":
                                    results.append({
                                        "model_code": model_code,
                                        "plan_id": plan_id,
                                        "amount": amount
                                    })
                    
                    except Exception as e:
                        print(f"Error crawling {url}: {e}")
                        continue
            
            await browser.close()
        
        # 3. support_amount에 upsert
        for r in results:
            supabase.table("support_amount").upsert(r, on_conflict="model_code,plan_id").execute()
        
        crawl_state["last_result"] = {
            "success": True,
            "saved": len(results),
            "new_models": len(new_models)
        }
    
    except Exception as e:
        crawl_state["last_result"] = {"success": False, "error": str(e)}
    
    finally:
        crawl_state["running"] = False

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
