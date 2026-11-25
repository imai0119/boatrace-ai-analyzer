
import json
import os
import time
import urllib.request
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))
BASE_URL = "https://boatrace-db.jp/api"

VENUES = {
    1: "桐生", 2: "戸田", 3: "江戸川", 4: "平和島",
    5: "多摩川", 6: "浜名湖", 7: "蒲郡", 8: "常滑",
    9: "津", 10: "三国", 11: "びわこ", 12: "住之江",
    13: "尼崎", 14: "鳴門", 15: "丸亀", 16: "児島",
    17: "宮島", 18: "徳山", 19: "下関", 20: "若松",
    21: "芦屋", 22: "福岡", 23: "唐津", 24: "大村"
}

def fetch(url):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "BoatraceAnalyzer/1.0"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read()
    return json.loads(raw.decode("utf-8")), len(raw)

def save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def collect():
    now = datetime.now(JST)
    date = now.strftime("%Y%m%d")

    os.makedirs("data/raw", exist_ok=True)
    os.makedirs("data/logs", exist_ok=True)

    results = []
    errors = []

    # 当日の開催情報
    try:
        url = f"{BASE_URL}/today/"
        data, size = fetch(url)
        save(f"data/raw/today_{date}.json", {
            "collected_at": now.isoformat(),
            "source": url,
            "data_type": "today",
            "data": data
        })
        results.append("today")
    except Exception as e:
        errors.append({"source": "today", "error": str(e)})

    # 全国24場のコース別統計
    for pid, venue in VENUES.items():
        url = f"{BASE_URL}/stadium/{pid:02d}/course/"

        try:
            data, size = fetch(url)

            save(
                f"data/raw/stadium_{pid:02d}_{date}.json",
                {
                    "collected_at": now.isoformat(),
                    "source": url,
                    "source_name": "艇愛ボートレースDB",
                    "pid": pid,
                    "venue_name": venue,
                    "data": data
                }
            )

            results.append(venue)
            print("取得成功:", venue)

        except Exception as e:
            errors.append({
                "pid": pid,
                "venue": venue,
                "error": str(e)
            })
            print("取得失敗:", venue, e)

        time.sleep(0.2)

    log = {
        "collected_at": now.isoformat(),
        "successful_venues": len(results),
        "failed_count": len(errors),
        "venues": results,
        "errors": errors
    }

    save("data/logs/collect.json", log)

    print("全国24場の収集終了")
    print("成功:", len(results))
    print("失敗:", len(errors))

    if not any(
        x in results for x in VENUES.values()
    ):
        raise RuntimeError("コースデータを取得できませんでした")

if __name__ == "__main__":
    collect()
