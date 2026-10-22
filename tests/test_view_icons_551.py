# -*- coding: utf-8 -*-
"""Ingen blyant i View mode (issue #551).

Blyanten (Fluent "Edit" / SVG-blyanten) staar kun, hvor indholdet
reelt kan rettes. Kan det kun laeses, er ikonet et View-ikon
(icons.FLUENT["view"] / oejet i hubben), tooltippet siger "View ...",
og knappen skifter aldrig siden til Edit mode."""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DIR = os.path.join(ROOT, "BIO SAP App")
sys.path.insert(0, os.path.join(ROOT, "tools"))

import icons  # noqa: E402
import action_tips as tips  # noqa: E402


def _yaml(screen):
    return open(os.path.join(APP_DIR, screen + ".pa.yaml"), encoding="utf-8").read()


def _block(y, name):
    lines = y.split("\n")
    for i, line in enumerate(lines):
        if re.match(r"^ *- %s:$" % name, line):
            ind = len(line) - len(line.lstrip())
            j = i + 1
            while j < len(lines) and (not lines[j].strip()
                                      or len(lines[j]) - len(lines[j].lstrip()) > ind):
                j += 1
            return "\n".join(lines[i:j])
    raise AssertionError(name)


def _prop(block, prop):
    m = re.search(r"\n( *)%s: \|-\n((?:\1 .*\n?)*)" % prop, block)
    assert m, prop
    return "\n".join(l.strip() for l in m.group(2).strip("\n").split("\n"))


def test_shared_helpers():
    assert icons.edit_or_view("x") == 'If(x, "DocumentText", "Edit")'
    assert icons.FLUENT["view"] == "DocumentText"
    assert tips.edit_or_view("details", "x") == 'If(x, "View details", "Edit details")'
    assert tips.edit_or_view("class data") == '"Edit class data"'
    assert tips.edit_row("x") == 'If(x, "View row", "Edit row")'


def test_domain_row_open_is_view_icon_when_locked():
    for screen, tag in (("ScreenEquipment", "Eq"), ("ScreenMaterial", "Mat"),
                        ("ScreenMeasuringPoint", "Mp")):
        y = _yaml(screen)
        locked = f'(var{tag}ViewOnly || ThisItem.Status = "submitted")'
        for name in (f"btn{tag}RowOpen", f"btn{tag}RowOpenC"):
            b = _block(y, name)
            assert _prop(b, "Icon") == f'=If({locked}, "DocumentText", "Edit")', name
            assert _prop(b, "Tooltip") == f'=If({locked}, "View row", "Edit row")', name
            # Aabner sidepanelet - skifter aldrig til Edit mode.
            assert f"Set(var{tag}ViewOnly" not in _prop(b, "OnSelect"), name


def test_fl_classes_open_uses_shared_helper():
    b = _block(_yaml("ScreenFunctionalLocation"), "btnFlCOpen")
    locked = 'varFlViewOnly || varFlStatus = "Indsendt"'
    assert _prop(b, "Icon") == f'=If({locked}, "DocumentText", "Edit")'
    assert "Set(varFlViewOnly" not in _prop(b, "OnSelect")


def test_vh_section_edit_buttons_only_in_edit_mode():
    y = _yaml("ScreenVhPlan")
    for name in ("btnVhpPlanSave", "btnVhpSaveItem", "btnVhpTasklistSave"):
        assert _prop(_block(y, name), "Visible") == "=!varVhpViewOnly", name
    # Reset regner med den SAMME synlighed for Save/Edit (mobilbredden).
    reset = _prop(_block(y, "btnVhpResetItem"), "Width")
    assert "Max(1, 1 + If(!varVhpViewOnly, 1, 0))" in reset


def test_hub_shows_eye_not_disabled_pencil():
    y = _yaml("ScreenMdHub")
    app = open(os.path.join(APP_DIR, "App.pa.yaml"), encoding="utf-8").read()
    assert 'Key: "edit-off"' not in app and 'Key: "view"' in app
    for name in ("btnMdRowEdit", "btnMdRowEditC"):
        b = _block(y, name)
        assert "DisplayMode" not in b, name
        img = _prop(b, "Image")
        assert 'Key = "edit"' in img and 'Key = "view"' in img and "edit-off" not in img
        on = _prop(b, "OnSelect")
        # Kan rettes: "edit:" - ellers aabnes anmodningen i View ("req:").
        assert '"edit:" & ThisItem.RequestGuid' in on and '"req:" & ThisItem.RequestGuid' in on
        assert '"View request", "Edit request")' in _prop(b, "Tooltip")


def test_no_pencil_reachable_in_view_mode():
    """Hver knap med blyanten er enten et View/Edit-skift, kun synlig i
    Edit mode, eller sidehovedets Edit (kun synlig i View, naar brugeren
    maa rette - indgangen til Edit mode)."""
    page_edit = re.compile(r"^=(IfError\()?var\w+ViewOnly && var\w+CanEdit(, false\))?$")
    for f in sorted(os.listdir(APP_DIR)):
        if not (f.startswith("Screen") and f.endswith(".pa.yaml")):
            continue
        y = _yaml(f[:-len(".pa.yaml")])
        for m in re.finditer(r"^ *- (\w+):$", y, re.M):
            name = m.group(1)
            b = _block(y, name)
            head = b.split("\n")[1] if "\n" in b else ""
            if "ModernButton" not in head:
                continue
            if not re.search(r"\n *Icon: \|-\n", b):
                continue
            icon = _prop(b, "Icon")
            if '"Edit"' not in icon:
                continue
            vis = _prop(b, "Visible") if re.search(r"\n *Visible: \|-\n", b) else "=true"
            ok = ('"DocumentText"' in icon and "ViewOnly" in icon) \
                or "!varVhpViewOnly" in vis or "!(varVhpViewOnly" in vis \
                or page_edit.match(vis) \
                or name == "btnIbEdit"   # Issue Board: kun synlig, naar issuet kan rettes
            assert ok, f"{f}: {name} viser blyanten i View mode ({icon} / {vis})"
