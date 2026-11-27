# Serverweergave van index en ticker

De bestaande adressen index.html en ticker.html blijven bestaan. PHP haalt de competities en scores op, valideert de invoer, kiest de periode, sorteert en bouwt de wedstrijdweergave. De browser ontvangt alleen de benodigde HTML, formulierwaarden en status. index.js verzorgt de bediening en het verversen; ticker.js verzorgt daarnaast de animatie.

Upload de volledige gewijzigde set samen: index.html, index.js, ticker.html, ticker.js, view.php, server-view.php, competition-data.php, competition-menu.php, club-ticker-data.php, api.php, competitions.php en club-ticker.php. Behoud de bestaande overige bestanden. De bestaande JSON-adressen blijven beschikbaar voor andere pagina's en koppelingen. De productie-workflow publiceert pas na samenvoegen met main.

Vereisten blijven PHP 8 met cURL en DOM/XML, uitgaande HTTPS en een schrijfbare tijdelijke map. De cache blijft buiten de webmap. De server geeft geen Clubee-parserdiagnostiek meer door aan bezoekers.

F12 blijft de ontvangen HTML, CSS, kleine browserscripts en netwerkantwoorden tonen. PHP-broncode blijft op de server wanneer PHP correct is geconfigureerd. Dit voorkomt geen kopie van de zichtbare vormgeving of hergebruik van openbare wedstrijdgegevens. Een openbare GitHub-repository maakt ook de PHP-broncode buiten de website zichtbaar; repositorytoegang staat los van deze wijziging.

Controleer na publicatie het competitieformulier, vorige/deze/volgende week, Apolloon bovenaan, automatisch verversen, score- en wedstrijdbladlinks, tickerparameters start/end/speed en Pauzeren. Controleer ook foutmeldingen en herstel wanneer Clubee niet bereikbaar is.

Regressiecontroles: voer vanuit de repository php .github/tests/test_handbal_views.php en node .github/tests/test_handbal_browser.cjs uit.

Kies in het competitieveld **Alle matchen van Apolloon** om de clubkalender van de ticker te tonen, met alle ploegen, thuis en uit. De gekozen periode en weekknoppen blijven werken. De deelbare URL gebruikt `source=apolloon`. Deze keuze blijft beschikbaar als het competitiemenu niet kan worden opgehaald. De lijst deelt de cache en live-scorecontroles met de ticker; afgelastingen en mislukte scorecontroles worden ook in de wedstrijdkaarten vermeld.

Zonder `source` in de URL wordt standaard **Alle matchen van Apolloon** geladen. Een expliciete competitiekeuze in de URL blijft behouden.
