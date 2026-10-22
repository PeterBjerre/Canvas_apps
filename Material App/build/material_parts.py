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
    [ Supplier    ][ Supp. part no][ Delivery time   ][ [Add text] ]
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
Kolonnen Remarks. Feltet er kun en knap (Add/Edit/View text) under sin
egen sektionsoverskrift, der aabner en popup med teksten (issue #279,
#429). Popuppens bund har Cancel og Save, som sidepanelets: Save laegger
teksten paa formularens raekke og lukker, Cancel og X lukker og
kasserer aendringerne siden popuppen blev aabnet. Teksten bliver staaende
i formularen, til hele raekken gemmes. Popuppen ligger OVER sidepanelet:
domain_app.build_screen laegger appens egne popupper efter panelet.

DOKUMENTER OG FUNKTIONSPLADSER STAAR PAA HVER SIN FANE
-----------------------------------------------------
Sidepanelet har fanerne Details, Objects og Documents. Dokumenterne ligger
i en mappe, der hedder raekkens noegle, og kraever en gemt raekke.
Funktionspladserne (Objects) er en del af formularen og gemmes med raekken
(tools/domain_objects.py, issue #485) - ogsaa paa en ny raekke.

No BOM Item og Recommended stock er fjernet (issue #228). Kolonnerne staar
uroert i SharePoint; appen skriver dem ikke laengere.

Created material no. er IKKE et felt her. Nummeret findes foerst, naar
materialet er oprettet i SAP - det udfyldes i Details bagefter.
"""
import display_text as dt
import domain_config as cfg
import domain_parts as dp
import env_config as env
import object_list as ol
import stepper as st
import admin_log as alog
import permissions as perm
import layout_tokens as lay
import mobile
from gen_screen import C_MUTED, C_INVALID_FG, C_MODAL_BG, C_PRIMARY_SOFT
import domain_objects as dobj
from build_helpers import (text_ctrl, group, button, text_input, card, grow, segmented,
                           section_header, tap_backdrop, text_min_height,
                           fit_button_width, text_px, popup_head, ICON_W)
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
# Teksten, som den stod, da popuppen blev aabnet - Cancel og X saetter den
# tilbage (issue #429). Og Save's lokale "Saving..."-tilstand.
PO_BEFORE = "varDomPoBefore"
PO_SAVING = "varDomPoSaving"
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

# OBJECT LIST (issue #204, #228 - formularens egen fane fra #485)
#
# Raekkens funktionspladser gemmes paa raekken som ObjectList (koderne),
# ObjectListJson (kode + beskrivelse) og FunctionalLocation (den foerste
# kode). Objects-fanen er faelles med Equipment og staar i
# tools/domain_objects.py: listen er formularens samling (colDomObjects),
# den fyldes, naar raekken hentes, og gemmes med Save - som felterne.
OBJECTS = dobj.OBJECTS
OBJ_SCHEMA = dobj.SCHEMA
# Object list-popuppens kladde og kandidater (issue #513) - samme skema.
OBJ_DRAFT = dobj.DRAFT
OBJ_CANDS = dobj.CANDS
# Det valgte soegeresultat paa fanen.
PICK = dobj.PICK
FL_MSG = dobj.FL_MSG
# Mindst 16 tegn foer der kan soeges OG foer der kan tilfoejes (Q11).
# "SSV13 HFC10AJ010" er praecis 16 - i praksis skal man kende hele koden.
MIN_FL_LEN = 16

# Appens egen tilstand i App.OnStart (domain_app.write_app).
EXTRA_STATE = (f"{dobj.STATE};\n"
               f"Set({PO_OPEN}, false);\n"
               f"Set({PO_SAVING}, false)")


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

# Prisen tastes som tekst ("dec", R2-010). Tekst, der ikke er et tal, ville
# stiltiende blive gemt som tom - den stoppes ogsaa paa en kladde (samme
# moenster som mp_parts._not_a_number).
PRICE = dp._var("Price")
PRICE_BAD = (f'!IsBlank(Trim(Coalesce({PRICE}, ""))) && '
             f'IsBlank(IfError({dp.dec_value(PRICE)}, Blank()))')
PRICE_MSG = "Price must be a number, not text."


def save_fx(status):
    """domain_parts' gem, plus Materials' egne krav: lagerniveauet og det
    erstattede materiale."""
    return dp.save_row_fx(status, required=_row_rules(),
                          always=[(MIN_MAX_BAD, MIN_MAX_MSG),
                                  (PRICE_BAD, PRICE_MSG)])


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
    ("conDomGridSupplier", ["Supplier", "SupplierPartNo", "DeliveringTime"], None),
    # Purchase order text - sin egen sektion med overskrift (issue #429)
    ("conDomGridPo", ["PO"], None),
    # Pris og enhed
    ("conDomGridPrice", ["Price", "PriceUnit", "StockUnit"], None),
    # Klassifikation og vedligeholdelsesordre
    ("conDomGridClass", ["StrategicPart", "WearPart", "MaintenanceOrderNo"], None),
]
FORM_ORDER = [k for _n, keys, _v in FORM_ROWS for k in keys]
# SEKTIONERNE (UX-review M2): overskriften staar foer den raekke, der
# aabner sektionen. Lager og erstatning hoerer til identifikationen.
SECTION_STARTS = {
    "conDomGridMain": ("Ident", "Identification"),
    "conDomGridMfr": ("Mfr", "Manufacturer and supplier"),
    "conDomGridPo": ("Po", "Purchase order text"),
    "conDomGridPrice": ("Price", "Price and classification"),
}
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


def _seg_cell(col, width=CELL_W):
    label = next(l for c, l, _k, _ch in dp.FIELDS if c == col)
    on = f"Coalesce({dp._var(col)}, false)"
    tip = SEG_TIPS[col]
    seg = segmented(f"conDom{col}Seg", [
        ("No", "No", f"!{on}", _seg_fx(col, False), tip),
        ("Yes", "Yes", on, _seg_fx(col, True), tip),
    ], display_mode=dp.DM_ROW, label=label, compact=True)
    return dp.grid_cell(f"conDom{col}", label, seg, width=width)


PO_TEXTS = ("Add text", "Edit text", "View text")
HAS_PO = f'!IsBlank(Trim(Coalesce({PO}, "")))'
# Knappen er saa hoej som et input. Overskriften staar over cellen
# (sektionen "Purchase order text", issue #429), saa cellen er kun knappen.
PO_BTN_H = 36
PO_CELL_H = PO_BTN_H


def _po_cell(width=CELL_W):
    """Purchase order text: kun knappen til popuppen (issue #279). Feltet
    med "No text yet" og den separate etiket er fjernet. Knappen er
    udfyldt, naar der ER en tekst. Overskriften er sektionens (#429).

    Aabningen gemmer teksten, som den staar, saa Cancel og X kan saette
    den tilbage."""
    w = max(fit_button_width(f'"{t}"', size=13) for t in PO_TEXTS)
    btn = button("btnDomPoText",
                 f'If({READ_ONLY}, "View text", If({HAS_PO}, "Edit text", "Add text"))',
                 f"Set({PO_BEFORE}, {PO});\nSet({PO_SAVING}, false);\n"
                 f"Set({PO_OPEN}, true)", width=w, height=PO_BTN_H,
                 accessible=('If(' + READ_ONLY + ', "View the purchase order text", '
                             'If(' + HAS_PO + ', "Edit the purchase order text", '
                             '"Add a purchase order text"))'),
                 tooltip='"Text for the purchase order"')
    btn.props["Size"] = "13"
    btn.props["LayoutMinWidth"] = str(w)
    btn.props["AlignInContainer"] = "AlignInContainer.Start"
    dp.pill(btn, HAS_PO)
    return group("conDomPo", [btn], direction="Vertical", gap=0, height=PO_CELL_H,
                 width=width, align_items="Start", justify="Start",
                 fill_portions="0", align_in_container="Start")


def _cell(key, width=CELL_W):
    if key == "TEXT":
        return dp.text_cell(width)
    if key == "PLANT":
        return dp.plant_cell(width)
    if key == "PO":
        return _po_cell(width)
    if key.startswith("SEG_"):
        return _seg_cell(key[4:], width)
    return dp.field_grid_cell(key, width=width, **CONDITIONAL.get(key, {}))


# UX-review F2: Save gemmer raekken (som kladde, til kravene er
# opfyldt). Funktionspladserne staar paa Objects-fanen og gemmes med
# raekken; dokumenterne paa Documents-fanen, naar raekken er gemt (#485).
EDITOR_HINT = ("Start with the four key fields and choose Save. Add functional "
               "locations on the Objects tab and documents on the Documents tab.")


def _editor_head(panel=False):
    """Sektionens overskrift - samme som Item Editor i VH-planen
    (build_helpers.section_header), med "* Required" efter titlen og en
    linje, der siger, hvordan formularen bruges.

    I sidepanelet staar "* Required" i panelets overskrift i stedet
    (domain_parts.required_legend, issue #431) - som i Equipment og MP."""
    head = section_header("conDomEditorHead", "Row details", None,
                          extra_left=[] if panel else list(dp.required_parts()))
    # Een linje paa en bred skaerm, to eller tre paa en smal - hoejden
    # foelger kortets bredde, saa intet klippes.
    need = text_px(EDITOR_HINT, 12, semibold=False)
    if getattr(cfg, "ROW_PANEL_ENABLED", False):
        # I sidepanelet er teksten bundet af panelets bredde: tael linjerne
        # (med 25 % luft til ordbrud), saa feltet aldrig faar en scrollbar.
        h = f"20 * RoundUp({need} * 1.25 / ({dp.PANEL_FORM_W}), 0) + 4"
    else:
        h = fits(dp.FORM_W, need, if_below("Tablet", "54", "36"), "18")
    hint = text_ctrl("txtDomEditorHint", f'"{EDITOR_HINT}"', size=12, color=C_MUTED,
                     height=h, wrap="true")
    return [head, hint]


def reset_fx():
    """Reset: KUN de ugemte aendringer kasseres - en gemt raekke faar sine
    gemte vaerdier igen, en ny raekke ryddes (domain_parts.reset_form_fx,
    issue #403). Rows og anmodningen roeres ikke, og panelet bliver
    aabent. Panelets Reset spoerger foerst, naar der er noget at kassere
    (domain_parts.reset_button / build_reset_confirm, issue #450)."""
    return dp.reset_form_fx()


# Funktionspladser paa en ny raekke er ogsaa noget at kassere.
DIRTY_NEW = (f"CountRows({OBJECTS}) > 0",)


def build_form(panel=False):
    dp.check_form_order(FORM_ORDER, SPECIAL, NOT_IN_GRID)
    form_width = dp.PANEL_FORM_W if panel else dp.FORM_W
    cell_width = dp.PANEL_CELL_W if panel else dp.CELL_W
    rows = []
    for name, keys, vis in FORM_ROWS:
        if name in SECTION_STARTS:
            key, title = SECTION_STARTS[name]
            rows.append(dp.form_section(key, title, first=not rows))
        row = dp.grid_row(name, [_cell(k, dp.panel_cell_w(k, cell_width)) for k in keys],
                          container_w=form_width, columns=2 if panel else None,
                  cell_width=cell_width)
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
        new_tooltip='"Undo the unsaved changes to this row - saved rows are not changed"')
    # Trinstriben lige under hovedet - foer felterne, saa den er det
    # foerste, man ser (kun naar godkendelsen er med).
    top = [build_steps()] if APPROVAL_ON else []
    return card("conDomFormCard", _editor_head(panel) + top + rows + dp.form_footer(buttons))


def editor_reset():
    """Reset staar i panelets bundbjaelke (tools/domain_app._row_editor),
    ikke i den scrollende formular."""
    return dp.reset_button(DIRTY_NEW)


def _objects_after():
    """Det, der sker efter en aendring af objektlisten (Apply selection i
    Object list og skraldespanden). En strategisk raekke: slaa systemet og
    dets ansvarlige op, saa initialerne staar under listen, mens der
    vaelges."""
    if not APPROVAL_ON:
        return ""
    return f"If(\n    {STRAT_FORM},\n{_indent(resolve_fx(ol.codes_fx(OBJECTS)), 4)}\n)"


def editor_panel_content(form, extras=()):
    """Fanerne Details, Objects og Documents - det faelles moenster i
    domain_parts.editor_tabs. Objects-fanen er faelles med Equipment
    (tools/domain_objects.py, issue #485)."""
    objects_body = dobj.tab_body(dp.EDITOR_TAB_BODY_H, min_len=MIN_FL_LEN, after=_objects_after(),
                                 extra=([_approver_line()] if APPROVAL_ON else ()))
    return dp.editor_tabs(form, extras, objects=[objects_body],
                          documents=[dp.docs_tab_body()], open_objects=dobj.open_tab_fx())


# ---------------------------------------------------------------------------
# Purchase order text - popuppen
# ---------------------------------------------------------------------------
PO_W = "Min(640, App.Width - 32)"


# Bundens knapper: Cancel og Save til hoejre, i sidepanelets raekkefoelge,
# hoejde og mellemrum (build_helpers.editor_footer). Save er saa bred som
# den laengste tekst, "Saving...", plus ikonet - saa den ikke hopper.
PO_FOOT_GAP = 8
PO_CANCEL_W = fit_button_width('"Cancel"')
PO_SAVE_W = max(fit_button_width(f'"{t}"') for t in ("Save", "Saving...")) + ICON_W + 8
PO_BUSY_DM = f"If({PO_SAVING}, DisplayMode.Disabled, DisplayMode.Edit)"


def po_cancel_fx():
    """Cancel og X: teksten tilbage til den, popuppen blev aabnet med, og
    feltet nulstilles (ogsaa det, der var skrevet uden at OnChange naaede
    at koere). Saa lukkes popuppen."""
    return (f"Set({PO}, {PO_BEFORE});\n"
            "Reset(inpDomPoText);\n"
            f"Set({PO_OPEN}, false)")


def po_save_fx():
    """Save: teksten paa formularens raekke og luk. Intet netvaerkskald -
    teksten gemmes med hele raekken (Save i sidepanelet). Knappen er slukket
    og siger "Saving...", mens det sker. Feltets tekst laeses direkte, saa
    intet gaar tabt, hvis OnChange ikke naaede at koere."""
    return (f"Set({PO_SAVING}, true);\n"
            f"If(!{READ_ONLY}, Set({PO}, inpDomPoText.Text));\n"
            f"Set({PO_BEFORE}, {PO});\n"
            f"Set({PO_OPEN}, false);\n"
            f"Set({PO_SAVING}, false)")


def _po_footer():
    cancel = button("btnDomPoCancel", '"Cancel"', po_cancel_fx(),
                    width=PO_CANCEL_W, height=lay.HIT_TOUCH, display_mode=PO_BUSY_DM,
                    accessible='"Cancel - close without applying the changes"',
                    tooltip='"Close without applying the changes"')
    save = button("btnDomPoSave", f'If({PO_SAVING}, "Saving...", "Save")', po_save_fx(),
                  primary=True, width=PO_SAVE_W, height=lay.HIT_TOUCH,
                  display_mode=(f"If({PO_SAVING} || {READ_ONLY}, DisplayMode.Disabled, "
                                "DisplayMode.Edit)"),
                  icon='"Save"', tooltip='"Apply the text to this row and close"')
    save.props["AccessibleLabel"] = "Self.Text"
    # Ikonet viger for "Saving...", som paa sidepanelets Save (#420).
    save.props["Layout"] = f"If({PO_SAVING}, ButtonLayout.TextOnly, {save.props['Layout']})"
    for b in (cancel, save):
        b.props["AlignInContainer"] = "AlignInContainer.Start"
        b.props["LayoutMinWidth"] = b.props["Width"]
    return group("conDomPoFooter", [cancel, save], direction="Horizontal",
                 gap=PO_FOOT_GAP, height=lay.HIT_TOUCH, align_items="Start",
                 justify="End")


def _po_popup():
    """Teksten skrives i formularens variabel og gemmes med raekken.
    Bunden er fast under feltet: Cancel og Save (issue #429). X oeverst til
    hoejre goer det samme som Cancel. Et tryk ved siden af lukker ikke."""
    vis = f"IfError({PO_OPEN}, false)"
    back = tap_backdrop("conDomPoBackdrop", vis, "false")
    title = grow(text_ctrl("txtDomPoH", '"Purchase order text"',
                           size=lay.SIZE_CARD_TITLE, weight="Semibold",
                           height=text_min_height(lay.SIZE_CARD_TITLE), wrap="false"))
    # X oeverst til hoejre (issue #343) - en anden vej til Cancel (#429).
    head = popup_head("conDomPoHead", title, "btnDomPoClose", po_cancel_fx(),
                      accessible='"Close without applying the changes"', mode=PO_BUSY_DM)
    hint = text_ctrl(
        "txtDomPoHint",
        f'If({READ_ONLY}, "Read only - this row cannot be changed.", '
        '"Save applies the text to this row. It is stored when you save the row.")',
        size=12, color=C_MUTED, height=if_below("Tablet", "36", "18"), wrap="true")
    # Feltet giver plads til hoved, linje og den faste bund paa en lille skaerm.
    box = text_input("inpDomPoText", PO, height="Min(220, App.Height - 280)",
                     display_mode=dp.DM_ROW, ttype="Multiline",
                     placeholder='"Text for the purchase order"',
                     label='"Purchase order text"',
                     onchange=f"Set({PO}, Self.Text)")
    modal = group("conDomPoModal", [head, hint, box, _po_footer()], direction="Vertical",
                  gap=12, fill=C_MODAL_BG, border_color=C_PRIMARY_SOFT,
                  radius=lay.RADIUS_MODAL, pad=(18, 18, 18, 18), width=PO_W,
                  drop_shadow="ExtraBold", visible=vis)
    modal.props["X"] = dp.MODAL_X
    modal.props["Y"] = dp.MODAL_Y
    # Paa en telefon: (naesten) hele bredden, oeverst (issue #508).
    mobile.mobile_popup(modal, top=True)
    return [back, modal]


def build_popups():
    """Materials' egne popupper (domain_app.build_screen): indkoebsteksten
    og Objects-fanens Object list (issue #513) - [sloer, popup] hver.
    Objektlisten er Objects-fanen i sidepanelet (#485), og Reset's
    bekraeftelse er den faelles (domain_parts.build_reset_confirm, issue
    #450)."""
    return _po_popup() + dobj.build_popup(_objects_after())


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


def row_actions():
    """De faelles raekkeikoner (domain_parts.standard_row_actions, issue
    #485): Edit, Documents, Objects, Copy og Delete. Antallet af dokumenter
    og funktionspladser staar i ikonernes tooltip."""
    return dp.standard_row_actions(
        docs_fx=(dp.load_row_fx() + f';\nSet({cfg.ROW_EDITOR_TAB_VAR}, "Documents");\n'
                 + dp.open_active_docs_fx()),
        docs_n="ThisItem.FileCount",
        objects_fx=dobj.open_row_fx(cfg.ROW_EDITOR_TAB_VAR),
        objects_n=ROW_OBJ_N)


# Soegefeltet paa listen er saa bredt, at hele pladsholderen staar (issue
# #513) - foer 240 px, og teksten endte med "...".
SEARCH_PLACEHOLDER = "Search FL, supplier, part no., material"


def build_rows():
    return dp.build_list(SLOTS, "STATUS", SEARCH_PLACEHOLDER,
                         search_w=dp.search_width(SEARCH_PLACEHOLDER))


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
DET_ROW = "LookUp(colDomRows, RowId = varDomActiveRowId)"
# Naar ruden skifter raekke, skal feltet vise DEN raekkes nummer.
DETAILS_SYNC = (f'Set({CREATED_VAR}, Coalesce({DET_ROW}.CreatedMaterialNo, ""));\n'
                f"Reset({CREATED_IN})")
# HVEM MAA (R2-011): rekvirenten paa sin egen raekke og en admin - og kun
# paa en indsendt raekke. Reglen staar baade i UI'et (CREATED_EDIT) og i
# selve handlingen (_save_created_fx), og aendringen logges i
# MD_ApprovalLog som andre admin-aendringer (tools/admin_log.py) - samme
# moenster som Measuring Points mp_parts._save_mpno_fx.
CREATED_MAY = (f'(Coalesce({DET_ROW}.Status, "") = "submitted" && '
               f'({perm.IS_ADMIN} || {perm.is_owner(DET_ROW + ".RequesterEmail", "varDomMe")}))')
CREATED_EDIT = f"If({CREATED_MAY}, DisplayMode.Edit, DisplayMode.Disabled)"


def _save_created_fx():
    new_no = f'Trim(Coalesce({CREATED_VAR}, ""))'
    log = alog.write(
        "varDomRequestGuid", f'Coalesce({DET_ROW}.RequestNo, "")', alog.EDIT,
        f'"Created material no. for " & Coalesce({DET_ROW}.ItemKey, "") & '
        f'": " & Coalesce({DET_ROW}.CreatedMaterialNo, "(blank)") & " '
        f'{alog.ARROW} " & {new_no}', 8)
    return (
        "If(\n"
        f"    !{CREATED_MAY},\n"
        '    Notify("Only the requester and admins can fill in the material no.",\n'
        "        NotificationType.Warning),\n"
        "\n"
        "    IfError(\n"
        f"    Patch(\n        {cfg.L_ROWS},\n"
        f"        LookUp({cfg.L_ROWS}, ID = varDomActiveRowId),\n"
        f"        {{ CreatedMaterialNo: {new_no} }}\n"
        "    );\n"
        + log + ";\n"
        + dp.refresh_rows_fx(4) + ";\n"
        '    Notify("Created material no. saved.", NotificationType.Success),\n'
        "\n"
        '    Notify("Save failed: " & FirstError.Message, NotificationType.Error)\n'
        "    )\n"
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
dp.configure(
    # Storage bin foreslaas som "X", naar formularen ryddes.
    field_defaults={"StorageBin": '"X"'},
    # Objects-fanens liste (tools/domain_objects.py, issue #485): fyldt fra
    # raekken, naar den hentes - ogsaa en kopi, der hentes efter Copy - og
    # ryddet med formularen.
    clear_extra=dobj.clear_extra(),
    load_extra=dobj.load_extra(),
    # Gem: koderne, JSON'en og FL-kolonnen som den FOERSTE kode.
    # ApprovalRequired er raekkens eget svar paa "skal den godkendes?".
    # Den skrives ved HVER gemning, ogsaa som kladde: det er data, ikke
    # godkendelse, og flowet filtrerer paa den.
    extra_patch=dobj.extra_patch() + [("ApprovalRequired", STRAT_FORM)],
    # Objektlisten i admin-loggen og i Reset's "ugemte aendringer".
    extra_diff=dobj.extra_diff(),
    # Grupperet detaljerude, og materialenummeret under felterne.
    details_groups=DETAILS_GROUPS,
    details_rows=details_rows,
    details_open=DETAILS_SYNC,
    details_nav=DETAILS_SYNC,
)
# Raekkens knapper bygges af hent/kopier/detaljer OVENFOR - derfor efter
# den foerste configure.
dp.configure(row_actions=row_actions())
# Paa en telefon (issue #508): producent/leverandoer og pris/klassifikation
# er klappet sammen - ingen af dem har et kraevet felt. En pris, der ikke
# er et tal, holder sin sektion aaben.
dp.configure(mobile_folds={"Mfr": (None, None), "Price": (PRICE_BAD, None)})


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
    """Linjen under objektlisten paa Objects-fanen: hvem godkendelsen vil spoerge.

    Kun raekkens EGNE koder - colDomApprovers kan ogsaa holde svaret fra
    Submit-opslaget, som daekker hele indmeldingen."""
    mine = (f"Filter({APPROVERS} As A, CountRows(Filter({OBJECTS}, "
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
        '        "Ready: " & ' + dt.plural("v", "row") + ' & " will be submitted." & '
        'If(d > 0, " " & ' + dt.plural("d", "draft row") + ' & " stay as drafts.", "")\n'
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
