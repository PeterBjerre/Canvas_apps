# -*- coding: utf-8 -*-
"""
Issue #402: sidepanelets gem-tilstand vises I panelet - ikke som sloer og
bjaelke midt paa siden bag det.

  - Functional Location (Edit, Class data, Manufacturer, Warranty - samme
    panel), Materials, Equipment og Measuring Points har den samme linje
    over bundbjaelken: "Save failed" og Retry. Mens der gemmes, siger Save
    selv "Saving..." - det eneste ventetegn (issue #441; foer stod et hjul
    med "Saving..." i linjen OGSAA).
  - Save og Retry er det samme gem, er spaerret, mens der gemmes, og
    tilstanden saettes foer og efter selve gemmet - ingen timer.
  - Panelets Save taender ikke sidens gem-sloer (img<App>Saving).
  - Et gennemsigtigt lag fanger tryk, mens der gemmes.

Power Fx kan ikke koeres her, saa testene laeser de GENEREREDE skaerme.

    python3 -m pytest tests/test_panel_save_feedback.py
"""
import os

import pytest

from conftest import ROOT

APP = os.path.join(ROOT, "BIO SAP App")
# Skaerm -> (prefix, panelets Save-knap)
SCREENS = {
    "ScreenFunctionalLocation.pa.yaml": ("Fl", "btnFlEditorSave"),
    "ScreenMaterial.pa.yaml": ("Mat", "btnMatSave"),
    "ScreenEquipment.pa.yaml": ("Eq", "btnEqSave"),
    "ScreenMeasuringPoint.pa.yaml": ("Mp", "btnMpSave"),
}
_TREE = {}


def _tree(screen):
    import yaml
    if screen not in _TREE:
        with open(os.path.join(APP, screen), encoding="utf-8") as f:
            _TREE[screen] = yaml.safe_load(f.read())
    return _TREE[screen]


def _find(node, ctrl):
    if isinstance(node, dict):
        if ctrl in node and isinstance(node[ctrl], dict) and "Control" in node[ctrl]:
            return node[ctrl]
        node = list(node.values())
    if isinstance(node, list):
        for x in node:
            hit = _find(x, ctrl)
            if hit is not None:
                return hit
    return None


def _ctrl(screen, name):
    hit = _find(_tree(screen), name)
    assert hit is not None, (screen, name)
    return hit


def _prop(screen, name, prop):
    return str(_ctrl(screen, name)["Properties"][prop]).lstrip("=")


def _children(screen, name):
    return [list(c)[0] for c in _ctrl(screen, name).get("Children", [])]


def _top(screen):
    scr = list(_tree(screen)["Screens"].values())[0]
    return [list(c)[0] for c in scr["Children"]]


@pytest.mark.parametrize("screen", sorted(SCREENS))
def test_status_line_sits_above_the_footer(screen):
    p, _save = SCREENS[screen]
    kids = _children(screen, f"con{p}EditorPanel")
    assert kids[-2:] == [f"con{p}EditorSaveStatus", f"con{p}EditorFooter"]
    # Kun fejlen og Retry (issue #441): mens der gemmes, siger Save selv
    # "Saving..." - hjulet med "Saving..." over bundbjaelken er vaek.
    assert _children(screen, f"con{p}EditorSaveStatus") == [
        f"txt{p}EditorSaveFailed", f"btn{p}EditorRetry"]
    assert "ModernSpinner" not in str(_ctrl(screen, f"con{p}EditorSaveStatus"))
    assert f"spn{p}EditorSaving" not in str(_tree(screen))
    state = f"var{p}PanelSave"
    failed = f'IfError({state} = "failed", false)'
    assert _prop(screen, f"con{p}EditorSaveStatus", "Visible") == failed
    assert _prop(screen, _save, "Text").startswith(
        f'If(IfError({state} = "saving", false), "Saving...", ')
    assert _prop(screen, f"txt{p}EditorSaveFailed", "Visible") == failed
    assert "Save failed" in _prop(screen, f"txt{p}EditorSaveFailed", "Text")
    assert _prop(screen, f"btn{p}EditorRetry", "Visible") == failed
    # Scrollen giver kun plads, mens linjen vises.
    assert state in _prop(screen, f"con{p}EditorSections", "Height")


@pytest.mark.parametrize("screen", sorted(SCREENS))
def test_save_and_retry_run_the_real_save_without_the_page_overlay(screen):
    p, save = SCREENS[screen]
    state = f"var{p}PanelSave"
    fx = _prop(screen, save, "OnSelect")
    assert fx.startswith(f'Set({state}, "saving");')
    # Ingen fast varighed, og sidens sloer taendes ikke.
    assert "Timer" not in fx and f"var{p}Saving" not in fx
    assert _prop(screen, f"btn{p}EditorRetry", "OnSelect") == fx
    busy = f'If(IfError({state} = "saving", false), DisplayMode.Disabled, '
    assert _prop(screen, save, "DisplayMode").startswith(busy)
    assert _prop(screen, f"btn{p}EditorRetry", "DisplayMode") == _prop(screen, save, "DisplayMode")
    # Fejlen saetter "failed" - raekken lukkes ikke, saa vaerdierne bliver.
    assert f'Set({state}, "failed")' in fx


@pytest.mark.parametrize("screen", sorted(SCREENS))
def test_transparent_block_while_saving(screen):
    p, _save = SCREENS[screen]
    top = _top(screen)
    block = f"img{p}EditorSaveBlock"
    assert top.index(f"con{p}EditorPanel") < top.index(block)
    assert _prop(screen, block, "Visible") == f'IfError(var{p}PanelSave = "saving", false)'
    assert "Image" not in _prop(screen, block, "Image").replace('""', "")
    # Save draft/Submit har ogsaa et gennemsigtigt lag nu (issue #420) -
    # sidens graa gem-sloer er vaek.
    assert f"img{p}ActBlock" in top and f"img{p}Saving" not in top


def test_state_is_cleared_when_the_panel_opens_or_closes():
    fl = "ScreenFunctionalLocation.pa.yaml"
    assert _prop(fl, "btnFlEditorClose", "OnSelect").startswith('Set(varFlPanelSave, "");')
    assert 'Set(varFlPanelSave, "");' in _prop(fl, "btnFlRowClassData", "OnSelect")
    for screen in ("ScreenMaterial.pa.yaml", "ScreenEquipment.pa.yaml",
                   "ScreenMeasuringPoint.pa.yaml"):
        p = SCREENS[screen][0]
        assert f'Set(var{p}PanelSave, "");' in _prop(screen, f"btn{p}EditorClose", "OnSelect")
        assert f'Set(var{p}PanelSave, "");' in _prop(screen, f"btn{p}EditorNext", "OnSelect")


IB = "ScreenIssueBoard.pa.yaml"


def test_issue_board_form_shows_the_save_state_in_the_panel():
    """Issue Board blev foejet til #402: New issue/Edit-formularens Submit
    issue/Save changes viser tilstanden under knappen i sidepanelet."""
    foot = _children(IB, "conIbFormFoot")
    assert foot.index("conIbFormFooter") < foot.index("conIbEditorSaveStatus")
    # Kun fejlen og Retry - knappen siger selv "Submitting..."/"Saving..."
    # (issue #441).
    assert _children(IB, "conIbEditorSaveStatus") == [
        "txtIbEditorSaveFailed", "btnIbEditorRetry"]
    assert _prop(IB, "conIbEditorSaveStatus", "Visible") == 'IfError(varIbPanelSave = "failed", false)'
    assert _prop(IB, "btnIbFormSubmit", "Text").startswith(
        'If(IfError(varIbPanelSave = "saving", false), If(')
    fx = _prop(IB, "btnIbFormSubmit", "OnSelect")
    # Baade ny sag og Edit: panelets tilstand - ikke sidens varIbBusy-sloer.
    assert "varIbBusy, true" not in fx and "Set(varIbBusy, false)" not in fx
    assert fx.count('Set(varIbPanelSave, "saving");') == 2
    assert fx.count('Set(varIbPanelSave, If(varIbSaved, "", "failed"))') == 2
    assert _prop(IB, "btnIbEditorRetry", "OnSelect") == fx
    assert _prop(IB, "btnIbEditorRetry", "DisplayMode") == _prop(IB, "btnIbFormSubmit", "DisplayMode")
    top = _top(IB)
    assert _prop(IB, "imgIbEditorSaveBlock", "Visible") == 'IfError(varIbPanelSave = "saving", false)'
    # De andre handlinger har deres eget gennemsigtige lag (issue #420).
    assert "imgIbActBlock" in top and "imgIbBusy" not in top
    assert _prop(IB, "btnIbFormClose", "OnSelect").count('Set(varIbPanelSave, "")') >= 1
