
import json
import os
import urllib.request
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))
API_URL = "https://boatrace-db.jp/api/today/"

def collect():
    now = datetime.now(JST)
    date = now.strftime("%Y%m%d")

    os.makedirs("data/raw", exist_ok=True)
    os.makedirs("data/logs", exist_ok=True)

    filename = f"data/raw/today_{date}.json"
    logname = "data/logs/collect.json"

    request = urllib.request.Request(
        API_URL,
        headers={"User-Agent": "BoatraceAnalyzer/1.0"}
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read()

        data = json.loads(raw.decode("utf-8"))

        result = {
            "collected_at": now.isoformat(),
            "source": API_URL,
            "source_name": "艇愛ボートレースDB",
            "data_type": "today_course_statistics",
            "data": data
        }

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(
                result, f,
                ensure_ascii=False,
                indent=2
            )

        log = {
            "status": "success",
            "collected_at": now.isoformat(),
            "file": filename,
            "bytes": len(raw)
        }

        print("Collection completed:", filename)

    except Exception as e:
        log = {
            "status": "error",
            "collected_at": now.isoformat(),
            "message": str(e)
        }

        print("Collection failed:", e)

        with open(logname, "w", encoding="utf-8") as f:
            json.dump(log, f, ensure_ascii=False, indent=2)

        raise

    with open(logname, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    collect()
