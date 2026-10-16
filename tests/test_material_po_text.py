# -*- coding: utf-8 -*-
"""
Issue #279: Purchase order text i Materials' sidepanel er kun knappen
(Add/Edit/View text), og popuppen ligger OVER sidepanelet og dets lag.

    python3 -m pytest tests/test_material_po_text.py
"""
import os
import re

from conftest import ROOT

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenMaterial.pa.yaml")


def _text():
    return open(SCREEN, encoding="utf-8").read()


def _top_level(text):
    """Skaermens kontroller i lag-raekkefoelge (senere = oeverst)."""
    return re.findall(r"^      - (\w+):", text, re.M)


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
    for name in ("conMatPoBackdrop", "conMatPoModal",
                 "conMatResetConfirmBackdrop", "conMatResetConfirmModal"):
        assert order.index(name) > panel, name + " ligger under sidepanelet"
    assert order.index("conMatPoBackdrop") < order.index("conMatPoModal")


def test_close_keeps_the_text():
    text = _text()
    m = re.search(r"- btnMatPoClose:.*?OnSelect: \|-?\n(.*?)\n\s+\w+:", text, re.S)
    assert m, "btnMatPoClose mangler"
    fx = m.group(1)
    assert "inpMatPoText.Text" in fx
    assert "Set(varMatPoOpen, false)" in fx
