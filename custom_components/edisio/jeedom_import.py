"""Chargement d'un fichier d'import Edisio (produit en amont par l'outil).

Le parsing de la base Jeedom (DB_backup.sql) est fait **hors de Home Assistant**
par `tools/jeedom_migration/edisio_migrate.py`, qui produit un fichier
`edisio_import.json`. Ce module se contente de **valider et nettoyer** ce fichier
avant de recreer les equipements :

  receivers : [{name, model, channel, edisio_id}]   -> options.devices
  emitters  : [{id, kinds}]                          -> store de la passerelle

Aucune dependance externe ; le format est volontairement simple et versionne.
"""
from __future__ import annotations

import re

from . import models
from .const import CONF_CHANNEL, CONF_EDISIO_ID, CONF_MODEL, CONF_NAME

SUPPORTED_VERSION = 1
HEX_ID_RE = re.compile(r"^[0-9A-Fa-f]{8}$")
VALID_KINDS = {"battery", "temperature", "binary", "event"}


class ImportError_(Exception):
    """Fichier d'import invalide ou illisible."""


def load_import(payload) -> dict:
    """Valide le contenu d'un fichier d'import et retourne des listes propres.

    Retourne {receivers, emitters, warnings}. Leve ImportError_ si la structure
    de base est inexploitable.
    """
    if not isinstance(payload, dict):
        raise ImportError_("Le fichier d'import n'est pas un objet JSON valide.")

    version = payload.get("edisio_import_version")
    if version is not None and version > SUPPORTED_VERSION:
        raise ImportError_(
            f"Version de fichier d'import non supportee ({version}).")

    if "receivers" not in payload and "emitters" not in payload:
        raise ImportError_("Aucune cle 'receivers' ou 'emitters' dans le fichier.")

    catalog = models.catalog()
    warnings: list[str] = []

    receivers: list[dict] = []
    seen_r: set[tuple] = set()
    for d in payload.get("receivers", []) or []:
        if not isinstance(d, dict):
            warnings.append("recepteur ignore (format invalide)")
            continue
        dev_id = str(d.get(CONF_EDISIO_ID, "")).strip().upper()
        model = str(d.get(CONF_MODEL, "")).strip()
        name = str(d.get(CONF_NAME, "")).strip() or f"Edisio {dev_id}"
        channel = d.get(CONF_CHANNEL, 1)
        if not HEX_ID_RE.match(dev_id):
            warnings.append(f"{name} : ID Edisio invalide ({dev_id!r})")
            continue
        if model not in catalog:
            warnings.append(f"{name} : modele inconnu ({model!r})")
            continue
        try:
            channel = int(channel)
        except (TypeError, ValueError):
            warnings.append(f"{name} : canal invalide ({channel!r})")
            continue
        key = (dev_id, channel)
        if key in seen_r:
            continue
        seen_r.add(key)
        receivers.append({
            CONF_NAME: name, CONF_MODEL: model,
            CONF_CHANNEL: channel, CONF_EDISIO_ID: dev_id,
        })

    emitters: list[dict] = []
    seen_e: set[str] = set()
    for e in payload.get("emitters", []) or []:
        if not isinstance(e, dict):
            warnings.append("emetteur ignore (format invalide)")
            continue
        dev_id = str(e.get("id", "")).strip().upper()
        if not HEX_ID_RE.match(dev_id):
            warnings.append(f"emetteur : ID invalide ({dev_id!r})")
            continue
        if dev_id in seen_e:
            continue
        seen_e.add(dev_id)
        kinds = [k for k in (e.get("kinds") or []) if k in VALID_KINDS]
        if not kinds:
            kinds = ["battery", "binary", "event"]
        emitters.append({"id": dev_id, "kinds": kinds})

    return {"receivers": receivers, "emitters": emitters, "warnings": warnings}
