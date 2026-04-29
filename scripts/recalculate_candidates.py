#!/usr/bin/env python3
"""
필모그래피 기반 자동 H-Score 재계산
=====================================
data/candidate_dramas.csv를 읽어, 각 드라마의 lead_actors/director/writer를
data/filmography/에서 자동 로드하고 RSI 기반으로 H-Score 재계산.

출력 (--version v3 기본):
    - output/recalculated_results_v{N}.json: 전체 결과
    - output/recalculated_results_v{N}.csv: 순위표

사용:
    python scripts/recalculate_candidates.py                # 기본 v3
    python scripts/recalculate_candidates.py --version v2   # legacy
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from hit_predictor.rsi.storage import load_person
from hit_predictor.rsi.calculator import (
    calculate_rsi, aggregate_cast_rsi,
    cast_score_from_rsi, creator_score_from_rsi,
)
from hit_predictor.core.hscore import calculate_triple_kpi
from hit_predictor.core.temporal import normalize_pre_buzz, DEFAULT_ALPHA
from hit_predictor.data.loaders import load_dramas_from_csv


MEASUREMENT_DATE = "2026.04.05"
LOOKBACK_YEARS = 15


def compute_cast_score(drama, filmography_root: Path) -> dict:
    """드라마의 lead_actors 문자열 → 필모그래피 로드 + RSI → 캐스트 점수."""
    if not drama.lead_actors:
        return {"score": None, "reason": "no lead_actors field"}

    names = [n.strip() for n in drama.lead_actors.split("|") if n.strip()]
    persons = []
    missing = []
    for name in names:
        p = load_person(name, "actor", root=filmography_root)
        if p is None:
            missing.append(name)
        else:
            persons.append(p)

    if not persons:
        return {"score": None, "reason": f"all actors missing: {missing}"}

    agg = aggregate_cast_rsi(persons, lookback_years=LOOKBACK_YEARS)
    score = cast_score_from_rsi(agg["avg_rsi"], agg["total_awards"], agg["n_actors"])
    return {
        "score": score,
        "avg_rsi": agg["avg_rsi"],
        "max_rsi": agg["max_rsi"],
        "n_actors": agg["n_actors"],
        "n_missing": len(missing),
        "missing": missing,
        "individual": agg["individual"],
    }


def compute_creator_score(drama, filmography_root: Path) -> dict:
    """director + writer 필모그래피 → 크리에이터 점수."""
    d_rsi = 0.0
    w_rsi = 0.0
    d_awards = 0
    w_awards = 0
    info = {"director": None, "writer": None}

    if drama.director:
        dp = load_person(drama.director, "director", root=filmography_root)
        if dp:
            r = calculate_rsi(dp, lookback_years=LOOKBACK_YEARS)
            d_rsi = r.rsi
            d_awards = r.award_count_5y
            info["director"] = {"name": drama.director, "rsi": r.rsi, "n_credits": r.n_credits}

    if drama.writer:
        wp = load_person(drama.writer, "writer", root=filmography_root)
        if wp:
            r = calculate_rsi(wp, lookback_years=LOOKBACK_YEARS)
            w_rsi = r.rsi
            w_awards = r.award_count_5y
            info["writer"] = {"name": drama.writer, "rsi": r.rsi, "n_credits": r.n_credits}

    score = creator_score_from_rsi(d_rsi, w_rsi, d_awards, w_awards)
    info["score"] = score
    info["director_rsi"] = d_rsi
    info["writer_rsi"] = w_rsi
    return info


def main() -> None:
    p = argparse.ArgumentParser(description="후보 드라마 H-Score 자동 재계산")
    p.add_argument("--version", default="v3",
                   help="출력 버전 태그 (기본: v3 = v3.1 시간 감쇠 적용)")
    p.add_argument("--csv", type=Path, default=None,
                   help="입력 CSV (기본: data/candidate_dramas.csv)")
    args = p.parse_args()

    root = Path(__file__).resolve().parent.parent
    csv_path = args.csv or (root / "data" / "candidate_dramas.csv")
    filmography_root = root / "data" / "filmography"
    output_dir = root / "output"
    output_dir.mkdir(exist_ok=True)
    version = args.version

    print(f"📂 후보 드라마 로드: {csv_path}")
    dramas = load_dramas_from_csv(csv_path)
    print(f"   총 {len(dramas)}편\n")

    results = []
    for d in dramas:
        print(f"▶ {d.title}")

        # 캐스트 자동 계산
        cast_info = compute_cast_score(d, filmography_root)
        cast_auto = cast_info["score"]
        if cast_auto is not None:
            print(f"   캐스트 자동: {cast_auto}/10 (avg_rsi={cast_info.get('avg_rsi')})")
            for ind in cast_info.get("individual", []):
                print(f"      - {ind['name']}: rsi={ind['rsi']}, TV {ind['n_tv']}, OTT {ind['n_ott']}")
        else:
            print(f"   캐스트 자동 실패: {cast_info['reason']}")

        # 크리에이터 자동 계산
        creator_info = compute_creator_score(d, filmography_root)
        creator_auto = creator_info["score"]
        print(f"   크리에이터 자동: {creator_auto}/10")
        if creator_info["director"]:
            print(f"      - 감독 {creator_info['director']['name']}: rsi={creator_info['director']['rsi']}")
        if creator_info["writer"]:
            print(f"      - 작가 {creator_info['writer']['name']}: rsi={creator_info['writer']['rsi']}")

        # H-Score 계산 — 자동값으로 캐스트·크리에이터 교체
        axis_scores = {
            "cast_power": cast_auto if cast_auto is not None else (d.cast_power or 5),
            "creator_power": creator_auto if creator_auto > 0 else (d.creator_power or 5),
            "ip_power": d.ip_power or 2,
            "platform_strategy": d.platform_strategy or 5,
            "pre_buzz": 0,  # 아래 정규화로 계산
            "genre_market_fit": d.genre_market_fit or 5,
        }

        # pre_buzz 정규화
        raw = d.pre_buzz_raw if d.pre_buzz_raw is not None else d.pre_buzz
        if d.release_date and raw is not None:
            try:
                axis_scores["pre_buzz"] = normalize_pre_buzz(
                    raw, d.release_date, MEASUREMENT_DATE, alpha=DEFAULT_ALPHA,
                )
            except Exception:
                axis_scores["pre_buzz"] = raw
        else:
            axis_scores["pre_buzz"] = raw or 0

        result = calculate_triple_kpi(d.title, axis_scores)
        print(f"   → 종합 H-Score: {result.combined} {result.verdict}")
        print()

        results.append({
            "title": d.title,
            "platform": d.platform,
            "release_date": d.release_date,
            "combined": result.combined,
            "first_ep": result.first_ep.hscore,
            "avg": result.avg.hscore,
            "rsi_victory": result.rsi_victory.hscore,
            "verdict": result.verdict,
            "axis_scores": axis_scores,
            "cast_auto": cast_info,
            "creator_auto": creator_info,
            "original_manual_scores": {
                "cast": d.cast_power, "creator": d.creator_power,
                "ip": d.ip_power, "platform": d.platform_strategy,
                "pre_buzz": d.pre_buzz, "genre": d.genre_market_fit,
            },
        })

    results.sort(key=lambda r: -r["combined"])

    # 저장
    json_path = output_dir / f"recalculated_results_{version}.json"
    csv_out_path = output_dir / f"recalculated_results_{version}.csv"

    methodology_map = {
        "v2": "H-Score v2 Triple KPI with auto RSI (full=5, decay=0.15)",
        "v3": "H-Score v3.1 Triple KPI — auto RSI + immediate decay (full=0, decay=0.10) + role_weight",
    }
    with json_path.open("w", encoding="utf-8") as f:
        json.dump({
            "measurement_date": MEASUREMENT_DATE,
            "methodology": methodology_map.get(version, f"H-Score {version}"),
            "results": results,
        }, f, ensure_ascii=False, indent=2)

    # CSV
    import csv as _csv
    with csv_out_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = _csv.writer(f)
        w.writerow(["rank", "title", "combined", "first_ep", "avg", "rsi_victory",
                    "verdict", "cast_auto", "creator_auto", "platform", "release_date"])
        for i, r in enumerate(results, 1):
            w.writerow([i, r["title"], r["combined"], r["first_ep"], r["avg"],
                        r["rsi_victory"], r["verdict"],
                        r["cast_auto"].get("score"), r["creator_auto"].get("score"),
                        r["platform"], r["release_date"]])

    print(f"\n💾 저장: {json_path.name}, {csv_out_path.name}")


if __name__ == "__main__":
    main()
