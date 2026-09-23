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
                          build_rows, build_details, build_submit, refresh_rows_fx,
                          clear_form_fx, HALF_W)


def on_visible():
    return (
        "Set(varDomMe, Lower(User().Email));\n"
        + refresh_rows_fx() + ";\n"
        + clear_form_fx()
    )


def build_screen():
    # LISTEN OG DOKUMENTERNE SIDE OM SIDE
    #
    # Ruden hoerer til den raekke, der er valgt i listen. Staar de under
    # hinanden, skal oejet hele vejen ned og op igen for at se, hvad
    # valget gjorde. Ved siden af hinanden ses begge dele paa een gang.
    #
    # Under braekpunktet stables de alligevel: to kolonner paa et smalt
    # vindue er een kolonne for meget, og listen har syv.
    # Detaljeruden staar UNDER listen og i den samme kolonne: den
    # hoerer til en raekke i listen, ikke til formularen.
    left = group("conDomLeft", [build_rows(), build_details()],
                 direction="Vertical", gap=16,
                 width=HALF_W)
    right = group("conDomRight", [build_attachments()], direction="Vertical",
                  gap=16, width=HALF_W)
    split = group("conDomSplit", [left, right], direction="Horizontal",
                  gap=20, wrap="true", wrap_rows=1)

    shell = group("conDomShell",
                  [build_bar(), build_form(), split, build_submit()],
                  direction="Vertical", gap=16,
                  # 32, ikke 24: SHELL_W er "App.Width - 64", og
                  # 24+24 er 48. De 16 px forskel gjorde SHELL_W
                  # usand, saa layout-tjekket ikke kunne se, at
                  # topbjaelken var 10 px for bred.
                  pad=(20, 32, 40, 32))
    root = group("conDomRoot", [shell], direction="Vertical",
                 height="Parent.Height", width="Parent.Width",
                 overflow_y="Scroll", fill=C_APP_BG)
    return render_screen(cfg.SCREEN,
                         {"Fill": C_APP_BG, "OnVisible": on_visible()},
                         [root])


def main():
    content = build_screen()
    out = os.path.join(OUT_DIR, cfg.SCREEN + ".pa.yaml")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print("Wrote", out, "-", content.count(chr(10)) + 1, "lines")


if __name__ == "__main__":
    main()
