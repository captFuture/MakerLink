# MakerLink – Architektur- und Umsetzungsplan

> Lebendes Dokument. Bei Änderungen an Architektur oder Entscheidungen hier nachziehen.
> Verlauf der Anforderungen: [PROMPTS.md](PROMPTS.md) · Backend-API: [API.md](API.md)

## Kontext
Heute steckt die gesamte Business-Logik des MakerAustria-Zugangssystems (MARS) in der ESPHome-Firmware ([legacy/maker-reader-logic.yaml](legacy/maker-reader-logic.yaml)). Dazu gehören Start/Stop, Countdown, Admin-Modus, Außer Betrieb, Display und die HTTP-Calls an `machineswitch.php` mit dem API-Key. Jeder Reader braucht deshalb Secrets und Logik, und Änderungen erfordern ein Neuflashen aller Geräte.

Es gibt **Maschinen** und **Türen**:
- **Maschinen** schalten beim Anhalten einer Karte ein und beim erneuten Anhalten wieder aus.
  - Manche Maschinen haben einen **Nachlauf-Timer** (zB 3D-Drucker). Der Strom bleibt nach dem Stop noch an, damit die Kühlung nicht zu früh endet.
  - Manche Maschinen haben **1 oder 2 Mikroschalter** an Türen oder Schutzvorrichtungen (zB Kiln). Ist die Tür nicht geschlossen, schaltet die Maschine nicht ein. Wird die Tür im Betrieb geöffnet, schaltet sie sofort aus (**Interlock**).
- **Türen** schalten ein Relais nur kurz, um den Türöffner freizugeben, und gehen dann in den Ruhezustand zurück. Die Impulsdauer ist konfigurierbar.

**Ziel:** Die Reader werden „dumm“ (Display, PN532, optional Relais, optional 1–2 Mikroschalter). Logik, Onboarding und die Verknüpfung mit externen WLAN- oder Zigbee-Steckdosen übernimmt die HA-Integration **MakerLink**, die per HACS aus diesem Repo installiert und aktualisiert wird.

### Getroffene Entscheidungen
| Thema | Entscheidung |
|---|---|
| Transport | **Entitäten-basiert**: Ein Reader ist ein Satz HA-Entitäten, damit ist die Funk-Technik egal. Für ESPHome liefern wir eine Referenz-Firmware mit. |
| Mikroschalter | **Interlock**: kein Einschalten bei offener Tür, sofortiges Ausschalten beim Öffnen im Betrieb. Konfigurierbar pro Maschine (0, 1 oder 2 Schalter). |
| Türen | Eigene Einheit-Art `door`: doorLockCheck, Relais-Impuls (Dauer konfigurierbar), logDoorAccess |
| Ausfall | **Lokaler Fallback**: Der Reader kennt alle geschulten Karten (gehasht), puffert Offline-Nutzungen und lässt sie nachverrechnen |
| Backend | `machineswitch.php` **darf erweitert werden** |
| Onboarding | **Auto-Discovery** für MakerLink-ESPHome-Reader und ein Assistent; manueller Weg für andere Technik |
| MVP | Start/Stop und Abrechnung, externe Steckdosen, Offline-Fallback |
| Interlock im Betrieb | Strom sofort aus (ohne Nachlauf), Session wird gestoppt und abgerechnet |
| HA-Neustart mit laufender Session | Schaltziel noch an → Session läuft weiter; aus → Session wird gestoppt (ersetzt `cleanup_stuck_session`) |
| Stop ohne Server | Lokal stoppen, Abrechnung persistent in die Queue, mit `end=<unix>` nachholen. Nur vorübergehende Fehler (Netz, 5xx, 401) kommen in die Queue, 4xx wird verworfen. Das Backend rechnet idempotent ab. |

### Offene Fragen
Derzeit keine.

---

## 1. Gesamtarchitektur

```
 Reader (dumm)                Home Assistant / MakerLink                 Server
 ─────────────                ───────────────────────────                ──────
 PN532 ── Tag-Event ────────▶ UnitController (pro Maschine/Tür) ─HTTP─▶ machineswitch.php
 Display ◀── text entities ── │ Zustandsautomat                        (start/stop/
 Relais  ◀── switch ───────── │ Nachlauf, Admin, OOO, Interlock         doorLockCheck/
 Schalter ─ binary_sensor ──▶ │ Display-Renderer                        logDoorAccess/
                              │ Offline-Kartensync ─ESPHome-Action─▶   trainedCards/
 Zigbee/WLAN-Steckdose ◀───── └─ Schaltziel = beliebige switch-Entity  offlineSession)
```

- **Hub (Config Entry):** API-URL und X-MARS-Key, genau einmal pro HA-Instanz.
- **Einheit (Config Subentry):** Art (Maschine/Tür), Unit-ID, Maschinentyp, Reader-Gerät, Display-Entitäten, Schaltziel, Mikroschalter, Parameter. Mindestversion HA 2025.4 (Subentries).

## 2. Reader-Vertrag (technologieneutral)

| Rolle | HA-Mechanismus | Pflicht |
|---|---|---|
| Karten-Scan | Event `esphome.makerlink_tag` (`uid`, `device_id`) **oder** Standard-Event `tag_scanned` mit `device_id`. Die UID kommt roh, die Integration wandelt ins MARS-Format um. | ja |
| Display Zeile 1/2 | 2× `text`-Entity (16 Zeichen) | nein |
| Schaltziel | `switch`-Entity (Reader-Relais **oder** externe Steckdose) | ja |
| Mikroschalter 1/2 | `binary_sensor` (HA-Konvention: `on` = offen) | nein |
| Offline-Fähigkeit | ESPHome-Actions `makerlink_sync_cards`, `makerlink_heartbeat`, Event `esphome.makerlink_offline_session` | nein (nur MakerLink-Firmware) |

Die MakerLink-Firmware nutzt `esphome.makerlink_tag` statt `tag_scanned`, damit nicht jede Mitgliedskarte in der Tag-Registry von HA landet.

UID-Konvertierung: 1:1-Port des Lambdas aus `maker-reader-hw-esp8266.yaml` („F4-96-D2-03“ → `0xf4 0x96 0xd2 0x3`, URL-codiert `0xf4%200x96%200xd2%200x3`, führende Null pro Byte entfernt) in `mars_format.py`, mit Unit-Tests.

## 3. Integration – Komponenten

```
custom_components/makerlink/
  __init__.py        Setup Hub, Controller pro Subentry, Reload bei Subentry-Änderung
  manifest.json
  const.py           Konstanten (ohne HA-Import)
  api.py             MarsApiClient (aiohttp)
  mars_format.py     UID-Konvertierung, Response-Parsing (ohne HA-Import)
  controller.py      MachineController / DoorController (ohne HA-Import, testbar)
  display.py         Port des LCD-Lambdas → (zeile1, zeile2) (ohne HA-Import)
  hub.py             HA-Glue: Events, State-Tracking, Ticker, Store, Display-Push
  config_flow.py     Hub-Flow + Einheit-Subentry-Flow (+ Reconfigure)
  entity.py          Basisklasse (Device pro Einheit)
  sensor.py / binary_sensor.py / switch.py / number.py / select.py / button.py
  diagnostics.py
  strings.json, translations/{de,en}.json
esphome/             Referenz-Firmware für dumme Reader
backend/             Erweiterte machineswitch.php (Deployment siehe backend/README.md)
docs/                Plan, API, Prompts, Legacy-Code
tests/               pytest (Kernlogik ohne HA; HA-Tests in CI)
```

### 3.1 MachineController (Zustandsautomat)
Port von `maker-reader-logic.yaml`:
- **Scan im Ruhezustand:** Interlock prüfen (Tür zu?) und Schaltziel prüfen (verfügbar?). Dann API `start` (min_balance als Float), Schaltziel ein, Name merken.
- **Scan bei aktiver Session:** API `stop`, Nachlauf `shutdown_time`, danach Schaltziel aus. Die Stop-Anzeige (Guthaben) bleibt 5 s stehen.
- **Antwort `ok` ohne `key`** (zB Kaffeemaschine Unit 6): Es wird nur die Meldung bzw. das Guthaben angezeigt, keine Session.
- **Schaltziel extern aus während Session:** Stop-Sequenz.
- **Schaltziel extern ein ohne Session:** Admin-Modus.
- **Tür geöffnet während Session oder Nachlauf:** Schaltziel sofort aus, Session stoppen.
- **Außer Betrieb:** Scans werden abgelehnt. Karten-Cooldown 5 s, Fehlermeldungen 3 s.
- **Persistenz** über HA `Store`: Session-Key, Name, Startzeit, Einstellungen, Queue offener Stops.
- **HA-Events:** `makerlink_session_started`, `makerlink_session_stopped`, `makerlink_card_rejected`.

### 3.2 DoorController
Scan → `doorLockCheck` → bei Zutritt Relais-Impuls (`pulse_time`, Standard 3 s) und Anzeige → nach 2 s `logDoorAccess` (TRUE/FALSE).

### 3.3 Externe Steckdosen
Das Schaltziel ist eine beliebige `switch`-Entity (ZHA/Z2M, Shelly, Tasmota …). Ist sie `unavailable`, wird der Start verweigert („Steckdose offline“). Der Offline-Fallback funktioniert nur mit dem Relais am Reader.

### 3.4 Discovery und Onboarding (Phase 1b)
Die Firmware setzt `esphome: project: name: makeraustria.makerlink_reader`. `discovery.py` erkennt solche Geräte im Device-Registry und startet einen Discovery-Flow, der die Entitäten des Geräts vorbelegt.

## 4. Offline-Fallback (Phase 1c)
- **Backend:** `action=trainedCards&unitid=X` liefert gehashte UIDs (`sha256(salt + mars_uid)` gekürzt auf 8 Byte). `action=offlineSession&rfid&unitid&type&start&end&offline_id` rechnet idempotent ab.
- **Integration:** Synchronisiert die Kartenliste stündlich, beim Start und per Button (gechunkt per ESPHome-Action). Gepufferte Sessions werden per Event angenommen, nachverrechnet und quittiert.
- **Firmware:** Offline heißt kein Heartbeat seit 60 s. Bei einem Hash-Treffer schaltet der Reader selbst, puffert Karte, Start und Ende im Flash und zeigt „OFFLINE“.
- **Sicherheit:** SQL-Injection im `start`-Query ist bereits in `backend/machineswitch.php` behoben.

## 5. Phasen
1. **Phase 1a – Kern:** api, mars_format, display, Controller (Maschine + Tür), Hub- und Subentry-Flow, Entitäten, externe Steckdosen, Interlock, Referenz-Firmware ohne Offline. Tests.
2. **Phase 1b – Discovery:** device_registry-Listener und Discovery-Flow.
3. **Phase 1c – Offline:** Backend-Patch, offline.py, Firmware-Erweiterung.
4. **Phase 2:** Diagnose-Dashboards, Statistiken, Kiln-Spezialfälle.

### Stand (2026-10-18)
- **Phase 1a umgesetzt (v0.2.0, ungetestet in echtem HA):**
  - Kernlogik: `controller.py`, `display.py`, `mars_format.py`, `api.py`
  - HA-Glue: `hub.py`, Config-Flow mit Subentries, alle Plattformen, Übersetzungen de/en, Diagnose
  - ESPHome-Referenz-Firmware unter `esphome/`
  - 40 lokale Unit-Tests grün; der Import-Smoke-Test gegen echtes HA läuft in der CI
- **Backend-Patch** (`backend/machineswitch.php`): `end`-Parameter, idempotenter Stop, SQL-Injection-Fix. Muss noch auf den Server.
- **Noch offen in 1a:** Config-Flow-Tests mit `pytest-homeassistant-custom-component` und ein E2E-Test auf echter Hardware.
- **Nächste Schritte:** Phase 1b (Discovery), danach 1c (Offline inklusive Backend-Patch).

## 6. Verifikation
- **Unit-Tests** (lokal, ohne HA): UID-Format, Response-Parsing, Display, Zustandsautomat mit Fake-API und Fake-Hardware.
- **CI:** HACS-Validierung, hassfest, pytest.
- **E2E:**
  1. Test-HA mit HACS aufsetzen und Hub gegen eine Testinstanz von `machineswitch.php` konfigurieren.
  2. Reader flashen und als Einheit anlegen.
  3. Karte scannen: Schaltziel geht an und es entsteht eine `machine_time`-Zeile.
  4. Erneut scannen: Nachlauf läuft, danach Abrechnung in `member_payload`.
  5. Tür öffnen: Die Maschine geht sofort aus.
