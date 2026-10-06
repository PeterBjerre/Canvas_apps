# -*- coding: utf-8 -*-
"""
Testflowet til FL-API'et (flow/fl-api-test).

    python3 -m pytest -q tests/test_fl_api_test.py

Repoet er offentligt. Det vigtigste her er derfor, at client secret og
x-apikey er tomme i flowet, og at den committede pakke er bygget fra den
nuvaerende definition.
"""
import json
import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import build_fl_api_test as pkg  # noqa: E402

with open(pkg.SRC, encoding="utf-8") as f:
    DEF = json.load(f)


def all_actions(actions):
    for name, a in actions.items():
        yield name, a
        yield from all_actions(a.get("actions", {}))
        yield from all_actions(a.get("else", {}).get("actions", {}))


ACTIONS = dict(all_actions(DEF["actions"]))


def test_hemmeligheder_er_tomme_variabler():
    for name in ("ClientSecret", "ApiKey"):
        var = ACTIONS["Initialize_variable_" + name]["inputs"]["variables"][0]
        assert var["name"] == name
        assert var["value"] == ""
        assert "inputs" in ACTIONS["Initialize_variable_" + name][
            "runtimeConfiguration"]["secureData"]["properties"]


def test_kun_variablerne_bruges_som_hemmeligheder():
    text = json.dumps(DEF)
    assert "variables('ClientSecret')" in text
    assert "variables('ApiKey')" in text
    hdr = ACTIONS["Kald_API"]["inputs"]["headers"]
    assert hdr["x-apikey"] == "@{variables('ApiKey')}"


def test_token_og_kald_er_skjult_i_koerselshistorikken():
    assert ACTIONS["Hent_token"]["runtimeConfiguration"]["secureData"][
        "properties"] == ["inputs", "outputs"]
    assert "inputs" in ACTIONS["Kald_API"]["runtimeConfiguration"][
        "secureData"]["properties"]


def test_handlinger_der_henvises_til_findes():
    text = json.dumps(DEF)
    refs = set(re.findall(r"(?:outputs|body)\('([^']+)'\)", text))
    assert refs <= set(ACTIONS), refs - set(ACTIONS)
    for name, a in ACTIONS.items():
        for dep in a.get("runAfter", {}):
            assert dep in ACTIONS, (name, dep)


def test_pakken_er_bygget_fra_definitionen():
    with zipfile.ZipFile(pkg.OUT) as z:
        committed = {n: json.loads(z.read(n)) for n in z.namelist()}
    expected = dict(pkg.files())
    assert committed == expected, \
        "Koer python3 tools/build_fl_api_test.py og commit zip'en"
