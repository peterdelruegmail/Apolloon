<?php
declare(strict_types=1);
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
header('X-Content-Type-Options: nosniff');

function rankingRespond(array $payload, int $status = 200): void {
    http_response_code($status);
    echo json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE);
    exit;
}
if (($_SERVER['REQUEST_METHOD'] ?? 'GET') !== 'GET') {
    header('Allow: GET');
    rankingRespond(['error' => 'Alleen GET wordt ondersteund.'], 405);
}
$config = require __DIR__ . '/config.php';
require __DIR__ . '/clubee.php';
$league = $_GET['league'] ?? 'Heren1';
$season = $_GET['season'] ?? (string) $config['season'];
if (!is_string($league) || !isset($config['leagues'][$league])
    || !is_string($season) || !preg_match('/^[1-9][0-9]{0,5}$/D', $season)) {
    rankingRespond(['error' => 'Ongeldige ploeg of ongeldig seizoen.'], 400);
}
$source = 'https://www.clubee.com/handballbelgium/standings-371073v4/leagues/'
    . $config['leagues'][$league] . '/seasons/' . $season;
try {
    $groups = rankingGroups(rankingFetch($source));
    // No standings files or server cache: each request contacts Clubee.
    rankingRespond(['checked_at' => gmdate('Y-m-d\TH:i:s\Z'), 'source_url' => $source, 'groups' => $groups]);
} catch (RuntimeException $error) {
    rankingRespond(['error' => $error->getMessage()], 502);
}
