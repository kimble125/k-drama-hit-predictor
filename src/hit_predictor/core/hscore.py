"""
H-Score 계산 엔진 (Triple KPI)
================================
순수 함수. 입력: 드라마 6축 점수. 출력: 3개 KPI + 종합.

Triple KPI:
    1. first_ep   — 첫방 시청률/오픈 반응
    2. avg        — 평균 시청률/롱런
    3. rsi_victory — 동시간대 상대우위 (주상필 2019)

    combined = first_ep × 0.30 + avg × 0.50 + rsi_victory × 0.20
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .axes import ALL_AXES, AXIS_LABELS_KR
from .weights import (
    WeightProfile, get_profile, validate_weights, COMBINED_WEIGHTS_V2,
)


# ────────────────────────────────────────────────────────────────
# 결과 스키마
# ────────────────────────────────────────────────────────────────
@dataclass
class AxisContribution:
    axis: str
    raw_score: float
    weight: float
    contribution: float

    @property
    def label_kr(self) -> str:
        return AXIS_LABELS_KR[self.axis]


@dataclass
class HScoreResult:
    hscore: float
    profile_name: str
    contributions: list[AxisContribution]

    def top_contributors(self, n: int = 2) -> list[AxisContribution]:
        return sorted(self.contributions, key=lambda c: -c.contribution)[:n]

    def bottom_contributors(self, n: int = 2) -> list[AxisContribution]:
        return sorted(self.contributions, key=lambda c: c.contribution)[:n]


@dataclass
class TripleKPIResult:
    """Triple KPI 통합 결과."""
    title: str
    first_ep: HScoreResult
    avg: HScoreResult
    rsi_victory: HScoreResult
    combined: float
    verdict: str
    axis_scores: dict[str, float]

    def as_dict(self) -> dict:
        return {
            "title": self.title,
            "hscore_first_ep": self.first_ep.hscore,
            "hscore_avg": self.avg.hscore,
            "hscore_rsi_victory": self.rsi_victory.hscore,
            "hscore_combined": self.combined,
            "verdict": self.verdict,
            "axis_scores": self.axis_scores,
        }


# ────────────────────────────────────────────────────────────────
# 검증
# ────────────────────────────────────────────────────────────────
def validate_axis_scores(axis_scores: dict[str, float]) -> None:
    missing = set(ALL_AXES) - set(axis_scores)
    if missing:
        raise ValueError(f"6축 누락: {missing}")
    for axis in ALL_AXES:
        s = axis_scores[axis]
        if s is None:
            raise ValueError(f"{axis}: None 불가")
        if not (0 <= s <= 10):
            raise ValueError(f"{axis}: 0~10 범위 벗어남 ({s})")


# ────────────────────────────────────────────────────────────────
# 코어: 단일 프로파일 H-Score
# ────────────────────────────────────────────────────────────────
def calculate_hscore(
    axis_scores: dict[str, float],
    profile: WeightProfile,
) -> HScoreResult:
    validate_axis_scores(axis_scores)
    validate_weights(profile.weights)

    contributions = []
    total = 0.0
    for axis in ALL_AXES:
        raw = axis_scores[axis]
        w = profile.weights[axis]
        contrib = raw * w / 10
        total += contrib
        contributions.append(
            AxisContribution(axis=axis, raw_score=raw, weight=w, contribution=round(contrib, 2))
        )

    hscore = round(total / profile.normalized_total() * 100, 1)
    return HScoreResult(
        hscore=hscore, profile_name=profile.name, contributions=contributions,
    )


# ────────────────────────────────────────────────────────────────
# Verdict 변환
# ────────────────────────────────────────────────────────────────
def verdict_from_score(combined: float) -> str:
    if combined >= 75:
        return "🏆 대박 유력"
    if combined >= 65:
        return "🔥 중박 이상"
    if combined >= 55:
        return "⚡ 승부처"
    if combined >= 45:
        return "❓ 다크호스"
    return "📉 난항 예상"


# ────────────────────────────────────────────────────────────────
# Triple KPI 통합
# ────────────────────────────────────────────────────────────────
def calculate_triple_kpi(
    title: str,
    axis_scores: dict[str, float],
    first_profile: Optional[WeightProfile] = None,
    avg_profile: Optional[WeightProfile] = None,
    rsi_profile: Optional[WeightProfile] = None,
) -> TripleKPIResult:
    if first_profile is None:
        first_profile = get_profile("first_ep_v2")
    if avg_profile is None:
        avg_profile = get_profile("avg_v2")
    if rsi_profile is None:
        rsi_profile = get_profile("rsi_victory_v2")

    first = calculate_hscore(axis_scores, first_profile)
    avg = calculate_hscore(axis_scores, avg_profile)
    rsi = calculate_hscore(axis_scores, rsi_profile)

    combined = round(
        first.hscore * COMBINED_WEIGHTS_V2["first_ep"]
        + avg.hscore * COMBINED_WEIGHTS_V2["avg"]
        + rsi.hscore * COMBINED_WEIGHTS_V2["rsi_victory"],
        1,
    )

    return TripleKPIResult(
        title=title,
        first_ep=first,
        avg=avg,
        rsi_victory=rsi,
        combined=combined,
        verdict=verdict_from_score(combined),
        axis_scores=axis_scores.copy(),
    )


# ────────────────────────────────────────────────────────────────
# 랭킹
# ────────────────────────────────────────────────────────────────
def rank_dramas(dramas: list[dict]) -> list[TripleKPIResult]:
    """여러 드라마를 종합 점수로 정렬.

    Args:
        dramas: [{"title": str, **axis_scores}, ...]
    """
    results = []
    for d in dramas:
        title = d.get("title", "unknown")
        scores = {axis: d[axis] for axis in ALL_AXES}
        results.append(calculate_triple_kpi(title, scores))
    return sorted(results, key=lambda r: -r.combined)
