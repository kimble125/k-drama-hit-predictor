# 📊 K-Drama Hit Decoder (H-Score)

> K-드라마 흥행 예측 프레임워크 — 데이터 기반 6축 분석 시스템

## 프로젝트 개요
블로그 시리즈 [드라마 H-디코딩](https://forrest125.tistory.com/)의 
분석 엔진. 방영 전 공개 정보만으로 드라마의 흥행 가능성을 
H-Score(100점 만점)로 산출합니다.

## H-Score 6축 구조
| 축 | 측정 요소 | 가중치 |
|---|---|---|
| 캐스트 파워 | SNS 팔로워, 전작 시청률/화제성, 수상 이력 | TBD |
| 크리에이터 파워 | 감독·작가 전작 시청률/화제성 | TBD |
| IP/원작 파워 | 원작 조회수·별점, 시즌 이력 | TBD |
| 플랫폼 전략 | 플랫폼 규모, 글로벌 동시공개, 편성 경쟁 | TBD |
| 사전 화제성 | 펀덱스 순위, 검색반응, 티저 조회수 | TBD |
| 장르·시장 적합도 | 경쟁작, 장르 트렌드, FUNdex 추이 | TBD |

> 가중치는 2025-2026 종영작 데이터 기반 실증 분석으로 산정 예정

## 데이터 출처
- [펀덱스(FUNdex)](https://www.fundex.co.kr/) 주간 화제성
- 닐슨코리아 시청률 (나무위키 경유)
- 네이버 검색 트렌드

## 기술 스택
Python | pandas | scikit-learn | XGBoost | SHAP | matplotlib

## 관련 블로그
- 📝 콘텐츠 분석: [forrest125.tistory.com](https://forrest125.tistory.com/)
- 🔬 데이터 분석: [kimble125.tistory.com](https://kimble125.tistory.com/)

## 로드맵
- [ ] Phase 1: 종영작 데이터 수집 및 가중치 산정
- [ ] Phase 2: 2026 상반기 기대작 5편 H-Score 산출
- [ ] Phase 3: 방영 후 실제 성적과 비교 검증
- [ ] Phase 4: 웹툰/영화로 프레임워크 확장
