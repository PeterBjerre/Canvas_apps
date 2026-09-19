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
    items_src = f"Filter({cfg.L_ITEMS}, MaintenancePlanNo.Id = pl.ID)"
    ops_src = f"Filter({cfg.L_TASKS}, MaintenancePlanID.Id = pl.ID)"
    mat_src = f"Filter({cfg.L_MATERIALS}, PlanKey = pl.PlanID)"
    att_src = f"Filter({cfg.L_ATTACHMENTS}, PlanKey = pl.PlanID)"

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
        "                // --- items ---------------------------------------\n"
        f"                {_collect('colVhpItems', items_src, 'IT', ITEM_FIELDS, 16)};\n"
        "\n"
        "                // Den samme oversaettelse, gemningen selv bygger.\n"
        "                // Materialer og dokumenter peger paa ItemKey.\n"
        "                ClearCollect(\n"
        "                    colVhpSavedItems,\n"
        "                    ForAll(\n"
        f"                        {items_src} As IT,\n"
        "                        { LocalId: IT.ID, SpId: IT.ID, ItemKey: IT.ItemID }\n"
        "                    )\n"
        "                );\n"
        "\n"
        "                // --- operationer, materialer, dokumenter ---------\n"
        f"                {_collect('colVhpOperations', ops_src, 'OP', OP_FIELDS, 16)};\n"
        f"                {_collect('colVhpMaterials', mat_src, 'MT', MAT_FIELDS, 16)};\n"
        f"                {_collect('colVhpAttachments', att_src, 'AT', ATT_FIELDS, 16)};\n"
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
        "    With(\n"
        f"        {{ idx: LookUp({cfg.L_INDEX}, RequestGuid = Param(\"reqid\")) }},\n"
        "        With(\n"
        f"            {{ pl: LookUp({cfg.L_PLANS}, ID = idx.SourceItemId) }},\n"
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
