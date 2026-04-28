"""
위키백과 ko 드라마 메타데이터 수집기
====================================
한국어 위키백과에서 드라마 페이지의 인포박스를 파싱하여
방영일/요일/시간/시청률/채널을 추출.

⚠️ 네트워크 필요:
    api.wikipedia.org, ko.wikipedia.org 접근 필요.
    Claude 샌드박스에선 차단. 로컬 실행 권장.

API 엔드포인트:
    - 검색: https://ko.wikipedia.org/w/api.php?action=opensearch&search={title}&limit=5
    - 파싱: https://ko.wikipedia.org/w/api.php?action=parse&page={title}&prop=wikitext&format=json

추출 정보 (인포박스 기준):
    - 방송 채널 (방송 채널, 방송사, 방송국)
    - 방영 기간 (방영 기간, 방송 기간)
    - 방영 시간 (방송 시간, 편성 시간)
    - 평균 시청률 (시청률, 평균 시청률)
    - 최고 시청률 (최고 시청률)
    - 회수 (회수, 회차)

사용:
    client = WikipediaClient()
    meta = client.fetch_drama_meta("선재 업고 튀어")
    # → {"channel": "tvN", "day_slot": "월화", "time_slot": "22:20",
    #    "avg_rating": 4.1, "max_rating": 5.8, ...}
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, asdict
from typing import Optional
from urllib.parse import quote

import requests

WIKI_API = "https://ko.wikipedia.org/w/api.php"
USER_AGENT = "k-drama-hit-predictor/2.0 (research; https://github.com/kimble125/k-drama-hit-predictor)"
REQUEST_DELAY = 0.2   # 위키백과 공식 가이드: 200 req/s 이하


# ────────────────────────────────────────────────────────────────
# 추출 정규식
# ────────────────────────────────────────────────────────────────
# 인포박스 필드 라인: "| 방송 채널 = [[tvN]]"
INFOBOX_FIELD = re.compile(r"^\|\s*([^=]+?)\s*=\s*(.+?)$", re.MULTILINE)

# 시청률: "4.1%", "평균 4.1% (닐슨)", "최고 12.3%"
RATING_PATTERN = re.compile(r"(\d+\.?\d*)\s*%")

# 방영 시간: "월·화 오후 10시 20분", "수·목 22:30"
# 요일 부분
DAY_WORDS = {
    "월": "월", "화": "화", "수": "수", "목": "목", "금": "금", "토": "토", "일": "일",
}
DAY_SLOT_PATTERNS = [
    re.compile(r"([월화수목금토일])\s*·\s*([월화수목금토일])"),  # 월·화
    re.compile(r"([월화수목금토일])[,\s]+([월화수목금토일])"),     # 월, 화
]

# 시간: "오후 10시 20분", "22:20", "22시 20분"
TIME_PATTERNS = [
    re.compile(r"(\d{1,2}):(\d{2})"),
    re.compile(r"(\d{1,2})시\s*(\d{1,2})분"),
    re.compile(r"오후\s*(\d{1,2})시(?:\s*(\d{1,2})분)?"),
    re.compile(r"오전\s*(\d{1,2})시(?:\s*(\d{1,2})분)?"),
    re.compile(r"밤\s*(\d{1,2})시(?:\s*(\d{1,2})분)?"),
]

# 위키 링크: [[tvN]] → tvN, [[tvN|티비엔]] → tvN
WIKI_LINK = re.compile(r"\[\[([^|\]]+)(?:\|[^\]]+)?\]\]")
HTML_TAG = re.compile(r"<[^>]+>")
# {{플래그|KR}} 같은 템플릿 제거
TEMPLATE = re.compile(r"\{\{[^}]+\}\}")


# ────────────────────────────────────────────────────────────────
# 결과 스키마
# ────────────────────────────────────────────────────────────────
@dataclass
class DramaMeta:
    title: str
    wiki_page_title: Optional[str] = None
    channel: Optional[str] = None
    day_slot: Optional[str] = None      # "월화", "수목" 등
    time_slot: Optional[str] = None     # "22:00", "22:20"
    avg_rating: Optional[float] = None
    max_rating: Optional[float] = None
    first_ep_rating: Optional[float] = None
    episodes: Optional[int] = None
    release_start: Optional[str] = None
    release_end: Optional[str] = None
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ────────────────────────────────────────────────────────────────
# 클라이언트
# ────────────────────────────────────────────────────────────────
class WikipediaClient:
    def __init__(self, user_agent: str = USER_AGENT, delay: float = REQUEST_DELAY):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        self.delay = delay

    def _get(self, **params) -> dict:
        params.setdefault("format", "json")
        params.setdefault("formatversion", "2")
        r = self.session.get(WIKI_API, params=params, timeout=15)
        r.raise_for_status()
        time.sleep(self.delay)
        return r.json()

    def search(self, query: str, limit: int = 5) -> list[str]:
        """드라마 제목으로 위키 페이지 검색."""
        try:
            data = self._get(action="opensearch", search=query, limit=limit, namespace=0)
            return data[1] if len(data) > 1 else []
        except Exception as e:
            print(f"  [검색 오류] {query}: {e}")
            return []

    def get_wikitext(self, page_title: str) -> Optional[str]:
        """페이지의 원본 위키텍스트 가져오기."""
        try:
            data = self._get(action="parse", page=page_title, prop="wikitext")
            return data.get("parse", {}).get("wikitext")
        except Exception as e:
            print(f"  [파싱 오류] {page_title}: {e}")
            return None

    def fetch_drama_meta(self, drama_title: str) -> Optional[DramaMeta]:
        """드라마 제목 → 메타데이터."""
        # 1. 검색 (후보 중 "드라마" 포함 우선)
        candidates = self.search(drama_title, limit=5)
        if not candidates:
            return None

        # 후보 중 "(드라마)" 태그 있는 것 우선, 없으면 첫번째
        page_title = None
        for c in candidates:
            if "드라마" in c or "텔레비전" in c:
                page_title = c
                break
        if page_title is None:
            page_title = candidates[0]

        # 2. 위키텍스트 파싱
        wikitext = self.get_wikitext(page_title)
        if not wikitext:
            return None

        meta = DramaMeta(title=drama_title, wiki_page_title=page_title)
        parse_infobox(wikitext, meta)

        # 3. 인포박스에 시청률 정보가 없을 경우, '== 시청률 ==' 섹션 fallback
        # (위키백과 한국어판은 인포박스가 아니라 본문에 시청률 표를 두는 경우 多)
        if meta.avg_rating is None or meta.max_rating is None:
            parse_rating_section(wikitext, meta)

        return meta


# ────────────────────────────────────────────────────────────────
# 파서 (의존성 없는 순수 함수)
# ────────────────────────────────────────────────────────────────
def clean_value(val: str) -> str:
    """위키 링크, HTML 태그 제거하고 정리."""
    if not val:
        return ""
    val = TEMPLATE.sub("", val)
    val = WIKI_LINK.sub(r"\1", val)
    val = HTML_TAG.sub(" ", val)
    return val.strip()


def extract_infobox(wikitext: str) -> dict:
    """{{Infobox ...}} 블록에서 필드 추출."""
    # 인포박스 시작 위치 찾기
    start = wikitext.find("{{")
    if start < 0:
        return {}

    # 매칭되는 }} 찾기 (중첩 처리)
    depth = 0
    end = start
    while end < len(wikitext) - 1:
        if wikitext[end:end+2] == "{{":
            depth += 1
            end += 2
        elif wikitext[end:end+2] == "}}":
            depth -= 1
            end += 2
            if depth == 0:
                break
        else:
            end += 1

    if depth != 0:
        return {}

    infobox_text = wikitext[start:end]
    # 필드 추출
    fields = {}
    for m in INFOBOX_FIELD.finditer(infobox_text):
        key = m.group(1).strip()
        val = clean_value(m.group(2))
        fields[key] = val
    return fields


def parse_day_slot(text: str) -> Optional[str]:
    """'월·화' / '월,화' → '월화' 정규화."""
    if not text:
        return None
    for pat in DAY_SLOT_PATTERNS:
        m = pat.search(text)
        if m:
            return m.group(1) + m.group(2)
    return None


def parse_time_slot(text: str) -> Optional[str]:
    """방영 시간 문자열 → 'HH:MM' 정규화."""
    if not text:
        return None
    # 24시간제 HH:MM
    m = TIME_PATTERNS[0].search(text)
    if m:
        h, mm = int(m.group(1)), int(m.group(2))
        return f"{h:02d}:{mm:02d}"
    # 한국어 "22시 20분"
    m = TIME_PATTERNS[1].search(text)
    if m:
        h, mm = int(m.group(1)), int(m.group(2))
        return f"{h:02d}:{mm:02d}"
    # "오후 10시 20분" → 22:20
    m = TIME_PATTERNS[2].search(text)
    if m:
        h = int(m.group(1)) + (12 if int(m.group(1)) < 12 else 0)
        mm = int(m.group(2)) if m.group(2) else 0
        return f"{h:02d}:{mm:02d}"
    # "밤 10시 20분" → 22:20
    m = TIME_PATTERNS[4].search(text)
    if m:
        h = int(m.group(1)) + (12 if int(m.group(1)) < 12 else 0)
        mm = int(m.group(2)) if m.group(2) else 0
        return f"{h:02d}:{mm:02d}"
    return None


def parse_rating(text: str) -> Optional[float]:
    """시청률 문자열 → float (첫 등장 값)."""
    if not text:
        return None
    m = RATING_PATTERN.search(text)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return None
    return None


def parse_infobox(wikitext: str, meta: DramaMeta) -> None:
    """wikitext 파싱해서 DramaMeta에 필드 채우기."""
    infobox = extract_infobox(wikitext)

    # 채널
    for k in ("방송 채널", "방송사", "방송국", "제작 방송국", "채널"):
        if k in infobox:
            meta.channel = infobox[k].split()[0] if infobox[k] else None
            if meta.channel:
                break

    # 방영 시간대
    time_text = None
    for k in ("방송 시간", "편성 시간", "방영 시간"):
        if k in infobox:
            time_text = infobox[k]
            break
    if time_text:
        meta.day_slot = parse_day_slot(time_text)
        meta.time_slot = parse_time_slot(time_text)

    # 방영 기간
    for k in ("방영 기간", "방송 기간"):
        if k in infobox:
            date_text = infobox[k]
            # ~ 로 시작/끝 분리
            parts = re.split(r"\s*[~–-]\s*", date_text)
            if parts:
                meta.release_start = parts[0].strip()
                if len(parts) > 1:
                    meta.release_end = parts[1].strip()
            break

    # 시청률
    for k in ("평균 시청률", "평균시청률", "시청률"):
        if k in infobox:
            meta.avg_rating = parse_rating(infobox[k])
            if meta.avg_rating:
                break
    for k in ("최고 시청률", "최고시청률"):
        if k in infobox:
            meta.max_rating = parse_rating(infobox[k])
            if meta.max_rating:
                break

    # 에피소드
    for k in ("회수", "회차", "에피소드"):
        if k in infobox:
            try:
                m = re.search(r"(\d+)", infobox[k])
                if m:
                    meta.episodes = int(m.group(1))
                    break
            except (ValueError, AttributeError):
                pass


# ────────────────────────────────────────────────────────────────
# 본문 '== 시청률 ==' 섹션 파서 (인포박스 fallback)
# ────────────────────────────────────────────────────────────────
RATING_SECTION_PATTERN = re.compile(
    r"==\s*시청률(?:\s*표)?\s*==(.+?)(?===|$)",
    re.DOTALL,
)


def parse_rating_section(wikitext: str, meta: DramaMeta) -> None:
    """위키텍스트의 '== 시청률 ==' 섹션에서 평균/최고 시청률 추출.

    한국어 위키백과는 드라마 페이지 본문 하단에 회차별 시청률 표를 두는 경우가
    많은데, 이 표가 인포박스보다 더 정확한 통계를 담는다. 인포박스 파싱이 실패하면
    이 본문 섹션을 fallback으로 사용한다.

    추출 패턴:
        - "평균 시청률 X.XX%" / "전국 평균: X.XX%" / "수도권 평균 X.XX%"
        - "최고 시청률 X.XX%" / "전국 최고 X.XX%" 등
        - 표 안의 모든 시청률 숫자 → 평균 / 최댓값 추정
    """
    m = RATING_SECTION_PATTERN.search(wikitext)
    if not m:
        return

    section_text = m.group(1)

    # 1. 명시적인 "평균 시청률" / "최고 시청률" 라벨 우선
    if meta.avg_rating is None:
        avg_m = re.search(
            r"(?:평균\s*시청률|전국\s*평균|평균)[:\s]*(\d+\.?\d*)\s*%",
            section_text,
        )
        if avg_m:
            try:
                meta.avg_rating = float(avg_m.group(1))
            except ValueError:
                pass

    if meta.max_rating is None:
        max_m = re.search(
            r"(?:최고\s*시청률|최고|최대치)[:\s]*(\d+\.?\d*)\s*%",
            section_text,
        )
        if max_m:
            try:
                meta.max_rating = float(max_m.group(1))
            except ValueError:
                pass

    # 2. 라벨이 없으면 표 안의 모든 % 숫자 추출 → 평균/최대 통계화
    if meta.avg_rating is None or meta.max_rating is None:
        ratings = []
        for rm in re.finditer(r"(\d+\.\d+)\s*%", section_text):
            try:
                v = float(rm.group(1))
                # 시청률 범위 sanity check (0.1~50%)
                if 0.1 <= v <= 50.0:
                    ratings.append(v)
            except ValueError:
                continue

        if ratings:
            if meta.avg_rating is None:
                meta.avg_rating = round(sum(ratings) / len(ratings), 2)
            if meta.max_rating is None:
                meta.max_rating = max(ratings)
