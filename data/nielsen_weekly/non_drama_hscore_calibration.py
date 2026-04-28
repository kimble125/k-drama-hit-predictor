#!/usr/bin/env python3
"""
Non-Drama H-Score 가중치 산정 스크립트 (Weight Calibration) v1.0
==================================================================
2024-2026 K-예능/쇼 프로그램 데이터를 기반으로
Non-Drama H-Score 6축의 최적 가중치를 실증적으로 산정합니다.

드라마 H-Score와의 핵심 차이:
  - 6축 재설계: 캐스트 케미 / PD파워 / 포맷파워 / 플랫폼편성 / 사전화제성 / 콘셉트트렌드
  - Dual KPI: 초기안착력(Landing) + 롱런지속력(Longevity)
  - 종속변수: 닐슨 시청률(%) + 브랜드평판지수 (이중 검증)

포맷 분류 (방송통신위원회 2012 공식분류 기반):
  - 관찰리얼리티 (관찰예능 포함)
  - 버라이어티 (리얼버라이어티, 게임/미션 등)
  - 서바이벌/경연 (오디션, 서바이벌)
  - 토크쇼
  - 음악쇼 (음악 경연, 음악 버라이어티)
  - 여행/요리/라이프 (먹방, 여행, 일상)
  - 스포츠예능

데이터 출처:
  - 닐슨코리아 주간 시청률 (첨부 CSV)
  - 한국기업평판연구소 예능 브랜드평판지수 (공개 기사 기반)
  - 나무위키, 각 방송사 공식 사이트 (시청률, 출연진 정보)
  - [EST] 표시: 추정치 (향후 검증 필요)

GitHub: https://github.com/kimble125/k-drama-hit-predictor
Blog:   https://forrest125.tistory.com/
"""

import os
import json
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import LeaveOneOut, cross_val_score
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

# ================================================================
# 한글 폰트 설정
# ================================================================
def setup_korean_font():
    import platform
    system = platform.system()
    if system == 'Darwin':
        font_path = '/System/Library/Fonts/AppleSDGothicNeo.ttc'
        if os.path.exists(font_path):
            fm.fontManager.addfont(font_path)
            plt.rcParams['font.family'] = 'Apple SD Gothic Neo'
        else:
            plt.rcParams['font.family'] = 'AppleGothic'
    elif system == 'Windows':
        plt.rcParams['font.family'] = 'Malgun Gothic'
    else:
        # Linux — try NanumGothic, fallback to DejaVu
        try:
            plt.rcParams['font.family'] = 'NanumGothic'
        except:
            plt.rcParams['font.family'] = 'DejaVu Sans'
    plt.rcParams['axes.unicode_minus'] = False

setup_korean_font()

OUTPUT_DIR = "output_nondrama"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ================================================================
# 1. Non-Drama 6축 점수 산출 기준 (Scoring Rubric)
# ================================================================
RUBRIC = """
┌──────────────────────────────────────────────────────────────────┐
│          Non-Drama H-Score 6축 점수 산출 기준 v1.0               │
├──────────┬───────────────────────────────────────────────────────┤
│ 점수 범위 │ 의미                                                 │
├──────────┼───────────────────────────────────────────────────────┤
│  9 ~ 10  │ 압도적 (국민MC / 레전드PD / 넷플릭스 글로벌)           │
│  7 ~ 8   │ 강함   (A급 예능인 / 검증된PD / 메이저 채널+OTT)      │
│  5 ~ 6   │ 보통   (중견급 / 안정적 포맷 / 일반 편성)              │
│  3 ~ 4   │ 약함   (신인급 / 미검증 포맷 / 비주류)                 │
│  1 ~ 2   │ 매우 약함 (무명 / 마이너 채널 / 트렌드 역행)           │
├──────────┴───────────────────────────────────────────────────────┤
│                                                                  │
│ ① 출연진 케미 파워 (Cast Chemistry Power)                        │
│   = 개별 인지도(SNS·인기도) + 예능 검증도(전작 성과)              │
│   + 멤버 조합 케미 기대치 + 다성성(독립적 캐릭터 충돌)            │
│   ※ 드라마와 달리 '조합의 화학작용'이 핵심                       │
│                                                                  │
│ ② PD/크리에이터 파워 (Creator Power)                              │
│   = PD 전작 최고 시청률/화제성 + 포맷 개발 이력 + 수상            │
│   ※ 나영석·김태호·신원호 등 스타PD 체계 반영                     │
│                                                                  │
│ ③ 포맷 파워 (Format Power)                                       │
│   = 포맷 유형(관찰/서바이벌/버라이어티 등) + 시즌 이력             │
│   + OSMU 가능성 + 포맷 신선도                                     │
│   ※ 드라마의 'IP/원작 파워' 대응. 예능에서는 포맷=IP               │
│                                                                  │
│ ④ 플랫폼·편성 전략 (Platform & Scheduling)                       │
│   = 채널 도달력 + OTT 동시공개 + 편성 요일·시간대 경쟁            │
│   + 글로벌 유통 여부                                              │
│                                                                  │
│ ⑤ 사전 화제성 (Pre-Buzz)                                         │
│   = 출연진 발표 반응 + 티저 조회수 + SNS 반응 + 기사량             │
│   ※ 예능은 '초반 3~4회 안착'이 핵심 (드라마보다 느린 안착)        │
│                                                                  │
│ ⑥ 콘셉트·트렌드 적합도 (Concept-Trend Fit)                       │
│   = 사회 트렌드 공명 + 새로움·낯익음 균형 + 동시기 경쟁 강도      │
│   ※ 드라마의 '장르 트렌드' 대응. 예능은 사회 트렌드와의 공명      │
│                                                                  │
│ 포맷 분류 (방송통신위 2012 공식분류 기반, 현행 확장):              │
│   OBS  관찰리얼리티  │  VAR  버라이어티  │  SRV  서바이벌/경연     │
│   TLK  토크쇼        │  MUS  음악쇼      │  TRL  여행/요리/라이프  │
│   SPT  스포츠예능    │                                            │
└──────────────────────────────────────────────────────────────────┘
"""


# ================================================================
# 2. 캘리브레이션 데이터: 2024~2026 예능 28편
# ================================================================
# 종속변수: avg_rating_pct (닐슨코리아 가구 시청률 %, 유료플랫폼 기준)
#           brand_reputation (한국기업평판연구소 브랜드평판지수, 만 단위)
# 독립변수: 6축 각 1~10점
#
# 포맷 유형 분류 (방송통신위 2012 공식분류 + 현행 확장):
#   OBS = 관찰 리얼리티 (나혼자산다, 미운우리새끼, 전지적참견시점 등)
#   VAR = 버라이어티 (무한도전, 런닝맨, 놀면뭐하니 등 게임/미션 기반)
#   SRV = 서바이벌/경연 (흑백요리사, 피지컬100, 미스트롯 등)
#   TLK = 토크쇼 (유퀴즈, 아는형님, 라디오스타 등)
#   MUS = 음악쇼 (불후의명곡, 복면가왕, 히든싱어 등)
#   TRL = 여행/요리/라이프 (삼시세끼, 서진이네, 1박2일 등)
#   SPT = 스포츠예능 (최강야구, 골때리는그녀들 등)

calibration_shows = [
    # ─── 흥행 대성공 (상위 tier) ───
    {
        "title": "흑백요리사: 요리 계급 전쟁",
        "platform": "Netflix", "year": 2024, "format_type": "SRV",
        "genre_desc": "요리서바이벌,경연",
        "avg_rating_pct": None,       # Netflix (시청률 미공개)
        "brand_reputation": 7700000,   # [EST] 2024.10 브랜드평판 1위급
        "netflix_global_rank": 1,      # 비영어TV 3주연속 1위
        "cast_chemistry": 8,          # 백종원·안성재 + 80인 셰프진, 계급 서사
        "creator_power": 8,           # 이욱정PD (피지컬100 성공)
        "format_power": 9,            # 서바이벌 포맷 진화 + 시즌2 확정
        "platform_scheduling": 10,    # Netflix 글로벌 동시공개
        "pre_buzz": 7,                # 피지컬100 후속 기대감
        "concept_trend_fit": 10,      # 요리+계급서사 = 2024 최강 트렌드
    },
    {
        "title": "나 혼자 산다",
        "platform": "MBC", "year": 2024, "format_type": "OBS",
        "genre_desc": "관찰리얼리티,싱글라이프",
        "avg_rating_pct": 4.5,        # [SRC:닐슨]
        "brand_reputation": 6500000,   # 2024 연간 브랜드평판 상위
        "cast_chemistry": 8,          # 박나래·기안84·전현무 등 검증 조합
        "creator_power": 7,           # 장수 PD팀, 안정적 연출
        "format_power": 9,            # 11년차 장수 + 시즌제 안착
        "platform_scheduling": 6,     # MBC 금요 20:55
        "pre_buzz": 6,                # 장수 프로그램이라 안정적이나 폭발X
        "concept_trend_fit": 8,       # 1인가구 트렌드 정조준, 여전히 유효
    },
    {
        "title": "미운 우리 새끼 (다시 쓰는 육아일기)",
        "platform": "SBS", "year": 2025, "format_type": "OBS",
        "genre_desc": "관찰리얼리티,가족",
        "avg_rating_pct": 11.3,       # [SRC:닐슨] SBS 일요 21:00 고시청률
        "brand_reputation": 5800000,   # 2025 상위권
        "cast_chemistry": 7,
        "creator_power": 6,
        "format_power": 8,            # 리뉴얼 성공 + 9년차 장수
        "platform_scheduling": 7,     # SBS 일요 황금시간 + 웨이브
        "pre_buzz": 5,
        "concept_trend_fit": 7,       # 가족·육아 관심 지속
    },
    {
        "title": "최강야구 시즌3",
        "platform": "JTBC", "year": 2024, "format_type": "SPT",
        "genre_desc": "스포츠예능,야구,서바이벌",
        "avg_rating_pct": 3.02,       # [SRC:나무위키] JTBC 월요
        "brand_reputation": 5200000,   # 2024.10 브랜드평판 상위
        "cast_chemistry": 9,          # 이승엽·김성근·이대호 레전드+신인 케미
        "creator_power": 7,           # 장시원PD
        "format_power": 9,            # 시즌3 + 독립리그 연계 + 직관데이
        "platform_scheduling": 6,     # JTBC 월요 + 티빙/넷플릭스
        "pre_buzz": 8,                # 시즌2 성공으로 사전 기대 폭발
        "concept_trend_fit": 9,       # 프로야구 부활 트렌드 + MZ 유입
    },
    {
        "title": "런닝맨",
        "platform": "SBS", "year": 2024, "format_type": "VAR",
        "genre_desc": "리얼버라이어티,게임,미션",
        "avg_rating_pct": 3.63,       # [SRC:나무위키]
        "brand_reputation": 5000000,   # 2024 상위 안정
        "cast_chemistry": 8,          # 유재석·지석진 등 14년차 고정 케미
        "creator_power": 6,
        "format_power": 9,            # 14년차 글로벌 장수 + 해외판 다수
        "platform_scheduling": 7,     # SBS 일요 + 웨이브 + 해외 동시
        "pre_buzz": 5,
        "concept_trend_fit": 5,       # 포맷 피로감 일부, but 글로벌 수요
    },
    # ─── 중상위 tier ───
    {
        "title": "삼시세끼 (어촌편/산촌편)",
        "platform": "tvN", "year": 2024, "format_type": "TRL",
        "genre_desc": "여행,요리,라이프,힐링",
        "avg_rating_pct": 8.86,       # [SRC:나무위키] tvN 어촌편
        "brand_reputation": 7710000,   # [SRC] 2024.10 브랜드평판 1위
        "cast_chemistry": 8,          # 차승원·유해진 + 게스트 조합
        "creator_power": 9,           # 나영석PD
        "format_power": 9,            # 10년차 시즌 누적 + OSMU 강력
        "platform_scheduling": 7,     # tvN + 티빙
        "pre_buzz": 7,
        "concept_trend_fit": 8,       # 힐링·요리 트렌드 지속
    },
    {
        "title": "유 퀴즈 온 더 블럭",
        "platform": "tvN", "year": 2024, "format_type": "TLK",
        "genre_desc": "토크쇼,인터뷰,길거리",
        "avg_rating_pct": 3.65,       # [SRC:닐슨]
        "brand_reputation": 4200000,   # 안정 상위
        "cast_chemistry": 7,
        "creator_power": 7,
        "format_power": 7,            # 길거리 인터뷰 독점 포맷 + 6년차
        "platform_scheduling": 7,     # tvN 수요 + 티빙
        "pre_buzz": 5,
        "concept_trend_fit": 6,
    },
    {
        "title": "1박 2일 시즌4",
        "platform": "KBS2", "year": 2024, "format_type": "TRL",
        "genre_desc": "여행,버라이어티,리얼",
        "avg_rating_pct": 5.9,        # [SRC:닐슨]
        "brand_reputation": 3800000,   # 중상위
        "cast_chemistry": 7,
        "creator_power": 6,
        "format_power": 8,            # 시즌4 + 17년차 장수 포맷
        "platform_scheduling": 6,     # KBS2 일요 + 웨이브
        "pre_buzz": 5,
        "concept_trend_fit": 6,
    },
    {
        "title": "피지컬: 100 시즌2 (언더그라운드)",
        "platform": "Netflix", "year": 2024, "format_type": "SRV",
        "genre_desc": "서바이벌,체력경쟁",
        "avg_rating_pct": None,       # Netflix
        "brand_reputation": 4500000,   # [EST]
        "cast_chemistry": 6,          # 일반인 100인 (개별 스타X, 집단 서사)
        "creator_power": 8,           # 장호기PD (시즌1 글로벌 히트)
        "format_power": 8,            # 시즌2 + 시즌1 글로벌 입증
        "platform_scheduling": 10,    # Netflix 글로벌
        "pre_buzz": 8,
        "concept_trend_fit": 7,       # 체력 서바이벌 = 피로감 일부
    },
    {
        "title": "놀면 뭐하니",
        "platform": "MBC", "year": 2024, "format_type": "VAR",
        "genre_desc": "버라이어티,프로젝트형",
        "avg_rating_pct": 3.83,       # [SRC:나무위키]
        "brand_reputation": 3500000,   # 하락세
        "cast_chemistry": 7,          # 유재석 MC + 매회 게스트
        "creator_power": 8,           # 김태호PD → 후임 전환기
        "format_power": 7,            # 프로젝트형 유연성 but 정체기
        "platform_scheduling": 6,     # MBC 토요
        "pre_buzz": 5,
        "concept_trend_fit": 5,       # 포맷 피로감
    },
    {
        "title": "불후의 명곡",
        "platform": "KBS2", "year": 2024, "format_type": "MUS",
        "genre_desc": "음악쇼,경연,리메이크",
        "avg_rating_pct": 4.7,        # [SRC:닐슨]
        "brand_reputation": 3200000,   # 안정
        "cast_chemistry": 6,
        "creator_power": 5,
        "format_power": 7,            # 12년차 장수 + 레전드 곡 리메이크
        "platform_scheduling": 6,     # KBS2 토요
        "pre_buzz": 4,
        "concept_trend_fit": 5,
    },
    {
        "title": "전국노래자랑",
        "platform": "KBS1", "year": 2024, "format_type": "MUS",
        "genre_desc": "음악쇼,참여형,시민",
        "avg_rating_pct": 5.6,        # [SRC:닐슨]
        "brand_reputation": 3500000,   # 안정
        "cast_chemistry": 5,
        "creator_power": 4,
        "format_power": 8,            # 40년+ 레전드 포맷
        "platform_scheduling": 5,     # KBS1 일요
        "pre_buzz": 3,
        "concept_trend_fit": 5,
    },
    # ─── 중위 tier ───
    {
        "title": "미스트롯4",
        "platform": "TV조선", "year": 2025, "format_type": "SRV",
        "genre_desc": "음악서바이벌,트로트,경연",
        "avg_rating_pct": 5.9,        # [SRC:닐슨] TV조선 목요
        "brand_reputation": 6890741,   # [SRC:brikorea] 2025.01 1위
        "cast_chemistry": 6,
        "creator_power": 6,
        "format_power": 7,            # 시즌4 (미스/미스터트롯 통합 6시즌)
        "platform_scheduling": 5,     # TV조선 (종편)
        "pre_buzz": 6,
        "concept_trend_fit": 5,       # 트롯 열풍 감소세 but 충성 팬덤
    },
    {
        "title": "히든싱어8",
        "platform": "JTBC", "year": 2026, "format_type": "MUS",
        "genre_desc": "음악쇼,숨은실력자,서바이벌",
        "avg_rating_pct": 4.55,       # [SRC:닐슨]
        "brand_reputation": 1144915,   # [SRC:brikorea] 2026.04 30위
        "cast_chemistry": 6,
        "creator_power": 6,
        "format_power": 7,            # 시즌8 장수 + 독창적 포맷
        "platform_scheduling": 6,     # JTBC + 티빙
        "pre_buzz": 5,
        "concept_trend_fit": 5,
    },
    {
        "title": "살림하는 남자들 시즌2",
        "platform": "KBS2", "year": 2024, "format_type": "OBS",
        "genre_desc": "관찰리얼리티,가족,육아",
        "avg_rating_pct": 5.2,        # [SRC:닐슨]
        "brand_reputation": 2800000,   # 중하위
        "cast_chemistry": 5,
        "creator_power": 5,
        "format_power": 6,
        "platform_scheduling": 5,     # KBS2 토요
        "pre_buzz": 3,
        "concept_trend_fit": 5,
    },
    {
        "title": "SNL코리아 시즌5",
        "platform": "쿠팡플레이", "year": 2024, "format_type": "VAR",
        "genre_desc": "코미디,패러디,버라이어티",
        "avg_rating_pct": None,       # 쿠팡플레이 (시청률 미공개)
        "brand_reputation": 4200000,   # [EST] 화제성 상위
        "cast_chemistry": 8,
        "creator_power": 7,
        "format_power": 8,            # 글로벌 포맷 + 코미디 부활 상징
        "platform_scheduling": 7,     # 쿠팡플레이 독점 (OTT 2위)
        "pre_buzz": 7,
        "concept_trend_fit": 8,       # 풍자 코미디 부활 + 사회 트렌드
    },
    {
        "title": "환승연애3",
        "platform": "TVING", "year": 2024, "format_type": "OBS",
        "genre_desc": "연애리얼리티,관찰",
        "avg_rating_pct": None,       # TVING (시청률 미공개)
        "brand_reputation": 4000000,   # [EST]
        "cast_chemistry": 7,
        "creator_power": 7,
        "format_power": 7,            # 시즌3 + 연애 리얼리티 대표
        "platform_scheduling": 7,     # TVING 독점
        "pre_buzz": 7,
        "concept_trend_fit": 7,
    },
    {
        "title": "서진이네2",
        "platform": "tvN", "year": 2024, "format_type": "TRL",
        "genre_desc": "요리,여행,식당운영",
        "avg_rating_pct": 7.80,       # [SRC:나무위키]
        "brand_reputation": 3780395,   # [SRC:네이버블로그] 2위
        "cast_chemistry": 8,          # 이서진·박서준·최우식·정유미
        "creator_power": 9,           # 나영석PD
        "format_power": 8,            # 시즌2 + 윤식당 계보
        "platform_scheduling": 7,     # tvN + 티빙
        "pre_buzz": 7,
        "concept_trend_fit": 7,       # K-푸드 + 해외여행
    },
    {
        "title": "골 때리는 그녀들",
        "platform": "SBS", "year": 2024, "format_type": "SPT",
        "genre_desc": "스포츠예능,여자축구",
        "avg_rating_pct": 4.73,       # [SRC:나무위키]
        "brand_reputation": 1404089,   # [SRC:brikorea] 2025.08 25위
        "cast_chemistry": 7,
        "creator_power": 6,
        "format_power": 7,            # 여성스포츠예능 개척
        "platform_scheduling": 6,     # SBS
        "pre_buzz": 5,
        "concept_trend_fit": 7,       # 여성스포츠 관심 증가
    },
    # ─── 중하위 tier ───
    {
        "title": "놀라운 토요일 (예능신대륙 개척)",
        "platform": "tvN", "year": 2025, "format_type": "VAR",
        "genre_desc": "버라이어티,음악,퀴즈",
        "avg_rating_pct": 2.19,       # [SRC:나무위키]
        "brand_reputation": 1874478,   # [SRC:brikorea] 2025.02 20위
        "cast_chemistry": 6,
        "creator_power": 5,
        "format_power": 6,            # 리뉴얼(예능신대륙) 시도
        "platform_scheduling": 6,     # tvN 토요
        "pre_buzz": 4,
        "concept_trend_fit": 5,
    },
    {
        "title": "나는 솔로",
        "platform": "ENA/SBS Plus", "year": 2024, "format_type": "OBS",
        "genre_desc": "연애리얼리티,결혼,관찰",
        "avg_rating_pct": 4.42,       # [SRC:나무위키] 2024 통합 평균
        "brand_reputation": 3200000,   # 화제성은 높으나 비주류 채널
        "cast_chemistry": 6,
        "creator_power": 5,
        "format_power": 7,            # 독점 포맷 + 밈 생산력 강
        "platform_scheduling": 4,     # ENA (마이너 채널)
        "pre_buzz": 5,
        "concept_trend_fit": 7,       # 결혼·연애 관심
    },
    {
        "title": "무명전설",
        "platform": "MBN", "year": 2026, "format_type": "MUS",
        "genre_desc": "음악쇼,숨은실력자,감동",
        "avg_rating_pct": 6.97,       # [SRC:닐슨] MBN 최고 시청률!
        "brand_reputation": 3429487,   # [SRC:brikorea] 2026.04 6위
        "cast_chemistry": 6,
        "creator_power": 5,
        "format_power": 6,            # 무명 발굴 포맷 (신규)
        "platform_scheduling": 4,     # MBN (종편)
        "pre_buzz": 4,
        "concept_trend_fit": 7,       # '숨은 실력자 발굴' = 공정성 밈
    },
    {
        "title": "세계밥장사도전기 백사장3",
        "platform": "tvN", "year": 2026, "format_type": "TRL",
        "genre_desc": "요리,해외,식당운영",
        "avg_rating_pct": 2.44,       # [SRC:나무위키]
        "brand_reputation": 3000000,   # [EST]
        "cast_chemistry": 7,
        "creator_power": 7,
        "format_power": 7,            # 시즌3 + 백종원 브랜드
        "platform_scheduling": 6,     # tvN
        "pre_buzz": 5,
        "concept_trend_fit": 6,       # K-푸드 해외진출 안정
    },
    {
        "title": "보검매직컬",
        "platform": "tvN", "year": 2026, "format_type": "VAR",
        "genre_desc": "버라이어티,마술,판타지",
        "avg_rating_pct": 3.2,        # [SRC:나무위키]
        "brand_reputation": 1493297,   # [SRC:brikorea] 2026.04 26위
        "cast_chemistry": 7,          # 박보검 (톱스타) + 게스트
        "creator_power": 6,
        "format_power": 5,            # 마술 포맷 = 신선 but 미검증
        "platform_scheduling": 6,     # tvN
        "pre_buzz": 7,                # 박보검 캐스팅 화제
        "concept_trend_fit": 5,       # 마술 포맷 니치
    },
    # ─── 하위 tier (참고 대조군) ───
    {
        "title": "예측불가 쑥이네 폐가 새로고침",
        "platform": "tvN", "year": 2026, "format_type": "OBS",
        "genre_desc": "관찰리얼리티,시골,리모델링",
        "avg_rating_pct": 2.26,       # [SRC:나무위키]
        "brand_reputation": 2104087,   # [SRC:brikorea] 2026.04 전체 14위
        "cast_chemistry": 5,
        "creator_power": 4,
        "format_power": 4,            # 시골 리모델링 = 니치
        "platform_scheduling": 6,     # tvN
        "pre_buzz": 3,
        "concept_trend_fit": 4,       # 시골 관심 but 포맷 미검증
    },
]

# ================================================================
# 3. 데이터 전처리
# ================================================================
def build_dataframe(shows):
    """예능 프로그램 리스트를 DataFrame으로 변환합니다."""
    df = pd.DataFrame(shows)

    # 6축 컬럼 정의
    axis_cols = [
        "cast_chemistry", "creator_power", "format_power",
        "platform_scheduling", "pre_buzz", "concept_trend_fit"
    ]

    # 6축 단순 평균 (가중치 적용 전)
    df["hscore_raw"] = df[axis_cols].mean(axis=1) * 10  # 100점 만점

    # 종속변수 정규화: 시청률이 없는 OTT 작품은 brand_reputation으로 대체
    # → 통합 지표 생성 (두 지표를 0~1 정규화 후 합산)
    from sklearn.preprocessing import MinMaxScaler

    # 시청률 있는 작품만으로 정규화 기준 설정
    has_rating = df['avg_rating_pct'].notna()

    if has_rating.sum() > 0:
        scaler_r = MinMaxScaler()
        df.loc[has_rating, 'rating_norm'] = scaler_r.fit_transform(
            df.loc[has_rating, 'avg_rating_pct'].values.reshape(-1, 1)
        ).flatten()

    scaler_b = MinMaxScaler()
    df['brand_norm'] = scaler_b.fit_transform(
        df['brand_reputation'].values.reshape(-1, 1)
    ).flatten()

    # 통합 성과 지표: 시청률 있으면 시청률 60% + 브랜드 40%, 없으면 브랜드 100%
    df['combined_performance'] = df.apply(
        lambda row: (row['rating_norm'] * 0.6 + row['brand_norm'] * 0.4)
        if pd.notna(row.get('rating_norm'))
        else row['brand_norm'],
        axis=1
    )

    return df, axis_cols


# ================================================================
# 4. 상관 분석
# ================================================================
def correlation_analysis(df, axis_cols, target="combined_performance"):
    """각 축과 타겟 변수 간의 상관계수를 계산합니다."""
    print("\n" + "=" * 60)
    print(f"📊 상관 분석 (타겟: {target})")
    print("=" * 60)

    correlations = {}
    for col in axis_cols:
        pearson = df[col].corr(df[target])
        spearman = df[col].corr(df[target], method='spearman')
        correlations[col] = {"pearson": pearson, "spearman": spearman}
        print(f"  {col:25s} | Pearson: {pearson:+.3f} | Spearman: {spearman:+.3f}")

    return correlations


# ================================================================
# 5. 회귀 분석 (다중 방법)
# ================================================================
def regression_analysis(df, axis_cols, target="combined_performance"):
    """여러 회귀 모델로 각 축의 기여도를 분석합니다."""
    print("\n" + "=" * 60)
    print(f"📈 회귀 분석 (타겟: {target})")
    print("=" * 60)

    X = df[axis_cols].values
    y = df[target].values

    scaler_X = StandardScaler()
    X_scaled = scaler_X.fit_transform(X)

    results = {}

    # --- 1) 선형 회귀 ---
    lr = LinearRegression()
    lr.fit(X_scaled, y)
    r2 = lr.score(X_scaled, y)

    loo = LeaveOneOut()
    loo_scores = cross_val_score(lr, X_scaled, y, cv=loo, scoring='r2')

    print(f"\n  [선형 회귀]")
    print(f"  R² (train): {r2:.3f}")
    print(f"  R² (LOO CV): {loo_scores.mean():.3f} ± {loo_scores.std():.3f}")
    lr_coefs = dict(zip(axis_cols, lr.coef_))
    for col in sorted(lr_coefs, key=lambda x: abs(lr_coefs[x]), reverse=True):
        print(f"    {col:25s} : {lr_coefs[col]:+.4f}")
    results["linear"] = lr_coefs

    # --- 2) Ridge 회귀 ---
    ridge = Ridge(alpha=1.0)
    ridge.fit(X_scaled, y)
    loo_ridge = cross_val_score(ridge, X_scaled, y, cv=loo, scoring='r2')
    print(f"\n  [Ridge 회귀 (α=1.0)]")
    print(f"  R² (LOO CV): {loo_ridge.mean():.3f} ± {loo_ridge.std():.3f}")
    ridge_coefs = dict(zip(axis_cols, ridge.coef_))
    results["ridge"] = ridge_coefs

    # --- 3) Random Forest ---
    rf = RandomForestRegressor(n_estimators=100, max_depth=3, random_state=42)
    rf.fit(X, y)
    loo_rf = cross_val_score(rf, X, y, cv=loo, scoring='r2')
    print(f"\n  [Random Forest]")
    print(f"  R² (LOO CV): {loo_rf.mean():.3f}")
    rf_imp = dict(zip(axis_cols, rf.feature_importances_))
    for col in sorted(rf_imp, key=lambda x: rf_imp[x], reverse=True):
        print(f"    {col:25s} : {rf_imp[col]:.3f}")
    results["random_forest"] = rf_imp

    # --- 4) Gradient Boosting ---
    gb = GradientBoostingRegressor(n_estimators=50, max_depth=2, random_state=42)
    gb.fit(X, y)
    print(f"\n  [Gradient Boosting]")
    gb_imp = dict(zip(axis_cols, gb.feature_importances_))
    for col in sorted(gb_imp, key=lambda x: gb_imp[x], reverse=True):
        print(f"    {col:25s} : {gb_imp[col]:.3f}")
    results["gradient_boost"] = gb_imp

    return results


# ================================================================
# 6. 가중치 통합 산출
# ================================================================
def derive_weights(correlations, regression_results, axis_cols):
    """여러 분석 결과를 종합하여 최종 가중치를 산출합니다."""
    print("\n" + "=" * 60)
    print("⚖️  Non-Drama 최종 가중치 산출")
    print("=" * 60)

    scores = {col: [] for col in axis_cols}

    # 상관계수 (절대값)
    corr_vals = {col: abs(correlations[col]["spearman"]) for col in axis_cols}
    corr_sum = sum(corr_vals.values())
    if corr_sum > 0:
        for col in axis_cols:
            scores[col].append(corr_vals[col] / corr_sum)

    # 회귀 계수 (절대값, 정규화)
    for method in ["linear", "ridge"]:
        vals = {col: abs(regression_results[method][col]) for col in axis_cols}
        total = sum(vals.values())
        if total > 0:
            for col in axis_cols:
                scores[col].append(vals[col] / total)

    # Feature Importance
    for method in ["random_forest", "gradient_boost"]:
        for col in axis_cols:
            scores[col].append(regression_results[method][col])

    # 종합 평균
    avg_scores = {col: np.mean(scores[col]) for col in axis_cols}
    total = sum(avg_scores.values())

    # 60점 총점으로 환산
    weights = {}
    for col in axis_cols:
        raw_weight = (avg_scores[col] / total) * 60
        weights[col] = round(raw_weight, 1)

    # 반올림 보정
    diff = 60 - sum(weights.values())
    max_col = max(weights, key=weights.get)
    weights[max_col] = round(weights[max_col] + diff, 1)

    print("\n  종합 가중치 (60점 만점 배분):")
    print("  " + "-" * 50)

    axis_names_kr = {
        "cast_chemistry": "① 출연진 케미 파워",
        "creator_power": "② PD/크리에이터 파워",
        "format_power": "③ 포맷 파워",
        "platform_scheduling": "④ 플랫폼·편성 전략",
        "pre_buzz": "⑤ 사전 화제성",
        "concept_trend_fit": "⑥ 콘셉트·트렌드 적합도",
    }

    for col in sorted(weights, key=lambda x: weights[x], reverse=True):
        bar = "█" * int(weights[col])
        print(f"  {axis_names_kr.get(col, col):24s} : {weights[col]:5.1f}점  {bar}")

    print(f"\n  총점: {sum(weights.values()):.1f}점")
    return weights


# ================================================================
# 7. Dual KPI H-Score 산출
# ================================================================
# 예능의 Dual KPI:
#   KPI-A: 초기 안착력 (Landing) = "첫 4회 안에 시청자가 정착하는가?"
#          → 사전 화제성 + 캐스트 케미 가 핵심
#   KPI-B: 롱런 지속력 (Longevity) = "시즌2 이상 갈 수 있는가?"
#          → PD 파워 + 포맷 확장성 + 트렌드 적합도 가 핵심

WEIGHTS_LANDING = {
    "cast_chemistry": 14.0,       # ★ 케미가 첫 안착의 핵심
    "creator_power": 6.0,
    "format_power": 5.0,
    "platform_scheduling": 8.0,
    "pre_buzz": 20.0,             # ★★ 초기 유입의 최대 동력
    "concept_trend_fit": 7.0,
}  # 합계: 60

WEIGHTS_LONGEVITY = {
    "cast_chemistry": 10.0,       # 케미 유지 → 롱런
    "creator_power": 14.0,        # ★★ PD의 스토리텔링 유지력
    "format_power": 14.0,         # ★★ 포맷 확장성 = 시즌2 가능성
    "platform_scheduling": 6.0,
    "pre_buzz": 4.0,              # 롱런에는 영향 미미
    "concept_trend_fit": 12.0,    # ★ 트렌드 지속성
}  # 합계: 60


def calculate_nondrama_hscore_dual(show, weights_landing, weights_longevity):
    """Non-Drama Dual KPI H-Score를 산출합니다.

    Returns:
        hscore_landing: 초기 안착력 점수 (100점)
        hscore_longevity: 롱런 지속력 점수 (100점)
        hscore_combined: 가중 평균 (안착 45% + 롱런 55%)
    """
    axis_cols = [
        "cast_chemistry", "creator_power", "format_power",
        "platform_scheduling", "pre_buzz", "concept_trend_fit"
    ]

    score_landing = 0
    score_long = 0

    for col in axis_cols:
        val = show[col]
        w_land = weights_landing[col] / 10
        w_long = weights_longevity[col] / 10
        score_landing += val * w_land
        score_long += val * w_long

    total_land = sum(weights_landing.values())
    total_long = sum(weights_longevity.values())

    hs_landing = round(score_landing / total_land * 100, 1)
    hs_longevity = round(score_long / total_long * 100, 1)
    # 예능은 롱런이 더 중요 (드라마 첫방40%+평균60% → 예능 안착45%+롱런55%)
    hs_combined = round(hs_landing * 0.45 + hs_longevity * 0.55, 1)

    return hs_landing, hs_longevity, hs_combined


# ================================================================
# 8. 시각화
# ================================================================
def plot_correlation_heatmap(df, axis_cols, target="combined_performance"):
    """6축 + 타겟 변수 간 상관 히트맵"""
    cols = axis_cols + [target]
    corr = df[cols].corr(method='spearman')

    labels_kr = {
        "cast_chemistry": "출연진 케미",
        "creator_power": "PD파워",
        "format_power": "포맷파워",
        "platform_scheduling": "플랫폼편성",
        "pre_buzz": "사전화제성",
        "concept_trend_fit": "콘셉트적합도",
        "combined_performance": "통합성과",
    }

    fig, ax = plt.subplots(figsize=(9, 7))
    display_labels = [labels_kr.get(c, c) for c in cols]
    sns.heatmap(
        corr, annot=True, fmt=".2f", cmap="RdYlBu_r",
        xticklabels=display_labels, yticklabels=display_labels,
        ax=ax, vmin=-1, vmax=1, center=0,
        linewidths=0.5, square=True
    )
    ax.set_title("Non-Drama H-Score 6축 × 통합성과 상관관계 (Spearman)", fontsize=13, pad=15)
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "nd_correlation_heatmap.png")
    fig.savefig(path, dpi=150, bbox_inches='tight')
    print(f"  💾 저장: {path}")
    plt.close()


def plot_weight_bar(weights):
    """가중치 배분 막대 차트"""
    labels_kr = {
        "cast_chemistry": "출연진 케미 파워",
        "creator_power": "PD/크리에이터 파워",
        "format_power": "포맷 파워",
        "platform_scheduling": "플랫폼·편성 전략",
        "pre_buzz": "사전 화제성",
        "concept_trend_fit": "콘셉트·트렌드 적합도",
    }

    sorted_w = sorted(weights.items(), key=lambda x: x[1], reverse=True)
    names = [labels_kr.get(k, k) for k, v in sorted_w]
    values = [v for k, v in sorted_w]
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD']

    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.barh(names, values, color=colors[:len(names)], edgecolor='white', height=0.6)

    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height() / 2,
                f'{val:.1f}점', va='center', fontsize=11, fontweight='bold')

    ax.set_xlabel('배점 (60점 만점)', fontsize=11)
    ax.set_title('Non-Drama H-Score 6축 가중치 배분 (실증 분석 결과)', fontsize=13, pad=15)
    ax.set_xlim(0, max(values) * 1.3)
    ax.invert_yaxis()
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "nd_weight_distribution.png")
    fig.savefig(path, dpi=150, bbox_inches='tight')
    print(f"  💾 저장: {path}")
    plt.close()


def plot_hscore_comparison(shows_scored):
    """캘리브레이션 프로그램 H-Score 비교 차트"""
    shows_sorted = sorted(shows_scored, key=lambda x: x["hscore"], reverse=True)

    titles = [d["title"][:12] for d in shows_sorted]
    scores = [d["hscore"] for d in shows_sorted]

    # 색상: 포맷별
    format_colors = {
        "OBS": "#4ECDC4", "VAR": "#FF6B6B", "SRV": "#FFEAA7",
        "TLK": "#96CEB4", "MUS": "#DDA0DD", "TRL": "#45B7D1",
        "SPT": "#FF8C42"
    }
    colors = [format_colors.get(d["format_type"], "#999") for d in shows_sorted]

    fig, ax = plt.subplots(figsize=(14, 7))
    bars = ax.barh(titles, scores, color=colors, edgecolor='white', height=0.65)

    for bar, val in zip(bars, scores):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                f'{val:.0f}', va='center', fontsize=9, fontweight='bold')

    ax.set_xlabel('H-Score (100점 만점)', fontsize=11)
    ax.set_title('2024-2026 K-예능 Non-Drama H-Score 비교', fontsize=14, pad=15)
    ax.set_xlim(0, 100)
    ax.axvline(x=70, color='#FF6B6B', linestyle='--', alpha=0.5, label='흥행 기대선 (70)')
    ax.axvline(x=50, color='#999', linestyle='--', alpha=0.3, label='평균선 (50)')

    # 범례 (포맷별)
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=v, label=k) for k, v in format_colors.items()
    ]
    ax.legend(handles=legend_elements, loc='lower right', fontsize=8, title='포맷유형')

    ax.invert_yaxis()
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "nd_hscore_comparison.png")
    fig.savefig(path, dpi=150, bbox_inches='tight')
    print(f"  💾 저장: {path}")
    plt.close()


def plot_actual_vs_predicted(df, axis_cols, weights):
    """실제 성과 vs 예측 H-Score 산점도"""
    fig, ax = plt.subplots(figsize=(8, 8))

    # H-Score 산출
    hscores = []
    for _, row in df.iterrows():
        total = 0
        for col in axis_cols:
            total += row[col] * (weights[col] / 10)
        hs = total / sum(weights.values()) * 100
        hscores.append(round(hs, 1))
    df['hscore_weighted'] = hscores

    # 포맷별 색상
    format_colors = {
        "OBS": "#4ECDC4", "VAR": "#FF6B6B", "SRV": "#FFEAA7",
        "TLK": "#96CEB4", "MUS": "#DDA0DD", "TRL": "#45B7D1",
        "SPT": "#FF8C42"
    }

    for fmt in df['format_type'].unique():
        mask = df['format_type'] == fmt
        ax.scatter(
            df.loc[mask, 'hscore_weighted'],
            df.loc[mask, 'combined_performance'],
            c=format_colors.get(fmt, '#999'),
            s=80, alpha=0.8, label=fmt, edgecolors='white'
        )
        for _, row in df[mask].iterrows():
            ax.annotate(row['title'][:8], (row['hscore_weighted'], row['combined_performance']),
                        fontsize=7, alpha=0.7, ha='left')

    ax.set_xlabel('H-Score (가중치 적용)', fontsize=11)
    ax.set_ylabel('통합 성과 (정규화)', fontsize=11)
    ax.set_title('Non-Drama: 예측 H-Score vs 실제 성과', fontsize=13, pad=15)
    ax.legend(fontsize=9, title='포맷')

    # 추세선
    z = np.polyfit(df['hscore_weighted'], df['combined_performance'], 1)
    p = np.poly1d(z)
    x_line = np.linspace(df['hscore_weighted'].min(), df['hscore_weighted'].max(), 100)
    ax.plot(x_line, p(x_line), '--', color='#FF6B6B', alpha=0.5, label=f'추세선')

    corr = df['hscore_weighted'].corr(df['combined_performance'], method='spearman')
    ax.text(0.05, 0.95, f'Spearman ρ = {corr:.3f}',
            transform=ax.transAxes, fontsize=11, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "nd_actual_vs_predicted.png")
    fig.savefig(path, dpi=150, bbox_inches='tight')
    print(f"  💾 저장: {path}")
    plt.close()

    return df


# ================================================================
# 9. 닐슨 데이터 연동
# ================================================================
def load_nielsen_data(csv_path):
    """닐슨 주간 시청률 CSV를 로드하여 예능 프로그램 시청률을 추출합니다."""
    try:
        df = pd.read_csv(csv_path)
        hr = df[df['metric_type'] == 'household_rating']

        # 프로그램별 평균 시청률
        prog_ratings = hr.groupby('program')['metric_value'].mean().sort_values(ascending=False)

        print("\n  📺 닐슨 데이터 로드 완료")
        print(f"  프로그램 수: {len(prog_ratings)}")
        print(f"\n  시청률 상위 10:")
        for prog, rating in prog_ratings.head(10).items():
            print(f"    {prog:40s} : {rating:.2f}%")
        return prog_ratings
    except FileNotFoundError:
        print("  ⚠️ 닐슨 CSV 파일을 찾을 수 없습니다.")
        return None


# ================================================================
# 10. 메인 실행
# ================================================================
def main():
    print(RUBRIC)

    # ─── Step 1: 캘리브레이션 데이터 구성 ───
    print("\n📦 Step 1: 캘리브레이션 데이터 로드")
    df, axis_cols = build_dataframe(calibration_shows)
    print(f"  데이터: {len(df)}편")
    print(f"  6축: {axis_cols}")
    print(f"  포맷 분포: {df['format_type'].value_counts().to_dict()}")
    print(f"\n  프로그램 목록 (H-Score raw 순):")
    for _, row in df.sort_values('hscore_raw', ascending=False).iterrows():
        rating_str = f"{row['avg_rating_pct']:.1f}%" if pd.notna(row['avg_rating_pct']) else "OTT"
        print(f"    {row['title']:30s} | raw:{row['hscore_raw']:5.1f} | "
              f"시청률:{rating_str:>6s} | 브랜드:{row['brand_reputation']:>5.0f} | "
              f"포맷:{row['format_type']}")

    # ─── Step 2: 닐슨 데이터 연동 ───
    print("\n📦 Step 2: 닐슨 데이터 교차 검증")
    nielsen_path = "/mnt/user-data/uploads/nielsen_weekly_all_categories_2024_2026.csv"
    nielsen = load_nielsen_data(nielsen_path)

    # ─── Step 3: 상관 분석 ───
    print("\n📦 Step 3: 상관 분석")
    corr = correlation_analysis(df, axis_cols)

    # 시청률 직접 상관 (OTT 제외)
    df_with_rating = df[df['avg_rating_pct'].notna()].copy()
    if len(df_with_rating) >= 5:
        print("\n  [시청률 직접 상관 (OTT 제외)]")
        correlation_analysis(df_with_rating, axis_cols, target="avg_rating_pct")

    # ─── Step 4: 회귀 분석 ───
    print("\n📦 Step 4: 회귀 분석")
    reg_results = regression_analysis(df, axis_cols)

    # ─── Step 5: 가중치 산출 ───
    print("\n📦 Step 5: 가중치 통합 산출")
    weights = derive_weights(corr, reg_results, axis_cols)

    # ─── Step 6: 전체 프로그램 H-Score 산출 (Dual KPI) ───
    print("\n" + "=" * 60)
    print("🎯 2024-2026 K-예능 Non-Drama H-Score 산출 결과 (Dual KPI)")
    print("=" * 60)

    scored = []
    for show in calibration_shows:
        hs_land, hs_long, hs_comb = calculate_nondrama_hscore_dual(
            show, WEIGHTS_LANDING, WEIGHTS_LONGEVITY
        )
        show["hscore_landing"] = hs_land
        show["hscore_longevity"] = hs_long
        show["hscore"] = hs_comb
        scored.append(show)

    scored.sort(key=lambda x: x["hscore"], reverse=True)

    print(f"\n  {'순위':>4s}  {'프로그램':30s}  {'안착':>5s}  {'롱런':>5s}  {'종합':>5s}  "
          f"{'시청률':>6s}  {'포맷':>4s}")
    print("  " + "-" * 95)
    for i, d in enumerate(scored, 1):
        rating_str = f"{d['avg_rating_pct']:.1f}%" if d.get('avg_rating_pct') else "OTT"
        print(f"  {i:>4d}  {d['title']:30s}  {d['hscore_landing']:5.1f}  "
              f"{d['hscore_longevity']:5.1f}  {d['hscore']:5.1f}  "
              f"{rating_str:>6s}  {d['format_type']:>4s}")

    # ─── Step 7: 시각화 ───
    print("\n📦 Step 7: 시각화 생성")
    plot_correlation_heatmap(df, axis_cols)
    plot_weight_bar(weights)
    plot_hscore_comparison(scored)
    df = plot_actual_vs_predicted(df, axis_cols, weights)

    # ─── Step 8: 결과 JSON 저장 ───
    output = {
        "weights_empirical": weights,
        "weights_landing": WEIGHTS_LANDING,
        "weights_longevity": WEIGHTS_LONGEVITY,
        "calibration_shows": [
            {
                "title": d["title"],
                "hscore_landing": d["hscore_landing"],
                "hscore_longevity": d["hscore_longevity"],
                "hscore": d["hscore"],
                "format_type": d["format_type"],
                "avg_rating_pct": d.get("avg_rating_pct"),
                "scores": {col: d[col] for col in axis_cols},
            }
            for d in scored
        ],
        "methodology": "5-method ensemble (Spearman corr + OLS + Ridge + RF + GB)",
        "dual_kpi": "Landing 45% + Longevity 55%",
        "data_size": len(df),
        "format_classification": "방송통신위 2012 공식분류 기반 (OBS/VAR/SRV/TLK/MUS/TRL/SPT)",
        "version": "1.0-nondrama"
    }
    json_path = os.path.join(OUTPUT_DIR, "nondrama_hscore_results.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n  💾 결과 JSON: {json_path}")

    print("\n" + "=" * 60)
    print("✅ 완료! output_nondrama/ 폴더에서 차트를 확인하세요.")
    print("=" * 60)

    return weights, scored


if __name__ == "__main__":
    weights, results = main()
