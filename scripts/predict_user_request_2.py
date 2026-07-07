#!/usr/bin/env python3
import sys
from pathlib import Path

# Add src to python path
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / "src"))

from hit_predictor.core.hscore import calculate_triple_kpi

# 1. 멋진 신세계
# - Auto: Cast 6.1, Creator 1.4, IP 2.0, Platform 8.0, Pre-buzz 6.7 (adj), Genre 5.0
# - Adjusted: Cast 7.0 (Lim Ji-yeon + Heo Nam-jun), Creator 7.0 (Han Tae-seop + Kang Hyun-joo, manual), IP 2.0, Platform 8.0, Pre-buzz 6.7, Genre 5.0
drama_shinsegae_auto = {
    "title": "멋진 신세계 (Auto)",
    "cast_power": 6.1,
    "creator_power": 1.4,
    "ip_power": 2.0,
    "platform_strategy": 8.0,
    "pre_buzz": 6.7,
    "genre_market_fit": 5.0
}
drama_shinsegae_adj = {
    "title": "멋진 신세계 (Adjusted)",
    "cast_power": 7.0,
    "creator_power": 7.0,
    "ip_power": 2.0,
    "platform_strategy": 8.0,
    "pre_buzz": 6.7,
    "genre_market_fit": 5.0
}

# 2. 참교육
# - Adjusted: Cast 8.5 (Lee Sung-min + Kim Mu-yeol), Creator 8.0 (Hong Jong-chan + Lee Nam-gyu), IP 8.0 (Mega-hit webtoon), Platform 10.0 (Netflix), Pre-buzz 8.0, Genre 9.0
drama_education_adj = {
    "title": "참교육 (Adjusted)",
    "cast_power": 8.5,
    "creator_power": 8.0,
    "ip_power": 8.0,
    "platform_strategy": 10.0,
    "pre_buzz": 8.0,
    "genre_market_fit": 9.0
}

# 3. 취사병 전설이 되다
# - Auto: Cast 0.0 (Park Ji-hoon tv credits <3), Creator 3.3, IP 9.0, Platform 8.0, Pre-buzz 7.0, Genre 8.0
# - Adjusted: Cast 8.0 (Park Ji-hoon manual rating), Creator 8.0 (Jo Nam-hyung + Choi Ryong, manual), IP 9.0, Platform 8.0, Pre-buzz 7.0, Genre 8.0
drama_chef_auto = {
    "title": "취사병 전설이 되다 (Auto)",
    "cast_power": 0.0,
    "creator_power": 3.3,
    "ip_power": 9.0,
    "platform_strategy": 8.0,
    "pre_buzz": 7.0,
    "genre_market_fit": 8.0
}
drama_chef_adj = {
    "title": "취사병 전설이 되다 (Adjusted)",
    "cast_power": 8.0,
    "creator_power": 8.0,
    "ip_power": 9.0,
    "platform_strategy": 8.0,
    "pre_buzz": 7.0,
    "genre_market_fit": 8.0
}

# 4. 신입사원 강회장
# - Auto: Cast 5.9, Creator 0.0, IP 6.0, Platform 6.0, Pre-buzz 5.0, Genre 5.0
# - Adjusted: Cast 8.0 (Son Hyun-joo + Lee Jun-young), Creator 9.0 (Kim Soon-ok star creator), IP 7.0 (San Kyeong webnovel), Platform 6.0, Pre-buzz 5.0, Genre 6.0
drama_president_auto = {
    "title": "신입사원 강회장 (Auto)",
    "cast_power": 5.9,
    "creator_power": 0.0,
    "ip_power": 6.0,
    "platform_strategy": 6.0,
    "pre_buzz": 5.0,
    "genre_market_fit": 5.0
}
drama_president_adj = {
    "title": "신입사원 강회장 (Adjusted)",
    "cast_power": 8.0,
    "creator_power": 9.0,
    "ip_power": 7.0,
    "platform_strategy": 6.0,
    "pre_buzz": 5.0,
    "genre_market_fit": 6.0
}

dramas = [
    (drama_shinsegae_auto, drama_shinsegae_adj),
    (None, drama_education_adj),
    (drama_chef_auto, drama_chef_adj),
    (drama_president_auto, drama_president_adj)
]

print("=" * 70)
print(" H-Score Analysis (Auto Recalculated vs. Verified/Adjusted)")
print("=" * 70)

for auto_d, adj_d in dramas:
    if auto_d:
        res_auto = calculate_triple_kpi(auto_d["title"], {k: v for k, v in auto_d.items() if k != "title"})
        print(f"\n📺 {res_auto.title}")
        print(f"   H-Score Combined: {res_auto.combined}/100 ({res_auto.verdict})")
        print(f"   ├ 첫방 예측 : {res_auto.first_ep.hscore}/100")
        print(f"   ├ 평균 예측 : {res_auto.avg.hscore}/100")
        print(f"   └ 상대우위  : {res_auto.rsi_victory.hscore}/100")
        
    res_adj = calculate_triple_kpi(adj_d["title"], {k: v for k, v in adj_d.items() if k != "title"})
    print(f"\n📺 {res_adj.title}")
    print(f"   H-Score Combined: {res_adj.combined}/100 ({res_adj.verdict})")
    print(f"   ├ 첫방 예측 : {res_adj.first_ep.hscore}/100")
    print(f"   ├ 평균 예측 : {res_adj.avg.hscore}/100")
    print(f"   └ 상대우위  : {res_adj.rsi_victory.hscore}/100")
    print(f"   [입력값] Cast={adj_d['cast_power']:.1f} | Creator={adj_d['creator_power']:.1f} | IP={adj_d['ip_power']:.1f} | Plat={adj_d['platform_strategy']:.1f} | Buzz={adj_d['pre_buzz']:.1f} | Genre={adj_d['genre_market_fit']:.1f}")
    
    print("-" * 70)
