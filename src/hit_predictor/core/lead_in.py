"""
Lead-in Effect (슬롯 모멘텀)
===========================
같은 편성 시간대에서 직전에 방영된 드라마의 후반 25% 회차 평균 시청률을
새 드라마의 첫방 유입 예측 지표로 사용.

논거:
    - 최현종 외(2017): '이전 드라마 후반 25%' 가장 강력한 설명변수 중 하나
    - 주상필 외(2019): 이 변수를 Naive Bayes 모델에 결합 → 정분류율 0.84

한계:
    - OTT 오리지널은 고정 슬롯이 없어 적용 불가 → None 반환
    - 닐슨 CSV 데이터가 누적되어 있어야 조회 가능
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional
import math

import pandas as pd

# ────────────────────────────────────────────────────────────────
# 슬롯 식별자
# ────────────────────────────────────────────────────────────────
# Slot key: (channel, day_slot, time_slot)
# 예: ("SBS", "금토", "22:00")
SlotKey = tuple[str, str, str]


def load_nielsen_history(nielsen_dir: Path) -> pd.DataFrame:
    """data/nielsen_weekly/*.csv 전체를 하나의 DataFrame으로 로드."""
    nielsen_dir = Path(nielsen_dir)
    csv_files = sorted(nielsen_dir.glob("*.csv"))
    if not csv_files:
        return pd.DataFrame()
    dfs = []
    for f in csv_files:
        try:
            df = pd.read_csv(f, encoding="utf-8-sig")
            dfs.append(df)
        except Exception as e:
            print(f"[WARN] Skip {f}: {e}")
    if not dfs:
        return pd.DataFrame()
    return pd.concat(dfs, ignore_index=True)


def find_previous_drama(
    history: pd.DataFrame,
    slot: SlotKey,
    before_date: str,
) -> Optional[str]:
    """닐슨 히스토리에서 해당 슬롯의 직전 드라마 제목 찾기.

    매우 단순화: 같은 채널(channel)에서 before_date 이전에 랭킹에 등장했던
    가장 최근 프로그램. day_slot/time_slot은 닐슨 CSV 스키마에 포함되지
    않아 채널 기준으로만 조회.
    """
    if history.empty:
        return None

    channel, _, _ = slot
    if "channel" not in history.columns or "program" not in history.columns:
        return None

    # before_date 이전 데이터만
    if "week_end" in history.columns:
        mask = (history["channel"] == channel) & (history["week_end"] < before_date)
        subset = history[mask]
    else:
        subset = history[history["channel"] == channel]

    if subset.empty:
        return None

    # 가장 최근 주차의 1위 프로그램
    latest = subset.sort_values("week_end", ascending=False).iloc[0]
    return str(latest.get("program", ""))


def calculate_last_quarter_rating(
    history: pd.DataFrame,
    drama_title: str,
) -> Optional[float]:
    """특정 드라마의 후반 25% 회차 평균 시청률.

    닐슨 주차별 데이터에서 해당 드라마가 랭크인된 주차들의
    뒤쪽 25%만 평균.
    """
    if history.empty or "program" not in history.columns:
        return None
    subset = history[history["program"] == drama_title]
    if subset.empty or "metric_value" not in subset.columns:
        return None

    # 시청률 타입만 필터 (metric_type이 있으면)
    if "metric_type" in subset.columns:
        subset = subset[subset["metric_type"] == "household_rating"]

    if subset.empty:
        return None

    # 주차 순서대로 정렬
    if "week_end" in subset.columns:
        subset = subset.sort_values("week_end")

    ratings = subset["metric_value"].dropna().tolist()
    if len(ratings) < 2:
        return None

    # 뒤 25% (최소 1개)
    n_last = max(1, math.ceil(len(ratings) * 0.25))
    last_quarter = ratings[-n_last:]
    return round(sum(last_quarter) / len(last_quarter), 2)


# ────────────────────────────────────────────────────────────────
# 상위 API: 슬롯 → lead-in 점수
# ────────────────────────────────────────────────────────────────
def get_lead_in_rating(
    channel: str,
    day_slot: str,
    time_slot: str,
    before_date: str,
    nielsen_dir: Path = Path("data/nielsen_weekly"),
) -> Optional[float]:
    """새 드라마의 슬롯 lead-in 시청률을 반환. OTT는 None."""
    if channel in {"Netflix", "Disney+", "TVING", "웨이브", "쿠팡플레이", "Wavve"}:
        return None

    history = load_nielsen_history(nielsen_dir)
    if history.empty:
        return None

    prev = find_previous_drama(history, (channel, day_slot, time_slot), before_date)
    if not prev:
        return None

    return calculate_last_quarter_rating(history, prev)


def lead_in_bonus(rating: Optional[float]) -> float:
    """Lead-in 시청률을 platform_strategy 축 가산점(0.0~2.0)으로 변환.

    15%+ → +2.0 (강한 슬롯)
    10-15% → +1.5
    5-10% → +1.0
    3-5% → +0.5
    <3% 또는 None → 0.0
    """
    if rating is None:
        return 0.0
    if rating >= 15:
        return 2.0
    if rating >= 10:
        return 1.5
    if rating >= 5:
        return 1.0
    if rating >= 3:
        return 0.5
    return 0.0
