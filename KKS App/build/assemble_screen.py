# -*- coding: utf-8 -*-
"""Samler KKS-skaermen -> ../ScreenKks.pa.yaml.

APPENS EGEN KOMPOSITION. Delene, formlerne og hentningen staar i
kks_parts.py; listerne og noegleomraaderne i kks_config.py.

DATAHENTNINGEN LIGGER I OnVisible, IKKE I App.OnStart - og den koerer
kun foerste gang skaermen vises (kks_parts.load_fx).
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
from side_nav import side_nav
import kks_config as cfg
import kks_parts as P


def build_screen(render=render_screen):
    """render: gen_screen.render_screen - eller BIO SAP App's opsamler."""
    root = P.frame(P.build_header(), [P.build_browse(), P.build_results()])
    # Sidebaren: skinnen efter rammen, det aabne panel SIDST (tools/side_nav.py).
    nav, overlay = side_nav("Kks", cfg.APP_KEY)
    # Ventespinneren ligger oeverst, mens noeglerne hentes.
    return render(cfg.SCREEN, {"Fill": C_APP_BG, "OnVisible": P.on_visible()},
                  [root, *nav, *overlay, *P.build_picker(), *P.build_detail(), P.build_loading()])


def main():
    content = build_screen()
    out = os.path.join(OUT_DIR, cfg.SCREEN + ".pa.yaml")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print("Wrote", out, "-", content.count(chr(10)) + 1, "lines")


if __name__ == "__main__":
    main()
