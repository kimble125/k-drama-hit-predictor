#!/usr/bin/env python3
"""
닐슨코리아 주간 시청률 자동 수집 wrapper
==========================================
collectors/nielsen.py 의 핵심 로직을 호출해 월별·지역별로 일괄 수집한다.

기능:
    - 단일 월 수집: --year-month 202604
    - 기간 수집: --from 202401 --to 202604 (월 단위)
    - 지역: --area both (default) | nationwide | metro
    - 카테고리: 지상파 + 종편 + 케이블 모두 자동
    - 출력: data/nielsen_weekly/nielsen_weekly_{YYYYMM}_{area}.csv

⚠️ 닐슨코리아 이용약관:
    수집된 CSV는 .gitignore에 의해 git 공개에서 제외된다 (재배포 금지).
    본 스크립트와 collectors/nielsen.py 코드 자체는 공개 가능.

사용:
    # 4월(현재) 수집 — 전국+수도권
    python scripts/fetch_nielsen_weekly.py --year-month 202604

    # 1년치 일괄 수집
    python scripts/fetch_nielsen_weekly.py --from 202501 --to 202604

    # 수도권만
    python scripts/fetch_nielsen_weekly.py --year-month 202604 --area metro
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pandas as pd  # noqa: E402

from hit_predictor.data.collectors.nielsen import (  # noqa: E402
    CATEGORY_CONFIG, AREA_CODE_TO_LABEL, collect_category,
)


# CLI 라벨 → area 코드
AREA_CLI_TO_CODE = {
    "nationwide": "00",
    "metro": "01",
}


def collect_one_month(
    begin_date: str, area: str, sleep_sec: float = 1.5,
) -> pd.DataFrame:
    """한 달치, 한 지역 — 지상파+종편+케이블 모두 수집해 결합."""
    frames = []
    for category_key in CATEGORY_CONFIG:
        try:
            df = collect_category(category_key, begin_date, area)
            if not df.empty:
                frames.append(df)
                print(
                    f"     {category_key:20s} ✓ {len(df)}행", file=sys.stderr,
                )
            else:
                print(
                    f"     {category_key:20s} (빈 결과)", file=sys.stderr,
                )
            time.sleep(sleep_sec)
        except Exception as e:
            print(f"     {category_key:20s} ✗ {e}", file=sys.stderr)
            time.sleep(sleep_sec * 2)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True).drop_duplicates()


def save_monthly_csv(
    df: pd.DataFrame, output_dir: Path, begin_date: str, area: str,
) -> Path:
    """월·지역별 CSV 저장."""
    output_dir.mkdir(parents=True, exist_ok=True)
    label_short = "nationwide" if area == "00" else (
        "metro" if area == "01" else f"area{area}"
    )
    fname = f"nielsen_weekly_{begin_date}_{label_short}.csv"
    out = output_dir / fname
    df.to_csv(out, index=False, encoding="utf-8-sig")
    return out


def iter_months(start_yyyymm: str, end_yyyymm: str):
    """startMonth ~ endMonth 까지 yyyymm 문자열 yield (포함)."""
    sy, sm = int(start_yyyymm[:4]), int(start_yyyymm[4:])
    ey, em = int(end_yyyymm[:4]), int(end_yyyymm[4:])
    y, m = sy, sm
    while (y, m) <= (ey, em):
        yield f"{y:04d}{m:02d}"
        m += 1
        if m > 12:
            y += 1
            m = 1


def main() -> None:
    p = argparse.ArgumentParser(description="닐슨 주간 시청률 자동 수집")
    p.add_argument("--year-month", type=str, default=None,
                   help="단일 월 수집: 202604 형식")
    p.add_argument("--from", dest="start", type=str, default=None,
                   help="기간 시작 yyyymm")
    p.add_argument("--to", dest="end", type=str, default=None,
                   help="기간 종료 yyyymm (포함)")
    p.add_argument("--area", choices=("both", "nationwide", "metro"),
                   default="both", help="수집 지역 (default: both)")
    p.add_argument("--sleep", type=float, default=1.5,
                   help="카테고리 간 sleep (초)")
    p.add_argument("--out-dir", type=Path, default=None,
                   help="출력 디렉터리 (기본: data/nielsen_weekly/)")
    args = p.parse_args()

    if args.year_month and (args.start or args.end):
        p.error("--year-month 또는 --from/--to 중 하나만 사용")
    if not args.year_month and not (args.start and args.end):
        p.error("--year-month 또는 --from/--to 가 필요")

    # 수집 대상 area 코드 결정
    if args.area == "both":
        area_codes = ["00", "01"]
    else:
        area_codes = [AREA_CLI_TO_CODE[args.area]]

    # 수집 대상 yyyymm 목록
    if args.year_month:
        months = [args.year_month]
    else:
        months = list(iter_months(args.start, args.end))

    repo_root = Path(__file__).resolve().parent.parent
    out_dir = args.out_dir or (repo_root / "data" / "nielsen_weekly")

    print("⚠️  닐슨 이용약관 준수: 개인 연구용. CSV는 .gitignore로 공개 제외.\n",
          file=sys.stderr)
    print(f"📅 대상 기간: {len(months)}개월 ({months[0]} ~ {months[-1]})",
          file=sys.stderr)
    print(f"🌐 지역: {[AREA_CODE_TO_LABEL[c] for c in area_codes]}",
          file=sys.stderr)

    total_files = 0
    total_rows = 0
    for ym in months:
        print(f"\n📊 {ym} 수집 중...", file=sys.stderr)
        for area in area_codes:
            label = AREA_CODE_TO_LABEL[area]
            print(f"   [{label}]", file=sys.stderr)
            df = collect_one_month(ym, area, sleep_sec=args.sleep)
            if df.empty:
                print(f"   [{label}] 빈 결과 — 건너뜀", file=sys.stderr)
                continue
            out = save_monthly_csv(df, out_dir, ym, area)
            print(f"   [{label}] ✅ {out.name}  ({len(df)}행)", file=sys.stderr)
            total_files += 1
            total_rows += len(df)

    print(f"\n✨ 완료: {total_files}개 파일, 누적 {total_rows}행", file=sys.stderr)


if __name__ == "__main__":
    main()
