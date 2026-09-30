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


def test_layout_rule_16_classic_dropdown(tmp_path):
    def plant(t):
        return t.replace("Control: ModernDropdown", "Control: Classic/DropDown", 1)
    rc, out = _layout(tmp_path, plant)
    assert rc == 1 and "[16]" in out


def test_layout_rule_33_prefix_follows_type(tmp_path):
    def plant(t):
        return t.replace("inpDomText:", "txtDomTextX:", 1)
    rc, out = _layout(tmp_path, plant)
    assert rc == 1 and "[33]" in out


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


def _ps1_list(name):
    text = open(os.path.join(ROOT, "sharepoint", "provision", "Provision-RequestIndex.ps1"),
                encoding="utf-8-sig").read()
    m = re.search(r"\$" + name + r"\s*=\s*((?:'[^']*'\s*,?\s*)+)", text)
    return re.findall(r"'([^']*)'", m.group(1))


def test_request_index_matches_provisioning():
    """Domaene- og statusvaerdierne, apperne skriver, er valgene i listen."""
    import request_index as ri
    assert list(ri.DOMAINS) == _ps1_list("DOMAINS")
    assert [k for k, _l, _s in ri.STATUS] == _ps1_list("STATUS")


def test_domain_configs_use_known_domains():
    import request_index as ri
    for app, rel in [("Equipment App", "domain_config.py"), ("Material App", "domain_config.py"),
                     ("Functional Location App", "fl_config.py")]:
        text = open(os.path.join(ROOT, app, "build", rel), encoding="utf-8").read()
        dom = re.search(r'^DOMAIN\s*=\s*"(\w+)"', text, re.M).group(1)
        assert dom in ri.DOMAINS, (app, dom)


def test_every_app_has_the_same_on_error():
    """Alle App.pa.yaml er skrevet af tools/app_yaml.py og har App.OnError."""
    import yaml
    import app_yaml
    import env_config
    want = "=" + app_yaml.ON_ERROR
    for key, app in env_config.APPS.items():
        doc = yaml.safe_load(open(os.path.join(ROOT, app["folder"], "App.pa.yaml"),
                                  encoding="utf-8"))
        assert doc["App"]["Properties"]["OnError"].strip() == want.strip(), key


def test_gen_screen_imports_outside_a_build_entry():
    """gen_screen maa kunne importeres fra en test - OUT_DIR er doven."""
    import importlib
    import gen_screen
    importlib.reload(gen_screen)


# --- tools/fx.py: den faelles Power Fx-scanner (REVIEW.md C7) -------------

def test_fx_ignores_strings_names_and_comments():
    import fx
    t = 'Patch(colX, "a, (b)", \'odd,(name\', { c: 1 }) // don\'t ( count\n'
    assert fx.call_args(t, 0) == ['colX', ' "a, (b)"', " 'odd,(name'", ' { c: 1 }']
    assert fx.call_end(t, 0) == t.index(")", t.index("}")) + 1
    assert fx.first_arg(t, 0) == "colX"
    assert fx.rest_args("ClearCollect(col, Filter(a, b))", 0) == " Filter(a, b)"
    assert fx.paren_balance("If(a, \"(\", b) /* ( */") == (0, False)
    assert fx.open_string('Notify("say ""hi""")') is False
    assert fx.open_string('Notify("oops)') is True
    assert fx.split_top('a; If(x; y); "b;c"', ";") == ["a", "If(x; y)", '"b;c"']


def test_skill_rules_table_matches_registry():
    """SKILL.md's regeltabel er genereret af check_layout --rules."""
    import check_layout
    skill = open(os.path.join(ROOT, ".github", "skills", "canvas-build", "SKILL.md"),
                 encoding="utf-8").read()
    block = skill[skill.index("<!-- rules:start"):skill.index("<!-- rules:end -->")]
    assert check_layout.rules_markdown() in block, \
        "SKILL.md er ikke opdateret - koer python3 tools/check_layout.py --rules"
    ids = [r.id for r in check_layout.RULES]
    assert len(ids) == len(set(ids))
