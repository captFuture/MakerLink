# MakerLink – Hinweise für Claude

Home-Assistant-Custom-Integration (HACS) für das MakerAustria-Maschinen- und Türzugangssystem (MARS).

## Dokumentation pflegen (Pflicht)
- Neue Anforderungen, Prompts und Entscheidungen des Users kommen **wörtlich** nach `docs/PROMPTS.md` (chronologisch, mit Datum).
- Architektur und offene Fragen stehen in `docs/PLAN.md`, der Backend-Vertrag in `docs/API.md`. Beides bei jeder relevanten Änderung aktualisieren.
- `docs/legacy/` enthält den Altbestand als Referenz für den Port (ESPHome-Logik, HW-Adapter, Beispielgerät, `machineswitch.php`). Nicht verändern.
- Keine Secrets ins Repo (Keys und Passwörter nur über `!secret` bzw. `config.inc.php`).

## Struktur
- `custom_components/makerlink/`: Integration. `const.py`, `mars_format.py`, `display.py` und `controller.py` importieren **kein** `homeassistant`, damit sie lokal ohne HA testbar sind. Der HA-Glue liegt in `hub.py`.
- `custom_components/makerlink/frontend/`: Seitenleisten-Panel (Vanilla-JS-Web-Component, kein Build-Schritt). Daten über `ws_api.py`.
- `esphome/`: Referenz-Firmware für „dumme“ Reader. Bausteine in `common/` (Basis, Hardware pro Board, Display-Pakete). PN532 immer über HSU: `esphome/makerlink/pn532_hsu.h` (Arduino) bzw. `pn532_uart.h` (ESP-IDF, Zigbee). Der Inhalt von `esphome/` wird 1:1 nach `/config/esphome/` kopiert, die Include-Pfade setzen das voraus. Prüfen mit `esphome config`/`compile` aus PowerShell, nicht Git Bash.
- `tests/`: pytest. Lokal läuft nur die Kernlogik, weil HA nicht unter Windows läuft.

## Konventionen
- UI-Texte auf Deutsch und Englisch (`translations/`). Displaytexte ASCII, maximal 16 Zeichen.
- **Vor jedem Push die Version erhöhen** (Wunsch des Users): `version` in `manifest.json` und dieselbe Nummer als `esphome: project: version` in `esphome/common/makerlink-reader-base.yaml` und `esp32c5-xiao-pn532-zigbee.yaml`. Patch für Fixes, Minor für neue Funktionen. Pro Push-Paket nur einmal erhöhen. Bei HACS mit Releases zusätzlich Tag `vX.Y.Z` und GitHub-Release.
