# -*- coding: utf-8 -*-
"""
fl_rules.generated.json mod sine kilder (R2-042).

harness.js test sammenligner nu hele planen med html/*.js. Her tjekkes
de to ting, den ikke ser: at noegletallet passer til seedet, SharePoint
faar, og at fl_validation.py's POSITIONSAFHAENGIGE udsnit af KKS-
moenstrene stadig peger paa KKSKV og KKSKA.
"""
import csv
import json
import os
import re

from conftest import ROOT

FL = os.path.join(ROOT, "Functional Location App", "build")
PLAN = json.load(open(os.path.join(FL, "fl_rules.generated.json"), encoding="utf-8"))


def test_function_key_count_matches_seed():
    with open(os.path.join(ROOT, "sharepoint", "seed", "MD_FLKey.csv"),
              encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["KeyType"] == "Function"]
    assert PLAN["functionKeyCount"] == len(rows) == len(PLAN["functionKeys"])
    assert sorted(r["KeyValue"] for r in rows) == PLAN["functionKeys"]


def _pfx(js):
    """Samme konvertering af \\d som harness.js toPfx (nok til de to moenstre):
    [0-9] udenfor en tegnklasse, 0-9 inde i en."""
    out, in_class, i = "", False, 0
    while i < len(js):
        c = js[i]
        if c == "\\" and js[i + 1] == "d":
            out += "0-9" if in_class else "[0-9]"
            i += 2
            continue
        if c == "\\":
            out += js[i:i + 2]
            i += 2
            continue
        in_class = (c == "[") or (in_class and c != "]")
        out += c
        i += 1
    return out


def _engine_kks_types():
    """{KKSKV: [moenstre], KKSKA: [...]} fra evaluateKksSyntax i motoren."""
    src = open(os.path.join(ROOT, "html", "fl-rule-engine.js"), encoding="utf-8").read()
    out = {}
    for m in re.finditer(r"if \(([^\n]*?)\) \{\s*return \{\s*kksType: \"(KKSK[VA])\"", src):
        out[m.group(2)] = [_pfx(x) for x in re.findall(r"/(\^[^/]*\$)/\.test", m.group(1))]
    return out


def _slice(var):
    src = open(os.path.join(FL, "fl_validation.py"), encoding="utf-8").read()
    m = re.search(r"^\s*%s = _any_match\(\"fl\", PAT\[\"kks\"\]\[(\d+):(\d+)\]\)" % var, src, re.M)
    assert m, "%s-udsnittet findes ikke laengere i fl_validation.py" % var
    return PAT_KKS[int(m.group(1)):int(m.group(2))]


PAT_KKS = PLAN["patterns"]["kks"]


def test_kv_ka_slices_point_at_kksv_and_kska():
    types = _engine_kks_types()
    assert set(types) == {"KKSKV", "KKSKA"}
    assert sorted(_slice("kv")) == sorted(types["KKSKV"])
    assert sorted(_slice("ka")) == sorted(types["KKSKA"])
