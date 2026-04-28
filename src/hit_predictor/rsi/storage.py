"""
필모그래피 저장소 (Filmography Storage)
========================================
data/filmography/*.json 파일들을 Person 객체로 로드.

디렉토리 구조:
    data/filmography/
        actors/
            아이유.json
            변우석.json
            ...
        directors/
            박준화.json
            ...
        writers/
            김은숙.json
            ...

JSON 스키마 (Person.to_dict() 결과와 동일):
    {
      "name": "아이유",
      "primary_role": "actor",
      "award_count_5y": 3,
      "sns_followers": 32000000,
      "credits": [
        {"drama_title": "호텔 델루나", "year": 2019, "role": "actor",
         "channel": "tvN", "day_slot": "토일", "time_slot": "21:00",
         "avg_rating": 10.5, "first_ep_rating": 7.3, "max_rating": 12.0,
         "is_lead": true, "notes": ""}
      ]
    }
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, Optional

from .schemas import Person, RoleType

DEFAULT_ROOT = Path("data/filmography")


def _role_to_dir(role: RoleType) -> str:
    return {"actor": "actors", "director": "directors", "writer": "writers"}[role]


def load_person(
    name: str,
    role: RoleType,
    root: Path = DEFAULT_ROOT,
) -> Optional[Person]:
    """이름과 역할로 Person 객체 로드. 없으면 None 반환."""
    path = Path(root) / _role_to_dir(role) / f"{name}.json"
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return Person.from_dict(data)


def save_person(person: Person, root: Path = DEFAULT_ROOT) -> Path:
    """Person 객체를 JSON으로 저장."""
    out_dir = Path(root) / _role_to_dir(person.primary_role)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{person.name}.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(person.to_dict(), f, ensure_ascii=False, indent=2)
    return out_path


def list_all_people(role: RoleType, root: Path = DEFAULT_ROOT) -> list[str]:
    """특정 역할의 등록된 인물 이름 목록."""
    dir_path = Path(root) / _role_to_dir(role)
    if not dir_path.exists():
        return []
    return sorted(p.stem for p in dir_path.glob("*.json"))


def load_many(
    names: list[str],
    role: RoleType,
    root: Path = DEFAULT_ROOT,
) -> list[Person]:
    """여러 이름을 한번에 로드. 없는 사람은 스킵."""
    people = []
    for name in names:
        p = load_person(name, role, root)
        if p is not None:
            people.append(p)
    return people


def create_placeholder(name: str, role: RoleType) -> Person:
    """DB에 없는 사람에 대한 빈 Person 생성 (fallback)."""
    return Person(name=name, primary_role=role, credits=[], award_count_5y=0)
