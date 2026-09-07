"""Backend GCE RFPlayer (RFP1000) : API ZIA (JSON) pour piloter de l'Edisio.

Contrairement au dongle Edisio transparent (qui transporte les trames RF brutes),
le RFPlayer est une passerelle intelligente : on lui parle en commandes de haut
niveau (« ZIA++… ») a 115200 bauds, et il livre les evenements en lignes JSON
prefixees « ZIA33 » (apres « ZIA++FORMAT JSON »).

Ce module se contente de TRADUIRE :
  - actions du catalogue Edisio  ->  commandes ZIA a emettre ;
  - trames Edisio recues (JSON)  ->  le meme dict decode que ``protocol.decode``
    (cle ``id`` en hexa 8 caracteres, ``value``, ``battery``, ``temperature``,
    ``button``…), afin que TOUTE la logique au-dessus (dispatch, entites,
    inclusion) fonctionne sans changement.

Reference : API RFPlayer (GCE/ZiBlue) + implementation open-source
gce-electronics/HA_RFPlayer (format JSON « ZIA33 », protocolMeaning=EDISIO).
Les details fins (code bouton multi-boutons, association) restent a valider sur
materiel reel ; le code est defensif et journalise sans planter.
"""
from __future__ import annotations

import re

# Commandes envoyees au demarrage (chacune sera prefixee « ZIA++ »).
#  - FORMAT JSON : recevoir les evenements en JSON (lignes ZIA33) ;
#  - FREQ H 868350 : accorder la bande haute sur Edisio (868.350 MHz).
INIT_COMMANDS = ["FORMAT JSON", "FREQ H 868350"]

# action du catalogue Edisio  ->  ordre ZIA
# NB : le RFPlayer n'a PAS de commande volet dediee (SHUTTER_OPEN/CLOSE/STOP) en
# ZIA. Un volet se pilote donc en ON (montee) / OFF (descente). L'ARRET en cours
# de course n'est PAS realisable via le RFPlayer : aucun verbe ZIA ne mappe les
# codes Edisio SHUTTER_STOP (0x0B) / DIM-STOP (0x08), et re-appui / TOGGLE / DIM /
# sens oppose n'arretent pas le module (teste sur materiel). "stop" n'est donc pas
# traduit (no-op cote RFPlayer) ; sur le dongle transparent, le vrai stop est emis.
_ACTION_ZIA = {
    "on": "ON", "off": "OFF", "toggle": "TOGGLE",
    "open": "ON", "close": "OFF",
    "up": "ON", "down": "OFF",
    "heat_on": "ON", "heat_off": "OFF", "heat_other": "DIM",
}

# Bouton « OFF » (pair) d'une paire Edisio lumiere/interrupteur ; l'autre tombe
# sur le bouton « ON » (impair). Voir _qualifier().
_OFF_ACTIONS = {"off", "heat_off"}

# Volet : montee/descente/stop passent tous par le MEME bouton Edisio ; c'est la
# commande (ON=montee, OFF=descente, TOGGLE=stop) qui porte le sens - et non deux
# boutons distincts comme pour une lumiere. Voir _qualifier().
_COVER_ACTIONS = {"open", "close", "stop", "up", "down"}


def _qualifier(action: str, group: int) -> int:
    """Numero de bouton Edisio (QUALIFIER RFPlayer) pour une action + un canal.

    Lumiere/interrupteur : boutons par PAIRES -> ON = bouton impair, OFF = pair.
    Canal 1 -> ON=1/OFF=2, canal 2 -> ON=3/OFF=4, etc. (confirme sur materiel :
    un module mono-canal s'eteint au QUALIFIER 2 et s'allume au QUALIFIER 1).
    Volet : montee/descente/stop partagent le MEME bouton (impair du canal), le
    sens venant de ON/OFF. Les stores EDR-B4 sont cables sur les voies paires ->
    canal 2 => QUALIFIER 3 pour monter ET descendre (confirme sur materiel reel).
    """
    base = 2 * (max(1, int(group)) - 1)
    if action in _COVER_ACTIONS:
        return base + 1
    return base + (2 if action in _OFF_ACTIONS else 1)

# subTypeMeaning RFPlayer  ->  valeur logique (comme protocol.DECODE_VALUE)
_SUBTYPE_VALUE = {
    "ON": "on", "OFF": "off", "TOGGLE": "toggle",
    "UP": "up", "DOWN": "down", "STOP": "stop", "MY": "stop",
}

_VOLT_RE = re.compile(r"([0-9]+(?:\.[0-9]+)?)\s*V")


def build_command(action: str, edisio_id: str, group: int,
                  level: int | None = None) -> str | None:
    """Traduit une action en commande ZIA (sans le prefixe « ZIA++ »).

    L'ID Edisio (hexa 8 caracteres cote integration) est passe en decimal au
    RFPlayer, comme il le fait lui-meme en reception.
    """
    try:
        dev_dec = int(edisio_id, 16)
    except (TypeError, ValueError):
        return None
    # Le canal (groupe) est passe en QUALIFIER pour adresser un canal precis
    # d'un recepteur multi-canaux (a valider sur materiel reel).
    # Syntaxe RFPlayer/ZiBlue : « ZIA++<CMD> <PROTOCOLE> ID <n> [QUALIFIER q] ».
    # Le nom du protocole vient AVANT « ID » (et non apres) ; l'inverse est mal
    # interprete par le RFPlayer (commande ON/OFF erratique sur materiel reel).
    # Le QUALIFIER = numero de bouton Edisio, distinct pour ON et OFF (paires).
    if action == "slider" and level is not None:
        lvl = max(0, min(100, int(level)))
        if lvl == 0:  # extinction -> bouton OFF de la paire
            return f"OFF EDISIO ID {dev_dec} QUALIFIER {_qualifier('off', group)}"
        return f"DIM EDISIO ID {dev_dec} %{lvl} QUALIFIER {_qualifier('on', group)}"
    zia = _ACTION_ZIA.get(action)
    if not zia:
        return None
    return f"{zia} EDISIO ID {dev_dec} QUALIFIER {_qualifier(action, group)}"


def build_assoc_command(edisio_id: str, group: int = 1) -> str | None:
    """Traduit l'appairage en commande ZIA « ASSOC » (sans le prefixe « ZIA++ »).

    Equivalent RFPlayer de la trame d'apprentissage Edisio ``09<MID>1F000010`` :
    le RFPlayer emet sa sequence d'association Edisio pendant que le module est
    en mode apprentissage, afin qu'il memorise l'emetteur virtuel. Le MID Edisio
    n'a pas d'equivalent ZIA (le RFPlayer gere l'emulation en interne).
    Detail a valider sur materiel reel.
    """
    try:
        dev_dec = int(edisio_id, 16)
    except (TypeError, ValueError):
        return None
    return f"ASSOC EDISIO ID {dev_dec} QUALIFIER {int(group)}"


def _battery_pct(infos: dict) -> int | None:
    """Extrait un pourcentage batterie depuis infoMeaning (« …, 3.5V »)."""
    meaning = str(infos.get("infoMeaning", ""))
    m = _VOLT_RE.search(meaning)
    if not m:
        return None
    try:
        volts = float(m.group(1))
    except ValueError:
        return None
    return max(0, min(100, round(volts / 3.3 * 100)))


def parse_event(data: dict) -> dict | None:
    """Traduit un evenement JSON RFPlayer en dict decode Edisio, ou None.

    Ne retient que les trames dont le protocole est EDISIO.
    """
    if not isinstance(data, dict):
        return None
    frame = data.get("frame")
    if not isinstance(frame, dict):
        return None
    header = frame.get("header")
    if not isinstance(header, dict) or header.get("protocolMeaning") != "EDISIO":
        return None
    infos = frame.get("infos")
    if not isinstance(infos, dict):
        return None
    raw_id = infos.get("id")
    if raw_id in (None, ""):
        return None
    try:
        dev_id = format(int(raw_id), "08X")
    except (TypeError, ValueError):
        return None

    subtype = str(infos.get("subTypeMeaning") or "").upper()
    out: dict = {
        "id": dev_id,
        # A defaut d'un code bouton dedie cote RFPlayer, on utilise le qualifier.
        "button": str(infos.get("qualifier") or ""),
        "mid": str(infos.get("subType") or ""),
        "cmd": subtype,
        "raw": str(data),
    }

    if "TEMPERATURE" in subtype:
        try:
            out["temperature"] = int(infos.get("add0")) / 100
        except (TypeError, ValueError):
            pass

    batt = _battery_pct(infos)
    if batt is not None:
        out["battery"] = batt

    val = _SUBTYPE_VALUE.get(subtype)
    if val is not None:
        out["value"] = val

    return out
