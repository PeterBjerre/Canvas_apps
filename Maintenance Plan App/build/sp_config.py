# -*- coding: utf-8 -*-
"""
Kontrakten mod SharePoint. ALT der afhaenger af listernes navne og kolonner
staar HER og kun her.

VIGTIGT: Power Fx binder SharePoint-kolonner paa VISNINGSNAVN, ikke internt
navn. Navnene nedenfor er visningsnavne, som de staar i
sharepoint/inspect/out/schema.md. Doeber nogen en kolonne om i SharePoint,
er det den her fil, der skal rettes - ikke formlerne ude i skaermen.

HVORFOR NAVNGIVNE FORMLER OG IKKE ClearCollect I OnStart
--------------------------------------------------------
OnStart betales af hver bruger hver gang appen aabnes. Et ClearCollect pr.
opslagsliste ville vaere ti kald, foer der overhovedet er tegnet noget.

Navngivne formler (App.Formulas) evalueres DOVENT: listen hentes foerste
gang en kontrol faktisk har brug for den, ikke foer den foerste skaerm
vises. Navnene er de samme colVhp*, som skaermen allerede bruger, saa ingen
kontrol skal aendres.

RETTELSE, efterproevet paa Learn: her stod foer "og kun een gang". Det er
forkert. En navngiven formel er ikke et engangs-cache men en definition,
der altid er sand - den genberegnes, naar dens afhaengigheder aendrer sig.
Det er en FORDEL her (listerne holder sig selv friske uden et Refresh),
men det er ikke det samme som at hente een gang, og den som laeser videre
skal ikke regne med et fast oejebliksbillede.

Til gengaeld kan en navngiven formel ikke skrives til. De samlinger, appen
REDIGERER - items, operationer, soegeresultater - er derfor stadig
rigtige samlinger og staar i OnStart med tom skemadefinition.
"""
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "tools"))
import env_config as env

# --- listenavne, som de hedder naar de er tilfoejet appen som datakilde ---
L_PLANTS      = "PlantList"
L_SORTFIELDS  = "SortFieldList"
L_ACTTYPES    = "MaintenanceActivityTypeList"
L_CALLHORIZON = "CallHorizonMatrix"
L_WORKCENTERS = "MainWorkCenters"
L_STRATEGY    = "MD_Strategy"
L_PACKAGES    = "MD_StrategyPackage"
L_STDOPS      = "MD_StandardTaskOperations"
L_PLANS       = "MaintenancePlans"
L_ITEMS       = "MaintenanceItems"
L_TASKS       = "TaskListMain"
L_INDEX       = "MD_RequestIndex"
L_MATERIALS   = "MD_TasklistMaterial"
L_ATTACHMENTS = "MD_TasklistAttachment"

# --- landingssiden --------------------------------------------------------
# VH-plan-appen aabnes af hubbens VHP-flise som en SELVSTAENDIG app, ikke
# som en skaerm i den. Back() kan derfor ikke foere tilbage - der skal et
# Launch til. LaunchTarget.Replace, saa det sker i den fane, brugeren
# staar i; ellers faar man en fane pr. klik.
#
# Samme id som apps.hub.app_id i tools/canvas_apps.json. build_all.py
# tjekker, at de to ikke glider fra hinanden.
# Kommer fra tools/canvas_apps.json via env_config - se der for hvorfor.
HUB_URL = env.hub_url()

# --- kolonnenavne der IKKE er selvindlysende -------------------------------
# MainWorkCenters er oprettet fra Excel, saa de interne navne er field_1 og
# field_2. Visningsnavnet paa field_1 er 'Description' med 33 efterfoelgende
# MELLEMRUM - det kan ikke skrives paalideligt i Power Fx, saa appen bruger
# det ikke. 'Plant Key' er field_2 og er ufarlig; den skal blot i enkelte
# anfoerselstegn, fordi den indeholder et mellemrum.
C_WC_PLANT = "'Plant Key'"

# MD_Strategy: Title er omdoebt til StrategyKey ved provisioneringen.
C_STRATEGY_KEY = "StrategyKey"

# MD_RequestIndex: Title er omdoebt til RequestNo. Power Fx binder paa
# VISNINGSNAVN, saa et Patch med { Title: ... } ville ramme ved siden af.
# Samme streng staar som COL_NO i "Masterdata Hub/build/hub_config.py".
C_INDEX_NO = "RequestNo"

# Samme faelde i de to nye lister: provisioneringen omdoeber Title til
# MaterialNo og FileName. Et Patch med { Title: ... } ville ramme ved siden
# af - praecis som det gjorde i MD_RequestIndex.
C_MATERIAL_NO = "MaterialNo"
C_FILE_NAME   = "FileName"


# ---------------------------------------------------------------------------
# Varighed regnes, den tastes ikke
# ---------------------------------------------------------------------------
# I SAP er operationens varighed arbejdstimerne fordelt paa det antal
# personer, der udfoerer den (ANZZL - "No."). Tastede man begge dele, kunne
# de modsige hinanden, og SAP ville alligevel regne sin egen.
#
# Nul personer findes ikke; en tom eller nulstillet celle regnes som een, saa
# udtrykket aldrig dividerer med nul.
def duration_expr(work, persons):
    return f"{work} / Max(Coalesce({persons}, 1), 1)"


def _forall(source, fields, alias="R"):
    """ForAll med eksplicit record - virker i alle Power Fx-versioner.

    RenameColumns/ShowColumns har skiftet signatur mellem versioner
    (kolonnenavne som strenge vs. som identifiers). ForAll med en
    record-literal goer ikke, og er samtidig til at laese."""
    body = ", ".join(f"{k}: {v}" for k, v in fields)
    return f"ForAll({source} As {alias}, {{ {body} }})"


# ---------------------------------------------------------------------------
# Navngivne formler. Raekkefoelgen er ligegyldig - Power Fx loeser selv
# afhaengighederne, saa laenge der ikke er cyklusser.
# ---------------------------------------------------------------------------
def named_formulas():
    F = []

    def add(name, expr, why=None):
        F.append((name, expr, why))

    # --- simple opslagslister: appen forventer { Value } ---
    add("colVhpPlantCodes",
        f"Sort({_forall(L_PLANTS, [('Value', 'R.Title')])}, Value)")

    add("colVhpSortFieldOptions",
        f"Sort({_forall(L_SORTFIELDS, [('Value', 'R.Title')])}, Value)")

    add("colVhpActivityTypeOptions",
        f"Sort({_forall(L_ACTTYPES, [('Value', 'R.Title')])}, Value)")

    # Value er teksten, brugeren vaelger. Days er TALLET, SharePoint vil have:
    # valgkolonnen CallHorizonChoiceOLD har engelske tekster ("55 days (1 YR)"),
    # som IKKE matcher matricens danske ("45 dage"), mens talkolonnen
    # CallHorizon tager tallet direkte. Derfor baeres begge dele.
    add("colVhpCallHorizonOptions",
        "Sort(" + _forall(L_CALLHORIZON,
                          [("Value", "R.Title"),
                           ("Days", "R.NewCallHorizonOrFCD"),
                           ("SchedPeriod", "R.SchedulingPeriodNum")]) + ", Value)")

    # --- valgkolonner: Choices() giver allerede { Value } ---
    add("colVhpPlanStatusOptions", f"Choices({L_ITEMS}.Status)")
    add("colVhpUnitOptions",       f"Choices({L_PLANS}.Unit)")
    add("colVhpRevisionOptions",   f"Choices({L_ITEMS}.RevisionMark)")
    add("colVhpPriorityOptions",   f"Choices({L_ITEMS}.Priority)")

    # --- arbejdscentre: baeres med vaerk, saa listen kan afgraenses ---
    # 53 arbejdscentre for hele afdelingen, ~7 der er relevante for det
    # valgte vaerk. Trim, fordi SAP-eksporten er polstret med mellemrum.
    add("colVhpMainWorkCenters",
        _forall(L_WORKCENTERS, [("Value", "Trim(R.Title)"),
                                ("Plant", f"Trim(R.{C_WC_PLANT})")]),
        "Alle arbejdscentre med deres vaerk. Afgraenses i kontrollen.")

    # --- styringsnoegler: findes ikke som egen liste, men staar paa
    #     standardoperationerne. Distinct giver { Value }. ---
    add("colVhpCtrlOptions", f"Sort(Distinct({L_STDOPS}, ControlKey), Value)")

    # --- strategier ---
    # ALLE strategier vises, ogsaa dem uden pakker. Det modsatte - kun at
    # tilbyde dem med pakker - ville give en HELT TOM dropdown, saa laenge
    # MD_StrategyPackage er tom, og saa kan strategidelen slet ikke bruges
    # eller testes. I stedet maerkes de, der ikke er klar, i selve teksten,
    # og pakkematricen forklarer hvorfor, naar en af dem vaelges.
    add("colVhpStrategies",
        "Sort(" + _forall(
            L_STRATEGY,
            [("Key", f"R.{C_STRATEGY_KEY}"),
             ("Name", "R.StrategyName"),
             ("SchedIndicator", "R.SchedulingIndicator.Value"),
             ("Hierarchical", "R.Hierarchical.Value"),
             ("PackagesLoaded", "R.PackagesLoaded"),
             ("Display", f"R.{C_STRATEGY_KEY} & \" - \" & R.StrategyName & "
                         "If(R.PackagesLoaded, \"\", \"   (packages missing)\")")])
        + ", Key)")

    add("colVhpStrategyPackages",
        _forall(L_PACKAGES, [("StrategyKey", "R.StrategyKey"),
                             ("PackageNo", "R.PackageNo"),
                             ("ShortCode", "R.ShortCode"),
                             ("CycleLength", "R.CycleLength"),
                             ("CycleUnit", "R.CycleUnit.Value"),
                             ("Hierarchy", "R.Hierarchy"),
                             ("PackageText", "R.PackageText")]))

    # --- standardarbejdsplaner ---
    # Een arbejdsplan pr. vaerk. Operationerne ligger fladt i listen med et
    # Plant og et OperationNo; her samles de til den indlejrede form,
    # skaermen allerede forventer.
    ops = _forall(
        f"Sort(Filter({L_STDOPS}, Plant.Value = P.Value), OperationNo)",
        [("OperationNo", "Text(O.OperationNo, \"0000\")"),
         ("OperationShortText", "O.OperationShortText"),
         ("WorkHours", "O.Work"),
         # NumberOfCapacities er standardplanens "No.". Varigheden stod foer
         # som 0 paa hver hentet linje; nu regnes den af de to felter med
         # samme udtryk som i operationstabellen.
         ("Persons", "O.NumberOfCapacities"),
         ("DurationHours", duration_expr("O.Work", "O.NumberOfCapacities")),
         ("MainWorkCenter", "O.WorkCenter"),
         ("Vendor", "O.VendorNo"),
         ("LongText", "\"\""),
         ("ControlKey", "O.ControlKey"),
         # Baeres med, saa en linje hentet fra standardplanen kommer ind
         # UDFYLDT. Brugeren skal kun redigere dem ved PM02.
         #
         # Price ER en timesats: hver linje i standardplanen staar med
         # Work = 1, og Price er prisen for den ene time (SSVXSTIL 494,
         # SSVXISOL 420). Beloebet er derfor timer gange sats - det holder
         # ogsaa, naar Work er 1, hvor de to er ens.
         ("UnitCost", "O.Price"),
         ("Cost", "O.Work * O.Price"),
         ("Currency", "O.Currency"),
         ("CostElement", "O.CostElement"),
         ("MaterialGroup", "O.MaterialGroup"),
         ("OpPlant", "O.SapPlant")],
        alias="O")
    add("colVhpTasklists",
        _forall(f"Distinct({L_STDOPS}, Plant.Value)",
                [("Plant", "P.Value"),
                 ("Key", "P.Value & \"-STD\""),
                 ("Name", "\"Standard task list - \" & P.Value"),
                 ("Description", "\"\""),
                 ("Operations", ops)],
                alias="P"))

    return F


# ---------------------------------------------------------------------------
# Vaerdier der IKKE kommer fra en liste.
#
# De staar i SAP og aendrer sig ikke, og der er ingen der vedligeholder dem
# som masterdata. En liste med tre raekker, ingen roerer, er daarligere end
# en konstant man kan se.
# ---------------------------------------------------------------------------
STATIC_TABLES = [
    ("colVhpYesNoOptions", [{"Value": "JA"}, {"Value": "NEJ"}],
     "SAP-vaerdier for schedulering."),
    ("colVhpPlanTypeOptions",
     [{"Key": "SingleCycle", "Value": "Single cycle plan (IP41)"},
      {"Key": "Strategy", "Value": "Strategiplan (IP42)"}],
     "Appens eget begreb, ikke et SAP-felt."),
]

# ---------------------------------------------------------------------------
# Samlinger appen SKRIVER til. De kan ikke vaere navngivne formler.
# Skemaet defineres med en enkelt raekke, som straks ryddes - ellers kender
# Power Fx ikke kolonnetyperne, foer der er lagt data i.
# ---------------------------------------------------------------------------
WORKING_COLLECTIONS = [
    ("colVhpItems",
     {"ItemId": 0, "ShortText": '""', "FunctionalLocation": '""', "FlDescription": '""',
      "MainWorkCenter": '""', "ActivityType": '""', "ObjectList": '""', "Revision": '""',
      "OrstedResponsible": '""', "Initials": '""', "LongText": '""',
      "TasklistKey": '""', "TasklistName": '""', "Status": '""'}),
    ("colVhpOperations",
     {"ItemId": 0, "OperationNo": '""', "OperationShortText": '""', "WorkHours": 0,
      # Persons er SAP's "No." (ANZZL). DurationHours regnes af de to og
      # tastes ikke - se duration_expr() ovenfor.
      "Persons": 0,
      "DurationHours": 0, "MainWorkCenter": '""', "Vendor": '""', "LongText": '""',
      "PackagesKey": '";"', "Selected": "false",
      # Styres af reglerne i operationstabellen: kontrolnoeglen kan kun
      # aendres paa *SUP og *TECH, og de tre indkoebsfelter kun ved PM02.
      # Cost er BELOEBET paa linjen. UnitCost er satsen bag det - kr/time
      # fra standardarbejdsplanen - saa beloebet kan regnes om, naar
      # timerne rettes. Se cost_expr() i build_tasklist.py.
      "ControlKey": '""', "Cost": 0, "UnitCost": 0, "Currency": '""',
      "CostElement": 0, "MaterialGroup": '""'}),
    ("colVhpFlSearch",
     {"Code": '""', "Description": '""', "Display": '""',
      "Maintainable": "false", "Level": '""'}),
    ("colVhpItemObjects", {"ItemId": 0, "Code": '""', "Description": '""'}),
    ("colVhpPickerSelected", {"OperationNo": '""'}),
    # Materialer til arbejdsplanen. Description og Unit staar tomme, indtil
    # materialeopslaget mod SAP er paa plads - felterne findes allerede, saa
    # opslaget kun skal fylde dem ud og ikke aendre skemaet.
    ("colVhpMaterials",
     {"ItemId": 0, "LineId": 0, "MaterialNo": '""', "Description": '""',
      "Unit": '""', "Quantity": 0, "OperationNo": '""', "Selected": "false"}),
    # Dokumenter. OperationsKey er ";0010;0020;" ligesom PackagesKey -
    # tomt (";") betyder at dokumentet hoerer til hele planen og ikke til
    # en bestemt operation.
    # FileName er noeglen paa raekken, ikke et loebenummer: SharePoint
    # tillader ikke to filer med samme navn i samme mappe, saa navnet er
    # unikt, stabilt og kendt af begge sider. Identifier kommer fra
    # Get-flowet og er det, sletningen skal bruge; FileUrl er linket.
    ("colVhpAttachments",
     {"ItemId": 0, "FileName": '""', "FileUrl": '""', "Identifier": '""',
      "FileSize": 0, "OperationsKey": '";"', "Status": '""',
      "Selected": "false"}),
    # Arbejdsspand til opdateringen fra biblioteket. colVhpAttKeep holder
    # operationskoblingen fast, mens raekkerne skiftes ud - den findes kun
    # i appen og ville ellers gaa tabt ved hver opdatering.
    ("colVhpAttFiles",
     {"Name": '""', "Link": '""', "Identifier": '""'}),
    ("colVhpAttKeep",
     {"FileName": '""', "OperationsKey": '";"'}),
    # Hvad flowet svarede paa hver enkelt fil ved upload. Uden den kunne
    # knappen kun kvittere paa tro og love.
    ("colVhpAttUp",
     {"Name": '""', "Ok": "false"}),
    # Kobler appens lokale ItemId til den raekke, der blev oprettet i
    # MaintenanceItems. Operationerne har brug for begge dele til deres
    # opslagsfelt, og de kan foerst kendes EFTER items er skrevet.
    ("colVhpSavedItems", {"LocalId": 0, "SpId": 0, "ItemKey": '""'}),
    # Samme aerinde for operationerne. Materialerne peger paa TaskItemID,
    # og den kan foerst kendes EFTER operationen er skrevet.
    ("colVhpSavedOps",
     {"LocalItemId": 0, "OperationNo": '""', "SpId": 0, "TaskKey": '""'}),
]
