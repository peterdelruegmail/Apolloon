<?php
declare(strict_types=1);
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');
require __DIR__ . '/club-ticker-data.php';
if (($_SERVER['REQUEST_METHOD'] ?? 'GET') !== 'GET') respond(['error' => 'Deze actie wordt niet ondersteund.'], 405);
$today = new DateTimeImmutable('today', new DateTimeZone('Europe/Brussels'));
$monday = $today->modify('-' . ((int)$today->format('N') - 1) . ' days');
$start = $_GET['start'] ?? $monday->format('Y-m-d');
$end = $_GET['end'] ?? $monday->modify('+6 days')->format('Y-m-d');
if (!is_string($start) || !is_string($end) || !($from = tickerDate($start)) || !($to = tickerDate($end))
    || $from > $to || (int)$from->diff($to)->format('%a') > 366) {
    respond(['error' => 'Kies start en end als JJJJ-MM-DD, met een oplopende periode van maximaal een jaar.'], 400);
}
@set_time_limit(150);
try {
    $calendar = tickerCalendar();
    $games = array_values(array_filter($calendar['games'], fn($g) => $g['date'] >= $start && $g['date'] <= $end));
    $urls = [];
    foreach ($games as $index => $game) {
        if (!$game['cancelled'] && $game['date'] === $today->format('Y-m-d')) {
            $urls[$index] = 'https://apiv3.clubee.com/scenes/' . $game['id'] . '?language=en';
        }
    }
    $failures = 0;
    foreach (tickerFetchPages($urls, true) as $index => $body) {
        $match = $body === null ? null : json_decode($body, true);
        if (!is_array($match) || (string)($match['id'] ?? '') !== $games[$index]['id']) {
            $failures++;
            $games[$index]['notUpdated'] = true;
        } else {
            $games[$index]['score'] = scoreValue($match);
            $games[$index]['cancelled'] = !empty($match['cancelled']);
        }
    }
    $warning = $calendar['warning'] ?? '';
    if ($failures) $warning .= ($warning ? ' ' : '') . $failures . ' scorecontrole(s) mislukt; zie niet bijgewerkt.';
    respond(['games' => $games, 'start' => $start, 'end' => $end,
        'calendarCheckedAt' => $calendar['checkedAt'], 'checkedAt' => gmdate('Y-m-d\TH:i:s\Z'),
        'warning' => $warning, 'stale' => isset($calendar['warning'])]);
} catch (RuntimeException $error) {
    respond(['error' => $error->getMessage()], in_array($error->getCode(), [502, 503], true) ? $error->getCode() : 502);
}
