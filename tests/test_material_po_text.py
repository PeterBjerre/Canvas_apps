# -*- coding: utf-8 -*-
"""
Issue #279: Purchase order text i Materials' sidepanel er kun knappen
(Add/Edit/View text), og popuppen ligger OVER sidepanelet og dets lag.

Issue #429: knappen har sektionsoverskriften PURCHASE ORDER TEXT over sig,
og popuppen har en fast bund med Cancel og Save. Cancel og X kasserer
aendringerne siden aabningen; Save laegger teksten paa raekken.

    python3 -m pytest tests/test_material_po_text.py
"""
import os
import re

import yaml

from conftest import ROOT

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenMaterial.pa.yaml")


def _text():
    return open(SCREEN, encoding="utf-8").read()


def _top_level(text):
    """Skaermens kontroller i lag-raekkefoelge (senere = oeverst)."""
    return re.findall(r"^      - (\w+):", text, re.M)


def _walk(node, out, order):
    for c in node.get("Children", []) or []:
        for n, v in c.items():
            out[n] = v
            order.append(n)
            _walk(v, out, order)


def _controls():
    doc = yaml.safe_load(_text())
    out, order = {}, []
    for scr in doc["Screens"].values():
        _walk(scr, out, order)
    return out, order


def _kids(node):
    return [n for c in node.get("Children", []) or [] for n in c]


def _prop(node, key):
    return str((node.get("Properties") or {}).get(key, "")).strip().lstrip("=").strip()


def test_po_cell_is_only_the_button():
    text = _text()
    assert "No text yet" not in text
    assert "- inpMatPoInfo:" not in text
    assert "- txtMatPoLbl:" not in text
    assert re.search(r"- btnMatPoText:\n\s+Control: ModernButton", text)
    assert '"Add text"' in text


def test_po_popup_is_above_the_side_panel():
    order = _top_level(_text())
    panel = order.index("conMatEditorPanel")
    for name in ("imgMatEditorOutside", "imgMatEditorBackdrop", "conMatNavOpen"):
        assert order.index(name) < panel, name
    for name in ("conMatPoBackdrop", "conMatPoModal"):
        assert order.index(name) > panel, name + " ligger under sidepanelet"
    assert order.index("conMatPoBackdrop") < order.index("conMatPoModal")


def test_section_heading_above_the_button():
    ctrls, order = _controls()
    assert _prop(ctrls["txtMatSecPo"], "Text") == 'Upper("Purchase order text")'
    # Overskriften kommer lige foer raekken med knappen.
    assert order.index("conMatSecPo") < order.index("conMatGridPo") < order.index("btnMatPoText")
    assert "btnMatPoText" not in str(ctrls["conMatGridSupplier"])


def test_open_remembers_the_text():
    ctrls, _ = _controls()
    fx = _prop(ctrls["btnMatPoText"], "OnSelect")
    assert "Set(varMatPoBefore, varMatFRemarks)" in fx
    assert fx.index("varMatPoBefore") < fx.index("Set(varMatPoOpen, true)")


def _idle(layout):
    """Knappens layout, naar intet gemmes: sidste gren af If(..., TextOnly, x)."""
    if layout.startswith("If("):
        return layout.rsplit(", ", 1)[-1][:-1]
    return layout


def test_footer_is_cancel_then_save_and_fixed():
    ctrls, _ = _controls()
    modal = ctrls["conMatPoModal"]
    kids = _kids(modal)
    assert kids[0] == "conMatPoHead" and kids[-1] == "conMatPoFooter"
    assert "Scroll" not in _prop(modal, "LayoutOverflowY")
    foot = ctrls["conMatPoFooter"]
    assert _kids(foot) == ["btnMatPoCancel", "btnMatPoSave"]
    assert _prop(foot, "LayoutJustifyContent") == "LayoutJustifyContent.End"
    assert _prop(foot, "LayoutGap") == "8"
    # Samme hoejde og stil som sidepanelets Cancel og Save.
    side_cancel, side_save = ctrls["btnMatEditorCancel"], ctrls["btnMatSave"]
    for mine, theirs in ((ctrls["btnMatPoCancel"], side_cancel),
                         (ctrls["btnMatPoSave"], side_save)):
        for key in ("Height", "Appearance", "BasePaletteColor", "BorderColor", "Icon"):
            assert _prop(mine, key) == _prop(theirs, key), key
        # Layout: samme i hvile; mens der gemmes, viger ikonet for teksten (#420).
        assert _idle(_prop(mine, "Layout")) == _idle(_prop(theirs, "Layout"))
    assert "varMatPoSaving, ButtonLayout.TextOnly" in _prop(ctrls["btnMatPoSave"], "Layout")
    assert _prop(ctrls["btnMatPoCancel"], "Text") == '"Cancel"'


def test_cancel_and_x_discard_the_changes():
    ctrls, _ = _controls()
    for name in ("btnMatPoCancel", "btnMatPoClose"):
        fx = _prop(ctrls[name], "OnSelect")
        assert "Set(varMatFRemarks, varMatPoBefore)" in fx, name
        assert "Reset(inpMatPoText)" in fx, name
        assert "Set(varMatPoOpen, false)" in fx, name
        assert "inpMatPoText.Text" not in fx, name


def test_save_applies_text_and_shows_saving():
    ctrls, _ = _controls()
    save = ctrls["btnMatPoSave"]
    fx = _prop(save, "OnSelect")
    assert fx.startswith("Set(varMatPoSaving, true)")
    assert "Set(varMatFRemarks, inpMatPoText.Text)" in fx
    assert fx.index("inpMatPoText.Text") < fx.index("Set(varMatPoOpen, false)")
    assert fx.rstrip().endswith("Set(varMatPoSaving, false)")
    # Kun formularens variabel - intet netvaerkskald.
    assert "Patch(" not in fx
    assert _prop(save, "Text") == 'If(varMatPoSaving, "Saving...", "Save")'
    assert _prop(save, "DisplayMode").startswith("If(varMatPoSaving ||")
