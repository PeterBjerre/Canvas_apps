# -*- coding: utf-8 -*-
"""Functional Location-skaermens to sektioner (issue #166).

fl_rules.generated.json markerer hver kolonne med en Section (harnessens
buildPlan). Skaermen viser Master i sektion 1 og Class/TRM/Ext i sektion
2 - testene her holder den inddeling sand, uanset hvad html/*.js siger
naeste gang."""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN = os.path.join(ROOT, "Functional Location App", "build", "fl_rules.generated.json")

# Felter, der ikke skal vaere i appen (issue #166, Peters svar 4 og 5).
REMOVED = {"LONG TEXT", "DLFL", "SUPERIOR FL", "DATASHEET", "1", "2", "LOCATION", "UNIT",
           "DOCUMENT NUMBER", "FIRST TIME MAINTENANCE", "SECTION AND PAGE SUPPLIERS MANUAL",
           "MAINTENANCE TASK", "FREQUENCE OF MAINTENANCE", "TECHNICAL DATA", "QUANTITY",
           "RISIKO", "ASBESTOS", "PTW"}
MASTER = ["STRINDICATOR", "FUNCTIONAL LOCATION", "DESCRIPTION", "ABC INDIC.", "MANUFACTURER",
          "MODEL NUMBER", "MANUFACTURER PART NUMBER", "MANUFACTURER SERIAL NUMBER", "ROOM",
          "SORT FIELD", "ATEX", "WARRANTY START", "WARRANTY END"]
TRM = {"TRM ASSIGNMENT", "EX-MARKING", "SAFETY CRITICAL EQUIPMENT", "FIRE CLASSIFICATION",
       "FIRE SEALING TYPE", "FIRE SEALING PRODUCT"}


def rules():
    with open(GEN, encoding="utf-8") as f:
        return json.load(f)


def by_class(R):
    out = {}
    for c in R["columns"]:
        out.setdefault(c["Cls"], []).append(c)
    return out


def test_every_column_has_a_known_section():
    R = rules()
    bad = [(c["Cls"], c["Column"], c.get("Section")) for c in R["columns"]
           if c.get("Section") not in ("Status", "Master", "Class", "TRM", "Ext")]
    assert not bad, bad[:10]


def test_master_set_is_the_same_in_every_class():
    """Sektion 1 er den samme for alle klasser - ogsaa i samme raekkefoelge."""
    R = rules()
    sets = {cls: [c["Field"] for c in sorted(cols, key=lambda c: c["Ord"]) if c["Section"] == "Master"]
            for cls, cols in by_class(R).items()}
    assert set(sets) == set(R["classes"])
    assert all(v == MASTER for v in sets.values()), {k: v for k, v in sets.items() if v != MASTER}


def test_master_fields_have_their_editors():
    R = rules()
    lists = {}
    for l in R["lists"]:
        lists.setdefault(l["List"], []).append(l["Value"])
    for c in R["columns"]:
        if c["Section"] != "Master":
            continue
        f = c["Field"]
        if f in ("STRINDICATOR", "ABC INDIC."):
            assert not c["Editable"], c       # afledt / saettes af TRM-automatikken
        elif f == "ATEX":
            assert c["Editable"] and lists[c["List"]] == ["X"], c   # afkrydsning
        else:
            assert c["Editable"] and not c["List"] and c["MaxLen"] > 0, c


def test_removed_fields_are_not_in_the_app():
    R = rules()
    found = sorted({c["Field"] for c in R["columns"]} & REMOVED)
    assert not found, found
    checked = sorted({p["Field"] for p in R["plan"]} & REMOVED)
    assert not checked, checked


def test_trm_fields_are_their_own_group():
    R = rules()
    for c in R["columns"]:
        if c["Field"] in TRM:
            assert c["Section"] == "TRM", c
    trm_classes = {p["Cls"] for p in R["plan"] if p["Ord"] == 0 and p["Chk"] == "TRMSET"}
    with_trm = {c["Cls"] for c in R["columns"] if c["Section"] == "TRM"}
    assert with_trm <= trm_classes, sorted(with_trm - trm_classes)


def test_rbr_is_a_class_with_its_characteristics():
    R = rules()
    assert "RBR" in R["classes"]
    cls = [c["Field"] for c in by_class(R)["RBR"] if c["Section"] == "Class"]
    assert cls == ["DESIGN POS COLD", "DESIGN POS WARM", "DIRECTION OF MOVEMENT", "REMARKS",
                   "SETTING COLD VERTICAL [KN]", "SETTING COLD VERTICAL [MM]",
                   "SETTING WARM VERTICAL [KN]", "SETTING WARM VERTICAL [MM]"]


def test_maf_values_are_in_givs_sce_list():
    """MAF er ingen klasse, men dens SCEq-vaerdier hoerer under GIV."""
    R = rules()
    lists = {}
    for l in R["lists"]:
        lists.setdefault(l["List"], []).append(l["Value"])
    giv = next(c for c in R["columns"] if c["Cls"] == "GIV" and c["Field"] == "SAFETY CRITICAL EQUIPMENT")
    for v in ("7.4 Miljømålere - vilkår", "7.5 Miljømålere - afregning", "7.6 Afregningsmålere"):
        assert v in lists[giv["List"]]
    assert "MAF" not in R["classes"]


def test_warranty_is_dd_mm_yyyy_only():
    R = rules()
    msgs = {p["Msg"] for p in R["plan"] if p["Chk"] == "DATE"}
    assert msgs == {"Use DD.MM.YYYY."}
