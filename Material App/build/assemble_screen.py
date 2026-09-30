# -*- coding: utf-8 -*-
"""Samler Material-skaermen -> ../ScreenMaterial.pa.yaml.

Kompositionen er faelles (tools/domain_app.build_screen); det, der er
appens eget, er formularen og listens kolonner i material_parts.py (issue #67).
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
import material_parts as parts


def build_screen(render=render_screen):
    # render: gen_screen.render_screen - eller BIO SAP App's opsamler.
    return domain_app.build_screen(cfg, parts, render)


def main():
    content = build_screen()
    out = os.path.join(HERE, "..", cfg.SCREEN + ".pa.yaml")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print("Wrote", out, "-", content.count(chr(10)) + 1, "lines")


if __name__ == "__main__":
    main()
