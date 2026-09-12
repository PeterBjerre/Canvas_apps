# -*- coding: utf-8 -*-
"""
Samler ScreenVhPlan.pa.yaml.

Hver sektion regner selv sin hoejde ud af sit indhold (se
gen_screen.stack_height). Ingen Height-formel refererer en anden kontrol -
det var den cirkelreference, der gav baade kaskade-vaeksten og de klippede
kort.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import Ctrl, render_screen, C_APP_BG, OUT_DIR
from build_helpers import group
from build_hero import build_hero
from build_plan_header import build_plan_header
from build_items import build_items_section
from build_tasklist import build_tasklist_section, build_dispatch_section, build_email_fab
from build_strategy import build_strategy_section
from build_modal import build_tasklist_picker_modal, build_modal_backdrop


def build_screen():
    sections = [
        build_hero(),
        build_plan_header(),
        build_items_section(),
        build_tasklist_section(),
        build_strategy_section(),
        build_dispatch_section(),
    ]

    # Bundpolstringen giver plads til den svaevende "Send as email"-knap,
    # saa det sidste kort ikke ligger under den.
    shell = group("conVhpShell", sections, direction="Vertical", gap=20, pad=(20, 24, 100, 24))

    root = group("conVhpRoot", [shell], direction="Vertical", height="Parent.Height",
                 width="Parent.Width", overflow_y="Scroll", fill=C_APP_BG)

    return render_screen("ScreenVhPlan", {"Fill": C_APP_BG},
                         [root, build_modal_backdrop(), build_tasklist_picker_modal(), build_email_fab()])


def main():
    content = build_screen()
    out_path = os.path.join(OUT_DIR, "ScreenVhPlan.pa.yaml")
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print("Wrote", out_path, "-", content.count(chr(10)) + 1, "lines")


if __name__ == "__main__":
    main()
