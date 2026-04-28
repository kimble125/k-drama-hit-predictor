#!/usr/bin/env python3
"""
Netflix Top10 공식 데이터 자동 다운로드
=======================================
Netflix Tudum 공식 사이트에서 주간 Top10 XLSX를 다운로드하여
data/netflix_top10/ 아래에 저장.

데이터 소스 (공식, 무료, 매주 업데이트):
    - all-weeks-countries.xlsx: 93개국 × 주간 Top10
    - all-weeks-global.xlsx: 글로벌 주간 Top10

참고:
    Netflix 이용약관: 개인 연구·학습용 가능. 재판매 금지.
    출처 명시: "Source: Netflix Top 10 (tudum.com/top10)"

실행:
    python scripts/fetch_netflix_top10.py
    python scripts/fetch_netflix_top10.py --peek  # 한국 Top5만 미리보기
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import argparse

import requests


NETFLIX_URLS = {
    "countries": "https://www.netflix.com/tudum/top10/data/all-weeks-countries.xlsx",
    "global": "https://www.netflix.com/tudum/top10/data/all-weeks-global.xlsx",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
    ),
    "Accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,*/*",
}


def download_file(url: str, out_path: Path, timeout: int = 60) -> int:
    """XLSX 파일 다운로드. 반환: 파일 크기 (bytes)."""
    print(f"  ⇣ 다운로드: {url}")
    r = requests.get(url, headers=HEADERS, timeout=timeout, stream=True)
    r.raise_for_status()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with out_path.open("wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                total += len(chunk)

    return total


def peek_korea_top5(countries_path: Path) -> None:
    """한국 최신 주차 Top5를 미리 보여주기."""
    import pandas as pd

    if not countries_path.exists():
        print(f"⚠️  파일 없음: {countries_path}")
        return

    try:
        df = pd.read_excel(countries_path)
        df.columns = [c.lower().strip() for c in df.columns]

        # 한국 필터
        country_col = "country_iso2" if "country_iso2" in df.columns else "country_name"
        if country_col == "country_iso2":
            kr_df = df[df[country_col] == "KR"].copy()
        else:
            kr_df = df[df[country_col].str.contains("Korea", case=False, na=False)].copy()

        if kr_df.empty:
            print("⚠️  한국 데이터 없음")
            return

        # 최신 주차
        week_col = next((c for c in ("week", "week_start", "week_end") if c in kr_df.columns), None)
        if week_col:
            kr_df = kr_df.sort_values(week_col, ascending=False)
            latest_week = kr_df[week_col].iloc[0]
            latest_df = kr_df[kr_df[week_col] == latest_week]
        else:
            latest_df = kr_df.head(30)

        rank_col = next((c for c in ("weekly_rank", "rank") if c in latest_df.columns), None)
        title_col = next((c for c in ("show_title", "title", "season_title") if c in latest_df.columns), None)
        weeks_col = next((c for c in ("cumulative_weeks_in_top_10", "weeks_in_top10") if c in latest_df.columns), None)

        print("\n🇰🇷 한국 최신 주차 Top 10 미리보기:")
        if week_col:
            print(f"   (주차: {latest_df[week_col].iloc[0]})\n")

        if rank_col:
            latest_df = latest_df.sort_values(rank_col).head(10)

        for _, row in latest_df.iterrows():
            rank = int(row[rank_col]) if rank_col else "?"
            title = row[title_col] if title_col else "?"
            weeks = int(row[weeks_col]) if weeks_col and not _pd_is_na(row[weeks_col]) else "?"
            print(f"   #{rank:2d}  {title}  (체류 {weeks}주)")
    except Exception as e:
        print(f"⚠️  미리보기 실패: {e}")


def _pd_is_na(v) -> bool:
    import pandas as pd
    try:
        return pd.isna(v)
    except Exception:
        return v is None


def main() -> None:
    parser = argparse.ArgumentParser(description="Netflix Top10 XLSX 자동 다운로드")
    parser.add_argument("--out-dir", type=str, default="data/netflix_top10",
                        help="저장 디렉토리 (기본: data/netflix_top10)")
    parser.add_argument("--peek", action="store_true",
                        help="다운로드 후 한국 Top5 미리보기")
    parser.add_argument("--global-only", action="store_true",
                        help="글로벌 파일만 다운로드")
    parser.add_argument("--countries-only", action="store_true",
                        help="국가별 파일만 다운로드")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    print("=" * 60)
    print(" Netflix Top 10 Downloader (공식 데이터)")
    print(" Source: https://www.netflix.com/tudum/top10/")
    print(" License: 개인 연구·학습용. 재판매 금지.")
    print("=" * 60 + "\n")

    targets = list(NETFLIX_URLS.items())
    if args.global_only:
        targets = [(k, v) for k, v in targets if k == "global"]
    elif args.countries_only:
        targets = [(k, v) for k, v in targets if k == "countries"]

    results = {}
    for kind, url in targets:
        out_path = out_dir / f"all-weeks-{kind}.xlsx"
        try:
            start = time.time()
            size = download_file(url, out_path)
            elapsed = time.time() - start
            size_mb = size / (1024 * 1024)
            print(f"  ✅ 저장: {out_path}  ({size_mb:.2f} MB, {elapsed:.1f}s)")
            results[kind] = out_path
        except requests.HTTPError as e:
            print(f"  ❌ HTTP 오류 ({kind}): {e}")
        except Exception as e:
            print(f"  ❌ 실패 ({kind}): {e}")

    if args.peek and "countries" in results:
        peek_korea_top5(results["countries"])

    print("\n💡 다음 단계:")
    print("   from hit_predictor.rsi.ott_converter import extract_drama_performance")
    print("   perf = extract_drama_performance('폭싹 속았수다')")
    print("   print(perf)")


if __name__ == "__main__":
    main()
