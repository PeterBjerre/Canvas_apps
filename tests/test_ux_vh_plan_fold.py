# -*- coding: utf-8 -*-
"""VH-planens hoved foldet sammen til een linje, naar planen er gemt
(UX-review 2026-10, M5)."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenVhPlan.pa.yaml")


def _yaml():
    return open(SCREEN, encoding="utf-8").read()


def _block(y, name, n=3000):
    i = y.index(f"- {name}:")
    return y[i:i + n]


def test_the_summary_line_shows_only_when_the_plan_is_locked():
    y = _yaml()
    row = _block(y, "conVhpPlanFoldRow", 60000)
    assert "varVhpPlanLocked && !IfError(varVhpPlanShow, false)" in row
    assert y.index("- btnVhpPlanHide:") > y.index("- conVhpPlanFoldRow:")
    for part in ('"Plant"', "drpVhpPlanType.Selected.Value", '"First call"',
                 "dteVhpFirstCall.SelectedDate", '"dd-mm-yyyy"'):
        assert part in row, part
def test_the_fields_fold_away_and_show_brings_them_back():
    y = _yaml()
    grid = _block(y, "conVhpPlanGrid", 2500)
    assert "!(varVhpPlanLocked && !IfError(varVhpPlanShow, false))" in grid
    show = _block(y, "btnVhpPlanHide", 2500)
    assert "Set(varVhpPlanShow, !IfError(varVhpPlanShow, false))" in show


def test_saving_the_plan_folds_it_again():
    save = _block(_yaml(), "btnVhpPlanSave", 9000)
    assert save.index("Set(varVhpPlanLocked, true)") < save.index("Set(varVhpPlanShow, false)")
