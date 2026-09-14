# -*- coding: utf-8 -*-
"""
App.OnStart for landingssiden.

Den henter BEVIDST ingen data. OnStart betales af hver bruger hver gang, og
alt hvad siden viser, kommer fra galleriets eget filter mod MD_RequestIndex.
Her staar kun de fire variabler, der styrer visningen.
"""
import os

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

ONSTART = '''Set(gblMe, Lower(User().Email));
Set(gblView, "mine");
Set(gblDomain, "");
Set(gblStatusMode, "open")'''

lines = ["App:", "  Properties:", "    OnStart: |"]
first = True
for line in ONSTART.split("\n"):
    if first and line.strip():
        lines.append("      =" + line); first = False
    else:
        lines.append(("      " + line) if line.strip() else "")
lines += ["    StartScreen: |-", "        =ScreenMdHub",
          "    Theme: |-", "        =PowerAppsTheme"]

content = "\n".join(lines) + "\n"
with open(os.path.join(OUT_DIR, "App.pa.yaml"), "w", encoding="utf-8", newline="\n") as f:
    f.write(content)
print("App.pa.yaml written. Lines:", content.count(chr(10)) + 1)
