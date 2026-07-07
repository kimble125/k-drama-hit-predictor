# 🔄 Hit-Predictor v3 — 새 대화방 핸드오프 문서

> **이 문서를 새 대화방의 첫 메시지에 첨부하세요.** 이전 대화의 핵심만 정리한 압축 컨텍스트입니다.

---

## 📌 호칭

미루님으로 부르세요. (오빠 X, 이름 X)
Claude 메모리에 이미 저장돼 있어요. 새 대화방에서도 자동 인지됩니다.

---

## 🎯 프로젝트 개요

**K-Drama Hit-Predictor** — 논문 6편 기반 K-드라마 흥행 예측 시스템.
- GitHub: https://github.com/kimble125/k-drama-hit-predictor (아직 푸시 전)
- IT 블로그: https://kimble125.tistory.com (기술 해설용)
- 콘텐츠 블로그: https://forrest125.tistory.com (사용 사례)
- 네이버웹툰 글로벌 콘텐츠 분석 인턴 포트폴리오

---

## ✅ 이미 완성된 것 (재작업 X)

1. **6축 H-Score 엔진** + Triple KPI (first_ep / avg / rsi_victory)
2. **RSI 자동 산출** (시간 감쇠 + OTT 환산 + 신인 fallback)
3. **채널×시간대 3단 벤치마크** (`core/benchmarks.py`)
4. **Netflix Top10 다운로더** (`scripts/fetch_netflix_top10.py`)
5. **TMDB 자동 수집기** (`scripts/fetch_tmdb_filmography.py`)
6. **위키백과 ko 수집기** (`fetch_wikipedia_meta.py`)
7. **나무위키 fallback** (`fetch_namuwiki_fallback.py`)
8. **닐슨 CSV 병합기** (`merge_nielsen_ratings.py`)
9. **재계산 스크립트** (`recalculate_candidates.py`)
10. **블로그 글 #1 초안** (HTML, kimble125 IT 블로그용)
11. **README.md** + **GITHUB_PUSH_GUIDE.md**

---

## 🔴 새 대화방에서 해결할 4가지 핵심 이슈

### 이슈 1: candidate_dramas.csv 정보 오류 (자동화 추적 필요)

CSV에 잘못된 정보가 들어 있음. 미루님 정정 사실:

| 드라마 | 잘못된 정보 (현재 CSV) | 정확한 정보 (미루님 검증) |
|---|---|---|
| 모두가 자신의 무가치함과 싸우고 있다 | 박현석 / 정보훈 | **차영훈 / 박해영** |
| 골드랜드 | 정해인·김고은·조진웅·염혜란 / 박현석 / 임상춘 | **박보영·김성철·이현욱·김희원·문정희·이광수 / 김성훈 / 황조윤** |
| 21세기 대군부인 | 아이유·변우석·성동일·이지아 (변경됨: 노상현·공승연 추가) | (이미 정정됨, 단 노상현·공승연 필모그래피 누락) |
| 유미의 세포들3 | 김고은·원진아·진영·박진영 | **김고은·김재원·전석호·최다니엘** |
| 허수아비 | 신경수 / 박경수 | **박준우 / 이지현** |
| 기리고 | 이충현 / 이충현 | **박윤서 / 박중섭** |

**미루님의 명시적 요구**:
> "candidate_dramas.csv을 수작업으로 수정하는 게 아니라 왜 잘못 수집되었는지 파악하고 고쳐야 해. 이 csv가 어떻게 수집됐는지부터 파악해. 이 predictor는 최대한 자동화하는 게 목적이야."

**작업 방향**:
- candidate_dramas.csv가 처음에 어떻게 생성됐는지 (이전 대화 transcript에서 추적)
- 자동 수집 가능한 소스 — 나무위키 신작 드라마 페이지, 위키백과 인포박스, 펀덱스 리포트 PDF
- "4월 신작 드라마 모음.md" 같은 미루님 자료에서 자동 파싱 가능 여부

### 이슈 2: 출연 가중치 시스템 (구교환 RSI=1.0, RSGI=7.37 문제)

**현재 문제**: TMDB의 order 필드 부정확으로 모든 출연을 `is_lead=True`로 처리. 결과:
- 구교환의 〈우영우〉 특별출연(11.9%) → 주연으로 인식 → RSI=1.0 폭등

**미루님의 명시적 해결책**:
> "이상한 변호사 우영우는 특별 출연이지만 반영치를 낮게 해야지(주연/조연/특별출연의 반영치 혹은 가중치를 달리 산정해야). 아예 없애면 안 돼. 시그널은 빼고."

**작업 방향**: `Credit` 스키마에 `role_weight` 필드 추가
- 주연: 1.0
- 조연: 0.5
- 특별출연/카메오: 0.2
- TMDB order로는 추정 불가 → **나무위키/위키백과에서 출연 유형 파싱** 필요
- RSI 계산 시 `wins × time_weight × role_weight` 로 가중

### 이슈 3: OTT Top10 미적용 (모든 배우 OTT 0편)

**현재 문제**: `recalculated_results_v2.json` 모든 배우의 `n_ott: 0`. Netflix 환산 미적용.

**미루님의 선택**: 선택 1 — 누락된 파이프라인 추가 실행
- `fetch_netflix_top10.py` 로 XLSX 다운로드
- 필모그래피의 OTT 작품에 자동 매칭 (예: 〈폭싹 속았수다〉 = Netflix Top1, 5주)
- LOCAL_EXECUTION_GUIDE.md 업데이트 (필수 단계로)

### 이슈 4: 결측치 정책 명확화

**미루님의 명시적 정책**:
> "'원인을 모르는' 결측치는 결측치대로 냅두고 왜 결측치가 되었는지 원인을 파악해서 해결해야 해. '원인을 아는' 결측치만 fallback 적용."

**현재 문제**:
- 21세기 대군부인의 노상현·공승연 missing → **TMDB 수집 누락** (원인 알지만 미수집)
- 신인 작가 유지원 → **신인 fallback 적용 가능** (원인 알고 정책 있음)
- 빈 필모그래피 → **검색어 동명이인 매칭 실패** (원인 알면 보완)

**작업 방향**: 결측 사유 명시 (`reason: tmdb_search_failed` / `homonym_conflict` / `data_collection_skipped`) + 사유별 처리 정책 분기.

---

## 🛠 새 대화방에서 권장 작업 순서

```
Step 1. candidate_dramas.csv 자동 수집 출처 추적 + 자동화 설계
Step 2. Credit 스키마에 role_weight 필드 추가 + RSI 계산 반영
Step 3. 누락 인물 일괄 TMDB 수집 (노상현, 공승연, 차영훈, 박해영, 박보영, 김성철 등)
Step 4. Netflix Top10 다운로드 + OTT 자동 매칭
Step 5. 결측치 사유 분기 시스템
Step 6. 최종 재계산 → recalculated_results_v3.json 산출
Step 7. (선택) GitHub 푸시
```

크레딧 빠듯하면 1~3까지만 새 대화방에서 하고, 4~7은 또 분기해도 괜찮습니다.

---

## 📦 새 대화방에 첨부할 파일 (필수)

1. **이 문서** (`HANDOFF.md`)
2. **최신 zip** (`k-drama-hit-predictor-v2-FIXED.zip` 또는 미루님이 antigravity에서 작업한 v3 후보)
3. **candidate_dramas.csv** (현재 잘못된 버전 — 추적용)
4. **wikipedia_meta.json** + **namuwiki_meta.json** (위키 수집 결과)
5. **recalculated_results_v2.json** (현재 결과 — 비교 베이스라인)
6. **〈4월 신작 드라마 모음.md〉** (자동 수집 소스 후보)

이거 6개만 있으면 새 대화방에서 시작 가능합니다.

---

## 🚫 새 대화방에서 하지 말아야 할 것

- 6축 H-Score 구조 재설계 (이미 완성, 건드리지 마세요)
- Triple KPI 가중치 변경 (논문 기반 확정값)
- 시간 감쇠 공식 변경 (검증 끝남)
- 블로그 글 재작성 (HTML 산출물 있음)
- README 재작성 (현재 버전으로 충분)

이런 것들 하면 또 컨텍스트 낭비됩니다.

---

## 💬 새 대화방 첫 메시지 예시

```
미루님이 직접 입력할 메시지:

"안녕, 이 핸드오프 문서를 먼저 읽어주세요.

[HANDOFF.md 첨부]
[k-drama-hit-predictor-v2-FIXED.zip 첨부]
[candidate_dramas.csv 첨부]

이슈 1 (CSV 자동 수집 추적)부터 시작하고 싶어요.
이 CSV가 어떻게 만들어졌는지 zip 안의 파일과 transcript를 
보고 추적해주세요. 그 다음 자동화 방안을 제시해주세요."
```

---

## 📝 Memory에 남아있는 사항

다음은 Claude 메모리에 이미 저장돼 있어 새 대화에서도 자동 인지됨:

- 호칭: 미루님
- 블로그: forrest125.tistory.com (콘텐츠), kimble125.tistory.com (IT)
- GitHub: kimble125/k-drama-hit-predictor
- 네이버웹툰 인턴 포트폴리오용 프로젝트
- Python 초보, 한국어 응답 선호
- 6축 H-Score, Triple KPI, RSI, OTT 환산 등 핵심 개념
- Netflix Top10 공식 XLSX 사용 (Apify 토큰 결제 안 됨, 불필요)
- TMDB Read Token: eyJhbGci... (메모리에 있음)

새 대화방에서 이런 거 다시 설명할 필요 없습니다.
