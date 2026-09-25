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

# Opslaget fra en operation til det item, der lige er skrevet. Stod foer
# som et per-raekke With({ m: LookUp(...) }) inde i den ForAll, der ogsaa
# skrev. Da skrivningen blev samlet i EET Patch-kald, kunne det With ikke
# blive staaende - saa opslaget staar nu direkte i feltet. Det er to
# opslag i stedet for eet, men de er i hukommelsen; det, der blev sparet,
# var et netvaerkskald pr. operation.
M_LOOKUP = "LookUp(colVhpSavedItems, LocalId = OP.ItemId)"
M_KEY = M_LOOKUP + ".ItemKey"
M_SPID = M_LOOKUP + ".SpId"

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


def _reindent(block, spaces):
    """Flyt en flerlinjet literal ind, saa den staar under det kald, den
    interpoleres ind i.

    Konstanterne her (item_fields, op_fields, SAVEABLE_ITEMS) er skrevet
    med den indrykning, de havde DENGANG de blev skrevet. Da gemningen
    blev lagt om til batch, rykkede kaldene to niveauer ind, og
    konstanterne fulgte ikke med - den byggede formel fik en record, der
    stod laengere til venstre end det ForAll, den var argument til.

    Foerste linje bliver staaende (den staar allerede efter noget andet
    paa samme linje); resten flyttes, saa den mindst indrykkede linje
    lander paa 'spaces'."""
    lines = block.split("\n")
    body = [l for l in lines[1:] if l.strip()]
    if not body:
        return block
    cur = min(len(l) - len(l.lstrip()) for l in body)
    pad = " " * spaces
    return lines[0] + "\n" + "\n".join(
        (pad + l[cur:]) if l.strip() else l for l in lines[1:])


def save_action(submit=False):
    """Hele gemningen som eet Power Fx-udtryk."""
    plan_status = PLAN_STATUS_SUBMITTED if submit else PLAN_STATUS_DRAFT
    idx_status = "Indsendt" if submit else "Kladde"
    idx_step = 2 if submit else 1
    verb = "submitted" if submit else "saved"

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
        # DEN HER SWITCH RAMTE ALDRIG
        #
        # Noeglerne var danske - "Ny", "AEndre", "Slettes" - men
        # varVhpPlan.Status kommer fra drpVhpStatus, hvis Items er
        # Choices(MaintenanceItems.Status). SharePoints egne valg
        # ER "New", "Change", "Deleted" (se schema.md). Ingen af de
        # tre danske noegler kunne derfor matche, og HVERT item blev
        # skrevet som "New" - ogsaa naar brugeren havde valgt Change
        # eller Deleted. Fundet under oversaettelsen til engelsk.
        #
        # Vaerdien er allerede den rigtige; der skal ikke oversaettes
        # noget. Coalesce daekker den tomme plan.
        "                        Status: { Value: Coalesce(varVhpPlan.Status, \"New\") },\n"
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
        # OPSLAG I SAMLINGEN, IKKE I LISTEN
        #
        # Her stod LookUp(MaintenanceActivityTypeList, ...) og
        # LookUp(MainWorkCenters, Trim(Title) = ...) - inde i et ForAll,
        # altsaa et SharePoint-opslag PR. ITEM. Begge er navngivne formler
        # i forvejen (dovent hentet, cachet, og nu med Id), saa opslaget
        # koster ingenting og kan ikke give en delegeringsadvarsel.
        #
        # Trim staar nu i den navngivne formel, hvor det udfoeres een gang
        # pr. arbejdscenter - ikke een gang pr. item.
        f"                        MaintenanceActivityType: With(\n"
        f"                            {{ a: LookUp(colVhpActivityTypeOptions, Value = IT.ActivityType) }},\n"
        "                            If(IsBlank(a.Id), Blank(), { Id: a.Id, Value: a.Value })\n"
        "                        ),\n"
        f"                        MainWorkCenter: With(\n"
        f"                            {{ w: LookUp(colVhpMainWorkCenters, Value = IT.MainWorkCenter) }},\n"
        "                            If(IsBlank(w.Id), Blank(), { Id: w.Id, Value: w.Value })\n"
        "                        )\n"
        "                    }"
    )

    op_fields = (
        "{\n"
        f"                            Title: {M_KEY} & \" - \" & OP.OperationShortText,\n"
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
        f"                            MaintenanceItemNo: {{ Id: {M_SPID}, Value: {M_KEY} }},\n"
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
        # VARIABLERNE, IKKE With-FELTERNE
        #
        # SharePoint delegerer kun en sammenligning mod noget, der er ENS
        # for alle raekker: en global variabel, en kontrolegenskab eller en
        # konstant. planKey og planId er felter i et With-scope, og
        # compile svarede med fire delegeringsadvarsler. De to variabler
        # saettes lige ovenfor og har praecis de samme vaerdier.
        f"                        Remove({cfg.L_MATERIALS},\n"
        f"                            Filter({cfg.L_MATERIALS}, PlanKey = varVhpPlanKey));\n"
        f"                        Remove({cfg.L_ATTACHMENTS},\n"
        f"                            Filter({cfg.L_ATTACHMENTS}, PlanKey = varVhpPlanKey));\n"
        f"                        Remove({cfg.L_TASKS},\n"
        f"                            Filter({cfg.L_TASKS}, MaintenancePlanID.Id = varVhpPlanSpId));\n"
        f"                        Remove({cfg.L_ITEMS},\n"
        f"                            Filter({cfg.L_ITEMS}, MaintenancePlanNo.Id = varVhpPlanSpId));\n"
        "\n"
        "                        // --- 3. items ------------------------------\n"
        # BATCH, IKKE EEN AD GANGEN
        #
        # Her stod ForAll med to Patch indeni: een der oprettede raekken,
        # og een der skrev noeglen tilbage. Det er TO netvaerkskald pr.
        # item, sekventielt. Patch tager en TABEL af basisraekker og en
        # tabel af aendringer og goer det i EET kald, og svaret er en
        # tabel, der staar EEN-TIL-EEN med dem (Patch-dokumentationen,
        # "Modify or create a set of records in a data source").
        #
        # Den een-til-een-garanti er det, der goer koblingen mulig:
        # itemRecs[n] er raekken, srcItems[n] blev til. Uden den kunne
        # colVhpSavedItems ikke bygges, og operationerne ville ikke vide,
        # hvilket item de hoerer til.
        "                        With(\n"
        f"                            {{ srcItems: {_reindent(SAVEABLE_ITEMS, 28)} }},\n"
        "                            If(\n"
        "                                CountRows(srcItems) = 0,\n"
        "                                Clear(colVhpSavedItems),\n"
        "\n"
        "                                With(\n"
        "                                    {\n"
        "                                        itemRecs: Patch(\n"
        f"                                            {cfg.L_ITEMS},\n"
        f"                                            ForAll(srcItems, Defaults({cfg.L_ITEMS})),\n"
        f"                                            ForAll(srcItems As IT, {_reindent(item_fields, 44)})\n"
        "                                        )\n"
        "                                    },\n"
        "                                    ClearCollect(\n"
        "                                        colVhpSavedItems,\n"
        "                                        ForAll(\n"
        "                                            Sequence(CountRows(itemRecs)) As N,\n"
        "                                            {\n"
        "                                                LocalId: Index(srcItems, N.Value).ItemId,\n"
        "                                                SpId: Index(itemRecs, N.Value).ID,\n"
        f"                                                ItemKey: {_key('MI', 'Index(itemRecs, N.Value).ID', 'itemOff')}\n"
        "                                            }\n"
        "                                        )\n"
        "                                    );\n"
        "                                    Patch(\n"
        f"                                        {cfg.L_ITEMS},\n"
        "                                        itemRecs,\n"
        "                                        ForAll(colVhpSavedItems As S, { ItemID: S.ItemKey })\n"
        "                                    )\n"
        "                                )\n"
        "                            )\n"
        "                        );\n"
        "\n"
        "                        // --- 4. operationer ------------------------\n"
        # Samme batch som items. Filteret erstatter det If(IsBlank(m.SpId))
        # der foer stod inde i loekken: en operation paa et item, der ikke
        # blev gemt, skal ikke skrives - men den skal frasorteres FOER
        # kaldet, ikke undervejs i det.
        "                        With(\n"
        "                            {\n"
        "                                srcOps: Filter(\n"
        "                                    colVhpOperations As OP,\n"
        f"                                    !IsBlank({M_SPID})\n"
        "                                )\n"
        "                            },\n"
        "                            If(\n"
        "                                CountRows(srcOps) = 0,\n"
        "                                Clear(colVhpSavedOps),\n"
        "\n"
        "                                With(\n"
        "                                    {\n"
        "                                        opRecs: Patch(\n"
        f"                                            {cfg.L_TASKS},\n"
        f"                                            ForAll(srcOps, Defaults({cfg.L_TASKS})),\n"
        f"                                            ForAll(srcOps As OP, {_reindent(op_fields, 44)})\n"
        "                                        )\n"
        "                                    },\n"
        "                                    ClearCollect(\n"
        "                                        colVhpSavedOps,\n"
        "                                        ForAll(\n"
        "                                            Sequence(CountRows(opRecs)) As N,\n"
        "                                            {\n"
        "                                                LocalItemId: Index(srcOps, N.Value).ItemId,\n"
        "                                                OperationNo: Index(srcOps, N.Value).OperationNo,\n"
        "                                                SpId: Index(opRecs, N.Value).ID,\n"
        f"                                                TaskKey: {_key('TI', 'Index(opRecs, N.Value).ID', 'taskOff')}\n"
        "                                            }\n"
        "                                        )\n"
        "                                    );\n"
        "                                    Patch(\n"
        f"                                        {cfg.L_TASKS},\n"
        "                                        opRecs,\n"
        "                                        ForAll(colVhpSavedOps As S, { TaskItemID: S.TaskKey })\n"
        "                                    )\n"
        "                                )\n"
        "                            )\n"
        "                        );\n"
        "\n"
        "                        // --- 5. materialer -------------------------\n"
        "                        // Peger paa operationens TaskItemID, ikke paa\n"
        "                        // itemet. Et materiale hoerer til EEN\n"
        "                        // operation - det er den relation SAP har.\n"
        # Samme batch. De to opslag stod foer i et per-raekke With; de er
        # flyttet ned i felterne, fordi der ikke laengere er en loekke at
        # haenge dem paa. Begge er i hukommelsen.
        "                        With(\n"
        "                            { srcMats: Filter(colVhpMaterials As MT, !IsBlank(MT.MaterialNo)) },\n"
        "                            If(\n"
        "                                CountRows(srcMats) > 0,\n"
        "                                Patch(\n"
        f"                                    {cfg.L_MATERIALS},\n"
        f"                                    ForAll(srcMats, Defaults({cfg.L_MATERIALS})),\n"
        "                                    ForAll(\n"
        "                                        srcMats As MT,\n"
        "                                        {\n"
        f"                                            {cfg.C_MATERIAL_NO}: MT.MaterialNo,\n"
        "                                            PlanKey: planKey,\n"
        "                                            ItemKey: LookUp(\n"
        "                                                colVhpSavedItems, LocalId = MT.ItemId\n"
        "                                            ).ItemKey,\n"
        "                                            TaskItemID: LookUp(\n"
        "                                                colVhpSavedOps,\n"
        "                                                LocalItemId = MT.ItemId && "
        "OperationNo = MT.OperationNo\n"
        "                                            ).TaskKey,\n"
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
        "                        With(\n"
        "                            { srcAtt: Filter(colVhpAttachments As AT, !IsBlank(AT.FileName)) },\n"
        "                            If(\n"
        "                                CountRows(srcAtt) > 0,\n"
        "                                Patch(\n"
        f"                                    {cfg.L_ATTACHMENTS},\n"
        f"                                    ForAll(srcAtt, Defaults({cfg.L_ATTACHMENTS})),\n"
        "                                    ForAll(\n"
        "                                        srcAtt As AT,\n"
        "                                        {\n"
        f"                                            {cfg.C_FILE_NAME}: AT.FileName,\n"
        "                                            PlanKey: planKey,\n"
        "                                            ItemKey: LookUp(\n"
        "                                                colVhpSavedItems, LocalId = AT.ItemId\n"
        "                                            ).ItemKey,\n"
        "                                            OperationsKey: Coalesce(AT.OperationsKey, \";\"),\n"
        "                                            FileSize: AT.FileSize,\n"
        "                                            FileUrl: AT.FileUrl,\n"
        "                                            UploadStatus: {\n"
        "                                                Value: Coalesce(AT.Status, \"Pending\")\n"
        "                                            }\n"
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
        "                                \" item(s) and \" & Text(CountRows(colVhpOperations)) &\n"
        "                                \" operation(s).\"\n"
        "                        );\n"
        f"                        Notify(planKey & \" {verb}.\", NotificationType.Success)\n"
        "                    )\n"
        "                )\n"
        "            )\n"
        "        ),\n"
        "\n"
        "        Set(varVhpSaving, false);\n"
        "        Set(varVhpRuntimeInfo, \"Save failed: \" & FirstError.Message);\n"
        "        Notify(\"Save failed: \" & FirstError.Message, NotificationType.Error)\n"
        "    )\n"
        ")"
    )


def build_save_section():
    header = section_header("conVhpSaveHead", "Save to SharePoint",
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

    btnDraft = button("btnVhpSaveDraft", "\"Save draft\"", save_action(submit=False),
                      display_mode=DM)
    btnSubmit = button("btnVhpSubmit", "\"Submit\"", save_action(submit=True),
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
