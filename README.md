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
4. Reader einrichten: siehe unten, alles passiert im MakerLink-Panel in der Seitenleiste.

Voraussetzung ist Home Assistant 2025.4 oder neuer.

## Installation der Reader (ESPHome)
HACS installiert nur die Integration (`custom_components/makerlink/`). Die Reader-Firmware liegt im Ordner [esphome/](esphome/README.md) und wird **nicht** von HACS verteilt. Du brauchst das ESPHome-Add-on (oder ESPHome Device Builder) in Home Assistant.

**Einmalig vorab**
1. Den **Inhalt** von `esphome/` aus diesem Repository (Download als ZIP oder `git clone`) nach `/config/esphome/` kopieren (Samba, SSH oder VS-Code-Add-on). Alle Ordner und Dateien, auch wenn du nur eine Variante nutzt, weil sie sich gegenseitig einbinden. Die Ordnerstruktur darf nicht verändert werden, die Include-Pfade (`common/…`, `makerlink/pn532_*.h`) gelten relativ zu `/config/esphome/`.
2. `secrets.yaml` im selben Ordner braucht: `wifi_ssid`, `wifi_password` (Hauptnetz), `wifi_ssid1`, `wifi_password1` (Fallback-Netz, bei Bedarf dieselben Werte oder ein Dummy), `api_encryption_key` (`openssl rand -base64 32`). Der API-Schlüssel gilt auch für OTA-Uploads. API-Key und URL des MARS-Servers gehören nicht auf den Reader, die stehen nur in der Integration.

**Pro neuem Reader (4 Schritte, geführt im Panel)**
1. **MakerLink-Panel → „Reader hinzufügen“.** Hardware wählen, der Gerätename ist schon vorbelegt (`makerlink-01`, `-02`, …, immer ein freier). Das Panel erzeugt die fertige YAML. Kopieren.
2. **In ESPHome** ein neues Gerät mit genau diesem Namen anlegen („Leere Konfiguration“), den Inhalt durch die kopierte YAML ersetzen und **Install** wählen. Beim ersten Mal per USB, danach per OTA.
3. **In Home Assistant** (Einstellungen → Geräte & Dienste) das gefundene ESPHome-Gerät **hinzufügen**. Das Panel zeigt dir diesen Schritt an, solange der Reader gefunden, aber noch nicht bestätigt ist.
4. **Zurück im Panel** erscheint der Reader unter **„Neue Reader“**. **Einrichten** klicken: Name, Funktion (Maschine oder Tür), Unit-ID (Standard 9999 = Test-ID) und bei Maschinen die Abrechnungsart. Display, Relais und Sicherheitsschalter werden automatisch zugeordnet. Mit **Identifizieren** zeigt der Reader 10 Sekunden „HIER BIN ICH“, so erkennst du ihn am Tisch.

Die Funktion ist nicht in der Firmware: Ein Reader kann jederzeit im Panel über **Bearbeiten** von Maschine auf Tür (oder zurück) umgestellt werden, ohne Neu-Flashen. Beim Wechsel werden die Einstellungen der Einheit zurückgesetzt, und er ist gesperrt, solange eine Session läuft. Dort lassen sich auch Name, Unit-ID, Abrechnungsart und Schaltziel ändern und die Einheit entfernen.

Die erzeugte YAML entspricht den Dateien `esphome/tocopy-makerlink-*.yaml` (nur mit anderem Namen). Wer lieber von Hand arbeitet, kopiert eine davon und passt `devicename` an. Der manuelle Weg über **Maschine oder Tür hinzufügen** in den Integrationseinstellungen funktioniert weiterhin, zB für Reader anderer Technik.

Der Zigbee-Reader (XIAO ESP32-C5) hat kein WLAN, keine API und kein OTA und wird nur per USB geflasht. Details dazu in [esphome/README.md](esphome/README.md).

## Übersicht in der Seitenleiste
Nach der Installation erscheint **MakerLink** in der Seitenleiste, sichtbar für alle Benutzer. Die Seite zeigt alle Maschinen und Türen live:
- Status, Displayinhalt, Benutzer und Laufzeit der Session, Nachlauf, letzte Kosten und Guthaben
- Zustand von Schaltziel, Sicherheitsschaltern und Reader (online/offline), offene Buchungen

Aktionen dort: Session beenden, Nachlauf beenden, Admin-Modus, Außer Betrieb, Tür öffnen, Link zur Geräteseite. Administratoren sehen zusätzlich **Reader hinzufügen**, **Neue Reader** und **Bearbeiten** (siehe Installation der Reader).

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
**Integration:** HACS zeigt neue Versionen an, sobald im Repository ein GitHub-Release existiert. Update in HACS installieren und Home Assistant neu starten.

**Reader-Firmware:** Das läuft getrennt und **nicht automatisch**. HACS fasst `/config/esphome/` nie an, und ein Reader ändert sich erst, wenn er neu gebaut und geflasht wird:
1. Das Repository in der neuen Version holen und den Inhalt von `esphome/` erneut nach `/config/esphome/` kopieren. Dabei vorhandene Dateien überschreiben. Deine eigenen Geräte-YAMLs und `secrets.yaml` liegen nicht im Repo und bleiben unberührt.
2. In ESPHome beim jeweiligen Reader **Install** (Wireless) ausführen. Das kompiliert mit den neuen Dateien und spielt sie per OTA ein.
3. Die Firmware-Version des Readers steht in den Gerätedetails in Home Assistant. Sie entspricht der Version von MakerLink (`esphome: project: version`). Ob ein Firmware-Update nötig ist, siehe Release-Notes.

**Release veröffentlichen (Entwickler):**
1. `version` in `custom_components/makerlink/manifest.json` und die gleiche Nummer in den ESPHome-Dateien erhöhen.
2. Committen und taggen: `git tag v0.2.0 && git push --tags`.
3. Auf GitHub ein Release zum Tag veröffentlichen.

## Entwicklung
```bash
python -m venv .venv && .venv/Scripts/pip install pytest pytest-asyncio aiohttp
.venv/Scripts/python -m pytest
```
Lokal laufen nur die Tests der Kernlogik, die ohne Home Assistant auskommt. Die CI testet zusätzlich gegen ein echtes Home Assistant und prüft mit hassfest und der HACS-Validierung.
