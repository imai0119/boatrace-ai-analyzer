
import json
import os
from collections import defaultdict
from datetime import datetime, timezone, timedelta

RAW_DIR = "data/races"
OUTPUT = "data/boat6_analysis.json"
JST = timezone(timedelta(hours=9))

VENUES = {
    1: "桐生", 2: "戸田", 3: "江戸川", 4: "平和島",
    5: "多摩川", 6: "浜名湖", 7: "蒲郡", 8: "常滑",
    9: "津", 10: "三国", 11: "びわこ", 12: "住之江",
    13: "尼崎", 14: "鳴門", 15: "丸亀", 16: "児島",
    17: "宮島", 18: "徳山", 19: "下関", 20: "若松",
    21: "芦屋", 22: "福岡", 23: "唐津", 24: "大村"
}


def as_int(value):
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def read_races():
    records = []
    errors = []
    files_read = 0

    stats = {
        "races_found": 0,
        "results_found": 0,
        "result_racers_found": 0,
        "boat6_found": 0,
        "valid_places": 0,
        "excluded_places": 0
    }

    if not os.path.isdir(RAW_DIR):
        return records, files_read, errors, stats

    seen = set()

    for filename in sorted(os.listdir(RAW_DIR)):
        if not filename.endswith(".json"):
            continue

        try:
            path = os.path.join(RAW_DIR, filename)

            with open(path, encoding="utf-8") as f:
                wrapper = json.load(f)

            data = wrapper.get("data", wrapper)

            # 二重ラップにも対応
            if isinstance(data, dict) and "programs" not in data:
                data = data.get("data", data)

            programs = data.get("programs", {})
            stadiums = programs.get("stadiums", {})

            if not isinstance(stadiums, dict):
                errors.append({
                    "file": filename,
                    "error": "programs.stadiums is not a dictionary"
                })
                continue

            files_read += 1

            for stadium_key, stadium in stadiums.items():
                if not isinstance(stadium, dict):
                    continue

                stadium_number = as_int(stadium.get("stadium_number"))
                if stadium_number is None:
                    stadium_number = as_int(stadium_key)

                races = stadium.get("races", {})
                if not isinstance(races, dict):
                    continue

                for race_key, race in races.items():
                    if not isinstance(race, dict):
                        continue

                    stats["races_found"] += 1

                    date = race.get("date") or wrapper.get("date")
                    if not date:
                        continue

                    venue_number = as_int(
                        race.get("stadium_number")
                    ) or stadium_number

                    race_number = as_int(
                        race.get("race_number")
                    ) or as_int(race_key)

                    if venue_number is None or race_number is None:
                        continue

                    result = race.get("result")
                    if not isinstance(result, dict):
                        continue

                    stats["results_found"] += 1

                    result_racers = result.get("racers")
                    if not isinstance(result_racers, (dict, list)):
                        continue

                    stats["result_racers_found"] += 1

                    program_racers = race.get("racers") or {}
                    if not isinstance(program_racers, dict):
                        program_racers = {}

                    # 結果データから枠番6の艇を探す
                    items = (
                        result_racers.items()
                        if isinstance(result_racers, dict)
                        else enumerate(result_racers, start=1)
                    )

                    for entry_key, racer in items:
                        if not isinstance(racer, dict):
                            continue

                        entry = (
                            as_int(racer.get("entry_number"))
                            or as_int(entry_key)
                        )

                        if entry != 6:
                            continue

                        stats["boat6_found"] += 1
if stats["boat6_found"] == 1:
    print(
        "DEBUG boat6 racer:",
        json.dumps(racer, ensure_ascii=False)
    )
    print(
        "DEBUG result racer keys:",
        list(result_racers.keys())
        if isinstance(result_racers, dict)
        else "list"
    )
                        place = as_int(racer.get("place_number"))

                        # 1〜6着のみを有効な着順として扱う
                        if place is None or not 1 <= place <= 6:
                            stats["excluded_places"] += 1
                            continue

                        race_id = (
                            str(date),
                            venue_number,
                            race_number
                        )

                        if race_id in seen:
                            continue

                        seen.add(race_id)
                        stats["valid_places"] += 1

                        program_boat6 = program_racers.get("6") or {}

                        records.append({
                            "date": str(date),
                            "stadium_number": venue_number,
                            "venue": VENUES.get(
                                venue_number, str(venue_number)
                            ),
                            "race_number": race_number,
                            "entry_number": 6,
                            "course_number": as_int(
                                racer.get("course_number")
                            ),
                            "place_number": place,
                            "racer_number": as_int(
                                racer.get(
                                    "number",
                                    program_boat6.get("number")
                                )
                            ),
                            "racer_name": (
                                racer.get("name")
                                or program_boat6.get("name")
                            ),
                            "source_file": filename
                        })

        except (OSError, json.JSONDecodeError, AttributeError, TypeError) as e:
            errors.append({
                "file": filename,
                "error": str(e)
            })

    return records, files_read, errors, stats


def summarize(rows):
    n = len(rows)

    wins = sum(r["place_number"] == 1 for r in rows)
    top2 = sum(r["place_number"] <= 2 for r in rows)
    top3 = sum(r["place_number"] <= 3 for r in rows)

    return {
        "starts": n,
        "win_count": wins,
        "top2_count": top2,
        "top3_count": top3,
        "win_rate": round(wins / n * 100, 2) if n else None,
        "top2_rate": round(top2 / n * 100, 2) if n else None,
        "top3_rate": round(top3 / n * 100, 2) if n else None
    }


def main():
    records, files_read, errors, stats = read_races()

    by_venue = defaultdict(list)
    by_course = defaultdict(list)

    for row in records:
        by_venue[row["venue"]].append(row)

        course = row["course_number"]
        if course in range(1, 7):
            by_course[str(course)].append(row)

    venues = [
        {"venue": venue, **summarize(rows)}
        for venue, rows in by_venue.items()
    ]

    venues.sort(
        key=lambda x: (
            x["top3_rate"] is None,
            -(x["top3_rate"] or 0)
        )
    )

    result = {
        "generated_at": datetime.now(JST).isoformat(),
        "files_read": files_read,
        "boat_number": 6,
        "definition": (
            "枠番6の艇を対象。本番の進入コースは"
            "result.racersのcourse_numberを使用。"
        ),
        "total_starts": len(records),
        "overall": summarize(records),
        "by_venue": venues,
        "by_actual_course": {
            k: summarize(v)
            for k, v in sorted(by_course.items())
        },
        "records": records,
        "errors": errors,
        "diagnostics": stats,
        "notes": [
            "6号艇は枠番(entry_number)6として集計。",
            "進入コースは本番結果(result)のcourse_numberを使用。",
            "着順7以上、欠場、失格などは分母から除外。",
            "集計はdata/races内に保存された結果に限定。",
            "データ提供元は非公式API。公式情報と照合してください。"
        ]
    }

    os.makedirs("data", exist_ok=True)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("Files:", files_read)
    print("Diagnostics:", json.dumps(stats, ensure_ascii=False))
    print("6号艇実績:", len(records))
    print("3着以内率:", result["overall"]["top3_rate"])
    print("Errors:", len(errors))


if __name__ == "__main__":
    main()
