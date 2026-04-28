#!/usr/bin/env python3
"""
통합 필모그래피 JSON을 개별 Person 파일로 분리
==============================================
입력: data/filmography_merged.json (TMDB로 긁은 통합 파일)
출력: data/filmography/{actors|directors|writers}/{name}.json

자동 수정 사항:
    1. is_lead: 배우 이름으로 검색한 것이므로 모두 True로 변경
       (감독/작가는 원래 True)
    2. 빈 크레디트 Person은 플레이스홀더로 저장 (0편)
"""
import json
import sys
from pathlib import Path


def split_and_save(
    merged_path: Path,
    out_root: Path,
) -> dict:
    """통합 파일 분리 + 저장."""
    with merged_path.open(encoding="utf-8") as f:
        data = json.load(f)

    role_to_dir = {"actors": "actors", "directors": "directors", "writers": "writers"}
    stats = {"actors": 0, "directors": 0, "writers": 0, "empty": [], "is_lead_fixed": 0}

    for role_key, people in data.items():
        if role_key not in role_to_dir:
            continue
        role_singular = {"actors": "actor", "directors": "director", "writers": "writer"}[role_key]
        out_dir = out_root / role_to_dir[role_key]
        out_dir.mkdir(parents=True, exist_ok=True)

        for name, person_data in people.items():
            # is_lead 일괄 True (배우 이름으로 검색한 것이므로)
            credits = person_data.get("credits", [])
            if role_singular == "actor":
                for c in credits:
                    if not c.get("is_lead"):
                        c["is_lead"] = True
                        stats["is_lead_fixed"] += 1

            # primary_role 표준화
            person_data["primary_role"] = role_singular
            person_data["credits"] = credits

            # 저장
            out_path = out_dir / f"{name}.json"
            with out_path.open("w", encoding="utf-8") as f:
                json.dump(person_data, f, ensure_ascii=False, indent=2)

            stats[role_key] += 1
            if not credits:
                stats["empty"].append(f"{role_singular}: {name}")

    return stats


if __name__ == "__main__":
    merged = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/filmography_merged.json")
    out_root = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("data/filmography")

    if not merged.exists():
        print(f"❌ 파일 없음: {merged}")
        sys.exit(1)

    print(f"📂 로드: {merged}")
    print(f"💾 저장: {out_root}/")
    stats = split_and_save(merged, out_root)

    print(f"\n✅ 분리 완료:")
    print(f"   배우:   {stats['actors']}명")
    print(f"   감독:   {stats['directors']}명")
    print(f"   작가:   {stats['writers']}명")
    print(f"   is_lead 수정: {stats['is_lead_fixed']}개 크레디트")
    if stats["empty"]:
        print(f"\n⚠️  빈 필모그래피 ({len(stats['empty'])}명):")
        for e in stats["empty"]:
            print(f"   - {e}")
