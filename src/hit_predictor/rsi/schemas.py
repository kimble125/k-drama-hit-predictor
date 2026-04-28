"""
필모그래피 데이터 스키마
========================
배우·감독·작가의 과거 드라마 이력을 DB화한 레코드 정의.

각 사람(Person)은 여러 Credit(출연/연출/극본 이력)을 가짐.
각 Credit은 한 드라마의 역할 + 성적(시청률)을 담음.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Literal, Optional

RoleType = Literal["actor", "director", "writer"]
CastRole = Literal["lead", "supporting", "special", "cameo"]

# 출연 분류별 RSI 가중치 (주연/조연/특별출연/카메오)
# 미루님 정책: 특별출연은 시그널을 빼지 말고 가중치만 낮춤.
ROLE_WEIGHT_MAP: dict[str, float] = {
    "lead": 1.0,
    "supporting": 0.5,
    "special": 0.2,
    "cameo": 0.1,
}


def role_weight_from_cast_role(cast_role: Optional[str]) -> float:
    """cast_role 문자열 → RSI 가중치. 미상이면 lead 가정(1.0)."""
    if not cast_role:
        return 1.0
    return ROLE_WEIGHT_MAP.get(cast_role, 1.0)


@dataclass
class Credit:
    """한 사람의 한 드라마 크레디트."""
    drama_title: str
    year: int
    role: RoleType              # actor / director / writer
    channel: Optional[str] = None      # 예: "tvN"
    day_slot: Optional[str] = None     # 예: "월화", "금토"
    time_slot: Optional[str] = None    # 예: "22:00"
    avg_rating: Optional[float] = None      # 평균 시청률 (TV만)
    first_ep_rating: Optional[float] = None # 첫방 시청률
    max_rating: Optional[float] = None      # 최고 시청률
    is_lead: bool = True        # (legacy) 주연 여부 — backward-compat만 유지, 신규 코드는 role_weight 사용
    cast_role: Optional[CastRole] = None    # 배우 역할(actor일 때만 의미; director/writer는 None)
    role_weight: float = 1.0    # RSI 가중치(lead=1.0, supporting=0.5, special=0.2, cameo=0.1)
    notes: str = ""


@dataclass
class Person:
    """배우·감독·작가 1인 프로필."""
    name: str
    primary_role: RoleType
    credits: list[Credit] = field(default_factory=list)
    award_count_5y: int = 0     # 최근 5년 수상 횟수
    sns_followers: Optional[int] = None  # 인스타그램 팔로워 (보조 지표)

    def recent_credits(self, within_years: int = 5, until_year: Optional[int] = None) -> list[Credit]:
        """최근 N년 이내 크레디트만 필터링."""
        import datetime
        if until_year is None:
            until_year = datetime.datetime.now().year
        return [c for c in self.credits if until_year - within_years <= c.year <= until_year]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "primary_role": self.primary_role,
            "award_count_5y": self.award_count_5y,
            "sns_followers": self.sns_followers,
            "credits": [asdict(c) for c in self.credits],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Person":
        credits = [Credit(**c) for c in d.get("credits", [])]
        return cls(
            name=d["name"],
            primary_role=d["primary_role"],
            credits=credits,
            award_count_5y=d.get("award_count_5y", 0),
            sns_followers=d.get("sns_followers"),
        )
