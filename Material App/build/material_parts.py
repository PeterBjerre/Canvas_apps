# -*- coding: utf-8 -*-
"""
Materials' EGNE dele: formularen og listen over gemte raekker (issue #67).

Skaermen er tegnet efter materials.png og "saved row.png" i app-mappen -
HTML-projektets reservedelsformular. De to dele her erstatter
domain_parts.build_form(), build_rows() og build_submit() i DENNE app;
Equipment bruger stadig de faelles. Alt andet - gem, hent, slet, kopier,
dokumentpopuppen, detaljepopuppen, indsend og bekraeftelsen - er de faelles
dele i tools/domain_parts.py, uaendret. Se SKILL.md, "Hvordan en af dem
afviger".

FORMULAREN
----------
    Spare Parts Form  * Required                    [No BOM Item: OFF]
    [ FL          ][ Manufacturer ][ Model number ][ Manuf. part no.  ]
    [ Description ][ Documentation][ Stock unit   ][ Price            ]
    [ Price unit  ][ Delivery time][ Rec. stock   ][ Supplier         ]
    [ Supp. part  ][ Strategic    ][ Wear part    ][ Plant            ]
    [ Long text                                                       ]
    (Plant: X) (Row status: ...)  [Delete row][Save draft][Save row][Reset form]

Ingen sektionsoverskrifter. Gitteret har fire kolonner paa en bred skaerm,
to paa en tablet og een paa en telefon - maalt paa KORTETS bredde, ikke paa
App.Width (layout_tokens.fits).

NO BOM ITEM
-----------
En knap i formularens hoved. Staar den til, er raekken ikke en BOM-post:
funktionspladsen ryddes og deaktiveres, dens stjerne forsvinder, og Save
row kraever den ikke. Vaerdien er kolonnen NoBomItem (domain_config), saa
gem, hent, kopier og detaljer tager den med af sig selv.
"""
import domain_config as cfg
import domain_parts as dp
from gen_screen import (Ctrl, C_MUTED, C_TITLE, C_PRIMARY, C_WHITE,
                        C_CARD_BORDER, C_TRANSPARENT, C_MUTED_BG, C_REQUIRED,
                        C_NEUTRAL_BG, C_NEUTRAL_FG, C_VALID_FG, C_VALID_BG,
                        C_INFO_FG, C_INFO_BG, C_WARN_FG, C_WARN_BG)
from layout_tokens import fits, SCROLLBAR_W
from build_helpers import (text_ctrl, group, button, text_input, card, field_cell,
                           grow, flow_row, themed_dropdown, fit_button_width, label_px, text_px,
                           with_busy, ICON_SAVE, ICON_SUBMIT, ICON_W)

att = dp.att

# Kortets indholdsbredde - den samme, domain_parts regner formularen af.
FORM_W = dp.FORM_W

# Det aktive raekke-opslag og visningstilstandene.
ACTIVE = dp.ACTIVE
DM_ROW = dp.DM_ROW
DM_SEL = dp.DM_SEL
REQUIRED = dp.REQUIRED

NOBOM = dp._var("NoBomItem")
FL_VAR = dp._var(cfg.FL_FIELD)
# Compact eller All columns i listen. Sat i App.OnStart.
ALL_COLS = "varDomAllCols"


# ---------------------------------------------------------------------------
# Gitteret
# ---------------------------------------------------------------------------
GAP = 20
# Mindste cellebredde for fire og for to kolonner. Graenserne regnes af
# dem - ikke skrevet af - saa en anden mindstebredde flytter dem selv.
CELL_MIN_4 = 200
CELL_MIN_2 = 220
NEED_4 = 4 * CELL_MIN_4 + 3 * GAP
NEED_2 = 2 * CELL_MIN_2 + GAP
COLS_MAX = 4

CELL_W = fits(FORM_W, NEED_4,
              fits(FORM_W, NEED_2, FORM_W, f"(({FORM_W}) - {GAP}) / 2"),
              f"(({FORM_W}) - {3 * GAP}) / 4")


def _line_h(hs):
    """Den hoejeste af cellerne paa en linje - tal, hvis de alle er tal."""
    if all(isinstance(h, (int, float)) for h in hs):
        return str(max(hs))
    return hs[0] if len(hs) == 1 else "Max(%s)" % ", ".join("(%s)" % h for h in hs)


def _chunk_h(heights, k):
    """Hoejden af en raekke, der ombryder til linjer a k celler."""
    lines = [heights[i:i + k] for i in range(0, len(heights), k)]
    return " + ".join("(%s)" % _line_h(l) for l in lines) + " + %d" % (GAP * (len(lines) - 1))


def grid_row(name, cells):
    """Op til fire celler, der ombryder til to og een kolonne.

    Hoejden regnes for hver af de tre tilstande af cellernes egne hoejder
    - check_layout regel 4c spiller ombrydningen og efterproever den."""
    hs = [c.h for c in cells]
    h = fits(FORM_W, NEED_4,
             fits(FORM_W, NEED_2, _chunk_h(hs, 1), _chunk_h(hs, 2)),
             _chunk_h(hs, 4))
    return group(name, cells, direction="Horizontal", gap=GAP, height=h, wrap="true")


# ---------------------------------------------------------------------------
# Cellerne
# ---------------------------------------------------------------------------
def _cell(name, label, ctrl, required=False):
    return field_cell(name, label, ctrl, required=required, width=CELL_W,
                      fill_portions_formula="0")


def _fl_cell():
    """Functional Location - EEN celle: soegningen over dropdownen.

    Stjernen staar kun, naar feltet er kraevet: No BOM Item slaar kravet
    fra, og saa ville en stjerne paa et deaktiveret felt lyve."""
    search, drop = dp.build_fl_controls(
        CELL_W, lock=NOBOM, required_formula=f"{REQUIRED} && !{NOBOM}")
    label = "Functional location"
    lbl = text_ctrl("conDomFlLbl", f'"{label}"', size=13, weight="Semibold",
                    height=20, width=f"Min({label_px(label)}, ({CELL_W}) - 13)",
                    wrap="false")
    star = text_ctrl("conDomFlStar", '"*"', size=13, color=C_REQUIRED,
                     weight="Semibold", height=20, width=10, wrap="false",
                     accessible='"Required"', visible=f"!{NOBOM}")
    head = group("conDomFlLblRow", [lbl, star], direction="Horizontal", gap=3,
                 height=20, align_items="Center")
    return group("conDomFl", [head, search, drop], direction="Vertical", gap=6,
                 width=CELL_W, align_in_container="Start")


def open_active_docs_fx():
    """Formularens Documents-knap: dokumentpopuppen for den AABNE raekke.

    Samme som raekkens Docs-knap (domain_parts.open_docs_fx), bare med den
    aktive raekke i stedet for ThisItem. Popuppen aabner kun her og paa
    Docs - aldrig af sig selv: varDomDocsId er Blank fra OnStart."""
    return (
        "Set(varDomDocsId, varDomActiveRowId);\n"
        "If(\n"
        f"    Coalesce({ACTIVE}.FileCount, 0) > 0 &&\n"
        "    CountRows(Filter(colDomAttachments, RowId = varDomActiveRowId)) = 0,\n"
        + att.refresh_fx(4) + "\n"
        ")"
    )


def _docs_cell():
    """Documentation: hvor mange dokumenter raekken har, og en knap til
    den eksisterende dokumentpopup. Dokumenterne ligger i en mappe, der
    hedder raekkens noegle, saa knappen virker foerst efter Save."""
    info = grow(text_input(
        "txtDomDocsInfo",
        ('If(IsBlank(varDomActiveRowId), "Save the row first", '
         f'Text(Coalesce({ACTIVE}.FileCount, 0)) & " document(s)")'),
        display_mode="DisplayMode.View", label='"Documents on this row"'))
    text = '"Documents"'
    btn = button("btnDomDocs", text, open_active_docs_fx(),
                 width=fit_button_width(text), display_mode=DM_SEL,
                 accessible='"Open the documents for this row"')
    btn.props["LayoutMinWidth"] = btn.props["Width"]
    row = group("conDomDocsRow", [info, btn], direction="Horizontal", gap=8,
                height=36, align_items="Center", width=CELL_W)
    return _cell("conDomDocs", "Documentation", row)


# Skaermens raekkefoelge - materials.png's. TEXT, DOCS og PLANT er de tre
# felter, der ikke er en linje i SECTIONS.
FORM_ORDER = ["FL", "Manufacturer", "ModelNumber", "ManufacturerPartNo",
              "TEXT", "DOCS", "StockUnit", "Price",
              "PriceUnit", "DeliveringTime", "RecommendedStock", "Supplier",
              "SupplierPartNo", "StrategicPart", "WearPart", "PLANT"]
# Felter, der ikke er en celle i gitteret: NoBomItem er knappen i hovedet,
# LongText har hele bredden under gitteret.
NOT_IN_GRID = {"NoBomItem", "LongText"}


def _check_order():
    """Et felt i SECTIONS, der ikke er i FORM_ORDER, ville ellers bare
    mangle paa skaermen - uden at noget sagde det."""
    want = {c for c, _l, _k, _ch in dp.FIELDS} - NOT_IN_GRID - {cfg.FL_FIELD}
    have = set(FORM_ORDER) - {"FL", "TEXT", "DOCS", "PLANT"}
    if want != have or len(FORM_ORDER) != len(set(FORM_ORDER)):
        raise SystemExit("material_parts.FORM_ORDER passer ikke til SECTIONS:\n"
                         f"  mangler: {sorted(want - have)}\n"
                         f"  ukendte: {sorted(have - want)}")


def _grid_cells():
    by_col = {c: (l, k, ch) for c, l, k, ch in dp.FIELDS}
    cells = []
    for key in FORM_ORDER:
        if key == "FL":
            cells.append(_fl_cell())
        elif key == "TEXT":
            cells.append(_cell("conDomText", cfg.TEXT_LABEL,
                               text_input("inpDomText", "varDomFText", max_length=40,
                                          placeholder=cfg.TEXT_PLACEHOLDER,
                                          required_formula=REQUIRED, display_mode=DM_ROW,
                                          onchange="Set(varDomFText, Self.Text)"),
                               required=True))
        elif key == "DOCS":
            cells.append(_docs_cell())
        elif key == "PLANT":
            cells.append(_cell("conDomPlant", cfg.PLANT_LABEL, dp._plant_dropdown(),
                               required=True))
        else:
            label, kind, choices = by_col[key]
            cells.append(_cell(f"con{key}", label, dp._input_for(key, kind, choices)))
    return cells


# ---------------------------------------------------------------------------
# Knapper: saa brede som deres tekst, og aldrig klippet
# ---------------------------------------------------------------------------
def _fit(btn, icon=False, size=14):
    """Bredden af knappens LAENGSTE tekst (+ ikon), laast som mindstebredde.

    fit_button_width kraever en litteral: en knap, hvis tekst skifter, skal
    have sin LAENGSTE tekst, naar den kaldes - og faa formlen bagefter."""
    w = fit_button_width(btn.props["Text"], size=size, min_w=0) + (ICON_W if icon else 0)
    btn.props["Width"] = str(w)
    btn.props["LayoutMinWidth"] = str(w)
    return btn


def _pill(btn, on):
    """En knap, der er TIL eller FRA: udfyldt, naar den er til."""
    for k in ("TopLeft", "TopRight", "BottomLeft", "BottomRight"):
        btn.props["Radius" + k] = "16"
    btn.props["Appearance"] = (f"If({on}, ButtonAppearance.Primary, "
                               "ButtonAppearance.Outline)")
    btn.props["BasePaletteColor"] = C_PRIMARY
    btn.props["Color"] = f"If({on}, {C_WHITE}, {C_TITLE})"
    btn.props["BorderColor"] = f"If({on}, {C_PRIMARY}, {C_CARD_BORDER})"
    return btn


def toggle_nobom_fx():
    """No BOM Item til/fra. TIL rydder funktionspladsen - soegningen, dens
    svar og det valgte - saa en No BOM-raekke aldrig gemmes med en."""
    return (
        f"Set({NOBOM}, !{NOBOM});\n"
        "If(\n"
        f"    {NOBOM},\n"
        f'    Set({FL_VAR}, "");\n'
        f'    Set({dp.FL_QUERY_VAR}, "");\n'
        "    Reset(txtDomFlQuery);\n"
        "    Reset(drpDomFl);\n"
        '    Set(varDomFlMsg, "No BOM item - a functional location is not required."),\n'
        '    Set(varDomFlMsg, "")\n'
        ")"
    )


def _nobom_button():
    # OFF er den laengste af de to tekster - bredden regnes af den.
    off, on = "No BOM Item: OFF", "No BOM Item: ON"
    b = button("btnDomNoBom", f'"{off}"', toggle_nobom_fx(), height=32,
               display_mode=DM_ROW,
               accessible=f'If({NOBOM}, "No BOM item: on", "No BOM item: off")')
    b.props["Size"] = "13"
    _fit(b, size=13)
    b.props["Text"] = f'If({NOBOM}, "{on}", "{off}")'
    return _pill(b, NOBOM)


# ---------------------------------------------------------------------------
# Formularen
# ---------------------------------------------------------------------------
def save_fx(status):
    """domain_parts' gem, plus Materials' eget krav: en faerdig raekke skal
    have en funktionsplads - medmindre den er No BOM."""
    need_fl = (f'!{NOBOM} && IsBlank(Trim(Coalesce({FL_VAR}, "")))',
               "Functional location is required - or turn on No BOM Item.")
    return dp.save_row_fx(status, required=[need_fl])


def build_form():
    _check_order()

    title_txt = "Spare Parts Form"
    title = text_ctrl("txtDomFormH", f'"{title_txt}"', size=17, weight="Semibold",
                      height=26, width=text_px(title_txt, 17), wrap="false")
    star = text_ctrl("txtDomFormReqStar", '"*"', size=12, color=C_REQUIRED,
                     weight="Semibold", height=18, width=8, wrap="false",
                     accessible='"Required"')
    legend = text_ctrl("txtDomFormReq", '"Required"', size=12, color=C_MUTED,
                       height=18, width=text_px("Required", 12, semibold=False),
                       wrap="false")
    left_w = sum(int(c.props["Width"]) for c in (title, star, legend)) + 2 * 4
    left = group("conDomFormTitle", [title, star, legend], direction="Horizontal",
                 gap=4, height=26, align_items="Center")
    head = flow_row("conDomFormHead", [left, _nobom_button()], FORM_W, gap=12,
                    flex=left, flex_min=left_w)

    cells = _grid_cells()
    rows = [grid_row(f"conDomGrid{i // COLS_MAX}", cells[i:i + COLS_MAX])
            for i in range(0, len(cells), COLS_MAX)]
    # Soegningens svar under den foerste raekke - den med FL i.
    rows.insert(1, dp.build_fl_msg())

    col, label, kind, choices = next(f for f in dp.FIELDS if f[0] == "LongText")
    long_text = field_cell(f"con{col}", label,
                           text_input(f"inp{col}", dp._var(col), height=72,
                                      display_mode=DM_ROW, ttype="Multiline",
                                      onchange=f"Set({dp._var(col)}, Self.Text)"),
                           width=FORM_W, fill_portions_formula="0")

    # Plant og raekkens tilstand som to piller til venstre - knapperne til
    # hoejre. Tilstanden er den tekst, der foer stod under "Row".
    plant = _meta_pill("txtDomFormPlant", '"Plant: " & Coalesce(varDomFPlant, "-")', 130)
    state = _meta_pill(
        "txtDomFormState",
        ('If(\n'
         '    IsBlank(varDomActiveRowId),\n'
         '    "Row status: New row - not saved yet",\n'
         '    "Row status: " & Coalesce(' + ACTIVE + '.ItemKey, "row " & varDomActiveRowId) &\n'
         '        " (" & varDomRowStatus & ")"\n'
         ')'), 290)
    meta_w = 130 + 8 + 290
    meta = group("conDomFormMeta", [plant, state], direction="Horizontal", gap=8,
                 height=28, align_items="Center")

    delete = _fit(button("btnDomDelete", '"Delete row"', dp.delete_row_fx(),
                         danger=True, display_mode=DM_SEL))
    draft = _fit(button("btnDomSaveDraft", '"Save draft"',
                        with_busy(dp.SAVING_VAR, save_fx("draft")),
                        display_mode=DM_ROW, icon=ICON_SAVE), icon=True)
    save = _fit(button("btnDomSave", '"Save row"',
                       with_busy(dp.SAVING_VAR, save_fx("valid")),
                       primary=True, display_mode=DM_ROW, icon=ICON_SAVE), icon=True)
    reset = _fit(button("btnDomNew", '"Reset form"', dp.clear_form_fx()))
    actions = flow_row("conDomFormActions", [meta, delete, draft, save, reset],
                       FORM_W, gap=8, flex=meta, flex_min=meta_w)

    info = text_ctrl("txtDomFormInfo", "varDomInfo", size=12, color=C_MUTED,
                     height=18, wrap="false")
    return card("conDomFormCard", [head] + rows + [long_text, actions, info])


def _meta_pill(name, text, width):
    return text_ctrl(name, text, size=12, color=C_MUTED, height=28, width=width,
                     wrap="false",
                     extra={"Fill": C_NEUTRAL_BG, "VerticalAlign": "VerticalAlign.Middle",
                            "PaddingLeft": "10", "PaddingRight": "10",
                            "RadiusBottomLeft": "8", "RadiusBottomRight": "8",
                            "RadiusTopLeft": "8", "RadiusTopRight": "8"})


# ---------------------------------------------------------------------------
# Listen
# ---------------------------------------------------------------------------
# "All plants"/"All status" er LOKALE ord: de betyder "filtrer ikke" og
# staar ingen steder i SharePoint. De tre andre statusvaerdier ER lagrede
# vaerdier i colDomRows.Status og maa ikke oversaettes.
ALL_STATUS = "All status"
ALL_PLANTS = "All plants"
SEARCH = " || ".join(f"Trim(txtDomSearch.Text) in {c}" for c in cfg.SEARCH_FIELDS)
SCOPE = (
    "Filter(\n"
    "    colDomRows,\n"
    f"    (IsBlank(Trim(txtDomSearch.Text)) || {SEARCH}),\n"
    f'    (drpDomStatusFilter.Selected.Value = "{ALL_STATUS}" ||\n'
    "     Status = drpDomStatusFilter.Selected.Value),\n"
    f'    (drpDomPlantFilter.Selected.Value = "{ALL_PLANTS}" ||\n'
    "     Plant = drpDomPlantFilter.Selected.Value)\n"
    ")"
)
PLANT_ITEMS = (
    "Ungroup(\n"
    f'    Table({{ Rows: Table({{ Value: "{ALL_PLANTS}" }}) }},\n'
    "          { Rows: Sort(Distinct(Filter(colDomRows, !IsBlank(Plant)), Plant), Value) }),\n"
    "    Rows\n"
    ")"
)

ROW_H = dp.ROW_H
GAL_ROWS = dp.GAL_ROWS
T_GAP = 6
BTN_H = dp.ROW_BTN_H
BTN_GAP = dp.ROW_BTN_GAP
HEAD_SIZE = 11
CELL_PAD = 10


def _col_w(header, min_w):
    """Saa bred, at overskriften aldrig klippes - og mindst min_w.

    label_px er Segoe UI's egne tegnbredder (build_helpers). text_px er et
    skoen, der med vilje rammer for bredt; paa sytten overskrifter blev det
    til flere hundrede pixels, og Compact kunne ikke staa uden scroll paa en
    1366-skaerm. 4 px oven i er sikkerheden."""
    return max(min_w, label_px(header, HEAD_SIZE) + 2 * CELL_PAD + 4)


def _num(col):
    return f'If(IsBlank(ThisItem.{col}), "", Text(ThisItem.{col}))'


# De to visninger, som issue #67 skriver dem: Compact og All columns.
#
# EEN RAEKKE, FLERE PLADSER
# -------------------------
# Kolonnerne staar i forskellig raekkefoelge i de to visninger
# (beskrivelsen er nr. 3 i Compact og nr. 6 i All). En celle kan ikke
# flytte sig i et galleri, men dens INDHOLD kan: hver plads viser een
# kolonne i Compact og en (evt. anden) i All. Saa er der ingen celle to
# gange, og overskriften skifter paa samme maade.
#
# (overskrift, udtryk, mindstebredde) - None = pladsen er tom i visningen.
DESC = (cfg.TEXT_LABEL.upper(),
        f'If(IsBlank(Trim(ThisItem.{cfg.C_TEXT})), "(no text)", ThisItem.{cfg.C_TEXT})', 150)
FL_C = ("FUNCTIONAL LOCATION",
        f'If(ThisItem.NoBomItem, "No BOM item", ThisItem.{cfg.FL_FIELD})', 150)
MFR = ("MANUFACTURER", "ThisItem.Manufacturer", 110)
MODEL = ("MODEL NUMBER", "ThisItem.ModelNumber", 110)
MPN = ("MANUFACTURER PART NO.", "ThisItem.ManufacturerPartNo", 150)
SUPP = ("SUPPLIER", "ThisItem.Supplier", 100)
DOCS = ("DOCUMENTATION",
        'If(ThisItem.FileCount > 0, Text(ThisItem.FileCount) & " file(s)", "-")', 110)
SLOTS = [
    # (Compact, All)
    (FL_C, FL_C),
    (DESC, MFR),
    (MFR, MODEL),
    (MPN, MPN),
    (SUPP, DESC),
    (None, DOCS),
    (None, ("STOCK UNIT", "ThisItem.StockUnit", 90)),
    (None, ("PRICE", _num("Price"), 80)),
    (None, ("PRICE UNIT", "ThisItem.PriceUnit", 90)),
    (None, ("DELIVERING TIME", _num("DeliveringTime"), 110)),
    (None, ("RECOMMENDED STOCK", _num("RecommendedStock"), 130)),
    (None, SUPP),
    (None, ("SUPPLIER'S PART NO.", "ThisItem.SupplierPartNo", 130)),
    (None, ("STRATEGIC PART", "ThisItem.StrategicPart", 100)),
    (None, ("WEAR PART", "ThisItem.WearPart", 90)),
]
STATUS_W = 90

# Knapperne. Details og Docs staar i DETAILS-kolonnen i Compact; i All
# columns er der ingen DETAILS-kolonne, og saa er de de foerste af
# handlingerne - overskriften "ACTIONS" flytter hen over dem.
DETAIL_BTNS = [("btnDomRowDetails", '"Details"'), ("btnDomRowDocs", '"Docs"')]
ACTION_BTNS = [("btnDomRowOpen", '"Edit"'), ("btnDomRowCopy", '"Copy"'),
               ("btnDomRowDelete", '"Delete"')]


# Bredderne er domain_parts.ROW_BTN - de er afproevet i Studio med 13 pt
# og klipper ikke teksten. En ny knap uden en bredde dér stopper byggeriet.
def _btn_w(name):
    if name not in dp.ROW_BTN:
        raise SystemExit(f"material_parts: {name} har ingen bredde i "
                         f"domain_parts.ROW_BTN")
    return dp.ROW_BTN[name]


def _btns_w(btns):
    return sum(_btn_w(n) for n, _t in btns) + BTN_GAP * (len(btns) - 1)


DETAILS_W = _btns_w(DETAIL_BTNS) + CELL_PAD
ACTIONS_W = _btns_w(ACTION_BTNS) + CELL_PAD


def _w(spec):
    return 0 if spec is None else _col_w(spec[0], spec[2])


ALL_WS = [_w(a) for _c, a in SLOTS]
ALL_TABLE_W = STATUS_W + sum(ALL_WS) + DETAILS_W + ACTIONS_W + T_GAP * (len(SLOTS) + 2)

# Compact FYLDER listens bredde: hver tekstkolonne faar sin mindstebredde
# (mindst saa bred som overskriften) plus en lige del af det, der er
# tilovers. Er der intet tilovers (en tablet), er tabellen sine
# mindstebredder og scroller vandret, ligesom All columns.
COMPACT = [(i, c) for i, (c, _a) in enumerate(SLOTS) if c is not None]
C_FIXED = STATUS_W + DETAILS_W + ACTIONS_W + T_GAP * (len(COMPACT) + 2)
C_MIN = C_FIXED + sum(_w(c) for _i, c in COMPACT)
# Galleriets egne 2 x 2 px skabelonpolstring og dets lodrette scrollbar.
TABLE_AVAIL = f"(({FORM_W}) - 4 - {SCROLLBAR_W})"
C_SPARE = f"Max(0, ({TABLE_AVAIL}) - {C_MIN}) / {len(COMPACT)}"


def _compact_w(i):
    return f"{_w(SLOTS[i][0])} + {C_SPARE}"


COMPACT_TABLE_W = f"Max({C_MIN}, {TABLE_AVAIL})"
TABLE_W = f"If({ALL_COLS}, {ALL_TABLE_W}, {COMPACT_TABLE_W})"


def _slot_w(i):
    c, a = SLOTS[i]
    if c is None:
        return str(ALL_WS[i])
    return f"If({ALL_COLS}, {ALL_WS[i]}, {_compact_w(i)})"


def _slot_vis(i):
    return None if SLOTS[i][0] is not None else ALL_COLS


def _slot_text(i, part):
    """part 0 = overskriften, 1 = udtrykket."""
    c, a = SLOTS[i]
    if c is None:
        return f'"{a[0]}"' if part == 0 else a[1]
    cv = f'"{c[0]}"' if part == 0 else c[1]
    av = f'"{a[0]}"' if part == 0 else a[1]
    return cv if cv == av else f"If({ALL_COLS}, {av}, {cv})"


def _pad(ctrl):
    ctrl.props["PaddingLeft"] = str(CELL_PAD)
    return ctrl


def _head_text(name, text, width, visible=None, accessible=None):
    return _pad(text_ctrl(name, text, size=HEAD_SIZE, color=C_MUTED, weight="Semibold",
                          height=18, width=width, wrap="false", visible=visible,
                          accessible=accessible))


def _status_badge():
    """Raekkens status som et maerke - VALID, DRAFT, SUBMITTED - i sin
    egen farve, saa listen kan skimmes."""
    s = "ThisItem.Status"
    fg = (f'Switch({s}, "valid", {C_VALID_FG}, "submitted", {C_INFO_FG}, '
          f'"draft", {C_WARN_FG}, {C_NEUTRAL_FG})')
    bg = (f'Switch({s}, "valid", {C_VALID_BG}, "submitted", {C_INFO_BG}, '
          f'"draft", {C_WARN_BG}, {C_NEUTRAL_BG})')
    badge = text_ctrl("txtDomRowStatus", f"Upper({s})", size=11, color=fg,
                      weight="Semibold", height=22, width=STATUS_W - 2 * CELL_PAD,
                      wrap="false", accessible=f'"Status: " & {s}',
                      extra={"Fill": bg, "Align": "Align.Center",
                             "AlignInContainer": "AlignInContainer.Center",
                             "RadiusBottomLeft": "6", "RadiusBottomRight": "6",
                             "RadiusTopLeft": "6", "RadiusTopRight": "6"})
    return group("conDomRowStatus", [badge], direction="Horizontal", gap=0,
                 height=22, width=STATUS_W, align_items="Center",
                 pad=(0, 0, 0, CELL_PAD))


def _row_buttons(name, btns, fxs, width, danger=()):
    out = []
    for (bn, text), fx in zip(btns, fxs):
        b = button(bn, text, fx, danger=bn in danger, width=_btn_w(bn), height=BTN_H)
        b.props["Size"] = "13"
        out.append(b)
    return group(name, out, direction="Horizontal", gap=BTN_GAP, height=BTN_H,
                 width=width, align_items="Center", pad=(0, 0, 0, CELL_PAD))


def build_rows():
    # --- hovedet: titel, soegning og de to filtre ---------------------
    title = text_ctrl("txtDomRowsH", '"Saved Rows"', size=17, weight="Semibold",
                      height=26, wrap="false")
    search = text_input("txtDomSearch", '""', width="240",
                        placeholder='"Search FL, supplier, part no., material"',
                        label='"Search the rows"')
    status = themed_dropdown(
        "drpDomStatusFilter", f'["{ALL_STATUS}", "draft", "valid", "submitted"]',
        f'"{ALL_STATUS}"', width="170", label='"Filter by status"')
    plant = themed_dropdown("drpDomPlantFilter", PLANT_ITEMS, f'"{ALL_PLANTS}"',
                               width="170", label='"Filter by plant"')
    head = flow_row("conDomRowsTop", [title, search, status, plant], FORM_W, gap=8,
                    flex=title, flex_min=text_px("Saved Rows", 17))

    # --- Compact / All columns --------------------------------------------
    compact = _pill(_fit(button("btnDomViewCompact", '"Compact"',
                                f"Set({ALL_COLS}, false)", height=32,
                                accessible='"Compact view"'), size=13),
                    f"!{ALL_COLS}")
    allc = _pill(_fit(button("btnDomViewAll", '"All columns"',
                             f"Set({ALL_COLS}, true)", height=32,
                             accessible='"All columns view"'), size=13),
                 ALL_COLS)
    for b in (compact, allc):
        b.props["Size"] = "13"
    views = group("conDomViewSwitch", [compact, allc], direction="Horizontal", gap=8,
                  height=32, align_items="Center", justify="End")

    # --- tabellen -----------------------------------------------------------
    heads = [_head_text("txtDomHeadStatus", '"STATUS"', STATUS_W)]
    cells = [_status_badge()]
    for i in range(len(SLOTS)):
        heads.append(_head_text(f"txtDomHead{i}", _slot_text(i, 0), _slot_w(i),
                                visible=_slot_vis(i),
                                accessible=_slot_text(i, 0)))
        cells.append(_pad(text_ctrl(f"txtDomCell{i}", _slot_text(i, 1), size=13,
                                    height=20, width=_slot_w(i), wrap="false",
                                    visible=_slot_vis(i))))
    heads.append(_head_text("txtDomHeadDetails",
                            f'If({ALL_COLS}, "ACTIONS", "DETAILS")', DETAILS_W))
    heads.append(_head_text("txtDomHeadActions", f'If({ALL_COLS}, "", "ACTIONS")',
                            ACTIONS_W, accessible='"Actions"'))
    cells.append(_row_buttons("conDomRowDetails", DETAIL_BTNS,
                              ['Set(varDomDetailsId, ThisItem.RowId)', dp.open_docs_fx()],
                              DETAILS_W))
    cells.append(_row_buttons("conDomRowActions", ACTION_BTNS,
                              [dp.load_row_fx(), dp.copy_row_fx(), dp.delete_this_row_fx()],
                              ACTIONS_W, danger=("btnDomRowDelete",)))

    list_head = group("conDomListHead", heads, direction="Horizontal", gap=T_GAP,
                      height=34, width=TABLE_W, align_items="Center", fill=C_MUTED_BG)
    row = group("conDomRow", cells, direction="Horizontal", gap=T_GAP,
                height="Parent.TemplateHeight - 2", align_items="Center",
                justify="Start", width="Parent.TemplateWidth")

    gal_h = f"Max(Min(CountRows({SCOPE}), {GAL_ROWS}), 1) * {ROW_H + 2}"
    gal = Ctrl("galDomRows", "Gallery", variant="Vertical", props={
        "AccessibleLabel": '"Saved rows"',
        "BorderStyle": "BorderStyle.None",
        "Fill": C_TRANSPARENT,
        "FillPortions": "0",
        "Height": gal_h,
        "Items": f"Sort({SCOPE}, RowId, SortOrder.Descending)",
        "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None",
        "OnSelect": dp.load_row_fx(),
        "Selectable": "true",
        "ShowScrollbar": "true",
        "TabIndex": "0",
        "TemplatePadding": "2",
        "TemplateSize": str(ROW_H),
        "Width": f"({TABLE_W}) + 4 + {SCROLLBAR_W}",
        "WrapCount": "1",
    }, children=[row], h=gal_h)

    # Vandret scroll, naar tabellen er bredere end kortet (All columns, og
    # Compact paa en tablet). Start, ikke Stretch - check_layout regel 14.
    # Den vandrette scrollbar tager hoejde, saa den laegges til, naar den
    # er der.
    wide = f"(({TABLE_W}) + 4 + {SCROLLBAR_W}) > ({FORM_W})"
    table = group("conDomTableWrap", [list_head, gal], direction="Vertical", gap=0,
                  overflow_x="Scroll", width="Parent.Width", align_items="Start")
    table.props["Height"] = f"{table.props['Height']} + If({wide}, {SCROLLBAR_W}, 0)"
    table.h = table.props["Height"]

    empty = text_ctrl("txtDomNoRows", '"No saved rows yet."', size=13, color=C_MUTED,
                      height=22, wrap="false",
                      visible="IfError(CountRows(colDomRows) = 0, false)")

    return card("conDomRowsCard", [head, views, table, empty] + _submit_parts())


# ---------------------------------------------------------------------------
# Indsend - under tabellen, til hoejre
# ---------------------------------------------------------------------------
def _submit_parts():
    """Save as draft, Submit og Reload rows fra domain_parts.build_submit -
    samme handlinger, nu under tabellen med Submit yderst til hoejre."""
    reload_ = _fit(button("btnDomReload", '"Reload rows"',
                          dp.refresh_rows_fx() + ';\nSet(varDomInfo, "Reloaded.")'))
    draft = _fit(button(
        "btnDomSendDraft", '"Save as draft"', with_busy(dp.SAVING_VAR, dp.send_fx(False)),
        icon=ICON_SAVE,
        display_mode=f'If(CountRows({dp.SENDABLE}) = 0, DisplayMode.Disabled, DisplayMode.Edit)'),
        icon=True)
    # Submit spoerger foerst (domain_parts.build_submit_confirm).
    submit = _fit(button(
        "btnDomSubmit", '"Submit saved rows"', f"Set({dp.CONFIRM_VAR}, true)", primary=True,
        icon=ICON_SUBMIT,
        display_mode=f'If(CountRows({dp.VALID}) = 0, DisplayMode.Disabled, DisplayMode.Edit)'),
        icon=True)
    state = text_ctrl(
        "txtDomSubmitState",
        ('If(\n'
         '    IsBlank(varDomRequestNo),\n'
         '    "The request has not been sent to the hub yet.",\n'
         '    "Request " & varDomRequestNo & " is on the landing page."\n'
         ')'),
        size=13, color=C_MUTED, height=20, wrap="false")
    row = flow_row("conDomSubmitRow", [state, reload_, draft, submit], FORM_W, gap=8,
                   flex=state, flex_min=0)
    note = text_ctrl(
        "txtDomSubmitNote",
        ('"Save as draft puts the request on the landing page with status Draft '
         '- it can still be edited. Submit locks the rows and sets the status '
         'to Submitted. Both write to the SAME row in the index."'),
        size=12, color=C_MUTED, height=18, wrap="false")
    return [row, note]
