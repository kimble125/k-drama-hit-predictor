# 🔄 Hit-Predictor v4 — 새 대화방 핸드오프 문서

> **이 문서를 새 대화방의 첫 메시지에 첨부하세요.** v3 작업방에서 _자동 수집·평가 시스템의 골격_을 완성한 직후의 컨텍스트입니다.

---

## 📌 호칭 / 메모리

- 미루님으로 부르세요. (오빠 X, 이름 X)
- 메모리에 이미 저장됨: 호칭, 블로그 URL, GitHub, Python 초보, 한국어 응답
- TMDB Read Token: 메모리에 보존 (환경변수 `TMDB_READ_TOKEN` 으로 export 필요)

---

## ✅ v3 작업방에서 완성된 것

### Phase 1 — 입력 시드 자동 수집 (이슈 1·2·4 해결)

| 단계 | 산출물 | 검증 |
|---|---|---|
| 1-A | [`rsi/schemas.py`](src/hit_predictor/rsi/schemas.py) Credit에 `cast_role`/`role_weight` 추가 + [`data/schemas.py`](src/hit_predictor/data/schemas.py) `MissingReason` enum + Drama에 `data_quality`/`field_sources` dict | backward-compat 통과 |
| 1-D | [`data/collectors/_http.py`](src/hit_predictor/data/collectors/_http.py) — 공통 HTTP 헬퍼 (User-Agent + 소스별 rate limit + robots.txt + 429/Retry-After + attribution) | 위키백과·나무위키·닐슨 GET 검증 |
| 1-B | [`scripts/discover_new_dramas.py`](scripts/discover_new_dramas.py) — 위키백과 API + 나무위키 + TMDB 신작 발견 | **4월 신작 9/9편 자동 발견** |
| 1-C | [`scripts/build_candidate_dramas.py`](scripts/build_candidate_dramas.py) — 다중 소스 투표 + role_weight 자동 분류 | **HANDOFF 핵심 오류 3건 자동 정정** (모두가… / 골드랜드 / 유미3) |

### Phase 2-A — 닐슨 자동 수집

- [`collectors/nielsen.py`](src/hit_predictor/data/collectors/nielsen.py)에 `AREA_CODE_TO_LABEL` 매핑 추가 (`00`=전국, `01`=수도권 — 사이트 JS 분석으로 확정)
- [`scripts/fetch_nielsen_weekly.py`](scripts/fetch_nielsen_weekly.py) — wrapper 신설 (월별·지역별 일괄)
- 검증: 4월 전국 80행 + 수도권 80행 자동 수집 (지상파·종편·케이블)

### Phase 4 — RSI에 역할 가중 반영 (이슈 2 해결)

- [`rsi/calculator.py`](src/hit_predictor/rsi/calculator.py)의 `calculate_rsi()`가 `role_weight`를 win 분자·분모 모두에 곱함
- 검증: **구교환(우영우 특별출연 11.9% + 좀비탐정 주연 3.0%) RSI 0.5 → 0.167** (특별출연 가중치 0.2로 희석)
- backward-compat: `role_weight` 미설정 시 default=1.0이 곱해져 _기존 값과 동일_

---

## ⚠️ 알려진 한계 — 다음 작업방에서 처리할 것

### 정확도 detail (Phase 1-C 후속 정제)

| 케이스 | 현상 | 원인 추정 | 해결 방향 |
|---|---|---|---|
| **허수아비** | 감독·작가·캐스트 모두 None | 나무위키 페이지 인포박스 셀렉터 미스매치 | 페이지 구조 봐서 셀렉터 보강 |
| **기리고** | 감독 None, 작가만 잡힘 | 인포박스 행 라벨이 다른 변형 사용 | 라벨 사전 확장 |
| **로맨스의 절댓값** | 감독·작가 None | 마이너 신작 — 인포박스가 _부분만_ 채워짐 | wikipedia 보완 + 방송사 공식 fallback |
| **골드랜드** | 출연진이 `["박보영 김성철"]` 한 묶음 | HTML strong 태그 안에 두 이름이 공백으로 결합됨 | strong 텍스트를 추가 split (한국 이름 2-4글자 패턴) |
| **유미의 세포들 3** | 나무위키 매칭 실패 | URL `유미의 세포들 3` ≠ `유미의 세포들3` (공백) | 정규화 후 redirect 검색 추가 |

### 알고리즘 개선 백로그 (미루님이 v3에서 제기)

1. **영화 등 cross-media bonus** — KOFIC 박스오피스 + TMDB 영화 popularity. _RSI 본 계산은 건드리지 말고_ `cast_score_from_rsi()`에 보너스 항만 추가 권장 (현재 award_count_5y 보너스와 같은 패턴)
2. **베테랑 fallback** — 구교환 같은 _15년+ 경력 + 드라마 RSI 표본 < 3편_ 케이스 보정. 현재는 신인 fallback만 있음. Bayesian smoothing(장르 평균과의 가중 평균) 도입 권장
3. **win의 격차 가중** — 현재 0.3%p 차로 이기든 10%p 차로 이기든 win=1.0. 격차에 비례한 partial win 도입 검토 (단, RSI vs RSGI 역할 분담 다시 정의 필요)
4. **벤치마크 — 단일 평균 → 분포** — 동시간대 _실제 경쟁작 분포_(Top3 평균 등)로 대체 시 강한 슬롯에서의 win이 더 어려워짐 (현실 반영)

---

## 🚀 다음 작업방 권장 우선순위

```
A. (우선) Phase 1-C 정제 — 허수아비/기리고/strong 분리/유미3 redirect — 1~2시간
B. (우선) Phase 3 — 6축 점수 자동 산정 (auto_score.py 신규) — 2~3시간
C. Phase 2-B — 펀덱스 PDF 자동 다운로드·아카이빙·파싱 — 2시간 (하단 청사진 참조)
D. 알고리즘 개선 — 영화 cross-media bonus + 베테랑 fallback — 1~2시간
E. 통합 재계산 → recalculated_results_v3.json + 블로그 글 #2 — 1시간
```

**미루님 결정 사항**: 위 5개 중 어디까지 다음 작업방에서 갈지

---

## 📦 펀덱스 자동화 청사진 (Phase 2-B 진입용)

### 입수 경로 (미루님 확인)

- 메인 페이지: https://www.fundex.co.kr/fxmain.do
- _공개 S3 버킷_: `racoi.s3.ap-northeast-2.amazonaws.com`
- URL 패턴: `https://racoi.s3.ap-northeast-2.amazonaws.com/[굿데이터]+펀덱스리포트_{M}월+{W}주차.pdf`
- _현재 주차_는 메인 페이지에 직접 anchor로 노출 (`FUNdex Report #N` 텍스트)
- 주차 번호 시스템: 2026-04-3주차 = #583 등 누적 회차 — 메인 페이지에서 추출 가능

### 자동화 설계 (구현 가이드)

```
scripts/fetch_pundex_archive.py:
  1. fxmain.do GET → 'FUNdex Report' anchor의 href 추출 → 최신 PDF URL
  2. 해당 PDF를 data/pundex_archive/{YYYY}/{YYYY-MM-DD}.pdf 로 저장
  3. (옵션) 과거 N주 이전까지 URL 패턴으로 추정·시도 → 404 시 skip
  4. .gitignore: data/pundex_archive/*.pdf  (저작권 — 재배포 금지)

scripts/parse_pundex_weekly.py:
  - PDF → pdfplumber 또는 PyPDF2로 텍스트 추출
  - 펀덱스 표준 섹션: 드라마 화제성 Top10 / 배우 화제성 Top20 / 감독·작가 Top10
  - 추출 결과 → data/pundex_weekly/{YYYY-MM-DD}.json
```

### 의존성 추가 필요

```
pdfplumber>=0.10  # 또는 PyPDF2
```

---

## ⚠️ 작업 환경 노트 (다음 작업방에서 주의)

- claude code worktree(`.claude/worktrees/mystifying-sutherland-5aaec0`)는 **빈 상태**
- 실제 코드는 부모 디렉터리(`/Users/kimble/Library/.../k-drama-hit-predictor 3/`)에 있음
- 부모 디렉터리는 `/Users/kimble`을 main worktree로 갖는 git의 _서브디렉터리_라 `git status`에서 사용자 홈 시스템 파일들이 노출됨 (`Library/Daemon Containers/` 등)
- **작업 시 `git add` 명시적 파일만**, **절대 `git add .` / `git commit -a` 금지**
- `.gitignore`: `data/nielsen_weekly/*.csv` 재배포 금지로 ignore되어 있음 — 닐슨 코드는 공개, 데이터는 로컬만

---

## 🚫 다음 작업방에서 하지 말 것

- 6축 H-Score 구조 재설계 (논문 기반 확정)
- Triple KPI 가중치 변경
- 시간 감쇠 공식 변경
- README 재작성 (현재 버전 유지)
- v3에서 만든 schemas/calculator/_http/build_candidate/discover_new/fetch_nielsen 6개 파일 _구조 변경_ — 보강·확장만

---

## 🛠 즉시 실행 가능한 명령 (다음 작업방 첫 검증용)

```bash
cd "/Users/kimble/Library/CloudStorage/GoogleDrive-hoykim125@gmail.com/내 드라이브/Git/k-drama-hit-predictor/k-drama-hit-predictor 3"

# v3에서 만든 자동화 파이프라인 실행
python3 scripts/discover_new_dramas.py --year 2026 --month 4
python3 scripts/build_candidate_dramas.py --year 2026 --month 4 --dry-run
python3 scripts/fetch_nielsen_weekly.py --year-month 202604 --area both

# 정제 대상 드라마만 빌드 (디버깅용)
python3 scripts/build_candidate_dramas.py --year 2026 \
    --titles "허수아비,기리고" --dry-run
```

---

## 💬 새 작업방 첫 메시지 예시

```
미루님 입력 예시:

"안녕, 이 핸드오프 문서(HANDOFF_v4.md)를 먼저 읽어주세요.
v3에서 자동 수집·평가 골격이 완성됐고, 이번 작업방에서는
[A. Phase 1-C 정제 / B. Phase 3 6축 점수 / C. 펀덱스]
중 [선택] 부터 진행하고 싶어요.

추가 자료:
- candidate_dramas_quality.json (이번 v3 산출물 — 결측 사유 trace)
- data/discovered/2026-04.json (자동 발견 결과)"
```

---

## 📝 메모리에 추가/수정될 사항 (참고)

- 자동 수집 시스템 v3: 위키백과 API + 나무위키(check_robots=False) + TMDB
- 닐슨 area: 00=전국, 01=수도권 (사이트 JS 분석 확정)
- role_weight 정책: lead 1.0 / supporting 0.5 / special 0.2 / cameo 0.1
- 펀덱스 자동화: racoi.s3.ap-northeast-2.amazonaws.com 공개 버킷
