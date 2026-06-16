# Migration des équipements Edisio : Jeedom → Home Assistant

Récupérez les modules Edisio déjà appairés sous le **plugin Jeedom** et
recréez-les dans l'**intégration Home Assistant** (ce dépôt), **sans rien
réappairer**.

Le processus se fait en **deux temps** :

1. **En amont, sur votre PC** : un petit outil lit la sauvegarde Jeedom
   (`DB_backup.sql`) et produit un fichier d'import propre `edisio_import.json`.
2. **Dans Home Assistant** : vous chargez ce fichier via l'interface
   (*Edisio → Configurer → Importer depuis Jeedom*) qui recrée les équipements.

> Aucune dépendance : Python 3.9+ (stdlib seule). Home Assistant ne lit **jamais**
> la base Jeedom : il ne charge que le `edisio_import.json` généré.

---

## Étape 1 — Exporter la base Jeedom (interface web)

Une sauvegarde Jeedom contient le **dump SQL complet** de la base.

1. Jeedom : **Réglages → Système → Sauvegardes** → générez puis **téléchargez**
   la dernière sauvegarde (`.tar.gz`).
2. Décompressez-la : elle contient un fichier `DB_backup.sql`.

```bash
tar xzf backup-jeedom-*.tar.gz        # produit un dossier contenant DB_backup.sql
```

## Étape 2 — Produire le fichier d'import (outil hors ligne)

```bash
python3 edisio_migrate.py chemin/vers/DB_backup.sql
# -> écrit edisio_import.json (option -o pour changer le nom)
```

L'outil affiche un **rapport** (récepteurs par module, émetteurs, non résolus) et
écrit `edisio_import.json`. **Relisez le rapport** : noms, modèles, groupes. Le
fichier produit est volontairement lisible — vous pouvez l'ouvrir et l'ajuster.

**Stores / volets — choisir le type :** par défaut, les groupes pilotés en
Haut/Bas sont importés en **switch** (ON = Haut, OFF = Bas). Pour les exposer en
entités **`cover`** à la place :

```bash
python3 edisio_migrate.py chemin/vers/DB_backup.sql --stores-as-cover
```

(Les volets utilisent alors le modèle `120C` « EDR-B4 (Volet/Store) », trames
identiques à Jeedom : open = Haut, close = Bas, stop = Inverser.)

Format du fichier :

```json
{
  "edisio_import_version": 1,
  "receivers": [{"name": "Garage", "model": "120", "channel": 1, "edisio_id": "7189E655"}],
  "emitters":  [{"id": "075A8A30", "kinds": ["battery", "binary", "event"]}],
  "unresolved": []
}
```

## Étape 3 — Charger dans Home Assistant (interface)

1. Déposez `edisio_import.json` dans un dossier accessible par HA, par ex.
   `/config` (add-on *Samba* ou *File editor*).
2. **Paramètres → Appareils et services → Edisio → Configurer →
   *Importer depuis Jeedom***, indiquez le chemin (défaut
   `/config/edisio_import.json`), puis validez le récapitulatif.
   Alternative : service `edisio.import_jeedom` avec le champ `path`.

L'intégration se recharge : les lumières/volets apparaissent comme entités
pilotables, les télécommandes/sondes comme appareils découverts. **L'import est
idempotent** : les doublons existants sont ignorés, vous pouvez recommencer sans
risque.

---

## Comment l'outil reconstruit les équipements

- **ID Edisio** : `logicalId` de l'équipement (8 caractères hex), repli sur la
  `configuration`.
- **Modèle** : champ `device` de la configuration, mis en correspondance avec une
  clé de [`models.json`](../../custom_components/edisio/models.json) (`120`,
  `119`, `0C`…) — codes **identiques** à ceux du plugin Jeedom.
- **Récepteur vs émetteur** : code modèle au catalogue → récepteur pilotable ;
  sinon (télécommandes `01/03/05`…) → émetteur découvert.
- **Un appareil par groupe réellement utilisé** : l'outil lit les **commandes
  d'action** (table `cmd`), les regroupe par *groupe* Edisio, et crée un appareil
  par groupe en reprenant le **nom métier** de la commande (`ON_Garage` →
  « Garage »). Les groupes non utilisés ne sont pas créés.
- **Stores / volets** : groupes pilotés en Haut/Bas → **switch** par défaut
  (ON = Haut, OFF = Bas), trames **identiques** à Jeedom, signalés
  « ⚠ store/volet ? » dans le rapport. Avec `--stores-as-cover`, ils sont
  exposés en entités **`cover`** (modèle `120C`). Les deux types restent
  disponibles : on peut aussi ajouter un volet manuellement dans l'UI de HA.
- **Sondes** : nom « temp/sonde/thermo » → `kinds` température + batterie ; les
  autres émetteurs → batterie + binaire + event. Ces capacités s'enrichissent
  **automatiquement** dès que l'appareil émet une trame.

## Validation côté Home Assistant

Au chargement, le composant **valide** le fichier : ID hexa, modèle présent au
catalogue, canal entier. Les entrées invalides sont **ignorées et comptées**
comme avertissements (rien ne plante). Un fichier qui n'est pas du JSON attendu
est refusé proprement.
