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
import request_index as ri

# Navnet paa listen som den hedder, naar den er tilfoejet appen som datakilde.
LIST = ri.LIST

# Power Fx binder SharePoint-kolonner paa VISNINGSNAVN, ikke internt navn.
# Provisioneringsscriptet doeber den indbyggede Title-kolonne om til
# "RequestNo", saa listen er laesbar for dem der aabner den direkte - og
# derfor skal appen ogsaa kalde den RequestNo. Aendrer du navnet i
# Provision-RequestIndex.ps1, skal det aendres her samtidig.
COL_NO = ri.COL_NO

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
    {"key": "MaintenancePlan",    "short": "VHP", "name": "Maintenance plan",
     "token": "domain-vhp", "app": "vhplan", "icon_key": "vhplan"},
    {"key": "Material",           "short": "MAT", "name": "Material",
     "token": "domain-mat", "app": "material", "icon_key": "material"},
    {"key": "Equipment",          "short": "EQ",  "name": "Equipment",
     "token": "domain-eq",  "app": "equipment", "icon_key": "equipment"},
    {"key": "MeasuringPoint",     "short": "MP",  "name": "Measuring point",
     "token": "domain-mp",  "app": "measuringpoint", "icon_key": "measuringpoint"},
]

# Ikonerne er de FAELLES (tools/icons.py, issue #74) - de samme som i
# sidebaren og sideoverskrifterne. Measuring Points lineal er spejlet, saa
# den peger samme vej som Equipments skruenoegle (issue #70).
for _d in DOMAINS:
    if _d["key"] not in ri.DOMAINS:
        raise SystemExit("hub_config: ukendt domaene '%s' - se tools/request_index.py" % _d["key"])
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
# Vaerdi, etiket og trin kommer fra tools/request_index.py - det samme
# ordforraad, som domaeneapperne skriver med. Her tilfoejes kun farverne.
_STATUS_COLORS = {
    "Kladde":          ("state-neutral-fg", "state-neutral-bg"),
    "Indsendt":        ("state-info-fg",    "state-info-bg"),
    "UnderBehandling": ("state-violet-fg",  "state-violet-bg"),
    "AfventerInfo":    ("state-warn-fg",    "state-warn-bg"),
    "KlarTilSAP":      ("state-ok-fg",      "state-ok-bg"),
    "OprettetISAP":    ("state-lime-fg",    "state-lime-bg"),
    "Afvist":          ("state-error-fg",   "state-error-bg"),
    "Annulleret":      ("state-rose-fg",    "state-rose-bg"),
}
if set(_STATUS_COLORS) != {k for k, _l, _s in ri.STATUS}:
    raise SystemExit("hub_config: _STATUS_COLORS og request_index.STATUS har ikke "
                     "de samme noegler.")
STATUS = [(k, label, step, _t(_STATUS_COLORS[k][0]), _t(_STATUS_COLORS[k][1]))
          for k, label, step in ri.STATUS]



# ---------------------------------------------------------------------------
# Statusikonet i listen - et ikon og en farve pr. valgvaerdi. Samme
# noegler som STATUS; build_hub stopper, hvis de to ikke er enige.
# Farven er navnet paa en designtoken (hex-udgaven bruges i SVG'en).
# ---------------------------------------------------------------------------
# Stierne staar i tools/icons.py (STATUS_*, issue #139), saa samme status
# har samme form overalt.
#   Draft           graat dokument            Submitted     blaa papirflyver
#   In progress     violet halvfyldt cirkel   Awaiting info orange advarsel
#   Ready for SAP   groent flueben            Created in SAP lime skjold
#   Rejected        roedt kryds               Cancelled     rose overstreget cirkel
# In progress var et ur; uret betyder nu tid (Stuck-filteret, aktivitet),
# og "paabegyndt" er den halvt fyldte cirkel.
STATUS_ICON = {
    "Kladde":          (icons.STATUS_DRAFT,     "state-neutral-fg"),
    "Indsendt":        (icons.STATUS_SUBMITTED, "state-info-fg"),
    "UnderBehandling": (icons.STATUS_PROGRESS,  "state-violet-fg"),
    "AfventerInfo":    (icons.STATUS_AWAITING,  "state-warn-fg"),
    "KlarTilSAP":      (icons.STATUS_READY,     "state-ok-fg"),
    "OprettetISAP":    (icons.STATUS_CREATED,   "state-lime-fg"),
    "Afvist":          (icons.STATUS_REJECTED,  "state-error-fg"),
    "Annulleret":      (icons.STATUS_CANCELLED, "state-rose-fg"),
}

# Ingen to statusser maa have samme ikon OG samme farve.
if len(set(STATUS_ICON.values())) != len(STATUS_ICON):
    raise SystemExit("hub_config: to statusser har samme ikon og farve")
