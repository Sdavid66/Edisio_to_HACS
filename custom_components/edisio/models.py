"""Catalogue des modeles Edisio (charge depuis models.json)."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_CATALOG_PATH = Path(__file__).parent / "models.json"


@lru_cache(maxsize=1)
def catalog() -> dict[str, dict]:
    """Retourne le catalogue {model_id: definition}."""
    return json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))


def model(model_id: str) -> dict | None:
    return catalog().get(model_id)


def models_for_platform(platform: str) -> dict[str, dict]:
    return {k: v for k, v in catalog().items() if v["platform"] == platform}


def choices() -> dict[str, str]:
    """Libelles pour la liste deroulante de configuration."""
    out = {}
    for k, v in sorted(catalog().items(), key=lambda x: (x[1]["category"], x[1]["name"])):
        cat = f"{v['category']} · " if v.get("category") else ""
        out[k] = f"{cat}{v['name']}"
    return out
