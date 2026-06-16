#!/usr/bin/env python3
"""Convertit une sauvegarde Jeedom (DB_backup.sql) en fichier d'import Edisio.

Outil **autonome** a lancer en amont (Python 3.9+, stdlib uniquement). Il lit le
dump SQL d'une sauvegarde Jeedom et produit un petit fichier `edisio_import.json`
**propre et verifiable**, qui sera ensuite charge depuis l'interface Home
Assistant (Edisio -> Configurer -> Importer depuis Jeedom) pour recreer les
equipements, sans rien reappairer.

Le fichier produit contient :
  - receivers : [{name, model, channel, edisio_id}]   (recepteurs pilotables)
  - emitters  : [{id, kinds}]                          (telecommandes / sondes)
  - unresolved: [noms]                                  (a verifier, informatif)

Exemple :
    python3 edisio_migrate.py chemin/vers/DB_backup.sql
    python3 edisio_migrate.py DB_backup.sql -o edisio_import.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

IMPORT_VERSION = 1

# Catalogue des modeles, partage avec l'integration.
_DEFAULT_MODELS = (
    Path(__file__).resolve().parents[2]
    / "custom_components" / "edisio" / "models.json"
)

HEX_ID_RE = re.compile(r"^[0-9A-Fa-f]{8}$")
TEMP_HINT_RE = re.compile(r"(temp|sonde|thermo)", re.I)
_COVER_HINT_RE = re.compile(r"(store|volet|haut|bas|ouvr|ferm|monter|descendre)", re.I)
_ACTION_PREFIX = re.compile(
    r"^(on|off|allumer|eteindre|haut|bas|monter|descendre|ouvrir|fermer|"
    r"stop|inverser|etat|toggle|e)([ _\-]+|$)", re.I)
_ACTION_SUFFIX = re.compile(r"([ _\-]+(haut|bas|du|\d+))+$", re.I)


def load_models(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
#  Mini-parseur de dump mysqldump (positionnel via le CREATE TABLE)            #
# --------------------------------------------------------------------------- #

def _table_columns(sql: str, table: str) -> list[str]:
    m = re.search(
        r"CREATE TABLE `" + re.escape(table) + r"` \((.*?)\n\) ENGINE",
        sql, re.S,
    )
    if not m:
        return []
    cols = []
    for line in m.group(1).splitlines():
        line = line.strip()
        cm = re.match(r"`([^`]+)`", line)
        if cm and not line.upper().startswith(
            ("PRIMARY", "UNIQUE", "KEY", "CONSTRAINT", "FOREIGN")
        ):
            cols.append(cm.group(1))
    return cols


def _split_values(blob: str) -> list[list]:
    """Decoupe la section `VALUES (...),(...)` en liste de tuples de valeurs."""
    rows: list[list] = []
    row: list = []
    cur: list[str] = []
    field_is_str = False
    in_str = False
    esc = False
    depth = 0

    def end_field() -> None:
        nonlocal cur, field_is_str
        token = "".join(cur)
        if field_is_str:
            row.append(token)
        else:
            token = token.strip()
            row.append(None if token == "" or token.upper() == "NULL" else token)
        cur = []
        field_is_str = False

    for c in blob:
        if in_str:
            if esc:
                cur.append({"n": "\n", "t": "\t", "r": "\r", "0": "\0"}.get(c, c))
                esc = False
            elif c == "\\":
                esc = True
            elif c == "'":
                in_str = False
            else:
                cur.append(c)
            continue
        if c == "'":
            in_str = True
            field_is_str = True
        elif c == "(":
            depth += 1
            if depth == 1:
                row, cur, field_is_str = [], [], False
        elif c == ")" and depth == 1:
            depth -= 1
            end_field()
            rows.append(row)
        elif c == ")":
            depth -= 1
        elif c == "," and depth == 1:
            end_field()
        elif depth == 1:
            cur.append(c)
    return rows


def iter_rows(sql: str, table: str) -> list[dict]:
    cols = _table_columns(sql, table)
    if not cols:
        return []
    rows: list[dict] = []
    for m in re.finditer(
        r"INSERT INTO `" + re.escape(table) + r"` VALUES (.*?);\n", sql, re.S
    ):
        for tup in _split_values(m.group(1)):
            if len(tup) == len(cols):
                rows.append(dict(zip(cols, tup)))
    return rows


# --------------------------------------------------------------------------- #
#  Extraction des champs Edisio                                                 #
# --------------------------------------------------------------------------- #

def _flatten(obj, out: list[str]) -> None:
    if isinstance(obj, dict):
        for v in obj.values():
            _flatten(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _flatten(v, out)
    elif obj is not None:
        out.append(str(obj))


def detect_id(values: list[str], logical_id) -> str | None:
    for v in ([logical_id] if logical_id else []) + values:
        if v and HEX_ID_RE.match(str(v).strip()):
            return str(v).strip().upper()
    return None


def detect_model(values: list[str], logical_id, models: dict) -> str | None:
    keys = set(models)
    for v in ([logical_id] if logical_id else []) + values:
        if v and str(v).strip() in keys:
            return str(v).strip()
    return None


def _derive_name(cmd_names: list[str], fallback: str) -> str:
    candidates: list[str] = []
    for raw in cmd_names:
        s = (raw or "").strip()
        s = _ACTION_PREFIX.sub("", s)
        s = _ACTION_SUFFIX.sub("", s).strip(" _-")
        if s and re.search(r"[A-Za-zÀ-ÿ]", s):
            candidates.append(s)
    if not candidates:
        return fallback
    return max(candidates, key=lambda x: (len(x), x))


# Modeles « cover » equivalents pour les groupes pilotes en Haut/Bas.
COVER_EQUIVALENT = {"120": "120C"}


def parse_dump(sql_path: Path, models: dict, stores_as_cover: bool = False) -> dict:
    sql = sql_path.read_text(encoding="utf-8", errors="replace")
    edisio = [e for e in iter_rows(sql, "eqLogic")
              if (e.get("eqType_name") or "").lower() == "edisio"]

    # Commandes d'action regroupees par eqLogic, avec leur groupe Edisio.
    actions_by_eq: dict[str, list[tuple[str, str]]] = {}
    for c in iter_rows(sql, "cmd"):
        if (c.get("type") or "").lower() != "action":
            continue
        try:
            ccfg = json.loads(c.get("configuration") or "{}")
        except (json.JSONDecodeError, TypeError):
            ccfg = {}
        if not isinstance(ccfg, dict):
            continue
        group = str(ccfg.get("group") or "").strip()
        if not group:
            continue
        actions_by_eq.setdefault(c.get("eqLogic_id"), []).append(
            (group, c.get("name") or ""))

    receivers: list[dict] = []
    emitters: list[dict] = []
    unresolved: list[str] = []
    cover_keys: set[tuple] = set()

    for eq in edisio:
        name = eq.get("name") or "Edisio"
        logical = eq.get("logicalId")
        try:
            cfg = json.loads(eq.get("configuration") or "{}")
        except (json.JSONDecodeError, TypeError):
            cfg = {}
        flat: list[str] = []
        _flatten(cfg, flat)

        dev_id = detect_id(flat, logical)
        model = detect_model([str(cfg.get("device") or "")] + flat, logical, models)

        if not dev_id:
            unresolved.append(name)
            continue

        if model:  # recepteur pilotable : un appareil par groupe utilise
            by_group: dict[str, list[str]] = {}
            for grp, cname in actions_by_eq.get(eq.get("id"), []):
                by_group.setdefault(grp, []).append(cname)
            if not by_group:
                for ch in models[model].get("channels", [1]):
                    by_group[str(ch)] = []
            for grp in sorted(by_group, key=lambda g: (len(g), g)):
                cnames = by_group[grp]
                ch = int(grp) if grp.isdigit() else grp
                is_cover = any(_COVER_HINT_RE.search(n or "") for n in cnames)
                grp_model = model
                if is_cover:
                    cover_keys.add((dev_id, ch))
                    if stores_as_cover and model in COVER_EQUIVALENT:
                        grp_model = COVER_EQUIVALENT[model]
                receivers.append({
                    "name": _derive_name(cnames, f"{name} G{grp}"),
                    "model": grp_model,
                    "channel": ch,
                    "edisio_id": dev_id,
                    "source": name,
                })
        else:  # emetteur decouvert
            kinds = (["battery", "temperature"]
                     if TEMP_HINT_RE.search(name) else
                     ["battery", "binary", "event"])
            emitters.append({"id": dev_id, "kinds": kinds, "name": name})

    # Dedoublonnage.
    seen = set()
    recv = []
    for d in receivers:
        key = (d["edisio_id"], d["channel"])
        if key not in seen:
            seen.add(key)
            recv.append(d)
    seen_e = set()
    emit = []
    for e in emitters:
        if e["id"] not in seen_e:
            seen_e.add(e["id"])
            emit.append(e)

    return {"receivers": recv, "emitters": emit,
            "unresolved": unresolved, "cover_keys": cover_keys}


# --------------------------------------------------------------------------- #
#  Rapport + ecriture du fichier d'import                                       #
# --------------------------------------------------------------------------- #

def report(data: dict, models: dict) -> None:
    recv, emit, unres = data["receivers"], data["emitters"], data["unresolved"]
    covers = data["cover_keys"]
    print(f"\n=== RECEPTEURS PILOTABLES : {len(recv)} entites ===")
    last = None
    for d in recv:
        if d.get("source") != last:
            last = d.get("source")
            print(f"  --- module {last} [{d['edisio_id']}] "
                  f"({models.get(d['model'],{}).get('name','?')}) ---")
        mdl = models.get(d["model"], {})
        flag = "  ⚠ store/volet ?" if (d["edisio_id"], d["channel"]) in covers else ""
        print(f"     groupe {str(d['channel']):<3} -> {mdl.get('platform','?'):<7} "
              f"{d['name']}{flag}")
    if covers:
        print(f"\n  ({len(covers)} groupe(s) ressemblent a des stores/volets : "
              "importes en switch ON=Haut / OFF=Bas par defaut, frames identiques "
              "a Jeedom.\n   Utilisez --stores-as-cover pour les exposer en "
              "entites 'cover' a la place.)")

    print(f"\n=== EMETTEURS DECOUVERTS : {len(emit)} appareils ===")
    for e in emit:
        print(f"  [{e['id']}] {e.get('name',''):<28} kinds={e['kinds']}")

    if unres:
        print(f"\n=== NON RESOLUS : {len(unres)} (sans ID exploitable) ===")
        for n in unres:
            print(f"  {n}")
    print()


def build_import_file(data: dict, source: str) -> dict:
    """Construit le contenu JSON charge par Home Assistant (champs nettoyes)."""
    receivers = [{k: d[k] for k in ("name", "model", "channel", "edisio_id")}
                 for d in data["receivers"]]
    emitters = [{"id": e["id"], "kinds": e["kinds"]} for e in data["emitters"]]
    return {
        "edisio_import_version": IMPORT_VERSION,
        "generated_from": source,
        "receivers": receivers,
        "emitters": emitters,
        "unresolved": data["unresolved"],
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dump", type=Path,
                    help="Fichier DB_backup.sql d'une sauvegarde Jeedom")
    ap.add_argument("-o", "--out", type=Path, default=Path("edisio_import.json"),
                    help="Fichier d'import a produire (defaut: edisio_import.json)")
    ap.add_argument("--models", type=Path, default=_DEFAULT_MODELS,
                    help="Catalogue models.json (defaut: celui de l'integration)")
    ap.add_argument("--stores-as-cover", action="store_true",
                    help="Importe les groupes Haut/Bas en entites 'cover' au lieu "
                         "de switch (defaut: switch Haut/Bas).")
    args = ap.parse_args()

    if not args.dump.exists():
        sys.exit(f"Fichier introuvable : {args.dump}")

    models = load_models(args.models)
    data = parse_dump(args.dump, models, stores_as_cover=args.stores_as_cover)
    report(data, models)

    payload = build_import_file(data, args.dump.name)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    print(f"Fichier d'import ecrit : {args.out}\n"
          f"  -> {len(payload['receivers'])} recepteurs, "
          f"{len(payload['emitters'])} emetteurs, "
          f"{len(payload['unresolved'])} non resolus.\n"
          "Chargez-le ensuite dans Home Assistant : Edisio -> Configurer -> "
          "Importer depuis Jeedom.")


if __name__ == "__main__":
    main()
