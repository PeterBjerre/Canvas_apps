# -*- coding: utf-8 -*-
"""Faelles opsaetning: tools/ paa sys.path, som indgangene selv goer."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)
