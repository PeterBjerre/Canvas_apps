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

REKKEFOELGEN OG SIKKERHED (REVIEW.md D7, D8)
-------------------------------------------
SharePoint har ingen transaktioner. Gemmet er derfor GENOPTAGELIGT, efter
samme model som FL-appen (Functional Location App/build/fl_save.py):

  1. Noeglerne. De tre offsets hentes paa een gang (Concurrent).
  2. Konflikt. Er planen gemt af en anden, siden den blev aabnet
     (Modified), stoppes der - foer der er skrevet noget.
  3. Planhovedet - altid som kladde. Status saettes SIDST (trin 8).
  4. Items. Et item, der ER i SharePoint (SpId), OPDATERES. Kun nye
     oprettes. Et item beholder derfor sit ID og sin noegle (MI0112) ved
     hvert gem - og dokumentmappen, der er opkaldt efter noeglen, bliver
     ved med at passe (D7). Foer blev alle items slettet og oprettet
     forfra, med nyt ID og ny noegle hver gang.
  5. Operationer - samme model som items.
  6. Materialer og dokumentraekker skrives forfra, men de GAMLE raekker
     slettes foerst, naar de nye er skrevet.
  7. Oprydning - KUN naar alt ovenfor lykkedes: operationer og items, der
     ikke laengere er i appen, og de gamle materiale- og dokumentraekker.
     En fejl giver altsaa i vaerste fald en raekke for meget, aldrig et
     tab (foer: slet foerst, skriv bagefter).
  8. Status og landingssiden.

Hvert trin har sin egen IfError og skriver i colVhpSaveErrors. Et trin
koeres kun, naar ingen af de foregaaende fejlede, og brugeren faar EEN
samlet besked.

Save draft og Submit er den SAMME gemning. Submit saetter
varVhpSubmitting og vaelger Save draft-knappen (Select), saa formlen kun
staar eet sted i appen (B7). Foer stod den to gange - 415 linjer hver.

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
from build_helpers import button, confirm_modal, ICON_SAVE, ICON_SUBMIT
import sp_config as cfg
import messages as msg
import admin_log as alog
import permissions as perm
import request_index as ri

# AppUrl (appens play-URL fra tools/canvas_apps.json) skrives af
# tools/request_index.record - samme felter som de andre apps.
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
SAVEABLE_ITEMS = ('Filter(colVhpItems, '
                  '!IsBlank(Trim(ShortText)) || !IsBlank(FunctionalLocation))')
SAVEABLE_COUNT = f"CountRows({SAVEABLE_ITEMS})"

# Opslaget fra en operation til dens item. colVhpSavedItems har ALLE
# gemte items - de opdaterede og de nye - naar operationerne skrives.
M_LOOKUP = "LookUp(colVhpSavedItems, LocalId = OP.ItemId)"
M_KEY = M_LOOKUP + ".ItemKey"
M_SPID = M_LOOKUP + ".SpId"

# Appens Status (New/Change/Deleted) er AENDRINGSTYPEN pr. item, ikke
# arbejdsgangens status. De to maa ikke blandes sammen.
PLAN_STATUS_DRAFT = "Draft"
PLAN_STATUS_SUBMITTED = "In Progress"

# Kun naar ingen af de foregaaende trin fejlede.
OK = "CountRows(colVhpSaveErrors) = 0"

# Knappen, begge veje ind i gemningen gaar igennem (se save_buttons).
SAVE_BUTTON = "btnVhpSaveDraft"

# Indeksraekken, som den staar i SharePoint, naar gemningen starter
# (_step_keys). Den er grundraekken i trin 8 og afgoer rettigheden.
IDX_NOW = "varVhpIdxNow"
# Planhovedet, som det staar i SharePoint, foer trin 3 skriver det.
PLAN_NOW = "varVhpPlanNow"
# Gemmer en admin en andens anmodning? Saa bevares ejeren (tools/permissions.py).
AS_ADMIN = (f"(!IsBlank({IDX_NOW}) && "
            f"!({perm.is_owner(IDX_NOW + '.RequesterEmail', 'varVhpMe')}))")
# Den ansvarlige paa et item: brugeren selv - eller, for en admin i en
# andens anmodning, den, der staar paa itemet, og ellers anmodningens ejer.
RESP_OTHER = f"Lower(Coalesce(IT.OrstedResponsible, {IDX_NOW}.RequesterEmail))"
RESP = f"If({AS_ADMIN}, {RESP_OTHER}, varVhpMe)"


def _offset(list_name, key_field, prefix):
    """Offsettet mellem SharePoints ID og forretningsnoeglen.

    Udledt af den nyeste raekke i stedet for af AppSettings, som kun har
    vaerdier for DEV. 0 paa en tom liste - saa starter serien paa ID.
    Blank, naar nummeret ikke er et tal: saa stopper gemningen."""
    return (
        f"With(\n"
        f"        {{ r: First(Sort({list_name}, ID, SortOrder.Descending)) }},\n"
        f"        If(\n"
        f"            IsBlank(r.ID), 0,\n"
        f"            IsNumeric(Mid(r.{key_field}, {len(prefix) + 1})),\n"
        f"            r.ID - Value(Mid(r.{key_field}, {len(prefix) + 1})),\n"
        f"            Blank()\n"
        f"        )\n"
        f"    )"
    )


def _key(prefix, id_expr, off_var):
    return f"\"{prefix}\" & Text({id_expr} - {off_var}, \"0000\")"


def _step(where, body):
    """Eet trin: body, og fejler den, en raekke i colVhpSaveErrors.

    Begge grene slutter med en boolean (check_layout regel 32): Patch giver
    en record, Collect en tabel, og IfError vil have samme type."""
    return (f"IfError(\n{body};\n    true,\n"
            f"    Collect(colVhpSaveErrors, {{ Where: \"{where}\", Msg: FirstError.Message }});\n"
            f"    false\n)")


def _when_ok(body):
    return f"If(\n    {OK},\n{body}\n)"


# ---------------------------------------------------------------------------
# Felterne
# ---------------------------------------------------------------------------
def plan_fields():
    """Planhovedet - altid som kladde. Status skrives af _step_status."""
    return (
        "{\n"
        "            Title: varVhpPlan.PlanText,\n"
        # En admin, der retter en andens plan, flytter den ikke tilbage til
        # Draft - godkendelsesflowet laeser planens status.
        f"            Status: If({AS_ADMIN} && !IsBlank({PLAN_NOW}), {PLAN_NOW}.Status, "
        f"{{ Value: \"{PLAN_STATUS_DRAFT}\" }}),\n"
        "            PlantsInitial: { Value: varVhpPlan.Plant },\n"
        "            Cycle: varVhpPlan.Cycle,\n"
        "            Unit: { Value: varVhpPlan.Unit },\n"
        "            PlannedDate: Date(\n"
        "                varVhpPlan.FirstCallYear, varVhpPlan.FirstCallMonth, varVhpPlan.FirstCallDay\n"
        "            ),\n"
        "            StrategyKey: varVhpPlan.Strategy,\n"
        # Id baeres i den navngivne formel (B7) - foer et opslag mod
        # SharePoint-listen ved hvert gem.
        "            SortField: With(\n"
        "                { sf: LookUp(colVhpSortFieldOptions, Value = varVhpPlan.SortField) },\n"
        "                If(IsBlank(sf.Id), Blank(), { Id: sf.Id, Value: sf.Value })\n"
        "            )\n"
        "        }"
    )


def item_fields(key=None):
    """Et items felter. key er ItemID for et item, der opdateres - saa det
    ogsaa faar sin noegle, hvis et afbrudt gem manglede den. Nye items faar
    noeglen bagefter, naar ID'et kendes."""
    return (
        "{\n"
        + (f"                ItemID: {key},\n" if key else "") +
        "                Title: IT.ShortText,\n"
        # Vaerdien er SharePoints egen (New/Change/Deleted) - se build_load.
        "                Status: { Value: Coalesce(varVhpPlan.Status, \"New\") },\n"
        "                MaintenancePlanNo: { Id: varVhpPlanSpId, Value: varVhpPlanKey },\n"
        "                ItemDescription: Coalesce(IT.LongText, IT.ShortText),\n"
        "                FunctionalLocation: IT.FunctionalLocation,\n"
        "                ObjectList: IT.ObjectList,\n"
        # Priority er obligatorisk i listen, men appen har ikke feltet.
        "                Priority: { Value: \"Yellow (default)\" },\n"
        # Person-kolonnen er obligatorisk. Indsenderen staar som ansvarlig,
        # indtil appen faar en rigtig personvaelger. Teksten ved siden af er
        # den, der kan filtreres delegerbart.
        "                OrstedResponsible: {\n"
        "                    '@odata.type': \"#Microsoft.Azure.Connectors.SharePoint.SPListExpandedUser\",\n"
        f"                    Claims: \"i:0#.f|membership|\" & {RESP},\n"
        f"                    DisplayName: If({AS_ADMIN}, {RESP_OTHER}, User().FullName),\n"
        f"                    Email: If({AS_ADMIN}, {RESP_OTHER}, User().Email),\n"
        "                    Department: \"\",\n"
        "                    JobTitle: \"\",\n"
        "                    Picture: \"\"\n"
        "                },\n"
        f"                OrstedResponsibleEmail: {RESP},\n"
        "                InitialOrstedResponsible: IT.Initials,\n"
        # Opslag i de navngivne formler, ikke i listerne - de har Id.
        "                MaintenanceActivityType: With(\n"
        "                    { a: LookUp(colVhpActivityTypeOptions, Value = IT.ActivityType) },\n"
        "                    If(IsBlank(a.Id), Blank(), { Id: a.Id, Value: a.Value })\n"
        "                ),\n"
        "                MainWorkCenter: With(\n"
        "                    { w: LookUp(colVhpMainWorkCenters, Value = IT.MainWorkCenter) },\n"
        "                    If(IsBlank(w.Id), Blank(), { Id: w.Id, Value: w.Value })\n"
        "                )\n"
        "            }"
    )


def op_fields(key=None):
    """Som item_fields: key er TaskItemID for en operation, der opdateres."""
    return (
        "{\n"
        + (f"                TaskItemID: {key},\n" if key else "") +
        f"                Title: {M_KEY} & \" - \" & OP.OperationShortText,\n"
        "                OperationShortText: OP.OperationShortText,\n"
        "                OperationNo: Value(OP.OperationNo),\n"
        "                PackagesKey: OP.PackagesKey,\n"
        "                Work: OP.WorkHours,\n"
        "                Num: OP.Persons,\n"
        "                Duration: OP.DurationHours,\n"
        "                WorkCtr: OP.MainWorkCenter,\n"
        "                Ctrl: OP.ControlKey,\n"
        "                Vendor: OP.Vendor,\n"
        "                Price: OP.Cost,\n"
        "                Currency: OP.Currency,\n"
        "                CostElem: OP.CostElement,\n"
        "                MaterialGroup: OP.MaterialGroup,\n"
        "                LongText: OP.LongText,\n"
        "                PlantInitial: varVhpPlan.Plant,\n"
        f"                MaintenanceItemNo: {{ Id: {M_SPID}, Value: {M_KEY} }},\n"
        "                MaintenancePlanID: { Id: varVhpPlanSpId, Value: varVhpPlanKey }\n"
        "            }"
    )


# ---------------------------------------------------------------------------
# Trinene (C15: een funktion pr. trin i stedet for eet udtryk paa 415 linjer)
# ---------------------------------------------------------------------------
def _step_keys():
    """1. De tre offsets - uafhaengige, saa paa een gang (B7)."""
    return _step("Keys", (
        "    Concurrent(\n"
        f"        Set(varVhpPlanOff, {_offset(cfg.L_PLANS, 'PlanID', 'MP')}),\n"
        f"        Set(varVhpItemOff, {_offset(cfg.L_ITEMS, 'ItemID', 'MI')}),\n"
        f"        Set(varVhpTaskOff, {_offset(cfg.L_TASKS, 'TaskItemID', 'TI')}),\n"
        # Indeksraekken hentes samtidig - den slaas op en gang, ikke to.
        f"        Set({IDX_NOW}, If(!IsBlank(varVhpRequestGuid), "
        f"LookUp({cfg.L_INDEX}, RequestGuid = varVhpRequestGuid)))\n"
        "    );\n"
        # Rettigheden i selve handlingen - ikke kun i UI'et.
        "    If(\n"
        f"        !IsBlank({IDX_NOW}) &&\n"
        f"        !{perm.may_change(IDX_NOW + '.RequesterEmail', IDX_NOW + '.Status.Value', 'varVhpMe')},\n"
        "        Collect(colVhpSaveErrors, {\n"
        "            Where: \"Request\",\n"
        "            Msg: \"This request can no longer be changed.\"\n"
        "        })\n"
        "    );\n"
        # Hellere stoppe end at starte en ny noegleserie ved siden af den
        # eksisterende, uden at nogen opdager det.
        "    If(\n"
        "        IsBlank(varVhpPlanOff) || IsBlank(varVhpItemOff) || IsBlank(varVhpTaskOff),\n"
        "        Collect(colVhpSaveErrors, {\n"
        "            Where: \"Keys\",\n"
        "            Msg: \"Cannot derive the keys from the existing rows - contact SAP master data.\"\n"
        "        })\n"
        "    )"))


def _step_conflict():
    """2. Er planen gemt af en anden, siden den blev aabnet? (D8)

    varVhpPlanModified saettes ved indlaesning og efter hvert gem. En ny
    plan har ingen og springer tjekket over."""
    return _step("Plan", (
        "    If(\n"
        "        varVhpPlanSpId > 0 && !IsBlank(varVhpPlanModified),\n"
        "        With(\n"
        f"            {{ now: LookUp({cfg.L_PLANS}, ID = varVhpPlanSpId) }},\n"
        "            If(\n"
        "                !IsBlank(now.ID) && now.Modified <> varVhpPlanModified,\n"
        "                Collect(colVhpSaveErrors, {\n"
        "                    Where: \"Plan\",\n"
        "                    Msg: \"Someone else saved this plan after you opened it. \" &\n"
        "                        \"Open it again from the landing page, then make your changes.\"\n"
        "                })\n"
        "            )\n"
        "        )\n"
        "    )"))


def _step_plan():
    """3. Planhovedet og dets noegle."""
    return _step("Plan", (
        f"    Set({PLAN_NOW}, If(varVhpPlanSpId > 0, LookUp({cfg.L_PLANS}, ID = varVhpPlanSpId)));\n"
        "    Set(\n"
        "        varVhpPlanRec,\n"
        "        Patch(\n"
        f"            {cfg.L_PLANS},\n"
        f"            If(varVhpPlanSpId > 0, {PLAN_NOW}, Defaults({cfg.L_PLANS})),\n"
        f"            {plan_fields()}\n"
        "        )\n"
        "    );\n"
        "    If(\n"
        "        IsBlank(varVhpPlanRec.PlanID),\n"
        "        Set(\n"
        "            varVhpPlanRec,\n"
        f"            Patch({cfg.L_PLANS}, varVhpPlanRec, "
        f"{{ PlanID: {_key('MP', 'varVhpPlanRec.ID', 'varVhpPlanOff')} }})\n"
        "        )\n"
        "    );\n"
        # Globale variabler, ikke With-felter: filtrene nedenfor sammenligner
        # med dem, og SharePoint delegerer kun mod noget, der er ens for alle
        # raekker.
        "    Set(varVhpPlanSpId, varVhpPlanRec.ID);\n"
        "    Set(varVhpPlanKey, varVhpPlanRec.PlanID);\n"
        "    Set(varVhpRequestGuid, Coalesce(varVhpRequestGuid, Text(GUID())))"))


def _step_items():
    """4. Items: opdatér de eksisterende, opret de nye (D7)."""
    ex = f"Filter({cfg.L_ITEMS}, MaintenancePlanNo.Id = varVhpPlanSpId)"
    return _step("Items", (
        # En admin i en andens plan: items, som de staar nu, til loggen.
        # Kun dér - andre betaler ingen ekstra hentning.
        "    If(\n"
        f"        {AS_ADMIN},\n"
        "        ClearCollect(\n"
        "            colVhpAdmOld,\n"
        f"            ForAll({ex} As I, {{ ID: I.ID, ItemID: I.ItemID, Title: I.Title, "
        "ItemDescription: I.ItemDescription, FunctionalLocation: I.FunctionalLocation, "
        "ObjectList: I.ObjectList })\n"
        "        ),\n"
        "        Clear(colVhpAdmOld)\n"
        "    );\n"
        # Hvad der er i SharePoint nu - ID og noegle.
        "    ClearCollect(\n"
        "        colVhpSpItems,\n"
        f"        ForAll({ex} As I, {{ ID: I.ID, ItemID: I.ItemID }})\n"
        "    );\n"
        # De eksisterende foerst i oversaettelsen: operationerne,
        # materialerne og dokumenterne slaar op i den.
        "    ClearCollect(\n"
        "        colVhpSavedItems,\n"
        "        ForAll(\n"
        f"            Filter({SAVEABLE_ITEMS}, SpId in colVhpSpItems.ID) As IT,\n"
        "            {\n"
        "                LocalId: IT.ItemId,\n"
        "                SpId: IT.SpId,\n"
        "                ItemKey: Coalesce(\n"
        "                    LookUp(colVhpSpItems, ID = IT.SpId).ItemID,\n"
        f"                    {_key('MI', 'IT.SpId', 'varVhpItemOff')}\n"
        "                )\n"
        "            }\n"
        "        )\n"
        "    );\n"
        # OPDATERING. Base-raekkerne er RIGTIGE raekker fra listen, hentet
        # een gang med et delegerbart filter (som fl_save.py) - ikke
        # { ID: ... }, som FL-appens compile afviste (issue #32).
        "    With(\n"
        "        {\n"
        f"            ex: {ex},\n"
        f"            old: Filter({SAVEABLE_ITEMS}, SpId in colVhpSpItems.ID)\n"
        "        },\n"
        "        If(\n"
        "            CountRows(old) > 0,\n"
        "            Patch(\n"
        f"                {cfg.L_ITEMS},\n"
        "                ForAll(old As IT, LookUp(ex, ID = IT.SpId)),\n"
        f"                ForAll(old As IT, {item_fields('LookUp(colVhpSavedItems, LocalId = IT.ItemId).ItemKey')})\n"
        "            )\n"
        "        )\n"
        "    );\n"
        # NYE: EET kald. Svaret staar een-til-een med kilden (Patch-
        # dokumentationen, "Modify or create a set of records").
        "    With(\n"
        f"        {{ src: Filter({SAVEABLE_ITEMS}, !(SpId in colVhpSpItems.ID)) }},\n"
        "        If(\n"
        "            CountRows(src) > 0,\n"
        "            With(\n"
        "                {\n"
        "                    recs: Patch(\n"
        f"                        {cfg.L_ITEMS},\n"
        f"                        ForAll(src, Defaults({cfg.L_ITEMS})),\n"
        f"                        ForAll(src As IT, {item_fields()})\n"
        "                    )\n"
        "                },\n"
        "                Collect(\n"
        "                    colVhpSavedItems,\n"
        "                    ForAll(\n"
        "                        Sequence(CountRows(recs)) As N,\n"
        "                        {\n"
        "                            LocalId: Index(src, N.Value).ItemId,\n"
        "                            SpId: Index(recs, N.Value).ID,\n"
        f"                            ItemKey: {_key('MI', 'Index(recs, N.Value).ID', 'varVhpItemOff')}\n"
        "                        }\n"
        "                    )\n"
        "                );\n"
        "                Patch(\n"
        f"                    {cfg.L_ITEMS},\n"
        "                    recs,\n"
        f"                    ForAll(recs As R, {{ ItemID: {_key('MI', 'R.ID', 'varVhpItemOff')} }})\n"
        "                )\n"
        "            )\n"
        "        )\n"
        "    );\n"
        # Appen husker nu, hvilken raekke hvert item er - naeste gem
        # opdaterer i stedet for at oprette. ItemId findes ikke i
        # colVhpSavedItems, saa det er itemets eget.
        "    UpdateIf(\n"
        "        colVhpItems,\n"
        "        ItemId in colVhpSavedItems.LocalId,\n"
        "        { SpId: LookUp(colVhpSavedItems, LocalId = ItemId).SpId }\n"
        "    )"))


def _step_ops():
    """5. Operationer - samme model som items."""
    ex = f"Filter({cfg.L_TASKS}, MaintenancePlanID.Id = varVhpPlanSpId)"
    live = f"Filter(colVhpOperations As OP, !IsBlank({M_SPID}))"
    return _step("Operations", (
        "    ClearCollect(\n"
        "        colVhpSpOps,\n"
        f"        ForAll({ex} As T, {{ ID: T.ID, TaskItemID: T.TaskItemID }})\n"
        "    );\n"
        "    ClearCollect(\n"
        "        colVhpSavedOps,\n"
        "        ForAll(\n"
        f"            Filter({live}, SpId in colVhpSpOps.ID) As O,\n"
        "            {\n"
        "                LocalItemId: O.ItemId,\n"
        "                OpNo: O.OperationNo,\n"
        "                SpId: O.SpId,\n"
        "                TaskKey: Coalesce(\n"
        "                    LookUp(colVhpSpOps, ID = O.SpId).TaskItemID,\n"
        f"                    {_key('TI', 'O.SpId', 'varVhpTaskOff')}\n"
        "                )\n"
        "            }\n"
        "        )\n"
        "    );\n"
        "    With(\n"
        "        {\n"
        f"            ex: {ex},\n"
        f"            old: Filter({live}, SpId in colVhpSpOps.ID)\n"
        "        },\n"
        "        If(\n"
        "            CountRows(old) > 0,\n"
        "            Patch(\n"
        f"                {cfg.L_TASKS},\n"
        "                ForAll(old As OP, LookUp(ex, ID = OP.SpId)),\n"
        f"                ForAll(old As OP, {op_fields('LookUp(colVhpSavedOps, SpId = OP.SpId).TaskKey')})\n"
        "            )\n"
        "        )\n"
        "    );\n"
        "    With(\n"
        f"        {{ src: Filter({live}, !(SpId in colVhpSpOps.ID)) }},\n"
        "        If(\n"
        "            CountRows(src) > 0,\n"
        "            With(\n"
        "                {\n"
        "                    recs: Patch(\n"
        f"                        {cfg.L_TASKS},\n"
        f"                        ForAll(src, Defaults({cfg.L_TASKS})),\n"
        f"                        ForAll(src As OP, {op_fields()})\n"
        "                    )\n"
        "                },\n"
        "                Collect(\n"
        "                    colVhpSavedOps,\n"
        "                    ForAll(\n"
        "                        Sequence(CountRows(recs)) As N,\n"
        "                        {\n"
        "                            LocalItemId: Index(src, N.Value).ItemId,\n"
        "                            OpNo: Index(src, N.Value).OperationNo,\n"
        "                            SpId: Index(recs, N.Value).ID,\n"
        f"                            TaskKey: {_key('TI', 'Index(recs, N.Value).ID', 'varVhpTaskOff')}\n"
        "                        }\n"
        "                    )\n"
        "                );\n"
        "                Patch(\n"
        f"                    {cfg.L_TASKS},\n"
        "                    recs,\n"
        f"                    ForAll(recs As R, {{ TaskItemID: {_key('TI', 'R.ID', 'varVhpTaskOff')} }})\n"
        "                )\n"
        "            )\n"
        "        )\n"
        "    );\n"
        # OpNo, ikke OperationNo, i oversaettelsen: saa binder ItemId og
        # OperationNo her til operationens egne felter.
        "    UpdateIf(\n"
        "        colVhpOperations,\n"
        "        true,\n"
        "        {\n"
        "            SpId: Coalesce(\n"
        "                LookUp(colVhpSavedOps, LocalItemId = ItemId && OpNo = OperationNo).SpId,\n"
        "                SpId\n"
        "            )\n"
        "        }\n"
        "    )"))


def _step_materials():
    """6a. Materialer. De gamle raekkers ID huskes, og de slettes foerst i
    oprydningen - efter de nye er skrevet."""
    return _step("Materials", (
        "    ClearCollect(\n"
        "        colVhpOldMats,\n"
        f"        ForAll(Filter({cfg.L_MATERIALS}, PlanKey = varVhpPlanKey) As M, {{ ID: M.ID }})\n"
        "    );\n"
        # Peger paa operationens TaskItemID, ikke paa itemet. Et materiale
        # hoerer til EEN operation - det er den relation SAP har.
        "    With(\n"
        "        { srcMats: Filter(colVhpMaterials As MT, !IsBlank(MT.MaterialNo)) },\n"
        "        If(\n"
        "            CountRows(srcMats) > 0,\n"
        "            Patch(\n"
        f"                {cfg.L_MATERIALS},\n"
        f"                ForAll(srcMats, Defaults({cfg.L_MATERIALS})),\n"
        "                ForAll(\n"
        "                    srcMats As MT,\n"
        "                    {\n"
        f"                        {cfg.C_MATERIAL_NO}: MT.MaterialNo,\n"
        "                        PlanKey: varVhpPlanKey,\n"
        "                        ItemKey: LookUp(colVhpSavedItems, LocalId = MT.ItemId).ItemKey,\n"
        "                        TaskItemID: LookUp(\n"
        "                            colVhpSavedOps,\n"
        "                            LocalItemId = MT.ItemId && OpNo = MT.OperationNo\n"
        "                        ).TaskKey,\n"
        "                        OperationNo: MT.OperationNo,\n"
        "                        Quantity: MT.Quantity,\n"
        "                        MaterialText: MT.Description,\n"
        "                        Unit: MT.Unit,\n"
        "                        LineId: MT.LineId\n"
        "                    }\n"
        "                )\n"
        "            )\n"
        "        )\n"
        "    )"))


def _step_attachments():
    """6b. Dokumentraekker. OperationsKey er ';0010;0020;'; tom (';')
    betyder hele itemet. UploadStatus skrives som Pending - flowet roerer
    aldrig listen (docs/18-materialer-og-attachments.md).

    Mappen i biblioteket er opkaldt efter ItemKey, og den er nu STABIL:
    et item beholder sin noegle ved hvert gem (trin 4)."""
    return _step("Documents", (
        "    ClearCollect(\n"
        "        colVhpOldAtts,\n"
        f"        ForAll(Filter({cfg.L_ATTACHMENTS}, PlanKey = varVhpPlanKey) As A, {{ ID: A.ID }})\n"
        "    );\n"
        "    With(\n"
        "        { srcAtt: Filter(colVhpAttachments As AT, !IsBlank(AT.FileName)) },\n"
        "        If(\n"
        "            CountRows(srcAtt) > 0,\n"
        "            Patch(\n"
        f"                {cfg.L_ATTACHMENTS},\n"
        f"                ForAll(srcAtt, Defaults({cfg.L_ATTACHMENTS})),\n"
        "                ForAll(\n"
        "                    srcAtt As AT,\n"
        "                    {\n"
        f"                        {cfg.C_FILE_NAME}: AT.FileName,\n"
        "                        PlanKey: varVhpPlanKey,\n"
        "                        ItemKey: LookUp(colVhpSavedItems, LocalId = AT.ItemId).ItemKey,\n"
        "                        OperationsKey: Coalesce(AT.OperationsKey, \";\"),\n"
        "                        FileSize: AT.FileSize,\n"
        "                        FileUrl: AT.FileUrl,\n"
        "                        UploadStatus: { Value: Coalesce(AT.Status, \"Pending\") }\n"
        "                    }\n"
        "                )\n"
        "            )\n"
        "        )\n"
        "    )"))


def _step_cleanup():
    """7. Oprydning - foerst naar alt er skrevet (D8).

    Remove(kilde, Filter(...)) og ikke RemoveIf: RemoveIf delegeres ikke
    paa en tekstkolonne eller et opslags underfelt. Filteret mod listen
    er delegerbart (lighed mod en global variabel); 'in' tages bagefter i
    hukommelsen paa planens egne raekker."""
    def rm(lst, flt, keep):
        return (f"    With(\n        {{ ex: Filter({lst}, {flt}) }},\n"
                f"        Remove({lst}, Filter(ex, {keep}))\n    )")
    return _step("Clean-up", ";\n".join([
        rm(cfg.L_MATERIALS, "PlanKey = varVhpPlanKey", "ID in colVhpOldMats.ID"),
        rm(cfg.L_ATTACHMENTS, "PlanKey = varVhpPlanKey", "ID in colVhpOldAtts.ID"),
        # Operationer foer items: en operation peger paa sit item.
        rm(cfg.L_TASKS, "MaintenancePlanID.Id = varVhpPlanSpId",
           "!(ID in colVhpSavedOps.SpId)"),
        rm(cfg.L_ITEMS, "MaintenancePlanNo.Id = varVhpPlanSpId",
           "!(ID in colVhpSavedItems.SpId)"),
    ]))


def _index_patch(status):
    rec = ri.record(
        DOMAIN, "vhplan", status,
        request_no="varVhpPlanKey", guid="varVhpRequestGuid", me="varVhpMe",
        owner=f"Coalesce({IDX_NOW}.RequesterEmail, varVhpMe)",
        owner_name=f"Coalesce({IDX_NOW}.RequesterName, User().FullName)",
        current=IDX_NOW,
        short_text="varVhpPlan.PlanText", plant="varVhpPlan.Plant",
        item_count=SAVEABLE_COUNT, source_id="varVhpPlanSpId", indent=8)
    return (f"Patch(\n        {cfg.L_INDEX},\n        Coalesce(\n"
            f"            {IDX_NOW},\n"
            f"            Defaults({cfg.L_INDEX})\n        ),\n        {rec}\n    )")


def _step_status():
    """8. Status SIDST, og landingssiden. Fejler noget foer, staar planen
    stadig som kladde og kan gemmes igen."""
    return _step("Status", (
        "    If(\n"
        "        varVhpSubmitting,\n"
        "        Set(\n"
        "            varVhpPlanRec,\n"
        f"            Patch({cfg.L_PLANS}, varVhpPlanRec, "
        f"{{ Status: {{ Value: \"{PLAN_STATUS_SUBMITTED}\" }}, "
        "ApprovalStage: { Value: \"System\" }, SubmittedOn: Now(), StageRunId: \"\" })\n"
        "        );\n"
        # Progressbaren viser nu godkendelsen (build_status.VhpSubmitted).
        "        Set(varVhpFlow, { Status: varVhpPlanRec.Status.Value, "
        "Stage: varVhpPlanRec.ApprovalStage.Value, ReturnComment: \"\" })\n"
        "    );\n"
        # Hubben laeser KUN indeksraekken.
        "    If(\n"
        "        varVhpSubmitting,\n"
        f"    {_index_patch(ri.SUBMITTED)},\n"
        f"    {_index_patch(ri.DRAFT)}\n"
        "    );\n"
        # Det, der nu staar i SharePoint - konflikttjekket (trin 2) maaler
        # mod det ved naeste gem.
        "    Set(varVhpPlanModified, varVhpPlanRec.Modified)"))


def _admin_log():
    """Admin i en andens plan: planhovedet foer/efter (varVhpPlanNow mod
    varVhpPlanRec - begge som de staar i SharePoint), items foer (colVhpAdmOld)
    mod det gemte, og Submit (tools/admin_log.py)."""
    P, N = PLAN_NOW, "varVhpPlanRec"
    header = alog.diff([
        ("Plan text", f"{P}.Title", f"{N}.Title"),
        ("Plant", f"{P}.PlantsInitial.Value", f"{N}.PlantsInitial.Value"),
        ("Cycle", f"{P}.Cycle", f"{N}.Cycle"),
        ("Unit", f"{P}.Unit.Value", f"{N}.Unit.Value"),
        ("Planned date", f"{P}.PlannedDate", f"{N}.PlannedDate"),
        ("Strategy", f"{P}.StrategyKey", f"{N}.StrategyKey"),
        ("Sort field", f"{P}.SortField.Value", f"{N}.SortField.Value"),
    ])
    item = alog.diff([
        ("Short text", "O.Title", "n.ShortText"),
        ("Long text", "O.ItemDescription", "Coalesce(n.LongText, n.ShortText)"),
        ("Functional location", "O.FunctionalLocation", "n.FunctionalLocation"),
        ("Object list", "O.ObjectList", "n.ObjectList"),
    ], 'O.ItemID & " "')
    items = (
        "Concat(\n    Filter(\n        ForAll(colVhpAdmOld As O,\n"
        f"            With({{ n: LookUp({SAVEABLE_ITEMS}, SpId = O.ID) }},\n"
        '                If(IsBlank(n), O.ItemID & ": removed",\n'
        + "\n".join(" " * 16 + l for l in item.split("\n")) + ")\n"
        "            )\n        ),\n        !IsBlank(Value)\n    ),\n    Value,\n    \"; \"\n)")
    added = (f'With({{ k: CountRows(Filter({SAVEABLE_ITEMS}, !(SpId in colVhpAdmOld.ID))) }}, '
             'If(k > 0, k & " item(s) added", ""))')
    status = f'If(varVhpSubmitting, {alog.submitted(IDX_NOW + ".Status.Value")}, "")'
    comment = alog.join(header, items, added, status)
    return (f"If(\n    {AS_ADMIN},\n    With(\n        {{ c: {comment} }},\n"
            "        If(\n            !IsBlank(c),\n"
            + alog.write("varVhpRequestGuid", "varVhpPlanKey", alog.EDIT, "c", 12)
            + "\n        )\n    )\n)")


def save_action():
    """Hele gemningen. Om det er Save draft eller Submit, afgoer
    varVhpSubmitting - den nulstilles, naar gemningen er faerdig."""
    detail = 'First(colVhpSaveErrors).Where & ": " & First(colVhpSaveErrors).Msg'
    report = (
        "If(\n"
        f"    {OK},\n"
        # Save-trinnet er groent, saa laenge planen er den samme - se
        # VhpStateJson i sp_config.py.
        "    Set(varVhpSavedJson, VhpStateJson);\n"
        # Tasklist and Operations' Save (issue #103): sektionen klappes
        # foerst sammen her, naar gemningen er lykkedes.
        "    If(\n"
        "        varVhpOpsSavePending > 0 && !(varVhpOpsSavePending in colVhpOpsDone.ItemId),\n"
        "        Collect(colVhpOpsDone, { ItemId: varVhpOpsSavePending })\n"
        "    );\n"
        + _admin_log() + ";\n"
        f"    If(varVhpSubmitting, {msg.submitted('varVhpPlanKey')}, {msg.saved('varVhpPlanKey')}),\n"
        f"    If(varVhpSubmitting, {msg.failed('Submit', detail)}, {msg.failed('Save', detail)})\n"
        ")")
    body = ";\n".join([
        "Set(varVhpSaving, true)",
        "Clear(colVhpSaveErrors)",
        _step_keys(),
        _when_ok(_step_conflict()),
        _when_ok(_step_plan()),
        _when_ok(_step_items()),
        _when_ok(_step_ops()),
        _when_ok(_step_materials()),
        _when_ok(_step_attachments()),
        _when_ok(_step_cleanup()),
        _when_ok(_step_status()),
        report,
        # EET sted spinneren slukkes og tilstanden nulstilles.
        "Set(varVhpSubmitting, false)",
        "Set(varVhpOpsSavePending, 0)",
        "Set(varVhpSaving, false)",
    ])
    return (
        "If(\n"
        f"    !varVhpPlanCommitted || {SAVEABLE_COUNT} = 0,\n"
        "    Set(varVhpSubmitting, false);\n"
        "    Set(varVhpOpsSavePending, 0);\n"
        "    Notify(\"Create the plan and at least one item first.\", NotificationType.Warning),\n"
        "\n"
        + body + "\n)"
    )


# Save draft kan bruges, saa snart der er noget at gemme. Samme maal som
# selve gemningen: et tomt item taeller ikke med, saa knappen bliver ikke
# aktiv af det item, appen selv aabnede med.
#
# Submit gaar ogsaa gennem den her knap (Select). Submit kan kun trykkes,
# naar planen kan indsendes - og saa er den her knap altid aktiv.
DRAFT_DM = ("If(\n"
            f"    varVhpViewOnly || varVhpSaving || !varVhpPlanCommitted || {SAVEABLE_COUNT} = 0,\n"
            "    DisplayMode.Disabled,\n"
            "    DisplayMode.Edit\n"
            ")")


def save_buttons(can_submit):
    """Save draft og Submit - de to knapper, der skriver planen i
    SharePoint - og Submits bekraeftelse.

    can_submit er betingelsen for, at planen kan indsendes. DisplayMode er
    bundet til den, saa en graa Submit ikke kan klikkes.

    Submit aabner en bekraeftelse; foerst "Submit" dér indsender: den
    saetter varVhpSubmitting og vaelger Save draft-knappen. Select koerer
    knappens OnSelect, efter bekraeftelsens egen formel er faerdig.

    Returnerer (Save draft, Submit, [sloer, popup])."""
    btnDraft = button(SAVE_BUTTON, "\"Save draft\"", save_action(),
                      display_mode=DRAFT_DM, icon=ICON_SAVE)
    btnSubmit = button("btnVhpSubmit", "\"Submit\"", "Set(varVhpConfirmSubmit, true)",
                       primary=True, icon=ICON_SUBMIT,
                       display_mode=f"If(!varVhpViewOnly && {can_submit}, DisplayMode.Edit, DisplayMode.Disabled)")
    confirm = confirm_modal(
        "Vhp", "varVhpConfirmSubmit", "Submit plan?",
        "\"The plan \" & varVhpPlan.Plant & \" \" & varVhpPlan.PlanText & "
        "\" is saved and marked as ready for processing on the landing page.\"",
        "Submit", f"Set(varVhpSubmitting, true);\nSelect({SAVE_BUTTON})",
        "btnVhpSubmitConfirm")
    return btnDraft, btnSubmit, confirm
