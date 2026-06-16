"""Encodage/decodage du protocole serie Edisio (porte depuis le demon Jeedom)."""
from __future__ import annotations
import binascii

HEADER = "6C7663"
FOOTER = "640D0A"
FRAME_MIN_LEN = 16  # octets

# CMD recu -> valeur logique
DECODE_VALUE = {
    "01": "on", "02": "off", "03": "toggle", "04": "toggle", "05": "toggle",
    "06": "toggle", "07": "up", "08": "toggle", "09": "on", "0A": "off",
    "0B": "stop", "1A": "on", "1B": "down",
    "F1": 20, "F2": 20, "F3": 30, "F4": 40, "F5": 50,
    "F6": 60, "F7": 70, "F8": 80, "F9": 90, "FA": 100,
}

def _hx(b: int) -> str:
    return format(b, "02X")

def is_valid(raw: bytes) -> bool:
    if len(raw) < FRAME_MIN_LEN:
        return False
    h = "".join(_hx(x) for x in raw)
    return h.startswith(HEADER) and h.endswith(FOOTER)

def decode(raw: bytes) -> dict | None:
    """Decode une trame entrante en dict d'etat."""
    if not is_valid(raw):
        return None
    h = [_hx(x) for x in raw]
    pid = "".join(h[3:7])           # identifiant module (4 octets)
    bid = h[7]                      # bouton / groupe
    mid = h[8]                      # type de module
    bl_raw = int(h[9], 16)          # tension batterie
    cmd = h[12]                     # commande
    data = "".join(h[13:-3]) if len(raw) > FRAME_MIN_LEN else ""

    battery = max(0, min(100, round((bl_raw / 3.3) * 10)))
    out = {"id": pid, "button": bid, "mid": mid, "cmd": cmd,
           "battery": battery, "raw": "".join(h)}

    if mid == "08":  # sonde de temperature
        try:
            out["temperature"] = int(data[3:4] + data[0:2], 16) / 100
        except (ValueError, IndexError):
            return None
        return out
    if mid == "1D":  # multi-etat
        out["state"] = {"0B": 1, "0A": 2, "09": 3}.get(cmd)
        return out
    out["value"] = DECODE_VALUE.get(cmd, cmd)
    return out

def _build(edisio_id: str, group: int, mid: str, cmd: str, level: str = "") -> str:
    grp = format(group, "02X")
    return f"{HEADER}{edisio_id.upper()}{grp}{mid}1E0100{cmd}{level}{FOOTER}"

def cmd_on(edisio_id, group=1, mid="04"):
    return [_build(edisio_id, group, mid, "01"), _build(edisio_id, group, mid, "09")]

def cmd_off(edisio_id, group=1, mid="04"):
    return [_build(edisio_id, group, mid, "02"), _build(edisio_id, group, mid, "1B")]

def cmd_dim(edisio_id, level_pct, group=1, mid="05"):
    lvl = max(0, min(100, int(level_pct)))
    if lvl == 0:
        return cmd_off(edisio_id, group, mid)
    return [_build(edisio_id, group, mid, "04", format(lvl, "02X"))]

def cmd_cover_up(edisio_id, group=1):   return [_build(edisio_id, group, "01", "09")]
def cmd_cover_down(edisio_id, group=1): return [_build(edisio_id, group, "01", "1B")]
def cmd_cover_stop(edisio_id, group=1): return [_build(edisio_id, group, "03", "0B")]
def cmd_learn(edisio_id, mid="04"):     return [f"{HEADER}{edisio_id.upper()}09{mid}1F000010{FOOTER}"]


# --- Moteur de rendu des templates du catalogue (porte de Jeedom execute()) ---
def render(template: str, edisio_id: str, group: int = 1,
           slider: int | None = None) -> list[str]:
    """Rend un template (#ID#/#GROUP#/#slider#) en liste de trames pretes a emettre.

    Reproduit la logique du plugin Jeedom : padding du groupe sur 2 caracteres,
    regle '04#slider#' -> '02' quand l'intensite vaut 0, separateur '&&'.
    """
    s = template.replace("#ID#", edisio_id.upper())
    s = s.replace("#GROUP#", f"{int(group):02d}")
    if slider is not None:
        lvl = max(0, min(100, int(slider)))
        hx = format(lvl, "02X")
        if lvl != 0:
            s = s.replace("#slider#", hx)
        else:
            s = s.replace("04#slider#", "02")
    return [f for f in s.strip("$").split("&&") if f]
