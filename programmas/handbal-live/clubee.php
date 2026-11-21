<?php
declare(strict_types=1);
function respond(array $body, int $status = 200): void {
    http_response_code($status);
    echo json_encode($body, JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE);
    exit;
}
function textValue(string $html): string {
    return trim(html_entity_decode(strip_tags($html), ENT_QUOTES | ENT_HTML5, 'UTF-8'));
}
function fetchClubee(string $source): string {
    if (!function_exists('curl_init')) {
        respond(['error' => 'De hosting mist de PHP cURL-uitbreiding. Vraag de hostingbeheerder die in te schakelen.'], 503);
    }
    $curl = curl_init($source);
    curl_setopt_array($curl, [CURLOPT_RETURNTRANSFER => true, CURLOPT_FOLLOWLOCATION => false,
        CURLOPT_CONNECTTIMEOUT => 10, CURLOPT_TIMEOUT => 20,
        CURLOPT_HTTPHEADER => ['Accept: text/html', 'Cache-Control: no-cache'],
        CURLOPT_SSL_VERIFYPEER => true, CURLOPT_SSL_VERIFYHOST => 2]);
    $html = curl_exec($curl);
    $status = (int) curl_getinfo($curl, CURLINFO_HTTP_CODE);
    curl_close($curl);
    if ($html === false || $status !== 200) {
        respond(['error' => 'Clubee kon niet worden opgehaald' . ($status ? ' (HTTP ' . $status . ')' : '') . '. Controleer of de hosting uitgaande HTTPS-verbindingen toestaat.'], 502);
    }
    return $html;
}
function fetchClubeeMatch(string $id): ?array {
    if (!function_exists('curl_init')) return null;
    $curl = curl_init('https://apiv3.clubee.com/scenes/' . $id . '?language=en');
    curl_setopt_array($curl, [CURLOPT_RETURNTRANSFER => true, CURLOPT_FOLLOWLOCATION => false,
        CURLOPT_CONNECTTIMEOUT => 5, CURLOPT_TIMEOUT => 10,
        CURLOPT_HTTPHEADER => ['Accept: application/json', 'X-Website: handballbelgium', 'Cache-Control: no-cache'],
        CURLOPT_SSL_VERIFYPEER => true, CURLOPT_SSL_VERIFYHOST => 2]);
    $body = curl_exec($curl);
    $status = (int) curl_getinfo($curl, CURLINFO_HTTP_CODE);
    curl_close($curl);
    if ($body === false || $status !== 200) return null;
    $game = json_decode($body, true);
    if (!is_array($game) || (string)($game['id'] ?? '') !== $id
        || !is_array($game['team1'] ?? null) || !is_array($game['team2'] ?? null)) return null;
    return $game;
}
function scoreValue(array $game): ?string {
    // Een nul is een geldige score; afwezige of lege scores zijn onbekend.
    $a = $game['score1'] ?? null;
    $b = $game['score2'] ?? null;
    $valid = static fn($value): bool => is_int($value) && $value >= 0
        || is_string($value) && preg_match('/^[0-9]+$/D', $value) === 1;
    if (!$valid($a) && !$valid($b)) return null;
    return ($valid($a) ? (string)$a : '0') . ' - ' . ($valid($b) ? (string)$b : '0');
}
