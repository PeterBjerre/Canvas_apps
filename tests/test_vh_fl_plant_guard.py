# -*- coding: utf-8 -*-
"""VH-planens FL-soegning kun for planens vaerk: de foerste 3 tegn skal
vaere planens Plant, ellers starter soegningen ikke, og brugeren faar at
vide hvorfor."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "BIO SAP App")
SCREEN = os.path.join(APP, "ScreenVhPlan.pa.yaml")
# Issue #453: vaerket er det, der STAAR i Plan Header (VhpPlant), ogsaa foer Save.
PREFIX = "Upper(Left(Trim(VhpPlant), 3))"


def _mapped(src):
    """Soegeteksten med vaerket udfyldt foran (build_items.fl_with_prefix)."""
    return (f"With({{ fq: Trim({src}) }}, If(!IsBlank({PREFIX}) && "
            f"IsMatch(Left(fq, 1), \"[0-9]\"), {PREFIX} & fq, fq))")


def _yaml(path=SCREEN):
    return open(path, encoding="utf-8").read()


def _block(y, name, n=6000):
    i = y.index(f"- {name}:")
    return y[i:i + n]


def test_search_button_is_disabled_and_guarded_for_another_plant():
    btn = _block(_yaml(), "btnVhpFlSearch", 15000)
    q = f"Trim({_mapped('Coalesce(cmbVhpItemFL.SearchText, varVhpFlQuery)')})"
    cond = f"(IsBlank(VhpPlant) || Upper(Left({q}, 3)) <> {PREFIX})"
    display = btn[btn.index("DisplayMode:"):btn.index("DisplayMode:") + 1200]
    assert cond in display
    # Selve soegningen: vaerk-tjekket kommer FOER flowkaldet.
    on_select = btn[btn.index("OnSelect:"):]
    assert on_select.index(cond) < on_select.index("Run(")


def test_enter_row_is_not_offered_for_another_plant():
    cmb = _block(_yaml(), "cmbVhpItemFL", 30000)
    assert f"Upper(Left(q, 3)) <> {PREFIX}" in cmb
    # Enter-soegningen (OnChange) er ogsaa stoppet.
    on_change = cmb[cmb.index("OnChange:"):]
    enter_q = f"Upper(Left(Trim({_mapped('varVhpFlQuery')}), 3))"
    assert on_change.index(enter_q) < on_change.index("Run(")


def test_user_is_told_why():
    msg = _block(_yaml(), "txtVhpFlWrongPlant", 8000)
    assert "Choose a plant in the Plan header" in msg
    assert "Only functional locations for plant" in msg
    assert f"Len({_mapped('cmbVhpItemFL.SearchText')}) >= 3" in msg


def test_other_apps_fl_search_is_unchanged():
    for name in os.listdir(APP):
        if name.startswith("Screen") and name.endswith(".pa.yaml") and name != "ScreenVhPlan.pa.yaml":
            assert "VhpPlant), 3)" not in _yaml(os.path.join(APP, name)), name
