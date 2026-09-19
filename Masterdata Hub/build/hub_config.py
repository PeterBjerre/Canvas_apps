# -*- coding: utf-8 -*-
"""
Alt der skal tilpasses, staar HER og kun her.

Landingssiden har EEN datakilde: SharePoint-listen MD_RequestIndex. De fem
domaeneapps skriver hver en opsummeringsraekke til den fra deres submit-flow.
Se docs/07-landingsside.md.
"""

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

DOMAINS = [
    {"key": "FunctionalLocation", "short": "FL",  "name": "Functional location",
     "color": "RGBA(0, 103, 174, 1)",  "app_id": None},
    # "Equipments" i solutionen - IKKE den aeldre app udenfor
    # (dd9544e2-a0aa-4713-a076-7637080a40fc), som flisen pegede paa,
    # indtil den nye havde et id. De to skal blive ved med at foelges ad
    # med tools/canvas_apps.json: deployer builderne eet sted og aabner
    # flisen et andet, ser appen bare forkert ud for brugeren.
    {"key": "Equipment",          "short": "EQ",  "name": "Equipment",
     "color": "RGBA(14, 124, 134, 1)",
     "app_id": "24bf3bbc-601f-480d-a8fe-7cd3180906d1"},
    {"key": "MeasuringPoint",     "short": "MP",  "name": "Measuring point",
     "color": "RGBA(21, 127, 92, 1)",  "app_id": None},
    {"key": "Material",           "short": "MAT", "name": "Material",
     "color": "RGBA(154, 99, 0, 1)",
     "app_id": "d7762919-c716-4bd0-9abd-24bab436221f"},
    {"key": "MaintenancePlan",    "short": "VHP", "name": "Maintenance plan",
     "color": "RGBA(109, 74, 166, 1)",
     "app_id": "11fa8d90-868a-45a4-ba23-28f2cf0671a2"},
]

PLAY = "https://apps.powerapps.com/play/e/{env}/a/{app}"

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
C_MUTED_ = "RGBA(89, 102, 122, 1)"
STATUS = [
    ("Kladde",          "Draft",          1, C_MUTED_,               "RGBA(228, 233, 241, 1)"),
    ("Indsendt",        "Submitted",      2, "RGBA(0, 83, 140, 1)",  "RGBA(222, 240, 252, 1)"),
    ("UnderBehandling", "In progress",    3, "RGBA(0, 83, 140, 1)",  "RGBA(222, 240, 252, 1)"),
    ("AfventerInfo",    "Awaiting info",  3, "RGBA(138, 90, 0, 1)",  "RGBA(253, 243, 226, 1)"),
    ("KlarTilSAP",      "Ready for SAP",  4, "RGBA(21, 127, 92, 1)", "RGBA(232, 245, 238, 1)"),
    ("OprettetISAP",    "Created in SAP", 5, "RGBA(21, 127, 92, 1)", "RGBA(232, 245, 238, 1)"),
    ("Afvist",          "Rejected",       0, "RGBA(179, 50, 60, 1)", "RGBA(253, 236, 236, 1)"),
    ("Annulleret",      "Cancelled",      0, C_MUTED_,               "RGBA(228, 233, 241, 1)"),
]


def switch_on_status(field, fallback):
    """Bygger en Switch over statusvaerdien. Bruges til farver og tekst, saa
    ordforraadet kun staar eet sted."""
    parts = []
    for key, label, step, fg, bg in STATUS:
        parts.append(f'"{key}", {field(key, label, step, fg, bg)}')
    return "Switch(\n    ThisItem.Status.Value,\n    " + ",\n    ".join(parts) + f",\n    {fallback}\n)"
