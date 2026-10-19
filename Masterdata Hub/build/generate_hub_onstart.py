# -*- coding: utf-8 -*-
"""
App.OnStart for landingssiden.

Den henter BEVIDST ingen data. OnStart betales af hver bruger hver gang, og
alt hvad siden viser, kommer fra galleriets eget filter mod MD_RequestIndex.
Her staar kun skemaerne; filtrene saetter skaermen selv (R2-044).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "tools"))
import app_yaml
import design_tokens as tok
import layout_tokens as lay
import permissions as perm
import display_text as dt

# App.Formulas findes ikke i hubben i dag - der er ingen opslagslister at
# hente dovent. Nu er der een formel, og det er temaet: C. Se
# tools/design_tokens.py for hvorfor farven hoerer hjemme i en navngiven
# formel og ikke i hver enkelt kontrol.
# MdIcons (R2-081): raekkernes ikoner, regnet een gang pr. tema.
import build_hub
FORMULAS = (tok.formula() + "\n\n" + lay.formula() + "\n\n" + perm.formula() + "\n\n" +
            dt.formula() + "\n\n" + perm.approver_formula() + "\n\n" +
            build_hub.icons_formula())

# Samlingen bag SaveData skal have et kendt skema, foer Coalesce kan laese
# .Dark - samme moenster som arbejdssamlingerne i de tre andre apps.
_prefs_name, _prefs_schema = tok.prefs_schema()
_prefs = "ClearCollect(%s, { %s });\nClear(%s);" % (
    _prefs_name,
    ", ".join("%s: %s" % kv for kv in _prefs_schema.items()),
    _prefs_name)

# FILTRENE SAETTES IKKE HER (R2-044). OnStart koerer samtidig med
# skaermens OnVisible (non-blocking OnStart). Stod Set(varMdView, "mine")
# her, kunne OnStart blive faerdig EFTER OnVisible og overskrive de
# filtre, brugeren havde gemt (UX-review F8). OnVisible
# (build_hub.HUB_ON_VISIBLE) saetter varMdMe, laeser de gemte filtre -
# og henter selv lageret, hvis det ikke er laest endnu - og falder
# tilbage til standarderne.
ONSTART = _prefs + "\n\n" + tok.onstart_block() + '''

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
