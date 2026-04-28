#!/usr/bin/env python3
"""
캘리브레이션 실행 스크립트
==========================
종영작 데이터로 6-method ensemble 가중치 산정.

실행:
    python scripts/run_calibration.py

출력:
    - 콘솔: 상관 분석 + 가중치
    - output/hscore_weights_v2.json
    - output/calibration_report.csv
    - output/validation_report.json
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pandas as pd

from hit_predictor.calibration.ensemble import (
    ensemble_weights, correlation_report, all_methods_report,
)
from hit_predictor.calibration.validate import full_validation_report
from hit_predictor.core.axes import ALL_AXES, AXIS_LABELS_KR
from hit_predictor.data.loaders import load_dramas_from_csv


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    csv_path = root / "data" / "completed_dramas.csv"
    output_dir = root / "output"
    output_dir.mkdir(exist_ok=True)

    print(f"📂 로드: {csv_path}")
    dramas = load_dramas_from_csv(csv_path)
    print(f"   {len(dramas)}편")

    # DataFrame
    rows = []
    for d in dramas:
        row = d.axis_scores()
        row["title"] = d.title
        row["fundex_weekly_avg"] = d.fundex_weekly_avg
        row["actual_avg_rating"] = d.actual_avg_rating
        rows.append(row)
    df = pd.DataFrame(rows).dropna(subset=["fundex_weekly_avg"])
    print(f"   유효 데이터: {len(df)}편\n")

    # 상관 분석
    print("=" * 60)
    print("  📊 상관 분석 (타깃: fundex_weekly_avg)")
    print("=" * 60)
    corr = correlation_report(df, "fundex_weekly_avg")
    for _, r in corr.iterrows():
        print(f"  {AXIS_LABELS_KR[r['axis']]:15s} | "
              f"Pearson {r['pearson']:+.3f} | Spearman {r['spearman']:+.3f}")
    corr.to_csv(output_dir / "calibration_report.csv", index=False, encoding="utf-8-sig")

    # 방법별 비교
    print("\n" + "=" * 60)
    print("  🔬 6-method ensemble 기여도 (각 방법 내 %)")
    print("=" * 60)
    methods_df = all_methods_report(df, "fundex_weekly_avg")
    for _, r in methods_df.iterrows():
        label = AXIS_LABELS_KR[r["axis"]]
        parts = []
        for col in methods_df.columns:
            if col == "axis":
                continue
            parts.append(f"{col}={r[col]:.1f}%")
        print(f"  {label:15s} | " + " ".join(parts))
    methods_df.to_csv(output_dir / "methods_report.csv", index=False, encoding="utf-8-sig")

    # 앙상블
    print("\n" + "=" * 60)
    print("  ⚖️  최종 앙상블 가중치 (총합 60)")
    print("=" * 60)
    weights = ensemble_weights(df, "fundex_weekly_avg", total=60.0)
    for axis in sorted(ALL_AXES, key=lambda a: -weights[a]):
        bar = "█" * int(weights[axis])
        print(f"  {AXIS_LABELS_KR[axis]:15s} {weights[axis]:5.1f}  {bar}")
    print(f"\n  총합: {sum(weights.values()):.1f}")

    # 검증
    print("\n" + "=" * 60)
    print("  🔍 검증 리포트")
    print("=" * 60)
    validation = full_validation_report(df, "fundex_weekly_avg")
    np_check = validation["np_check"]
    print(f"  n/p 비율: {np_check['np_ratio']} (임계 {np_check['threshold']}) → "
          f"{'통과' if np_check['passes'] else '실패'}")
    if np_check.get("warning"):
        print(f"  ⚠️  {np_check['warning']}")
    loo = validation["loo_cv_ridge"]
    if "error" not in loo:
        print(f"  LOO CV (Ridge): MAE={loo['mae']:.0f}  RMSE={loo['rmse']:.0f}")

    # 저장
    output = {
        "weights": weights,
        "total": sum(weights.values()),
        "data_size": len(df),
        "target": "fundex_weekly_avg",
        "methodology": "6-method ensemble (Spearman+OLS+Ridge+NB+RF+GB)",
        "complex_models_used": len(df) >= 50,
    }
    (output_dir / "hscore_weights_v2.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    (output_dir / "validation_report.json").write_text(
        json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    print(f"\n💾 저장: {output_dir}/")


if __name__ == "__main__":
    main()
