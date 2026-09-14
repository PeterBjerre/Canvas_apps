# -*- coding: utf-8 -*-
"""Samler ScreenMdHub.pa.yaml."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "shared", "canvas"))

from canvas_dsl import render_screen, C_APP_BG
from canvas_helpers import group
from build_hub import build_bar, build_tiles, build_filters, build_list

OUT_DIR = os.path.join(HERE, "..")


def build_screen():
    shell = group("conMdShell",
                  [build_bar(), build_tiles(), build_filters(), build_list()],
                  direction="Vertical", gap=16, pad=(20, 24, 40, 24))
    root = group("conMdRoot", [shell], direction="Vertical", height="Parent.Height",
                 width="Parent.Width", overflow_y="Scroll", fill=C_APP_BG)
    return render_screen("ScreenMdHub", {"Fill": C_APP_BG}, [root])


def main():
    content = build_screen()
    out = os.path.join(OUT_DIR, "ScreenMdHub.pa.yaml")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print("Wrote", out, "-", content.count(chr(10)) + 1, "lines")


if __name__ == "__main__":
    main()
