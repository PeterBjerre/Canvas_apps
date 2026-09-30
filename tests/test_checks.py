# -*- coding: utf-8 -*-
"""
Tjekkene skal FEJLE, naar fejlen er der.

Hvert tjek i tools/ er vores eneste vagt mod en fejlklasse, og et tjek,
der aldrig er set fejle, er ikke en vagt. Her plantes fejlen i en KOPI af
det byggede output (eller i en midlertidig fil), og tjekket skal melde den.

    python3 -m pytest tests
"""
import io
import os
import re
import shutil
import sys
from contextlib import redirect_stdout

import pytest

from conftest import ROOT

APP = os.path.join(ROOT, "Equipment App")
SCREEN = "ScreenEquipment.pa.yaml"


def _layout(tmp_path, mutate):
    """Koer check_layout paa en kopi af Equipment-skaermen, hvor mutate()
    har plantet en fejl. Returnerer (exitkode, output)."""
    import check_layout
    shutil.copy(os.path.join(APP, "App.pa.yaml"), tmp_path / "App.pa.yaml")
    text = open(os.path.join(APP, SCREEN), encoding="utf-8").read()
    new = mutate(text)
    assert new != text, "mutationen ramte ikke noget - testen er forkert"
    (tmp_path / SCREEN).write_text(new, encoding="utf-8")
    old_argv = sys.argv
    sys.argv = ["check_layout.py", str(tmp_path / SCREEN)]
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            rc = check_layout.main()
    finally:
        sys.argv = old_argv
    return rc, buf.getvalue()


def test_layout_clean_screen_passes(tmp_path):
    rc, out = _layout(tmp_path, lambda t: t + "\n")
    assert rc == 0, out


def test_layout_rule_1_height_references_other_control(tmp_path):
    def plant(t):
        return re.sub(r"(conDomFormCard:\n(?:.*\n)*?\s+Height: \|-\n\s+)=[^\n]+",
                      r"\1=btnDomSave.Height + 10", t, count=1)
    rc, out = _layout(tmp_path, plant)
    assert rc == 1 and "[1]" in out


def test_layout_rule_8c_app_width_comparison(tmp_path):
    def plant(t):
        return t.replace("=LayoutRank", "=If(App.Width < 900, 1, 2) + 0 * LayoutRank", 1)
    rc, out = _layout(tmp_path, plant)
    assert rc == 1 and "[8c]" in out


def test_layout_rule_0_duplicate_name(tmp_path):
    def plant(t):
        return t.replace("btnDomNew:", "btnDomSave:", 1)
    rc, out = _layout(tmp_path, plant)
    assert rc == 1 and "[0]" in out


def test_layout_rule_31_string_column_name(tmp_path):
    def plant(t):
        return t.replace("=LayoutRank", '=CountRows(GroupBy(colDomRows, "Plant", "G")) * 0 + LayoutRank', 1)
    rc, out = _layout(tmp_path, plant)
    assert rc == 1 and "[31]" in out


def test_color_guard_finds_rgba(tmp_path, monkeypatch):
    import build_all
    app = tmp_path / "X" / "build"
    app.mkdir(parents=True)
    (app / "b.py").write_text('FILL = "RGBA(1, 2, 3, 1)"\n', encoding="utf-8")
    (tmp_path / "tools").mkdir()
    monkeypatch.setattr(build_all, "ROOT", str(tmp_path))
    monkeypatch.setattr(build_all, "APPS", [("X", [])])
    bad = build_all.check_no_raw_colors()
    assert len(bad) == 1 and "RGBA" in bad[0]


def test_color_guard_ignores_docstrings(tmp_path, monkeypatch):
    import build_all
    app = tmp_path / "X" / "build"
    app.mkdir(parents=True)
    (app / "b.py").write_text('"""Skriv aldrig RGBA(1, 2, 3, 1) her."""\n', encoding="utf-8")
    (tmp_path / "tools").mkdir()
    monkeypatch.setattr(build_all, "ROOT", str(tmp_path))
    monkeypatch.setattr(build_all, "APPS", [("X", [])])
    assert build_all.check_no_raw_colors() == []


def test_secret_check_finds_sas_signature():
    import check_secrets
    url = b"https://x.example/invoke?api-version=1&sig=" + b"A" * 43
    assert check_secrets.scan_bytes(url) == ["SAS-signatur"]
    assert check_secrets.scan_bytes(b"no secrets here") == []


def test_language_check_finds_danish(tmp_path, monkeypatch):
    import check_language
    (tmp_path / "A").mkdir()
    (tmp_path / "A" / "S.pa.yaml").write_text(
        'x: =Notify("Gemning afbrudt - kontakt support.")\n', encoding="utf-8")
    monkeypatch.setattr(check_language, "ROOT", str(tmp_path))
    with pytest.raises(SystemExit):
        check_language.check()


def test_language_check_allows_choice_values(tmp_path, monkeypatch):
    import check_language
    (tmp_path / "A").mkdir()
    (tmp_path / "A" / "S.pa.yaml").write_text(
        'x: =Patch(L, r, { Status: { Value: "Kladde" } })\n', encoding="utf-8")
    monkeypatch.setattr(check_language, "ROOT", str(tmp_path))
    check_language.check()


def test_every_light_token_has_a_dark_value():
    import design_tokens as dt
    assert set(dt.LIGHT) == set(dt.DARK)


def test_breakpoint_test_widths_straddle_every_boundary():
    import layout_tokens as lay
    widths = set(lay.test_widths())
    for _name, w in lay.BREAKPOINTS[1:]:
        assert w in widths and w - 1 in widths


def test_every_app_folder_in_config_exists():
    import env_config
    for key, app in env_config.APPS.items():
        assert os.path.isdir(os.path.join(ROOT, app["folder"])), key
