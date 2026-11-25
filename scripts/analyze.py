
import csv
import json
import os
from datetime import datetime, timezone, timedelta

RAW_DIR = "data/raw"
OUTPUT = "data/analysis.json"
JST = timezone(timedelta(hours=9))

BOAT_KEYS = [
    "boat_no", "boat", "lane", "boatNumber",
    "boatNo", "枠番", "艇番"
]

FINISH_KEYS = [
    "finish", "rank", "arrival", "finish_position",
    "着順", "順位"
]


def get_value(record, keys):
    for key in keys:
        if key in record:
            value = record[key]
            if isinstance(value, (str, int, float)):
                return value
    return None


def extract_records(obj, records):
    if isinstance(obj, dict):
        boat = get_value(obj, BOAT_KEYS)
        finish = get_value(obj, FINISH_KEYS)

        try:
            boat = int(boat)
            finish = int(finish)

            if 1 <= boat <= 6 and finish >= 1:
                records.append({
                    "boat_no": boat,
                    "finish": finish,
                    "venue": str(
                        obj.get("venue_name",
                        obj.get("venue", "不明"))
                    )
                })
        except (ValueError, TypeError):
            pass

        for value in obj.values():
            if isinstance(value, (dict, list)):
                extract_records(value, records)

    elif isinstance(obj, list):
        for item in obj:
            extract_records(item, records)


def load_data():
    records = []
    files_read = 0

    if not os.path.isdir(RAW_DIR):
        return records, files_read

    for filename in sorted(os.listdir(RAW_DIR)):
        path = os.path.join(RAW_DIR, filename)

        try:
            if filename.endswith(".json"):
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)

                extract_records(data, records)
                files_read += 1

            elif filename.endswith(".csv"):
                with open(
                    path,
                    encoding="utf-8-sig",
                    newline=""
                ) as f:
                    for row in csv.DictReader(f):
                        extract_records(row, records)

                files_read += 1

        except (OSError, json.JSONDecodeError) as e:
            print("読み込みエラー:", filename, str(e))

    return records, files_read


def rate(count, total):
    if total == 0:
        return 0.0
    return round(count / total * 100, 2)


def main():
    records, files_read = load_data()

    six_boat = [
        row["finish"]
        for row in records
        if row["boat_no"] == 6
    ]

    total = len(six_boat)

    first = six_boat.count(1)
    second = six_boat.count(2)
    third = six_boat.count(3)
    top3 = sum(1 for x in six_boat if x <= 3)

    result = {
        "generated_at": datetime.now(JST).isoformat(),
        "total_rows": len(records),
        "files_read": files_read,
        "six_boat": {
            "starts": total,
            "first_count": first,
            "second_count": second,
            "third_count": third,
            "top3_count": top3,
            "first_rate": rate(first, total),
            "second_rate": rate(second, total),
            "third_rate": rate(third, total),
            "top3_rate": rate(top3, total)
        },
        "status": (
            "success" if total > 0
            else "waiting_for_race_data"
        )
    }

    os.makedirs("data", exist_ok=True)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(
            result,
            f,
            ensure_ascii=False,
            indent=2
        )

    print("Analysis completed")
    print("Files read:", files_read)
    print("Total records:", len(records))
    print("6号艇の出走数:", total)
    print("6号艇の3着以内率:", result["six_boat"]["top3_rate"])


if __name__ == "__main__":
    main()
