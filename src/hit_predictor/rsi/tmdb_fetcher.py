"""
TMDB 필모그래피 자동 수집기
============================
TMDB (The Movie Database) API를 사용해 배우·감독·작가의 필모그래피를
자동으로 가져와 Person JSON 파일로 저장.

⚠️ 네트워크 필요:
    이 모듈은 api.themoviedb.org 접근이 필요합니다. Claude 샌드박스에선
    차단되므로 미루님 로컬 환경에서 실행하세요.

인증:
    환경변수 TMDB_READ_TOKEN 또는 스크립트에 직접 토큰 전달.
    발급: https://www.themoviedb.org/settings/api

한계:
    - TMDB는 시청률 데이터를 제공하지 않음 → avg_rating은 별도 수집 필요
      (닐슨 크롤러 또는 수기)
    - TMDB는 is_lead(주연) 정보가 없음 → order<=3 또는 top-billed cast로 추정
    - 극본·연출 이력은 crew department로 필터링 (job="Director", "Writer")

사용 예시:
    from hit_predictor.rsi.tmdb_fetcher import TMDBClient, fetch_and_save_person
    client = TMDBClient(read_token="eyJ...")

    # 1. 배우 이름으로 검색
    person_id = client.search_person_id("아이유")

    # 2. 필모그래피 전체 수집 + 저장
    person = fetch_and_save_person(client, "아이유", role="actor")
    print(f"수집 완료: {len(person.credits)}편")
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import asdict
from pathlib import Path
from typing import Literal, Optional

import requests

from .schemas import Person, Credit, RoleType
from .storage import save_person

# ────────────────────────────────────────────────────────────────
# TMDB API 기본 설정
# ────────────────────────────────────────────────────────────────
TMDB_BASE = "https://api.themoviedb.org/3"
DEFAULT_LANGUAGE = "ko-KR"
REQUEST_DELAY = 0.3  # TMDB 무료 rate limit: 50 req/sec (여유있게)


# ────────────────────────────────────────────────────────────────
# TMDB 클라이언트
# ────────────────────────────────────────────────────────────────
class TMDBClient:
    """TMDB API 래퍼. Bearer 토큰 인증."""

    def __init__(
        self,
        read_token: Optional[str] = None,
        language: str = DEFAULT_LANGUAGE,
        timeout: int = 15,
    ):
        self.read_token = read_token or os.environ.get("TMDB_READ_TOKEN")
        if not self.read_token:
            raise ValueError(
                "TMDB Read Token 필요. 환경변수 TMDB_READ_TOKEN을 설정하거나 "
                "생성자에 read_token= 인수로 전달하세요."
            )
        self.language = language
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {self.read_token}",
            "Accept": "application/json",
        })

    def _get(self, path: str, **params) -> dict:
        """GET 요청. 공통 언어 파라미터 자동 추가."""
        params.setdefault("language", self.language)
        url = f"{TMDB_BASE}{path}"
        r = self._session.get(url, params=params, timeout=self.timeout)
        r.raise_for_status()
        time.sleep(REQUEST_DELAY)
        return r.json()

    # ─── 검색 ───
    def search_person_id(self, name: str, adult: bool = False) -> Optional[int]:
        """이름으로 TMDB person_id 검색. 가장 인기 있는 1인 선택."""
        data = self._get("/search/person", query=name, include_adult=adult)
        results = data.get("results", [])
        if not results:
            # 한국어로 안 나오면 영문으로 재시도
            data = self._get("/search/person", query=name, language="en-US")
            results = data.get("results", [])
        if not results:
            return None
        # popularity 가장 높은 사람
        results.sort(key=lambda r: -(r.get("popularity") or 0))
        return results[0]["id"]

    # ─── 상세 정보 ───
    def get_person_details(self, person_id: int) -> dict:
        return self._get(f"/person/{person_id}")

    def get_person_tv_credits(self, person_id: int) -> dict:
        """TV 크레딧 전체 (cast + crew)."""
        return self._get(f"/person/{person_id}/tv_credits")

    def get_tv_details(self, tv_id: int) -> dict:
        """특정 드라마 상세 (방영 기간, 에피소드 수, 방송사 등)."""
        return self._get(f"/tv/{tv_id}")


# ────────────────────────────────────────────────────────────────
# TMDB credits → Credit 변환
# ────────────────────────────────────────────────────────────────
# 한국 방송사 TMDB network name → 표준 채널명
NETWORK_NORMALIZATION = {
    "SBS": "SBS", "MBC": "MBC", "KBS1": "KBS1", "KBS2": "KBS2", "KBS": "KBS2",
    "tvN": "tvN", "JTBC": "JTBC", "ENA": "ENA", "OCN": "OCN",
    "Channel A": "채널A", "MBN": "MBN", "TV Chosun": "TV조선",
    "Netflix": "Netflix", "Disney+": "Disney+", "Disney Plus": "Disney+",
    "Apple TV+": "Apple TV+", "Wavve": "웨이브", "TVING": "TVING",
    "Coupang Play": "쿠팡플레이", "Watcha": "왓챠",
}


def _extract_year(date_str: Optional[str]) -> Optional[int]:
    if not date_str:
        return None
    try:
        return int(date_str[:4])
    except (ValueError, TypeError):
        return None


def _tmdb_cast_to_credits(
    cast_entries: list[dict],
    client: TMDBClient,
    enrich_with_details: bool = True,
) -> list[Credit]:
    """TMDB tv_credits.cast 리스트를 Credit 객체로 변환.

    Args:
        cast_entries: TMDB /person/{id}/tv_credits.cast 리스트
        client: 상세 정보 조회용
        enrich_with_details: True면 각 TV show의 채널/에피소드 정보 추가 조회
    """
    credits = []
    for entry in cast_entries:
        tv_id = entry.get("id")
        title_ko = entry.get("name") or entry.get("original_name") or ""
        order = entry.get("order")  # 캐스팅 순서 (낮을수록 주연)
        year = _extract_year(entry.get("first_air_date"))

        # 주연 판단: order <= 3 → 주연으로 추정
        is_lead = order is not None and order <= 3

        channel = None
        if enrich_with_details and tv_id:
            try:
                details = client.get_tv_details(tv_id)
                networks = details.get("networks", [])
                if networks:
                    raw_ch = networks[0].get("name", "")
                    channel = NETWORK_NORMALIZATION.get(raw_ch, raw_ch)
            except Exception:
                pass

        # 한국 드라마만 (origin_country 포함 KR)
        origin = entry.get("origin_country") or []
        if origin and "KR" not in origin:
            continue

        credits.append(Credit(
            drama_title=title_ko,
            year=year or 0,
            role="actor",
            channel=channel,
            avg_rating=None,       # TMDB는 시청률 없음 → 수기/닐슨 병합 필요
            first_ep_rating=None,
            max_rating=None,
            is_lead=is_lead,
            notes=f"tmdb_id={tv_id}, order={order}",
        ))
    return credits


def _tmdb_crew_to_credits(
    crew_entries: list[dict],
    target_role: RoleType,
    client: TMDBClient,
    enrich_with_details: bool = True,
) -> list[Credit]:
    """TMDB tv_credits.crew에서 특정 역할(director/writer)만 추출."""
    job_filter = {"director": ("Director",), "writer": ("Writer", "Screenplay", "Story")}[target_role]

    credits = []
    seen_ids = set()
    for entry in crew_entries:
        if entry.get("job") not in job_filter:
            continue
        tv_id = entry.get("id")
        if tv_id in seen_ids:  # 같은 드라마 중복 방지
            continue
        seen_ids.add(tv_id)

        title_ko = entry.get("name") or entry.get("original_name") or ""
        year = _extract_year(entry.get("first_air_date"))

        origin = entry.get("origin_country") or []
        if origin and "KR" not in origin:
            continue

        channel = None
        if enrich_with_details and tv_id:
            try:
                details = client.get_tv_details(tv_id)
                networks = details.get("networks", [])
                if networks:
                    raw_ch = networks[0].get("name", "")
                    channel = NETWORK_NORMALIZATION.get(raw_ch, raw_ch)
            except Exception:
                pass

        credits.append(Credit(
            drama_title=title_ko,
            year=year or 0,
            role=target_role,
            channel=channel,
            avg_rating=None,
            first_ep_rating=None,
            max_rating=None,
            is_lead=True,  # 감독·작가는 항상 "참여"
            notes=f"tmdb_id={tv_id}, job={entry.get('job')}",
        ))
    return credits


# ────────────────────────────────────────────────────────────────
# 상위 API: 이름만으로 Person 완성
# ────────────────────────────────────────────────────────────────
def fetch_person(
    client: TMDBClient,
    name: str,
    role: RoleType,
    enrich_with_details: bool = True,
    max_credits: int = 30,
) -> Optional[Person]:
    """TMDB에서 필모그래피를 가져와 Person 객체 생성.

    Args:
        client: TMDBClient
        name: 배우/감독/작가 이름 (한국어 또는 영문)
        role: "actor" / "director" / "writer"
        enrich_with_details: 각 드라마의 채널 정보까지 추가 조회 (느리지만 정확)
        max_credits: 최근 N개만 반환 (기본 30)

    Returns:
        Person 또는 None (검색 실패)
    """
    person_id = client.search_person_id(name)
    if person_id is None:
        print(f"[WARN] TMDB에서 '{name}' 찾기 실패")
        return None

    tv_credits = client.get_person_tv_credits(person_id)

    if role == "actor":
        entries = tv_credits.get("cast", [])
        credits = _tmdb_cast_to_credits(entries, client, enrich_with_details)
    else:
        entries = tv_credits.get("crew", [])
        credits = _tmdb_crew_to_credits(entries, role, client, enrich_with_details)

    # 최근순 정렬 + 상한
    credits.sort(key=lambda c: -c.year)
    credits = credits[:max_credits]

    return Person(
        name=name,
        primary_role=role,
        credits=credits,
        award_count_5y=0,  # TMDB는 수상 정보 없음 → 수기 업데이트
    )


def fetch_and_save_person(
    client: TMDBClient,
    name: str,
    role: RoleType,
    root: Path = Path("data/filmography"),
    enrich_with_details: bool = True,
) -> Optional[Person]:
    """fetch_person + save_person."""
    person = fetch_person(client, name, role, enrich_with_details)
    if person is None:
        return None
    save_person(person, root=root)
    return person


# ────────────────────────────────────────────────────────────────
# 배치: 이름 리스트 → 전체 필모그래피
# ────────────────────────────────────────────────────────────────
def batch_fetch(
    client: TMDBClient,
    actors: Optional[list[str]] = None,
    directors: Optional[list[str]] = None,
    writers: Optional[list[str]] = None,
    root: Path = Path("data/filmography"),
    enrich_with_details: bool = False,  # 배치는 default False (속도)
) -> dict:
    """여러 사람의 필모그래피를 한 번에 수집.

    Returns:
        {"actors": [Person...], "directors": [Person...], "writers": [Person...]}
    """
    result = {"actors": [], "directors": [], "writers": []}
    for name in (actors or []):
        p = fetch_and_save_person(client, name, "actor", root, enrich_with_details)
        if p:
            result["actors"].append(p)
            print(f"  ✓ 배우 {name}: {len(p.credits)}편")
    for name in (directors or []):
        p = fetch_and_save_person(client, name, "director", root, enrich_with_details)
        if p:
            result["directors"].append(p)
            print(f"  ✓ 감독 {name}: {len(p.credits)}편")
    for name in (writers or []):
        p = fetch_and_save_person(client, name, "writer", root, enrich_with_details)
        if p:
            result["writers"].append(p)
            print(f"  ✓ 작가 {name}: {len(p.credits)}편")
    return result


# ────────────────────────────────────────────────────────────────
# 닐슨/수기 데이터와 병합: TMDB credits에 avg_rating 주입
# ────────────────────────────────────────────────────────────────
def enrich_with_ratings(
    person: Person,
    rating_map: dict[str, dict],
) -> Person:
    """기존 Person의 credits에 시청률 정보를 병합.

    Args:
        person: TMDB로 가져온 Person (avg_rating=None)
        rating_map: {drama_title: {"avg_rating": 10.5, "first_ep_rating": 7.3, ...}}

    Returns:
        rating 정보가 병합된 새 Person.
    """
    enriched_credits = []
    for c in person.credits:
        if c.drama_title in rating_map:
            r = rating_map[c.drama_title]
            enriched_credits.append(Credit(
                drama_title=c.drama_title, year=c.year, role=c.role,
                channel=c.channel or r.get("channel"),
                day_slot=c.day_slot or r.get("day_slot"),
                time_slot=c.time_slot or r.get("time_slot"),
                avg_rating=r.get("avg_rating"),
                first_ep_rating=r.get("first_ep_rating"),
                max_rating=r.get("max_rating"),
                is_lead=c.is_lead, notes=c.notes,
            ))
        else:
            enriched_credits.append(c)
    return Person(
        name=person.name, primary_role=person.primary_role,
        credits=enriched_credits, award_count_5y=person.award_count_5y,
        sns_followers=person.sns_followers,
    )
