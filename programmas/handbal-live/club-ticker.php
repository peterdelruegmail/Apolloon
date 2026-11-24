<?php
declare(strict_types=1);
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');
require_once __DIR__ . '/club-ticker-data.php';
if (($_SERVER['REQUEST_METHOD'] ?? 'GET') !== 'GET') respond(['error' => 'Deze actie wordt niet ondersteund.'], 405);
foreach (['start', 'end'] as $key) {
    if (isset($_GET[$key]) && !is_string($_GET[$key])) respond(['error' => 'Ongeldige datum.'], 400);
}
try {
    respond(tickerResult($_GET['start'] ?? null, $_GET['end'] ?? null));
} catch (RuntimeException $error) {
    respond(['error' => $error->getMessage()], in_array($error->getCode(), [400, 502, 503], true) ? $error->getCode() : 502);
}
