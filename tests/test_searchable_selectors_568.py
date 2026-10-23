# -*- coding: utf-8 -*-
"""
Issue #568: alle listevalg er SOEGBARE ModernCombobox (build_helpers.
themed_dropdown) - ingen ModernDropdown eller Classic/DropDown tilbage.

Tastaturet (Tab, skriv for at filtrere, piletaster, Enter, Escape) kan ikke
proeves her; det staar i PR'ens manuelle testplan.

    python3 -m pytest tests/test_searchable_selectors_568.py
"""
import glob
import os
import re
import sys

import yaml

from conftest import ROOT

sys.path.insert(0, os.path.join(ROOT, "tools"))
import build_helpers as bh  # noqa: E402
import gen_screen  # noqa: E402

APP = os.path.join(ROOT, "BIO SAP App")
GUARD = "CountRows(Self.SelectedItems) = 0"


def _controls():
    out = []

    def walk(n, f):
        if isinstance(n, dict):
            for k, v in n.items():
                if isinstance(v, dict) and "Control" in v:
                    out.append((os.path.basename(f), k, v["Control"].split("@")[0],
                                v.get("Properties") or {}))
                walk(v, f)
        elif isinstance(n, list):
            for x in n:
                walk(x, f)
    for f in sorted(glob.glob(os.path.join(APP, "*.pa.yaml"))):
        walk(yaml.safe_load(open(f, encoding="utf-8")), f)
    return out


CONTROLS = _controls()
LISTS = [c for c in CONTROLS if c[2] == "ModernCombobox" and c[1].startswith("drp")]


def test_no_dropdowns_left():
    left = [(f, n, t) for f, n, t, _ in CONTROLS
            if t in ("ModernDropdown", "Classic/DropDown")]
    assert not left, left


def test_every_list_selector_is_a_searchable_single_select_combobox():
    # De 43 tidligere ModernDropdown-felter (issue #568).
    assert len(LISTS) >= 43, len(LISTS)
    for f, n, _, p in LISTS:
        assert p["SelectMultiple"].strip() == "=false", n
        assert p["IsSearchable"].strip() in ("=true", "=If(LayoutRank < 2, false, true)"), n
        assert p["DelayOutput"].strip() == "=false", n
        assert p["DefaultSelectedItems"].startswith("=FirstN(Filter("), n
        assert "Default" not in p, n
        assert re.fullmatch(r"=ThisItem\.\w+", p["ItemDisplayText"].strip()), n
        acc = p["AccessibleLabel"].strip()
        assert acc not in ('=""', '="%s"' % n), (n, acc)
        # Samme hoejde, hjoerner, farver og tema som de andre felter.
        for key in ("Height", "RadiusTopLeft", "Fill", "Color", "BasePaletteColor",
                    "Appearance", "Font", "Size", "InputTextPlaceholder"):
            assert key in p, (n, key)
        assert "_KeepSelection" not in p, n


def test_click_on_selected_item_never_empties_the_field():
    """ModernCombobox fravaelger ved et klik paa det valgte; ModernDropdown
    kunne aldrig blive tom. Vagten nulstiller til standardvaerdien."""
    for f, n, _, p in LISTS:
        oc = p.get("OnChange", "").strip()
        assert oc.startswith("=If(") and GUARD in oc, n
        assert "Reset(%s)" % n in oc, n


def test_existing_onchange_logic_is_kept_inside_the_guard():
    eq = {n: p for f, n, _, p in LISTS if n == "drpEqPlant"}
    oc = eq["drpEqPlant"]["OnChange"]
    assert "Set(varEqFPlant, Self.Selected.Value)" in oc
    assert oc.index(GUARD) < oc.index("Set(varEqFPlant")


def test_view_mode_keeps_selection_read_only():
    by = {n: p for f, n, _, p in LISTS}
    for n in ("drpEqPlant", "drpMatPlant", "drpMpPlant", "drpMpCharacteristic",
              "drpMpCounterCreateIn", "drpVhpPlant", "drpVhpPlanType"):
        dm = by[n]["DisplayMode"]
        assert "DisplayMode.View" in dm, n


def test_short_fixed_lists_do_not_force_the_phone_keyboard():
    assert bh._literal_option_count('["A", "B", "C"]') == 3
    assert bh._literal_option_count('Table({ Value: "a" }, { Value: "b" })') == 2
    assert bh._literal_option_count("colVhpTasklists") is None
    short = bh.themed_dropdown("drpXTest", '["A", "B"]', '"A"')
    assert short.props["IsSearchable"] == "If(LayoutRank < 2, false, true)"
    long_ = bh.themed_dropdown("drpXTest", "colX", '"A"')
    assert long_.props["IsSearchable"] == "true"


def test_guard_wraps_onchange_set_after_the_helper():
    c = bh.themed_dropdown("drpXTest", "colX", '"A"')
    c.props["OnChange"] = "Set(a, 1);\nSet(b, 2)"
    text = "\n".join(gen_screen.render(c, 0))
    assert "_KeepSelection" not in text
    assert GUARD in text and "Reset(drpXTest)" in text and "Set(b, 2)" in text
