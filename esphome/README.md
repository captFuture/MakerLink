# MakerLink Reader-Firmware (ESPHome)

„Dumme“ Reader ohne Business-Logik. Ein Reader kann

- Karten lesen und als Event `esphome.makerlink_tag` mit der rohen `uid` (zB `F4-96-D2-28`) an Home Assistant schicken,
- zwei Displayzeilen anzeigen, die die Integration über die Text-Entitäten setzt,
- optional ein Relais schalten und 1–2 Sicherheitsschalter melden.

Ist Home Assistant nicht verbunden, zeigt das Display „HA offline“.

| Datei | Hardware |
|---|---|
**Geräte-Varianten** (diese Datei im Geräte-YAML einbinden):

| Datei | Hardware |
|---|---|
| `makerlink-reader-esp32s3-pn532.yaml` | ESP32-S3 Super Mini + PN532 (HSU) + **LCD 16x2** (PCF8574) |
| `makerlink-reader-esp32s3-pn532-oled.yaml` | ESP32-S3 Super Mini + PN532 (HSU) + **0,91" OLED 128x32** (SSD1306, I2C) |
| `makerlink-reader-esp8266-rc522.yaml` | Bestands-Reader: D1 Mini + RC522 (SPI) + LCD 16x2 |

**Bausteine** in `common/`:

| Datei | Inhalt |
|---|---|
| `makerlink-reader-base.yaml` | API, WLAN, Karten-Event, Text-Entitäten für die 2 Displayzeilen |
| `esp32s3-supermini-pn532-hsu.yaml` | Board, PN532 über HSU, Relais, 2 Sicherheitsschalter |
| `display-lcd1602.yaml` | LCD 16x2 (Adresse `display_i2c_address`, Standard 0x27) |
| `display-ssd1306-128x32.yaml` | OLED 128x32 (Adresse `oled_i2c_address`, Standard 0x3C), Roboto Mono 12 px, 2×16 Zeichen |

`pn532_hsu.h` ist der PN532-HSU-Treiber, unverändert aus der bestehenden Firmware.

## PN532 über HSU, nicht I2C
Der ESP32 kommt mit dem Clock-Stretching des PN532 an I2C nicht zurecht. Der PN532 hängt deshalb per HSU (UART) an GPIO4 (RX ← PN532 TX) und GPIO5 (TX → PN532 RX).

ESPHome bietet für den PN532 nur SPI und I2C an, deshalb wird `pn532_hsu.h` per `esphome: includes:` eingebunden. Das Modul muss auf HSU stehen (Schalter bzw. Jumper I0 = 0, I1 = 0), und das Framework muss **Arduino** sein.

Der Reader fragt den PN532 jede Sekunde ab und meldet eine Karte **einmal pro Auflegen**. Bleibt die Karte liegen, folgt kein weiteres Event. Erst nach dem Abnehmen (2 leere Lesungen) wird sie wieder gemeldet. Die alte Firmware hat eine liegende Karte nach 5 s erneut gewertet und die Maschine dadurch wieder ausgeschaltet. Die Diagnose-Entität „PN532 bereit“ zeigt, ob der Leser initialisiert ist.

## Pinbelegung ESP32-S3 Super Mini
| Funktion | Pin |
|---|---|
| PN532 HSU RX / TX | GPIO4 / GPIO5 |
| I2C SDA / SCL (LCD 50 kHz, OLED 400 kHz) | GPIO8 / GPIO9 |
| Relais | GPIO6 |
| Sicherheitsschalter 1 / 2 | GPIO10 / GPIO11 |

## Einrichten
1. Den Inhalt dieses Ordners in den ESPHome-Config-Ordner nach **`makerlink/`** kopieren. Der Include-Pfad `makerlink/pn532_hsu.h` setzt genau diesen Ordnernamen voraus:
   ```
   esphome/
     secrets.yaml
     maker9998.yaml
     makerlink/
       pn532_hsu.h
       makerlink-reader-esp32s3-pn532.yaml
       makerlink-reader-esp32s3-pn532-oled.yaml
       common/…
   ```
2. Pro Gerät eine kleine YAML anlegen:
   ```yaml
   substitutions:
     devicename: maker9998
     friendly_name: Reader Demo
     # display_i2c_address: "0x3F"   # LCD, Standard 0x27
     # oled_i2c_address: "0x3D"      # OLED, Standard 0x3C
   packages:
     reader: !include makerlink/makerlink-reader-esp32s3-pn532.yaml       # LCD
     # reader: !include makerlink/makerlink-reader-esp32s3-pn532-oled.yaml  # OLED
   ```
   Die OLED-Variante lädt beim ersten Kompilieren den Font „Roboto Mono“ von Google Fonts und braucht dafür Internet.
3. `secrets.yaml` braucht diese Einträge: `wifi_ssid`, `wifi_password`, `api_encryption_key` (`openssl rand -base64 32`) und `ota_password`. API-Key und URL des MARS-Servers gehören **nicht** mehr auf den Reader.
4. Den Reader flashen und in HA über die ESPHome-Integration hinzufügen.
5. In der MakerLink-Integration unter **Maschine oder Tür hinzufügen** das Reader-Gerät, die Text-Entitäten, das Schaltziel (Relais oder Steckdose) und die Sicherheitsschalter auswählen.

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
- **Geprüft** mit ESPHome 2026.9.1: `esphome config` ist für alle drei Varianten fehlerfrei. Beide ESP32-S3-Varianten kompilieren ohne Warnungen (LCD: Flash 51 %, RAM 32 %; OLED: Flash 52 %, RAM 32 %). Auf echter Hardware sind sie noch nicht getestet.
- **Unter Windows** `esphome compile` aus PowerShell oder cmd starten, nicht aus Git Bash. Das ESP-IDF-Setup bricht dort mit „MSys/Mingw is not supported“ ab.
