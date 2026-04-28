"""
드라마 데이터 스키마
===================
확장 스키마: RSI 자동 산출용 필드 + 결측치 사유 분기 포함.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional


class MissingReason(str, Enum):
    """결측치 사유 분류 — 사유에 따라 fallback 정책이 분기됨.

    미루님 정책: '원인을 모르는' 결측치는 결측치대로 두고 원인 파악 후 해결.
    '원인을 아는' 결측치만 fallback 적용.
    """
    # ─── 알려진 사유: fallback 적용됨 ───
    APPLIED_ROOKIE_FALLBACK = "applied_rookie_fallback"  # 신인 → 신인 fallback 적용

    # ─── 수집 실패: 재시도 또는 보완 필요 ───
    TMDB_SEARCH_FAILED = "tmdb_search_failed"            # TMDB 인물/작품 검색 실패
    WIKIPEDIA_NOT_FOUND = "wikipedia_not_found"          # 위키백과에 페이지 없음
    NAMUWIKI_NOT_FOUND = "namuwiki_not_found"            # 나무위키에 페이지 없음
    PUNDEX_UNAVAILABLE = "pundex_unavailable"            # 펀덱스 리포트 입수 실패
    NIELSEN_UNAVAILABLE = "nielsen_unavailable"          # 닐슨 시청률 입수 실패

    # ─── 모호함: 확정 불가 ───
    HOMONYM_CONFLICT = "homonym_conflict"                # 동명이인으로 인물 식별 실패
    SOURCE_DISAGREEMENT = "source_disagreement"          # 다중 소스가 서로 다른 값 제시

    # ─── 운영: 의도적 결측 ───
    DATA_COLLECTION_SKIPPED = "data_collection_skipped"  # 의도적으로 수집 건너뜀
    NOT_IN_ANY_SOURCE = "not_in_any_source"              # 어느 소스에도 정보 없음(확인 필요)
    NOT_YET_AIRED = "not_yet_aired"                      # 미방영 — 시청률 등은 자연 결측


@dataclass
class Drama:
    title: str
    # ─── 6축 점수 (0~10) ───
    cast_power: Optional[float] = None
    creator_power: Optional[float] = None
    ip_power: Optional[float] = None
    platform_strategy: Optional[float] = None
    pre_buzz: Optional[float] = None
    genre_market_fit: Optional[float] = None

    # ─── 원본 값 (정규화 전) ───
    pre_buzz_raw: Optional[float] = None

    # ─── RSI 원시 값 (자동산출 기반) ───
    actor_rsi_avg: Optional[float] = None
    director_rsi: Optional[float] = None
    writer_rsi: Optional[float] = None
    lead_actors: Optional[str] = None       # ","로 구분
    director: Optional[str] = None
    writer: Optional[str] = None

    # ─── 메타데이터 ───
    platform: Optional[str] = None
    channel: Optional[str] = None
    day_slot: Optional[str] = None           # "월화", "금토" 등
    time_slot: Optional[str] = None          # "22:00"
    genre: Optional[str] = None
    genre_key: Optional[str] = None          # GENRE_TAXONOMY 키
    release_date: Optional[str] = None
    episodes: Optional[int] = None
    year: Optional[int] = None
    has_ip: Optional[bool] = None
    season_number: Optional[int] = None      # 시즌 2/3 등

    # ─── Lead-in 관련 ───
    prev_slot_final_rating: Optional[float] = None

    # ─── 실제 성적 (calibration 및 사후) ───
    actual_first_rating: Optional[float] = None
    actual_avg_rating: Optional[float] = None
    actual_max_rating: Optional[float] = None
    fundex_grade: Optional[str] = None
    fundex_weekly_avg: Optional[float] = None

    # ─── 수상 ───
    total_awards_5y: Optional[int] = None

    notes: Optional[str] = None

    # ─── 결측치 사유 추적 (필드명 → MissingReason 값) ───
    # 예: {"director": "namuwiki_not_found", "writer": "source_disagreement"}
    # CSV 출력 시에는 별도 *_quality.json으로 저장하여 flat CSV 호환 유지.
    data_quality: dict[str, str] = field(default_factory=dict)

    # ─── 데이터 출처 추적 (필드명 → 소스명) ───
    # 예: {"lead_actors": "namuwiki", "channel": "wikipedia", "release_date": "tmdb"}
    field_sources: dict[str, str] = field(default_factory=dict)

    def axis_scores(self) -> dict[str, float]:
        return {
            "cast_power": self.cast_power or 0,
            "creator_power": self.creator_power or 0,
            "ip_power": self.ip_power or 0,
            "platform_strategy": self.platform_strategy or 0,
            "pre_buzz": self.pre_buzz or 0,
            "genre_market_fit": self.genre_market_fit or 0,
        }

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Drama":
        valid = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in d.items() if k in valid}
        return cls(**filtered)
