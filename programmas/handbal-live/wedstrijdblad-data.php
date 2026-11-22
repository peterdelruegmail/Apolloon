<?php
declare(strict_types=1);
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');
require __DIR__ . '/clubee.php';
if (($_SERVER['REQUEST_METHOD'] ?? 'GET') !== 'GET') respond(['error' => 'Methode niet ondersteund.'], 405);
$id = $_GET['match'] ?? '';
if (!is_string($id) || !preg_match('/^[1-9][0-9]{0,11}$/D', $id)) respond(['error' => 'Ongeldig wedstrijdnummer.'], 400);
if (!class_exists('DOMDocument')) respond(['error' => 'PHP DOM/XML ontbreekt op de hosting.'], 503);
require __DIR__ . '/wedstrijdblad-parser.php';
$base = 'https://www.clubee.com/handballbelgium/games/' . $id;
try {
    $d = parseSheet(fetchClubee($base . '/gamesheet'), fetchClubee($base . '/lineup'));
    $info = fetchClubeeMatch($id);
    $start = $info['start_date'] ?? '';
    $d['details'] = is_string($start) && preg_match('/^(\d{4})-(\d{2})-(\d{2})T(\d{2}:\d{2})/', $start, $m)
        ? 'Wedstrijd: ' . $m[3] . '/' . $m[2] . '/' . $m[1] . ' om ' . $m[4] : '';
    $d['matchId'] = $id;
    respond(['match' => $d]);
} catch (RuntimeException $e) {
    respond(['error' => $e->getMessage()], 422);
}
