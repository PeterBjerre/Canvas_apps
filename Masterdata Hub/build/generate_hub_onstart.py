# -*- coding: utf-8 -*-
"""
App.OnStart for landingssiden.

Den henter BEVIDST ingen data. OnStart betales af hver bruger hver gang, og
alt hvad siden viser, kommer fra galleriets eget filter mod MD_RequestIndex.
Her staar kun de fire variabler, der styrer visningen.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "tools"))
import design_tokens as tok
import layout_tokens as lay

# App.Formulas findes ikke i hubben i dag - der er ingen opslagslister at
# hente dovent. Nu er der een formel, og det er temaet: C. Se
# tools/design_tokens.py for hvorfor farven hoerer hjemme i en navngiven
# formel og ikke i hver enkelt kontrol.
FORMULAS = tok.formula() + "\n\n" + lay.formula()

# Samlingen bag SaveData skal have et kendt skema, foer Coalesce kan laese
# .Dark - samme moenster som arbejdssamlingerne i de tre andre apps.
_prefs_name, _prefs_schema = tok.prefs_schema()
_prefs = "ClearCollect(%s, { %s });\nClear(%s);" % (
    _prefs_name,
    ", ".join("%s: %s" % kv for kv in _prefs_schema.items()),
    _prefs_name)

ONSTART = _prefs + "\n\n" + tok.onstart_block() + '''

Set(gblMe, Lower(User().Email));
Set(gblView, "mine");
Set(gblDomain, "");
Set(gblStatusMode, "open")'''


def _block(prop, text):
    out = ["    %s: |" % prop]
    first = True
    for line in text.split("\n"):
        if not line.strip():
            out.append("")
            continue
        out.append(("      =" if first else "      ") + line)
        first = False
    return out


lines = ["App:", "  Properties:"]
lines += _block("Formulas", FORMULAS)
lines += _block("OnStart", ONSTART)
lines += ["    StartScreen: |-", "        =ScreenMdHub",
          "    Theme: |-", "        =PowerAppsTheme"]

content = "\n".join(lines) + "\n"
with open(os.path.join(OUT_DIR, "App.pa.yaml"), "w", encoding="utf-8", newline="\n") as f:
    f.write(content)
print("App.pa.yaml written. Lines:", content.count(chr(10)) + 1)
