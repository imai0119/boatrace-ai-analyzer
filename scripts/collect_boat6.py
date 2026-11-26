import json, os, tempfile, urllib.request
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))
API_URL = "https://boatraceopenapi.github.io/api/v1/today.json"
OUTPUT_DIR = "data/races"

def fetch_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": "BoatraceAIAnalyzer/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))

def atomic_save(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix=".tmp_", suffix=".json", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

def main():
    now = datetime.now(JST)
    payload = fetch_json(API_URL)
    programs = payload.get("programs")
    stadiums = programs.get("stadiums") if isinstance(programs, dict) else None
    if not isinstance(stadiums, dict) or not stadiums:
        raise ValueError("API response has no programs.stadiums data")

    race_count = 0
    races_with_results = 0
    for stadium in stadiums.values():
        if not isinstance(stadium, dict):
            continue
        races = stadium.get("races")
        if not isinstance(races, dict):
            continue
        race_count += len(races)
        for race in races.values():
            result = race.get("result") if isinstance(race, dict) else None
            racers = result.get("racers") if isinstance(result, dict) else None
            if isinstance(racers, dict) and racers:
                races_with_results += 1

    if race_count == 0:
        raise ValueError("No race records found in API response")

    output = {
        "collected_at": now.isoformat(),
        "source": API_URL,
        "date": now.strftime("%Y-%m-%d"),
        "race_count": race_count,
        "races_with_results": races_with_results,
        "data": payload
    }
    path = os.path.join(OUTPUT_DIR, now.strftime("%Y%m%d") + ".json")
    atomic_save(path, output)
    print("Date:", output["date"], "Stadiums:", len(stadiums),
          "Races:", race_count, "With results:", races_with_results)

if __name__ == "__main__":
    main()
