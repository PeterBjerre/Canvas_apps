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
Det er selvkorrigerende og miljoeuafhaengigt. Kun raekker, hvis noegle
starter med praefikset, taeller med (R2-037): en raekke, et afbrudt gem
efterlod uden noegle, stopper ikke laengere serien for alle. Kan det ikke
udledes (ingen raekke med noegle, eller et nummer der ikke er et tal),
bruges 0 for en liste uden noegler og ellers stoppes der - en forkert
noegleserie er vaerre end en fejlbesked.

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
  6. Materialer skrives forfra, men de GAMLE raekker slettes foerst, naar
     de nye er skrevet. De aeldre dokumentraekker (MD_TasklistAttachment)
     roeres ikke laengere (R2-071): dokumenter er vedhaeftninger paa
     operationens raekke (issue #300/#323), og de gamle raekker er et
     mellemlager, der kun laeses (build_load), til en migrering er besluttet.
  7. Oprydning - KUN naar alt ovenfor lykkedes: operationer og items, der
     ikke laengere er i appen, og de gamle materialeraekker.
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
  MaintenancePlans.CallHorizon  Kaldshorisonten (kolonnen CallHorizon0) og
  og SchedulingPeriod           SchedulingPeriod skrives, regnet af
                                CallHorizonMatrix som i den gamle app
                                (sp_config: VhpCallHorizon). Her stod, at den
                                gamle app ikke skrev CallHorizon - det gjorde
                                den, via det skjulte kort med
                                'CallHorizon (CallHorizon0)'. Netop den form
                                skal bruges: "CallHorizon" alene er det
                                interne navn paa valgkolonnen
                                CallHorizonChoiceOLD, og det var derfor,
                                compile svarede "expected type 'Record'".
  MultiCounterStrategy          bruges ikke af appen.

De staar tomme med vilje. Bliver de noedvendige for SAP-oprettelsen, skal
kilden afklares foerst - ikke gaettes her.
"""
import display_text as dt
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_helpers import button, act_fx, act_button, ICON_SAVE, ICON_SUBMIT
import sp_config as cfg
import messages as msg
import admin_log as alog
import permissions as perm
import request_index as ri
import submission_notes as sn

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

# Items, der ville blive gemt uden et af de paakraevede felter. Title
# (kort tekst), FunctionalLocation, MaintenanceActivityType og
# MainWorkCenter er paakraevede i MaintenanceItems (sharepoint/inspect/out/
# schema.json), saa SharePoint afviser hele Items-Patch'et, hvis bare eet
# item mangler et af dem (R2-008). Et item er "saveable" med kort tekst
# ELLER funktionsplads, saa begge tjekkes. Aktivitetstype og arbejdscenter
# tjekkes paa opslaget, som item_fields skriver - et ukendt navn giver
# Blank() dér.
NO_REQ = (f"Filter({SAVEABLE_ITEMS} As IT, "
          "IsBlank(Trim(IT.ShortText)) || IsBlank(IT.FunctionalLocation) || "
          "IsBlank(LookUp(colVhpActivityTypeOptions, Value = IT.ActivityType).Id) || "
          "IsBlank(LookUp(colVhpMainWorkCenters, Value = Trim(IT.MainWorkCenter)).Id))")

# Opslaget fra en operation til dens item. colVhpSavedItems har ALLE
# gemte items - de opdaterede og de nye - naar operationerne skrives.
M_LOOKUP = "LookUp(colVhpSavedItems, LocalId = OP.ItemId)"
M_KEY = M_LOOKUP + ".ItemKey"
M_SPID = M_LOOKUP + ".SpId"

# Appens Status (New/Change/Deleted) er AENDRINGSTYPEN pr. item, ikke
# arbejdsgangens status. De to maa ikke blandes sammen.
PLAN_STATUS_DRAFT = "Draft"
PLAN_STATUS_SUBMITTED = "In Progress"
# Sat af godkendelsesflowene ved Send retur (docs/32 §5).
PLAN_STATUS_RETURNED = "Returned"
# Indeksets status for en returneret plan (build_load.AWAITING).
IDX_STATUS_AWAITING = "AfventerInfo"

# PRIORITETEN regnes, den vaelges ikke - samme regel som den gamle app
# (solution/BIOSAP/.../orsted_biosapmaintenanceplans_ba408.src, Priority-
# kortet i MaintenanceItemForm):
#
#   Roed    lovpligtigt (aktivitetstype 110 eller 115) eller sikkerheds-
#           kritisk udstyr (SCEqFL/SCEqOL udfyldt paa itemet)
#   Blaa    staaende ordre (120)
#   Gul     ellers
#
# FL-flowet svarer ikke laengere med "Safety Critical Equip.", saa et NYT
# item kan ikke blive roedt af den grund. Et item, der allerede STAAR med
# SCEq i listen, bliver ved med at vaere roedt (colVhpSpItems.Sceq) - foer
# blev alle items skrevet som gule ved hvert gem.
def priority_expr(act, sceq):
    return (
        "If(\n"
        f"                    {sceq} || StartsWith({act}, \"110\") || StartsWith({act}, \"115\"),\n"
        "                    \"Red (Statutory and SCEq)\",\n"
        f"                    StartsWith({act}, \"120\"), \"Blue (standing order)\",\n"
        "                    \"Yellow (default)\"\n"
        "                )"
    )


PRIORITY = priority_expr("IT.ActivityType",
                         "Coalesce(LookUp(colVhpSpItems, ID = IT.SpId).Sceq, false)")

# Kun naar ingen af de foregaaende trin fejlede.
OK = "CountRows(colVhpSaveErrors) = 0"

# Knappen, begge veje ind i gemningen gaar igennem (se save_buttons).
SAVE_BUTTON = "btnVhpSaveDraft"
# Knappernes ventetilstand (issue #420): "save"/"submit" mens der gemmes,
# "<noegle>:ok"/":failed" bagefter - build_helpers.act_fx.
ACT = "varVhpAct"

# Indeksraekken, som den staar i SharePoint, naar gemningen starter
# (_step_keys). Den er grundraekken i trin 8 og afgoer rettigheden.
IDX_NOW = "varVhpIdxNow"
# Status, rettigheden regnes paa - SAMME sandhed som indlaesningen
# (build_load.IDX_STATUS): staar planen selv i Returned, er det
# AfventerInfo, uanset hvad indeksraekken siger. Ellers kunne en returneret
# plan aabnes i Edit, men ikke gemmes, naar indekset haltede (R2-036).
# varVhpFlow saettes ved indlaesning og i _step_status.
IDX_STATUS_NOW = (f'If(varVhpFlow.Status = "{PLAN_STATUS_RETURNED}", '
                  f'"{IDX_STATUS_AWAITING}", {IDX_NOW}.Status.Value)')
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

    Udledt af den nyeste raekke MED NOEGLE i stedet for af AppSettings, som
    kun har vaerdier for DEV. 0, naar ingen raekke har en noegle - saa
    starter serien paa ID. Blank, naar nummeret ikke er et tal: saa stopper
    gemningen.

    D17/R2-037: nye raekker faar noeglen i et SEPARAT Patch (trin 3-5).
    Afbrydes gemningen imellem, staar den nyeste raekke uden noegle. Foer
    gav det Blank her, og saa kunne INGEN gemme nogen plan, foer nogen
    rettede raekken i haanden. Filteret springer den slags raekker over;
    StartsWith er delegerbar mod en SharePoint-tekstkolonne, saa det koerer
    i SharePoint. IsNumeric er stadig sidste vaern."""
    return (
        f"With(\n"
        f"        {{ r: First(Sort(Filter({list_name}, StartsWith({key_field}, \"{prefix}\")), "
        f"ID, SortOrder.Descending)) }},\n"
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
        # Draft - godkendelsesflowet laeser planens status. Det goer ejeren
        # heller ikke med en plan, der er sendt retur: den bliver Returned
        # (med kommentaren i banneret), til den indsendes igen.
        f"            Status: If(!IsBlank({PLAN_NOW}) && ({AS_ADMIN} || "
        f"{PLAN_NOW}.Status.Value = \"{PLAN_STATUS_RETURNED}\"), {PLAN_NOW}.Status, "
        f"{{ Value: \"{PLAN_STATUS_DRAFT}\" }}),\n"
        "            PlantsInitial: { Value: varVhpPlan.Plant },\n"
        # En strategiplan (IP42) har ingen cyklus og enhed: Plan Header
        # saetter Cycle 0 og Unit "" (build_plan_header). Cycle 0 er et
        # gyldigt tal; en tom Unit skrives som Blank() og ikke som valget
        # { Value: "" }, som ikke findes i Choice-kolonnen (R2-070). Om
        # SharePoint tager en tom Unit paa den paakraevede kolonne, er ikke
        # efterproevet i Studio - SAP-ordren kraever kun unit paa en
        # enkeltcyklusplan (schema/vhplan-sap-order.schema.json).
        "            Cycle: varVhpPlan.Cycle,\n"
        "            Unit: If(IsBlank(varVhpPlan.Unit), Blank(), { Value: varVhpPlan.Unit }),\n"
        "            PlannedDate: Date(\n"
        "                varVhpPlan.FirstCallYear, varVhpPlan.FirstCallMonth, varVhpPlan.FirstCallDay\n"
        "            ),\n"
        "            StrategyKey: varVhpPlan.Strategy,\n"
        # Regnes af CallHorizonMatrix (sp_config: VhpCallHorizon), som i
        # den gamle app. Visningsnavnet CallHorizon er ogsaa det interne navn
        # paa valgkolonnen CallHorizonChoiceOLD, saa Power Fx skelner med
        # 'Visningsnavn (internt navn)' - den form brugte den gamle app.
        "            'CallHorizon (CallHorizon0)': VhpCallHorizon,\n"
        "            SchedulingPeriod: VhpSchedulingPeriod,\n"
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
        # Itemets identitet paa tvaers af gem (docs/32 §6, R2-034) -
        # godkendelsesflowene logger den i MD_ApprovalLog.ItemGuid.
        "                ItemGuid: IT.ItemGuid,\n"
        # Vaerdien er SharePoints egen (New/Change/Deleted) - se build_load.
        "                Status: { Value: Coalesce(varVhpPlan.Status, \"New\") },\n"
        "                MaintenancePlanNo: { Id: varVhpPlanSpId, Value: varVhpPlanKey },\n"
        "                ItemDescription: Coalesce(IT.LongText, IT.ShortText),\n"
        "                FunctionalLocation: IT.FunctionalLocation,\n"
        "                ObjectList: IT.ObjectList,\n"
        # Priority er obligatorisk i listen. Appen har ikke feltet - den
        # regnes som i den gamle app (PRIORITY ovenfor).
        f"                Priority: {{ Value: {PRIORITY} }},\n"
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
        # REVISIONSMAERKET (outage-arbejde). Den gamle app skrev det i den
        # boolske Revision - det er den, de eksisterende items har det i.
        # RevisionMark er valgkolonnen med samme betydning, som appens
        # toggle laeser sin tekst fra. Begge skrives, saa intet, der laeser
        # den ene af dem, mister maerket. Foer blev ingen af dem skrevet, og
        # toggle'en var vaek efter naeste aabning.
        "                Revision: !IsBlank(IT.Revision),\n"
        "                RevisionMark: If(IsBlank(IT.Revision), Blank(), { Value: IT.Revision }),\n"
        # SAP-koden som valg; "" rydder kolonnen (issue #112). SAP-ordre-
        # flowet laeser NonFlowUserStatus.Value herfra.
        "                NonFlowUserStatus: If(\n"
        "                    IsBlank(IT.NonFlowUserStatus), Blank(),\n"
        "                    { Value: IT.NonFlowUserStatus }\n"
        "                ),\n"
        # Opslag i de navngivne formler, ikke i listerne - de har Id.
        "                MaintenanceActivityType: With(\n"
        "                    { a: LookUp(colVhpActivityTypeOptions, Value = IT.ActivityType) },\n"
        "                    If(IsBlank(a.Id), Blank(), { Id: a.Id, Value: a.Value })\n"
        "                ),\n"
        "                MainWorkCenter: With(\n"
        "                    { w: LookUp(colVhpMainWorkCenters, Value = Trim(IT.MainWorkCenter)) },\n"
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
        # PM02 gemmes med den varegruppe, brugeren har tastet - ingen
        # standard. PM02-reglen (material_group) i build_status holder Submit tilbage, til den er udfyldt.
        "                MaterialGroup: OP.MaterialGroup,\n"
        # Ydelsesnummeret fra standardoperationen (PM03), se colVhpTasklists.
        "                ServiceNo: OP.ServiceNo,\n"
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
        f"        !{perm.may_change(IDX_NOW + '.RequesterEmail', IDX_STATUS_NOW, 'varVhpMe', resubmit=True)},\n"
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
        # Ren global variabel til filtrene i trin 4, 5 og 7 (R2-007):
        # Coalesce(...) inde i Filter er et funktionsudtryk.
        f"    Set({cfg.PLAN_KEY_Q}, {cfg.PLAN_KEY_REF});\n"
        "    Set(varVhpRequestGuid, Coalesce(varVhpRequestGuid, Text(GUID())))"))


def _step_items():
    """4. Items: opdatér de eksisterende, opret de nye (D7).

    Planens raekker hentes EEN gang ind i colVhpSpItemRows med et
    delegerbart filter mod en ren global variabel - filteret koerer i
    SharePoint, saa samlingen er planens raekker, uanset hvor lang listen
    er. Alt andet (loggen, noeglerne, basisraekkerne til opdateringen og
    oprydningen i trin 7) slaar op i samlingen. Ikke With({ex: Filter(
    liste, ...)}): den scope-variabel bryder delegeringen og har kun de
    foerste 500/2.000 raekker af LISTEN (R2-007). Og ikke LookUp(liste,
    ID = IT.SpId) i ForAll: et scope-felt delegeres ikke (check_layout
    regel 30)."""
    ex = cfg.plan_rows(cfg.L_ITEMS, cfg.PLAN_KEY_Q)
    return _step("Items", (
        # En admin i en andens plan: items, som de staar nu, til loggen.
        # Kun dér; hentningen er den samme som noeglernes.
        f"    ClearCollect(colVhpSpItemRows, {ex});\n"
        "    If(\n"
        f"        {AS_ADMIN},\n"
        "        ClearCollect(\n"
        "            colVhpAdmOld,\n"
        f"            ForAll(colVhpSpItemRows As I, {{ ID: I.ID, ItemID: I.ItemID, Title: I.Title, "
        "ItemDescription: I.ItemDescription, FunctionalLocation: I.FunctionalLocation, "
        "ObjectList: I.ObjectList })\n"
        "        ),\n"
        "        Clear(colVhpAdmOld)\n"
        "    );\n"
        # Hvad der er i SharePoint nu - ID og noegle.
        "    ClearCollect(\n"
        "        colVhpSpItems,\n"
        "        ForAll(colVhpSpItemRows As I, { ID: I.ID, ItemID: I.ItemID, "
        "Sceq: !IsBlank(I.SCEqFL) || !IsBlank(I.SCEqOL) })\n"
        "    );\n"
        # De eksisterende foerst i oversaettelsen: operationerne og
        # materialerne slaar op i den.
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
        # een gang med et delegerbart filter (colVhpSpItemRows ovenfor) -
        # ikke { ID: ... }, som FL-appens compile afviste (issue #32).
        "    With(\n"
        "        {\n"
        f"            old: Filter({SAVEABLE_ITEMS}, SpId in colVhpSpItems.ID)\n"
        "        },\n"
        "        If(\n"
        "            CountRows(old) > 0,\n"
        "            Patch(\n"
        f"                {cfg.L_ITEMS},\n"
        "                ForAll(old As IT, LookUp(colVhpSpItemRows, ID = IT.SpId)),\n"
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
    """5. Operationer - samme model som items (R2-007)."""
    ex = cfg.plan_rows(cfg.L_TASKS, cfg.PLAN_KEY_Q)
    live = f"Filter(colVhpOperations As OP, !IsBlank({M_SPID}))"
    return _step("Operations", (
        f"    ClearCollect(colVhpSpOpRows, {ex});\n"
        "    ClearCollect(\n"
        "        colVhpSpOps,\n"
        "        ForAll(colVhpSpOpRows As T, { ID: T.ID, TaskItemID: T.TaskItemID })\n"
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
        f"            old: Filter({live}, SpId in colVhpSpOps.ID)\n"
        "        },\n"
        "        If(\n"
        "            CountRows(old) > 0,\n"
        "            Patch(\n"
        f"                {cfg.L_TASKS},\n"
        "                ForAll(old As OP, LookUp(colVhpSpOpRows, ID = OP.SpId)),\n"
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
    """6. Materialer. De gamle raekkers ID huskes, og de slettes foerst i
    oprydningen - efter de nye er skrevet.

    Raekkerne faar derfor nyt ID ved hvert gem (R2-071). Det er accepteret:
    intet slaar et materiale op paa ID - SAP-ordren og indlaesningen gaar
    paa PlanKey/ItemKey/TaskItemID - og en plan har faa materialer."""
    return _step("Materials", (
        # Hele raekkerne: oprydningen fjerner dem direkte (R2-007).
        f"    ClearCollect(colVhpOldMats, Filter({cfg.L_MATERIALS}, PlanKey = varVhpPlanKey));\n"
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


def _step_cleanup():
    """7. Oprydning - foerst naar alt er skrevet (D8).

    Hvad der skal vaek, afgoeres i hukommelsen paa samlinger af planens
    EGNE raekker, hentet med et delegerbart filter i trin 4, 5 og 6
    (colVhpSpItemRows, colVhpSpOpRows, colVhpOldMats), og
    raekkerne fjernes direkte med Remove(liste, <raekker>). Ikke
    With({ex: Filter(liste, ...)}): den scope-variabel har kun de foerste
    500/2.000 raekker af listen, og planens raekker ud over loftet blev
    staaende (R2-007). Ikke RemoveIf: den delegeres ikke paa en
    tekstkolonne eller et opslags underfelt."""
    def rm(lst, rows):
        return f"    Remove({lst}, {rows})"
    return _step("Clean-up", ";\n".join([
        # Materialerne skrives altid paa ny (trin 6), saa alle de gamle
        # raekker gaar. De aeldre dokumentraekker roeres ikke (R2-071).
        rm(cfg.L_MATERIALS, "colVhpOldMats"),
        # Operationer foer items: en operation peger paa sit item.
        rm(cfg.L_TASKS, "Filter(colVhpSpOpRows, !(ID in colVhpSavedOps.SpId))"),
        rm(cfg.L_ITEMS, "Filter(colVhpSpItemRows, !(ID in colVhpSavedItems.SpId))"),
    ]))


def _index_patch(status, extra=None):
    rec = ri.record(
        DOMAIN, "vhplan", status,
        request_no="varVhpPlanKey", guid="varVhpRequestGuid", me="varVhpMe",
        owner=f"Coalesce({IDX_NOW}.RequesterEmail, varVhpMe)",
        owner_name=f"Coalesce({IDX_NOW}.RequesterName, User().FullName)",
        current=IDX_NOW,
        short_text="varVhpPlan.PlanText", plant="varVhpPlan.Plant",
        item_count=SAVEABLE_COUNT, source_id="varVhpPlanSpId", indent=8)
    more = f",\n        {extra}" if extra else ""
    return (f"Patch(\n        {cfg.L_INDEX},\n        Coalesce(\n"
            f"            {IDX_NOW},\n"
            f"            Defaults({cfg.L_INDEX})\n        ),\n        {rec}{more}\n    )")


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
        "ApprovalStage: { Value: \"System\" }, SubmittedOn: Now(), StageRunId: \"\", "
        # Kvitteringsmailen (flowet NewPlanCreated) sendes, naar flaget er
        # falsk, og flowet saetter det selv. Nulstilles ved HVER indsendelse,
        # saa en genindsendt plan efter Return ogsaa faar kvittering (R2-050).
        "InitialEmailSent: false, "
        # Note to approver og hvem der indsendte (issue #115) - kun her,
        # saa Save draft og flowene aldrig overskriver noten.
        f"{sn.COL_APPROVER}: varVhpNoteApprover, {sn.COL_BY}: varVhpMe }})\n"
        "        );\n"
        # Progressbaren viser nu godkendelsen (build_status.VhpSubmitted).
        "        Set(varVhpFlow, { Status: varVhpPlanRec.Status.Value, "
        "Stage: varVhpPlanRec.ApprovalStage.Value, ReturnComment: \"\" })\n"
        "    );\n"
        # Hubben laeser KUN indeksraekken. En returneret plan, der gemmes
        # som kladde, staar i AfventerInfo - ogsaa naar indekset haltede
        # bagefter, saa det heler ved foerste gem (R2-036).
        "    If(\n"
        "        varVhpSubmitting,\n"
        f"    {_index_patch(ri.SUBMITTED, NOTE_FLAG)},\n"
        f"        varVhpPlanRec.Status.Value = \"{PLAN_STATUS_RETURNED}\",\n"
        f"    {_index_patch(IDX_STATUS_AWAITING)},\n"
        f"    {_index_patch(ri.DRAFT)}\n"
        "    );\n"
        # Det, der nu staar i SharePoint - konflikttjekket (trin 2) maaler
        # mod det ved naeste gem.
        "    Set(varVhpPlanModified, varVhpPlanRec.Modified)"))


# Hubben viser note-ikonet af indeksraekken alene (tools/submission_notes.py).
NOTE_FLAG = f"{{ {sn.FLAG}: !IsBlank(Trim(varVhpNoteApprover)) }}"


def _step_notes():
    """7b. Note to self ved Submit (issue #115) - i sin egen liste, som kun
    ejeren (og admins) kan laese. Kun ejeren skriver den: en admin, der
    indsender en andens plan, ville eje raekken, og ejeren kunne ikke se
    den. En tom note roerer ingen liste - en eksisterende slettes.
    Teksten gemmes, som den er skrevet."""
    owner = f"!({AS_ADMIN})"
    cur = f"LookUp({sn.LIST}, RequestGuid = varVhpRequestGuid && OwnerEmail = varVhpMe)"
    return _step("Note to self", (
        "    If(\n"
        f"        varVhpSubmitting && {owner},\n"
        f"        With(\n            {{ s: {cur} }},\n"
        "            If(\n"
        "                IsBlank(Trim(varVhpNoteSelf)),\n"
        f"                If(!IsBlank(s), Remove({sn.LIST}, s)),\n"
        f"                Patch(\n                    {sn.LIST},\n"
        f"                    If(IsBlank(s), Defaults({sn.LIST}), s),\n"
        "                    {\n"
        "                        RequestNo: varVhpPlanKey,\n"
        "                        RequestGuid: varVhpRequestGuid,\n"
        "                        PlanId: varVhpPlanSpId,\n"
        "                        Note: varVhpNoteSelf,\n"
        "                        OwnerEmail: varVhpMe\n"
        "                    }\n"
        "                )\n"
        "            )\n"
        "        )\n"
        "    )"))


def _admin_log(submitting="varVhpSubmitting"):
    """Admin i en andens plan: planhovedet foer/efter (varVhpPlanNow mod
    varVhpPlanRec - begge som de staar i SharePoint), items foer (colVhpAdmOld)
    mod det gemte, og Submit (tools/admin_log.py). submitting er udtrykket
    for "det var en indsendelse" - i save_action en kopi af flaget, som
    allerede er nulstillet (R2-035)."""
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
             'If(k > 0, ' + dt.plural("k", "item") + ' & " added", ""))')
    status = f'If({submitting}, {alog.submitted(IDX_NOW + ".Status.Value")}, "")'
    comment = alog.join(header, items, added, status)
    return (f"If(\n    {AS_ADMIN},\n    With(\n        {{ c: {comment} }},\n"
            "        If(\n            !IsBlank(c),\n"
            + alog.write("varVhpRequestGuid", "varVhpPlanKey", alog.EDIT, "c", 12)
            + "\n        )\n    )\n)")


def save_action():
    """Hele gemningen. Om det er Save draft eller Submit, afgoer
    varVhpSubmitting.

    FLAGET NULSTILLES FOERST I BESKEDEN (R2-035). Beskeden laeser en kopi
    (sub), og flaget er falsk, foer der vises eller logges noget - ogsaa
    hvis noget i beskeden fejler. Stod det til sidst, kunne et flag, der
    blev haengende, faa naeste "Save draft" til at indsende planen."""
    detail = 'First(colVhpSaveErrors).Where & ": " & First(colVhpSaveErrors).Msg'
    report = (
        "With(\n"
        "    { sub: varVhpSubmitting },\n"
        "    Set(varVhpSubmitting, false);\n"
        "    If(\n"
        f"    {OK},\n"
        # Save-trinnet er groent, saa laenge planen er den samme - se
        # VhpStateJson i sp_config.py.
        "    Set(varVhpSavedJson, VhpStateJson);\n"
        + _admin_log("sub") + ";\n"
        f"    If(sub, {msg.submitted('varVhpPlanKey')}, {msg.saved('varVhpPlanKey')}),\n"
        f"    If(sub, {msg.failed('Submit', detail)}, {msg.failed('Save', detail)})\n"
        "    )\n"
        ")")
    steps = ";\n".join([
        "Clear(colVhpSaveErrors)",
        _step_keys(),
        _when_ok(_step_conflict()),
        _when_ok(_step_plan()),
        _when_ok(_step_items()),
        _when_ok(_step_ops()),
        _when_ok(_step_materials()),
        _when_ok(_step_cleanup()),
        _when_ok(_step_notes()),
        _when_ok(_step_status()),
        report,
    ])
    # Knappens tilstand (issue #420, build_helpers.act_fx): "save" eller
    # "submit", mens der gemmes - afgjort af flaget, foer det nulstilles -
    # og bagefter ":ok" eller ":failed" efter colVhpSaveErrors. varVhpSaving
    # taendes og slukkes stadig eet sted (A12); andre knapper laeser den.
    body = act_fx(ACT, None, steps, busy_var="varVhpSaving", ok=OK,
                  key_fx='If(varVhpSubmitting, "submit", "save")')
    return (
        "If(\n"
        f"    !varVhpPlanCommitted || {SAVEABLE_COUNT} = 0,\n"
        "    Set(varVhpSubmitting, false);\n"
        "    Notify(\"Create the plan and at least one item first.\", NotificationType.Warning),\n"
        "\n"
        # PLANT ER AENDRET, MEN IKKE GEMT (issue #453). Items, regler og
        # filtre foelger allerede det nye vaerk (VhpPlant), men gemningen
        # skriver planhovedet, som det blev gemt (varVhpPlan). Saa ville
        # planen gemmes med det gamle vaerk og items valideret mod det nye.
        "    Upper(VhpPlant) <> Upper(varVhpPlan.Plant),\n"
        "    Set(varVhpSubmitting, false);\n"
        "    Notify(\"Plant changed to \" & VhpPlant & \" - press Save in the plan header before saving the plan.\", NotificationType.Warning),\n"
        "\n"
        # Kort tekst, funktionsplads, aktivitetstype og arbejdscenter er
        # PAAKRAEVEDE kolonner i MaintenanceItems. Et item uden dem kan ikke
        # gemmes - heller ikke som kladde - saa det siges her, foer noget
        # skrives, i stedet for som SharePoints netvaerksfejl midt i
        # gemningen (R2-008).
        f"    CountRows({NO_REQ}) > 0,\n"
        "    Set(varVhpSubmitting, false);\n"
        "    Notify(\n"
        "        \"Fill in short text, functional location, activity type and main work center on every item before saving: \" &\n"
        f"        Concat({NO_REQ}, Coalesce(Trim(ShortText), FunctionalLocation), \", \"),\n"
        "        NotificationType.Warning\n"
        "    ),\n"
        "\n"
        + body + "\n)"
    )


# Save draft kan bruges, saa snart der er noget at gemme. Samme maal som
# selve gemningen: et tomt item taeller ikke med, saa knappen bliver ikke
# aktiv af det item, appen selv aabnede med.
#
# Submit gaar ogsaa gennem den her knap (Select). Select paa en DEAKTIVERET
# knap koerer ikke dens OnSelect, og popuppen kan staa aaben, mens
# tilstanden aendrer sig - derfor tjekker popuppens Submit knappens
# DisplayMode, foer flaget saettes (SUBMIT_FX, R2-035).
DRAFT_DM = ("If(\n"
            f"    varVhpViewOnly || varVhpSaving || !varVhpPlanCommitted || {SAVEABLE_COUNT} = 0,\n"
            "    DisplayMode.Disabled,\n"
            "    DisplayMode.Edit\n"
            ")")


def save_buttons(can_submit):
    """Save draft og Submit - de to knapper, der skriver planen i
    SharePoint - og Submits popup med noterne (issue #115).

    can_submit er betingelsen for, at planen kan indsendes. DisplayMode er
    bundet til den, saa en graa Submit ikke kan klikkes.

    Submit aabner popuppen med noterne; foerst "Submit" dér indsender: den
    saetter noterne og varVhpSubmitting og vaelger Save draft-knappen.
    Select koerer knappens OnSelect, efter popuppens egen formel er faerdig
    - men kun, naar knappen er aktiv (SUBMIT_FX).

    Returnerer (Save draft, Submit, [popup])."""
    btnDraft = button(SAVE_BUTTON, "\"Save draft\"", save_action(),
                      display_mode=DRAFT_DM, icon=ICON_SAVE)
    btnSubmit = button("btnVhpSubmit", "\"Submit\"", NOTES_OPEN_SUBMIT,
                       primary=True, icon=ICON_SUBMIT,
                       display_mode=f"If(!varVhpViewOnly && {can_submit}, DisplayMode.Edit, DisplayMode.Disabled)")
    return btnDraft, btnSubmit, notes_popup()


def busy_buttons(btnDraft, btnSubmit):
    """"Saving..." / "Submitting..." paa knapperne, mens der gemmes (issue
    #420). Kaldes, naar headeren har sat knappernes endelige tekst og
    bredde. Save draft beholder sin bredde ("Saving..." er kortere);
    Submit vokser kun, hvor "Submitting..." er bredere end teksten."""
    act_button(btnDraft, ACT, "save", grow=False)
    act_button(btnSubmit, ACT, "submit")


# NOTERNE VED SUBMIT (issue #115)
#
# Submit aabner popuppen med de to valgfri noter - den erstatter
# bekraeftelsen, saa der stadig kun er eet ekstra klik. Popuppens Submit
# laegger noterne i variablerne og koerer den SAMME gemning som foer. Tomme
# noter stopper intet. Close er den eneste anden vej ud.
#
# Uden for indsendelsen (en indsendt plan, View) viser den samme popup
# noterne skrivebeskyttet - knappen btnVhpNotes i topbjaelken.
NOTES_EDIT = "IfError(varVhpNotesEdit, false)"
_INPUTS = ("inpVhpNoteA", "inpVhpNoteS")
NOTES_OPEN_SUBMIT = ("Set(varVhpNotesEdit, true);\n" + "".join(f"Reset({c});\n" for c in _INPUTS)
                     + "Set(varVhpConfirmSubmit, true)")
NOTES_OPEN_VIEW = ("Set(varVhpNotesEdit, false);\n" + "".join(f"Reset({c});\n" for c in _INPUTS)
                   + "Set(varVhpConfirmSubmit, true)")
# Ejeren af planen - eller brugeren selv i en ny plan (build_load saetter den).
VHP_OWNER = 'Coalesce(varVhpOwnerEmail, varVhpMe)'
NOTES_HAVE = '(!IsBlank(varVhpNoteApprover) || !IsBlank(varVhpNoteSelf))'

# Popuppens Submit. Flaget saettes KUN, naar Save draft-knappen er aktiv:
# Select paa en deaktiveret knap koerer ikke OnSelect, og saa blev
# varVhpSubmitting staaende, og naeste "Save draft" indsendte planen (R2-035).
SUBMIT_FX = (
    f"If(\n    {SAVE_BUTTON}.DisplayMode = DisplayMode.Edit,\n"
    f"    Set(varVhpSubmitting, true);\n    Select({SAVE_BUTTON}),\n"
    '    Notify("The plan cannot be submitted right now - save it first.", NotificationType.Warning)\n'
    ")")


def notes_popup():
    edit = NOTES_EDIT
    intro = (f'If({edit}, "The plan " & varVhpPlan.Plant & " " & varVhpPlan.PlanText & '
             '" is saved and marked as ready for processing on the landing page. '
             'Both notes are optional.", '
             '"Notes added when " & varVhpPlanKey & " was submitted. They are read-only.")')
    owner = sn.may_self(VHP_OWNER, "varVhpMe")
    ctrls, _a, _s = sn.popup(
        "Vhp", "varVhpConfirmSubmit", edit,
        f'If({edit}, "Submit plan?", "Submission notes")', intro,
        "varVhpNoteApprover", "varVhpNoteSelf",
        # Note to approver: altid i indsendelsen; i visningen kun, naar
        # brugeren maa se den (build_load fylder kun noter, brugeren maa se).
        f"{edit} || !IsBlank(varVhpNoteApprover) || !IsBlank(varVhpNoteSelf)",
        # Note to self: kun ejeren skriver den (_step_notes); i visningen
        # ejer og admin.
        f"If({edit}, {perm.is_owner(VHP_OWNER, 'varVhpMe')}, {owner})",
        submit_fx=("Set(varVhpNoteApprover, inpVhpNoteA.Text);\n"
                   "Set(varVhpNoteSelf, If(" + perm.is_owner(VHP_OWNER, "varVhpMe") +
                   ", inpVhpNoteS.Text, varVhpNoteSelf));\n"
                   + SUBMIT_FX),
        submit_name="btnVhpSubmitConfirm")
    return ctrls
