# MakerLink Reader-Firmware (ESPHome)

„Dumme“ Reader ohne Business-Logik. Ein Reader kann

- Karten lesen und als Event `esphome.makerlink_tag` mit `uid` an Home Assistant schicken,
- zwei Displayzeilen anzeigen, die die Integration über die Text-Entitäten setzt,
- optional ein Relais schalten und 1–2 Sicherheitsschalter melden.

Ist Home Assistant nicht verbunden, zeigt das Display „HA offline“.

| Datei | Hardware |
|---|---|
| `makerlink-reader-esp32s3-pn532.yaml` | ESP32-S3 + PN532 (I2C), Relais, 2 Schalter |
| `makerlink-reader-esp8266-rc522.yaml` | Bestands-Reader: D1 Mini + RC522 (SPI), Relais |
| `common/makerlink-reader-base.yaml` | Gemeinsame Basis (API, Display, Event) |

## Einrichten
1. Die Dateien in den ESPHome-Ordner kopieren und pro Gerät eine kleine YAML anlegen:
   ```yaml
   substitutions:
     devicename: maker1720
     friendly_name: Reader P1P Rot
   packages:
     reader: !include makerlink-reader-esp32s3-pn532.yaml
   ```
2. `secrets.yaml` braucht diese Einträge: `wifi_ssid`, `wifi_password`, `api_encryption_key` und `ota_password`. API-Key und URL des Servers gehören **nicht** mehr auf den Reader.
3. Den Reader flashen und in HA über die ESPHome-Integration hinzufügen.
4. In den ESPHome-Geräteoptionen „Erlauben, dass das Gerät Home Assistant-Aktionen ausführt“ aktivieren. Das ist für Events nicht zwingend nötig, aber für spätere Funktionen wie den Offline-Sync.
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
