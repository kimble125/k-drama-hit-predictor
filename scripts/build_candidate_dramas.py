#!/usr/bin/env python3
"""
candidate_dramas.csv 자동 빌더 (이슈 1 핵심)
=============================================
discovered JSON을 입력으로 받아 각 드라마의 메타·출연진·감독·작가를
다중 소스(나무위키, 위키백과, TMDB)에서 수집·교차검증하여
candidate_dramas.csv를 자동 생성한다.

특징:
    - 나무위키 우선(출연진·역할 가장 풍부) + 위키백과(객관 사실 보강)
    - 출연 가중치(role_weight) 자동 분류: 주연/조연/특별출연/카메오
    - 결측치 사유(MissingReason) 자동 기록
    - 출처(field_sources) 자동 추적
    - 미루님 정책: '원인을 모르는' 결측치는 결측치대로 두고, 사유 기록만 함

사용:
    python scripts/build_candidate_dramas.py --year 2026 --month 4
    python scripts/build_candidate_dramas.py --year 2026 --month 4 --dry-run
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode, quote

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from bs4 import BeautifulSoup  # noqa: E402

from hit_predictor.data.collectors._http import (  # noqa: E402
    polite_get, attribution_for, RobotsDisallowedError,
)
from hit_predictor.data.wikipedia_fetcher import (  # noqa: E402
    extract_infobox, clean_value, WIKI_LINK,
)
from hit_predictor.data.schemas import MissingReason  # noqa: E402
from hit_predictor.rsi.schemas import (  # noqa: E402
    ROLE_WEIGHT_MAP, role_weight_from_cast_role,
)


WIKIPEDIA_API = "https://ko.wikipedia.org/w/api.php"
NAMU_BASE = "https://namu.wiki/w/"


# ────────────────────────────────────────────────────────────
# 위키백과: 인포박스에서 출연·연출·극본 추출
# ────────────────────────────────────────────────────────────
def fetch_wikipedia_drama(wiki_page: str) -> dict:
    """위키백과에서 드라마 메타+캐스트+감독+작가 수집."""
    params = {
        "action": "parse", "page": wiki_page, "prop": "wikitext",
        "format": "json", "formatversion": "2",
    }
    try:
        r = polite_get(
            f"{WIKIPEDIA_API}?{urlencode(params)}",
            source_key="wikipedia", check_robots=False,
        )
    except Exception as e:
        return {"_error": f"wikipedia_fetch: {e}"}

    data = json.loads(r.text)
    if "error" in data:
        return {"_error": f"wikipedia_api: {data['error'].get('info', '')}"}

    wikitext = data.get("parse", {}).get("wikitext", "")
    if not wikitext:
        return {"_error": "wikipedia_empty_wikitext"}

    infobox = extract_infobox(wikitext)
    out: dict = {"_source": "wikipedia"}

    # 채널
    for k in ("방송 채널", "방송사", "방송국", "채널", "방영 채널"):
        if k in infobox and infobox[k]:
            out["channel"] = infobox[k].split()[0]
            break

    # 방영기간
    for k in ("방영 기간", "방송 기간"):
        if k in infobox and infobox[k]:
            parts = re.split(r"\s*[~–-]\s*", infobox[k])
            if parts:
                out["release_date"] = parts[0].strip()
            break

    # 출연자
    for k in ("출연자", "출연", "주연"):
        if k in infobox and infobox[k]:
            out["lead_actors"] = _wiki_person_list(infobox[k])
            break

    # 연출
    for k in ("연출", "감독", "PD", "프로듀서"):
        if k in infobox and infobox[k]:
            out["director"] = _wiki_person_list(infobox[k])
            break

    # 극본
    for k in ("극본", "각본", "작가"):
        if k in infobox and infobox[k]:
            out["writer"] = _wiki_person_list(infobox[k])
            break

    # 회수
    for k in ("회수", "회차", "에피소드"):
        if k in infobox and infobox[k]:
            m = re.search(r"(\d+)", infobox[k])
            if m:
                out["episodes"] = int(m.group(1))
            break

    # 원작
    for k in ("원작", "기반"):
        if k in infobox and infobox[k]:
            out["has_ip"] = True
            out["ip_source"] = clean_value(infobox[k])[:80]
            break

    # 시간대
    for k in ("방송 시간", "편성 시간", "방영 시간"):
        if k in infobox and infobox[k]:
            out["time_text"] = infobox[k]
            break

    return out


def _wiki_person_list(text: str) -> list[str]:
    """위키 인포박스 값에서 인물 이름 리스트 추출."""
    if not text:
        return []
    # [[이름]] 또는 [[페이지|표시]] 패턴 우선
    links = WIKI_LINK.findall(text)
    if links:
        return [_clean_name(n) for n in links if _is_person_name(_clean_name(n))]
    # 링크 없으면 br/콤마/슬래시로 분리
    parts = re.split(r"<br\s*/?>|,|·|/", text)
    cleaned = [_clean_name(clean_value(p)) for p in parts if p.strip()]
    return [c for c in cleaned if _is_person_name(c)]


def _clean_name(s: str) -> str:
    """배우 이름 끝의 (역할명)·괄호 부연 제거."""
    s = re.sub(r"\s*[\(（].+?[\)）]\s*$", "", s).strip()
    return s


def _is_person_name(s: str) -> bool:
    """한국식 인물 이름 판정 — 너무 짧거나 일반 단어 제외."""
    if not s or len(s) < 2 or len(s) > 8:
        return False
    # 한글 또는 한자 또는 (드물지만) 영문 이름
    if not re.fullmatch(r"[가-힣A-Za-z\s\.]+", s):
        return False
    # 잡 단어 제외
    excluded = {"드라마", "텔레비전", "방송", "참고", "기타"}
    return s not in excluded


# ────────────────────────────────────────────────────────────
# 나무위키: 인포박스 + 출연 섹션의 주연/조연/특별출연 분류
# ────────────────────────────────────────────────────────────
def fetch_namuwiki_drama(title: str, namu_url: Optional[str] = None) -> dict:
    """나무위키에서 드라마 메타+캐스트(역할)+감독+작가 수집."""
    url = namu_url or (NAMU_BASE + quote(title))
    try:
        r = polite_get(url, source_key="namuwiki", check_robots=False)
    except Exception as e:
        return {"_error": f"namuwiki_fetch: {e}"}

    soup = BeautifulSoup(r.text, "html.parser")
    out: dict = {"_source": "namuwiki"}

    # 1) 인포박스 — 첫 테이블의 th-td 쌍
    creators = _namu_extract_creators(soup)
    if creators.get("director"):
        out["director"] = creators["director"]
    if creators.get("writer"):
        out["writer"] = creators["writer"]
    if creators.get("channel"):
        out["channel"] = creators["channel"]
    if creators.get("episodes"):
        out["episodes"] = creators["episodes"]
    if creators.get("release_date"):
        out["release_date"] = creators["release_date"]
    if creators.get("has_ip") is not None:
        out["has_ip"] = creators["has_ip"]
    if creators.get("ip_source"):
        out["ip_source"] = creators["ip_source"]
    if creators.get("time_text"):
        out["time_text"] = creators["time_text"]

    # 2) 출연 섹션 — 주연/조연/특별출연 분류
    cast = _namu_extract_cast(soup)
    out["cast_by_role"] = cast  # {lead: [...], supporting: [...], special: [...], cameo: [...]}
    out["lead_actors"] = cast["lead"]
    return out


def _namu_extract_creators(soup: BeautifulSoup) -> dict:
    """나무위키 페이지의 인포박스에서 연출·각본·채널 등 추출."""
    out: dict = {}
    # 인포박스는 보통 wiki-table 클래스 또는 첫 번째 table
    tables = soup.find_all("table")
    if not tables:
        return out

    label_map = {
        "director": ("연출", "감독", "PD"),
        "writer": ("각본", "극본", "작가"),
        "channel": ("방송사", "방송 채널", "방송국", "채널", "방영 채널"),
        "release_date": ("방영 기간", "방송 기간", "방영일", "첫 방송"),
        "time_text": ("방영 시간", "방송 시간", "편성 시간"),
        "episodes": ("회차", "회수", "에피소드", "분량"),
        "ip_source": ("원작",),
    }

    for table in tables[:3]:  # 첫 3개 테이블만 인포박스 후보
        for row in table.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            if not th or not td:
                continue
            label = th.get_text(strip=True)
            value = td.get_text(" ", strip=True)
            if not value:
                continue
            for field, keywords in label_map.items():
                if any(kw in label for kw in keywords) and field not in out:
                    if field in ("director", "writer"):
                        out[field] = _extract_korean_names(value)
                    elif field == "channel":
                        m = re.search(
                            r"(KBS\s?\d?|MBC|SBS|tvN|JTBC|ENA|채널A|MBN|TV조선|"
                            r"OCN|Netflix|Disney\+|TVING|웨이브|쿠팡플레이|"
                            r"GenieTV|U\+모바일tv)",
                            value,
                        )
                        if m:
                            out["channel"] = m.group(1)
                    elif field == "episodes":
                        m = re.search(r"(\d+)\s*(?:부작|화|회|편)", value)
                        if m:
                            out["episodes"] = int(m.group(1))
                    elif field == "ip_source":
                        out["has_ip"] = True
                        out["ip_source"] = value[:80]
                    else:
                        out[field] = value[:120]
        if out:
            break  # 첫 인포박스에서 정보 찾았으면 다음 테이블 스킵
    return out


def _namu_extract_cast(soup: BeautifulSoup) -> dict:
    """나무위키 출연 섹션에서 주연/조연/특별출연 분류."""
    cast = {"lead": [], "supporting": [], "special": [], "cameo": []}
    seen_per_role = {k: set() for k in cast}

    role_keywords = [
        ("special", ["특별 출연", "특별출연", "스페셜"]),
        ("cameo", ["카메오", "단역"]),
        ("supporting", ["조연", "주변 인물", "주변 등장인물", "그 외 인물"]),
        ("lead", ["주연", "주요 등장인물", "주요 인물", "메인 캐스트", "출연진"]),
    ]

    # h2/h3/h4/h5 헤더 순회
    headings = soup.find_all(["h2", "h3", "h4", "h5"])
    for h in headings:
        ht = h.get_text(strip=True)
        # 가장 구체적 매칭(특별→카메오→조연→주연 순)
        matched_role = None
        for role_key, keywords in role_keywords:
            if any(kw in ht for kw in keywords):
                matched_role = role_key
                break
        if not matched_role:
            continue
        names = _names_after_heading(h)
        for n in names:
            if n not in seen_per_role[matched_role]:
                seen_per_role[matched_role].add(n)
                cast[matched_role].append(n)
    return cast


def _names_after_heading(heading) -> list[str]:
    """헤더 다음부터 같은/상위 헤더 전까지의 영역에서 한국 이름 추출."""
    names: list[str] = []
    seen: set[str] = set()
    current = heading.find_next_sibling()
    h_level = int(heading.name[1]) if heading.name and heading.name[0] == "h" else 99

    # find_all_next로 전체 후속 노드 순회 (sibling만으로는 부족할 수 있음)
    for el in heading.find_all_next():
        if el.name and el.name.startswith("h") and len(el.name) == 2:
            try:
                if int(el.name[1]) <= h_level:
                    break
            except ValueError:
                pass
        if el.name in ("strong", "b", "a"):
            txt = el.get_text(strip=True)
            cleaned = _clean_name(txt)
            if _is_person_name(cleaned) and cleaned not in seen:
                seen.add(cleaned)
                names.append(cleaned)
        if len(names) >= 30:  # 한 섹션에서 너무 많은 후보는 노이즈 방지
            break
    return names


def _extract_korean_names(text: str) -> list[str]:
    """텍스트에서 한국식 이름 후보 추출."""
    # 한자/한글 2-4글자 이름 패턴
    candidates = re.findall(r"[가-힣]{2,4}", text)
    return [c for c in candidates if _is_person_name(c)]


# ────────────────────────────────────────────────────────────
# 다중 소스 통합·투표
# ────────────────────────────────────────────────────────────
SOURCE_PRIORITY_BY_FIELD = {
    "lead_actors": ["namuwiki", "wikipedia"],
    "director": ["namuwiki", "wikipedia"],
    "writer": ["namuwiki", "wikipedia"],
    "channel": ["wikipedia", "namuwiki"],
    "release_date": ["wikipedia", "namuwiki"],
    "episodes": ["wikipedia", "namuwiki"],
    "has_ip": ["namuwiki", "wikipedia"],
}


def merge_field(
    field: str, sources: dict[str, dict],
) -> tuple[Optional[object], Optional[str], Optional[str]]:
    """
    필드별 다중 소스 투표.
    Returns: (value, source_used, reason_if_missing)
    """
    priority = SOURCE_PRIORITY_BY_FIELD.get(field, ["namuwiki", "wikipedia"])
    candidates = []
    for src in priority:
        v = sources.get(src, {}).get(field)
        if v not in (None, "", [], {}):
            candidates.append((v, src))

    if not candidates:
        return None, None, MissingReason.NOT_IN_ANY_SOURCE.value

    # 첫 우선순위 소스 채택
    value, source = candidates[0]

    # 리스트 값에 대해 다른 소스의 값과 _많이_ 다르면 source_disagreement 표기
    if len(candidates) >= 2 and isinstance(value, list):
        other = candidates[1][0]
        if isinstance(other, list):
            common = set(value) & set(other)
            if not common and len(value) > 0 and len(other) > 0:
                # 완전 불일치 — 우선순위 따르되 사유 기록
                return value, source, MissingReason.SOURCE_DISAGREEMENT.value
    return value, source, None


def build_drama_record(merged_entry: dict) -> dict:
    """단일 드라마: 다중 소스 수집 + 통합 + 6축 점수 placeholder."""
    title = merged_entry["title"]
    sources_data: dict[str, dict] = {}

    # Wikipedia
    if "wiki_page" in merged_entry:
        wp = fetch_wikipedia_drama(merged_entry["wiki_page"])
        if "_error" not in wp:
            sources_data["wikipedia"] = wp
    # Namuwiki
    if "namuwiki_url" in merged_entry or "namuwiki" in merged_entry.get("sources", []):
        nw = fetch_namuwiki_drama(title, merged_entry.get("namuwiki_url"))
        if "_error" not in nw:
            sources_data["namuwiki"] = nw

    record: dict = {
        "title": title,
        "lead_actors": None,
        "director": None,
        "writer": None,
        "channel": None,
        "release_date": None,
        "episodes": None,
        "has_ip": False,
        "year": merged_entry.get("year"),
        "season_number": _detect_season(title),
        "notes": "",
    }
    quality: dict[str, str] = {}
    field_sources: dict[str, str] = {}

    for field in ("lead_actors", "director", "writer", "channel",
                  "release_date", "episodes", "has_ip"):
        value, source, reason = merge_field(field, sources_data)
        if value is not None:
            record[field] = value
            if source:
                field_sources[field] = source
        if reason:
            quality[field] = reason

    # 출연 가중치 자동 분류 (나무위키의 cast_by_role 활용)
    cast_by_role = sources_data.get("namuwiki", {}).get("cast_by_role")
    if cast_by_role:
        # 주연만 lead_actors로 압축. 나머지는 별도 dict에 보존.
        record["lead_actors"] = cast_by_role.get("lead") or record["lead_actors"]
        record["cast_role_breakdown"] = {
            role: names for role, names in cast_by_role.items() if names
        }

    # 데이터 출처 표기
    record["data_quality"] = quality
    record["field_sources"] = field_sources
    record["sources_attempted"] = list(sources_data.keys())

    return record


def _detect_season(title: str) -> Optional[int]:
    """제목에서 시즌 번호 추출 (예: '유미의 세포들3' → 3)."""
    m = re.search(r"(\d+)$", title.strip())
    if m:
        n = int(m.group(1))
        if 2 <= n <= 9:  # 1은 보통 시즌 표기 없음
            return n
    m = re.search(r"시즌\s*(\d+)", title)
    if m:
        return int(m.group(1))
    return None


# ────────────────────────────────────────────────────────────
# CSV 출력 (기존 컬럼 호환)
# ────────────────────────────────────────────────────────────
CSV_COLUMNS = [
    "title", "cast_power", "creator_power", "ip_power", "platform_strategy",
    "pre_buzz_raw", "genre_market_fit",
    "lead_actors", "director", "writer",
    "platform", "channel", "day_slot", "time_slot",
    "genre", "genre_key", "release_date", "episodes",
    "year", "has_ip", "season_number", "notes",
]


def to_csv_row(record: dict) -> list[str]:
    """record → CSV 1행. 6축 점수는 자동 산정 전이므로 빈 값 또는 placeholder."""
    def _join(v):
        if isinstance(v, list):
            return "|".join(str(x) for x in v)
        if v is None:
            return ""
        if isinstance(v, bool):
            return "True" if v else "False"
        return str(v)

    return [_join(record.get(col)) for col in CSV_COLUMNS]


def write_csv(records: list[dict], out_path: Path) -> None:
    import csv
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(CSV_COLUMNS)
        for r in records:
            w.writerow(to_csv_row(r))


def write_quality_json(records: list[dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    quality_payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "by_drama": {
            r["title"]: {
                "data_quality": r.get("data_quality", {}),
                "field_sources": r.get("field_sources", {}),
                "sources_attempted": r.get("sources_attempted", []),
                "cast_role_breakdown": r.get("cast_role_breakdown"),
            }
            for r in records
        },
        "attribution": {
            "wikipedia": attribution_for("wikipedia"),
            "namuwiki": attribution_for("namuwiki"),
        },
    }
    out_path.write_text(
        json.dumps(quality_payload, ensure_ascii=False, indent=2), encoding="utf-8",
    )


# ────────────────────────────────────────────────────────────
# 필터: discovered 169편 → 실제 드라마만
# ────────────────────────────────────────────────────────────
def filter_dramas(merged: list[dict], min_sources: int = 1) -> list[dict]:
    """노이즈(인물 페이지·일반 단어) 제외, 다중 소스 매칭 우선."""
    filtered = []
    for entry in merged:
        title = entry["title"]
        # 인물 페이지 패턴 — "이름 (연출가)" 등
        if re.search(r"\((연출가|작가|배우|가수|감독|성우)\)$", title):
            continue
        # 너무 일반적 단어
        if title in {"텔레비전", "드라마", "방송", "한국", "프로그램"}:
            continue
        # 한 글자
        if len(title) < 2:
            continue
        if len(entry.get("sources", [])) >= min_sources:
            filtered.append(entry)
    return filtered


# ────────────────────────────────────────────────────────────
# 메인
# ────────────────────────────────────────────────────────────
def main() -> None:
    p = argparse.ArgumentParser(description="candidate_dramas.csv 자동 빌더")
    p.add_argument("--year", type=int, required=True)
    p.add_argument("--month", type=int, default=None)
    p.add_argument(
        "--discovered", type=Path, default=None,
        help="discovered JSON 경로 (기본: data/discovered/{year}-{month}.json)",
    )
    p.add_argument(
        "--out", type=Path, default=None,
        help="출력 CSV 경로 (기본: data/candidate_dramas.csv)",
    )
    p.add_argument(
        "--titles", type=str, default=None,
        help="콤마구분 제목 목록만 처리 (디버깅용; discovered 무시)",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="기존 CSV와 비교만 (덮어쓰지 않음)",
    )
    p.add_argument("--limit", type=int, default=None, help="처리 제한 (테스트용)")
    args = p.parse_args()

    repo_root = Path(__file__).resolve().parent.parent

    # 입력 데이터 로드
    if args.titles:
        # 직접 제목 목록 — 나무위키 single source 진입
        targets = [
            {
                "title": t.strip(),
                "sources": ["namuwiki"],
                "namuwiki_url": NAMU_BASE + quote(t.strip()),
                "wiki_page": t.strip(),
                "year": args.year,
            }
            for t in args.titles.split(",") if t.strip()
        ]
    else:
        suffix = f"{args.year}-{args.month:02d}" if args.month else f"{args.year}"
        disc_path = args.discovered or (
            repo_root / "data" / "discovered" / f"{suffix}.json"
        )
        if not disc_path.exists():
            print(
                f"❌ discovered 파일 없음: {disc_path}\n"
                f"   먼저 discover_new_dramas.py 실행:\n"
                f"   python scripts/discover_new_dramas.py --year {args.year} "
                f"--month {args.month or ''}",
                file=sys.stderr,
            )
            sys.exit(1)
        disc = json.loads(disc_path.read_text(encoding="utf-8"))
        targets = filter_dramas(disc.get("merged", []), min_sources=1)

    if args.limit:
        targets = targets[:args.limit]

    print(f"🔧 {len(targets)}편 처리 시작...", file=sys.stderr)

    records: list[dict] = []
    for i, entry in enumerate(targets, 1):
        try:
            rec = build_drama_record(entry)
            records.append(rec)
            print(
                f"   [{i:3d}/{len(targets)}] {rec['title']:30s}  "
                f"src={rec.get('sources_attempted', [])}  "
                f"missing={list(rec.get('data_quality', {}).keys())}",
                file=sys.stderr,
            )
        except Exception as e:
            print(f"   [{i:3d}/{len(targets)}] {entry['title']}  ❌ {e}",
                  file=sys.stderr)

    # 출력
    out_csv = args.out or (repo_root / "data" / "candidate_dramas.csv")
    out_quality = repo_root / "data" / "candidate_dramas_quality.json"

    if args.dry_run:
        print(f"\n[DRY-RUN] 생성될 CSV ({out_csv}):", file=sys.stderr)
        for r in records:
            print(f"  {r['title']:30s}  "
                  f"감독={r.get('director')}  "
                  f"작가={r.get('writer')}  "
                  f"주연={r.get('lead_actors')}",
                  file=sys.stderr)
        # 기존 CSV와 diff
        if out_csv.exists():
            print(f"\n[DRY-RUN] 기존 CSV diff:", file=sys.stderr)
            existing = _load_existing_titles(out_csv)
            new_titles = {r["title"] for r in records}
            print(f"   추가될 드라마: {sorted(new_titles - existing)}", file=sys.stderr)
            print(f"   유지/갱신: {sorted(new_titles & existing)}", file=sys.stderr)
            print(f"   사라질 드라마: {sorted(existing - new_titles)}", file=sys.stderr)
        return

    write_csv(records, out_csv)
    write_quality_json(records, out_quality)
    print(f"\n✅ {out_csv}  ({len(records)}편)", file=sys.stderr)
    print(f"✅ {out_quality}  (결측치 사유 + 출처)", file=sys.stderr)


def _load_existing_titles(csv_path: Path) -> set[str]:
    import csv
    titles: set[str] = set()
    with csv_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            t = row.get("title", "").strip()
            if t:
                titles.add(t)
    return titles


if __name__ == "__main__":
    main()
