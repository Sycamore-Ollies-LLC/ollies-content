"""Check the content files before committing. Run from anywhere: python tools/validate.py
Exits with status 1 if any problem is found."""
import datetime, glob, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEASONS = {"summer", "fall", "winter"}
DAY_KEYS = {"flavor", "flavor2", "note", "fundraiser", "status"}
problems = []

def load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return json.load(f)

catalog = load("catalog.json")["flavors"]
names = {f["name"] for f in catalog}
ids = [f["id"] for f in catalog]
if len(ids) != len(set(ids)):
    problems.append("catalog.json: duplicate ids")
for f in catalog:
    if f["availability"] == "seasonal" and f.get("season") not in SEASONS:
        problems.append(f"catalog.json: {f['name']} is seasonal but season is {f.get('season')!r}")

for path in sorted(glob.glob(os.path.join(ROOT, "calendar", "*.json"))):
    rel = os.path.relpath(path, ROOT)
    d = load(rel)
    month, days = d["month"], d["days"]
    if os.path.basename(path) != f"{month}.json":
        problems.append(f"{rel}: month is {month} but file name does not match")
    for k, e in days.items():
        if not k.startswith(month + "-"):
            problems.append(f"{rel}: {k} is not in {month}")
        extra = set(e) - DAY_KEYS
        if extra:
            problems.append(f"{rel}: {k} has unknown keys {sorted(extra)}")
        for key in ("flavor", "flavor2"):
            if key in e and e[key] not in names:
                problems.append(f"{rel}: {k} {key} {e[key]!r} is not in catalog.json")
        closed = e.get("status") == "closed"
        if closed and "flavor" in e:
            problems.append(f"{rel}: {k} is closed but has a flavor")
        if not closed and "flavor" not in e:
            problems.append(f"{rel}: {k} has no flavor")
    ds = sorted(days)
    first, last = datetime.date.fromisoformat(ds[0]), datetime.date.fromisoformat(ds[-1])
    gaps = [(first + datetime.timedelta(i)).isoformat() for i in range((last - first).days + 1)
            if (first + datetime.timedelta(i)).isoformat() not in days]
    if gaps:
        problems.append(f"{rel}: missing days {gaps}")
    print(f"{rel}: {len(days)} days, {ds[0]} to {ds[-1]}")

# Dole weeks: in order. The first week of a season can open on any day and is
# marked "seasonStart": true (the very first week counts as one). Every other
# week starts on a Monday, 7 days after the week before.
weeks = load("dole.json")["weeks"]
starts = [datetime.date.fromisoformat(w["start"]) for w in weeks]
if starts != sorted(starts):
    problems.append("dole.json: weeks are not in date order")
for i, s in enumerate(starts):
    if len(weeks[i]["flavors"]) != 2:
        problems.append(f"dole.json: week {s} does not have exactly 2 flavors")
    if i == 0 or weeks[i].get("seasonStart"):
        continue
    prev_is_start = i - 1 == 0 or weeks[i - 1].get("seasonStart")
    if s.weekday() != 0:
        problems.append(f"dole.json: week {s} does not start on a Monday")
    elif not prev_is_start and (s - starts[i - 1]).days != 7:
        problems.append(f"dole.json: week {s} is not 7 days after {starts[i - 1]}")
print(f"dole.json: {len(weeks)} weeks")

for p in problems:
    print("PROBLEM:", p)
print(f"{len(problems)} problem(s)")
sys.exit(1 if problems else 0)
