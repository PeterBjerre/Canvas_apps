# -*- coding: utf-8 -*-
"""
Measuring Points EGNE dele: formularens felter og listens kolonner
(issue #210, fase 1 - skelettet).

Byggeklodserne - gitteret, knapperne, pillerne, dokumentcellen,
FL-comboboksen, listen, detaljerne og indsend - er faelles med Equipment
og Materials og staar i tools/domain_parts.py. Her staar kun det, der er
Measuring Points: hvilke felter, i hvilken raekkefoelge, og hvilke
kolonner listen viser.

Fase 2 laegger de betingede sektioner (kun typens felter vises),
karakteristik-opslaget og valideringen oven paa denne flade formular.
"""
import domain_config as cfg
import domain_parts as dp
from build_helpers import card

SPECIAL = {"FL", "TEXT", "DOCS", "PLANT"}
FORM_ORDER = [
    # Hvor sidder det
    "PLANT", "FL", "TEXT", "ExistsInSap",
    # Findes det, eller skal det oprettes
    "MeasuringPoint", "MeasuringPointType", "Characteristic",
    "CharacteristicDescription",
    # Karakteristikken bestemmer enheden
    "CharacteristicUnit", "CharacteristicUnitDescription", "DecimalPlaces",
    "TargetValue",
    # Graenser og taelleren
    "LowerLimit", "UpperLimit", "ExpectedAnnualUsage", "InProdos",
    # Hvor aflaesningen kommer fra
    "ProdosTag", "ProdosCounterExists", "CounterCreateIn", "DOCS",
    # Resten
    "Remarks",
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
    dp.check_form_order(FORM_ORDER, SPECIAL, NOT_IN_GRID)
    head = dp.form_head("Measuring Point Form")
    rows = dp.grid_rows("conDomGrid", [_cell(k) for k in FORM_ORDER])
    # Soegningens svar under den foerste raekke - den med FL i.
    rows.insert(1, dp.build_fl_msg())
    buttons = dp.form_buttons(dp.save_row_fx, "Save row", "New row")
    return card("conDomFormCard", [head] + rows + dp.form_footer(buttons))


# ---------------------------------------------------------------------------
# Listen
# ---------------------------------------------------------------------------
PLANT = ("PLANT", "ThisItem.Plant", 70)
FL_C = ("FUNCTIONAL LOCATION", f"ThisItem.{cfg.FL_FIELD}", 150)
MPNO = ("MEASURING POINT",
        'If(!IsBlank(ThisItem.CreatedMeasuringPointNo), ThisItem.CreatedMeasuringPointNo, '
        '!IsBlank(ThisItem.MeasuringPoint), ThisItem.MeasuringPoint, "New")', 130)
TYPE = ("TYPE", "ThisItem.MeasuringPointType", 120)
CHAR = ("CHARACTERISTIC", "ThisItem.Characteristic", 130)
UNIT = ("UNIT", "ThisItem.CharacteristicUnit", 70)
TAG = ("PRODOS TAG", "ThisItem.ProdosTag", 110)
DESC = (cfg.TEXT_LABEL.upper(),
        f'If(IsBlank(Trim(ThisItem.{cfg.C_TEXT})), "(no text)", ThisItem.{cfg.C_TEXT})', 130)
SLOTS = [
    # (Compact, All)
    (PLANT, PLANT),
    (FL_C, FL_C),
    (MPNO, MPNO),
    (TYPE, TYPE),
    (CHAR, CHAR),
    (UNIT, UNIT),
    (TAG, TAG),
    (None, DESC),
    (None, ("DECIMAL PLACES", dp.num_text("DecimalPlaces"), 110)),
    (None, ("EXISTS IN SAP", "ThisItem.ExistsInSap", 100)),
    (None, ("IN PRODOS", "ThisItem.InProdos", 90)),
    (None, ("DOCUMENTS",
            'If(ThisItem.FileCount > 0, Text(ThisItem.FileCount) & " file(s)", "-")', 90)),
]


def build_rows():
    return dp.build_list(SLOTS, "STATUS",
                         "Search FL, measuring point, characteristic, PRODOS tag")
