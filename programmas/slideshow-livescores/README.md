# Slideshow met livescores

Broncode van de recentste lokaal gevonden versie (v5).

## Starten vanuit Python op Windows

Installeer Python met Tcl/Tk-ondersteuning. Voer in deze map uit:

```powershell
py -m pip install -r requirements.txt
py slideshow.py
```

Maak een map `Images` met afbeeldingen, of kies je eigen afbeeldingsmap in het instellingenvenster. Pas competitie en datums aan voor gebruik. `settings.ini` bevat voorbeeldinstellingen; het persoonlijke Google Drive-pad is vervangen door `Images`.

Zie ook `LEESMIJ.txt` voor de uitgebreide bediening. Die uitleg is afkomstig uit het v4-pakket; de drie Python-bestanden en competitions.json komen uit v5.

## Zelf een Windows-exe bouwen

```powershell
py -m pip install pyinstaller
py -m PyInstaller --onefile --windowed --name Slideshow-livescores slideshow.py
```

Kopieer `competitions.json` en `settings.ini` naast de exe in de map `dist`. Plaats daar ook de afbeeldingsmap of kies je eigen map via de instellingen.
