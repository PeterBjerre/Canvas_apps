# -*- coding: utf-8 -*-
"""VH-planens FL-soegning kun for planens vaerk: de foerste 3 tegn skal
vaere planens Plant, ellers starter soegningen ikke, og brugeren faar at
vide hvorfor."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "BIO SAP App")
SCREEN = os.path.join(APP, "ScreenVhPlan.pa.yaml")
PREFIX = "Upper(Left(Trim(varVhpPlan.Plant), 3))"


def _yaml(path=SCREEN):
    return open(path, encoding="utf-8").read()


def _block(y, name, n=6000):
    i = y.index(f"- {name}:")
    return y[i:i + n]


def test_search_button_is_disabled_and_guarded_for_another_plant():
    btn = _block(_yaml(), "btnVhpFlSearch")
    q = "Trim(Coalesce(cmbVhpItemFL.SearchText, varVhpFlQuery))"
    cond = f"(IsBlank(varVhpPlan.Plant) || Upper(Left({q}, 3)) <> {PREFIX})"
    display = btn[btn.index("DisplayMode:"):btn.index("DisplayMode:") + 400]
    assert cond in display
    # Selve soegningen: vaerk-tjekket kommer FOER flowkaldet.
    on_select = btn[btn.index("OnSelect:"):]
    assert on_select.index(cond) < on_select.index("Run(")


def test_enter_row_is_not_offered_for_another_plant():
    cmb = _block(_yaml(), "cmbVhpItemFL", 12000)
    assert f"Upper(Left(q, 3)) <> {PREFIX}" in cmb
    # Enter-soegningen (OnChange) er ogsaa stoppet.
    on_change = cmb[cmb.index("OnChange:"):]
    assert on_change.index("Upper(Left(Trim(varVhpFlQuery), 3))") < on_change.index("Run(")


def test_user_is_told_why():
    msg = _block(_yaml(), "txtVhpFlWrongPlant", 3000)
    assert "Choose a plant in the Plan header" in msg
    assert "Only functional locations for plant" in msg
    assert "Len(Trim(cmbVhpItemFL.SearchText)) >= 3" in msg


def test_other_apps_fl_search_is_unchanged():
    for name in os.listdir(APP):
        if name.endswith(".pa.yaml") and name != "ScreenVhPlan.pa.yaml":
            assert "varVhpPlan.Plant), 3)" not in _yaml(os.path.join(APP, name)), name
