"""
시간 정규화 (Temporal Normalization)
====================================
"공개일 임박 작품일수록 사전 화제성이 구조적으로 높다" 편향 보정.

원리:
    공개 2주 전 5점 > 공개 1주 전 5점 (멀수록 가치 有)
    adjusted = raw × (1 + α × log2(weeks_until_release))
    α = 0.15 (기본), 최대 10점 캡.
"""
from __future__ import annotations

import math
from datetime import date, datetime
from typing import Union

DEFAULT_ALPHA = 0.15
DEFAULT_MIN_WEEKS = 0.5

DateLike = Union[str, datetime, date]


def _parse_date(value: DateLike) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    for fmt in ("%Y.%m.%d", "%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unparseable date: {value}")


def weeks_until(
    release_date: DateLike,
    measurement_date: DateLike,
    min_weeks: float = DEFAULT_MIN_WEEKS,
) -> float:
    r = _parse_date(release_date)
    m = _parse_date(measurement_date)
    days = (r - m).days
    return max(days / 7, min_weeks)


def normalize_pre_buzz(
    raw_score: float,
    release_date: DateLike,
    measurement_date: DateLike,
    alpha: float = DEFAULT_ALPHA,
    max_score: float = 10.0,
    min_weeks: float = DEFAULT_MIN_WEEKS,
) -> float:
    if raw_score <= 0:
        return raw_score
    w = weeks_until(release_date, measurement_date, min_weeks)
    multiplier = 1 + alpha * math.log2(w)
    adjusted = raw_score * multiplier
    adjusted = min(max(adjusted, 0.0), max_score)
    return round(adjusted, 2)


def normalization_report(
    raw_score: float,
    release_date: DateLike,
    measurement_date: DateLike,
    alpha: float = DEFAULT_ALPHA,
) -> dict:
    w = weeks_until(release_date, measurement_date)
    multiplier = 1 + alpha * math.log2(w)
    adjusted = normalize_pre_buzz(raw_score, release_date, measurement_date, alpha)
    return {
        "raw_score": raw_score,
        "release_date": str(release_date),
        "measurement_date": str(measurement_date),
        "weeks_until_release": round(w, 2),
        "alpha": alpha,
        "multiplier": round(multiplier, 3),
        "adjusted_score": adjusted,
        "delta": round(adjusted - raw_score, 2),
    }
