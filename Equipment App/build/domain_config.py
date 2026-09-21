# -*- coding: utf-8 -*-
"""
Alt det, der skiller Equipment-appen fra Materials-appen, staar HER.

De to apps er den samme app. Samme skaerm, samme gem, samme dokumentrude -
kun felterne og listenavnet er forskellige. Derfor er build_domain.py,
attflows.py, assemble_screen.py og generate_app_onstart.py ORDRET ens i de
to build-mapper, og kun denne fil er forskellig. tools/build_all.py
tjekker, at de bliver ved med at vaere ens.

FELTERNE ER KONTRAKTEN, IKKE ET VALG
------------------------------------
Hver linje i FIELDS svarer til en kolonne i SharePoint-listen
EquipmentItems, som den staar i sharepoint/inspect/out/schema.md.
tools/check_datasources.py efterproever det ved hver bygning: staar der et
felt her, som listen ikke har, er byggeriet roedt.

Listen er provisioneret af sharepoint/provision/Provision-EqMatLists.ps1,
og DEN er skrevet af den formular, appen havde i Studio. Kaeden er altsaa
formular -> liste -> builder, og ingen af de tre led er gaettet.
"""

# --- appen ------------------------------------------------------------
APP_KEY = "equipment"
SCREEN = "ScreenEquipment"
TITLE = "Equipment"
SUBTITLE = "Opret, aendr og slet udstyr - og send indberetningen videre."

# Praefikset i noeglerne: EQ-000912.
PREFIX = "EQ"

# Domaeneteksten i MD_RequestIndex. SKAL vaere ordret den samme som i
# hub_config.py og Provision-RequestIndex.ps1 - ellers faar raekken hverken
# farve eller navn paa landingssiden.
DOMAIN = "Equipment"

# --- listen, som den hedder naar den er tilfoejet appen som datakilde --
L_ROWS = "EquipmentItems"
L_INDEX = "MD_RequestIndex"
L_PLANTS = "PlantList"

# Provisioneringen omdoeber Title. Power Fx binder paa VISNINGSNAVN, saa et
# Patch med { Title: ... } rammer ved siden af.
C_TEXT = "Description"
TEXT_LABEL = "Beskrivelse"
TEXT_PLACEHOLDER = '"Kort tekst, hoejst 40 tegn"'

PLAY_URL = ("https://apps.powerapps.com/play/e/"
            "e0f8f822-d16a-e878-ba4e-fb42bc617e47"
            "/a/24bf3bbc-601f-480d-a8fe-7cd3180906d1")

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
# (kolonne, etiket, art, valgmuligheder)
#
#   art: "text"   enkeltlinjet tekst
#        "num"    tal
#        "date"   dato     -> ModernDatePicker, .SelectedDate
#        "choice" fast ordforraad i appen (IKKE en SharePoint-valgkolonne)
#        "long"   flerlinjet tekst
#
# Arten bestemmer BAADE kontrollen paa skaermen, kolonnen i samlingen og
# formen i Patch. Det er den eneste maade at undgaa, at de tre kommer til
# at sige noget forskelligt om det samme felt.
#
# DROPDOWNENE VENTER PAA LISTER
# -----------------------------
# RequestType og EquipmentCategory var dropdowns i den haandbyggede app,
# men de samlinger, de pegede paa, blev aldrig defineret - hverken i
# App.OnStart eller i en OnVisible. Derfor stod de tomme med roede fejl,
# og derfor kendes ordforraadet ikke. De er TEKSTfelter her og
# TEKSTkolonner i SharePoint, indtil listerne findes. Saa er det een linje
# her og een i provisioneringen.
SECTIONS = [
    ("Hvad skal der ske", [
        ("RequestType", "Type", "text", None),
        ("EquipmentNumber", "Equipmentnummer", "text", None),
    ]),
    ("Stamdata", [
        ("EquipmentCategory", "Equipment type", "text", None),
        ("Manufacturer", "Fabrikat", "text", None),
        ("TypeDesignation", "Type betegnelse", "text", None),
        ("SerialNumber", "Serienummer", "text", None),
    ]),
    ("Hvor sidder det", [
        ("FunctionalLocation", "Func. location", "text", None),
        ("FunctionalLocation1", "Func. loc. 1", "text", None),
        ("FunctionalLocation2", "Functional location 2", "text", None),
        ("ClassData", "Klasse data", "text", None),
        ("RoomCoordinates", "Rum koordinater", "text", None),
        ("Placement", "Placeringstekst", "text", None),
    ]),
    ("Garanti", [
        ("WarrantyStart", "Garanti start", "date", None),
        ("WarrantyEnd", "Garanti slut", "date", None),
    ]),
    ("Bemaerkninger", [
        ("LongText", "Langtekst", "long", None),
    ]),
]

# Plant staar for sig i hovedet - den er obligatorisk og filtreres paa.
PLANT_LABEL = "Plant"

# Kolonner i raekkeoversigten. Foerste er altid raekkens tekst, sidste er
# altid antallet af dokumenter; bredden 0 betyder "tag resten".
LIST_COLS = [("BESKRIVELSE", 0), ("EQUIPMENTNR.", 110), ("FUNC. LOCATION", 140),
             ("PLANT", 55), ("STATUS", 75), ("FILER", 40), ("", 60)]
LIST_FIELDS = ["EquipmentNumber", "FunctionalLocation", "Plant"]

# Felter soegefeltet kigger i. Skal vaere tekstfelter i samlingen.
SEARCH_FIELDS = ["Description", "FunctionalLocation", "SerialNumber",
                 "EquipmentNumber"]
