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
    {"key": "FunctionalLocation", "short": "FL",  "name": "Functional location",
     "color": "RGBA(0, 103, 174, 1)",  "url": ""},
    {"key": "Equipment",          "short": "EQ",  "name": "Equipment",
     "color": "RGBA(14, 124, 134, 1)", "url": ""},
    {"key": "MeasuringPoint",     "short": "MP",  "name": "Measuring point",
     "color": "RGBA(21, 127, 92, 1)",  "url": ""},
    {"key": "Material",           "short": "MAT", "name": "Material",
     "color": "RGBA(154, 99, 0, 1)",   "url": ""},
    {"key": "MaintenancePlan",    "short": "VHP", "name": "Maintenance plan",
     "color": "RGBA(109, 74, 166, 1)",
     "url": "https://apps.powerapps.com/play/e/e0f8f822-d16a-e878-ba4e-fb42bc617e47"
            "/a/11fa8d90-868a-45a4-ba23-28f2cf0671a2"},
]

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
