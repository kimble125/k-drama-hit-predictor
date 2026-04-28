#!/usr/bin/env python3
"""
신작 드라마 자동 발견기
========================
위키백과 + 나무위키 + TMDB에서 특정 연/월의 신작 K-드라마 목록을 자동 수집.

각 소스의 표제어/링크/식별자를 모아 후속 단계(build_candidate_dramas.py)의
입력 시드로 제공한다.

사용:
    python scripts/discover_new_dramas.py --year 2026 --month 4
    python scripts/discover_new_dramas.py --year 2026  # 연간

출력:
    data/discovered/{year}-{month}.json
    (또는 --out으로 지정한 경로)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from bs4 import BeautifulSoup  # noqa: E402

from hit_predictor.data.collectors._http import (  # noqa: E402
    polite_get, attribution_for, RobotsDisallowedError,
)


# ────────────────────────────────────────────────────────────
# 위키백과 — 공식 MediaWiki API 사용 (robots.txt 우회 불필요)
# ────────────────────────────────────────────────────────────
WIKIPEDIA_API = "https://ko.wikipedia.org/w/api.php"


def discover_wikipedia(year: int, month: Optional[int] = None) -> list[dict]:
    """위키백과 [YYYY년 대한민국의 텔레비전 드라마 목록]에서 드라마 추출."""
    page_title = f"{year}년 대한민국의 텔레비전 드라마 목록"
    params = {
        "action": "parse",
        "page": page_title,
        "prop": "wikitext",
        "format": "json",
        "formatversion": "2",
    }
    url = f"{WIKIPEDIA_API}?{urlencode(params)}"
    try:
        # Wikipedia /w/api.php는 명시적으로 API 사용을 허용함.
        # urllib.robotparser가 percent-encoded path를 오매칭하는 이슈를 우회.
        r = polite_get(url, source_key="wikipedia", check_robots=False)
    except Exception as e:
        print(f"[WARN] Wikipedia fetch 실패 ({page_title}): {e}", file=sys.stderr)
        return []

    data = json.loads(r.text)
    if "error" in data:
        print(f"[WARN] Wikipedia API: {data['error'].get('info', 'unknown')}", file=sys.stderr)
        return []

    wikitext = data.get("parse", {}).get("wikitext", "")
    if not wikitext:
        return []
    return _parse_wikitext_drama_list(wikitext, year, month)


def _parse_wikitext_drama_list(
    wikitext: str, year: int, month: Optional[int] = None
) -> list[dict]:
    """wikitext에서 [[제목]] 추출, 월 섹션 필터링."""
    results: list[dict] = []
    seen: set[str] = set()

    # 월별 섹션 분리: == 1월 == ~ == 12월 ==
    sections = re.split(r"^==\s*(\d+)월\s*==", wikitext, flags=re.MULTILINE)

    if len(sections) < 3:
        sections_to_process: list[tuple[Optional[int], str]] = [(None, wikitext)]
    else:
        sections_to_process = []
        for i in range(1, len(sections), 2):
            try:
                mo = int(sections[i])
            except ValueError:
                continue
            content = sections[i + 1] if i + 1 < len(sections) else ""
            if month is None or mo == month:
                sections_to_process.append((mo, content))

    for section_month, content in sections_to_process:
        for match in re.finditer(r"\[\[([^\[\]\|]+?)(?:\|[^\[\]]*)?\]\]", content):
            title = match.group(1).strip()
            if not title or len(title) > 80:
                continue
            # 메타 페이지·분류·일 등 제외
            if any(prefix in title for prefix in [":", "분류", "파일", "위키"]):
                continue
            # 날짜·연도 등 단독 숫자 링크 제외
            if re.fullmatch(r"\d+(년|월|일)?", title):
                continue
            if title in seen:
                continue
            seen.add(title)
            results.append({
                "title": title,
                "source": "wikipedia",
                "wiki_page": title,
                "section_month": section_month,
                "year": year,
            })
    return results


# ────────────────────────────────────────────────────────────
# 나무위키 — 분류 페이지 직접 파싱
# 미루님 정책: 기존 namuwiki_fetcher.py 방식 답습 (check_robots=False)
# ────────────────────────────────────────────────────────────
def discover_namuwiki(year: int) -> list[dict]:
    """나무위키 [분류:YYYY년 드라마] 페이지 멤버 추출."""
    url = f"https://namu.wiki/w/분류:{year}년 드라마"
    try:
        r = polite_get(url, source_key="namuwiki", check_robots=False)
    except RobotsDisallowedError as e:
        print(f"[WARN] Namuwiki robots.txt: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"[WARN] Namuwiki fetch 실패: {e}", file=sys.stderr)
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    results: list[dict] = []
    seen: set[str] = set()

    # 메타·페이지네이션 키워드 (포함 여부로 필터링)
    META_KEYWORDS = (
        "분류", "연도별", "년 방송", "세기", "년대 드라마",
        "목록", "프로그램", "사이트맵",
    )
    # 페이지네이션·UI 텍스트
    UI_TEXT = {"다음", "이전", "처음", "마지막", "위로", "맨 위", "맨 아래"}

    for a in soup.select('a[href^="/w/"]'):
        href = a.get("href", "")
        if not href:
            continue
        # URL 자체가 메타 페이지면 제외
        if any(prefix in href for prefix in ["/분류:", "/사용자:", "/파일:", "/틀:"]):
            continue
        title = a.get_text(strip=True)
        if not title or len(title) > 80 or len(title) < 2:
            continue
        if title in seen or title in UI_TEXT:
            continue
        # 메타 키워드 포함 → 메타 페이지로 분류
        if any(kw in title for kw in META_KEYWORDS):
            continue
        # 영숫자 only 또는 단일 알파벳(앵커) 제외
        if re.fullmatch(r"[A-Za-z0-9\s]+", title):
            continue
        seen.add(title)
        results.append({
            "title": title,
            "source": "namuwiki",
            "url": "https://namu.wiki" + href,
            "year": year,
        })
    return results


# ────────────────────────────────────────────────────────────
# TMDB — 공식 API
# ────────────────────────────────────────────────────────────
TMDB_API = "https://api.themoviedb.org/3"
TMDB_TOKEN_ENV = "TMDB_READ_TOKEN"


def discover_tmdb(year: int, month: Optional[int] = None) -> list[dict]:
    """TMDB /discover/tv 에서 한국 드라마 목록 추출."""
    token = os.getenv(TMDB_TOKEN_ENV)
    if not token:
        print(
            f"[INFO] TMDB token 없음 ({TMDB_TOKEN_ENV} 미설정) — TMDB 단계 건너뜀",
            file=sys.stderr,
        )
        return []

    if month:
        gte = f"{year:04d}-{month:02d}-01"
        lte = (
            f"{year + 1:04d}-01-01" if month == 12
            else f"{year:04d}-{month + 1:02d}-01"
        )
    else:
        gte = f"{year:04d}-01-01"
        lte = f"{year + 1:04d}-01-01"

    base_params = {
        "with_origin_country": "KR",
        "first_air_date.gte": gte,
        "first_air_date.lte": lte,
        "language": "ko-KR",
        "sort_by": "popularity.desc",
    }

    results: list[dict] = []
    seen: set[int] = set()
    for page in range(1, 4):
        params = dict(base_params, page=page)
        url = f"{TMDB_API}/discover/tv?{urlencode(params)}"
        try:
            r = polite_get(
                url, source_key="tmdb",
                extra_headers={"Authorization": f"Bearer {token}"},
            )
        except Exception as e:
            print(f"[WARN] TMDB fetch 실패 (page {page}): {e}", file=sys.stderr)
            break

        data = json.loads(r.text)
        for item in data.get("results", []):
            tmdb_id = item.get("id")
            if not tmdb_id or tmdb_id in seen:
                continue
            title = item.get("name") or item.get("original_name", "")
            if not title:
                continue
            seen.add(tmdb_id)
            results.append({
                "title": title,
                "source": "tmdb",
                "tmdb_id": tmdb_id,
                "first_air_date": item.get("first_air_date"),
                "year": year,
            })
        if page >= data.get("total_pages", 1):
            break
    return results


# ────────────────────────────────────────────────────────────
# 통합 + 정규화
# ────────────────────────────────────────────────────────────
def _normalize_title(title: str) -> str:
    """제목 정규화 — 동일 작품을 다른 표기로 두 번 세지 않기 위함."""
    s = title.strip()
    # 시즌 표기 통일: "유미의 세포들 시즌3" → "유미의세포들3"
    s = re.sub(r"\s*시즌\s*(\d+)", r"\1", s)
    # 공백/구두점 제거
    s = re.sub(r"[\s·,\-_!?'\"]+", "", s)
    return s.lower()


def discover_all(year: int, month: Optional[int] = None) -> dict:
    """모든 소스에서 신작 발견 + 제목 정규화로 병합."""
    print(f"🔍 {year}년 {month or '전체'} 신작 드라마 발견 중...", file=sys.stderr)

    wp = discover_wikipedia(year, month)
    print(f"   Wikipedia: {len(wp)}개", file=sys.stderr)

    nw = discover_namuwiki(year)
    print(f"   Namuwiki: {len(nw)}개", file=sys.stderr)

    tm = discover_tmdb(year, month)
    print(f"   TMDB: {len(tm)}개", file=sys.stderr)

    merged_map: dict[str, dict] = {}
    for item in wp + nw + tm:
        norm = _normalize_title(item["title"])
        entry = merged_map.setdefault(norm, {
            "title": item["title"],
            "norm_key": norm,
            "sources": [],
        })
        if item["source"] not in entry["sources"]:
            entry["sources"].append(item["source"])

        if item["source"] == "wikipedia":
            entry["wiki_page"] = item.get("wiki_page")
            entry.setdefault("section_month", item.get("section_month"))
        elif item["source"] == "namuwiki":
            entry["namuwiki_url"] = item.get("url")
        elif item["source"] == "tmdb":
            entry["tmdb_id"] = item.get("tmdb_id")
            entry["first_air_date"] = item.get("first_air_date")

    return {
        "year": year,
        "month": month,
        "discovered_at": datetime.now().isoformat(timespec="seconds"),
        "by_source": {"wikipedia": wp, "namuwiki": nw, "tmdb": tm},
        "merged": list(merged_map.values()),
        "attribution": {
            "wikipedia": attribution_for("wikipedia"),
            "namuwiki": attribution_for("namuwiki"),
            "tmdb": attribution_for("tmdb"),
        },
    }


def main() -> None:
    p = argparse.ArgumentParser(description="신작 드라마 자동 발견기")
    p.add_argument("--year", type=int, required=True)
    p.add_argument("--month", type=int, default=None, help="특정 월만 (1-12)")
    p.add_argument("--out", type=Path, default=None,
                   help="출력 경로 (기본: data/discovered/{year}-{month}.json)")
    args = p.parse_args()

    result = discover_all(args.year, args.month)

    out_path = args.out
    if out_path is None:
        repo_root = Path(__file__).resolve().parent.parent
        suffix = f"{args.year}-{args.month:02d}" if args.month else f"{args.year}"
        out_path = repo_root / "data" / "discovered" / f"{suffix}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"\n✅ 저장: {out_path}", file=sys.stderr)
    print(f"   총 {len(result['merged'])}편 (소스별 dedup 후)", file=sys.stderr)
    for entry in result["merged"][:20]:
        srcs = "+".join(entry["sources"])
        print(f"   [{srcs:>22s}] {entry['title']}", file=sys.stderr)
    if len(result["merged"]) > 20:
        print(f"   ... 외 {len(result['merged']) - 20}편", file=sys.stderr)


if __name__ == "__main__":
    main()
