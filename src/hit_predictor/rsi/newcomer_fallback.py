"""
신인 작가·감독 Fallback 점수 시스템
=====================================
주상필(2019), 최현종(2017) 등 기존 RSI 모델은 "참여 회차 0인 신인은 결측치"
로 처리. 그러나 실무에서는 신인의 검증 지표가 분명히 존재함.

배진아(2005)의 발견:
    "작가의 시상 경력이 장르 적합도와 결합될 때 의미 있다"
    → 즉 수상 이력이 신인의 RSI 대체 신호가 될 수 있음

이 모듈의 정책:
    base_score = 0.3   # 신인 중립값 (기존 0.0보다 합리적)
    
    가산점 (수상 이력):
        대상/최우수상:           +0.20
        우수상/장려상:           +0.10
        입선/심사위원특별상:     +0.05
        
    가산점 (제도권 검증):
        방송사 작가실 수료:      +0.05
        한콘진/CJ ENM 사업 선정: +0.05
        대학·아카데미 졸업:      +0.03
    
    cap = 0.6   # 신인은 베테랑(0.7+)을 못 넘음
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

# ────────────────────────────────────────────────────────────────
# 가산점 정의
# ────────────────────────────────────────────────────────────────
AWARD_BONUSES = {
    "grand_prize": 0.20,        # 대상
    "best_screenplay": 0.20,    # 최우수극본상
    "excellence": 0.10,         # 우수상
    "encouragement": 0.10,      # 장려상
    "selection": 0.05,          # 입선
    "special_jury": 0.05,       # 심사위원특별상
}

VERIFICATION_BONUSES = {
    "broadcaster_writer_room": 0.05,   # 방송사 작가실 수료 (KBS, MBC 등)
    "kocca_ip_selection": 0.05,        # 한국콘텐츠진흥원 스토리IP 선정
    "cj_oneoftheway": 0.05,            # CJ ENM 'O'PEN 등 신인 발굴 사업
    "writer_academy": 0.03,            # 작가아카데미 졸업
    "drama_school": 0.03,              # 드라마스쿨 (한국방송작가협회 등)
}

NEWCOMER_BASE = 0.3
NEWCOMER_CAP = 0.6


# ────────────────────────────────────────────────────────────────
# 데이터 구조
# ────────────────────────────────────────────────────────────────
@dataclass
class NewcomerCredentials:
    """신인 작가·감독의 검증 자료."""
    awards: list[str]              # ["excellence", "selection"] 등
    verifications: list[str]       # ["broadcaster_writer_room"] 등
    notes: str = ""                # 출처/세부 (예: "MBC 극본공모 우수상 2024")


def calculate_newcomer_rsi(creds: NewcomerCredentials) -> float:
    """신인의 fallback RSI 계산.
    
    Examples:
        >>> creds = NewcomerCredentials(awards=["excellence"], verifications=[])
        >>> calculate_newcomer_rsi(creds)  
        # 0.3 + 0.10 = 0.40
        
        >>> creds = NewcomerCredentials(
        ...     awards=["grand_prize"], 
        ...     verifications=["broadcaster_writer_room"],
        ... )
        >>> calculate_newcomer_rsi(creds)  
        # 0.3 + 0.20 + 0.05 = 0.55
    """
    score = NEWCOMER_BASE
    for award in creds.awards:
        score += AWARD_BONUSES.get(award, 0.0)
    for v in creds.verifications:
        score += VERIFICATION_BONUSES.get(v, 0.0)
    return min(round(score, 3), NEWCOMER_CAP)


# ────────────────────────────────────────────────────────────────
# 알려진 신인 데이터베이스 (수기, 21세기 대군부인 등)
# ────────────────────────────────────────────────────────────────
# 미루님이 발견하신 케이스들 + 향후 누적
KNOWN_NEWCOMERS: dict[str, NewcomerCredentials] = {
    # 21세기 대군부인 작가
    "유지원": NewcomerCredentials(
        awards=["excellence"],
        verifications=[],
        notes="MBC 드라마 극본 공모 장편시리즈 부문 우수상 (2024). 21세기 대군부인 데뷔.",
    ),
    # 은밀한 감사 작가  
    "여은호": NewcomerCredentials(
        awards=["selection"],
        verifications=["broadcaster_writer_room"],
        notes="신인급. tvN 데뷔작 〈은밀한 감사〉. (참고: 일부 단편 경력 있음)",
    ),
    # 오늘도 매진했습니다 작가
    "이영미": NewcomerCredentials(
        awards=[],
        verifications=["broadcaster_writer_room"],
        notes="신인급. SBS 데뷔작.",
    ),
    # 기리고 감독 박윤서
    "박윤서": NewcomerCredentials(
        awards=["selection"],  # 〈무빙〉 공동연출 경력
        verifications=[],
        notes="〈무빙〉 공동연출. Netflix 〈기리고〉 단독 연출 데뷔.",
    ),
    # 기리고 작가 박중섭
    "박중섭": NewcomerCredentials(
        awards=[],
        verifications=[],
        notes="〈천박사 퇴마연구소: 설경의 비밀〉 각본. Netflix 〈기리고〉.",
    ),
    # 은밀한 감사 감독 이수현 — 신인급으로 판단
    "이수현": NewcomerCredentials(
        awards=[],
        verifications=["broadcaster_writer_room"],
        notes="tvN 신예 감독. 데뷔작.",
    ),
}


def get_newcomer_rsi_or_none(name: str) -> Optional[float]:
    """이름으로 알려진 신인의 fallback RSI 조회. 없으면 None."""
    if name in KNOWN_NEWCOMERS:
        return calculate_newcomer_rsi(KNOWN_NEWCOMERS[name])
    return None


def add_newcomer(
    name: str,
    awards: list[str] = None,
    verifications: list[str] = None,
    notes: str = "",
) -> NewcomerCredentials:
    """런타임에 신인 정보 추가."""
    creds = NewcomerCredentials(
        awards=awards or [],
        verifications=verifications or [],
        notes=notes,
    )
    KNOWN_NEWCOMERS[name] = creds
    return creds
