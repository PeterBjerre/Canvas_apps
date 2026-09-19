# -*- coding: utf-8 -*-
"""
Alt det, der skiller Materials-appen fra Equipment-appen, staar HER.

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
Felterne nedenfor er SAP's materialestamdata (MM01), grupperet som de
visninger, der skal udfyldes for et reservedelsmateriale, og de er valgt
her - ikke aftalt.

Skal der et felt til eller fra, er det EN linje i SECTIONS og EN linje i
Provision-EqMatLists.ps1. Skaermen, skemaet og gem-logikken foelger med af
sig selv, fordi de alle tre laeser den samme liste.
"""

# --- appen ------------------------------------------------------------
APP_KEY = "material"
SCREEN = "ScreenMaterial"
TITLE = "Materials"
SUBTITLE = "Report material master data for SAP."

# Praefikset i indmeldingsnummeret: MAT-001233.
PREFIX = "MAT"

# Domaeneteksten i MD_RequestIndex. SKAL vaere ordret den samme som i
# hub_config.py og Provision-RequestIndex.ps1.
DOMAIN = "Material"

# --- listerne, som de hedder naar de er tilfoejet appen som datakilde --
L_REQ = "MaterialRequests"
L_ITEM = "MaterialItems"
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
PLAY_URL = "https://apps.powerapps.com/play/e/e0f8f822-d16a-e878-ba4e-fb42bc617e47/a/d7762919-c716-4bd0-9abd-24bab436221f"

# Provisioneringen omdoeber Title. Power Fx binder paa VISNINGSNAVN, saa et
# Patch med { Title: ... } rammer ved siden af.
C_ITEM_TEXT = "MaterialText"
C_REQ_NO = "RequestNo"

# --- felterne ---------------------------------------------------------
# Se Equipment-appens domain_config.py for hvad "art" betyder - listen er
# den samme, og den bestemmer BAADE kontrollen paa skaermen og formen i
# Patch.
SECTIONS = [
    ("What should happen", [
        ("ChangeType", "Change type", "choice", 200,
         ["Create", "Change", "Extend", "Block"]),
        ("MaterialNo", "Material no.", "text", 200, None),
    ]),
    ("Basic data", [
        ("MaterialType", "Material type", "choice", 160,
         ["ERSA", "HIBE", "NLAG", "UNBW", "DIEN", "HALB", "FERT", "ROH"]),
        ("IndustrySector", "Industry sector", "choice", 140, ["M", "C", "P", "A"]),
        ("MaterialGroup", "Material group", "text", 160, None),
        ("BaseUnit", "Base unit", "text", 120, None),
        ("OldMaterialNo", "Old material no.", "text", 180, None),
        ("ManufacturerName", "Manufacturer", "text", 220, None),
        ("ManufPartNo", "Manuf. part no.", "text", 200, None),
        ("EAN", "EAN", "text", 160, None),
        ("GrossWeight", "Gross weight", "num", 140, None),
        ("NetWeight", "Net weight", "num", 140, None),
        ("WeightUnit", "Weight unit", "text", 120, None),
        ("Volume", "Volume", "num", 120, None),
        ("VolumeUnit", "Volume unit", "text", 120, None),
        ("SizeDimension", "Size / dimension", "text", 180, None),
    ]),
    ("Where", [
        ("Plant", "Plant", "text", 120, None),
        ("StorageLocation", "Storage location", "text", 160, None),
        ("StorageBin", "Storage bin", "text", 160, None),
    ]),
    ("Purchasing", [
        ("PurchasingGroup", "Purchasing group", "text", 160, None),
        ("PurchaseOrderUnit", "Order unit", "text", 120, None),
        ("PlannedDeliveryTime", "Planned deliv. (days)", "num", 180, None),
        ("GRProcessingTime", "GR time (days)", "num", 160, None),
        ("PreferredVendor", "Preferred vendor", "text", 220, None),
    ]),
    ("Planning", [
        ("MRPType", "MRP type", "text", 120, None),
        ("MRPController", "MRP controller", "text", 160, None),
        ("ProcurementType", "Procurement", "choice", 140, ["E", "F", "X"]),
        ("SpecialProcurement", "Special procurement", "text", 180, None),
        ("LotSizeKey", "Lot size key", "text", 140, None),
        ("ReorderPoint", "Reorder point", "num", 140, None),
        ("SafetyStock", "Safety stock", "num", 140, None),
        ("MinLotSize", "Min lot size", "num", 140, None),
        ("MaxLotSize", "Max lot size", "num", 140, None),
        ("RoundingValue", "Rounding value", "num", 140, None),
    ]),
    ("Accounting", [
        ("ValuationClass", "Valuation class", "text", 160, None),
        ("PriceControl", "Price control", "choice", 140, ["S", "V"]),
        ("StandardPrice", "Standard price", "num", 160, None),
        ("PriceUnit", "Price unit", "num", 120, None),
        ("Currency", "Currency", "text", 100, None),
    ]),
    ("Control", [
        ("SerialNoProfile", "Serial no. profile", "text", 160, None),
        ("BatchManaged", "Batch managed", "bool", 160, None),
        ("ABCIndicator", "ABC", "choice", 100, ["A", "B", "C"]),
        ("IsSpare", "Spare part", "bool", 140, None),
    ]),
    ("Where it is used", [
        ("FunctionalLocation", "Functional location", "text", 260, None),
        ("EquipmentNo", "Equipment no.", "text", 200, None),
    ]),
]

ITEM_TEXT_LABEL = "Material text"
ITEM_TEXT_PLACEHOLDER = '"Short text, max 40 characters"'

LIST_COLS = [("MATERIAL", 0), ("TYPE", 90), ("GROUP", 120), ("PLANT", 80),
             ("CHANGE", 110), ("FILES", 70)]
LIST_FIELDS = ["MaterialType", "MaterialGroup", "Plant", "ChangeType"]
