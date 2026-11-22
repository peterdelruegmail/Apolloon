<?php
declare(strict_types=1);
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');

require __DIR__ . '/clubee.php';
if (($_SERVER['REQUEST_METHOD'] ?? 'GET') !== 'GET') {
    respond(['error' => 'Deze actie wordt niet ondersteund.'], 405);
}
$source = $_GET['source'] ?? 'https://www.clubee.com/handballbelgium/first-division-m--982001v4/leagues/18702/seasons/220';
if (!is_string($source)) respond(['error' => 'Ongeldige competitielink.'], 400);
$parts = parse_url($source);
if (!$parts || ($parts['scheme'] ?? '') !== 'https'
    || !in_array($parts['host'] ?? '', ['www.clubee.com', 'clubee.com'], true)
    || isset($parts['user']) || isset($parts['pass']) || isset($parts['port'])
    || !preg_match('~^/handballbelgium/[a-zA-Z0-9_-]+v4(?:/leagues/[0-9]+/seasons/[0-9]+)?/?$~', $parts['path'] ?? '')) {
    respond(['error' => 'Kies een geldige competitie van Handball Belgium.'], 400);
}
$source = 'https://' . $parts['host'] . $parts['path'];
// Cache only successful parsed responses, never empty/error pages.
$cacheDir = sys_get_temp_dir() . '/apolloon-handbal-live';
$cacheFile = $cacheDir . '/' . hash('sha256', $source) . '.json';
$cached = null;
if (is_file($cacheFile) && (time() - (int)filemtime($cacheFile)) < 86400) {
    $cached = json_decode((string)@file_get_contents($cacheFile), true);
}
$html = fetchClubee($source);
preg_match_all('~<a\b[^>]*href="([^"<>]*/games/[0-9]+)"[^>]*>(.*?)</a>~s', $html, $cards, PREG_SET_ORDER);
// Clubee may render an empty overlay link with the card content in sibling nodes.
// Read the surrounding card via DOM rather than assuming the anchor wraps its text.
if (class_exists('DOMDocument')) {
    $dom = new DOMDocument();
    $previous = libxml_use_internal_errors(true);
    $dom->loadHTML('<?xml encoding="UTF-8">' . $html);
    libxml_clear_errors();
    libxml_use_internal_errors($previous);
    $xpath = new DOMXPath($dom);
    foreach ($xpath->query('//a[contains(@href, "/games/")]') as $link) {
        $href = $link->getAttribute('href');
        if (!preg_match('~/games/[0-9]+~', $href)) continue;
        $node = $link->parentNode;
        for ($depth = 0; $depth < 5 && $node; $depth++, $node = $node->parentNode) {
            $text = trim(preg_replace('/\\s+/u', ' ', $node->textContent ?? ''));
            if (strlen($text) > 20 && strlen($text) < 1500 && preg_match('~[0-9]{2}[./][0-9]{2}[./][0-9]{4}~', $text)) {
                $cards[] = [0 => '', 1 => $href, 2 => $dom->saveHTML($node)];
                break;
            }
        }
    }
}
$games = [];
$seen = [];
function cardLogo(string $card, string $side): ?string {
    if (!preg_match('~<div\b[^>]*class="[^"]*_team' . $side . '[^"]*"[^>]*>\s*<img\b[^>]*src="([^"]+)"~s', $card, $match)) return null;
    $url = html_entity_decode($match[1], ENT_QUOTES | ENT_HTML5, 'UTF-8');
    $parts = parse_url($url);
    if (!$parts || ($parts['scheme'] ?? '') !== 'https' || isset($parts['user']) || isset($parts['pass'])) return null;
    $host = $parts['host'] ?? '';
    if (!in_array($host, ['www.clubee.com', 'clubee.com', 'clubee-websites-prod.s3.eu-central-1.amazonaws.com'], true)) return null;
    return $url;
}
foreach ($cards as $card) {
    preg_match_all('~<strong\b[^>]*>(.*?)</strong>~s', $card[2], $namesMatch);
    $names = array_map('textValue', $namesMatch[1]);
    preg_match_all('~<(?:p|h3)\b[^>]*>(.*?)</(?:p|h3)>~s', $card[2], $valuesMatch);
    $values = array_map('textValue', $valuesMatch[1]);
    $date = null;
    $score = null;
    $time = null;
    foreach ($values as $value) {
        if (preg_match('~^[0-9]{2}[./][0-9]{2}[./][0-9]{4}$~', $value)) $date = $value;
        if (preg_match('/^[0-9]+\s*[--]\s*[0-9]+$/u', $value)) $score = $value;
        if (preg_match('/^[0-9]{1,2}:[0-9]{2}$/', $value)) $time = $value;
    }
    if (count($names) !== 2 || !$date || isset($seen[$card[1]])) continue;
    [$day, $month, $year] = explode('.', str_replace('/', '.', $date));
    if (!checkdate((int)$month, (int)$day, (int)$year)) continue;
    $games[] = ['id' => $card[1], 'home' => $names[0], 'away' => $names[1],
        'date' => "$year-$month-$day", 'score' => $score, 'time' => $time,
        'homeLogo' => cardLogo($card[2], 'Left'), 'awayLogo' => cardLogo($card[2], 'Right')];
    $seen[$card[1]] = true;
}
if (!$games) {
    // Diagnostics without exposing the upstream HTML or private server details.
    $diagnostics = [
        'htmlBytes' => strlen($html),
        'gameLinks' => preg_match_all('~/games/[0-9]+~', $html),
        'anchorLinks' => count($cards),
        'sampleCardText' => isset($cards[0][2]) ? mb_substr(preg_replace('/\\s+/u', ' ', textValue($cards[0][2])), 0, 450) : null,
        'sampleStrongCount' => isset($cards[0][2]) ? preg_match_all('~<strong\\b~i', $cards[0][2]) : 0,
        'nextPayloads' => preg_match_all('~self\\.__next_f\\.push~', $html),
    ];
    if (is_array($cached) && !empty($cached['games'])) {
        $cached['stale'] = true;
        $cached['warning'] = 'Clubee leverde geen herkenbare wedstrijden; laatste succesvolle lijst wordt getoond.';
        respond($cached);
    }
    respond(['error' => 'Geen herkenbare wedstrijden gevonden. Mogelijk heeft Clubee de HTML-structuur gewijzigd.', 'diagnostics' => $diagnostics], 502);
}
usort($games, fn(array $a, array $b): int => strcmp($a['date'], $b['date']) ?: strcmp($a['time'] ?? '', $b['time'] ?? ''));
$result = ['games' => $games, 'checkedAt' => gmdate('Y-m-d\TH:i:s\Z'), 'source' => $source];
if ((is_dir($cacheDir) || @mkdir($cacheDir, 0700, true)) && is_writable($cacheDir)) {
    @file_put_contents($cacheFile, json_encode($result, JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE), LOCK_EX);
}
respond($result);

