#!/usr/bin/env python3
"""
Clubee Standings Scraper
=========================

Haalt de standings-tabel op van een publieke Clubee-pagina (bv. Handball Belgium)
zonder in te loggen. De data zit ingebakken in de server-rendered HTML als een
Next.js RSC-payload (self.__next_f.push([1, "..."])). Dit script zoekt het stuk
met "standingsStats" op, parseert het als JSON en zet het om naar een nette
lijst met team-statistieken.

Gebruik (met league + season, zoals in de URL van je Clubee-standings-pagina):
    python3 clubee_standings_scraper.py --league 18702 --season 220

Voorbeeld met JSON-output:
    python3 clubee_standings_scraper.py --league 18702 --season 220 --json standings.json

Als je club-prefix of pagina-slug anders is dan de standaard (handballbelgium /
standings-371073v4), kan je die overschrijven:
    python3 clubee_standings_scraper.py \
        --league 18702 --season 220 \
        --prefix handballbelgium --page standings-371073v4

Of geef gewoon de volledige URL rechtstreeks mee met --url:
    python3 clubee_standings_scraper.py \
        --url "https://www.clubee.com/handballbelgium/standings-371073v4/leagues/18702/seasons/220"

Meerdere poules/fases:
    Sommige leagues hebben meer dan 1 klassement op dezelfde pagina (bv.
    meerdere poules, of een reguliere fase + play-offs). Dit script vindt ze
    allemaal en toont ze na elkaar. Wil je er maar 1, gebruik dan --group N
    (1-based, in de volgorde waarin ze op de pagina staan):
        python3 clubee_standings_scraper.py --league 18725 --season 220 --group 1

Let op:
- Dit is scraping, geen officiële API. Als Clubee hun frontend-framework of
  layout wijzigt, kan dit script stuklopen en moet de parsing-logica worden
  aangepast.
- Gebruik een redelijke interval (bv. niet vaker dan elke paar uur) om de
  Clubee-servers niet onnodig te belasten.
"""

import sys
import json
import re
import argparse
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Standaardwaarden voor Handball Belgium. Pas aan met --prefix / --page
# als je een andere club/federatie of een andere pagina wil gebruiken.
DEFAULT_PREFIX = "handballbelgium"
DEFAULT_PAGE = "standings-371073v4"


def build_url(league: str, season: str, prefix: str, page: str) -> str:
    return f"https://www.clubee.com/{prefix}/{page}/leagues/{league}/seasons/{season}"


def fetch_html(url: str) -> str:
    """Haalt de rauwe HTML van de pagina op (geen login/cookies nodig)."""
    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=20) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            return resp.read().decode(charset, errors="replace")
    except HTTPError as e:
        raise RuntimeError(f"HTTP-fout {e.code} bij ophalen van {url}") from e
    except URLError as e:
        raise RuntimeError(f"Netwerkfout bij ophalen van {url}: {e.reason}") from e


def extract_next_f_chunks(html: str):
    """
    Vindt alle self.__next_f.push([1, "...JSON-string..."]) blokken in de HTML
    en decodeert de JS-string erin (die zelf JSON-geëscapet is).
    """
    chunks = []
    pattern = re.compile(
        r'self\.__next_f\.push\(\[1,\s*(".*?")\]\)', re.DOTALL
    )
    for match in pattern.finditer(html):
        raw_js_string = match.group(1)
        try:
            decoded = json.loads(raw_js_string)
            chunks.append(decoded)
        except json.JSONDecodeError:
            continue
    return chunks


def _extract_balanced_array(chunk: str, start: int):
    """Leest vanaf een '[' een volledig gebalanceerd JSON-array-stuk uit `chunk`."""
    depth = 0
    end = None
    in_string = False
    escape = False
    for i in range(start, len(chunk)):
        c = chunk[i]
        if in_string:
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == '"':
                in_string = False
            continue
        else:
            if c == '"':
                in_string = True
            elif c == "[":
                depth += 1
            elif c == "]":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
    return end


def find_standings_blocks(chunks) -> list:
    """
    Zoekt in de gedecodeerde chunks naar ALLE "standingsStats":[...] stukken
    (er kan meer dan 1 fase/poule/groep zijn, bv. bij reeksen met meerdere
    poules of een reguliere fase + play-offs) en geeft een lijst van
    standings-blocks terug (1 per groep/fase), gededupliceerd.
    """
    blocks = []
    seen = set()

    for chunk in chunks:
        search_from = 0
        while True:
            idx = chunk.find('"standingsStats":', search_from)
            if idx == -1:
                break

            start = chunk.find("[", idx)
            if start == -1:
                break

            end = _extract_balanced_array(chunk, start)
            if end is None:
                break

            array_str = chunk[start:end]
            search_from = end

            try:
                standings_array = json.loads(array_str)
            except json.JSONDecodeError:
                continue

            for group_block in standings_array:
                # Dedupliceren op basis van inhoud, want dezelfde fase kan
                # in meerdere RSC-chunks voorkomen.
                key = json.dumps(group_block, sort_keys=True)
                if key in seen:
                    continue
                seen.add(key)
                blocks.append(group_block)

    return blocks


def guess_block_name(block: dict, index: int) -> str:
    """Probeert een leesbare naam voor een fase/poule/groep te vinden."""
    for key in ("name", "title", "label", "phase", "phaseName", "groupName", "poule"):
        value = block.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return f"Groep {index + 1}"


def normalize_standings(standings_block: dict):
    """
    Zet het rauwe Clubee-formaat om naar een simpele lijst van dicts:
    [{ "position": 1, "team": "...", "logo": "...", "mp":0, "w":0, "d":0,
       "l":0, "gs":0, "ga":0, "gd":0, "pts":0 }, ...]
    """
    if not standings_block:
        return []

    rows = standings_block.get("rows", [])
    result = []
    for position, row in enumerate(rows, start=1):
        group = row.get("group", {})
        result.append({
            "position": position,
            "team": group.get("full_name") or group.get("name"),
            "team_id": group.get("id"),
            "logo": group.get("pic"),
            "mp": row.get("stat1"),
            "w": row.get("stat2"),
            "d": row.get("stat3"),
            "l": row.get("stat4"),
            "gs": row.get("stat5"),
            "ga": row.get("stat6"),
            "gd": row.get("stat7"),
            "pts": row.get("stat8"),
        })
    return result


def scrape_clubee_standings(url: str):
    """
    Geeft een lijst terug van (naam, standings) tuples: 1 per groep/poule/fase
    die op de pagina gevonden is. Meestal is dat er 1, maar bij leagues met
    meerdere poules of een reguliere fase + play-offs kunnen dat er meerdere zijn.
    """
    html = fetch_html(url)
    chunks = extract_next_f_chunks(html)
    if not chunks:
        raise RuntimeError(
            "Geen Next.js data-chunks gevonden. Is dit wel een Clubee-standings-URL? "
            "Of heeft Clubee hun frontend gewijzigd?"
        )

    standings_blocks = find_standings_blocks(chunks)
    if not standings_blocks:
        raise RuntimeError(
            "Geen 'standingsStats' gevonden in de pagina. "
            "Controleer of league/season correct zijn, of geef --url rechtstreeks mee."
        )

    results = []
    for i, block in enumerate(standings_blocks):
        name = guess_block_name(block, i)
        results.append((name, normalize_standings(block)))
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Scrape Clubee standings zonder login (via league + season, of een volledige URL)."
    )
    parser.add_argument(
        "--league", help="League-ID uit de Clubee-URL (bv. 18702)"
    )
    parser.add_argument(
        "--season", help="Season-ID uit de Clubee-URL (bv. 220)"
    )
    parser.add_argument(
        "--prefix",
        default=DEFAULT_PREFIX,
        help=f"Club/federatie-prefix in de URL (standaard: {DEFAULT_PREFIX})",
    )
    parser.add_argument(
        "--page",
        default=DEFAULT_PAGE,
        help=f"Standings-pagina-slug in de URL (standaard: {DEFAULT_PAGE})",
    )
    parser.add_argument(
        "--url",
        help="Volledige Clubee standings-URL (overschrijft --league/--season/--prefix/--page)",
    )
    parser.add_argument("--json", metavar="FILE", help="Schrijf output naar dit JSON-bestand")
    parser.add_argument(
        "--group",
        type=int,
        metavar="N",
        help="Als er meerdere poules/fases zijn: enkel groep N tonen (1-based). "
             "Standaard: allemaal tonen.",
    )
    args = parser.parse_args()

    if args.url:
        url = args.url
    else:
        if not args.league or not args.season:
            parser.error("Geef ofwel --url mee, ofwel zowel --league als --season.")
        url = build_url(args.league, args.season, args.prefix, args.page)

    try:
        groups = scrape_clubee_standings(url)
    except RuntimeError as e:
        print(f"Fout: {e}", file=sys.stderr)
        sys.exit(1)

    if not groups:
        print("Geen standings-rijen gevonden (leeg resultaat).", file=sys.stderr)
        sys.exit(1)

    if args.group is not None:
        if not (1 <= args.group <= len(groups)):
            print(
                f"Fout: --group {args.group} bestaat niet. Er zijn {len(groups)} "
                f"groep(en)/poule(s) gevonden (1-{len(groups)}).",
                file=sys.stderr,
            )
            sys.exit(1)
        groups = [groups[args.group - 1]]

    groups = [(name, rows) for name, rows in groups if rows]
    if not groups:
        print("Geen standings-rijen gevonden (leeg resultaat).", file=sys.stderr)
        sys.exit(1)

    if args.json:
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_url": url,
            "groups": [
                {"name": name, "standings": rows} for name, rows in groups
            ],
        }
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        total = sum(len(rows) for _, rows in groups)
        print(f"Weggeschreven naar {args.json} ({len(groups)} groep(en), {total} teams totaal)")
    else:
        header = f"{'#':<3} {'Team':<40} {'MP':>3} {'W':>3} {'D':>3} {'L':>3} {'GS':>4} {'GA':>4} {'GD':>4} {'Pts':>4}"
        print(f"Bron: {url}")
        if len(groups) > 1:
            print(f"({len(groups)} groepen/poules gevonden)")
        for name, rows in groups:
            print(f"\n== {name} ==")
            print(header)
            print("-" * len(header))
            for row in rows:
                print(
                    f"{row['position']:<3} {row['team'][:40]:<40} "
                    f"{row['mp']:>3} {row['w']:>3} {row['d']:>3} {row['l']:>3} "
                    f"{row['gs']:>4} {row['ga']:>4} {row['gd']:>4} {row['pts']:>4}"
                )


if __name__ == "__main__":
    main()
