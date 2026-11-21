# Rankings voor de Apolloon-site

## Bestanden

- `clubee_standings_scraper.py`: haalt de klassementen van Clubee op.
- `standings.html`: broncode van de widget voor Twizzit.
- `../docs/standings.html`: gepubliceerde kopie van de widget.
- `../docs/standings*.json`: gepubliceerde klassementen per ploeg.
- `../.github/workflows/`: workflows per ploeg en de gedeelde update-workflow. Deze blijven op de verplichte GitHub Actions-locatie.

## Automatisch verversen

Fastcron start de bestaande GitHub-workflows. De namen en locaties van de workflows zijn behouden. De gedeelde workflow voert nu `ranking/clubee_standings_scraper.py` uit en kopieert `ranking/standings.html` naar `docs/standings.html`. Aanpassingen aan de widget worden dus gepubliceerd bij de volgende geslaagde rankingupdate. Bewerk de bron in `ranking`, niet de gegenereerde kopie onder `docs`.

De competitie-ID en bestandsnaam worden door de ploegworkflow meegegeven. Het seizoen komt uit de bestaande repositoryvariabele `SEASON`.

## Bestaande website-links

De openbare URL's en JSON-bestandsnamen blijven behouden. Je hoeft de iframes op jullie site niet aan te passen.

```html
<iframe
  src="https://peterdelruegmail.github.io/Apolloon/standings.html?league=Heren1&title=1ste%20Nationale&group=1"
  style="width:100%; border:none; min-height:400px;"
  loading="lazy">
</iframe>
```

Parameters: `league` bepaalt het bestand (`standingsHeren1.json`), `title` de titel en `group` optioneel de poule (1-based index, naam of `all`).

## Handmatig vanaf de repository-hoofdmap

```sh
python3 ranking/clubee_standings_scraper.py --league 18702 --season 220 --json docs/standingsHeren1.json
```

Pas seizoen en competitie aan waar nodig. Het script gebruikt alleen de Python-standaardbibliotheek.
