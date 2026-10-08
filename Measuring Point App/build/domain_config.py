# -*- coding: utf-8 -*-
"""
Alt det, der skiller Measuring Point-appen fra Equipment og Materials,
staar HER (issue #210).

De tre domaeneapps deler byggeklodserne i tools/domain_parts.py. Denne fil
er appens kontrakt: felterne (SECTIONS), listenavnet og praefikset.
Kompositionen staar i assemble_screen.py og mp_parts.py.

FELTERNE ER KONTRAKTEN, IKKE ET VALG
------------------------------------
Hver linje i SECTIONS svarer til en kolonne i SharePoint-listen
MeasuringPointItems, som den oprettes af
sharepoint/provision/Provision-MeasuringPointLists.ps1.
tools/check_datasources.py efterproever det ved hver bygning - saa snart
listen er med i et nyt udtraek af sharepoint/inspect/out/schema.md.

EN ENKELTAPP FINDES IKKE
------------------------
Enkeltapperne er udfaset (docs/33). Measuring Point bygges KUN som skaerm
i BIO SAP App - men byggermappen skal findes, fordi BIO SAP bygges af
domaenernes egne byggere (BIO SAP App/build/build_screens.py).

JA/NEJ ER TEKST, IKKE BOOLEAN
-----------------------------
"Does it exist in SAP?", "Is it located in PRODOS?" og "Does the counter
exist in PRODOS?" gemmes som "Yes"/"No". En Boolean kan ikke skelne "ikke
besvaret" fra "No", og saa kan "kraevet" ikke kontrolleres. IsCounter er
derimod en Boolean - den er altid AFLEDT af typen (issue #210 Q14) og
skrives af appen, ikke af brugeren (EXTRA_PATCH nedenfor).
"""
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "tools"))
import env_config as env

# --- appen ------------------------------------------------------------
APP_KEY = "measuringpoint"
SCREEN = "ScreenMeasuringPoint"
TITLE = "Measuring Points"
SUBTITLE = "Report counters and measuring points for a functional location."

# Praefikset i noeglerne og i anmodningsnummeret: MP-000123.
PREFIX = "MP"

# Domaeneteksten i MD_RequestIndex. SKAL vaere ordret den samme som i
# hub_config.py og Provision-RequestIndex.ps1 - ellers faar raekken hverken
# farve eller navn paa landingssiden. Valget findes allerede i listen.
DOMAIN = "MeasuringPoint"

# --- listerne, som de hedder naar de er tilfoejet appen som datakilde --
L_ROWS = "MeasuringPointItems"
L_INDEX = "MD_RequestIndex"
L_PLANTS = "PlantList"
# Opslagslisten bag feltet Characteristic. Karakteristikken bestemmer
# enheden (Q3), saa der er ingen fri tekst og ingen enhedsliste.
L_CHARS = "MD_MpCharacteristic"

# Provisioneringen omdoeber Title. Power Fx binder paa VISNINGSNAVN, saa et
# Patch med { Title: ... } rammer ved siden af.
C_TEXT = "Description"
TEXT_LABEL = "Description"
TEXT_PLACEHOLDER = '"Short text, max 40 characters"'

HUB_URL = env.hub_url()

# FL-soegningen (tools/fl_picker.py) - den samme i alle domaeneapps. Der
# vaelges ALTID en funktionsplads (Q4); udstyrsmaalepunkter kommer senere.
FL_FIELD = "FunctionalLocation"

# --- felterne ---------------------------------------------------------
# (kolonne, etiket, art, valgmuligheder)
#
#   art: "text"   enkeltlinjet tekst
#        "num"    heltal      -> ModernNumberInput
#        "dec"    tal med decimaler. Tastes som tekst og gemmes i en
#                 Number-kolonne (tools/domain_parts.py): den moderne
#                 talkontrol har heltalspraecision, og en maaling kan have
#                 op til tre decimaler (Q9)
#        "choice" fast ordforraad i appen
#        "long"   flerlinjet tekst
#        "bool"   sand/falsk
#
# SEKTIONERNE ER GRUPPERING, IKKE OVERSKRIFTER - raekkefoelgen paa skaermen
# staar i mp_parts.FORM_ORDER.
YESNO = ["Yes", "No"]
# Typerne er appens ordforraad OG valgvaerdierne i kolonnen, saa de to ikke
# kan komme til at sige noget forskelligt (Q1).
MP_TYPES = ["Counter", "MeasuringPoint"]

SECTIONS = [
    ("Object", [
        ("FunctionalLocation", "Functional location", "text", None),
    ]),
    ("Existing or new", [
        ("ExistsInSap", "Does it exist in SAP?", "choice", YESNO),
        ("MeasuringPoint", "Measuring point no.", "text", None),
    ]),
    ("Type and characteristic", [
        ("MeasuringPointType", "Measuring point type", "choice", MP_TYPES),
        ("Characteristic", "Characteristic", "text", None),
        ("CharacteristicDescription", "Characteristic description", "text", None),
        ("CharacteristicUnit", "Unit", "text", None),
        ("CharacteristicUnitDescription", "Unit description", "text", None),
        ("DecimalPlaces", "Decimal places", "num", None),
    ]),
    ("Measuring point", [
        ("TargetValue", "Target value", "dec", None),
        ("LowerLimit", "Lower limit", "dec", None),
        ("UpperLimit", "Upper limit", "dec", None),
    ]),
    ("Counter", [
        ("ExpectedAnnualUsage", "Expected annual usage", "dec", None),
    ]),
    ("Reading source", [
        ("InProdos", "Is it located in PRODOS?", "choice", YESNO),
        ("ProdosTag", "PRODOS tag", "text", None),
        ("ProdosCounterExists", "Does the counter exist in PRODOS?", "choice", YESNO),
        ("CounterCreateIn", "Counter to be created in", "choice", ["PRODOS", "SRO"]),
    ]),
    ("Additional information", [
        ("Remarks", "Remarks", "long", None),
    ]),
]

# FELTER, DER KUN LAESES
# ----------------------
# De hentes ind i colDomRows og vises i listen og i detaljerne, men de er
# IKKE i formularen, i Patch, i kopien eller i admin-loggens diff.
#
#   IsCounter, ApprovalRequired     afledt af typen, skrives af EXTRA_PATCH
#   CreatedMeasuringPointNo         nummeret fra SAP. Udfyldes i foerste
#                                   version i haanden i Details (Q8/Q19)
#   CounterCreatedOn/By             naar PRODOS/SRO-taelleren er markeret
#                                   oprettet (Q7) - kommer med fase 5
#   SapResult                       kvitteringens svar pr. raekke
READ_FIELDS = [
    ("IsCounter", "Is a counter", "bool", None),
    ("ApprovalRequired", "Approval required", "bool", None),
    ("CreatedMeasuringPointNo", "Created measuring point no.", "text", None),
    ("CounterCreatedOn", "Counter created on", "date", None),
    ("CounterCreatedBy", "Counter created by", "text", None),
    ("SapResult", "SAP result", "long", None),
]

PLANT_LABEL = "Plant"

# Felter soegefeltet kigger i. Skal vaere tekstfelter i samlingen.
SEARCH_FIELDS = ["Description", "FunctionalLocation", "MeasuringPoint",
                 "ProdosTag", "Characteristic"]
