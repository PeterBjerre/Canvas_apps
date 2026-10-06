# -*- coding: utf-8 -*-
"""Samler ScreenMdHub.pa.yaml."""
# tools/ paa sys.path. De tre store faellesfiler - gen_screen.py,
# build_helpers.py og check_layout.py - ligger DER og ikke i en kopi pr.
# app-mappe. sys.path er procesglobal, saa det raekker at saette den her i
# indgangen: alt hvad builderne importerer bagefter, finder dem selv.
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(
    _os.path.dirname(_os.path.abspath(__file__)))), "tools"))

import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from gen_screen import render_screen, C_APP_BG, OUT_DIR
from build_helpers import app_frame
from side_nav import side_nav
import build_hub
import approval_flow
import submission_notes as sn
from build_hub import (build_bar, build_tiles, build_filters, build_banner, build_list, build_new_menu,
                       build_closed_peek, build_delete_modal)


def build_screen(render=render_screen):
    """render: gen_screen.render_screen - eller BIO SAP App's opsamler."""
    # RAMMEN: bjaelken i en header, der ikke scroller, og resten i en
    # krop, der goer. Se build_helpers.app_frame.
    root = app_frame("Md", build_bar(), [build_tiles(), build_banner(), build_filters(), build_list()])
    # Sidebaren: skinnen efter rammen, det aabne panel SIDST (tools/side_nav.py).
    nav, overlay = side_nav("Md", "hub")
    # "New request"-menuen ligger oven paa rammen, men under den aabne
    # sidebar.
    # Tallene paa fliserne taelles i colMdScope, som hentes her og ved
    # skift af visning/status (build_hub.SCOPE_REFRESH).
    return render("ScreenMdHub", {"Fill": C_APP_BG,
                                         "OnVisible": build_hub.HUB_ON_VISIBLE},
                         [root, *nav, *build_new_menu(), *build_closed_peek(), *build_delete_modal(), *approval_flow.build_popup(),
                          # Noterne aabnes ogsaa fra Activity, saa de ligger over den (issue #115).
                          *sn.hub_popup(),
                          *overlay])


def main():
    content = build_screen()
    out = os.path.join(OUT_DIR, "ScreenMdHub.pa.yaml")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print("Wrote", out, "-", content.count(chr(10)) + 1, "lines")


if __name__ == "__main__":
    main()
