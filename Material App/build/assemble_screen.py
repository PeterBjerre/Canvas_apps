# -*- coding: utf-8 -*-
"""Samler Material-skaermen.

APPENS EGEN. Den var foer ordret ens med den anden domaeneapps,
og build_all naegtede at bygge, hvis de gled fra hinanden. Den
vagt er vaek: de to apps skal kunne to forskellige ting.
Byggeklodserne er stadig faelles - se tools/domain_parts.py.

DATAHENTNINGEN LIGGER I OnVisible, IKKE I App.OnStart
----------------------------------------------------
OnStart betales af hver bruger hver gang, ogsaa naar appen aabnes for at
kigge. Raekkerne hoerer til skaermen, saa de hentes, naar skaermen vises.
Det er den samme regel som i de to andre apps - se
.github/skills/canvas-build/SKILL.md.
"""
# tools/ paa sys.path. De tre store faellesfiler - gen_screen.py,
# build_helpers.py og check_layout.py - ligger DER og ikke i en kopi pr.
# app-mappe. sys.path er procesglobal, saa det raekker at saette den her i
# indgangen: alt hvad builderne importerer bagefter, finder dem selv.
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
import domain_config as cfg
from domain_parts import (build_bar, build_form, build_attachments,
                          build_rows, build_details, build_submit, build_backdrop,
                          refresh_rows_fx, clear_form_fx)


def on_visible():
    return (
        "Set(varDomMe, Lower(User().Email));\n"
        + refresh_rows_fx() + ";\n"
        + clear_form_fx()
    )


def build_screen():
    # Een spalte: formular, liste, indsend. Dokumenterne og detaljerne er
    # popups (domain_parts), saa listen har hele bredden til sine syv
    # kolonner og fem knapper.
    #
    # RAMMEN: bjaelken i en header, der ikke scroller, og kortene direkte
    # i en krop, der goer - se build_helpers.app_frame.
    root = app_frame("Dom", build_bar(), [build_form(), build_rows(), build_submit()])
    # Sloeret FOER popupperne: kontrollerne tegnes i den raekkefoelge, de
    # staar, saa det, der skal ligge bagved, skal staa foerst.
    return render_screen(cfg.SCREEN,
                         {"Fill": C_APP_BG, "OnVisible": on_visible()},
                         [root, *side_nav("Dom", "material"),
                          build_backdrop(), build_details(), build_attachments()])


def main():
    content = build_screen()
    out = os.path.join(OUT_DIR, cfg.SCREEN + ".pa.yaml")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print("Wrote", out, "-", content.count(chr(10)) + 1, "lines")


if __name__ == "__main__":
    main()
