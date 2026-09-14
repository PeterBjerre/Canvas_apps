# -*- coding: utf-8 -*-
"""
VH-plan appens indgang til de faelles byggeklodser.

Implementationen ligger i shared/canvas/canvas_helpers.py og deles med de
oevrige canvas apps. Denne fil findes kun, saa appens egne buildere kan
blive ved med at skrive "from build_helpers import ...".
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "shared", "canvas"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from canvas_helpers import *      # noqa: F401,F403
