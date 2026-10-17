# -*- coding: utf-8 -*-
"""
Issue #305: gem- og upload-indikatorerne er den moderne Progress bar
(ModernProgressBar@1.0.0, ubestemt) - og de vises og skjules paa PRAECIS
de samme betingelser som foer.

    python3 -m pytest tests/test_modern_progress_bar.py
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
VERSION = "ModernProgressBar@1.0.0"

# Skaerm -> [(sloer, busy-udtryk foer #305, billedtekst)]. Busy-udtrykket
# er det, sloeret havde i Visible foer; det maa ikke aendre sig.
OVERLAYS = {
    "ScreenEquipment.pa.yaml": [("imgEqSaving", "varEqSaving", None)],
    "ScreenMaterial.pa.yaml": [("imgMatSaving", "varMatSaving", None)],
    "ScreenMeasuringPoint.pa.yaml": [("imgMpSaving", "varMpSaving", None)],
    "ScreenFunctionalLocation.pa.yaml": [("imgFlSaving", "varFlSaving", None)],
    "ScreenVhPlan.pa.yaml": [("imgVhpSaving", "varVhpSaving", None)],
    "ScreenIssueBoard.pa.yaml": [
        ("imgIbBusy", "(varIbBusy || varIbPosting) && !varIbUploading", None),
        ("imgIbUploading", "varIbUploading", "Uploading files..."),
    ],
}
# Indlaesning (ikke gem/upload) er ikke dette issue - de er hjul (#302).
NOT_PROGRESS = {"ScreenKks.pa.yaml": "imgKksLoading", "ScreenMdHub.pa.yaml": "imgMdNavigating"}


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
    return m.group(1) if m else None


def test_saving_and_uploading_are_indeterminate_progress_bars():
    total = 0
    for screen, rows in OVERLAYS.items():
        text = _read(screen)
        assert text.count(f"Control: {VERSION}") == len(rows), screen
        for img, busy, caption in rows:
            vis = f"IfError({busy}, false)"
            scrim = _block(text, img)
            assert "Control: Image" in scrim
            assert _prop(scrim, "Image") == '""', img           # intet hjul mere
            assert "rotate(360" not in scrim
            assert _prop(scrim, "Visible") == vis, img
            bar = _block(text, "prg" + img[3:])
            assert f"Control: {VERSION}" in bar, img
            assert _prop(bar, "Indeterminate") == "true", img
            assert _prop(bar, "Visible") == vis, img
            assert _prop(bar, "AccessibleLabel") == _prop(scrim, "AccessibleLabel"), img
            for gone in ("Label", "TabIndex", "OnChange", "Color", "Fill"):
                assert _prop(bar, gone) is None, (img, gone)
            cap_name = "txt" + img[3:] + "Caption"
            if caption:
                cap = _block(text, cap_name)
                assert _prop(cap, "Text") == f'"{caption}"'
                assert _prop(cap, "Visible") == vis
            else:
                assert f"- {cap_name}:" not in text
            # sloer, bjaelke, (tekst) i den raekkefoelge - oeverst til sidst.
            assert text.index(f"- {img}:") < text.index(f"- prg{img[3:]}:")
            total += 1
    assert total == 7


def test_loading_overlays_are_not_progress_bars():
    for screen, name in NOT_PROGRESS.items():
        text = _read(screen)
        assert "ModernProgressBar" not in text, screen
        assert f"- {name}:" in text, screen


def _check_layout():
    spec = importlib.util.spec_from_file_location("tools_check_layout_305",
                                                  os.path.join(TOOLS, "check_layout.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_rule_16f_rejects_other_versions_props_and_determinate(tmp_path):
    cl = _check_layout()
    screen = "ScreenEquipment.pa.yaml"
    shutil.copy(os.path.join(APP, "App.pa.yaml"), tmp_path / "App.pa.yaml")
    text = _read(screen)
    bad_texts = [
        None,
        text.replace(f"Control: {VERSION}", "Control: ModernProgressBar@0.9.0", 1),
        text.replace(f"Control: {VERSION}", "Control: ModernProgressBar", 1),
        text.replace("Indeterminate: |-\n                =true",
                     "Indeterminate: |-\n                =false", 1),
        text.replace("ProgressColor: |-", "TabIndex: |-\n                =0\n"
                     "            ProgressColor: |-", 1),
    ]
    for new in bad_texts:
        assert new is None or new != text
        (tmp_path / screen).write_text(text if new is None else new, encoding="utf-8")
        old_argv, sys.argv = sys.argv, ["check_layout.py", str(tmp_path / screen)]
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                rc = cl.main()
        finally:
            sys.argv = old_argv
        if new is None:
            assert rc == 0 and "[16f]" not in buf.getvalue(), buf.getvalue()
        else:
            assert rc == 1 and "[16f]" in buf.getvalue(), buf.getvalue()
