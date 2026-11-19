# MARS-Mock fuer MakerLink

Simuliert `backend/machineswitch.php` (Python 3, nur Standardbibliothek, keine Installation).

```
python tools/mock_server/server.py [--port 8080] [--key test-key] [--state szenario.json]
```

- GUI: `http://localhost:8080/`
- API: `http://<IP-des-PCs>:8080/machineswitch.php`, Header `X-MARS-Key` (Standard `test-key`)

## In Home Assistant verwenden
MakerLink unter *Neu konfigurieren* auf `http://<IP-des-PCs>:8080/machineswitch.php` und den Key `test-key` stellen. Auf dem PC muss die Windows-Firewall den Port freigeben (beim ersten Start fragt Windows danach). Es werden keine echten Daten benutzt, der Mock hat nur Beispielmitglieder.

## Geraete (Standard)
| unitid | Geraet | Typ | Besonderheit |
|---|---|---|---|
| 1 | Tuer aussen | door | `doorLockCheck` + `logDoorAccess`, Zutritt nach Tarif und Uhrzeit |
| 6 | Kaffeemaschine | coffee | Start bucht sofort 0,50 EUR, kein Stop |
| 1720 | Laser | laser | je angefangene Viertelstunde, Preis nach Tarif |
| 1721 | 3D-Drucker | 3dprint | je angefangene Minute |
| 1722 | Brennofen | kiln | Fixpreis 40 EUR |
| 1730 | Standmaschine | machine | kostenlos, nur Schulung noetig |

Geraete lassen sich in der GUI (Einstellungen) aendern.

## Beispielmitglieder
Max (Unlimited, 50 EUR), Erika (Basic, 20 EUR), Sepp (Standard, 12,30 EUR), Leo (Guthaben 0), Bernd (blockiert), Hanna (ohne Schulung), Lisa (Zutritt nur Mo/Mi 18-22 Uhr). Karten-UIDs stehen in der GUI.

## Szenarien
- **Fehlerregeln** (Tab *Fehler*): pro Aktion und Geraet, Modus: HTTP-Status, Timeout, Verbindung trennen, HTML statt JSON, leerer Body, **Aktion ausfuehren, aber Antwort verlieren** (testet die Idempotenz von stop/offlineSession). Optional nur jede n-te Anfrage, begrenzte Trefferzahl.
- **Serverzeit** verschieben: Zutrittstarife, Laufzeiten, 30-Tage-Grenze bei `offlineSession`.
- **Virtueller Reader** (Tab *Geraete*): Karte scannen, Start, Stop (auch doppelt), Zeit vorspulen.
- Zustand exportieren/importieren; mit `--state` beim Start laden.

## Tests
`pytest tests/test_mock_server.py`
