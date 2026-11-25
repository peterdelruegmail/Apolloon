# Wekelijkse wedstrijdcontrole

De workflow vergelijkt iedere donderdag om 09:00 uur in Europe/Brussels de komende
Apolloon-wedstrijden uit het huidige openbare Clubee-seizoen met de openbare
Twizzit-wedstrijdexport. Zomer- en wintertijd volgen de ingestelde tijdzone.
GitHub kan geplande uitvoeringen later starten bij drukte.

Ontvanger: peter.delrue@gmail.com. De controle verandert niets in Clubee of Twizzit.

## E-mail instellen

Standaard is peter.delrue@gmail.com de Gmail-afzender en de ontvanger.

1. Maak voor het verzendaccount een Gmail-appwachtwoord:
   https://myaccount.google.com/apppasswords . Hiervoor is tweestapsverificatie nodig.
   Zie https://support.google.com/mail/answer/185833 .
2. Open https://github.com/peterdelruegmail/Apolloon/settings/secrets/actions/new
   en sla het appwachtwoord op als repository secret GMAIL_APP_PASSWORD.
3. Optioneel: zet de repository variable MAIL_FROM op een ander Gmail-afzenderadres.
   Het appwachtwoord moet dan bij dat account horen. De ontvanger blijft Peter.
4. Start een handmatige uitvoering met e-mail ingeschakeld en controleer de inbox.

Verzending loopt via smtp.gmail.com:587 met STARTTLS. Zet wachtwoorden nooit in
broncode of chat. Zonder GMAIL_APP_PASSWORD mislukt verzending met een duidelijke
melding. Een ontbrekende mailconfiguratie wordt nooit als verzonden gemeld.

De workflow staat in .github/workflows/check-match-calendar.yml. De planning werkt
vanaf de standaardbranch main. Pushes testen en maken een rapport zonder e-mail.
Via Actions > Wekelijkse wedstrijdcontrole > Run workflow kan een handmatige test
worden gestart. Alleen met het vakje voor e-mail aangevinkt wordt dan mail verstuurd.
Na succesvolle SMTP-overdracht moet ontvangst nog in de inbox worden gecontroleerd.

## Rapport en beperkingen

Elke uitvoering bewaart rapport.txt en rapport.html als workflowartifact
wedstrijdcontrole gedurende 30 dagen, ook wanneer ophalen of verzenden mislukt.
Ook zonder verschillen wordt bij een geplande uitvoering een rapport verstuurd.
Een onvolledige broncontrole krijgt een duidelijke foutmelding en een mislukte
workflowstatus; het gedeeltelijke rapport wordt wel per e-mail aangeboden als SMTP werkt.

De vergelijking gebruikt ploeg, thuis/uit, genormaliseerde tegenstander en datum.
Een unieke wedstrijd met een andere datum wordt als mogelijke verplaatsing gemeld.
Bij meerdere kandidaten wordt geen keuze gegokt. Twizzit-activiteiten zonder
koppeling kunnen ook tornooien, oefenwedstrijden of samengestelde activiteiten zijn.
De twee U12-ploegen kunnen bij gelijknamige tegenstanders handmatige controle vragen.

Locaties worden alleen vergeleken als beide bronnen er een vermelden; afwijkende
zaalnamen worden ter controle gemeld. Deze controle bewijst niet dat alle zalen
overeenkomen. Clubee geeft in de API een UTC-suffix, terwijl de zichtbare kalender
hetzelfde uur zonder omzetting toont. Het rapport volgt daarom het zichtbare
Clubee-uur. Twizzit UTC-tijden worden wel naar Europe/Brussels omgerekend.

De Clubee-competitielijst wordt elke keer opnieuw opgehaald. Wijzigingen in HTML,
de openbare kalenderlink, clubnamen of ploegnamen kunnen aanpassing vereisen.
Een seizoen zonder herkenbare Apolloon-wedstrijden wordt als fout gemeld.
Er worden geen Twizzit-beschrijvingen met interne opmerkingen in het rapport overgenomen.

## Lokaal controleren

Python 3.11 of nieuwer, zonder extra bibliotheken op Linux:

    python3 .github/scripts/test_match_calendar.py
    python3 .github/scripts/check_match_calendar.py --output /tmp/wedstrijdcontrole

Op Windows kan het Python-pakket tzdata nodig zijn voor Europe/Brussels.
De opdracht zonder --send-email verstuurt niets.
