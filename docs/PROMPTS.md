# Prompt- und Entscheidungsprotokoll

Chronologische Aufzeichnung der Anforderungen und Entscheidungen aus den Sessions mit Claude Code. Neue Einträge kommen unten dazu.

---

## 2026-10-17 – Projektstart
> ich möchte eine integration für home assistant schreiben. sie heisst MakerLink. sie soll in meinem git-repository vorhanden sein und ich möchte sie in home assistant installieren und updaten können

**Ergebnis:** Ein HACS-fähiges Grundgerüst (`custom_components/makerlink`, `hacs.json`, Validate-Workflow, README). Updates laufen über GitHub-Releases.

## 2026-10-17 – Fachlicher Rahmen
> Das Maschinenzugangssystem von makeraustria basiert im moment auf intelligenten "readern" die per wifi verbunden sind, telemetrie an home-assistant schicken, somit verwaltbar sind und dann mit einer http schnittstelle auf unserem server kommunizieren für zugänge, checks und beschränkungen.
> Der Plan ist es, dass die Geräte (egal welche mcu oder funk-technologie nur noch ein display, einen pn532 reader und eventuell ein relais sowie 2 mikroschalter die ein öffnen oder schliessen einer maschinentür kontrollieren besitzen. die Businesslogik, das onboarden von neuen readern und das verknüpfen mit wlan oder zigbee steckdosen zum schalten von entfernten geräten soll in der integration gemacht werden.
> - erst planen, dann entwerfen wir gemeinsam.
> Die relevanten dateien sind im anhang

Anhänge (alle unter [legacy/](legacy/), Vertrag zusätzlich in [API.md](API.md)): `mars-1720-bambulabp1prot.yaml`, `maker-reader-hw-esp8266.yaml`, `maker-reader-logic.yaml`, `machineswitch.php`. Später nachgereicht: `mars-9998-demo32supermini.yaml`, `maker-reader-hw-esp32s3.yaml`, `pn532_hsu.h`.

**Entscheidungen (Rückfragen):**
| Frage | Antwort |
|---|---|
| Transport Reader ↔ HA | Entitäten-basiert |
| Zweck der Mikroschalter | Nutzungserkennung → später präzisiert als **Interlock** (siehe unten) |
| Verhalten bei Ausfall | Lokaler Fallback |
| Backend | Erweitern erlaubt |
| Türlogik | Pro Maschine konfigurierbar |
| Umfang des Fallbacks | Alle geschulten Karten |
| Onboarding | Auto-Discovery + Assistent |
| MVP | Start/Stop + Abrechnung, externe Steckdosen, Offline-Fallback |

## 2026-10-18 – Präzisierung im Plan (vom User ergänzt)
> Es gibt Maschinen und Türen:
> - Maschinen schalten beim anhalten einer Karte ein und bei erneutem anhalten wieder aus. Manche Maschinen haben einen "cooldown timer" beim ausschalten (zB: 3D Drucker) der verhindern soll, dass der strom ausschaltet und die Maschine noch heiss ist, somit die Kühlung zu früh endet. Manche Maschinen haben Mikroschalter 1 oder 2 für Türen oder schutzvorrichtungen (zB: Kiln) die verhindern, dass der Reader und somit die Maschine einschaltet, wenn die tür nicht geschlossen ist und sofort ausschaltet wenn die tür im betrieb geöffnet wird.
> - Türen schalten ein relais nur kurz um das türöffnerelement freizugeben und gehen dann wieder in den Ruhezustand zurück. Das soll konfigurierbar sein.

**Folge:** Die Mikroschalter sind ein Interlock. Türen werden eine eigene Einheit-Art mit Impuls-Relais und kommen in Phase 1a.

## 2026-10-18 – Arbeitsweise
> arbeite weiter > schreibe die relevanten informationen, prompts usw. ins projektverzeichnis, merke dir das!

**Folge:** Ab jetzt werden Anforderungen, Prompts und Entscheidungen fortlaufend in `docs/` gepflegt (diese Datei, [PLAN.md](PLAN.md), [API.md](API.md)).

**Umgesetzt (Phase 1a):**
- Kernlogik als Port der Legacy-Firmware
- Einheiten „Maschine“ und „Tür“ als Config-Subentries
- Interlock, Nachlauf, Admin-Modus und Außer Betrieb
- Stop-Queue bei Serverausfall
- Externe Schaltziele (beliebige switch-, light- oder input_boolean-Entität)
- ESPHome-Referenz-Firmware

Getroffene Annahmen stehen in [PLAN.md](PLAN.md) unter „Offene Fragen“.

## 2026-10-18 – Legacy-Dateien
> docs/legacy/ enthält nur maker-reader-logic.yaml. Die anderen beiden Dateien hattest du abgelehnt, und den PHP-Code habe ich deshalb auch nicht ins Repo kopiert.
> versuche das nocheinmal

**Folge:** Alle vier Anhänge liegen jetzt unverändert in `docs/legacy/` (die frühere Ablehnung war nicht als „nicht ins Repo“ gemeint).

## 2026-10-18 – Offene Fragen beantwortet
> lies die plan.md nochmal mit der beantwortung der offenen fragen und implementiere entsprechend

Antworten (in PLAN.md eingetragen):
- **Interlock im Betrieb:** Strom sofort aus (ohne Nachlauf), Session wird gestoppt und abgerechnet.
- **HA-Neustart:** Ist das Schaltziel noch an, läuft die Session weiter. Ist es aus, wird sie gestoppt.
- **Stop ohne Server:** „Ja, das machen wir so“ (Queue und `end=<unix>`).

**Umgesetzt:**
- Die Integration verhielt sich bei allen drei Punkten schon so.
- Neu ist, dass nur vorübergehende Fehler in die Queue kommen, 4xx wird verworfen.
- Backend-Patch `backend/machineswitch.php` mit `end`-Parameter, idempotentem Stop und SQL-Injection-Fix.

## 2026-10-18 – Privates Repository
> ich möchte mein github repo nicht öffentlich machen > wie kann ich das dann trotzdem installieren?

**Folge:** Das Repo bleibt privat. Die Installation über HACS ist damit nicht vorgesehen, stattdessen per Deploy-Key, `git clone` auf dem HA-Host und Symlink nach `custom_components` (Details in der Antwort bzw. im README, sobald übernommen).

## 2026-10-18 – Secret-Check vor Veröffentlichung
> kontrolliere ob keine geheimnisse im repo stehen, dann würde ich in betracht ziehen es öffentlich zu machen.

**Ergebnis:**
- Arbeitsstand und gesamte Git-Historie (3 Commits) durchsucht: keine Keys, Passwörter, Tokens oder Secret-Dateien. Alles läuft über `!secret` bzw. `config.inc.php`.
- **Vor dem Veröffentlichen:** gepatchte `backend/machineswitch.php` deployen, weil Legacy-Code und Doku die SQL-Injection im Start-Query offenlegen.
- Weitere Hinweise: Fallback-Key `CHANGEME`, interne IPs in `docs/legacy`, die Commit-E-Mail wird öffentlich.

## 2026-10-18 – PN532 über HSU statt I2C
> der pn532 reader funktioniert NICHT über i2c (das liegt am esp32 und clockstretching) -> deshab war der ursprung per hsu implementiert:
>   p_pn532_rx: "4"    # HSU RX  (ESP RX ← PN532 TX)
>   p_pn532_tx: "5"    # HSU TX  (ESP TX → PN532 RX)
>
> > das brauchen wir jetzt auch wieder um eine funktion zu gewährleisten

Nachgereicht: `mars-9998-demo32supermini.yaml`, `maker-reader-hw-esp32s3.yaml`, `pn532_hsu.h` (→ [legacy/](legacy/)).

**Umgesetzt:**
- `esphome/makerlink-reader-esp32s3-pn532.yaml` nutzt jetzt HSU über `pn532_hsu.h` (Arduino) mit der echten Pinbelegung: PN532 4/5, Relais 6, I2C 8/9 mit 50 kHz, Schalter 10/11.
- Die Karte wird einmal pro Auflegen gemeldet (Verhaltensänderung gegenüber der Legacy-Firmware).
- Neue Diagnose-Entität „PN532 bereit“.
- `esphome config` mit ESPHome 2026.9.1 ist für beide Varianten fehlerfrei, und die ESP32-S3-Variante kompiliert ohne Warnungen. Auf Hardware ist sie noch nicht getestet.

## 2026-10-18 – OLED-Variante
> this reader has an 0,91 Zoll 128x32 IIC I2C SSD1306

Kontext: Der User hat `esphome/makerlink-reader-esp32s3-pn532-oled.yaml` als Kopie angelegt und das Pinout `docs/layouts/esp32s3-supermini.png` beigelegt.

**Umgesetzt:**
- Die Firmware ist jetzt in Bausteine aufgeteilt: Basis, ESP32-S3-Hardware und Display-Pakete (LCD 16x2 bzw. SSD1306 128x32).
- Die OLED-Variante zeigt 2×16 Zeichen in Roboto Mono 12 px. I2C läuft dort mit 400 kHz, weil der PN532 nicht am Bus hängt.
- Alle drei Varianten bestehen `esphome config`, die OLED-Variante kompiliert ohne Warnungen. Auf Hardware ist sie noch nicht getestet.

## 2026-10-18 – Seitenleiste und Reader-Übersicht
> ich möchte die integration in der seitenleiste anzeigen können und brauche eine übersicht der konfigurierten reader mit status usw. funktioniert das mit einer integration oder müsste man da eine APP daraus machen? wie kann ich vorgehen?

**Antwort/Empfehlung:** Keine App (früher Add-on) nötig. Die Integration registriert selbst ein Seitenleisten-Panel (Custom Panel, eigene JS-Datei in der Integration) und liefert die Daten über eine eigene WebSocket-API.

## 2026-10-18 – Panel umsetzen
> der eintrag soll für alle sichtbar sein, setze um wie vorgeschlagen :)
> erhöhe die versionsnummer, damit Nach dem repo-push ein update im test-ha gemacht werden kann

**Umgesetzt (v0.3.0):**
- Seitenleisten-Panel „MakerLink“ für alle Benutzer.
- WebSocket-API (`makerlink/units`, `makerlink/subscribe`, `makerlink/action`).
- Kachel pro Einheit mit Status, Display-Vorschau, Session, Laufzeit, Schaltziel, Sicherheitsschaltern, Reader online und offenen Buchungen.
- Aktionen: Session beenden, Nachlauf beenden, Admin-Modus, Außer Betrieb, Tür öffnen, Link zur Geräteseite.
- Version 0.2.0 → 0.3.0 in `manifest.json` und im ESPHome-Projekt.
- Geprüft: Das Panel wurde mit Fake-Daten in Chrome headless gerendert (hell, dunkel, schmal). Escaping und Layout stimmen. Ein Test im echten HA steht noch aus.

## 2026-10-19 – XIAO ESP32-S3 und XIAO ESP32-C5 über Zigbee
> the esp32s3 and xiao-esp32s3 have similar capabilities but different pins that can be used > i made a copy (makerlink-reader-xiao-esp32s3-pn532-oled and esp32s3-xiao-pn532-hsu.yaml) to get a demo working.
> ADDITIONALLY > we want to get the same behaviour with a XIAO ESP32 C5 over zigbee > can we do a seperate config in /common/ for that? (every other pinout is the same) ... what i want is that the boot button on the C5 (gpio28 is activating pairing and resetting when it is long pressed >5s) ... the userLed (GPIO27 should indicate the relay status on or off)

Kontext: Pinout `docs/layouts/esp32s3-xiao.png` beigelegt. Die beiden Kopien waren noch unverändert (Super-Mini-Pins, Top-Datei bindet die Super-Mini-Hardware ein).

**Recherche-Ergebnisse (Stand ESPHome 2026.9):**
- Die native ESPHome-Zigbee-Komponente (ab 2026.5) unterstützt den ESP32-C5. Auf ESP32 stellt sie aber nur `binary_sensor` und `sensor` bereit, kein Switch, kein Text, kein Event.
- Die externe Komponente `luar123/zigbee_esphome` kann eigene Cluster und String-Attribute. Sie braucht ESP-IDF und ist auf dem C5 nicht getestet. OTA über Zigbee gibt es nicht.
- `pn532_hsu.h` braucht Arduino (`HardwareSerial`), Zigbee braucht ESP-IDF. Der Treiber muss deshalb auf die ESPHome-`uart`-Komponente portiert werden.
- XIAO ESP32-C5: D0=GPIO1, D1=GPIO0, D2=GPIO25 (Strapping), D3=GPIO7 (Strapping), D4/SDA=GPIO23, D5/SCL=GPIO24, D6/TX=GPIO11, D7/RX=GPIO12, D8=GPIO8, D9=GPIO9, D10=GPIO10. BOOT=GPIO28, User-LED=GPIO27 (Polarität unklar, vermutlich active-low).

**Entscheidungen (Rückfragen):**
| Frage | Antwort |
|---|---|
| Zigbee-Coordinator | ZHA |
| XIAO-Pinbelegung | Vorschlag: D0 Relais, D4/D5 I2C, D6/D7 PN532 HSU, D8/D9 Schalter |
| Vorgehen C5 | Erst Machbarkeit: PN532-Port, minimale Zigbee-Firmware mit Kartenscan, Relais, LED, BOOT-Taste. Display und Integrations-Anbindung folgen danach. |

**Umgesetzt:**
- XIAO-ESP32-S3-Dateien mit XIAO-Pins und Board `seeed_xiao_esp32s3`. Die Top-Datei bindet jetzt die XIAO-Hardware ein.
- Neuer Treiber `esphome/pn532_uart.h` (ESPHome-uart, ESP-IDF-tauglich). Dabei ist der Pufferüberlauf aus `pn532_hsu.h` behoben.
- `common/esp32c5-xiao-pn532-zigbee.yaml` und `makerlink-reader-xiao-esp32c5-pn532-oled-zigbee.yaml`.
- Display-Pakete nutzen jetzt die Substitutions `link_connected`/`link_offline_text` (WLAN: HA-API, Zigbee: Netz beigetreten).
- Geprüft: Alle fünf Varianten bestehen `esphome config`. XIAO-S3 und XIAO-C5 kompilieren, Hardware- und ZHA-Test stehen aus.

## 2026-10-19 – PN532-Treiber nach esphome/makerlink/
> ich habe die pn532 dateien in den korrekten ordner /makerlink/ verschoben, damit die struktur einfacher zum kopieren in home-assistant ist

**Folge:**
- Der Inhalt von `esphome/` wird 1:1 nach `/config/esphome/` kopiert. Die Include-Pfade `makerlink/pn532_*.h` passen dazu, im README angepasst.
- Beim Prüfen gefunden und behoben: In `makerlink-reader-esp8266-rc522.yaml` stand `reset_pin: ${. }` (aus Commit b1404cb) statt `${p_rfid_rst}`.
- Alle fünf Varianten bestehen mit dem neuen Layout `esphome config`.

## 2026-10-19 – XIAO-S3-Demo: PN532 antwortet nicht
> (Screenshot Web-Serial-Log „MakerLink Reader XIAO ESP32-S3“: jede Sekunde `[E][pn532:051]: GetFirmwareVersion failed (no response)`, `safe_mode: Boot seems successful`)

**Analyse:** Die Firmware läuft, aber auf dem UART kommt nichts zurück. Aktiv sind D6/D7 = GPIO43/44, die Datei enthält aber auch den Kommentar „verdrahtet“ mit GPIO4/5. Wahrscheinlichste Ursache: Firmware-Pins und Verdrahtung passen nicht zusammen. Weitere Kandidaten: TX/RX vertauscht, PN532 nicht auf HSU gejumpert, Versorgung.

## 2026-10-19 – Relais am XIAO
> kontrolliere das mit dem https://wiki.seeedstudio.com/relay_add_on_module_for_xiao/ nochmal > das relay schaltet meiner meinung nach nicht (ich höre kein klicken)

**Ergebnis:**
- Das Seeed Relay Add-on schaltet über **D1**.
- In der S3-Datei stand `GPIO0 # D1`. Beim XIAO-S3 ist D1 aber **GPIO2**, GPIO0 ist dort der BOOT-Strapping-Pin und liegt auf keinem Header-Pin.
- Korrigiert: S3 D1 = GPIO2, C5 D1 = GPIO0 (vorher D0/GPIO1). D0 ist jetzt frei.

## 2026-10-19 – Version bei jedem Push
> merke dir bei jedem git push die versionsnummer zu erhöhen, damit hacs das auch mitbekommt

**Folge:** Als Regel in `CLAUDE.md` und im Memory festgehalten. Version jetzt 0.3.0 → **0.3.1** (Fixes: Relais-Pin XIAO, ESP8266 `reset_pin`, README-Struktur).

## 2026-10-20 – Reader-Installation in der README
> Bei Installation in der Readme gehört ein Block der Reader-Installation (wie definiert man die reader korrekt? welche yaml dateien (dateien generell) müssen manuell in welchen ordner kopiert werden. Wie funktionieren updates aus dem repo hier?

**Ergebnis:** README hat jetzt den Abschnitt „Installation der Reader (ESPHome)“ (Dateien nach `/config/esphome/`, `secrets.yaml`, Geräte-YAML, Flashen, Verknüpfung). „Updates“ trennt Integration (HACS) und Reader-Firmware (manuell kopieren, dann per OTA neu flashen; HACS fasst `/config/esphome/` nicht an).

## 2026-10-20 – Zweites WLAN als Fallback
> i want wifi_ssid and wifi_ssid1 to be configured - the second entry is the fallback

**Ergebnis:** `common/makerlink-reader-base.yaml` nutzt `wifi: networks:` mit `wifi_ssid`/`wifi_password` (Priorität 10) und `wifi_ssid1`/`wifi_password1` (Priorität 0). Secrets in beiden READMEs ergänzt.

## 2026-10-20 – Unit-ID pflegen, Standard 9999
> wo wird die reader-id (unitid) gepflegt und verändert? Ein Reader soll nach dem onboarding standardmäßig die unitid 9999 haben, bis sie überschrieben wird (das ist die TEST-ID)

**Ergebnis:** Die Unit-ID liegt in der Integration (Subentry pro Einheit, `unit_id`), nicht auf dem Reader. Vorher war sie Pflichtfeld ohne Vorgabe und nach dem Anlegen nicht änderbar. Jetzt: Vorgabe 9999 (`TEST_UNIT_ID`), 9999 darf mehrfach vergeben werden (kein `unique_id`), und **Neu konfigurieren** zeigt erst Name + Unit-ID, dann die Hardware.

## 2026-10-20 – OTA-Passwort durch Verschlüsselung ersetzen
> WARNING 'ota' password wastes significant flash and RAM (about 3.5 KB and 60 bytes plus the password on the heap): the device already offers encryption with the 'api' encryption key, which authenticates any uploader that takes it, and a password only matters for uploaders without encryption support; remove 'password' and add 'encryption' under 'ota' so uploads use the key and encryption is required

**Ergebnis:** `common/makerlink-reader-base.yaml`: `ota: password` entfernt, stattdessen `encryption: key: !secret api_encryption_key`. `ota_password` entfällt aus den Secrets (beide READMEs angepasst).

## 2026-10-20 – ESPHome-Bausteine überarbeiten (Planung)
> rework the esphome stuff: (plan first and give me options and lets discuss)
> - it should be possible to use both > oled and lcd without reflashing
> - The lcd normally needs 5v (the oled 3)
> - i want to keep the amount of configurations as low as possible
> - is it feasable to put it on the same i2c or better on a seperate one (my preference because of pin amount would be seperate)
> - The WEMOS version is a legacy reader which is already present 30 times and just needs to be reflashed, the others are new hardware to be built

**Status:** Diskussion, Plan vorgeschlagen.

## 2026-10-20 – ESPHome-Umbau freigegeben
> leg los und mach es wie vorgeschlagen.
> Der wemos bleibt so (ich kann nichts umbauen) - die bestehenden reader muss ich sowieso manuell per usb flashen und dann onboarden.
> Behalte supermini xiao s3 und c5 Beide displays

**Ergebnis:** Drei Geräte-YAMLs statt fünf: `makerlink-reader-esp32s3.yaml` (Super Mini oder XIAO per `board`, später in zwei Dateien geteilt, siehe unten), `makerlink-reader-xiao-esp32c5-zigbee.yaml`, `makerlink-reader-esp8266-rc522-lcd.yaml` (unverändert). `common/display-dual.yaml` enthält LCD und OLED, `common/esp32s3-pn532-hsu.yaml` ersetzt die zwei S3-Hardwarepakete (Jinja-Substitutions je nach `board`). S3: zwei getrennte I2C-Busse (OLED 400 kHz, LCD 50 kHz hinter Pegelwandler). C5: nur ein Hardware-I2C-Bus, deshalb ein gemeinsamer Bus mit 100 kHz.

## 2026-10-20 – S3-Varianten getrennt, Bootloop-Fix
Kontext: Der User flashte die S3-Firmware und bekam einen Bootloop (`spi_flash: Detected size(4096k) smaller than the size in the binary image header(8192k)`, `octal_psram: PSRAM chip is not connected`). Standard `board: xiao` setzte 8 MB Flash und Octal-PSRAM, die Hardware hat 4 MB und kein PSRAM.

> teile den supermini und den xiao s3 in 2 files auf (reduziert die probleme)

**Ergebnis:** PSRAM entfernt (wird nicht genutzt). Zwei Geräte-YAMLs `makerlink-reader-esp32s3-supermini.yaml` (4 MB) und `makerlink-reader-esp32s3-xiao.yaml` (8 MB). Board, Pins und Flash-Größe in `common/esp32s3-supermini.yaml` bzw. `common/esp32s3-xiao.yaml`, die gemeinsame Logik bleibt in `common/esp32s3-pn532-hsu.yaml`. Die Substitution `board` entfällt.

## 2026-10-21 – „Verbinde...“ nach Neustart, kein Scan-Feedback
> Bei einem neustart des readers wird in der zweiten zeile meist "verbinde..." angezeigt obwohl er schon verbunden ist. es gibt leider auch keine indikation, dass eine karte gerade gescannt wird und der user weiss nicht wie lange er die karte dranhalten sollte (das müssen wir beheben)

**Ursache 1:** Die Firmware startet mit `Verbinde...` in Zeile 2. Die Integration schickt Displaytexte nur, wenn sich ihr Soll-Text ändert (`_refresh` vergleicht mit `_last_lines`). Nach einem Reader-Neustart im Ruhezustand ist der Soll-Text unverändert, also wurde nichts geschickt. Zeile 1 stimmt zufällig, weil Start- und Ruhetext gleich sind.

**Fix 1 (Integration):** Ändert sich eine Display-Entität des Readers auf einen Wert ungleich dem Soll-Text (Reboot/Reconnect), sendet `UnitController.resend_display()` den aktuellen Text erneut. Höchstens alle 2 s pro Einheit, damit keine Schleife entsteht. Mit Test abgedeckt.

**Fix 2 (Firmware):** Lokales Scan-Feedback. Sofort beim Lesen zeigt das Display „Karte erkannt / Bitte warten...“, bis neue Texte aus HA kommen, höchstens 4 s (Globals `g_scan_pending`/`g_scan_ms`, in allen Display-Paketen).

Version 0.4.0 → **0.4.1**.

## 2026-10-27 – Onboarding zu kompliziert (Planung)
> the onboarding of a device is too complicated at the moment. What was holding me back:
> - the yaml files for esphome are always a copy of a known hardware but the filenames are difficult to get right.
> - Our readers have unique ids (and a description, and a function like door, machine [with sub-function]) - it is difficult to get it right the first time
> - the process is > flashing, finding the device in esphome integration and add it to makerlink integration, then it shows in the makerlink page, this is complicated and confusing.
> - The reader device can not be switched from door to machine and vice versa
>
> the readers themselves work great

**Analyse:** Name, Funktion und Unit-ID standen an drei Stellen (YAML, ESPHome-Gerät, MakerLink-Einheit) und mussten von Hand zusammengeführt werden (sechs Entitäten-Auswahlfelder). Die Funktion (Tür/Maschine) steckt gar nicht in der Firmware, das Umstellen scheiterte nur daran, dass der Neu-konfigurieren-Dialog die Art nicht änderbar machte. Außerdem passten die Dateinamen in der README nicht zu denen im Repo (`makerlink-reader-*` statt `tocopy-makerlink-*`).

**Entscheidungen des Users** (Rückfrage am 2026-10-27):
- Einrichten im **MakerLink-Panel** statt im HA-Config-Flow.
- **Eigene YAML pro Reader**, dafür ein Generator im Panel (statt generischer Firmware mit MAC-Suffix).
- Der ESPHome-Bestätigungsklick bleibt, das Panel zeigt den Schritt als **Hinweis** an.

**Ergebnis (v0.5.0):** Siehe PLAN.md 3.6. Panel: „Reader hinzufügen“ (YAML-Generator mit freiem Namen), „Neue Reader“ mit Einrichten/Identifizieren, Bearbeiten (Name, Funktion Maschine ↔ Tür, Unit-ID, Abrechnungsart, Schaltziel) und Entfernen. README-Dateinamen korrigiert.

## 2026-10-27 – Logo für die Integration
> ich möchte ein logo bei der hacs integration anzeigen
>
> (SVG `makerlink5.svg` mitgeliefert: Zahnrad, NFC-Karte, Funkwellen)

**Ergebnis (v0.5.1):** Quelle in `docs/logo/makerlink.svg`. Daraus gerenderte PNGs in `custom_components/makerlink/brand/` (`icon`, `logo`, `dark_logo`, jeweils auch `@2x`), das ab Home Assistant 2026.3 lokal geladen wird. Offen: Ob HACS selbst das Logo in seiner Liste zeigt, ist nicht bestätigt (ein Forenbeitrag sagt, nur mit Eintrag im Brands-Repository). Das Wortmarken-Logo ist Icon plus Text „MakerLink“ in der Systemschrift, nicht das Original.
