<?php
declare(strict_types=1);
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');
require_once __DIR__ . '/club-ticker-data.php';
require_once __DIR__ . '/server-view.php';
if (($_SERVER['REQUEST_METHOD'] ?? 'GET') !== 'GET') respond(['error' => 'Deze actie wordt niet ondersteund.'], 405);
foreach ($_GET as $value) if (!is_string($value)) respond(['error' => 'Ongeldige invoer.'], 400);
@set_time_limit(150);
try {
    if (($_GET['view'] ?? '') === 'ticker') {
        $data = tickerResult($_GET['start'] ?? null, $_GET['end'] ?? null);
        respond(['html' => viewTicker($data['games']), 'hasGames' => !empty($data['games']), 'warning' => $data['warning'],
            'checkedAt' => (new DateTimeImmutable($data['checkedAt']))->setTimezone(new DateTimeZone('Europe/Brussels'))->format('H:i:s')]);
    }
    require_once __DIR__ . '/competition-data.php';
    require_once __DIR__ . '/competition-menu.php';
    $today = new DateTimeImmutable('today', new DateTimeZone('Europe/Brussels'));
    [$from, $to] = viewPeriod($_GET, $today);
    $action = $_GET['action'] ?? '';
    $requestedSource = $_GET['source'] ?? 'https://www.clubee.com/handballbelgium/first-division-m--982001v4/leagues/18702/seasons/220';
    $source = $requestedSource === 'apolloon' ? 'apolloon' : competitionSource($requestedSource);
    $options = null;
    if ($action === 'init') {
        try {
            $menu = competitionMenu();
            $found = $source === 'apolloon';
            foreach ($menu as $item) {
                if ($source === $item['source'] || str_starts_with($source, $item['source'] . '/')) $found = true;
            }
            if (!$found) {
                $source = $menu[0]['source'];
                foreach ($menu as $item) if ($item['name'] === 'DIVISION 1 (M)') $source = $item['source'];
            }
            $options = viewOptions($menu, $source);
        } catch (RuntimeException $error) {
            $options = viewOptions([], $source);
            if ($source !== 'apolloon') {
                $options .= '<option selected value="' . viewEscape($source) . '">Competitie - rechtstreekse link</option>';
            }
        }
    }
    // Return the validated form first, so an upstream outage never disables the controls.
    $apolloon = ($_GET['apolloon'] ?? '1') !== '0';
    $state = ['source' => $source, 'from' => $from, 'to' => $to, 'apolloon' => $apolloon ? '1' : '0'];
    $base = ['from' => viewDisplayDate($from), 'to' => viewDisplayDate($to), 'options' => $options,
        'query' => http_build_query($state), 'period' => viewDisplayDate($from) . ' - ' . viewDisplayDate($to)];
    try {
        $allApolloon = $source === 'apolloon';
        $data = $allApolloon ? tickerResult($from, $to) : competitionGames($source);
        $games = viewSelectGames($data['games'], $from, $to, $apolloon);
        $now = new DateTimeImmutable('now', new DateTimeZone('Europe/Brussels'));
        $urls = [];
        // The club ticker has already refreshed today's scores.
        foreach ($allApolloon ? [] : $games as $index => $game) {
            $id = basename($game['id']);
            if ($game['date'] === $now->format('Y-m-d') && (empty($game['time']) || str_pad($game['time'], 5, '0', STR_PAD_LEFT) <= $now->format('H:i'))
                && preg_match('/^[1-9][0-9]{0,11}$/D', $id)) {
                $urls[$index] = 'https://apiv3.clubee.com/scenes/' . $id . '?language=en';
            }
        }
        $failures = 0;
        foreach (tickerFetchPages($urls, true) as $index => $body) {
            $match = $body === null ? null : json_decode($body, true);
            if (!is_array($match) || (string)($match['id'] ?? '') !== basename($games[$index]['id'])
                || !is_array($match['team1'] ?? null) || !is_array($match['team2'] ?? null)) {
                $failures++;
            } elseif (($score = scoreValue($match)) !== null) {
                $games[$index]['score'] = $score;
            }
        }
        $checkedAt = (new DateTimeImmutable($data['checkedAt']))->setTimezone(new DateTimeZone('Europe/Brussels'))->format('H:i:s');
        $status = (count($games) ? count($games) . ' wedstrijden' : 'Geen wedstrijden in deze periode') . ' · opgehaald om ' . $checkedAt;
        if (!empty($data['warning'])) $status .= ' ' . $data['warning'];
        elseif (!empty($data['stale'])) $status .= ' De laatste succesvolle wedstrijdlijst wordt getoond.';
        if ($failures) $status .= ' ' . $failures . ' live-scorecontrole(s) mislukt; de score uit de wedstrijdlijst blijft staan.';
        respond($base + ['html' => viewMatches($games), 'count' => count($games), 'status' => $status]);
    } catch (RuntimeException $error) {
        // Keep the last displayed results only when their filters still match.
        respond($base + ['error' => $error->getMessage()], in_array($error->getCode(), [400, 404, 502, 503], true) ? $error->getCode() : 502);
    }
} catch (RuntimeException $error) {
    respond(['error' => $error->getMessage()], in_array($error->getCode(), [400, 404, 502, 503], true) ? $error->getCode() : 502);
}
