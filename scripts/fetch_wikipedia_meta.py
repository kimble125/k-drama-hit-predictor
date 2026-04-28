#!/usr/bin/env python3
"""
필모그래피의 모든 드라마에 대해 위키백과 메타데이터 수집
========================================================
data/filmography/**/*.json의 모든 drama_title을 추출해
위키백과 ko에서 방영 요일/시간/시청률을 가져와 주입.

⚠️ 네트워크 필요. Claude 샌드박스 차단. 로컬에서 실행하세요:

    pip install requests
    cd ~/projects/k-drama-hit-predictor
    python scripts/fetch_wikipedia_meta.py

결과:
    - data/wikipedia_meta.json: 수집된 메타 전체 (백업)
    - data/filmography/**/*.json: day_slot, time_slot, avg_rating, max_rating 병합됨
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from hit_predictor.data.wikipedia_fetcher import WikipediaClient


def collect_all_drama_titles(filmography_dir: Path) -> set[str]:
    """필모그래피 전체 순회해서 고유 드라마 제목 추출."""
    titles = set()
    for subdir in ("actors", "directors", "writers"):
        dpath = filmography_dir / subdir
        if not dpath.exists():
            continue
        for json_file in dpath.glob("*.json"):
            with json_file.open(encoding="utf-8") as f:
                data = json.load(f)
            for c in data.get("credits", []):
                t = c.get("drama_title", "").strip()
                if t:
                    titles.add(t)
    return titles


def merge_meta_into_credit(credit: dict, meta: dict) -> dict:
    """위키 메타를 Credit에 주입. 기존 값 덮어쓰지 않음 (닐슨 우선)."""
    if not credit.get("day_slot") and meta.get("day_slot"):
        credit["day_slot"] = meta["day_slot"]
    if not credit.get("time_slot") and meta.get("time_slot"):
        credit["time_slot"] = meta["time_slot"]
    if credit.get("avg_rating") is None and meta.get("avg_rating") is not None:
        credit["avg_rating"] = meta["avg_rating"]
    if credit.get("max_rating") is None and meta.get("max_rating") is not None:
        credit["max_rating"] = meta["max_rating"]
    if not credit.get("channel") and meta.get("channel"):
        credit["channel"] = meta["channel"]
    notes = credit.get("notes", "")
    if "wiki_matched" not in notes:
        credit["notes"] = f"{notes}|wiki_matched".strip("|")
    return credit


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    filmography_dir = root / "data" / "filmography"
    cache_file = root / "data" / "wikipedia_meta.json"

    # 1. 모든 드라마 제목 수집
    print("📋 필모그래피에서 드라마 제목 추출 중...")
    titles = collect_all_drama_titles(filmography_dir)
    print(f"   고유 드라마: {len(titles)}편\n")

    # 2. 캐시 로드
    cache = {}
    if cache_file.exists():
        with cache_file.open(encoding="utf-8") as f:
            cache = json.load(f)
        print(f"📦 기존 캐시: {len(cache)}편\n")

    # 3. 위키 수집
    client = WikipediaClient()
    new_count = 0
    failed = []

    for i, title in enumerate(sorted(titles), 1):
        # 캐시 스킵 조건:
        # 1) not_found가 아니어야 함 (재시도 안 함)
        # 2) avg_rating이 채워져 있어야 함 (없으면 재스크래핑 — 본문 섹션 fallback이 도입되었으므로)
        if title in cache:
            cached = cache[title]
            has_rating = cached.get("avg_rating") is not None
            is_not_found = cached.get("notes") == "not_found"
            # not_found는 재시도 안 함 (위키에 정말 없는 것)
            # 단, rating이 없으면 재스크래핑 (parse_rating_section 도입 후 재시도 필요)
            if is_not_found or has_rating:
                continue
        print(f"  [{i}/{len(titles)}] {title} ... ", end="", flush=True)
        try:
            meta = client.fetch_drama_meta(title)
            if meta:
                cache[title] = meta.to_dict()
                fields = [k for k in ("day_slot", "time_slot", "avg_rating", "max_rating")
                          if cache[title].get(k) is not None]
                print(f"✓ {fields if fields else '(페이지만 있음)'}")
                new_count += 1
            else:
                cache[title] = {"title": title, "notes": "not_found"}
                print("✗ 미등록")
                failed.append(title)
        except Exception as e:
            print(f"오류: {e}")
            failed.append(title)
            time.sleep(2)

        # 중간 저장
        if new_count > 0 and new_count % 10 == 0:
            with cache_file.open("w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)

    # 4. 최종 캐시 저장
    with cache_file.open("w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    print(f"\n💾 캐시 저장: {cache_file}")

    # 5. 필모그래피에 병합
    print(f"\n🔄 필모그래피에 메타 병합 중...")
    updated_credits = 0
    updated_persons = 0
    for subdir in ("actors", "directors", "writers"):
        dpath = filmography_dir / subdir
        if not dpath.exists():
            continue
        for json_file in dpath.glob("*.json"):
            with json_file.open(encoding="utf-8") as f:
                person = json.load(f)
            changed = False
            for c in person.get("credits", []):
                meta = cache.get(c.get("drama_title"))
                if meta and meta.get("notes") != "not_found":
                    before = (c.get("day_slot"), c.get("time_slot"),
                              c.get("avg_rating"), c.get("max_rating"))
                    merge_meta_into_credit(c, meta)
                    after = (c.get("day_slot"), c.get("time_slot"),
                             c.get("avg_rating"), c.get("max_rating"))
                    if before != after:
                        changed = True
                        updated_credits += 1
            if changed:
                with json_file.open("w", encoding="utf-8") as f:
                    json.dump(person, f, ensure_ascii=False, indent=2)
                updated_persons += 1

    # 요약
    print(f"\n✅ 완료")
    print(f"   수집: {len(cache)}편 (신규 {new_count}편)")
    print(f"   실패: {len(failed)}편")
    print(f"   병합된 인물: {updated_persons}명")
    print(f"   병합된 크레디트: {updated_credits}개")
    if failed:
        print(f"\n⚠️  위키 미등록 드라마 (수기 보완 또는 나무위키 fetch 필요):")
        for t in failed[:20]:
            print(f"   - {t}")
        if len(failed) > 20:
            print(f"   ... 외 {len(failed) - 20}편")


if __name__ == "__main__":
    main()
