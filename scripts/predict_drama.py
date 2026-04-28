#!/usr/bin/env python3
"""
단일 드라마 H-Score 대화형 예측
==============================
실행: python scripts/predict_drama.py

6축 점수를 순차 입력받고 Triple KPI 결과를 출력합니다.
"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from hit_predictor.core.axes import ALL_AXES, RUBRICS, AXIS_LABELS_KR
from hit_predictor.core.hscore import calculate_triple_kpi
from hit_predictor.core.temporal import normalize_pre_buzz, normalization_report


def ask_int(prompt: str, lo: int = 1, hi: int = 10) -> int:
    while True:
        try:
            v = int(input(prompt).strip())
            if lo <= v <= hi:
                return v
            print(f"  ⚠️  {lo}~{hi} 범위 숫자")
        except (ValueError, EOFError, KeyboardInterrupt):
            print("  ⚠️  유효한 숫자 입력")


def ask_str(prompt: str, default: str = "") -> str:
    v = input(prompt).strip()
    return v or default


def show_hint(axis: str) -> None:
    r = RUBRICS[axis]
    print(f"\n  ▣ {r.label_kr}")
    print(f"    {r.description}")
    print("    참고 점수:")
    for s in [9, 7, 5, 3]:
        guide = r.scoring_guide.get(s, "")
        print(f"      {s}점: {guide}")


def main() -> None:
    print("\n" + "=" * 62)
    print(" K-Drama Hit Predictor v2 — Triple KPI 대화형 예측")
    print("=" * 62)
    print("\n6축 점수 (1~10)를 순서대로 입력해주세요.\n")

    # Step 1: 메타
    title = ask_str("드라마 제목: ")
    if not title:
        print("제목 필수. 종료.")
        return
    release = ask_str("공개일 (YYYY.MM.DD, 엔터=건너뛰기): ")
    platform = ask_str("플랫폼 (엔터=건너뛰기): ")
    genre = ask_str("장르 (엔터=건너뛰기): ")

    # Step 2: 6축
    print("\n" + "─" * 50)
    print("▼ 6축 점수 입력")
    print("─" * 50)

    axis_scores = {}
    for axis in ALL_AXES:
        show_hint(axis)
        axis_scores[axis] = ask_int(f"    {AXIS_LABELS_KR[axis]} (1-10): ")

    # Step 3: 시간 정규화
    if release:
        m_date = ask_str(
            f"\n사전 화제성 측정일 (엔터={datetime.now().strftime('%Y.%m.%d')}): ",
            default=datetime.now().strftime("%Y.%m.%d"),
        )
        try:
            raw = axis_scores["pre_buzz"]
            adj = normalize_pre_buzz(raw, release, m_date)
            rpt = normalization_report(raw, release, m_date)
            print(f"\n  🕐 시간 정규화:")
            print(f"     원점수 {raw} → 보정 {adj}")
            print(f"     공개까지 {rpt['weeks_until_release']}주, 승수 {rpt['multiplier']}")
            axis_scores["pre_buzz"] = adj
        except Exception as e:
            print(f"  ⚠️  정규화 실패 ({e}), 원점수 사용")

    # Step 4: 계산
    result = calculate_triple_kpi(title, axis_scores)

    print("\n" + "=" * 62)
    print(f" 📊 {title} — H-Score Triple KPI")
    print("=" * 62)
    print(f"\n  종합 H-Score: {result.combined}/100")
    print(f"  전망        : {result.verdict}")
    print(f"  ├ 첫방 예측 : {result.first_ep.hscore}/100")
    print(f"  ├ 평균 예측 : {result.avg.hscore}/100")
    print(f"  └ 상대우위  : {result.rsi_victory.hscore}/100  (경쟁 승리 예측)")

    # Step 5: 축별 점수
    print("\n  ─ 축별 점수 ─")
    for axis in ALL_AXES:
        raw = axis_scores[axis]
        label = AXIS_LABELS_KR[axis]
        bar = "█" * int(raw)
        print(f"    {label:12s} {raw:5.1f}  {bar}")

    # Step 6: 강점/약점
    top = result.avg.top_contributors(2)
    bot = result.avg.bottom_contributors(2)
    print(f"\n  💪 강점: {', '.join(c.label_kr for c in top)}")
    print(f"  ⚠️  약점: {', '.join(c.label_kr for c in bot)}")

    print("\n" + "=" * 62 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n중단됨.")
