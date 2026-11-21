<?php
declare(strict_types=1);

/** Read a balanced JSON array without treating brackets inside strings as syntax. */
function rankingArrayEnd(string $text, int $start): ?int {
    $depth = 0;
    $quoted = false;
    $escaped = false;
    $length = strlen($text);
    for ($i = $start; $i < $length; $i++) {
        $c = $text[$i];
        if ($quoted) {
            if ($escaped) $escaped = false;
            elseif ($c === '\\') $escaped = true;
            elseif ($c === '"') $quoted = false;
        } elseif ($c === '"') $quoted = true;
        elseif ($c === '[') $depth++;
        elseif ($c === ']' && --$depth === 0) return $i + 1;
    }
    return null;
}

function rankingGroups(string $html): array {
    preg_match_all('~self\.__next_f\.push\(\[1,\s*("(?:[^"\\\\]|\\\\.)*")\]\)~s', $html, $matches);
    $chunks = [];
    foreach ($matches[1] as $encoded) {
        $chunk = json_decode($encoded, true);
        if (is_string($chunk)) $chunks[] = $chunk;
    }
    if (!$chunks) throw new RuntimeException('Geen herkenbare Clubee-paginagegevens gevonden.');

    $groups = [];
    $seen = [];
    // RSC payloads can continue across adjacent transport chunks.
    $text = implode('', $chunks);
    preg_match_all('/"standingsStats"\s*:\s*\[/', $text, $positions, PREG_OFFSET_CAPTURE);
    foreach ($positions[0] as [$marker, $offset]) {
        $start = $offset + strlen($marker) - 1;
        $end = rankingArrayEnd($text, $start);
        if ($end === null) continue;
        $blocks = json_decode(substr($text, $start, $end - $start), true);
        if (!is_array($blocks)) continue;
        foreach ($blocks as $block) {
            if (!is_array($block)) continue;
            $key = json_encode($block);
            if (isset($seen[$key])) continue;
            $seen[$key] = true;
            $name = 'Groep ' . (count($groups) + 1);
            foreach (['name', 'title', 'label', 'phase', 'phaseName', 'groupName', 'poule'] as $field) {
                if (isset($block[$field]) && is_string($block[$field]) && trim($block[$field]) !== '') {
                    $name = trim($block[$field]);
                    break;
                }
            }
            $rows = [];
            foreach (($block['rows'] ?? []) as $row) {
                if (!is_array($row)) continue;
                $team = is_array($row['group'] ?? null) ? $row['group'] : [];
                $entry = [
                    'position' => count($rows) + 1,
                    'team' => $team['full_name'] ?? $team['name'] ?? '',
                    'team_id' => $team['id'] ?? null,
                    'logo' => $team['pic'] ?? null,
                ];
                foreach (['mp', 'w', 'd', 'l', 'gs', 'ga', 'gd', 'pts'] as $i => $stat) {
                    $entry[$stat] = $row['stat' . ($i + 1)] ?? null;
                }
                $rows[] = $entry;
            }
            $groups[] = ['name' => $name, 'standings' => $rows];
        }
    }
    if (!$groups) throw new RuntimeException('Geen klassement gevonden. Controleer competitie en seizoen.');
    return $groups;
}

function rankingFetch(string $url): string {
    if (!function_exists('curl_init')) throw new RuntimeException('PHP cURL ontbreekt op deze hosting.');
    $curl = curl_init($url);
    $body = '';
    curl_setopt_array($curl, [
        CURLOPT_FOLLOWLOCATION => false,
        CURLOPT_CONNECTTIMEOUT => 8,
        CURLOPT_TIMEOUT => 20,
        CURLOPT_SSL_VERIFYPEER => true,
        CURLOPT_SSL_VERIFYHOST => 2,
        CURLOPT_USERAGENT => 'Mozilla/5.0 (compatible; ApolloonRanking/1.0)',
        CURLOPT_HTTPHEADER => ['Accept: text/html', 'Cache-Control: no-cache', 'Pragma: no-cache'],
        CURLOPT_WRITEFUNCTION => static function ($handle, string $chunk) use (&$body): int {
            if (strlen($body) + strlen($chunk) > 8000000) return 0;
            $body .= $chunk;
            return strlen($chunk);
        },
    ]);
    $ok = curl_exec($curl);
    $status = (int) curl_getinfo($curl, CURLINFO_HTTP_CODE);
    curl_close($curl);
    if ($ok === false || $status !== 200) {
        throw new RuntimeException('Clubee is momenteel niet bereikbaar' . ($status ? ' (HTTP ' . $status . ')' : '') . '. Probeer opnieuw.');
    }
    return $body;
}
