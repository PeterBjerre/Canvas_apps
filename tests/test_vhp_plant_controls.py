# -*- coding: utf-8 -*-
"""Issue #453: Plan Headers Plant styrer de vaerksafhaengige felter med det
samme - ogsaa foer Save i Plan header.

VhpPlant (App.Formulas) er vaerket, som det STAAR i dropdownen. Filtre,
FL-soegningen, reglerne og Save draft laeser den; vaerdier fra et andet
vaerk markeres som fejl i stedet for at blive slettet."""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "BIO SAP App")
SCREEN = os.path.join(APP, "ScreenVhPlan.pa.yaml")
APP_YAML = os.path.join(APP, "App.pa.yaml")


def _yaml(path=SCREEN):
    return open(path, encoding="utf-8").read()


def _block(y, name, n=8000):
    i = y.index(f"- {name}:")
    return y[i:i + n]


def _prop(block, prop):
    """Egenskaben prop - til naeste egenskab med samme indrykning."""
    m = re.search(rf"\n( +){prop}: ", block)
    ind = m.group(1)
    rest = block[m.end():]
    nxt = re.search(rf"\n{ind}[A-Z][A-Za-z]+: ", rest)
    return block[m.start():m.end() + (nxt.start() if nxt else len(rest))]


def test_vhp_plant_is_the_live_selection():
    app = _yaml(APP_YAML)
    assert "VhpPlant = Coalesce(varVhpLivePlant, varVhpPlan.Plant);" in app
    # Startvaerdi, naar skaermen aabnes (generate_app_onstart.VARS_BLOCK).
    assert 'Set(varVhpLivePlant, "");' in _prop(_block(_yaml(), "btnVhpOpen", 400000), "OnSelect")


def test_plant_dropdown_sets_live_plant_immediately():
    on_change = _prop(_block(_yaml(), "drpVhpPlant", 12000), "OnChange")
    assert "Set(varVhpLivePlant, np)" in on_change
    assert "Reset(drpVhpItemMainWorkCenter)" in on_change
    assert "Reset(drpVhpItemTasklist)" in on_change
    assert "Plant changed to" in on_change


def test_live_plant_cleared_on_save_reset_new_and_load():
    y = _yaml()
    save = _prop(_block(y, "btnVhpPlanSave", 15000), "OnSelect")
    assert 'Set(varVhpLivePlant, "")' in save
    reset = _prop(_block(y, "btnVhpPlanReset", 6000), "OnSelect")
    assert 'Set(varVhpLivePlant, "")' in reset
    # Ny plan og indlaest plan.
    assert y.count('Set(varVhpLivePlant, "")') >= 4


def test_filters_read_vhp_plant_not_saved_plant():
    y = _yaml()
    mwc = _prop(_block(y, "drpVhpItemMainWorkCenter", 12000), "Items")
    assert "Upper(Plant) = Upper(VhpPlant)" in mwc
    tl = _prop(_block(y, "drpVhpItemTasklist", 12000), "Items")
    assert "Upper(Plant) = Upper(VhpPlant)" in tl
    # Ingen vaerksafhaengig kontrol laeser laengere den gemte Plant direkte
    # (kun planhovedet selv og indlaesningen).
    for name in ("drpVhpItemMainWorkCenter", "drpVhpItemTasklist", "cmbVhpItemFL",
                 "btnVhpFlSearch", "txtVhpFlWrongPlant"):
        assert "varVhpPlan.Plant" not in _block(y, name, 6000).split("\n            - ")[0], name


def test_fl_search_fills_in_plant_prefix():
    cmb = _block(_yaml(), "cmbVhpItemFL", 30000)
    placeholder = _prop(cmb, "InputTextPlaceholder")
    assert "type the rest" in placeholder and "VhpPlant" in placeholder
    assert 'IsMatch(Left(fq, 1), "[0-9]"), Upper(Left(Trim(VhpPlant), 3)) & fq, fq)' in cmb


def test_conflicts_are_flagged_not_cleared():
    app = _yaml(APP_YAML)
    assert "does not belong to plant" in app
    assert "belongs to another plant - choose the task list for" in app
    y = _yaml()
    # Itemets kort ("N to fix") taeller konflikterne med.
    assert "Main work center (other plant)" in y
    assert "Task list (other plant)" in y
    # Plantskiftet skriver aldrig paa itemsne: ingen UpdateIf i OnChange.
    on_change = _prop(_block(y, "drpVhpPlant", 12000), "OnChange")
    assert "UpdateIf" not in on_change and "RemoveIf" not in on_change


def test_save_draft_blocked_while_plant_unsaved():
    y = _yaml()
    assert "Upper(VhpPlant) <> Upper(varVhpPlan.Plant)" in y
    assert "press Save in the plan header before saving the plan" in y
