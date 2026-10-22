# -*- coding: utf-8 -*-
"""
Equipments EGNE dele: formularens felter og listens kolonner (issue #68).

Skaermen er tegnet efter eq.png (skaermbilledet ligger nu kun i
git-historikken) - HTML-projektets
udstyrsformular. Byggeklodserne - gitteret, knapperne, pillerne,
dokumentcellen, FL-comboboksen, listen og indsend - er faelles med
Materials og staar i tools/domain_parts.py. Her staar kun det, der er
Equipments: hvilke felter, i hvilken raekkefoelge, og hvilke kolonner
listen viser.

FORMULAREN - I SEKTIONER (issue #160, UX-review M2)
--------------------------------------------------
    Row details  * Required
    Identification
    [ Plant         ][ Type             ][ Equipment type    ][ Description    ]
    ─ Location
    [ Func. location][ Room coordinates ][ Placement text    ]
    ─ Manufacturer
    [ Manufacturer  ][ Type designation ][ Serial number     ][ Class data     ]
    ─ Warranty
    [ Warranty from ][ Warranty to      ]
    ─ Documents
    [ Documentation ]
    (Plant: X) (Row status: ...)   [Add row][New row]

Sektionerne er Equipment-mockuppens. Hver sektions raekke er sin egen
container, der ombryder til to og een kolonne, saa laese- og
tab-raekkefoelgen er den samme paa desktop, tablet og mobil (felterne har
TabIndex 0 og foelger containerens orden).

Equipment number, Func. loc. 1 og Functional location 2 er fjernet fra
formularen (issue #94). FL-soegningen er den eneste maade at vaelge en
funktionsplads paa, og udstyrsnummeret er SAP's - det vises stadig i
listen og i detaljerne (domain_config.READ_FIELDS). En gemt raekke
slettes med ikonet i listens Actions-kolonne, ikke fra formularen.

SIDEPANELETS FANER (issue #430)
-------------------------------
I sidepanelet staar formularen under to faner - samme moenster som
Materials (domain_parts.editor_tabs), men uden Objects-fanen:
    Details    Identification, Location (med FL-soegningen), Manufacturer,
               Warranty (Warranty from/to - issue #531)
    Documents  Documents: antallet af dokumenter og
               ModernAttachments-kontrollen (Save documents)
Felterne, variablerne og Patch er de samme - de staar bare paa en anden
fane. Gem-tjekkene er Notify-beskeder, saa de ses paa alle faner.

GARANTIEN PAA DETAILS (issue #531)
----------------------------------
Warranty from/to stod foer paa Documents-fanen under "Warranty and
documents". Nu staar de i deres egen sektion, Warranty, sidst paa Details,
og Documents-fanen er kun dokumenterne (sektionen hedder Documents). Samme
datovaelgere, variabler, tjek (WARRANTY_BAD) og visning; paa en telefon er
Warranty-sektionen stadig klappet sammen, og den aabner sig selv, naar
garantien slutter foer den starter.

EEN FUNKTIONSPLADS (issue #485)
-------------------------------
Udstyr sidder paa EEN funktionsplads - ingen Objects-fane og intet
Objects-ikon (kun Materials har en objektliste). Funktionspladsen vaelges
med FL-soegningen i Location-sektionen paa Details og gemmes i
FunctionalLocation, som paa Measuring Point.

Dokumenttype og dokumentlink er IKKE felter: dokumenterne ligger i
biblioteket (dokumentpopuppen), ikke som et link paa raekken - se
Provision-EqMatLists.ps1. Cellen Documentation aabner popuppen.
"""
import domain_config as cfg
import domain_parts as dp
from build_helpers import card

# SEKTIONERNE (UX-review M2, Equipment-mockuppen): hver sektion er sine
# egne raekker af fire celler, der ombryder til to og een. FL, TEXT, DOCS
# og PLANT er de celler, der ikke er et almindeligt felt fra SECTIONS.
SPECIAL = {"FL", "TEXT", "DOCS", "PLANT", "EQNO"}
SECTIONS = [
    ("Ident", "Identification", ["RequestType", "PLANT", "EquipmentCategory", "EQNO", "TEXT"]),
    ("Loc", "Location", ["FL", "RoomCoordinates", "Placement"]),
    ("Mfr", "Manufacturer", ["Manufacturer", "TypeDesignation", "SerialNumber", "ClassData"]),
    ("Warranty", "Warranty", ["WarrantyStart", "WarrantyEnd"]),
    ("Docs", "Documents", ["DOCS"]),
]
FORM_ORDER = [k for _k, _t, keys in SECTIONS for k in keys]
NOT_IN_GRID = {cfg.FL_FIELD}

# Sidepanelets faner (issue #430): det, der flyttes fra Details.
TABBED = bool(getattr(cfg, "ROW_PANEL_ENABLED", False)
              and getattr(cfg, "ROW_EDITOR_TAB_VAR", None))
# Ingen Objects-fane (issue #485): FL bliver paa Details.
OBJECT_KEYS = []
# Garantien staar paa Details (issue #531) - Documents er kun dokumenterne.
DOC_KEYS = ["DOCS"]


def _detail_sections():
    """Details-fanens sektioner: SECTIONS uden det, Objects og Documents
    har. En sektion, der bliver tom, udelades (Documents)."""
    moved = set(OBJECT_KEYS) | set(DOC_KEYS)
    out = []
    for key, title, keys in SECTIONS:
        rest = [k for k in keys if k not in moved]
        if rest:
            out.append((key, title, rest))
    return out


def _cell(key, width=dp.CELL_W):
    if key == "FL":
        return dp.grid_cell("conDomFl", "Functional location",
                            dp.build_fl_picker(width), width=width)
    if key == "TEXT":
        return dp.text_cell(width)
    if key == "DOCS":
        # I fanerne: kun antallet - Documents-fanen ER dokumenterne.
        return dp.docs_count_cell(width) if TABBED else dp.docs_cell(width)
    if key == "PLANT":
        return dp.plant_cell(width)
    if key == "EQNO":
        value = ('If(IsBlank(varDomActiveRowId), "Set by SAP", '
                 'Coalesce(LookUp(colDomRows, RowId = varDomActiveRowId).EquipmentNumber, ""))')
        return dp.grid_cell(
            "conDomEquipmentNumber", "Equipment number",
            dp.text_ctrl("txtDomEquipmentNumber", value, size=13, height=36,
                         wrap="false", accessible='"Equipment number: " & Self.Text'),
            width=width)
    return dp.field_grid_cell(key, width=width)


# EQUIPMENTS EGNE KRAV (R2-040)
# ----------------------------
# En FAERDIG raekke kraever ogsaa udstyrstypen (SAP IE01: EQTYP) og
# funktionspladsen - de to felter ud over beskrivelse og vaerk, der har
# Required i MD_FLCharacteristic (docs/16-spool-regler.md: "Description,
# Beskrivelse, Plant, Equipment Category og Func. location"). Mangler de,
# gemmes raekken som kladde med besked om, hvad der mangler.
#
# Garanti til foer garanti fra er en FORKERT vaerdi, ikke en manglende -
# den stoppes ogsaa paa en kladde (samme moenster som Materials' min/max).
def _row_rules():
    return [
        (f'IsBlank(Trim(Coalesce({dp._var("EquipmentCategory")}, "")))',
         "Equipment type is required."),
        (f'IsBlank(Trim(Coalesce({dp._var(cfg.FL_FIELD)}, "")))',
         "A functional location is required."),
    ]


WARRANTY_BAD = (f'!IsBlank({dp._var("WarrantyStart")}) && !IsBlank({dp._var("WarrantyEnd")}) && '
                f'{dp._var("WarrantyEnd")} < {dp._var("WarrantyStart")}')
WARRANTY_MSG = "Warranty to must be on or after warranty from."


def save_fx(status):
    """domain_parts' gem, plus Equipments egne krav (R2-040)."""
    return dp.save_row_fx(status, required=_row_rules(),
                          always=[(WARRANTY_BAD, WARRANTY_MSG)])


def build_form(panel=False):
    dp.check_form_order(FORM_ORDER, SPECIAL, NOT_IN_GRID)
    form_width = dp.PANEL_FORM_W if panel else dp.FORM_W
    cell_width = dp.PANEL_CELL_W if panel else dp.CELL_W
    # Med sidepanel staar "* Required" i panelets overskrift (issue #431),
    # saa formularen starter direkte med den foerste sektion.
    head = [] if panel else [dp.form_head("Row details")]
    secs = []
    for key, title, keys in (_detail_sections() if panel and TABBED else SECTIONS):
        rows = dp.grid_rows(f"conDomGrid{key}",
                            [_cell(k, dp.panel_cell_w(k, cell_width)) for k in keys],
                            container_w=form_width, columns=2 if panel else None,
                            cell_width=cell_width)
        if "FL" in keys:
            # Soegningens svar under raekken med FL i.
            rows.append(dp.build_fl_msg())
        secs.append((key, title, None, rows))
    rows = dp.sectioned(secs)
    buttons = dp.form_buttons(save_fx, "Save row", "New row")
    return card("conDomFormCard", head + rows + dp.form_footer(buttons))


def _panel_rows(key, keys):
    return dp.grid_rows(f"conDomGrid{key}",
                        [_cell(k, dp.panel_cell_w(k, dp.PANEL_CELL_W)) for k in keys],
                        container_w=dp.PANEL_FORM_W, columns=2,
                        cell_width=dp.PANEL_CELL_W)


def editor_panel_content(form, extras=()):
    """Fanerne Details og Documents (issue #430) - Materials' moenster
    (domain_parts.editor_tabs) uden Objects-fanen (issue #485): udstyret
    har een funktionsplads, og dens soegning staar paa Details. Documents:
    antallet af dokumenter og ModernAttachments-kontrollen - garantien
    staar paa Details (issue #531)."""
    docs = dp.sectioned([("Docs", "Documents", None, _panel_rows("Docs", DOC_KEYS))])
    # Dokumentkontrollen under antallet - samme krop og hoejde som
    # Materials' Documents-fane; panelet scroller, hvis der mangler plads.
    documents = docs + [dp.docs_tab_body()]
    return dp.editor_tabs(form, extras, objects=None, documents=documents)


# ---------------------------------------------------------------------------
# Listen - kolonnerne, som issue #68 skriver dem
# ---------------------------------------------------------------------------
# Appens sprog er engelsk (tools/check_language.py), saa overskrifterne er
# formularens egne etiketter - i issuets raekkefoelge. "Status" i eq.png er
# feltet RequestType; det hedder nu REQUEST TYPE, og statusmaerket foerst
# hedder STATUS som i Materials og MP (R2-072).
#
# (overskrift, udtryk, mindstebredde). Se domain_parts.build_list for, hvad
# en plads er.
TYPE = ("REQUEST TYPE", "ThisItem.RequestType", 90)
PLANT = ("PLANT", "ThisItem.Plant", 70)
EQNO = ("EQUIPMENT NUMBER", "ThisItem.EquipmentNumber", 120)
DESC = (cfg.TEXT_LABEL.upper(),
        f'If(IsBlank(Trim(ThisItem.{cfg.C_TEXT})), "(no text)", ThisItem.{cfg.C_TEXT})', 130)
EQTYPE = ("TYPE", "ThisItem.EquipmentCategory", 110)
FL_C = ("FUNCTIONAL LOCATION", f"ThisItem.{cfg.FL_FIELD}", 150)
# EET fast saet kolonner (issue #204): de samme seks, Compact viste.
# Compact/All columns er vaek i baade Equipment og Materials - resten af
# raekkens felter ses i Details.
SLOTS = [TYPE, DESC, FL_C, EQTYPE, PLANT]



def build_rows():
    return dp.build_list(SLOTS, "STATUS",
                         "Search FL, equipment no., serial no., description")


# De faelles raekkeikoner (issue #485): Edit, Documents, Copy og Delete.
# Intet Objects-ikon (udstyret har een funktionsplads, i formularen), ingen
# More-menu og ingen Details.
dp.configure(row_actions=dp.standard_row_actions(
    docs_fx=((dp.load_row_fx() + f';\nSet({cfg.ROW_EDITOR_TAB_VAR}, "Documents");\n'
              + dp.open_active_docs_fx()) if TABBED else dp.open_docs_fx()),
    docs_n="ThisItem.FileCount"))
# Paa en telefon (issue #508): producenten og garantien (begge paa
# Details, issue #531) er klappet sammen - ingen kraevede felter. En garanti, der slutter foer
# den starter, holder sin sektion aaben.
dp.configure(mobile_folds={"Mfr": (None, None), "Warranty": (WARRANTY_BAD, None)})
