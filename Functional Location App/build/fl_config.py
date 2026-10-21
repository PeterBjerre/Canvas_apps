# -*- coding: utf-8 -*-
"""
Alt, der er Functional Location-appens eget: navne, lister, noegler.

REGLERNE STAAR IKKE HER
-----------------------
De staar i html/app-functional-location.js og html/fl-rule-engine.js, og
de er foldet ud til fl_rules.generated.json af tools/fl/harness.js. Skal en
regel aendres, aendres den i JS'en, og planen genereres igen:

    node tools/fl/harness.js plan
    node tools/fl/harness.js test

Kontrakten - hvilke regler der findes, og hvor de er implementeret - er
docs/31-functional-location-regler.md.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "tools"))
import env_config as env

# --- appen ------------------------------------------------------------
APP_KEY = "functionallocation"
SCREEN = "ScreenFunctionalLocation"
# Titlen er HTML-sidens <h1> (functional-location.html:40).
TITLE = "Functional Location - Spool"
SUBTITLE = "Verify KKS codes, classes and spool fields - and pass the request on."

# Noeglen i MD_RequestIndex og hub_config.DOMAINS. Ordret, ellers faar
# raekken hverken farve eller navn paa landingssiden.
DOMAIN = "FunctionalLocation"
PREFIX = "FL"

# --- listerne, som de hedder naar de er tilfoejet som datakilder -------
# Provisioneret af sharepoint/provision/Provision-FunctionalLocationLists.ps1.
# Power Fx binder paa VISNINGSNAVN: Title hedder RequestNo / RowGuid /
# KeyValue.
L_REQ = "FunctionalLocationRequests"
L_ITEMS = "FunctionalLocationItems"
L_KEYS = "MD_FLKey"
L_INDEX = "MD_RequestIndex"

# MD_RequestIndex.AppUrl peger paa den SAMLEDE app - se
# tools/request_index.py (COMBINED_APP).
HUB_URL = env.hub_url()

# --- reglerne ------------------------------------------------------------
RULES_JSON = os.path.join(HERE, "fl_rules.generated.json")


def rules():
    with open(RULES_JSON, encoding="utf-8") as f:
        return json.load(f)


# --- sidepanelet (raekkens editor, issue #278) ---------------------------
# Panelets sektioner i SAMME raekkefoelge som raekkens kolonner:
#   Functional Location | Description | StrIndicator | Class |
#   Class data | Room | Sort field | ABC indicator | ATEX |
#   Manufacturer | Warranty
# og derefter TRM. Class og TRM er reglernes Section; de andre deler
# Master-felterne op. Status-sektionen (SAP status, Info, User status,
# System status) vises ikke i panelet, og GIV_EXT/WCM (Section "Ext") vises
# ingen steder i appen (issue #308) - vaerdierne bliver i colFlVals og i
# SharePoint, de kan bare ikke ses eller rettes her.
PANEL_SECTIONS = [
    ("Main", "Functional location"),
    ("Class", "Class characteristics"),
    ("Loc", "Location and indicators"),
    ("Mfr", "Manufacturer"),
    ("War", "Warranty"),
    ("TRM", "TRM"),
]
# Reglernes sektioner, som sidepanelet ikke viser.
HIDDEN_SECTIONS = ("Status", "Ext")
# StrIndicator og Class (issue #467: foer "KKS type" og "Assigned class")
# staar paa EEN linje sidst i Functional
# location-sektionen, lige foer Class data (issue #308) - et eget gitter
# med to kolonner (een paa smalle skaerme), uden egen overskrift.
PANEL_SUB = {"Main": "Kks"}
# Master-felterne: (felt, sektion, etiket). Etiketten er raekkens
# kolonneoverskrift, hvor feltet har sin egen kolonne (fl_parts.V_FIXED -
# tests/test_fl_panel_order.py holder dem ens). Raekkefoelgen her ER
# raekkefoelgen i sektionen. ASSIGNED CLASS er ikke et spool-felt, men
# raekkens klasse - kun til visning.
PANEL_FIELDS = [
    ("FUNCTIONAL LOCATION", "Main", "Functional Location"),
    ("DESCRIPTION", "Main", "Description"),
    ("STRINDICATOR", "Kks", "StrIndicator"),
    ("ASSIGNED CLASS", "Kks", "Class"),
    ("ROOM", "Loc", "Room"),
    ("SORT FIELD", "Loc", "Sort field"),
    ("ABC INDIC.", "Loc", "ABC indicator"),
    ("ATEX", "Loc", "ATEX"),
    ("MANUFACTURER", "Mfr", "Manufacturer"),
    ("MODEL NUMBER", "Mfr", "Model Number"),
    ("MANUFACTURER PART NUMBER", "Mfr", "Manufacturer Part Number"),
    ("MANUFACTURER SERIAL NUMBER", "Mfr", "Manufacturer Serial Number"),
    ("WARRANTY START", "War", "Warranty Start"),
    ("WARRANTY END", "War", "Warranty End"),
]
# Raekkens eget felt - ikke et spool-felt i colFlColumns.
PANEL_ROW_ONLY = "ASSIGNED CLASS"
