# Rankings voor de Apolloon-site

## Live stand

De actieve ranking staat op:
https://www.apolloon-spurs.be/Handbal-Live/ranking/standings.html?league=Heren1&group=1

De PHP-hosting vraagt bij paginaopening de actuele stand op bij Clubee en herhaalt dat elke minuut zolang het tabblad zichtbaar is. Er worden geen standen in JSON-bestanden opgeslagen. Bij een fout verschijnt een melding, geen ongemarkeerde oude stand.

De bestaande GitHub Pages-link `https://peterdelruegmail.github.io/Apolloon/standings.html` verwijst automatisch door. Alle queryparameters en het fragment blijven behouden, inclusief `league`, `title`, `group` en eventueel `season`. Bestaande iframes hoeven daardoor niet aangepast te worden.

## Broncode en onderhoud

- [live/](live/): actieve HTML-widget, PHP-endpoint, configuratie en tests.
- `live/config.php`: ploeg-ID's en standaardseizoen (220 voor 2026/2027). De live PHP-versie gebruikt dit bestand, niet de GitHub-variabele SEASON.
- `standings.html` en `../docs/standings.html`: doorverwijspagina voor bestaande links.
- `clubee_standings_scraper.py`: oude batchscraper, alleen nog voor handmatig gebruik.
- `../docs/standings*.json`: historische bestanden; worden niet meer gebruikt door de rankingpagina.
- `../.github/workflows/update-standings.yml`: maakt geen JSON-bestanden meer en meldt alleen de omschakeling naar live. De ploegworkflows en All.yml blijven beschikbaar voor oude aanroepen.

De bestaande Fastcron-rankingtaken zijn niet meer nodig en kunnen in Fastcron worden uitgeschakeld. Ze veranderen de gegevens niet meer.

## Hosting bijwerken

[Download het uploadpakket](https://github.com/peterdelruegmail/Apolloon/raw/refs/heads/main/ranking/Apolloon-ranking-live.zip). Upload de uitgepakte bestanden naar `/Handbal-Live/ranking/` op www.apolloon-spurs.be. Wijzigingen in GitHub worden niet vanzelf naar deze PHP-hosting geüpload.

## Rechtstreeks embedden

```html
<iframe
  src="https://www.apolloon-spurs.be/Handbal-Live/ranking/standings.html?league=Heren1&title=1ste%20Nationale&group=1"
  style="width:100%; border:none; min-height:400px;"
  loading="lazy">
</iframe>
```

`league` is een ploegnaam uit config.php; `title` bepaalt de titel; `group` selecteert een poule (1-based index, naam of `all`). Optioneel overschrijft `season` het standaardseizoen.

Het tijdstip “Opgehaald bij Clubee” is het moment van de geslaagde controle. De gegevens zijn zo actueel als Clubee ze publiceert.
