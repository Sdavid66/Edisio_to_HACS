# Edisio pour Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

> Intégration **custom** Home Assistant pour la domotique **Edisio** (dongle USB 868 MHz),
> portée depuis le plugin Jeedom. 100 % locale, sans cloud.

## Installation via HACS (recommandé)

1. Assurez-vous que [HACS](https://hacs.xyz) est installé.
2. Dans Home Assistant : **HACS → menu ⋮ (en haut à droite) → Dépôts personnalisés**.
3. Collez l'URL de votre dépôt GitHub, ex. `https://github.com/Sdavid66/edisio_HA_v2`,
   choisissez la catégorie **Integration**, puis **Ajouter**.
4. Ouvrez la fiche **Edisio** qui apparaît → **Télécharger**.
5. **Redémarrez Home Assistant**.
6. **Paramètres → Appareils et services → Ajouter une intégration → Edisio**,
   puis sélectionnez le port série du dongle.

### Installation manuelle (sans HACS)
Copiez le dossier `custom_components/edisio` dans le `config/custom_components/`
de Home Assistant, puis redémarrez.


Intégration **custom component** portant le protocole Edisio (dongle USB 868 MHz)
depuis le plugin Jeedom vers Home Assistant. Communication 100 % locale (`local_push`),
aucune dépendance cloud.

> Portage du protocole série du démon Jeedom `edisiod.py`. L'encodage des trames
> a été validé bit à bit contre les templates d'origine (voir `tests/test_protocol.py`).

## Matériel
- Dongle USB Edisio (Prolific PL2303 `067B:2303` ou FTDI FT232 `0403:6001`), 9600 bauds.
- Modules Edisio : interrupteurs/télécommandes (émetteurs) et récepteurs
  (micro-modules, rail DIN, volet EMV-400…).


## Fonctionnement

### Modules émetteurs (télécommandes, sondes) — découverte automatique
Dès qu'une trame est reçue, l'appareil est créé automatiquement :
- `event.edisio_<id>_telecommande` : appui des boutons (types `on/off/toggle/up/down/stop`)
  → idéal pour déclencher des automatisations.
- `sensor.edisio_<id>_batterie` et `…_temperature` (sondes MID 08).
- `binary_sensor.edisio_<id>_etat` : dernier état ON/OFF (contacts, interrupteurs).

### Modules récepteurs (lumières, volets) — à ajouter manuellement
Dans **Configurer** sur l'intégration → *Ajouter un module pilotable* :
choisir un type (`switch`, `light`, `dimmer`, `cover`), un *groupe* et,
optionnellement, un *ID Edisio* (laissé vide → un émetteur virtuel est généré).

**Appairage** : mettre le récepteur en apprentissage, puis appeler le service
`edisio.learn` avec l'`edisio_id` de l'entité (ou simplement actionner l'entité
pendant la fenêtre d'apprentissage).


## Modèles de récepteurs pris en charge (trames exactes du catalogue)

Chaque modèle ci-dessous est défini avec ses **trames d'origine** (vérifiées contre
le plugin Jeedom). À l'ajout d'un module multi-canaux, **tous ses canaux** sont créés
sous le même ID appairé.

| Réf. | Nom | Entité HA | Canaux |
|------|-----|-----------|--------|
| 0C | Module Fil Pilote | select | 1 |
| 0F | Module Chaudière | select | 1 |
| 103 | Emetteur 1 bouton (ON/OFF) | switch | 1 |
| 108 | Emetteur 2 boutons (ON/OFF) | switch | 2 |
| 109 | Emetteur 3 boutons (ON/OFF) | switch | 3 |
| 110 | Emetteur 4 boutons (ON/OFF) | switch | 4 |
| 111 | Emetteur 5 boutons (ON/OFF) | switch | 5 |
| 112 | Micro-module EMV-400 (Volet roulant) | cover | 1 |
| 113 | Micro-module EMV-400 (Lumière) | light | 2 |
| 114 | Module lumière | light | 1 |
| 115 | Module volet roulant | cover | 1 |
| 116 | Micro-module EMSD-300A | light | 1 |
| 119 | EDR-D4 (ON/OFF/Intensité) | light (variateur) | 4 |
| 120 | EDR-B4 (ON/OFF) | switch | 4 |
| 120C | EDR-B4 (Volet/Store) | cover | 4 |

Les émetteurs (télécommandes, interrupteurs, sondes) ne figurent pas ici : ils sont
**découverts automatiquement** à la réception et exposés en `event`/`sensor`/`binary_sensor`.

## Migration depuis Jeedom (import de la base)

Si vous veniez du **plugin Edisio de Jeedom**, vous pouvez réimporter vos
équipements **sans rien réappairer**, en **deux temps** :

**1. En amont (sur votre PC) — produire le fichier d'import**

- Côté Jeedom : **Réglages → Système → Sauvegardes**, générez puis téléchargez
  une sauvegarde, et récupérez le `DB_backup.sql` qu'elle contient.
- Lancez l'outil fourni pour le convertir en fichier d'import :
  ```bash
  python3 tools/jeedom_migration/edisio_migrate.py chemin/vers/DB_backup.sql
  # -> produit edisio_import.json
  ```

**2. Dans Home Assistant — charger le fichier d'import**

- Déposez `edisio_import.json` dans un dossier accessible par HA (ex. `/config`,
  via l'add-on *Samba* ou *File editor*).
- **Paramètres → Appareils et services → Edisio → Configurer → *Importer depuis
  Jeedom*** : indiquez le chemin du fichier, validez le récapitulatif.
  (Aussi disponible en service `edisio.import_jeedom`.)

<!-- Capture de l'étape d'import : remplacez l'image ci-dessous par un vrai
     screenshot/GIF de votre HA (déposez-le dans docs/import_jeedom.png).
     Voir docs/README.md. -->
![Étape « Importer depuis Jeedom » dans Home Assistant](docs/import_jeedom.png)

L'import reconstruit **un appareil par groupe Edisio réellement utilisé**, en
reprenant le **nom métier** de vos commandes Jeedom (`ON_Garage`/`OFF_Garage`
→ « Garage »), et pré-enregistre les télécommandes/sondes comme émetteurs
découverts. Les doublons existants sont ignorés (ré-import sans risque). Home
Assistant ne lit jamais la base Jeedom : il ne charge que le `edisio_import.json`.

> **Stores / volets — deux choix possibles.** Par défaut, les groupes pilotés en
> Haut/Bas sont importés en **switch** (ON = Haut, OFF = Bas), trames identiques
> à Jeedom. Pour les exposer plutôt en entités **`cover`** (modèle *EDR-B4
> Volet/Store*, réf. `120C`), relancez l'outil avec `--stores-as-cover`. Vous
> pouvez aussi, à tout moment, ajouter un volet manuellement via *Configurer →
> Ajouter un module pilotable → EDR-B4 (Volet/Store)*.
>
> Détails et format du fichier : [`tools/jeedom_migration/`](tools/jeedom_migration/).

## Mode inclusion / exclusion

Par défaut, **aucun émetteur inconnu n'est ajouté** : les trames d'appareils non
connus (voisinage, télécommandes non désirées) sont ignorées. Pour appairer un
émetteur, on ouvre une fenêtre d'inclusion — exactement comme sur Jeedom.

**Inclusion :**
- Interrupteur `switch.edisio_mode_inclusion` (catégorie *Configuration*), ou
- Service `edisio.inclusion_mode` (`enable`, `duration` en secondes).

Pendant la fenêtre (120 s par défaut, fermeture automatique), appuyez sur le bouton
de la télécommande ou laissez la sonde émettre : l'appareil et ses entités
(`event` / `sensor` / `binary_sensor`) sont créés et **mémorisés** (ils survivent
au redémarrage, sans réactiver l'inclusion).

**Exclusion :**
- Supprimez l'appareil depuis l'UI (**Appareil → Supprimer**), ou
- Service `edisio.exclude` (`device_id`, et `ban: true` pour **bannir** définitivement
  un identifiant qui ne pourra plus jamais être inclus).

L'état accepté/banni est conservé dans un *store* dédié (hors configuration), donc
la découverte ne provoque jamais de rechargement de l'intégration.

## Services
- `edisio.inclusion_mode` : ouvre/ferme la fenêtre d'inclusion.
- `edisio.exclude` : retire (et bannit en option) un émetteur découvert.
- `edisio.learn` : envoie une trame d'apprentissage (`edisio_id`, `emitter_mid`).
- `edisio.send_raw` : envoie une trame hexa brute (debug).

## Protocole (résumé du reverse-engineering)
Trame (≥ 16 octets), 9600 8N1 :
```
6C 76 63 │ ID(4) │ BOUTON(1) │ MID(1) │ BATT(1) │ RMAX(1) │ RC(1) │ CMD(1) │ [DATA] │ 64 0D 0A
```
- En-tête `6C7663`, pied `640D0A`.
- `MID` = type de module (`08` = sonde température, `1D` = multi-état…).
- `CMD` : `01`=ON, `02`=OFF, `03..08`=toggle, `09`=ON, `1B`=down, `0B`=stop, `F1..FA`=intensité 20..100 %.
- Batterie : `pct = round((octet / 3.3) × 10)` (3,3 V ⇒ 100 %).
- Température (MID 08) : `int(DATA[3:4] + DATA[0:2], 16) / 100`.
- Émission : trame complète écrite **3 fois** espacées de 140 ms.

## Limitations
- Les récepteurs ne renvoient pas leur état : l'état dans HA est **optimiste**.
- La correspondance modèle → type est volontairement générique ; ajustez le
  `group`/type lors de l'ajout d'un module.
- Testé en simulation du protocole ; une validation sur dongle réel est recommandée.

## Licence
GPL-2.0 (cohérente avec le plugin Jeedom d'origine).
