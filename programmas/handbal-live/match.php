<?php
declare(strict_types=1);
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');
require __DIR__ . '/clubee.php';
if (($_SERVER['REQUEST_METHOD'] ?? 'GET') !== 'GET') respond(['error' => 'Deze actie wordt niet ondersteund.'], 405);
$id = $_GET['match'] ?? '';
if (!is_string($id) || !preg_match('/^[1-9][0-9]{0,11}$/', $id)) {
    respond(['error' => 'Geef een geldig wedstrijdnummer mee, bijvoorbeeld score.html?match=2848993.'], 400);
}
$game = fetchClubeeMatch($id);
$html = null;
function findMatch(array $value, string $id): ?array {
    if ((string)($value['id'] ?? '') === $id && isset($value['team1'], $value['team2'])) return $value;
    foreach ($value as $child) {
        if (is_array($child)) {
            $found = findMatch($child, $id);
            if ($found !== null) return $found;
        }
    }
    return null;
}
function matchLogo($url): ?string {
    if (!is_string($url)) return null;
    $parts = parse_url($url);
    if (!$parts || ($parts['scheme'] ?? '') !== 'https' || isset($parts['user']) || isset($parts['pass'])) return null;
    if (!in_array($parts['host'] ?? '', ['www.clubee.com', 'clubee.com', 'clubee-websites-prod.s3.eu-central-1.amazonaws.com', 'd28kyj1r8oju1l.cloudfront.net'], true)) return null;
    return $url;
}
if ($game === null) {
    $html = fetchClubee('https://www.clubee.com/handballbelgium/games/' . $id);
    preg_match_all('~self\.__next_f\.push\((\[.*?\])\)</script>~s', $html, $chunks);
    foreach ($chunks[1] as $chunk) {
        $payload = json_decode($chunk, true);
        if (!is_array($payload) || !is_string($payload[1] ?? null)) continue;
        foreach (explode("\n", $payload[1]) as $line) {
            $position = strpos($line, ':');
            if ($position === false) continue;
            $value = json_decode(substr($line, $position + 1), true);
            if (is_array($value)) $game = findMatch($value, $id);
            if ($game !== null) break 2;
        }
    }
}
if (!$game || empty($game['team1']['name']) || empty($game['team2']['name'])) {
    respond(['error' => 'De wedstrijd is niet gevonden of Clubee heeft de gegevensindeling gewijzigd.'], 404);
}
$score = scoreValue($game);
if ($score === null && $html !== null && preg_match('~<h2\b[^>]*>\s*([0-9]+\s*[--]\s*[0-9]+)\s*</h2>~u', $html, $scoreMatch)) {
    $score = textValue($scoreMatch[1]);
}
respond(['game' => ['id' => $id,
    'home' => $game['team1']['full_name'] ?? $game['team1']['name'],
    'away' => $game['team2']['full_name'] ?? $game['team2']['name'],
    // Clubee publiceert de lokale wedstrijdtijd met een +00:00-suffix.
    // Behoud daarom datum en uur zoals ze op de wedstrijdpagina staan.
    'startDate' => is_string($game['start_date'] ?? null) ? substr($game['start_date'], 0, 10) : null,
    'startTime' => is_string($game['start_date'] ?? null) ? substr($game['start_date'], 11, 5) : null,
    'homeLogo' => matchLogo($game['team1']['pic'] ?? null),
    'awayLogo' => matchLogo($game['team2']['pic'] ?? null), 'score' => $score],
    'checkedAt' => gmdate('Y-m-d\TH:i:s\Z')]);
