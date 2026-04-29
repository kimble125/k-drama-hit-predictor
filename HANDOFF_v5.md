# 🔄 Hit-Predictor v5 — GPT 이어받기 핸드오프 (v3.1 직후)

> **이 문서는 ChatGPT(GPT-4/5 계열)에서 이 프로젝트 작업을 이어받기 위한 자족적(self-contained) 핸드오프입니다.**
>
> Claude Code 작업방에서 v3.1 (RSI 시간 감쇠 즉시 누진 정책 + Netflix Top10 raw 격리)까지 commit·push 완료 시점의 컨텍스트입니다. GPT는 파일 시스템 접근이 제한될 수 있으므로, 이 문서 하나로 작업 재개에 필요한 모든 정보를 담았습니다.

---

## 0. 빠른 시작 (3분)

```
1. 미루님으로 부르세요. (오빠 X, 본명 X)
2. Python 초보입니다. 코드 수정 제안 시 한국어로, 그리고 변경 이유부터 설명해주세요.
3. 답변은 한국어로.
4. 현재 브랜치: feature/auto-collection-v3
5. 최신 commit: 6b54d43  "v3.1: RSI 시간 감쇠 즉시 누진 + Netflix Top10 raw 격리"
6. GitHub: https://github.com/kimble125/k-drama-hit-predictor
7. 사용자 환경: macOS, Python 3.9+, 로컬 디렉터리
   /Users/kimble/Library/CloudStorage/GoogleDrive-hoykim125@gmail.com/내 드라이브/Git/k-drama-hit-predictor/k-drama-hit-predictor 3
```

미루님이 GPT에게 다음과 같이 요청할 가능성이 높습니다:

- **A.** "v3.1 후속으로 Phase 1-C 정제(허수아비/기리고/골드랜드/유미3/로맨스의 절댓값) 진행"
- **B.** "Phase 3 — 6축 점수 자동 산정(`auto_score.py` 신규)"
- **C.** "Phase 2-B — 펀덱스 PDF 아카이빙·파싱"
- **D.** "알고리즘 개선 — 영화 cross-media bonus + 베테랑 fallback"
- **E.** "통합 재계산 → `recalculated_results_v3.json` + 블로그 글 #2"

각 옵션의 상세 설계는 **§7 다음 작업 우선순위** 참조.

---

## 1. 프로젝트 정체

**K-Drama Hit-Predictor** — 논문 6편(주상필 2019, 최현종 2017 등) 기반 K-드라마 흥행 예측 시스템.

- **GitHub**: https://github.com/kimble125/k-drama-hit-predictor
- **사용자 블로그**:
  - 콘텐츠 분석: https://forrest125.tistory.com
  - 기술 해설: https://kimble125.tistory.com
- **포지셔닝**: 네이버웹툰 글로벌 콘텐츠 분석 인턴 포트폴리오
- **스택**: Python 3.9+, pandas, numpy, scikit-learn, requests, beautifulsoup4, openpyxl
- **TMDB Read Token**: 메모리에 보존(미루님이 직접 환경변수 `TMDB_READ_TOKEN`으로 export). GPT가 토큰을 본문에 출력하면 안 됩니다.

### 핵심 산식 — 6축 H-Score + Triple KPI + RSI

- **6축**: cast_power, creator_power, ip_power, platform_strategy, pre_buzz, genre_market_fit (각 1~10)
- **Triple KPI**: first_ep / avg_rating / rsi_victory(승률 기반)
- **RSI**: `Σ(wins × time_weight × role_weight) / Σ(time_weight × role_weight)` ─ 자세한 정의는 [`src/hit_predictor/rsi/calculator.py`](src/hit_predictor/rsi/calculator.py)
- **OTT 환산**: Netflix Top10 → virtual TV rating (max 35.0%)

### 절대 건드리지 말 것 (논문·검증 기반 확정)

- 6축 H-Score 구조
- Triple KPI 가중치
- 시간 감쇠 공식의 *형태*(exp decay) — *defaults*는 v3.1에서 변경됨(아래 §3 참조)
- README.md 재작성

---

## 2. 작업 방의 흐름 (v1 → v3.1)

| 단계 | 마일스톤 | 산출물·검증 |
|---|---|---|
| v1 | 6축 H-Score 엔진 + Triple KPI | `core/hscore.py`, `axes.py`, `weights.py` |
| v2 | RSI 시간 감쇠 + OTT 환산 + 신인 fallback | `rsi/calculator.py`, `ott_converter.py`, `newcomer_fallback.py` |
| v3 | **자동 수집 파이프라인** — 위키백과/나무위키/TMDB 신작 자동 발견 + 다중 소스 투표 + 닐슨 자동 수집 | `scripts/discover_new_dramas.py`, `build_candidate_dramas.py`, `fetch_nielsen_weekly.py`; HANDOFF_v3 핵심 오류 3건 자동 정정 (모두가… / 골드랜드 / 유미3) |
| v3.1 (**최신**) | **RSI 시간 감쇠 즉시 누진 + Netflix Top10 raw 격리** | `calculator.py` defaults 변경, `.gitignore` 보강 — §3 참조 |

미해결 한계 — §6 참조.

---

## 3. v3.1 변경 사항 (이번 작업방의 산출물)

### 3-1. RSI 시간 감쇠 정책 변경 (`src/hit_predictor/rsi/calculator.py`)

**Before (v3까지)**:
```python
DEFAULT_DECAY_RATE = 0.15
DEFAULT_FULL_WEIGHT_YEARS = 5  # 5년 풀가중 후 감쇠
```

**After (v3.1)**:
```python
DEFAULT_DECAY_RATE = 0.10
DEFAULT_FULL_WEIGHT_YEARS = 0  # 즉시 감쇠 시작
```

**가중치 변화** (검증 완료):

| 경과 연수 | v3 (full=5, λ=0.15) | v3.1 (full=0, λ=0.10) | 의미 |
|---|---|---|---|
| 0년(올해) | 1.000 | 1.000 | 동일 |
| 1년 | 1.000 | 0.905 | **즉시 감쇠 시작** |
| 3년 | 1.000 | 0.741 | **최근작 가중 약화** |
| 5년 | 1.000 | 0.607 | **5년 풀가중 종료** |
| 7년 | 0.741 | 0.497 | 더 감쇠 |
| 10년 | 0.472 | 0.368 | 약간 감쇠 |
| 15년 | 0.223 | 0.223 | **동일 수렴(끝점 일치)** |

**왜 바꿨나**: OTT·콘텐츠 트렌드 변동이 빨라진 환경에서 5년 풀가중은 너무 길다고 판단. 1~5년 사이의 *최근* 작품들이 서로 차등화되도록 즉시 감쇠로 변경.

**Backward-compat**: 함수 호출 시 `full_weight_years=5`를 *명시적으로* 넘기면 legacy 동작 유지됨. 기존 테스트가 깨질 우려 거의 없음(단, default를 바꿨으므로 default 사용 호출자는 새 가중치를 받음).

**검증 명령**:
```bash
python3 -c "
import sys; sys.path.insert(0, 'src')
from hit_predictor.rsi.calculator import time_decay_weight
for y in [0,1,3,5,10,15]:
    print(f'{y}년: {time_decay_weight(y):.3f}')
"
```

### 3-2. Netflix Top10 raw 데이터 격리

**다운로드 완료**: `data/netflix_top10/all-weeks-countries.xlsx` (13.3MB), `all-weeks-global.xlsx` (398KB)
- 출처: `https://www.netflix.com/tudum/top10/data/`
- 다운로더: [`scripts/fetch_netflix_top10.py`](scripts/fetch_netflix_top10.py)

**`.gitignore` 보강** (Netflix 이용약관 — 개인 연구·학습용만, 재판매 금지):
```
data/netflix_top10/*.xlsx
!data/netflix_top10/.gitkeep
```

**통합 검증** ([`rsi/ott_converter.py`](src/hit_predictor/rsi/ott_converter.py)의 `extract_drama_performance` 호출):

| 작품 | best_rank_kr | weeks_kr | best_rank_global | weeks_global | virtual_rating |
|---|---|---|---|---|---|
| When Life Gives You Tangerines (=폭싹 속았수다) | 1 | 14 | 1 | 9 | **35.0% (cap)** |
| Squid Game | 1 | 19 | 1 | 32 | **35.0% (cap)** |
| Crash Landing on You | 8 | 7 | None | None | **8.5%** |
| 폭싹 속았수다 (한글) | — | — | — | — | **NOT FOUND** |

🔑 **중요한 발견**: Netflix Top10 XLSX는 **영문 제목**(show_title) 기준이라 **한국어 제목으로는 매칭 실패**. 폭싹 속았수다 → "When Life Gives You Tangerines"처럼 **국문↔영문 매핑** 필요.

**해결 방향(다음 작업)**: `extract_drama_performance` 호출 전에 TMDB로 한국어 제목 → 영문 original_title/title 변환. TMDB의 `/search/tv?query={한국어}&language=ko-KR`로 검색 후 응답의 `original_name`(영문)을 Netflix XLSX 검색에 사용. `data/filmography/` 또는 새 `data/title_mapping.json` 캐시 권장.

---

## 4. 코드 베이스 지도 (Module Map)

### 핵심 엔진 — `src/hit_predictor/`

| 경로 | 책임 | 비고 |
|---|---|---|
| `core/hscore.py` | 6축 → H-Score 종합 | 변경 금지 |
| `core/axes.py` | 각 축 raw → 0-10 정규화 | 변경 금지 |
| `core/weights.py` | 6축 가중치 | 변경 금지 (논문 기반) |
| `core/benchmarks.py` | 채널×시간대 3단 벤치마크 (지상파 5.5%, OTT 6.0% 등) | `get_benchmark_for_credit()` 인터페이스 유지 |
| `core/temporal.py` | 시간 가중 보조 함수 | |
| `core/lead_in.py` | 직전 슬롯 시청률 보정 | |
| `rsi/calculator.py` | **RSI/RSGI 산출** (v3.1에서 defaults 변경) | 시간×역할 가중 적용 — 핵심 함수 `calculate_rsi`, `aggregate_cast_rsi`, `cast_score_from_rsi`, `creator_score_from_rsi` |
| `rsi/schemas.py` | `Person`/`Credit` + `cast_role`/`role_weight` + `ROLE_WEIGHT_MAP` | lead 1.0 / supporting 0.5 / special 0.2 / cameo 0.1 |
| `rsi/ott_converter.py` | Netflix Top10 → 가상 시청률 (`OTTPerformance`, `convert_to_virtual_rating`, `extract_drama_performance`) | XLSX 직접 파싱 |
| `rsi/newcomer_fallback.py` | 신인 가산점 fallback (배진아 2005 기반) | |
| `rsi/tmdb_fetcher.py` | TMDB API → Person/Credit | `TMDB_READ_TOKEN` 필요 |
| `rsi/storage.py` | 필모그래피 JSON 저장/로드 | |
| `data/schemas.py` | `Drama` + `MissingReason` enum + `data_quality`/`field_sources` | v3에서 결측 사유 분기 추가 |
| `data/wikipedia_fetcher.py` | 위키백과 인포박스 파싱 | `extract_infobox`, `WIKI_LINK` |
| `data/namuwiki_fetcher.py` | 나무위키 파싱 | |
| `data/loaders.py` | candidate_dramas.csv 로더 | |
| `data/nielsen_merger.py` | 닐슨 CSV 병합 | |
| `data/collectors/_http.py` | **공통 HTTP 헬퍼** — User-Agent + rate limit + robots.txt + 429/Retry-After + attribution | `polite_get`, `attribution_for`, `RobotsDisallowedError` |
| `data/collectors/nielsen.py` | 닐슨 코리아 시청률 크롤러 (지상파/종편/케이블) | `AREA_CODE_TO_LABEL = {"00":"전국", "01":"수도권"}` |
| `prediction/updater.py` | 사후 업데이트 | |
| `calibration/ensemble.py`, `validate.py` | 캘리브레이션 |  |

### 자동화 스크립트 — `scripts/`

| 스크립트 | 역할 | 입력 | 출력 |
|---|---|---|---|
| `discover_new_dramas.py` | 위키백과 + 나무위키 + TMDB에서 월/연 신작 자동 발견 | `--year 2026 --month 4` | `data/discovered/{Y}-{M}.json` |
| `build_candidate_dramas.py` | 다중 소스 투표 + role_weight 자동 분류 → CSV | discovered JSON | `data/candidate_dramas.csv` (+ `_quality.json` *예정*) |
| `fetch_nielsen_weekly.py` | 닐슨 wrapper — 월별·지역별 일괄 | `--year-month 202604 --area both` | `data/nielsen_weekly/nielsen_weekly_{YM}_{area}.csv` (.gitignore) |
| `fetch_netflix_top10.py` | Netflix Tudum 공식 XLSX 다운로드 | (인자 없음) | `data/netflix_top10/*.xlsx` (.gitignore) |
| `fetch_tmdb_filmography.py` | TMDB로 인물 필모 수집 | TMDB_READ_TOKEN | `data/filmography/{role}/...json` |
| `fetch_wikipedia_meta.py` | 위키백과 메타 수집 | | `data/wikipedia_meta.json` |
| `fetch_namuwiki_fallback.py` | 나무위키 보완 수집 | | `data/namuwiki_meta.json` |
| `recalculate_candidates.py` | 6축 점수 + RSI 재계산 → JSON | candidate_dramas.csv + 필모 | `output/recalculated_results_v{N}.json` |
| `predict_drama.py` | 단건 예측 |  | |
| `rank_candidates.py` | 후보 순위 산출 | | `output/ranking_results.json` |
| `merge_nielsen_ratings.py` | 닐슨 CSV → 표준 형식 병합 | | |
| `run_calibration.py` | 캘리브레이션 실행 | | |
| `update_postlaunch.py` | 방영 후 실적 업데이트 | | |
| `split_filmography.py` | 단일 JSON → 배우별 분할 | | |

---

## 5. 데이터·산출물 현황

### 5-1. 추적되는(public) 데이터

```
data/
├── candidate_dramas.csv       # 후보작 CSV (수정 대상)
├── completed_dramas.csv        # 완료작
├── filmography_merged.json     # 통합 필모
├── wikipedia_meta.json         # 위키 메타
├── namuwiki_meta.json          # 나무위키 메타
├── discovered/2026-04.json     # v3 자동 발견 결과 (4월 9/9편)
├── filmography/
│   ├── actors/    (개별 배우 JSON)
│   ├── directors/
│   └── writers/
└── awards/
output/
├── ranking_results.{csv,json}
└── recalculated_results_v2.{csv,json}   # v3 재계산은 미수행
docs/
├── blog_draft_01_rsi_ott_extension.md
├── GITHUB_PUSH_GUIDE.md
└── LOCAL_EXECUTION_GUIDE.md
```

### 5-2. 로컬 전용(.gitignore — 절대 commit·push 금지)

```
data/nielsen_weekly/*.csv      # 닐슨 이용약관 — 재배포 금지
data/nielsen_weekly/*.json
data/netflix_top10/*.xlsx      # Netflix 이용약관 — 재판매 금지
data/raw/
data/*_raw.csv
output/*.png, *.pdf, *.xlsx
```

⚠️ **GPT가 새 데이터 파일을 추가할 때**: 1차/원천 데이터(크롤링 결과, 다운로드한 XLSX 등)는 기본 .gitignore. 분석 결과(JSON, 작은 CSV)만 공개 가능.

### 5-3. 환경 변수

```bash
export TMDB_READ_TOKEN="<미루님이 직접 export>"
```
GPT가 토큰을 출력하지 않도록 주의. 코드에서는 `os.getenv("TMDB_READ_TOKEN")`로만 참조.

---

## 6. 알려진 한계 — 다음 작업방에서 처리할 것

### 6-1. Phase 1-C 정제 (미해결 5건)

`build_candidate_dramas.py`의 출력에서 다음 케이스가 미정제:

| 케이스 | 현상 | 원인 추정 | 해결 방향 |
|---|---|---|---|
| **허수아비** | 감독·작가·캐스트 모두 None | 나무위키 페이지 인포박스 셀렉터 미스매치 | 페이지 HTML 보고 셀렉터 보강 |
| **기리고** | 감독 None, 작가만 잡힘 | 인포박스 행 라벨 변형 | `(연출\|감독\|디렉터)` 라벨 사전 확장 |
| **로맨스의 절댓값** | 감독·작가 None | 인포박스가 부분만 채워짐 | wikipedia 보완 + 방송사 공식 fallback |
| **골드랜드** | `lead_actors=["박보영 김성철"]` 한 묶음 | HTML strong 안에 두 이름이 공백 결합 | strong 텍스트를 한국 이름 2-4글자 패턴으로 추가 split |
| **유미의 세포들 3** | 나무위키 매칭 실패 | URL `유미의 세포들 3` ≠ `유미의 세포들3` (공백) | 공백 정규화 후 redirect 검색 추가 |

**디버깅 명령**:
```bash
python3 scripts/build_candidate_dramas.py --year 2026 --month 4 \
    --titles "허수아비,기리고,로맨스의 절댓값,골드랜드,유미의 세포들 3" --dry-run
```

### 6-2. 알고리즘 개선 백로그

1. **영화 등 cross-media bonus** — KOFIC 박스오피스 + TMDB 영화 popularity. **RSI 본 계산은 건드리지 말고** `cast_score_from_rsi()`에 보너스 항만 추가 권장 (현재 `award_count_5y` 보너스와 같은 패턴)
2. **베테랑 fallback** — 구교환 같은 *15년+ 경력 + 드라마 RSI 표본 < 3편* 케이스 보정. 현재는 신인 fallback만 있음. **Bayesian smoothing** (장르 평균과 가중 평균) 도입 권장
3. **win의 격차 가중** — 현재 0.3%p 차이로 이기든 10%p 차이로 이기든 win=1.0. 격차 비례한 partial win 검토 (단, RSI vs RSGI 역할 분담 재정의 필요)
4. **벤치마크: 단일 평균 → 분포** — 동시간대 *실제 경쟁작 분포*(Top3 평균 등)로 대체 시 강한 슬롯 win이 더 어려워짐
5. **🆕 한국어→영문 제목 매핑** (v3.1 발견) — Netflix Top10 매칭 실패 케이스. TMDB로 자동 매핑 권장

### 6-3. 미수행 통합 단계

- **`recalculated_results_v3.json` 미생성**: v3.1 변경(decay rate) 효과를 전체 후보작에 적용한 결과 미산출. v3가 baseline.
- **펀덱스 자동화 미구현** (Phase 2-B): 청사진은 §8 참조

---

## 7. 다음 작업 우선순위 (미루님 결정 사항)

```
A. (우선) Phase 1-C 정제 — 허수아비/기리고/strong 분리/유미3 redirect — 1~2시간
B. (우선) Phase 3 — 6축 점수 자동 산정 (auto_score.py 신규) — 2~3시간
C. Phase 2-B — 펀덱스 PDF 아카이빙·파싱 — 2시간 (§8 청사진)
D. 알고리즘 개선 — 영화 cross-media bonus + 베테랑 fallback — 1~2시간
E. 통합 재계산 → recalculated_results_v3.json + 블로그 글 #2 — 1시간
F. (v3.1 신규) 한국어↔영문 제목 매핑 (TMDB 기반) — 30분
```

**미루님이 GPT에게 "어디부터 시작할지" 결정하면 그 단계만 집중해서 진행.**

---

## 8. 펀덱스 자동화 청사진 (Phase 2-B 진입용)

### 입수 경로

- 메인 페이지: https://www.fundex.co.kr/fxmain.do
- **공개 S3 버킷**: `racoi.s3.ap-northeast-2.amazonaws.com`
- URL 패턴: `https://racoi.s3.ap-northeast-2.amazonaws.com/[굿데이터]+펀덱스리포트_{M}월+{W}주차.pdf`
- *현재 주차*는 메인 페이지 anchor에 `FUNdex Report #N` 텍스트로 노출
- 주차 번호 시스템: 2026-04-3주차 = #583 (누적 회차)

### 구현 가이드

```python
# scripts/fetch_pundex_archive.py
# 1. fxmain.do GET → 'FUNdex Report' anchor의 href 추출 → 최신 PDF URL
# 2. PDF를 data/pundex_archive/{YYYY}/{YYYY-MM-DD}.pdf 로 저장
# 3. (옵션) 과거 N주 이전까지 URL 패턴으로 추정·시도 → 404 시 skip
# 4. .gitignore: data/pundex_archive/*.pdf  (저작권 — 재배포 금지)

# scripts/parse_pundex_weekly.py
# - PDF → pdfplumber 또는 PyPDF2로 텍스트 추출
# - 펀덱스 표준 섹션: 드라마 화제성 Top10 / 배우 화제성 Top20 / 감독·작가 Top10
# - 추출 결과 → data/pundex_weekly/{YYYY-MM-DD}.json
```

**의존성 추가**:
```
pdfplumber>=0.10  # 또는 PyPDF2
```
(현재 `requirements.txt`에 미포함)

---

## 9. GPT 작업 시 주의사항

### 9-1. 환경 차이 (Claude Code vs GPT)

| 사항 | Claude Code | GPT |
|---|---|---|
| 파일 직접 read/write | ✅ | ❌ (대화로 코드 주고받음) |
| 직접 명령 실행 | ✅ | ❌ (사용자가 실행) |
| Git 조작 | ✅ | ❌ (사용자가 실행) |
| 메모리 시스템 | ✅ (`memory/`) | 대화 내 휘발성 |

**→ GPT에게 작업을 시킬 때**: 
1. 변경할 파일을 사용자가 GPT에게 **본문 붙여넣기**
2. GPT가 **수정된 파일 전체 또는 unified diff** 출력
3. 사용자가 로컬에서 적용 후 검증

### 9-2. 응답 톤

- **한국어** (사용자가 한국인, Python 초보)
- 코드 변경 시 **변경 이유부터** 설명 → 그 다음 코드
- 변경 영향 범위(어떤 호출자가 깨질 수 있는지) 명시
- 미루님이 직접 명령을 실행해야 하므로 **실행 명령은 별도 코드블록**에 정확하게

### 9-3. 절대 하지 말 것

- 6축/Triple KPI 가중치 변경
- 시간 감쇠 *공식 형태* 변경 (defaults는 v3.1에서 합의됨)
- README.md 재작성
- TMDB 토큰을 본문에 출력
- `data/nielsen_weekly/*` 또는 `data/netflix_top10/*.xlsx`를 `git add`

### 9-4. 미루님 정책 (반드시 따를 것)

- **결측치 정책**: "원인을 모르는 결측치는 결측치대로 두고 원인 파악 후 해결. 원인을 아는 결측치만 fallback."
- **수작업 수정 금지**: candidate_dramas.csv는 자동 수집으로만 갱신. 잘못된 정보가 있으면 *수집 로직*을 고치지 *결과물 CSV*를 직접 편집 X.
- **시그널은 빼지 말고 가중치만 낮춤**: 특별출연·카메오 = role_weight 낮음, 제외 X.

---

## 10. 즉시 실행 가능한 검증 명령 (작업 재개 첫 단계)

```bash
cd "/Users/kimble/Library/CloudStorage/GoogleDrive-hoykim125@gmail.com/내 드라이브/Git/k-drama-hit-predictor/k-drama-hit-predictor 3"

# 1) 현재 상태 확인
git status
git log --oneline -5
# 기대: 6b54d43 v3.1 commit이 HEAD, working tree clean

# 2) v3.1 시간 감쇠 검증
python3 -c "
import sys; sys.path.insert(0, 'src')
from hit_predictor.rsi.calculator import time_decay_weight
for y in [0,1,3,5,10,15]:
    print(f'{y}년: {time_decay_weight(y):.3f}')
"
# 기대: 1.000 / 0.905 / 0.741 / 0.607 / 0.368 / 0.223

# 3) Netflix Top10 통합 검증
python3 -W ignore -c "
import sys; sys.path.insert(0, 'src')
from hit_predictor.rsi.ott_converter import extract_drama_performance, convert_to_virtual_rating
perf = extract_drama_performance('Squid Game')
print(perf)
print('virtual_rating:', convert_to_virtual_rating(perf))
"
# 기대: best_rank_kr=1, weeks_kr=19, ..., virtual_rating: 35.0

# 4) v3 자동화 파이프라인 재실행 (필요시)
python3 scripts/discover_new_dramas.py --year 2026 --month 4
python3 scripts/build_candidate_dramas.py --year 2026 --month 4 --dry-run
python3 scripts/fetch_nielsen_weekly.py --year-month 202604 --area both

# 5) 정제 대상만 빌드 (Phase 1-C 진입용)
python3 scripts/build_candidate_dramas.py --year 2026 \
    --titles "허수아비,기리고,로맨스의 절댓값,골드랜드,유미의 세포들 3" --dry-run
```

---

## 11. Git 상태 (커밋 시점 기준)

```
브랜치: feature/auto-collection-v3
최신 커밋: 6b54d43

커밋 히스토리:
6b54d43 v3.1: RSI 시간 감쇠 즉시 누진 + Netflix Top10 raw 격리
94350a3 Initial commit: v2 baseline + v3 auto-collection pipeline

워킹 트리: clean
원격: https://github.com/kimble125/k-drama-hit-predictor (push 완료)
```

⚠️ **부모 디렉터리 주의사항**: 이 프로젝트의 working dir(`/Users/kimble/.../k-drama-hit-predictor 3/`)은 사용자 홈(`/Users/kimble`)을 main worktree로 갖는 git의 *서브디렉터리*입니다. 따라서 `git status`에서 사용자 홈 시스템 파일들(예: `Library/Daemon Containers/`)이 노출될 수 있습니다.
- ✅ **반드시 명시적 파일만 `git add`**
- ❌ **절대 `git add .` / `git commit -a` 금지**

---

## 12. 첫 메시지 예시 (미루님이 GPT에게 보낼 템플릿)

```
안녕, 이 핸드오프 문서(HANDOFF_v5.md)를 먼저 읽어주세요.

현재 상태:
- Claude Code 작업방에서 v3.1 (RSI 즉시 누진 감쇠 + Netflix Top10 격리) 까지 commit·push 완료
- 다음 작업: [A. Phase 1-C 정제 / B. Phase 3 6축 점수 / C. 펀덱스 / D. 알고리즘 개선 / E. 통합 재계산 / F. 한↔영 제목 매핑]
  중 [내 선택] 부터 진행하고 싶어요.

작업 방식:
- 변경할 코드는 제가 채팅으로 붙여넣을게요
- 수정본 또는 diff를 받으면 제가 로컬에서 적용 + git commit 합니다
- 한국어로 응답해주세요. 변경 이유부터 설명해주세요.

추가 자료 첨부:
- HANDOFF_v5.md (이 문서)
- (필요 시) src/hit_predictor/rsi/calculator.py
- (필요 시) scripts/build_candidate_dramas.py
- (필요 시) data/discovered/2026-04.json
```

---

## 13. 부록 — 주요 파일 절대경로

```
프로젝트 루트:
/Users/kimble/Library/CloudStorage/GoogleDrive-hoykim125@gmail.com/내 드라이브/Git/k-drama-hit-predictor/k-drama-hit-predictor 3

핵심 파일:
- HANDOFF_v5.md (이 문서)
- HANDOFF_v4.md, HANDOFF_v3.md (이전 작업방)
- README.md
- pyproject.toml, requirements.txt
- src/hit_predictor/rsi/calculator.py        ← v3.1 변경점
- src/hit_predictor/rsi/ott_converter.py     ← Netflix 환산
- src/hit_predictor/rsi/schemas.py           ← Person/Credit + role_weight
- src/hit_predictor/data/schemas.py          ← Drama + MissingReason
- scripts/build_candidate_dramas.py          ← Phase 1-C 정제 대상
- scripts/discover_new_dramas.py
- scripts/fetch_nielsen_weekly.py
- data/discovered/2026-04.json               ← v3 발견 결과
- data/netflix_top10/.gitkeep                ← XLSX는 .gitignore
- data/nielsen_weekly/                       ← CSV는 .gitignore
- output/recalculated_results_v2.json        ← v3 재계산 미수행, v2가 baseline
```

---

## 14. v3.1 작업방 요약 (1줄)

> 시간 감쇠를 v3 (5년 풀가중 후 λ=0.15) → **v3.1 (즉시 시작 + λ=0.10)**으로 변경해 1~5년 최근작 차등화를 강화했고, Netflix Top10 raw XLSX(28MB+) 두 파일을 .gitignore로 격리했다. 코드 자체와 환산 로직은 공개 유지. v3.1의 **`recalculated_results_v3.json` 산출은 다음 작업방으로 이월**.

---

**이 문서를 ChatGPT에 붙여넣고, "어떤 단계부터 시작할까요?"로 물으면 GPT가 §7을 보고 옵션을 제시할 겁니다. 좋은 작업 되세요, 미루님!**
