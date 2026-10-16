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
# det gamle billedes (synlighed og billedtekst).
SPINNERS = {
    "ScreenEquipment.pa.yaml": {
        "spnEqSaving": ("IfError(varEqSaving, false)", '""'),
        "spnEqLoadIcon": ("!IfError(varEqLoadFailed, false)", '""'),
        "spnEqFlBusy": ("varEqFlBusy", '"Searching..."'),
    },
    "ScreenMaterial.pa.yaml": {
        "spnMatSaving": ("IfError(varMatSaving, false)", '""'),
        "spnMatLoadIcon": ("!IfError(varMatLoadFailed, false)", '""'),
        "spnMatFlBusy": ("varMatFlBusy", '"Searching..."'),
    },
    "ScreenMeasuringPoint.pa.yaml": {
        "spnMpSaving": ("IfError(varMpSaving, false)", '""'),
        "spnMpLoadIcon": ("!IfError(varMpLoadFailed, false)", '""'),
        "spnMpFlBusy": ("varMpFlBusy", '"Searching..."'),
    },
    "ScreenFunctionalLocation.pa.yaml": {
        "spnFlSaving": ("IfError(varFlSaving, false)", '""'),
        "spnFlLoadIcon": ("!IfError(varFlLoadFailed, false)", '""'),
    },
    "ScreenVhPlan.pa.yaml": {
        "spnVhpSaving": ("IfError(varVhpSaving, false)", '""'),
        "spnVhpLoadIcon": ("!IfError(varVhpLoadFailed, false)", '""'),
        "spnVhpFlBusy": ("varVhpFlBusy", '"Searching..."'),
        "spnVhpVenBusy": ("varVhpVenBusy", '"Searching..."'),
    },
    "ScreenIssueBoard.pa.yaml": {
        "spnIbBusy": ("IfError((varIbBusy || varIbPosting) && !varIbUploading, false)", '""'),
        "spnIbUploading": ("IfError(varIbUploading, false)", '"Uploading files..."'),
    },
    "ScreenKks.pa.yaml": {
        "spnKksLoading": ("IfError(varKksLoading, false)", '""'),
    },
    "ScreenMdHub.pa.yaml": {
        "spnMdNavigating": ("IfError(gblNavigating, false)", '"Opening..."'),
        "spnMdAprSpinner": ("IfError(varMdAprBusy, false)", '""'),
    },
}
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
            assert _prop(block, "Label") == label, name
            if vis:
                assert _prop(block, "Visible") == vis, name
            acc = _prop(block, "AccessibleLabel")
            assert acc and acc != '""', name
            for bad in ("Image", "TabIndex", "Fill", "SpinnerSize", "FontSize", "FontColor"):
                assert _prop(block, bad) is None, (name, bad)
            total += 1
    assert total == 20


def test_overlays_keep_the_scrim_and_center_the_wheel():
    """Sloeret er stadig et billede over hele skaermen (tager trykket);
    hjulet staar oven paa det, midt paa skaermen."""
    for screen, spins in SPINNERS.items():
        text = _read(screen)
        for name in spins:
            if not (name.endswith("Saving") or name in ("spnIbBusy", "spnIbUploading",
                                                       "spnKksLoading", "spnMdNavigating")):
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
    for screen, name in (("ScreenIssueBoard.pa.yaml", "spnIbUploading"),
                         ("ScreenMdHub.pa.yaml", "spnMdNavigating")):
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
