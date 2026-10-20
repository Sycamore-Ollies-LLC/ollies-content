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

# Hours: filled in daily from the Google listing by tools/import_google_hours.py.
# An empty "hours" list is allowed until the first sync has run.
WEEKDAYS = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"]
HOUR_KEYS = {"updated", "status", "googlePlaceId", "hours", "specialDays", "note"}
TIME = __import__("re").compile(r"^([01]\d|2[0-3]):[0-5]\d$")
hours = load("hours.json")
extra = set(hours) - HOUR_KEYS
if extra:
    problems.append(f"hours.json: unknown keys {sorted(extra)}")
if hours.get("status") not in ("open", "temporarilyClosed"):
    problems.append(f"hours.json: status {hours.get('status')!r} is not 'open' or 'temporarilyClosed'")
try:
    datetime.date.fromisoformat(hours.get("updated", ""))
except ValueError:
    problems.append("hours.json: updated is not a YYYY-MM-DD date")
seen_days = []
for slot in hours.get("hours", []):
    days = slot.get("days", [])
    if not days or any(d not in WEEKDAYS for d in days):
        problems.append(f"hours.json: slot {slot} has missing or unknown days")
    seen_days += days
    if "label" not in slot:
        if not TIME.match(slot.get("open", "")):
            problems.append(f"hours.json: slot {slot} has no valid opening time")
        if "close" in slot and not TIME.match(slot["close"]):
            problems.append(f"hours.json: slot {slot} has an invalid closing time")
if len(seen_days) != len(set(seen_days)):
    problems.append("hours.json: a day appears in more than one slot")
special = hours.get("specialDays", [])
for d in special:
    try:
        datetime.date.fromisoformat(d.get("date", ""))
    except ValueError:
        problems.append(f"hours.json: special day {d} has an invalid date")
        continue
    if not isinstance(d.get("closed"), bool):
        problems.append(f"hours.json: special day {d['date']} needs closed: true or false")
    elif not d["closed"] and not TIME.match(d.get("open", "")):
        problems.append(f"hours.json: special day {d['date']} is open but has no valid opening time")
if [d.get("date") for d in special] != sorted(d.get("date", "") for d in special):
    problems.append("hours.json: special days are not in date order")
print(f"hours.json: {len(hours.get('hours', []))} slot(s), {len(special)} special day(s)")

# About and links: text and web addresses the app shows, edited by hand.
about = load("about.json")
paras = about.get("about", {}).get("paragraphs")
if not about.get("about", {}).get("title") or not isinstance(paras, list) or not paras or not all(isinstance(x, str) and x.strip() for x in paras):
    problems.append("about.json: about needs a title and at least one paragraph of text")
if "@" not in about.get("contact", {}).get("email", "@"):
    problems.append("about.json: contact email doesn't look like an email address")
jobs = about.get("jobs")
if jobs is not None:
    if not isinstance(jobs.get("hiring"), bool):
        problems.append("about.json: jobs.hiring must be true or false")
    if jobs.get("applyUrl") and not jobs["applyUrl"].startswith("https://"):
        problems.append("about.json: jobs.applyUrl must start with https://")
links = load("links.json")
for k, v in links.items():
    if not isinstance(v, str) or not v.startswith("https://"):
        problems.append(f"links.json: {k} must be a web address starting with https://")
print(f"about.json: {len(paras or [])} paragraph(s); links.json: {len(links)} link(s)")

# Menu: sections of items, each with sizes and prices. A price of null means "Price coming soon".
menu = load("menu.json")
item_ids = []
for sec in menu.get("sections", []):
    if not sec.get("id") or not sec.get("title") or not sec.get("items"):
        problems.append(f"menu.json: section {sec.get('id')!r} needs an id, a title, and at least one item")
    for it in sec.get("items", []):
        where = f"menu.json: {sec.get('id')}/{it.get('id')}"
        item_ids.append(it.get("id"))
        if not it.get("id") or not it.get("name"):
            problems.append(f"{where} needs an id and a name")
        size_names = [sz.get("name") for sz in it.get("sizes", [])]
        if len(size_names) != len(set(size_names)) or not all(size_names):
            problems.append(f"{where} has a blank or repeated size name")
        for sz in it.get("sizes", []):
            price = sz.get("price")
            if price is not None and (not isinstance(price, (int, float)) or price < 0 or round(price, 2) != price):
                problems.append(f"{where} size {sz.get('name')!r} has price {price!r}; use a number like 4.25, or null")
        for ph in it.get("photos", []):
            if not ph.startswith("https://") and not os.path.exists(os.path.join(ROOT, ph)):
                problems.append(f"{where} photo {ph} is not in the repo")
dupes = sorted({i for i in item_ids if item_ids.count(i) > 1})
if dupes:
    problems.append(f"menu.json: repeated item ids {dupes}")
priced = sum(1 for sec in menu.get("sections", []) for it in sec["items"] for sz in it.get("sizes", []) if sz.get("price") is not None)
total = sum(len(it.get("sizes", [])) for sec in menu.get("sections", []) for it in sec["items"])
print(f"menu.json: {len(item_ids)} items, {priced} of {total} sizes priced")

for p in problems:
    print("PROBLEM:", p)
print(f"{len(problems)} problem(s)")
sys.exit(1 if problems else 0)
