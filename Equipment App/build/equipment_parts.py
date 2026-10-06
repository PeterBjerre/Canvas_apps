# -*- coding: utf-8 -*-
"""
Equipments EGNE dele: formularens felter og listens kolonner (issue #68).

Skaermen er tegnet efter eq.png i app-mappen - HTML-projektets
udstyrsformular. Byggeklodserne - gitteret, knapperne, pillerne,
dokumentcellen, FL-comboboksen, listen og indsend - er faelles med
Materials og staar i tools/domain_parts.py. Her staar kun det, der er
Equipments: hvilke felter, i hvilken raekkefoelge, og hvilke kolonner
listen viser.

FORMULAREN - I KOLONNE-ORDEN, SOM eq.png
---------------------------------------
    Equipment Form  * Required
    [ Type          ][ Manufacturer     ][ Class data        ][ Warranty from ]
    [ Plant         ][ Type designation ][ Room coordinates  ][ Warranty to   ]
    [ Description   ][ Serial number    ][ Placement text    ][ Documentation ]
    [ Equipment type][ Func. location   ]
    (Plant: X) (Row status: ...)   [Save draft][Save][New row]

Equipment number, Func. loc. 1 og Functional location 2 er fjernet fra
formularen (issue #94). FL-soegningen er den eneste maade at vaelge en
funktionsplads paa, og udstyrsnummeret er SAP's - det vises stadig i
listen og i detaljerne (domain_config.READ_FIELDS). En gemt raekke
slettes med ikonet i listens Actions-kolonne, ikke fra formularen.

Paa en tablet staar kolonne 1 og 2 side om side over 3 og 4; paa en
telefon under hinanden.

Dokumenttype og dokumentlink er IKKE felter: dokumenterne ligger i
biblioteket (dokumentpopuppen), ikke som et link paa raekken - se
Provision-EqMatLists.ps1. Cellen Documentation aabner popuppen.
"""
import attflows
import domain_config as cfg
import domain_parts as dp
from build_helpers import card

# eq.png's fire kolonner. FL, TEXT, DOCS og PLANT er de celler, der ikke er
# et almindeligt felt fra SECTIONS.
SPECIAL = {"FL", "TEXT", "DOCS", "PLANT"}
COLUMNS = [
    ["RequestType", "PLANT", "TEXT", "EquipmentCategory"],
    ["Manufacturer", "TypeDesignation", "SerialNumber", "FL"],
    ["ClassData", "RoomCoordinates", "Placement"],
    ["WarrantyStart", "WarrantyEnd", "DOCS"],
]
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
    dp.check_form_order([k for col in COLUMNS for k in col], SPECIAL, NOT_IN_GRID)
    head = dp.form_head("Equipment Form")
    grid = dp.grid_columns("conDomGrid", [[_cell(k) for k in col] for col in COLUMNS])
    buttons = dp.form_buttons(dp.save_row_fx, "Save row", "New row")
    return card("conDomFormCard",
                [head, grid, dp.build_fl_msg()] + dp.form_footer(buttons))


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
SLOTS = [
    # (Compact, All)
    (TYPE, TYPE),
    (PLANT, PLANT),
    (FL_C, EQNO),
    (EQNO, DESC),
    (DESC, EQTYPE),
    (EQTYPE, ("MANUFACTURER", "ThisItem.Manufacturer", 110)),
    (None, ("TYPE DESIGNATION", "ThisItem.TypeDesignation", 110)),
    (None, ("SERIAL NUMBER", "ThisItem.SerialNumber", 110)),
    (None, FL_C),
    (None, ("CLASS DATA", "ThisItem.ClassData", 100)),
    (None, ("ROOM COORDINATES", "ThisItem.RoomCoordinates", 110)),
    (None, ("PLACEMENT TEXT", "ThisItem.Placement", 120)),
    (None, ("WARRANTY FROM", dp.date_text("WarrantyStart"), 100)),
    (None, ("WARRANTY TO", dp.date_text("WarrantyEnd"), 100)),
    # Dokumenttype og -link: dokumenterne i biblioteket, ikke felter paa
    # raekken. Antallet og mappen, de ligger i.
    (None, ("DOCUMENTS",
            'If(ThisItem.FileCount > 0, Text(ThisItem.FileCount) & " file(s)", "-")', 90)),
    (None, ("DOCUMENT LINK",
            f'If(IsBlank(ThisItem.ItemKey), "-", "{attflows.LIBRARY}/" & ThisItem.ItemKey)',
            200)),
]


def build_rows():
    return dp.build_list(SLOTS, "STATUS",
                         "Search FL, equipment no., serial no., description")
