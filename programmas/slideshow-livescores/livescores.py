"""Public Clubee data for the slideshow; no website hosting required."""
import concurrent.futures
import datetime as dt
import html
import json
import re
import urllib.request
import urllib.error
import ssl
import time
import truststore

ROOT = 'https://www.clubee.com/handballbelgium'
CLUB_SOURCE = 'apolloon-spurs'
CLUB_LABEL = 'Alle matchen van Apolloon Spurs'
_club_calendar = None


def valid_source(source, allow_club=True):
    return (allow_club and source == CLUB_SOURCE) or bool(re.fullmatch(
        r'https://(?:www\.)?clubee\.com/handballbelgium/[\w-]+v4(?:/leagues/\d+/seasons/\d+)?/?', source))


def fetch(url, api=False):
    headers = {'Accept': 'application/json' if api else 'text/html',
               'User-Agent': 'Mozilla/5.0', 'Cache-Control': 'no-cache'}
    if api:
        headers['X-Website'] = 'handballbelgium'
    try:
        context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=20, context=context) as response:
            return response.read(8_000_000).decode('utf-8')
    except urllib.error.HTTPError as exc:
        raise ConnectionError(f'Clubee antwoordt met HTTP {exc.code}: {exc.reason}') from exc
    except urllib.error.URLError as exc:
        reason = exc.reason
        if isinstance(reason, ssl.SSLCertVerificationError):
            raise ConnectionError(f'Het beveiligingscertificaat wordt op deze pc niet vertrouwd. Controleer de Windows-datum en laat de certificaten of netwerkbeveiliging nakijken. Details: {reason}') from exc
        raise ConnectionError(f'Geen verbinding met {url.split("/")[2]}: {reason}') from exc

def text(value):
    return ' '.join(html.unescape(re.sub('<[^>]+>', '', value)).split())

def payloads(page):
    for chunk in re.findall(r'self\.__next_f\.push\((\[.*?\])\)</script>', page, re.S):
        try:
            data = json.loads(chunk)
            if len(data) < 2 or not isinstance(data[1], str):
                continue
            for line in data[1].splitlines():
                try:
                    yield json.loads(line.split(':', 1)[1])
                except (ValueError, IndexError):
                    pass
        except ValueError:
            pass

def competitions():
    found = {}
    def walk(node, group='', inside=False):
        if isinstance(node, list):
            for item in node:
                walk(item, group, inside)
        elif isinstance(node, dict):
            inside = inside or node.get('name') == 'COMPETITION'
            if inside and node.get('page', {}).get('type') == 'results' and re.fullmatch(r'[\w-]+v4', node.get('url', '')):
                found[ROOT + '/' + node['url']] = {'name': text(node['name']), 'source': ROOT + '/' + node['url']}
            for item in node.values():
                if isinstance(item, (dict, list)):
                    walk(item, group, inside)
    for data in payloads(fetch(ROOT)):
        walk(data)
    if not found:
        raise ValueError('De divisies konden niet uit Clubee worden gelezen.')
    return sorted(found.values(), key=lambda item: item['name'])

def games(source):
    if not valid_source(source, allow_club=False):
        raise ValueError('Kies een geldige Clubee-divisie.')
    found = {}
    page = fetch(source)
    for card in re.findall(r'<li\b[^>]*>(.*?)</li>', page, re.S):
        identifier = re.search(r'href="[^"<>]*/games/(\d+)"', card)
        names = [text(n) for n in re.findall(r'<span\b[^>]*class="[^"]*\b[\w-]+_name\b[^"]*"[^>]*>(.*?)</span>', card, re.S)]
        date = re.search(r'>(\d{2}[./]\d{2}[./]\d{4})<', card)
        time = re.search(r'>(\d{1,2}:\d{2})<', card)
        score = re.search(r'<span\b[^>]*class="[^"]*\b[\w-]+_score\b[^"]*"[^>]*>(.*?)</div>', card, re.S)
        score_text = text(score.group(1)) if score else ''
        if identifier and len(names) == 2 and date:
            key = identifier.group(1)
            found[key] = {'id': key, 'home': names[0], 'away': names[1],
                'date': dt.datetime.strptime(date.group(1).replace('/', '.'), '%d.%m.%Y').date().isoformat(),
                'time': time.group(1) if time else '',
                'score': re.sub(r'\s*:\s*', ' - ', score_text) if re.fullmatch(r'\d+\s*:\s*\d+', score_text) else None}
    for link, card in re.findall(r'<a\b[^>]*href="([^"<>]*/games/\d+)"[^>]*>(.*?)</a>', page, re.S):
        names = [text(n) for n in re.findall(r'<strong\b[^>]*>(.*?)</strong>', card, re.S)]
        values = [text(n) for n in re.findall(r'<(?:p|h3)\b[^>]*>(.*?)</(?:p|h3)>', card, re.S)]
        date = next((v for v in values if re.fullmatch(r'\d{2}[./]\d{2}[./]\d{4}', v)), None)
        if len(names) != 2 or not date:
            continue
        identifier = link.rsplit('/', 1)[1]
        found[identifier] = {'id': identifier, 'home': names[0], 'away': names[1],
            'date': dt.datetime.strptime(date.replace('/', '.'), '%d.%m.%Y').date().isoformat(),
            'time': next((v for v in values if re.fullmatch(r'\d{1,2}:\d{2}', v)), ''),
            'score': next((v for v in values if re.fullmatch(r'\d+\s*[-–]\s*\d+', v)), None)}
    if not found:
        raise ValueError('Geen herkenbare wedstrijden gevonden voor deze divisie.')
    return sorted(found.values(), key=lambda g: (g['date'], g['time']))

def live_game(game):
    data = json.loads(fetch('https://apiv3.clubee.com/scenes/' + game['id'] + '?language=en', True))
    if str(data.get('id')) != game['id']:
        raise ValueError('Onverwacht wedstrijdnummer.')
    def score(value):
        return str(value) if isinstance(value, (str, int)) and not isinstance(value, bool) and re.fullmatch(r'\d+', str(value)) else None
    a, b = score(data.get('score1')), score(data.get('score2'))
    game = dict(game)
    game['score'] = f'{a or "0"} - {b or "0"}' if a is not None or b is not None else None
    if isinstance(data.get('start_date'), str):
        game['time'] = data['start_date'][11:16]
    return game

def club_games():
    """Cache complete scans for five minutes; current scores refresh separately."""
    global _club_calendar
    if _club_calendar is not None and time.monotonic() - _club_calendar[0] < 300:
        return [dict(game) for game in _club_calendar[1]]
    found, failures = {}, []
    items = competitions()
    if not items:
        raise ValueError('Geen competities gevonden voor de clubkalender.')
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        futures = [(item, pool.submit(games, item['source'])) for item in items]
        for item, future in futures:
            try:
                for game in future.result():
                    if any(re.search(r'\bapolloon\b', game[side], re.I) for side in ('home', 'away')):
                        found[game['id']] = game
            except Exception as exc:
                failures.append(f"{item['name']}: {exc}")
    if failures:
        raise ConnectionError('Clubkalender onvolledig; niet alle reeksen konden worden gelezen. '
                              + '; '.join(failures))
    ordered = sorted(found.values(), key=lambda g: (g['date'], g['time'], g['id']))
    _club_calendar = (time.monotonic(), ordered)
    return [dict(game) for game in ordered]


def load_scores(source, start, end):
    calendar = club_games() if source == CLUB_SOURCE else games(source)
    selected = [g for g in calendar if start <= g['date'] <= end]
    failures = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(live_game, g) for g in selected]
        for i, future in enumerate(futures):
            try:
                selected[i] = future.result()
            except Exception:
                failures += 1
                # Do not silently label a schedule-page score as current.
                selected[i]['score'] = (selected[i]['score'] or '—') + ' (niet bijgewerkt)'
    return selected, failures

def ticker_text(games):
    return '   •   '.join(f"{g['date'][8:10]}/{g['date'][5:7]} {g['time']}  {g['home']}  {g['score'] or '—'}  {g['away']}" for g in games) or 'Geen wedstrijden in het gekozen datumbereik'


