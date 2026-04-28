"""
나무위키 fallback 메타데이터 수집기
====================================
위키백과에 없는 드라마(마이너·신작)의 방영 정보를 나무위키에서 보완.

⚠️ 주의사항:
    - 나무위키는 API가 없음. HTML 스크래핑.
    - robots.txt 준수: User-Agent 명시, 요청 간 1초 이상 간격
    - 라이센스 CC BY-NC-SA 4.0: 비상업 이용만. 개인 연구는 가능.
    - 대량 크롤링은 차단됨. **위키백과에서 실패한 것만** 제한적으로 fetch.

사용:
    from hit_predictor.data.namuwiki_fetcher import NamuwikiClient
    client = NamuwikiClient()
    meta = client.fetch_drama_meta("선재 업고 튀어")
"""
from __future__ import annotations

import re
import time
from typing import Optional
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

from .wikipedia_fetcher import (
    DramaMeta, parse_day_slot, parse_time_slot, parse_rating,
)

NAMU_BASE = "https://namu.wiki/w/"
USER_AGENT = "k-drama-hit-predictor/2.0 (research; https://github.com/kimble125/k-drama-hit-predictor)"
REQUEST_DELAY = 2.0  # 나무위키는 천천히


class NamuwikiClient:
    def __init__(self, user_agent: str = USER_AGENT, delay: float = REQUEST_DELAY):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        self.delay = delay

    def fetch_html(self, title: str) -> Optional[str]:
        """나무위키 페이지 HTML 가져오기."""
        url = NAMU_BASE + quote(title)
        try:
            r = self.session.get(url, timeout=20)
            r.raise_for_status()
            time.sleep(self.delay)
            if r.status_code == 200:
                return r.text
            return None
        except Exception as e:
            print(f"  [나무위키 오류] {title}: {e}")
            time.sleep(self.delay)
            return None

    def fetch_drama_meta(self, drama_title: str) -> Optional[DramaMeta]:
        """나무위키에서 드라마 메타 수집."""
        html = self.fetch_html(drama_title)
        if not html:
            return None

        soup = BeautifulSoup(html, "html.parser")
        meta = DramaMeta(title=drama_title, wiki_page_title=drama_title)
        parse_namuwiki_page(soup, meta)
        return meta if _has_useful_data(meta) else None


def _has_useful_data(meta: DramaMeta) -> bool:
    """의미있는 정보가 하나라도 있으면 True."""
    return any([
        meta.channel, meta.day_slot, meta.time_slot,
        meta.avg_rating, meta.max_rating,
    ])


def parse_namuwiki_page(soup: BeautifulSoup, meta: DramaMeta) -> None:
    """나무위키 페이지 HTML에서 정보 추출.

    나무위키는 인포박스가 <table class="wiki-table">의 첫 번째 테이블.
    필드명-값 쌍이 <tr><th>필드명</th><td>값</td></tr> 형태.
    """
    # 전체 텍스트에서 주요 패턴 찾기 (infobox 셀 구조 다양성 대응)
    text = soup.get_text("\n", strip=True)

    # 방영 시간 찾기
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue

        if any(kw in line for kw in ("방영 시간", "방송 시간", "편성 시간")):
            if not meta.day_slot:
                ds = parse_day_slot(line)
                if ds:
                    meta.day_slot = ds
            if not meta.time_slot:
                ts = parse_time_slot(line)
                if ts:
                    meta.time_slot = ts

        if any(kw in line for kw in ("방송국", "방영 채널", "방송 채널", "채널")):
            if not meta.channel:
                # "방송국 [[tvN]]" 류에서 채널 후보 찾기
                m = re.search(r"(KBS[12]?|MBC|SBS|tvN|JTBC|ENA|채널A|MBN|TV조선|OCN|Netflix|Disney\+|TVING|웨이브|쿠팡플레이)",
                              line)
                if m:
                    meta.channel = m.group(1)

        if "평균 시청률" in line or "평균시청률" in line:
            r = parse_rating(line)
            if r and not meta.avg_rating:
                meta.avg_rating = r

        if "최고 시청률" in line or "최고시청률" in line:
            r = parse_rating(line)
            if r and not meta.max_rating:
                meta.max_rating = r

        if "에피소드" in line or "회차" in line or "방영 횟수" in line:
            m = re.search(r"(\d+)\s*부작", line) or re.search(r"전\s*(\d+)\s*화", line)
            if m and not meta.episodes:
                try:
                    meta.episodes = int(m.group(1))
                except ValueError:
                    pass
