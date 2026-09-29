# Exact Verkoopkansen Tool

Automatisch verkoopkansen aanmaken in Exact Online via een lokale webapplicatie.

## Wat doet het?

1. Klik **🌐 Open Exact**. Er opent een browser.
2. Log in en **kies zelf de administratie** (en eventueel direct de relatielijst die je wilt verwerken).
3. Klik **▶ START**. De tool opent 1 tot 10 vensters tegelijk (standaard 8) en maakt voor elk bedrijf een verkoopkans aan met:
   - de ingestelde titel
   - fase VB (Voorbereid)
   - de sluitingsdatum
   - een notitie met tijdstempel en bedrijfsinfo (wat doet het, grootte, DMU, kans)
4. Na elke klik op Opslaan kijkt de tool of Exact echt heeft opgeslagen. Bij een foutmelding wordt die in de log gezet en komt er een screenshot in `logs/`.

Met 8 vensters duren 50 klanten ongeveer 1 à 2 minuten.

### Alles wordt bewaard
- `logs/<datum_tijd>.log`: volledige log van elke run
- `logs/fout_*.png` / `.html`: screenshot en pagina van elk mislukt bedrijf
- `verwerkt.json`: welke bedrijven al een verkoopkans hebben (per titel). Klik je nog een keer op START, dan worden alleen de nog niet (of mislukt) verwerkte bedrijven gedaan.

Op de Mac-app staan deze bestanden in `~/Documents/ExactTool`.

---

## Installatie & gebruik

### Mac (als app)

1. Download of clone deze repo.
2. Dubbelklik **`INSTALLEER_MAC.command`**. Krijg je een beveiligingsmelding, klik dan met rechts → *Open*.
3. Het script bouwt **ExactTool.app** en zet die in *Programma's*. Sleep de app naar je Dock.

Zonder app starten kan ook: dubbelklik `START.command`.

### Windows

1. Download of clone deze repo.
2. Dubbelklik **`SETUP.bat`** (één keer: installeert Python en alles wat nodig is).
3. Dubbelklik daarna **`START.bat`** om de app te starten.

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
| `INSTALLEER_MAC.command` | Mac: bouwt en installeert ExactTool.app |
| `START.command` | Mac: app starten zonder te bouwen |
| `SETUP.bat` | Windows: eenmalige installatie |
| `START.bat` | Windows: app starten |
| `BUILD_EXE.bat` | Windows: bouw een standalone `.exe` |
