<?php
declare(strict_types=1);
require_once __DIR__ . '/clubee.php';
function competitionSource(string $source): string {
    $parts = parse_url($source);
    if (!$parts || ($parts['scheme'] ?? '') !== 'https'
        || !in_array($parts['host'] ?? '', ['www.clubee.com', 'clubee.com'], true)
        || isset($parts['user']) || isset($parts['pass']) || isset($parts['port'])
        || !preg_match('~^/handballbelgium/[a-zA-Z0-9_-]+v4(?:/leagues/[0-9]+/seasons/[0-9]+)?/?$~', $parts['path'] ?? '')) {
        throw new RuntimeException('Kies een geldige competitie van Handball Belgium.', 400);
}
$source = 'https://' . $parts['host'] . $parts['path'];
return $source;
}
function cardField(DOMXPath $xpath, DOMNode $node, string $suffix): ?DOMNode {
    return $xpath->query('.//*[contains(concat(" ", normalize-space(@class), " "), "_' . $suffix . ' ")]', $node)->item(0);
}
function cardText(?DOMNode $node): string {
    return $node ? trim(preg_replace('/\s+/u', ' ', $node->textContent)) : '';
}
function logoUrl(string $url): ?string {
    $parts = parse_url($url);
    if (!$parts || ($parts['scheme'] ?? '') !== 'https' || isset($parts['user']) || isset($parts['pass'])) return null;
    $host = $parts['host'] ?? '';
    if (!in_array($host, ['www.clubee.com', 'clubee.com', 'clubee-websites-prod.s3.eu-central-1.amazonaws.com'], true)) return null;
    return $url;
}
function cardLogo(string $card, string $side): ?string {
    if (!preg_match('~<div\b[^>]*class="[^"]*_team' . $side . '[^"]*"[^>]*>\s*<img\b[^>]*src="([^"]+)"~s', $card, $match)) return null;
    return logoUrl(html_entity_decode($match[1], ENT_QUOTES | ENT_HTML5, 'UTF-8'));
}

function competitionGames(string $source): array {
    $source = competitionSource($source);
    // Cache only successful parsed responses, never empty/error pages.
    $cacheDir = sys_get_temp_dir() . '/apolloon-handbal-live';
    $cacheFile = $cacheDir . '/' . hash('sha256', $source) . '.json';
    $cached = null;
    if (is_file($cacheFile) && (time() - (int)filemtime($cacheFile)) < 86400) {
        $cached = json_decode((string)@file_get_contents($cacheFile), true);
    }
    $serveCached = static function (string $warning) use ($cached): ?array {
        if (is_array($cached) && !empty($cached['games'])) {
            $cached['stale'] = true;
            $cached['warning'] = $warning;
            return $cached;
        }
        return null;
    };
    if (!class_exists('DOMDocument')) {
        throw new RuntimeException('De hosting mist PHP DOM/XML. Vraag de hostingbeheerder die in te schakelen.', 503);
    }
    try {
        $html = fetchClubee($source, true);
    } catch (RuntimeException $e) {
        if ($fallback = $serveCached('Clubee is niet bereikbaar; de laatste succesvolle wedstrijdlijst wordt getoond.')) return $fallback;
        throw $e;
    }
    $games = competitionParseGames($html);
    if (!$games) {
        if ($fallback = $serveCached('Clubee leverde geen herkenbare wedstrijden; de laatste succesvolle wedstrijdlijst wordt getoond.')) return $fallback;
        throw new RuntimeException('Geen herkenbare wedstrijden gevonden. Mogelijk heeft Clubee de HTML-structuur gewijzigd.', 502);
    }
    usort($games, fn(array $a, array $b): int => strcmp($a['date'], $b['date']) ?: strcmp($a['time'] ?? '', $b['time'] ?? ''));
    $result = ['games' => $games, 'checkedAt' => gmdate('Y-m-d\TH:i:s\Z'), 'source' => $source];
    if ((is_dir($cacheDir) || @mkdir($cacheDir, 0700, true)) && is_writable($cacheDir)) {
        @file_put_contents($cacheFile, json_encode($result, JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE), LOCK_EX);
    }
    return $result;
}

function competitionParseGames(string $html): array {
    preg_match_all('~<a\b[^>]*href="([^"<>]*/games/[0-9]+)"[^>]*>(.*?)</a>~s', $html, $cards, PREG_SET_ORDER);
    // Overlay links are empty: select their nearest row/list item, not the link text.
    // Match class suffixes so a changed CSS module hash does not break the parser.
    if (class_exists('DOMDocument')) {
        $dom = new DOMDocument();
        $previous = libxml_use_internal_errors(true);
        $dom->loadHTML('<?xml encoding="UTF-8">' . $html, LIBXML_NONET);
        libxml_clear_errors();
        libxml_use_internal_errors($previous);
        $xpath = new DOMXPath($dom);
        foreach ($xpath->query('//a[contains(@href, "/games/")]') as $link) {
            $href = $link->getAttribute('href');
            if (!preg_match('~/games/[0-9]+$~', $href)) continue;
            $node = $xpath->query('ancestor::*[self::li or contains(concat(" ", normalize-space(@class), " "), "_row ")][1]', $link)->item(0);
            if (!$node) {
                // Keep support for older cards whose links wrap the match content.
                $node = $link;
                for ($depth = 0; $depth < 5 && $node; $depth++, $node = $node->parentNode) {
                    $text = trim(preg_replace('/\s+/u', ' ', $node->textContent ?? ''));
                    if (strlen($text) > 20 && strlen($text) < 1500 && preg_match('~[0-9]{2}[./][0-9]{2}[./][0-9]{4}~', $text)) break;
                }
                if (!$node || $depth === 5) continue;
            }
            $cards[] = [0 => '', 1 => $href, 2 => $dom->saveHTML($node), 3 => $node];
        }
    }
    $games = [];
    $seen = [];
    foreach ($cards as $card) {
        if (isset($seen[$card[1]])) continue;
        $homeLogo = cardLogo($card[2], 'Left');
        $awayLogo = cardLogo($card[2], 'Right');
        $home = isset($card[3]) ? cardField($xpath, $card[3], 'home') : null;
        $away = isset($card[3]) ? cardField($xpath, $card[3], 'away') : null;
        if ($home && $away) {
            $names = [cardText(cardField($xpath, $home, 'name')), cardText(cardField($xpath, $away, 'name'))];
            $date = cardText(cardField($xpath, $card[3], 'date'));
            $timeText = cardText(cardField($xpath, $card[3], 'time'));
            $time = preg_match('/^(?:[01]?[0-9]|2[0-3]):[0-5][0-9]$/D', $timeText) ? $timeText : null;
            // Only read the score element: a kickoff time also contains a colon.
            $scoreText = cardText(cardField($xpath, $card[3], 'score'));
            $score = preg_match('/^([0-9]+)\s*[:\x{2013}\x{2014}-]\s*([0-9]+)$/uD', $scoreText, $scoreMatch)
                ? $scoreMatch[1] . ' - ' . $scoreMatch[2] : null;
            $homeImage = $xpath->query('.//img[@src]', $home)->item(0);
            $awayImage = $xpath->query('.//img[@src]', $away)->item(0);
            $homeLogo = $homeImage ? logoUrl($homeImage->getAttribute('src')) : null;
            $awayLogo = $awayImage ? logoUrl($awayImage->getAttribute('src')) : null;
        } else {
            // Legacy markup remains supported.
            preg_match_all('~<strong\b[^>]*>(.*?)</strong>~s', $card[2], $namesMatch);
            $names = array_map('textValue', $namesMatch[1]);
            preg_match_all('~<(?:p|h3)\b[^>]*>(.*?)</(?:p|h3)>~s', $card[2], $valuesMatch);
            $values = array_map('textValue', $valuesMatch[1]);
            $date = null;
            $score = null;
            $time = null;
            foreach ($values as $value) {
                if (preg_match('~^[0-9]{2}[./][0-9]{2}[./][0-9]{4}$~', $value)) $date = $value;
                if (preg_match('/^([0-9]+)\s*[\x{2013}\x{2014}-]\s*([0-9]+)$/uD', $value, $scoreMatch)) $score = $scoreMatch[1] . ' - ' . $scoreMatch[2];
                if (preg_match('/^(?:[01]?[0-9]|2[0-3]):[0-5][0-9]$/D', $value)) $time = $value;
            }
        }
        if (count($names) !== 2 || $names[0] === '' || $names[1] === '' || !$date
            || !preg_match('~^[0-9]{2}[./][0-9]{2}[./][0-9]{4}$~', $date)) continue;
        [$day, $month, $year] = explode('.', str_replace('/', '.', $date));
        if (!checkdate((int)$month, (int)$day, (int)$year)) continue;
        $games[] = ['id' => $card[1], 'home' => $names[0], 'away' => $names[1],
            'date' => "$year-$month-$day", 'score' => $score, 'time' => $time,
            'homeLogo' => $homeLogo, 'awayLogo' => $awayLogo];
        $seen[$card[1]] = true;
    }
    return $games;
}
