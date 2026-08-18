"""Catalogue des modeles Edisio (charge depuis models.json)."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_CATALOG_PATH = Path(__file__).parent / "models.json"


@lru_cache(maxsize=1)
def catalog() -> dict[str, dict]:
    """Retourne le catalogue {model_id: definition}.

    Lecture synchrone : ne doit PAS etre appelee directement dans la boucle
    d'evenements avant un prechargement. Utiliser ``async_load_catalog`` au
    demarrage pour remplir le cache via un executor.
    """
    return json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))


async def async_load_catalog(hass) -> dict[str, dict]:
    """Precharge le catalogue dans un executor (evite l'I/O bloquante)."""
    return await hass.async_add_executor_job(catalog)


def model(model_id: str) -> dict | None:
    return catalog().get(model_id)


def models_for_platform(platform: str) -> dict[str, dict]:
    return {k: v for k, v in catalog().items() if v["platform"] == platform}


def choices() -> dict[str, str]:
    """Libelles pour la liste deroulante d'ajout (hors modeles masques).

    Les modeles ``hidden`` restent resolus par ``model()`` (retrocompat des
    appareils deja ajoutes) mais n'apparaissent plus dans le catalogue d'ajout.
    """
    out = {}
    items = [(k, v) for k, v in catalog().items() if not v.get("hidden")]
    for k, v in sorted(items, key=lambda x: (x[1]["category"], x[1]["name"])):
        cat = f"{v['category']} · " if v.get("category") else ""
        out[k] = f"{cat}{v['name']}"
    return out
