"""
채널 × 시간대별 시청률 벤치마크
================================
RSI 계산 시 "경쟁작 정보 없음" 상황에서 사용하는 벤치마크 값.
일괄 5.5%가 아니라 채널×시간대 조합별로 세분화.

이유:
    - tvN 월화 22:20: 미니시리즈 평균 3.5% → 변우석 <선재 업고 튀어> 4.1%는
      지상파 기준(5.5%)으론 '열위'지만, 실제 맥락에선 '대박 승리'
    - JTBC 토일 22:30: 2~4%대가 정상
    - SBS 금토 22:00: 7~10% 기대 슬롯

데이터 업데이트 원칙:
    1. 닐슨 주차별 CSV가 쌓이면 자동 재계산 (learn_from_nielsen)
    2. 초기값은 최근 3년 평균 기반 수기 (논문·기사·닐슨 리포트 참조)
    3. 데이터가 부족한 조합은 fallback 계층 활용:
       channel×day×time → channel×day → channel → overall

확장성:
    - 블로그에 공개 가능: "2023-2025 지상파/케이블/종편 채널별 기대 시청률 맵"
    - 미루님의 콘텐츠 데이터 분석가 포트폴리오에 직접 활용
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# ────────────────────────────────────────────────────────────────
# 초기 벤치마크 맵 (2023-2025 평균 기반 수기 값)
# 2025년 TV 시청률 전반적 하락 추세 반영
# ────────────────────────────────────────────────────────────────

# Level 1: 채널 × 요일슬롯 × 시간대 (가장 정밀)
CHANNEL_DAY_TIME_BENCHMARK: dict[tuple[str, str, str], float] = {
    # ─── 지상파 ───
    ("SBS", "금토", "22:00"): 8.5,      # 금토 드라마 프라임 (모범택시3: 16.5%)
    ("SBS", "수목", "22:00"): 5.5,
    ("SBS", "월화", "22:00"): 5.0,
    ("KBS2", "수목", "21:50"): 5.0,
    ("KBS2", "월화", "21:50"): 4.5,
    ("KBS2", "월화-금", "19:50"): 10.0,  # 일일드라마 (화려한 날들: 12.5%)
    ("MBC", "수목", "21:50"): 5.0,
    ("MBC", "월화", "21:50"): 4.5,
    ("MBC", "토일", "21:20"): 6.0,
    # ─── 케이블 ───
    ("tvN", "토일", "21:10"): 6.0,       # tvN 프라임 (보통 8-12%)
    ("tvN", "토일", "21:20"): 6.0,
    ("tvN", "수목", "22:30"): 4.0,
    ("tvN", "월화", "20:50"): 3.5,
    ("tvN", "월화", "22:20"): 3.0,       # 변우석 <선재 업고 튀어> 슬롯
    ("tvN", "월", "21:00"): 4.5,
    # ─── 종편 ───
    ("JTBC", "토일", "22:30"): 4.0,
    ("JTBC", "금토", "22:30"): 4.0,      # 박서준 <경도를 기다리며> 슬롯
    ("JTBC", "수목", "22:30"): 3.5,
    # ─── 2차 케이블·종편 ───
    ("ENA", "수목", "21:00"): 3.0,
    ("채널A", "토일", "21:10"): 2.0,
    ("TV조선", "토일", "21:50"): 4.0,
}

# Level 2: 채널 × 요일슬롯 (시간대 정보 없을 때)
CHANNEL_DAY_BENCHMARK: dict[tuple[str, str], float] = {
    ("SBS", "금토"): 8.0,
    ("SBS", "수목"): 5.5,
    ("SBS", "월화"): 5.0,
    ("KBS2", "수목"): 5.0,
    ("KBS2", "월화"): 4.5,
    ("KBS2", "토일"): 7.0,
    ("MBC", "수목"): 5.0,
    ("MBC", "월화"): 4.5,
    ("MBC", "토일"): 6.0,
    ("tvN", "토일"): 6.5,
    ("tvN", "수목"): 4.5,
    ("tvN", "월화"): 3.5,
    ("JTBC", "토일"): 4.0,
    ("JTBC", "금토"): 4.0,
    ("JTBC", "수목"): 3.5,
    ("ENA", "수목"): 3.0,
    ("ENA", "월화"): 2.5,
}

# Level 3: 채널만
CHANNEL_BENCHMARK: dict[str, float] = {
    "SBS": 6.0, "KBS1": 7.0, "KBS2": 5.0, "MBC": 4.5,
    "tvN": 5.0, "JTBC": 3.8, "ENA": 2.8,
    "채널A": 2.0, "MBN": 2.0, "TV조선": 3.5,
    "Netflix": 6.0, "Disney+": 6.0, "TVING": 5.0,
    "웨이브": 4.0, "쿠팡플레이": 4.0,
}

# Level 4: 전체 fallback
OVERALL_BENCHMARK = 5.5  # 논문 원본값 유지


# ────────────────────────────────────────────────────────────────
# 조회 함수 (Fallback 계층 활용)
# ────────────────────────────────────────────────────────────────
def get_benchmark(
    channel: Optional[str] = None,
    day_slot: Optional[str] = None,
    time_slot: Optional[str] = None,
) -> tuple[float, str]:
    """채널×요일×시간대 조합에 맞는 벤치마크 반환.

    Returns:
        (benchmark_value, source) 튜플.
        source는 'level1', 'level2', 'level3', 'overall' 중 하나.
    """
    if channel and day_slot and time_slot:
        key = (channel, day_slot, time_slot)
        if key in CHANNEL_DAY_TIME_BENCHMARK:
            return CHANNEL_DAY_TIME_BENCHMARK[key], "level1"
    if channel and day_slot:
        key = (channel, day_slot)
        if key in CHANNEL_DAY_BENCHMARK:
            return CHANNEL_DAY_BENCHMARK[key], "level2"
    if channel and channel in CHANNEL_BENCHMARK:
        return CHANNEL_BENCHMARK[channel], "level3"
    return OVERALL_BENCHMARK, "overall"


def get_benchmark_for_credit(credit) -> tuple[float, str]:
    """Credit 객체로부터 벤치마크 조회."""
    return get_benchmark(
        channel=credit.channel,
        day_slot=credit.day_slot,
        time_slot=credit.time_slot,
    )


# ────────────────────────────────────────────────────────────────
# 닐슨 데이터로 자동 학습 (데이터 쌓이면)
# ────────────────────────────────────────────────────────────────
def learn_from_nielsen(
    nielsen_history_df,
    min_samples_per_key: int = 10,
) -> dict:
    """닐슨 히스토리 DataFrame에서 채널×시간대 평균을 자동 산출.

    Args:
        nielsen_history_df: pandas DataFrame
            필수 컬럼: channel, metric_value (시청률 %)
            선택: day_slot, time_slot
        min_samples_per_key: 학습에 필요한 최소 관측치 수

    Returns:
        {"level1": {...}, "level2": {...}, "level3": {...}} 형태 딕셔너리
    """
    import pandas as pd

    if nielsen_history_df.empty:
        return {}

    df = nielsen_history_df[nielsen_history_df["metric_type"] == "household_rating"]
    df = df[df["metric_value"].notna()]

    result = {"level1": {}, "level2": {}, "level3": {}}

    # Level 3: 채널만
    for ch, grp in df.groupby("channel"):
        if len(grp) >= min_samples_per_key:
            result["level3"][ch] = round(grp["metric_value"].mean(), 2)

    # Level 1, 2: day_slot / time_slot 컬럼 있을 때만
    if "day_slot" in df.columns and "time_slot" in df.columns:
        for (ch, day, time), grp in df.groupby(["channel", "day_slot", "time_slot"]):
            if len(grp) >= min_samples_per_key:
                result["level1"][f"{ch}|{day}|{time}"] = round(grp["metric_value"].mean(), 2)
        for (ch, day), grp in df.groupby(["channel", "day_slot"]):
            if len(grp) >= min_samples_per_key:
                result["level2"][f"{ch}|{day}"] = round(grp["metric_value"].mean(), 2)

    return result


def save_learned_benchmarks(
    learned: dict,
    out_path: Path = Path("data/benchmarks_learned.json"),
) -> None:
    """학습된 벤치마크를 JSON으로 저장."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(learned, f, ensure_ascii=False, indent=2)


def load_learned_benchmarks(
    path: Path = Path("data/benchmarks_learned.json"),
) -> dict:
    """저장된 학습 벤치마크 로드."""
    path = Path(path)
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def apply_learned_benchmarks(learned: dict) -> int:
    """학습된 벤치마크를 전역 맵에 반영. 반환: 업데이트된 항목 수."""
    count = 0
    for key_str, value in learned.get("level1", {}).items():
        parts = key_str.split("|")
        if len(parts) == 3:
            CHANNEL_DAY_TIME_BENCHMARK[tuple(parts)] = value
            count += 1
    for key_str, value in learned.get("level2", {}).items():
        parts = key_str.split("|")
        if len(parts) == 2:
            CHANNEL_DAY_BENCHMARK[tuple(parts)] = value
            count += 1
    for ch, value in learned.get("level3", {}).items():
        CHANNEL_BENCHMARK[ch] = value
        count += 1
    return count


# ────────────────────────────────────────────────────────────────
# 디버깅: 현재 벤치마크 맵 요약 출력
# ────────────────────────────────────────────────────────────────
def print_benchmark_summary() -> None:
    """현재 설정된 벤치마크 맵을 사람이 읽기 좋게 출력."""
    print("\n채널×요일×시간대 벤치마크 (Level 1):")
    for (ch, day, time), v in sorted(CHANNEL_DAY_TIME_BENCHMARK.items()):
        print(f"  {ch:6s} {day:6s} {time:6s} → {v:5.2f}%")
    print(f"\n채널×요일 (Level 2): {len(CHANNEL_DAY_BENCHMARK)}개 항목")
    print(f"채널만 (Level 3): {len(CHANNEL_BENCHMARK)}개 항목")
    print(f"전체 Fallback: {OVERALL_BENCHMARK}%")
