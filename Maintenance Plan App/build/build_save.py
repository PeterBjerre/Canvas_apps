# -*- coding: utf-8 -*-
"""
Gem en indmelding i SharePoint.

FIRE LISTER SKRIVES
-------------------
    MaintenancePlans    planhovedet          -> PlanID   MP0068
    MaintenanceItems    eet pr. item         -> ItemID   MI0112
    TaskListMain        eet pr. operation    -> TaskItemID TI0341
    MD_RequestIndex     EEN opsummering      -> hubben laeser kun den

NOEGLERNE
---------
Den gamle app afleder noeglen af SharePoints eget ID minus et fast offset:
PlanID = ID - 5, ItemID = ID - 6, TaskItemID = ID - 1 (i DEV). Det holder i
ALLE 398 eksisterende raekker. Da ID tildeles atomart, er der ingen
kapløbstilstand - to samtidige indsendelser kan ikke faa samme noegle.

Offsettet staar i AppSettings, men KUN for DEV. I stedet for at gaette paa 0
i TEST og PROD udledes det af data: nyeste raekkes ID minus dens eget nummer.
Det er selvkorrigerende og miljoeuafhaengigt. Kan det ikke udledes
(tom liste, eller et nummer der ikke er et tal), bruges 0 for en tom liste
og ellers stoppes der - en forkert noegleserie er vaerre end en fejlbesked.

REKKEFOELGEN
------------
Planen foerst, saa items, saa operationer: hvert trin har brug for ID'et fra
det foregaaende til sit opslagsfelt. Ved gensave slettes de gamle items og
operationer foerst - en halv opdatering er sværere at rydde op i end en
gentagelse.

DET DER IKKE SKRIVES
--------------------
Nogle kolonner i de eksisterende lister kan ikke udfyldes forsvarligt herfra:

  MaintenancePlans.PlanType     eneste valgvaerdi er "PM" - siger intet om
                                IP41/IP42. StrategyKey baerer det i stedet.
  MaintenancePlans.Package      een enkelt pakke pr. plan. Appens matrix er
                                pr. operation og ligger i PackagesKey.
  MaintenancePlans.CallHorizon  skrives IKKE. Tre grunde, i den raekkefoelge
                                de vejer:

                                1. Den er TOM i alle 34 eksisterende planer.
                                   Den gamle app skriver den heller ikke, saa
                                   ingen mangler den.
                                2. Listen har TRE CallHorizon-kolonner efter
                                   oprydningen (CallHorizon som tal,
                                   CallHorizonChoiceOLD som valg,
                                   CallHorizonUnit). Hvilken der er den
                                   levende, er ikke afklaret.
                                3. Et forsoeg fejlede i compile:
                                   "argument 'CallHorizon' does not match the
                                   expected type 'Record'. Found type
                                   'Number'." SharePoint siger Number, men
                                   appens CACHEDE datakildeskema siger Choice
                                   - kolonnen blev doebt om, EFTER listen var
                                   tilfoejet som datakilde.

                                SchedulingPeriod skrives derimod. Den er
                                udfyldt i 9 af 34 planer, er et rent tal, og
                                har ingen navnetvivl.
  MultiCounterStrategy          bruges ikke af appen.

De staar tomme med vilje. Bliver de noedvendige for SAP-oprettelsen, skal
kilden afklares foerst - ikke gaettes her.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import (Ctrl, C_CARD_BG, C_CARD_BORDER, C_TITLE, C_MUTED, C_PRIMARY, C_WHITE,
                        C_VALID_FG, C_INVALID_FG, SHELL_W)
from build_helpers import text_ctrl, group, button, button_row, card
from build_plan_header import section_header
import sp_config as cfg

# Appens play-URL. Hubben bruger den til at aabne indmeldingen igen.
APP_URL = ("https://apps.powerapps.com/play/e/e0f8f822-d16a-e878-ba4e-fb42bc617e47"
           "/a/11fa8d90-868a-45a4-ba23-28f2cf0671a2")

DOMAIN = "MaintenancePlan"

# Appen aabner med eet tomt item, saa Item Editoren ikke staar graa (#8).
# Det maa ikke ende som en tom raekke i MaintenanceItems, hvis brugeren
# aldrig roerte det - og "mindst eet item" ville ellers vaere opfyldt af
# noget, ingen har skrevet i.
#
# Et item taeller foerst med, naar det har en kort tekst eller en
# funktionsplads. Begge dele er i forvejen paakraevede for at itemet kan
# blive valid, saa et item uden dem kan alligevel ikke gemmes meningsfuldt.
# Operationer paa et udeladt item falder selv fra: de slaar itemet op i
# colVhpSavedItems og springer over, naar det ikke er der.
SAVEABLE_ITEMS = ('Filter(\n'
                  '                            colVhpItems,\n'
                  '                            !IsBlank(Trim(ShortText)) || !IsBlank(FunctionalLocation)\n'
                  '                        )')
SAVEABLE_COUNT = ('CountRows(Filter(colVhpItems, '
                  '!IsBlank(Trim(ShortText)) || !IsBlank(FunctionalLocation)))')

# Appens Status (Ny/AEndre/Slettes) er AENDRINGSTYPEN pr. item, ikke
# arbejdsgangens status. De to maa ikke blandes sammen.
PLAN_STATUS_DRAFT = "Draft"
PLAN_STATUS_SUBMITTED = "In Progress"


def _offset(list_name, key_field, prefix):
    """Offsettet mellem SharePoints ID og forretningsnoeglen.

    Udledt af den nyeste raekke i stedet for af AppSettings, som kun har
    vaerdier for DEV. Blank paa en tom liste - saa starter serien paa ID."""
    return (
        f"With(\n"
        f"    {{ r: First(Sort({list_name}, ID, SortOrder.Descending)) }},\n"
        f"    If(\n"
        f"        IsBlank(r.ID), 0,\n"
        f"        IsNumeric(Mid(r.{key_field}, {len(prefix) + 1})),\n"
        f"        r.ID - Value(Mid(r.{key_field}, {len(prefix) + 1})),\n"
        f"        Blank()\n"
        f"    )\n"
        f")"
    )


def _key(prefix, id_expr, off_var):
    return f"\"{prefix}\" & Text({id_expr} - {off_var}, \"0000\")"


def save_action(submit=False):
    """Hele gemningen som eet Power Fx-udtryk."""
    plan_status = PLAN_STATUS_SUBMITTED if submit else PLAN_STATUS_DRAFT
    idx_status = "Indsendt" if submit else "Kladde"
    idx_step = 2 if submit else 1
    verb = "indsendt" if submit else "gemt"

    # Planhovedets felter. PlannedDate samles af de tre First Call-felter.
    plan_fields = (
        "{\n"
        "            Title: varVhpPlan.PlanText,\n"
        f"            Status: {{ Value: \"{plan_status}\" }},\n"
        "            PlantsInitial: { Value: varVhpPlan.Plant },\n"
        "            Cycle: varVhpPlan.Cycle,\n"
        "            Unit: { Value: varVhpPlan.Unit },\n"
        "            PlannedDate: Date(\n"
        "                varVhpPlan.FirstCallYear, varVhpPlan.FirstCallMonth, varVhpPlan.FirstCallDay\n"
        "            ),\n"
        "            StrategyKey: varVhpPlan.Strategy,\n"
        # CallHorizon skrives IKKE. Se docstringen oeverst.
        "            SchedulingPeriod: LookUp(\n"
        "                colVhpCallHorizonOptions, Value = varVhpPlan.CallHorizon\n"
        "            ).SchedPeriod,\n"
        f"            SortField: With(\n"
        f"                {{ sf: LookUp({cfg.L_SORTFIELDS}, Title = varVhpPlan.SortField) }},\n"
        "                If(IsBlank(sf.ID), Blank(), { Id: sf.ID, Value: sf.Title })\n"
        "            )\n"
        "        }"
    )

    item_fields = (
        "{\n"
        "                        Title: IT.ShortText,\n"
        "                        Status: { Value: Switch(varVhpPlan.Status,\n"
        "                            \"Ny\", \"New\", \"AEndre\", \"Change\", \"Slettes\", \"Deleted\", \"New\") },\n"
        "                        MaintenancePlanNo: { Id: planId, Value: planKey },\n"
        "                        ItemDescription: Coalesce(IT.LongText, IT.ShortText),\n"
        "                        FunctionalLocation: IT.FunctionalLocation,\n"
        "                        ObjectList: IT.ObjectList,\n"
        # Priority er obligatorisk i listen, men appen har ikke feltet.
        # Standardvaerdien hedder bogstaveligt "Yellow (default)".
        "                        Priority: { Value: \"Yellow (default)\" },\n"
        # Person-kolonnen er obligatorisk. Indsenderen staar som ansvarlig,
        # indtil appen faar en rigtig personvaelger. Teksten ved siden af er
        # den, der kan filtreres delegerbart.\n
        "                        OrstedResponsible: {\n"
        "                            '@odata.type': \"#Microsoft.Azure.Connectors.SharePoint.SPListExpandedUser\",\n"
        "                            Claims: \"i:0#.f|membership|\" & Lower(User().Email),\n"
        "                            DisplayName: User().FullName,\n"
        "                            Email: User().Email,\n"
        "                            Department: \"\",\n"
        "                            JobTitle: \"\",\n"
        "                            Picture: \"\"\n"
        "                        },\n"
        "                        OrstedResponsibleEmail: Lower(User().Email),\n"
        "                        InitialOrstedResponsible: IT.Initials,\n"
        f"                        MaintenanceActivityType: With(\n"
        f"                            {{ a: LookUp({cfg.L_ACTTYPES}, Title = IT.ActivityType) }},\n"
        "                            If(IsBlank(a.ID), Blank(), { Id: a.ID, Value: a.Title })\n"
        "                        ),\n"
        f"                        MainWorkCenter: With(\n"
        f"                            {{ w: LookUp({cfg.L_WORKCENTERS}, Trim(Title) = IT.MainWorkCenter) }},\n"
        "                            If(IsBlank(w.ID), Blank(), { Id: w.ID, Value: w.Title })\n"
        "                        )\n"
        "                    }"
    )

    op_fields = (
        "{\n"
        "                            Title: m.ItemKey & \" - \" & OP.OperationShortText,\n"
        "                            OperationShortText: OP.OperationShortText,\n"
        "                            OperationNo: Value(OP.OperationNo),\n"
        "                            PackagesKey: OP.PackagesKey,\n"
        "                            Work: OP.WorkHours,\n"
        "                            Num: OP.Persons,\n"
        "                            Duration: OP.DurationHours,\n"
        "                            WorkCtr: OP.MainWorkCenter,\n"
        "                            Ctrl: OP.ControlKey,\n"
        "                            Vendor: OP.Vendor,\n"
        "                            Price: OP.Cost,\n"
        "                            Currency: OP.Currency,\n"
        "                            CostElem: OP.CostElement,\n"
        "                            MaterialGroup: OP.MaterialGroup,\n"
        "                            LongText: OP.LongText,\n"
        "                            PlantInitial: varVhpPlan.Plant,\n"
        "                            MaintenanceItemNo: { Id: m.SpId, Value: m.ItemKey },\n"
        "                            MaintenancePlanID: { Id: planId, Value: planKey }\n"
        "                        }"
    )

    index_fields = (
        "{\n"
        f"                {cfg.C_INDEX_NO}: planKey,\n"
        f"                Domain: {{ Value: \"{DOMAIN}\" }},\n"
        f"                Status: {{ Value: \"{idx_status}\" }},\n"
        f"                StatusStep: {idx_step},\n"
        "                IsOpen: true,\n"
        "                RequestGuid: varVhpRequestGuid,\n"
        "                RequesterEmail: Lower(User().Email),\n"
        "                RequesterName: User().FullName,\n"
        "                ShortText: varVhpPlan.PlanText,\n"
        "                Plant: varVhpPlan.Plant,\n"
        f"                ItemCount: {SAVEABLE_COUNT},\n"
        "                SourceItemId: planId,\n"
        f"                AppUrl: \"{APP_URL}\",\n"
        "                LastActionOn: Now(),\n"
        "                LastActionBy: Lower(User().Email)\n"
        "            }"
    )

    return (
        "If(\n"
        f"    !varVhpPlanCommitted || {SAVEABLE_COUNT} = 0,\n"
        "    Notify(\"Create the plan and at least one item first.\", NotificationType.Warning),\n"
        "\n"
        "    Set(varVhpSaving, true);\n"
        "    IfError(\n"
        "        With(\n"
        "            {\n"
        f"                planOff: {_offset(cfg.L_PLANS, 'PlanID', 'MP')},\n"
        f"                itemOff: {_offset(cfg.L_ITEMS, 'ItemID', 'MI')},\n"
        f"                taskOff: {_offset(cfg.L_TASKS, 'TaskItemID', 'TI')}\n"
        "            },\n"
        "            If(\n"
        "                IsBlank(planOff) || IsBlank(itemOff) || IsBlank(taskOff),\n"
        # Hellere stoppe end at starte en ny noegleserie ved siden af den
        # eksisterende, uden at nogen opdager det.
        "                Notify(\n"
        "                    \"Cannot derive the keys from the existing rows. \" &\n"
        "                        \"Gemning afbrudt - kontakt SAP masterdata.\",\n"
        "                    NotificationType.Error\n"
        "                );\n"
        "                Set(varVhpSaving, false),\n"
        "\n"
        "                Set(varVhpRequestGuid, Coalesce(varVhpRequestGuid, Text(GUID())));\n"
        "\n"
        "                // --- 1. planhovedet ---------------------------------\n"
        "                With(\n"
        "                    {\n"
        "                        planRec: Patch(\n"
        f"                            {cfg.L_PLANS},\n"
        f"                            If(varVhpPlanSpId > 0, LookUp({cfg.L_PLANS}, ID = varVhpPlanSpId),\n"
        f"                                Defaults({cfg.L_PLANS})),\n"
        f"                            {plan_fields}\n"
        "                        )\n"
        "                    },\n"
        "                    With(\n"
        "                        {\n"
        "                            planId: planRec.ID,\n"
        f"                            planKey: Coalesce(planRec.PlanID, {_key('MP', 'planRec.ID', 'planOff')})\n"
        "                        },\n"
        f"                        Patch({cfg.L_PLANS}, planRec, {{ PlanID: planKey }});\n"
        "                        Set(varVhpPlanSpId, planId);\n"
        "                        Set(varVhpPlanKey, planKey);\n"
        "\n"
        "                        // --- 2. ryd det gamle -----------------------\n"
        "                        // Ved gensave er det enklere og sikrere at\n"
        "                        // skrive linjerne forfra end at finde ud af\n"
        "                        // hvilke der er tilfoejet, aendret og slettet.\n"
        # Remove(kilde, Filter(...)) og IKKE RemoveIf.
        #
        # RemoveIf delegeres ikke til SharePoint paa en tekstkolonne, og
        # heller ikke paa en opslagskolonnes underfelt. Dokumentationen
        # modsiger endda sig selv om HVOR meget der hentes foerst: Remove-
        # siden siger "all data matching the filter expression, up to 500 or
        # 2000", UpdateIf-siden siger "only the initial portion of the data
        # source". Den tvetydighed er ikke noget at bygge paa, naar den
        # foerst bider paa en liste der er vokset.
        #
        # Filter ER delegerbart paa SharePoint for = paa tekst og paa et
        # opslags underfelt, saa filtreringen sker paa serveren, og Remove
        # faar praecis de raekker der skal vaek.
        f"                        Remove({cfg.L_MATERIALS},\n"
        f"                            Filter({cfg.L_MATERIALS}, PlanKey = planKey));\n"
        f"                        Remove({cfg.L_ATTACHMENTS},\n"
        f"                            Filter({cfg.L_ATTACHMENTS}, PlanKey = planKey));\n"
        f"                        Remove({cfg.L_TASKS},\n"
        f"                            Filter({cfg.L_TASKS}, MaintenancePlanID.Id = planId));\n"
        f"                        Remove({cfg.L_ITEMS},\n"
        f"                            Filter({cfg.L_ITEMS}, MaintenancePlanNo.Id = planId));\n"
        "\n"
        "                        // --- 3. items ------------------------------\n"
        "                        Clear(colVhpSavedItems);\n"
        "                        ForAll(\n"
        f"                            {SAVEABLE_ITEMS} As IT,\n"
        "                            With(\n"
        "                                {\n"
        "                                    itemRec: Patch(\n"
        f"                                        {cfg.L_ITEMS}, Defaults({cfg.L_ITEMS}),\n"
        f"                                        {item_fields}\n"
        "                                    )\n"
        "                                },\n"
        f"                                With(\n"
        f"                                    {{ itemKey: {_key('MI', 'itemRec.ID', 'itemOff')} }},\n"
        f"                                    Patch({cfg.L_ITEMS}, itemRec, {{ ItemID: itemKey }});\n"
        "                                    Collect(\n"
        "                                        colVhpSavedItems,\n"
        "                                        { LocalId: IT.ItemId, SpId: itemRec.ID, ItemKey: itemKey }\n"
        "                                    )\n"
        "                                )\n"
        "                            )\n"
        "                        );\n"
        "\n"
        "                        // --- 4. operationer ------------------------\n"
        "                        Clear(colVhpSavedOps);\n"
        "                        ForAll(\n"
        "                            colVhpOperations As OP,\n"
        "                            With(\n"
        "                                { m: LookUp(colVhpSavedItems, LocalId = OP.ItemId) },\n"
        "                                If(\n"
        "                                    IsBlank(m.SpId), false,\n"
        "                                    With(\n"
        "                                        {\n"
        "                                            opRec: Patch(\n"
        f"                                                {cfg.L_TASKS}, Defaults({cfg.L_TASKS}),\n"
        f"                                                {op_fields}\n"
        "                                            )\n"
        "                                        },\n"
        f"                                        With(\n"
        f"                                            {{ taskKey: {_key('TI', 'opRec.ID', 'taskOff')} }},\n"
        f"                                            Patch({cfg.L_TASKS}, opRec, {{ TaskItemID: taskKey }});\n"
        "                                            Collect(\n"
        "                                                colVhpSavedOps,\n"
        "                                                {\n"
        "                                                    LocalItemId: OP.ItemId,\n"
        "                                                    OperationNo: OP.OperationNo,\n"
        "                                                    SpId: opRec.ID,\n"
        "                                                    TaskKey: taskKey\n"
        "                                                }\n"
        "                                            )\n"
        "                                        )\n"
        "                                    )\n"
        "                                )\n"
        "                            )\n"
        "                        );\n"
        "\n"
        "                        // --- 5. materialer -------------------------\n"
        "                        // Peger paa operationens TaskItemID, ikke paa\n"
        "                        // itemet. Et materiale hoerer til EEN\n"
        "                        // operation - det er den relation SAP har.\n"
        "                        ForAll(\n"
        "                            colVhpMaterials As MT,\n"
        "                            With(\n"
        "                                {\n"
        "                                    it: LookUp(colVhpSavedItems, LocalId = MT.ItemId),\n"
        "                                    op: LookUp(\n"
        "                                        colVhpSavedOps,\n"
        "                                        LocalItemId = MT.ItemId && OperationNo = MT.OperationNo\n"
        "                                    )\n"
        "                                },\n"
        "                                If(\n"
        "                                    IsBlank(MT.MaterialNo), false,\n"
        f"                                    Patch(\n"
        f"                                        {cfg.L_MATERIALS}, Defaults({cfg.L_MATERIALS}),\n"
        "                                        {\n"
        f"                                            {cfg.C_MATERIAL_NO}: MT.MaterialNo,\n"
        "                                            PlanKey: planKey,\n"
        "                                            ItemKey: it.ItemKey,\n"
        "                                            TaskItemID: op.TaskKey,\n"
        "                                            OperationNo: MT.OperationNo,\n"
        "                                            Quantity: MT.Quantity,\n"
        "                                            MaterialText: MT.Description,\n"
        "                                            Unit: MT.Unit,\n"
        "                                            LineId: MT.LineId\n"
        "                                        }\n"
        "                                    )\n"
        "                                )\n"
        "                            )\n"
        "                        );\n"
        "\n"
        "                        // --- 6. dokumenter -------------------------\n"
        "                        // OperationsKey er ';0010;0020;'. Tom (';')\n"
        "                        // betyder hele itemet.\n"
        "                        //\n"
        "                        // UploadStatus skrives som Pending.\n"
        "                        //\n"
        "                        // Her stod, at FLOWET retter den bagefter. Det\n"
        "                        // goer det ikke: BioSap-TaskListAttachment\n"
        "                        // bestaar af eet CreateFile og et svar, og\n"
        "                        // roerer aldrig denne liste. Raekken bliver\n"
        "                        // staaende som Pending, indtil appen selv\n"
        "                        // retter den - den kender flowets svar.\n"
        "                        // Se docs/18-materialer-og-attachments.md.\n"
        "                        ForAll(\n"
        "                            colVhpAttachments As AT,\n"
        "                            With(\n"
        "                                { it: LookUp(colVhpSavedItems, LocalId = AT.ItemId) },\n"
        "                                If(\n"
        "                                    IsBlank(AT.FileName), false,\n"
        f"                                    Patch(\n"
        f"                                        {cfg.L_ATTACHMENTS}, Defaults({cfg.L_ATTACHMENTS}),\n"
        "                                        {\n"
        f"                                            {cfg.C_FILE_NAME}: AT.FileName,\n"
        "                                            PlanKey: planKey,\n"
        "                                            ItemKey: it.ItemKey,\n"
        "                                            OperationsKey: Coalesce(AT.OperationsKey, \";\"),\n"
        "                                            FileSize: AT.FileSize,\n"
        "                                            LineId: AT.LineId,\n"
        "                                            UploadStatus: { Value: \"Pending\" }\n"
        "                                        }\n"
        "                                    )\n"
        "                                )\n"
        "                            )\n"
        "                        );\n"
        "\n"
        "                        // --- 7. opsummering til landingssiden ------\n"
        "                        // Hubben laeser KUN denne raekke. Den skal\n"
        "                        // skrives hver gang status aendrer sig,\n"
        "                        // ellers viser oversigten noget forkert.\n"
        "                        Patch(\n"
        f"                            {cfg.L_INDEX},\n"
        "                            Coalesce(\n"
        f"                                LookUp({cfg.L_INDEX}, RequestGuid = varVhpRequestGuid),\n"
        f"                                Defaults({cfg.L_INDEX})\n"
        "                            ),\n"
        f"                            {index_fields}\n"
        "                        );\n"
        "\n"
        "                        Set(varVhpSaving, false);\n"
        "                        Set(\n"
        "                            varVhpRuntimeInfo,\n"
        f"                            planKey & \" {verb}: \" & Text(CountRows(colVhpItems)) &\n"
        "                                \" item(s) og \" & Text(CountRows(colVhpOperations)) &\n"
        "                                \" operation(er).\"\n"
        "                        );\n"
        f"                        Notify(planKey & \" {verb}.\", NotificationType.Success)\n"
        "                    )\n"
        "                )\n"
        "            )\n"
        "        ),\n"
        "\n"
        "        Set(varVhpSaving, false);\n"
        "        Set(varVhpRuntimeInfo, \"Gemning fejlede: \" & FirstError.Message);\n"
        "        Notify(\"Gemning fejlede: \" & FirstError.Message, NotificationType.Error)\n"
        "    )\n"
        ")"
    )


def build_save_section():
    header = section_header("conVhpSaveHead", "Gem i SharePoint",
                            "The plan, its items and operations are written to the lists, "
                            "and the request appears on the landing page.", "Step 6")

    state = text_ctrl(
        "txtVhpSaveState",
        (
            "If(\n"
            "    varVhpSaving, \"Gemmer ...\",\n"
            "    IsBlank(varVhpPlanKey),\n"
            "        \"Not saved yet. Save as draft so you can come back to it.\",\n"
            "    \"Saved as \" & varVhpPlanKey & \". The next save overwrites items and \" &\n"
            "        \"operations on the same plan.\"\n"
            ")"
        ),
        size=13, height=20, wrap="true",
        color=f"If(IsBlank(varVhpPlanKey), {C_MUTED}, {C_VALID_FG})")

    # Samme maal som selve gemningen: et tomt item taeller ikke med, saa
    # knappen bliver ikke aktiv af det item, appen selv aabnede med.
    DM = ("If(\n"
          f"    varVhpSaving || !varVhpPlanCommitted || {SAVEABLE_COUNT} = 0,\n"
          "    DisplayMode.Disabled,\n"
          "    DisplayMode.Edit\n"
          ")")

    btnDraft = button("btnVhpSaveDraft", "\"Gem kladde\"", save_action(submit=False),
                      display_mode=DM)
    btnSubmit = button("btnVhpSubmit", "\"Indsend\"", save_action(submit=True),
                       primary=True, display_mode=DM)
    # Kortet har 18 px polstring i hver side.
    CARD_W = f"({SHELL_W} - 36)"
    row = button_row("conVhpSaveActions", [btnDraft, btnSubmit], container_w=CARD_W)

    hint = text_ctrl(
        "txtVhpSaveHint",
        (
            "\"Draft = saved but not sent on. Submit marks it as \" &\n"
            "\"ready for processing on the landing page. The key (the MP number) \" &\n"
            "\"is assigned by SharePoint and cannot collide with anyone else's.\""
        ),
        size=12, color=C_MUTED, height=32, wrap="true")

    return card("conVhpSaveCard", [header, state, row, hint], gap=10)
