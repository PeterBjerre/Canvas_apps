# -*- coding: utf-8 -*-
"""
Issue #420: ingen ventebjaelke midt paa skaermen - tilstanden staar i den
knap, der startede handlingen.

  - Ingen skaerm har ModernProgressBar, det graa gem-sloer (img<X>Saving,
    imgIbBusy, imgIbUploading) eller de gamle busy-variabler, der kun
    styrede sloeret (varDomSaving, varFlSaving). tools/progress_overlay.py
    er slettet, og check_layout regel 16f afviser en bjaelke.
  - Hver knap, der foer taendte bjaelken, siger "Saving..." /
    "Submitting..." / "Deleting..." o.l., mens dens handling koerer, og er
    spaerret, mens en handling paa skaermen koerer. Det er handlingens
    eneste ventetegn (issue #441) - intet hjul ved siden af.
  - Tilstanden saettes lige foer og lige efter selve handlingen - ingen
    timer i OnSelect. Udfaldet ("<noegle>:ok"/":failed") staar ved knappen.
  - Et gennemsigtigt lag fanger tryk imens; det tegner intet.
  - Tilstanden nulstilles, naar skaermen klargoeres.

Power Fx kan ikke koeres her, saa testene laeser de GENEREREDE skaerme og
byggeklodserne.

    python3 -m pytest tests/test_button_loading.py
"""
import importlib.util
import io
import os
import re
import shutil
import sys
from contextlib import redirect_stdout

import pytest

from conftest import ROOT, TOOLS

APP = os.path.join(ROOT, "BIO SAP App")
SCREENS = sorted(f for f in os.listdir(APP) if f.startswith("Screen") and f.endswith(".pa.yaml"))

# Skaerm -> (tilstandsvariabel, [(knap, noegle, ventetekst)])
BUTTONS = {
    "ScreenVhPlan.pa.yaml": ("varVhpAct", [
        ("btnVhpSaveDraft", "save", "Saving..."),
        ("btnVhpFootSaveDraft", "save", "Saving..."),
        ("btnVhpSubmit", "submit", "Submitting..."),
        ("btnVhpFootSubmit", "submit", "Submitting..."),
    ]),
    "ScreenFunctionalLocation.pa.yaml": ("varFlAct", [
        ("btnFlSaveDraft", "save", "Saving..."),
        ("btnFlSubmit", "submit", "Submitting..."),
    ]),
    "ScreenIssueBoard.pa.yaml": ("varIbAct", [
        ("btnIbReopen", "reopen", "Reopening..."),
        ("btnIbUpload", "upload", "Saving..."),
        ("btnIbDelConfirm", "delete", "Deleting..."),
    ]),
}
for _p, _t in (("Eq", "Equipment"), ("Mat", "Material"), ("Mp", "MeasuringPoint")):
    BUTTONS[f"Screen{_t}.pa.yaml"] = (f"var{_p}Act", [
        (f"btn{_p}SendDraft", "save", "Saving..."),
        (f"btn{_p}FootSendDraft", "save", "Saving..."),
        (f"btn{_p}Submit", "submit", "Submitting..."),
        (f"btn{_p}FootSubmit", "submit", "Submitting..."),
        (f"btn{_p}Duplicate", "duplicate", "Duplicating..."),
        (f"btn{_p}PasteAdd", "add", "Adding..."),
        (f"btn{_p}DeleteConfirm", "delete", "Deleting..."),
    ])

# Knappen, der faktisk koerer handlingen (Submit koerer fra bekraeftelsen).
RUNS = {
    "ScreenVhPlan.pa.yaml": ["btnVhpSaveDraft"],
    "ScreenFunctionalLocation.pa.yaml": ["btnFlSaveDraft", "btnFlSubmitConfirm"],
    "ScreenIssueBoard.pa.yaml": ["btnIbReopen", "btnIbUpload", "btnIbDelConfirm",
                                 "btnIbArchive", "btnIbRestore"],
}
for _p, _t in (("Eq", "Equipment"), ("Mat", "Material"), ("Mp", "MeasuringPoint")):
    RUNS[f"Screen{_t}.pa.yaml"] = [f"btn{_p}SendDraft", f"btn{_p}SubmitConfirm",
                                   f"btn{_p}Duplicate", f"btn{_p}PasteAdd",
                                   f"btn{_p}DeleteConfirm"]

_TEXT = {}


def _read(screen):
    if screen not in _TEXT:
        _TEXT[screen] = open(os.path.join(APP, screen), encoding="utf-8").read()
    return _TEXT[screen]


def _block(text, name):
    m = re.search(r"^( *)- %s:\n" % name, text, re.M)
    assert m, name
    rest = text[m.end():]
    end = re.search(r"^ {0,%d}- \w+:" % len(m.group(1)), rest, re.M)
    return rest[:end.start()] if end else rest


def _prop(block, key):
    """Hele egenskaben (ogsaa over flere linjer), uden '='."""
    m = re.search(r"^( +)%s: \|-\n" % key, block, re.M)
    if not m:
        return None
    lines = []
    for line in block[m.end():].split("\n"):
        if line.strip() and len(line) - len(line.lstrip()) <= len(m.group(1)):
            break
        lines.append(line.strip())
    return "\n".join(lines).strip().lstrip("=")


def _running(var):
    return f'IfError(!IsBlank({var}) && !(":" in {var}), false)'


def test_no_center_bar_or_grey_saving_scrim_is_left():
    assert not os.path.exists(os.path.join(TOOLS, "progress_overlay.py"))
    for screen in SCREENS:
        text = _read(screen)
        assert "ModernProgressBar" not in text, screen
        names = re.findall(r"^ *- (\w+):\n", text, re.M)
        for n in names:
            assert not re.fullmatch(r"(img|prg|txt)\w*Saving(Caption)?", n), (screen, n)
            assert n not in ("imgIbBusy", "imgIbUploading", "prgIbBusy", "prgIbUploading"), n
        # Variablerne, der KUN styrede sloeret, er vaek.
        for var in ("varEqSaving", "varMatSaving", "varMpSaving", "varFlSaving",
                    "varDomSaving"):
            assert var not in text, (screen, var)


def test_no_builder_imports_the_old_overlay():
    for base, _dirs, files in os.walk(ROOT):
        if "/.git" in base or base.startswith(os.path.join(ROOT, "tests")):
            continue
        for f in files:
            if f.endswith(".py"):
                src = open(os.path.join(base, f), encoding="utf-8").read()
                assert "import progress_overlay" not in src and \
                    "from progress_overlay" not in src, f


@pytest.mark.parametrize("screen", sorted(BUTTONS))
def test_every_button_has_its_own_busy_state(screen):
    var, rows = BUTTONS[screen]
    text = _read(screen)
    for name, key, busy in rows:
        b = _block(text, name)
        t = _prop(b, "Text")
        assert t.startswith(f'If(IfError({var} = "{key}", false), "{busy}", '), (name, t[:80])
        dm = _prop(b, "DisplayMode")
        assert dm.startswith(f"If({_running(var)}, DisplayMode.Disabled, "), (name, dm[:80])


@pytest.mark.parametrize("screen", sorted(RUNS))
def test_state_is_set_right_before_and_after_the_action(screen):
    var = BUTTONS[screen][0]
    text = _read(screen)
    for name in RUNS[screen]:
        on = _prop(_block(text, name), "OnSelect")
        assert f"Set({var}, " in on, name
        # Ingen fast varighed: ingen timer startes af knappen.
        assert "Timer" not in on and "tmr" not in on, name
        # Afslutningen: udfaldet - eller tom, naar handlingen blev stoppet.
        tail = on.rstrip()
        assert (tail.endswith(f'If({_running(var)}, Set({var}, ""))')
                or tail.endswith(f'If({_running(var)}, Set({var}, {var} & ":failed"))')
                or f'Set({var}, {var} & If(' in tail
                or f'If(!IfError({var} = "delete:failed", false)' in tail), (name, tail[-120:])


@pytest.mark.parametrize("screen", sorted(BUTTONS))
def test_note_sits_next_to_the_buttons(screen):
    """"Saved"/"Save failed" ved knapperne (issue #420). Hjulet ved siden
    af er vaek (issue #441) - kun en ren ikonknap har det stadig, se
    tests/test_one_loading_indicator.py."""
    var = BUTTONS[screen][0]
    text = _read(screen)
    notes = re.findall(r"^ *- (txt\w+ActNote):\n", text, re.M)
    assert notes, screen
    for note in notes:
        nb = _block(text, note)
        assert ":ok" in _prop(nb, "Text") and ":failed" in _prop(nb, "Text"), note
        # Groen ved succes, roed ved fejl.
        assert "state-error-fg" in _prop(nb, "Color") and "state-ok-fg" in _prop(nb, "Color")
        assert var in _prop(nb, "Visible"), note


@pytest.mark.parametrize("screen", sorted(BUTTONS))
def test_transparent_block_while_running_and_a_brief_ok(screen):
    var = BUTTONS[screen][0]
    p = var[3:-3]
    text = _read(screen)
    b = _block(text, f"img{p}ActBlock")
    assert _prop(b, "Visible") == _running(var)
    assert _prop(b, "Image") == '""'
    assert _prop(b, "Fill") == _prop(b, "HoverFill") == "RGBA(0, 0, 0, 0)"
    # Laget staar oven paa popupperne - kun den samlede apps aabne-kort og
    # beskeden (toast) ligger over det (plus den skjulte Open-knap).
    top = re.findall(r"^      - (\w+):\n", text, re.M)
    after = top[top.index(f"img{p}ActBlock") + 1:]
    assert all(re.search(r"Open$|Load|Toast", n) for n in after), after
    tmr = _block(text, f"tmr{p}ActDone")
    assert _prop(tmr, "Start") == f'IfError(EndsWith({var}, ":ok"), false)'
    assert _prop(tmr, "OnTimerEnd") == f'If(IfError(EndsWith({var}, ":ok"), false), Set({var}, ""))'


@pytest.mark.parametrize("screen", sorted(BUTTONS))
def test_state_is_cleared_when_the_screen_is_prepared(screen):
    """Klargoeringen (den skjulte Open-knap, Issue Boards OnVisible)
    nulstiller tilstanden - intet gammelt "saving" kan laase skaermen."""
    var = BUTTONS[screen][0]
    text = _read(screen)
    p = var[3:-3]
    if f"- btn{p}Open:" in text:
        prep = _prop(_block(text, f"btn{p}Open"), "OnSelect")
    else:
        prep = text.split("    Children:")[0]
    assert f'Set({var}, "")' in prep


def test_panel_save_buttons_say_saving():
    for screen, name, var in (
            ("ScreenFunctionalLocation.pa.yaml", "btnFlEditorSave", "varFlPanelSave"),
            ("ScreenMaterial.pa.yaml", "btnMatSave", "varMatPanelSave"),
            ("ScreenEquipment.pa.yaml", "btnEqSave", "varEqPanelSave"),
            ("ScreenMeasuringPoint.pa.yaml", "btnMpSave", "varMpPanelSave"),
            ("ScreenIssueBoard.pa.yaml", "btnIbFormSubmit", "varIbPanelSave")):
        b = _block(_read(screen), name)
        assert _prop(b, "Text").startswith(f'If(IfError({var} = "saving", false), '), name
        assert '"Saving..."' in _prop(b, "Text"), name
        # Ikonet viger for teksten imens, saa bredden staar fast.
        assert _prop(b, "Layout").startswith(f'If(IfError({var} = "saving", false), '
                                             "ButtonLayout.TextOnly, "), name


def test_comment_posting_is_not_part_of_the_button_state():
    """Kommentaren har sin egen tilstand i feltet (issue #370/#418)."""
    on = _prop(_block(_read("ScreenIssueBoard.pa.yaml"), "btnIbSend"), "OnSelect") \
        if "- btnIbSend:" in _read("ScreenIssueBoard.pa.yaml") else ""
    assert "varIbAct" not in on


def test_act_fx_sets_before_and_ends_after():
    sys.path.insert(0, TOOLS)
    import build_helpers as bh
    fx = bh.act_fx("varXAct", "save", "DoIt()")
    assert fx.split(";\n") == ['Set(varXAct, "save")', "DoIt()",
                              f'If({_running("varXAct")}, Set(varXAct, ""))']
    fx = bh.act_fx("varXAct", "save", "DoIt()", busy_var="varXBusy", ok="Ok()")
    assert fx.split(";\n") == ['Set(varXAct, "save")', "Set(varXBusy, true)", "DoIt()",
                              "Set(varXBusy, false)",
                              'Set(varXAct, varXAct & If(Ok(), ":ok", ":failed"))']
    assert bh.act_mark("varXAct", "add") == 'Set(varXAct, "add:ok")'
    assert bh.act_mark("varXAct", "add", False) == 'Set(varXAct, "add:failed")'


def _check_layout():
    spec = importlib.util.spec_from_file_location("tools_check_layout_420",
                                                  os.path.join(TOOLS, "check_layout.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_rule_16f_rejects_a_progress_bar(tmp_path):
    cl = _check_layout()
    screen = "ScreenEquipment.pa.yaml"
    shutil.copy(os.path.join(APP, "App.pa.yaml"), tmp_path / "App.pa.yaml")
    text = _read(screen)
    bad = text.replace("Control: ModernSpinner@1.1.0", "Control: ModernProgressBar@1.0.0", 1)
    assert bad != text
    for new, want in ((text, 0), (bad, 1)):
        (tmp_path / screen).write_text(new, encoding="utf-8")
        old_argv, sys.argv = sys.argv, ["check_layout.py", str(tmp_path / screen)]
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                rc = cl.main()
        finally:
            sys.argv = old_argv
        assert ("[16f]" in buf.getvalue()) == bool(want), buf.getvalue()[-500:]
        if not want:
            assert rc == 0, buf.getvalue()[-500:]
