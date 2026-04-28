"""
H-Score 가중치 프로파일
======================
Triple KPI 구조:
    1. first_ep_v2     — 첫방 시청률/오픈 반응 예측
    2. avg_v2          — 평균 시청률/롱런 예측
    3. rsi_victory_v2  — 상대우위 (동시간대 경쟁 승리 확률) 예측
    
    combined_v2        — 종합 = 첫방 30% + 평균 50% + 상대우위 20%

가중치 원천:
    - empirical_v1  : 5-method ensemble 실증 (레거시)
    - first_ep_v2   : 논문 보정 + Phase 1 업데이트
    - avg_v2        : 크리에이터 중심
    - rsi_victory_v2: 주상필(2019) 기반 relative competitiveness
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .axes import (
    AXIS_CAST, AXIS_CREATOR, AXIS_IP,
    AXIS_PLATFORM, AXIS_BUZZ, AXIS_GENRE, ALL_AXES,
)


@dataclass(frozen=True)
class WeightProfile:
    name: str
    description: str
    weights: dict[str, float]
    version: str
    source: str
    total: float = 60.0   # 기본 합계 (정규화 기준)

    def normalized_total(self) -> float:
        return sum(self.weights.values())


# ────────────────────────────────────────────────────────────────
# Profile 1: 첫방 시청률 예측 (v2)
# 논거: 배우 스타파워 + 사전 화제성 + lead-in이 첫방 좌우
# ────────────────────────────────────────────────────────────────
PROFILE_FIRST_EP_V2 = WeightProfile(
    name="first_ep_v2",
    description=(
        "첫방 시청률/오픈 반응 예측. "
        "배우 RSI, 사전 화제성, platform의 lead-in 모멘텀이 핵심."
    ),
    weights={
        AXIS_CAST: 13.0,         # 스타 파워 → 첫 진입
        AXIS_CREATOR: 7.0,       # 작가 이름값
        AXIS_IP: 5.0,            # 원작 팬덤 첫 유입
        AXIS_PLATFORM: 9.0,      # 플랫폼 + lead-in
        AXIS_BUZZ: 20.0,         # ★ 최강 (Spearman 0.91)
        AXIS_GENRE: 6.0,         # 장르 호기심
    },
    version="2.0",
    source="empirical_v1 + 주상필(2019) + Ahn(2017)",
)

# ────────────────────────────────────────────────────────────────
# Profile 2: 평균 시청률 예측 (v2)
# 논거: 크리에이터와 장르 적합도가 이탈 방지
# ────────────────────────────────────────────────────────────────
PROFILE_AVG_V2 = WeightProfile(
    name="avg_v2",
    description=(
        "평균 시청률/롱런 예측. "
        "크리에이터 파워(RSI)와 장르 적합도가 이탈 방지의 핵심."
    ),
    weights={
        AXIS_CAST: 10.0,
        AXIS_CREATOR: 15.0,      # ★ Spearman 0.87
        AXIS_IP: 9.0,            # 원작 서사 깊이
        AXIS_PLATFORM: 6.0,
        AXIS_BUZZ: 7.0,          # 초반 이후 영향 급감
        AXIS_GENRE: 13.0,        # ★ 장르 트렌드 + 계절
    },
    version="2.0",
    source="5-method ensemble + 강명현(2019) + 장르 연관규칙",
)

# ────────────────────────────────────────────────────────────────
# Profile 3: 상대우위 예측 (v2, 신규)
# 주상필(2019) 기반: 동시간대 경쟁 승리 예측
# 여기선 cast/creator RSI가 압도적으로 중요
# ────────────────────────────────────────────────────────────────
PROFILE_RSI_VICTORY_V2 = WeightProfile(
    name="rsi_victory_v2",
    description=(
        "동시간대 경쟁작 대비 상대우위 예측. "
        "주상필(2019) RSI 기반 — 배우·PD·작가 RSI가 가장 강력."
    ),
    weights={
        AXIS_CAST: 16.0,         # ★ 배우 RSI 평균
        AXIS_CREATOR: 16.0,      # ★ PD + 작가 RSI
        AXIS_IP: 6.0,
        AXIS_PLATFORM: 10.0,     # lead-in 포함
        AXIS_BUZZ: 8.0,
        AXIS_GENRE: 4.0,         # 상대비교에선 장르 영향 작음
    },
    version="2.0",
    source="주상필·홍준석·김우주(2019) 상대우위 모델",
)

# ────────────────────────────────────────────────────────────────
# 레거시 v1 (비교용, 호환 유지)
# ────────────────────────────────────────────────────────────────
PROFILE_EMPIRICAL_V1 = WeightProfile(
    name="empirical_v1",
    description="25편 5-method ensemble (레거시, 순환편향 주의)",
    weights={
        AXIS_CAST: 7.1, AXIS_CREATOR: 9.8, AXIS_IP: 2.2,
        AXIS_PLATFORM: 3.4, AXIS_BUZZ: 33.5, AXIS_GENRE: 4.0,
    },
    version="1.0",
    source="5-method ensemble",
)

# ────────────────────────────────────────────────────────────────
# 레지스트리
# ────────────────────────────────────────────────────────────────
PROFILES: dict[str, WeightProfile] = {
    "empirical_v1": PROFILE_EMPIRICAL_V1,
    "first_ep_v2": PROFILE_FIRST_EP_V2,
    "avg_v2": PROFILE_AVG_V2,
    "rsi_victory_v2": PROFILE_RSI_VICTORY_V2,
}

# 종합 점수 가중치 (3 KPI 결합)
COMBINED_WEIGHTS_V2 = {
    "first_ep": 0.30,
    "avg": 0.50,
    "rsi_victory": 0.20,
}

ProfileName = Literal[
    "empirical_v1", "first_ep_v2", "avg_v2", "rsi_victory_v2",
]


def get_profile(name: str = "avg_v2") -> WeightProfile:
    if name not in PROFILES:
        raise KeyError(f"Unknown profile: {name}. Available: {list(PROFILES)}")
    return PROFILES[name]


def validate_weights(weights: dict[str, float]) -> None:
    missing = set(ALL_AXES) - set(weights)
    if missing:
        raise ValueError(f"누락된 축: {missing}")
    extra = set(weights) - set(ALL_AXES)
    if extra:
        raise ValueError(f"알 수 없는 축: {extra}")
    for axis, w in weights.items():
        if w < 0:
            raise ValueError(f"{axis}: 가중치 음수 불가 (현재 {w})")
