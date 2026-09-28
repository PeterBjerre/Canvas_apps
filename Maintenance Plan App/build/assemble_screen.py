# -*- coding: utf-8 -*-
"""
Samler ScreenVhPlan.pa.yaml.

Hver sektion regner selv sin hoejde ud af sit indhold (se
gen_screen.stack_height). Ingen Height-formel refererer en anden kontrol -
det var den cirkelreference, der gav baade kaskade-vaeksten og de klippede
kort.
"""
# tools/ paa sys.path. De tre store faellesfiler - gen_screen.py,
# build_helpers.py og check_layout.py - ligger DER og ikke i en kopi pr.
# app-mappe. sys.path er procesglobal, saa det raekker at saette den her i
# indgangen: alt hvad builderne importerer bagefter, finder dem selv.
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(
    _os.path.dirname(_os.path.abspath(__file__)))), "tools"))

import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import Ctrl, render_screen, C_APP_BG, OUT_DIR
from build_helpers import app_frame
from build_hero import build_top_bar, HELP_ON, HELP_ACTION, focus_border
from gen_screen import C_CARD_BORDER
from side_nav import side_nav
from build_plan_header import build_plan_header
from build_items import build_items_section, build_object_list_modal
from build_tasklist import build_tasklist_section
from build_modal import (build_tasklist_picker_modal, build_longtext_modal,
                         build_modal_backdrop)


def build_screen():
    # Sektionen, et klik i progressbaren peger paa, faar en tyk kant.
    items = build_items_section()
    for card in items.children:
        focus_border(card, (2,), C_CARD_BORDER)
    sections = [
        focus_border(build_plan_header(), (1,), C_CARD_BORDER),
        items,
        # Pakkematricen er nu en fane i Tasklist-sektionen, ikke et kort
        # for sig. Se build_tasklist._tab_bar.
        focus_border(build_tasklist_section(), (3, 4), C_CARD_BORDER),
        # Dispatch and Control og Save to SharePoint er fjernet (issue #54).
        # Save draft og Submit staar for enden af progressbaren i
        # topbjaelken (build_hero.py), og reglerne bag Validate er de
        # navngivne formler i build_status.py.
    ]

    # RAMMEN: topbjaelken i en header, der ikke scroller, og sektionerne
    # direkte i en krop, der goer. Se build_helpers.app_frame.
    root = app_frame("Vhp", build_top_bar(), sections, body_gap=20)

    # Sidebaren: skinnen efter rammen, det aabne panel SIDST (tools/side_nav.py).
    rail, overlay = side_nav("Vhp", "vhplan", HELP_ON, HELP_ACTION)
    return render_screen("ScreenVhPlan", {"Fill": C_APP_BG},
                         [root, rail,
                          build_modal_backdrop(), build_tasklist_picker_modal(),
                          build_longtext_modal(), build_object_list_modal(), *overlay])


def main():
    content = build_screen()
    out_path = os.path.join(OUT_DIR, "ScreenVhPlan.pa.yaml")
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print("Wrote", out_path, "-", content.count(chr(10)) + 1, "lines")


if __name__ == "__main__":
    main()
