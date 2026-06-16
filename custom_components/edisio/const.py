"""Constantes de l'integration Edisio."""
from __future__ import annotations

DOMAIN = "edisio"
PLATFORMS = ["switch", "light", "cover", "select", "sensor", "binary_sensor", "event"]

# Configuration
CONF_PORT = "port"
CONF_DEVICES = "devices"
CONF_EDISIO_ID = "edisio_id"
CONF_GROUP = "group"
CONF_TYPE = "type"
CONF_MODEL = "model"
CONF_CHANNEL = "channel"
CONF_NAME = "name"
CONF_EMITTER_MID = "emitter_mid"

# Types de modules pilotables (recepteurs)
TYPE_SWITCH = "switch"
TYPE_LIGHT = "light"
TYPE_DIMMER = "dimmer"
TYPE_COVER = "cover"

DEVICE_TYPES = [TYPE_SWITCH, TYPE_LIGHT, TYPE_DIMMER, TYPE_COVER]

# MID (modele d'emetteur) emule par defaut selon le type
DEFAULT_MID = {
    TYPE_SWITCH: "04",
    TYPE_LIGHT: "04",
    TYPE_DIMMER: "05",
    TYPE_COVER: "01",
}

# Liaison serie
SERIAL_BAUDRATE = 9600
# VID:PID des dongles USB Edisio connus (Prolific PL2303 / FTDI FT232)
KNOWN_USB_IDS = [("067B", "2303"), ("0403", "6001")]

# Signaux dispatcher
SIGNAL_RX = f"{DOMAIN}_rx"                 # trame entrante decodee
SIGNAL_DISCOVERY = f"{DOMAIN}_discovery"   # nouveau module detecte

# Services
SERVICE_LEARN = "learn"
SERVICE_SEND_RAW = "send_raw"
SERVICE_IMPORT = "import_jeedom"

# Delais d'emission (porte du demon Jeedom : 3 envois espaces de 140 ms)
TX_REPEAT = 3
TX_DELAY = 0.14

# Inclusion / exclusion
CONF_DISCOVERED = "discovered"   # liste {id, kinds:[...]} des emetteurs acceptes
CONF_BANNED = "banned"           # liste d'ids ignores en permanence
SIGNAL_INCLUSION = f"{DOMAIN}_inclusion"
SERVICE_INCLUSION = "inclusion_mode"
SERVICE_EXCLUDE = "exclude"
INCLUSION_TIMEOUT = 120          # fenetre d'inclusion (s), comme un appairage
EVENT_TYPES = ["on", "off", "toggle", "up", "down", "stop"]
