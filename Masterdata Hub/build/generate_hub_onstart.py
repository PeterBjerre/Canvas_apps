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
import app_yaml
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

Set(varMdMe, Lower(User().Email));
Set(varMdView, "mine");
Set(varMdDomain, "");
Set(varMdStatusMode, "open");
Set(varMdClosedPeek, false);
// Skemaet for flisernes taellesamling - hentes i skaermens OnVisible.
// If(false, ...): kun skemaet, ingen handling. OnStart koerer samtidig med
// OnVisible, og en Clear her kunne toemme taellingen, OnVisible lige havde
// hentet - saa stod alle fliser paa 0.
If(false, ClearCollect(colMdScope, { Domain: "" }))'''


def main():
    content = app_yaml.write(OUT_DIR, FORMULAS, ONSTART, "ScreenMdHub")
    print("App.pa.yaml skrevet.", content.count(chr(10)) + 1, "linjer, "
          "0 datahentninger i OnStart.")


if __name__ == "__main__":
    main()
