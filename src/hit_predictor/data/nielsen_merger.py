"""
닐슨 히스토리 병합기
====================
닐슨 CSV에서 드라마 시청률을 추출하여 필모그래피 JSON에
avg_rating/max_rating을 자동 주입한다.

닐슨 CSV 특성 (실측 기반):
    - 프로그램명이 "SBS금토드라마(신이랑법률사무소)" 형태
      → 괄호 안이 실제 제목
    - household_rating, audience_count 두 가지 metric이 있음
    - 드라마/뉴스/예능이 섞여 있어 필터링 필요

매칭 로직:
    1. 괄호 안 제목 추출 (공백 제거한 버전 포함)
    2. 필모그래피의 drama_title과 정규화 후 매칭
    3. 해당 프로그램의 주간 시청률 → avg/max 계산
"""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Optional

import pandas as pd


PAREN_PATTERN = re.compile(r"\(([^)]+)\)")
NORMALIZE_PATTERN = re.compile(r"[\s·\-_·]")


def extract_title_from_nielsen_program(program) -> Optional[str]:
    """닐슨 프로그램명에서 실제 드라마 제목 추출.

    예시:
        "SBS금토드라마(신이랑법률사무소)" → "신이랑 법률사무소"
        "KBS2주말드라마(사랑을처방해드립니다)" → "사랑을 처방해드립니다"
        "일일드라마(첫번째남자)" → "첫번째 남자"
        "9시뉴스" → None (드라마 아님)
    """
    if not program or not isinstance(program, str):
        return None
    m = PAREN_PATTERN.search(program)
    if not m:
        return None
    raw = m.group(1).strip()
    if not raw:
        return None
    return raw


def normalize_title(title) -> str:
    """매칭용 정규화: 공백, 특수문자 제거."""
    if not title or not isinstance(title, str):
        return ""
    return NORMALIZE_PATTERN.sub("", title).lower()


def load_nielsen_ratings(csv_path: Path) -> pd.DataFrame:
    """닐슨 CSV 로드 + 드라마 시청률만 필터."""
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    df = df[df["metric_type"] == "household_rating"].copy()
    df["metric_value"] = pd.to_numeric(df["metric_value"], errors="coerce")
    df = df.dropna(subset=["metric_value"])
    # 드라마인 프로그램만 (괄호 제목 추출 가능한 것)
    df["extracted_title"] = df["program"].apply(extract_title_from_nielsen_program)
    df["normalized_title"] = df["extracted_title"].apply(
        lambda t: normalize_title(t) if t else ""
    )
    return df[df["extracted_title"].notna()].reset_index(drop=True)


def build_rating_map(df: pd.DataFrame) -> dict[str, dict]:
    """정규화된 제목 → rating 정보 dict.

    Returns:
        {normalized_title: {
            "canonical_title": str,
            "channel": str,
            "avg_rating": float,
            "max_rating": float,
            "first_ep_rating": Optional[float],  # 첫 등장 주차 시청률
            "n_weeks": int,
        }}
    """
    rating_map = {}
    for norm_title, grp in df.groupby("normalized_title"):
        if not norm_title:
            continue
        vals = grp["metric_value"].tolist()
        grp_sorted = grp.sort_values("week_end")
        channel = grp["channel"].mode().iloc[0] if not grp["channel"].empty else None
        rating_map[norm_title] = {
            "canonical_title": grp["extracted_title"].iloc[0],
            "channel": channel,
            "avg_rating": round(sum(vals) / len(vals), 2),
            "max_rating": round(max(vals), 2),
            "first_ep_rating": round(grp_sorted["metric_value"].iloc[0], 2),
            "n_weeks": len(vals),
        }
    return rating_map


def merge_ratings_into_credit(credit: dict, rating_map: dict) -> dict:
    """Credit dict에 rating 정보 주입. 매칭 안 되면 그대로 반환."""
    title = credit.get("drama_title", "")
    norm = normalize_title(title)
    if norm in rating_map:
        r = rating_map[norm]
        credit["avg_rating"] = r["avg_rating"]
        credit["max_rating"] = r["max_rating"]
        credit["first_ep_rating"] = r["first_ep_rating"]
        if not credit.get("channel"):
            credit["channel"] = r["channel"]
        notes = credit.get("notes", "")
        credit["notes"] = f"{notes}|nielsen_matched".strip("|")
    return credit


def merge_ratings_into_filmography(
    filmography_dir: Path,
    rating_map: dict,
) -> dict:
    """필모그래피 디렉토리 전체 순회하며 시청률 병합.

    Returns:
        {"updated_persons": int, "updated_credits": int, "matched_titles": set}
    """
    import json
    stats = {
        "updated_persons": 0,
        "updated_credits": 0,
        "matched_titles": set(),
    }
    for subdir in ("actors", "directors", "writers"):
        dpath = filmography_dir / subdir
        if not dpath.exists():
            continue
        for json_file in dpath.glob("*.json"):
            with json_file.open(encoding="utf-8") as f:
                data = json.load(f)
            updated_count = 0
            for c in data.get("credits", []):
                before_rating = c.get("avg_rating")
                merge_ratings_into_credit(c, rating_map)
                if c.get("avg_rating") != before_rating and c.get("avg_rating") is not None:
                    updated_count += 1
                    stats["matched_titles"].add(c["drama_title"])
            if updated_count > 0:
                with json_file.open("w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                stats["updated_persons"] += 1
                stats["updated_credits"] += updated_count
    return stats
