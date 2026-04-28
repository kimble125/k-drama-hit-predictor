#!/usr/bin/env python3
"""
위키백과에서 못 찾은 드라마만 나무위키에서 보완
=============================================
data/wikipedia_meta.json에서 notes=="not_found" 인 것만 대상.

⚠️ 네트워크 + 나무위키 CC BY-NC-SA 라이센스 준수.
    로컬에서만, 천천히 실행.

사용:
    pip install requests beautifulsoup4 lxml
    python scripts/fetch_namuwiki_fallback.py
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from hit_predictor.data.namuwiki_fetcher import NamuwikiClient


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    wiki_cache = root / "data" / "wikipedia_meta.json"
    namu_cache = root / "data" / "namuwiki_meta.json"

    if not wiki_cache.exists():
        print(f"❌ 먼저 fetch_wikipedia_meta.py 실행 필요")
        sys.exit(1)

    with wiki_cache.open(encoding="utf-8") as f:
        wiki_data = json.load(f)

    # 위키 실패 목록
    failed_titles = [
        title for title, meta in wiki_data.items()
        if meta.get("notes") == "not_found"
    ]
    print(f"📋 위키백과 실패: {len(failed_titles)}편\n")

    namu_data = {}
    if namu_cache.exists():
        with namu_cache.open(encoding="utf-8") as f:
            namu_data = json.load(f)

    client = NamuwikiClient()

    for i, title in enumerate(failed_titles, 1):
        if title in namu_data:
            continue
        print(f"  [{i}/{len(failed_titles)}] {title} ... ", end="", flush=True)
        try:
            meta = client.fetch_drama_meta(title)
            if meta:
                namu_data[title] = meta.to_dict()
                fields = [k for k in ("day_slot", "time_slot", "avg_rating", "max_rating")
                          if meta.to_dict().get(k) is not None]
                print(f"✓ {fields if fields else '(페이지만 있음)'}")
            else:
                namu_data[title] = {"title": title, "notes": "not_found_namu"}
                print("✗")
        except Exception as e:
            print(f"오류: {e}")
            time.sleep(3)

        # 중간 저장
        if (i % 5) == 0:
            with namu_cache.open("w", encoding="utf-8") as f:
                json.dump(namu_data, f, ensure_ascii=False, indent=2)

    with namu_cache.open("w", encoding="utf-8") as f:
        json.dump(namu_data, f, ensure_ascii=False, indent=2)

    print(f"\n💾 저장: {namu_cache}")
    print(f"   성공: {sum(1 for v in namu_data.values() if v.get('notes') != 'not_found_namu')}편")


if __name__ == "__main__":
    main()
