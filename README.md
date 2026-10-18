# MakerLink

Home-Assistant-Integration für das Maschinen- und Türzugangssystem von MakerAustria (MARS).

Die Reader sind „dumm“: Sie lesen Karten, zeigen zwei Displayzeilen und schalten optional ein Relais. Die gesamte Logik läuft in Home Assistant:
- Start und Stop mit Abrechnung über das MARS-Backend
- Nachlaufzeit (zB 3D-Drucker)
- Sicherheitsschalter (Interlock)
- Admin-Modus und Außer Betrieb
- Türöffner mit Impuls
- Schalten externer WLAN- oder Zigbee-Steckdosen

Architektur und Entscheidungen: [docs/PLAN.md](docs/PLAN.md) · Backend-API: [docs/API.md](docs/API.md) · Reader-Firmware: [esphome/](esphome/README.md)

## Installation (HACS)
1. In HACS über ⋮ → **Benutzerdefinierte Repositories** die URL dieses Repositories mit Kategorie **Integration** hinzufügen.
2. **MakerLink** installieren und Home Assistant neu starten.
3. Unter Einstellungen → Geräte & Dienste → **Integration hinzufügen** → MakerLink die URL von `machineswitch.php` und den API-Key eintragen.
4. In der Integration über **Maschine oder Tür hinzufügen** pro Einheit Folgendes wählen:
   - Unit-ID
   - Reader-Gerät
   - Display-Text-Entitäten
   - Schaltziel (Relais am Reader oder Steckdose)
   - optional die Sicherheitsschalter

Voraussetzung ist Home Assistant 2025.4 oder neuer.

## Übersicht in der Seitenleiste
Nach der Installation erscheint **MakerLink** in der Seitenleiste, sichtbar für alle Benutzer. Die Seite zeigt alle Maschinen und Türen live:
- Status, Displayinhalt, Benutzer und Laufzeit der Session, Nachlauf, letzte Kosten und Guthaben
- Zustand von Schaltziel, Sicherheitsschaltern und Reader (online/offline), offene Buchungen

Aktionen dort: Session beenden, Nachlauf beenden, Admin-Modus, Außer Betrieb, Tür öffnen, Link zur Geräteseite.

## Entitäten pro Einheit
| Entität | Maschine | Tür |
|---|---|---|
| Status, Display | ✓ | ✓ |
| Benutzer, Sessionbeginn, Letzte Kosten, Letztes Guthaben, Offene Buchungen | ✓ | |
| Session aktiv, Sicherheitsschalter | ✓ | |
| Außer Betrieb (Switch) | ✓ | ✓ |
| Admin-Modus (Switch) | ✓ | |
| Mindestguthaben, Nachlaufzeit, Abrechnungsart | ✓ | |
| Türöffner-Impuls | | ✓ |
| Session beenden / Tür öffnen (Button) | ✓ | ✓ |

Events für Automationen und Logbuch: `makerlink_session_started`, `makerlink_session_stopped`, `makerlink_card_rejected`, `makerlink_door_access`.

## Updates
HACS zeigt neue Versionen an, sobald ein GitHub-Release existiert:
1. `version` in `custom_components/makerlink/manifest.json` erhöhen.
2. Committen und taggen: `git tag v0.2.0 && git push --tags`.
3. Auf GitHub ein Release zum Tag veröffentlichen.

## Entwicklung
```bash
python -m venv .venv && .venv/Scripts/pip install pytest pytest-asyncio aiohttp
.venv/Scripts/python -m pytest
```
Lokal laufen nur die Tests der Kernlogik, die ohne Home Assistant auskommt. Die CI testet zusätzlich gegen ein echtes Home Assistant und prüft mit hassfest und der HACS-Validierung.
