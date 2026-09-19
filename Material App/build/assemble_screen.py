# -*- coding: utf-8 -*-
"""Samler skaermen. Ordret ens i de to domaene-build-mapper."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from gen_screen import render_screen, C_APP_BG, OUT_DIR, SHELL_W, RAIL_W, SPLIT_GAP
from build_helpers import group
import domain_config as cfg
from build_domain import (build_bar, build_header, build_items, build_detail,
                          build_attachments, build_savebar)


def build_screen():
    # Listen til venstre, posten til hoejre - og under braekpunktet
    # stablet, fordi to kolonner paa en telefon er een kolonne for meget.
    left = group("conDomLeft", [build_items()], direction="Vertical", gap=16,
                 width=f"If(App.Width < 1000, {SHELL_W}, {RAIL_W})")
    right = group("conDomRight", [build_detail(), build_attachments()],
                  direction="Vertical", gap=16,
                  width=f"If(App.Width < 1000, {SHELL_W}, "
                        f"{SHELL_W} - {RAIL_W} - {SPLIT_GAP})")
    split = group("conDomSplit", [left, right], direction="Horizontal",
                  gap=SPLIT_GAP, wrap="true", wrap_rows=1)

    shell = group("conDomShell",
                  [build_bar(), build_header(), split, build_savebar()],
                  direction="Vertical", gap=16, pad=(20, 24, 40, 24))
    root = group("conDomRoot", [shell], direction="Vertical",
                 height="Parent.Height", width="Parent.Width",
                 overflow_y="Scroll", fill=C_APP_BG)
    return render_screen(cfg.SCREEN, {"Fill": C_APP_BG}, [root])


def main():
    content = build_screen()
    out = os.path.join(OUT_DIR, cfg.SCREEN + ".pa.yaml")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print("Wrote", out, "-", content.count(chr(10)) + 1, "lines")


if __name__ == "__main__":
    main()
