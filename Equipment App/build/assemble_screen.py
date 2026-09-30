# -*- coding: utf-8 -*-
"""Samler Equipment-skaermen -> ../ScreenEquipment.pa.yaml.

Kompositionen er faelles (tools/domain_app.build_screen); det, der er
appens eget, er formularen og listens kolonner i equipment_parts.py (issue #68).
Datahentningen ligger i skaermens OnVisible, ikke i App.OnStart - se
SKILL.md.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "tools"))

from gen_screen import render_screen
import domain_config as cfg
import domain_app
import equipment_parts as parts


def build_screen():
    # render_screen slaas op i DETTE modul ved kaldet, saa BIO SAP App kan
    # bytte den ud (build_screens._capture).
    return domain_app.build_screen(cfg, parts, render_screen)


def main():
    content = build_screen()
    out = os.path.join(HERE, "..", cfg.SCREEN + ".pa.yaml")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print("Wrote", out, "-", content.count(chr(10)) + 1, "lines")


if __name__ == "__main__":
    main()
