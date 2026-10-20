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
   - Unit-ID (Standard 9999 = Test-ID, mehrfach verwendbar; später über Neu konfigurieren änderbar)
   - Reader-Gerät
   - Display-Text-Entitäten
   - Schaltziel (Relais am Reader oder Steckdose)
   - optional die Sicherheitsschalter

Voraussetzung ist Home Assistant 2025.4 oder neuer.

## Installation der Reader (ESPHome)
HACS installiert nur die Integration (`custom_components/makerlink/`). Die Reader-Firmware liegt im Ordner [esphome/](esphome/README.md) und wird **nicht** von HACS verteilt. Du brauchst das ESPHome-Add-on (oder ESPHome Device Builder) in Home Assistant.

**1. Dateien kopieren.** Den **Inhalt** von `esphome/` aus diesem Repository (Download als ZIP oder `git clone`) in den ESPHome-Config-Ordner von Home Assistant kopieren, also nach `/config/esphome/` (per Samba, SSH oder VS-Code-Add-on). Alle Ordner und Dateien kopieren, auch wenn du nur eine Variante nutzt, weil sie sich gegenseitig einbinden:
```
/config/esphome/
  secrets.yaml                        ← deine Zugangsdaten (nicht im Repo)
  maker9998.yaml                      ← deine Geräte-YAML (siehe Schritt 3)
  makerlink-reader-*.yaml             ← Gerätevarianten aus dem Repo
  common/                             ← Bausteine (Basis, Hardware, Displays)
  makerlink/
    pn532_hsu.h
    pn532_uart.h
```
Die Ordnerstruktur darf nicht verändert werden, die Include-Pfade (`common/…`, `makerlink/pn532_*.h`) gelten relativ zu `/config/esphome/`.

**2. `secrets.yaml`** (im selben Ordner) braucht: `wifi_ssid`, `wifi_password` (Hauptnetz), `wifi_ssid1`, `wifi_password1` (Fallback-Netz, bei Bedarf dieselben Werte oder ein Dummy), `api_encryption_key` (`openssl rand -base64 32`). Der API-Schlüssel gilt auch für OTA-Uploads. API-Key und URL des MARS-Servers gehören nicht auf den Reader, die stehen nur in der Integration.

**3. Reader definieren.** Pro Reader eine eigene kleine YAML anlegen, zB `maker9998.yaml`. Sie enthält nur Name und die passende Gerätevariante:
```yaml
substitutions:
  devicename: maker9998        # eindeutig, nur Kleinbuchstaben, Ziffern, Bindestrich
  friendly_name: Reader Drucker 1
  # display_i2c_address: "0x3F"   # LCD, Standard 0x27
  # oled_i2c_address: "0x3D"      # OLED, Standard 0x3C
packages:
  reader: !include makerlink-reader-esp32s3-xiao.yaml
```
Beide Displays (LCD und OLED) sind in jeder neuen Firmware enthalten. Welche Variante zu welcher Hardware gehört, steht in der Tabelle in [esphome/README.md](esphome/README.md). Die Gerätevarianten selbst nicht bearbeiten, sonst gehen Änderungen beim nächsten Update verloren. Eigene Anpassungen gehören in die Geräte-YAML.

**4. Flashen.** Beim ersten Mal per USB (ESPHome → Install → Plug into this computer / Manual download), danach per OTA über WLAN. Der Reader taucht dann in Home Assistant unter der ESPHome-Integration auf und wird dort hinzugefügt.

**5. In MakerLink verknüpfen.** Unter **Maschine oder Tür hinzufügen** das Reader-Gerät, die beiden Display-Text-Entitäten, das Schaltziel und die Sicherheitsschalter auswählen (siehe oben).

Der Zigbee-Reader (XIAO ESP32-C5) hat kein WLAN, keine API und kein OTA und wird nur per USB geflasht. Details dazu in [esphome/README.md](esphome/README.md).

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
