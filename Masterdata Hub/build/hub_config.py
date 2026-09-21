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
ENV_ID = "e0f8f822-d16a-e878-ba4e-fb42bc617e47"

# Flisernes stribefarve er en DESIGNTOKEN, ikke et tal. Otte af de ni
# statusfarver herunder var i forvejen vaerdier, der havde et navn i
# gen_screen.py - de var bare skrevet af som tal, saa de ikke fulgte med,
# naar nogen aendrede navnet. Se tools/design_tokens.py.
DOMAINS = [
    {"key": "FunctionalLocation", "short": "FL",  "name": "Functional location",
     "color": _t("domain-fl"),  "app_id": None},
    # "Equipments" i solutionen - IKKE den aeldre app udenfor
    # (dd9544e2-a0aa-4713-a076-7637080a40fc), som flisen pegede paa,
    # indtil den nye havde et id. De to skal blive ved med at foelges ad
    # med tools/canvas_apps.json: deployer builderne eet sted og aabner
    # flisen et andet, ser appen bare forkert ud for brugeren.
    {"key": "Equipment",          "short": "EQ",  "name": "Equipment",
     "color": _t("domain-eq"),
     "app_id": "24bf3bbc-601f-480d-a8fe-7cd3180906d1"},
    {"key": "MeasuringPoint",     "short": "MP",  "name": "Measuring point",
     "color": _t("domain-mp"),  "app_id": None},
    {"key": "Material",           "short": "MAT", "name": "Material",
     "color": _t("domain-mat"),
     "app_id": "d7762919-c716-4bd0-9abd-24bab436221f"},
    {"key": "MaintenancePlan",    "short": "VHP", "name": "Maintenance plan",
     "color": _t("domain-vhp"),
     "app_id": "11fa8d90-868a-45a4-ba23-28f2cf0671a2"},
]

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
    _d["url"] = PLAY.format(env=ENV_ID, app=_d["app_id"]) if _d["app_id"] else ""


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
