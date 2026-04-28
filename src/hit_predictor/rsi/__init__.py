"""RSI (Relative Superiority Index) 모듈 v2."""
from .schemas import Person, Credit, RoleType
from .calculator import (
    calculate_rsi,
    aggregate_cast_rsi,
    cast_score_from_rsi,
    creator_score_from_rsi,
    time_decay_weight,
    get_credit_rating,
    RSIResult,
    DEFAULT_DECAY_RATE,
    DEFAULT_FULL_WEIGHT_YEARS,
)
from .storage import (
    load_person, save_person, list_all_people,
    load_many, create_placeholder,
)
from .ott_converter import (
    OTTPerformance,
    convert_to_virtual_rating,
    conversion_report,
    base_rank_score,
    duration_factor,
    region_factor,
    extract_drama_performance,
    VIRTUAL_RATING_MAX,
)

__all__ = [
    "Person", "Credit", "RoleType",
    "calculate_rsi", "aggregate_cast_rsi",
    "cast_score_from_rsi", "creator_score_from_rsi",
    "time_decay_weight", "get_credit_rating",
    "RSIResult", "DEFAULT_DECAY_RATE", "DEFAULT_FULL_WEIGHT_YEARS",
    "load_person", "save_person", "list_all_people",
    "load_many", "create_placeholder",
    "OTTPerformance", "convert_to_virtual_rating", "conversion_report",
    "base_rank_score", "duration_factor", "region_factor",
    "extract_drama_performance", "VIRTUAL_RATING_MAX",
]
