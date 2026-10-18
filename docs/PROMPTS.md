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

Anhänge (alle unter [legacy/](legacy/), Vertrag zusätzlich in [API.md](API.md)): `mars-1720-bambulabp1prot.yaml`, `maker-reader-hw-esp8266.yaml`, `maker-reader-logic.yaml`, `machineswitch.php`.

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
