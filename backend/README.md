# Backend-Patch für `machineswitch.php`

`machineswitch.php` hier ist die erweiterte Version von [docs/legacy/machineswitch.php](../docs/legacy/machineswitch.php). Sie ist rückwärtskompatibel, alte ESPHome-Reader funktionieren damit unverändert weiter.

## Änderungen
| Änderung | Warum |
|---|---|
| `action=stop` akzeptiert optional `end=<unix>` | MakerLink holt Stops nach einem Serverausfall nach. Abgerechnet wird bis zur echten Endzeit statt bis zum Zeitpunkt des Nachholens. Werte in der Zukunft werden ignoriert, und das Ende liegt nie vor dem Start. |
| `action=stop` ist idempotent | `UPDATE … WHERE machine_end IS NULL`. Ein wiederholter Stop (zB weil die Antwort verloren ging) liefert `{"ok":true,"msg":"Bereits gestoppt","already_stopped":true}` und rechnet nicht doppelt ab. Ist die Session geschlossen, aber noch nicht bezahlt (`paid` ≠ 1), wird die Abrechnung nachgeholt. |
| Kein Standard-Key `CHANGEME` mehr | Fehlt `$config_mars_api_key`, ist er leer oder `CHANGEME`, wird jede Anfrage mit 500 abgelehnt (fail closed, plus Eintrag im PHP-Fehlerlog). Bisher galt dann `CHANGEME` als gültig, und der steht öffentlich im Code. Der Key wird zeitkonstant mit `hash_equals` verglichen. **Vor dem Deploy prüfen:** Ist euer echter Key wörtlich `CHANGEME`, erst einen neuen Key setzen (Server, Reader, MakerLink), sonst sind alle Reader ausgesperrt. |
| SQL-Injection im `start`-Query behoben | `$rfid` wird jetzt mit `mysqli_real_escape_string` maskiert, wie schon in `doorLockCheck`. |
| **Neu (MakerLink 0.6.0):** `action=whitelist` | UIDs aller aktiven Unlimited-Mitglieder für den Offline-Fallback. Mit X-MARS-Key und ohne Namen, anders als `query.php?action=getRFIDWhitelist`. |
| **Neu (MakerLink 0.6.0):** `action=offlineSession` | Bucht eine während eines Serverausfalls freigegebene Nutzung nach. Idempotent über Mitglied und Startzeit, Abrechnung wie `stop` (gemeinsame Funktion `finishSession`). |
| **Neu (MakerLink 0.6.0):** `logDoorAccess&time=` | Nachgemeldete Offline-Zutritte bekommen die echte Zeit. |

### Test der 0.6.0-Erweiterung (wieder als `machineswitch_test.php`)
1. `php -l machineswitch_test.php`
2. `action=whitelist`: `ok:true`, `count` plausibel (gleich viele Einträge wie `getRFIDWhitelist`, abzüglich blockierter Mitglieder), keine Namen.
3. `action=offlineSession` mit Testkarte, Unit 9998, `type=machine`, `start`/`end` vor wenigen Minuten: `Gestoppt`. Denselben Aufruf wiederholen: `already_stopped`.
4. Start/Stop wie bisher (Regression). Dann über `machineswitch.php` kopieren.

## Deployment
Die Datei wurde nie gegen einen PHP-Interpreter geprüft. Ein Syntaxfehler würde alle Reader gleichzeitig stilllegen, deshalb zuerst parallel testen:

1. Prüfen, dass `$config_mars_api_key` in `config.inc.php` gesetzt und **nicht** `CHANGEME` ist.
2. Die laufende `machineswitch.php` sichern (Rückweg = Backup zurückkopieren).
3. `backend/machineswitch.php` **daneben** als `machineswitch_test.php` hochladen. Sie lädt dieselbe `../config.inc.php`.
4. Syntax prüfen: `php -l machineswitch_test.php`
5. Ohne `action` aufrufen, mit Header `X-MARS-Key`. Erwartet: HTTP **400** („Parameter action fehlt“), also Key und Datenbank in Ordnung. Ohne Header muss **401** kommen.
6. Einen Start/Stop-Zyklus mit Testkarte gegen die Testdatei (zB MakerLink kurz auf deren URL stellen), dann denselben Stop noch einmal: Der zweite muss `already_stopped` liefern.
7. Erst dann die Testdatei über `machineswitch.php` kopieren und die Testdatei löschen.
