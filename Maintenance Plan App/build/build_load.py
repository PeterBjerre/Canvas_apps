# -*- coding: utf-8 -*-
"""
Indlaesning af en gemt plan - modstykket til build_save.py.

HVORFOR DEN FINDES
------------------
Masterdata Hub aabner en indmelding med sin egen play-URL plus
"?reqid=<RequestGuid>". VH-plan-appen laeste aldrig den parameter, saa
hubbens Aabn-knap startede en TOM app. Det saa ud som et defekt link; i
virkeligheden manglede modtageren.

VEJEN FRA GUID TIL PLAN
-----------------------
RequestGuid staar kun i indekslisten - MaintenancePlans har ingen
GUID-kolonne. Indekset baerer til gengaeld SourceItemId, som ER planens
ID i MaintenancePlans. Opslaget gaar derfor i to hop:

    MD_RequestIndex.RequestGuid  ->  SourceItemId  ->  MaintenancePlans.ID

NOEGLERNE I SAMLINGERNE
-----------------------
colVhpItems.ItemId er appens EGEN noegle, og den maa vaere hvad som helst,
saa laenge operationerne peger paa den samme. Her bruges SharePoint-ID'et:
TaskListMain.MaintenanceItemNo er et opslag paa netop det ID, saa
operationerne kan kobles til deres item uden en oversaettelsestabel.

Materialer og dokumenter peger derimod paa ItemKey ("MI0007"), ikke paa
ID'et. Derfor fyldes colVhpSavedItems - den samme oversaettelse gemningen
selv bygger - foerst, og de to slaar op i den.

HVAD DER IKKE KAN LAESES TILBAGE
-------------------------------
Gemningen skriver dem ikke, saa de staar tomme efter en indlaesning:

    TasklistKey / TasklistName   itemets valgte standardarbejdsplan
    FlDescription                teksten ved funktionspladsen

Ingen af delene bruges til andet end visning og til at hente nye
operationslinjer. Operationerne selv kommer med.
"""
import sp_config as cfg
from build_helpers import concurrent

# Et helt tomt item, saa Item Editoren staar klar (#8). Bruges baade naar
# appen aabnes uden dyblink, og naar et dyblink ikke kan findes.
EMPTY_ITEM_FIELDS = [
    ("ItemId", "1"), ("ShortText", '""'), ("FunctionalLocation", '""'),
    ("FlDescription", '""'), ("MainWorkCenter", '""'), ("ActivityType", '""'),
    ("ObjectList", '""'), ("Revision", '""'), ("OrstedResponsible", '""'),
    ("Initials", '""'), ("LongText", '""'), ("TasklistKey", '""'),
    ("TasklistName", '""'), ("Status", '"draft"'),
]

# Planhovedet. Feltnavnene SKAL vaere de samme som i OnStart's foerste
# Set(varVhpPlan, ...) - en record med andre felter er en anden type, og
# Power Fx afviser den. generate_app_onstart efterproever det ved byg.
PLAN_FIELDS = [
    ("Plant", "pl.PlantsInitial.Value"),
    ("Status", '""'),
    ("PlanType", 'If(IsBlank(pl.StrategyKey), "SingleCycle", "Strategy")'),
    ("Strategy", 'Coalesce(pl.StrategyKey, "")'),
    ("PlanText", "pl.Title"),
    ("SortField", "pl.SortField.Value"),
    ("Cycle", "pl.Cycle"),
    ("Unit", "pl.Unit.Value"),
    # Gemningen skriver SchedulingPeriod (tallet), ikke teksten. Vejen
    # tilbage gaar gennem den samme matrix, som fyldte dropdownen.
    ("CallHorizon",
     "LookUp(\n                            colVhpCallHorizonOptions, "
     "SchedPeriod = pl.SchedulingPeriod\n                        ).Value"),
    ("SchedulingIndicator", "pl.SchedulingIndicator.Value"),
    ("FirstCallDay", "Day(pl.PlannedDate)"),
    ("FirstCallMonth", "Month(pl.PlannedDate)"),
    ("FirstCallYear", "Year(pl.PlannedDate)"),
    ("StatutorySortField", '""'),
]

# --- felt for felt, som modstykke til build_save ---------------------------
ITEM_FIELDS = [
    ("ItemId", "IT.ID"),
    ("ShortText", "IT.Title"),
    ("FunctionalLocation", "IT.FunctionalLocation"),
    ("FlDescription", '""'),
    ("MainWorkCenter", "IT.MainWorkCenter.Value"),
    ("ActivityType", "IT.MaintenanceActivityType.Value"),
    ("ObjectList", "IT.ObjectList"),
    ("Revision", "IT.RevisionMark.Value"),
    ("OrstedResponsible", "IT.OrstedResponsibleEmail"),
    ("Initials", "IT.InitialOrstedResponsible"),
    ("LongText", "IT.ItemDescription"),
    ("TasklistKey", '""'),
    ("TasklistName", '""'),
    # Raekken har vaeret gemt, saa den har bestaaet valideringen.
    ("Status", '"valid"'),
]

OP_FIELDS = [
    ("ItemId", "OP.MaintenanceItemNo.Id"),
    # OperationNo er et TAL i listen og en streng i appen - "0010" sorterer
    # og sammenlignes som tekst hele vejen igennem skaermen.
    ("OperationNo", 'Text(OP.OperationNo, "0000")'),
    ("OperationShortText", "OP.OperationShortText"),
    ("WorkHours", "OP.Work"),
    ("Persons", "OP.Num"),
    ("DurationHours", "OP.Duration"),
    ("MainWorkCenter", "OP.WorkCtr"),
    ("Vendor", "OP.Vendor"),
    ("LongText", "OP.LongText"),
    ("PackagesKey", 'Coalesce(OP.PackagesKey, ";")'),
    ("Selected", "false"),
    ("ControlKey", "OP.Ctrl"),
    ("Cost", "OP.Price"),
    # Satsen gemmes ikke - TaskListMain har kun beloebet. Den regnes tilbage
    # af beloeb og timer, saa en genaabnet PM03-linje stadig kan regne sit
    # beloeb om, naar timerne rettes.
    ("UnitCost", 'If(Coalesce(OP.Work, 0) > 0, OP.Price / OP.Work, OP.Price)'),
    ("Currency", "OP.Currency"),
    ("CostElement", "OP.CostElem"),
    ("MaterialGroup", "OP.MaterialGroup"),
]

MAT_FIELDS = [
    ("ItemId", "LookUp(colVhpSavedItems, ItemKey = MT.ItemKey).LocalId"),
    ("LineId", "MT.LineId"),
    ("MaterialNo", f"MT.{cfg.C_MATERIAL_NO}"),
    ("Description", "MT.MaterialText"),
    ("Unit", "MT.Unit"),
    ("Quantity", "MT.Quantity"),
    ("OperationNo", "MT.OperationNo"),
    ("Selected", "false"),
]

ATT_FIELDS = [
    ("ItemId", "LookUp(colVhpSavedItems, ItemKey = AT.ItemKey).LocalId"),
    ("FileName", f"AT.{cfg.C_FILE_NAME}"),
    ("FileUrl", "AT.FileUrl"),
    # Identifier gemmes ikke - den hoerer til biblioteket, ikke til listen.
    # Knappen "Refresh from SharePoint" henter den, og foerst derefter kan
    # en genaabnet plan slette filen og ikke kun appens raekke.
    ("Identifier", '""'),
    ("FileSize", "AT.FileSize"),
    ("OperationsKey", 'Coalesce(AT.OperationsKey, ";")'),
    ("Status", "AT.UploadStatus.Value"),
    ("Selected", "false"),
]

_MAPPINGS = {
    "colVhpItems": ITEM_FIELDS,
    "colVhpItems (tomt)": EMPTY_ITEM_FIELDS,
    "colVhpOperations": OP_FIELDS,
    "colVhpMaterials": MAT_FIELDS,
    "colVhpAttachments": ATT_FIELDS,
}


def check_mappings():
    """Hvert felt i skemaet skal fyldes af indlaesningen.

    ClearCollect saetter samlingens skema. Mangler et felt her, findes
    kolonnen ikke efter en indlaesning, og enhver formel, der laeser den,
    fejler - foerst naar nogen aabner et dyblink. Tilfoejer nogen et felt i
    WORKING_COLLECTIONS, siger byggeriet til med det samme i stedet."""
    problems = []
    for name, fields in _MAPPINGS.items():
        schema = dict(cfg.WORKING_COLLECTIONS)[name.split(" ")[0]]
        mapped = {k for k, _ in fields}
        missing = set(schema) - mapped
        extra = mapped - set(schema)
        if missing:
            problems.append(f"{name}: indlaesningen fylder ikke {sorted(missing)}")
        if extra:
            problems.append(f"{name}: indlaesningen fylder {sorted(extra)}, "
                            f"som ikke findes i skemaet")
    return problems


def _record(fields, indent):
    pad = " " * indent
    body = (",\n" + pad + "    ").join(f"{k}: {v}" for k, v in fields)
    return "{\n" + pad + "    " + body + "\n" + pad + "}"


def _collect(name, source, alias, fields, indent):
    pad = " " * indent
    return (f"ClearCollect(\n{pad}    {name},\n{pad}    ForAll(\n"
            f"{pad}        {source} As {alias},\n"
            f"{pad}        {_record(fields, indent + 8)}\n{pad}    )\n{pad})")


def load_block():
    """Hele indlaesningen som eet Power Fx-udtryk til App.OnStart."""
    # DE FIRE FILTRE MAALER MOD GLOBALE VARIABLER, IKKE MOD pl.
    #
    # SharePoint delegerer kun en sammenligning mod noget, der er ENS for
    # alle raekker: en global variabel, en kontrolegenskab eller en
    # konstant. pl.ID og pl.PlanID er felter i et With-scope, og compile
    # svarede med otte delegeringsadvarsler paa App.OnStart alene.
    #
    # De to variabler saettes i toppen af 'load', FOER hentningerne - og de
    # har praecis de samme vaerdier.
    items_src = f"Filter({cfg.L_ITEMS}, MaintenancePlanNo.Id = varVhpPlanSpId)"
    ops_src = f"Filter({cfg.L_TASKS}, MaintenancePlanID.Id = varVhpPlanSpId)"
    mat_src = f"Filter({cfg.L_MATERIALS}, PlanKey = varVhpPlanKey)"
    att_src = f"Filter({cfg.L_ATTACHMENTS}, PlanKey = varVhpPlanKey)"

    load = (
        "// --- planhovedet ---------------------------------\n"
        "                Set(\n"
        "                    varVhpPlan,\n"
        f"                    {_record(PLAN_FIELDS, 20)}\n"
        "                );\n"
        "                Set(varVhpPlanSpId, pl.ID);\n"
        "                Set(varVhpPlanKey, pl.PlanID);\n"
        "                Set(varVhpRequestGuid, idx.RequestGuid);\n"
        "                Set(varVhpPlanCommitted, true);\n"
        "\n"
        "                // --- de fem hentninger, PAA EEN GANG -------------\n"
        "                //\n"
        "                // Fem lister i kaede er fem rundture efter hinanden;\n"
        "                // appen venter paa SUMMEN. I Concurrent venter den kun\n"
        "                // paa den laengste.\n"
        "                //\n"
        "                // De fem er uafhaengige af hinanden. De afhaenger alle\n"
        "                // af 'pl' - men den er sat UDENFOR og er faerdig, foer\n"
        "                // Concurrent starter. Og varVhpActiveItemId nedenfor\n"
        "                // laeser colVhpItems: ogsaa sikkert, for Concurrent\n"
        "                // venter paa dem alle, foer den gaar videre.\n"
        # TO BOELGER, IKKE EEN
        #
        # Alle fem stod i det SAMME Concurrent. Power Apps afviste at
        # compile:
        #
        #   [App, OnStart] There is a dependency on 'colVhpSavedItems'
        #   between two different formulas in the Concurrent function.
        #   One formula is changing it while another may be reading it.
        #
        # Og den har ret: MAT_FIELDS og ATT_FIELDS slaar begge op i
        # colVhpSavedItems for at oversaette ItemKey til appens lokale
        # ItemId - og colVhpSavedItems fyldes af en AF de andre formler i
        # den samme Concurrent. Concurrent lover netop INGEN raekkefoelge,
        # saa de to sidste kunne laese en tom samling.
        #
        # Boelge 1 er de tre, der kun laeser SharePoint. Boelge 2 er de to,
        # der har brug for oversaettelsen. Fem sekventielle kald er dermed
        # stadig blevet til to ventetider, ikke fem.
        "                " + concurrent(
            _collect('colVhpItems', items_src, 'IT', ITEM_FIELDS, 20),
            # Den samme oversaettelse, gemningen selv bygger.
            # Materialer og dokumenter peger paa ItemKey.
            "ClearCollect(\n"
            "                        colVhpSavedItems,\n"
            "                        ForAll(\n"
            f"                            {items_src} As IT,\n"
            "                            { LocalId: IT.ID, SpId: IT.ID, ItemKey: IT.ItemID }\n"
            "                        )\n"
            "                    )",
            _collect('colVhpOperations', ops_src, 'OP', OP_FIELDS, 20),
            indent=16) + ";\n"
        "\n"
        "                // Disse to LAESER colVhpSavedItems, som boelge 1\n"
        "                // skriver. De kan derfor ikke koere sammen med den.\n"
        "                " + concurrent(
            _collect('colVhpMaterials', mat_src, 'MT', MAT_FIELDS, 20),
            _collect('colVhpAttachments', att_src, 'AT', ATT_FIELDS, 20),
            indent=16) + ";\n"
        "\n"
        "                // --- hvad der er valgt naar skaermen tegnes -------\n"
        "                Set(varVhpActiveItemId, First(colVhpItems).ItemId);\n"
        "                Set(varVhpNextItemId, Max(colVhpItems, ItemId));\n"
        "                Set(\n"
        "                    varVhpRuntimeInfo,\n"
        "                    \"Opened \" & idx.RequestNo & \" - \" &\n"
        "                        Text(CountRows(colVhpItems)) & \" item(s), \" &\n"
        "                        Text(CountRows(colVhpOperations)) & \" operation line(s).\"\n"
        "                )"
    )

    return (
        "// Dyblink fra Masterdata Hub: <app-url>?reqid=<RequestGuid>.\n"
        "//\n"
        "// Det er en datahentning i OnStart, og reglen er ellers, at der ikke\n"
        "// er nogen. Undtagelsen er bevidst og betales kun af den, der\n"
        "// FAKTISK aabner et dyblink: uden parameter koeres kun Collect af et\n"
        "// tomt item, og der roeres ingen liste. Se build_load.py.\n"
        "If(\n"
        "    IsBlank(Param(\"reqid\")),\n"
        "\n"
        f"    Collect(colVhpItems, {_record(EMPTY_ITEM_FIELDS, 4)}),\n"
        "\n"
        # Param() og idx.SourceItemId er heller ikke "ens for alle
        # raekker" i delegeringens forstand. Begge opslag maaler nu mod en
        # global variabel, der er sat lige foer - og de to variabler
        # findes i forvejen og faar de samme vaerdier lidt senere.
        "    Set(varVhpRequestGuid, Param(\"reqid\"));\n"
        "    With(\n"
        f"        {{ idx: LookUp({cfg.L_INDEX}, RequestGuid = varVhpRequestGuid) }},\n"
        "        Set(varVhpPlanSpId, idx.SourceItemId);\n"
        "        With(\n"
        f"            {{ pl: LookUp({cfg.L_PLANS}, ID = varVhpPlanSpId) }},\n"
        "            If(\n"
        "                IsBlank(pl.ID),\n"
        "\n"
        "                // Linket peger paa noget, der ikke er her - fx en\n"
        "                // indmelding fra et andet miljoe. Sig det, og aabn\n"
        "                // som en ny plan i stedet for at staa tom og tavs.\n"
        "                Notify(\n"
        "                    \"Could not find the request behind this link. Opening a new plan.\",\n"
        "                    NotificationType.Warning\n"
        "                );\n"
        f"                Collect(colVhpItems, {_record(EMPTY_ITEM_FIELDS, 16)}),\n"
        "\n"
        f"                {load}\n"
        "            )\n"
        "        )\n"
        "    )\n"
        ")"
    )
