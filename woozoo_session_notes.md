# 우주커넥트 재고관리 시스템 - 작업 현황

## 📌 접속 정보
- 관리자 웹: https://woozoo.vercel.app
- GitHub: https://github.com/ggg709674-afk/woozoo
- Supabase URL: https://duclnvlwvzhwhhglaxwr.supabase.co
- 작업 파일: C:\woozoo\index.html
- 배포: deploy.bat 더블클릭

---

## ✅ 오늘 완료한 작업

### 1. 요금제 관리
- 사이드바에 요금제 관리 메뉴 추가
- plans 테이블 생성 (name, monthly_fee, plan_group, is_active, sort_order)
- 요금제 CRUD 기능 (추가/수정/삭제/활성토글)
- 요금제군: 프리미엄, I_100, F_79, L_69, M_50, R_43, S_33
- 요금제 29개 DB 입력 완료

### 2. 공통지원금 관리
- support_amount 테이블 생성 (model_code, plan_id, amount)
- 공통지원금 메뉴 추가 (설정 섹션)
- **지원금 테이블** - 세로=모델, 가로=요금제(기본요금 내림차순)
- 셀 클릭 → 인라인 편집 → 포커스 이동/엔터 시 자동 저장
- 엑셀 다운로드 (테이블과 동일한 형식)
- 엑셀 업로드 → DB 일괄 저장
- Supabase Max Rows 10000으로 변경 (모델40개 × 요금제29개 = 1160행)

### 3. 재고 목록 개선
- 모델/색상 드롭다운 필터 추가
- 상태 변경 시 실시간 반영 (해당 행만 업데이트)
- 그룹 체크박스 추가 (A B C D E) - 체크=해당그룹에서 숨김
- 그룹 필터 드롭다운 추가

### 4. 거래처 관리
- 그룹 컬럼 추가 (A~E 그룹 지정)
- inventory 테이블에 visible_groups TEXT[] 컬럼 추가
- partners 테이블에 partner_group TEXT 컬럼 추가

### 5. 재고 현황 개선
- 전체/전체수량에서 개통 제외 (재고+출고중+숨김 기준)
- 재고현황표 탭 복귀시 전체 카드 active 복원

### 6. UI/UX 개선
- 다크/라이트 토글 버튼 (로고 옆) - 설정 로컬스토리지 저장
- 다크모드 전체 보완 (테이블 헤더, 뱃지, 버튼, 드롭다운 등)
- 정산 관리 페이지는 다크모드에서 라이트 고정
- 새로고침 시 현재 페이지 유지 (URL hash 활용)
- 정산 드롭다운 (판매처/모델) 닫힘 버그 수정
- 드롭다운 첫 항목에 "— 없음 —" 추가 (선택 취소용)

### 7. 메뉴 구조 변경
```
메인: 대시보드 / 정산 관리
재고: 입고 등록 / 재고 현황
운영: 주문 처리 / 거래처 관리
설정: 공통지원금 / 모델 관리 / 요금제 관리 / 회원 관리
```

---

## ⬜ 미완료 / 다음 작업

### 우선순위 높음
- **거래처용 웹페이지** - 슬러그 기반 주문 링크에서 재고 + 공통지원금 표시
  - 그룹별 재고 필터링 (visible_groups 활용)
  - 공통지원금 함께 표시
- **정산 DB 저장** - 행 단위 저장 기능
- **출고처리 연동** - 재고 ↔ 주문 연동

### 우선순위 중간
- **회원 권한 관리** - 메뉴별 접근 권한 (추후 결정)
- **엑셀 다운로드** - 재고목록, 주문목록
- **거래처 슬러그 undefined 수정**

### 나중에
- **Flutter 네이티브 앱** - iOS/Android

---

## 🗄️ DB 테이블 현황

| 테이블 | 설명 |
|--------|------|
| inventory | 재고 (status, stock_date, visible_groups, location 등) |
| orders | 주문 (partner_id, customer_name, model, color 등) |
| partners | 거래처 (name, slug, partner_group) |
| models | 모델마스터 (code, color1~6, is_active, price) |
| stock_in | 입고내역 |
| profiles | 회원정보 (승인제, role: admin/staff) |
| plans | 요금제 (name, monthly_fee, plan_group, is_active, sort_order) |
| support_amount | 공통지원금 (model_code, plan_id, amount) |
| settlements | 정산 (미사용) |
| settings | 설정 |

---

## 📋 요금제 구조
- 요금제군: 프리미엄, I_100, F_79, L_69, M_50, R_43, S_33
- 요금제 29개 등록 완료
- 공통지원금: 모델별로 요금제마다 금액 설정

## 🔑 그룹 시스템
- 거래처에 A~E 그룹 지정
- 재고에 visible_groups 배열로 숨길 그룹 지정
- 체크 = 해당 그룹에서 숨김
- 미체크 = 모든 그룹에 공개
- status='숨김' = 전체 숨김

