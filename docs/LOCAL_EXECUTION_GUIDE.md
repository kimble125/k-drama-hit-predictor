# 🖥️ 로컬 실행 가이드

미루님이 로컬 컴퓨터에서 실행하셔야 하는 스크립트들과 실행 순서입니다.

---

## 📋 전체 흐름

```
현재 상태:
    ✅ TMDB로 수집된 필모그래피 46명 (is_lead 수정됨)
    ❌ 대부분 avg_rating/day_slot/time_slot 비어있음
    ❌ RSI 계산 시 rating 없어서 대부분 0으로 나옴

목표:
    ✅ 위키백과 + 나무위키로 시청률/방영정보 자동 수집
    ✅ 의미있는 RSI 계산 → 자동 H-Score 채점 완성
```

---

## 🛠️ 준비 (한 번만)

### 1. 프로젝트 풀기

다운로드 받은 zip 파일을 원하는 곳에 풀어주세요:

```bash
unzip k-drama-hit-predictor-v2.zip
cd k-drama-hit-predictor
```

### 2. Python 패키지 설치

```bash
pip install -r requirements.txt
pip install wikipedia-api  # 혹시 없으면
```

필요 패키지:
- `requests` (HTTP 요청)
- `beautifulsoup4`, `lxml` (HTML 파싱)
- `pandas` (데이터 처리)

---

## 🚀 실행 순서 (중요!)

### Step 1: 위키백과 메타데이터 수집 (필수, 10~15분)

**이게 가장 중요합니다.** 필모그래피 안 드라마 약 700편의 방영 정보를 자동 수집합니다.

```bash
python scripts/fetch_wikipedia_meta.py
```

**무슨 일이 일어나는가:**
- 필모그래피 JSON 모두 스캔 → 드라마 제목 추출
- 한국어 위키백과 API 호출 (별도 API 키 불필요!)
- 각 드라마의 인포박스에서 **방영 요일/시간/시청률/최고 시청률** 추출
- `data/wikipedia_meta.json` 에 캐시 저장
- 필모그래피 JSON들에 자동 병합

**예상 로그:**
```
📋 필모그래피에서 드라마 제목 추출 중...
   고유 드라마: 312편

  [1/312] 도깨비 ... ✓ ['day_slot', 'time_slot', 'avg_rating', 'max_rating']
  [2/312] 알함브라 궁전의 추억 ... ✓ ['day_slot', 'time_slot', 'avg_rating']
  [3/312] 진격의 거인 ... ✗ 미등록
  ...

🔄 필모그래피에 메타 병합 중...
✅ 완료
   수집: 312편 (신규 312편)
   실패: 47편
   병합된 인물: 38명
   병합된 크레디트: 480개
```

**예상 소요 시간**: 5~15분 (초당 5 request 정도)

### Step 2: 나무위키 보완 수집 (선택, 10~20분)

위키백과에 없는 마이너 드라마/신작을 나무위키에서 보완:

```bash
python scripts/fetch_namuwiki_fallback.py
```

**주의**: 나무위키는 요청 간격 2초로 천천히 fetch합니다 (라이센스 존중).

### Step 3: 닐슨 CSV 업데이트 (선택, 즉시)

이미 포함된 닐슨 CSV로 추가 병합하려면:

```bash
python scripts/merge_nielsen_ratings.py
```

(현재 닐슨 CSV는 2024~2026만이라 교집합이 적습니다. 닐슨 크롤러로 더 많이 쌓으면 좋음)

### Step 4: H-Score 재계산

모든 데이터가 준비됐으면 재계산:

```bash
python scripts/recalculate_candidates.py
```

**출력:**
- `output/recalculated_results_v2.json` — 전체 결과
- `output/recalculated_results_v2.csv` — 순위표
- 각 드라마의 **자동 산출** 캐스트/크리에이터 점수

### Step 5: 결과 파일을 Claude에게 업로드

`output/recalculated_results_v2.json` 파일을 Claude 프로젝트에 업로드하면
다음 대화에서 **비교표를 자동으로 생성**해드립니다.

---

## ❓ 자주 나오는 에러

### `ModuleNotFoundError: No module named 'hit_predictor'`

```bash
# 프로젝트 루트에서 실행하고 있는지 확인
pwd  # k-drama-hit-predictor 폴더여야 함
ls src/hit_predictor  # 이 폴더가 보여야 함
```

### `ConnectionError: ko.wikipedia.org`

- 네트워크 확인
- VPN 쓰는 경우 잠깐 꺼보기
- 캐시 파일이 있으면 중단된 지점부터 재시작됨 (안심하고 다시 실행)

### 위키백과 미등록 드라마가 많은 경우

인기 드라마는 거의 다 등록돼 있지만, **OTT 오리지널 최신작**이나 **마이너 드라마**는 없을 수 있습니다.
→ Step 2 나무위키 fallback 실행
→ 그래도 없으면 `data/wikipedia_meta.json`을 텍스트 에디터로 열어서 수동 보완 가능

---

## 🎯 Tip: 한 명만 먼저 테스트

전체 돌리기 전에 한 사람만 테스트해보려면:

```python
# Python 콘솔에서
import sys
sys.path.insert(0, "src")
from hit_predictor.data.wikipedia_fetcher import WikipediaClient

client = WikipediaClient()
meta = client.fetch_drama_meta("도깨비")
print(meta.to_dict())
# → {'title': '도깨비', 'channel': 'tvN', 'day_slot': '금토',
#    'time_slot': '20:00', 'avg_rating': 12.8, 'max_rating': 20.5, ...}
```

---

## 📊 이게 왜 중요한가 — 블로그 글감

미루님 블로그에 쓸 수 있는 기술적 스토리:

> **"공식 API vs 크롤링 — 한국 드라마 데이터 수집의 3단 파이프라인"**
>
> 1. TMDB → 배우 필모그래피 뼈대 (공식 API, 무료, 한계: 시청률 없음)
> 2. 위키백과 ko → 시청률·방영일 보완 (공식 API, 무료, CC BY-SA)
> 3. 나무위키 → 마이너 보완 (HTML 스크래핑, CC BY-NC-SA, 주의 필요)
>
> 각 소스의 라이센스, 안정성, 커버리지 비교.
> 한국 콘텐츠 데이터 분석 시 실전 적용 팁.
