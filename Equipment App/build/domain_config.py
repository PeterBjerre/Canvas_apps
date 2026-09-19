# -*- coding: utf-8 -*-
"""
Alt det, der skiller Equipment-appen fra Materials-appen, staar HER.

De to apps er den samme app. Samme skaerm, samme gem, samme
dokumentrude - kun felterne og listenavnene er forskellige. Derfor er
build_domain.py, attflows.py, assemble_screen.py og
generate_app_onstart.py ORDRET ens i de to build-mapper, og kun denne fil
er forskellig. tools/build_all.py tjekker, at de bliver ved med at vaere
ens.

FELTERNE ER ET FORSLAG
----------------------
Da det her blev skrevet, var appen i Studio TOM - een blank Screen1, ingen
kontroller, ingen datakilder. Der var altsaa ikke noget at laese sig til.
Felterne nedenfor er SAP's udstyrsstamdata (IE01), grupperet som fanerne i
transaktionen, og de er valgt her - ikke aftalt.

Skal der et felt til eller fra, er det EN linje i FIELDS og EN linje i
Provision-EqMatLists.ps1. Skaermen, skemaet og gem-logikken foelger med af
sig selv, fordi de alle tre laeser den samme liste.
"""

# --- appen ------------------------------------------------------------
APP_KEY = "equipment"
SCREEN = "ScreenEquipment"
TITLE = "Equipment"
SUBTITLE = "Report equipment master data for SAP."

# Praefikset i indmeldingsnummeret: EQ-000912.
PREFIX = "EQ"

# Domaeneteksten i MD_RequestIndex. SKAL vaere ordret den samme som i
# hub_config.py og Provision-RequestIndex.ps1 - ellers faar raekken
# hverken farve eller navn paa landingssiden.
DOMAIN = "Equipment"

# --- listerne, som de hedder naar de er tilfoejet appen som datakilde --
L_REQ = "EquipmentRequests"
L_ITEM = "EquipmentItems"
L_INDEX = "MD_RequestIndex"
L_PLANTS = "PlantList"

# Play-URL'en, appen skriver i MD_RequestIndex.AppUrl, saa "Open" paa
# landingssiden lander paa den rigtige indmelding og ikke bare i appen.
#
# App-id'et staar IKKE i solution-eksporten - det Id, der staar i
# Properties.json, er dokumentets, ikke app'ens. Id'et nedenfor er
# app'ens, hentet i Studio-URL'en:
#
#   https://make.powerapps.com/e/<env>/canvas/?action=edit&app-id=...%2Fapps%2F<app_id>
#
# eller med:  pac canvas list
#
# Formatet er:
#   https://apps.powerapps.com/play/e/<env>/a/<app_id>
#
# Appen haenger selv "?reqid=" & varDomGuid paa. Den SKAL vaere det
# samme id som i tools/canvas_apps.json og hub_config.py - ellers
# aabner hubbens "Open" en anden app end den, raekken blev skrevet i.
PLAY_URL = "https://apps.powerapps.com/play/e/e0f8f822-d16a-e878-ba4e-fb42bc617e47/a/24bf3bbc-601f-480d-a8fe-7cd3180906d1"

# Provisioneringen omdoeber Title. Power Fx binder paa VISNINGSNAVN, saa et
# Patch med { Title: ... } rammer ved siden af.
C_ITEM_TEXT = "EquipmentText"
C_REQ_NO = "RequestNo"

# --- felterne ---------------------------------------------------------
# (kolonne, etiket, art, bredde, valgmuligheder)
#
#   art: "text"   enkeltlinjet tekst
#        "num"    tal
#        "date"   dato
#        "choice" SharePoint-valgkolonne  -> skrives som { Value: ... }
#        "bool"   ja/nej
#        "long"   flerlinjet tekst
#
# Arten bestemmer BAADE kontrollen paa skaermen og formen i Patch. Det er
# den eneste maade at undgaa, at de to kommer til at sige noget
# forskelligt om det samme felt.
SECTIONS = [
    ("What should happen", [
        ("ChangeType", "Change type", "choice", 200,
         ["Create", "Change", "Dismantle", "Scrap"]),
        ("EquipmentNo", "Equipment no.", "text", 200, None),
    ]),
    ("General", [
        ("EquipmentCategory", "Category", "choice", 140, ["M", "S", "P", "Q", "F"]),
        ("TechObjectType", "Object type", "text", 160, None),
        ("InventoryNo", "Inventory no.", "text", 160, None),
        ("SerialNumber", "Serial no.", "text", 160, None),
        ("ManufacturerName", "Manufacturer", "text", 220, None),
        ("ManufPartNo", "Model / part no.", "text", 200, None),
        ("ManufSerialNo", "Manuf. serial no.", "text", 200, None),
        ("ManufCountry", "Country", "text", 120, None),
        ("ConstructionYear", "Year built", "num", 120, None),
        ("ConstructionMonth", "Month built", "num", 120, None),
        ("SizeDimension", "Size / dimension", "text", 180, None),
        ("Weight", "Weight", "num", 120, None),
        ("WeightUnit", "Unit", "text", 100, None),
        ("StartUpDate", "Start-up date", "date", 160, None),
        ("AcquisitionValue", "Acquisition value", "num", 160, None),
        ("Currency", "Currency", "text", 100, None),
    ]),
    ("Location", [
        ("MaintPlant", "Maintenance plant", "text", 160, None),
        ("Location", "Location", "text", 160, None),
        ("Room", "Room", "text", 140, None),
        ("PlantSection", "Plant section", "text", 140, None),
        ("WorkCenter", "Work centre", "text", 160, None),
        ("ABCIndicator", "ABC", "choice", 100, ["A", "B", "C"]),
        ("SortField", "Sort field", "text", 160, None),
    ]),
    ("Organisation", [
        ("PlanningPlant", "Planning plant", "text", 160, None),
        ("PlannerGroup", "Planner group", "text", 160, None),
        ("MainWorkCenter", "Main work centre", "text", 160, None),
        ("CatalogProfile", "Catalog profile", "text", 160, None),
        ("BusinessArea", "Business area", "text", 140, None),
        ("CostCenter", "Cost centre", "text", 160, None),
        ("CompanyCode", "Company code", "text", 140, None),
        ("WBSElement", "WBS element", "text", 180, None),
    ]),
    ("Structure", [
        ("FunctionalLocation", "Functional location", "text", 260, None),
        ("SuperiorEquipment", "Superior equipment", "text", 200, None),
        ("PositionInFl", "Position", "text", 120, None),
    ]),
]

# Den obligatoriske tekst paa posten - listens omdoebte Title.
ITEM_TEXT_LABEL = "Equipment text"
ITEM_TEXT_PLACEHOLDER = '"Short text, max 40 characters"'

# Kolonner i postoversigten. Foerste er altid teksten.
LIST_COLS = [("EQUIPMENT", 0), ("CATEGORY", 100), ("FUNCT. LOCATION", 220),
             ("CHANGE", 110), ("FILES", 70)]
LIST_FIELDS = ["EquipmentCategory", "FunctionalLocation", "ChangeType"]
