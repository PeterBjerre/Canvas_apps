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
DOMAINS = [
    {"key": "FunctionalLocation", "short": "FL",  "name": "Functional location",
     "color": _t("domain-fl"),  "app": None},
    {"key": "Equipment",          "short": "EQ",  "name": "Equipment",
     "color": _t("domain-eq"),  "app": "equipment"},
    {"key": "MeasuringPoint",     "short": "MP",  "name": "Measuring point",
     "color": _t("domain-mp"),  "app": None},
    {"key": "Material",           "short": "MAT", "name": "Material",
     "color": _t("domain-mat"), "app": "material"},
    {"key": "MaintenancePlan",    "short": "VHP", "name": "Maintenance plan",
     "color": _t("domain-vhp"), "app": "vhplan"},
]

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
