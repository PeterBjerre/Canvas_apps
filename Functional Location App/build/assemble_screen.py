# -*- coding: utf-8 -*-
"""Samler Functional Location-skaermen -> ../ScreenFunctionalLocation.pa.yaml.

APPENS EGEN KOMPOSITION. Delene staar i fl_parts.py (skaermen),
fl_validation.py (Verify) og fl_save.py (gem/indsend). Reglerne, de
haandhaever, staar i docs/31-functional-location-regler.md.

DATAHENTNINGEN LIGGER I OnVisible, IKKE I App.OnStart - og kun dyblinket
(?reqid=) henter noget. Alle andre starter med een tom raekke, ligesom
HTML-siden (app-functional-location.js:399).
"""
# tools/ paa sys.path. De faelles filer - gen_screen.py, build_helpers.py,
# check_layout.py - ligger DER. sys.path er procesglobal, saa det raekker
# at saette den her i indgangen.
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(
    _os.path.dirname(_os.path.abspath(__file__)))), "tools"))

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from gen_screen import render_screen, C_APP_BG, OUT_DIR
from build_helpers import app_frame
import fl_config as cfg
import fl_parts as P
import fl_save as S


def on_visible():
    return (
        "Set(varFlMe, Lower(User().Email));\n"
        "If(\n"
        '    !IsBlank(Param("reqid")) && varFlRequestGuid <> Param("reqid"),\n'
        "    " + S.load_fx().replace("\n", "\n    ") + "\n"
        ");\n"
        "If(CountRows(colFlRows) = 0, " + P.add_row_fx().replace("\n", " ") + ")"
    )


def build_screen():
    # EEN spalte: Validation, Classes, strukturen og indsend. Detaljerne og
    # eksporten er popups, med sloeret FOERST, saa det ligger bagved.
    root = app_frame("Fl", P.build_bar(),
                     [P.build_rows(), P.build_classes(), P.build_structure(),
                      P.build_submit()])
    return render_screen(cfg.SCREEN, {"Fill": C_APP_BG, "OnVisible": on_visible()},
                         [root, P.build_backdrop(), P.build_detail(), P.build_export()])


def main():
    content = build_screen()
    out = os.path.join(OUT_DIR, cfg.SCREEN + ".pa.yaml")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print("Wrote", out, "-", content.count(chr(10)) + 1, "lines")


if __name__ == "__main__":
    main()
