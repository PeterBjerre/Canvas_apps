# -*- coding: utf-8 -*-
"""
Alt der skal tilpasses, staar HER og kun her.

Landingssiden har EEN datakilde: SharePoint-listen MD_RequestIndex. De fem
domaeneapps skriver hver en opsummeringsraekke til den fra deres submit-flow.
Se docs/07-landingsside.md.
"""
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "tools"))
from design_tokens import ref as _t
import env_config as env
import icons

# Navnet paa listen som den hedder, naar den er tilfoejet appen som datakilde.
LIST = "MD_RequestIndex"

# Power Fx binder SharePoint-kolonner paa VISNINGSNAVN, ikke internt navn.
# Provisioneringsscriptet doeber den indbyggede Title-kolonne om til
# "RequestNo", saa listen er laesbar for dem der aabner den direkte - og
# derfor skal appen ogsaa kalde den RequestNo. Aendrer du navnet i
# Provision-RequestIndex.ps1, skal det aendres her samtidig.
COL_NO = "RequestNo"

# ---------------------------------------------------------------------------
# De fem domaener.
#
# app_id = satellittens app-id. Flisen bygger selv play-URL'en af ENV_ID og
#          app_id, saa miljoeet staar EET sted i stedet for fem.
#          Er app_id None, staar flisen som "Kommer snart" og kan ikke
#          aabnes - appen findes ikke, eller ingen har fundet id'et endnu.
#
# App-id'et staar IKKE i solution-eksporten. Det Id, der staar i en app's
# Properties.json, er DOKUMENTETS id, ikke app'ens - de to er forskellige,
# og play-URL'en vil have app'ens. Hent det i Studio-URL'en:
#
#   https://make.powerapps.com/e/<env>/canvas/?action=edit&app-id=...%2Fapps%2F<app_id>
#
# eller med:  pac canvas list
# ---------------------------------------------------------------------------
# Miljoe og app-id'er kommer fra tools/canvas_apps.json via env_config.
# De stod foer her OG tre andre steder, holdt sammen af 60 linjers regex i
# build_all.py. Se tools/env_config.py.
ENV_ID = env.ENV_ID

# "app" er noeglen i canvas_apps.json. Er der intet id dér, staar flisen
# som "Kommer snart" og kan ikke aabnes - appen findes ikke endnu.
#
# "token" er farvens navn i tools/design_tokens.py - flisens og raekkens
# ikon er SVG'er, og de skal have hex-udgaven af den samme farve.
# "icon_key" er noeglen i tools/icons.DOMAIN - stien slaas op dér.
DOMAINS = [
    {"key": "FunctionalLocation", "short": "FL",  "name": "Functional location",
     "token": "domain-fl",  "app": "functionallocation", "icon_key": "functionallocation"},
    {"key": "Equipment",          "short": "EQ",  "name": "Equipment",
     "token": "domain-eq",  "app": "equipment", "icon_key": "equipment"},
    {"key": "MeasuringPoint",     "short": "MP",  "name": "Measuring point",
     "token": "domain-mp",  "app": None, "icon_key": "measuringpoint"},
    {"key": "Material",           "short": "MAT", "name": "Material",
     "token": "domain-mat", "app": "material", "icon_key": "material"},
    {"key": "MaintenancePlan",    "short": "VHP", "name": "Maintenance plan",
     "token": "domain-vhp", "app": "vhplan", "icon_key": "vhplan"},
]

# Ikonerne er de FAELLES (tools/icons.py, issue #74) - de samme som i
# sidebaren og sideoverskrifterne. Measuring Points lineal er spejlet, saa
# den peger samme vej som Equipments skruenoegle (issue #70).
for _d in DOMAINS:
    _d["icon"] = icons.path(_d["icon_key"])
    _d["mirror"] = icons.mirrored(_d["icon_key"])

for _d in DOMAINS:
    _d["color"] = _t(_d["token"])

for _d in DOMAINS:
    _d["app_id"] = env.app_id(_d["app"]) if _d["app"] else None

PLAY = "https://apps.powerapps.com/play/e/{env}/a/{app}"

# SAMME FANE, IKKE EN NY
#
# LaunchTarget.Replace sender browseren videre i den fane, brugeren staar
# i. Med New fik man en fane pr. klik: aabn tre indmeldinger, og der er
# fire faner med Power Apps i, som alle ser ens ud i proceslinjen.
#
# Gaelder navigation MELLEM APPS. Et dokument fra biblioteket aabnes
# stadig i en ny fane - dér ville Replace smide appen vaek, og en
# halvudfyldt formular med den.
APP_TARGET = "LaunchTarget.Replace"

for _d in DOMAINS:
    _d["url"] = env.play_url(_d["app"]) if _d["app"] else ""


# ---------------------------------------------------------------------------
# Det faelles statusordforraad.
#
# Alle fem apps skal bruge de samme vaerdier, ellers kan de ikke vises i
# samme oversigt.
#
# FOERSTE felt er SharePoint-valgvaerdien. Den skrives af de fem domaeneapps
# og laeses af flowene - den maa IKKE oversaettes. Andet felt er etiketten,
# brugeren ser, og den er engelsk som resten af appen.
#
# step 1-5 baeres som tal i indekset, saa hubben kan tegne forloebet uden at
# kende domaenespecifikke statusvaerdier. step 0 = afsluttet uden oprettelse.
# ---------------------------------------------------------------------------
STATUS = [
    ("Kladde",          "Draft",          1, _t("state-neutral-fg"), _t("state-neutral-bg")),
    ("Indsendt",        "Submitted",      2, _t("state-info-fg"),    _t("state-info-bg")),
    ("UnderBehandling", "In progress",    3, _t("state-info-fg"),    _t("state-info-bg")),
    ("AfventerInfo",    "Awaiting info",  3, _t("state-warn-fg"),    _t("state-warn-bg")),
    ("KlarTilSAP",      "Ready for SAP",  4, _t("state-ok-fg"),      _t("state-ok-bg")),
    ("OprettetISAP",    "Created in SAP", 5, _t("state-ok-fg"),      _t("state-ok-bg")),
    ("Afvist",          "Rejected",       0, _t("state-error-fg"),   _t("state-error-bg")),
    ("Annulleret",      "Cancelled",      0, _t("state-neutral-fg"), _t("state-neutral-bg")),
]


def switch_on_status(field, fallback):
    """Bygger en Switch over statusvaerdien. Bruges til farver og tekst, saa
    ordforraadet kun staar eet sted."""
    parts = []
    for key, label, step, fg, bg in STATUS:
        parts.append(f'"{key}", {field(key, label, step, fg, bg)}')
    return "Switch(\n    ThisItem.Status.Value,\n    " + ",\n    ".join(parts) + f",\n    {fallback}\n)"


# ---------------------------------------------------------------------------
# Statusikonet i listen - et ikon og en farve pr. valgvaerdi. Samme
# noegler som STATUS; build_hub stopper, hvis de to ikke er enige.
# Farven er navnet paa en designtoken (hex-udgaven bruges i SVG'en).
# ---------------------------------------------------------------------------
_DOC = ("M14 2.5H7a2 2 0 0 0-2 2v15a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7.5L14 2.5Z "
        "M14 2.5v5h5 M9 13h6M9 17h6")
_CHECK = "M12 21.5a9.5 9.5 0 1 0 0-19 9.5 9.5 0 0 0 0 19Z M8 12.2l2.8 2.8L16 9.5"
_CLOCK = "M12 21.5a9.5 9.5 0 1 0 0-19 9.5 9.5 0 0 0 0 19Z M12 7v5l3.5 2"
_ALERT = "M12 21.5a9.5 9.5 0 1 0 0-19 9.5 9.5 0 0 0 0 19Z M12 7.5v5.5M12 16.5v.01"
_CROSS = "M12 21.5a9.5 9.5 0 1 0 0-19 9.5 9.5 0 0 0 0 19Z M9 9l6 6M15 9l-6 6"
# Oprettet i SAP: et skjold med flueben - "laast og faerdigt", og en anden
# FORM end Ready for SAP's cirkel, saa de to groenne kan skelnes.
_SHIELD = "M12 21.5s7.5-3.2 7.5-9.5V5.2L12 2.5 4.5 5.2V12c0 6.3 7.5 9.5 7.5 9.5Z M8.8 11.8l2.3 2.3 4.3-4.6"
# Annulleret: en overstreget cirkel - ikke Afvist's kryds i graat.
_BAN = "M12 21.5a9.5 9.5 0 1 0 0-19 9.5 9.5 0 0 0 0 19Z M5.3 5.3l13.4 13.4"

# Issue #74: hver status sin egen kombination af form og farve.
#   Draft, Submitted, In progress   den blaa familie - tre forskellige former
#   Submitted                       blaat flueben i blaa cirkel (var groent)
#   Ready for SAP                   groent flueben i groen cirkel (uaendret)
#   Created in SAP                  groent skjold med flueben
#   Awaiting info                   advarsel
#   Rejected / Cancelled            roedt kryds / graa overstreget cirkel
STATUS_ICON = {
    "Kladde":          (_DOC,    "state-info-fg"),
    "Indsendt":        (_CHECK,  "state-info-fg"),
    "UnderBehandling": (_CLOCK,  "state-info-fg"),
    "AfventerInfo":    (_ALERT,  "state-warn-fg"),
    "KlarTilSAP":      (_CHECK,  "state-ok-fg"),
    "OprettetISAP":    (_SHIELD, "state-ok-fg"),
    "Afvist":          (_CROSS,  "state-error-fg"),
    "Annulleret":      (_BAN,    "state-neutral-fg"),
}

# Ingen to statusser maa have samme ikon OG samme farve.
if len(set(STATUS_ICON.values())) != len(STATUS_ICON):
    raise SystemExit("hub_config: to statusser har samme ikon og farve")
