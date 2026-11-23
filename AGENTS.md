# Afspraken voor Codex in Apolloon

Deze instructies gelden voor de hele repository. De gebruiker geeft hiermee toestemming om onderstaande stappen na een afgeronde codewijziging uit te voeren, inclusief pushen en releases publiceren.

## Na elke afgeronde codewijziging

1. Maak vóór het wijzigen een eigen branch met een duidelijke naam zoals `codex/korte-beschrijving`. Gebruik voor een vervolg binnen dezelfde taak de bestaande taakbranch.
2. Controleer de wijzigingen met passende controles en beschikbare relevante tests. Controleer de diff op fouten en ongewenste bestanden. Bewaar bestaande wijzigingen van de gebruiker en commit alleen bestanden die bij de taak horen.
3. Commit de afgeronde wijziging met een duidelijke commitboodschap en push de taakbranch naar `peterdelruegmail/Apolloon`. Gebruik normale pushes. Los conflicten zorgvuldig op en behoud werk van anderen.
4. Geef de gebruiker de branchnaam, commit, GitHub-link en een korte beschrijving van de controles en eventuele beperkingen. Voeg de branch pas samen met `main` wanneer de gebruiker daarom vraagt.

## Windows-programma's en releases

Wanneer een wijziging een Windows-programma zoals `programmas/slideshow-livescores` raakt:

- Werk de benodigde bibliotheken in `requirements.txt` bij.
- Bouw de bijgewerkte `.exe` met de bestaande bouwprocedure. Controleer eerst welke procedure en instellingen in de repository worden gebruikt.
- Test de gewijzigde functionaliteit en controleer dat de build slaagt. Vermeld wanneer de uiteindelijke executable of werking op een andere pc nog niet getest is.
- Commit en push alle bijbehorende broncode en noodzakelijke bouwbestanden naar de taakbranch voordat de release wordt gemaakt.
- Publiceer automatisch een nieuwe GitHub-release met een unieke opvolgende versietag volgens de bestaande naamgeving, bijvoorbeeld `slideshow-v7`. Laat de tag verwijzen naar de commit met de bijbehorende broncode op de taakbranch, zodat de automatische broncodedownload bij de executable past.
- Voeg de bijgewerkte executable als releasebestand toe. Voeg aanvullende bestanden toe wanneer die nodig zijn voor installatie of gebruik. Publiceer voorbeeldinstellingen zonder persoonlijke paden of gegevens.
- Beschrijf in de release wat is gewijzigd, hoe gebruikers bijwerken en welke controles zijn uitgevoerd. Geef onopgeloste problemen en niet uitgevoerde controles duidelijk aan. Markeer een release met bekende blokkerende fouten als prerelease.
- Controleer na publicatie dat de release en bestanden op GitHub zichtbaar zijn en geef de downloadlink aan de gebruiker.

Als toegang, bouwomgeving of een andere concrete afhankelijkheid een stap verhindert, voltooi de overige uitvoerbare stappen en meld precies wat nog ontbreekt. Claim uitsluitend stappen als voltooid wanneer het resultaat is gecontroleerd.
