# MakerLink Reader-Firmware (ESPHome)

„Dumme“ Reader ohne Business-Logik. Ein Reader kann

- Karten lesen und als Event `esphome.makerlink_tag` mit der rohen `uid` (zB `F4-96-D2-28`) an Home Assistant schicken,
- zwei Displayzeilen anzeigen, die die Integration über die Text-Entitäten setzt,
- optional ein Relais schalten und 1–2 Sicherheitsschalter melden.

Ist Home Assistant nicht verbunden, zeigt das Display „HA offline“.

**Geräte-Varianten:** Die Datei für einen neuen Reader erzeugt das MakerLink-Panel unter **Reader hinzufügen** (mit freiem Gerätenamen). Die Vorlagen liegen auch hier als `tocopy-*.yaml`: kopieren, nach `<devicename>.yaml` umbenennen und `devicename` anpassen. Sie werden aus `custom_components/makerlink/readers.py` erzeugt (Test `tests/test_readers.py` prüft das), Änderungen gehören dorthin.

| Datei | Hardware |
|---|---|
| `tocopy-makerlink-esp32s3-supermini.yaml` | ESP32-S3 **Super Mini** (4 MB Flash) + PN532 (HSU) + **LCD 16x2 und/oder OLED 128x32** |
| `tocopy-makerlink-esp32s3-xiao.yaml` | **XIAO ESP32-S3** (8 MB Flash) + PN532 (HSU) + **LCD 16x2 und/oder OLED 128x32** |
| `tocopy-makerlink-xiao-esp32c5-zigbee.yaml` | Seeed XIAO ESP32-C5 + PN532 (HSU) + LCD und/oder OLED über **Zigbee**, Machbarkeitsstufe, siehe unten |
| `tocopy-makerlink-esp8266-rc522-lcd.yaml` | Bestands-Reader (30 Stück): D1 Mini + RC522 (SPI) + LCD 16x2. Hardware bleibt unverändert, wird nur neu geflasht |

**Bausteine** in `common/`:

| Datei | Inhalt |
|---|---|
| `makerlink-reader-base.yaml` | API, WLAN, Karten-Event, Text-Entitäten für die 2 Displayzeilen |
| `esp32s3-supermini.yaml` / `esp32s3-xiao.yaml` | Board, Pins und Flash-Größe je ESP32-S3-Variante |
| `esp32s3-pn532-hsu.yaml` | Gemeinsame ESP32-S3-Logik: PN532 über HSU, Relais, 2 Sicherheitsschalter, zwei I2C-Busse |
| `esp32c5-xiao-pn532-zigbee.yaml` | XIAO ESP32-C5 **mit Zigbee statt WLAN**: ersetzt auch die Basis, plus BOOT-Taste und LED, ein I2C-Bus |
| `display-dual.yaml` | LCD 16x2 (Adresse `display_i2c_address`, Standard 0x27) **und** OLED 128x32 (Adresse `oled_i2c_address`, Standard 0x3C, Roboto Mono 12 px, 2×16 Zeichen), beide immer einkompiliert |
| `display-lcd1602.yaml` | Nur LCD, für den Bestands-Reader (D1 Mini) |

## LCD und OLED ohne Neu-Flashen
Beide Treiber stecken in jeder neuen Firmware. Es zeigt, was angeschlossen ist; ein fehlendes Display bleibt dunkel (und schreibt eventuell Warnungen ins Log). Ein Wechsel LCD ↔ OLED braucht kein Flashen.

**Zwei getrennte I2C-Busse** (ESP32-S3), weil das LCD-Backpack mit **5 V** läuft und das OLED mit **3,3 V**, und weil das LCD höchstens 100 kHz verträgt (hier 50 kHz), das OLED aber 400 kHz bekommt:
- **OLED-Bus:** direkt an den ESP, 3,3 V.
- **LCD-Bus:** das Backpack bekommt 5 V. Dazwischen gehört ein bidirektionaler **Pegelwandler (BSS138-Modul)** für SDA/SCL, sonst liegen 5 V (Pull-ups des Backpacks) an den ESP-Pins, und der PCF8574 erkennt 3,3-V-High nicht sicher.
- **ESP32-C5:** hat nur **einen** Hardware-I2C-Bus. OLED und LCD teilen sich ihn mit 100 kHz. Das LCD hängt hinter dem Pegelwandler, das OLED direkt auf der 3,3-V-Seite.

PN532-Treiber (in `makerlink/`):
- `pn532_hsu.h`: unverändert aus der bestehenden Firmware. Nutzt `HardwareSerial` und braucht daher das Arduino-Framework.
- `pn532_uart.h`: dasselbe Protokoll über die ESPHome-`uart`-Komponente. Läuft auch mit ESP-IDF, was Zigbee voraussetzt. Die Puffer sind außerdem auf 32 Byte vergrößert, im Original konnte `begin()` über `resp[12]` hinausschreiben.

## PN532 über HSU, nicht I2C
Der ESP32 kommt mit dem Clock-Stretching des PN532 an I2C nicht zurecht. Der PN532 hängt deshalb per HSU (UART) an GPIO4 (RX ← PN532 TX) und GPIO5 (TX → PN532 RX).

ESPHome bietet für den PN532 nur SPI und I2C an, deshalb wird `pn532_hsu.h` per `esphome: includes:` eingebunden. Das Modul muss auf HSU stehen (Schalter bzw. Jumper I0 = 0, I1 = 0), und das Framework muss **Arduino** sein.

Der Reader fragt den PN532 jede Sekunde ab und meldet eine Karte **einmal pro Auflegen**. Bleibt die Karte liegen, folgt kein weiteres Event. Erst nach dem Abnehmen (2 leere Lesungen) wird sie wieder gemeldet. Die alte Firmware hat eine liegende Karte nach 5 s erneut gewertet und die Maschine dadurch wieder ausgeschaltet. Die Diagnose-Entität „PN532 bereit“ zeigt, ob der Leser initialisiert ist.

**Scan-Feedback:** Sobald eine Karte gelesen ist, zeigt das Display sofort „Karte erkannt / Bitte warten...“. Das bleibt, bis die Integration neue Texte schickt (Prüfung, Ein/Aus, Ablehnung), höchstens 4 s. Der Benutzer sieht so, dass er die Karte abnehmen kann. Beim Zigbee-Reader endet es vorerst immer nach 4 s.

## Pinbelegung ESP32-S3 Super Mini
| Funktion | Pin |
|---|---|
| PN532 HSU RX / TX | GPIO4 / GPIO5 |
| OLED-Bus SDA / SCL (3,3 V, 400 kHz) | GPIO8 / GPIO9 |
| LCD-Bus SDA / SCL (50 kHz, über Pegelwandler) | GPIO12 / GPIO13 |
| Relais | GPIO6 |
| Sicherheitsschalter 1 / 2 | GPIO10 / GPIO11 |

## Pinbelegung XIAO (ESP32-S3 und ESP32-C5)
Gleiche D-Pins auf beiden Boards, nur die GPIO-Nummern unterscheiden sich:

| XIAO-Pin | Funktion | ESP32-S3 | ESP32-C5 |
|---|---|---|---|
| D1 | Relais (Seeed Relay Add-on for XIAO) | GPIO2 | GPIO0 |
| D4 / SDA | OLED SDA (beim C5 auch LCD, 100 kHz) | GPIO5 | GPIO23 |
| D5 / SCL | OLED SCL (beim C5 auch LCD) | GPIO6 | GPIO24 |
| D0 | LCD SDA (nur S3, über Pegelwandler) | GPIO1 | – |
| D10 | LCD SCL (nur S3, über Pegelwandler) | GPIO9 | – |
| D6 / TX | ESP TX → PN532 RX | GPIO43 | GPIO11 |
| D7 / RX | ESP RX ← PN532 TX | GPIO44 | GPIO12 |
| D8 | Sicherheitsschalter 1 | GPIO7 | GPIO8 |
| D9 | Sicherheitsschalter 2 | GPIO8 | GPIO9 |
| BOOT (onboard) | > 5 s: Zigbee zurücksetzen und koppeln | – | GPIO28 |
| User-LED (onboard) | zeigt den Relais-Zustand | – | GPIO27 (active low) |

Die Strapping-Pins D2/D3 bleiben frei. Beim C5 sind D0/D10 ebenfalls frei (der LCD hängt am gemeinsamen Bus). Achtung: D1 ist beim S3 GPIO2, beim C5 GPIO0. GPIO0 ist beim S3 der BOOT-Pin. Das Log läuft über USB (`USB_SERIAL_JTAG`), deshalb ist der Standard-UART an D6/D7 frei für den PN532.

## XIAO ESP32-C5 über Zigbee (Machbarkeitsstufe)
Der C5 spricht **Zigbee statt WLAN**: Er hat keine ESPHome-API und kein OTA, Updates gehen nur per USB. Die Zigbee-Anbindung übernimmt die externe Komponente [luar123/zigbee_esphome](https://github.com/luar123/zigbee_esphome), festgelegt auf einen geprüften Commit. Die native ESPHome-Zigbee-Komponente kann auf ESP32 keine Switches und keine Texte. Die Zigbee-Komponente verlangt ESP-IDF, deshalb nutzt diese Variante `pn532_uart.h`.

**Was diese Stufe kann:**
- Kartenscan: als String-Attribut `"<n>:<UID>"` im herstellerspezifischen Cluster `0xFC00` (Endpoint 1, Attribut `0x0000`). Der Wert wird an den Coordinator gemeldet. Der Zähler `n` sorgt dafür, dass dieselbe Karte erneut als Scan zählt.
- Relais: Standard-On/Off-Cluster auf Endpoint 1, in ZHA als Schalter steuerbar. Die User-LED zeigt den Relais-Zustand.
- Sicherheitsschalter: Standard-Binary-Input-Cluster auf Endpoint 2 und 3.
- BOOT > 5 s halten: Der Reader verlässt das Zigbee-Netz und sucht ein neues zum Koppeln. Die LED blinkt dabei, bis er beigetreten ist (höchstens 3 Minuten).
- Display: Es zeigt lokale Texte. Solange kein Netz verbunden ist, steht dort „Zigbee koppeln“.

**Was diese Stufe noch nicht kann** (nächste Stufe, siehe docs/PLAN.md): Display-Texte von der Integration, Auswertung der Kartenscans durch MakerLink, ZHA-Quirk.

**Test mit ZHA:**
1. Per USB flashen (`esphome run …`).
2. In ZHA „Gerät hinzufügen“ starten. Ein neuer Reader sucht beim ersten Start selbst ein Netz, sonst BOOT > 5 s halten.
3. Erwartet werden ein Schalter (Relais) und zwei Binärsensoren (Sicherheitsschalter). Den Kartenscan siehst du ohne Quirk nur unter Gerät → „Zigbee-Gerät verwalten“ → Endpoint 1, Cluster `0xFC00`, Attribut `0x0000` lesen. Alternativ im HA-Log mit Debug für `zigpy`/`homeassistant.components.zha`.

## Einrichten
1. Den **Inhalt** dieses Ordners (`esphome/` im Repo) direkt in den ESPHome-Config-Ordner von Home Assistant kopieren (`/config/esphome/`). Die Gerätevarianten liegen dann direkt neben deinen Geräte-YAMLs, die Treiber in `makerlink/`. Der Include-Pfad `makerlink/pn532_*.h` gilt relativ zum Config-Ordner und setzt genau diese Struktur voraus:
   ```
   /config/esphome/
     secrets.yaml
     maker9998.yaml                         ← deine Geräte-YAML
     tocopy-makerlink-*.yaml                     ← Vorlagen aus dem Repo (optional)
     common/                                ← Bausteine
     makerlink/
       pn532_hsu.h
       pn532_uart.h
   ```
2. Pro Gerät eine YAML anlegen: im MakerLink-Panel **Reader hinzufügen** wählen und die erzeugte Datei in ESPHome als neues Gerät einfügen (oder eine `tocopy-*.yaml` kopieren und `devicename` ändern). Die LCD/OLED-Adressen lassen sich dort über die auskommentierten Substitutions `display_i2c_address` und `oled_i2c_address` ändern. Die Firmware enthält das OLED und lädt beim ersten Kompilieren den Font „Roboto Mono“ von Google Fonts und braucht dafür Internet.
3. `secrets.yaml` braucht diese Einträge: `wifi_ssid`, `wifi_password` (Hauptnetz), `wifi_ssid1`, `wifi_password1` (Fallback-Netz), `api_encryption_key` (`openssl rand -base64 32`). Der API-Schlüssel gilt auch für OTA-Uploads. API-Key und URL des MARS-Servers gehören **nicht** mehr auf den Reader.
4. Den Reader flashen und in HA über die ESPHome-Integration hinzufügen.
5. Im MakerLink-Panel unter **Neue Reader** auf **Einrichten** klicken. Display, Relais und Sicherheitsschalter erkennt MakerLink an den Entitätsnamen der Firmware („Display Zeile 1/2“, „Relais“, „Sicherheitsschalter 1/2“), dort wählst du nur Funktion, Name und Unit-ID.

## Hinweise
- **Sicherheitsschalter:** Sie werden gegen GND geschaltet. `off` bedeutet geschlossen. Unbekannt oder nicht verfügbar gilt als offen (fail-safe).
- **Türöffner:** Fällt HA mitten im Impuls aus, bleibt das Relais an. Für Türen ein Auto-Off als Absicherung ergänzen:
  ```yaml
  switch:
    - id: !extend relay
      on_turn_on:
        - delay: 10s
        - switch.turn_off: relay
  ```
- **Maschinen:** Das Relais bleibt bei einem HA-Neustart im aktuellen Zustand, damit ein laufender Druck nicht abbricht. Nach einem Reboot des Readers ist es aus. Die Integration erkennt das und schließt die Session.
- **Geprüft** mit ESPHome 2026.9.1: `esphome config` ist für alle fünf Varianten fehlerfrei. Gebaut habe ich:
  - Super Mini LCD: Flash 51 %, RAM 32 %
  - Super Mini OLED: Flash 52 %, RAM 32 %
  - XIAO-S3 OLED: Flash 24 %, RAM 33 %
  - XIAO-C5 Zigbee: Flash 18 %. Die einzige Compiler-Warnung stammt aus der externen Zigbee-Komponente.

  Auf echter Hardware ist keine Variante getestet.
- **Unter Windows** `esphome compile` aus PowerShell oder cmd starten, nicht aus Git Bash. Das ESP-IDF-Setup bricht dort mit „MSys/Mingw is not supported“ ab.
