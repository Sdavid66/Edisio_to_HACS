# Edisio pour Home Assistant

**🇫🇷 Français** · [🇬🇧 English](README.en.md)

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![release](https://img.shields.io/github/v/release/Sdavid66/edisio_HA_v2)](https://github.com/Sdavid66/edisio_HA_v2/releases)
[![Buy me a coffee](https://img.shields.io/badge/Buy%20me%20a%20coffee-soutenir%20le%20projet-orange?logo=buy-me-a-coffee&logoColor=white)](https://buymeacoffee.com/sdavid66)

> Intégration **custom** Home Assistant pour la domotique **Edisio** (dongle USB 868 MHz),
> portée depuis le plugin Jeedom. 100 % locale, sans cloud.

> ☕ Ce projet vous est utile ? Vous pouvez **[m'offrir un café](https://buymeacoffee.com/sdavid66)**
> pour soutenir son développement — merci !

> ℹ️ **Pas encore dans le magasin HACS par défaut.** Installez l'intégration en
> **dépôt personnalisé** (voir ci-dessous). La publication dans le magasin
> officiel se fera plus tard.

## Installation via HACS (recommandé)

1. Assurez-vous que [HACS](https://hacs.xyz) est installé.
2. Dans Home Assistant : **HACS → menu ⋮ (en haut à droite) → Dépôts personnalisés**.
3. Collez l'URL du dépôt GitHub `https://github.com/Sdavid66/edisio_HA_v2`,
   choisissez la catégorie **Integration**, puis **Ajouter**.
4. Ouvrez la fiche **Edisio** qui apparaît → **Télécharger**.
5. **Redémarrez Home Assistant**.
6. **Paramètres → Appareils et services → Ajouter une intégration → Edisio**,
   puis choisissez le **type de dongle** et son **port série**.

### Installation manuelle (sans HACS)
Copiez le dossier `custom_components/edisio` dans le `config/custom_components/`
de Home Assistant, puis redémarrez.


Intégration **custom component** portant le protocole Edisio (dongle USB 868 MHz)
depuis le plugin Jeedom vers Home Assistant. Communication 100 % locale (`local_push`),
aucune dépendance cloud.

> Portage du protocole série du démon Jeedom `edisiod.py`. L'encodage des trames
> a été validé bit à bit contre les templates d'origine (voir `tests/test_protocol.py`).

## Matériel
- **Dongle USB Edisio** (Prolific PL2303 `067B:2303` ou FTDI FT232 `0403:6001`), 9600 bauds.
- **GCE RFPlayer (RFP1000)** — passerelle radio 433/868 MHz, en **version de test** (voir plus bas).
- Modules Edisio : interrupteurs/télécommandes (émetteurs) et récepteurs
  (micro-modules, rail DIN, volet EMV-400…).

## Dongle / passerelle : Edisio ou GCE RFPlayer

À l'ajout de l'intégration (et via **Reconfigurer**), choisissez le **type de dongle** :

| Type | Description | État |
|------|-------------|------|
| **Dongle Edisio** | Adaptateur USB transparent (PL2303/FT232), 9600 bauds, trames Edisio brutes. | ✅ Stable |
| **GCE RFPlayer (RFP1000)** | Passerelle intelligente, API ZIA à 115200 bauds, protocole Edisio 868 MHz. | 🧪 **Version de test** |

> ⚠️ **Le type doit correspondre à votre matériel.** En cas de mauvais choix,
> la passerelle ne fonctionnera pas (protocole et débit différents).

> 🧪 **Support RFPlayer en version de test.** L'émission/réception de base
> (ON/OFF/TOGGLE, batterie, température) est implémentée, mais certains détails
> fins (canal des récepteurs multi-voies, volets/variateurs, association) restent
> **à valider sur matériel réel**. En cas de souci, activez les logs de debug et
> ouvrez une *issue* :
> ```yaml
> logger:
>   logs:
>     custom_components.edisio: debug
> ```
> (cherchez les lignes `RFPlayer TX`/`RFPlayer RX`).


## Fonctionnement

### Télécommandes multi-boutons (1 à 5 boutons, boutons muraux)
**Ajouter un appareil → Détecter une télécommande** : nommez la télécommande, puis
apprenez ses boutons **un par un** (nommez le bouton → l'inclusion s'active →
appuyez → mémorisé → « Ajouter un autre bouton ? »). Vous obtenez **un seul
appareil** regroupant **une entité `event` par bouton** (+ batterie). Pour en
ajouter un plus tard : fiche de l'appareil → **Reconfigurer**.

### Autres émetteurs (sondes, contacts) — découverte automatique
En **mode inclusion**, une trame reçue fait apparaître une carte de découverte :
- `event.edisio_<id>_telecommande` : appui des boutons (types `on/off/toggle/up/down/stop`)
  → idéal pour déclencher des automatisations.
- `sensor.edisio_<id>_batterie` et `…_temperature` (sondes MID 08).
- `binary_sensor.edisio_<id>_etat` : dernier état ON/OFF (contacts, interrupteurs).

### Modules récepteurs (lumières, volets) — à ajouter manuellement
Sur la page de l'intégration (**Paramètres → Appareils et services → Edisio**),
cliquez sur le bouton **Ajouter un appareil** (à côté de *Ajouter un Hub*, comme
pour Z-Wave/Zigbee) : choisissez le **modèle** dans le catalogue, donnez un **nom**
et, optionnellement, un *ID Edisio* (laissé vide → un émetteur virtuel est généré).
Tous les canaux du module sont créés et rattachés à la passerelle. L'appareil est
ensuite **reconfigurable** (nom/ID) et **supprimable** individuellement.

> Les récepteurs ajoutés avant la v1.7.0 (via *Configurer*) restent pris en
> charge sans rien changer.

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

- **Paramètres → Appareils et services → Edisio → Configurer → *Importer depuis
  Jeedom*** : **téléversez `edisio_import.json` directement depuis votre
  ordinateur** (idéal si HA tourne sur une machine distante : Proxmox, NAS…),
  puis validez le récapitulatif.
- *Alternative* : si le fichier est déjà sur le serveur HA (ex. `/config` via
  l'add-on *Samba* / *File editor*), indiquez plutôt son chemin. Le service
  `edisio.import_jeedom` (basé sur un chemin serveur) reste aussi disponible.

L'import reconstruit **un appareil par groupe Edisio réellement utilisé**, en
reprenant le **nom métier** de vos commandes Jeedom (`ON_Garage`/`OFF_Garage`
→ « Garage »), et pré-enregistre les télécommandes/sondes comme émetteurs
découverts. Les doublons existants sont ignorés (ré-import sans risque). Home
Assistant ne lit jamais la base Jeedom : il ne charge que le `edisio_import.json`.

> **Stores / volets — deux choix possibles.** Par défaut, les groupes pilotés en
> Haut/Bas sont importés en **switch** (ON = Haut, OFF = Bas), trames identiques
> à Jeedom. Pour les exposer plutôt en entités **`cover`** (modèle *EDR-B4
> Volet/Store*, réf. `120C`), relancez l'outil avec `--stores-as-cover`. Vous
> pouvez aussi, à tout moment, ajouter un volet manuellement via le bouton
> *Ajouter un appareil → EDR-B4 (Volet/Store)*.
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
de la télécommande ou laissez la sonde émettre : une **carte « Émetteur Edisio
détecté »** apparaît sur **Paramètres → Appareils et services**. Cliquez sur
**Configurer** pour lier l'appareil ; ses entités (`event` bouton / `sensor` /
`binary_sensor`) sont alors créées, rattachées à la passerelle, et **mémorisées**
(elles survivent au redémarrage, sans réactiver l'inclusion). Vous voyez donc
chaque appareil avant de l'ajouter, et les émetteurs du voisinage n'encombrent
jamais votre installation.

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

## Soutenir le projet ☕
Ce plugin est gratuit et développé sur mon temps libre. S'il vous rend service,
vous pouvez **[m'offrir un café](https://buymeacoffee.com/sdavid66)** — chaque
petit soutien est très apprécié et motive les prochaines améliorations. Merci ! 🙏

[![Buy me a coffee](https://img.shields.io/badge/Buy%20me%20a%20coffee-soutenir%20le%20projet-orange?logo=buy-me-a-coffee&logoColor=white)](https://buymeacoffee.com/sdavid66)

## Licence
GPL-2.0 (cohérente avec le plugin Jeedom d'origine).
