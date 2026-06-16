# Changelog

## 1.1.0
- **Import depuis Jeedom en deux temps, sans réappairage** :
  - Outil hors ligne `tools/jeedom_migration/edisio_migrate.py` qui convertit la
    sauvegarde Jeedom (`DB_backup.sql`) en fichier d'import `edisio_import.json`.
  - Nouvelle entrée *Configurer → Importer depuis Jeedom* (et service
    `edisio.import_jeedom`) qui **charge et valide** ce fichier pour recréer les
    équipements. Home Assistant ne lit pas la base Jeedom.
- L'outil reconstruit un appareil par groupe Edisio réellement utilisé, en
  reprenant le nom métier des commandes ; les émetteurs sont pré-enregistrés.
- Import idempotent (les doublons existants sont ignorés) et validé (les entrées
  invalides sont ignorées et signalées).
- Nouveau modèle `120C` « EDR-B4 (Volet/Store) » (platform cover). Les stores
  sont importés en switch Haut/Bas par défaut ; l'option `--stores-as-cover` de
  l'outil les expose en entités `cover`. Les deux types restent disponibles.

## 1.0.0
- Portage initial du plugin Edisio (Jeedom) vers Home Assistant.
- Liaison série asynchrone du dongle USB (PL2303 / FT232), reconnexion auto.
- Catalogue de 14 récepteurs avec trames exactes (EMV-400, EDR-D4, EDR-B4, EMSD-300A, fil pilote…).
- Plateformes : light (+ variateur), switch, cover, select, sensor, binary_sensor, event.
- Mode inclusion / exclusion / bannissement des émetteurs, persistance dédiée.
- Services : inclusion_mode, exclude, learn, send_raw.
