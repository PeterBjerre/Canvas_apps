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

from gen_screen import render_screen, C_APP_BG, OUT_DIR, SHELL_W
from build_helpers import group
import domain_config as cfg
from domain_parts import (build_bar, build_form, build_attachments,
                          build_rows, build_details, build_submit,
                          build_backdrop, refresh_rows_fx, clear_form_fx)


def on_visible():
    return (
        "Set(varDomMe, Lower(User().Email));\n"
        + refresh_rows_fx() + ";\n"
        + clear_form_fx()
    )


def build_screen():
    # BJAELKEN SCROLLER IKKE MED
    #
    # Den laa oeverst i den scrollende beholder sammen med alt andet. En
    # formular med nitten felter er hoejere end skaermen, saa i det
    # oejeblik man ruller ned for at udfylde den, er overskriften, antallet
    # af raekker, Dark-knappen og vejen tilbage til hubben vaek. Og ruller
    # man ikke helt til toppen igen, er titlen der stadig ikke - den
    # ligger 30 px over kanten, mens undertitlen og knapperne kan ses.
    #
    # Det var praecis den melding, der kom: "man kan se knapperne paa
    # oeverste banner, men ikke overskriften".
    #
    # Nu staar bjaelken UDEN FOR scrollbeholderen. Roden er skaermhoej og
    # deler sig i to: en fast top og en rude, der tager resten og
    # scroller. Bjaelken kan dermed ikke rulle vaek, uanset hvor langt ned
    # i formularen man er.
    header = group("conDomHeader", [build_bar()], direction="Vertical",
                   gap=0, pad=(20, 32, 16, 32), fill=C_APP_BG)

    # Hoejden er "resten" skrevet ud. FillPortions ville goere det samme,
    # men regel 9 i layout-tjekket forbyder FillPortions i en lodret
    # container - og den har ret i alle de andre tilfaelde, hvor hoejden
    # er regnet ud af boernene. Her er den ikke; roden er skaermhoej.
    body = group("conDomScroll",
                 [build_form(), build_rows(), build_submit()],
                 direction="Vertical", gap=16, pad=(0, 32, 40, 32),
                 overflow_y="Scroll",
                 # PARENTESEN ER IKKE PYNT. header.h er en SUM -
                 # "36 + (52)" - saa "Parent.Height - 36 + (52)" er
                 # Parent.Height PLUS 16. Ruden blev 104 px for hoej, og
                 # den fejl kan ingen se paa et tal.
                 height=f"Parent.Height - ({header.h})")

    root = group("conDomRoot", [header, body], direction="Vertical", gap=0,
                 height="Parent.Height", width="Parent.Width", fill=C_APP_BG)
    # Sloeret FOER popupperne: kontrollerne tegnes i den raekkefoelge, de
    # staar, saa det, der skal ligge bagved, skal staa foerst.
    return render_screen(cfg.SCREEN,
                         {"Fill": C_APP_BG, "OnVisible": on_visible()},
                         [root, build_backdrop(), build_details(),
                          build_attachments()])


def main():
    content = build_screen()
    out = os.path.join(OUT_DIR, cfg.SCREEN + ".pa.yaml")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print("Wrote", out, "-", content.count(chr(10)) + 1, "lines")


if __name__ == "__main__":
    main()
