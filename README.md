# MakerLink

Home Assistant Custom Integration.

## Installation (HACS)

1. HACS → ⋮ → **Benutzerdefinierte Repositories**
2. URL dieses Repositories eintragen, Kategorie **Integration**
3. **MakerLink** installieren, Home Assistant neu starten
4. Einstellungen → Geräte & Dienste → **Integration hinzufügen** → MakerLink

## Updates

HACS zeigt neue Versionen an, sobald im Repository ein GitHub-Release existiert.

Release erstellen:
1. `version` in `custom_components/makerlink/manifest.json` erhöhen
2. Committen, Tag setzen (`git tag v0.1.1 && git push --tags`)
3. Auf GitHub ein Release zu diesem Tag veröffentlichen

## Manuelle Installation

Ordner `custom_components/makerlink` nach `<config>/custom_components/` kopieren und neu starten.
