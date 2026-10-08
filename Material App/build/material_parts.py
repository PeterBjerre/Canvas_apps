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
    Spare Parts Form  * Required   [No BOM Item: OFF] [More details: OFF]
    [ Plant       ][ FL + Add     ][ Description  ][ Manufacturer     ]
    [ Model number][ Manuf. part  ][ Supplier     ][ Supp. part no.   ]
    [ Stock unit  ][ Price        ][ Price unit   ][ Delivery time    ]
    [ Stock item  ][ Min stock *  ][ Max stock *  ][ Rec. stock       ]
    [ Storage bin ][ Strategic    ][ Wear part    ][ Documentation    ]
    [ Remarks     ][ Order no.    ][ Replaces     ][ Replaced no.     ]   <- foldet ind
    (Plant: X) (Row status: ...)  [Save draft][Save row][Reset form]

STOCK AND STORAGE (issue #204)
------------------------------
Stock item er raekkens til/fra. Staar den til, KRAEVES min og max, og
min <= max; staar den fra, roeres de ikke. Storage bin foreslaas som "X",
og standarden staar HER - ikke som en default i SharePoint, hvor den
ville udfylde et felt bag om brugeren.

YDERLIGERE OPLYSNINGER
----------------------
Remarks, maintenance order no. og "replaces existing material" er
valgfrie og staar foldet ind bag knappen "More details" i hovedet - de
fylder ellers en hel raekke i en formular, de fleste raekker ikke bruger.
Replaced material no. vises foerst, naar Replaces existing staar til, og
er saa kraevet.

Created material no. er IKKE et felt her. Nummeret findes foerst, naar
materialet er oprettet i SAP, altsaa efter godkendelse og overdragelse -
det udfyldes i Details bagefter (domain_parts' detaljerude).

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
from build_helpers import (text_ctrl, group, button, text_input, card, field_cell,
                           label_px, fit_button_width)
from gen_screen import C_MUTED

NOBOM = dp._var("NoBomItem")
FL_VAR = dp._var(cfg.FL_FIELD)
CELL_W = dp.CELL_W
REQUIRED = dp.REQUIRED

# Lagervare, "erstatter et materiale" og de tre felter, de styrer.
STOCK = dp._var("IsStockItem")
MIN_S = dp._var("MinStock")
MAX_S = dp._var("MaxStock")
REPLACES = dp._var("ReplacesExisting")
REPLACED_NO = dp._var("ReplacedMaterialNo")
# Er raekken strategisk? Kolonnen er tekst, og gamle raekker kan staa med
# Ja, Y eller true. Normaliseringen staar HER og kun her - der skrives
# altid "Yes"/"No" (domain_config.SECTIONS), og gamle vaerdier laeses som
# de var ment.
STRAT_VALUES = '["YES", "JA", "Y", "TRUE", "1"]'


def is_strategic(expr):
    return f'(Upper(Trim(Coalesce({expr}, ""))) in {STRAT_VALUES})'


STRAT_FORM = is_strategic(dp._var("StrategicPart"))
# Formularens "flere oplysninger" - foldet ind, indtil nogen aabner den.
EXTRA_OPEN = "varDomExtraOpen"
# Appens egen tilstand i App.OnStart (domain_app.write_app).
EXTRA_STATE = f'Set({EXTRA_OPEN}, false);\nSet(varDomDetCreatedNo, "")'


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


def _extra_button():
    """More details til/fra - raekken med de valgfrie oplysninger."""
    off, on = "More details: OFF", "More details: ON"
    b = button("btnDomMoreDetails", f'"{off}"', f"Set({EXTRA_OPEN}, !{EXTRA_OPEN})",
               height=32,
               accessible=f'If({EXTRA_OPEN}, "More details: on", "More details: off")',
               tooltip='"Remarks, maintenance order no. and replaced material"')
    b.props["Size"] = "13"
    dp.fit(b, size=13)
    b.props["Text"] = f'If({EXTRA_OPEN}, "{on}", "{off}")'
    return dp.pill(b, EXTRA_OPEN)


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


# KRAVENE TIL EN FAERDIG RAEKKE
#
# Hvert krav er (betingelse der betyder "mangler", besked). De staar her,
# fordi de er Materials' - domain_parts' gem kender dem ikke, og en kladde
# tjekker dem ikke. Beskederne siger HVAD der mangler.
def _row_rules():
    return [
        (f'!{NOBOM} && IsBlank(Trim(Coalesce({FL_VAR}, "")))',
         "Functional location is required - or turn on No BOM Item."),
        (f"Coalesce({STOCK}, false) && (IsBlank({MIN_S}) || IsBlank({MAX_S}))",
         "Min stock and max stock are required for a stock item."),
        (f"Coalesce({STOCK}, false) && !IsBlank({MIN_S}) && !IsBlank({MAX_S}) && "
         f"{MIN_S} > {MAX_S}",
         "Min stock must be less than or equal to max stock."),
        (f'Coalesce({REPLACES}, false) && IsBlank(Trim(Coalesce({REPLACED_NO}, "")))',
         "Replaced material no. is required when the material replaces an existing one."),
    ]


def save_fx(status):
    """domain_parts' gem, plus Materials' egne krav til en faerdig raekke
    (_row_rules): funktionspladsen, lagerniveauet og det erstattede
    materiale."""
    return dp.save_row_fx(status, required=_row_rules())


# ---------------------------------------------------------------------------
# Formularen
# ---------------------------------------------------------------------------
# Skaermens raekkefoelge - issue #159's fire grupper, fire celler pr.
# raekke. FL, TEXT, DOCS og PLANT er de celler, der ikke er et almindeligt
# felt fra SECTIONS.
SPECIAL = {"FL", "TEXT", "DOCS", "PLANT"}
MAIN_ORDER = [
    # Organisation og identifikation - Plant foerst
    "PLANT", "FL", "TEXT", "Manufacturer",
    # Producent og leverandoer
    "ModelNumber", "ManufacturerPartNo", "Supplier", "SupplierPartNo",
    # Pris og levering
    "StockUnit", "Price", "PriceUnit", "DeliveringTime",
    # Lager (issue #204)
    "IsStockItem", "MinStock", "MaxStock", "RecommendedStock",
    # Plads, klassifikation og dokumentation
    "StorageBin", "StrategicPart", "WearPart", "DOCS",
]
# Raekken, der er foldet ind (issue #204) - valgfrie oplysninger.
EXTRA_ORDER = ["Remarks", "MaintenanceOrderNo", "ReplacesExisting",
               "ReplacedMaterialNo"]
FORM_ORDER = MAIN_ORDER + EXTRA_ORDER
# Felter, der ikke er en celle i gitteret: NoBomItem er knappen i hovedet,
# og FL er cellen "FL".
NOT_IN_GRID = {"NoBomItem", cfg.FL_FIELD}


# Feltets krav og synlighed, hvor de afhaenger af et andet felt. Et
# krav, der ikke gaelder lige nu, viser ingen stjerne og giver ingen roed
# kant (domain_parts.field_grid_cell).
CONDITIONAL = {
    "MinStock": {"required": f"Coalesce({STOCK}, false)"},
    "MaxStock": {"required": f"Coalesce({STOCK}, false)"},
    "ReplacedMaterialNo": {"required": f"Coalesce({REPLACES}, false)",
                           "visible": f"Coalesce({REPLACES}, false)"},
}


def _cell(key):
    if key == "FL":
        return _fl_cell()
    if key == "TEXT":
        return dp.text_cell()
    if key == "DOCS":
        return dp.docs_cell()
    if key == "PLANT":
        return dp.plant_cell()
    return dp.field_grid_cell(key, **CONDITIONAL.get(key, {}))


def build_form():
    dp.check_form_order(FORM_ORDER, SPECIAL, NOT_IN_GRID)
    head = dp.form_head("Spare Parts Form",
                        right=[_nobom_button(), _extra_button()])
    rows = dp.grid_rows("conDomGrid", [_cell(k) for k in MAIN_ORDER])
    # Soegningens svar under den foerste raekke - den med FL i.
    rows.insert(1, dp.build_fl_msg())
    # De valgfrie oplysninger: een raekke, der kun er der, naar den er
    # foldet ud - skjult koster den ingen plads.
    extra = dp.grid_row("conDomGridX", [_cell(k) for k in EXTRA_ORDER])
    extra.vis = EXTRA_OPEN
    rows.append(extra)

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
# EET fast saet kolonner (issue #204). Compact/All columns er vaek; resten
# af raekkens felter staar i Details, grupperet. DOCS, pris og lager var
# kun i "All columns" og er der nu - de staar i Details.
SLOTS = [FL_C, DESC, MFR, MPN, SUPP]



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
        ("Functional locations", 'If(Coalesce({row}.NoBomItem, false), "No BOM item", '
                                 'Coalesce({row}.ObjectList, Coalesce({row}.FunctionalLocation, "-")))'),
        ("Primary functional location", 'Coalesce({row}.FunctionalLocation, "-")'),
    ]),
    ("Manufacturer and supplier", ["Manufacturer", "ModelNumber", "ManufacturerPartNo",
                                   "Supplier", "SupplierPartNo"]),
    ("Stock and storage", ["StockUnit", "Price", "PriceUnit", "DeliveringTime",
                           "IsStockItem", "MinStock", "MaxStock", "RecommendedStock",
                           "StorageBin"]),
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
dp.configure(
    # Storage bin foreslaas som "X", naar formularen ryddes.
    field_defaults={"StorageBin": '"X"'},
    # Grupperet detaljerude, og materialenummeret under felterne.
    details_groups=DETAILS_GROUPS,
    details_rows=details_rows,
    details_open=DETAILS_SYNC,
    details_nav=DETAILS_SYNC,
)
