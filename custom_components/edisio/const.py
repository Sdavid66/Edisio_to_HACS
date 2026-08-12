"""Constantes de l'integration Edisio."""
from __future__ import annotations

DOMAIN = "edisio"
PLATFORMS = ["switch", "light", "cover", "select", "sensor", "binary_sensor", "event"]

# Type de sous-entree (bouton « Ajouter un appareil » sur la page d'integration)
SUBENTRY_TYPE_DEVICE = "device"
# Cles des sous-entrees telecommande
CONF_KIND = "kind"
CONF_DEV_ID = "dev_id"
CONF_BUTTONS = "buttons"
CONF_CODE = "code"
KIND_REMOTE = "remote"

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
SERIAL_BAUDRATE = 9600            # dongle Edisio transparent (trames brutes)
RFPLAYER_BAUDRATE = 115200        # passerelle GCE RFPlayer (API ZIA)
# VID:PID des dongles USB connus (Prolific PL2303 / FTDI FT232 ; le RFPlayer est FT232R)
KNOWN_USB_IDS = [("067B", "2303"), ("0403", "6001")]

# Type de dongle (clef stockee dans entry.data ; defaut = edisio pour la retrocompat)
CONF_DONGLE = "dongle"
DONGLE_EDISIO = "edisio"          # dongle Edisio transparent (comportement historique)
DONGLE_RFPLAYER = "rfplayer"      # passerelle GCE RFPlayer RFP1000

MANUFACTURER = "Edisio"

# Signaux dispatcher
SIGNAL_RX = f"{DOMAIN}_rx"                 # trame entrante decodee
SIGNAL_DISCOVERY = f"{DOMAIN}_discovery"   # nouveau module detecte
SIGNAL_STATUS = f"{DOMAIN}_status"         # changement d'etat de la passerelle
SIGNAL_REMOVED = f"{DOMAIN}_removed"       # emetteur supprime (purge des caches)

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
