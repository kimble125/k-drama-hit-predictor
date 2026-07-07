# 🔄 Hit-Predictor v6 — 다음 Claude Code 세션 핸드오프 (v3.1 + 12 filmography 수동 보강 완료)

> **이 문서의 수신 대상**
> 1. **Claude Code 새 세션** (1순위): 코드 최신화 + 5월 드라마 H-Score 조사 (사후 검증 + 신작 추가)
> 2. **ChatGPT Codex** (2순위): Claude Code 1차 작업 종료 후 후속 발전
>
> v5(`HANDOFF_v5.md`)와 함께 읽으세요. v6은 **v5 이후 변경분과 5월 작업 가이드만** 다룹니다. 기초 정보(코드 구조, 산식, 정책 등)는 v5 유지.
>
> **2026-05-01 ~ 2026-05-02 추가 작업 요약 (이번 세션)**
> - 12개 filmography JSON 수동 생성 (web research 기반): 감독 3명·작가 3명·배우 6명
> - H-Score v3 재계산: 허수아비 50.4→**56.8** ⚡, 은밀한 감사 49.0→**50.7**, 골드랜드 54.4→**52.6**
> - AI학습용 분석 컨텍스트 파일 추가 (`docs/[AI학습용]...md`, 543줄/28KB)
> - PR #1 생성·머지 가능 상태

---

## 0. 빠른 시작 (3분)

```
1. 미루님으로 부르세요. (오빠 X, 본명 X)
2. Python 초보입니다. 코드 수정 제안 시 한국어로, 변경 이유부터 설명해주세요.
3. 답변은 한국어로.
4. 현재 브랜치: main (HEAD)
5. 최신 commit: 54c7bda  "docs: AI학습용 H-Score 분석 컨텍스트 파일 추가"
6. GitHub: https://github.com/kimble125/k-drama-hit-predictor
7. PR #1: https://github.com/kimble125/k-drama-hit-predictor/pull/1 (open, main → claude/mystifying-sutherland-5aaec0)
8. 사용자 환경: macOS, Python 3.9+, 로컬 디렉터리
   /Users/kimble/Library/CloudStorage/GoogleDrive-hoykim125@gmail.com/내 드라이브/Git/k-drama-hit-predictor/k-drama-hit-predictor 3
```

**오늘 미루님이 시작할 작업 (확정)**
- ✅ **5월 드라마 H-Score 조사**: 기존 4편(허수아비·은밀한 감사·골드랜드·기리고) 사후 검증 + 5월 신작 추가
- 🟡 **코드 최신화 우선순위**: 이 채팅과 **Perplexity 피드백** 결과를 바탕으로 **다음 세션에서 결정**
- ⏭️ **ChatGPT Codex 이양**: 위 1차 작업이 끝난 시점에 별도 세션 핸드오프

---

## 1. v5 → v6 변경 사항 (이번 세션의 산출물)

### 1-1. filmography 12개 수동 생성 (`data/filmography/`)

v5의 §6-3에서 “TMDB filmography 일괄 자동수집 대상”으로 잡혔던 인물 중 12명을 **TMDB 토큰 없이 web research**로 우선 채움. 모든 파일은 `"notes": "manually_created"` 태그 포함 (데이터 계보 추적용).

| 분류 | 인물 | 드라마 | RSI | 핵심 근거작 |
|------|------|--------|-----|------------|
| director | **이수현** | 은밀한 감사 | 0.355 | 그놈은 흑염룡(2025), 이로운 사기(2023) 모두 tvN 월화 벤치 경계 |
| director | **박준우** | 허수아비 | **0.592** | 모범택시(2021 SBS 금토 12.0%, max 18.0%) |
| director | **김성훈** (1974생) | 골드랜드 | 1.0 | 수사반장 1958(2024 MBC 금토 10.3%, max 12.9%) — **킹덤 김성훈(1971생)과 동명이인 주의** |
| writer | **여은호** | 은밀한 감사 | 1.0 | 일타 스캔들(2023 tvN 토일 17.0%, max 18.9%) — **공동집필**(양희승 작가와) |
| writer | **이지현** | 허수아비 | 1.0 | 모범택시(2021, 박준우 감독과 재결합) |
| writer | **황조윤** | 골드랜드 | 0.0 | 영화 각본만 존재(올드보이·광해·창궐), 드라마 첫 작품 |
| actor | **박보영** | 골드랜드 | 0.635 | 힘쎈여자 도봉순(2017 JTBC 6.5%) |
| actor | **김성철** | 골드랜드 | 0.622 | 슬기로운 감빵생활(2017), 아스달 연대기(2019) |
| actor | **이현욱** | 골드랜드 | 0.0 | 마인·타인은 지옥이다 모두 벤치 하회 |
| actor | **김희원** | 골드랜드 | 0.331 | 사이코지만 괜찮아(2020 tvN 토일 9.5%, 조연) |
| actor | **문정희** | 골드랜드 | 1.0 | 마마(2014 MBC 14.0%, max 21.4%), 배가본드(2019 SBS 8.9%) |
| actor | **이광수** | 골드랜드 | 0.177 | 디어 마이 프렌즈(2016) 외 최근작 저조 |

⚠️ **검증 필요 사항**
- 김성훈 감독은 **1974년생** 기준 (공조 시리즈·수사반장 1958). 1971년생 김성훈(킹덤·신호 시리즈)이 골드랜드를 연출했다는 다른 소스가 있다면 재확인 필요.
- 여은호 작가는 일타스캔들 **공동집필**. 단독 집필 역량은 「은밀한 감사」로 첫 검증 중.

### 1-2. H-Score v3 재계산 결과 (`output/recalculated_results_v3.{json,csv}`)

| 드라마 | v5 시점 | v6 (현재) | Δ | Verdict 변화 |
|--------|---------|-----------|---|-------------|
| **허수아비** | 50.4 | **56.8** | **+6.4** | ❓ → **⚡ 승부처** |
| **은밀한 감사** | 49.0 | 50.7 | +1.7 | ❓ → ❓ (creator_auto 0→6.8) |
| **골드랜드** | 54.4 | 52.6 | −1.8 | ❓ → ❓ (cast_auto None→5.1, creator_auto 0→5.0) |
| 기리고 | 44.9 | 44.9 | 0.0 | 변화 없음 (감독·작가 미수집) |
| 모두가 자신의… | 62.5 | 62.5 | 0.0 | |
| 21세기 대군부인 | 66.1 | 66.1 | 0.0 | |
| 오늘도 매진했습니다 | 60.5 | 60.5 | 0.0 | |
| 유미의 세포들3 | 53.8 | 53.8 | 0.0 | |
| 로맨스의 절댓값 | 37.2 | 37.2 | 0.0 | 캐스트 10명 전원 missing 유지 |

**골드랜드 감소 이유**: cast_auto=None이었던 상태가 5.1로 채워졌는데, 이전 수동 입력값(6.0)보다 낮아서 종합 점수가 소폭 하락. 데이터의 정직한 반영.

### 1-3. AI학습용 H-Score 분석 컨텍스트 파일 신규 추가

`docs/[AI학습용] 26년 4-5월 드라마 H-Score 분석_은밀한감사·허수아비·골드랜드·기리고.md` (543줄/28KB)

- 4개 드라마 각각: 기본 정보 / H-Score 6축 / 출연진 RSI 상세 / 크리에이터 RSI / 편집 포인트(탑승각·하차각) / miru 메모 소재
- 4편 비교 요약 테이블 + 블로그 글 작성 가이드 포함
- 용도: 티스토리 블로그 「오늘의 하차/탑승」 시리즈 글 작성 시 Claude에 제공하는 컨텍스트

### 1-4. Git 상태 (이번 세션 종료 시)

```
브랜치: main (HEAD)
워킹 트리: clean

새 커밋 (v5 이후):
54c7bda   docs: AI학습용 H-Score 분석 컨텍스트 파일 추가
4cc95a6   feat: 은밀한감사·허수아비·골드랜드 감독·작가·배우 12명 filmography 수동 생성 + v3 재계산
e7cdd4b   docs: HANDOFF_v5 § 11 git 상태 최종 commit hash 반영 (v5 시점 최종 commit)

PR:
#1 open  https://github.com/kimble125/k-drama-hit-predictor/pull/1
   base: claude/mystifying-sutherland-5aaec0 (v5 시점 commit e7cdd4b로 새로 생성된 비교 브랜치)
   head: main (위 2개 새 commit 포함)
```

---

## 2. 다음 세션 작업 — 5월 드라마 H-Score 조사 (가이드)

### 2-A. 기존 4편 사후 검증 (방영 후 실적 수집)

**대상**: 허수아비, 은밀한 감사, 골드랜드, 기리고

**수집해야 할 데이터**:

| 항목 | 출처 | 비고 |
|------|------|------|
| 회차별 시청률 | 닐슨 코리아 / 굿데이터 펀덱스 | TV 본방작(허수아비·은밀한 감사). OTT는 N/A |
| 최고 시청률(max_rating) | 동상 | |
| 평균 시청률(avg_rating) | 동상 | 종영 전이라도 현재까지 평균 산출 |
| Netflix Top10 순위 | data/netflix_top10/*.xlsx | 골드랜드(Disney+)·기리고는 Top10 미해당 → 별도 OTT 화제성 지표 모색 |
| 펀덱스 화제성 | data/pundex_archive/ (v5 §8 청사진) | 자동화 미구현 — 수동 PDF 다운로드 우선 |
| SNS 화제성 | Twitter/X, 네이버 검색량 | pre_buzz 사후 검증용 |

**검증 절차**:
1. `data/candidate_dramas.csv`의 각 행에 `release_date`, `actual_first_ep_rating`, `actual_avg_rating`, `actual_max_rating` 컬럼 채우기 (없으면 신규 컬럼 추가)
2. `scripts/update_postlaunch.py` 활용 (v5 §4에 존재 — 동작 확인 필요)
3. 예측값 vs 실제 차이를 `output/postlaunch_validation_v3.csv` 등으로 저장
4. **2회 7.7%로 확인된 은밀한 감사**의 사례처럼 H-Score 모델의 보수성·낙관성 평가

**중요 관찰점 (이미 알려진 것)**:
- 은밀한 감사 2회 7.7% — 예측 H-Score 50.7(❓)보다 실적 좋음. tvN 토일 벤치 6.5% 초과 → RSI WIN 확정
- release_date 미입력으로 pre_buzz 정규화 안 됨 → release_date 채우면 combined ≈ 52.4 추정

### 2-B. 5월 신작 발견·분석

**파이프라인**:

```bash
cd "/Users/kimble/Library/CloudStorage/GoogleDrive-hoykim125@gmail.com/내 드라이브/Git/k-drama-hit-predictor/k-drama-hit-predictor 3"

# Step 1: 5월 신작 자동 발견 (위키 + 나무위키 + TMDB)
python3 scripts/discover_new_dramas.py --year 2026 --month 5
# → data/discovered/2026-05.json

# Step 2: candidate_dramas.csv에 추가 (dry-run으로 먼저 확인)
python3 scripts/build_candidate_dramas.py --year 2026 --month 5 --dry-run

# Step 3: 닐슨 5월 수집
python3 scripts/fetch_nielsen_weekly.py --year-month 202605 --area both

# Step 4: 통합 재계산
python3 scripts/recalculate_candidates.py --version v3
```

**주의 — v5 §6-1의 자동 수집 버그 영향**:
- `build_candidate_dramas.py`가 인포박스 변형(공백 정규화·셀렉터 미스매치)에 약함
- 5월 신작에서도 None 채워질 가능성 높음 → **자동 수집 결과 검토 후 수동 보완**
- v5 §9-4 정책 환기: "수작업 수정 금지 — 잘못된 정보는 수집 로직을 고치지 결과물 CSV를 직접 편집 X" — 그러나 마감 압박 상황에서는 일시적으로 수동 입력 후 별도 이슈로 기록 권장

### 2-C. Perplexity 피드백 통합 절차 (다음 세션 시작 시)

미루님이 Perplexity로 받은 피드백을 다음 세션에 가져올 예정. 통합 절차:

1. **세션 시작 시 피드백 텍스트를 그대로 붙여넣기**
2. Claude Code가 피드백을 다음 카테고리로 분류:
   - (a) 모델 산식 개선 제안 → `src/hit_predictor/core/` 변경 후보
   - (b) 데이터 수집 누락 항목 → `scripts/` 또는 `data/` 보강
   - (c) 결과 해석 오류 → 블로그 글·AI학습용 파일 정정
   - (d) 신규 인사이트 → backlog 추가
3. 분류 결과 + 이 채팅방 작업 결과를 종합해 **§3의 우선순위 보드**에서 1순위 결정

---

## 3. 우선순위 보드 (다음 세션에서 결정)

> v5 §7의 옵션 + 이번 세션 추가분. **순위는 다음 세션에서 Perplexity 피드백 + 5월 조사 결과를 보고 확정**합니다.

| 옵션 | 작업 | 예상 소요 | v5 ROI 평가 | v6 추가 메모 |
|------|------|----------|-----------|------------|
| **A** | 5월 신작 발견·H-Score 산출 | 1~2h | — | **이번 세션 시작 직후 권장** |
| **B** | 기존 4편 사후 검증 (post-launch validation) | 1h | — | 은밀한 감사 2회 7.7% 등 일부 데이터 이미 있음 |
| **C** | TMDB filmography 일괄 자동수집 (잔여 인물) | 1h | **v5 1순위** | 이번 세션에서 12명 수동 보완 → 잔여 인물 줄어듦. **여전히 1순위 후보** |
| **D** | Phase 1-C 자동수집 버그 픽스 (5건) | 1~2h | v5 2순위 | 5월 신작 빌드에서 또 발생 가능성 — **5월 조사 후 빈도 평가** |
| **E** | Phase 3 — auto_score.py (6축 자동 산정) | 2~3h | v5 4순위 | |
| **F** | Phase 2-B — 펀덱스 PDF 아카이빙·파싱 | 2h | v5 5순위 | 사후 검증 데이터 소스로 활용 가치 |
| **G** | 알고리즘 — 영화 cross-media bonus + 베테랑 fallback + win 격차 가중 | 1~2h | v5 6순위 | |
| **H** | 한국어↔영문 제목 매핑 (Netflix Top10 매칭용) | 30m | v5 7순위 | 사후 검증에서 OTT 매칭 필요 시 ROI 올라감 |
| **I** | 블로그 글 #2 (v3.1 결과 해설) | 1h | v5 8순위 | AI학습용 파일이 이미 작성됨 → 글 작성 직행 가능 |
| **J** | **신규** — 결측치 정책 도구화 (csv 정정 시 수집 로직 수정 검증 자동화) | 2h | v6 신규 | v5 §9-4 정책 강제 자동화 |

**ROI 재평가 가이드** (다음 세션 시작 시):
- 5월 신작이 자동수집에서 또 None 다발 → D(버그 픽스) ROI ↑
- 사후 검증에서 OTT 매칭 실패 다발 → H(제목 매핑) ROI ↑
- Perplexity 피드백이 산식 개선 중심 → G(알고리즘) ROI ↑
- 피드백이 데이터 누락 중심 → C(TMDB) ROI ↑

---

## 4. 이번 세션 후 잔존 작업 (v5 §6-3 갱신)

### 4-1. TMDB filmography 미수집 인물 (v5 대비 줄어듦)

**ACTORS — 20명 잔여** (v5 26명에서 6명 감소)
- 21세기 대군부인: 노상현, 공승연
- 유미의 세포들3: 김재원, 전석호, 최다니엘
- 모두가 자신의…: 강말금, 배종옥, 한선화, 최원영
- ~~골드랜드 (6명): 박보영, 김성철, 이현욱, 김희원, 문정희, 이광수~~ ✅ **이번 세션 완료**
- 로맨스의 절댓값 (10명): 여의주, 김향기, 가우수, 차학연, 노다주, 김재현, 정기전, 손정혁, 윤동주, 김동규
- 기타 변동 가능

**DIRECTORS — 4명 잔여** (v5 7명에서 3명 감소)
- ~~이수현(은밀한 감사)~~ ✅, ~~박준우(허수아비)~~ ✅, ~~김성훈(골드랜드)~~ ✅ — 이번 세션 완료
- 잔여: 박윤서(기리고), 배희영(공동연출 21세기), 이슬기(오늘도 매진), 차영훈(모두가)

**WRITERS — 4명 잔여** (v5 7명에서 3명 감소)
- ~~여은호(은밀한 감사)~~ ✅, ~~이지현(허수아비)~~ ✅, ~~황조윤(골드랜드)~~ ✅ — 이번 세션 완료
- 잔여: 박중섭(기리고), 박해영(모두가), 유지원(21세기), 진승희(오늘도 매진)

**TMDB 자동수집 명령** (v5 §6-3 동일):
```bash
export TMDB_READ_TOKEN="..."  # 미루님 직접 export
python3 scripts/fetch_tmdb_filmography.py --names "노상현,공승연,김재원,..." --role actor
python3 scripts/fetch_tmdb_filmography.py --names "박윤서,배희영,이슬기,차영훈" --role director
python3 scripts/fetch_tmdb_filmography.py --names "박중섭,박해영,유지원,진승희" --role writer

# 수집 후 v4 재산출
python3 scripts/recalculate_candidates.py --version v4
```

### 4-2. v5에서 이월된 검증 필요 사항

- **오늘도 매진했습니다 감독·작가** (v5 §6-1-B): director 조영민 vs 이슬기 / writer 이영미 vs 진승희 — 자동 수집값 채택 중, 원본 확인 필요
- **로맨스의 절댓값 director·writer**: 자동 수집 실패 — 사용자 자료 또는 방송사 공식 fallback 필요
- **모두가 자신의…, 은밀한 감사 release_date**: wikipedia 미수록 → 보강 필요 (은밀한 감사는 2026.04.25로 확인됨 — CSV 입력 필요)

### 4-3. 이번 세션에서 새로 발견된 사항

- **AI학습용 파일 갱신 트리거**: 다음 세션에서 4편의 사후 검증·5월 신작이 추가되면 `docs/[AI학습용]...md`도 업데이트 필요. 매번 새로 만들기보다 **v6.1, v6.2 식 버전 관리** 권장.
- **PR #1**: open 상태. 머지 결정은 다음 세션 첫 단계로 처리(또는 미루님 즉시 결정).

---

## 5. ChatGPT Codex 이양 시 인계 사항 (다음 세션 종료 시점에 작성 예정)

> 이 섹션은 다음 Claude Code 세션이 끝날 때 채워질 placeholder입니다. 다음 세션 종료 시 다음 정보를 정리해야 합니다:

- [ ] 5월 신작 추가된 candidate_dramas.csv 최종 상태
- [ ] 사후 검증 결과 (예측 vs 실제 비교 테이블)
- [ ] Perplexity 피드백 처리 결과 (반영 항목 / 미반영 항목)
- [ ] 코드 변경분 (`src/` 수정사항 + diff 요약)
- [ ] ChatGPT Codex 환경 제약 고지 (v5 §9-1과 동일)
- [ ] Codex가 받아 처리하기 적합한 작업과 부적합한 작업 분류

**Codex 추천 작업 패턴**:
- 적합: 산식·알고리즘 개선(`core/`, `rsi/calculator.py` 수정), 단위 함수 리팩터, 테스트 작성
- 부적합: 다중 외부 사이트 크롤링 디버깅(브라우저 환경 필요), 대량 데이터 수집 자동화

---

## 6. 즉시 실행 가능한 검증 명령 (작업 재개 첫 단계)

```bash
cd "/Users/kimble/Library/CloudStorage/GoogleDrive-hoykim125@gmail.com/내 드라이브/Git/k-drama-hit-predictor/k-drama-hit-predictor 3"

# 1) 현재 상태 확인
git status
git log --oneline -5
# 기대: 54c7bda HEAD, working tree clean

# 2) PR #1 상태 확인 (gh CLI 없으면 GitHub 웹에서)
#    https://github.com/kimble125/k-drama-hit-predictor/pull/1

# 3) v3.1 시간 감쇠 검증 (v5와 동일 — 회귀 없음 확인)
python3 -c "
import sys; sys.path.insert(0, 'src')
from hit_predictor.rsi.calculator import time_decay_weight
for y in [0,1,3,5,10,15]:
    print(f'{y}년: {time_decay_weight(y):.3f}')
"
# 기대: 1.000 / 0.905 / 0.741 / 0.607 / 0.368 / 0.223

# 4) 이번 세션 추가 filmography 12개 확인
ls data/filmography/directors/이수현.json data/filmography/directors/박준우.json data/filmography/directors/김성훈.json
ls data/filmography/writers/여은호.json data/filmography/writers/이지현.json data/filmography/writers/황조윤.json
ls data/filmography/actors/박보영.json data/filmography/actors/김성철.json data/filmography/actors/이현욱.json
ls data/filmography/actors/김희원.json data/filmography/actors/문정희.json data/filmography/actors/이광수.json

# 5) v3 재계산 결과 확인 (허수아비 56.8, 은밀한 감사 50.7, 골드랜드 52.6)
python3 -c "
import json
with open('output/recalculated_results_v3.json') as f:
    data = json.load(f)
for r in data['results']:
    if r['title'] in ['허수아비','은밀한 감사','골드랜드','기리고']:
        print(f\"{r['title']:10} combined={r['combined']:.1f} {r['verdict']}\")
"
# 기대:
# 허수아비    combined=56.8 ⚡ 승부처
# 골드랜드    combined=52.6 ❓ 다크호스
# 은밀한 감사 combined=50.7 ❓ 다크호스
# 기리고      combined=44.9 📉 난항 예상

# 6) 5월 신작 발견 (작업 시작 시)
python3 scripts/discover_new_dramas.py --year 2026 --month 5
python3 scripts/build_candidate_dramas.py --year 2026 --month 5 --dry-run
```

---

## 7. 다음 Claude Code 세션 첫 메시지 템플릿

```
안녕! 핸드오프 문서(HANDOFF_v6.md)와 함께 작업을 이어받았어.
HANDOFF_v5.md도 기초 정보용으로 함께 참고해줘.

오늘 작업 흐름:
1. 먼저 §6의 검증 명령을 실행해서 v6 상태가 일치하는지 확인해줘.
2. Perplexity로 받은 피드백을 붙여넣을게. 이걸 §2-C 절차대로 분류해줘.
3. 그 다음 §3 우선순위 보드에서 어떤 작업부터 진행할지 함께 결정하자.
4. 최종 목표: 5월 드라마 H-Score 조사 (기존 4편 사후 검증 + 5월 신작 추가)
5. 위 작업이 끝나면 ChatGPT Codex 이양용 §5 섹션을 채워서 핸드오프 마무리.

작업 방식:
- Python 초보 — 코드 변경 시 한국어로, 변경 이유부터 설명
- 결측치 정책: 원인 모르는 결측은 그대로, 원인 아는 결측만 fallback
- candidate_dramas.csv는 수동 편집 금지(수집 로직 수정으로 갱신)
- TMDB_READ_TOKEN은 내가 export — 본문에 출력 X

[Perplexity 피드백 시작]
...붙여넣기...
[Perplexity 피드백 끝]
```

---

## 8. 부록 — v5 이후 변경 파일 절대경로

```
신규 파일 (v6):
- HANDOFF_v6.md (이 문서)
- docs/[AI학습용] 26년 4-5월 드라마 H-Score 분석_은밀한감사·허수아비·골드랜드·기리고.md
- data/filmography/directors/{이수현,박준우,김성훈}.json
- data/filmography/writers/{여은호,이지현,황조윤}.json
- data/filmography/actors/{박보영,김성철,이현욱,김희원,문정희,이광수}.json

수정 파일 (v6):
- output/recalculated_results_v3.json   (12 filmography 추가 후 재산출)
- output/recalculated_results_v3.csv    (동일)

미변경 (v5와 동일):
- src/hit_predictor/**  (코드 변경 없음 — 이번 세션은 데이터 보강만)
- scripts/**            (코드 변경 없음)
- data/candidate_dramas.csv  (변경 없음)
- HANDOFF_v5.md         (아카이브로 유지)
```

---

## 9. 작업방 요약

### v6 (3단계, 2026-05-01~02)

> v5의 §6-3에서 잡혔던 "creator/cast RSI=0 다발" 문제를 **TMDB 토큰 없이 web research로 12개 filmography 수동 생성**해 완화했다. 결과적으로 허수아비가 50.4 → **56.8 ⚡ 승부처**로 점프하고, 골드랜드(54.4→52.6)·은밀한 감사(49.0→50.7)는 더 정직한 점수로 재정렬됐다.
>
> 부가로 4편 H-Score 분석을 망라한 **AI학습용 컨텍스트 파일**(543줄)을 신설해 향후 티스토리 블로그 작성 효율을 끌어올렸다.
>
> **다음 세션 1순위 후보**: 5월 신작 발견·분석 + 기존 4편 사후 검증. 코드 최신화 우선순위는 Perplexity 피드백을 반영해 다음 세션에서 확정.

### v3.1 → v6 누적 KPI (참고)

| 항목 | v3.1 (4/29) | v6 (5/02) | 비고 |
|------|-------------|-----------|------|
| candidate_dramas.csv 편수 | 9 | 9 | 5월 신작 추가 예정 |
| filmography actors | 21명 | **27명** | +6 (골드랜드 캐스트) |
| filmography directors | 2명 | **5명** | +3 |
| filmography writers | 1명 | **4명** | +3 |
| _archived_v1 orphan | 22개 | 22개 | 변동 없음 |
| H-Score ⚡ 승부처 작품수 | 0 | **1** | 허수아비 진입 |
| recalculated_results_v3 산출일 | 2026-04-29 | 2026-05-02 | 12명 보강 반영 |

---

**미루님, 다음 세션에서 §6의 검증 명령부터 시작하시고, Perplexity 피드백을 §2-C 절차로 흘려보내세요. 좋은 작업 되세요! 🚀**
