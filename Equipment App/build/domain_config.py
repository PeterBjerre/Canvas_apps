# -*- coding: utf-8 -*-
"""
Alt det, der skiller Equipment-appen fra Materials-appen, staar HER.

Equipments og Materials er to apps, der deler byggeklodserne i
tools/domain_parts.py. Denne fil er appens kontrakt: felterne (SECTIONS),
listenavnet og praefikset. Kompositionen staar i assemble_screen.py og
*_parts.py (se SKILL.md "Hvem ejer hvad - Equipments og Materials").

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
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "tools"))
import env_config as env

# --- appen ------------------------------------------------------------
APP_KEY = "equipment"
SCREEN = "ScreenEquipment"
TITLE = "Equipment"
SUBTITLE = "Create, change and delete equipment"

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
TEXT_LABEL = "Description"
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

# Feltet der skal have FL-SOEGNING i stedet for et tekstfelt: EEN combobox
# med Search-knap (tools/fl_picker.py, issue #63/#68) - den samme i alle
# tre apps. Flowet er allerede datakilde.
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
#
# INTET LANGTEKSTFELT (issue #37)
# -------------------------------
# "Remarks / Long text" er fjernet fra Equipment-appen - kun her, ikke i
# Materials. Kolonnen LongText staar stadig i EquipmentItems: den slettes
# ikke, saa gamle raekker beholder deres tekst, og Patch roerer den ikke,
# fordi Patch kun skriver de felter, der staar herunder.
#
# SEKTIONERNE ER GRUPPERING, IKKE OVERSKRIFTER. Formularen viser dem ikke
# laengere (issue #68); raekkefoelgen paa skaermen staar i
# equipment_parts.FORM_ORDER.
SECTIONS = [
    ("What should happen", [
        ("RequestType", "Type", "text", None),
    ]),
    ("Master data", [
        ("EquipmentCategory", "Equipment type", "text", None),
        ("Manufacturer", "Manufacturer", "text", None),
        ("TypeDesignation", "Type designation", "text", None),
        ("SerialNumber", "Serial number", "text", None),
    ]),
    # Func. loc. 1 og Functional location 2 er fjernet igen (issue #94):
    # FL-soegningen (FunctionalLocation) er den eneste maade at vaelge en
    # funktionsplads paa. Kolonnerne FunctionalLocation1/2 staar stadig i
    # EquipmentItems - de slettes ikke, og Patch roerer dem ikke, fordi
    # Patch kun skriver felterne herunder.
    ("Where it sits", [
        ("FunctionalLocation", "Functional location", "text", None),
        ("ClassData", "Class data", "text", None),
        ("RoomCoordinates", "Room coordinates", "text", None),
        ("Placement", "Placement text", "text", None),
    ]),
    ("Warranty", [
        ("WarrantyStart", "Warranty from", "date", None),
        ("WarrantyEnd", "Warranty to", "date", None),
    ]),
]

# FELTER, DER KUN LAESES (issue #94)
# ----------------------------------
# Udstyrsnummeret tastes ikke laengere i formularen - det er SAP's. Men et
# nummer, der allerede staar paa raekken (fra SAP eller fra en aeldre
# raekke), skal stadig kunne ses og soeges paa. Felterne her hentes ind i
# colDomRows og vises i listen og i detaljerne, men de er IKKE i
# formularen, i Patch, i kopien eller i admin-loggens diff.
READ_FIELDS = [
    ("EquipmentNumber", "Equipment number", "text", None),
]

# Plant staar for sig i hovedet - den er obligatorisk og filtreres paa.
PLANT_LABEL = "Plant"

# Listens kolonner staar i equipment_parts.SLOTS.

# Felter soegefeltet kigger i. Skal vaere tekstfelter i samlingen.
SEARCH_FIELDS = ["Description", "FunctionalLocation", "SerialNumber",
                 "EquipmentNumber"]
