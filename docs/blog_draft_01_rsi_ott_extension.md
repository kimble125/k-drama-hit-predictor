# 아이유가 <폭싹 속았수다>로 찍은 Netflix 1위, 이걸 '시청률 몇 %'로 바꿀 수 있을까?

> — 데이터로 배우 파워 측정하기, 그리고 한국 논문이 놓친 것

---

## 이 글에서 다룰 것

- 2019년 연세대 논문이 만든 **배우 능력 지표(RSI)** — 84% 정분류율을 달성한 실전 모델
- 근데 이 논문, **Netflix·Disney+를 못 다룬다** — OTT 시대엔 치명적 구멍
- 그래서 만든 **환산 공식**: Netflix Top10 → 지상파 시청률 등가치
- 실제 Python 코드와, **아이유·변우석 RSI 실측값** (스포: 둘 다 만점)
- 이걸로 뭘 할 수 있나 — 4월 기대작 <21세기 대군부인> 자동 채점

**소요 독서 시간: 8분**
**코드 실행 환경: Python 3.9+**
**전체 코드: [GitHub 레포지토리 링크]**

---

## 1. 문제: "김수현이 나오면 몇 %?"를 어떻게 숫자로?

미디어 업계 30년 관계자도 답 못 하는 질문입니다. 배우 캐스팅이 시청률에 얼마나 기여하는지, **아무도 정량적으로 측정 안 해왔어요**. 그냥 "김수현이면 15%, 신인이면 5%" 식의 감(感).

그런데 2019년, 연세대 주상필·홍준석·김우주 세 연구자가 이 감을 숫자로 만들었습니다. 논문 제목이 바로 "TV드라마 참여 인물의 계량 능력지표에 기반한 첫 회 시청률 상대적 우위 예측".

핵심 아이디어 하나만 기억하세요:

> **배우 A의 과거 드라마를 전부 꺼내서, 그 드라마들이 동시간대 경쟁작을 이겼는지 졌는지 계산한다. 승률이 곧 그 배우의 파워다.**

수식으로 쓰면 이렇습니다:

```
RSI(배우 A) = 승점 합계 / 참여 회차 수
  where 승점 = 1 (이겼을 때), 0.5 (동률), 0 (졌을 때)
```

간단하죠. 이게 전부예요. 논문은 이걸로 Naive Bayes 모델 돌려서 **84% 정분류율**을 찍었습니다. 현업에 바로 쓸 수 있는 수준이에요.

---

## 2. 근데 문제가 생겼습니다 — 2025년, 지상파가 죽었어요

논문은 지상파 3사(KBS·MBC·SBS) 밤 10시대만 분석합니다. 이유는 **비교 가능한 동시간대 경쟁작이 있어야** 승점을 계산할 수 있기 때문이에요.

그런데 우리가 사는 2025년 상황은 이렇습니다:

- 지상파 드라마 **평균 시청률 3~5%**로 떨어짐
- 히트 드라마는 대부분 Netflix (<폭싹 속았수다>, <오징어 게임>) 또는 Disney+ (<무빙>)
- **OTT 드라마는 시청률이 아예 없음** — 넷플릭스가 공개 안 함

그래서 RSI를 순수하게 적용하면 이런 기괴한 일이 벌어집니다:

```python
# 아이유의 최근 5년 TV 드라마: 0편 (호텔 델루나는 2019년)
# 아이유 RSI = 0.0  ← ???
```

글로벌 메가스타 아이유의 배우 파워가 0. 말이 안 되죠. 이건 **지표의 문제가 아니라 데이터 적용 범위의 문제**입니다.

---

## 3. 해결책: Netflix Top10을 시청률로 환산하자

다행히 Netflix가 2021년 11월부터 **공식 주간 Top10 데이터를 XLSX로 무료 공개**합니다:

```
https://www.netflix.com/tudum/top10/data/all-weeks-countries.xlsx
https://www.netflix.com/tudum/top10/data/all-weeks-global.xlsx
```

데이터 구조는 이렇습니다:

| week | country_iso2 | weekly_rank | show_title | cumulative_weeks_in_top_10 |
|------|-------------|------|-----------|----|
| 2025-03-10 | KR | 1 | 폭싹 속았수다 | 5 |
| 2025-03-10 | KR | 2 | 오징어 게임 시즌2 | 12 |

한국 Top10 + 글로벌 Top10 + 체류 주수. 이걸 지상파 시청률 스케일로 환산하는 공식을 만들었습니다:

```python
virtual_rating = base_rank × duration_factor × region_factor

# base_rank (Top10 순위별 기본 점수)
Rank 1        : 15.0  # 지상파 히트급
Rank 2-3      : 10.0
Rank 4-7      : 7.0
Rank 8-10     : 5.0

# duration_factor (체류 주수별 승수)
1주 : 1.0
2-3주 : 1.3
4-7주 : 1.7
8주+ : 2.0   # 오징어 게임급

# region_factor (지역 도달 승수)
KR Top10만       : 1.0
KR + Global Top10 : 1.3

# 최종 상한: 35 (오징어 게임 시즌1급)
```

검증해볼까요. 실제 흥행 기록을 이 공식에 넣으면:

```python
from hit_predictor import OTTPerformance, convert_to_virtual_rating

# 오징어 게임 시즌1 (Global 1위 + 한국 1위, 12주 체류)
squid = OTTPerformance(
    best_rank_kr=1, best_rank_global=1,
    weeks_in_top10_kr=12, weeks_in_top10_global=10,
)
print(convert_to_virtual_rating(squid))
# → 35.0 (상한 도달, 지상파 대히트 = 35% 시청률 등가)

# 폭싹 속았수다 (KR 1~2위, 글로벌 4위, 5주 체류)
ppo = OTTPerformance(
    best_rank_kr=1, best_rank_global=4,
    weeks_in_top10_kr=5, weeks_in_top10_global=4,
)
print(convert_to_virtual_rating(ppo))
# → 33.2 (역대급 오리지널 드라마 등가)
```

숫자가 **감각적으로 맞아떨어집니다**. 오징어 게임이 35% 시청률 드라마 정도의 영향력이었다? 납득되죠. 폭싹 속았수다가 33%? 이것도 말이 됩니다.

---

## 4. 또 하나의 문제 — 2019년 호텔 델루나를 2025년에도 똑같이 쳐야 할까?

RSI 계산할 때 논문은 "최근 5년" hard cutoff를 씁니다. 5년 안이면 100%, 밖이면 0%. 그런데 이건 너무 비연속적이에요.

배우의 과거작은 **시간이 지날수록 현재 파워를 대표할 설명력이 떨어집니다**. 그걸 자연스럽게 반영하려면 정보검색(IR) 분야에서 쓰는 **지수 감쇠 가중치**를 빌려오면 됩니다:

```python
import math

def time_decay_weight(years_ago, decay_rate=0.15, full_years=5):
    """5년까진 100%, 그 이후 지수적으로 감쇠."""
    if years_ago <= full_years:
        return 1.0
    return math.exp(-decay_rate * (years_ago - full_years))

# 검증
for y in [3, 5, 7, 10, 15, 20]:
    print(f"{y:2}년 전: {time_decay_weight(y):.3f}")
```

```
 3년 전: 1.000
 5년 전: 1.000
 7년 전: 0.741
10년 전: 0.472
15년 전: 0.223
20년 전: 0.105
```

20년 전 전성기 배우의 RSI가 10%만 반영되는 게 공정하죠. 수학적으로는 BM25의 freshness boost, PageRank의 damping factor와 같은 계열의 기법입니다. 머신러닝 모델에 이 `decay_rate`를 학습 가능한 파라미터로 넣으면 자동 튜닝도 됩니다.

---

## 5. 종합: 아이유 RSI는 얼마?

자, 모든 걸 조합해서 아이유의 진짜 RSI를 계산해봅시다.

**아이유의 최근 필모그래피:**
| 작품 | 연도 | 플랫폼 | 성과 |
|------|------|--------|------|
| 폭싹 속았수다 | 2025 | Netflix | 한국 Top1, 글로벌 Top4, 5주 체류 |
| 호텔 델루나 | 2019 | tvN | 평균 10.5% (토일 21:00) |
| 나의 아저씨 | 2018 | tvN | 평균 5.5% (수목 22:30) |

```python
from hit_predictor import calculate_rsi, OTTPerformance
from hit_predictor.rsi.storage import load_person

iu = load_person("아이유", "actor")
ott_map = {
    "폭싹 속았수다": OTTPerformance(
        best_rank_kr=1, best_rank_global=4,
        weeks_in_top10_kr=5, weeks_in_top10_global=4,
    ),
}

result = calculate_rsi(iu, ott_performance_map=ott_map, until_year=2026)
print(f"RSI: {result.rsi}")
# → RSI: 1.0 (3개 작품 모두 채널×시간대 벤치마크 대비 승리)
```

**RSI = 1.0**. 3개 작품 모두 각 채널·시간대 벤치마크를 이겼다는 뜻입니다. 수상 3회까지 더하면 H-Score 캐스트 파워 점수가 **10/10 만점**으로 환산됩니다.

이게 왜 중요하냐면, **이전엔 드라마 예측할 때 사람이 "아이유는 10점"이라고 주관적으로 입력**했어요. 이젠 이름만 넣으면 자동 산출됩니다. 100편 드라마 채점이 분 단위로 끝나요.

---

## 6. "하지만 tvN 월화 22:20 작품이 5.5% 벤치마크로 평가되면..."

이 글을 읽으시는 분 중 방송 좀 아시는 분은 여기서 멈추실 겁니다. **채널·시간대별로 시청률 기대치가 완전 다르거든요.**

변우석의 <선재 업고 튀어>(2024, tvN 월화 22:20)는 평균 4.1%입니다. 지상파 기준(5.5%)이면 평범하지만, tvN 월화 22:20 슬롯의 **실제 기대값은 3%** 수준이에요. 같은 4.1%가 전혀 다른 의미라는 거죠.

그래서 저는 **채널 × 요일 × 시간대 3단 계층 벤치마크**를 추가했습니다:

```python
# Level 1: 채널 × 요일 × 시간대 (최정밀)
CHANNEL_DAY_TIME_BENCHMARK = {
    ("SBS", "금토", "22:00"): 8.5,   # 지상파 금토 프라임
    ("tvN", "월화", "22:20"): 3.0,   # 변우석 작품 슬롯
    ("JTBC", "토일", "22:30"): 4.0,
    # ...
}

# Level 2 (요일까지만), Level 3 (채널만), Level 4 (전체 5.5%)
# → 계층적 fallback으로 조회
```

이걸 적용하니 변우석 RSI가 "열위"(0.0)에서 "완승"(1.0)으로 바뀌었어요. 잘못된 분석이 바로잡힌 거죠.

**이게 실제로 논문이 놓친 가장 큰 구멍입니다.** 2019년엔 지상파만 봤으니 벤치마크를 통일해도 괜찮았지만, 2025년엔 채널 스펙트럼이 너무 넓어서 통일 벤치마크가 의미 없어집니다.

---

## 7. 그래서 이걸로 뭘 하는가

이 RSI를 자동으로 뽑아내면, 방영 전 드라마의 **흥행 점수를 자동 채점**할 수 있습니다. 4월 기대작을 예로 들면:

```
1위: 21세기 대군부인 (아이유+변우석)  — H-Score 74.4 🔥 중박 이상
2위: 유미의 세포들3 (김고은)          — H-Score 67.5 🔥 중박 이상
3위: 오늘도 매진했습니다 (안효섭)     — H-Score 64.5 ⚡ 승부처
...
8위: 기리고 (노정의)                  — H-Score 41.3 📉 난항 예상
```

이 점수는 **배우 RSI, 감독·작가 RSI, 플랫폼 전략, 사전 화제성, 장르 적합도, IP 파워**를 종합한 값입니다. 수동으로 10개 필드 채우던 작업이 **이름 몇 개와 공개일 하나만 넣으면 자동**으로 돌아가게 됐어요.

---

## 8. 확장 — 여러분의 프로젝트에 쓸 수 있는 지점

이 글을 여기까지 읽으셨다면, 이 방법론이 **드라마만의 이야기가 아니라**는 걸 눈치채셨을 겁니다. RSI 개념은 이런 곳에 다 쓸 수 있어요:

- **음악**: 가수별 멜론/스포티파이 과거 차트 성적 → 신곡 히트 예측
- **영화**: 감독·배우의 과거 박스오피스 성적 → 개봉작 예상 관객수
- **유튜브**: 채널의 과거 영상 조회수 vs 카테고리 평균 → 신규 영상 예측
- **게임**: 스튜디오의 과거 작품 동접 vs 장르 평균 → 신작 흥행 예측

핵심은 **"경쟁작과 비교"**, **"시간 감쇠 가중치"**, **"도메인별 벤치마크 세분화"** 이 세 가지를 묶는 거예요.

---

## 이 글에 쓰인 전체 코드

GitHub: [https://github.com/kimble125/k-drama-hit-predictor](https://github.com/kimble125/k-drama-hit-predictor)

```bash
git clone https://github.com/kimble125/k-drama-hit-predictor.git
cd k-drama-hit-predictor
pip install -r requirements.txt

# Netflix 공식 데이터 다운로드
python scripts/fetch_netflix_top10.py --peek

# TMDB에서 배우 필모그래피 자동 수집
export TMDB_READ_TOKEN='eyJhbGci...'
python scripts/fetch_tmdb_filmography.py --actor "아이유"

# 4월 기대작 H-Score 일괄 채점
python scripts/rank_candidates.py
```

---

## 이어지는 글 예고

다음 편은 **"왜 Neural Network보다 Naive Bayes가 이겼나 — 작은 데이터의 저주"**입니다. 주상필 논문에서 NB 84%, NN 58%로 예상 밖 역전이 일어난 이유를 파헤쳐봅니다. `curse of dimensionality`가 실전에서 어떻게 드러나는지 보고 싶으신 분께 추천.

---

**참고 논문:**
- 주상필·홍준석·김우주 (2019). "TV드라마 참여 인물의 계량 능력지표에 기반한 첫 회 시청률 상대적 우위 예측". 한국콘텐츠학회논문지, 19(6), 179-192.
- 최현종·박영선·정수미·김화종 (2017). "데이터 마이닝을 통한 지상파 드라마 첫 회 시청률 예측 모형 연구". 한국정보기술학회논문지, 15(1), 1-10.
- 남기환·성노윤 (2018). "초기 시청시간 패턴 분석을 통한 대흥행 드라마 예측". JIIS, 24(4), 33-49.

**데이터 출처:**
- Netflix Top 10 (https://www.netflix.com/tudum/top10/)
- TMDB API (https://www.themoviedb.org/)
- 닐슨 코리아 (https://www.nielsenkorea.co.kr/) — 크롤러는 개인 연구용

---
*미루(kimble125) | 콘텐츠 데이터 분석 | 2026.04*
