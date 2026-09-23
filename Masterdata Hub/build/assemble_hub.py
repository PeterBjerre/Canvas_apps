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
from build_helpers import group
from build_hub import build_bar, build_tiles, build_filters, build_list


def build_screen():
    shell = group("conMdShell",
                  [build_bar(), build_tiles(), build_filters(), build_list()],
                  direction="Vertical", gap=16,
                  # 32, ikke 24: SHELL_W er "App.Width - 64".
                  pad=(20, 32, 40, 32))
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
