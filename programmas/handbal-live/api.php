<?php
declare(strict_types=1);
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');
require_once __DIR__ . '/competition-data.php';
if (($_SERVER['REQUEST_METHOD'] ?? 'GET') !== 'GET') respond(['error' => 'Deze actie wordt niet ondersteund.'], 405);
$source = $_GET['source'] ?? 'https://www.clubee.com/handballbelgium/first-division-m--982001v4/leagues/18702/seasons/220';
if (!is_string($source)) respond(['error' => 'Ongeldige competitielink.'], 400);
try {
    respond(competitionGames($source));
} catch (RuntimeException $error) {
    respond(['error' => $error->getMessage()], in_array($error->getCode(), [400, 502, 503], true) ? $error->getCode() : 502);
}
