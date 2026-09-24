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

# Play-URL'en skrives i MD_RequestIndex.AppUrl, saa hubbens "Open" lander
# paa den rigtige anmodning. Tom, indtil appen har et app_id i
# tools/canvas_apps.json - se docs/31, "Deploy".
PLAY_URL = env.play_url(APP_KEY)
HUB_URL = env.hub_url()

# --- reglerne ------------------------------------------------------------
RULES_JSON = os.path.join(HERE, "fl_rules.generated.json")


def rules():
    with open(RULES_JSON, encoding="utf-8") as f:
        return json.load(f)
