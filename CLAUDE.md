# MakerLink – Hinweise für Claude

Home-Assistant-Custom-Integration (HACS) für das MakerAustria-Maschinen- und Türzugangssystem (MARS).

## Dokumentation pflegen (Pflicht)
- Neue Anforderungen, Prompts und Entscheidungen des Users kommen **wörtlich** nach `docs/PROMPTS.md` (chronologisch, mit Datum).
- Architektur und offene Fragen stehen in `docs/PLAN.md`, der Backend-Vertrag in `docs/API.md`. Beides bei jeder relevanten Änderung aktualisieren.
- `docs/legacy/` enthält den Altbestand als Referenz für den Port (ESPHome-Logik, HW-Adapter, Beispielgerät, `machineswitch.php`). Nicht verändern.
- Keine Secrets ins Repo (Keys und Passwörter nur über `!secret` bzw. `config.inc.php`).

## Struktur
- `custom_components/makerlink/`: Integration. `const.py`, `mars_format.py`, `display.py` und `controller.py` importieren **kein** `homeassistant`, damit sie lokal ohne HA testbar sind. Der HA-Glue liegt in `hub.py`.
- `esphome/`: Referenz-Firmware für „dumme“ Reader.
- `tests/`: pytest. Lokal läuft nur die Kernlogik, weil HA nicht unter Windows läuft.

## Konventionen
- UI-Texte auf Deutsch und Englisch (`translations/`). Displaytexte ASCII, maximal 16 Zeichen.
- Release: `version` in `manifest.json` erhöhen, taggen (`vX.Y.Z`) und GitHub-Release anlegen, damit HACS das Update anbietet.
