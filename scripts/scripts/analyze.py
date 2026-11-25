
import csv
import json
import os
from datetime import datetime, timezone

def main():
    rows = []
    folder = "data/raw"

    if os.path.isdir(folder):
        for filename in os.listdir(folder):
            if not filename.endswith(".csv"):
                continue

            with open(
                os.path.join(folder, filename),
                encoding="utf-8-sig",
                newline=""
            ) as f:
                for row in csv.DictReader(f):
                    try:
                        boat = int(row["boat_no"])
                        finish = int(row["finish"])
                        if 1 <= boat <= 6 and 1 <= finish <= 6:
                            rows.append((boat, finish))
                    except (ValueError, KeyError):
                        continue

    six = [finish for boat, finish in rows if boat == 6]
    total = len(six)

    def rate(count):
        return round(count / total * 100, 2) if total else None

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_rows": len(rows),
        "six_boat": {
            "starts": total,
            "first_rate": rate(six.count(1)),
            "second_rate": rate(six.count(2)),
            "third_rate": rate(six.count(3)),
            "top3_rate": rate(sum(x <= 3 for x in six))
        }
    }

    os.makedirs("data", exist_ok=True)

    with open("data/analysis.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("Analysis completed:", total)

if __name__ == "__main__":
    main()
