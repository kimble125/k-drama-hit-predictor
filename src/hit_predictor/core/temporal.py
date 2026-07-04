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


def calculate_youtube_buzz(
    views: int,
    likes: int,
    comments: int,
    days_elapsed: float,
) -> float:
    """유튜브 예고편 지표(조회수, 좋아요, 댓글수)를 정규화하여 1.0~10.0점 사이의 raw 화제성 점수 산출.

    공식:
    raw_score = 0.5 * log10(views + 1) + 0.3 * log10(likes * 10 + 1) + 0.2 * log10(comments * 100 + 1)

    업로드 경과일(days_elapsed) 보정 가중치:
    - 지수 감쇄 모델(미분적 감쇄): w_time = 1.0 + 0.2 * exp(-0.15 * max(0.0, days_elapsed))
      (업로드 극초반에는 조회수 증가율이 높으므로 가산 가중치 적용, 시간이 흐를수록 1.0으로 수렴)

    최종 10점 캡 적용.
    """
    if views <= 0:
        return 0.0

    # 로그 기반 원본 점수 계산
    v_term = 0.5 * math.log10(views + 1)
    l_term = 0.3 * math.log10(likes * 10 + 1)
    c_term = 0.2 * math.log10(comments * 100 + 1)
    raw = v_term + l_term + c_term

    # 경과일 보정 가중치 (지수 감쇄 적용)
    w_time = 1.0
    if days_elapsed > 0:
        w_time = 1.0 + 0.2 * math.exp(-0.15 * max(0.0, days_elapsed))

    adjusted = raw * w_time
    # 1.0 ~ 10.0 범위로 제한
    adjusted = min(max(adjusted, 1.0), 10.0)
    return round(adjusted, 2)
