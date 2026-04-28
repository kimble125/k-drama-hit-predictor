"""
사후 업데이트 예측 (Post-Launch Updater)
==========================================
남기환·성노윤(2018) 논문 기반: 1~5회차 방영 후 H-Score를 재산정.

단순화:
    - 논문의 시청시간 분포는 닐슨 Ariana 같은 고해상도 데이터 필요
    - 여기선 공개된 **1~3회 실제 시청률**로 사전 예측값을 베이지안 업데이트
    - posterior = prior × likelihood 형태

입력:
    - 방영 전 H-Score (prior)
    - 1~3회 실제 시청률 또는 초기 화제성 주차 데이터 (evidence)

출력:
    - 업데이트된 H-Score (v2.0 Post-Launch)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# ────────────────────────────────────────────────────────────────
# 업데이트 규칙
# ────────────────────────────────────────────────────────────────
@dataclass
class EarlyEvidence:
    """1~3회 방영 후 관찰된 증거."""
    first_ep_rating: Optional[float] = None
    ep2_rating: Optional[float] = None
    ep3_rating: Optional[float] = None
    week1_fundex: Optional[float] = None     # 1주차 펀덱스 화제성
    week2_fundex: Optional[float] = None

    def average_early_rating(self) -> Optional[float]:
        vals = [v for v in (self.first_ep_rating, self.ep2_rating, self.ep3_rating) if v is not None]
        if not vals:
            return None
        return sum(vals) / len(vals)

    def buzz_trajectory(self) -> Optional[str]:
        """펀덱스 추이 분류: 상승/유지/하락."""
        if self.week1_fundex is None or self.week2_fundex is None:
            return None
        delta = self.week2_fundex - self.week1_fundex
        if delta > self.week1_fundex * 0.15:
            return "상승"
        elif delta < -self.week1_fundex * 0.15:
            return "하락"
        else:
            return "유지"


# ────────────────────────────────────────────────────────────────
# Update formula
# ────────────────────────────────────────────────────────────────
def expected_avg_from_early_episodes(ev: EarlyEvidence) -> Optional[float]:
    """1~3회 시청률로부터 평균 시청률 기대값 추정.

    한국 드라마 경향: 평균 시청률은 첫 3회 평균의 약 1.05~1.15배.
    상승 장르는 더 오름, 로맨스 등은 유지.
    """
    early = ev.average_early_rating()
    if early is None:
        return None
    return round(early * 1.10, 2)


def update_hscore(
    prior_hscore: float,
    evidence: EarlyEvidence,
    weight_evidence: float = 0.4,
    expected_first_ep_range: tuple[float, float] = (4.0, 10.0),
) -> dict:
    """사전 H-Score를 초기 증거로 업데이트.

    단순 Bayesian-style:
        posterior = prior × (1 - α) + evidence_score × α
        where α = weight_evidence

    Args:
        prior_hscore: 방영 전 H-Score (0-100)
        evidence: 1-3회 증거
        weight_evidence: 증거 가중 (0.0=prior only, 1.0=evidence only)
        expected_first_ep_range: 첫방 기대치 하/상한 (이 범위를 100 기준으로 스케일)
    """
    early = evidence.average_early_rating()
    if early is None:
        return {
            "posterior_hscore": prior_hscore,
            "prior_hscore": prior_hscore,
            "evidence_score": None,
            "note": "No early rating data; posterior = prior",
        }

    # 시청률 → 0-100 스케일로 변환
    lo, hi = expected_first_ep_range
    evidence_score = (early - lo) / (hi - lo) * 100
    evidence_score = max(0.0, min(100.0, evidence_score))

    # 펀덱스 추이 보정
    traj = evidence.buzz_trajectory()
    if traj == "상승":
        evidence_score += 5
    elif traj == "하락":
        evidence_score -= 5
    evidence_score = max(0.0, min(100.0, evidence_score))

    posterior = prior_hscore * (1 - weight_evidence) + evidence_score * weight_evidence

    return {
        "prior_hscore": prior_hscore,
        "posterior_hscore": round(posterior, 1),
        "evidence_score": round(evidence_score, 1),
        "evidence_weight": weight_evidence,
        "early_rating_avg": early,
        "buzz_trajectory": traj,
    }


def update_verdict(posterior_hscore: float) -> str:
    """업데이트된 스코어의 전망 라벨."""
    if posterior_hscore >= 75:
        return "🏆 대박 확정화"
    if posterior_hscore >= 65:
        return "🔥 중박 안착"
    if posterior_hscore >= 55:
        return "⚡ 경쟁 구도 유지"
    if posterior_hscore >= 45:
        return "❓ 반등 여지"
    return "📉 반전 난망"
