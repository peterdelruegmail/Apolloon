<?php
declare(strict_types=1);

/** All dynamic markup is escaped here before it is sent to the browser. */
function viewEscape(?string $value): string {
    return htmlspecialchars($value ?? '', ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}
function viewDate(string $value): ?DateTimeImmutable {
    if (!preg_match('/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/D', $value)) return null;
    $date = DateTimeImmutable::createFromFormat('!Y-m-d', $value, new DateTimeZone('Europe/Brussels'));
    return $date && $date->format('Y-m-d') === $value ? $date : null;
}
function viewDisplayDate(string $value): string {
    return substr($value, 8, 2) . '/' . substr($value, 5, 2) . '/' . substr($value, 0, 4);
}
function viewInputDate(string $value): string {
    if (preg_match('~^(\d{2})/(\d{2})/(\d{4})$~D', $value, $m)) return "$m[3]-$m[2]-$m[1]";
    return $value;
}
function viewOptions(array $competitions, string $source): string {
    $groups = [];
    foreach ($competitions as $competition) {
        $groups[$competition['group'] ?: 'Competities'][] = $competition;
    }
    $html = '<option value="apolloon"' . ($source === 'apolloon' ? ' selected' : '')
        . '>Alle matchen van Apolloon</option>';
    foreach ($groups as $group => $items) {
        $html .= '<optgroup label="' . viewEscape($group) . '">';
        foreach ($items as $item) {
            $selected = $source === $item['source'] || str_starts_with($source, $item['source'] . '/');
            $html .= '<option value="' . viewEscape($selected ? $source : $item['source']) . '"'
                . ($selected ? ' selected' : '') . '>' . viewEscape($item['name']) . '</option>';
        }
        $html .= '</optgroup>';
    }
    return $html;
}
function viewTeam(array $game, string $side): string {
    $html = '<div class="match-team">';
    $logo = $game[$side . 'Logo'] ?? '';
    $parts = is_string($logo) ? parse_url($logo) : false;
    if ($parts && ($parts['scheme'] ?? '') === 'https' && !isset($parts['user']) && !isset($parts['pass'])
        && in_array($parts['host'] ?? '', ['www.clubee.com', 'clubee.com',
            'clubee-websites-prod.s3.eu-central-1.amazonaws.com', 'd28kyj1r8oju1l.cloudfront.net'], true)) {
        $html .= '<img loading="lazy" src="' . viewEscape($logo) . '" alt="'
            . viewEscape('Logo ' . $game[$side]) . '">';
    }
    return $html . '<div>' . viewEscape($game[$side]) . '</div></div>';
}
function viewMatches(array $games): string {
    $html = '';
    foreach ($games as $game) {
        $id = basename($game['id']);
        if (!preg_match('/^[1-9][0-9]{0,11}$/D', $id)) continue;
        $score = !empty($game['cancelled']) ? 'Afgelast' : ($game['score'] ?: '-');
        if (!empty($game['notUpdated'])) $score .= ' (niet bijgewerkt)';
        $html .= '<article class="match-card"><div class="match-date">'
            . viewEscape(viewDisplayDate($game['date']) . (!empty($game['time']) ? ' om ' . $game['time'] : ''))
            . '</div><div class="match-teams">' . viewTeam($game, 'home')
            . '<div class="match-score">' . viewEscape($score) . '</div>'
            . viewTeam($game, 'away') . '</div><div class="match-links">';
        foreach (['score.html?match=' => 'Open scorepagina', 'wedstrijdblad.html?match=' => 'Open wedstrijdblad',
            'https://www.clubee.com/handballbelgium/games/' => 'Open op Clubee'] as $url => $label) {
            $html .= '<a target="_blank" rel="noopener" href="' . $url . $id . '">' . $label . '</a>';
        }
        $html .= '</div></article>';
    }
    return $html;
}
function viewTicker(array $games): string {
    if (!$games) return 'Geen wedstrijden van Apolloon Spurs in deze periode';
    $html = '';
    foreach ($games as $game) {
        $score = $game['cancelled'] ? 'Afgelast' : ($game['score'] ?: '-');
        if (!empty($game['notUpdated'])) $score .= ' (niet bijgewerkt)';
        $html .= '<span class="match"><time datetime="' . viewEscape($game['date']) . '">'
            . viewEscape(substr($game['date'], 8, 2) . '/' . substr($game['date'], 5, 2) . ' ' . ($game['time'] ?? ''))
            . '</time><span>' . viewEscape($game['home']) . '</span><strong class="score">'
            . viewEscape($score) . '</strong><span>' . viewEscape($game['away']) . '</span></span>';
    }
    return $html;
}

/** Calendar navigation uses Belgian dates, independent of the visitor's timezone. */
function viewPeriod(array $query, DateTimeImmutable $today): array {
    $monday = $today->setTime(0, 0)->modify('-' . ((int)$today->format('N') - 1) . ' days');
    $from = viewInputDate($query['from'] ?? $monday->format('Y-m-d'));
    $to = viewInputDate($query['to'] ?? $monday->modify('+6 days')->format('Y-m-d'));
    $action = $query['action'] ?? '';
    if ($action === 'current') {
        $from = $monday->format('Y-m-d');
        $to = $monday->modify('+6 days')->format('Y-m-d');
    }
    $first = viewDate($from);
    $last = viewDate($to);
    if (!$first || !$last || $first > $last || (int)$first->diff($last)->format('%a') > 366) {
        throw new RuntimeException('Kies geldige datums en een oplopende periode van maximaal een jaar.', 400);
    }
    if (in_array($action, ['prev', 'next'], true)) {
        $shift = $action === 'prev' ? '-7 days' : '+7 days';
        $from = $first->modify($shift)->format('Y-m-d');
        $to = $last->modify($shift)->format('Y-m-d');
    }
    return [$from, $to];
}
function viewSelectGames(array $games, string $from, string $to, bool $apolloon): array {
    $games = array_values(array_filter($games, fn($game) => $game['date'] >= $from && $game['date'] <= $to));
    $isApolloon = static fn($game): int => preg_match('/apolloon/i', $game['home'] . ' ' . $game['away']);
    usort($games, fn($a, $b) => ($apolloon ? $isApolloon($b) - $isApolloon($a) : 0)
        ?: strcmp($a['date'], $b['date']) ?: strcmp($a['time'] ?? '', $b['time'] ?? ''));
    return $games;
}
