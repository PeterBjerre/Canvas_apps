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

# --- appen ------------------------------------------------------------
APP_KEY = "material"
SCREEN = "ScreenMaterial"
TITLE = "Materials"
SUBTITLE = "Meld reservedele ind - leverandoer, pris og lager."

# Praefikset i noeglerne: MAT-000441.
PREFIX = "MAT"

DOMAIN = "Material"

# --- listen, som den hedder naar den er tilfoejet appen som datakilde --
L_ROWS = "MaterialItems"
L_INDEX = "MD_RequestIndex"
L_PLANTS = "PlantList"

C_TEXT = "MaterialDescription"
TEXT_LABEL = "Materialebeskrivelse"
TEXT_PLACEHOLDER = '"Kort tekst, hoejst 40 tegn"'

PLAY_URL = ("https://apps.powerapps.com/play/e/"
            "e0f8f822-d16a-e878-ba4e-fb42bc617e47"
            "/a/d7762919-c716-4bd0-9abd-24bab436221f")

# Landingssiden. De to domaeneapps aabnes af hubben med
# Launch(..., LaunchTarget.New) - altsaa i en NY fane, som en anden app.
# Back() kan derfor ikke foere tilbage: den navigerer mellem SKAERME i
# samme app, og der er kun een. Knappen skal aabne hubben.
#
# Samme id som apps.hub.app_id i tools/canvas_apps.json; build_all.py
# tjekker at de to ikke glider fra hinanden.
HUB_URL = ("https://apps.powerapps.com/play/e/e0f8f822-d16a-e878-ba4e-fb42bc617e47/a/f387047d-86af-4d6a-8370-afcf35939436")

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
    ("Hvor", [
        ("FunctionalLocation", "Func. location", "text", None),
    ]),
    ("Stamdata", [
        ("Manufacturer", "Fabrikant", "text", None),
        ("ModelNumber", "Modelnummer", "text", None),
        ("ManufacturerPartNo", "Fabrikantens varenr.", "text", None),
    ]),
    ("Leverandoer", [
        ("Supplier", "Leverandoer", "text", None),
        ("SupplierPartNo", "Leverandoerens varenr.", "text", None),
        ("DeliveringTime", "Leveringstid (dage)", "num", None),
    ]),
    ("Pris og lager", [
        ("Price", "Pris", "num", None),
        ("PriceUnit", "Prisenhed", "text", None),
        ("StockUnit", "Lagerenhed", "text", None),
        ("RecommendedStock", "Anbefalet lager", "num", None),
    ]),
    ("Klassificering", [
        ("StrategicPart", "Strategisk del", "text", None),
        ("WearPart", "Sliddel", "text", None),
    ]),
    ("Bemaerkninger", [
        ("LongText", "Langtekst", "long", None),
    ]),
]

PLANT_LABEL = "Plant"

LIST_COLS = [("MATERIALE", 0), ("FABRIKANTENS NR.", 160), ("LEVERANDOER", 150),
             ("PLANT", 70), ("STATUS", 90), ("FILER", 50), ("", 70)]
LIST_FIELDS = ["ManufacturerPartNo", "Supplier", "Plant"]

SEARCH_FIELDS = ["MaterialDescription", "FunctionalLocation",
                 "ManufacturerPartNo", "Supplier"]
