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
import env_config as env
import object_list as ol
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
# OBJECT LIST (issue #204)
#
# Raekkens funktionspladser. Samlingen hoerer til FORMULAREN - den raekke,
# man staar paa - og den gemmes paa raekken som ObjectList (koderne),
# ObjectListJson (kode + beskrivelse) og FunctionalLocation (den foerste
# kode). Delene staar i tools/object_list.py og er domaeneneutrale.
OBJECTS = "colDomObjects"
OBJ_SCHEMA = ol.schema()
OBJ_COUNT = ol.count_fx(OBJECTS)
FL_MSG = "varDomFlMsg"
# Mindst 16 tegn foer der kan soeges OG foer der kan tilfoejes (Q11).
# "SSV13 HFC10AJ010" er praecis 16 - i praksis skal man kende hele koden.
MIN_FL_LEN = 16
ADD_READY = f'Len(Trim(Coalesce({FL_VAR}, ""))) >= {MIN_FL_LEN}'
# Gendannelsen, naar en raekke hentes eller kopieres: JSON'en foerst, saa
# den "; "-adskilte liste, og til sidst FL-kolonnen alene (gamle raekker).
OBJ_RESTORE = ol.restore_fx(
    OBJECTS, json_src="ThisItem.ObjectListJson", list_src="ThisItem.ObjectList",
    fl_src=f"ThisItem.{cfg.FL_FIELD}")

# Formularens "flere oplysninger" - foldet ind, indtil nogen aabner den.
EXTRA_OPEN = "varDomExtraOpen"
# Appens egen tilstand i App.OnStart (domain_app.write_app).
EXTRA_STATE = f'Set({EXTRA_OPEN}, false);\nSet(varDomDetCreatedNo, "")'


# ---------------------------------------------------------------------------
# Functional Location og No BOM Item
# ---------------------------------------------------------------------------
def _add_fx():
    """Add: laeg det VALGTE resultat i objektlisten. Soegningen er
    FL-vaelgerens egen - knappen her tilfoejer kun.

    Er raekken strategisk, slaas systemet og dets ansvarlige op med det
    samme (bag flaget), saa initialerne staar under listen, foer raekken
    gemmes."""
    desc = f'Coalesce(LookUp(colDomFl, Code = {FL_VAR}).Description, "")'
    fx = ol.add_fx(OBJECTS, FL_VAR, desc, FL_MSG)
    if APPROVAL_ON:
        look = "\n".join("    " + l for l in resolve_fx(FORM_CODES).split("\n"))
        fx += f";\nIf(\n    {STRAT_FORM},\n{look}\n)"
    return fx


def _fl_cell():
    """Functional Location - EEN celle med EEN combobox, Search og Add
    (fl_picker.py, issue #63; objektlisten er issue #204).

    Stjernen staar kun, naar feltet er kraevet: No BOM Item slaar kravet
    fra, og saa ville en stjerne paa et deaktiveret felt lyve. Kravet er
    nu objektlisten - der skal vaere MINDST EET objekt."""
    picker = dp.build_fl_picker(
        CELL_W, lock=NOBOM, min_len=MIN_FL_LEN,
        required_formula=f"{REQUIRED} && !{NOBOM} && {OBJ_COUNT} = 0")
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
    svar, det valgte OG objektlisten - saa en No BOM-raekke aldrig gemmes
    med en.

    En STRATEGISK raekke kan ikke blive No BOM (issue #204): godkendelsen
    findes gennem funktionspladsen, saa No BOM Item kan ikke bruges til at
    omgaa kravet."""
    return (
        "If(\n"
        f"    !{NOBOM} && {STRAT_FORM},\n"
        '    Set(varDomFlMsg, "A strategic part needs at least one functional location."),\n'
        "\n"
        f"    Set({NOBOM}, !{NOBOM});\n"
        "    If(\n"
        f"        {NOBOM},\n"
        f'        Set({FL_VAR}, "");\n'
        f"        {ol.clear_fx(OBJECTS)};\n"
        f"        {dp.fl_reset_fx_dom()};\n"
        '        Set(varDomFlMsg, "No BOM item - a functional location is not required."),\n'
        '        Set(varDomFlMsg, "")\n'
        "    )\n"
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
        (f"!{NOBOM} && {OBJ_COUNT} = 0",
         "Add at least one functional location - or turn on No BOM Item."),
        (f"{STRAT_FORM} && {OBJ_COUNT} = 0",
         "A strategic row needs at least one functional location."),
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
    # Objektlisten i FULD bredde under soegningen: koderne er lange, og i
    # en fjerdedel af kortet ville de blive klippet.
    add = ol.add_button(
        "Dom", _add_fx(),
        display_mode=f"If({NOBOM} || !({ADD_READY}), DisplayMode.Disabled, {dp.DM_ROW})")
    rows.insert(2, ol.panel(
        "Dom", OBJECTS, width="Parent.Width", msg_var=FL_MSG, add=add,
        display_mode=f"If({NOBOM}, DisplayMode.Disabled, {dp.DM_ROW})",
        extra=([_approver_line()] if APPROVAL_ON else ()),
        hint='"No functional location yet - search above and press Add."'))
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
# "SSV13 HFC10AJ010 +2": den foerste kode og hvor mange flere raekken har
# (issue #204). Regnet af den GEMTE ObjectList, saa den virker for hver
# raekke i tabellen.
FL_C = ("FUNCTIONAL LOCATION",
        'If(ThisItem.NoBomItem, "No BOM item", '
        + ol.summary_fx("ThisItem.ObjectList", f"ThisItem.{cfg.FL_FIELD}") + ")", 170)
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
    # Objektlisten foelger raekken: den fyldes, naar en raekke hentes eller
    # kopieres, og ryddes med formularen.
    clear_extra=ol.clear_fx(OBJECTS),
    load_extra=OBJ_RESTORE,
    copy_extra=OBJ_RESTORE,
    # Gem: koderne, JSON'en - og FL-kolonnen som den FOERSTE kode.
    # ApprovalRequired er raekkens eget svar paa "skal den godkendes?".
    # Den skrives ved HVER gemning, ogsaa som kladde: det er data, ikke
    # godkendelse, og flowet filtrerer paa den. Saa er den rigtig den dag,
    # flaget taendes - ogsaa paa raekker, der laa der i forvejen.
    extra_patch=[("ObjectList", ol.codes_fx(OBJECTS)),
                 ("ObjectListJson", ol.json_fx(OBJECTS)),
                 ("ApprovalRequired", STRAT_FORM)],
    patch_override={cfg.FL_FIELD: ol.first_fx(OBJECTS)},
    # Grupperet detaljerude, og materialenummeret under felterne.
    details_groups=DETAILS_GROUPS,
    details_rows=details_rows,
    details_open=DETAILS_SYNC,
    details_nav=DETAILS_SYNC,
)


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

# Raekkens funktionspladser som een "; "-adskilt tekst - formatet, flowet
# forventer, og det samme som ObjectList gemmes i.
FORM_CODES = ol.codes_fx(OBJECTS)
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
        "        ),\n"
        f'        Set({APPR_MSG}, "Could not look up the system managers: " & '
        "FirstError.Message)\n"
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


def _approver_line():
    """Linjen under objektlisten: hvem godkendelsen vil spoerge.

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


# Godkendelsen er bag flaget: er det slukket, er appen praecis som foer -
# ingen opslag, ingen vagt paa Submit og intet flow-kald. Flaget staar i
# tools/canvas_apps.json (environments.<miljoe>.features.material_approval).
if APPROVAL_ON:
    dp.configure(submit_guard=submit_guard())
