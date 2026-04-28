#!/usr/bin/env python3
"""
방영 후 H-Score 업데이트 (Phase 3)
===================================
1~3회 방영 후 실제 시청률/펀덱스로 사전 예측을 업데이트.

실행:
    python scripts/update_postlaunch.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from hit_predictor.prediction.updater import (
    EarlyEvidence, update_hscore, update_verdict,
)


def ask_float(prompt: str) -> float | None:
    v = input(prompt).strip()
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def main() -> None:
    print("\n" + "=" * 60)
    print(" H-Score 사후 업데이트 (Phase 3)")
    print("=" * 60 + "\n")

    title = input("드라마 제목: ").strip()
    prior = ask_float("사전 예측 H-Score (종합, 0-100): ")
    if prior is None:
        print("H-Score 필수. 종료.")
        return

    print("\n방영 후 증거 입력 (없으면 엔터):")
    ev = EarlyEvidence(
        first_ep_rating=ask_float("  첫 회 시청률 (%): "),
        ep2_rating=ask_float("  2회 시청률 (%): "),
        ep3_rating=ask_float("  3회 시청률 (%): "),
        week1_fundex=ask_float("  1주차 펀덱스 점수: "),
        week2_fundex=ask_float("  2주차 펀덱스 점수: "),
    )

    result = update_hscore(prior, ev, weight_evidence=0.4)

    print("\n" + "=" * 60)
    print(f" {title} — Post-Launch Update")
    print("=" * 60)
    print(f"\n  사전 H-Score    : {result['prior_hscore']}")
    if result.get("evidence_score") is not None:
        print(f"  증거 점수       : {result['evidence_score']}")
        print(f"  증거 가중치     : {result['evidence_weight']}")
        print(f"  사후 H-Score    : {result['posterior_hscore']}")
        print(f"  업데이트 전망   : {update_verdict(result['posterior_hscore'])}")
        print(f"\n  초기 시청률 평균: {result.get('early_rating_avg')}%")
        if result.get("buzz_trajectory"):
            print(f"  화제성 추이     : {result['buzz_trajectory']}")
    else:
        print(f"  사후 H-Score    : {result['posterior_hscore']} (증거 없음, prior 그대로)")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n중단됨.")
