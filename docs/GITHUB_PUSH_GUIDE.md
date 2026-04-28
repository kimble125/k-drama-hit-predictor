# 🚀 GitHub 푸시 가이드 (로컬 실행)

Claude 샌드박스 환경은 GitHub 인증이 불가하므로, 미루님이 로컬에서 직접 푸시하셔야 합니다. 이 가이드대로 따라하시면 5분 내 완료됩니다.

---

## ✅ 푸시 전 점검 (체크리스트)

```
[ ] 위키백과·나무위키 메타 수집 완료 (data/wikipedia_meta.json 존재)
[ ] 재계산 결과 정상 (output/recalculated_results_v2.json 존재, RSI 정상값)
[ ] 캐스팅·제작진 정보 정정 (data/candidate_dramas.csv)
[ ] 신인 fallback 동작 확인 (유지원, 박윤서 등 RSI 부여됨)
[ ] .gitignore 가 닐슨 CSV 차단 ✓ (이미 설정됨)
[ ] LICENSE, README.md 최신본 ✓ (이미 작성됨)
```

---

## 📦 Step 1: 압축 해제 & 디렉토리 진입

```bash
unzip k-drama-hit-predictor-v2.zip
cd k-drama-hit-predictor
```

---

## 🔍 Step 2: 닐슨 CSV가 빠졌는지 확인

```bash
git check-ignore -v data/nielsen_weekly/*.csv
# 출력 예시: .gitignore:8:data/nielsen_weekly/*.csv ...
```

이런 출력이 나와야 합니다 (= `.gitignore`가 닐슨 CSV를 막고 있다는 뜻). 안 나오면 `.gitignore` 파일을 점검하세요.

---

## 🌱 Step 3: Git 초기화

이미 init돼 있는 경우면 Step 4로 점프하세요. 처음이면:

```bash
git init
git add .
git commit -m "Initial commit: K-Drama Hit-Predictor v2"
```

---

## 🔗 Step 4: GitHub 원격 레포 연결

GitHub.com에서 미리 빈 레포를 만들어두셨다고 가정합니다 (`https://github.com/kimble125/k-drama-hit-predictor`).

```bash
# 원격 추가 (한 번만)
git remote add origin https://github.com/kimble125/k-drama-hit-predictor.git

# 또는 SSH
git remote add origin git@github.com:kimble125/k-drama-hit-predictor.git
```

이미 추가돼 있으면:

```bash
git remote set-url origin https://github.com/kimble125/k-drama-hit-predictor.git
```

---

## 🚀 Step 5: 푸시

```bash
# 메인 브랜치 표준화
git branch -M main

# 푸시
git push -u origin main
```

GitHub 인증을 묻습니다:
- **Personal Access Token (PAT) 방식 권장**: GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token (`repo` 권한 체크)
- 비밀번호 자리에 PAT 붙여넣기

---

## 🛠️ 일상 워크플로우 (변경사항 푸시)

```bash
# 변경사항 추가
git add .
git status   # 닐슨 CSV가 빠져 있는지 확인

# 커밋
git commit -m "feat: Add newcomer fallback for writers/directors"

# 푸시
git push
```

---

## 📝 좋은 커밋 메시지 패턴

이번 변경사항에 적합한 예시:

```bash
# 한꺼번에
git commit -m "feat: K-Drama Hit-Predictor v2 with auto RSI

- RSI 자동 산출 (시간 감쇠 + OTT 환산 + 신인 fallback)
- Triple KPI 구조 (first_ep / avg / rsi_victory)
- 채널×시간대 3단 벤치마크 세분화
- TMDB·위키백과·나무위키·닐슨 4단 수집 파이프라인
- 6-method 앙상블 캘리브레이션 (Spearman + OLS + Ridge + RF + GB + NB)

논문 기반: 주상필(2019), 최현종(2017), 남기환(2018), Ahn(2017),
강명현(2019), 윤용아(2020), 전익진·은혜정(2014)"
```

---

## 🆘 자주 나오는 문제

### "Permission denied (publickey)"
SSH 인증 실패. HTTPS URL로 바꾸세요:
```bash
git remote set-url origin https://github.com/kimble125/k-drama-hit-predictor.git
```

### "fatal: refusing to merge unrelated histories"
GitHub에 README나 .gitignore를 미리 만든 경우. 이렇게:
```bash
git pull origin main --allow-unrelated-histories
git push -u origin main
```

### "닐슨 CSV가 푸시되어버렸다!"
🔴 즉시 조치:
```bash
git rm --cached data/nielsen_weekly/*.csv
git commit -m "fix: remove Nielsen CSV per ToS"
git push
```
GitHub에 흔적이 남으므로, 큰 일이면 `git filter-branch` 또는 `git-filter-repo`로 히스토리에서 완전 제거 필요.

---

## ✅ 푸시 후 확인

1. `https://github.com/kimble125/k-drama-hit-predictor` 접속
2. README가 잘 렌더링되는지 확인 (배지, 표, 코드블록)
3. `data/nielsen_weekly/` 폴더에 `.gitkeep`만 있고 CSV는 없는지 확인
4. Sources 라벨 잘 보이는지 (`Python` 표시)

이제 IT 블로그에 GitHub 링크 걸어도 됩니다. 🎉

---

## 📞 문제가 계속 나면

다음 정보로 알려주세요:
- 어느 Step에서 막혔는지
- 정확한 오류 메시지
- 운영체제 (macOS / Windows / Linux)

다음 대화에서 해결책 찾아드리겠습니다.
