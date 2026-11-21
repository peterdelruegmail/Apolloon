# Live ranking op PHP-hosting

Deze versie vraagt alleen bij het openen of herladen van de pagina de actuele, door Clubee gepubliceerde stand op. Er is geen periodieke verversing. Ook terugkeren naar het tabblad veroorzaakt geen extra aanvraag. Er worden geen standen in JSON-bestanden opgeslagen; de API geeft een dynamisch JSON-antwoord terug.

## Installatie en updates

De actieve installatie staat onder `https://www.apolloon-spurs.be/Handbal-Live/ranking/`.

Upload `standings.html`, `api.php`, `clubee.php` en `config.php` samen naar webhosting met PHP 8.0+ en cURL. De server moet uitgaande HTTPS-verzoeken naar `www.clubee.com` toestaan. GitHub Pages kan de PHP-bestanden niet uitvoeren.

Bij de aanpassing van 21 november 2026 die de automatische verversing verwijdert, volstaat het om alleen `standings.html` opnieuw te uploaden. De PHP-bestanden zijn ongewijzigd.

Open `standings.html?league=Heren1&title=1ste%20Nationale&group=1`. De parameters `league`, `title` en `group` blijven ondersteund. Optioneel kan `season=220` worden toegevoegd. Zonder die parameter wordt het seizoen uit `config.php` gebruikt (momenteel 220 voor 2026/2027).

De oude GitHub Pages-link verwijst automatisch door met behoud van parameters. Fastcron-rankingtaken zijn niet meer nodig.

## Gedrag

- `Opgehaald bij Clubee` is het tijdstip van de aanvraag, geen garantie over het laatste wijzigingstijdstip bij Clubee.
- Bij een fout verschijnt een melding; een oude stand wordt niet als actueel getoond.
- Lege klassementen, meerdere poules en nulwaarden worden ondersteund.
- Geen authenticatiegegevens nodig: alleen openbare Clubee-pagina's worden gelezen.
- Alleen de ploegen in `config.php` zijn toegestaan.

Wijzigingen in GitHub moeten apart op de PHP-hosting worden geüpload.
