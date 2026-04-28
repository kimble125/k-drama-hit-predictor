"""
H-Score 6축 정의
================
각 축은 1~10점 스케일. 각 축은 내부적으로 여러 subfield를 가지며,
자동 산출(RSI 기반) 또는 사용자 선언(manual) 방식으로 점수가 부여됩니다.

축 목록:
    1. cast_power         — 캐스트 파워 (배우 RSI + 수상 + SNS)
    2. creator_power      — 크리에이터 파워 (감독 RSI + 작가 RSI + 수상)
    3. ip_power           — IP/원작 파워
    4. platform_strategy  — 플랫폼 전략 (플랫폼 + lead-in + 글로벌 공개)
    5. pre_buzz           — 사전 화제성 (시간 정규화 적용)
    6. genre_market_fit   — 장르·시장 적합도
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

# ────────────────────────────────────────────────────────────────
# 축 상수
# ────────────────────────────────────────────────────────────────
AXIS_CAST = "cast_power"
AXIS_CREATOR = "creator_power"
AXIS_IP = "ip_power"
AXIS_PLATFORM = "platform_strategy"
AXIS_BUZZ = "pre_buzz"
AXIS_GENRE = "genre_market_fit"

ALL_AXES: tuple[str, ...] = (
    AXIS_CAST,
    AXIS_CREATOR,
    AXIS_IP,
    AXIS_PLATFORM,
    AXIS_BUZZ,
    AXIS_GENRE,
)

AXIS_LABELS_KR: dict[str, str] = {
    AXIS_CAST: "캐스트 파워",
    AXIS_CREATOR: "크리에이터 파워",
    AXIS_IP: "IP/원작 파워",
    AXIS_PLATFORM: "플랫폼 전략",
    AXIS_BUZZ: "사전 화제성",
    AXIS_GENRE: "장르·시장 적합도",
}


# ────────────────────────────────────────────────────────────────
# 점수 산출 방식
# ────────────────────────────────────────────────────────────────
ScoreSource = Literal["auto", "manual", "mixed"]
# auto: RSI/DB 자동산출  |  manual: 사용자 선언  |  mixed: auto + manual 가중평균


# ────────────────────────────────────────────────────────────────
# 장르 표준 분류 (주창윤 2004 + 의학 + 현대)
# ────────────────────────────────────────────────────────────────
GENRE_TAXONOMY = {
    "melo": "멜로드라마",
    "home": "홈드라마",
    "romantic": "로맨틱드라마",
    "historical": "사극",
    "police": "범죄·수사",
    "legal": "법률",
    "docu": "다큐드라마",
    "action": "무협·액션",
    "school": "학교",
    "country": "전원",
    "medical": "의학",
    "thriller": "스릴러",
    "fantasy": "판타지",
    "mystery": "미스터리",
    "comedy": "코미디",
    "human": "휴먼",
    "office": "오피스",
    "horror": "호러",
    "scifi": "SF",
}


# ────────────────────────────────────────────────────────────────
# 장르 트렌드 (2025 기준, 펀덱스 FUNdex 리포트 + 논문 참조)
# 값: 1.0 = 안정, >1.0 = 상승세, <1.0 = 하락세
# ────────────────────────────────────────────────────────────────
GENRE_TRENDS_2025: dict[str, float] = {
    "melo": 0.80,       # TV 로맨스 위기 (FUNdex p.12)
    "romantic": 0.85,
    "home": 0.95,
    "historical": 1.05,
    "police": 1.15,     # 강세
    "legal": 1.10,
    "thriller": 1.15,   # 강세
    "mystery": 1.10,
    "action": 1.05,
    "medical": 1.00,
    "human": 1.00,
    "comedy": 0.95,
    "office": 0.95,
    "fantasy": 1.00,
    "scifi": 1.05,
    "horror": 1.05,     # Netflix 신선
    "school": 0.90,
    "docu": 0.95,
    "country": 0.85,
}


# ────────────────────────────────────────────────────────────────
# Rubric 정의
# ────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class AxisRubric:
    name: str
    label_kr: str
    description: str
    components: tuple[str, ...]
    auto_calculable: bool   # Phase 1: RSI 등으로 자동 산출 가능 여부
    scoring_guide: dict[int, str]
    rationale: str


RUBRICS: dict[str, AxisRubric] = {
    AXIS_CAST: AxisRubric(
        name=AXIS_CAST,
        label_kr="캐스트 파워",
        description="주연 배우들의 과거 실적·수상·SNS 영향력",
        components=(
            "주연 4명의 배우 RSI 평균 (최근 5년)",
            "최근 5년 수상 횟수 (백상·APAN 등)",
            "SNS 팔로워 (인스타그램, 보조 지표)",
        ),
        auto_calculable=True,
        scoring_guide={
            10: "메가스타 2+ (RSI 0.85+, 수상 3+)",
            9:  "메가스타 1 + A급 1",
            8:  "A급 2+ (RSI 0.70+)",
            7:  "A급 1 + 중견 (RSI 0.60+)",
            6:  "중견 2-3 (RSI 0.50)",
            5:  "중견 평균",
            4:  "라이징",
            3:  "신인급",
            2:  "비공개/무명",
            1:  "정보 부재",
        },
        rationale="배우 RSI ↔ 첫방 시청률 Spearman 0.76 (실증).",
    ),

    AXIS_CREATOR: AxisRubric(
        name=AXIS_CREATOR,
        label_kr="크리에이터 파워",
        description="감독·작가의 과거 실적과 협업 이력",
        components=(
            "감독 RSI (최근 5년 연출작 상대우위)",
            "작가 RSI (최근 5년 극본작 상대우위)",
            "수상 이력 (백상 연출상·작가상 등)",
            "연속 협업 보너스 (같은 팀 재결합)",
        ),
        auto_calculable=True,
        scoring_guide={
            10: "스타 감독+스타 작가 (김은숙·박지은 급)",
            9:  "검증된 조합 (유인식·박재범 등)",
            8:  "히트작 보유 (환혼·우영우 연출/극본)",
            7:  "중견, 전작 평균 이상",
            6:  "경험 있으나 히트 부재",
            5:  "중견 평균",
            4:  "신인 감독 또는 작가 단독",
            3:  "극본공모 당선 신인",
            2:  "정보 부재",
            1:  "검증 불가",
        },
        rationale="크리에이터 RSI ↔ 평균 시청률 Spearman 0.87 (최강 변수).",
    ),

    AXIS_IP: AxisRubric(
        name=AXIS_IP,
        label_kr="IP/원작 파워",
        description="원작의 팬덤 규모·검증도",
        components=(
            "원작 유무·유형",
            "원작 조회수·별점",
            "시즌 이력 (시즌2+ 가산)",
            "번역/수상 이력",
        ),
        auto_calculable=False,   # 원작 정보 DB 필요 (향후 자동화)
        scoring_guide={
            10: "글로벌 메가 IP",
            9:  "네이버 웹툰 누적 30억뷰+ 또는 시즌3+",
            8:  "네이버 웹툰 히트작, 시즌2",
            7:  "인기 웹소설 원작",
            6:  "해외 드라마 리메이크",
            5:  "마이너 원작",
            4:  "소규모 원작",
            3:  "실화 모티브",
            2:  "오리지널 각본 (기본값)",
            1:  "원작 미상",
        },
        rationale="원작 팬덤은 초반 유입과 이탈 방지에 기여.",
    ),

    AXIS_PLATFORM: AxisRubric(
        name=AXIS_PLATFORM,
        label_kr="플랫폼 전략",
        description="플랫폼 규모 + 슬롯 모멘텀(lead-in) + 글로벌 동시공개",
        components=(
            "플랫폼 기본 점수 (규모별)",
            "Lead-in: 직전 같은 슬롯 드라마의 후반 25% 평균 시청률",
            "글로벌 동시공개 가산",
            "다중 플랫폼(TV+OTT) 가산",
        ),
        auto_calculable=True,  # lead_in은 닐슨 DB로 자동
        scoring_guide={
            10: "Netflix 글로벌 단독 + 강한 lead-in",
            9:  "Disney+ 글로벌 또는 Netflix",
            8:  "TV + Netflix/Disney+ 동시",
            7:  "TV + 국내 OTT 동시",
            6:  "tvN/SBS/JTBC 단독",
            5:  "MBC/KBS2",
            4:  "ENA/종편",
            3:  "채널A/MBN",
            2:  "마이너 OTT 단독",
            1:  "무명 플랫폼",
        },
        rationale="플랫폼 규모 × 슬롯 lead-in 모멘텀.",
    ),

    AXIS_BUZZ: AxisRubric(
        name=AXIS_BUZZ,
        label_kr="사전 화제성",
        description="방영 전 측정 시점의 화제성 (시간 정규화 적용)",
        components=(
            "FUNdex 방영 전 순위",
            "네이버 검색 트렌드",
            "티저/예고 유튜브 조회수",
            "SNS 언급량",
            "리스크 감점 (논란·이슈)",
        ),
        auto_calculable=False,   # FUNdex 등 외부 데이터 필요
        scoring_guide={
            10: "FUNdex XL+ 또는 티저 천만 뷰+",
            9:  "FUNdex L+1~+2, 방영 전 1위",
            8:  "FUNdex L, 상위권",
            7:  "FUNdex M+",
            6:  "FUNdex M",
            5:  "FUNdex S+",
            4:  "FUNdex S",
            3:  "정보 미미",
            2:  "홍보 부재",
            1:  "마이너스 이슈",
        },
        rationale="첫방 시청률과 최강 상관 (0.91), 단 시간 편향 보정 필수.",
    ),

    AXIS_GENRE: AxisRubric(
        name=AXIS_GENRE,
        label_kr="장르·시장 적합도",
        description="장르 트렌드 + 편성 적합 + 계절 요인",
        components=(
            "장르 트렌드 계수 (GENRE_TRENDS_2025)",
            "장르×플랫폼 궁합",
            "계절 요인 (가을 시작이 유의미하게 높음, 전익진·은혜정 2014)",
            "동시기 같은 장르 경쟁작 수",
        ),
        auto_calculable=True,   # 트렌드·계절 자동
        scoring_guide={
            10: "상승 장르 + 경쟁 없음 + 궁합 최적",
            9:  "상승 장르 + 신선 조합",
            8:  "상승 장르",
            7:  "안정 장르",
            6:  "혼합 장르",
            5:  "보통",
            4:  "하락 추세 (TV 로맨스)",
            3:  "과포화",
            2:  "특수 장르",
            1:  "경쟁+하락",
        },
        rationale="장르 × 계절 × 편성 조합 효과 (연관규칙 분석).",
    ),
}


def get_rubric(axis: str) -> AxisRubric:
    if axis not in RUBRICS:
        raise KeyError(f"Unknown axis: {axis}")
    return RUBRICS[axis]


def get_genre_trend(genre_key: str) -> float:
    """장르 키로 트렌드 계수 조회. 미등록 장르는 1.0 (중립) 반환."""
    return GENRE_TRENDS_2025.get(genre_key, 1.0)
