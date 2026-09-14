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

Navngivne formler (App.Formulas) evalueres DOVENT og caches: listen hentes
foerste gang en kontrol faktisk har brug for den, og kun een gang. Navnene
er de samme colVhp*, som skaermen allerede bruger, saa ingen af de 281
kontroller skal aendres.

Til gengaeld kan en navngiven formel ikke skrives til. De samlinger, appen
REDIGERER - items, operationer, soegeresultater - er derfor stadig
rigtige samlinger og staar i OnStart med tom skemadefinition.
"""

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

# --- kolonnenavne der IKKE er selvindlysende -------------------------------
# MainWorkCenters er oprettet fra Excel, saa de interne navne er field_1 og
# field_2. Visningsnavnet paa field_1 er 'Description' med 33 efterfoelgende
# MELLEMRUM - det kan ikke skrives paalideligt i Power Fx, saa appen bruger
# det ikke. 'Plant Key' er field_2 og er ufarlig; den skal blot i enkelte
# anfoerselstegn, fordi den indeholder et mellemrum.
C_WC_PLANT = "'Plant Key'"

# MD_Strategy: Title er omdoebt til StrategyKey ved provisioneringen.
C_STRATEGY_KEY = "StrategyKey"


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

    add("colVhpCallHorizonOptions",
        f"Sort({_forall(L_CALLHORIZON, [('Value', 'R.Title')])}, Value)")

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
                         "If(R.PackagesLoaded, \"\", \"   (pakker mangler)\")")])
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
         ("DurationHours", "0"),
         ("MainWorkCenter", "O.WorkCenter"),
         ("Vendor", "O.VendorNo"),
         ("LongText", "\"\""),
         ("ControlKey", "O.ControlKey"),
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
      "DurationHours": 0, "MainWorkCenter": '""', "Vendor": '""', "LongText": '""',
      "PackagesKey": '";"', "Selected": "false"}),
    ("colVhpFlSearch",
     {"Code": '""', "Description": '""', "Display": '""',
      "Maintainable": "false", "Level": '""'}),
    ("colVhpItemObjects", {"ItemId": 0, "Code": '""', "Description": '""'}),
    ("colVhpPickerSelected", {"OperationNo": '""'}),
]
