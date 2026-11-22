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
function sheetOfficials(?array $info): array {
    $result = ['referees' => [], 'officials' => []];
    $roles = [
        'referee' => 'Scheidsrechter',
        'referee_position.timekeeper' => 'Tijdwaarnemer',
        'referee_position.match_supervisor' => 'Wedstrijdtoezichter',
        'referee_position.table_official' => 'Tafelofficial',
        'referee_position.technical_delegate' => 'Technisch afgevaardigde',
    ];
    $seen = [];
    foreach ($info['officials'] ?? [] as $official) {
        if (!is_array($official) || !empty($official['canceled']) || !empty($official['deleted'])) continue;
        $name = trim((string)($official['full_name'] ?? ''));
        if ($name === '') continue;
        $isReferee = ($official['type'] ?? '') === 'referee';
        $position = $official['o_position']['name'] ?? '';
        $role = $roles[$position] ?? ($official['position'] ?? ($isReferee ? 'Scheidsrechter' : 'Official'));
        $group = $isReferee ? 'referees' : 'officials';
        $key = $group . "\0" . $role . "\0" . $name;
        if (isset($seen[$key])) continue;
        $seen[$key] = true;
        $result[$group][] = ['name' => $name, 'role' => $role];
    }
    return $result;
}
$base = 'https://www.clubee.com/handballbelgium/games/' . $id;
try {
    $d = parseSheet(fetchClubee($base . '/gamesheet'), fetchClubee($base . '/lineup'));
    $info = fetchClubeeMatch($id);
    $d += sheetOfficials($info);
    $start = $info['start_date'] ?? '';
    $d['details'] = is_string($start) && preg_match('/^(\d{4})-(\d{2})-(\d{2})T(\d{2}:\d{2})/', $start, $m)
        ? 'Wedstrijd: ' . $m[3] . '/' . $m[2] . '/' . $m[1] . ' om ' . $m[4] : '';
    $d['matchId'] = $id;
    respond(['match' => $d]);
} catch (RuntimeException $e) {
    respond(['error' => $e->getMessage()], 422);
}
