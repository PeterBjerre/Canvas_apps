# -*- coding: utf-8 -*-
"""
Alt det, der skiller Materials-appen fra Equipment-appen, staar HER.

Equipments og Materials er to apps, der deler byggeklodserne i
tools/domain_parts.py. Denne fil er appens kontrakt: felterne (SECTIONS),
listenavnet og praefikset. Kompositionen staar i assemble_screen.py og
*_parts.py (se SKILL.md "Hvem ejer hvad - Equipments og Materials").

FELTERNE ER KONTRAKTEN, IKKE ET VALG
------------------------------------
Hver linje i FIELDS svarer til en kolonne i SharePoint-listen
MaterialItems, som den staar i sharepoint/inspect/out/schema.md.
tools/check_datasources.py efterproever det ved hver bygning.

DET ER IKKE MM01
----------------
Der er hverken materialenummer, materialetype eller materialegruppe. Det,
appen samler ind, er reservedelsoplysninger - leverandoer, pris,
leveringstid, lager - knyttet til en eller flere funktionspladser. Saadan var
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
# MD_RequestIndex.AppUrl peger paa den SAMLEDE app - se
# tools/request_index.py (COMBINED_APP).

# Landingssiden. De to domaeneapps aabnes af hubben som en SELVSTAENDIG
# app - ikke som en skaerm i den samme. Back() kan derfor ikke foere
# tilbage: den navigerer mellem SKAERME, og der er kun een. Knappen skal
# aabne hubben med Launch.
#
# LaunchTarget.Replace, saa det sker i den fane, brugeren staar i.
HUB_URL = env.hub_url()

# FUNKTIONSPLADSERNE ER IKKE ET FELT I FORMULAREN (issue #228)
#
# Her stod FL_FIELD = "FunctionalLocation", og formularen havde FL-soegning,
# Add og Object List. Nu tilfoejes funktionspladserne paa den GEMTE raekke
# (Saved Rows -> Objects), og FunctionalLocation er en kolonne, appen
# laeser og skriver (READ_FIELDS + material_parts' extra_patch) - ikke et
# felt. Uden FL_FIELD henter og kopierer domain_parts ikke en FL ind i
# formularens vaelger, som ikke laengere findes.

# --- felterne ---------------------------------------------------------
# Se Equipment-appens domain_config.py for hvad "art" betyder.
#
# StockUnit, PriceUnit, StrategicPart og WearPart var dropdowns i den
# haandbyggede app, men samlingerne colStockUnits, colPriceUnits og
# colYesNo blev aldrig defineret. Derfor er de TEKST her og i SharePoint,
# indtil listerne findes.
#
# NoBomItem og RecommendedStock er fjernet fra formularen (issue #228).
# Kolonnerne bliver staaende i SharePoint med de vaerdier, der er gemt;
# appen hverken viser, henter eller skriver dem laengere. En raekke uden
# funktionspladser ER nu det, No BOM Item sagde.
#
# SEKTIONERNE ER GRUPPERING, IKKE OVERSKRIFTER. Formularen viser dem ikke
# laengere (issue #67); raekkefoelgen paa skaermen staar i
# material_parts.FORM_ORDER.
SECTIONS = [
    ("Master data", [
        ("Manufacturer", "Manufacturer", "text", None),
        ("ModelNumber", "Model number", "text", None),
        ("ManufacturerPartNo", "Manufacturer part no.", "text", None),
    ]),
    ("Supplier", [
        ("Supplier", "Supplier", "text", None),
        ("SupplierPartNo", "Supplier part no.", "text", None),
        ("DeliveringTime", "Delivery time (days)", "num", None),
    ]),
    ("Price and stock", [
        ("Price", "Price", "num", None),
        ("PriceUnit", "Price unit", "text", None),
        ("StockUnit", "Stock unit", "text", None),
    ]),
    # LAGER OG PLADS (issue #204). IsStockItem er en rigtig til/fra -
    # kolonnen er Boolean, og appen sender sand/falsk. Min og max kraeves
    # KUN for en lagervare (material_parts.save_fx), og de har ingen
    # standardvaerdi: et tal, ingen har valgt, ser ud som et oensket
    # lagerniveau. StorageBin foreslaas som "X" i formularen. De tre felter
    # vises kun for en lagervare (WHEN nedenfor, issue #228).
    ("Stock and storage", [
        ("IsStockItem", "Stock item", "bool", None),
        ("MinStock", "Min stock", "num", None),
        ("MaxStock", "Max stock", "num", None),
        ("StorageBin", "Storage bin", "text", None),
    ]),
    ("Classification", [
        # Ja/nej, skrevet som teksten "Yes"/"No" i den EKSISTERENDE
        # tekstkolonne (issue #204, Q2: Critical = Strategic). Gamle
        # vaerdier (Ja, Y, true) laeses som Yes og skrives ikke om.
        ("StrategicPart", "Strategic part", "choice", ["Yes", "No"]),
        ("WearPart", "Wear part", "text", None),
    ]),
    # YDERLIGERE OPLYSNINGER (issue #204) - alle valgfrie. Remarks hedder
    # "Purchase order text" paa skaermen (issue #228); kolonnen er den samme.
    ("Additional information", [
        ("Remarks", "Purchase order text", "long", None),
        ("MaintenanceOrderNo", "Maintenance order no.", "text", None),
        ("ReplacesExisting", "Replace existing material", "bool", None),
        ("ReplacedMaterialNo", "Replaced material no.", "text", None),
    ]),
]

# Kolonner appen LAESER, men formularen ikke skriver (issue #204):
#
#   FunctionalLocation  raekkens FOERSTE funktionsplads (issue #228: ikke
#       laengere et felt - se FL_FIELD ovenfor).
#   ObjectList/ObjectListJson  raekkens funktionspladser. De skrives af
#       gem (material_parts.OBJECT_PATCH), ikke af et felt.
#   ApprovalRequired           fastfrosset ved Submit - et filter, ikke et
#       resultat. Udfaldet staar i MD_ApprovalLog.
#   CreatedMaterialNo          materialenummeret fra SAP. Det findes
#       foerst, naar materialet er oprettet, og udfyldes derfor i Details
#       bagefter - aldrig i formularen foer Submit (Q16).
#   RequesterName/Email/SubmittedOn  rekvirenten og tidspunktet. De staar
#       paa raekken i SharePoint og vises i Details (issue #204).
READ_FIELDS = [
    ("FunctionalLocation", "Functional location", "text", None),
    ("ObjectList", "Object list", "long", None),
    ("ObjectListJson", "Object list (json)", "long", None),
    ("ApprovalRequired", "Approval required", "bool", None),
    ("CreatedMaterialNo", "Created material no.", "text", None),
    ("RequesterName", "Requested by", "text", None),
    ("RequesterEmail", "Requester e-mail", "text", None),
    ("SubmittedOn", "Submitted on", "date", None),
]

PLANT_LABEL = "Plant"

# BETINGEDE FELTER (issue #228, domain_parts.WHEN). Min, max og lagerplads
# vises kun for en lagervare, og det erstattede materialenummer kun, naar
# materialet erstatter et andet. Et skjult felt gemmes TOMT, saa en raekke,
# der ikke er lagervare, ikke sender et lagerniveau videre.
_STOCK = "Coalesce(varDomFIsStockItem, false)"
_REPLACES = "Coalesce(varDomFReplacesExisting, false)"
WHEN = {
    "MinStock": _STOCK,
    "MaxStock": _STOCK,
    "StorageBin": _STOCK,
    "ReplacedMaterialNo": _REPLACES,
}

# Listens kolonner staar i material_parts.SLOTS.

# Soegningen i Saved rows. ObjectList er med (issue #204), saa ALLE
# raekkens funktionspladser kan findes - ikke kun den foerste, der staar i
# FunctionalLocation.
SEARCH_FIELDS = ["MaterialDescription", "FunctionalLocation", "ObjectList",
                 "ManufacturerPartNo", "Supplier", "CreatedMaterialNo"]
