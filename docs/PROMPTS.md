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

## 2026-10-27 – Sicherheitsschalter nur wenn vorhanden
> wenn bei der erstkonfiguration kein "Sicherheitsschalter" definiert ist (2 stück möglich), dann soll das nicht angezeigt werden (dann gibt es keinen sicherheitsschalter)
> Nur bei 1 oder 2 sicherheitsschaltern soll am display der hinweis "tür offen" stehen und ein einschalten verhindern, wenn nicht geschlossen

**Ursache:** Das Onboarding im Panel hängte beide Sicherheitsschalter-Eingänge der Firmware automatisch an jede Maschine. Ein nicht angeschlossener Eingang liest sich als „offen“, also zeigte das Display „Tür offen“ und der Start war gesperrt.

**Ergebnis (v0.5.2):** Im Einrichten/Bearbeiten-Formular gibt es „Sicherheitsschalter“ mit keine / 1 / 2 (Standard keine). Nur dann werden die Eingänge zugeordnet. Controller, Display, Entität und Panel zeigten Interlocks schon vorher nur bei konfigurierten Schaltern.

## 2026-10-21 – Außer Betrieb: keine Karte lesen
> wenn der "ausser betrieb" modus aktiv ist, darf keine karte gelesen werden

**Ergebnis:** `on_card` im Controller kehrt bei „Außer Betrieb“ sofort zurück: kein API-Call, keine Ablehnungsmeldung, kein `makerlink_card_rejected`-Event, kein Cooldown. Das Display zeigt weiter „AUSSER BETRIEB“.

## 2026-11-09 – Bestandsaufnahme
> was fehlt uns noch?

**Antwort:** Offene Punkte nach Priorität. Vor dem Echtbetrieb: Backend-Patch deployen, E2E-Test gegen den echten MARS-Server, Unit-IDs der 30 Bestands-Reader. Fehlende Funktionen: Offline-Fallback (Phase 1c), Zigbee-Stufen 1–3, Scan-Protokoll im Panel. Qualität: HA-Tests für Config-Flow/WebSocket, Release-Tags für HACS. Details in der Antwort im Chat.

## 2026-11-09 – Home-Assistant-MCP für Remote-Tests
> können wir ein mcp verbinden um die sachen remote durchzuführen? der Home Assistant MCP Server ist installiert und online

**Ergebnis:** Der ha-mcp-Server ist in Claude bereits verbunden und erreicht das Test-HA (HA 2026.11.0, ha-mcp 9.1.2). MakerLink ist geladen (1 Einheit). Der Demo-Reader `makerlink-9999` (192.168.20.224) war zum Prüfzeitpunkt nicht erreichbar, alle seine Entitäten `unavailable`. Regel: Lesen ohne Rückfrage, schreibende Aktionen (Services, Events, Neustart, HACS-Update) nur nach Bestätigung, weil ein simulierter Kartenscan echte Buchungen am MARS-Server auslöst.

## 2026-11-10 – Bricht der Backend-Patch die alten Reader?
> zu > Backend-Patch deployen (?) ... würde das die momentane lösung brechen? oder kann ich es einfach deployen und die alten reader gehen trotzdem?

**Analyse (Diff legacy ↔ backend, abgeglichen mit `maker-reader-logic.yaml`):** Abwärtskompatibel. Drei inhaltliche Änderungen:
1. Start: `$rfid` wird maskiert. Für echte UIDs (`0xf4 0x96 …`) gibt es nichts zu maskieren, das Verhalten ist identisch.
2. Stop ohne `end` (alte Reader senden keins) rechnet wie bisher mit `time()`. Gleiches UPDATE und gleiche Antwort für offene Sessions.
3. Stop einer bereits geschlossenen Session: bisher wurde erneut abgerechnet (Doppelbuchung), jetzt kommt `ok:true, "Bereits gestoppt"` ohne `cost`. Der alte Reader zeigt dann „Schaltet aus“ ohne Guthaben. Unbekannter Key wie bisher „Session nicht gefunden“.

Tür-Aktionen sind unverändert. **Restrisiko:** Die PHP-Syntax ist nie geprüft worden (kein PHP lokal, WSL startet nicht). Deshalb parallel als Testdatei deployen, `php -l`, testen, dann tauschen; Backup für den Rückweg.

## 2026-11-10 – CHANGEME-Fix im Backend
> ja, bau den CHANGEME-fix ein

**Ergebnis:**
- `backend/machineswitch.php` hat keinen Standard-Key mehr. Fehlt `$config_mars_api_key`, ist er leer oder `CHANGEME`, antwortet der Server auf jede Anfrage mit 500 und schreibt einen Eintrag ins PHP-Fehlerlog (fail closed).
- Der Key wird zeitkonstant mit `hash_equals` verglichen. Er wird nicht getrimmt, damit das Verhalten gegenüber heute exakt gleich bleibt.
- Normaler Betrieb (Key gesetzt) ist unverändert.
- Achtung: Ist der echte Key wörtlich `CHANGEME`, sperrt der Patch alle Reader aus.
- Doku: `docs/API.md`, `backend/README.md`. Version 0.5.2 → **0.5.3** (Push-Regel; die Integration selbst ist unverändert).

## 2026-11-10 – Testdatei auf dem Server
> (Screenshot: Browser ruft `http://makeradmin.ddns.net:8080/crm/api/machineswitch_test.php` auf, Antwort `{"ok":false,"msg":"Unauthorized"}`)

**Bewertung:** Die Datei ist syntaktisch fehlerfrei (sonst Parse-Fehler statt JSON). Der Key in `config.inc.php` ist gesetzt und nicht `CHANGEME` (sonst 500). Ohne Header 401 wie erwartet.
- **Nächster Schritt:** `curl` mit `X-MARS-Key`, erwartet 400. Danach MakerLink per „Neu konfigurieren“ auf die Testdatei stellen und Start/Stop mit Testkarte remote prüfen.
- **Nebenbefund:** Die API läuft über unverschlüsseltes HTTP übers Internet, der Key geht im Klartext. Das ist kein Effekt des Patches. Empfehlung: HTTPS (Let's Encrypt).

## 2026-11-10 – Test der Testdatei mit Key
> (PowerShell: `curl -i -H "X-MARS-Key: <redigiert>" …/machineswitch_test.php` scheiterte, weil `curl` in PowerShell `Invoke-WebRequest` ist)

**Ergebnis** (mit `curl` aus Git Bash ausgeführt, ohne `action`, also ohne Wirkung):
- Richtiger Key → **400** „Parameter action fehlt“, Key-Vergleich und DB funktionieren.
- Ohne Key → 401. Falscher Key → 401.
- Server: Apache 2.4 / PHP 8.3.

Der Key wurde im Chat im Klartext genannt und läuft ohnehin unverschlüsselt über HTTP. Beim Umstieg auf HTTPS einen neuen Key vergeben. Nächster Schritt: Start/Stop mit Testkarte über die Testdatei.

## 2026-11-10 – Updates ohne manuellen Aufwand über ha-mcp?
> ich habe einen mcp server auf home assistant installiert.
> Checke ob wir jetzt die veränderungen für makerlink (esphome) ohne mabuellen aufwand umsetzen können

**Bestandsaufnahme** (nur gelesen, nichts geändert):
- **Integration:** HACS führt MakerLink als Custom-Repo `captFuture/MakerLink`, installiert ist Commit `50fba17` (keine Releases, HACS verfolgt Commits). Entity `update.makerlink_update` existiert. Nach einem Push lässt sich das Update samt HA-Neustart per MCP auslösen (Schreibaktion, nur nach Rückfrage).
- **ESPHome-Dateien nach `/config/esphome/`:** Mit ha-mcp derzeit **nicht** möglich. Die Datei-Tools fehlen („HA-MCP File & YAML Tools“-Eintrag nicht eingerichtet), und `esphome/` steht auch dann nicht in der Schreib-Allowlist, sondern müsste in den ha-mcp-Einstellungen als eigenes Verzeichnis freigegeben werden.
- **Kompilieren + OTA:** ha-mcp kann ESPHome nicht direkt bauen. Möglich ist `update.install` auf der „Firmware“-Update-Entity, die die ESPHome-Integration pro Gerät anlegt (baut im Device Builder und flasht OTA). Für den Demo-Reader 9999 gibt es keine solche Entity, er ist offline.
- Add-ons vorhanden: ESPHome Device Builder 2026.10.2, Samba, SSH, Studio Code Server. Die Samba-Freigabe ist von diesem PC aus derzeit nicht erreichbar.

## 2026-11-10 – HA-MCP-Integration installieren
> ja, mach schritt 1 und 2

`ha_manage_hacs(download, homeassistant-ai/ha-mcp)` abgesetzt. Antwort: „Anthropic Proxy: Invalid content from server“, danach scheiterten auch reine Lesezugriffe. Ob der Download durchlief, ist offen. Den Neustart habe ich deshalb nicht ausgelöst.

## 2026-11-10 – ESPHome-Dateien per ha-mcp nach HA kopiert
> ja, setz die option und kopier die dateien
> ich habe den eintrag hinzugefügt

- `allowed_dirs` am Eintrag „HA-MCP File & YAML Tools“ kann ha-mcp nicht selbst setzen (eigene Einträge sind gesperrt). Der User hat `esphome` in der UI freigegeben.
- Vergleich `esphome/` (Repo) mit `/config/esphome/` (HA): Nur `common/makerlink-reader-base.yaml` und `common/esp32c5-xiao-pn532-zigbee.yaml` unterschieden sich, und zwar nur in `project.version` (0.5.0 → 0.5.3). Die Größenunterschiede kamen von CRLF/LF. Beide Dateien überschrieben, die Größen stimmen jetzt mit dem Repo überein.
- Unverändert gelassen: die Gerätedateien in HA (`9997/9998/9999-makerlink.yaml`, `1720–1723-makerlink-printer-*.yaml`; sie heißen anders als die Beispiele im Repo), die `tocopy-*.yaml` (identisch) und `secrets.yaml`.
- `/config/esphome` ist in HA ein eigenes Git-Repo (`.git`).

## 2026-11-10 – Reader 9998 remote über Tailscale an HA
> ich bin gerade nicht vor-ort wo der home assistant steht. kann ich den reader (er liegt vor mir am tisch) irgendwie remote verbinden und testen?
> das funktioniert so nicht - ich habe den reader jetzt direkt ins TarantlHome gebracht
> ja, führ die tailscale befehle aus
> route ist freigegeben, leg den reader in HA an

- Der Weg über den Windows-Hotspot (`192.168.137.x`) des Gaming-Rechners klappte nicht. Am WLAN `TarantlHome` bekam der Reader `192.168.50.18` und war vom Laptop aus erreichbar (Ping, Port 6053).
- Brücke: Tailscale auf dem Laptop (Tailnet-Name `chrislaptop`), `tailscale set --advertise-routes=192.168.50.18/32`, Route vom User in der Adminkonsole freigegeben. Das HA-Tailscale-Add-on hat `accept_routes: true`.
- ESPHome-Eintrag per MCP angelegt (Host `192.168.50.18`) → „9998 DEMO MakerLink Supermini“ (`01M73F54KR5CZ8AP9WAFR2Y6JC`). Den Noise-Key hat HA selbst aus dem Device Builder geholt.
- Befunde am Reader: LCD (PCF8574 `0x27`) „Communication failed“, OLED `0x3C` ok, PN532 ok. Der Router weist ihn sporadisch ab („Authentication Failed“, „Probe Request Unsuccessful“).
- Nach dem Test: Route wieder entfernen (`tailscale set --advertise-routes=`) und den ESPHome-Eintrag auf die Adresse vor Ort umstellen bzw. löschen.

## 2026-11-10 – Ein Display pro Reader
> der reader ist da und in makerlink sichtbar (noch nicht eingerichtet oder zugeordnet)
> generell ist zu sagen > ein reader kann ein Oled oder ein LCD haben > beide codes sind am gerät, es ist aber immer nur eine display -art angeschlossen

**Entscheidung/Doku:** `display-dual.yaml` bleibt wie gebaut (beide Displays einkompiliert, eines angeschlossen). Im Kopfkommentar ergänzt: Das „Communication failed … marked FAILED“ des fehlenden Displays ist erwartet. Nach dem Umstecken muss der Reader neu gestartet werden.

## 2026-11-10 – HA friert ein (Watchdog-Neustarts)
> der home assistant scheint immer wieder offline zu sein (reboot? beschäftigt?) was stimmt hier nicht
> ich komme nicht auf das dashboard - kann es sein, dass wir was kaputt gemacht haben? kannst du über den mcp zugreifen und debuggen?

**Befund** (Supervisor- und Core-Log per MCP):
- Der Core-Event-Loop war mehrfach minutenlang blockiert: ~20:33–20:35:47, dann ab ~20:40. Der Supervisor-Watchdog verpasste API-Antworten (20:34, 20:42) und startete Core um 20:45 neu, die SQLite-DB wurde nicht sauber geschlossen. Nach dem Neustart um 20:56 hing HA erneut. Speicher war nicht das Problem (RPi4 8 GB, Add-ons ~2 GB), es gab auch keinen nativen Absturz (fault_log leer).
- Zeitlich passt das zu: Reader 9998 kommt online (ESPHome-Eintrag 20:32), Einheit 9998 angelegt, MakerLink-Panel im Browser offen.

**Ursache (sehr wahrscheinlich):** `makerlink/subscribe` baute bei **jedem** Dispatcher-Signal (jede Zustandsänderung der Reader-Entitäten) und bei **jedem** Geräte-/Entitäts-Registry-Event einen kompletten Snapshot. `discovery.find_readers` ging dabei jedes Mal über **alle** Geräte der Installation (über die veraltete Mapping-API `devices.values()`). Solange 9999 offline war, fiel das nicht auf. Mit dem Online-Reader und den Registry-Bursts beim Anlegen blockierte das den Pi. Nach jedem Neustart verbindet sich das offene Panel neu → Endlosschleife.

**Fix:**
- `ws_api.py`: Snapshots an das Panel gebündelt, höchstens einer pro Sekunde (`SUBSCRIBE_DEBOUNCE`).
- `discovery.py`: Es werden nur noch die Geräte der ESPHome-Einträge durchsucht (`async_entries_for_config_entry`) statt der ganzen Registry. Das behebt auch zwei Deprecation-Warnungen.

**Sofortmaßnahme bis zum Update:** MakerLink-Panel in allen Browsern schließen.

## 2026-11-10 – Fix ausgerollt
> ist gepusht, spiel das HACS-Update ein
> ja, akzeptieren

- Der Marketplace (HACS) verlangt pro Benutzer die Bestätigung seines Warnhinweises. Für den MCP-Benutzer nach Zustimmung des Users per `accept_warning` bestätigt.
- MakerLink `05cf13d` installiert, HA um 21:07 neu gestartet. Danach antwortet die API stabil in ~1,1 s. Die beiden Deprecation-Warnungen aus `discovery.py` tauchen nicht mehr auf. Einheit 9998 läuft: online, idle, Relais aus.
- Offen: die Deprecation `async_get_device` in `hub.py:286` (gilt noch bis HA 2027.8).

## 2026-11-10 – Erster Ende-zu-Ende-Test mit Reader 9998 (remote über Tailscale)
> Panel ist offen, Karte gescannt – schau nach
> Karte nochmal gescannt – schau nach

- 21:10:39 Scan → `checking` → `active`, MARS meldet Benutzer „Christoph“, Relais ein, Display `EIN:` / `Christoph`.
- 21:11:12 zweiter Scan → `stopping` → `idle` (Nachlaufzeit 0), Relais aus, `last_cost` 0, keine offenen Buchungen (`pending_bookings` 0). MARS hat den Stop also angenommen.
- HA blieb mit offenem Panel flüssig: Der Fix gegen das Einfrieren wirkt.
- Nebenbefund: Um 20:54 stand die Einheit kurz auf `admin`, weil das Relais während des HA-Hängers ohne Session einschaltete. Seither nicht wieder aufgetreten.

## 2026-11-10 – Rückmeldungen zum Test, hub.py-Fix, Plan für den Backend-Test
> Admin Modus > das war ICH manuell
> Ich hab ein OLED am 9998
> Mein zuhause Netzwerk ist nur "TarantlHome" ... ich weiss nicht warum das erste mal scheitert
> die schnittstelle im hub.py bitte machen
> lass uns mit diesem reader jetzt machineswitch_test.php testen - wie mache ich das?

- Der Admin-Modus um 20:54 war ein manuelles Einschalten, also korrektes Verhalten. Am 9998 hängt ein OLED, die LCD-Meldung ist damit erwartet.
- WLAN: Der Router zu Hause sendet `TarantlHome` (BSSID `B0:19:21:63:98:7E`) und `MakerIntern_001` (`BE:19:21:63:98:7E`), offensichtlich dasselbe Gerät. Der erste Verbindungsversuch scheitert jeweils mit „Authentication Failed“, der zweite gelingt. Ursache offen (vermutlich das Zusammenspiel von Router und ESP32), harmlos, weil ESPHome sofort erneut versucht.
- `hub.py`: `async_get_device(identifiers=...)` ersetzt. Gesucht wird jetzt nur unter den Geräten des eigenen Eintrags (`async_entries_for_config_entry`). Version 0.5.4.

## 2026-11-10 – Test machineswitch_test.php (Backend-Patch)
> URL ist umgestellt, Karte gescannt – schau nach
> B1-F4-0A-B1

**Teil A, über MakerLink und Reader 9998** (URL auf `machineswitch_test.php`): 21:18:30 Start → aktiv, Relais ein; 21:18:36 Stop → idle, Relais aus, Kosten 0, keine offenen Buchungen. Start (mit maskiertem `rfid`) und Stop funktionieren mit dem Patch.

**Teil B, per curl** (Karte `0xb1 0xf4 0xa 0xb1`, Unit 9998, Typ `machine`, also kostenlos):
| Aufruf | Antwort |
|---|---|
| `start` | `{"ok":true,"key":46407,"name":"Christoph","msg":"Aktiviert"}` |
| `stop key=46407 end=<jetzt-60>` | `{"ok":true,"msg":"Gestoppt","cost":0,"duration_s":0}`: Ende vor dem Start wird auf den Start geklemmt |
| derselbe `stop` nochmal | `{"ok":true,"msg":"Bereits gestoppt","already_stopped":true}`: keine Doppelbuchung |
| `stop key=1 unitid=9998` | `{"ok":false,"msg":"Session nicht gefunden (key=1 unitid=9998)"}` |

Alle Erwartungen aus `backend/README.md` sind erfüllt. Die Testdatei kann `machineswitch.php` ersetzen.

**Nebenbei:**
- Der MARS-Server war über den Tailscale-Exit-Node `arnolaptop` nicht erreichbar: Er steht im Makerspace hinter derselben öffentlichen IP, und der Weg zur eigenen öffentlichen IP klappt dort nicht. Exit-Node für den Test kurz abgeschaltet (mit Zustimmung des Users) und danach wiederhergestellt.
- Neue HA-Warnung „has an update listener and should use it for scheduling a reload“ (wird in HA 2026.12 zum Fehler). Behoben: Der Reconfigure-Flow nutzt jetzt `async_update_and_abort`, der Update-Listener `async_schedule_reload`. Kommt mit 0.5.4.

## 2026-11-10 – 0.5.4 ausgerollt
> ist gepusht, spiel das HACS-Update ein

MakerLink `10acc85` (0.5.4) per HACS installiert, HA um 21:30 neu gestartet. Danach erzeugt die Einheiten-Abfrage keine `async_get_device`-Warnung mehr, und `device_id` wird weiter aufgelöst. Ob die Warnung zum Update-Listener weg ist, zeigt sich erst beim nächsten „Neu konfigurieren“.

## 2026-11-10 – Backend-Patch produktiv
> ich habe alles bei mir erledigt :)

- Der User hat `machineswitch_test.php` über `machineswitch.php` kopiert, die Testdatei gelöscht und die URL in MakerLink zurückgestellt.
- Kontrolle: 21:32:21 Start → aktiv, Relais ein; 21:32:29 Stop → idle, Relais aus. Reader 9998 funktioniert gegen die produktive, gepatchte Datei.
- Die URL wurde um 21:28:53 umgestellt, also noch mit 0.5.3 (0.5.4 lief ab 21:30). Der Fix zum Update-Listener ist damit noch nicht im Betrieb bestätigt. Das geht erst beim nächsten „Neu konfigurieren“.

## 2026-11-10 – Phase 2 / Start Phase 1c (Offline-Fallback)
> wir hatten im ursprungsplan features für "phase 2"

Bestandsaufnahme: Aus dem ursprünglichen Phase-2-Umfang sind Interlock, Tür (doorLockCheck/logDoorAccess), Kaffeemaschine (Unit 6) und „Neustart beendet Nutzung“ bereits umgesetzt. Offen sind Statistiken, ein Diagnose-Dashboard und die Kiln-Spezialfälle (noch nicht definiert). Phase 1c (Offline-Fallback, MVP) fehlt komplett.

**Entscheidungen des Users:**
- Weiter mit **Phase 1c**.
- Umfang: **erst A** (MARS bzw. Internet weg, HA entscheidet), **dann B** (HA weg, Reader entscheidet).
- Offline-Start ohne Guthabenprüfung: **pro Einheit einstellbar** (Standard aus).
- Kartenliste: > Nur Unlimited User, wöchentlich > man kann sie von http://makeradmin.ddns.net:8080/crm/api/query.php?action=getRFIDWhitelist holen
- Türen: > Nur unlimited user > http://makeradmin.ddns.net:8080/crm/api/query.php?action=getRFIDWhitelist diese haben keine zeiteinschränkung

**Sicherheitsbefund:** `query.php?action=getRFIDWhitelist` antwortet **ohne Authentifizierung** über HTTP aus dem Internet und liefert Vor- und Nachname, Tarif und Karten-UID aller Unlimited-Mitglieder. Mit den UIDs lassen sich Karten klonen (MIFARE-UIDs sind kopierbar), die Tür lässt sich damit öffnen. Zudem ein DSGVO-Problem. Empfehlung: Endpunkt absichern oder entfernen. MakerLink soll die Liste nur über einen Endpunkt mit X-MARS-Key holen. (Nur eine Probe abgerufen, nichts gespeichert.)

## 2026-11-10 – Entscheidungen zur Whitelist, Umsetzung 1c-A
> Whitelist reicht einstweilen (wir implementieren das dann später mit schulung - merk dir das)
> Neue Aktion in machineswitch.php (Empfohlen)
> (Code von `getRFIDWhitelist` aus `query.php`: Plan-IDs 12,13,14,15,16,19,20,50,51,52,53, aktive Mitgliedschaft/Karte, nicht gelöscht)

**Umgesetzt (0.6.0), siehe PLAN.md Abschnitt 4:**
- Backend: `action=whitelist` (nur UIDs, X-MARS-Key, zusätzlich ohne blockierte Mitglieder), `action=offlineSession` (idempotent über Mitglied und Startzeit, Abrechnung über die gemeinsame Funktion `finishSession`), `logDoorAccess&time=`.
- Integration: `whitelist.py` (HA-frei), Sync beim Start und wöchentlich (stündlicher Retry nach Fehlern), Panel zeigt Whitelist-Stand und „Jetzt synchronisieren“. Neuer Schalter „Offline erlauben“ pro Einheit (Maschine Standard aus, Tür Standard an). Offline-Session im Controller, Nachbuchung über die bestehende Queue, Tür-Protokoll persistent gepuffert.
- 10 neue Tests, insgesamt 84 grün. PHP nicht lokal geprüft (kein PHP installiert), `php -l` steht im Test-Ablauf in `backend/README.md`.
- Die spätere Schulungsprüfung ist im Memory und in PLAN.md vermerkt.

## 2026-11-10 – Test der 0.6.0-Backend-Erweiterung (machineswitch_test.php)
> 1. ist erledigt

| Aufruf | Ergebnis |
|---|---|
| ohne `action` | 400 (Regression ok) |
| `whitelist` mit Key | `ok:true`, 91 Karten, Antwort nur mit `cards`/`count` (keine Namen), Testkarte enthalten |
| `whitelist` ohne Key | 401 |
| `offlineSession` (Unit 9998, `machine`, 3 min) | `Gestoppt`, `duration_s` 180 |
| dieselbe `offlineSession` nochmal | `Bereits gestoppt`, `already_stopped:true` |
| Ende vor Start | 400 `Parameter start/end ungueltig` |
| unbekannte Karte | 404 `Karte unbekannt` |
| `start` → `stop` → `stop` | `Aktiviert` (46410) → `Gestoppt` → `Bereits gestoppt` |
| `doorLockCheck` | `["True","Super User","Unlimited (0)"]` |

Nicht getestet: `logDoorAccess&time=` (hätte einen echten Eintrag in `access_log` geschrieben). Die Testdatei kann `machineswitch.php` ersetzen.

## 2026-11-10 – 0.6.0-Backend produktiv
> ich habe machineswitch_test gelöscht

Kontrolle: Die produktive `machineswitch.php` beantwortet `action=whitelist` (91 Karten), die Testdatei liefert 404. Damit ist das Backend für 0.6.0 live.

## 2026-11-10 – 0.6.0 in HA
> ja, spiel das HACS-Update ein

MakerLink `b5712b3` (0.6.0) installiert, HA um 22:44 neu gestartet. Die Whitelist wurde beim Start automatisch geholt (91 Karten, 22:45:56, kein Fehler). Beide Einheiten haben `offline_allowed: false` (Maschinen-Standard). Keine neuen Fehler von MakerLink im Log.

## 2026-11-10 – Offline-Test Teil 1: Start
> Datei, Schalter und URL stehen, Karte gescannt – schau nach

- 22:49:15 URL per „Neu konfigurieren“ auf `machineswitch_down.php` (simuliert 503). Die Einheit wurde einmal neu geladen, die Warnung zum Update-Listener kam **nicht** mehr: Fix aus 0.5.4 bestätigt.
- 22:50:06 Scan: `checking` → Backend 503 → Log „backend down (HTTP 503: Simulierter Ausfall), starting offline session“ → `active`, Relais ein (22:50:07), Display `EIN:` / `Offline-Modus`, `session_offline: true`.

## 2026-11-10 – Offline-Test Teil 2: Stop und Nachbuchung
> Karte nochmal gescannt, URL zurückgestellt – schau nach
> schau nach ob die Buchungen durch sind

- Zwei Offline-Nutzungen (22:50:06–22:50:29 und 22:50:51–22:51:04). Beim Stop jeweils 503 → in die Queue, Relais aus, Status `message` („Server offline / Wird nachgebucht“), „Offene Buchungen“ 2.
- 22:51:34 URL zurück auf `machineswitch.php` (Neuladen): Die 2 offenen Buchungen haben das Neuladen überstanden (persistent).
- Danach: `pending_bookings` 0, im Log kein „queued stop … dropped“. Beide Nachbuchungen wurden also vom Backend angenommen (ein Fehler hätte den Eintrag in der Queue gelassen, eine 4xx-Ablehnung hätte einen ERROR geloggt).
- Die direkte Gegenprobe in MARS (gleiche `offlineSession` nochmal → erwartet `already_stopped`) wurde vom Sicherheitsfilter blockiert, weil sie gegen die Produktiv-DB geht. Kann der User bei Bedarf selbst prüfen (machine_time, Unit 9998, Starts 1794347406 und 1794347451).
- Kosmetik: Die Log-Zeilen sagten bei Offline-Sessions „stop of session None“. Jetzt „offline <start>“. Version 0.6.1.
- Offline-Fallback 1c-A damit Ende zu Ende bestätigt.
