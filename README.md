# Exact Verkoopkansen Tool

Automatisch verkoopkansen aanmaken in Exact Online via een lokale webapplicatie.

## Wat doet het?

De tool opent Exact Online in een browser, loopt door de suspects-lijst en maakt voor elk bedrijf automatisch een verkoopkans aan met:
- Ingestelde titel
- Fase: VB (Voorbereid)
- Sluitingsdatum
- Notitie met bedrijfsinfo (wat doet het, grootte, DMU, kans)

---

## Installatie & gebruik

### Mac

1. Download of clone deze repo
2. Zorg dat Python 3 en de packages geïnstalleerd zijn:
   ```bash
   pip3 install flask playwright
   playwright install chromium
   ```
3. Dubbelklik `ExactTool.app` — of start handmatig:
   ```bash
   python3 app.py
   ```
4. De browser opent automatisch op `http://127.0.0.1:5050`

### Windows

1. Download of clone deze repo
2. Dubbelklik **`SETUP.bat`** (eenmalig — installeert Python + alles automatisch)
3. Dubbelklik daarna **`START.bat`** om de app te starten

---

## Bedrijvenlijst aanpassen

Vervang `bedrijven_data.json` via de knop in de app, of stuur een nieuwe lijst naar Claude Code met:

> *"Maak hiervoor een nieuwe bedrijven_data.json"*

---

## Bestandsoverzicht

| Bestand | Omschrijving |
|---|---|
| `app.py` | Hoofdapplicatie (Flask webserver + Playwright automatisering) |
| `bedrijven_data.json` | Bedrijfsinfo voor de notities |
| `SETUP.bat` | Windows: eenmalige installatie |
| `START.bat` | Windows: app starten |
| `BUILD_EXE.bat` | Windows: bouw een standalone `.exe` |
