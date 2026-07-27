# Clubee Standings Widget voor Twizzit

Deze mini-repo haalt automatisch de standings van je Clubee-pagina op en toont
ze als een nette tabel, klaar om in je Twizzit-website te embedden via een
`<iframe>`.

## Hoe het werkt
1. `clubee_standings_scraper.py` haalt de standings-data van Clubee op (geen
   login nodig) en schrijft ze naar `docs/standings.json`.
2. GitHub Actions (`.github/workflows/update-standings.yml`) draait dit script
   automatisch elke 3 uur en commit het resultaat.
3. GitHub Pages publiceert de map `docs/` als een publieke website.
4. `docs/index.html` is de widget zelf: ze haalt `standings.json` op en toont
   een tabel.
5. In Twizzit plaats je een `<iframe>` die naar die gepubliceerde
   `index.html`-URL verwijst.

## Installatie-stappen

### 1. Maak een GitHub-account (indien nog niet aanwezig)
Ga naar [github.com](https://github.com) en maak een gratis account.

### 2. Maak een nieuwe (publieke) repository
- Klik op **New repository**
- Geef een naam, bv. `clubee-standings-widget`
- Zet de zichtbaarheid op **Public** (nodig voor gratis GitHub Pages)
- Klik **Create repository**

### 3. Upload deze bestanden
Upload alle bestanden uit deze map (met behoud van de mapstructuur:
`.github/workflows/update-standings.yml`, `docs/index.html`,
`clubee_standings_scraper.py`) naar je nieuwe repository. Dat kan via:
- De GitHub-website (**Add file → Upload files**), of
- Git op je computer (`git add`, `git commit`, `git push`)

### 4. Pas league en season in de workflow aan
Open `.github/workflows/update-standings.yml` en vervang de waarden bij
`--league` en `--season` door de IDs van jouw eigen competitie/seizoen (die
vind je terug in de URL van je Clubee-standings-pagina, bv.
`.../leagues/18702/seasons/220`).

Gebruikt jouw club een andere prefix of pagina-slug dan `handballbelgium` /
`standings-371073v4`? Voeg dan ook `--prefix` en `--page` toe aan het commando.

### 5. Activeer GitHub Pages
- Ga naar **Settings → Pages** in je repository
- Bij **Source**: kies **Deploy from a branch**
- Bij **Branch**: kies `main` (of `master`) en map **`/docs`**
- Klik **Save**

Na een minuutje krijg je een URL zoals:
```
https://jouwgebruikersnaam.github.io/clubee-standings-widget/
```

### 6. Laat de workflow één keer manueel draaien
- Ga naar het tabblad **Actions** in je repository
- Klik op **Update Clubee Standings** → **Run workflow**
- Wacht tot die groen wordt (klaar) — dit genereert `docs/standings.json`

### 7. Test de widget
Open de GitHub Pages-URL in je browser. Je zou nu de standings-tabel moeten
zien.

### 8. Embed in Twizzit
Plaats in je Twizzit HTML/embed-blok:
```html
<iframe
  src="https://jouwgebruikersnaam.github.io/clubee-standings-widget/"
  style="width:100%; border:none; min-height:400px;"
  loading="lazy">
</iframe>
```

## Onderhoud
- De data ververst automatisch elke 3 uur via GitHub Actions.
- Wil je een andere frequentie? Pas de `cron`-regel aan in
  `.github/workflows/update-standings.yml`
  ([crontab.guru](https://crontab.guru/) helpt met de juiste cron-syntax).
- Breekt Clubee ooit hun paginastructuur? Dan faalt de GitHub Action (rood
  vinkje in het Actions-tabblad) en moet de parsing-logica in
  `clubee_standings_scraper.py` worden bijgewerkt.
