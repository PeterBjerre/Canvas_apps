# -*- coding: utf-8 -*-
"""
Measuring Points EGNE dele: formularen med de betingede sektioner,
karakteristik-opslaget, valideringen og listens kolonner (issue #210).

Byggeklodserne - gitteret, knapperne, pillerne, dokumentcellen,
FL-comboboksen, listen, detaljerne og indsend - er faelles med Equipment
og Materials og staar i tools/domain_parts.py.

FORMULAREN SPOERGER KUN OM DET, DER GAELDER
-------------------------------------------
    Measuring Point Form  * Required
    [ Plant      ][ Func. location ][ Description ][ Exists in SAP? ]
    findes i forvejen:
    [ Measuring point no. ]
    ny:
    [ Type       ][ Characteristic ][ Char. descr.][ Unit           ]
    [ Unit descr.][ Decimal places ]
    type Measuring Point:   [ Target value ][ Lower limit ][ Upper limit ]
    type Counter:           [ Expected annual usage ]
    [ In PRODOS? ]
    PRODOS = Yes:           [ PRODOS tag ]
    PRODOS = Yes + Counter: [ Counter exists in PRODOS? ]
    taelleren mangler:      [ Counter to be created in ]  + info
    [ Remarks    ][ Documentation ]

HVER SEKTION ER SIN EGEN RAEKKE, OG RAEKKEN BAERER BETINGELSEN. Saa koster
en skjult sektion ingen hoejde: AutoLayout udelader skjulte boern, og
hoejdealgebraen (gen_screen.stack_height) taeller dem kun med, naar de
vises. Felterne har DEN SAMME betingelse i domain_config.WHEN, og den
bruges ogsaa til at rydde et skjult felt ved gem.
"""
import domain_config as cfg
import domain_parts as dp
from gen_screen import C_INFO_FG, C_MUTED, C_WARN_FG
import admin_log as alog
import permissions as perm
import stepper as st
from build_helpers import (button, card, fit_button_width, group, grow, text_ctrl,
                           text_input, themed_dropdown)

CELL_W = dp.CELL_W
REQUIRED = dp.REQUIRED
DM_ROW = dp.DM_ROW

V_TYPE = dp._var("MeasuringPointType")
V_CHAR = dp._var("Characteristic")
V_CHAR_DESC = dp._var("CharacteristicDescription")
V_UNIT = dp._var("CharacteristicUnit")
V_UNIT_DESC = dp._var("CharacteristicUnitDescription")
V_DEC = dp._var("DecimalPlaces")
V_FL = dp._var(cfg.FL_FIELD)
V_TARGET = dp._var("TargetValue")
V_LOW = dp._var("LowerLimit")
V_UP = dp._var("UpperLimit")
V_USAGE = dp._var("ExpectedAnnualUsage")

# Karakteristikkerne, der passer til typen. Tom type paa raekken betyder
# "begge typer" (issue #210 Q18).
CHAR_ITEMS = ("Filter(colDomChars, IsBlank(MeasuringPointType) || "
              f"MeasuringPointType = {V_TYPE})")


def _num(v):
    """Tekstfeltets tal. En tom tekst er Blank(), og noget, der ikke er et
    tal, er ogsaa Blank() - saa en sammenligning aldrig fejler."""
    return f'If(IsBlank(Trim(Coalesce({v}, ""))), Blank(), IfError(Value(Trim({v})), Blank()))'


def _not_a_number(v):
    return (f'!IsBlank(Trim(Coalesce({v}, ""))) && '
            f'IsBlank(IfError(Value(Trim({v})), Blank()))')


def _too_many_decimals(v):
    n = f"Coalesce({V_DEC}, 0)"
    return (f'!IsBlank({_num(v)}) && '
            f'Round({_num(v)}, {n}) <> {_num(v)}')


# ---------------------------------------------------------------------------
# Cellerne, der ikke er et almindeligt felt
# ---------------------------------------------------------------------------
def _clear_characteristic_fx():
    """Et typeskift rydder karakteristikken: listen filtreres paa typen, og
    en karakteristik fra den anden type maa ikke blive staaende."""
    return (f'Set({V_CHAR}, "");\n'
            f'Set({V_CHAR_DESC}, "");\n'
            f'Set({V_UNIT}, "");\n'
            f'Set({V_UNIT_DESC}, "")')


def _type_cell():
    """Typevalget. Det erstatter "Is it a counter?" (Q14) - IsCounter
    udledes af det (domain_config.EXTRA_PATCH)."""
    items = "[" + ", ".join(f'"{x}"' for x in cfg.MP_TYPES) + "]"
    drp = themed_dropdown(
        "drpDomMeasuringPointType", items, V_TYPE, display_mode=DM_ROW,
        label='"Measuring point type, required"',
        onchange=(f"If(\n    Self.Selected.Value <> {V_TYPE},\n"
                  f"    Set({V_TYPE}, Self.Selected.Value);\n"
                  + "\n".join("    " + l for l in _clear_characteristic_fx().split("\n"))
                  + "\n)"))
    cell = dp.grid_cell("conDomMeasuringPointType", "Measuring point type", drp,
                        required=True)
    cell.vis = cfg.WHEN["MeasuringPointType"]
    return cell


def _characteristic_cell():
    """Karakteristikken - og enheden foelger med (Q3).

    Beskrivelsen og enheden KOPIERES ned paa raekken, saa raekken er
    selvstaendig, hvis opslagslisten senere aendres."""
    drp = themed_dropdown(
        "drpDomCharacteristic", CHAR_ITEMS, V_CHAR, display_mode=DM_ROW,
        label='"Characteristic, required"',
        onchange=(f"Set({V_CHAR}, Self.Selected.Value);\n"
                  f"Set({V_CHAR_DESC}, Self.Selected.Description);\n"
                  f"Set({V_UNIT}, Self.Selected.Unit);\n"
                  f"Set({V_UNIT_DESC}, Self.Selected.UnitDescription);\n"
                  f"Set({V_DEC}, Self.Selected.DefaultDecimalPlaces)"))
    cell = dp.grid_cell("conDomCharacteristic", "Characteristic", drp, required=True)
    cell.vis = cfg.WHEN["Characteristic"]
    return cell


def _readonly_cell(col, label):
    """Et felt, karakteristikken bestemmer. Det vises, men tastes ikke."""
    inp = text_input(f"inpDom{col}", dp._var(col), display_mode="DisplayMode.View",
                     label=f'"{label}, from the characteristic"')
    cell = dp.grid_cell(f"conDom{col}", label, inp)
    cell.vis = cfg.WHEN[col]
    return cell


def _cell(key):
    if key == "FL":
        return dp.grid_cell("conDomFl", "Functional location",
                            dp.build_fl_picker(dp.CELL_W, required_formula=REQUIRED),
                            required=True)
    if key == "TEXT":
        return dp.text_cell()
    if key == "DOCS":
        return dp.docs_cell()
    if key == "PLANT":
        return dp.plant_cell()
    if key == "MeasuringPointType":
        return _type_cell()
    if key == "Characteristic":
        return _characteristic_cell()
    if key in ("CharacteristicDescription", "CharacteristicUnit",
               "CharacteristicUnitDescription"):
        return _readonly_cell(key, dict(_LABELS)[key])
    return dp.field_grid_cell(key, required=key in REQUIRED_FIELDS)


_LABELS = [(c, label) for _sec, fields in cfg.SECTIONS for c, label, _k, _ch in fields]

# Felterne med en stjerne. Stjernen staar i en sektion, der kun vises, naar
# den gaelder - saa der staar aldrig en stjerne ved et felt, der ikke skal
# udfyldes.
REQUIRED_FIELDS = {"ExistsInSap", "MeasuringPoint", "MeasuringPointType",
                   "Characteristic", "DecimalPlaces", "ExpectedAnnualUsage",
                   "InProdos", "ProdosTag", "ProdosCounterExists",
                   "CounterCreateIn"}

SPECIAL = {"FL", "TEXT", "DOCS", "PLANT"}
# Raekkerne: (navn, betingelse eller None, cellerne). Hoejst fire celler.
ROWS = [
    ("Object", None, ["PLANT", "FL", "TEXT", "ExistsInSap"]),
    ("Existing", cfg.OLD, ["MeasuringPoint"]),
    ("Type", cfg.NEW, ["MeasuringPointType", "Characteristic",
                       "CharacteristicDescription", "CharacteristicUnit"]),
    ("Unit", cfg.NEW, ["CharacteristicUnitDescription", "DecimalPlaces"]),
    ("Value", f"{cfg.NEW} && {cfg.IS_MP}", ["TargetValue", "LowerLimit", "UpperLimit"]),
    ("Counter", f"{cfg.NEW} && {cfg.IS_COUNTER}", ["ExpectedAnnualUsage"]),
    ("Source", cfg.NEW, ["InProdos"]),
    ("Tag", cfg.IN_PRODOS, ["ProdosTag"]),
    ("CounterQ", cfg.COUNTER_Q, ["ProdosCounterExists"]),
    ("CounterIn", cfg.COUNTER_MISSING, ["CounterCreateIn"]),
    ("More", None, ["Remarks", "DOCS"]),
]
FORM_ORDER = [k for _n, _c, keys in ROWS for k in keys]
NOT_IN_GRID = {cfg.FL_FIELD}


# ---------------------------------------------------------------------------
# Beskederne under formularen
# ---------------------------------------------------------------------------
def _counter_info():
    """Taelleren mangler i PRODOS/SRO - saa venter SAP-oprettelsen paa den
    (Q7). Teksten staar, hvor svaret blev givet."""
    t = text_ctrl(
        "txtDomCounterInfo",
        '"The counter must be created in PRODOS or SRO before the measuring '
        'point can be created in SAP. The PRODOS/SRO creator for the plant is '
        'asked to create it."',
        size=12, color=C_INFO_FG, height=36, wrap="true")
    t.vis = cfg.COUNTER_MISSING
    return t


DUPLICATE = (
    f'!IsBlank(Trim(Coalesce({V_FL}, ""))) && '
    f'!IsBlank(Trim(Coalesce({V_CHAR}, ""))) && '
    "CountRows(Filter(colDomRows, "
    f"{cfg.FL_FIELD} = {V_FL}, Characteristic = {V_CHAR}, "
    "RowId <> Coalesce(varDomActiveRowId, 0))) > 0")


def _duplicate_warning():
    """Samme funktionsplads og karakteristik staar allerede paa en anden
    raekke. Det BLOKERER ikke - to maalepunkter kan vaere ens med vilje -
    men det er naesten altid en gentagelse."""
    t = text_ctrl(
        "txtDomDuplicate",
        '"This functional location and characteristic are already on another '
        'row in this request."',
        size=12, color=C_WARN_FG, height=18, wrap="false")
    t.vis = DUPLICATE
    return t


# ---------------------------------------------------------------------------
# Gem: kravene pr. kombination
# ---------------------------------------------------------------------------
def _blank(v):
    return f'IsBlank(Trim(Coalesce({v}, "")))'


def save_fx(status):
    """domain_parts' gem, plus Measuring Points egne krav til en FAERDIG
    raekke. En kladde kraever kun beskrivelsen, som i de to andre apps.

    Hvert krav er sin egen gren med sin egen besked, saa brugeren ser HVAD
    der mangler."""
    ex = dp._var("ExistsInSap")
    need = [
        (_blank(V_FL),
         "A functional location is required."),
        (_blank(ex),
         "Select whether the measuring point already exists in SAP."),
        (f'{cfg.OLD} && {_blank(dp._var("MeasuringPoint"))}',
         "Enter the existing measuring point no."),
        (f'{cfg.NEW} && {_blank(V_TYPE)}',
         "Select the measuring point type."),
        (f'{cfg.NEW} && {_blank(V_CHAR)}',
         "Select a characteristic from the list."),
        (f'{cfg.NEW} && (IsBlank({V_DEC}) || {V_DEC} < 0 || {V_DEC} > 3)',
         "Decimal places must be between 0 and 3."),
        (f'{cfg.NEW} && ({_not_a_number(V_TARGET)} || {_not_a_number(V_LOW)} || '
         f'{_not_a_number(V_UP)} || {_not_a_number(V_USAGE)})',
         "Target value, limits and expected annual usage must be numbers, not text."),
        (f'{cfg.NEW} && {cfg.IS_MP} && ({_too_many_decimals(V_TARGET)} || '
         f'{_too_many_decimals(V_LOW)} || {_too_many_decimals(V_UP)})',
         "The value has more decimals than Decimal places allows."),
        (f'{cfg.NEW} && {cfg.IS_MP} && !IsBlank({_num(V_LOW)}) && '
         f'!IsBlank({_num(V_UP)}) && {_num(V_LOW)} > {_num(V_UP)}',
         "Lower limit must be less than or equal to upper limit."),
        (f'{cfg.NEW} && {cfg.IS_MP} && !IsBlank({_num(V_TARGET)}) && ('
         f'(!IsBlank({_num(V_LOW)}) && {_num(V_TARGET)} < {_num(V_LOW)}) || '
         f'(!IsBlank({_num(V_UP)}) && {_num(V_TARGET)} > {_num(V_UP)}))',
         "The target value must be between the lower and the upper limit."),
        (f'{cfg.NEW} && {cfg.IS_COUNTER} && '
         f'(IsBlank({_num(V_USAGE)}) || {_num(V_USAGE)} <= 0)',
         "Enter the expected annual usage for the counter - it must be above zero."),
        (f'{cfg.NEW} && {_blank(dp._var("InProdos"))}',
         "Select whether the measuring point is located in PRODOS."),
        (f'{cfg.IN_PRODOS} && {_blank(dp._var("ProdosTag"))}',
         "Enter the PRODOS tag."),
        (f'{cfg.COUNTER_Q} && {_blank(dp._var("ProdosCounterExists"))}',
         "Select whether the counter already exists in PRODOS."),
        (f'{cfg.COUNTER_MISSING} && {_blank(dp._var("CounterCreateIn"))}',
         "Select whether the counter is created in PRODOS or SRO."),
    ]
    return dp.save_row_fx(status, required=need)


# ---------------------------------------------------------------------------
# Formularen
# ---------------------------------------------------------------------------
def build_form():
    dp.check_form_order(FORM_ORDER, SPECIAL, NOT_IN_GRID)
    head = dp.form_head("Measuring Point Form")
    rows = []
    for name, cond, keys in ROWS:
        row = dp.grid_row(f"conDomGrid{name}", [_cell(k) for k in keys])
        if cond:
            row.vis = cond
        rows.append(row)
        if name == "Object":
            # Soegningens svar og dubletadvarslen under den raekke, FL staar i.
            rows.append(dp.build_fl_msg())
            rows.append(_duplicate_warning())
        if name == "CounterIn":
            rows.append(_counter_info())
    buttons = dp.form_buttons(save_fx, "Save row", "New row")
    # Trinstriben lige under hovedet - kun naar godkendelsen er med
    # (features.measuring_point_approval), som i Materials.
    top = [build_steps()] if APPROVAL_ON else []
    return card("conDomFormCard", [head] + top + rows + dp.form_footer(buttons))


# ---------------------------------------------------------------------------
# Listen
# ---------------------------------------------------------------------------
PLANT = ("PLANT", "ThisItem.Plant", 70)
FL_C = ("FUNCTIONAL LOCATION", f"ThisItem.{cfg.FL_FIELD}", 150)
MPNO = ("MEASURING POINT",
        'If(!IsBlank(ThisItem.CreatedMeasuringPointNo), ThisItem.CreatedMeasuringPointNo, '
        '!IsBlank(ThisItem.MeasuringPoint), ThisItem.MeasuringPoint, "New")', 130)
TYPE = ("TYPE", "ThisItem.MeasuringPointType", 120)
CHAR = ("CHARACTERISTIC", "ThisItem.Characteristic", 130)
UNIT = ("UNIT", "ThisItem.CharacteristicUnit", 70)
TAG = ("PRODOS TAG", "ThisItem.ProdosTag", 110)
DESC = (cfg.TEXT_LABEL.upper(),
        f'If(IsBlank(Trim(ThisItem.{cfg.C_TEXT})), "(no text)", ThisItem.{cfg.C_TEXT})', 130)
# EET FAST LAYOUT (Q13): ingen Compact/All columns - og efter #204 har
# ingen af domaeneappene dem. En plads er (overskrift, udtryk,
# mindstebredde). Alt det, der ikke er plads til, staar i Details.
SLOTS = [PLANT, FL_C, MPNO, TYPE, CHAR, UNIT, TAG]


def build_rows():
    return dp.build_list(SLOTS, "STATUS",
                         "Search FL, measuring point, characteristic, PRODOS tag")


# ---------------------------------------------------------------------------
# Details: Master Data udfylder maalepunktsnummeret
#
# SAP Opretters MP-del kommer senere (Q19). Indtil da - og bagefter som
# den manuelle vej og til at bekraefte et eksisterende nummer - skriver
# Master Data eller en admin nummeret her. AEndringen logges som alle
# andre admin-aendringer (tools/admin_log.py).
# ---------------------------------------------------------------------------
MPNO_INPUT = "inpDomDetMpNo"
# Kun en admin (Master Data staar i admin-listen, tools/permissions.py).
# Reglen staar baade i UI'et og i selve handlingen.
MPNO_DM = f"If({perm.IS_ADMIN}, DisplayMode.Edit, DisplayMode.View)"


def _save_mpno_fx(row):
    new_no = f"Trim({MPNO_INPUT}.Text)"
    log = alog.write(
        "varDomRequestGuid", f'Coalesce({row}.RequestNo, "")', alog.EDIT,
        f'"Created measuring point no. for " & Coalesce({row}.ItemKey, "") & '
        f'": " & Coalesce({row}.CreatedMeasuringPointNo, "(blank)") & " '
        f'{alog.ARROW} " & {new_no}', 8)
    return (
        "If(\n"
        f"    !{perm.IS_ADMIN},\n"
        '    Notify("Only Master Data and admins can fill in the measuring point no.",\n'
        "        NotificationType.Warning),\n"
        "\n"
        "    IfError(\n"
        f"    Patch(\n        {cfg.L_ROWS},\n"
        f"        LookUp({cfg.L_ROWS}, ID = varDomDetailsId),\n"
        f"        {{ CreatedMeasuringPointNo: {new_no} }}\n"
        "    );\n"
        + log + ";\n"
        + dp.refresh_rows_fx(4) + ";\n"
        '    Notify("The measuring point no. was saved.", NotificationType.Success),\n'
        "\n"
        '    Notify("Save failed: " & FirstError.Message, NotificationType.Error)\n'
        "    )\n"
        ")")


def details_extra(row):
    """Linjerne nederst i detaljeruden: nummeret fra SAP, som Master Data
    eller en admin kan udfylde og rette - og, med godkendelsen, taellerens
    tilstand og PRODOS/SRO-opretterens knap (fase 5)."""
    lbl = text_ctrl("txtDomDetMpNoL", '"Set measuring point no."', size=12,
                    color=C_MUTED, weight="Semibold", height=36,
                    width=dp.DETAIL_LBL_W, wrap="false")
    inp = grow(text_input(MPNO_INPUT, f'Coalesce({row}.CreatedMeasuringPointNo, "")',
                          max_length=40, display_mode=MPNO_DM,
                          placeholder='"Number from SAP"',
                          label='"Created measuring point no."'), min_w=140)
    btn = button("btnDomDetSaveMpNo", '"Save no."', _save_mpno_fx(row),
                 primary=True, width=fit_button_width('"Save no."'), height=36,
                 display_mode=MPNO_DM,
                 tooltip='"Save the measuring point number from SAP on this row"')
    btn.props["LayoutMinWidth"] = btn.props["Width"]
    out = [group("conDomDetMpNo", [lbl, inp, btn], direction="Horizontal", gap=12,
                 height=36, align_items="Center")]
    if APPROVAL_ON:
        out.append(_counter_line(row))
    return out


# ---------------------------------------------------------------------------
# GODKENDELSEN AF NYE COUNTER-RAEKKER (issue #210, fase 4) - bag flaget
# features.measuring_point_approval
#
# HVEM GODKENDER
# --------------
# En NY Counter (ApprovalRequired, Q1/Q16) godkendes af System Manageren
# for funktionspladsens system - uden undtagelse (Q2). Systemet staar i
# Power BI og den ansvarlige i MD_Approver; appen kan ikke noget af det
# selv. Opslaget er Materials' flow BioSap-Material-ResolveApprovers,
# GENBRUGT uaendret: det tager funktionspladser og svarer med
# { code, systemNo, approver, error } pr. kode og ved intet om materialer.
# Et nyt navn ville aendre Materials' skaerm, og det skal den ikke.
#
# PRODOS/SRO-OPRETTEREN
# ---------------------
# En Counter, hvis taeller mangler i PRODOS, skal oprettes af vaerkets
# PRODOS/SRO-opretter (Q7). Han staar i MD_Approver med noeglen
# PRODOS-<vaerk>, een raekke pr. vaerk (Q17). Det opslag kan appen selv -
# MD_Approver er allerede en datakilde i BIO SAP App.
#
# BEGGE SLAAS OP, NAAR SUBMIT TRYKKES
# ------------------------------------
# Mangler et system, en System Manager eller en opretter, aabner
# bekraeftelsen slet ikke, og beskeden siger hvad der mangler
# (domain_parts.HOOKS["submit_guard"], samme krog som Materials). Det er
# bedre at stoppe her end at sende noget af sted, ingen kan godkende.
# Measuring Point-raekker og eksisterende punkter slaas aldrig op.
# ---------------------------------------------------------------------------
APPROVAL_ON = cfg.APPROVAL_ON

RESOLVE_FLOW = "'BioSap-Material-ResolveApprovers'"
RESOLVE_OUT = "resolveoutput"

APPROVERS = "colDomApprovers"
APPR_SCHEMA = {"Code": '""', "SystemNo": '""', "Approver": '""', "Error": '""'}
APPR_RAW = "varDomApprRaw"
APPR_MSG = "varDomApprMsg"
# Vaerkernes PRODOS/SRO-oprettere - kun de vaerker, Submit sender en
# manglende taeller til.
CREATORS = "colDomCreators"
CRE_SCHEMA = {"Plant": '""', "Creator": '""'}
# Appens tilstand i App.OnStart, naar flaget er taendt.
APPR_STATE = f'Set({APPR_MSG}, "");\nSet(varDomCtrMay, false)'

# Noeglen i MD_Approver: PRODOS- og vaerkets tre bogstaver (seedet
# sharepoint/seed/MD_Approver_MeasuringPoint.csv). Samme regel som hubbens
# vaerksopslag (Upper(Left(Plant, 3))).
CREATOR_PREFIX = "PRODOS-"


def plant_key(expr):
    return f'Upper(Left(Trim(Coalesce({expr}, "")), 3))'


# En raekke i colDomRows (feltnavnene uden praefiks - de bruges i Filter).
NEEDS_APPROVAL = "Coalesce(ApprovalRequired, false)"
COUNTER_MISSING = ('MeasuringPointType = "Counter" && ExistsInSap = "No" && '
                   'InProdos = "Yes" && ProdosCounterExists = "No"')
# De raekker, Submit ville sende (VALID er domain_parts').
APPR_ROWS = f'Filter(colDomRows, Status = "valid" && {NEEDS_APPROVAL})'
CTR_ROWS = f'Filter(colDomRows, Status = "valid" && {COUNTER_MISSING})'
# Funktionspladserne som een "; "-adskilt tekst - formatet, flowet forventer.
SUBMIT_CODES = f'Concat({APPR_ROWS}, FunctionalLocation, "; ")'
BAD = f'Filter({APPROVERS}, !IsBlank(Trim(Coalesce(Error, ""))))'
BAD_CRE = f"Filter({CREATORS}, IsBlank(Creator))"
APPR_FAIL = f'!IsBlank(Trim(Coalesce({APPR_MSG}, "")))'
APPR_BLOCKED = f"(CountRows({BAD}) > 0 || {APPR_FAIL})"
CRE_BLOCKED = f"CountRows({BAD_CRE}) > 0"
BLOCKED = f"({APPR_BLOCKED} || {CRE_BLOCKED})"
MSG_NO_CREATOR = '"Cannot submit: no PRODOS/SRO creator is configured for plant " & '


def resolve_fx(codes):
    """Slaa system og System Manager op for koderne i codes - samme kald
    som Materials (material_parts.resolve_fx).

    Svaret lander i colDomApprovers. Fejler kaldet - flowet er ikke
    importeret, eller Power BI svarer ikke - staar grunden i
    varDomApprMsg, og Submit spaerrer paa den: uden et opslag ved appen
    ikke, om raekken KAN godkendes."""
    return (
        f'Set({APPR_MSG}, "");\n'
        f"Clear({APPROVERS});\n"
        "If(\n"
        f'    !IsBlank(Trim(Coalesce({codes}, ""))),\n'
        "    IfError(\n"
        f"        Set({APPR_RAW}, {RESOLVE_FLOW}.Run({codes}));\n"
        "        Collect(\n"
        f"            {APPROVERS},\n"
        f"            ForAll(Table(ParseJSON({APPR_RAW}.{RESOLVE_OUT})) As R,\n"
        "                {\n"
        "                    Code: Text(R.Value.code),\n"
        "                    SystemNo: Text(R.Value.systemNo),\n"
        "                    Approver: Text(R.Value.approver),\n"
        "                    Error: Text(R.Value.error)\n"
        "                })\n"
        "        );\n"
        # Begge grene skal give det SAMME (check_layout regel 32).
        "        true,\n"
        f'        Set({APPR_MSG}, "Could not look up the system managers: " & '
        "FirstError.Message);\n"
        "        false\n"
        "    )\n"
        ")"
    )


def creators_fx():
    """Vaerkernes PRODOS/SRO-oprettere for de raekker, hvis taeller mangler.

    Eet opslag pr. VAERK, ikke pr. raekke (Distinct). LookUp paa
    ApproverKey delegeres. Approver1Absent -> Approver2, som i flowene."""
    return (
        f"ClearCollect(\n    {CREATORS},\n"
        f"    ForAll(\n        Distinct({CTR_ROWS}, {plant_key('Plant')}) As P,\n"
        f'        With({{ a: LookUp(MD_Approver, ApproverKey = "{CREATOR_PREFIX}" & P.Value) }},\n'
        "            {\n"
        "                Plant: P.Value,\n"
        "                Creator: Upper(Trim(Coalesce(If(a.Approver1Absent, a.Approver2, "
        'a.Approver1), "")))\n'
        "            })\n"
        "    )\n"
        ")"
    )


def guard_message():
    return (
        "If(\n"
        f"    {APPR_FAIL}, {APPR_MSG},\n"
        f'    CountRows({BAD}) > 0, "Cannot submit: " & First({BAD}).Error & ".",\n'
        f'    {MSG_NO_CREATOR}First({BAD_CRE}).Plant & "."\n'
        ")")


def submit_guard():
    """Submit-vagten (domain_parts.HOOKS["submit_guard"]): (foer, spaerret,
    besked). Opslagene koeres kun for de raekker, der skal bruge dem - en
    anmodning uden nye Counter-raekker kalder intet flow."""
    return (resolve_fx(SUBMIT_CODES) + ";\n" + creators_fx(), BLOCKED, guard_message())


# ---------------------------------------------------------------------------
# TRINSTRIBEN (issue #210, fase 4) - den delte stribe fra #204
# (tools/stepper.py)
#
# Foer Submit:   Rows -> Approvers -> PRODOS / SRO -> Ready to submit
# Efter Submit:  Submitted -> Approval -> PRODOS / SRO counter ->
#                Master Data (SAP) / Created in SAP
#
# Det er DE SAMME fire knuder foer og efter, saa billedet ikke skifter
# under brugeren. Et trin, der ikke gaelder - ingen ny Counter, ingen
# manglende taeller - staar som "Not required".
#
# "Efter" er den AABNE anmodning (varDomRequestGuid), naar den er sendt
# af sted - ikke "brugeren har en indsendt raekke et sted": colDomRows er
# alle brugerens raekker. Efter en indsendelse ryddes GUID'en, og striben
# staar igen ved Rows for den naeste.
#
# Hvilket trin en indsendt anmodning er i, staar i indeksraekken:
# UnderBehandling + LastActionBy "System approval" er godkendelsen,
# UnderBehandling + LastActionBy "PRODOS/SRO counter" er taelleren - de to
# tekster skriver flowet BioSap-MeasuringPoint-Approval.
# ---------------------------------------------------------------------------
COUNTER_ACTOR = "PRODOS/SRO counter"
APPROVAL_ACTOR = "System approval"

IDX_ST = 'Coalesce(varDomIdx.Status.Value, "")'
LAST_BY = 'Coalesce(varDomIdx.LastActionBy, "")'
AFTER = ('(!IsBlank(varDomRequestGuid) && !IsBlank(varDomIdx) && '
         'varDomIdx.RequestGuid = varDomRequestGuid && '
         f'({IDX_ST} = "Indsendt" || {IDX_ST} = "UnderBehandling" || '
         f'{IDX_ST} = "KlarTilSAP" || {IDX_ST} = "OprettetISAP"))')
IN_COUNTER = f'({IDX_ST} = "UnderBehandling" && {LAST_BY} = "{COUNTER_ACTOR}")'
AT_SAP = f'({IDX_ST} = "KlarTilSAP" || {IDX_ST} = "OprettetISAP")'
# Den aabne anmodnings raekker.
THIS = 'Filter(colDomRows, !IsBlank(varDomRequestNo) && RequestNo = varDomRequestNo)'
THIS_APPR = f"CountRows(Filter({THIS}, {NEEDS_APPROVAL})) > 0"
THIS_CTR = f"CountRows(Filter({THIS}, {COUNTER_MISSING}))"
CTR_LEFT = f"CountRows(Filter({THIS}, {COUNTER_MISSING} && IsBlank(CounterCreatedOn)))"
VALID_N = 'CountRows(Filter(colDomRows, Status = "valid"))'
DRAFTS = 'CountRows(Filter(colDomRows, Status = "draft"))'


def _steps():
    rows = f'If(\n    {AFTER}, "Done",\n    {VALID_N} > 0, "Done",\n    "Current"\n)'
    appr = (
        "If(\n"
        f"    {AFTER},\n"
        f'    If(!({THIS_APPR}), "Skipped", {IN_COUNTER} || {AT_SAP}, "Done", "Current"),\n'
        f'    CountRows({APPR_ROWS}) = 0, "Skipped",\n'
        f'    {APPR_BLOCKED}, "Current",\n'
        f'    {VALID_N} > 0, "Done",\n'
        '    "Pending"\n'
        ")")
    ctr = (
        "If(\n"
        f"    {AFTER},\n"
        f'    If({THIS_CTR} = 0, "Skipped", {AT_SAP} || {CTR_LEFT} = 0, "Done", '
        f'{IN_COUNTER}, "Current", "Pending"),\n'
        f'    CountRows({CTR_ROWS}) = 0, "Skipped",\n'
        f'    {CRE_BLOCKED}, "Current",\n'
        f'    {VALID_N} > 0, "Done",\n'
        '    "Pending"\n'
        ")")
    done = (
        "If(\n"
        f"    {AFTER},\n"
        f'    If({IDX_ST} = "OprettetISAP", "Done", {IDX_ST} = "KlarTilSAP", "Current", "Pending"),\n'
        f'    {VALID_N} > 0 && !{BLOCKED}, "Current",\n'
        '    "Pending"\n'
        ")")
    return [
        (f'If({AFTER}, "Submitted", "Rows")', rows),
        (f'If({AFTER}, "Approval", "Approvers")', appr),
        (f'If({AFTER}, "PRODOS / SRO counter", "PRODOS / SRO")', ctr),
        (f'If({AFTER}, If({IDX_ST} = "OprettetISAP", "Created in SAP", "Master Data (SAP)"), '
         '"Ready to submit")', done),
    ]


def _steps_hint():
    """Linjen under striben - de samme beskeder, Submit ville give."""
    return (
        "With(\n"
        f"    {{ v: {VALID_N}, d: {DRAFTS} }},\n"
        "    If(\n"
        f"        {AFTER},\n"
        "        If(\n"
        f'            {IDX_ST} = "OprettetISAP", "The measuring points are created in SAP.",\n'
        f'            {IDX_ST} = "KlarTilSAP", "The request is with Master Data for creation in SAP.",\n'
        f'            {IN_COUNTER}, "Waiting for the PRODOS/SRO creator: " & {CTR_LEFT} & '
        '" counter(s) left to create.",\n'
        '            "Waiting for the System Manager to approve the new counters - you get an '
        'e-mail when it moves on."\n'
        "        ),\n"
        '        v = 0 && d = 0, "Add a row and save it to get started.",\n'
        f"        {APPR_FAIL}, {APPR_MSG},\n"
        f'        CountRows({BAD}) > 0, "Cannot submit: " & First({BAD}).Error & ".",\n'
        f'        {CRE_BLOCKED}, {MSG_NO_CREATOR}First({BAD_CRE}).Plant & ".",\n'
        '        d > 0 && v = 0, "Finish the draft row before submitting.",\n'
        '        "Ready: " & v & " row(s) will be submitted." & '
        f'If(CountRows({APPR_ROWS}) > 0, " New counters are approved by the System Manager.", "") & '
        'If(d > 0, " " & d & " draft row(s) stay as drafts.", "")\n'
        "    )\n"
        ")")


def build_steps():
    return st.strip("Dom", _steps(), hint=_steps_hint(),
                    label='"Progress of this request"')


# ---------------------------------------------------------------------------
# GODKENDELSESFLOWET (issue #210, fase 5)
#
# BioSap-MeasuringPoint-Approval startes efter en lykket indsendelse. Det
# svarer appen MED DET SAMME og arbejder videre bagefter - en godkendelse
# kan tage dage. Det koeres for HVER indsendelse (flaget taendt): det er
# flowet, der flytter anmodningen fra Indsendt til KlarTilSAP, ogsaa naar
# der intet er at godkende (Q12).
# ---------------------------------------------------------------------------
APPROVAL_FLOW = "'BioSap-MeasuringPoint-Approval'"


def after_submit_fx():
    """domain_parts.HOOKS["after_submit"] - mens varDomRequestGuid staar."""
    return (
        "IfError(\n"
        f"    {APPROVAL_FLOW}.Run(varDomRequestGuid),\n"
        '    Notify("The request was submitted, but the approval could not be started: " & '
        "FirstError.Message, NotificationType.Warning)\n"
        ")"
    )


# ---------------------------------------------------------------------------
# PRODOS/SRO-TAELLEREN I DETAILS (issue #210, fase 5, Q7)
#
# Vaerkets PRODOS/SRO-opretter (MD_Approver, PRODOS-<vaerk>) faar en mail
# fra flowet og markerer taelleren oprettet her. Det skriver
# CounterCreatedOn/By paa raekken og en "Done"-raekke i MD_ApprovalLog
# (Stage "Counter"), saa hubben kan se trinnet. Er det den SIDSTE taeller,
# og staar anmodningen i taellertrinnet, gaar den til Master Data
# (KlarTilSAP). En admin kan ogsaa markere.
#
# Om brugeren ER opretteren for raekkens vaerk, slaas op EEN gang, naar
# Details aabnes eller skifter raekke (HOOKS details_open/details_nav) -
# ikke i knappens DisplayMode, der evalueres igen og igen.
# ---------------------------------------------------------------------------
DET_ROW = "LookUp(colDomRows, RowId = varDomDetailsId)"
CTR_MAY = "varDomCtrMay"
CTR_ROW = "varDomCtrRow"
CTR_IDX = "varDomCtrIdx"
ME_ID = 'Upper(First(Split(User().Email, "@")).Value)'


def _missing(r):
    return (f'({r}.MeasuringPointType = "Counter" && {r}.ExistsInSap = "No" && '
            f'{r}.InProdos = "Yes" && {r}.ProdosCounterExists = "No")')


def _waiting(r):
    """Raekken har en taeller, der venter paa at blive oprettet."""
    return f'({_missing(r)} && IsBlank({r}.CounterCreatedOn) && {r}.Status = "submitted")'


CTR_SYNC = (
    f"Set({CTR_MAY}, With({{ r: {DET_ROW} }}, If(\n"
    f"    {_waiting('r')},\n"
    f'    With({{ a: LookUp(MD_Approver, ApproverKey = "{CREATOR_PREFIX}" & '
    f"{plant_key('r.Plant')}) }},\n"
    f'        !IsBlank(a) && (Upper(Trim(Coalesce(a.Approver1, ""))) = {ME_ID} || '
    f'Upper(Trim(Coalesce(a.Approver2, ""))) = {ME_ID})),\n'
    "    false\n"
    ")))")
CTR_DM = (f"With({{ r: {DET_ROW} }}, If({_waiting('r')} && ({perm.IS_ADMIN} || {CTR_MAY}), "
          "DisplayMode.Edit, DisplayMode.Disabled))")


def _mark_counter_fx():
    r = CTR_ROW
    left = (f"CountRows(Filter(colDomRows, RequestNo = {r}.RequestNo && "
            f"{COUNTER_MISSING} && IsBlank(CounterCreatedOn)))")
    return (
        f"Set({r}, {DET_ROW});\n"
        "If(\n"
        f"    !({perm.IS_ADMIN} || {CTR_MAY}),\n"
        '    Notify("Only the PRODOS/SRO creator for the plant and admins can mark the counter '
        'as created.", NotificationType.Warning),\n'
        f"    !{_waiting(r)},\n"
        '    Notify("This row has no counter waiting to be created.", NotificationType.Warning),\n'
        "\n"
        "    IfError(\n"
        f"    Patch(\n        {cfg.L_ROWS},\n"
        f"        LookUp({cfg.L_ROWS}, ID = {r}.RowId),\n"
        "        { CounterCreatedOn: Now(), CounterCreatedBy: Lower(User().Email) }\n"
        "    );\n"
        f"    Set({CTR_IDX}, LookUp({cfg.L_INDEX}, RequestNo = {r}.RequestNo));\n"
        f"    Patch({alog.LIST}, Defaults({alog.LIST}), {{\n"
        f"        Title: {r}.RequestNo,\n"
        f"        RequestGuid: {CTR_IDX}.RequestGuid,\n"
        '        Stage: "Counter",\n'
        f'        ItemGuid: {r}.ItemKey & "#counter",\n'
        f'        ItemText: {r}.{cfg.C_TEXT} & " - " & {r}.{cfg.FL_FIELD} & " - " & {r}.ProdosTag,\n'
        '        Decision: "Done",\n'
        f'        Detail: "Counter created in " & Coalesce({r}.CounterCreateIn, "PRODOS"),\n'
        "        DecidedByEmail: Lower(User().Email),\n"
        "        DecidedOn: Now()\n"
        "    });\n"
        + dp.refresh_rows_fx(4) + ";\n"
        # Den SIDSTE taeller i taellertrinnet: anmodningen gaar til Master
        # Data. Staar den stadig i godkendelsen, goer flowet det bagefter.
        "    If(\n"
        f'        !IsBlank({CTR_IDX}) && {CTR_IDX}.Status.Value = "UnderBehandling" &&\n'
        f'        Coalesce({CTR_IDX}.LastActionBy, "") = "{COUNTER_ACTOR}" && {left} = 0,\n'
        f"        Set({CTR_IDX}, Patch({cfg.L_INDEX}, {CTR_IDX}, {{\n"
        '            Status: { Value: "KlarTilSAP" },\n'
        "            StatusStep: 4,\n"
        "            LastActionOn: Now(),\n"
        "            LastActionBy: Lower(User().Email)\n"
        "        }));\n"
        f"        If(!IsBlank(varDomIdx) && varDomIdx.ID = {CTR_IDX}.ID, Set(varDomIdx, {CTR_IDX}));\n"
        '        Notify("All counters are created - the request is now with Master Data.", '
        "NotificationType.Success),\n"
        '        Notify("The counter is marked as created.", NotificationType.Success)\n'
        "    ),\n"
        "\n"
        '    Notify("Save failed: " & FirstError.Message, NotificationType.Error)\n'
        "    )\n"
        ")")


def _counter_line(row):
    """Linjen i Details: taellerens tilstand og knappen."""
    lbl = text_ctrl("txtDomDetCtrL", '"PRODOS/SRO counter"', size=12, color=C_MUTED,
                    weight="Semibold", height=36, width=dp.DETAIL_LBL_W, wrap="false")
    state = (
        f"With({{ r: {row} }}, If(\n"
        f'    !{_missing("r")}, "Not required",\n'
        '    !IsBlank(r.CounterCreatedOn), "Created " & Text(r.CounterCreatedOn, "dd-mm-yyyy") & '
        '" by " & Coalesce(r.CounterCreatedBy, "-"),\n'
        '    "To be created in " & Coalesce(r.CounterCreateIn, "PRODOS")\n'
        "))")
    val = grow(text_ctrl("txtDomDetCtrV", state, size=13, height=36, wrap="false"))
    text = '"Mark counter created"'
    btn = button("btnDomDetCtrDone", text, _mark_counter_fx(), primary=True,
                 width=fit_button_width(text), height=36, display_mode=CTR_DM,
                 tooltip='"Mark the PRODOS/SRO counter on this row as created"')
    btn.props["LayoutMinWidth"] = btn.props["Width"]
    return group("conDomDetCtr", [lbl, val, btn], direction="Horizontal", gap=12,
                 height=36, align_items="Center")


# Godkendelsen er bag flaget: er det slukket, er skaermen praecis som foer -
# ingen opslag, ingen vagt paa Submit, ingen stribe og intet flow.
if APPROVAL_ON:
    dp.configure(submit_guard=submit_guard(), after_submit=after_submit_fx(),
                 details_open=CTR_SYNC, details_nav=CTR_SYNC)
