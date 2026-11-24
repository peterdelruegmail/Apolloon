# Slideshow met livescores

Onder **Wedstrijden en periode → Wedstrijden van** kies je tussen:

- **Alle matchen van Apolloon Spurs**: heren, dames, jeugd en bekers, thuis en uit.
- **Een bepaalde reeks** uit de competitielijst: alle wedstrijden van die reeks.

Voor beide keuzes geldt het ingestelde datumbereik, inclusief de einddatum.
De keuze wordt opgeslagen. Bestaande instellingen voor een reeks blijven werken.

De clubkeuze doorzoekt de openbare Clubee-competities van het standaardseizoen.
Dubbele wedstrijdnummers verschijnen één keer. De kalender wordt vijf minuten
bewaard; scores worden bij elke ingestelde controle opnieuw opgehaald.
Een mislukte reekscontrole geeft een foutmelding, zodat een onvolledige kalender
niet ongemerkt als volledig wordt getoond. De eerste clubcontrole kan langer duren.

## Starten vanuit Python op Windows

Installeer Python met Tcl/Tk-ondersteuning. Voer in deze map uit:

```powershell
py -m pip install -r requirements.txt
py slideshow.py
```

Maak een map `Images` met afbeeldingen, of kies je eigen afbeeldingsmap in het instellingenvenster. Pas competitie en datums aan voor gebruik. `settings.ini` bevat voorbeeldinstellingen; het persoonlijke Google Drive-pad is vervangen door `Images`.

Zie ook `LEESMIJ.txt` voor de uitgebreide bediening. De aanvullende clubkeuze staat hierboven beschreven.

## Zelf een Windows-exe bouwen

```powershell
py -m pip install pyinstaller
py -m PyInstaller --onefile --windowed --name Slideshow-livescores slideshow.py
```

Kopieer `competitions.json` en `settings.ini` naast de exe in de map `dist`. Plaats daar ook de afbeeldingsmap of kies je eigen map via de instellingen.
