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
                          clear_form_fx)


def on_visible():
    return (
        "Set(varDomMe, Lower(User().Email));\n"
        + refresh_rows_fx() + ";\n"
        + clear_form_fx()
    )


def build_screen():
    # DOKUMENTERNE LIGGER NEDERST
    #
    # De sad foer i en skinne til hoejre for formularen. Det var forkert af
    # to grunde: ruden hoerer til den VALGTE raekke, og raekken vaelges i
    # listen laengere nede - saa oejet skulle hele vejen op igen for at se,
    # hvad der skete. Og skinnen gjorde formularen smal, hvilket er dyrt,
    # naar den har fire kolonner.
    #
    # Raekkefoelgen foelger nu arbejdet: udfyld, gem, vaelg i listen, laeg
    # dokumenter paa, indsend.
    shell = group("conDomShell",
                  [build_bar(), build_form(), build_rows(),
                   build_attachments(), build_submit()],
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
