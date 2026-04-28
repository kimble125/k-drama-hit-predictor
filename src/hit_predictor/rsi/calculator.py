"""
RSI (Relative Superiority Index) 계산기 v2
============================================
주상필·홍준석·김우주(2019) + 최현종 외(2017) 기반 + OTT 시대 확장.

v2 확장 (v1 대비):
    [1] 시간 감쇠 가중치 (Exponential decay)
        - 5년 이내 전작: weight = 1.0
        - 그 이후: exp(-0.15 × (years - 5))
        - 10년 전작: 0.47, 15년 전작: 0.22

    [2] OTT 환산값 통합
        - TV 시청률 없는 크레디트도 virtual_rating으로 RSI 계산 가능
        - Netflix Top10 → ott_converter.convert_to_virtual_rating()

    [3] 혼합 비교 (TV-OTT 벤치마크)
        - OTT 작품은 TV 벤치마크(6.0%) vs 환산값으로 승점
        - TV 작품은 기존 방식 유지

정의:
    RSI = Σ(wins_i × time_weight_i) / Σ(time_weight_i)
    RSGI = Σ((rating_i - competitor_avg_i) × time_weight_i) / Σ(time_weight_i)
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from .schemas import Person, Credit
from .ott_converter import OTTPerformance, convert_to_virtual_rating
from .newcomer_fallback import get_newcomer_rsi_or_none
from ..core.benchmarks import get_benchmark_for_credit

# ────────────────────────────────────────────────────────────────
# 상수
# ────────────────────────────────────────────────────────────────
DEFAULT_DECAY_RATE = 0.15
DEFAULT_FULL_WEIGHT_YEARS = 5
DEFAULT_TV_BENCHMARK = 5.5
OTT_TV_BENCHMARK = 6.0
DRAW_THRESHOLD = 0.3


# ────────────────────────────────────────────────────────────────
# 시간 감쇠 가중치
# ────────────────────────────────────────────────────────────────
def time_decay_weight(
    years_ago: float,
    full_weight_years: int = DEFAULT_FULL_WEIGHT_YEARS,
    decay_rate: float = DEFAULT_DECAY_RATE,
) -> float:
    """Exponential decay weight."""
    if years_ago < 0:
        return 1.0
    if years_ago <= full_weight_years:
        return 1.0
    return math.exp(-decay_rate * (years_ago - full_weight_years))


# ────────────────────────────────────────────────────────────────
# 결과 스키마
# ────────────────────────────────────────────────────────────────
@dataclass
class RSIResult:
    person_name: str
    role: str
    rsi: float
    rsgi: float
    n_credits: int
    n_tv: int
    n_ott: int
    effective_weight_sum: float
    award_count_5y: int
    components: dict


# ────────────────────────────────────────────────────────────────
# rating 추출 (TV 또는 OTT 환산)
# ────────────────────────────────────────────────────────────────
def get_credit_rating(
    credit: Credit,
    ott_performance: Optional[OTTPerformance] = None,
) -> tuple[Optional[float], str]:
    """크레디트에서 사용할 rating과 출처 반환."""
    if credit.avg_rating is not None:
        return credit.avg_rating, "tv"
    if ott_performance is not None:
        virtual = convert_to_virtual_rating(ott_performance)
        if virtual > 0:
            return virtual, "ott"
    return None, "none"


# ────────────────────────────────────────────────────────────────
# 메인: RSI 계산 (시간 가중 + OTT)
# ────────────────────────────────────────────────────────────────
def calculate_rsi(
    person: Person,
    ott_performance_map: Optional[dict[str, OTTPerformance]] = None,
    competitor_map: Optional[dict[str, list[Credit]]] = None,
    lookback_years: int = 15,
    until_year: Optional[int] = None,
    decay_rate: float = DEFAULT_DECAY_RATE,
    full_weight_years: int = DEFAULT_FULL_WEIGHT_YEARS,
) -> RSIResult:
    """시간 가중 RSI/RSGI 계산.

    Args:
        person: Person 객체
        ott_performance_map: {drama_title: OTTPerformance}
        competitor_map: {drama_title: [competing Credit]}
        lookback_years: 분석 총 기간 (기본 15년)
        until_year: 기준 연도
        decay_rate: exp decay λ
        full_weight_years: 풀 가중치 구간
    """
    if until_year is None:
        import datetime
        until_year = datetime.datetime.now().year

    # Step 1: role_weight > 0인 모든 크레딧 (주연/조연/특별출연/카메오 모두 포함)
    # 미루님 정책: 특별출연도 시그널을 빼지 말고 가중치만 낮춰서 반영.
    # 기존 is_lead 필드는 backward-compat: role_weight 미설정 시 is_lead로 1.0/0.5 결정.
    def _eff_role_weight(c: Credit) -> float:
        rw = getattr(c, "role_weight", None)
        if rw is not None and rw > 0:
            return rw
        # legacy: role_weight 미설정 — is_lead True면 1.0, False면 0.5
        return 1.0 if c.is_lead else 0.5

    candidates = [c for c in person.credits
                  if until_year - lookback_years <= c.year <= until_year
                  and _eff_role_weight(c) > 0]

    # Step 2: Fallback — 모든 크레딧이 필터링되어 비어 있으면 전체 필모그래피로 재시도.
    # role_weight=0인 명시적 비포함 크레딧만 있는 케이스 등.
    used_lead_filter = True
    if not candidates:
        candidates = [c for c in person.credits
                      if until_year - lookback_years <= c.year <= until_year]
        used_lead_filter = False

    if not candidates:
        # 신인 fallback: 알려진 신인이면 가산점 기반 RSI 부여 (배진아 2005 기반)
        newcomer_rsi = get_newcomer_rsi_or_none(person.name)
        if newcomer_rsi is not None:
            return RSIResult(
                person_name=person.name, role=person.primary_role,
                rsi=newcomer_rsi, rsgi=0.0, n_credits=0, n_tv=0, n_ott=0,
                effective_weight_sum=0.0,
                award_count_5y=person.award_count_5y,
                components={"note": f"Newcomer fallback (수상/검증 가산 적용, RSI={newcomer_rsi})"},
            )
        return RSIResult(
            person_name=person.name, role=person.primary_role,
            rsi=0.0, rsgi=0.0, n_credits=0, n_tv=0, n_ott=0,
            effective_weight_sum=0.0,
            award_count_5y=person.award_count_5y,
            components={"note": "No lead-role credits in lookback window"},
        )

    weighted_wins = 0.0
    weighted_gap = 0.0
    weight_sum = 0.0
    details = []
    n_tv = 0
    n_ott = 0

    for credit in candidates:
        years_ago = until_year - credit.year
        w_time = time_decay_weight(years_ago, full_weight_years, decay_rate)
        # role_weight 반영: 특별출연(0.2)·카메오(0.1)는 시그널은 살리되 가중치 낮춤.
        w_role = _eff_role_weight(credit)
        w = w_time * w_role

        ott_perf = ott_performance_map.get(credit.drama_title) if ott_performance_map else None
        own_rating, source = get_credit_rating(credit, ott_perf)
        if own_rating is None:
            details.append({
                "drama": credit.drama_title, "year": credit.year,
                "skipped": True, "reason": "No rating source",
            })
            continue

        opponent_ratings = []
        if competitor_map and credit.drama_title in competitor_map:
            opponents = competitor_map[credit.drama_title]
            opponent_ratings = [c.avg_rating for c in opponents if c.avg_rating is not None]

        if not opponent_ratings:
            if source == "ott":
                benchmark = OTT_TV_BENCHMARK
                benchmark_source = "ott_global"
            else:
                benchmark, benchmark_source = get_benchmark_for_credit(credit)
            opponent_ratings = [benchmark]
        else:
            benchmark_source = "actual_competitors"

        avg_opp = sum(opponent_ratings) / len(opponent_ratings)

        if own_rating > avg_opp + DRAW_THRESHOLD:
            win = 1.0
            outcome = "win"
        elif own_rating < avg_opp - DRAW_THRESHOLD:
            win = 0.0
            outcome = "loss"
        else:
            win = 0.5
            outcome = "draw"

        weighted_wins += win * w
        weighted_gap += (own_rating - avg_opp) * w
        weight_sum += w

        if source == "tv":
            n_tv += 1
        else:
            n_ott += 1

        details.append({
            "drama": credit.drama_title,
            "year": credit.year,
            "years_ago": years_ago,
            "time_weight": round(w_time, 3),
            "role_weight": round(w_role, 3),
            "effective_weight": round(w, 3),
            "cast_role": getattr(credit, "cast_role", None),
            "source": source,
            "own_rating": round(own_rating, 1),
            "avg_opponent_rating": round(avg_opp, 2),
            "benchmark_source": benchmark_source,
            "outcome": outcome,
        })

    if weight_sum == 0:
        return RSIResult(
            person_name=person.name, role=person.primary_role,
            rsi=0.0, rsgi=0.0, n_credits=len(candidates), n_tv=0, n_ott=0,
            effective_weight_sum=0.0,
            award_count_5y=person.award_count_5y,
            components={"note": "No valid ratings", "details": details},
        )

    rsi = weighted_wins / weight_sum
    rsgi = weighted_gap / weight_sum

    return RSIResult(
        person_name=person.name, role=person.primary_role,
        rsi=round(rsi, 3), rsgi=round(rsgi, 2),
        n_credits=n_tv + n_ott, n_tv=n_tv, n_ott=n_ott,
        effective_weight_sum=round(weight_sum, 3),
        award_count_5y=person.award_count_5y,
        components={
            "details": details,
            "decay_rate": decay_rate,
            "used_lead_filter": used_lead_filter,
        },
    )


# ────────────────────────────────────────────────────────────────
# 드라마 단위 캐스트 집계
# ────────────────────────────────────────────────────────────────
def aggregate_cast_rsi(
    actor_persons: list[Person],
    ott_performance_map: Optional[dict[str, OTTPerformance]] = None,
    competitor_map: Optional[dict] = None,
    lookback_years: int = 15,
) -> dict:
    if not actor_persons:
        return {"avg_rsi": 0.0, "max_rsi": 0.0, "n_actors": 0,
                "total_awards": 0, "individual": []}

    results = [
        calculate_rsi(p, ott_performance_map=ott_performance_map,
                      competitor_map=competitor_map, lookback_years=lookback_years)
        for p in actor_persons
    ]
    valid = [r for r in results if r.n_credits > 0]
    if not valid:
        return {
            "avg_rsi": 0.0, "max_rsi": 0.0,
            "n_actors": len(actor_persons), "total_awards": 0,
            "individual": [{"name": r.person_name, "rsi": 0.0, "n_credits": 0} for r in results],
        }

    rsis = [r.rsi for r in valid]
    return {
        "avg_rsi": round(sum(rsis) / len(rsis), 3),
        "max_rsi": round(max(rsis), 3),
        "n_actors": len(actor_persons),
        "total_awards": sum(p.award_count_5y for p in actor_persons),
        "individual": [
            {"name": r.person_name, "rsi": r.rsi, "rsgi": r.rsgi,
             "n_tv": r.n_tv, "n_ott": r.n_ott}
            for r in results
        ],
    }


# ────────────────────────────────────────────────────────────────
# 1-10 스케일 변환
# ────────────────────────────────────────────────────────────────
def cast_score_from_rsi(
    avg_rsi: float, total_awards: int = 0, n_actors: int = 0,
) -> float:
    """배우 평균 RSI + 수상 → H-Score 캐스트 파워 (1-10)."""
    base = avg_rsi * 10
    award_bonus = min(total_awards * 0.3, 1.5)
    n_actor_bonus = min(max(n_actors - 1, 0) * 0.1, 0.5)
    return round(min(base + award_bonus + n_actor_bonus, 10.0), 1)


def creator_score_from_rsi(
    director_rsi: float, writer_rsi: float,
    director_awards: int = 0, writer_awards: int = 0,
    is_repeat_collab: bool = False,
) -> float:
    """감독·작가 RSI → 크리에이터 파워 (1-10)."""
    base = (director_rsi + writer_rsi) / 2 * 10
    award_bonus = min((director_awards + writer_awards) * 0.3, 2.0)
    collab_bonus = 0.5 if is_repeat_collab else 0.0
    return round(min(base + award_bonus + collab_bonus, 10.0), 1)
