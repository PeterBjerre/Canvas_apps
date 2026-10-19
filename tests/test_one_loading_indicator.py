# -*- coding: utf-8 -*-
"""
Issue #441: eet ventetegn pr. handling - i den knap, der startede den.

  - Sidepanelets Save siger "Saving..." og er spaerret; hjulet med
    "Saving..." over bundbjaelken (spn<X>EditorSaving) er vaek. Fejlen og
    Retry staar der stadig.
  - Save draft, Submit, Duplicate, Add rows, Delete, Reopen og Save
    documents siger selv "Saving..." o.l.; hjulet ved siden af er vaek.
    Kun en knap, der kan vaere sit ikon alene (Archive/Restore, FL's
    knapper under Desktop, Duplicate paa en telefon), har stadig hjulet -
    og kun mens den er det.
  - Dokumentpopuppens "Save documents" siger "Saving..." - linjen
    "Saving documents... please wait." under knappen er vaek.
  - FL-/leverandoersoegningen: hjulet med "Searching..." i Search-knappens
    plads er det ene tegn; beskeden under feltet siger ikke ogsaa
    "Searching for ...".
  - VH-planens statuslinje siger ikke "Saving ..." ved siden af knappen.
  - check_layout regel 16g holder det saadan.

Power Fx kan ikke koeres her, saa testene laeser byggeklodserne og de
GENEREREDE skaerme.

    python3 -m pytest tests/test_one_loading_indicator.py
"""
import importlib.util
import io
import os
import re
import shutil
import sys
from contextlib import redirect_stdout

from conftest import ROOT, TOOLS

import build_helpers as bh
import build_flsearch as fl

APP = os.path.join(ROOT, "BIO SAP App")
SCREENS = sorted(f for f in os.listdir(APP) if f.startswith("Screen") and f.endswith(".pa.yaml"))


def _read(screen):
    return open(os.path.join(APP, screen), encoding="utf-8").read()


def _block(text, name):
    m = re.search(r"^( *)- %s:\n" % name, text, re.M)
    assert m, name
    rest = text[m.end():]
    end = re.search(r"^ {0,%d}- \w+:" % len(m.group(1)), rest, re.M)
    return rest[:end.start()] if end else rest


def _prop(block, key):
    m = re.search(r"^ +%s: \|-\n +=(.*)$" % key, block, re.M)
    return m.group(1).strip() if m else None


def test_act_status_has_no_wheel_unless_the_button_can_be_icon_only():
    act = "varXAct"
    kids = bh.act_status("XAct", act, ("save", "submit"))
    assert [k.name for k in kids] == ["txtXActNote"]
    # En knap, der altid viser sin tekst, giver intet hjul.
    kids = bh.act_status("XAct", act, ("save", "submit"), spin={"save": None})
    assert [k.name for k in kids] == ["txtXActNote"]
    kids = bh.act_status("XAct", act, ("save", "submit"), spin={"save": "LayoutRank < 3"})
    assert [k.name for k in kids] == ["spnXAct", "txtXActNote"]
    vis = kids[0].props["Visible"]
    assert vis == '((IfError(varXAct = "save", false) && (LayoutRank < 3)))'
    assert "submit" not in vis


def test_icon_only_when_reads_the_button_layout():
    b = bh.button("btnX", '"Save"', "true", icon="Save")
    assert bh.icon_only_when(b) is None
    b.props["Layout"] = "If(LayoutRank < 2, ButtonLayout.IconOnly, ButtonLayout.IconBefore)"
    assert bh.icon_only_when(b) == "LayoutRank < 2"
    b.props["Layout"] = "ButtonLayout.IconOnly"
    assert bh.icon_only_when(b) == "true"


def test_panel_save_status_is_only_the_failure():
    status = bh.panel_save_status("X", "varXPanelSave", "true")
    assert [k.name for k in status.children] == ["txtXEditorSaveFailed", "btnXEditorRetry"]
    assert status.props["Visible"] == 'IfError(varXPanelSave = "failed", false)'


def test_no_wheel_repeats_what_a_button_already_says():
    """Ingen ModernSpinner viser en tilstand, som en knap med synlig tekst
    allerede siger (samme kontrol som regel 16g)."""
    busy_text = re.compile(r'If\(IfError\((\w+) = "(\w+)", false\), "')
    state = re.compile(r'IfError\((\w+) = "(\w+)", false\)')
    for screen in SCREENS:
        text = _read(screen)
        said = {}
        for m in re.finditer(r"^ *- (btn\w+):\n", text, re.M):
            b = _block(text, m.group(1))
            if "Control: ModernButton" not in b:
                continue
            for st in busy_text.findall(_prop(b, "Text") or ""):
                said.setdefault(st, []).append((m.group(1), "IconOnly" in (_prop(b, "Layout") or "")))
        for m in re.finditer(r"^ *- (spn\w+):\n", text, re.M):
            vis = _prop(_block(text, m.group(1)), "Visible") or ""
            for st in state.findall(vis):
                for btn, icon_only in said.get(st, []):
                    assert icon_only, (screen, m.group(1), btn, st)
        assert not re.search(r"spn\w+EditorSaving:", text), screen


def test_document_save_says_saving_in_the_button():
    for screen, p in (("ScreenEquipment.pa.yaml", "Eq"), ("ScreenMaterial.pa.yaml", "Mat"),
                      ("ScreenVhPlan.pa.yaml", "Vhp")):
        text = _read(screen)
        b = _block(text, f"btn{p}AttUpload")
        busy = f"IfError(Coalesce(var{p}AttBusy, false), false)"
        assert _prop(b, "Text") == f'If({busy}, "Saving...", "Save documents")', screen
        assert _prop(b, "DisplayMode").startswith(f"If({busy} || "), screen
        assert "Saving documents" not in text and f"txt{p}AttStatus" not in text, screen


def test_search_does_not_say_searching_twice():
    fx = fl.search_action("x", "colX", "varXMsg", raw_var="varXRaw", busy_var="varXBusy")
    assert 'Set(varXMsg, "");' in fx and "Searching for" not in fx
    # Uden hjul er beskeden stadig det, der siger, at der soeges.
    fx = fl.search_action("x", "colX", "varXMsg", raw_var="varXRaw")
    assert "Searching for" in fx
    for screen in SCREENS:
        assert "Searching for" not in _read(screen), screen


def test_vh_plan_status_line_does_not_say_saving():
    text = _read("ScreenVhPlan.pa.yaml")
    block = _block(text, "txtVhpReadiness")
    assert "Saving" not in block
    # Knapperne siger det selv.
    assert '"Saving..."' in _prop(_block(text, "btnVhpSaveDraft"), "Text")


def _check_layout():
    spec = importlib.util.spec_from_file_location("tools_check_layout_441",
                                                  os.path.join(TOOLS, "check_layout.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run(cl, tmp_path, screen, text):
    (tmp_path / screen).write_text(text, encoding="utf-8")
    old_argv, sys.argv = sys.argv, ["check_layout.py", str(tmp_path / screen)]
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            rc = cl.main()
    finally:
        sys.argv = old_argv
    return rc, buf.getvalue()


def test_rule_16g_rejects_a_second_loading_indicator(tmp_path):
    cl = _check_layout()
    screen = "ScreenIssueBoard.pa.yaml"
    shutil.copy(os.path.join(APP, "App.pa.yaml"), tmp_path / "App.pa.yaml")
    text = _read(screen)
    rc, out = _run(cl, tmp_path, screen, text)
    assert rc == 0 and "[16g]" not in out, out

    # Hjulet ogsaa for Reopen, der selv siger "Reopening...".
    old = '=(IfError(varIbAct = "archive", false))'
    assert text.count(old) == 1
    new = text.replace(old, '=(IfError(varIbAct = "reopen", false) || '
                            'IfError(varIbAct = "archive", false))')
    rc, out = _run(cl, tmp_path, screen, new)
    assert rc == 1 and "[16g] spnIbDetAct" in out and "btnIbReopen" in out, out

    # En ventetekst for sig selv, uden for knappen.
    old = '="Loading the rest of the issue..."'
    assert old in text
    new = text.replace(old, '="Saving the issue..."')
    rc, out = _run(cl, tmp_path, screen, new)
    assert rc == 1 and "[16g] txtIbDetLoading" in out, out
