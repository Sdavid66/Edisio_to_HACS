# Changelog

## 1.5.0
- **Découverte des émetteurs par cartes (comme ZHA/Z-Wave)** : en mode inclusion,
  appuyer sur un bouton/télécommande Edisio inconnu fait apparaître une **carte
  « Émetteur Edisio détecté »** sur **Paramètres → Appareils et services**. Un clic
  sur **Configurer** lie le module et crée ses entités (bouton `event`, état, batterie,
  température) rattachées à la passerelle. Fini l'ajout silencieux : on voit et on
  valide chaque appareil.
- Les cartes n'apparaissent que **pendant le mode inclusion** (garde-fou anti-voisin),
  et sont dédupliquées (une seule carte par identifiant, même en cas d'appuis répétés).
- Nouvelle méthode `EdisioGateway.async_accept_emitter` + étapes de flux
  `integration_discovery` / `discovery_confirm`.
- `hacs.json` : version minimale de Home Assistant portée à **2026.3.0** (requise
  par les icônes de marque locales `brand/`, déjà utilisées depuis la v1.2.2).

## 1.4.0
- **Vue « réseau » type ZHA/Z-Wave** : la passerelle est désormais un véritable
  appareil **hub** (fabricant, modèle = dongle détecté, version), et tous les
  modules — récepteurs **et** émetteurs découverts — y sont rattachés via
  `via_device` (topologie du réseau visible dans la page de l'intégration, avec
  le nombre d'appareils et d'entités).
- **Entités de diagnostic sur la passerelle** :
  - `binary_sensor` *Connectée* (état du dongle, classe connectivity) ;
  - capteurs *Port*, *Émetteurs appairés*, *Trames reçues*, *Dernière trame*.
- **Télécharger les diagnostics** : export du réseau (passerelle, émetteurs
  appairés/bannis, récepteurs) depuis la page de l'intégration.
- Les émetteurs découverts sont maintenant **regroupés dans un appareil** dédié
  (au lieu d'entités isolées).

## 1.3.0
- **Changement du port USB sans tout refaire** : nouvelle action **Reconfigurer**
  (menu ⋮ de l'intégration → *Reconfigurer*) qui permet de sélectionner un autre
  port série du dongle. Les modules déjà configurés sont conservés ; l'intégration
  est rechargée automatiquement. Plus besoin de supprimer puis recréer l'entrée
  quand le dongle change de port (`/dev/ttyUSB0` → `ttyUSB1`, déplacement de prise…).

## 1.2.5
- **Dépendance série** : remplacement de `pyserial-asyncio` (non maintenu) par
  `pyserial-asyncio-fast`, conformément à l'avertissement Home Assistant
  (« should be replaced by pyserial-asyncio-fast … will stop working in
  Home Assistant 2026.7 »). L'import devient `serial_asyncio_fast` (API
  identique, aliasée), aucun changement de comportement.

## 1.2.4
- **Correctif** : suppression d'un appel bloquant (`models.json` lu en synchrone)
  dans la boucle d'événements lors du démarrage des plateformes
  (`Detected blocking call to read_text … inside the event loop`). Le catalogue
  de modèles est désormais préchargé via un executor (`models.async_load_catalog`)
  au début de `async_setup_entry`, avant la création des entités.

## 1.2.3
- **Modèle volet `120C` : vrai stop.** La commande stop utilise désormais la
  commande Edisio `0B` (`6C7663#ID##GROUP#031E01000B640D0A`) — arrêt mi-course
  confirmé sur EDR-B4 — au lieu de l'« inverser ». open = Haut, close = Bas,
  stop = arrêt.

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
