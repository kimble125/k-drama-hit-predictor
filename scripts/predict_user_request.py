#!/usr/bin/env python3
import sys
from pathlib import Path

# Add src to python path
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / "src"))

from hit_predictor.core.hscore import calculate_triple_kpi
from hit_predictor.core.temporal import normalize_pre_buzz

# Define candidate dramas with different scenarios to analyze
dramas_data = [
    # 1. 내일도 출근 (Mon-Tue tvN Drama)
    # Cast: 서인국, 박지현, 강미나 (A/B+ level leads, solid fanbase -> 7)
    # Creator: 조은솔 (director), 김경민 (writer) (Rookie/rising team -> 4)
    # IP: Kakao Webtoon 'Tomorrow Also Go to Work!' (Very popular romance webtoon -> 7)
    # Platform: tvN + TVING + Wavve (Major cable + domestic OTTs + strong predecessor lead-in -> 7)
    # Pre-buzz: FUNdex 6th place in TV dramas (Raw 6.5)
    # Genre Market Fit: Romance/Office (Romance decline but office comedy stable -> 5)
    {
        "title": "내일도 출근",
        "release": "2026.06.22",
        "measurement": "2026.06.15", # measured 1 week before premiere
        "cast_power": 7.0,
        "creator_power": 4.0,
        "ip_power": 7.0,
        "platform_strategy": 7.0,
        "pre_buzz_raw": 6.5,
        "genre_market_fit": 5.0,
    },
    # 2. 김부장 (Fri-Sat SBS Drama)
    # Cast: 소지섭, 최대훈, 윤경호, 주상욱, 손나은 (Grand prize winner + veteran superstar -> 8.5)
    # Creator: 이승영 (director, Voice 2/Tracer), 남대중 (writer, 30 Days film -> 7.5)
    # IP: Naver Webtoon 'Manager Kim' (Mega-hit webtoon franchise with hundreds of millions of views -> 8.0)
    # Platform: SBS + Netflix (Major terrestrial + global OTT -> 8.0)
    # Pre-buzz: FUNdex 7th place in TV dramas before airing (Raw 7.0)
    # Genre Market Fit: Action, Noir, Thriller (Highly popular rising genres -> 8.0)
    {
        "title": "김부장",
        "release": "2026.06.26",
        "measurement": "2026.06.19", # measured 1 week before premiere
        "cast_power": 8.5,
        "creator_power": 7.5,
        "ip_power": 8.0,
        "platform_strategy": 8.0,
        "pre_buzz_raw": 7.0,
        "genre_market_fit": 8.0,
    },
    # 3. 맨 끝줄 소년 (Netflix Original Series)
    # Cast: 최민식, 최현욱, 허준호, 김윤진, 진경 (Legendary actor Choi Min-sik + rising star Choi Hyun-wook -> 9.0)
    # Creator: 김규태 (director, Our Blues/Iris/괜찮아사랑이야), 장명우 (writer, Bogota co-writer -> 8.0)
    # IP: Spanish play 'El chico de la última fila' (Prestigious award-winning theatrical IP -> 5.0)
    # Platform: Netflix (Global OTT exclusive -> 10.0)
    # Pre-buzz: Strong media interest and high trailer views due to Choi Min-sik (Raw 6.5)
    # Genre Market Fit: Suspense, Drama (Strong fit on Netflix -> 7.0)
    {
        "title": "맨 끝줄 소년",
        "release": "2026.06.26",
        "measurement": "2026.06.19", # measured 1 week before premiere
        "cast_power": 9.0,
        "creator_power": 8.0,
        "ip_power": 5.0,
        "platform_strategy": 10.0,
        "pre_buzz_raw": 6.5,
        "genre_market_fit": 7.0,
    }
]

print("=" * 60)
print(" H-Score Calculation for June 2026 Dramas")
print("=" * 60)

for d in dramas_data:
    # 1. Normalize pre_buzz
    raw_buzz = d["pre_buzz_raw"]
    adjusted_buzz = normalize_pre_buzz(
        raw_buzz, d["release"], d["measurement"]
    )
    
    # 2. Prepare axis scores
    axis_scores = {
        "cast_power": d["cast_power"],
        "creator_power": d["creator_power"],
        "ip_power": d["ip_power"],
        "platform_strategy": d["platform_strategy"],
        "pre_buzz": adjusted_buzz,
        "genre_market_fit": d["genre_market_fit"],
    }
    
    # 3. Calculate Triple KPI
    result = calculate_triple_kpi(d["title"], axis_scores)
    
    # 4. Print results
    print(f"\n📺 드라마: {result.title}")
    print(f"   공개일: {d['release']} | 측정일: {d['measurement']}")
    print(f"   사전 화제성: {raw_buzz} (raw) -> {adjusted_buzz} (adjusted)")
    print(f"   ----------------------------------------")
    print(f"   [Triple KPI H-Score]")
    print(f"   - 첫방 예측 (First Ep) : {result.first_ep.hscore}/100")
    print(f"   - 평균 예측 (Average)  : {result.avg.hscore}/100")
    print(f"   - 상대우위 (RSI Victory): {result.rsi_victory.hscore}/100")
    print(f"   ========================================")
    print(f"   - 종합 H-Score (Combined): {result.combined}/100")
    print(f"   - 예측 등급 (Verdict)   : {result.verdict}")
    print(f"   ----------------------------------------")
    print(f"   [6축 입력값]")
    for axis, score in axis_scores.items():
        print(f"     * {axis:18s}: {score:.1f}")
    
    # Print top/bottom contributors
    top = result.avg.top_contributors(2)
    bot = result.avg.bottom_contributors(2)
    print(f"   [분석 피드백]")
    print(f"     💪 강점: {', '.join(c.label_kr for c in top)}")
    print(f"     ⚠️  약점: {', '.join(c.label_kr for c in bot)}")
    print("-" * 60)
