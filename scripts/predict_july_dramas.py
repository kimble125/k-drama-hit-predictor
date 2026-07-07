#!/usr/bin/env python3
import sys
import math
from pathlib import Path
from datetime import timedelta

# Add src to python path
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / "src"))

from hit_predictor.core.hscore import calculate_triple_kpi
from hit_predictor.core.temporal import normalize_pre_buzz, calculate_youtube_buzz, DEFAULT_ALPHA
from hit_predictor.core.lead_in import lead_in_bonus
from hit_predictor.rsi.calculator import creator_score_from_rsi

# Define raw input data for 4 dramas
dramas_info = [
    {
        "title": "결혼의 완성",
        "release": "2026.07.04",
        "measurement": "2026.07.03",  # 방영 1일 전
        "cast_power": 9.0,  # 남궁민(메가스타) + 조연진 조합
        "director_rsi": 0.43,
        "writer_rsi": 0.35,
        "writer_hierarchy": [
            {"rsi": 0.35, "role": "main_single"}  # 단독 집필 (정재하 작가)
        ],
        "ip_power": 2.0,  # 오리지널 각본
        "platform_base": 6.0,  # KBS 2TV 주말 미니시리즈
        "platform_ott_bonus": 1.5,  # 디즈니+ 동시
        "lead_in_rating": 7.0,  # 전작 은애하는 도적님아 7.0% 가정
        "lead_in_gap_days": 132,  # 2월 22일 종영 ~ 7월 4일 방영 (공백 약 4개월)
        "youtube_views": 410000,
        "youtube_likes": 254,
        "youtube_comments": 18,
        "youtube_days_elapsed": 10.0,
        "raw_buzz_override": 6.0,  # 네이버 검색 등 종합 화제성 보정
        "genre_market_fit": 7.0,  # 로맨스/범죄/스릴러 복합, 주말 슬롯
    },
    {
        "title": "아파트",
        "release": "2026.07.11",
        "measurement": "2026.07.03",  # 방영 8일 전
        "cast_power": 9.0,  # 지성(메가스타) + 하윤경 + 박병은 + 문소리 조합
        "director_rsi": 0.50,
        "writer_rsi": 0.40,
        "writer_hierarchy": [
            {"rsi": 0.40, "role": "main_single"}  # 단독 집필 (김윤영 작가)
        ],
        "ip_power": 2.0,  # 오리지널 각본
        "platform_base": 7.0,  # JTBC 토일
        "platform_ott_bonus": 1.5,  # 넷플릭스 + 티빙 동시
        "lead_in_rating": 10.5,  # 전작 신입사원 강회장 후반부 약 10.5% 가정
        "lead_in_gap_days": 0,  # 바로 이어지는 후속
        "youtube_views": 110000,
        "youtube_likes": 717,
        "youtube_comments": 114,
        "youtube_days_elapsed": 14.0,
        "raw_buzz_override": 6.5,
        "genre_market_fit": 8.0,  # 범죄/미스터리/스릴러/코미디 복합
    },
    {
        "title": "그에게 드림",
        "release": "2026.07.13",
        "measurement": "2026.07.03",  # 방영 10일 전
        "cast_power": 6.5,  # 스타 및 라이징 캐스팅
        "director_rsi": 0.67,
        "writer_rsi": 0.35,  # 신인 작가 (정은비 작가)
        "writer_hierarchy": [
            {"rsi": 0.35, "role": "main_single"},  # 메인 단독 작가
            {"rsi": 0.95, "role": "assistant"}     # 보조 작가 참여작 (도깨비, 미스터션샤인)
        ],
        "ip_power": 2.0,  # 오리지널 각본
        "platform_base": 4.0,  # ENA 월화
        "platform_ott_bonus": 1.0,  # 국내 OTT 동시
        "lead_in_rating": None,
        "lead_in_gap_days": None,
        "youtube_views": 3800,
        "youtube_likes": 50,
        "youtube_comments": 16,
        "youtube_days_elapsed": 8.0,
        "raw_buzz_override": 3.5,
        "genre_market_fit": 5.0,  # 로맨틱 코미디
    },
    {
        "title": "가스인간",
        "release": "2026.07.02",
        "measurement": "2026.07.03",  # 공개 1일 후 측정
        "cast_power": 9.0,  # 오구리 슌 등 일본 초호화 캐스팅
        "director_rsi": 0.80,
        "writer_rsi": 0.88,
        "writer_hierarchy": [
            {"rsi": 0.88, "role": "main_co"},  # 공동 집필 (연상호)
            {"rsi": 0.88, "role": "main_co"}   # 공동 집필 (류용재)
        ],
        "ip_power": 6.0,  # 원작 가스인간 제1호 리메이크
        "platform_base": 10.0,  # 넷플릭스 글로벌 독점 오리지널
        "platform_ott_bonus": 0.0,
        "lead_in_rating": None,
        "lead_in_gap_days": None,
        "youtube_views": 15000,  # 넷플릭스 코리아 기준만 반영
        "youtube_likes": 233,
        "youtube_comments": 89,
        "youtube_days_elapsed": 21.0,
        "raw_buzz_override": 6.0,
        "genre_market_fit": 7.0,  # SF 장르 마니아층 타겟
    }
]

print("=" * 80)
print(" H-Score v7.1 Algorithm Recalculation (July New Dramas)")
print("=" * 80)

for d in dramas_info:
    # 1. 크리에이터 점수 계산 (작가 층위 반영)
    creator_power = creator_score_from_rsi(
        director_rsi=d["director_rsi"],
        writer_rsi=d["writer_rsi"],
        writer_hierarchy=d["writer_hierarchy"]
    )
    
    # 2. 플랫폼 전략 계산 (전작 갭 감쇄 가중치 적용)
    li_bonus = 0.0
    if d["lead_in_rating"] is not None:
        li_bonus = lead_in_bonus(d["lead_in_rating"], d["lead_in_gap_days"])
    
    platform_strategy = d["platform_base"] + d["platform_ott_bonus"] + li_bonus
    platform_strategy = min(platform_strategy, 10.0)
    
    # 3. 유튜브 화제성 원본 지표 산출
    yt_buzz = calculate_youtube_buzz(
        views=d["youtube_views"],
        likes=d["youtube_likes"],
        comments=d["youtube_comments"],
        days_elapsed=d["youtube_days_elapsed"]
    )
    
    # 4. 사전 화제성(Pre-buzz) 계산 (방영일 임박 보정 적용)
    raw_buzz = d["raw_buzz_override"]
    adjusted_buzz = normalize_pre_buzz(
        raw_buzz, d["release"], d["measurement"], alpha=DEFAULT_ALPHA
    )
    
    # 5. H-Score 6축 취합
    axis_scores = {
        "cast_power": d["cast_power"],
        "creator_power": creator_power,
        "ip_power": d["ip_power"],
        "platform_strategy": platform_strategy,
        "pre_buzz": adjusted_buzz,
        "genre_market_fit": d["genre_market_fit"]
    }
    
    result = calculate_triple_kpi(d["title"], axis_scores)
    
    print(f"\n📺 작품명: {result.title}")
    print(f"   공개일: {d['release']} | 측정일: {d['measurement']}")
    print(f"   [세부 알고리즘 결과]")
    print(f"   ├ 크리에이터 파워 : {creator_power}/10 (작가 층위 반영)")
    print(f"   ├ 플랫폼 전략     : {platform_strategy:.1f}/10 (전작 갭 {d['lead_in_gap_days']}일 보너스 반영)")
    print(f"   └ 유튜브 화제성   : {yt_buzz:.2f}/10 (업로드 {d['youtube_days_elapsed']}일차 보정)")
    print(f"   [H-Score 결과]")
    print(f"   └ H-Score Combined: {result.combined}/100 ({result.verdict})")
    print(f"     ├ 첫방 예측 : {result.first_ep.hscore}/100")
    print(f"     ├ 평균 예측 : {result.avg.hscore}/100")
    print(f"     └ 상대우위  : {result.rsi_victory.hscore}/100")
    print(f"   [6축 입력값] Cast={d['cast_power']:.1f} | Creator={creator_power:.1f} | IP={d['ip_power']:.1f} | Plat={platform_strategy:.1f} | Buzz={adjusted_buzz:.1f} | Genre={d['genre_market_fit']:.1f}")
    print("-" * 80)
