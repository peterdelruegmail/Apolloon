# Clubee Standings Widget voor Twizzit


Deze mini-repo haalt automatisch de standings van je Clubee-pagina op en toont ze als een nette tabel, klaar om in je Twizzit-website te embedden via een `<iframe>`.

## Hoe het werkt
1. `clubee_standings_scraper.py` haalt de standings-data van Clubee op (geen login nodig) en schrijft ze naar `docs/standings.json`.
2. GitHub Actions (`.github/workflows/update-standings.yml`) draait dit script automatisch elk uur en commit het resultaat.
3. GitHub Pages publiceert de map `docs/` als een publieke website.
4. `docs/standings.html` is de widget zelf: deze haalt `standings.json` op en toont een tabel.
5. In Twizzit plaats je een `<iframe>` die naar die gepubliceerde `standings.html`-URL verwijst.  Dit gebeurt met de parameters league (vb. Heren1, dan wordt het bestand standingsHeren1.json gebruikt), title (komt boven de tabel te staan), group (is de index van de reeks indien meer dan 1 reeks op de originele Clubee pagina staan)

### 1. Pas league en name in de workflow aan (season zit in een omgevingsvariabele)
Roep `.github/workflows/update-standings.yml` met parameters LEAGUE en NAME door de IDs van jouw eigen competitie en de naam die je aan het json bestand wil geven (vb. Heren1, dan wordt het bestand standingsHeren1.json)

### 2. Embed in Twizzit
Plaats in je Twizzit HTML/embed-blok:
```html
<iframe
  src="https://peterdelruegmail.github.io/Apolloon/standings.html?league=Heren1&title=1ste Nationale&group=1"
  style="width:100%; border:none; min-height:400px;"
  loading="lazy">
</iframe>
```
met 
- league : die je hebt gebruikt om het json bestand aan te maken
- title : komt boven de rankingtabel te staan
- group (optioneel) : is de index van de rankingtabel indien er meerdere bestaan (1-based)

## Verversing
Aangezien de workflow-scheduler van github niet goed werkt, gebeurt dit nu in fastcron.com
