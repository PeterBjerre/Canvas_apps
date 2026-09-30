# -*- coding: utf-8 -*-
"""Samler Functional Location-skaermen -> ../ScreenFunctionalLocation.pa.yaml.

APPENS EGEN KOMPOSITION. Delene staar i fl_parts.py (skaermen),
fl_validation.py (den automatiske validering) og fl_save.py (gem/indsend). Reglerne, de
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
from side_nav import side_nav
import fl_config as cfg
import fl_parts as P
import fl_save as S


ME = "Set(varFlMe, Lower(User().Email))"


def load_part():
    """Hent anmodningen bag ?reqid=, naar det er en anden end den viste.

    Egen funktion, saa BIO SAP App kan koere den KUN naar hubben beder om
    en anden anmodning (dens open_block) - ikke ved hvert skaermbesoeg.
    Stod den i OnVisible dér, overskrev et besoeg en ny anmodning med den
    gamle, fordi "New request" ikke nulstiller gblFlReqId (REVIEW.md D23)."""
    return (
        "If(\n"
        '    !IsBlank(Param("reqid")) && varFlRequestGuid <> Param("reqid"),\n'
        "    " + S.load_fx().replace("\n", "\n    ") + ";\n"
        "    // Beskederne gemmes ikke - de regnes igen, automatisk (issue #77).\n"
        "    Select(btnFlVerify)\n"
        ")"
    )


def ensure_row_part():
    """En tom anmodning har altid een raekke at skrive i."""
    return "If(CountRows(colFlRows) = 0, " + P.add_row_fx().replace("\n", " ") + ")"


def on_visible():
    return ME + ";\n" + load_part() + ";\n" + ensure_row_part()


def build_screen():
    # EEN spalte: Validation, Classes og strukturen. Save draft, Submit og
    # New request staar i bjaelken (issue #77). Detaljerne er en popup, med
    # sloeret FOERST, saa det ligger bagved.
    root = app_frame("Fl", P.build_bar(),
                     [P.build_rows(), P.build_classes(), P.build_structure()])
    # Sidebaren: skinnen efter rammen, det aabne panel SIDST (tools/side_nav.py).
    nav, overlay = side_nav("Fl", "functionallocation")
    return render_screen(cfg.SCREEN, {"Fill": C_APP_BG, "OnVisible": on_visible()},
                         [root, *nav, P.build_backdrop(), P.build_detail(),
                          *overlay, *P.build_submit_confirm()])


def main():
    content = build_screen()
    out = os.path.join(OUT_DIR, cfg.SCREEN + ".pa.yaml")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print("Wrote", out, "-", content.count(chr(10)) + 1, "lines")


if __name__ == "__main__":
    main()
