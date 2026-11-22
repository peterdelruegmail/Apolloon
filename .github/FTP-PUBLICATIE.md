# Handbal Live publiceren

De workflow **Publish Handbal Live** uploadt gewijzigde websitebestanden vanuit
programmas/handbal-live/ op main naar de FTP-map Handbal-Live.
Andere serverbestanden worden niet verwijderd. PHP en JavaScript worden eerst
op syntaxis gecontroleerd; uploads worden gecontroleerd voordat ze het bestaande
bestand vervangen.

## Eenmalig instellen

1. Open de repository **Settings → Secrets and variables → Actions**.
2. Kies **New repository secret**.
3. Gebruik als naam FTP_PASSWORD en als waarde het wachtwoord van de FTP-account.
   Zet het wachtwoord nooit in broncode, issues of chat.
4. Open **Actions → Publish Handbal Live → Run workflow**.
5. Kies main en geef voor een eerste beperkte test wedstrijdblad-parser.php op.
6. Controleer de groene workflowstatus en het wedstrijdblad op de website.

Server: ftp.guytnbe.webhosting.be, poort 21, gebruiker apolloon@guytnbe.
De server accepteerde tijdens de controle geen AUTH TLS. Gewone FTP verstuurt
inloggegevens en bestanden zonder versleuteling. Bij overstap naar een server
met expliciete FTPS kan FTP_PROTOCOL naar ftps; certificaatcontrole blijft aan.

## Daarna

Een push naar main met wijzigingen in de website-map start de publicatie.
Wijzigingen in andere programma’s starten deze workflow niet.
Bij een mislukte publicatie worden bij een volgende push ook wijzigingen sinds
de laatste geslaagde automatische publicatie meegenomen.

Handmatig kun je via **Run workflow** één of meerdere bestandsnamen opgeven,
gescheiden door komma’s, bijvoorbeeld index.html,api.php.
Er worden uitsluitend PHP-, HTML-, JavaScript-, CSS-bestanden en .htaccess
gepubliceerd. Verwijderingen in GitHub verwijderen niets op de hosting.

De eerste verbinding controleert dat in de doelmap de bestaande Handbal
Live-indexpagina staat. Pas de doelmap aan in de workflow als de FTP-account
bij het aanmelden een andere startmap gebruikt.
