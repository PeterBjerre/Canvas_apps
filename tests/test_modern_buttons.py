# -*- coding: utf-8 -*-
"""
Issue #307 (del af #161): feedback-vaelgerens felt (btn*FbSubject, 7) og
"nogle valgt"-feltet i operationsvaelgeren (btnVhpPickerHeadPartial) er
ModernButton uden indre luft. OnSelect og synlighed er uaendrede.
Raekkelagene og btnMdRowApproval forbliver Classic/Button.

    python3 -m pytest tests/test_modern_buttons.py
"""
import os
import re
from types import SimpleNamespace

from conftest import ROOT

APP = os.path.join(ROOT, "BIO SAP App")
SUBJECTS = {
    "ScreenEquipment.pa.yaml": "btnEqFbSubject",
    "ScreenFunctionalLocation.pa.yaml": "btnFlFbSubject",
    "ScreenIssueBoard.pa.yaml": "btnIbFbSubject",
    "ScreenKks.pa.yaml": "btnKksFbSubject",
    "ScreenMaterial.pa.yaml": "btnMatFbSubject",
    "ScreenMdHub.pa.yaml": "btnMdFbSubject",
    "ScreenMeasuringPoint.pa.yaml": "btnMpFbSubject",
    "ScreenVhPlan.pa.yaml": "btnVhpFbSubject",
}


def _read(screen):
    return open(os.path.join(APP, screen), encoding="utf-8").read()


def _block(text, name):
    """Kontrollens egen YAML-blok - til naeste soeskende paa samme niveau."""
    m = re.search(r"^( *)- %s:\n" % name, text, re.M)
    assert m, name
    rest = text[m.end():]
    end = re.search(r"^ {0,%d}- \w+:" % len(m.group(1)), rest, re.M)
    return rest[:end.start()] if end else rest


def _prop(block, key):
    m = re.search(r"^ +%s: \|-\n +=(.*)$" % key, block, re.M)
    return m.group(1).strip() if m else None


def _multi(block, key):
    m = re.search(r"^ +%s: \|-\n(.*?)(?=^ +\w+: \|-|\Z)" % key, block, re.M | re.S)
    return m.group(1).strip() if m else None


def _padding_zero(block):
    for k in ("PaddingBottom", "PaddingLeft", "PaddingRight", "PaddingTop"):
        assert _prop(block, k) == "0", k


def test_feedback_subject_is_a_flat_modern_button():
    found = 0
    for screen, name in SUBJECTS.items():
        text = _read(screen)
        b = _block(text, name)
        assert "Control: ModernButton\n" in b, name
        assert _prop(b, "OnSelect") == "Set(gblFbPick, !gblFbPick)", name
        assert _prop(b, "Align") == "Align.Left", name
        assert _prop(b, "Appearance") == "ButtonAppearance.Transparent", name
        assert _prop(b, "BorderStyle") == "BorderStyle.None", name
        assert _prop(b, "Visible") is None, name
        _padding_zero(b)
        assert _prop(b, "AccessibleLabel"), name
        for bad in ("TabIndex", "Fill", "HoverFill", "PressedFill", "FocusedBorderColor"):
            assert _prop(b, bad) is None, (name, bad)
        # Raekkelaget i listen under er stadig klassisk.
        assert "Control: Classic/Button" in _block(text, name + "Pick"), name
        found += 1
    assert found == len(SUBJECTS)


def test_partial_head_is_a_modern_button_with_same_action_and_visibility():
    text = _read("ScreenVhPlan.pa.yaml")
    b = _block(text, "btnVhpPickerHeadPartial")
    chk = _block(text, "chkVhpPickerHeadAll")
    assert "Control: ModernButton\n" in b
    assert _prop(b, "BasePaletteColor") == "C.'color-brand-primary'"
    assert _prop(b, "Height") == "18" and _prop(b, "Width") == "18"
    _padding_zero(b)
    assert _prop(b, "TabIndex") is None
    # Samme handling som "Select all"-boksens OnCheck.
    assert _multi(b, "OnSelect") == _multi(chk, "OnCheck")
    # Synlig praecis naar boksen ikke er: <desktop> && <nogle valgt>.
    assert _prop(chk, "Visible").replace(" && !", " && ", 1) == _prop(b, "Visible")


def test_only_row_layers_and_md_approval_stay_classic():
    names = set()
    for screen in SUBJECTS:
        names |= set(re.findall(r"^ *- (\w+):\n +Control: Classic/Button", _read(screen), re.M))
    assert "btnMdRowApproval" in names
    assert not any(n.endswith("FbSubject") or n == "btnVhpPickerHeadPartial" for n in names)


def test_rule_16k_allows_only_transparent_classic_layers():
    import check_layout
    from design_tokens import TRANSPARENT
    ok_layer = ("/a", "btnXRowHit", {"Control": "Classic/Button",
                                      "Properties": {"Color": "=" + TRANSPARENT}})
    classic = ("/b", "btnXOld", {"Control": "Classic/Button",
                                  "Properties": {"Color": "=C.'input-fg'"}})
    versioned = ("/c", "btnXNew", {"Control": "ModernButton@1.0.0", "Properties": {}})
    unknown = ("/d", "btnXFill", {"Control": "ModernButton",
                                   "Properties": {"HoverFill": "=Red", "PaddingLeft": "=0"}})
    ctx = SimpleNamespace(all_nodes=[ok_layer, classic, versioned, unknown], problems=[])
    check_layout.rule_16k(ctx)
    text = "\n".join(ctx.problems)
    assert "btnXRowHit" not in text
    assert "btnXOld" in text
    assert "btnXNew" in text
    assert "'HoverFill'" in text and "'PaddingLeft'" not in text
