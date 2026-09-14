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
# url  = satellittens play-URL. Udfyldes naar appen findes; indtil da staar
#        tile'en som "Kommer snart" og kan ikke aabnes.
#        Formatet er:  https://apps.powerapps.com/play/e/<env>/a/<appid>
# ---------------------------------------------------------------------------
DOMAINS = [
    {"key": "FunctionalLocation", "short": "FL",  "name": "Funktionsplads",
     "color": "RGBA(0, 103, 174, 1)",  "url": ""},
    {"key": "Equipment",          "short": "EQ",  "name": "Udstyr",
     "color": "RGBA(14, 124, 134, 1)", "url": ""},
    {"key": "MeasuringPoint",     "short": "MP",  "name": "Maalepunkt",
     "color": "RGBA(21, 127, 92, 1)",  "url": ""},
    {"key": "Material",           "short": "MAT", "name": "Materiale",
     "color": "RGBA(154, 99, 0, 1)",   "url": ""},
    {"key": "MaintenancePlan",    "short": "VHP", "name": "VH-plan",
     "color": "RGBA(109, 74, 166, 1)",
     "url": "https://apps.powerapps.com/play/e/e0f8f822-d16a-e878-ba4e-fb42bc617e47"
            "/a/11fa8d90-868a-45a4-ba23-28f2cf0671a2"},
]

# ---------------------------------------------------------------------------
# Det faelles statusordforraad. Alle fem apps skal bruge de samme vaerdier,
# ellers kan de ikke vises i samme oversigt.
#
# step 1-5 baeres som tal i indekset, saa hubben kan tegne forloebet uden at
# kende domaenespecifikke statusvaerdier. step 0 = afsluttet uden oprettelse.
# ---------------------------------------------------------------------------
C_MUTED_ = "RGBA(89, 102, 122, 1)"
STATUS = [
    ("Kladde",          "Kladde",           1, C_MUTED_,                 "RGBA(228, 233, 241, 1)"),
    ("Indsendt",        "Indsendt",         2, "RGBA(0, 83, 140, 1)",    "RGBA(222, 240, 252, 1)"),
    ("UnderBehandling", "Under behandling", 3, "RGBA(0, 83, 140, 1)",    "RGBA(222, 240, 252, 1)"),
    ("AfventerInfo",    "Afventer info",    3, "RGBA(138, 90, 0, 1)",    "RGBA(253, 243, 226, 1)"),
    ("KlarTilSAP",      "Klar til SAP",     4, "RGBA(21, 127, 92, 1)",   "RGBA(232, 245, 238, 1)"),
    ("OprettetISAP",    "Oprettet i SAP",   5, "RGBA(21, 127, 92, 1)",   "RGBA(232, 245, 238, 1)"),
    ("Afvist",          "Afvist",           0, "RGBA(179, 50, 60, 1)",   "RGBA(253, 236, 236, 1)"),
    ("Annulleret",      "Annulleret",       0, C_MUTED_,                 "RGBA(228, 233, 241, 1)"),
]


def switch_on_status(field, fallback):
    """Bygger en Switch over statusvaerdien. Bruges til farver og tekst, saa
    ordforraadet kun staar eet sted."""
    parts = []
    for key, label, step, fg, bg in STATUS:
        parts.append(f'"{key}", {field(key, label, step, fg, bg)}')
    return "Switch(\n    ThisItem.Status.Value,\n    " + ",\n    ".join(parts) + f",\n    {fallback}\n)"
