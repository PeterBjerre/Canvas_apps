# -*- coding: utf-8 -*-
"""
Materials' EGNE dele: formularens felter, No BOM Item og listens kolonner
(issue #67).

Skaermen er tegnet efter materials.png og "saved row.png" i app-mappen -
HTML-projektets reservedelsformular. Byggeklodserne - gitteret, knapperne,
pillerne, dokumentcellen, listen og indsend - er faelles med Equipment og
staar i tools/domain_parts.py. Her staar kun det, der er Materials': hvilke
felter, i hvilken raekkefoelge, og hvilke kolonner listen viser.

FORMULAREN
----------
    Spare Parts Form  * Required   [Import invoice] [No BOM Item: OFF]
    [ Plant       ][ FL           ][ Description  ][ Manufacturer     ]
    [ Model number][ Manuf. part  ][ Supplier     ][ Supp. part no.   ]
    [ Stock unit  ][ Price        ][ Price unit   ][ Delivery time    ]
    [ Rec. stock  ][ Strategic    ][ Wear part    ][ Documentation    ]
    (Plant: X) (Row status: ...)  [Save draft][Save row][Reset form]

Raekkefoelgen er issue #159's fire grupper: organisation og identifikation,
producent og leverandoer, lager/pris/levering, klassifikation og
dokumentation. Hver raekke er sin egen container, der ombryder til to og
een kolonne, saa laese- og tab-raekkefoelgen er den samme paa desktop,
tablet og mobil (felterne har TabIndex 0 og foelger containerens orden).

NO BOM ITEM
-----------
En knap i formularens hoved. Staar den til, er raekken ikke en BOM-post:
funktionspladsen ryddes og deaktiveres, dens stjerne forsvinder, og Save
row kraever den ikke. Vaerdien er kolonnen NoBomItem (domain_config), saa
gem, hent, kopier og detaljer tager den med af sig selv.
"""
import domain_config as cfg
import domain_parts as dp
from gen_screen import C_REQUIRED
from build_helpers import text_ctrl, group, button, text_input, card, field_cell, label_px

NOBOM = dp._var("NoBomItem")
FL_VAR = dp._var(cfg.FL_FIELD)
CELL_W = dp.CELL_W
REQUIRED = dp.REQUIRED


# ---------------------------------------------------------------------------
# Functional Location og No BOM Item
# ---------------------------------------------------------------------------
def _fl_cell():
    """Functional Location - EEN celle med EEN combobox og Search
    (fl_picker.py, issue #63).

    Stjernen staar kun, naar feltet er kraevet: No BOM Item slaar kravet
    fra, og saa ville en stjerne paa et deaktiveret felt lyve."""
    picker = dp.build_fl_picker(
        CELL_W, lock=NOBOM, required_formula=f"{REQUIRED} && !{NOBOM}")
    label = "Functional location"
    lbl = text_ctrl("txtDomFlLbl", f'"{label}"', size=13, weight="Semibold",
                    height=20, width=f"Min({label_px(label)}, ({CELL_W}) - 13)",
                    wrap="false")
    star = text_ctrl("txtDomFlStar", '"*"', size=13, color=C_REQUIRED,
                     weight="Semibold", height=20, width=10, wrap="false",
                     accessible='"Required"', visible=f"!{NOBOM}")
    head = group("conDomFlLblRow", [lbl, star], direction="Horizontal", gap=3,
                 height=20, align_items="Center")
    return group("conDomFl", [head, picker], direction="Vertical", gap=6,
                 width=CELL_W, align_in_container="Start")


def toggle_nobom_fx():
    """No BOM Item til/fra. TIL rydder funktionspladsen - soegningen, dens
    svar og det valgte - saa en No BOM-raekke aldrig gemmes med en."""
    return (
        f"Set({NOBOM}, !{NOBOM});\n"
        "If(\n"
        f"    {NOBOM},\n"
        f'    Set({FL_VAR}, "");\n'
        f"    {dp.fl_reset_fx_dom()};\n"
        '    Set(varDomFlMsg, "No BOM item - a functional location is not required."),\n'
        '    Set(varDomFlMsg, "")\n'
        ")"
    )


def _nobom_button():
    # OFF er den laengste af de to tekster - bredden regnes af den.
    off, on = "No BOM Item: OFF", "No BOM Item: ON"
    b = button("btnDomNoBom", f'"{off}"', toggle_nobom_fx(), height=32,
               display_mode=dp.DM_ROW,
               accessible=f'If({NOBOM}, "No BOM item: on", "No BOM item: off")')
    b.props["Size"] = "13"
    dp.fit(b, size=13)
    b.props["Text"] = f'If({NOBOM}, "{on}", "{off}")'
    return dp.pill(b, NOBOM)


def save_fx(status):
    """domain_parts' gem, plus Materials' eget krav: en faerdig raekke skal
    have en funktionsplads - medmindre den er No BOM."""
    need_fl = (f'!{NOBOM} && IsBlank(Trim(Coalesce({FL_VAR}, "")))',
               "Functional location is required - or turn on No BOM Item.")
    return dp.save_row_fx(status, required=[need_fl])


# ---------------------------------------------------------------------------
# Formularen
# ---------------------------------------------------------------------------
# Skaermens raekkefoelge - issue #159's fire grupper, fire celler pr.
# raekke. FL, TEXT, DOCS og PLANT er de celler, der ikke er et almindeligt
# felt fra SECTIONS.
SPECIAL = {"FL", "TEXT", "DOCS", "PLANT"}
FORM_ORDER = [
    # Organisation og identifikation - Plant foerst
    "PLANT", "FL", "TEXT", "Manufacturer",
    # Producent og leverandoer
    "ModelNumber", "ManufacturerPartNo", "Supplier", "SupplierPartNo",
    # Lager, pris og levering
    "StockUnit", "Price", "PriceUnit", "DeliveringTime",
    # Klassifikation og dokumentation
    "RecommendedStock", "StrategicPart", "WearPart", "DOCS",
]
# Felter, der ikke er en celle i gitteret: NoBomItem er knappen i hovedet,
# og FL er cellen "FL".
NOT_IN_GRID = {"NoBomItem", cfg.FL_FIELD}


def _cell(key):
    if key == "FL":
        return _fl_cell()
    if key == "TEXT":
        return dp.text_cell()
    if key == "DOCS":
        return dp.docs_cell()
    if key == "PLANT":
        return dp.plant_cell()
    return dp.field_grid_cell(key)


def build_form():
    dp.check_form_order(FORM_ORDER, SPECIAL, NOT_IN_GRID)
    head = dp.form_head("Spare Parts Form", right=[_nobom_button()])
    rows = dp.grid_rows("conDomGrid", [_cell(k) for k in FORM_ORDER])
    # Soegningens svar under den foerste raekke - den med FL i.
    rows.insert(1, dp.build_fl_msg())

    buttons = dp.form_buttons(save_fx, "Save row", "New row")
    return card("conDomFormCard", [head] + rows + dp.form_footer(buttons))


# ---------------------------------------------------------------------------
# Listen - kolonnerne, som issue #67 skriver dem
# ---------------------------------------------------------------------------
# (overskrift, udtryk, mindstebredde). Se domain_parts.build_list for, hvad
# en plads er.
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
    (None, ("PRICE", dp.num_text("Price"), 80)),
    (None, ("PRICE UNIT", "ThisItem.PriceUnit", 90)),
    (None, ("DELIVERY TIME", dp.num_text("DeliveringTime"), 110)),
    (None, ("RECOMMENDED STOCK", dp.num_text("RecommendedStock"), 130)),
    (None, SUPP),
    (None, ("SUPPLIER PART NO.", "ThisItem.SupplierPartNo", 130)),
    (None, ("STRATEGIC PART", "ThisItem.StrategicPart", 100)),
    (None, ("WEAR PART", "ThisItem.WearPart", 90)),
]


def build_rows():
    return dp.build_list(SLOTS, "STATUS", "Search FL, supplier, part no., material")
