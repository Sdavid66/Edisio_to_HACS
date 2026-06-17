# Changelog

## 1.2.2
- **Logo de l'intégration** : icône Edisio embarquée dans `custom_components/edisio/brand/`
  (`icon.png` 256, `icon@2x.png` 512, `logo.png`), fond transparent. Depuis Home
  Assistant 2026.3, ces images locales sont prioritaires et affichées directement
  dans l'UI — plus besoin du dépôt `home-assistant/brands`.

## 1.2.1
- **Correctif** : import incorrect `homeassistant.helpers.device_info` (module
  inexistant) qui empêchait la configuration de l'entrée
  (`ModuleNotFoundError: Platform edisio.switch not found` puis
  `No module named 'homeassistant.helpers.device_info'`). `DeviceInfo` est
  désormais importé depuis `homeassistant.helpers.device_registry`
  (dans `entity.py` et `switch.py`).

## 1.2.0
- **Import par téléversement de fichier** : l'étape *Importer depuis Jeedom*
  permet désormais de **choisir le fichier `edisio_import.json` directement
  depuis l'ordinateur** (sélecteur de fichier du navigateur), pratique quand HA
  tourne sur une machine distante (Proxmox, NAS…). Le chemin sur le serveur reste
  disponible en alternative. Ajoute la dépendance `file_upload`.

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
