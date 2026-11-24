<?php
declare(strict_types=1);
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');
require_once __DIR__ . '/competition-menu.php';
if (($_SERVER['REQUEST_METHOD'] ?? 'GET') !== 'GET') respond(['error' => 'Deze actie wordt niet ondersteund.'], 405);
try {
    respond(['competitions' => competitionMenu(), 'checkedAt' => gmdate('Y-m-d\TH:i:s\Z')]);
} catch (RuntimeException $error) {
    respond(['error' => $error->getMessage()], in_array($error->getCode(), [502, 503], true) ? $error->getCode() : 502);
}
