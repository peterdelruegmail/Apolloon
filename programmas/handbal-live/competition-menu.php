<?php
declare(strict_types=1);
require_once __DIR__ . '/clubee.php';
function collectCompetitions(array $node, array &$competitions, string $group = ''): void {

    if (($node['page']['type'] ?? '') === 'results' && isset($node['name'], $node['url'])
        && preg_match('/^[a-zA-Z0-9_-]+v4$/', $node['url'])) {
        $url = 'https://www.clubee.com/handballbelgium/' . $node['url'];
        $competitions[$url] = ['name' => textValue($node['name']), 'source' => $url, 'group' => $group];
    }
    foreach ($node['children'] ?? [] as $child) {
        if (is_array($child)) collectCompetitions($child, $competitions, $group ?: (string)($child['name'] ?? ''));
    }
}
function findCompetitionMenu(array $value, array &$competitions): void {
    if (($value['name'] ?? '') === 'COMPETITION') {
        foreach ($value['children'] ?? [] as $child) {
            if (is_array($child)) collectCompetitions($child, $competitions, (string)($child['name'] ?? ''));
        }
        return;
    }
    foreach ($value as $child) if (is_array($child)) findCompetitionMenu($child, $competitions);
}
function competitionMenu(): array {
    $html = fetchClubee('https://www.clubee.com/handballbelgium', true);
    $competitions = [];
    foreach (clubeePageValues($html) as $value) {
        findCompetitionMenu($value, $competitions);
    }
    if (!$competitions) throw new RuntimeException('De competities konden niet uit het Clubee-menu worden gelezen. Probeer later opnieuw.', 502);
    return array_values($competitions);
}
