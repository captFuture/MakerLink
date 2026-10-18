<?php
/**
 * machineswitch.php
 *
 * Dedizierter Endpoint für MARS ESPHome Nodes.
 * Kombiniert alle nötigen Checks (User, Guthaben, Schulung) und die
 * maschinenspezifische Abrechnung in EINEM HTTP-Call statt vier.
 *
 * Die gesamte Abrechnungslogik (endLaserTime, endMachineTime3D, endKiln, etc.)
 * ist 1:1 aus query.php übernommen.
 *
 * ============================================================
 * AUFRUF START:
 *   GET machineswitch.php?action=start
 *                        &rfid=0xf4%200x96%200xd2%200x28
 *                        &unitid=1720
 *                        &type=laser        (machine|laser|3dprint|dtf|kiln)
 *                        &min_balance=5.0   (optional, default 5.0)
 *   unitid=6 is the coffee machine: start debits 0.50 EUR immediately;
 *   it does not require training or a follow-up stop call.
 *
 * TUER AUSSEN (Unit-ID 1):
 *   GET machineswitch.php?action=doorLockCheck&rfid=<uid>
 *   Auswertung: Antwort-Array [0] == "True" bedeutet Zutritt.
 *   Nach der Relaisaktion 2 Sekunden warten und danach protokollieren:
 *   GET machineswitch.php?action=logDoorAccess&rfid=<uid>&status=TRUE&unitid=1&check=2
 *   Bei Ablehnung status=FALSE verwenden.
 *
 * ANTWORT START OK:
 *   {"ok":true, "key":23212, "name":"Max", "msg":"Aktiviert"}
 *
 * ANTWORT START FAIL:
 *   {"ok":false, "key":null, "name":null, "msg":"Keine Schulung fuer diese Maschine"}
 *
 * ============================================================
 * AUFRUF STOP:
 *   GET machineswitch.php?action=stop
 *                        &key=23212
 *                        &unitid=1720
 *                        &type=laser
 *                        &end=1760000000  (optional, Unix-Zeit; MakerLink sendet das
 *                                          bei nachgeholten Stops nach Serverausfall)
 *
 *   Idempotent: Ein erneuter Stop derselben Session rechnet nicht doppelt ab
 *   ({"ok":true, "msg":"Bereits gestoppt", "already_stopped":true}).
 *   War die Session geschlossen, aber noch nicht bezahlt (Abbruch zwischen
 *   UPDATE und Buchung), wird die Abrechnung nachgeholt.
 *
 * ANTWORT STOP OK:
 *   {"ok":true, "key":null, "name":null, "msg":"Gestoppt", "cost":-2.50, "balance":12.30}
 *
 * ANTWORT STOP FAIL:
 *   {"ok":false, "key":null, "name":null, "msg":"Key nicht gefunden"}
 *
 * ============================================================
 * HTTP Status Codes:
 *   200 = verarbeitet (auch ok:false bei Zugangsverweigung)
 *   400 = fehlende/ungültige Parameter
 *   500 = Datenbankfehler
 */

error_reporting(E_ALL);
header('Content-Type: application/json; charset=utf-8');

// ============================================================
// DB-Verbindung – gleich wie query.php
// ============================================================
// ---- Auth ----------------------------------------------------------------
// X-MARS-Key Header (von ESPHome Nodes)
// Den Key hier eintragen ODER aus config.inc.php laden wenn du ihn dort zentral verwaltest.
// Beispiel config.inc.php: $config_mars_api_key = 'dein-geheimer-key';

require_once(__DIR__ . '/../config.inc.php');

$valid_api_key = $config_mars_api_key ?? 'CHANGEME';

$request_key = $_SERVER['HTTP_X_MARS_KEY'] ?? '';
if (empty($request_key) || $request_key !== $valid_api_key) {
    http_response_code(401);
    exit(json_encode(['ok' => false, 'msg' => 'Unauthorized']));
}

// ---- DB ------------------------------------------------------------------
$con = mysqli_connect($config_db_host, $config_db_user, $config_db_password, $config_db_db);
mysqli_set_charset($con, 'utf8');
if (mysqli_connect_errno()) {
    http_response_code(500);
    exit(json_encode(['ok' => false, 'msg' => 'DB connection failed: ' . mysqli_connect_error()]));
}

// ============================================================
// Hilfsfunktionen
// ============================================================

function ti($data) {
    // testInput aus query.php
    $data = trim($data ?? '');
    $data = stripslashes($data ?? '');
    $data = htmlspecialchars($data ?? '');
    return $data;
}

function json_out(bool $ok, $key, $name, string $msg, array $extra = []): void {
    $resp = array_merge(['ok' => $ok, 'key' => $key, 'name' => $name, 'msg' => $msg], $extra);
    exit(json_encode($resp));
}

function writeLOG($logtext) {
    // 1:1 aus query.php
    $filename = __DIR__ . '/errorlog.txt';
    $somecontent = $logtext . "\n";
    if (is_writable($filename)) {
        if ($fp = fopen($filename, "a")) {
            fwrite($fp, $somecontent);
            fclose($fp);
        }
    }
}

/**
 * Ermittelt den PlanVomUser (1=Basic, 2=Standard, 4=Unlimited)
 * aus der membership-Tabelle. Logik 1:1 aus query.php.
 */
function getPlanVomUser($con, int $memberID): int {
    $userPlan = [0 => 0, 1 => 0, 2 => 0];

    $query = "SELECT * FROM membership WHERE end IS NULL AND cid = " . $memberID;
    $result = mysqli_query($con, $query);
    if (!empty($error = mysqli_error($con))) {
        writeLOG(date('Y-m-d H:i:s') . ": getPlanVomUser: " . $error);
    }

    while ($row = mysqli_fetch_assoc($result)) {
        $planID = $row["pid"];
        $query2 = "SELECT * FROM plan WHERE pid = " . $planID;
        $result2 = mysqli_query($con, $query2);
        $row2 = mysqli_fetch_assoc($result2);
        $pid = (int)$row2["pid"];

        if ($pid == 2)
            $userPlan[0] = 1;
        elseif ($pid == 3 || $pid == 17 || $pid == 22)
            $userPlan[1] = 1;
        elseif (in_array($pid, [12, 13, 14, 15, 16, 19, 20, 50, 51, 52]))
            $userPlan[2] = 1;
    }

    if (isset($userPlan[2]) && $userPlan[2] == 1) return 4; // Unlimited
    if (isset($userPlan[1]) && $userPlan[1] == 1) return 2; // Standard
    if (isset($userPlan[0]) && $userPlan[0] == 1) return 1; // Basic
    return 1; // Fallback
}

/**
 * Aktuelles Guthaben aus member_payload holen.
 */
function getCurrentPayload($con, int $memberID): array {
    $query = "SELECT * FROM member_payload WHERE cid = " . $memberID . " ORDER BY mytimestamp DESC LIMIT 1";
    $result = mysqli_query($con, $query);
    if (!empty($error = mysqli_error($con))) {
        writeLOG(date('Y-m-d H:i:s') . ": getCurrentPayload: " . $error);
    }
    $row = mysqli_fetch_assoc($result);
    return $row ?: ['payload' => 0, 'fname' => '', 'lname' => ''];
}

/**
 * Guthaben-Buchung schreiben.
 */
function writePayload($con, int $memberID, string $fname, string $lname, float $newPayload, int $unitid, float $amount): bool {
    $mytimestamp = date('Y-m-d H:i:s');
    $fname = mysqli_real_escape_string($con, $fname);
    $lname = mysqli_real_escape_string($con, $lname);
    $query = "INSERT INTO member_payload VALUES ('$mytimestamp', $memberID, '$fname', '$lname', $newPayload, $unitid, $amount)";
    if (!mysqli_query($con, $query)) {
        writeLOG(date('Y-m-d H:i:s') . ": writePayload: " . mysqli_error($con));
        return false;
    }
    return true;
}

function doorLockCheck($con, string $rfid): array {
    $escapedRfid = mysqli_real_escape_string($con, $rfid);
    $query = "SELECT c.cid, c.blocked, c.deleted, p.name
              FROM `key` k
              LEFT JOIN contact c ON k.cid = c.cid
              LEFT JOIN membership m ON m.cid = c.cid
              LEFT JOIN plan p ON p.pid = m.pid
              WHERE k.serial = '$escapedRfid'
                AND (k.end IS NULL OR k.end > CURDATE())
                AND m.end IS NULL";
    $result = mysqli_query($con, $query);
    if (!$result) {
        writeLOG(date('Y-m-d H:i:s') . ': doorLockCheck: ' . mysqli_error($con));
        http_response_code(500);
        json_out(false, null, null, 'DB Fehler bei der Zutrittspruefung');
    }

    $plans = [];
    $accessBlocked = false;
    while ($row = mysqli_fetch_assoc($result)) {
        $plans[] = (string)$row['name'];
        $accessBlocked = $accessBlocked
            || (int)$row['blocked'] !== 0
            || (int)$row['deleted'] !== 0;
    }
    if (!$plans) {
        return ['False', 'KEY ' . $rfid . ' not in DB or enddate set'];
    }
    if ($accessBlocked) {
        return ['False', 'Mitglied ist blockiert oder geloescht'];
    }

    $today = date('D');
    $hour = (int)date('H');
    $dayStart = null;
    $dayEnd = null;
    $hasToday = false;

    foreach ($plans as $planName) {
        if (substr($planName, 0, 3) === 'Unl') {
            return ['True', 'Super User', $planName];
        }

        if (substr($planName, 0, 3) !== $today) {
            continue;
        }

        $startText = substr($planName, 4, 2);
        $endText = substr($planName, 6, 2);
        if (!ctype_digit($startText) || !ctype_digit($endText)) {
            continue;
        }

        $start = (int)$startText;
        $end = (int)$endText;
        $dayStart = $dayStart === null ? $start : min($dayStart, $start);
        $dayEnd = $dayEnd === null ? $end : max($dayEnd, $end);
        $hasToday = true;
    }

    if (!$hasToday) {
        return ['False', 'Wrong Day', implode('-', $plans)];
    }
    if ($hour < $dayStart || $hour >= $dayEnd) {
        return ['False', 'Wrong Time', implode('-', $plans)];
    }

    return ['True', 'Limited User', implode('-', $plans)];
}

function logDoorAccess($con, string $rfid, string $status, int $unitid): void {
    $escapedRfid = mysqli_real_escape_string($con, $rfid);
    $query = "SELECT c.cid
              FROM `key` k
              LEFT JOIN contact c ON k.cid = c.cid
              LEFT JOIN membership m ON m.cid = c.cid
              WHERE k.serial = '$escapedRfid' AND m.end IS NULL
              LIMIT 1";
    $result = mysqli_query($con, $query);
    if (!$result) {
        writeLOG(date('Y-m-d H:i:s') . ': logDoorAccess member lookup: ' . mysqli_error($con));
        http_response_code(500);
        json_out(false, null, null, 'DB Fehler bei der Mitgliederermittlung');
    }

    $row = mysqli_fetch_assoc($result);
    $memberID = $row ? (int)$row['cid'] : 0;
    $statusValue = $status === 'TRUE' ? 1 : 0;
    $timestamp = date('Y-m-d H:i:s');
    $query = "INSERT INTO access_log VALUES (
                '$timestamp', $memberID, '$escapedRfid', $statusValue, $unitid, 2
              )";
    if (!mysqli_query($con, $query)) {
        writeLOG(date('Y-m-d H:i:s') . ': logDoorAccess insert: ' . mysqli_error($con));
        http_response_code(500);
        json_out(false, null, null, 'DB Fehler beim Protokollieren des Zutritts');
    }
}

// ============================================================
// Parameter einlesen & validieren
// ============================================================

$action  = ti($_GET['action']  ?? '');
$rfid    = ti($_GET['rfid']    ?? '');
$unitid  = intval($_GET['unitid']  ?? 0);
$key     = intval($_GET['key']     ?? 0);
$type    = ti($_GET['type']    ?? 'machine'); // machine|laser|3dprint|dtf|kiln
$min_bal = floatval($_GET['min_balance'] ?? 5.0);

if ($action === 'doorLockCheck') {
    if ($rfid === '') {
        http_response_code(400);
        json_out(false, null, null, 'Parameter rfid fehlt');
    }

    exit(json_encode(doorLockCheck($con, $rfid)));
}

if ($action === 'logDoorAccess') {
    $status = strtoupper(ti($_GET['status'] ?? ''));
    $check = intval($_GET['check'] ?? 0);
    if ($rfid === '') {
        http_response_code(400);
        json_out(false, null, null, 'Parameter rfid fehlt');
    }
    if ($unitid <= 0 || $check !== 2 || !in_array($status, ['TRUE', 'FALSE'], true)) {
        http_response_code(400);
        json_out(false, null, null, 'Ungueltige Parameter fuer Tuer (unitid>0, check=2, status=TRUE|FALSE)');
    }

    logDoorAccess($con, $rfid, $status, $unitid);
    json_out(true, null, null, 'Zutritt protokolliert', ['status' => $status, 'unitid' => $unitid]);
}

if (!in_array($action, ['start', 'stop'], true)) {
    http_response_code(400);
    json_out(false, null, null, 'Parameter action fehlt oder ungueltig (start|stop)');
}
if ($unitid <= 0) {
    http_response_code(400);
    json_out(false, null, null, 'Parameter unitid fehlt oder ungueltig');
}
if (!in_array($type, ['machine', 'laser', '3dprint', 'dtf', 'kiln'], true)) {
    http_response_code(400);
    json_out(false, null, null, 'Parameter type ungueltig (machine|laser|3dprint|dtf|kiln)');
}
if ($action === 'start' && empty($rfid)) {
    http_response_code(400);
    json_out(false, null, null, 'Parameter rfid fehlt');
}
if ($action === 'stop' && $key <= 0) {
    http_response_code(400);
    json_out(false, null, null, 'Parameter key fehlt oder ungueltig');
}

// ============================================================
// ACTION: START
// Checks: User -> Guthaben -> Schulung -> machine_time Insert
// Logik aus: getMemberInfoByRFID, checkPayload, checkSchulung, startMachineTime
// ============================================================

if ($action === 'start') {

    // -- 1. User lookup via RFID (aus getMemberInfoByRFID + checkSchulung) --
    $query = "SELECT c.cid, c.firstName, c.lastName, c.blocked, c.deleted
              FROM (`key` k
              LEFT JOIN `contact` c ON k.cid = c.cid)
              LEFT JOIN `membership` m ON m.cid = c.cid
              WHERE k.serial = '" . mysqli_real_escape_string($con, $rfid) . "' AND m.end IS NULL
              LIMIT 1";
    $result = mysqli_query($con, $query);
    if (!empty($error = mysqli_error($con))) {
        http_response_code(500);
        json_out(false, null, null, 'DB Fehler: ' . $error);
    }

    $member = mysqli_fetch_assoc($result);
    if (!$member || !$member['cid']) {
        json_out(false, null, null, 'Karte unbekannt oder kein aktives Mitglied');
    }

    $memberID  = (int)$member['cid'];
    $firstName = mb_convert_encoding($member['firstName'], 'UTF-8', 'ISO-8859-1');
    $lastName  = mb_convert_encoding($member['lastName'],  'UTF-8', 'ISO-8859-1');

    if ((int)$member['deleted'] === 1) {
        json_out(false, null, $firstName, 'Zugang gesperrt (geloescht)');
    }
    if ((int)$member['blocked'] === 1) {
        json_out(false, null, $firstName, 'Zugang gesperrt (blockiert)');
    }

    $payloadRow = getCurrentPayload($con, $memberID);
    $balance    = (float)$payloadRow['payload'];

    if ($unitid === 6) {
        $amount     = -0.5;
        $newPayload = round($balance + $amount, 1, PHP_ROUND_HALF_UP);
        if (!writePayload($con, $memberID, $payloadRow['fname'], $payloadRow['lname'], $newPayload, $unitid, $amount)) {
            http_response_code(500);
            json_out(false, null, $firstName, 'DB Fehler Kaffee-Abrechnung');
        }

        json_out(true, null, $firstName, 'Kaffee verrechnet', [
            'cost'    => $amount,
            'balance' => $newPayload,
        ]);
    }

    // -- 2. Guthaben prüfen (aus checkPayload) --
    if ($balance <= 0 && $type !== 'machine') {
        json_out(false, null, $firstName,
            sprintf('Guthaben %.2f EUR reicht nicht (min %.2f EUR)', $balance, $min_bal));
    }
    if ($balance < $min_bal) {
        json_out(false, null, $firstName,
            sprintf('Guthaben %.2f EUR (min %.2f EUR)', $balance, $min_bal));
    }

    // -- 3. Schulung prüfen (aus checkSchulung) --
    $query = "SELECT COUNT(*) as cnt FROM `schulung` WHERE reader_id = $unitid AND cid = $memberID";
    $result = mysqli_query($con, $query);
    if (!empty($error = mysqli_error($con))) {
        http_response_code(500);
        json_out(false, null, $firstName, 'DB Fehler Schulung: ' . $error);
    }
    $row = mysqli_fetch_assoc($result);
    if ((int)$row['cnt'] === 0) {
        json_out(false, null, $firstName, 'Keine Schulung fuer diese Maschine');
    }

    // -- 4. Session starten (aus startMachineTime) --
    $query = "SELECT * FROM contact WHERE cid = " . $memberID;
    $result1 = mysqli_query($con, $query);
    $row1    = mysqli_fetch_assoc($result1);

    $mytime = time();
    $fn     = mysqli_real_escape_string($con, $row1['firstName']);
    $ln     = mysqli_real_escape_string($con, $row1['lastName']);

    $query = "INSERT INTO machine_time VALUES (NULL, $memberID, $unitid, '$fn', '$ln', $mytime, NULL, NULL)";
    mysqli_query($con, $query);
    if (!empty($error = mysqli_error($con))) {
        http_response_code(500);
        json_out(false, null, $firstName, 'DB Fehler Insert: ' . $error);
    }
    $insertKey = (int)mysqli_insert_id($con);
    if ($insertKey <= 0) {
        http_response_code(500);
        json_out(false, null, $firstName, 'DB Fehler: kein Insert-Key');
    }

    json_out(true, $insertKey, $firstName, 'Aktiviert');
}

// ============================================================
// ACTION: STOP
// Maschinen-spezifische Abrechnung je nach type.
// Logik 1:1 aus: endMachineTime, endLaserTime, endMachineTime3D,
//                endMachineTimeDTF, endKiln
// ============================================================

if ($action === 'stop') {

    // Nachgeholter Stop (MakerLink-Queue): echte Endzeit verwenden, nie in der Zukunft.
    $now    = time();
    $endReq = intval($_GET['end'] ?? 0);
    $mytime = ($endReq > 0 && $endReq < $now) ? $endReq : $now;

    // -- machine_time schliessen (nur wenn noch offen -> idempotent) --
    $query = "UPDATE machine_time SET machine_end = GREATEST(machine_start, $mytime)
              WHERE id = $key AND machine_end IS NULL";
    mysqli_query($con, $query);
    if (!empty($error = mysqli_error($con))) {
        writeLOG(date('Y-m-d H:i:s') . ": stop UPDATE: " . $error);
        http_response_code(500);
        json_out(false, null, null, 'DB Fehler beim Stoppen: ' . $error);
    }
    $justClosed = mysqli_affected_rows($con) > 0;

    // -- Session-Daten holen --
    $query  = "SELECT * FROM machine_time WHERE id = $key";
    $result = mysqli_query($con, $query);
    if (!empty($error = mysqli_error($con))) {
        http_response_code(500);
        json_out(false, null, null, 'DB Fehler Sessiondaten: ' . $error);
    }
    $row           = mysqli_fetch_assoc($result);
    if (!$row) {
        json_out(false, null, null, 'Session nicht gefunden (key=' . $key . ' unitid=' . $unitid . ')');
    }
    // Wiederholter Stop: bereits geschlossen und (falls kostenpflichtig) bezahlt -> nichts tun.
    if (!$justClosed && ($type === 'machine' || (int)$row['paid'] === 1)) {
        json_out(true, null, null, 'Bereits gestoppt', ['already_stopped' => true]);
    }
    $memberID      = (int)$row['cid'];
    $tempID        = (int)$row['id'];
    $machine_start = (int)$row['machine_start'];
    $machine_end   = (int)$row['machine_end'];
    $duration_s    = $machine_end - $machine_start;

    // -- type=machine: kein Guthaben abziehen, nur schliessen --
    if ($type === 'machine') {
        json_out(true, null, null, 'Gestoppt', ['cost' => 0.0, 'duration_s' => $duration_s]);
    }

    // -- Alle anderen Types: Guthaben-Abrechnung --

    $PlanVomUser = getPlanVomUser($con, $memberID);

    // Preis-Spalte und Zeiteinheit je Type:
    //   laser:   ceil(sekunden / 3600 * 4) = angefangene Viertelstunden, Spalte: laser_full
    //   3dprint: ceil(sekunden / 60)        = angefangene Minuten,        Spalte: 3dprint_min
    //   dtf:     ceil(sekunden / 60)        = angefangene Minuten,        Spalte: dtf_drucker_min
    //   kiln:    Fixpreis 40 EUR (TODO: eigene price-Spalte anlegen)

    if ($type === 'kiln') {
        // Fixpreis - noch keine price-Tabellen-Spalte (TODO in query.php kommentiert)
        $cost    = 40.0;
        $useTime = 1;
    } else {
        $priceColMap = [
            'laser'   => ['col' => 'laser_full',      'unit' => ceil($duration_s / 3600 * 4)],
            '3dprint' => ['col' => '3dprint_min',     'unit' => ceil($duration_s / 60)],
            'dtf'     => ['col' => 'dtf_drucker_min', 'unit' => ceil($duration_s / 60)],
        ];
        $priceCol = $priceColMap[$type]['col'];
        $useTime  = $priceColMap[$type]['unit'];

        $query  = "SELECT * FROM price WHERE price_id = $PlanVomUser";
        $result = mysqli_query($con, $query);
        if (!empty($error = mysqli_error($con))) {
            writeLOG(date('Y-m-d H:i:s') . ": stop price query: " . $error);
        }
        $priceRow = mysqli_fetch_assoc($result);
        $cost     = (float)($priceRow[$priceCol] ?? 0);
    }

    // Guthaben berechnen und buchen
    $payloadRow = getCurrentPayload($con, $memberID);
    $oldPayload = (float)$payloadRow['payload'];
    $amount     = round((float)($cost * $useTime) * -1, 1, PHP_ROUND_HALF_UP);
    $newPayload = round($oldPayload + $amount, 1, PHP_ROUND_HALF_UP);

    if (!writePayload($con, $memberID, $payloadRow['fname'], $payloadRow['lname'], $newPayload, $unitid, $amount)) {
        http_response_code(500);
        json_out(false, null, null, 'DB Fehler bei der Guthaben-Buchung');
    }

    // machine_time als bezahlt markieren
    mysqli_query($con, "UPDATE machine_time SET paid = 1 WHERE id = $tempID");
    if (!empty($error = mysqli_error($con))) {
        writeLOG(date('Y-m-d H:i:s') . ": stop paid update: " . $error);
    }

    json_out(true, null, null, 'Gestoppt', [
        'cost'       => $amount,
        'balance'    => $newPayload,
        'duration_s' => $duration_s,
        'use_units'  => $useTime,
    ]);
}

mysqli_close($con);
