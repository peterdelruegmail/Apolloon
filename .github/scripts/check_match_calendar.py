"""Compare public Clubee fixtures with the Apolloon Twizzit iCalendar."""
import argparse
import concurrent.futures
import datetime as dt
import html
import json
import os
from pathlib import Path
import re
import smtplib
import ssl
import time
import unicodedata
import urllib.request
from email.message import EmailMessage
from zoneinfo import ZoneInfo

ROOT = "https://www.clubee.com/handballbelgium"
ICAL = ("https://static.twizzit.com/v2/activity/export/ical?"
        "c=ZHJaenhkRTBzKzVjRDk3dnlNd3FHQT09&"
        "o=Yjl3SUZteEZTK0ltRVZBeHlTa3lodz09&"
        "f=eyJjIjpudWxsLCJnIjpudWxsLCJyIjpbXSwiZ2MiOltdLCJhdCI6WyIzIl0sImFzdCI6W119")
TZ = ZoneInfo("Europe/Brussels")
DEFAULT_MAIL_FROM = "peter.delrue@gmail.com"
DEFAULT_MAIL_TO = "peter.delrue@gmail.com"


def fetch(url, api=False):
    headers = {"User-Agent": "Apolloon-calendar-check/1.0",
               "Accept": "application/json" if api else "*/*"}
    if api:
        headers["X-Website"] = "handballbelgium"
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=25) as response:
                return response.read(12_000_001).decode("utf-8")
        except Exception:
            if attempt == 2:
                raise
            time.sleep(attempt + 1)


def text(value):
    return " ".join(html.unescape(re.sub("<[^>]+>", " ", value)).split())


def normalize(value):
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(c for c in value if not unicodedata.combining(c))
    return " ".join(re.findall(r"[a-z0-9]+", value))


def opponent(value):
    value = re.sub(r"\([^)]*\)", "", value)
    category = re.search(r"\b(?:D1|D|G14|M14|B18|U12|U14|U16|U18)\b", value)
    if category:
        number = re.search(r"\b([1-9])\s*$", value[category.start():])
        value = value[:category.start()] + (number[1] if number else "")
    words = normalize(value).split()
    aliases = {"db": "", "don": "", "bosco": "", "handbalclub": "",
               "handbal": "", "hbc": "", "hc": "", "hkv": "", "hv": "",
               "dhc": "", "hk": "", "besox": "", "biobest": "", "sezoens": "",
               "achilles": "", "sporting": "", "derdaele": "", "sp": "",
               "estudiantes": "", "pentagoon": "", "p": "", "h": "",
               "renaissance": "", "handball": "", "club": "", "desselgemse": "desselgem", "1": "", "hestia": "", "elita": "", "ehc": ""}
    return " ".join(aliases.get(w, w) for w in words if aliases.get(w, w))


def parse_ical(body):
    if "BEGIN:VCALENDAR" not in body or "END:VCALENDAR" not in body:
        raise ValueError("Twizzit gaf geen volledige iCalendar terug.")
    body = re.sub(r"\r?\n[ \t]", "", body)
    found = {}
    for block in re.findall(r"BEGIN:VEVENT\r?\n(.*?)END:VEVENT", body, re.S):
        fields = {}
        params = {}
        for line in block.splitlines():
            key, separator, value = line.partition(":")
            if separator:
                name = key.split(";")[0]
                fields[name] = re.sub(r"\\([nN,;\\])",
                                      lambda m: "\n" if m[1].lower() == "n" else m[1], value)
                params[name] = key
        if fields.get("STATUS") == "CANCELLED":
            continue
        start = fields.get("DTSTART", "")
        if not start or "SUMMARY" not in fields:
            raise ValueError("Twizzit-wedstrijd mist datum of titel.")
        if start.endswith("Z"):
            stamp = dt.datetime.strptime(start, "%Y%m%dT%H%M%SZ").replace(tzinfo=dt.timezone.utc).astimezone(TZ)
        elif "T" in start:
            stamp = dt.datetime.strptime(start, "%Y%m%dT%H%M%S")
            zone = re.search(r"TZID=([^;:]+)", params["DTSTART"])
            stamp = stamp.replace(tzinfo=ZoneInfo(zone[1]) if zone else TZ).astimezone(TZ)
        else:
            stamp = dt.datetime.strptime(start, "%Y%m%d").replace(tzinfo=TZ)
        parts = fields["SUMMARY"].split(" - ", 1)
        fixture = {"id": fields.get("UID", block), "title": fields["SUMMARY"],
                   "date": stamp.date().isoformat(), "time": stamp.strftime("%H:%M"),
                   "location": fields.get("LOCATION", ""), "team": None,
                   "opponent": "", "home": None}
        for side, part in enumerate(parts):
            code = normalize(part).upper().replace(" ", "_")
            match = re.fullmatch(r"(H[123]|D1|J18|J16|JM16|J14|JM14|M14|U12(?:_P[WB])?)", code)
            if match:
                fixture.update(team={"JM16": "J16", "JM14": "J14"}.get(code, code.split("_")[0]),
                               opponent=opponent(parts[1 - side]), home=side == 0)
                break
        found[fixture["id"]] = fixture
    if not found:
        raise ValueError("Twizzit-export bevat geen wedstrijden; controleer de kalenderlink.")
    return list(found.values())


def competitions(page):
    # Reassemble Next.js transport records before decoding the navigation tree.
    chunks = []
    for chunk in re.findall(r"self\.__next_f\.push\((\[.*?\])\)</script>", page, re.S):
        try:
            record = json.loads(chunk)
            if record[0] == 1 and isinstance(record[1], str):
                chunks.append(record[1])
        except (ValueError, IndexError, TypeError):
            pass
    result = {}

    def walk(node, inside=False):
        if isinstance(node, list):
            for child in node:
                walk(child, inside)
        elif isinstance(node, dict):
            inside = inside or node.get("name") == "COMPETITION"
            if (inside and node.get("page", {}).get("type") == "results"
                    and re.fullmatch(r"[\w-]+v4", node.get("url", ""))):
                result[ROOT + "/" + node["url"]] = text(node["name"])
            for child in node.values():
                if isinstance(child, (dict, list)):
                    walk(child, inside)
    for line in "".join(chunks).splitlines():
        try:
            walk(json.loads(line.split(":", 1)[1]))
        except (ValueError, IndexError):
            pass
    if len(result) < 20:
        raise ValueError("Clubee-competitielijst niet volledig herkenbaar.")
    return result


def team_code(name):
    if "D1 M (Senior M)" in name:
        return "H1"
    if "D1 W VHV" in name:
        return "D1"
    if "D1 M VHV" in name:
        return "H2"
    if "D M VHV OWV" in name:
        return "H3"
    for pattern, code in [(r"U12", "U12"), (r"(?:U14|G14|M14).*U14 F|M14-Beker", "M14"),
                          (r"U14", "J14"), (r"U16", "J16"), (r"B18|U18", "J18")]:
        if re.search(pattern, name):
            return code
    return None


def fixtures(page, competition):
    result = {}
    links = re.findall(r"/games/(\d+)", page)
    recognized = 0
    for card in re.findall(r"<li\b[^>]*>(.*?)</li>", page, re.S):
        identifier = re.search(r'href="[^"<>]*/games/(\d+)"', card)
        names = [text(n) for n in re.findall(
            r'<span\b[^>]*class="[^"]*\b[\w-]+_name\b[^"]*"[^>]*>(.*?)</span>', card, re.S)]
        date = re.search(r">(\d{2}[./]\d{2}[./]\d{4})<", card)
        if identifier and len(names) == 2 and date:
            recognized += 1
            sides = [i for i, name in enumerate(names) if re.search(r"\bapolloon\b", name, re.I)]
            if len(sides) != 1:
                continue
            side = sides[0]
            stamp = dt.datetime.strptime(date[1].replace("/", "."), "%d.%m.%Y").date()
            hour = re.search(r">(\d{1,2}:\d{2})<", card)
            result[identifier[1]] = {
                "id": identifier[1], "title": " - ".join(names), "date": stamp.isoformat(),
                "time": hour[1] if hour else "", "team": team_code(names[side]),
                "opponent": opponent(names[1 - side]), "home": side == 0,
                "competition": competition, "location": ""}
    if links and not recognized:
        raise ValueError("Clubee-wedstrijdkaarten niet herkenbaar: " + competition)
    return list(result.values())


def hydrate(game):
    data = json.loads(fetch("https://apiv3.clubee.com/scenes/" + game["id"] + "?language=en", True))
    if str(data.get("id")) != game["id"] or not data.get("start_date"):
        raise ValueError("Onvolledige Clubee-details voor " + game["id"])
    # Clubee's public page displays the literal API wall clock even though the API
    # adds +00:00. Converting this suffix would introduce a 1/2 hour difference.
    stamp = dt.datetime.fromisoformat(data["start_date"])
    return dict(game, date=stamp.date().isoformat(), time=stamp.strftime("%H:%M"),
                location=data.get("venue_name") or "", cancelled=bool(data.get("cancelled")),
                date_unknown=bool(data.get("date_unknown")), time_unknown=bool(data.get("time_unknown")))


def compare(clubee, twizzit):
    rows, used, matched = [], set(), 0
    for game in clubee:
        same = [t for t in twizzit if t["id"] not in used and game["team"]
                and t["team"] == game["team"] and t["opponent"] == game["opponent"]
                and t["home"] == game["home"]]
        # A short Twizzit name may omit the reserve-team number. Flag the
        # ambiguity instead of declaring the whole fixture missing.
        shortened = []
        if not same and game["team"]:
            base = lambda name: re.sub(r"\s+(?:[a-z]|[2-9])$", "", name)
            shortened = [t for t in twizzit if t["id"] not in used
                         and t["team"] == game["team"] and t["home"] == game["home"]
                         and t["date"] == game["date"]
                         and base(t["opponent"]) == base(game["opponent"])]
            same = shortened
        on_date = [t for t in same if t["date"] == game["date"]]
        candidates = on_date if on_date else same
        if len(candidates) != 1:
            rows.append(("Mogelijke koppeling onduidelijk" if candidates else "Niet gevonden in Twizzit", game, None))
            continue
        other = candidates[0]
        used.add(other["id"])
        matched += 1
        changes = ["Ploegnummer controleren"] if shortened else []
        if game.get("cancelled"):
            changes.append("Afgelast in Clubee")
        if game["date"] != other["date"]:
            changes.append("Mogelijke datumwijziging; koppeling controleren")
        if game["time"] != other["time"]:
            changes.append("Uur verschilt")
        if game.get("date_unknown") or game.get("time_unknown"):
            changes.append("Datum/uur onbekend in Clubee")
        if other["location"] and game["location"]:
            if normalize(game["location"]) not in normalize(other["location"]):
                changes.append("Locatie controleren")
        if changes:
            rows.append((", ".join(changes), game, other))
    extras = [t for t in twizzit if t["id"] not in used]
    return rows, extras, matched


def render(clubee, twizzit, errors, today):
    rows, extras, matched = compare(clubee, twizzit)
    lines = ["Apolloon: wekelijkse wedstrijdcontrole",
             "Gecontroleerd: " + today.isoformat(),
             "Bereik: komende wedstrijden in het huidige openbare Clubee-seizoen.",
             "ONVOLLEDIGE CONTROLE" if errors else "Bronnen opgehaald.",
             f"Clubee: {len(clubee)} wedstrijden; Twizzit: {len(twizzit)} activiteiten; gekoppeld: {matched}.",
             "Afwijkingen en ontbrekende wedstrijden zijn controlesuggesties; er is niets aangepast.", ""]
    if errors:
        lines += ["Problemen bij ophalen (geen volledige vergelijking):"] + errors + [""]
    if not rows and not extras and not errors:
        lines += ["Geen verschillen gevonden in datum, uur en tegenstander.", ""]
    for label, game, other in rows:
        lines += [label + ": " + game["title"],
                  "Clubee: " + game["date"] + " " + game["time"] + " | " + (game["location"] or "locatie ontbreekt"),
                  ROOT + "/games/" + game["id"]]
        if other:
            lines += ["Twizzit: " + other["date"] + " " + other["time"] + " | " + (other["location"] or "locatie ontbreekt")]
        lines += [""]
    if extras:
        lines += ["Twizzit-activiteiten zonder eenduidige koppeling (kunnen tornooien/oefenmatchen zijn):"]
        lines += [t["date"] + " " + t["time"] + " " + t["title"] for t in extras]
        lines += [""]
    lines += ["Locaties worden alleen vergeleken als beide bronnen een locatie vermelden.",
              "Afkortingen en zaalnamen kunnen handmatige controle vragen.",
              "Clubee-uren volgen de zichtbare wedstrijdpagina; 00:00 en opvallende datums eerst navragen.",
              "Bronnen: " + ROOT, "Twizzit-kalender via https://apolloon-spurs.be/?oid=40188&pid=134839"]
    return "\n".join(lines)


def send_report(report, recipient):
    required = ["SMTP_PASSWORD"]
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise ValueError("E-mail niet verstuurd: ontbrekende GitHub Secrets: " + ", ".join(missing))
    message = EmailMessage()
    sender = (os.environ.get("MAIL_FROM") or os.environ.get("SMTP_FROM")
              or os.environ.get("SMTP_USERNAME") or DEFAULT_MAIL_FROM)
    username = os.environ.get("SMTP_USERNAME") or sender
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = "Apolloon - wekelijkse controle Clubee / Twizzit"
    message.set_content(report)
    with smtplib.SMTP(os.environ.get("SMTP_HOST") or "smtp.gmail.com", int(os.environ.get("SMTP_PORT") or "587"), timeout=30) as smtp:
        smtp.starttls(context=ssl.create_default_context())
        smtp.login(username, os.environ["SMTP_PASSWORD"].replace(" ", ""))
        smtp.send_message(message)


def arguments(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--send-email", action="store_true")
    parser.add_argument("--recipient", default=os.environ.get("MAIL_TO") or DEFAULT_MAIL_TO)
    parser.add_argument("--output", default="wedstrijdcontrole")
    return parser.parse_args(argv)


def main():
    args = arguments()
    today = dt.datetime.now(TZ).date()
    errors, games, twizzit = [], {}, []
    try:
        twizzit = parse_ical(fetch(ICAL))
    except Exception as exc:
        errors.append("Twizzit: " + type(exc).__name__ + ": " + str(exc))
    try:
        sources = competitions(fetch(ROOT))
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            pending = {pool.submit(fetch, url): name for url, name in sources.items()}
            for future in concurrent.futures.as_completed(pending):
                name = pending[future]
                try:
                    for game in fixtures(future.result(), name):
                        games[game["id"]] = game
                except Exception as exc:
                    errors.append("Clubee " + name + ": " + str(exc))
    except Exception as exc:
        errors.append("Clubee-competities: " + str(exc))
    verified = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        # Include old fixtures so rescheduled games cannot disappear from the scan.
        pending = {pool.submit(hydrate, game): game for game in games.values()}
        for future in concurrent.futures.as_completed(pending):
            try:
                game = future.result()
                if game["date"] >= today.isoformat():
                    verified.append(game)
            except Exception as exc:
                errors.append("Clubee-wedstrijd " + pending[future]["id"] + ": " + str(exc))
    if not games:
        errors.append("Geen Apolloon-wedstrijden herkend in Clubee.")
    twizzit = [t for t in twizzit if t["date"] >= today.isoformat()]
    verified.sort(key=lambda g: (g["date"], g["time"], g["id"]))
    report = render(verified, twizzit, errors, today)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "rapport.txt").write_text(report, encoding="utf-8")
    (output / "rapport.html").write_text(
        '<!doctype html><html lang="nl"><meta charset="utf-8"><title>Apolloon wedstrijdcontrole</title>'
        '<body><pre style="white-space:pre-wrap;font:15px/1.5 sans-serif">'
        + html.escape(report) + "</pre></body></html>", encoding="utf-8")
    print(f"Rapport gemaakt: {len(verified)} Clubee, {len(twizzit)} Twizzit; {len(errors)} bronfouten.")
    if args.send_email:
        send_report(report, args.recipient)
        print("Rapport aangeboden aan de mailserver voor " + args.recipient)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
