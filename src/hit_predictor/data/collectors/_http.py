"""
HTTP 수집 공통 헬퍼
====================
모든 데이터 수집기가 공유하는 정중한(polite) HTTP 클라이언트.

기능:
    - 프로젝트 식별 User-Agent
    - 소스별 차등 rate limit (사이트마다 robots.txt 권장값이 다름)
    - robots.txt 자동 캐싱·검사
    - 재시도 + 지수 백오프
    - 출처 표기(attribution) 자동 생성 — 라이센스 준수

사용:
    from hit_predictor.data.collectors._http import polite_get, attribution_for
    r = polite_get('https://namu.wiki/w/...', source_key='namuwiki')
    html = r.text
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests


USER_AGENT = (
    "KDramaHitPredictor/3.0 "
    "(Research; Hit prediction model; "
    "+https://github.com/kimble125/k-drama-hit-predictor)"
)

# 소스별 권장 delay (초). 사이트 robots.txt·이용약관 기반 보수적 기본값.
RATE_LIMIT_BY_SOURCE: dict[str, float] = {
    "namuwiki": 3.0,         # CC BY-NC-SA, 적극적 차단
    "wikipedia": 1.0,        # API 친화적
    "tmdb": 0.25,            # 4 RPS 정도가 안전
    "nielsen": 1.5,          # 이용약관 명시 — 보수적
    "naver": 1.0,            # Naver DataLab quota 별도
    "youtube": 0.0,          # YouTube Data API quota 별도
    "_default": 2.0,
}

# 출처 표기 — 결과 JSON의 attribution 필드에 자동 기록.
ATTRIBUTION: dict[str, str] = {
    "namuwiki": "나무위키 (CC BY-NC-SA 2.0 KR) — 비상업적 이용 허용, 출처 명시",
    "wikipedia": "위키백과 (CC BY-SA 4.0)",
    "tmdb": "TMDB (https://www.themoviedb.org/) — This product uses the TMDB API but is not endorsed or certified by TMDB.",
    "nielsen": "닐슨코리아 — 개인 연구 용도(재배포·재판매 금지)",
    "naver": "Naver DataLab",
    "youtube": "YouTube Data API",
}


_last_request_time: dict[str, float] = {}
_robots_cache: dict[str, Optional[RobotFileParser]] = {}


def get_delay(source_key: str) -> float:
    return RATE_LIMIT_BY_SOURCE.get(source_key, RATE_LIMIT_BY_SOURCE["_default"])


def attribution_for(source_key: str) -> str:
    """출처 표기 문자열 — 결과 JSON의 attribution 필드 등에 기록."""
    return ATTRIBUTION.get(source_key, source_key)


def _enforce_rate_limit(source_key: str) -> None:
    delay = get_delay(source_key)
    if delay <= 0:
        return
    now = time.time()
    elapsed = now - _last_request_time.get(source_key, 0.0)
    if elapsed < delay:
        time.sleep(delay - elapsed)
    _last_request_time[source_key] = time.time()


def _get_robots(url: str) -> Optional[RobotFileParser]:
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    if base in _robots_cache:
        return _robots_cache[base]
    rp = RobotFileParser()
    rp.set_url(urljoin(base, "/robots.txt"))
    try:
        rp.read()
    except Exception:
        _robots_cache[base] = None
        return None
    _robots_cache[base] = rp
    return rp


def can_fetch(url: str, user_agent: str = USER_AGENT) -> bool:
    """robots.txt 기반 fetch 허용 여부. robots.txt 부재 시 허용."""
    rp = _get_robots(url)
    if rp is None:
        return True
    try:
        return rp.can_fetch(user_agent, url)
    except Exception:
        return True


@dataclass
class FetchResult:
    url: str
    status_code: int
    text: str
    headers: dict
    elapsed_seconds: float

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300


class RobotsDisallowedError(PermissionError):
    """robots.txt가 명시적으로 disallow한 URL을 fetch하려 한 경우."""


def polite_get(
    url: str,
    source_key: str = "_default",
    timeout: int = 30,
    max_retries: int = 3,
    backoff_base: float = 2.0,
    extra_headers: Optional[dict] = None,
    check_robots: bool = True,
) -> FetchResult:
    """정중한 GET — 소스별 rate limit, robots.txt 검사, 재시도+백오프.

    Args:
        url: 요청 URL
        source_key: 소스 식별자 (RATE_LIMIT_BY_SOURCE 키)
        timeout: HTTP 타임아웃
        max_retries: 5xx/네트워크 오류 재시도 횟수
        backoff_base: 지수 백오프 베이스
        extra_headers: 추가 헤더
        check_robots: robots.txt 검사 여부

    Raises:
        RobotsDisallowedError: robots.txt가 disallow일 때
        requests.HTTPError: 4xx (재시도 안함)
        requests.RequestException: 모든 재시도 실패
    """
    if check_robots and not can_fetch(url):
        raise RobotsDisallowedError(f"robots.txt disallows: {url}")

    headers = {"User-Agent": USER_AGENT, "Accept-Language": "ko,en;q=0.8"}
    if extra_headers:
        headers.update(extra_headers)

    last_exc: Optional[Exception] = None
    for attempt in range(max_retries):
        _enforce_rate_limit(source_key)
        try:
            t0 = time.time()
            r = requests.get(url, headers=headers, timeout=timeout)
            elapsed = time.time() - t0
            if r.status_code == 429 or 500 <= r.status_code < 600:
                # 429(Too Many Requests) + 5xx는 재시도. Retry-After 헤더 존중.
                retry_after = r.headers.get("Retry-After")
                wait = float(retry_after) if retry_after and retry_after.isdigit() else (backoff_base ** attempt)
                last_exc = requests.HTTPError(f"{r.status_code}: {url}")
                time.sleep(wait)
                continue
            r.raise_for_status()
            r.encoding = r.encoding or "utf-8"
            return FetchResult(
                url=url, status_code=r.status_code, text=r.text,
                headers=dict(r.headers), elapsed_seconds=elapsed,
            )
        except (requests.Timeout, requests.ConnectionError) as e:
            last_exc = e
            time.sleep(backoff_base ** attempt)
        except requests.HTTPError:
            raise
    raise last_exc or requests.RequestException(
        f"Failed after {max_retries} retries: {url}"
    )
