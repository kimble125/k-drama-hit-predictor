"""
OTT 환산 모듈 (Netflix Top10 → Virtual TV Rating)
==================================================
Netflix 공식 주간 Top10 데이터를 지상파 TV 시청률 등가치로 환산.

논거:
    주상필(2019), 최현종(2017) 논문의 RSI/RSGI는 TV 시청률 기반이라
    OTT 오리지널 드라마에 적용 불가. 이 모듈은 OTT 지표를 TV 시청률로
    환산해 기존 논문 방법론을 OTT 시대로 확장함.

공식 (v1, rank × duration × region, 상한 35):
    virtual_rating = base_rank_score × duration_factor × region_factor
    max = 35.0  # 오징어 게임급 상한

    base_rank_score (국가별 Top10 기준):
        Rank  1:       15.0  (지상파 히트급)
        Rank  2-3:     10.0
        Rank  4-7:      7.0
        Rank  8-10:     5.0
        Top10 미진입:    0.0

    duration_factor (cumulative_weeks_in_top_10):
        1주:       1.0
        2-3주:     1.3
        4-7주:     1.7
        8주+:      2.0

    region_factor:
        한국 Top10만:        1.0
        한국+글로벌 Top10:   1.3

데이터 소스:
    https://www.netflix.com/tudum/top10/data/all-weeks-countries.xlsx (국가별)
    https://www.netflix.com/tudum/top10/data/all-weeks-global.xlsx     (글로벌)
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# ────────────────────────────────────────────────────────────────
# 상수
# ────────────────────────────────────────────────────────────────
VIRTUAL_RATING_MAX = 35.0

DEFAULT_COUNTRY_CACHE = Path("data/netflix_top10/all-weeks-countries.xlsx")
DEFAULT_GLOBAL_CACHE = Path("data/netflix_top10/all-weeks-global.xlsx")


# ────────────────────────────────────────────────────────────────
# 공식 구현
# ────────────────────────────────────────────────────────────────
def base_rank_score(rank: Optional[int]) -> float:
    """Top10 순위를 기본 점수로 변환."""
    if rank is None or rank < 1 or rank > 10:
        return 0.0
    if rank == 1:
        return 15.0
    if rank <= 3:
        return 10.0
    if rank <= 7:
        return 7.0
    return 5.0  # 8~10위


def duration_factor(weeks_in_top10: Optional[int]) -> float:
    """Top10 체류 주수별 승수."""
    if weeks_in_top10 is None or weeks_in_top10 <= 0:
        return 0.0
    if weeks_in_top10 == 1:
        return 1.0
    if weeks_in_top10 <= 3:
        return 1.3
    if weeks_in_top10 <= 7:
        return 1.7
    return 2.0  # 8주+


def region_factor(in_country_top10: bool, in_global_top10: bool) -> float:
    """국가별/글로벌 Top10 진입 여부에 따른 승수."""
    if in_country_top10 and in_global_top10:
        return 1.3
    if in_country_top10 or in_global_top10:
        return 1.0
    return 0.0


# ────────────────────────────────────────────────────────────────
# 최상위 환산 함수
# ────────────────────────────────────────────────────────────────
@dataclass
class OTTPerformance:
    """한 OTT 작품의 환산 입력 정보."""
    title: str
    best_rank_kr: Optional[int] = None         # 한국 Top10 최고 순위
    best_rank_global: Optional[int] = None     # 글로벌 Top10 최고 순위
    weeks_in_top10_kr: Optional[int] = None    # 한국 누적 체류 주수
    weeks_in_top10_global: Optional[int] = None
    notes: str = ""


def convert_to_virtual_rating(perf: OTTPerformance) -> float:
    """OTT 성과를 가상 TV 시청률(%)로 환산.

    Args:
        perf: OTTPerformance

    Returns:
        가상 TV 시청률 (0.0 ~ 35.0). 소수점 1자리 반올림.
    """
    # 국가/글로벌 중 더 높은 rank와 긴 체류를 반영 (상한 규칙 내에서)
    ranks = [r for r in (perf.best_rank_kr, perf.best_rank_global) if r is not None]
    best_rank = min(ranks) if ranks else None

    weeks = [w for w in (perf.weeks_in_top10_kr, perf.weeks_in_top10_global) if w is not None]
    max_weeks = max(weeks) if weeks else None

    base = base_rank_score(best_rank)
    dur = duration_factor(max_weeks)
    reg = region_factor(
        in_country_top10=perf.best_rank_kr is not None and perf.best_rank_kr <= 10,
        in_global_top10=perf.best_rank_global is not None and perf.best_rank_global <= 10,
    )

    raw = base * dur * reg
    return round(min(raw, VIRTUAL_RATING_MAX), 1)


def conversion_report(perf: OTTPerformance) -> dict:
    """디버깅용: 환산 과정 단계별 설명."""
    ranks = [r for r in (perf.best_rank_kr, perf.best_rank_global) if r is not None]
    best_rank = min(ranks) if ranks else None

    weeks = [w for w in (perf.weeks_in_top10_kr, perf.weeks_in_top10_global) if w is not None]
    max_weeks = max(weeks) if weeks else None

    base = base_rank_score(best_rank)
    dur = duration_factor(max_weeks)
    reg = region_factor(
        in_country_top10=perf.best_rank_kr is not None and perf.best_rank_kr <= 10,
        in_global_top10=perf.best_rank_global is not None and perf.best_rank_global <= 10,
    )
    virtual = convert_to_virtual_rating(perf)

    return {
        "title": perf.title,
        "best_rank_used": best_rank,
        "max_weeks_used": max_weeks,
        "base_rank_score": base,
        "duration_factor": dur,
        "region_factor": reg,
        "raw_product": round(base * dur * reg, 2),
        "virtual_rating": virtual,
        "capped_at_max": (base * dur * reg) > VIRTUAL_RATING_MAX,
    }


# ────────────────────────────────────────────────────────────────
# Netflix XLSX 파일에서 특정 드라마 정보 추출
# ────────────────────────────────────────────────────────────────
def extract_drama_performance(
    drama_title: str,
    countries_xlsx: Path = DEFAULT_COUNTRY_CACHE,
    global_xlsx: Path = DEFAULT_GLOBAL_CACHE,
    country_iso2: str = "KR",
) -> Optional[OTTPerformance]:
    """Netflix 공식 XLSX에서 특정 드라마의 성과 추출.

    Returns:
        OTTPerformance 또는 None (파일 없음/드라마 미등록).
    """
    import pandas as pd

    countries_xlsx = Path(countries_xlsx)
    global_xlsx = Path(global_xlsx)

    best_rank_kr = None
    weeks_kr = None
    best_rank_global = None
    weeks_global = None

    # 국가별 데이터
    if countries_xlsx.exists():
        try:
            df_c = pd.read_excel(countries_xlsx)
            df_c.columns = [c.lower().strip() for c in df_c.columns]
            # 제목 컬럼: show_title 우선, 없으면 다른 후보
            title_col = None
            for cand in ("show_title", "title", "season_title"):
                if cand in df_c.columns:
                    title_col = cand
                    break
            if title_col:
                kr_df = df_c[
                    (df_c.get("country_iso2", df_c.get("country_name", "")) == country_iso2)
                    & (df_c[title_col].astype(str).str.contains(drama_title, case=False, na=False))
                ]
                if not kr_df.empty:
                    rank_col = next((c for c in ("weekly_rank", "rank") if c in kr_df.columns), None)
                    weeks_col = next(
                        (c for c in ("cumulative_weeks_in_top_10", "weeks_in_top10")
                         if c in kr_df.columns), None,
                    )
                    if rank_col:
                        best_rank_kr = int(kr_df[rank_col].min())
                    if weeks_col:
                        weeks_kr = int(kr_df[weeks_col].max())
        except Exception as e:
            print(f"[WARN] 국가별 XLSX 파싱 실패: {e}")

    # 글로벌 데이터
    if global_xlsx.exists():
        try:
            df_g = pd.read_excel(global_xlsx)
            df_g.columns = [c.lower().strip() for c in df_g.columns]
            title_col = next((c for c in ("show_title", "title", "season_title")
                              if c in df_g.columns), None)
            if title_col:
                g_df = df_g[df_g[title_col].astype(str).str.contains(drama_title, case=False, na=False)]
                if not g_df.empty:
                    rank_col = next((c for c in ("weekly_rank", "rank") if c in g_df.columns), None)
                    weeks_col = next(
                        (c for c in ("cumulative_weeks_in_top_10", "weeks_in_top10")
                         if c in g_df.columns), None,
                    )
                    if rank_col:
                        best_rank_global = int(g_df[rank_col].min())
                    if weeks_col:
                        weeks_global = int(g_df[weeks_col].max())
        except Exception as e:
            print(f"[WARN] 글로벌 XLSX 파싱 실패: {e}")

    if best_rank_kr is None and best_rank_global is None:
        return None

    return OTTPerformance(
        title=drama_title,
        best_rank_kr=best_rank_kr,
        best_rank_global=best_rank_global,
        weeks_in_top10_kr=weeks_kr,
        weeks_in_top10_global=weeks_global,
    )
