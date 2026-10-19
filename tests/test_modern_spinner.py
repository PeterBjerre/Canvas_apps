# -*- coding: utf-8 -*-
"""
Issue #302 (del af #161): alle hjul er den moderne Spinner
(ModernSpinner@1.1.0) i brandfarven - intet Image med et drejende SVG.
Hvornaar de vises, hvor de staar og deres tekst er uaendret.

    python3 -m pytest tests/test_modern_spinner.py
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
VERSION = "ModernSpinner@1.1.0"

# Skaerm -> {spinner: (Visible, Label)}. Visible og Label er de samme som
# det gamle billedes (synlighed og billedtekst). Gem/upload-sloerene
# (*Saving, IbBusy, IbUploading) er vaek: knappen viser selv sin tilstand,
# med et hjul ved siden af (issue #420, ACT_SPINNERS nederst).
SPINNERS = {
    "ScreenEquipment.pa.yaml": {
        "spnEqLoadIcon": ("!IfError(varEqLoadFailed, false)", '""'),
        "spnEqFlBusy": ("varEqFlBusy", '"Searching..."'),
        # Sidepanelets gem (issue #402).
        "spnEqEditorSaving": ('IfError(varEqPanelSave = "saving", false)', '"Saving..."'),
    },
    "ScreenMaterial.pa.yaml": {
        "spnMatLoadIcon": ("!IfError(varMatLoadFailed, false)", '""'),
        "spnMatFlBusy": ("varMatFlBusy", '"Searching..."'),
        # Sidepanelets gem (issue #402).
        "spnMatEditorSaving": ('IfError(varMatPanelSave = "saving", false)', '"Saving..."'),
    },
    "ScreenMeasuringPoint.pa.yaml": {
        "spnMpLoadIcon": ("!IfError(varMpLoadFailed, false)", '""'),
        "spnMpFlBusy": ("varMpFlBusy", '"Searching..."'),
        # Sidepanelets gem (issue #402).
        "spnMpEditorSaving": ('IfError(varMpPanelSave = "saving", false)', '"Saving..."'),
    },
    "ScreenFunctionalLocation.pa.yaml": {
        "spnFlLoadIcon": ("!IfError(varFlLoadFailed, false)", '""'),
        "spnFlEditorSaving": ('IfError(varFlPanelSave = "saving", false)', '"Saving..."'),
    },
    "ScreenVhPlan.pa.yaml": {
        "spnVhpLoadIcon": ("!IfError(varVhpLoadFailed, false)", '""'),
        "spnVhpFlBusy": ("varVhpFlBusy", '"Searching..."'),
        "spnVhpVenBusy": ("varVhpVenBusy", '"Searching..."'),
    },
    # Gem/upload viser tilstanden i knappen (issue #420, ACT_SPINNERS).
    # Hjulet er kommentarens egen ventetilstand (issue #370) - siden #411 i
    # send-ikonets sted nederst i feltet, uden egen tekst (trinnet staar
    # under feltet, tests/test_issue_board.py).
    "ScreenIssueBoard.pa.yaml": {
        "spnIbPosting": (None, '""'),
        # Formularens gem i sidepanelet (issue #402).
        "spnIbEditorSaving": ('IfError(varIbPanelSave = "saving", false)', '"Saving..."'),
    },
    "ScreenKks.pa.yaml": {
        "spnKksLoading": ("IfError(varKksLoading, false)", '""'),
        "spnKksFlBusy": ("varKksFlBusy", '"Searching..."'),
    },
    "ScreenMdHub.pa.yaml": {
        "spnMdNavigating": ("IfError(gblNavigating, false)", '"Opening..."'),
        "spnMdAprSpinner": ("IfError(varMdAprBusy, false)", '""'),
    },
}


def _act(var, keys, desktop=False):
    """Hjulet ved knapperne (build_helpers.act_status, issue #420)."""
    run = "(" + " || ".join(f'IfError({var} = "{k}", false)' for k in keys) + ")"
    return (f"(LayoutRank >= 3) && {run}" if desktop else run), '""'


# Skaerm -> hjulene ved knapperne (issue #420): (navn, variabel, noegler,
# kun fra Desktop). Headerens hjul ses fra Desktop; bundbjaelkens under.
ACT_SPINNERS = {
    "ScreenVhPlan.pa.yaml": [("spnVhpAct", "varVhpAct", ("save", "submit"), True),
                             ("spnVhpFootAct", "varVhpAct", ("save", "submit"), False)],
    "ScreenFunctionalLocation.pa.yaml": [("spnFlAct", "varFlAct", ("save", "submit"), False)],
    "ScreenIssueBoard.pa.yaml": [("spnIbDetAct", "varIbAct", ("reopen", "archive"), False),
                                 ("spnIbFilesAct", "varIbAct", ("upload",), False),
                                 ("spnIbDelAct", "varIbAct", ("delete",), False)],
}
for _p, _t in (("Eq", "Equipment"), ("Mat", "Material"), ("Mp", "MeasuringPoint")):
    ACT_SPINNERS[f"Screen{_t}.pa.yaml"] = [
        (f"spn{_p}Act", f"var{_p}Act", ("save", "submit", "duplicate"), True),
        (f"spn{_p}FootAct", f"var{_p}Act", ("save", "submit", "duplicate"), False),
        (f"spn{_p}PasteAct", f"var{_p}Act", ("add",), False),
        (f"spn{_p}DelConfirmAct", f"var{_p}Act", ("delete",), False)]
for _screen, _rows in ACT_SPINNERS.items():
    for _name, _var, _keys, _desk in _rows:
        SPINNERS[_screen][_name] = _act(_var, _keys, _desk)

SPIN_RE = re.compile(r"rotate\(\s*360|animateTransform")


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


def test_no_image_spinner_is_left():
    for screen in SPINNERS:
        text = _read(screen)
        assert not SPIN_RE.search(text), screen


def test_every_spinner_is_modern_spinner_in_the_brand_color():
    total = 0
    for screen, spins in SPINNERS.items():
        text = _read(screen)
        assert text.count("Control: ModernSpinner") == len(spins), screen
        for name, (vis, label) in spins.items():
            block = _block(text, name)
            assert f"Control: {VERSION}" in block, name
            assert _prop(block, "BasePaletteColor") == "C.'color-brand-primary'", name
            if label is None:
                assert _prop(block, "Label") not in (None, '""'), name
            else:
                assert _prop(block, "Label") == label, name
            if vis:
                assert _prop(block, "Visible") == vis, name
            acc = _prop(block, "AccessibleLabel")
            assert acc and acc != '""', name
            for bad in ("Image", "TabIndex", "Fill", "SpinnerSize", "FontSize", "FontColor"):
                assert _prop(block, bad) is None, (name, bad)
            total += 1
    # 20 foer #420 + 18 hjul ved knapperne (ACT_SPINNERS).
    assert total == 38


def test_overlays_keep_the_scrim_and_center_the_wheel():
    """Sloeret er stadig et billede over hele skaermen (tager trykket);
    hjulet staar oven paa det, midt paa skaermen."""
    for screen, spins in SPINNERS.items():
        text = _read(screen)
        for name in spins:
            if name not in ("spnKksLoading", "spnMdNavigating"):
                continue
            scrim = "img" + name[3:]
            sb = _block(text, scrim)
            assert "Control: Image" in sb and _prop(sb, "Image") == '""', scrim
            assert _prop(sb, "Width") == "App.Width", scrim
            assert _prop(sb, "Visible") == _prop(_block(text, name), "Visible"), scrim
            assert text.index(f"- {scrim}:") < text.index(f"- {name}:"), name
            block = _block(text, name)
            assert _prop(block, "X") == "(App.Width - Self.Width) / 2", name
            assert _prop(block, "Y") == "(App.Height - Self.Height) / 2", name


def test_caption_stays_below_the_wheel():
    for screen, name in (("ScreenMdHub.pa.yaml", "spnMdNavigating"),):
        block = _block(_read(screen), name)
        assert _prop(block, "LabelPosition") == "SpinnerLabelPosition.Below", name


def test_open_card_shows_wheel_or_error_in_the_same_place():
    for screen, spins in SPINNERS.items():
        name = next((n for n in spins if n.endswith("LoadIcon")), None)
        if not name:
            continue
        text = _read(screen)
        err = _block(text, "img" + name[3:])
        assert "Control: Image" in err and not SPIN_RE.search(err), name
        spin_vis = _prop(_block(text, name), "Visible")
        assert _prop(err, "Visible") == spin_vis.lstrip("!"), name
        for b in (err, _block(text, name)):
            assert _prop(b, "Width") == "40" and _prop(b, "Height") == "40", name


def _check_layout():
    spec = importlib.util.spec_from_file_location("tools_check_layout_302",
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


def test_rule_16c_rejects_image_spinners_and_other_versions(tmp_path):
    cl = _check_layout()
    screen = "ScreenKks.pa.yaml"
    shutil.copy(os.path.join(APP, "App.pa.yaml"), tmp_path / "App.pa.yaml")
    text = _read(screen)
    rc, out = _run_rule(cl, tmp_path, screen, text)
    assert rc == 0 and "[16c]" not in out, out

    # Et andet versionsnummer, ingen version og en ukendt egenskab.
    for bad in ("ModernSpinner@1.0.0", "ModernSpinner"):
        new = text.replace(f"Control: {VERSION}", f"Control: {bad}", 1)
        rc, out = _run_rule(cl, tmp_path, screen, new)
        assert rc == 1 and "[16c]" in out, (bad, out)
    block = _block(text, "spnKksLoading")
    new = text.replace(block, block.replace("            Label: |-",
                                            "            SpinnerSize: |-\n"
                                            "                =1\n"
                                            "            Label: |-", 1), 1)
    rc, out = _run_rule(cl, tmp_path, screen, new)
    assert rc == 1 and "[16c]" in out and "SpinnerSize" in out, out

    # Et drejende SVG i et billede - CSS og SMIL.
    for svg in ("@keyframes s{to{transform:rotate(360deg)}}",
                "<animateTransform attributeName='transform' type='rotate'/>"):
        sb = _block(text, "imgKksLoading")
        new = text.replace(sb, sb.replace("            Image: |-\n                =\"\"",
                                          f"            Image: |-\n                =\"{svg}\"", 1), 1)
        assert new != text
        rc, out = _run_rule(cl, tmp_path, screen, new)
        assert rc == 1 and "[16c] imgKksLoading" in out, (svg, out)
