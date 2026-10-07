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
# Hjaelpeteksterne. De stod i build_help.py og kunne kun rettes af den,
# der kunne bygge appen. Nu er de en liste. Se
# sharepoint/provision/Provision-HelpText.ps1.
L_HELP        = "MD_HelpText"
C_HELP_KEY    = "HelpKey"     # Title, omdoebt
# Samme vaerdi som Domain i MD_RequestIndex, saa de fem apps kan dele
# listen uden at laese hinandens tekster.
HELP_APP      = "MaintenancePlan"

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
#
# Afrundet til to decimaler som i den gamle app: 10 timer paa 3 personer er
# 3,33 og ikke 3,3333333 i TaskListMain og i SAP-ordren.
def duration_expr(work, persons):
    return f"Round({work} / Max(Coalesce({persons}, 1), 1), 2)"


# Beskrivelserne til Non Flow User Status-koderne (issue #112). Kun
# visningstekst: hvilke koder der kan vaelges, bestemmer SharePoint-kolonnen
# (Choices), og det er koden, der gemmes og sendes til SAP.
NON_FLOW_STATUS_TEXT = [
    ("INCD", "Create Synergy Incident Q-Case"),
    ("ZBUN", "Bundling"),
    ("ZMOC", "Create Synergy MoC Action Plan"),
    ("WADO", "Ope Waiting for documentation"),
    ("ZBOW", "Bowtie"),
    ("OPHO", "Operation on Hold"),
    ("UNEX", "Work Under Execution"),
    ("OFIX", "Operation Fixed"),
    ("REWO", "Maintenance Rework"),
]


def non_flow_desc(code):
    """Power Fx: beskrivelsen til en kode, blank hvis koden er ukendt."""
    pairs = ", ".join(f'"{k}", "{v}"' for k, v in NON_FLOW_STATUS_TEXT)
    return f"Switch({code}, {pairs}, Blank())"


NON_FLOW_DESC = non_flow_desc("c")


# Vaerk -> vaerket, hvis standardtaskliste det laaner, saa laenge det ingen
# har selv. Fra den gamle app (StandardTasklistGallery: HCV og SMV -> AVV).
TASKLIST_FALLBACK = {"HCV": "AVV", "SMV": "AVV"}


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
# ---------------------------------------------------------------------------
# Vaerdier der IKKE kommer fra en liste.
#
# De staar i SAP og aendrer sig ikke, og der er ingen der vedligeholder dem
# som masterdata. En liste med tre raekker, ingen roerer, er daarligere end
# en konstant man kan se.
#
# DE ER NAVNGIVNE FORMLER, IKKE SAMLINGER. App checker:
#
#   [Performance] App.OnStart: Collection is initialized but never updated
#   Rule: CollectingReadOnlyTable
#
# En samling koster sporingsarbejde, saa alt hvad der afhaenger af den,
# holdes i sync naar den aendrer sig. Disse to aendrer sig aldrig. En
# navngiven formel giver de samme raekker uden den omkostning - og uden at
# blive betalt i OnStart af hver bruger hver gang.
# ---------------------------------------------------------------------------
STATIC_TABLES = [
    ("colVhpPlanTypeOptions",
     [{"Key": "SingleCycle", "Value": "Single cycle plan (IP41)"},
      {"Key": "Strategy", "Value": "Strategy plan (IP42)"}],
     "Appens eget begreb, ikke et SAP-felt."),
]

def named_formulas():
    F = []

    def add(name, expr, why=None):
        F.append((name, expr, why))

    # --- simple opslagslister: appen forventer { Value } ---
    # HJAELPETEKSTERNE
    #
    # En navngiven formel: den laeses DOVENT og kun EEN gang. Ingen
    # hjaelpetekst koster noget, foer den foerste bliver vist, og derefter
    # er den cachet resten af sessionen. Listen har under hundrede raekker,
    # saa det er eet delegeret kald.
    #
    # Body er en Note-kolonne (ren tekst). Heading er tom paa hints.
    add("colVhpHelp",
        _forall(f'Filter({L_HELP}, AppArea.Value = "{HELP_APP}")',
                [("Key", f"R.{C_HELP_KEY}"),
                 ("Kind", "R.Kind.Value"),
                 ("Heading", "Coalesce(R.Heading, \"\")"),
                 ("Body", "Coalesce(R.Body, \"\")"),
                 # Ord, ikke Sort: "Sort(tabel, Sort)" er en kolonne med samme navn
                 # som funktionen. Power Fx loeser det, men ingen skal
                 # laese det to gange for at vaere sikker.
                 ("Ord", "Coalesce(R.SortOrder, 0)")]),
        "Hjaelpetekster. En manglende raekke = ingen tekst, ikke en fejl.")

    add("colVhpPlantCodes",
        f"Sort({_forall(L_PLANTS, [('Value', 'R.Title')])}, Value)")

    # Id baeres med, saa gem kan skrive opslaget uden at slaa op i
    # listen (REVIEW.md B7).
    add("colVhpSortFieldOptions",
        f"Sort({_forall(L_SORTFIELDS, [('Id', 'R.ID'), ('Value', 'R.Title')])}, Value)")

    # Id baeres med. Gem skal skrive { Id, Value } i opslagskolonnen, og
    # slog det foer op i SharePoint EEN GANG PR. ITEM inde i et ForAll -
    # et netvaerkskald pr. raekke, og en delegeringsadvarsel, fordi
    # sammenligningen var mod et ForAll-felt og ikke mod en variabel.
    add("colVhpActivityTypeOptions",
        f"Sort({_forall(L_ACTTYPES, [('Id', 'R.ID'), ('Value', 'R.Title')])}, Value)")

    # --- valgkolonner: Choices() giver allerede { Value } ---
    add("colVhpPlanStatusOptions", f"Choices({L_ITEMS}.Status)")
    add("colVhpUnitOptions",       f"Choices({L_PLANS}.Unit)")
    add("colVhpRevisionOptions",   f"Choices({L_ITEMS}.RevisionMark)")

    # NON FLOW USER STATUS (issue #112). Valgene ER SharePoint-kolonnen
    # MaintenanceItems.NonFlowUserStatus - et nyt valg dukker op i appen
    # uden en ny build. Vaerdien er SAP-koden alene (ZBOW): SAP-ordre-flowet
    # sender .Value direkte videre, og GUI-scriptet skriver den i
    # GV_NON_FLOW_USER_STAT. Derfor kan beskrivelsen ikke staa i selve
    # valget. Den slaas op her og er KUN visningstekst; en kode uden
    # beskrivelse vises som koden alene.
    #
    # Foerste raekke er "(none)" med tom Value, saa et valg kan fjernes igen -
    # en ModernDropdown kan ikke ryddes af brugeren. Sequence/Index i stedet
    # for Table(tabel, tabel), som ikke alle Power Fx-versioner kender.
    add("colVhpNonFlowStatusOptions",
        "With(\n"
        f"    {{ ch: Choices({L_ITEMS}.NonFlowUserStatus) }},\n"
        "    ForAll(\n"
        "        Sequence(CountRows(ch) + 1),\n"
        "        If(\n"
        "            Value = 1,\n"
        "            { Value: \"\", Display: \"(none)\" },\n"
        "            With(\n"
        "                { c: Index(ch, Value - 1).Value },\n"
        "                {\n"
        "                    Value: c,\n"
        "                    Display: c & With(\n"
        "                        { d: " + NON_FLOW_DESC + " },\n"
        "                        If(IsBlank(d), \"\", \" - \" & d)\n"
        "                    )\n"
        "                }\n"
        "            )\n"
        "        )\n"
        "    )\n"
        ")",
        "Non Flow User Status: valgene fra SharePoint, vist som kode - beskrivelse.")

    # --- arbejdscentre: baeres med vaerk, saa listen kan afgraenses ---
    # 53 arbejdscentre for hele afdelingen, ~7 der er relevante for det
    # valgte vaerk. Trim, fordi SAP-eksporten er polstret med mellemrum.
    add("colVhpMainWorkCenters",
        _forall(L_WORKCENTERS, [("Id", "R.ID"),
                                ("Value", "Trim(R.Title)"),
                                ("Plant", f"Trim(R.{C_WC_PLANT})")]),
        "Alle arbejdscentre med deres vaerk. Afgraenses i kontrollen.")

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

    # Kun til drpVhpStrategy: samme form som colVhpPlanTypeOptions, { Key,
    # Value }, og bygget direkte paa MD_Strategy. Issue #45: et --clean-
    # deploy, hvor kontrollen oprettes forfra, gav "'Selected' isn't
    # recognized" paa drpVhpStrategy - den eneste dropdown, hvis Items bar
    # valgkolonner (SchedulingIndicator.Value, Hierarchical.Value) og en
    # boolsk kolonne. drpVhpPlanType, med en ren { Key, Value }-tabel, gik
    # igennem. Dropdownen skal kun bruge noeglen og teksten; resten af
    # strategien slaas op i colVhpStrategies.
    add("colVhpStrategyOptions",
        "Sort(" + _forall(
            L_STRATEGY,
            [("Key", f"R.{C_STRATEGY_KEY}"),
             ("Value", f"R.{C_STRATEGY_KEY} & \" - \" & R.StrategyName & "
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
    # STANDARDOPERATIONERNE HENTES EEN GANG
    #
    # Her stod Filter(MD_StandardTaskOperations, Plant.Value = P.Value)
    # inde i et ForAll over vaerkerne: eet opslag PR. VAERK, og ingen af
    # dem delegerbare, fordi P.Value er et scope-felt. Hvert opslag hentede
    # derfor 500 raekker hjem og filtrerede lokalt - og har listen mere end
    # 500 raekker, er svaret ikke bare langsomt, det er forkert.
    #
    # colVhpStdOps henter listen EEN gang (dovent, og kun hvis nogen aabner
    # en tasklist). Resten er filtrering i hukommelsen, hvor delegering
    # ikke er et begreb.
    add("colVhpStdOps",
        _forall(L_STDOPS, [("Plant", "O.Plant.Value"),
                           ("OperationNo", "O.OperationNo"),
                           ("OperationShortText", "O.OperationShortText"),
                           ("Work", "O.Work"),
                           ("NumberOfCapacities", "O.NumberOfCapacities"),
                           ("WorkCenter", "O.WorkCenter"),
                           ("VendorNo", "O.VendorNo"),
                           ("ControlKey", "O.ControlKey"),
                           ("Price", "O.Price"),
                           ("Currency", "O.Currency"),
                           ("CostElement", "O.CostElement"),
                           ("MaterialGroup", "O.MaterialGroup"),
                           ("ServiceNo", "O.ServiceNo"),
                           ("SapPlant", "O.SapPlant")],
                alias="O"),
        "Standardoperationerne, hentet een gang. colVhpTasklists deler dem "
        "op pr. vaerk i hukommelsen.")

    ops = _forall(
        "Sort(Filter(colVhpStdOps, Plant = P.Src), OperationNo)",
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
         # PM02 kommer ind med TOM varegruppe: brugeren angiver den rigtige
         # (M1 i build_status holder Submit tilbage, til den er udfyldt).
         ("MaterialGroup",
          "If(Upper(Trim(Coalesce(O.ControlKey, \"\"))) = \"PM02\", \"\", O.MaterialGroup)"),
         # Ydelsesnummeret vedligeholdes paa standardoperationen og foelger
         # med til TaskListMain. Kun PM03 har en ydelse.
         ("ServiceNo",
          "If(Upper(Trim(Coalesce(O.ControlKey, \"\"))) = \"PM03\", O.ServiceNo, \"\")"),
         ("OpPlant", "O.SapPlant")],
        alias="O")
    # VAERKER UDEN EGEN STANDARDARBEJDSPLAN. Den gamle app gav HCV og SMV
    # AVV's standardtaskliste (TASKLIST_FALLBACK). Har vaerket faaet sine
    # egne operationer i MD_StandardTaskOperations, bruges de i stedet.
    fallback = ", ".join(f'"{k}", "{v}"' for k, v in TASKLIST_FALLBACK.items())
    add("colVhpTasklistPlants",
        "Filter(\n"
        f"    ForAll(Choices({L_STDOPS}.Plant) As C,\n"
        "        {\n"
        "            Plant: C.Value,\n"
        "            Src: If(C.Value in colVhpStdOps.Plant, C.Value,\n"
        f"                Coalesce(Switch(C.Value, {fallback}), C.Value))\n"
        "        }\n"
        "    ),\n"
        "    Src in colVhpStdOps.Plant\n"
        ")",
        "Vaerkerne med en standardtaskliste, og hvis operationer den bruger.")
    add("colVhpTasklists",
        _forall("colVhpTasklistPlants",
                [("Plant", "P.Plant"),
                 ("Key", "P.Plant & \"-STD\""),
                 ("Name", "\"Standard task list - \" & P.Plant"),
                 ("Description", "\"\""),
                 ("Operations", ops)],
                alias="P"))

    # --- kaldshorisont og planlaegningsperiode ---
    # Den gamle VH-plan-app regnede dem ud fra CallHorizonMatrix og skrev
    # dem paa planen; Excel-opretteren har den samme tabel i arket Opslag.
    # CycleOrUnit er teksten "2 mon" - den deles her i tal og enhed, saa
    # opslaget ikke afhaenger af store/smaa bogstaver eller mellemrum.
    # Raekken uden cyklus (taellerbaseret) falder fra. 16 raekker, hentet
    # een gang, dovent.
    add("colVhpCallHorizon",
        "Filter(\n"
        f"    ForAll({L_CALLHORIZON} As H,\n"
        "        With({ t: Trim(Coalesce(H.CycleOrUnit, \"\")) },\n"
        "            With({ p: Find(\" \", t) },\n"
        "                {\n"
        "                    Cycle: If(IsBlank(p), Blank(), Value(Left(t, p - 1))),\n"
        "                    Unit: If(IsBlank(p), \"\", Upper(Trim(Mid(t, p + 1)))),\n"
        "                    Fcd: H.NewCallHorizonOrFCD,\n"
        "                    Period: H.SchedulingPeriodNum\n"
        "                }\n"
        "            )\n"
        "        )\n"
        "    ),\n"
        "    !IsBlank(Cycle) && !IsBlank(Unit)\n"
        ")",
        "CallHorizonMatrix som { Cycle, Unit, Fcd, Period }.")
    # Samme regel som den gamle app: den eksakte cyklus, og findes den ikke,
    # den naermeste MINDRE cyklus med samme enhed (5 WK -> 2 WK).
    add("VhpCallHorizon",
        "With(\n"
        "    { c: varVhpPlan.Cycle, u: Upper(varVhpPlan.Unit) },\n"
        "    First(Sort(Filter(colVhpCallHorizon, Unit = u && Cycle <= c), Cycle, SortOrder.Descending)).Fcd\n"
        ")",
        "Kaldshorisonten (FCD) for planens cyklus. Tom paa en strategiplan.")
    # Planlaegningsperioden kun ved eksakt cyklus - som i den gamle app.
    add("VhpSchedulingPeriod",
        "LookUp(colVhpCallHorizon, Unit = Upper(varVhpPlan.Unit) && Cycle = varVhpPlan.Cycle).Period",
        "Planlaegningsperioden (aar) for planens cyklus.")

    # De faste tabeller. Samme form som resten: en navngiven formel, der
    # laeses dovent og caches. Se STATIC_TABLES nedenfor.
    for name, rows, why in STATIC_TABLES:
        recs = ", ".join(
            "{ " + ", ".join(f'{k}: "{v}"' for k, v in r.items()) + " }"
            for r in rows)
        add(name, f"Table({recs})", why)

    return F


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
      # SAP-koden fra MaintenanceItems.NonFlowUserStatus; "" = ingen (#112).
      "NonFlowUserStatus": '""',
      "TasklistKey": '""', "TasklistName": '""', "Status": '""',
      # Raekkens ID i MaintenanceItems; 0 = ikke gemt endnu. Gem opdaterer
      # et item med SpId i stedet for at oprette det igen (REVIEW.md D7).
      "SpId": 0}),
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
      "CostElement": 0, "MaterialGroup": '""', "ServiceNo": '""',
      # Raekkens ID i TaskListMain; 0 = ny. Se colVhpItems.SpId.
      "SpId": 0}),
    ("colVhpFl",
     {"Code": '""', "Description": '""', "Display": '""',
      "Maintainable": "false", "Level": '""'}),
    ("colVhpItemObjects", {"ItemId": 0, "Code": '""', "Description": '""'}),
    # Kladden i Object List-popup'en. Foerst "Use selected" skriver den i
    # colVhpItemObjects; lukkes popup'en, er intet aendret.
    ("colVhpObjDraft", {"Code": '""', "Description": '""'}),
    ("colVhpPickerSelected", {"OperationNo": '""'}),
    # Items, hvis Tasklist and Operations er gemt og klappet sammen (issue
    # #103) - kun skaermens tilstand, aldrig gemt. Se build_tasklist.OPS_LOCKED.
    ("colVhpOpsDone", {"ItemId": 0}),
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
    # OpNo, ikke OperationNo: saa kan UpdateIf(colVhpOperations, ...) slaa
    # op i den uden at operationens eget felt skygges (build_save).
    ("colVhpSavedOps",
     {"LocalItemId": 0, "OpNo": '""', "SpId": 0, "TaskKey": '""'}),
    # Gemmets arbejdssamlinger (build_save.py): hvad der er i SharePoint
    # foer skrivningen, de gamle raekker, der slettes til sidst, og
    # trinenes fejl.
    # Sceq: raekken har SCEqFL eller SCEqOL - sikkerhedskritisk udstyr, som
    # den gamle app hentede fra FL-flowet. Prioriteten (build_save.PRIORITY)
    # holder et saadant item roedt, ogsaa naar det gemmes igen.
    ("colVhpSpItems", {"ID": 0, "ItemID": '""', "Sceq": "false"}),
    # Items, som de stod foer en ADMINS gemning af en andens plan - kun
    # hentet dér, til admin-loggen (tools/admin_log.py).
    ("colVhpAdmOld", {"ID": 0, "ItemID": '""', "Title": '""', "ItemDescription": '""',
                      "FunctionalLocation": '""', "ObjectList": '""'}),
    ("colVhpSpOps", {"ID": 0, "TaskItemID": '""'}),
    ("colVhpOldMats", {"ID": 0}),
    ("colVhpOldAtts", {"ID": 0}),
    ("colVhpSaveErrors", {"Where": '""', "Msg": '""'}),
]
