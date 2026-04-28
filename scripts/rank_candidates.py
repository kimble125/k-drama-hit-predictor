#!/usr/bin/env python3
"""
후보 드라마 일괄 Triple KPI 예측
================================
data/candidate_dramas.csv를 읽어 H-Score Triple KPI로 순위 매김.

실행:
    python scripts/rank_candidates.py

출력:
    - 콘솔: 순위 + 상세
    - output/ranking_results.json
    - output/ranking_results.csv
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from hit_predictor.core.axes import ALL_AXES, AXIS_LABELS_KR
from hit_predictor.core.hscore import calculate_triple_kpi
from hit_predictor.core.temporal import normalize_pre_buzz, DEFAULT_ALPHA
from hit_predictor.data.loaders import load_dramas_from_csv


MEASUREMENT_DATE = "2026.04.05"


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    csv_path = root / "data" / "candidate_dramas.csv"
    output_dir = root / "output"
    output_dir.mkdir(exist_ok=True)

    print(f"📂 로드: {csv_path}")
    dramas = load_dramas_from_csv(csv_path)
    print(f"   총 {len(dramas)}편\n")

    # 점수가 다 있는 드라마만
    scored = []
    for d in dramas:
        core_5 = [d.cast_power, d.creator_power, d.ip_power,
                  d.platform_strategy, d.genre_market_fit]
        if all(x is not None for x in core_5):
            scored.append(d)

    print(f"   유효 (점수 부여): {len(scored)}편\n")

    results = []
    for d in scored:
        # 시간 정규화 (pre_buzz_raw가 있으면 사용)
        raw = d.pre_buzz_raw if d.pre_buzz_raw is not None else d.pre_buzz
        if d.release_date and raw is not None:
            try:
                adjusted = normalize_pre_buzz(raw, d.release_date, MEASUREMENT_DATE, alpha=DEFAULT_ALPHA)
            except Exception:
                adjusted = raw
        else:
            adjusted = raw if raw is not None else 0

        axis_scores = d.axis_scores()
        axis_scores["pre_buzz"] = adjusted

        result = calculate_triple_kpi(d.title, axis_scores)
        results.append({
            "title": d.title,
            "platform": d.platform,
            "genre": d.genre,
            "release_date": d.release_date,
            "combined": result.combined,
            "first_ep": result.first_ep.hscore,
            "avg": result.avg.hscore,
            "rsi_victory": result.rsi_victory.hscore,
            "verdict": result.verdict,
            "axis_scores": axis_scores,
            "pre_buzz_raw": raw,
            "pre_buzz_adjusted": adjusted,
        })

    results.sort(key=lambda r: -r["combined"])

    # 출력
    print("=" * 72)
    print("  🎯 H-Score v2 Triple KPI 예측 (종합 내림차순)")
    print("=" * 72)
    for i, r in enumerate(results, 1):
        print(f"\n  {i}위: {r['title']}  —  {r['verdict']}")
        print(f"      종합 {r['combined']:5.1f} | 첫방 {r['first_ep']:5.1f} | "
              f"평균 {r['avg']:5.1f} | 상대우위 {r['rsi_victory']:5.1f}")
        print(f"      플랫폼: {r['platform']} | 공개: {r['release_date']}")
        if r["pre_buzz_raw"] != r["pre_buzz_adjusted"]:
            print(f"      사전화제성: {r['pre_buzz_raw']} → {r['pre_buzz_adjusted']}")

    # 저장
    out = {
        "measurement_date": MEASUREMENT_DATE,
        "alpha": DEFAULT_ALPHA,
        "methodology": "H-Score v2 Triple KPI (first_ep 0.30 + avg 0.50 + rsi_victory 0.20)",
        "results": results,
    }
    (output_dir / "ranking_results.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8",
    )

    # CSV
    import csv as _csv
    with (output_dir / "ranking_results.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = _csv.writer(f)
        writer.writerow(["rank", "title", "combined", "first_ep", "avg",
                         "rsi_victory", "verdict", "platform", "release_date"])
        for i, r in enumerate(results, 1):
            writer.writerow([i, r["title"], r["combined"], r["first_ep"],
                             r["avg"], r["rsi_victory"], r["verdict"],
                             r["platform"], r["release_date"]])

    print(f"\n💾 저장: {output_dir}/ranking_results.{{json,csv}}")


if __name__ == "__main__":
    main()
