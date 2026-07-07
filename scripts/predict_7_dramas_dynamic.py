#!/usr/bin/env python3
import sys
from pathlib import Path

# Add src to python path
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / "src"))

from hit_predictor.core.hscore import calculate_triple_kpi
from hit_predictor.core.temporal import normalize_pre_buzz, DEFAULT_ALPHA

# Define 7 dramas with Auto and Adjusted versions based on the new logic
# Dynamic pre-buzz measurement dates are set to release_date - 7 days, meaning adjusted buzz = raw buzz
dramas_data = [
    {
        "title": "내일도 출근 (Adjusted)",
        "release": "2026.06.22",
        "cast_power": 7.0,
        "creator_power": 4.0,
        "ip_power": 7.0,
        "platform_strategy": 7.0,
        "pre_buzz_raw": 6.5,
        "genre_market_fit": 5.0,
    },
    {
        "title": "김부장 (Adjusted)",
        "release": "2026.06.26",
        "cast_power": 8.5,
        "creator_power": 7.5,
        "ip_power": 8.0,
        "platform_strategy": 8.0,
        "pre_buzz_raw": 7.0,
        "genre_market_fit": 8.0,
    },
    {
        "title": "맨 끝줄 소년 (Adjusted)",
        "release": "2026.06.26",
        "cast_power": 9.0,
        "creator_power": 8.0,
        "ip_power": 5.0,
        "platform_strategy": 10.0,
        "pre_buzz_raw": 6.5,
        "genre_market_fit": 7.0,
    },
    {
        "title": "멋진 신세계 (Auto)",
        "release": "2026.05.08",
        "cast_power": 6.1,
        "creator_power": 1.4,
        "ip_power": 2.0,
        "platform_strategy": 8.0,
        "pre_buzz_raw": 5.0,
        "genre_market_fit": 5.0,
    },
    {
        "title": "멋진 신세계 (Adjusted)",
        "release": "2026.05.08",
        "cast_power": 7.0,
        "creator_power": 7.0,
        "ip_power": 2.0,
        "platform_strategy": 8.0,
        "pre_buzz_raw": 5.0,
        "genre_market_fit": 5.0,
    },
    {
        "title": "참교육 (Adjusted)",
        "release": "2026.06.05",
        "cast_power": 8.5,
        "creator_power": 8.0,
        "ip_power": 8.0,
        "platform_strategy": 10.0,
        "pre_buzz_raw": 8.0,
        "genre_market_fit": 9.0,
    },
    {
        "title": "취사병 전설이 되다 (Auto)",
        "release": "2026.05.11",
        "cast_power": 0.0,
        "creator_power": 3.3,
        "ip_power": 9.0,
        "platform_strategy": 8.0,
        "pre_buzz_raw": 7.0,
        "genre_market_fit": 8.0,
    },
    {
        "title": "취사병 전설이 되다 (Adjusted)",
        "release": "2026.05.11",
        "cast_power": 8.0,
        "creator_power": 8.0,
        "ip_power": 9.0,
        "platform_strategy": 8.0,
        "pre_buzz_raw": 7.0,
        "genre_market_fit": 8.0,
    },
    {
        "title": "신입사원 강회장 (Auto)",
        "release": "2026.05.30",
        "cast_power": 5.9,
        "creator_power": 4.3, # Kim Soon-ok auto reflected
        "ip_power": 6.0,
        "platform_strategy": 6.0,
        "pre_buzz_raw": 5.0,
        "genre_market_fit": 5.0,
    },
    {
        "title": "신입사원 강회장 (Adjusted)",
        "release": "2026.05.30",
        "cast_power": 8.0,
        "creator_power": 9.0,
        "ip_power": 7.0,
        "platform_strategy": 6.0,
        "pre_buzz_raw": 5.0,
        "genre_market_fit": 6.0,
    }
]

print("=" * 75)
print(" H-Score Recalculation for 7 Dramas (Dynamic Pre-buzz & Creator Blending)")
print("=" * 75)

for d in dramas_data:
    # Calculate dynamic measurement date (release - 7 days)
    from datetime import timedelta
    from hit_predictor.core.temporal import _parse_date
    rel_dt = _parse_date(d["release"])
    m_dt = rel_dt - timedelta(days=7)
    m_date_str = m_dt.strftime("%Y.%m.%d")
    
    adjusted_buzz = normalize_pre_buzz(
        d["pre_buzz_raw"], d["release"], m_date_str, alpha=DEFAULT_ALPHA
    )
    
    axis_scores = {
        "cast_power": d["cast_power"],
        "creator_power": d["creator_power"],
        "ip_power": d["ip_power"],
        "platform_strategy": d["platform_strategy"],
        "pre_buzz": adjusted_buzz,
        "genre_market_fit": d["genre_market_fit"],
    }
    
    result = calculate_triple_kpi(d["title"], axis_scores)
    
    print(f"\n📺 {result.title}")
    print(f"   공개일: {d['release']} | 측정일(동적): {m_date_str}")
    print(f"   사전 화제성: {d['pre_buzz_raw']} (raw) -> {adjusted_buzz} (adjusted)")
    print(f"   H-Score Combined: {result.combined}/100 ({result.verdict})")
    print(f"   ├ 첫방 예측 : {result.first_ep.hscore}/100")
    print(f"   ├ 평균 예측 : {result.avg.hscore}/100")
    print(f"   └ 상대우위  : {result.rsi_victory.hscore}/100")
    print(f"   [6축 입력값] Cast={d['cast_power']:.1f} | Creator={d['creator_power']:.1f} | IP={d['ip_power']:.1f} | Plat={d['platform_strategy']:.1f} | Buzz={adjusted_buzz:.1f} | Genre={d['genre_market_fit']:.1f}")
    print("-" * 75)
