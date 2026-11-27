<?php
declare(strict_types=1);
require __DIR__ . '/../../programmas/handbal-live/competition-data.php';
require __DIR__ . '/../../programmas/handbal-live/competition-menu.php';
require __DIR__ . '/../../programmas/handbal-live/server-view.php';
require __DIR__ . '/../../programmas/handbal-live/club-ticker-data.php';
function check(bool $condition, string $message): void {
    if (!$condition) throw new RuntimeException($message);
}
function badRequest(callable $call): void {
    try { $call(); } catch (RuntimeException $error) {
        check($error->getCode() === 400, 'Expected HTTP 400');
        return;
    }
    throw new RuntimeException('Invalid input accepted');
}
$today = new DateTimeImmutable('2026-11-24', new DateTimeZone('Europe/Brussels'));
check(viewPeriod([], $today) === ['2026-11-23', '2026-11-29'], 'Belgian current week');
check(viewPeriod(['from' => '28/12/2026', 'to' => '03/01/2027', 'action' => 'next'], $today)
    === ['2027-01-04', '2027-01-10'], 'Next week across year boundary');
check(viewPeriod(['from' => '2026-03-30', 'to' => '2026-04-05', 'action' => 'prev'], $today)
    === ['2026-03-23', '2026-03-29'], 'Previous week across daylight saving');
check(viewPeriod(['from' => 'bad', 'to' => 'bad', 'action' => 'current'], $today)
    === ['2026-11-23', '2026-11-29'], 'Current week repairs invalid date fields');
badRequest(fn() => viewPeriod(['from' => '31/02/2026'], $today));
badRequest(fn() => viewPeriod(['from' => '2026-11-25', 'to' => '2026-11-24'], $today));
badRequest(fn() => viewPeriod(['from' => '2020-01-01', 'to' => '2026-01-01'], $today));
foreach (['http://clubee.com/handballbelgium/testv4', 'https://evil.example/handballbelgium/testv4',
    'https://clubee.com:443/handballbelgium/testv4', 'https://user@clubee.com/handballbelgium/testv4',
    'https://clubee.com/handballbelgium/../testv4'] as $url) {
    badRequest(fn() => competitionSource($url));
}
check(competitionSource('https://www.clubee.com/handballbelgium/testv4?ignored=1#fragment')
    === 'https://www.clubee.com/handballbelgium/testv4', 'Canonical source');

$fixture = '<ul><li class="x_row"><a href="/handballbelgium/games/123"></a>'
    . '<div class="x_date">24/11/2026</div><div class="x_time">9:30</div>'
    . '<div class="x_score">0 : 0</div><div class="x_home"><span class="x_name">Apolloon &amp; Spurs</span>'
    . '<img src="https://www.clubee.com/logo.png"></div>'
    . '<div class="x_away"><span class="x_name">Other team</span></div></li></ul>';
$parsed = competitionParseGames($fixture);
check(count($parsed) === 1, 'One parsed match, duplicate overlay link ignored');
check($parsed[0]['home'] === 'Apolloon & Spurs' && $parsed[0]['score'] === '0 - 0', 'Decoded team and zero score');
check($parsed[0]['date'] === '2026-11-24' && $parsed[0]['time'] === '9:30', 'Match date/time retained');
check(competitionParseGames(str_replace('24/11/2026', '31/02/2026', $fixture)) === [], 'Invalid upstream date skipped');
check(competitionParseGames('<p>Service unavailable</p>') === [], 'Unknown HTML does not become a match');
$menu = [];
findCompetitionMenu(['name' => 'COMPETITION', 'children' => [['name' => 'Men', 'children' =>
    [['name' => 'Division 1', 'url' => 'testv4', 'page' => ['type' => 'results']]]]]], $menu);
check(count($menu) === 1 && array_values($menu)[0]['group'] === 'Men', 'Menu parsed without global state');

$base = ['id' => '/handballbelgium/games/123', 'home' => 'Other', 'away' => 'Team', 'date' => '2026-11-24',
    'time' => '12:00', 'score' => '0 - 0', 'cancelled' => false];
$games = [$base, array_replace($base, ['id' => '124', 'home' => 'Apolloon', 'date' => '2026-11-25']),
    array_replace($base, ['id' => '125', 'date' => '2026-11-30'])];
check(array_column(viewSelectGames($games, '2026-11-24', '2026-11-25', true), 'id')
    === ['124', '/handballbelgium/games/123'], 'Inclusive filtering and Apolloon first');
check(viewSelectGames($games, '2026-11-24', '2026-11-25', false)[0]['id'] === '/handballbelgium/games/123',
    'Chronological sort when Apolloon first is off');

$unsafe = array_replace($base, ['home' => '<script>alert(1)</script>', 'away' => '" onmouseover="evil',
    'homeLogo' => 'javascript:alert(1)', 'awayLogo' => 'https://evil.example/pixel.png']);
$html = viewMatches([$unsafe]);
check(!str_contains($html, '<script>') && str_contains($html, '&lt;script&gt;'), 'Team names escaped');
check(!str_contains($html, '<img'), 'Unsafe/unapproved logo URLs rejected');
check(str_contains($html, 'score.html?match=123') && str_contains($html, 'wedstrijdblad.html?match=123'), 'Match links preserved');
check(viewMatches([array_replace($base, ['id' => 'javascript:alert(1)'])]) === '', 'Invalid match IDs not rendered');
check(!str_contains(viewTicker([$unsafe]), '<script>'), 'Ticker team names escaped');
check(str_contains(viewTicker([array_replace($base, ['cancelled' => true, 'notUpdated' => true])]),
    'Afgelast (niet bijgewerkt)'), 'Ticker cancellation and warning preserved');
check(viewTicker([]) === 'Geen wedstrijden van Apolloon Spurs in deze periode', 'Empty ticker message');
$options = viewOptions([['source' => 'https://www.clubee.com/handballbelgium/testv4', 'name' => '<img>', 'group' => '"<script>']],
    'https://www.clubee.com/handballbelgium/testv4/leagues/1/seasons/2');
check(str_contains($options, ' selected') && !str_contains($options, '<script>') && !str_contains($options, '<img>'),
    'Selected season and menu escaping');
$clubOptions = viewOptions([], 'apolloon');
check(str_contains($clubOptions, 'value="apolloon" selected'), 'Club option remains available without competition menu');
check(substr_count(viewOptions(array_values($menu), 'apolloon'), ' selected') === 1, 'Only club option selected');
check(str_contains(viewOptions([], 'https://www.clubee.com/handballbelgium/testv4'), 'value="apolloon">'),
    'Club option does not override competition selection');
check(str_contains(viewMatches([array_replace($base, ['cancelled' => true, 'notUpdated' => true])]),
    'Afgelast (niet bijgewerkt)'), 'Club match cards preserve cancellation and failed score checks');
$clubGames = []; $recognised = 0;
foreach ([['id' => '201', 'team1' => ['name' => 'Apolloon U16'], 'team2' => ['name' => 'Other']],
    ['id' => '202', 'team1' => ['name' => 'Other'], 'team2' => ['name' => 'Apolloon Dames']],
    ['id' => '203', 'team1' => ['name' => 'Other'], 'team2' => ['name' => 'Another']]] as $match) {
    tickerCollectGames($match + ['start_date' => '2026-11-24 12:00:00'], $clubGames, $recognised);
}
check(array_column(viewSelectGames(array_values($clubGames), '2026-11-24', '2026-11-24', false), 'id')
    === ['201', '202'], 'Club calendar includes home and away teams across divisions, excludes other clubs');
echo "All server view regression checks passed.\n";
