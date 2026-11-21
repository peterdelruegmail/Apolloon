<?php
declare(strict_types=1);
require __DIR__ . '/clubee.php';

function ensure(bool $ok, string $message): void {
    if (!$ok) throw new RuntimeException($message);
}
function chunkHtml(string $text): string {
    return '<script>self.__next_f.push([1,' . json_encode($text) . '])</script>';
}
$block = ['name' => 'Poule [A] "��n"', 'rows' => [
    ['group' => ['id' => 1, 'full_name' => 'Apolloon "Spurs" [A]'],
     'stat1' => 0, 'stat2' => 0, 'stat3' => 0, 'stat4' => 0,
     'stat5' => 0, 'stat6' => 23, 'stat7' => -23, 'stat8' => 0],
]];
$payload = json_encode(['standingsStats' => [$block, $block, ['title' => 'Poule B', 'rows' => []]]]);
$html = chunkHtml(substr($payload, 0, 100)) . chunkHtml(substr($payload, 100));
$groups = rankingGroups($html);
ensure(count($groups) === 2, 'Deduplicatie of meerdere poules fout.');
ensure($groups[0]['name'] === $block['name'], 'Poulenaam of Unicode fout.');
ensure($groups[0]['standings'][0]['team'] === 'Apolloon "Spurs" [A]', 'Teamnaam fout.');
ensure($groups[0]['standings'][0]['pts'] === 0, 'Nulscore verloren.');
ensure($groups[0]['standings'][0]['gd'] === -23, 'Negatief saldo verloren.');
ensure($groups[1]['standings'] === [], 'Lege poule fout.');
$failed = false;
try { rankingGroups('<html>Geen klassement</html>'); } catch (RuntimeException $e) { $failed = true; }
ensure($failed, 'Ontbrekende bron moet een fout opleveren.');
echo "Parsercontroles geslaagd.\n";
if (in_array('--live', $argv, true)) {
    $url = 'https://www.clubee.com/handballbelgium/standings-371073v4/leagues/18702/seasons/220';
    $live = rankingGroups(rankingFetch($url));
    ensure(count($live[0]['standings']) > 0, 'Live klassement is leeg.');
    $teams = array_column($live[0]['standings'], 'team');
    ensure(count(array_filter($teams, fn($name) => stripos((string) $name, 'Apolloon') !== false)) > 0, 'Apolloon niet gevonden.');
    echo 'Actuele Clubee-aanvraag geslaagd: ' . count($live[0]['standings']) . " teams.\n";
}
