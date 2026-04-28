"""
드라마 데이터 로더
================
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Union

from .schemas import Drama


FLOAT_FIELDS = {
    "cast_power", "creator_power", "ip_power",
    "platform_strategy", "pre_buzz", "genre_market_fit",
    "pre_buzz_raw", "actor_rsi_avg", "director_rsi", "writer_rsi",
    "prev_slot_final_rating",
    "actual_first_rating", "actual_avg_rating", "actual_max_rating",
    "fundex_weekly_avg",
}

INT_FIELDS = {"episodes", "year", "season_number", "total_awards_5y"}

BOOL_FIELDS = {"has_ip"}


def _clean_row(row: dict) -> dict:
    cleaned = {}
    for k, v in row.items():
        if v is None or v == "":
            cleaned[k] = None
        elif k in FLOAT_FIELDS:
            try:
                cleaned[k] = float(v)
            except (ValueError, TypeError):
                cleaned[k] = None
        elif k in INT_FIELDS:
            try:
                cleaned[k] = int(float(v))
            except (ValueError, TypeError):
                cleaned[k] = None
        elif k in BOOL_FIELDS:
            if isinstance(v, bool):
                cleaned[k] = v
            else:
                cleaned[k] = str(v).strip().lower() in {"true", "1", "yes", "y"}
        else:
            cleaned[k] = v
    return cleaned


def load_dramas_from_csv(path: Union[str, Path]) -> list[Drama]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Not found: {path}")
    dramas = []
    with path.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            dramas.append(Drama.from_dict(_clean_row(row)))
    return dramas


def save_dramas_to_csv(dramas: list[Drama], path: Union[str, Path]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not dramas:
        return
    fieldnames = list(dramas[0].to_dict().keys())
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for d in dramas:
            writer.writerow(d.to_dict())


def load_dramas_from_json(path: Union[str, Path]) -> list[Drama]:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        return [Drama.from_dict(data)]
    return [Drama.from_dict(d) for d in data]
