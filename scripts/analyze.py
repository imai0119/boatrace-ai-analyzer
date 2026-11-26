
import json
import os
from datetime import datetime, timezone, timedelta

RAW_DIR = "data/raw"
OUTPUT = "data/analysis.json"
JST = timezone(timedelta(hours=9))


def to_number(value):
    """数値を安全に変換する"""
    if value is None or isinstance(value, bool):
        return None

    try:
        if isinstance(value, str):
            value = value.replace(",", "").replace("%", "").strip()
            if not value:
                return None
        return float(value)
    except (ValueError, TypeError):
        return None


def to_int(value):
    number = to_number(value)
    if number is None:
        return None
    return int(number)


def get_rate(row, keys):
    for key in keys:
        if key in row:
            return to_number(row[key])
    return None


def find_course_sets(obj, venue_hint=None):
    """JSON内部からコース別統計を探す"""
    found = []

    if isinstance(obj, dict):
        venue = (
            obj.get("venue_name")
            or obj.get("venue")
            or venue_hint
        )

        courses = obj.get("courses")

        if isinstance(courses, list):
            valid = [
                row for row in courses
                if isinstance(row, dict)
                and to_int(row.get("course")) in range(1, 7)
                and to_int(row.get("starts")) is not None
            ]

            if valid:
                found.append((str(venue or "不明"), valid))

        for key, value in obj.items():
            if key == "courses":
                continue
            found.extend(find_course_sets(value, venue))

    elif isinstance(obj, list):
        for item in obj:
            found.extend(find_course_sets(item, venue_hint))

    return found


def load_data():
    records = []
    files_read = 0
    errors = []

    if not os.path.isdir(RAW_DIR):
        return records, files_read, errors

    for root, dirs, files in os.walk(RAW_DIR):
        dirs.sort()

        for filename in sorted(files):
            if not filename.endswith(".json"):
                continue

            path = os.path.join(root, filename)

            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)

                files_read += 1

                course_sets = find_course_sets(data)

                for venue, courses in course_sets:
                    for row in courses:
                        course = to_int(row.get("course"))
                        starts = to_int(row.get("starts"))

                        if course not in range(1, 7):
                            continue

                        if starts is None or starts <= 0:
                            continue

                        records.append({
                            "venue": venue,
                            "course": course,
                            "starts": starts,
                            "win_rate": get_rate(
                                row, ["win_rate"]
                            ),
                            "place2_rate": get_rate(
                                row, ["place2_rate"]
                            ),
                            "place3_rate": get_rate(
                                row, ["place3_rate"]
                            ),
                            "file": filename
                        })

            except (OSError, json.JSONDecodeError) as e:
                errors.append({
                    "file": filename,
                    "error": str(e)
                })

    return records, files_read, errors


def weighted_rate(rows, key):
    """出走数を基準にした加重平均"""
    valid = [
        row for row in rows
        if row[key] is not None
    ]

    total = sum(row["starts"] for row in valid)

    if total == 0:
        return None

    value = sum(
        row["starts"] * row[key]
        for row in valid
    ) / total

    return round(value, 2)


def summarize(records):
    result = []

    venues = sorted(set(
        row["venue"] for row in records
    ))

    for venue in venues:
        venue_rows = [
            row for row in records
            if row["venue"] == venue
        ]

        courses = []

        for course in range(1, 7):
            rows = [
                row for row in venue_rows
                if row["course"] == course
            ]

            if not rows:
                continue

            courses.append({
                "course": course,
                "starts": sum(
                    row["starts"] for row in rows
                ),
                "win_rate": weighted_rate(
                    rows, "win_rate"
                ),
                "place2_rate": weighted_rate(
                    rows, "place2_rate"
                ),
                "place3_rate": weighted_rate(
                    rows, "place3_rate"
                )
            })

        six = next(
            (row for row in courses
             if row["course"] == 6),
            None
        )

        result.append({
            "venue": venue,
            "courses": courses,
            "course6": six
        })

    return result


def national_summary(records):
    result = {}

    for course in range(1, 7):
        rows = [
            row for row in records
            if row["course"] == course
        ]

        if not rows:
            continue

        result[str(course)] = {
            "starts": sum(
                row["starts"] for row in rows
            ),
            "win_rate": weighted_rate(
                rows, "win_rate"
            ),
            "place2_rate": weighted_rate(
                rows, "place2_rate"
            ),
            "place3_rate": weighted_rate(
                rows, "place3_rate"
            )
        }

    return result


def main():
    records, files_read, errors = load_data()

    venues = summarize(records)

    six_course_rows = [
        row for row in records
        if row["course"] == 6
    ]

    six_course = {
        "starts": sum(
            row["starts"] for row in six_course_rows
        ),
        "win_rate": weighted_rate(
            six_course_rows, "win_rate"
        ),
        "place2_rate": weighted_rate(
            six_course_rows, "place2_rate"
        ),
        "place3_rate": weighted_rate(
            six_course_rows, "place3_rate"
        )
    }

    ranking = sorted(
        [
            row for row in venues
            if row["course6"] is not None
            and row["course6"]["place3_rate"] is not None
        ],
        key=lambda x: x["course6"]["place3_rate"],
        reverse=True
    )

    result = {
        "generated_at": datetime.now(JST).isoformat(),
        "files_read": files_read,
        "total_course_records": len(records),
        "venue_count": len(venues),
        "status": (
            "success" if records
            else "waiting_for_course_data"
        ),
        "national_course_summary": national_summary(
            records
        ),
        "six_course": six_course,
        "venue_details": venues,
        "course6_ranking": ranking,
        "errors": errors,
        "data_notes": [
            "集計対象はコース別統計です。",
            "6コース成績と6号艇の個別成績は異なります。",
            "3着以内率はplace3_rateを使用しています。",
            "加重平均は出走数を基準にしています。",
            "実際のレース別着順データは別途必要です。"
        ],
        "credit": {
            "name": "艇愛ボートレースDB",
            "url": "https://boatrace-db.jp/"
        }
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
    print("Course records:", len(records))
    print("Venues:", len(venues))
    print("6コース出走数:", six_course["starts"])
    print(
        "6コース3着率:",
        six_course["place3_rate"]
    )
    print("ランキング:", len(ranking))
    print("Errors:", len(errors))


if __name__ == "__main__":
    main()
