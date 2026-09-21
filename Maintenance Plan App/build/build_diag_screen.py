# -*- coding: utf-8 -*-
"""
Minimal diagnostic screen to isolate why ScreenVhPlan's nested AutoLayout content
isn't rendering in Power Apps Studio. Contains:
1. A big red banner at screen root level (tests basic control rendering/sync).
2. A single card replicating the exact nested pattern used in ScreenVhPlan
   (card > grid > row > cell > label-row(label+star) > dropdown) to test if
   THAT specific nesting pattern is the problem.
3. A simple flat card (no deep nesting) with a label + dropdown directly, for comparison.
"""
import sys
sys.path.insert(0, r"c:\Users\PKBJE\.copilot\session-state\e93d42be-2820-4dcf-8776-8328cfe9a7c9\files")
from gen_screen import (Ctrl, render_screen, C_APP_BG, C_CARD_BG, C_CARD_BORDER, C_TITLE,
                        C_MUTED, C_REQUIRED, C_WHITE, C_INVALID_FG)
from build_helpers import group, text_ctrl, button, dropdown, field_cell, two_col_row

OUT_DIR = r"C:\Temp\powerapp-vhplan"


def main():
    banner = text_ctrl(
        "txtDiagBanner", "\"TEST BANNER - HVIS DU KAN SE DETTE, ER AENDRINGER LIVE (v3)\"",
        size=22, weight="Semibold", color=C_WHITE, height=60, wrap="false",
        extra={
            "Fill": C_INVALID_FG,
            "Align": "Align.Center",
            "Width": "Parent.Width",
            "X": "0",
            "Y": "0",
        })

    # Replica of the exact nested pattern used in ScreenVhPlan (card > grid > row > cell > label-row > dropdown)
    drpTest = dropdown("drpDiagPlant", "colVhpPlantCodes", "LookUp(colVhpPlantCodes, Value = varVhpPlan.Plant)",
                        item_display="ThisItem.Value")
    cell = field_cell("conDiagCellPlant", "Plant (nested pattern)", drpTest, required=True)
    row = two_col_row("conDiagRow1", cell,
                       group("conDiagCellSpacer", [], height=62, width="(Parent.Width - 20) / 2"))
    grid = group("conDiagGrid", [row], direction="Vertical", gap=16, height=62)

    cardTitle = text_ctrl("txtDiagCardTitle", "\"Diagnostic Card (nested pattern)\"", size=19, weight="Semibold",
                          height=26, wrap="false")
    nestedCard = group("conDiagNestedCard", [cardTitle, grid], direction="Vertical", gap=14, height=26 + 14 + 62,
                       fill=C_CARD_BG, border_color=C_CARD_BORDER, radius=14, pad=(18, 18, 18, 18))

    # Flat/simple card: label + dropdown as DIRECT children, no extra nesting layers
    flatTitle = text_ctrl("txtDiagFlatTitle", "\"Diagnostic Card (flat, no extra nesting)\"", size=19,
                          weight="Semibold", height=26, wrap="false")
    flatLabel = text_ctrl("txtDiagFlatLabel", "\"Plant (flat)\"", size=13, weight="Semibold", height=20,
                          wrap="false")
    flatDropdown = dropdown("drpDiagFlatPlant", "colVhpPlantCodes",
                             "LookUp(colVhpPlantCodes, Value = varVhpPlan.Plant)", item_display="ThisItem.Value")
    flatCard = group("conDiagFlatCard", [flatTitle, flatLabel, flatDropdown], direction="Vertical", gap=8,
                     height=26 + 8 + 20 + 8 + 36, fill=C_CARD_BG, border_color=C_CARD_BORDER, radius=14,
                     pad=(18, 18, 18, 18))

    shell = group("conDiagShell", [nestedCard, flatCard], direction="Vertical", gap=20, height=3000,
                 pad=(80, 24, 24, 24))
    root = group("conDiagRoot", [shell], direction="Vertical", height="Parent.Height", width="Parent.Width",
                overflow_y="Scroll", fill=C_APP_BG)

    content = render_screen("ScreenVhPlanDiag", {"Fill": C_APP_BG}, [root, banner])

    out_path = OUT_DIR + r"\ScreenVhPlanDiag.pa.yaml"
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print("Wrote", out_path, "-", content.count(chr(10)) + 1, "lines")


if __name__ == "__main__":
    main()
