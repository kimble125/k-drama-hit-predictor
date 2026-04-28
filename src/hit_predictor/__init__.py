"""
K-Drama Hit Predictor (v2)
===========================
논문 기반 K-드라마 흥행 예측 프레임워크 (OTT 시대 확장).

핵심 기능:
    - Triple KPI (first_ep / avg / rsi_victory)
    - RSI 자동 산출 (배우·감독·작가 필모그래피 DB 기반)
    - 시간 감쇠 가중치 (Exponential decay, 5년 이후 점진적 감쇠)
    - OTT 환산 (Netflix Top10 → 가상 TV 시청률)
    - Lead-in 효과 (직전 슬롯 드라마의 후반 25% 시청률)
    - 시간 정규화 (사전 화제성 편향 보정)
    - 사후 업데이트 예측 (Bayesian-style, 1~3회 방영 후)

논문 레퍼런스:
    - 주상필·홍준석·김우주 (2019): RSI/RSGI 도입, NB 84% 정분류율
    - 최현종·박영선·정수미·김화종 (2017): 여배우 전작 시청률, 연출자 수상수
    - 남기환·성노윤 (2018): 초기 시청시간 패턴, 75% 사후 예측력
    - Ahn et al. (2017): 빅데이터 기반 AMR/SHR 분리
    - 전익진·은혜정 (2014): 연관규칙 분석 (가을 시작 유의)
    - 강명현 (2019): 시청률 vs 가치평가지표 비동치성

사용 예시:
    >>> from hit_predictor import calculate_triple_kpi
    >>> result = calculate_triple_kpi(
    ...     title="21세기 대군부인",
    ...     axis_scores={
    ...         "cast_power": 10, "creator_power": 8, "ip_power": 2,
    ...         "platform_strategy": 7, "pre_buzz": 9, "genre_market_fit": 6,
    ...     },
    ... )
    >>> print(result.combined, result.verdict)
    74.4 🔥 중박 이상
"""
from .core import (
    calculate_hscore, calculate_triple_kpi, rank_dramas,
    TripleKPIResult, HScoreResult, verdict_from_score,
    get_profile, PROFILES, WeightProfile,
    ALL_AXES, AXIS_LABELS_KR, RUBRICS, get_rubric,
    GENRE_TAXONOMY, GENRE_TRENDS_2025,
    normalize_pre_buzz, weeks_until, normalization_report,
    get_lead_in_rating, lead_in_bonus,
)
from .rsi import (
    Person, Credit, RoleType,
    calculate_rsi, aggregate_cast_rsi,
    cast_score_from_rsi, creator_score_from_rsi,
    time_decay_weight, RSIResult,
    load_person, save_person, list_all_people,
    OTTPerformance, convert_to_virtual_rating, conversion_report,
    extract_drama_performance,
)
from .data import Drama, load_dramas_from_csv, save_dramas_to_csv
from .prediction import EarlyEvidence, update_hscore

__version__ = "2.0.0"
