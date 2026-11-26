import json, os
from collections import defaultdict
from datetime import datetime, timezone, timedelta

RAW_DIR = "data/races"
OUTPUT = "data/boat6_analysis.json"
JST = timezone(timedelta(hours=9))
VENUES = {
    1:"桐生",2:"戸田",3:"江戸川",4:"平和島",5:"多摩川",6:"浜名湖",
    7:"蒲郡",8:"常滑",9:"津",10:"三国",11:"びわこ",12:"住之江",
    13:"尼崎",14:"鳴門",15:"丸亀",16:"児島",17:"宮島",18:"徳山",
    19:"下関",20:"若松",21:"芦屋",22:"福岡",23:"唐津",24:"大村"
}

def as_int(value):
    try: return int(value)
    except (TypeError, ValueError): return None

def read_races():
    records, seen, errors = [], set(), []
    files_read = 0
    if not os.path.isdir(RAW_DIR):
        return records, files_read, errors
    for filename in sorted(os.listdir(RAW_DIR)):
        if not filename.endswith(".json"): continue
        try:
            with open(os.path.join(RAW_DIR, filename), encoding="utf-8") as f:
                wrapper = json.load(f)
            data = wrapper.get("data", wrapper)
            stadiums = data.get("programs", {}).get("stadiums", {})
            files_read += 1
            for stadium_key, stadium in stadiums.items():
                if not isinstance(stadium, dict): continue
                stadium_number = as_int(stadium_key)
                races = stadium.get("races", {})
                if not isinstance(races, dict): continue
                for race_key, race in races.items():
                    if not isinstance(race, dict): continue
                    date = race.get("date") or wrapper.get("date")
                    race_number = as_int(race.get("race_number", race_key))
                    venue_number = as_int(race.get("stadium_number", stadium_number))
                    if not date or venue_number is None or race_number is None: continue
                    race_id = (str(date), venue_number, race_number)
                    if race_id in seen: continue
                    seen.add(race_id)

                    program_racers = race.get("racers") or {}
                    result = race.get("result")
                    result_racers = result.get("racers") if isinstance(result, dict) else None
                    if not isinstance(result_racers, dict): continue
                    boat6 = result_racers.get("6") or {}
                    if not isinstance(boat6, dict): continue
                    program_boat6 = program_racers.get("6") or {}
                    entry = as_int(boat6.get("entry_number", program_boat6.get("entry_number", 6)))
                    if entry != 6: continue
                    place = as_int(boat6.get("place_number"))
                    # 7以上は着順コードではないため対象外
                    if place is None or place < 1 or place > 6: continue
                    records.append({
                        "date": str(date), "stadium_number": venue_number,
                        "venue": VENUES.get(venue_number, str(venue_number)),
                        "race_number": race_number, "entry_number": 6,
                        "course_number": as_int(boat6.get("course_number")),
                        "place_number": place,
                        "racer_number": as_int(boat6.get("number", program_boat6.get("number"))),
                        "racer_name": boat6.get("name") or program_boat6.get("name"),
                        "source_file": filename
                    })
        except (OSError, json.JSONDecodeError, AttributeError, TypeError) as e:
            errors.append({"file": filename, "error": str(e)})
    return records, files_read, errors

def summarize(rows):
    n = len(rows)
    wins = sum(r["place_number"] == 1 for r in rows)
    top2 = sum(r["place_number"] <= 2 for r in rows)
    top3 = sum(r["place_number"] <= 3 for r in rows)
    return {
        "starts": n, "win_count": wins, "top2_count": top2, "top3_count": top3,
        "win_rate": round(wins/n*100, 2) if n else None,
        "top2_rate": round(top2/n*100, 2) if n else None,
        "top3_rate": round(top3/n*100, 2) if n else None
    }

def main():
    records, files_read, errors = read_races()
    by_venue, by_course = defaultdict(list), defaultdict(list)
    for row in records:
        by_venue[row["venue"]].append(row)
        if row["course_number"] in range(1, 7):
            by_course[str(row["course_number"])].append(row)
    venues = [{"venue": v, **summarize(rows)} for v, rows in by_venue.items()]
    venues.sort(key=lambda x: (x["top3_rate"] is None, -(x["top3_rate"] or 0)))
    result = {
        "generated_at": datetime.now(JST).isoformat(), "files_read": files_read,
        "boat_number": 6,
        "definition": "枠番6の艇を対象。本番の進入コースはresult.racers['6'].course_numberを使用。",
        "total_starts": len(records), "overall": summarize(records),
        "by_venue": venues,
        "by_actual_course": {k: summarize(v) for k, v in sorted(by_course.items())},
        "records": records, "errors": errors,
        "notes": [
            "6号艇は枠番(entry_number)6として集計。",
            "進入コースは本番結果(result)のcourse_numberを使用。",
            "着順7以上、欠場、失格など着順として扱えない値は分母から除外。",
            "集計はdata/races内に保存された日付の結果に限り、過去データは自動補完しない。",
            "データ提供元は非公式API。公式情報と照合してください。"
        ]
    }
    os.makedirs("data", exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("Files:", files_read, "6号艇実績:", len(records),
          "3着以内率:", result["overall"]["top3_rate"], "Errors:", len(errors))

if __name__ == "__main__":
    main()
