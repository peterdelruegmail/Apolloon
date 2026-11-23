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
function clubeeFetchError(string $message, int $status, bool $throwOnError): void {
    if ($throwOnError) throw new RuntimeException($message, $status);
    respond(['error' => $message], $status);
}
function fetchClubee(string $source, bool $throwOnError = false): string {
    if (!function_exists('curl_init')) {
        clubeeFetchError('De hosting mist de PHP cURL-uitbreiding. Vraag de hostingbeheerder die in te schakelen.', 503, $throwOnError);
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
        clubeeFetchError('Clubee kon niet worden opgehaald' . ($status ? ' (HTTP ' . $status . ')' : '') . '. Controleer of de hosting uitgaande HTTPS-verbindingen toestaat.', 502, $throwOnError);
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
    if (!$valid($a) || !$valid($b)) return null;
    return (string)$a . ' - ' . (string)$b;
}

/** Find a complete transport array, including brackets and escapes inside strings. */
function clubeeArrayEnd(string $text, int $start): ?int {
    $depth = 0;
    $quoted = false;
    $escaped = false;
    for ($i = $start, $length = strlen($text); $i < $length; $i++) {
        $char = $text[$i];
        if ($quoted) {
            if ($escaped) $escaped = false;
            elseif ($char === '\\') $escaped = true;
            elseif ($char === '"') $quoted = false;
        } elseif ($char === '"') $quoted = true;
        elseif ($char === '[') $depth++;
        elseif ($char === ']' && --$depth === 0) return $i + 1;
    }
    return null;
}
/** RSC records can span multiple Next.js transport chunks. */
function clubeePageValues(string $html): iterable {
    $chunks = [];
    $offset = 0;
    while (($marker = strpos($html, 'self.__next_f.push(', $offset)) !== false) {
        $start = strpos($html, '[', $marker);
        if ($start === false) break;
        $end = clubeeArrayEnd($html, $start);
        if ($end === null) break;
        $offset = $end;
        $payload = json_decode(substr($html, $start, $end - $start), true);
        if (is_array($payload) && ($payload[0] ?? null) === 1 && is_string($payload[1] ?? null)) {
            $chunks[] = $payload[1];
        }
    }
    foreach (explode("\n", implode('', $chunks)) as $line) {
        $position = strpos($line, ':');
        if ($position === false) continue;
        $value = json_decode(substr($line, $position + 1), true);
        if (is_array($value)) yield $value;
    }
}
/** Limit diagnostic text without requiring the mbstring extension. */
function clubeeExcerpt(string $text, int $length): string {
    return preg_match('/^.{0,' . $length . '}/us', $text, $match) === 1 ? $match[0] : '';
}
