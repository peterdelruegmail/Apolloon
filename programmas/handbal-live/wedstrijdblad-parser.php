<?php
declare(strict_types=1);

function sheetText(DOMNode $node): string {
    return trim(preg_replace('/\s+/u', ' ', $node->textContent) ?? '');
}
function sheetDocument(string $html): DOMXPath {
    $doc = new DOMDocument();
    if (!$doc->loadHTML('<?xml encoding="UTF-8">' . $html, LIBXML_NONET | LIBXML_NOERROR | LIBXML_NOWARNING)) {
        throw new RuntimeException('Clubee-pagina kon niet worden gelezen.');
    }
    return new DOMXPath($doc);
}
function parseSheet(string $game, string $line): array {
    $g = sheetDocument($game);
    $l = sheetDocument($line);
    $title = static fn(DOMXPath $x): string => explode(' - Match', (string)$x->evaluate('string(//title)'))[0];
    $names = explode(' / ', $title($g));
    if (count($names) !== 2 || $title($g) !== $title($l)) throw new RuntimeException('Ploegnamen komen niet overeen.');
    $score = [];
    foreach ($g->query('//h1|//h2|//h3|//h4|//h5|//h6|//p|//span') as $n) {
        if (preg_match('/^(\d+)\s*[-–]\s*(\d+)$/u', sheetText($n), $m)) { $score = [(int)$m[1], (int)$m[2]]; break; }
    }
    if (!$score) throw new RuntimeException('Eindstand niet gevonden.');
    $events = []; $teams = $names;
    $pattern = "~^H([1-9])\s*(\d+)'(\d+)''\s*(.*?)\s+-\s+(.*?)(?:\s*#(\d+)\s*(.*))?$~u";
    $actions = $g->query('//div[contains(@class,"__action")]');
    $read = static function (DOMNode $n) use ($pattern): ?array {
        $s = str_replace(['’','"','″'], ["'","''","''"], sheetText($n));
        return preg_match($pattern, $s, $m) ? $m : null;
    };
    $matches = [];
    foreach ($actions as $n) {
        if (preg_match('/__action(?:\s|$)/', $n->getAttribute('class')) && ($m = $read($n))) $matches[] = $m;
    }
    if (!$matches) {
        $nodes = [];
        foreach ($g->query('//div|//li|//tr|//article') as $n) {
            if (($m = $read($n)) && strlen($m[4]) <= 90 && strlen(sheetText($n)) <= 360) $nodes[] = [$n,$m];
        }
        $parents = [];
        foreach ($nodes as [$n,$m]) for ($p = $n->parentNode; $p instanceof DOMElement; $p = $p->parentNode) $parents[$p->getNodePath()] = true;
        foreach ($nodes as [$n,$m]) if (!isset($parents[$n->getNodePath()])) $matches[] = $m;
    }
    if (!$matches) throw new RuntimeException('Geen wedstrijdverloop gevonden.');
    foreach (array_reverse($matches) as $m) {
        $raw = trim(preg_replace('/Scored by\s*$/i', '', $m[5]));
        $side = null; $staff = ''; $name = $m[7] ?? '';
        foreach ($names as $i => $team) {
            $prefix = preg_quote(trim(preg_replace('/\s+/u', ' ', $team)), '~');
            if (!preg_match('~^(' . $prefix . '(?:\s+\([^)]*\))?)(.*)$~u', $raw, $t)) continue;
            $suffix = trim($t[2]);
            if ($suffix !== '' && !(preg_match('/card|exclusion|kaart|uitsluiting/i', $m[4]) && (preg_match('/^(trainer|coach|staff(?: member)?|team official|staflid)\b/i', $suffix) || substr($t[1], -1) === ')' || preg_match('/^\s/u', $t[2])))) continue;
            $side = $i; $staff = $suffix;
            if (strlen($t[1]) > strlen($teams[$i])) $teams[$i] = $t[1];
            break;
        }
        $events[] = ['period'=>(int)$m[1],'minute'=>(int)$m[2],'second'=>(int)$m[3],'kind'=>$m[4],'side'=>$side,'unassigned'=>$side === null ? $raw : '', 'nr'=>$m[6] ?? '', 'name'=>$name !== '' ? $name : $staff];
    }
    $players = []; $staff = [];
    foreach ($l->query('//table') as $table) {
        $txt = sheetText($table);
        if (strpos($txt, '7MS') === false || strpos($txt, '7MM') === false) continue;
        $rows = [];
        foreach ($l->query('.//tbody/tr', $table) as $row) {
            $cells = [];
            foreach ($l->query('./td', $row) as $cell) $cells[] = sheetText($cell);
            if (count($cells) !== 10 || count(array_filter(array_slice($cells, 2), 'ctype_digit')) !== 8) throw new RuntimeException('De kolommen in Line up zijn gewijzigd.');
            $rows[] = $cells;
        }
        $players[] = $rows;
        $coaches = [];
        for ($p = $table->parentNode; $p instanceof DOMElement && $p->tagName !== 'body'; $p = $p->parentNode) {
            if ($l->query('.//table', $p)->length > 1) break;
            foreach ($l->query('.//p', $p) as $n) if (preg_match('/\([^)]*Coach\)/i', sheetText($n))) $coaches[] = sheetText($n);
            if ($coaches) break;
        }
        $staff[] = $coaches;
    }
    if (count($players) !== 2) throw new RuntimeException('De twee spelerslijsten zijn niet gevonden.');
    $halftime = [null,null];
    foreach ($g->query('//div|//tr|//*[@role="row"]') as $row) {
        $cells = [];
        foreach ($row->childNodes as $cell) if ($cell instanceof DOMElement) $cells[] = sheetText($cell);
        if (count($cells) < 3) continue;
        $numbers = array_slice($cells, 1);
        if (count(array_filter($numbers, 'ctype_digit')) !== count($numbers)) continue;
        foreach ($teams as $i => $team) if (in_array($cells[0], [$team,$names[$i]], true) && array_sum($numbers) === $score[$i]) $halftime[$i] = (int)$cells[1];
    }
    $running = $first = [0,0]; $periods = []; $unassigned = 0;
    foreach ($events as &$e) {
        $i = $e['side']; $periods[$e['period']] = true;
        if ($i === null) ++$unassigned;
        if ($i !== null && in_array($e['kind'], ['Goal','7-meter throw scored'], true)) {
            ++$running[$i];
            if ($e['period'] === 1) ++$first[$i];
        }
        $e['team'] = $i === null ? null : $teams[$i]; $e['score'] = $running;
        unset($e['side']);
    }
    unset($e);
    if ($running === $score && isset($periods[1],$periods[2]) && count($periods) === 2) foreach ($first as $i => $n) if ($halftime[$i] === null) $halftime[$i] = $n;
    $totals = [];
    foreach ($players as $i => &$rows) {
        $goals = array_sum(array_column($rows, 3)); $seven = array_sum(array_column($rows, 4));
        if ($goals !== $score[$i] && $goals + $seven === $score[$i]) foreach ($rows as &$r) $r[3] = (int)$r[3] + (int)$r[4];
        unset($r);
        $totals[] = array_sum(array_column($rows, 3));
    }
    unset($rows);
    return compact('teams','players','staff','events','score','halftime') + ['unassigned' => $unassigned, 'verified' => $unassigned === 0 && $running === $score && $totals === $score && $first === $halftime];
}
