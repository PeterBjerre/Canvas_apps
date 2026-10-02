# -*- coding: utf-8 -*-
"""
Kontrakten mellem flowene og VH-plan Opretter.

    python3 -m pytest -q tests/test_sap_contract.py

Tre parter skal vaere enige om de samme feltnavne:

    flowet    flow/sap-ordre/ordre-*.json        skriver ordren
    skemaet   schema/vhplan-sap-order.schema.json  beskriver den
    VBA       excel/opretter/*.bas                 laeser den (JStr(item, "title"))

og den anden vej: opretteren skriver kvitteringen, flowet laeser den
(flow/sap-ordre/kvittering-*). Et omdoebt felt i een af dem giver ingen fejl
nogen steder - feltet er bare tomt. Det er den fejl, testene her fanger.
"""
import glob
import json
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLOW = os.path.join(ROOT, "flow", "sap-ordre")
SCHEMA = os.path.join(ROOT, "schema")
RUNNER = os.path.join(ROOT, "excel", "opretter")
sys.path.insert(0, os.path.join(ROOT, "tools"))


def load(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return json.load(f)


ORDER = load(SCHEMA, "vhplan-sap-order.schema.json")
RECEIPT = load(SCHEMA, "vhplan-sap-receipt.schema.json")


def props(schema, *path):
    node = schema
    for p in path:
        node = node["properties"][p]
        if node.get("type") == "array":
            node = node["items"]
    return node


def all_property_names(node, out=None):
    out = set() if out is None else out
    if isinstance(node, dict):
        for k, v in node.get("properties", {}).items():
            out.add(k)
            all_property_names(v, out)
        if "items" in node:
            all_property_names(node["items"], out)
    return out


#==============================================================================
# Skemaerne og eksemplerne
#==============================================================================
@pytest.mark.parametrize("schema,example", [
    ("vhplan-sap-order.schema.json", "example-sap-order.json"),
    ("vhplan-sap-receipt.schema.json", "example-sap-receipt.json"),
])
def test_example_matches_schema(schema, example):
    jsonschema = pytest.importorskip("jsonschema")
    sch = load(SCHEMA, schema)
    jsonschema.Draft202012Validator.check_schema(sch)
    errors = list(jsonschema.Draft202012Validator(
        sch, format_checker=jsonschema.FormatChecker()).iter_errors(load(SCHEMA, example)))
    assert not errors, [e.message for e in errors]


#==============================================================================
# Flowet skriver ordren
#==============================================================================
@pytest.mark.parametrize("snippet,part", [
    ("ordre-1-select-items.json", "items"),
    ("ordre-2-select-operations.json", "operations"),
    ("ordre-3-select-materials.json", "materials"),
])
def test_flow_select_has_exactly_the_schema_fields(snippet, part):
    keys = set(load(FLOW, snippet))
    want = set(props(ORDER, part)["properties"])
    assert keys == want, f"mangler: {sorted(want - keys)}, ukendte: {sorted(keys - want)}"


def test_flow_compose_matches_schema():
    order = load(FLOW, "ordre-4-compose-order.json")
    assert set(order) <= set(ORDER["properties"])
    assert set(ORDER["required"]) <= set(order)
    assert set(order["plan"]) == set(props(ORDER, "plan")["properties"])
    # Arrays kommer fra de tre Select-handlinger.
    for part, action in (("items", "Select_items"), ("operations", "Select_operations"),
                         ("materials", "Select_materials")):
        assert order[part] == f"@body('{action}')"
    assert order["kind"] == ORDER["properties"]["kind"]["const"]
    assert order["version"] == ORDER["properties"]["version"]["const"]


#==============================================================================
# Flowet laeser kvitteringen
#==============================================================================
def _receipt_snippets():
    return "\n".join(open(p, encoding="utf-8").read()
                     for p in glob.glob(os.path.join(FLOW, "kvittering-*")))


def test_receipt_flow_reads_only_receipt_fields():
    text = _receipt_snippets()
    top = set(re.findall(r"outputs\('Receipt'\)\?\['(\w+)'\]", text))
    item = set(re.findall(r"items\('Each_item'\)\?\['(\w+)'\]", text))
    assert top, "ingen felter fundet - er handlingen omdoebt?"
    assert top <= set(RECEIPT["properties"]), sorted(top - set(RECEIPT["properties"]))
    assert item <= set(props(RECEIPT, "items")["properties"]), \
        sorted(item - set(props(RECEIPT, "items")["properties"]))


def test_receipt_flow_writes_known_columns():
    """Kolonnerne, kvitteringsflowet og ordreflowet skriver, findes i
    SharePoint-udtraekket eller oprettes af et provisioneringsscript."""
    import check_datasources as cds
    schema = cds.load_schema() or {}
    provisioned = cds.provisioned_columns()

    def known(lst, col):
        return col in schema.get(lst, {}).get("cols", {}) or (lst, col) in provisioned

    writes = {
        "MaintenancePlans": set(load(FLOW, "ordre-5-merge-plan.json")) |
                            set(load(FLOW, "ordre-6-merge-plan-reset.json")) |
                            set(load(FLOW, "kvittering-4-merge-plan.json")),
        "MaintenanceItems": set(load(FLOW, "kvittering-3-merge-item.json")),
    }
    missing = [(l, c) for l, cols in writes.items() for c in sorted(cols) if not known(l, c)]
    assert not missing, missing


#==============================================================================
# Udtrykkene i flowene
#==============================================================================
def _expressions():
    return {os.path.basename(p): open(p, encoding="utf-8").read()
            for p in sorted(glob.glob(os.path.join(FLOW, "*.txt")))}


@pytest.mark.parametrize("name", sorted(_expressions()))
def test_expression_is_balanced(name):
    """Et udtryk indsaettes i haanden. En manglende parentes eller et
    manglende ' giver en fejl, foerst naar flowet gemmes."""
    text = _expressions()[name]
    depth = 0
    in_str = False
    for ch in text:
        if ch == "'":
            in_str = not in_str
        elif not in_str and ch == "(":
            depth += 1
        elif not in_str and ch == ")":
            depth -= 1
            assert depth >= 0, "')' uden '('"
    assert not in_str, "et ' er ikke lukket"
    assert depth == 0, f"{depth} '(' er ikke lukket"


def test_status_values_are_choices():
    """De statusvaerdier, flowene sammenligner med og skriver, er valg i
    MaintenancePlans.Status. En stavefejl ville bare give en betingelse,
    der aldrig er sand."""
    import check_datasources as cds
    schema = cds.load_schema() or {}
    choices = set(schema.get("MaintenancePlans", {}).get("choices", {}).get("Status", [])) | \
        cds.provisioned_choices()
    text = "\n".join(_expressions().values())
    used = set(re.findall(r"\['Status'\]\?\['Value'\],\s*'([^']+)'", text))
    used.add(load(FLOW, "kvittering-4-merge-plan.json")["Status"])
    assert {"Ready for creation in SAP", "Published"} <= used
    if choices:
        assert used <= choices, sorted(used - choices)


def test_order_trigger_and_reset():
    """Flowet skriver en ordre, naar planen er klar og ikke har en, og
    nulstiller SapOrderGuid, naar planen forlader 'Ready' uden at vaere
    oprettet. Saa giver en ny godkendelse en ny ordre."""
    trigger = _expressions()["ordre-0-trigger.txt"]
    assert trigger.startswith("@"), "en triggerbetingelse begynder med @"
    assert trigger.count("SapOrderGuid") == 2
    assert set(load(FLOW, "ordre-6-merge-plan-reset.json")) == set(load(FLOW, "ordre-5-merge-plan.json"))
    assert all(v == "" for v in load(FLOW, "ordre-6-merge-plan-reset.json").values())


#==============================================================================
# Opretteren laeser ordren
#==============================================================================
# Noegler i opretterens egne Dictionaries (opslagene i arket Opslag). De er
# ikke en del af kontrakten.
INTERNAL = {"sapPlant", "profile", "serviceSpec", "horizon", "period", "periodUnit",
            "serviceNo", "matGroup"}

J_CALL = re.compile(r'\bJ(?:Str|Num|Lng|Bool|Obj|List|Has)\(\s*[^,()]+(?:\([^()]*\))?\s*,\s*"(\w+)"')


def test_vba_reads_only_contract_fields():
    allowed = all_property_names(ORDER) | all_property_names(RECEIPT) | INTERNAL
    used = {}
    for path in glob.glob(os.path.join(RUNNER, "Vhp*.bas")):
        text = open(path, encoding="utf-8").read()
        for m in J_CALL.finditer(text):
            used.setdefault(m.group(1), os.path.basename(path))
    assert used, "ingen J*-opslag fundet - er moenstret forkert?"
    unknown = {k: v for k, v in used.items() if k not in allowed}
    assert not unknown, f"felter, ingen af skemaerne kender: {unknown}"


def test_vba_status_matches_receipt_schema():
    """NewStatus og NewStatusItem i VhpRun skriver kvitteringens felter."""
    text = open(os.path.join(RUNNER, "VhpRun.bas"), encoding="utf-8").read()
    status = set(re.findall(r'\bs\.Add "(\w+)"', text))
    item = set(re.findall(r'\bst\.Add "(\w+)"', text))
    assert status == set(RECEIPT["properties"]), \
        f"mangler: {sorted(set(RECEIPT['properties']) - status)}, ukendte: {sorted(status - set(RECEIPT['properties']))}"
    assert item == set(props(RECEIPT, "items")["properties"])


def test_folder_names_agree():
    """Biblioteket og mapperne hedder det samme i opretteren (VhpConfig),
    i provisioneringsscriptet og i kvitteringsflowets filter."""
    config = open(os.path.join(RUNNER, "VhpConfig.bas"), encoding="utf-8").read()
    const = dict(re.findall(r'Public Const (FOLDER_\w+|SUFFIX_\w+) As String = "([^"]*)"', config))
    ps1 = open(os.path.join(ROOT, "sharepoint", "provision", "Provision-SapCreation.ps1"),
               encoding="utf-8-sig").read()
    assert f"$LibraryName = '{const['FOLDER_LIBRARY']}'" in ps1
    folders = re.search(r"foreach \(\$folder in @\(([^)]*)\)\)", ps1).group(1)
    for key in ("FOLDER_ORDERS", "FOLDER_RECEIPTS", "FOLDER_DONE"):
        assert f"'{const[key]}'" in folders, key
    assert const["SUFFIX_RECEIPT"] in _expressions()["kvittering-0-filter.txt"]
