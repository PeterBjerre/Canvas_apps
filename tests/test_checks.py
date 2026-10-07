# -*- coding: utf-8 -*-
"""
Tjekkene skal FEJLE, naar fejlen er der.

Hvert tjek i tools/ er vores eneste vagt mod en fejlklasse, og et tjek,
der aldrig er set fejle, er ikke en vagt. Her plantes fejlen i en KOPI af
det byggede output (eller i en midlertidig fil), og tjekket skal melde den.

    python3 -m pytest tests
"""
import contextlib
import io
import os
import re
import shutil
import sys
from contextlib import redirect_stdout

import pytest

from conftest import ROOT

# Den samlede app: dens skaerme findes, ogsaa naar enkeltapperne er udfaset
# (docs/33-udfasning.md). Equipment-skaermen hedder Eq i stedet for Dom.
APP = os.path.join(ROOT, "BIO SAP App")
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
        return re.sub(r"(conEqFormCard:\n(?:.*\n)*?\s+Height: \|-\n\s+)=[^\n]+",
                      r"\1=btnEqSave.Height + 10", t, count=1)
    rc, out = _layout(tmp_path, plant)
    assert rc == 1 and "[1]" in out


def test_layout_rule_10_wrapcount_on_variable_height_gallery(tmp_path):
    # Issue #130: compile kender ikke WrapCount paa et VariableHeight-galleri.
    def plant(t):
        return re.sub(r"(galEqRows:\n\s+Control: Gallery\n\s+Variant: )Vertical",
                      r"\1VariableHeight", t, count=1)
    rc, out = _layout(tmp_path, plant)
    assert rc == 1 and "[10] galEqRows" in out and "WrapCount" in out, out


def test_layout_rule_8c_app_width_comparison(tmp_path):
    def plant(t):
        return t.replace("=LayoutRank", "=If(App.Width < 900, 1, 2) + 0 * LayoutRank", 1)
    rc, out = _layout(tmp_path, plant)
    assert rc == 1 and "[8c]" in out


def test_layout_rule_0_duplicate_name(tmp_path):
    def plant(t):
        return t.replace("btnEqNew:", "btnEqSave:", 1)
    rc, out = _layout(tmp_path, plant)
    assert rc == 1 and "[0]" in out


def test_layout_rule_31_string_column_name(tmp_path):
    def plant(t):
        return t.replace("=LayoutRank", '=CountRows(GroupBy(colEqRows, "Plant", "G")) * 0 + LayoutRank', 1)
    rc, out = _layout(tmp_path, plant)
    assert rc == 1 and "[31]" in out


def test_layout_rule_30_column_against_expression(tmp_path):
    """Issue #84: IsOpen = (udtryk) i et filter mod en SharePoint-liste."""
    def plant(t):
        return t.replace("=LayoutRank", '=CountRows(Filter(EquipmentItems, IsOpen = (varEqView = "open"))) * 0 + LayoutRank', 1)
    rc, out = _layout(tmp_path, plant)
    assert rc == 1 and "[30]" in out and "The query is not valid" in out


def test_layout_rule_34_onstart_clears_what_onvisible_fills(tmp_path):
    """Issue #84: OnStart toemte hubbens taelling, OnVisible lige havde hentet."""
    import check_layout
    shutil.copy(os.path.join(APP, "App.pa.yaml"), tmp_path / "App.pa.yaml")
    with open(tmp_path / "App.pa.yaml", "a", encoding="utf-8") as f:
        f.write("# Clear(colMdScope)\n")
    shutil.copy(os.path.join(APP, "ScreenMdHub.pa.yaml"), tmp_path / "ScreenMdHub.pa.yaml")
    old_argv, sys.argv = sys.argv, ["check_layout.py", str(tmp_path / "ScreenMdHub.pa.yaml")]
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            rc = check_layout.main()
    finally:
        sys.argv = old_argv
    assert rc == 1 and "[34]" in buf.getvalue()


def test_layout_rule_30_nested_filter_on_list(tmp_path):
    """Issue #84: Filter(Filter(liste, A), B) gav forkerte raekker."""
    def plant(t):
        return t.replace("=LayoutRank", '=CountRows(Filter(Filter(EquipmentItems, Title = varEqMe), Status = "x")) * 0 + LayoutRank', 1)
    rc, out = _layout(tmp_path, plant)
    assert rc == 1 and "Filter(Filter(EquipmentItems" in out


def test_layout_rule_16_classic_dropdown(tmp_path):
    def plant(t):
        return t.replace("Control: ModernDropdown", "Control: Classic/DropDown", 1)
    rc, out = _layout(tmp_path, plant)
    assert rc == 1 and "[16]" in out


def test_layout_rule_33_prefix_follows_type(tmp_path):
    def plant(t):
        return t.replace("inpEqText:", "txtEqTextX:", 1)
    rc, out = _layout(tmp_path, plant)
    assert rc == 1 and "[33]" in out


# Issue #165: Studios App checker. De fire moenstre, den meldte, skal
# byggeriet afvise, foer de naar Studio.
def test_layout_rule_35_indexed_access_via_copy(tmp_path):
    def plant(t):
        return t.replace("=LayoutRank",
                         "=If(IsBlank(First(LastN(colEqRows, 2))), 0, 0) + LayoutRank", 1)
    rc, out = _layout(tmp_path, plant)
    assert rc == 1 and "[35]" in out and "IndexedAccessViaCopy" in out, out


def test_layout_rule_36_countrows_gallery_allitems(tmp_path):
    def plant(t):
        return t.replace("=LayoutRank", "=CountRows(galEqRows.AllItems) * 0 + LayoutRank", 1)
    rc, out = _layout(tmp_path, plant)
    assert rc == 1 and "[36]" in out and "galEqRows.AllItemsCount" in out, out


def test_layout_rule_37_image_without_tab_stop(tmp_path):
    def plant(t):
        return re.sub(r"(imgEqTitleIcon:\n(?:.*\n)*?\s+TabIndex: \|-\n\s+)=0",
                      r"\1=-1", t, count=1)
    rc, out = _layout(tmp_path, plant)
    assert rc == 1 and "[37] imgEqTitleIcon" in out, out


def test_layout_rule_38_empty_accessible_label(tmp_path):
    def plant(t):
        return re.sub(r"(imgEqTitleIcon:\n\s+Control: Image\n\s+Properties:\n"
                      r"\s+AccessibleLabel: \|-\n\s+)=[^\n]+", r'\1=""', t, count=1)
    rc, out = _layout(tmp_path, plant)
    assert rc == 1 and "[38] imgEqTitleIcon" in out, out


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


def test_language_check_finds_danish_flow_text(tmp_path, monkeypatch):
    """Issue #162: et flow, der skriver dansk i en kolonne, appen viser."""
    import json
    import check_language
    d = tmp_path / "solution" / "BIOSAP" / "src" / "Workflows"
    d.mkdir(parents=True)
    flow = {"properties": {"definition": {"actions": {"Log": {"inputs": {"parameters": {
        "item/Detail": "@concat('opretter er 1. eller 2. godkender for system ', outputs('SysNo'))",
        "item/Status/Value": "Kladde"}}}}}}}
    (d / "BioSap-Test-00000000-0000-0000-0000-000000000000.json").write_text(
        json.dumps(flow), encoding="utf-8")
    monkeypatch.setattr(check_language, "ROOT", str(tmp_path))
    bad, n = check_language.check_flows()
    assert n == 1 and len(bad) == 1 and "opretter" in bad[0]


def test_language_check_allows_stored_values_in_flows(tmp_path, monkeypatch):
    import json
    import check_language
    d = tmp_path / "solution" / "BIOSAP" / "src" / "Workflows"
    d.mkdir(parents=True)
    flow = {"properties": {"definition": {"actions": {"If": {
        "expression": "@contains(createArray('Indsendt', 'KlarTilSAP'), triggerBody()?['Status'])",
        "inputs": {"parameters": {"folderPath": "/SAP-oprettelse/Til oprettelse",
                                  "item/Status": {"Value": "AfventerInfo"}}}}}}}}
    (d / "BioSap-Test-00000000-0000-0000-0000-000000000000.json").write_text(
        json.dumps(flow), encoding="utf-8")
    monkeypatch.setattr(check_language, "ROOT", str(tmp_path))
    assert check_language.check_flows()[0] == []


def test_status_labels_cover_every_stored_status():
    import display_text as dt
    import request_index as ri
    f = dt.formula()
    for key, label, _step in ri.STATUS:
        assert f'{{ Key: "{key}", Label: "{label}" }}' in f
    assert dt.STATUS_TABLE in dt.status("ThisItem.Status.Value")


def test_old_flow_texts_are_shown_in_english():
    """Hver dansk saetning i udtraekket af MD_ApprovalLog bliver engelsk,
    og den engelske tekst, flowene skriver nu, gaar uaendret igennem."""
    import json
    import check_language as cl
    import display_text as dt
    rows = json.load(io.open(os.path.join(ROOT, "sharepoint", "inspect", "out",
                                          "sample-MD_ApprovalLog.json"), encoding="utf-8-sig"))
    seen = 0
    for r in rows:
        for col in ("Detail", "ItemText"):
            v = r.get(col) or ""
            out = dt.log_py(v)
            assert not cl._danish(out.strip()), (col, v, out)
            seen += out != v
    assert seen >= 10
    for en in ("System 2", "Cost", "Quality SSV", "Quality (SSV)", "Approved earlier",
               "No response from x@y.com", "494 DKK (threshold 300000 DKK)", "SAP plan 1",
               "Requester is 1st or 2nd approver for system 2: a@b.com",
               "FL SSV13 HFC10 belongs to SSV, the plan is for ASV", "System approval",
               "Quality review (SSV): ok", "The plan has no items."):
        assert dt.log_py(en) == en, en


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
    for key in env_config.build_targets():
        app = env_config.APPS[key]
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


# ---------------------------------------------------------------------------
# KKS: seedet og den genbrugte MD_FLKey skal vaere KKS-vejledningens raekker
# ---------------------------------------------------------------------------
def _kks_check(monkeypatch, tmp_path, csv_name, mutate):
    """Koer gen_kks_seed --check paa en kopi af et seed, hvor mutate() har
    aendret en raekke. Returnerer (exitkode, output)."""
    import gen_kks_seed as g
    src = os.path.join(ROOT, "sharepoint", "seed", csv_name)
    text = open(src, encoding="utf-8-sig").read()
    new = mutate(text)
    assert new != text, "mutationen ramte ikke noget - testen er forkert"
    dst = tmp_path / csv_name
    dst.write_text(new, encoding="utf-8-sig")
    attr = "FLKEY_CSV" if csv_name == "MD_FLKey.csv" else "FUNCTION_CSV"
    monkeypatch.setattr(g, attr, str(dst))
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = g.check()
    return rc, buf.getvalue()


def test_kks_seed_is_in_step_with_html():
    import gen_kks_seed as g
    buf = io.StringIO()
    with redirect_stdout(buf):
        assert g.check() == 0, buf.getvalue()


def test_kks_check_finds_stale_function_seed(monkeypatch, tmp_path):
    rc, out = _kks_check(monkeypatch, tmp_path, "MD_KksFunctionKey.csv",
                         lambda t: t.replace('"SAMLET PROJEKT"', '"SAMLET"', 1))
    assert rc == 1 and "MD_KksFunctionKey.csv" in out


def test_kks_check_finds_flkey_drifting_from_kks(monkeypatch, tmp_path):
    """Aendres en aggregatbeskrivelse i MD_FLKey, er genbruget forkert."""
    rc, out = _kks_check(monkeypatch, tmp_path, "MD_FLKey.csv",
                         lambda t: t.replace('"Transformere."', '"Transformer."', 1))
    assert rc == 1 and "Aggregate" in out


def test_vhp_every_rule_has_a_section():
    """Sektionernes badge (issue #123) sorterer VhpValidationErrors efter
    beskedens begyndelse. En ny regel uden sektion ville aldrig holde et
    badge fra "Valid" - mens Submit stadig var graa."""
    sys.path.insert(0, os.path.join(ROOT, "Maintenance Plan App", "build"))
    import build_status as bs
    codes = set(re.findall(r'"([A-Z]\d+): ', bs.VALIDATION))
    assert codes, "fandt ingen regler - testen er forkert"
    prefixes = [p for ps in bs.RULE_SECTIONS.values() for p in ps]
    assert len(prefixes) == len(set(prefixes)), "en regel staar i to sektioner"
    for code in codes:
        assert code + ":" in prefixes, f"regel {code} hoerer ikke til nogen sektion"
    # Item-reglen er den eneste uden kode: "Item <id> (...): missing ...".
    assert '"Item " & Text(ItemId) & " ("' in bs.VALIDATION
    assert "Item " in bs.RULE_SECTIONS["Item"]
