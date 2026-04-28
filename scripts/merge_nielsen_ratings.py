#!/usr/bin/env python3
"""
닐슨 CSV 시청률을 필모그래피에 병합
==================================
data/nielsen_weekly/*.csv의 시청률을 data/filmography/*/*.json에 자동 주입.

실행:
    python scripts/merge_nielsen_ratings.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from hit_predictor.data.nielsen_merger import (
    load_nielsen_ratings, build_rating_map, merge_ratings_into_filmography,
)


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    nielsen_dir = root / "data" / "nielsen_weekly"
    filmography_dir = root / "data" / "filmography"

    # 모든 닐슨 CSV 수집
    csv_files = list(nielsen_dir.glob("*.csv"))
    if not csv_files:
        print(f"❌ 닐슨 CSV 없음: {nielsen_dir}")
        sys.exit(1)

    print(f"📂 닐슨 CSV {len(csv_files)}개 발견")

    # 병합 후 rating map 구축
    import pandas as pd
    dfs = []
    for f in csv_files:
        try:
            dfs.append(load_nielsen_ratings(f))
            print(f"   ✓ {f.name}")
        except Exception as e:
            print(f"   ✗ {f.name}: {e}")
    if not dfs:
        print("❌ 로드 가능한 CSV 없음")
        sys.exit(1)
    df = pd.concat(dfs, ignore_index=True)

    rating_map = build_rating_map(df)
    print(f"\n📊 추출된 드라마 목록 ({len(rating_map)}편):")
    for norm, info in list(rating_map.items())[:20]:
        print(f"   {info['avg_rating']:5.2f}%  {info['canonical_title']:20s}  ({info['channel']}, {info['n_weeks']}주)")
    if len(rating_map) > 20:
        print(f"   ... 외 {len(rating_map) - 20}편")

    # 필모그래피에 병합
    print(f"\n🔄 필모그래피에 병합 중...")
    stats = merge_ratings_into_filmography(filmography_dir, rating_map)

    print(f"\n✅ 병합 완료:")
    print(f"   업데이트된 인물: {stats['updated_persons']}명")
    print(f"   업데이트된 크레디트: {stats['updated_credits']}개")
    print(f"   매칭된 드라마: {len(stats['matched_titles'])}편")
    if stats["matched_titles"]:
        for t in sorted(stats["matched_titles"]):
            print(f"      - {t}")


if __name__ == "__main__":
    main()
