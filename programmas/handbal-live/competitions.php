<?php
declare(strict_types=1);
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');
require __DIR__ . '/clubee.php';
if (($_SERVER['REQUEST_METHOD'] ?? 'GET') !== 'GET') respond(['error' => 'Deze actie wordt niet ondersteund.'], 405);
$html = fetchClubee('https://www.clubee.com/handballbelgium');
$competitions = [];
function collectCompetitions(array $node, string $group = ''): void {
    global $competitions;
    if (($node['page']['type'] ?? '') === 'results' && isset($node['name'], $node['url'])
        && preg_match('/^[a-zA-Z0-9_-]+v4$/', $node['url'])) {
        $url = 'https://www.clubee.com/handballbelgium/' . $node['url'];
        $competitions[$url] = ['name' => textValue($node['name']), 'source' => $url, 'group' => $group];
    }
    foreach ($node['children'] ?? [] as $child) {
        if (is_array($child)) collectCompetitions($child, $group ?: (string)($child['name'] ?? ''));
    }
}
function findCompetitionMenu(array $value): void {
    if (($value['name'] ?? '') === 'COMPETITION') {
        foreach ($value['children'] ?? [] as $child) {
            if (is_array($child)) collectCompetitions($child, (string)($child['name'] ?? ''));
        }
        return;
    }
    foreach ($value as $child) if (is_array($child)) findCompetitionMenu($child);
}
foreach (clubeePageValues($html) as $value) {
    findCompetitionMenu($value);
}
if (!$competitions) respond(['error' => 'De competities konden niet uit het Clubee-menu worden gelezen. Probeer later opnieuw.'], 502);
respond(['competitions' => array_values($competitions), 'checkedAt' => gmdate('Y-m-d\TH:i:s\Z')]);
