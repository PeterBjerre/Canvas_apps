# -*- coding: utf-8 -*-
"""Layout-tjekket (tools/check_layout.py) paa hver af den samlede apps skaerme.

De andre apps har een skaerm, og deres indgang finder den selv. Her er der
seks, saa hver tjekkes for sig - i sin egen proces, som naar den tjekkes
alene. Tjekket laeser App.pa.yaml ved siden af skaermen, altsaa den
samlede apps."""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(HERE)
TOOL = os.path.join(os.path.dirname(APP_DIR), "tools", "check_layout.py")


def main():
    rc = 0
    for fn in sorted(os.listdir(APP_DIR)):
        if fn.startswith("Screen") and fn.endswith(".pa.yaml"):
            print("--- %s" % fn)
            r = subprocess.run([sys.executable, TOOL, os.path.join(APP_DIR, fn)], cwd=HERE)
            rc = rc or r.returncode
    return rc


if __name__ == "__main__":
    sys.exit(main())
