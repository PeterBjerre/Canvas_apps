# -*- coding: utf-8 -*-
"""
VH-plan appens indgang til det faelles canvas-DSL.

Selve DSL'et, hoejde-algebraen og stylingkonstanterne ligger i
shared/canvas/canvas_dsl.py og deles med de oevrige canvas apps i repoet.
Kun de maal, der er specifikke for DENNE skaerm, staar her.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "shared", "canvas"))

from canvas_dsl import *          # noqa: F401,F403
from canvas_dsl import SHELL_W

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

# Bredden af items-skinnen naar de to kort staar side om side.
RAIL_W = 360
SPLIT_GAP = 20
# Bredden af Item Editor-kortet, udtrykt uden at referere nogen kontrol.
EDITOR_W = f"If(App.Width < 1000, {SHELL_W}, {SHELL_W} - {RAIL_W} - {SPLIT_GAP})"
