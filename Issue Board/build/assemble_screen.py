# -*- coding: utf-8 -*-
"""Samler Issue Board-skaermen -> ../ScreenIssueBoard.pa.yaml (issue #114).

Delene, formlerne og hentningen staar i ib_parts.py; listerne og
ordforraadet i ib_config.py. Hentningen ligger i OnVisible og koerer kun
foerste gang skaermen vises.
"""
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
import ib_config as cfg
import ib_parts as P


def build_screen(render=render_screen):
    """render: gen_screen.render_screen - eller BIO SAP App's opsamler."""
    root = app_frame(P.P, P.build_bar(), [P.build_list()])
    nav, overlay = side_nav(P.P, cfg.APP_KEY)
    return render(cfg.SCREEN, {"Fill": C_APP_BG, "OnVisible": P.on_visible()},
                  [root, *nav, *overlay, *P.build_form(), *P.build_detail(), *P.build_delete(),
                   *P.build_loading()])


def main():
    content = build_screen()
    out = os.path.join(OUT_DIR, cfg.SCREEN + ".pa.yaml")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print("Wrote", out, "-", content.count(chr(10)) + 1, "lines")


if __name__ == "__main__":
    main()
