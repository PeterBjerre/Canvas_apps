# -*- coding: utf-8 -*-
"""
Materials' EGNE dele: formularens felter, popupperne og listens kolonner
(issue #67, omlagt i #228).

Byggeklodserne - gitteret, knapperne, pillerne, dokumentpopuppen, listen og
indsend - er faelles med Equipment og staar i tools/domain_parts.py. Her
staar kun det, der er Materials': hvilke felter, i hvilken raekkefoelge,
hvilke popupper og hvilke kolonner og knapper listen viser.

FORMULAREN (issue #228)
-----------------------
    Material Editor  * Required
    Start with the four key fields ...
    [ Plant       ][ Description  ][ Stock item  No|Yes ][ Replace existing  No|Yes ]
    [ Min stock * ][ Max stock *  ][ Storage bin ]                 <- kun lagervare
    [ Replaced material no. * ]                                    <- kun ved Replace
    [ Manufacturer][ Model number ][ Manuf. part no. ]
    [ Supplier    ][ Supp. part no][ Delivery time   ][ Purchase order text [Add text] ]
    [ Price       ][ Price unit   ][ Stock unit      ]
    [ Strategic   ][ Wear part    ][ Maintenance order no. ]
    (Plant: X) (Row status: ...)  [Save row draft][Save row][Reset]

Den FOERSTE raekke er fast: Plant, beskrivelse og de to til/fra-valg. De
to valg aabner hver deres raekke lige under sig, saa det, de styrer, staar
hvor brugeren kigger. Skjult koster en raekke ingen plads (gitterets og
kortets hoejde regnes af de synlige boern). Resten er grupper: producent,
leverandoer og indkoeb, pris og enhed, klassifikation og ordre.

Hver raekke er sin egen container, der ombryder til to og een kolonne, saa
laese- og tab-raekkefoelgen er den samme paa desktop, tablet og mobil.

STOCK ITEM OG REPLACE EXISTING MATERIAL
---------------------------------------
To segmenterede valg [ No | Yes ] - samme kontrol som Revision i VH-planens
Item Editor (build_helpers.segmented). Felterne, de styrer, staar i
domain_config.WHEN: de vises kun, naar valget er Yes, og gemmes tomme, naar
det er No. Min <= max tjekkes ved BAADE kladde og faerdig raekke.

PURCHASE ORDER TEXT
-------------------
Kolonnen Remarks. Feltet er en knap, der aabner en popup med teksten -
Close er den eneste vej ud, og teksten bliver staaende i formularen, til
raekken gemmes.

DOKUMENTER OG FUNKTIONSPLADSER HOERER TIL DEN GEMTE RAEKKE
---------------------------------------------------------
De stod i formularen. Dokumenterne ligger i en mappe, der hedder raekkens
noegle, og funktionspladserne slaas op og godkendes pr. raekke - begge dele
kraever en gemt raekke. Nu er de knapper paa raekken i Saved Rows
(Docs, Objects), og formularen siger, at de findes dér.

No BOM Item og Recommended stock er fjernet (issue #228). Kolonnerne staar
uroert i SharePoint; appen skriver dem ikke laengere.

Created material no. er IKKE et felt her. Nummeret findes foerst, naar
materialet er oprettet i SAP - det udfyldes i Details bagefter.
"""
import domain_config as cfg
import domain_parts as dp
import env_config as env
import object_list as ol
import stepper as st
import admin_log as alog
import permissions as perm
import layout_tokens as lay
from fl_picker import fl_picker
from gen_screen import C_MUTED, C_INVALID_FG, C_MODAL_BG, C_PRIMARY_SOFT, C_REQUIRED
import doc_upload as du
from build_helpers import (text_ctrl, group, button, text_input, card, grow, segmented,
                           section_header, tap_backdrop, confirm_modal, text_min_height,
                           fit_button_width, text_px, label_px)
from layout_tokens import if_below, fits

CELL_W = dp.CELL_W
REQUIRED = dp.REQUIRED

# Lagervare, "erstatter et materiale" og de felter, de styrer.
STOCK = dp._var("IsStockItem")
MIN_S = dp._var("MinStock")
MAX_S = dp._var("MaxStock")
BIN = dp._var("StorageBin")
REPLACES = dp._var("ReplacesExisting")
REPLACED_NO = dp._var("ReplacedMaterialNo")
IS_STOCK = f"Coalesce({STOCK}, false)"
IS_REPL = f"Coalesce({REPLACES}, false)"
# Purchase order text er kolonnen Remarks (issue #228).
PO = dp._var("Remarks")
PO_OPEN = "varDomPoOpen"
# Kan formularens raekke rettes? Samme regel som domain_parts.DM_ROW.
READ_ONLY = '(varDomViewOnly || varDomRowStatus = "submitted")'

# Er raekken strategisk? Kolonnen er tekst, og gamle raekker kan staa med
# Ja, Y eller true. Normaliseringen staar HER og kun her - der skrives
# altid "Yes"/"No" (domain_config.SECTIONS), og gamle vaerdier laeses som
# de var ment.
STRAT_VALUES = '["YES", "JA", "Y", "TRUE", "1"]'


def is_strategic(expr):
    return f'(Upper(Trim(Coalesce({expr}, ""))) in {STRAT_VALUES})'


STRAT_FORM = is_strategic(dp._var("StrategicPart"))

# OBJECT LIST (issue #204, flyttet til den gemte raekke i #228)
#
# Raekkens funktionspladser gemmes paa raekken som ObjectList (koderne),
# ObjectListJson (kode + beskrivelse) og FunctionalLocation (den foerste
# kode). Delene staar i tools/object_list.py og er domaeneneutrale.
#
# TO SAMLINGER
#   colDomObjects   formularens. Den holder kun en KOPI's objekter: Copy
#                   tager dem med til den nye, ugemte raekke, og Save row
#                   skriver dem paa den. En hentet raekke roerer dem ikke -
#                   dens objekter staar paa raekken og rettes i popuppen.
#   colDomObjPop    popuppens - den gemte raekke, popuppen er aabnet for.
#                   Hver Add og Remove gemmes paa raekken med det samme.
OBJECTS = "colDomObjects"
POP = "colDomObjPop"
OBJ_SCHEMA = ol.schema()
OBJ_ROW = "varDomObjRowId"
OBJ_REC = f"LookUp(colDomRows, RowId = {OBJ_ROW})"
# Det valgte soegeresultat i popuppen.
PICK = "varDomObjPick"
FL_MSG = "varDomFlMsg"
# Mindst 16 tegn foer der kan soeges OG foer der kan tilfoejes (Q11).
# "SSV13 HFC10AJ010" er praecis 16 - i praksis skal man kende hele koden.
MIN_FL_LEN = 16
ADD_READY = f'Len(Trim(Coalesce({PICK}, ""))) >= {MIN_FL_LEN}'
# Gendannelsen, naar en raekke kopieres: JSON'en foerst, saa den
# "; "-adskilte liste, og til sidst FL-kolonnen alene (gamle raekker).
OBJ_RESTORE = ol.restore_fx(
    OBJECTS, json_src="ThisItem.ObjectListJson", list_src="ThisItem.ObjectList",
    fl_src="ThisItem.FunctionalLocation")
# Popuppens liste fra den GEMTE raekke - ved aabning og naar en gemning
# fejler (saa listen aldrig viser noget, der ikke staar paa raekken).
POP_RESTORE = ol.restore_fx(
    POP, json_src=f"{OBJ_REC}.ObjectListJson", list_src=f"{OBJ_REC}.ObjectList",
    fl_src=f"{OBJ_REC}.FunctionalLocation")
# Maa popuppens raekke aendres? Samme laas som dokumenterne
# (domain_parts.DOCS_EDIT): anmodningen kan redigeres, og raekken er ikke
# indsendt.
OBJ_EDIT = (f'(!IsBlank({OBJ_ROW}) && !IfError(varDomViewOnly, false) && '
            f'{OBJ_REC}.Status <> "submitted")')
DM_OBJ = f"If({OBJ_EDIT}, DisplayMode.Edit, DisplayMode.Disabled)"
STRAT_POP = is_strategic(f"{OBJ_REC}.StrategicPart")

# Reset spoerger foerst, naar der er noget at miste.
RESET_ASK = "varDomResetAsk"
# Appens egen tilstand i App.OnStart (domain_app.write_app).
EXTRA_STATE = (f'Set(varDomDetCreatedNo, "");\n'
               f"Set({OBJ_ROW}, Blank());\n"
               f'Set({PICK}, "");\n'
               f"Set({PO_OPEN}, false);\n"
               f"Set({RESET_ASK}, false)")


def _indent(text, n):
    return "\n".join(" " * n + l for l in text.split("\n"))


# KRAVENE TIL EN FAERDIG RAEKKE
#
# Hvert krav er (betingelse der betyder "mangler", besked). De staar her,
# fordi de er Materials' - domain_parts' gem kender dem ikke, og en kladde
# tjekker dem ikke. Beskederne siger HVAD der mangler.
#
# Funktionspladsen er IKKE et krav ved gem laengere (issue #228): den
# tilfoejes paa den gemte raekke, saa en ny raekke kan ikke have en. En
# strategisk raekke uden funktionsplads stoppes i stedet ved Submit
# (submit_guard) - det var der, godkendelsen alligevel kraevede den.
def _row_rules():
    return [
        (f"{IS_STOCK} && (IsBlank({MIN_S}) || IsBlank({MAX_S}))",
         "Min stock and max stock are required for a stock item."),
        (f'{IS_REPL} && IsBlank(Trim(Coalesce({REPLACED_NO}, "")))',
         "Replaced material no. is required when the material replaces an existing one."),
    ]


# Min > max er en FORKERT vaerdi, ikke en manglende - den stoppes ogsaa paa
# en kladde, og linjen under felterne siger det, mens der skrives.
MIN_MAX_BAD = (f"{IS_STOCK} && !IsBlank({MIN_S}) && !IsBlank({MAX_S}) && "
               f"{MIN_S} > {MAX_S}")
MIN_MAX_MSG = "Min stock must be less than or equal to max stock."


def save_fx(status):
    """domain_parts' gem, plus Materials' egne krav: lagerniveauet og det
    erstattede materiale."""
    return dp.save_row_fx(status, required=_row_rules(),
                          always=[(MIN_MAX_BAD, MIN_MAX_MSG)])


# ---------------------------------------------------------------------------
# Formularen
# ---------------------------------------------------------------------------
# Skaermens raekkefoelge (issue #228). Hver liste er een raekke i gitteret;
# (navn, celler, synlighed). Den FOERSTE er fast. TEXT, PLANT, PO og SEG_*
# er de celler, der ikke er et almindeligt felt fra SECTIONS.
SPECIAL = {"TEXT", "PLANT", "PO", "SEG_IsStockItem", "SEG_ReplacesExisting"}
FORM_ROWS = [
    ("conDomGridMain", ["PLANT", "TEXT", "SEG_IsStockItem", "SEG_ReplacesExisting"], None),
    # Lager - kun for en lagervare
    ("conDomGridStock", ["MinStock", "MaxStock", "StorageBin"], IS_STOCK),
    # Erstatning - kun naar materialet erstatter et andet
    ("conDomGridReplace", ["ReplacedMaterialNo"], IS_REPL),
    # Producent og model
    ("conDomGridMfr", ["Manufacturer", "ModelNumber", "ManufacturerPartNo"], None),
    # Leverandoer og indkoeb
    ("conDomGridSupplier", ["Supplier", "SupplierPartNo", "DeliveringTime", "PO"], None),
    # Pris og enhed
    ("conDomGridPrice", ["Price", "PriceUnit", "StockUnit"], None),
    # Klassifikation og vedligeholdelsesordre
    ("conDomGridClass", ["StrategicPart", "WearPart", "MaintenanceOrderNo"], None),
]
FORM_ORDER = [k for _n, keys, _v in FORM_ROWS for k in keys]
# Felter, der ikke er en almindelig celle: de to valg er SEG_*, og
# Purchase order text (Remarks) er PO.
NOT_IN_GRID = {"IsStockItem", "ReplacesExisting", "Remarks"}

# Feltets krav, hvor det afhaenger af et andet felt. Et krav, der ikke
# gaelder lige nu, viser ingen stjerne og giver ingen roed kant
# (domain_parts.field_grid_cell). Synligheden staar i domain_config.WHEN.
CONDITIONAL = {
    "MinStock": {"required": IS_STOCK},
    "MaxStock": {"required": IS_STOCK},
    "ReplacedMaterialNo": {"required": IS_REPL},
}

SEG_TIPS = {
    "IsStockItem": '"Yes: the material is kept in stock - min stock, max stock and '
                   'storage bin are shown"',
    "ReplacesExisting": '"Yes: the material replaces an existing material - its '
                        'number is required"',
}


def _seg_fx(col, on):
    """Valget [ No | Yes ]. Bliver en raekke lagervare, og har den ingen
    lagerplads, foreslaas "X" igen - som paa en ny raekke."""
    v = dp._var(col)
    fx = f"Set({v}, {'true' if on else 'false'})"
    if col == "IsStockItem" and on:
        fx += f'; If(IsBlank(Trim(Coalesce({BIN}, ""))), Set({BIN}, "X"))'
    return fx


def _seg_cell(col):
    label = next(l for c, l, _k, _ch in dp.FIELDS if c == col)
    on = f"Coalesce({dp._var(col)}, false)"
    tip = SEG_TIPS[col]
    seg = segmented(f"conDom{col}Seg", [
        ("No", "No", f"!{on}", _seg_fx(col, False), tip),
        ("Yes", "Yes", on, _seg_fx(col, True), tip),
    ], display_mode=dp.DM_ROW, label=label)
    return dp.grid_cell(f"conDom{col}", label, seg)


PO_TEXTS = ("Add text", "Edit text", "View text")
HAS_PO = f'!IsBlank(Trim(Coalesce({PO}, "")))'


def _po_cell():
    """Purchase order text: de foerste ord af teksten og en knap til
    popuppen. Knappen er udfyldt, naar der ER en tekst."""
    info = grow(text_input(
        "inpDomPoInfo",
        f'If({HAS_PO}, Substitute(Trim({PO}), Char(10), " "), "No text yet")',
        display_mode="DisplayMode.View", label='"Purchase order text"'))
    w = max(fit_button_width(f'"{t}"', size=13) for t in PO_TEXTS)
    btn = button("btnDomPoText",
                 f'If({READ_ONLY}, "View text", If({HAS_PO}, "Edit text", "Add text"))',
                 f"Set({PO_OPEN}, true)", width=w, height=32,
                 accessible='"Open the purchase order text"',
                 tooltip='"Text for the purchase order"')
    btn.props["Size"] = "13"
    btn.props["LayoutMinWidth"] = str(w)
    dp.pill(btn, HAS_PO)
    row = group("conDomPoRow", [info, btn], direction="Horizontal", gap=8,
                height=36, align_items="Center", width=CELL_W)
    return dp.grid_cell("conDomPo", "Purchase order text", row)


def _cell(key):
    if key == "TEXT":
        return dp.text_cell()
    if key == "PLANT":
        return dp.plant_cell()
    if key == "PO":
        return _po_cell()
    if key.startswith("SEG_"):
        return _seg_cell(key[4:])
    return dp.field_grid_cell(key, **CONDITIONAL.get(key, {}))


EDITOR_HINT = ("Start with the four key fields. Save the row, then add documentation "
               "and functional locations from Saved Rows.")


def _editor_head():
    """Sektionens overskrift - samme som Item Editor i VH-planen
    (build_helpers.section_header), med "* Required" efter titlen og en
    linje, der siger, hvordan formularen bruges."""
    star = text_ctrl("txtDomFormReqStar", '"*"', size=12, color=C_REQUIRED,
                     weight="Semibold", height=18, width=8, wrap="false",
                     accessible='"Required"')
    legend = text_ctrl("txtDomFormReq", '"Required"', size=12, color=C_MUTED,
                       height=18, width=text_px("Required", 12, semibold=False),
                       wrap="false")
    head = section_header("conDomEditorHead", "Material Editor", None,
                          extra_left=[star, legend])
    # Een linje paa en bred skaerm, to eller tre paa en smal - hoejden
    # foelger kortets bredde, saa intet klippes.
    need = text_px(EDITOR_HINT, 12, semibold=False)
    h = fits(dp.FORM_W, need, if_below("Tablet", "54", "36"), "18")
    hint = text_ctrl("txtDomEditorHint", f'"{EDITOR_HINT}"', size=12, color=C_MUTED,
                     height=h, wrap="true")
    return [head, hint]


def reset_fx():
    """Reset: ryd KUN formularen. Saved Rows og anmodningen roeres ikke.
    Er der noget at miste, spoerges der foerst."""
    return (f"If(\n{_indent(_dirty(), 4)},\n    Set({RESET_ASK}, true),\n"
            + _indent(dp.clear_form_fx(), 4) + "\n)")


def _dirty():
    """Er der ugemte aendringer i formularen?

    En NY raekke: noget er udfyldt ud over standardvaerdierne (eller en
    kopi har taget objekter med). En HENTET raekke: formularen er ikke den
    samme som raekken i listen - samme sammenligning, som admin-loggen
    bruger (admin_log.diff)."""
    new = [f'!IsBlank(Trim(Coalesce(varDomFText, "")))',
           f'!IsBlank(Trim(Coalesce(varDomFPlant, "")))',
           f"CountRows({OBJECTS}) > 0"]
    defaults = dp.HOOKS["field_defaults"]
    for col, _l, kind, _ch in dp.FIELDS:
        v = dp._var(col)
        if col in defaults:
            new.append(f'Coalesce({v}, "") <> {defaults[col]}')
        elif kind == "bool":
            new.append(f"Coalesce({v}, false)")
        elif kind == "num":
            new.append(f"!IsBlank({v})")
        else:
            new.append(f'!IsBlank(Trim(Coalesce({v}, "")))')
    changed = (f"!IsBlank(With({{ o: {dp.ACTIVE} }},\n"
               + _indent(alog.diff(dp._diff_pairs()), 4) + "\n))")
    return ("If(\n    IsBlank(varDomActiveRowId),\n    "
            + " ||\n    ".join(new) + ",\n    " + changed + "\n)")


def build_form():
    dp.check_form_order(FORM_ORDER, SPECIAL, NOT_IN_GRID)
    rows = []
    for name, keys, vis in FORM_ROWS:
        row = dp.grid_row(name, [_cell(k) for k in keys])
        if vis:
            row.vis = vis
        rows.append(row)
        if name == "conDomGridStock":
            # Min > max siges, mens der skrives - ikke foerst ved gem.
            rows.append(text_ctrl("txtDomStockMsg", f'"{MIN_MAX_MSG}"', size=12,
                                  color=C_INVALID_FG, height=18, wrap="false",
                                  visible=MIN_MAX_BAD))
    buttons = dp.form_buttons(
        save_fx, "Save row", "Reset", new_fx=reset_fx(), new_icon="ArrowReset",
        new_tooltip='"Clear the form and start a new row - saved rows are not changed"')
    # Trinstriben lige under hovedet - foer felterne, saa den er det
    # foerste, man ser (kun naar godkendelsen er med).
    top = [build_steps()] if APPROVAL_ON else []
    return card("conDomFormCard", _editor_head() + top + rows + dp.form_footer(buttons))


# ---------------------------------------------------------------------------
# Purchase order text - popuppen
# ---------------------------------------------------------------------------
PO_W = "Min(640, App.Width - 32)"


def _po_popup():
    """Teksten skrives direkte i formularens variabel, saa den bliver
    staaende, naar popuppen lukkes, og gemmes med raekken. Close er den
    eneste vej ud - et tryk ved siden af lukker den ikke."""
    vis = f"IfError({PO_OPEN}, false)"
    back = tap_backdrop("conDomPoBackdrop", vis, "false")
    title = grow(text_ctrl("txtDomPoH", '"Purchase order text"',
                           size=lay.SIZE_CARD_TITLE, weight="Semibold",
                           height=text_min_height(lay.SIZE_CARD_TITLE), wrap="false"))
    close = button("btnDomPoClose", '"Close"', f"Set({PO_OPEN}, false)",
                   width=84, height=32, accessible='"Close the purchase order text"')
    close.props["LayoutMinWidth"] = "84"
    head = group("conDomPoHead", [title, close], direction="Horizontal", gap=12,
                 align_items="Center")
    hint = text_ctrl(
        "txtDomPoHint",
        f'If({READ_ONLY}, "Read only - this row cannot be changed.", '
        '"The text is saved with the row when you press Save row or Save row draft.")',
        size=12, color=C_MUTED, height=if_below("Tablet", "36", "18"), wrap="true")
    box = text_input("inpDomPoText", PO, height="Min(220, App.Height - 220)",
                     display_mode=dp.DM_ROW, ttype="Multiline",
                     placeholder='"Text for the purchase order"',
                     label='"Purchase order text"',
                     onchange=f"Set({PO}, Self.Text)")
    modal = group("conDomPoModal", [head, hint, box], direction="Vertical", gap=12,
                  fill=C_MODAL_BG, border_color=C_PRIMARY_SOFT, radius=lay.RADIUS_MODAL,
                  pad=(18, 18, 18, 18), width=PO_W, drop_shadow="ExtraBold",
                  visible=vis)
    modal.props["X"] = dp.MODAL_X
    modal.props["Y"] = dp.MODAL_Y
    return [back, modal]


# ---------------------------------------------------------------------------
# Functional locations / Object List - popuppen paa den gemte raekke
# ---------------------------------------------------------------------------
OBJ_W = "Min(760, App.Width - 32)"


def open_objects_fx():
    """Raekkens Objects-knap: peg popuppen paa DENNE raekke og fyld listen
    fra raekken, som den er gemt. Soegningen starter forfra."""
    return (f"Set({OBJ_ROW}, ThisItem.RowId);\n"
            f'Set({PICK}, "");\n'
            f"{dp.fl_reset_fx_dom()};\n"
            + ol.restore_fx(POP, json_src="ThisItem.ObjectListJson",
                            list_src="ThisItem.ObjectList",
                            fl_src="ThisItem.FunctionalLocation"))


def close_objects_fx():
    return (f"Set({OBJ_ROW}, Blank());\n"
            f'Set({PICK}, "");\n'
            f"{ol.clear_fx(POP)};\n"
            f"{dp.fl_reset_fx_dom()}")


def persist_objects_fx():
    """Gem popuppens liste paa raekken - med det samme, efter hver Add og
    Remove, saa intet kan gaa tabt ved Close.

    Kun de tre objektkolonner skrives. Samlingen af raekker opdateres med
    det, SharePoint svarede, i stedet for at hente alle raekker forfra.
    Fejler gemningen, vises listen, som den staar paa raekken."""
    key = f'Coalesce({OBJ_REC}.ItemKey, "")'
    log = alog.write("varDomRequestGuid", "varDomRequestNo", alog.EDIT,
                     f'"Object list on " & {key} & ": " & '
                     f'Coalesce(varDomObjSp.ObjectList, "(empty)")', 12)
    return (
        "If(\n"
        # Rettigheden staar ogsaa i selve handlingen, ikke kun i UI'et.
        f"    {dp.AS_ADMIN} && !{perm.IS_ADMIN},\n"
        f"    {dp.DENIED_OTHER};\n"
        + _indent(POP_RESTORE, 4) + ";\n"
        "    false,\n"
        "    IfError(\n"
        "        Set(\n"
        "            varDomObjSp,\n"
        f"            Patch({cfg.L_ROWS}, LookUp({cfg.L_ROWS}, ID = {OBJ_ROW}), {{\n"
        f"                ObjectList: {ol.codes_fx(POP)},\n"
        f"                ObjectListJson: {ol.json_fx(POP)},\n"
        f"                FunctionalLocation: {ol.first_fx(POP)}\n"
        "            })\n"
        "        );\n"
        f"        UpdateIf(colDomRows, RowId = {OBJ_ROW}, {{\n"
        '            ObjectList: Coalesce(varDomObjSp.ObjectList, ""),\n'
        '            ObjectListJson: Coalesce(varDomObjSp.ObjectListJson, ""),\n'
        '            FunctionalLocation: Coalesce(varDomObjSp.FunctionalLocation, "")\n'
        "        });\n"
        f"        If(\n            {dp.AS_ADMIN},\n{log}\n        );\n"
        "        true,\n"
        f'        Set({FL_MSG}, "Could not save the object list: " & FirstError.Message);\n'
        + _indent(POP_RESTORE, 8) + ";\n"
        "        false\n"
        "    )\n"
        ")"
    )


def _add_fx():
    """Add: laeg det VALGTE resultat i listen og gem den paa raekken.
    Dubletter og et tomt valg afvises af ol.add_fx - saa gemmes der intet.

    Er raekken strategisk, slaas systemet og dets ansvarlige op med det
    samme (bag flaget), saa initialerne staar under listen."""
    desc = f'Coalesce(LookUp(colDomFl, Code = {PICK}).Description, "")'
    after = persist_objects_fx()
    if APPROVAL_ON:
        look = _indent(resolve_fx(ol.codes_fx(POP)), 4)
        after += f";\nIf(\n    {STRAT_POP},\n{look}\n)"
    return (f"Set(varDomObjN, {ol.count_fx(POP)});\n"
            + ol.add_fx(POP, PICK, desc, FL_MSG) + ";\n"
            f"If(\n    {ol.count_fx(POP)} > varDomObjN,\n"
            + _indent(after, 4) + "\n)")


def _objects_popup():
    vis = f"!IsBlank({OBJ_ROW})"
    back = tap_backdrop("conDomObjPopBackdrop", vis,
                        f"If(!{dp.FL_BUSY_VAR}, {close_objects_fx()})")
    title = grow(text_ctrl(
        "txtDomObjPopH",
        f'"Functional locations · " & Coalesce({OBJ_REC}.ItemKey, "")',
        size=lay.SIZE_CARD_TITLE, weight="Semibold",
        height=text_min_height(lay.SIZE_CARD_TITLE), wrap="false"))
    close = button("btnDomObjPopClose", '"Close"', close_objects_fx(),
                   width=84, height=32,
                   accessible='"Close the functional locations"',
                   display_mode=f"If({dp.FL_BUSY_VAR}, DisplayMode.Disabled, DisplayMode.Edit)")
    close.props["LayoutMinWidth"] = "84"
    head = group("conDomObjPopHead", [title, close], direction="Horizontal", gap=12,
                 align_items="Center")
    hint = text_ctrl(
        "txtDomObjPopHint",
        f'If({OBJ_EDIT}, "Search with at least {MIN_FL_LEN} characters, pick a result '
        'and press Add. Each change is saved on the row.", '
        '"Read only - the row or the request cannot be changed.")',
        size=12, color=C_MUTED, height=if_below("Tablet", "36", "18"), wrap="true")
    # Soegningen er FL-vaelgerens egen (tools/fl_picker.py) - den samme som
    # stod i formularen, med samme mindstelaengde.
    picker = fl_picker(
        "Dom", combo=dp.FL_COMBO, results="colDomFl", raw_var="varDomFlRaw",
        msg_var=FL_MSG, busy_var=dp.FL_BUSY_VAR, query_var=dp.FL_QUERY_VAR,
        last_var=dp.FL_LAST_VAR, pick_var=PICK,
        default_items=f"Filter(colDomFl, Code = {PICK})",
        display_mode="DisplayMode.Edit", min_len=MIN_FL_LEN,
        width="Parent.Width", stack_search=True)
    picker.vis = OBJ_EDIT
    msg = dp.build_fl_msg()
    add = ol.add_button(
        "Dom", _add_fx(),
        display_mode=f"If({OBJ_EDIT} && {ADD_READY}, DisplayMode.Edit, DisplayMode.Disabled)")
    add.vis = OBJ_EDIT
    pnl = ol.panel(
        "Dom", POP, width="Parent.Width", msg_var=FL_MSG, add=add,
        display_mode=DM_OBJ,
        extra=([_approver_line()] if APPROVAL_ON else ()),
        hint='"No functional locations on this row yet."',
        on_remove=persist_objects_fx())
    body = du.capped_body("conDomObjPopBody", [hint, picker, msg, pnl],
                             f"App.Height - 40 - 36 - {head.h} - 14")
    modal = group("conDomObjPopModal", [head, body], direction="Vertical", gap=14,
                  fill=C_MODAL_BG, border_color=C_PRIMARY_SOFT, radius=lay.RADIUS_MODAL,
                  pad=(18, 18, 18, 18), width=OBJ_W, drop_shadow="ExtraBold",
                  visible=vis)
    modal.props["X"] = dp.MODAL_X
    modal.props["Y"] = dp.MODAL_Y
    return [back, modal]


def build_popups():
    """Materials' egne popupper (domain_app.build_screen): objektlisten,
    indkoebsteksten og Reset's spoergsmaal - [sloer, popup] hver."""
    ask = confirm_modal(
        "DomReset", RESET_ASK, "Discard unsaved changes?",
        '"The form is cleared and starts a new row. Saved rows and the request '
        'are not changed."',
        "Reset", dp.clear_form_fx(), "btnDomResetConfirm", icon=None)
    return _objects_popup() + _po_popup() + ask


# ---------------------------------------------------------------------------
# Listen - kolonnerne og raekkens knapper (issue #228)
# ---------------------------------------------------------------------------
# (overskrift, udtryk, mindstebredde). Se domain_parts.build_list for, hvad
# en plads er. Funktionspladsen er ikke en kolonne laengere: den staar paa
# Objects-knappen og i Details.
DESC = (cfg.TEXT_LABEL.upper(),
        f'If(IsBlank(Trim(ThisItem.{cfg.C_TEXT})), "(no text)", ThisItem.{cfg.C_TEXT})', 150)
MFR = ("MANUFACTURER", "ThisItem.Manufacturer", 110)
MPN = ("MANUFACTURER PART NO.", "ThisItem.ManufacturerPartNo", 150)
SUPP = ("SUPPLIER", "ThisItem.Supplier", 100)
SLOTS = [DESC, MFR, MPN, SUPP]

# Antal funktionspladser paa en gemt raekke - af den GEMTE ObjectList, og
# FL-kolonnen alene paa en raekke fra foer objektlisten.
ROW_OBJ_N = ('With({ n: CountRows(Filter(Split(Coalesce(ThisItem.ObjectList, ""), ";"), '
             '!IsBlank(Trim(Value)))) }, '
             'If(n = 0 && !IsBlank(Trim(Coalesce(ThisItem.FunctionalLocation, ""))), 1, n))')


def _w(name, longest):
    """Bredden: den afproevede i domain_parts.ROW_BTN (13 pt, klipper ikke),
    eller tekstens laengste form + den samme luft (label_px + 32)."""
    return max(dp.ROW_BTN.get(name, 0), label_px(longest, 13) + 32)


def row_actions():
    """Details, Edit, Docs, Objects, Copy og Delete - Delete sidst og kun
    som ikon. Docs og Objects viser antallet, naar der er noget."""
    docs_n = "Coalesce(ThisItem.FileCount, 0)"
    return [
        dp.RowAction("btnDomRowDetails", '"Details"', dp.details_fx(), _w("btnDomRowDetails", "Details")),
        dp.RowAction("btnDomRowOpen", '"Edit"', dp.load_row_fx(), _w("btnDomRowOpen", "Edit"),
                     mode=dp.DM_ROW_EDIT),
        dp.RowAction("btnDomRowDocs",
                     f'If({docs_n} > 0, "Docs (" & {docs_n} & ")", "Docs")',
                     dp.open_docs_fx(), _w("btnDomRowDocs", "Docs (00)"),
                     label=f'"Documentation for " & ThisItem.ItemKey & ", " & {docs_n} & " file(s)"'),
        dp.RowAction("btnDomRowObjects",
                     f'If({ROW_OBJ_N} > 0, "Objects (" & {ROW_OBJ_N} & ")", "Objects")',
                     open_objects_fx(), _w("btnDomRowObjects", "Objects (00)"), line=2,
                     label=f'"Functional locations for " & ThisItem.ItemKey'),
        dp.RowAction("btnDomRowCopy", '"Copy"', dp.copy_row_fx(), _w("btnDomRowCopy", "Copy"),
                     mode=dp.ROW_MODES["btnDomRowCopy"], line=2),
        dp.RowAction("btnDomRowDelete", '"Delete row"', dp.delete_this_row_fx(),
                     dp.ROW_BTN["btnDomRowDelete"], mode=dp.DM_ROW_DEL, danger=True,
                     icon="Delete", icon_only=True, line=2),
    ]


def build_rows():
    return dp.build_list(SLOTS, "STATUS", "Search FL, supplier, part no., material")


# ---------------------------------------------------------------------------
# DETALJERUDEN - grupperet (issue #204)
#
# Samme felter som foer, men i grupper, saa raekken kan laeses. Hver gruppe
# er (overskrift, felter); et felt er en kolonne eller (etiket, udtryk),
# hvor {row} er raekken.
# ---------------------------------------------------------------------------
DETAILS_GROUPS = [
    ("Identification", ["KEY", "TEXT", "PLANT", "STATUS"]),
    ("Object list", [
        ("Functional locations", 'Coalesce({row}.ObjectList, Coalesce({row}.FunctionalLocation, "-"))'),
        ("Primary functional location", 'Coalesce({row}.FunctionalLocation, "-")'),
    ]),
    ("Manufacturer and supplier", ["Manufacturer", "ModelNumber", "ManufacturerPartNo",
                                   "Supplier", "SupplierPartNo"]),
    ("Stock and storage", ["StockUnit", "Price", "PriceUnit", "DeliveringTime",
                           "IsStockItem", "MinStock", "MaxStock", "StorageBin"]),
    ("Classification and approval", [
        ("Strategic part", 'If(%s, "Yes", "No")' % is_strategic("{row}.StrategicPart")),
        "WearPart",
        ("Approval required", 'If(Coalesce({row}.ApprovalRequired, false), "Yes", "No")'),
    ]),
    ("Additional information", ["Remarks", "MaintenanceOrderNo", "ReplacesExisting",
                                "ReplacedMaterialNo", "CreatedMaterialNo"]),
    ("Requester and request", ["REQUESTNO", "RequesterName", "RequesterEmail",
                               "SubmittedOn", "DOCS"]),
]

# CREATED MATERIAL NO. UDFYLDES HER - IKKE I FORMULAREN (issue #204, Q16)
#
# Nummeret er det, anmodningen FOERER TIL: det findes foerst, naar
# materialet er oprettet i SAP. Derfor staar feltet i Details og kan
# udfyldes bagefter - af rekvirenten paa sine egne raekker og af en admin.
# Det starter ikke godkendelsen igen: godkendelsen handler om anmodningen,
# og nummeret findes foerst efter den.
CREATED_VAR = "varDomDetCreatedNo"
CREATED_IN = "inpDomDetCreatedNo"
DET_ROW = "LookUp(colDomRows, RowId = varDomDetailsId)"
# Naar ruden skifter raekke, skal feltet vise DEN raekkes nummer.
DETAILS_SYNC = (f'Set({CREATED_VAR}, Coalesce({DET_ROW}.CreatedMaterialNo, ""));\n'
                f"Reset({CREATED_IN})")
CREATED_EDIT = (f'If(Coalesce({DET_ROW}.Status, "") = "submitted" || IsAdmin, '
                "DisplayMode.Edit, DisplayMode.Disabled)")


def _save_created_fx():
    return (
        "IfError(\n"
        f"    Patch(\n        {cfg.L_ROWS},\n"
        f"        LookUp({cfg.L_ROWS}, ID = varDomDetailsId),\n"
        f'        {{ CreatedMaterialNo: Trim(Coalesce({CREATED_VAR}, "")) }}\n'
        "    );\n"
        + dp.refresh_rows_fx(4) + ";\n"
        '    Notify("Created material no. saved.", NotificationType.Success),\n'
        '    Notify("Save failed: " & FirstError.Message, NotificationType.Error)\n'
        ")"
    )


def details_rows(row):
    """Linjen under felterne i Details: materialenummeret fra SAP, og en
    mail til rekvirenten."""
    lbl = text_ctrl("txtDomDetCreatedLbl", '"Created material no."', size=12,
                    color=C_MUTED, weight="Semibold", height=18, wrap="false")
    hint = text_ctrl("txtDomDetCreatedHint",
                     '"Fill this in once the material exists in SAP. It does not '
                     'restart the approval."',
                     size=11, color=C_MUTED, height=18, wrap="false")
    inp = text_input(CREATED_IN, CREATED_VAR, max_length=40, width="200",
                     placeholder='"SAP material number"',
                     display_mode=CREATED_EDIT,
                     label='"Created material no."',
                     onchange=f"Set({CREATED_VAR}, Self.Text)")
    inp.props["LayoutMinWidth"] = "140"
    save = button("btnDomDetCreatedSave", '"Save number"', _save_created_fx(),
                  width=fit_button_width('"Save number"'), height=36,
                  display_mode=CREATED_EDIT,
                  tooltip='"Save the SAP material number on this row"')
    save.props["LayoutMinWidth"] = save.props["Width"]
    mail = button("btnDomDetMail", '"Email requester"',
                  f'Launch("mailto:" & Coalesce({row}.RequesterEmail, ""))',
                  width=fit_button_width('"Email requester"'), height=36,
                  visible=f'!IsBlank({row}.RequesterEmail)',
                  tooltip='"Write to the requester"')
    mail.props["LayoutMinWidth"] = mail.props["Width"]
    row_ctrl = group("conDomDetCreatedRow", [inp, save, mail], direction="Horizontal",
                     gap=8, height=36, align_items="Center")
    return [group("conDomDetCreated", [lbl, hint, row_ctrl], direction="Vertical", gap=4)]


# ---------------------------------------------------------------------------
# Materials' kroge i de faelles dele (tools/domain_parts.configure)
#
# De saettes ved IMPORT, fordi delene kaldes af tools/domain_app.py, som
# kun ser modulet - ikke en opsaetningsfunktion.
# ---------------------------------------------------------------------------
# Objektkolonnerne, naar formularen gemmer: en NY raekke (en kopi) faar de
# objekter, kopien tog med; en hentet raekke beholder sine egne - de rettes
# i popuppen og staar allerede i colDomRows.
def _obj_patch(new_fx, col):
    return (f"If(IsBlank(varDomActiveRowId), {new_fx}, "
            f'Coalesce({dp.ACTIVE}.{col}, ""))')


dp.configure(
    # Storage bin foreslaas som "X", naar formularen ryddes.
    field_defaults={"StorageBin": '"X"'},
    # Formularens objekter er kun en kopis (se OBJECTS): de fyldes ved
    # Copy og ryddes ellers.
    clear_extra=ol.clear_fx(OBJECTS),
    load_extra=ol.clear_fx(OBJECTS),
    copy_extra=OBJ_RESTORE,
    # Gem: koderne, JSON'en og FL-kolonnen som den FOERSTE kode.
    # ApprovalRequired er raekkens eget svar paa "skal den godkendes?".
    # Den skrives ved HVER gemning, ogsaa som kladde: det er data, ikke
    # godkendelse, og flowet filtrerer paa den.
    extra_patch=[("FunctionalLocation", _obj_patch(ol.first_fx(OBJECTS), "FunctionalLocation")),
                 ("ObjectList", _obj_patch(ol.codes_fx(OBJECTS), "ObjectList")),
                 ("ObjectListJson", _obj_patch(ol.json_fx(OBJECTS), "ObjectListJson")),
                 ("ApprovalRequired", STRAT_FORM)],
    # Grupperet detaljerude, og materialenummeret under felterne.
    details_groups=DETAILS_GROUPS,
    details_rows=details_rows,
    details_open=DETAILS_SYNC,
    details_nav=DETAILS_SYNC,
)
# Raekkens knapper bygges af hent/kopier/detaljer OVENFOR - derfor efter
# den foerste configure.
dp.configure(row_actions=row_actions())


# ---------------------------------------------------------------------------
# SYSTEMGODKENDELSEN (issue #204) - bag feature-flaget material_approval
#
# HVORFOR DER SKAL SLAAS OP I ET FLOW
# -----------------------------------
# En strategisk raekke skal godkendes af systemets ansvarlige. Hvilket
# SYSTEM en funktionsplads hoerer til staar i Power BI (Functional
# Locations, Plant Section Key), og HVEM der er ansvarlig staar i
# MD_Approver. Appen kan ikke noget af det selv, saa
# BioSap-Material-ResolveApprovers slaar begge op og svarer med et
# JSON-array: { code, systemNo, approver, error } pr. kode.
#
# Flowet LAESER kun. Det kaldes to steder:
#   1. naar et objekt er lagt i listen paa en strategisk raekke - saa
#      brugeren ser initialerne MENS han skriver
#   2. naar Submit trykkes - for ALLE strategiske raekker i indmeldingen.
#      Mangler et system eller en ansvarlig, aabner bekraeftelsen ikke,
#      og beskeden siger hvilken funktionsplads det er. Det er bedre at
#      stoppe her end at sende noget af sted, ingen kan godkende.
#
# BioSap-Material-SystemApproval startes EFTER en lykket indsendelse. Den
# svarer med det samme og arbejder videre bagefter - en godkendelse kan
# tage dage, og appen maa ikke vente.
# ---------------------------------------------------------------------------
APPROVAL_ON = env.feature_on("material_approval")

RESOLVE_FLOW = "'BioSap-Material-ResolveApprovers'"
RESOLVE_OUT = "resolveoutput"
APPROVAL_FLOW = "'BioSap-Material-SystemApproval'"

APPROVERS = "colDomApprovers"
APPR_SCHEMA = {"Code": '""', "SystemNo": '""', "Approver": '""', "Error": '""'}
APPR_RAW = "varDomApprRaw"
APPR_MSG = "varDomApprMsg"
# Appens tilstand i App.OnStart, naar flaget er taendt.
APPR_STATE = f'Set({APPR_MSG}, "")'

# De strategiske raekker, Submit ville sende (VALID er domain_parts').
STRAT_ROWS = ('Filter(colDomRows, Status = "valid" && '
              + is_strategic("StrategicPart") + ")")
ROW_CODES = 'Coalesce(ObjectList, Coalesce(FunctionalLocation, ""))'
SUBMIT_CODES = f'Concat({STRAT_ROWS}, {ROW_CODES}, "{ol.SEP}")'
# En strategisk raekke UDEN objekt kan slet ikke slaas op.
NO_OBJECT = (f'CountRows(Filter({STRAT_ROWS}, '
             f'IsBlank(Trim({ROW_CODES})))) > 0')
BAD = f'Filter({APPROVERS}, !IsBlank(Trim(Coalesce(Error, ""))))'


def resolve_fx(codes):
    """Slaa system og systemansvarlig op for koderne i codes.

    Svaret lander i colDomApprovers. Fejler kaldet - flowet er ikke
    importeret, eller Power BI svarer ikke - staar grunden i
    varDomApprMsg, og Submit spaerrer paa den. Det er med vilje: uden et
    opslag ved appen ikke, om raekken KAN godkendes."""
    return (
        f'Set({APPR_MSG}, "");\n'
        f"{ol.clear_fx(APPROVERS)};\n"
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
        # Begge grene skal give det SAMME - IfError er et udtryk, ikke to
        # blokke (check_layout regel 32).
        "        true,\n"
        f'        Set({APPR_MSG}, "Could not look up the system managers: " & '
        "FirstError.Message);\n"
        "        false\n"
        "    )\n"
        ")"
    )


def submit_guard():
    """Submit-vagten (domain_parts.HOOKS["submit_guard"])."""
    blocked = (f"({NO_OBJECT} || CountRows({BAD}) > 0 || "
               f'!IsBlank(Trim(Coalesce({APPR_MSG}, ""))))')
    message = (
        "If(\n"
        f'    !IsBlank(Trim(Coalesce({APPR_MSG}, ""))), {APPR_MSG},\n'
        f'    {NO_OBJECT}, "A strategic row needs at least one functional '
        'location before it can be submitted.",\n'
        f'    "Cannot submit: " & First({BAD}).Error\n'
        ")")
    return (resolve_fx(SUBMIT_CODES), blocked, message)


def after_submit_fx():
    """Start systemgodkendelsen, naar indmeldingen har strategiske
    raekker. Raekkerne er hentet forfra (domain_parts' refresh), saa de
    staar med anmodningens nummer."""
    strat = ("CountRows(Filter(colDomRows, RequestNo = varDomRequestNo && "
             "Coalesce(ApprovalRequired, false))) > 0")
    return (
        "If(\n"
        f"    {strat},\n"
        "    IfError(\n"
        f"        {APPROVAL_FLOW}.Run(varDomRequestGuid),\n"
        '        Notify("The request was submitted, but the system approval '
        'could not be started: " & FirstError.Message, NotificationType.Warning)\n'
        "    )\n"
        ")"
    )


def _approver_line():
    """Linjen under objektlisten i popuppen: hvem godkendelsen vil spoerge.

    Kun raekkens EGNE koder - colDomApprovers kan ogsaa holde svaret fra
    Submit-opslaget, som daekker hele indmeldingen."""
    mine = (f"Filter({APPROVERS} As A, CountRows(Filter({POP}, "
            "Upper(Trim(Code)) = Upper(Trim(A.Code)))) > 0)")
    bad = f'Filter({mine}, !IsBlank(Trim(Coalesce(Error, ""))))'
    ok = f'Filter({mine}, !IsBlank(Trim(Coalesce(Approver, ""))))'
    text = (
        "With(\n"
        f"    {{ bad: {bad}, ok: {ok} }},\n"
        "    If(\n"
        f'        !IsBlank(Trim(Coalesce({APPR_MSG}, ""))), {APPR_MSG},\n'
        '        CountRows(bad) > 0, "Cannot be approved: " & First(bad).Error,\n'
        '        CountRows(ok) > 0,\n'
        '        "System approval: " & Concat(Distinct(ok, Approver & " (system " & '
        'SystemNo & ")"), Value, ", "),\n'
        '        ""\n'
        "    )\n"
        ")")
    seen = (f'CountRows({mine}) > 0 || '
            f'!IsBlank(Trim(Coalesce({APPR_MSG}, "")))')
    return text_ctrl("txtDomObjApprovers", text, size=12, color=C_MUTED,
                     height=18, wrap="false", visible=seen)


# ---------------------------------------------------------------------------
# TRINSTRIBEN (issue #204) - hvor langt er indmeldingen?
#
# Hubben har altid vist forloebet pr. anmodning; den, der UDFYLDER
# formularen, har aldrig haft det. Han saa en liste raekker og en
# Submit-knap, og foerst naar han trykkede, fik han at vide, at noget
# manglede. Striben er de samme tre trin FOER indsendelsen - og de samme
# tre knuder bliver forloebet EFTER den, saa billedet ikke skifter under
# brugeren.
#
# Hjaelpelinjen under striben siger praecis det, Submit ville sige: samme
# udtryk, samme beskeder. Delene staar i tools/stepper.py og er
# domaeneneutrale.
# ---------------------------------------------------------------------------
SUBMITTED = 'CountRows(Filter(colDomRows, Status = "submitted")) > 0'
DRAFTS = 'CountRows(Filter(colDomRows, Status = "draft"))'
VALID_N = 'CountRows(Filter(colDomRows, Status = "valid"))'
# Strategiske raekker UANSET status - ogsaa de indsendte, for efter Submit
# er der ingen "valid" raekker tilbage at taelle.
ANY_STRAT = ("CountRows(Filter(colDomRows, " + is_strategic("StrategicPart")
             + ")) > 0")
IDX_ST = 'Coalesce(varDomIdx.Status.Value, "")'
# Det, Submit ville spaerre paa (submit_guard).
BLOCKED = (f"{NO_OBJECT} || CountRows({BAD}) > 0 || "
           f'!IsBlank(Trim(Coalesce({APPR_MSG}, "")))')


def _steps():
    rows = (f'If(\n    {SUBMITTED}, "Done",\n'
            '    CountRows(colDomRows) > 0, "Done",\n    "Current"\n)')
    appr = (
        "If(\n"
        f"    !({ANY_STRAT}), \"Skipped\",\n"
        f"    {SUBMITTED},\n"
        "    If(\n"
        f'        {IDX_ST} = "UnderBehandling" || {IDX_ST} = "AfventerInfo", "Current",\n'
        f'        {IDX_ST} = "Indsendt" || {IDX_ST} = "KlarTilSAP" || '
        f'{IDX_ST} = "OprettetISAP", "Done",\n'
        '        "Pending"\n'
        "    ),\n"
        f"    {BLOCKED}, \"Current\",\n"
        '    "Done"\n'
        ")")
    done = (
        "If(\n"
        f"    {SUBMITTED},\n"
        "    If(\n"
        f'        {IDX_ST} = "OprettetISAP", "Done",\n'
        f'        {IDX_ST} = "KlarTilSAP", "Current",\n'
        '        "Pending"\n'
        "    ),\n"
        f"    {VALID_N} > 0 && !({BLOCKED}), \"Current\",\n"
        '    "Pending"\n'
        ")")
    return [
        (f'If({SUBMITTED}, "Submitted", "Rows")', rows),
        (f'If({SUBMITTED}, "System approval", "Objects & approvers")', appr),
        (f'If({SUBMITTED}, "Handed over", "Ready to submit")', done),
    ]


def _steps_hint():
    """Linjen under striben - de samme beskeder, Submit ville give."""
    return (
        "With(\n"
        f"    {{ v: {VALID_N}, d: {DRAFTS} }},\n"
        "    If(\n"
        f"        {SUBMITTED}, \"The request is with Master Data - you get an "
        'e-mail when it moves on.",\n'
        '        v = 0 && d = 0, "Add a row and save it to get started.",\n'
        f"        {NO_OBJECT}, \"A strategic row needs at least one functional "
        'location before it can be submitted.",\n'
        f'        CountRows({BAD}) > 0, "Cannot submit: " & First({BAD}).Error,\n'
        f'        !IsBlank(Trim(Coalesce({APPR_MSG}, ""))), {APPR_MSG},\n'
        '        d > 0 && v = 0, "Finish the draft row before submitting.",\n'
        '        "Ready: " & v & " row(s) will be submitted." & '
        'If(d > 0, " " & d & " draft row(s) stay as drafts.", "")\n'
        "    )\n"
        ")")


def build_steps():
    return st.strip("Dom", _steps(), hint=_steps_hint(),
                    label='"Progress of this request"')


# Godkendelsen er bag flaget: er det slukket, er appen praecis som foer -
# ingen opslag, ingen vagt paa Submit og intet flow-kald. Flaget staar i
# tools/canvas_apps.json (environments.<miljoe>.features.material_approval).
if APPROVAL_ON:
    dp.configure(submit_guard=submit_guard(), after_submit=after_submit_fx())
else:
    # Uden godkendelse stopper Submit stadig en strategisk raekke uden
    # funktionsplads (issue #228). Kravet stod foer ved Save row, men nu
    # tilfoejes funktionspladserne paa den gemte raekke.
    dp.configure(submit_guard=(
        "", NO_OBJECT,
        '"A strategic row needs at least one functional location before it can be submitted."'))
