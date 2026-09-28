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
# "icon" er en SVG-sti i en 24 x 24 viewBox, tegnet med streg (ikke fyld).
DOMAINS = [
    {"key": "FunctionalLocation", "short": "FL",  "name": "Functional location",
     "token": "domain-fl",  "app": "functionallocation",
     "icon": "M12 21s7-5.2 7-11a7 7 0 1 0-14 0c0 5.8 7 11 7 11Z "
             "M12 12.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Z"},
    {"key": "Equipment",          "short": "EQ",  "name": "Equipment",
     "token": "domain-eq",  "app": "equipment",
     "icon": "M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 "
             "7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76Z"},
    {"key": "MeasuringPoint",     "short": "MP",  "name": "Measuring point",
     "token": "domain-mp",  "app": None,
     "icon": "M21.3 15.3a2.4 2.4 0 0 1 0 3.4l-2.6 2.6a2.4 2.4 0 0 1-3.4 0L2.7 8.7a2.41 2.41 "
             "0 0 1 0-3.4l2.6-2.6a2.41 2.41 0 0 1 3.4 0Z "
             "M14.5 12.5l2-2 M11.5 9.5l2-2 M8.5 6.5l2-2 M17.5 15.5l2-2"},
    {"key": "Material",           "short": "MAT", "name": "Material",
     "token": "domain-mat", "app": "material",
     "icon": "M12 3 2.5 8l9.5 5 9.5-5L12 3Z M2.5 12.5 12 17.5l9.5-5 M2.5 17 12 22l9.5-5"},
    {"key": "MaintenancePlan",    "short": "VHP", "name": "Maintenance plan",
     "token": "domain-vhp", "app": "vhplan",
     "icon": "M5 4.5h14a2 2 0 0 1 2 2V19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6.5a2 2 0 0 1 2-2Z "
             "M8 2.5v4M16 2.5v4M3 10h18"},
]

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

STATUS_ICON = {
    "Kladde":          (_DOC,   "state-info-fg"),
    "Indsendt":        (_CHECK, "state-ok-fg"),
    "UnderBehandling": (_CLOCK, "state-info-fg"),
    "AfventerInfo":    (_ALERT, "state-warn-fg"),
    "KlarTilSAP":      (_CHECK, "state-ok-fg"),
    "OprettetISAP":    (_CHECK, "state-ok-fg"),
    "Afvist":          (_CROSS, "state-error-fg"),
    "Annulleret":      (_CROSS, "state-neutral-fg"),
}
