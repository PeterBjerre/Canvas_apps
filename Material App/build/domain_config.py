# -*- coding: utf-8 -*-
"""
Alt det, der skiller Materials-appen fra Equipment-appen, staar HER.

De to apps er den samme app. Samme skaerm, samme gem, samme dokumentrude -
kun felterne og listenavnet er forskellige. Derfor er build_domain.py,
attflows.py, assemble_screen.py og generate_app_onstart.py ORDRET ens i de
to build-mapper, og kun denne fil er forskellig. tools/build_all.py
tjekker, at de bliver ved med at vaere ens.

FELTERNE ER KONTRAKTEN, IKKE ET VALG
------------------------------------
Hver linje i FIELDS svarer til en kolonne i SharePoint-listen
MaterialItems, som den staar i sharepoint/inspect/out/schema.md.
tools/check_datasources.py efterproever det ved hver bygning.

DET ER IKKE MM01
----------------
Der er hverken materialenummer, materialetype eller materialegruppe. Det,
appen samler ind, er reservedelsoplysninger - leverandoer, pris,
leveringstid, anbefalet lager - knyttet til en funktionsplads. Saadan var
formularen i Studio, og saadan er listen.
"""
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "tools"))
import env_config as env

# --- appen ------------------------------------------------------------
APP_KEY = "material"
SCREEN = "ScreenMaterial"
TITLE = "Materials"
SUBTITLE = "Report spare parts - supplier, price and stock."

# Praefikset i noeglerne: MAT-000441.
PREFIX = "MAT"

DOMAIN = "Material"

# --- listen, som den hedder naar den er tilfoejet appen som datakilde --
L_ROWS = "MaterialItems"
L_INDEX = "MD_RequestIndex"
L_PLANTS = "PlantList"

C_TEXT = "MaterialDescription"
TEXT_LABEL = "Material description"
TEXT_PLACEHOLDER = '"Short text, max 40 characters"'

# Play-URL'erne kommer fra tools/canvas_apps.json via env_config. De stod
# foer skrevet af her, og build_all.py havde 60 linjers regex til at
# tjekke, at de tre kopier ikke gled fra hinanden. Se tools/env_config.py.
#
# PLAY_URL skrives i MD_RequestIndex.AppUrl, saa hubbens "Open" lander paa
# den rigtige indmelding.
PLAY_URL = env.play_url("material")

# Landingssiden. De to domaeneapps aabnes af hubben som en SELVSTAENDIG
# app - ikke som en skaerm i den samme. Back() kan derfor ikke foere
# tilbage: den navigerer mellem SKAERME, og der er kun een. Knappen skal
# aabne hubben med Launch.
#
# LaunchTarget.Replace, saa det sker i den fane, brugeren staar i.
HUB_URL = env.hub_url()

# Feltet der skal have FL-SOEGNING i stedet for et tekstfelt.
# Konstruktionen er VH-plan-appens - soegefelt, soegeknap og dropdown -
# kopieret i build_flsearch.py. Flowet er allerede datakilde i begge apps.
FL_FIELD = "FunctionalLocation"

# --- felterne ---------------------------------------------------------
# Se Equipment-appens domain_config.py for hvad "art" betyder.
#
# StockUnit, PriceUnit, StrategicPart og WearPart var dropdowns i den
# haandbyggede app, men samlingerne colStockUnits, colPriceUnits og
# colYesNo blev aldrig defineret. Derfor er de TEKST her og i SharePoint,
# indtil listerne findes.
SECTIONS = [
    ("Where", [
        ("FunctionalLocation", "Func. location", "text", None),
    ]),
    ("Stamdata", [
        ("Manufacturer", "Manufacturer", "text", None),
        ("ModelNumber", "Modelnummer", "text", None),
        ("ManufacturerPartNo", "Manufacturer part no.", "text", None),
    ]),
    ("Supplier", [
        ("Supplier", "Supplier", "text", None),
        ("SupplierPartNo", "Leverandoerens varenr.", "text", None),
        ("DeliveringTime", "Leveringstid (dage)", "num", None),
    ]),
    ("Price and stock", [
        ("Price", "Price", "num", None),
        ("PriceUnit", "Prisenhed", "text", None),
        ("StockUnit", "Lagerenhed", "text", None),
        ("RecommendedStock", "Recommended stock", "num", None),
    ]),
    ("Klassificering", [
        ("StrategicPart", "Strategic part", "text", None),
        ("WearPart", "Sliddel", "text", None),
    ]),
    ("Bemaerkninger", [
        ("LongText", "Langtekst", "long", None),
    ]),
]

PLANT_LABEL = "Plant"

LIST_COLS = [("MATERIAL", 0), ("MFR. PART NO.", 130), ("SUPPLIER", 120),
             ("PLANT", 55), ("STATUS", 75), ("FILES", 40), ("", 60)]
LIST_FIELDS = ["ManufacturerPartNo", "Supplier", "Plant"]

SEARCH_FIELDS = ["MaterialDescription", "FunctionalLocation",
                 "ManufacturerPartNo", "Supplier"]
