# MARS Backend-API (`machineswitch.php`)

Alle Aufrufe sind `GET` mit dem Header `X-MARS-Key: <key>`. Ohne gültigen Key antwortet der Server mit `401 {"ok":false,"msg":"Unauthorized"}`. Ab dem Patch in `backend/` gibt es keinen Standard-Key mehr: Fehlt `$config_mars_api_key` in `config.inc.php`, ist er leer oder noch `CHANGEME`, lehnt der Server **jede** Anfrage mit `500 {"ok":false,"msg":"Server nicht konfiguriert (API-Key fehlt)"}` ab. Der Key wird zeitkonstant verglichen (`hash_equals`).
Statuscodes: 200 = verarbeitet (auch `ok:false` bei verweigertem Zugang), 400 = Parameter fehlen oder sind ungültig, 500 = Datenbankfehler.

Die `rfid` steht im MARS-Format: Bytes als `0x..` in Kleinbuchstaben, ohne führende Null, durch Leerzeichen getrennt (zB `0xf4 0x96 0xd2 0x3`).

## Bestehend

### `action=start`
Parameter: `rfid`, `unitid`, `type` (machine|laser|3dprint|dtf|kiln), `min_balance` (Float, Standard 5.0)

Prüft User, Guthaben und Schulung (`schulung.reader_id = unitid`) und legt eine `machine_time`-Zeile an.
```json
{"ok":true,  "key":23212, "name":"Max", "msg":"Aktiviert"}
{"ok":false, "key":null,  "name":null,  "msg":"Keine Schulung fuer diese Maschine"}
```
Sonderfall `unitid=6` (Kaffeemaschine): bucht sofort 0,50 EUR ab, liefert `key:null`, `cost` und `balance`. Ein Stop ist nicht nötig.

### `action=stop`
Parameter: `key`, `unitid`, `type`, optional `end` (Unix-Zeit, ab [backend/machineswitch.php](../backend/machineswitch.php))

Schließt die `machine_time`-Zeile und rechnet je nach `type` ab: laser pro angefangener Viertelstunde, 3dprint und dtf pro Minute, kiln fix 40 EUR, machine kostenlos.
```json
{"ok":true, "key":null, "name":null, "msg":"Gestoppt", "cost":-2.5, "balance":12.3, "duration_s":900, "use_units":1}
{"ok":false, "key":null, "name":null, "msg":"Session nicht gefunden (key=.. unitid=..)"}
{"ok":true,  "key":null, "name":null, "msg":"Bereits gestoppt", "already_stopped":true}
```
Ab dem Patch ist der Stop idempotent: Eine bereits geschlossene und bezahlte Session wird nicht nochmal abgerechnet. Mit `end` wird bis zu diesem Zeitpunkt abgerechnet (Werte in der Zukunft werden ignoriert).

### `action=doorLockCheck`
Parameter: `rfid`

Antwort ist ein Array, `[0] == "True"` bedeutet Zutritt: `["True","Limited User","Mon18-22"]` oder `["False","Wrong Time","..."]`.

### `action=logDoorAccess`
Parameter: `rfid`, `status` (TRUE|FALSE), `unitid`, `check=2`, optional `time` (Unix-Zeit, ab 0.6.0)

Wird ca. 2 s nach der Relaisaktion aufgerufen. Mit `time` meldet MakerLink Zutritte nach, die während eines Serverausfalls stattfanden (Werte in der Zukunft werden ignoriert).

### `action=whitelist` (ab 0.6.0)
Ohne Parameter. Liefert die Karten-UIDs aller aktiven Unlimited-Mitglieder für den Offline-Fallback, **ohne Namen**:
```json
{"ok":true, "key":null, "name":null, "msg":"Whitelist", "cards":["0xe7 0xf7 0x1b 0xa3", "..."], "count":42}
```
Gleiche Regel wie `getRFIDWhitelist` in `query.php` (Plan-IDs 12, 13, 14, 15, 16, 19, 20, 50, 51, 52, 53, aktive Mitgliedschaft und Karte, nicht gelöscht), zusätzlich ohne blockierte Mitglieder.

### `action=offlineSession` (ab 0.6.0)
Parameter: `rfid`, `unitid`, `type`, `start`, `end` (Unix-Zeiten)

Bucht eine Nutzung nach, die MakerLink während eines Serverausfalls freigegeben hat: legt `machine_time` mit Start und Ende an und rechnet wie `stop` ab. **Idempotent** über Mitglied und Startzeit, eine zweite Meldung liefert `already_stopped`. Start älter als 30 Tage, Start in der Zukunft oder Ende vor dem Start → 400. Unbekannte Karte → 404, MakerLink verwirft den Eintrag dann.

### Ohne/ungültige `action`
Liefert `400`, aber erst **nach** Auth und DB-Verbindung. Die Integration nutzt das als Verbindungstest: 400 bedeutet ok, 401 einen falschen Key, 500 einen DB-Fehler.

## Erweiterungen

| Erweiterung | Zweck |
|---|---|
| ✅ `action=stop&end=<unix>` + Idempotenz | Umgesetzt in `backend/machineswitch.php` |
| ✅ `action=whitelist` | Umgesetzt (0.6.0), siehe oben. Ersetzt das geplante `trainedCards` vorerst. |
| ✅ `action=offlineSession` | Umgesetzt (0.6.0), idempotent über Mitglied und Startzeit statt über eine `offline_id`, deshalb ohne neue DB-Spalte. |
| `action=trainedCards&unitid=X` | Später: Whitelist geschnitten mit den Schulungen pro Unit (Entscheidung des Users: Offline-Schulungsprüfung nachrüsten). |
| ✅ Fix SQL-Injection im `start`-Query | Umgesetzt in `backend/machineswitch.php` |
