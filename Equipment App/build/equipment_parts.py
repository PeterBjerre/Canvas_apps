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
SPECIAL = {"FL", "TEXT", "DOCS", "PLANT"}
SECTIONS = [
    ("Ident", "Identification", ["PLANT", "RequestType", "EquipmentCategory", "TEXT"]),
    ("Loc", "Location", ["FL", "RoomCoordinates", "Placement"]),
    ("Mfr", "Manufacturer", ["Manufacturer", "TypeDesignation", "SerialNumber", "ClassData"]),
    ("Warranty", "Warranty and documents", ["WarrantyStart", "WarrantyEnd", "DOCS"]),
]
FORM_ORDER = [k for _k, _t, keys in SECTIONS for k in keys]
NOT_IN_GRID = {cfg.FL_FIELD}


def _cell(key):
    if key == "FL":
        return dp.grid_cell("conDomFl", "Functional location",
                            dp.build_fl_picker(dp.CELL_W))
    if key == "TEXT":
        return dp.text_cell()
    if key == "DOCS":
        return dp.docs_cell()
    if key == "PLANT":
        return dp.plant_cell()
    return dp.field_grid_cell(key)


def build_form():
    dp.check_form_order(FORM_ORDER, SPECIAL, NOT_IN_GRID)
    head = dp.form_head("Row details")
    secs = []
    for key, title, keys in SECTIONS:
        rows = dp.grid_rows(f"conDomGrid{key}", [_cell(k) for k in keys])
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
