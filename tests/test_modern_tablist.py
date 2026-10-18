# -*- coding: utf-8 -*-
"""
Issue #303 (del af #161): fanerne er den moderne Tab list
(ModernTabList@1.0.0). De laeser og saetter de SAMME variabler som de
knapper, de afloeser, saa filtreringen er uaendret. FL's klassefaner
(galFlTabs) er bevidst beholdt (docs/38).

    python3 -m pytest tests/test_modern_tablist.py
"""
import importlib.util
import io
import os
import re
import shutil
import sys
from contextlib import redirect_stdout

from conftest import ROOT, TOOLS

APP = os.path.join(ROOT, "BIO SAP App")
VERSION = "ModernTabList@1.0.0"

# Skaerm -> {fane: (variabel, {vaerdi: tekst(er)})}
TABS = {
    "ScreenIssueBoard.pa.yaml": {
        "tabIbScope": ("varIbScope", {"all": ("All issues", "All"), "mine": ("My issues", "Mine"),
                                      "assigned": ("Assigned to me", "Assigned")}),
        "tabIbState": ("varIbState", {"open": ("Open",), "closed": ("Closed",),
                                      "archived": ("Archived",)}),
    },
    "ScreenVhPlan.pa.yaml": {
        "tabVhpOps": ("varVhpOpsTab", {"ops": ("Operations",),
                                       "pkg": ("Maintenance packages", "Packages")}),
    },
}
# Issue #371: hubbens My requests | All requests er igen en segmenteret
# skinne som Open/Closed/All (tests/test_hub_all_requests.py).
# De knapper, fanerne afloeser.
GONE = ("btnIbScopeAll", "btnIbScopeMine", "btnIbScopeAssigned", "btnIbStateOpen",
        "btnIbStateClosed", "btnIbStateArchived", "conIbScope:", "conIbState:",
        "btnVhpTabOps", "btnVhpTabPkg", "conVhpOpsTabBar")


def _read(screen):
    return open(os.path.join(APP, screen), encoding="utf-8").read()


def _block(text, name):
    m = re.search(r"^( *)- %s:\n" % name, text, re.M)
    assert m, name
    rest = text[m.end():]
    end = re.search(r"^ {0,%d}- \w+:" % len(m.group(1)), rest, re.M)
    return rest[:end.start()] if end else rest


def _prop(block, key):
    m = re.search(r"^( +)%s: \|-\n +=(.*(?:\n\1    .*)*)" % key, block, re.M)
    return m.group(2).strip() if m else None


def test_every_tab_row_is_a_modern_tab_list_on_the_same_variable():
    total = 0
    for screen, tabs in TABS.items():
        text = _read(screen)
        assert text.count("Control: ModernTabList") == len(tabs), screen
        for name, (var, values) in tabs.items():
            b = _block(text, name)
            assert f"Control: {VERSION}" in b, name
            # Tenantens Tab list kender ikke TabListAppearance.Underline og
            # TabListAlignment (#331) - Fluents standard bruges.
            assert _prop(b, "Appearance") is None, name
            assert _prop(b, "Alignment") is None, name
            assert _prop(b, "Color") == "C.'text-primary'", name
            acc = _prop(b, "AccessibleLabel")
            assert acc and acc != '""', name
            items, default, change = _prop(b, "Items"), _prop(b, "Default"), _prop(b, "OnChange")
            assert default.startswith(f"{{Value: Switch({var}, "), name
            # Valget skrives kun, naar det faktisk skifter.
            assert f"If(!IsBlank(k) && k <> {var}," in change, name
            assert f"Set({var}, k)" in change, name
            for key, texts in values.items():
                assert f'"{key}", ' in default, (name, key)
                for t in texts:
                    assert f'"{t}"' in items, (name, t)
                    assert f'"{t}", "{key}"' in change, (name, t)
            for bad in ("TabIndex", "Fill", "BasePaletteColor", "Tooltip", "FontSize",
                        "FontColor", "BorderRadius", "Text", "OnSelect"):
                assert _prop(b, bad) is None, (name, bad)
            total += 1
    assert total == 3


def test_old_tab_buttons_are_gone():
    for screen in TABS:
        text = _read(screen)
        for g in GONE:
            assert f"- {g}" not in text, (screen, g)


def test_assigned_to_me_is_still_admin_only():
    b = _block(_read("ScreenIssueBoard.pa.yaml"), "tabIbScope")
    assert _prop(b, "Items").startswith("Filter([")
    assert 'Value <> "Assigned to me" && Value <> "Assigned" || IsAdmin' in _prop(b, "Items")


def test_packages_tab_only_on_a_strategy_plan():
    b = _block(_read("ScreenVhPlan.pa.yaml"), "tabVhpOps")
    assert "PlanType = \"Strategy\"" in _prop(b, "Visible")
    assert "PlanType = \"Strategy\"" in _prop(b, "Items")


def test_fl_class_tabs_are_kept_as_a_gallery():
    """Bevidst beholdt (docs/38): klassens hjaelpetekst er fanens tooltip
    (FL65), og der kan vaere flere klasser, end der er plads til - Tab list
    ruller ikke."""
    text = _read("ScreenFunctionalLocation.pa.yaml")
    assert "Control: ModernTabList" not in text
    b = _block(text, "galFlTabs")
    assert "Control: Gallery" in b
    assert _prop(_block(text, "btnFlTab"), "Tooltip")


def _check_layout():
    spec = importlib.util.spec_from_file_location("tools_check_layout_303",
                                                  os.path.join(TOOLS, "check_layout.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run_rule(cl, tmp_path, screen, text):
    (tmp_path / screen).write_text(text, encoding="utf-8")
    old_argv, sys.argv = sys.argv, ["check_layout.py", str(tmp_path / screen)]
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            rc = cl.main()
    finally:
        sys.argv = old_argv
    return rc, buf.getvalue()


def test_rule_16t_rejects_other_versions_and_unknown_properties(tmp_path):
    cl = _check_layout()
    screen = "ScreenVhPlan.pa.yaml"
    shutil.copy(os.path.join(APP, "App.pa.yaml"), tmp_path / "App.pa.yaml")
    text = _read(screen)
    rc, out = _run_rule(cl, tmp_path, screen, text)
    assert "[16t]" not in out, out

    for bad in ("ModernTabList@1.1.0", "ModernTabList"):
        new = text.replace(f"Control: {VERSION}", f"Control: {bad}", 1)
        rc, out = _run_rule(cl, tmp_path, screen, new)
        assert rc == 1 and "[16t]" in out, (bad, out)

    block = _block(text, "tabVhpOps")
    new = text.replace(block, block.replace("Properties:\n",
                                            "Properties:\n"
                                            "                              TabIndex: |-\n"
                                            "                                  =0\n", 1), 1)
    assert new != text
    rc, out = _run_rule(cl, tmp_path, screen, new)
    assert rc == 1 and "[16t] tabVhpOps" in out and "TabIndex" in out, out
