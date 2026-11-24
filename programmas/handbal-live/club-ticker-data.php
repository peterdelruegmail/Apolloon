<?php
declare(strict_types=1);
require_once __DIR__ . '/clubee.php';

/** Read only the public competition menu, never URLs supplied by visitors. */
function tickerSources(array $node, array &$sources, bool $inside = false): void {
    $inside = $inside || ($node['name'] ?? '') === 'COMPETITION';
    if ($inside && ($node['page']['type'] ?? '') === 'results'
        && is_string($node['url'] ?? null) && preg_match('/^[a-zA-Z0-9_-]+v4$/D', $node['url'])) {
        $sources['https://www.clubee.com/handballbelgium/' . $node['url']] = true;
    }
    foreach ($node as $child) if (is_array($child)) tickerSources($child, $sources, $inside);
}

/** All phases are present in the public Next.js payload, including youth groups. */
function tickerCollectGames(array $node, array &$games, int &$recognised): void {
    if (is_array($node['team1'] ?? null) && is_array($node['team2'] ?? null)
        && preg_match('/^[1-9][0-9]{0,11}$/D', (string)($node['id'] ?? ''))
        && is_string($node['start_date'] ?? null)) {
        $date = substr($node['start_date'], 0, 10);
        if (!tickerDate($date)) return;
        $recognised++;
        $home = $node['team1']['full_name'] ?? $node['team1']['name'] ?? '';
        $away = $node['team2']['full_name'] ?? $node['team2']['name'] ?? '';
        if (!is_string($home) || !is_string($away) || $home === '' || $away === '') return;
        if (!preg_match('/\bapolloon\b/iu', $home . ' ' . $away)) return;
        $id = (string)$node['id'];
        $games[$id] = ['id' => $id, 'home' => $home, 'away' => $away,
            'date' => $date, 'time' => !empty($node['time_unknown']) ? '' : substr($node['start_date'], 11, 5),
            'score' => scoreValue($node), 'cancelled' => !empty($node['cancelled'])];
        return;
    }
    foreach ($node as $child) if (is_array($child)) tickerCollectGames($child, $games, $recognised);
}

function tickerDate(string $value): ?DateTimeImmutable {
    $date = DateTimeImmutable::createFromFormat('!Y-m-d', $value, new DateTimeZone('Europe/Brussels'));
    return $date && $date->format('Y-m-d') === $value ? $date : null;
}

/** Bounded concurrency prevents one connection per division at the same time. */
function tickerFetchPages(array $urls, bool $api = false): array {
    if (!function_exists('curl_multi_init')) throw new RuntimeException('De hosting mist PHP cURL.', 503);
    $results = [];
    foreach (array_chunk($urls, 6, true) as $batch) {
        $multi = curl_multi_init();
        $handles = [];
        try {
            foreach ($batch as $key => $url) {
                $handle = curl_init($url);
                curl_setopt_array($handle, [CURLOPT_RETURNTRANSFER => true, CURLOPT_FOLLOWLOCATION => false,
                    CURLOPT_CONNECTTIMEOUT => 5, CURLOPT_TIMEOUT => 12,
                    CURLOPT_SSL_VERIFYPEER => true, CURLOPT_SSL_VERIFYHOST => 2,
                    CURLOPT_HTTPHEADER => $api
                        ? ['Accept: application/json', 'X-Website: handballbelgium', 'Cache-Control: no-cache']
                        : ['Accept: text/html', 'Cache-Control: no-cache']]);
                $handles[$key] = $handle;
                curl_multi_add_handle($multi, $handle);
            }
            do {
                $code = curl_multi_exec($multi, $running);
                if ($code !== CURLM_OK) throw new RuntimeException('Clubee ophalen is mislukt.', 502);
                if ($running) curl_multi_select($multi, 0.2);
            } while ($running);
            foreach ($handles as $key => $handle) {
                $body = curl_multi_getcontent($handle);
                $results[$key] = curl_errno($handle) === 0 && (int)curl_getinfo($handle, CURLINFO_HTTP_CODE) === 200
                    && is_string($body) ? $body : null;
            }
        } finally {
            foreach ($handles as $handle) { curl_multi_remove_handle($multi, $handle); curl_close($handle); }
            curl_multi_close($multi);
        }
    }
    return $results;
}

function tickerReadCache(string $path): ?array {
    $file = @fopen($path, 'rb');
    if (!$file) return null;
    try {
        if (!flock($file, LOCK_SH)) return null;
        $cache = json_decode((string)stream_get_contents($file), true);
        flock($file, LOCK_UN);
        return is_array($cache) && isset($cache['fetchedAt'], $cache['checkedAt'])
            && is_array($cache['games'] ?? null) ? $cache : null;
    } finally { fclose($file); }
}

function tickerCalendar(): array {
    $directory = sys_get_temp_dir() . '/apolloon-club-ticker';
    if (!is_dir($directory) && !@mkdir($directory, 0700, true) && !is_dir($directory)) {
        throw new RuntimeException('De hosting kan de tickercache niet aanmaken.', 503);
    }
    $path = $directory . '/calendar-v1.json';
    $cache = tickerReadCache($path);
    if ($cache && time() - $cache['fetchedAt'] < 300) return $cache;
    $lock = @fopen($directory . '/calendar.lock', 'c');
    if (!$lock) throw new RuntimeException('De hosting kan de tickercache niet openen.', 503);
    try {
        if (!flock($lock, LOCK_EX | LOCK_NB)) {
            if ($cache && time() - $cache['fetchedAt'] < 86400) {
                $cache['warning'] = 'Clubkalender wordt vernieuwd; de vorige wedstrijdlijst wordt getoond.';
                return $cache;
            }
            throw new RuntimeException('Clubkalender wordt geladen. De ticker probeert het automatisch opnieuw.', 503);
        }
        // Another request may have completed between the first cache read and the lock.
        $latest = tickerReadCache($path);
        if ($latest && time() - $latest['fetchedAt'] < 300) return $latest;
        try {
            $sources = [];
            foreach (clubeePageValues(fetchClubee('https://www.clubee.com/handballbelgium', true)) as $node) {
                tickerSources($node, $sources);
            }
            if (!$sources) throw new RuntimeException('De competitielijst kon niet worden gelezen.', 502);
            $games = [];
            foreach (tickerFetchPages(array_keys($sources)) as $body) {
                if ($body === null) throw new RuntimeException('Niet alle Clubee-reeksen konden worden opgehaald.', 502);
                $recognised = 0;
                foreach (clubeePageValues($body) as $node) tickerCollectGames($node, $games, $recognised);
                if (!$recognised) throw new RuntimeException('Een Clubee-reeks bevat geen herkenbare wedstrijden; de clubkalender is niet volledig gecontroleerd.', 502);
            }
            $games = array_values($games);
            usort($games, fn($a, $b) => strcmp($a['date'] . $a['time'] . $a['id'], $b['date'] . $b['time'] . $b['id']));
            $result = ['games' => $games, 'fetchedAt' => time(), 'checkedAt' => gmdate('Y-m-d\TH:i:s\Z')];
            if (@file_put_contents($path, json_encode($result, JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE), LOCK_EX) === false) {
                throw new RuntimeException('De hosting kan de tickercache niet opslaan.', 503);
            }
            return $result;
        } catch (RuntimeException $error) {
            if (!$cache || time() - $cache['fetchedAt'] >= 86400) throw $error;
            $cache['warning'] = $error->getMessage() . ' De laatste volledige wedstrijdlijst wordt getoond.';
            return $cache;
        }
    } finally { flock($lock, LOCK_UN); fclose($lock); }
}
