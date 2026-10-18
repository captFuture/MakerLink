# Backend-Patch für `machineswitch.php`

`machineswitch.php` hier ist die erweiterte Version von [docs/legacy/machineswitch.php](../docs/legacy/machineswitch.php). Sie ist rückwärtskompatibel, alte ESPHome-Reader funktionieren damit unverändert weiter.

## Änderungen
| Änderung | Warum |
|---|---|
| `action=stop` akzeptiert optional `end=<unix>` | MakerLink holt Stops nach einem Serverausfall nach. Abgerechnet wird bis zur echten Endzeit statt bis zum Zeitpunkt des Nachholens. Werte in der Zukunft werden ignoriert, und das Ende liegt nie vor dem Start. |
| `action=stop` ist idempotent | `UPDATE … WHERE machine_end IS NULL`. Ein wiederholter Stop (zB weil die Antwort verloren ging) liefert `{"ok":true,"msg":"Bereits gestoppt","already_stopped":true}` und rechnet nicht doppelt ab. Ist die Session geschlossen, aber noch nicht bezahlt (`paid` ≠ 1), wird die Abrechnung nachgeholt. |
| SQL-Injection im `start`-Query behoben | `$rfid` wird jetzt mit `mysqli_real_escape_string` maskiert, wie schon in `doorLockCheck`. |

## Deployment
1. Die bestehende Datei auf dem Server sichern.
2. `backend/machineswitch.php` an dieselbe Stelle kopieren. Sie lädt weiterhin `../config.inc.php`.
3. Die Datei mit `php -l machineswitch.php` prüfen.
4. Einen Start/Stop-Zyklus mit einem Reader testen, dann einen Stop doppelt aufrufen. Der zweite muss `already_stopped` liefern.
