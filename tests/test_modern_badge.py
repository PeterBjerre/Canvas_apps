# -*- coding: utf-8 -*-
"""
Issue #304 (del af #161): status- og nummermaerkerne er den moderne Badge
(ModernBadge@1.0.0) med de SAMME tekster og farver som foer - vores egne
tokens i Color/Fill, ikke Fluents Intent-farver.

    python3 -m pytest tests/test_modern_badge.py
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
VERSION = "ModernBadge@1.0.0"

# Skaerm -> {maerke: (Content, Color, Fill)}. None = ikke tjekket her
# (lange Switch-formler; deres farvepar tjekkes nedenfor).
BADGES = {
    "ScreenEquipment.pa.yaml": {
        "bdgEqNumber": ("varEqRequestNo", "ColorValue(C.'hex-domain-eq')",
                        "ColorValue(C.'hex-domain-eq' & \"1F\")"),
    },
    "ScreenMaterial.pa.yaml": {
        "bdgMatNumber": ("varMatRequestNo", "ColorValue(C.'hex-domain-mat')",
                         "ColorValue(C.'hex-domain-mat' & \"1F\")"),
    },
    "ScreenMeasuringPoint.pa.yaml": {
        "bdgMpNumber": ("varMpRequestNo", "ColorValue(C.'hex-domain-mp')",
                        "ColorValue(C.'hex-domain-mp' & \"1F\")"),
    },
    "ScreenVhPlan.pa.yaml": {
        "bdgVhpNumber": ("varVhpPlanKey", "ColorValue(C.'hex-domain-vhp')",
                         "ColorValue(C.'hex-domain-vhp' & \"1F\")"),
        "bdgVhpPlanHeadBadge": ('If(VhpPlanValid, "Valid", "")', None, None),
        # Planens samlede pris i det foldede planhoved (Peter 2026-10-19).
        "bdgVhpPlanFoldCost": (None, "C.'text-primary'", "C.'state-neutral-bg'"),
        "bdgVhpOpsHeadBadge": ('If(VhpOpsValid, "Valid", "")', None, None),
    },
    "ScreenIssueBoard.pa.yaml": {
        "bdgIbRowNo": ("ThisItem.TicketNo", "C.'color-brand-primary'", "C.'bg-muted'"),
        "bdgIbRowNoC": ("ThisItem.TicketNo", "C.'color-brand-primary'", "C.'bg-muted'"),
        "bdgIbDetNo": ("varIbSel.TicketNo", "C.'color-brand-primary'", "C.'bg-muted'"),
        "bdgIbDetStatus": (None, None, None),
        "bdgIbDetPriority": (None, None, None),
    },
    "ScreenMdHub.pa.yaml": {
        "bdgMdAprNo": ("varMdAprReq.RequestNo", None, None),
        "bdgMdAprChip": ("ThisItem.Label", None, None),
        # SAP OBJECT-popuppen (issue #471) - samme nummerbadge som Approval flow.
        "bdgMdSapNo": ("varMdSapReq.RequestNo", None, None),
    },
}
OLD_NAMES = ("bdgVhpItemsHeadBadge", "bdgVhpEditorHeadBadge", "txtVhpPlanHeadBadge", "txtVhpOpsHeadBadge", "txtIbRowNo", "txtIbDetNo",
             "txtIbDetStatus", "txtIbDetPriority", "txtIbActRole", "txtMdAprChip",
             "imgMdAprNo", "imgEqNumber", "imgMatNumber", "imgMpNumber", "imgVhpNumber")


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
    """Hele formlen (ogsaa over flere linjer) uden '='."""
    m = re.search(r"^( +)%s: \|-\n((?:\1 +.*\n?)+)" % key, block, re.M)
    if not m:
        return None
    lines = [ln.strip() for ln in m.group(2).splitlines()]
    return " ".join(lines).lstrip("=").strip()


def test_every_badge_is_modern_badge_with_our_colors():
    total = 0
    for screen, badges in BADGES.items():
        text = _read(screen)
        assert text.count("Control: ModernBadge") == len(badges), screen
        for name, (content, color, fill) in badges.items():
            block = _block(text, name)
            assert f"Control: {VERSION}" in block, name
            for key, want in (("Content", content), ("Color", color), ("Fill", fill)):
                got = _prop(block, key)
                assert got, (name, key)
                if want:
                    assert got == want, (name, key, got)
            assert _prop(block, "Intent") == "BadgeIntent.Neutral", name
            acc = _prop(block, "AccessibleLabel")
            assert acc and acc != '""', name
            for bad in ("Text", "TabIndex", "FontColor", "FontSize", "ThemeColor", "Image"):
                assert _prop(block, bad) is None, (name, bad)
            total += 1
    # + 1: SAP OBJECT-popuppens nummerbadge (issue #471); - 1: Activity's
    # rollemaerke (issue #475 - rollen staar nu i typen); - 2: Items- og
    # Item-sektionens Valid-badge (issue #530 - flueben i stedet).
    assert total == 15


def test_old_controls_are_gone():
    for screen in BADGES:
        text = _read(screen)
        for old in OLD_NAMES:
            assert f"- {old}:" not in text, (screen, old)


def test_status_colors_are_unchanged():
    """Hvert maerke har samme farvepar pr. status som teksten foer."""
    vhp = _read("ScreenVhPlan.pa.yaml")
    b = _block(vhp, "bdgVhpPlanHeadBadge")
    # Uden Self.Content (#331): farven vaelges af samme betingelse som teksten.
    assert _prop(b, "Fill") == "If(VhpPlanValid, C.'state-ok-bg', C.'state-neutral-bg')"
    assert _prop(b, "Color") == "If(VhpPlanValid, C.'state-ok-fg', C.'text-muted')"
    for screen in ("ScreenVhPlan.pa.yaml", "ScreenIssueBoard.pa.yaml"):
        assert "Self.Content" not in _read(screen), screen
    ib = _read("ScreenIssueBoard.pa.yaml")
    pri = _block(ib, "bdgIbDetPriority")
    assert "\"Urgent\", C.'state-error-bg'" in _prop(pri, "Fill")
    assert "\"Urgent\", C.'state-error-fg'" in _prop(pri, "Color")
    st = _block(ib, "bdgIbDetStatus")
    assert "C.'state-" in _prop(st, "Fill") and "C.'state-" in _prop(st, "Color")
    hub = _read("ScreenMdHub.pa.yaml")
    chip = _block(hub, "bdgMdAprChip")
    assert "\"Approved\", C.'state-ok-bg'" in _prop(chip, "Fill")
    assert "\"Rejected\", C.'state-error-fg'" in _prop(chip, "Color")


def _check_layout():
    spec = importlib.util.spec_from_file_location("tools_check_layout_304",
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


def test_rule_16e_rejects_other_versions_unknown_props_and_missing_colors(tmp_path):
    cl = _check_layout()
    screen = "ScreenMeasuringPoint.pa.yaml"
    shutil.copy(os.path.join(APP, "App.pa.yaml"), tmp_path / "App.pa.yaml")
    text = _read(screen)
    rc, out = _run_rule(cl, tmp_path, screen, text)
    assert rc == 0 and "[16e]" not in out, out

    for bad in ("ModernBadge@0.0.1", "ModernBadge"):
        new = text.replace(f"Control: {VERSION}", f"Control: {bad}", 1)
        rc, out = _run_rule(cl, tmp_path, screen, new)
        assert rc == 1 and "[16e]" in out, (bad, out)

    block = _block(text, "bdgMpNumber")
    new = text.replace(block, re.sub(r"( +)Content: \|-\n",
                                     r'\1ThemeColor: |-\n\1    ="Brand"\n\1Content: |-\n',
                                     block, count=1), 1)
    assert new != text
    rc, out = _run_rule(cl, tmp_path, screen, new)
    assert rc == 1 and "[16e]" in out and "ThemeColor" in out, out

    new = text.replace(block, re.sub(r"( +)Fill: \|-\n +=.*\n", "", block, count=1), 1)
    assert new != text
    rc, out = _run_rule(cl, tmp_path, screen, new)
    assert rc == 1 and "[16e] bdgMpNumber" in out and "Fill" in out, out
