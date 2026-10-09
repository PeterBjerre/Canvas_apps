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

# --- betingede felter (issue #210, fase 2) ----------------------------
# Hvert felt, der kun gaelder i en bestemt situation, har et Power
# Fx-udtryk her. tools/domain_parts.py bruger det TO steder: cellens
# Visible, og ryd-ved-gem, saa en aendret type ikke efterlader gamle
# vaerdier paa raekken.
#
# Variablerne er formularens egne (varDomF<kolonne>); i den samlede app
# doebes Dom om til Mp (BIO SAP App/build/combined.py).
_EXISTS = 'varDomFExistsInSap'
_TYPE = 'varDomFMeasuringPointType'
_PRODOS = 'varDomFInProdos'
_COUNTER_IN_PRODOS = 'varDomFProdosCounterExists'

# Nyt maalepunkt (Exists = No) - resten af formularen.
NEW = f'{_EXISTS} = "No"'
# Et eksisterende maalepunkt registreres kun (Q5).
OLD = f'{_EXISTS} = "Yes"'
IS_COUNTER = f'{_TYPE} = "Counter"'
IS_MP = f'{_TYPE} = "MeasuringPoint"'
IN_PRODOS = f'{NEW} && {_PRODOS} = "Yes"'
COUNTER_Q = f'{IN_PRODOS} && {IS_COUNTER}'
COUNTER_MISSING = f'{COUNTER_Q} && {_COUNTER_IN_PRODOS} = "No"'

WHEN = {
    "MeasuringPoint": OLD,
    "MeasuringPointType": NEW,
    "Characteristic": NEW,
    "CharacteristicDescription": NEW,
    "CharacteristicUnit": NEW,
    "CharacteristicUnitDescription": NEW,
    "DecimalPlaces": NEW,
    "TargetValue": f"{NEW} && {IS_MP}",
    "LowerLimit": f"{NEW} && {IS_MP}",
    "UpperLimit": f"{NEW} && {IS_MP}",
    "ExpectedAnnualUsage": f"{NEW} && {IS_COUNTER}",
    "InProdos": NEW,
    "ProdosTag": IN_PRODOS,
    "ProdosCounterExists": COUNTER_Q,
    "CounterCreateIn": COUNTER_MISSING,
}

# --- valgkolonner i SharePoint ----------------------------------------
# Provisioneringen (Provision-MeasuringPointLists.ps1) har oprettet de fem
# ja/nej- og typefelter som CHOICE-kolonner, og udtraekket
# (sharepoint/inspect/out/schema.md) er sandheden. Appen arbejder stadig
# med teksten ("Yes", "Counter"), men den skal skrives som { Value: ... }
# og laeses som .Value - ellers compiler skaermen ikke i Studio.
# tools/domain_parts.py goer det for felterne her (opt-in); Equipment og
# Materials har tekstkolonner og roeres ikke.
SP_CHOICE = {"ExistsInSap", "MeasuringPointType", "InProdos",
             "ProdosCounterExists", "CounterCreateIn"}

# --- det, appen selv skriver ------------------------------------------
# "Is the measuring point a counter?" er ET TYPEVALG (Q14), saa IsCounter
# er afledt og ikke et felt. ApprovalRequired er sand for en NY Counter
# (Q1, Q16) - en eksisterende Counter, der kun registreres, godkendes
# ikke. Begge fastfryses, naar raekken laases ved Submit.
EXTRA_PATCH = {
    "IsCounter": IS_COUNTER,
    "ApprovalRequired": f"({IS_COUNTER} && {NEW})",
}

# --- opslagslisten bag Characteristic ---------------------------------
# Karakteristik og enhed haenger sammen (Q3): man vaelger karakteristikken,
# og enheden foelger med. Kun aktive raekker kan vaelges; en gammel raekke
# beholder de vaerdier, der blev KOPIERET ned paa den.
#
# Navngiven formel: den laeses dovent og hoejst een gang pr. session, og
# Filter paa en Boolean delegeres.
EXTRA_FORMULAS = (
    "// Karakteristikker til maalepunkter (issue #210). Genereret af\n"
    "// Measuring Point App/build/domain_config.py - ret ikke i YAML'en.\n"
    "colDomChars = Sort(\n"
    f"    ForAll(Filter({L_CHARS}, Active = true) As R, {{\n"
    "        Value: R.Title,\n"
    "        Description: Coalesce(R.Description, \"\"),\n"
    "        Unit: Coalesce(R.Unit, \"\"),\n"
    "        UnitDescription: Coalesce(R.UnitDescription, \"\"),\n"
    "        MeasuringPointType: Coalesce(R.MeasuringPointType.Value, \"\"),\n"
    "        DefaultDecimalPlaces: Coalesce(R.DefaultDecimalPlaces, 0)\n"
    "    }),\n"
    "    Value\n"
    ");"
)

# --- Submit ------------------------------------------------------------
# GODKENDELSEN AF NYE COUNTER-RAEKKER ER BAG ET FLAG (fase 4-6)
#
# features.measuring_point_approval i tools/canvas_apps.json. Slaaet FRA
# er skaermen den fra fase 1-3: intet opslag, ingen vagt foer Submit, ingen
# trinstribe og intet flow-kald - og en anmodning gaar direkte til Master
# Data (KlarTilSAP, Q12).
#
# Slaaet TIL indsendes anmodningen som Indsendt, og flowet
# BioSap-MeasuringPoint-Approval afgoer resten: ingen ny Counter -> straks
# KlarTilSAP (Q12); ellers systemgodkendelsen, PRODOS/SRO-taelleren og
# saa KlarTilSAP. Status skifter dermed kun eet sted - i flowet.
APPROVAL_ON = env.feature_on("measuring_point_approval")
SUBMIT_STATUS = "Indsendt" if APPROVAL_ON else "KlarTilSAP"

# --- Saved Rows og kopi (fase 3) --------------------------------------
# EET fast layout (Q13): ingen Compact/All columns og ingen varDomAllCols.
# Det er nu faelles for alle domaeneapps (#204), saa der er intet at slaa
# fra her - pladserne staar i mp_parts.SLOTS.

# Copy laver en NY raekke af en gammel. Et eksisterende maalepunktsnummer
# maa ikke foelge med - to raekker kan ikke vaere det samme punkt.
# CreatedMeasuringPointNo staar i READ_FIELDS og kopieres aldrig.
COPY_SKIP = {"MeasuringPoint"}
