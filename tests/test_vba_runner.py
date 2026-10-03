# -*- coding: utf-8 -*-
"""
VH-plan Opretter (excel/opretter) uden Excel.

    python3 -m pytest -q tests/test_vba_runner.py

To lag:

  1. De strenge statiske tjek (tools/vba_strict.py) - koerer altid. De
     afproeves ogsaa med plantede fejl, saa et tjek, der stille holder op
     med at virke, bliver opdaget.
  2. LibreOffice - kun hvor soffice og python3-uno findes (ellers skip).
     Hvert modul oversaettes for sig (syntaksfejl), og selvtestens rene del
     (VhpTest.SelfTestPure: oversaettelser, langtekst og FL-regler) koeres
     for alvor.

SAP-delen (VhpSap, VhpSteps, VhpFlSteps) kan ingen af delene koere. Den
afproeves i SAP efter tjeklisterne i docs/34 og docs/36.
"""
import glob
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, "excel", "opretter")
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import vba_strict  # noqa: E402


def _modules():
    return sorted(glob.glob(os.path.join(RUNNER, "*.bas")))


def _strict(files):
    """vba_strict paa en liste af (filnavn, linjer)."""
    import check_vba
    from pathlib import Path
    mods = {}
    problems = []
    for name, lines in files:
        m = check_vba.Module.__new__(check_vba.Module)
        m.path = Path(name)
        m.raw = lines
        first = lines[0] if lines else ""
        m.name = first.split('"')[1] if first.startswith('Attribute VB_Name = "') else Path(name).stem
        m.public = set()
        m.procs = []
        check_vba.parse(m, problems)
        mods[m.name] = m
    vba_strict.run([(m.path, m.raw, m.name) for m in mods.values()],
                   {m.name: m.public for m in mods.values()}, problems)
    return problems


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read().splitlines()


def _all_files():
    return [(p, _read(p)) for p in _modules()]


#==============================================================================
# 1. Statiske tjek
#==============================================================================
def test_runner_passes_strict_checks():
    assert _strict(_all_files()) == []


def _with(path_part, old, new):
    files = _all_files()
    out = []
    hit = False
    for p, lines in files:
        if p.endswith(path_part):
            text = "\n".join(lines)
            assert old in text, f"{old!r} findes ikke i {path_part}"
            text = text.replace(old, new, 1)
            lines = text.split("\n")
            hit = True
        out.append((p, lines))
    assert hit
    return out


def test_strict_catches_misspelled_variable():
    files = _with("VhpMap.bas", 'PriorityKey = "3"', 'PriortyKey = "3"')
    assert any("PriortyKey" in p for p in _strict(files))


def test_strict_catches_missing_end_if():
    files = _with("VhpMap.bas", "        Case Else: Exit Function\n    End Select\n",
                  "        Case Else: Exit Function\n")
    assert any("uden afslutning" in p or "lukker" in p for p in _strict(files))


def test_strict_catches_private_call_across_modules():
    # ObjectEntry er Private i VhpMap. Et kald fra et andet modul giver
    # "Sub or Function not defined" i Excel.
    files = _with("VhpOrder.bas", "    ItemLabel = s\n", "    ItemLabel = ObjectEntry(s)\n")
    assert any("ObjectEntry" in p for p in _strict(files))


def test_strict_catches_non_ascii():
    files = _with("VhpUtil.bas", "' Dansk tekst til skaermen.", "' Dansk tekst til skærmen.")
    assert any("ASCII" in p for p in _strict(files))


def test_settings_are_complete():
    """Hver SET_-noegle har en standardvaerdi og en raekke i Setup."""
    import re
    config = open(os.path.join(RUNNER, "VhpConfig.bas"), encoding="utf-8").read()
    ui = open(os.path.join(RUNNER, "VhpUi.bas"), encoding="utf-8").read()
    keys = re.findall(r"Public Const (SET_\w+) As String", config)
    assert keys
    for k in keys:
        assert re.search(rf"Case {k}:", config), f"{k} mangler i DefaultSetting"
        assert re.search(rf"Array\({k},", ui), f"{k} mangler i VhpUi.BuildSettings"


#==============================================================================
# 2. LibreOffice
#==============================================================================
@pytest.fixture(scope="module")
def lo():
    import vba_lo
    if not vba_lo.available():
        pytest.skip("LibreOffice/python3-uno findes ikke")
    pure = [os.path.join(RUNNER, m) for m in
            ("VhpUtil.bas", "VhpMap.bas", "VhpItf.bas", "VhpFl.bas", "VhpTest.bas")]
    with vba_lo.VbaRunner(pure) as runner:
        yield runner


@pytest.mark.parametrize("module", [os.path.basename(p) for p in _modules()
                                    if not p.endswith("JsonConverter.bas")])
def test_module_compiles(lo, module):
    assert lo.syntax_ok(os.path.join(RUNNER, module)), \
        f"{module} kan ikke oversaettes - en syntaksfejl (se docs/34, Afproevning)"


def test_planted_syntax_error_is_caught(lo, tmp_path):
    src = open(os.path.join(RUNNER, "VhpMap.bas"), encoding="utf-8").read()
    bad = tmp_path / "VhpMap.bas"
    bad.write_text(src.replace('PriorityKey = "1"', 'PriorityKey = & "1"', 1), encoding="utf-8")
    assert not lo.syntax_ok(str(bad))


def test_pure_selftest(lo):
    result = lo.call("VhpTest", "SelfTestPure")
    assert result.startswith("OK"), result


def test_itf_example_from_contract(lo):
    """Itemets langtekst i eksempelordren, som SAP faar den."""
    import json
    order = json.load(open(os.path.join(ROOT, "schema", "example-sap-order.json"), encoding="utf-8"))
    text = lo.call("VhpItf", "HtmlToSapText", order["items"][0]["longText"])
    assert text == ("<H>Formål:</> kontrol af tætninger og lejer.\n\n"
                    "- Kontrollér for lækager\n"
                    "- Mål lejetemperatur\n"
                    "  - Notér værdien i loggen")
