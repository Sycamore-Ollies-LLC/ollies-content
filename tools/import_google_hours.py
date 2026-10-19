"""Updates hours.json from Ollie's Google Business Profile: the regular weekly hours, holiday
and other special hours Google lists for the coming days, and whether the listing is marked
temporarily closed.

Run with: GOOGLE_PLACES_API_KEY=... python tools/import_google_hours.py [--summary FILE]
Prints a plain-English list of changes and writes hours.json only if something changed.
--summary also writes that list (Markdown) to FILE, for the pull request.
Uses only Python's standard library, so there is nothing to install.

Cost: one request to Google per run (two on the very first run, to look up the listing).
It runs once a day, so it stays far inside Google's free monthly allowance no matter how many
people use the app. A daily cap of 50 requests is set in Google Cloud as a backstop.
"""
import datetime, json, os, sys, urllib.error, urllib.request
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOURS_FILE = os.path.join(ROOT, "hours.json")
SEARCH_TEXT = "Ollie's Frozen Custard, 2290 Oakland Drive, Sycamore, IL"
DAYS = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"]
TIME_ZONE = ZoneInfo("America/Chicago")


def google(path, key, field_mask, body=None):
    request = urllib.request.Request(
        f"https://places.googleapis.com/v1/{path}",
        data=json.dumps(body).encode() if body else None,
        method="POST" if body else "GET",
        headers={"X-Goog-Api-Key": key, "X-Goog-FieldMask": field_mask, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as err:
        details = err.read().decode(errors="replace")[:300]
        raise SystemExit(f"Google refused the request (status {err.code}): {details}")


def find_place_id(key):
    data = google("places:searchText", key, "places.id,places.displayName,places.formattedAddress", {"textQuery": SEARCH_TEXT})
    for place in data.get("places", []):
        address = place.get("formattedAddress", "")
        if "Oakland" in address and "Sycamore" in address:
            print(f"Found the Google listing {place.get('displayName', {}).get('text')!r} ({address}).")
            return place["id"]
    raise SystemExit(f"Couldn't find Ollie's listing on Google by searching {SEARCH_TEXT!r}.")


def hhmm(point):
    return f"{point.get('hour', 0):02d}:{point.get('minute', 0):02d}"


def date_text(d):
    return f"{d['year']}-{d['month']:02d}-{d['day']:02d}"


def regular_slots(regular):
    """Google's weekly hours -> slots like {"days": ["mon", "tue"], "open": "11:00", "close": "21:00"},
    grouping days with the same hours. Days with no slot are closed."""
    periods = (regular or {}).get("periods", [])
    if not periods:
        raise SystemExit("Google returned no regular hours for the listing, so nothing was changed.")
    if len(periods) == 1 and "close" not in periods[0]:
        return [{"days": list(DAYS), "label": "Open 24 hours"}]
    by_day = {}
    for p in periods:
        day = DAYS[p["open"]["day"]]
        entry = {"open": hhmm(p["open"]), "close": hhmm(p["close"]) if "close" in p else None}
        # A day split into two openings is shown from first opening to last close.
        if day in by_day:
            entry = {"open": by_day[day]["open"], "close": entry["close"]}
        by_day[day] = entry
    groups = []
    for day in DAYS:
        if day not in by_day:
            continue
        hours = by_day[day]
        group = next((g for g in groups if g["open"] == hours["open"] and g["close"] == hours["close"]), None)
        if group:
            group["days"].append(day)
        else:
            groups.append({"days": [day], **hours})
    return [{k: v for k, v in g.items() if v is not None} for g in groups]


def special_days(current, today):
    """Google's special hours for the coming days -> entries like {"date": "2026-11-26", "closed": true}."""
    current = current or {}
    dates = sorted({date_text(s["date"]) for s in current.get("specialDays", []) if "date" in s})
    result = []
    for date in dates:
        if date < today:
            continue
        period = next((p for p in current.get("periods", []) if "date" in p.get("open", {}) and date_text(p["open"]["date"]) == date), None)
        if not period:
            result.append({"date": date, "closed": True})
        else:
            entry = {"date": date, "closed": False, "open": hhmm(period["open"])}
            if "close" in period:
                entry["close"] = hhmm(period["close"])
            result.append(entry)
    return result


def describe(old, new):
    def show(slots):
        return "; ".join(f"{', '.join(s['days'])}: {s.get('label') or s['open'] + '-' + s.get('close', 'close')}" for s in slots) or "none"

    def show_day(d):
        return f"{d['date']} " + ("closed" if d["closed"] else f"{d['open']}-{d.get('close', 'close')}")

    lines = []
    if old.get("status") != new["status"]:
        lines.append(f"- **Listing status changed** on Google: {old.get('status', 'unknown')} -> {new['status']}.")
    if old.get("hours") != new["hours"]:
        lines.append(f"- **Regular hours changed** on Google. Was: {show(old.get('hours', []))}. Now: {show(new['hours'])}.")
    before = [show_day(d) for d in old.get("specialDays", [])]
    after = [show_day(d) for d in new.get("specialDays", [])]
    lines += [f"- Special hours added: {d}" for d in after if d not in before]
    lines += [f"- Special hours removed: {d}" for d in before if d not in after]
    return lines


def main():
    summary_file = sys.argv[sys.argv.index("--summary") + 1] if "--summary" in sys.argv else None
    key = os.environ.get("GOOGLE_PLACES_API_KEY")
    if not key:
        # Not set up yet: do nothing rather than fail every day.
        print("No Google key saved yet (GOOGLE_PLACES_API_KEY), so hours were not checked.")
        return

    with open(HOURS_FILE, encoding="utf-8") as f:
        current = json.load(f)
    # The listing's id is saved in hours.json after the first run, so later runs skip the search.
    place_id = current.get("googlePlaceId") or find_place_id(key)
    place = google(f"places/{place_id}", key, "id,businessStatus,regularOpeningHours,currentOpeningHours")

    today = datetime.datetime.now(TIME_ZONE).date().isoformat()
    updated = dict(current)
    updated["googlePlaceId"] = place_id
    updated["status"] = "temporarilyClosed" if place.get("businessStatus") == "CLOSED_TEMPORARILY" else "open"
    updated["hours"] = regular_slots(place.get("regularOpeningHours"))
    upcoming = special_days(place.get("currentOpeningHours"), today)
    if upcoming:
        updated["specialDays"] = upcoming
    else:
        updated.pop("specialDays", None)

    changes = describe(current, updated)
    if not changes and current.get("googlePlaceId") == place_id:
        print("No changes. hours.json already matches Google.")
        return
    updated["updated"] = today
    with open(HOURS_FILE, "w", encoding="utf-8") as f:
        f.write(json.dumps(updated, indent=2) + "\n")
    summary = "\n".join(["Ollie's hours updated from the Google listing.", ""] + (changes or ["- Saved the Google listing's id."]))
    print(summary)
    if summary_file:
        with open(summary_file, "w", encoding="utf-8") as f:
            f.write(summary + "\n")


if __name__ == "__main__":
    main()
