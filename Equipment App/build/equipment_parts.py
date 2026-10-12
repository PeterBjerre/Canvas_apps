# -*- coding: utf-8 -*-
"""
Equipments EGNE dele: formularens felter og listens kolonner (issue #68).

Skaermen er tegnet efter eq.png i app-mappen - HTML-projektets
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
    ─ Warranty and documents
    [ Warranty from ][ Warranty to      ][ Documentation     ]
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

Dokumenttype og dokumentlink er IKKE felter: dokumenterne ligger i
biblioteket (dokumentpopuppen), ikke som et link paa raekken - se
Provision-EqMatLists.ps1. Cellen Documentation aabner popuppen.
"""
import attflows
import domain_config as cfg
import domain_parts as dp
from build_helpers import card

# SEKTIONERNE (UX-review M2, Equipment-mockuppen): hver sektion er sine
# egne raekker af fire celler, der ombryder til to og een. FL, TEXT, DOCS
# og PLANT er de celler, der ikke er et almindeligt felt fra SECTIONS.
SPECIAL = {"FL", "TEXT", "DOCS", "PLANT", "EQNO"}
SECTIONS = [
    ("Ident", "Identification", ["PLANT", "RequestType", "EquipmentCategory", "EQNO", "TEXT"]),
    ("Loc", "Location", ["FL", "RoomCoordinates", "Placement"]),
    ("Mfr", "Manufacturer", ["Manufacturer", "TypeDesignation", "SerialNumber", "ClassData"]),
    ("Warranty", "Warranty and documents", ["WarrantyStart", "WarrantyEnd", "DOCS"]),
]
FORM_ORDER = [k for _k, _t, keys in SECTIONS for k in keys]
NOT_IN_GRID = {cfg.FL_FIELD}


def _cell(key, width=dp.CELL_W):
    if key == "FL":
        return dp.grid_cell("conDomFl", "Functional location",
                            dp.build_fl_picker(width), width=width)
    if key == "TEXT":
        return dp.text_cell(width)
    if key == "DOCS":
        return dp.docs_cell(width)
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


def build_form(panel=False):
    dp.check_form_order(FORM_ORDER, SPECIAL, NOT_IN_GRID)
    form_width = dp.PANEL_FORM_W if panel else dp.FORM_W
    cell_width = dp.PANEL_CELL_W if panel else dp.CELL_W
    head = dp.form_head("Row details")
    secs = []
    for key, title, keys in SECTIONS:
        rows = dp.grid_rows(f"conDomGrid{key}", [_cell(k, cell_width) for k in keys],
                            container_w=form_width, columns=2 if panel else None,
                            cell_width=cell_width)
        if "FL" in keys:
            # Soegningens svar under raekken med FL i.
            rows.append(dp.build_fl_msg())
        secs.append((key, title, None, rows))
    rows = dp.sectioned(secs)
    buttons = dp.form_buttons(dp.save_row_fx, "Save row", "New row")
    return card("conDomFormCard", [head] + rows + dp.form_footer(buttons))


# ---------------------------------------------------------------------------
# Listen - kolonnerne, som issue #68 skriver dem
# ---------------------------------------------------------------------------
# Appens sprog er engelsk (tools/check_language.py), saa overskrifterne er
# formularens egne etiketter - i issuets raekkefoelge. "Status" i eq.png er
# feltet Type (RequestType); statusmaerket foerst er VALIDATION.
#
# (overskrift, udtryk, mindstebredde). Se domain_parts.build_list for, hvad
# en plads er.
TYPE = ("TYPE", "ThisItem.RequestType", 70)
PLANT = ("PLANT", "ThisItem.Plant", 70)
EQNO = ("EQUIPMENT NUMBER", "ThisItem.EquipmentNumber", 120)
DESC = (cfg.TEXT_LABEL.upper(),
        f'If(IsBlank(Trim(ThisItem.{cfg.C_TEXT})), "(no text)", ThisItem.{cfg.C_TEXT})', 130)
EQTYPE = ("EQUIPMENT TYPE", "ThisItem.EquipmentCategory", 110)
FL_C = ("FUNCTIONAL LOCATION", f"ThisItem.{cfg.FL_FIELD}", 150)
# EET fast saet kolonner (issue #204): de samme seks, Compact viste.
# Compact/All columns er vaek i baade Equipment og Materials - resten af
# raekkens felter ses i Details.
SLOTS = [TYPE, PLANT, FL_C, EQNO, DESC, EQTYPE]



def build_rows():
    return dp.build_list(SLOTS, "STATUS",
                         "Search FL, equipment no., serial no., description")


dp.configure(row_actions=[
    dp.RowAction("btnDomRowDocs",
                 'If(Coalesce(ThisItem.FileCount, 0) > 0, "Documents (" & ThisItem.FileCount & ")", "Documents")',
                 dp.open_docs_fx(), 126, icon="Document",
                 label='"Documents for " & ThisItem.ItemKey'),
    dp.RowAction("btnDomRowOpen", '"Edit"', dp.load_row_fx(), 64,
                 mode=dp.DM_ROW_EDIT),
    dp.RowAction("btnDomRowMore", '"More"', "Set(varDomMoreRowId, ThisItem.RowId)",
                 64, label='"More actions for " & ThisItem.ItemKey', line=2),
])
