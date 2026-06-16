# Edisio pour Home Assistant

Intégration **locale** (`local_push`) des modules domotiques Edisio via le dongle
USB 868 MHz, portée depuis le plugin Jeedom.

- Récepteurs pilotables : EMV-400 (volet / lumière), EDR-D4 (variateur 4 voies),
  EDR-B4, EMSD-300A, modules fil pilote / chaudière…
- Émetteurs (télécommandes, sondes température, contacts) découverts via un
  **mode inclusion** explicite, avec exclusion et bannissement.
- Protocole reverse-engineeré et **validé bit à bit** contre les trames Jeedom.

Voir le README pour l'installation et la liste complète des modèles.
