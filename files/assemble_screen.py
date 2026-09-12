# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"c:\Users\PKBJE\.copilot\session-state\e93d42be-2820-4dcf-8776-8328cfe9a7c9\files")
from gen_screen import Ctrl, render_screen, C_APP_BG
from build_helpers import group
from build_hero import build_hero
from build_plan_header import build_plan_header
from build_items import build_items_section
from build_tasklist import build_tasklist_section, build_dispatch_section, build_email_fab
from build_modal import build_tasklist_picker_modal, build_modal_backdrop

OUT_DIR = r"C:\Temp\powerapp-vhplan"


def main():
    hero = build_hero()
    planHeader = build_plan_header()
    itemsSplit = build_items_section()
    tasklistSection = build_tasklist_section()
    dispatchSection = build_dispatch_section()

    shell = group(
        "conVhpShell", [hero, planHeader, itemsSplit, tasklistSection, dispatchSection],
        direction="Vertical", gap=20,
        height=(
            "IfError(40 + conVhpHero.Height + 20 + conVhpPlanCard.Height + 20 + conVhpItemsSplit.Height + 20 + "
            "conVhpOpsCard.Height + 20 + conVhpDispatchCard.Height + 120, 3000)"
        ),
        pad=(20, 24, 24, 24))

    root = group(
        "conVhpRoot", [shell], direction="Vertical", height="Parent.Height", width="Parent.Width",
        overflow_y="Scroll", fill=C_APP_BG)

    backdrop = build_modal_backdrop()
    modal = build_tasklist_picker_modal()
    emailFab = build_email_fab()

    screen_props = {
        "Fill": C_APP_BG,
    }

    content = render_screen("ScreenVhPlan", screen_props, [root, backdrop, modal, emailFab])

    out_path = OUT_DIR + r"\ScreenVhPlan.pa.yaml"
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print("Wrote", out_path, "-", content.count(chr(10)) + 1, "lines")


if __name__ == "__main__":
    main()
