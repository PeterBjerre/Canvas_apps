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
    return card("conDomFormCard", [head] + rows + dp.form_footer(buttons))


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
# EET FAST LAYOUT (Q13): ingen Compact/All columns. Pladserne er derfor
# (plads, None) - den anden halvdel af parret hoerer til den visning, der
# ikke findes her. Alt det, der ikke er plads til, staar i Details.
SLOTS = [
    (PLANT, None),
    (FL_C, None),
    (MPNO, None),
    (TYPE, None),
    (CHAR, None),
    (UNIT, None),
    (TAG, None),
]


def build_rows():
    return dp.build_list(SLOTS, "STATUS",
                         "Search FL, measuring point, characteristic, PRODOS tag",
                         views=False, fixed=True)


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
    """Linjen nederst i detaljeruden: nummeret fra SAP, som Master Data
    eller en admin kan udfylde og rette."""
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
    return [group("conDomDetMpNo", [lbl, inp, btn], direction="Horizontal", gap=12,
                  height=36, align_items="Center")]
