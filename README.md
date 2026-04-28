# K-Drama Hit-Predictor

**논문 6편 + 한국 콘텐츠 산업 데이터로 만든 K-드라마 흥행 예측 프레임워크**

방영 전 K-드라마의 흥행 잠재력을 6축 H-Score로 정량 평가하고, Triple KPI(첫방·평균·상대우위)로 분리 예측합니다. RSI 자동 산출, OTT 시청률 환산, 시간 감쇠 가중치, 채널×시간대 벤치마크 세분화 등 기존 학술 모델을 OTT 시대로 확장한 구조.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 📌 한 눈에

```
입력: 드라마 1편 (배우, 감독, 작가, 플랫폼, 공개일 등)
   ↓
[1] TMDB·위키백과·나무위키에서 필모그래피 자동 수집
[2] Netflix Top10 → 가상 시청률 환산 (rank × duration × region)
[3] 채널×요일×시간대별 벤치마크와 비교 → 개인별 RSI 계산
[4] 시간 감쇠(exp decay)로 5년+ 전작 가중치 자동 조정
[5] 신인 작가·감독은 수상/검증 가산 fallback
   ↓
출력: Triple KPI 점수 (first_ep / avg / rsi_victory) + 종합 H-Score 0-100
      + 4단 verdict (대박 / 중박 / 다크호스 / 난항)
```

**실측 예시 (2026년 4월 K-드라마 8편):**

| 순위 | 드라마 | 종합 H | 전망 |
|---|---|---|---|
| 1 | 모두가 자신의 무가치함과 싸우고 있다 | 63.9 | ⚡ 승부처 |
| 2 | 허수아비 | 61.1 | ⚡ 승부처 |
| 3 | 오늘도 매진했습니다 | 60.8 | ⚡ 승부처 |
| 4 | 골드랜드 | 60.1 | ⚡ 승부처 |
| 5 | 유미의 세포들3 | 57.3 | ⚡ 승부처 |
| 6 | 21세기 대군부인 | 54.6 | ❓ 다크호스 |
| 7 | 은밀한 감사 | 48.1 | ❓ 다크호스 |
| 8 | 기리고 | 44.5 | 📉 난항 예상 |

자세한 분석: [흥행 디코딩 #1 - 콘텐츠 블로그](https://forrest125.tistory.com/114) | [기술 해설 - IT 블로그](https://kimble125.tistory.com/)

---

## 🏗️ 아키텍처

### 6축 H-Score

| 축 | 의미 | 자동 산출 |
|---|---|---|
| `cast_power` | 주연 배우들의 RSI 평균 + 수상 + SNS | ✅ 필모그래피 DB |
| `creator_power` | 감독 RSI + 작가 RSI + 협업 보너스 | ✅ 필모그래피 DB |
| `ip_power` | 원작 팬덤 (웹툰·웹소설·시즌제) | 🔶 부분 자동 |
| `platform_strategy` | 플랫폼 + 슬롯 lead-in + 글로벌 동시공개 | ✅ 닐슨 DB |
| `pre_buzz` | FUNdex + 검색량 + 티저 (시간 정규화) | 🔶 부분 자동 |
| `genre_market_fit` | 2025 장르 트렌드 + 계절 + 혼합도 | ✅ 자동 |

### Triple KPI

각 축에 가중치를 다르게 곱해 **3개 트랙으로 분리 예측**합니다 (강명현 2019의 "시청률 ≠ 가치평가지표" 발견 반영):

```
first_ep_v2     = 첫방 시청률 (캐스트 13, 사전화제성 20 강조)
avg_v2          = 평균 시청률 (크리에이터 15, 장르 13 강조)
rsi_victory_v2  = 동시간대 상대우위 (캐스트·크리에이터 RSI 16,16 강조)

combined = first_ep × 0.30 + avg × 0.50 + rsi_victory × 0.20
```

---

## 🔬 기술 핵심 — 논문 어떻게 확장했는가

### 1. RSI (Relative Superiority Index)
**원전**: 주상필·홍준석·김우주 (2019). 한국콘텐츠학회논문지 19(6).

```
RSI = Σ(wins_i × time_weight_i) / Σ(time_weight_i)
```

**확장 사항:**
- ✅ **시간 감쇠 (Exponential decay)**: hard cutoff(5년) 대신 `exp(-0.15 × (years - 5))`로 점진적 감쇠
- ✅ **OTT 환산**: Netflix Top10 → 가상 시청률 (`rank × duration × region`, 상한 35)
- ✅ **신인 fallback**: 필모그래피 비어 있으면 수상·검증 가산점 기반 0.3~0.6 부여

### 2. Lead-in 효과
**원전**: 최현종 외 (2017). 한국정보기술학회논문지 15(1).

같은 슬롯 직전 드라마의 **후반 25% 회차 평균 시청률**을 새 드라마의 첫방 모멘텀 지표로 사용. `core/lead_in.py`에 구현, `platform_strategy` 축의 서브필드로 통합.

### 3. 사후 업데이트 예측
**원전**: 남기환·성노윤 (2018). 지능정보연구 24(4).

방영 1~3회 시청률·펀덱스 추이가 들어오면 사전 예측을 Bayesian-style로 업데이트. `prediction/updater.py`에 구현.

### 4. 채널×시간대 벤치마크 세분화 (독자 확장)
"지상파 5.5%" 일괄 벤치마크의 한계를 보완. tvN 월화 22:20 = 3.0%, SBS 금토 22:00 = 8.5% 등 21개 슬롯 × 3단 fallback 계층으로 정밀화. `core/benchmarks.py`.

---

## 🚀 빠른 시작

### 설치

```bash
git clone https://github.com/kimble125/k-drama-hit-predictor.git
cd k-drama-hit-predictor
pip install -r requirements.txt
```

### 1. 단일 드라마 대화형 예측

```bash
python scripts/predict_drama.py
```

6축 점수를 순차 입력하면 Triple KPI + verdict 출력.

### 2. 후보 드라마 일괄 예측

```bash
python scripts/rank_candidates.py
```

출력: `output/ranking_results.json`, `output/ranking_results.csv`.

### 3. 필모그래피 자동 수집 (TMDB)

```bash
export TMDB_READ_TOKEN='eyJhbGci...'  # 본인 토큰

# 단일 인물
python scripts/fetch_tmdb_filmography.py --actor "아이유"

# CSV 일괄
python scripts/fetch_tmdb_filmography.py --from-csv data/candidate_dramas.csv
```

### 4. 위키백과 ko 메타 보완

```bash
python scripts/fetch_wikipedia_meta.py
```

방영 요일/시간/시청률을 자동 보완 후 필모그래피에 병합.

### 5. Netflix Top10 다운로드

```bash
python scripts/fetch_netflix_top10.py --peek
```

---

## 📂 프로젝트 구조

```
k-drama-hit-predictor/
├── src/hit_predictor/
│   ├── core/              # H-Score 엔진 (6축, Triple KPI, 벤치마크)
│   │   ├── axes.py        # 6축 정의 + 장르 트렌드 2025
│   │   ├── weights.py     # Triple KPI 가중치 프로파일
│   │   ├── temporal.py    # 사전화제성 시간 정규화
│   │   ├── benchmarks.py  # 채널×시간대 3단 벤치마크
│   │   ├── lead_in.py     # 슬롯 모멘텀
│   │   └── hscore.py      # 통합 계산 엔진
│   ├── rsi/               # RSI 자동 산출
│   │   ├── calculator.py  # 시간감쇠 + OTT환산 + 신인fallback 통합 RSI
│   │   ├── ott_converter.py        # Netflix Top10 환산
│   │   ├── newcomer_fallback.py    # 신인 작가/감독 가산점
│   │   ├── tmdb_fetcher.py         # TMDB 자동 수집
│   │   └── storage.py     # 필모그래피 JSON DB
│   ├── data/              # 데이터 수집·병합
│   │   ├── nielsen_merger.py       # 닐슨 CSV 병합
│   │   ├── wikipedia_fetcher.py    # 위키 ko 인포박스 파싱
│   │   ├── namuwiki_fetcher.py     # 나무위키 fallback
│   │   └── collectors/nielsen.py   # 닐슨 크롤러
│   ├── calibration/       # 6-method 가중치 학습
│   └── prediction/updater.py       # 방영 후 Bayesian 업데이트
├── scripts/               # CLI 진입점
├── data/
│   ├── filmography/       # 배우/감독/작가 필모그래피 JSON
│   ├── candidate_dramas.csv        # 예측 대상 드라마
│   ├── completed_dramas.csv        # 캘리브레이션용 종영작
│   └── nielsen_weekly/    # 닐슨 CSV (.gitignore로 미포함)
├── output/                # 예측 결과
└── docs/                  # 가이드 문서
```

---

## 📊 데이터 출처와 라이센스

| 출처 | 사용 범위 | 라이센스 | 재배포 |
|------|---|---|---|
| TMDB API | 필모그래피 (배우·감독·작가) | 무료 (API Key 필요) | 출처 명시 시 가능 |
| 위키백과 ko | 방영일·시청률·인포박스 | CC BY-SA | 가능 |
| 나무위키 | 마이너 드라마 fallback | CC BY-NC-SA 4.0 | **비상업** 한정 |
| Netflix Top10 | 글로벌 OTT 순위 | 공식 무료 공개 | 출처 명시 시 가능 |
| 닐슨 코리아 | TV 시청률 | 이용약관상 재배포 금지 | **재배포 불가** |
| 굿데이터 FUNdex | 화제성 지표 | 리포트 인용 | 인용만 가능 |

> **닐슨 데이터 정책**: `data/nielsen_weekly/` 디렉토리는 `.gitignore`로 제외됩니다. 크롤러 코드(`src/hit_predictor/data/collectors/nielsen.py`)는 공개되지만 수집된 데이터는 로컬에만 보관하며 재배포하지 않습니다.

---

## ⚠️ 한계 & 로드맵

### 현재 한계
- **국내 OTT 미지원**: TVING/Wavve/쿠팡플레이는 공식 차트가 없어 펀덱스로 간접 측정
- **정성적 분석 부재**: 작품성·서사·연출 문법은 평가 안 함 (외부 정량지표만 반영)
- **일부 신인 누락**: 데뷔작 작가/감독은 수기 등록 필요 (`KNOWN_NEWCOMERS`)
- **종영작 학습 데이터 부족**: 25편 → 50편 이상 확장 시 RF/GB 모델 활성화 가능

### 다음 목표
- **첫 회 감상 후 작품성 AI 보정 레이어** — 컷잘알 기술과 통합. 대본 텐션 구조, 장면 전환 리듬, 대사 밀도가 H-Score에 반영되도록.
- **국내 OTT 환산식** — TVING/Wavve의 펀덱스 화제성 → 가상 시청률 변환식
- **TVING 단독작 OTT 환산 v2** — Netflix 외 플랫폼 적용 확장

---

## 📚 참고 논문

1. 주상필·홍준석·김우주 (2019). *TV드라마 참여 인물의 계량 능력지표에 기반한 첫 회 시청률 상대적 우위 예측*. 한국콘텐츠학회논문지 19(6).
2. 최현종·박영선·정수미·김화종 (2017). *데이터 마이닝을 통한 지상파 드라마 첫 회 시청률 예측 모형 연구*. 한국정보기술학회논문지 15(1).
3. 남기환·성노윤 (2018). *초기 시청시간 패턴 분석을 통한 대흥행 드라마 예측*. 지능정보연구 24(4).
4. Ahn, Ma, Lee, Sura (2017). *Do big data support TV viewing rate forecasting? A case study of a Korean TV drama*. Information Systems Frontiers 19.
5. 강명현 (2019). *가치평가지표를 통한 드라마 시청성과 측정*. 한국방송학보 33(5).
6. 윤용아 (2020). *TV 드라마 〈동백꽃 필 무렵〉의 성공 요인 분석*. 영상기술연구 32.
7. 전익진·은혜정 (2014). *연관 규칙 분석을 이용한 시청률 분석 연구*. 한국언론학보 58(5).

---

## 📜 라이센스

코드는 [MIT License](LICENSE) 아래 자유롭게 사용 가능합니다. 단, 데이터(특히 닐슨 코리아)는 각 출처의 라이센스를 따릅니다.

---

## 🙋 연락 / 기여

미루 (kimble125)  
- 콘텐츠 블로그: [forrest125.tistory.com](https://forrest125.tistory.com)
- IT 블로그: [kimble125.tistory.com](https://kimble125.tistory.com)
- GitHub: [@kimble125](https://github.com/kimble125)

피드백·이슈·PR 환영합니다.
