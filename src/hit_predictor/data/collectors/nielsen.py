"""
닐슨 코리아 주간 시청률 수집기
==============================
수집 대상: 닐슨 코리아 공식 페이지 (지상파/종편/케이블 주간 순위).

⚠️ 중요 — Nielsen Korea 이용약관 준수:
    - 수집된 데이터는 **개인 연구·학습 용도로만** 사용합니다.
    - 데이터를 재배포·재판매·공개 업로드 해서는 안 됩니다.
    - 상업적 이용이 금지됩니다.
    - 본 크롤러는 공공 페이지에서 허용된 범위의 정보를 지연 요청으로 수집.
    - 모든 결과에 source URL과 collected_at을 기록합니다.
    - CSV는 .gitignore로 레포 공개에서 제외됩니다.

원본 출처: https://www.nielsenkorea.co.kr/tv_terrestrial_day.asp

사용:
    from hit_predictor.data.collectors.nielsen import collect_recent_week, save_weekly_csv
    df = collect_recent_week()
    save_weekly_csv(df, Path("data/nielsen_weekly"))
"""
from __future__ import annotations

import re
import time
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.nielsenkorea.co.kr/tv_terrestrial_day.asp"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
    )
}

CATEGORY_CONFIG = {
    "terrestrial": {"label": "지상파", "sub_menu": "1_2", "expected_top_n": 20},
    "general_programming": {"label": "종편", "sub_menu": "2_2", "expected_top_n": 10},
    "cable": {"label": "케이블", "sub_menu": "3_2", "expected_top_n": 10},
}

# 닐슨 사이트 area 코드 매핑 (사이트 JS 분석 결과)
#   00 → 전국 (8개 권역, "National, 단위:%" basis)
#   01 → 수도권 (서울·경기·인천, "수도권, 단위:%" basis)
AREA_CODE_TO_LABEL = {
    "00": "전국",
    "01": "수도권",
}


def build_url(sub_menu: str, begin_date: str, area: str = "00") -> str:
    params = {"menu": "Tit_1", "sub_menu": sub_menu, "area": area, "begin_date": begin_date}
    return f"{BASE_URL}?{urlencode(params)}"


def fetch_html(url: str, timeout: int = 30) -> str:
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    r.encoding = "utf-8"
    return r.text


def extract_week_candidates(text: str) -> list[str]:
    return sorted(set(re.findall(r"\b(20\d{6}-20\d{6})\b", text)))


def extract_displayed_week_range(text: str) -> tuple[Optional[str], Optional[str]]:
    m = re.search(r"(\d{4}\.\d{2}\.\d{2})\s*~\s*(\d{4}\.\d{2}\.\d{2})", text)
    if not m:
        return None, None
    return m.group(1), m.group(2)


def extract_analysis_basis(text: str) -> dict[str, Optional[str]]:
    basis = {"rating_basis": None, "audience_basis": None}
    m1 = re.search(r"가구시청률 TOP \d+\s*\(\s*분석기준:\s*([^)]+)\)", text)
    if m1:
        basis["rating_basis"] = m1.group(1).strip()
    m2 = re.search(r"시청자수 TOP \d+\s*\(\s*분석기준:\s*([^)]+)\)", text)
    if m2:
        basis["audience_basis"] = m2.group(1).strip()
    return basis


def parse_tables(
    html: str, category_label: str, source_url: str,
    begin_date: str, area_label: str = "전국",
) -> pd.DataFrame:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)

    week_start, week_end = extract_displayed_week_range(text)
    week_candidates = extract_week_candidates(text)
    basis = extract_analysis_basis(text)
    collected_at = datetime.now().isoformat(timespec="seconds")

    try:
        tables = pd.read_html(StringIO(html))
    except ValueError:
        return pd.DataFrame()

    frames = []
    for df in tables:
        cols = [str(c).strip() for c in df.columns]
        if not {"순위", "채널", "프로그램"}.issubset(set(cols)):
            header_idx = None
            for idx, row in df.iterrows():
                row_vals = [str(x).strip() for x in row.values]
                if {"순위", "채널", "프로그램"}.issubset(set(row_vals)):
                    header_idx = idx
                    cols = row_vals
                    break
            if header_idx is not None:
                df.columns = cols
                df = df.iloc[header_idx + 1:].reset_index(drop=True)
            else:
                continue

        if "시청률" in cols:
            metric_col, metric_type, unit = "시청률", "household_rating", "percent"
            basis_value = basis["rating_basis"]
        elif "시청자수" in cols:
            metric_col, metric_type, unit = "시청자수", "audience_count", "thousand_persons"
            basis_value = basis["audience_basis"]
        else:
            continue

        temp = df[["순위", "채널", "프로그램", metric_col]].copy()
        temp.columns = ["rank", "channel", "program", "metric_value"]
        temp["rank"] = pd.to_numeric(temp["rank"], errors="coerce")
        temp["metric_value"] = (
            temp["metric_value"].astype(str).str.replace(",", "", regex=False).str.strip()
        )
        temp["metric_value"] = pd.to_numeric(temp["metric_value"], errors="coerce")

        temp["category"] = category_label
        temp["area"] = area_label
        temp["begin_date"] = begin_date
        temp["week_start"] = week_start
        temp["week_end"] = week_end
        temp["metric_type"] = metric_type
        temp["unit"] = unit
        temp["analysis_basis"] = basis_value
        temp["week_candidates"] = "|".join(week_candidates)
        temp["source_url"] = source_url
        temp["collected_at"] = collected_at
        frames.append(temp)

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True).drop_duplicates()


def collect_category(category_key: str, begin_date: str, area: str = "00") -> pd.DataFrame:
    cfg = CATEGORY_CONFIG[category_key]
    url = build_url(sub_menu=cfg["sub_menu"], begin_date=begin_date, area=area)
    html = fetch_html(url)
    return parse_tables(
        html=html, category_label=cfg["label"], source_url=url,
        begin_date=begin_date,
        area_label=AREA_CODE_TO_LABEL.get(area, f"unknown({area})"),
    )


def collect_recent_week(area: str = "00", sleep_sec: float = 1.5) -> pd.DataFrame:
    """최근 주의 지상파/종편/케이블 전체 수집."""
    today = datetime.now().strftime("%Y%m")
    frames = []
    for key in CATEGORY_CONFIG:
        try:
            df = collect_category(key, today, area)
            if not df.empty:
                frames.append(df)
            time.sleep(sleep_sec)
        except Exception as e:
            print(f"[ERR] {key}: {e}")
            time.sleep(3)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True).drop_duplicates()


def save_weekly_csv(df: pd.DataFrame, output_dir: Path) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if df.empty:
        raise ValueError("빈 DataFrame 저장 불가")
    week_start = df["week_start"].iloc[0] or datetime.now().strftime("%Y.%m.%d")
    fname = f"{week_start.replace('.', '-')}.csv"
    out_path = output_dir / fname
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    return out_path


if __name__ == "__main__":
    print("⚠️  Nielsen Korea 이용약관 준수: 개인 연구용. 재배포 금지.")
    print("닐슨 최근 1주차 데이터 수집 중...")
    df = collect_recent_week()
    if df.empty:
        print("수집 실패")
    else:
        out = save_weekly_csv(df, Path("data/nielsen_weekly"))
        print(f"저장: {out}  ({len(df)}행)")
