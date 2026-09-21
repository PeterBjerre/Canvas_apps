# -*- coding: utf-8 -*-
"""Samler skaermen. Ordret ens i de to domaene-build-mapper.

DATAHENTNINGEN LIGGER I OnVisible, IKKE I App.OnStart
----------------------------------------------------
OnStart betales af hver bruger hver gang, ogsaa naar appen aabnes for at
kigge. Raekkerne hoerer til skaermen, saa de hentes, naar skaermen vises.
Det er den samme regel som i de to andre apps - se
.github/skills/canvas-build/SKILL.md.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from gen_screen import render_screen, C_APP_BG, OUT_DIR, SHELL_W
from build_helpers import group
import domain_config as cfg
from build_domain import (build_bar, build_form, build_attachments,
                          build_rows, build_submit, refresh_rows_fx,
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
    left = group("conDomLeft", [build_rows()], direction="Vertical", gap=16,
                 width=HALF_W)
    right = group("conDomRight", [build_attachments()], direction="Vertical",
                  gap=16, width=HALF_W)
    split = group("conDomSplit", [left, right], direction="Horizontal",
                  gap=20, wrap="true", wrap_rows=1)

    shell = group("conDomShell",
                  [build_bar(), build_form(), split, build_submit()],
                  direction="Vertical", gap=16, pad=(20, 24, 40, 24))
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
