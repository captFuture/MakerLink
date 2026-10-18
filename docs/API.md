# MARS Backend-API (`machineswitch.php`)

Alle Aufrufe sind `GET` mit dem Header `X-MARS-Key: <key>`. Ohne gültigen Key antwortet der Server mit `401 {"ok":false,"msg":"Unauthorized"}`.
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
Parameter: `key`, `unitid`, `type`

Schließt die `machine_time`-Zeile und rechnet je nach `type` ab: laser pro angefangener Viertelstunde, 3dprint und dtf pro Minute, kiln fix 40 EUR, machine kostenlos.
```json
{"ok":true, "key":null, "name":null, "msg":"Gestoppt", "cost":-2.5, "balance":12.3, "duration_s":900, "use_units":1}
{"ok":false, "key":null, "name":null, "msg":"Session nicht gefunden (key=.. unitid=..)"}
```

### `action=doorLockCheck`
Parameter: `rfid`

Antwort ist ein Array, `[0] == "True"` bedeutet Zutritt: `["True","Limited User","Mon18-22"]` oder `["False","Wrong Time","..."]`.

### `action=logDoorAccess`
Parameter: `rfid`, `status` (TRUE|FALSE), `unitid`, `check=2`

Wird ca. 2 s nach der Relaisaktion aufgerufen.

### Ohne/ungültige `action`
Liefert `400`, aber erst **nach** Auth und DB-Verbindung. Die Integration nutzt das als Verbindungstest: 400 bedeutet ok, 401 einen falschen Key, 500 einen DB-Fehler.

## Geplante Erweiterungen

| Erweiterung | Zweck |
|---|---|
| `action=stop&end=<unix>` (optional) | Nachgeholter Stop nach einem Server-Ausfall rechnet mit der echten Endzeit ab statt mit `time()`. |
| `action=trainedCards&unitid=X` | `{"ok":true,"cards":["<16 hex>",...],"version":"<etag>"}` mit `sha256(salt + rfid)`, gekürzt auf 8 Byte. Für den Offline-Fallback. |
| `action=offlineSession&rfid&unitid&type&start&end&offline_id` | Nachverrechnung einer Offline-Nutzung, idempotent über `offline_id`. |
| Fix | Im `start`-Query `$rfid` mit `mysqli_real_escape_string` maskieren (SQL-Injection). |
