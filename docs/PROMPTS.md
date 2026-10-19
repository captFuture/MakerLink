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
