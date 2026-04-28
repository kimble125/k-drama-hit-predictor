"""Core H-Score 엔진."""
from .axes import (
    ALL_AXES, AXIS_LABELS_KR, RUBRICS, get_rubric,
    GENRE_TAXONOMY, GENRE_TRENDS_2025, get_genre_trend,
    AXIS_CAST, AXIS_CREATOR, AXIS_IP, AXIS_PLATFORM, AXIS_BUZZ, AXIS_GENRE,
)
from .weights import (
    PROFILES, get_profile, validate_weights, WeightProfile,
    COMBINED_WEIGHTS_V2,
)
from .temporal import (
    normalize_pre_buzz, weeks_until, normalization_report,
    DEFAULT_ALPHA,
)
from .hscore import (
    calculate_hscore, calculate_triple_kpi, rank_dramas,
    HScoreResult, TripleKPIResult, AxisContribution, verdict_from_score,
)
from .lead_in import (
    get_lead_in_rating, lead_in_bonus,
    load_nielsen_history,
)

__all__ = [
    "ALL_AXES", "AXIS_LABELS_KR", "RUBRICS", "get_rubric",
    "GENRE_TAXONOMY", "GENRE_TRENDS_2025", "get_genre_trend",
    "AXIS_CAST", "AXIS_CREATOR", "AXIS_IP",
    "AXIS_PLATFORM", "AXIS_BUZZ", "AXIS_GENRE",
    "PROFILES", "get_profile", "validate_weights", "WeightProfile",
    "COMBINED_WEIGHTS_V2",
    "normalize_pre_buzz", "weeks_until", "normalization_report",
    "DEFAULT_ALPHA",
    "calculate_hscore", "calculate_triple_kpi", "rank_dramas",
    "HScoreResult", "TripleKPIResult", "AxisContribution", "verdict_from_score",
    "get_lead_in_rating", "lead_in_bonus", "load_nielsen_history",
]
