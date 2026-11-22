# Live ranking op PHP-hosting

Deze versie vraagt bij elke paginaopening de actuele, door Clubee gepubliceerde stand op. Zolang de pagina zichtbaar blijft, herhaalt ze dit elke minuut. Er worden geen standen in JSON-bestanden opgeslagen. De API geeft alleen een dynamisch JSON-antwoord terug.

## Installatie

Upload `standings.html`, `api.php`, `clubee.php` en `config.php` samen naar een map `ranking` op webhosting met PHP 8.0+ en cURL. De server moet uitgaande HTTPS-verzoeken naar `www.clubee.com` toestaan. GitHub Pages kan de PHP-bestanden niet uitvoeren.

Open `https://JOUW-DOMEIN/ranking/standings.html?league=Heren1&title=1ste%20Nationale&group=1`. De bestaande parameters `league`, `title` en `group` blijven ondersteund. Optioneel kan `season=220` worden toegevoegd. Zonder die parameter wordt het seizoen uit `config.php` gebruikt. Controleer dat seizoen bij een seizoenswissel; deze configuratie staat op seizoen 220 (2026/2027).

Vervang pas na een geslaagde test de iframe-URL op jullie site door de URL op deze PHP-hosting. De bestaande GitHub Pages-versie blijft tot die omschakeling werken met de opgeslagen JSON-bestanden. Schakel Fastcron pas uit als alle iframes overgezet zijn.

## Gedrag

- `Opgehaald bij Clubee` is het tijdstip van de geslaagde aanvraag, geen garantie over het laatste wijzigingstijdstip bij Clubee.
- Bij een fout verschijnt een melding; een oude stand wordt niet als actueel getoond.
- Lege klassementen, meerdere poules en nulwaarden worden ondersteund.
- Geen authenticatiegegevens nodig: alleen openbare Clubee-pagina's worden gelezen.
- Er is geen willekeurige URL-proxy: alleen de ploegen in `config.php` zijn toegestaan.

Dit is een tweede versie naast de bestaande publicatie. De actieve site wordt pas omgeschakeld nadat de PHP-hosting en de nieuwe URL bekend zijn.
