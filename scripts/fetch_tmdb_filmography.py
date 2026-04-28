#!/usr/bin/env python3
"""
TMDB로 필모그래피 자동 수집
===========================
이름 리스트를 주면 TMDB API로 필모그래피를 자동 수집하고
data/filmography/ 아래에 JSON으로 저장.

⚠️ Claude 샌드박스에서는 TMDB 접근이 차단되어 실행되지 않습니다.
   미루님 로컬 환경에서 실행하세요.

사용:
    # 환경변수 설정 (.env 또는 export)
    export TMDB_READ_TOKEN='eyJhbGciOiJIUzI1NiJ9...'

    # 단일 수집
    python scripts/fetch_tmdb_filmography.py --actor "아이유"
    python scripts/fetch_tmdb_filmography.py --director "이응복"

    # 배치 (CSV에서 이름 추출)
    python scripts/fetch_tmdb_filmography.py --from-csv data/candidate_dramas.csv

    # 빠른 모드 (채널 정보 생략, 10배 빠름)
    python scripts/fetch_tmdb_filmography.py --actor "아이유" --fast
"""
import argparse
import csv
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from hit_predictor.rsi.tmdb_fetcher import TMDBClient, fetch_and_save_person, batch_fetch


def extract_names_from_csv(csv_path: Path) -> dict:
    """CSV에서 lead_actors, director, writer 컬럼의 이름들을 추출."""
    actors, directors, writers = set(), set(), set()
    with csv_path.open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("lead_actors"):
                for name in row["lead_actors"].split("|"):
                    name = name.strip()
                    if name:
                        actors.add(name)
            if row.get("director"):
                directors.add(row["director"].strip())
            if row.get("writer"):
                writers.add(row["writer"].strip())
    return {
        "actors": sorted(actors),
        "directors": sorted(directors),
        "writers": sorted(writers),
    }


def main():
    parser = argparse.ArgumentParser(description="TMDB 필모그래피 자동 수집")
    parser.add_argument("--actor", help="단일 배우 이름")
    parser.add_argument("--director", help="단일 감독 이름")
    parser.add_argument("--writer", help="단일 작가 이름")
    parser.add_argument("--from-csv", help="CSV에서 이름 추출해 배치 수집")
    parser.add_argument("--fast", action="store_true",
                        help="채널 정보 조회 생략 (10배 빠름, 단 channel=None)")
    parser.add_argument("--token", help="TMDB Read Token (환경변수 대신)")
    parser.add_argument("--out-dir", default="data/filmography",
                        help="저장 경로 (기본: data/filmography)")
    args = parser.parse_args()

    token = args.token or os.environ.get("TMDB_READ_TOKEN")
    if not token:
        print("❌ TMDB_READ_TOKEN 환경변수 또는 --token 필수.")
        print("   export TMDB_READ_TOKEN='eyJ...'")
        sys.exit(1)

    print("=" * 60)
    print(" TMDB Filmography Fetcher")
    print(" Source: https://www.themoviedb.org/")
    print("=" * 60 + "\n")

    client = TMDBClient(read_token=token)
    enrich = not args.fast
    root = Path(args.out_dir)

    if args.from_csv:
        csv_path = Path(args.from_csv)
        if not csv_path.exists():
            print(f"❌ CSV 없음: {csv_path}")
            sys.exit(1)
        names = extract_names_from_csv(csv_path)
        print(f"📋 {csv_path}에서 추출:")
        print(f"   배우: {len(names['actors'])}명")
        print(f"   감독: {len(names['directors'])}명")
        print(f"   작가: {len(names['writers'])}명\n")

        result = batch_fetch(
            client,
            actors=names["actors"],
            directors=names["directors"],
            writers=names["writers"],
            root=root,
            enrich_with_details=enrich,
        )
        print(f"\n✅ 완료: 배우 {len(result['actors'])}, "
              f"감독 {len(result['directors'])}, 작가 {len(result['writers'])}")
        return

    # 단일 모드
    targets = []
    if args.actor:
        targets.append((args.actor, "actor"))
    if args.director:
        targets.append((args.director, "director"))
    if args.writer:
        targets.append((args.writer, "writer"))

    if not targets:
        parser.print_help()
        sys.exit(1)

    for name, role in targets:
        print(f"\n🔍 {role}: {name}")
        person = fetch_and_save_person(client, name, role, root=root,
                                        enrich_with_details=enrich)
        if person:
            print(f"  ✅ {len(person.credits)}편 수집")
            for c in person.credits[:5]:
                ch = c.channel or "?"
                print(f"     {c.year} {c.drama_title} ({ch})")
            if len(person.credits) > 5:
                print(f"     ... 외 {len(person.credits) - 5}편")
        else:
            print(f"  ❌ 수집 실패")


if __name__ == "__main__":
    main()
