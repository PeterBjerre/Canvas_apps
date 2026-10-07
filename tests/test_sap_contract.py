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
    allowed = all_property_names(ORDER) | all_property_names(RECEIPT) | INTERNAL | \
        all_property_names(load(SCHEMA, "fl-sap-order.schema.json")) | \
        all_property_names(load(SCHEMA, "fl-sap-receipt.schema.json"))
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


#==============================================================================
# FL-anmodninger (docs/36): ordre, kvittering, flows og SPOOL-arket
#==============================================================================
FL_ORDER = load(SCHEMA, "fl-sap-order.schema.json")
FL_RECEIPT = load(SCHEMA, "fl-sap-receipt.schema.json")
SPOOL_XLSM = os.path.join(ROOT, "excel", "artifact", "FL indberetninger udgave SPOOL V3.xlsm")
SPOOL_GUI = os.path.join(ROOT, "excel", "vba", "spool-gui", "GUI_SCRIPT.bas")


@pytest.mark.parametrize("schema,example", [
    ("fl-sap-order.schema.json", "example-fl-sap-order.json"),
    ("fl-sap-receipt.schema.json", "example-fl-sap-receipt.json"),
])
def test_fl_example_matches_schema(schema, example):
    test_example_matches_schema(schema, example)


def test_fl_flow_select_has_exactly_the_schema_fields():
    keys = set(load(FLOW, "fl-ordre-1-select-rows.json"))
    want = set(props(FL_ORDER, "rows")["properties"])
    assert keys == want, f"mangler: {sorted(want - keys)}, ukendte: {sorted(keys - want)}"


def test_fl_flow_compose_matches_schema():
    order = load(FLOW, "fl-ordre-2-compose-order.json")
    assert set(order) <= set(FL_ORDER["properties"])
    assert set(FL_ORDER["required"]) <= set(order)
    assert set(order["request"]) == set(props(FL_ORDER, "request")["properties"])
    assert order["rows"] == "@body('Select_rows')"
    assert order["kind"] == FL_ORDER["properties"]["kind"]["const"]
    assert order["version"] == FL_ORDER["properties"]["version"]["const"]


def _fl_receipt_snippets():
    return "\n".join(open(p, encoding="utf-8").read()
                     for p in glob.glob(os.path.join(FLOW, "fl-kvittering-*")))


def test_fl_receipt_flow_reads_only_receipt_fields():
    text = _fl_receipt_snippets()
    top = set(re.findall(r"outputs\('Receipt'\)\?\['(\w+)'\]", text))
    row = set(re.findall(r"items\('Each_row'\)\?\['(\w+)'\]", text)) | \
        set(re.findall(r"item\(\)\?\['(\w+)'\]", text))
    assert top and row, "ingen felter fundet - er handlingerne omdoebt?"
    assert top <= set(FL_RECEIPT["properties"]), sorted(top - set(FL_RECEIPT["properties"]))
    assert row <= set(props(FL_RECEIPT, "rows")["properties"]), \
        sorted(row - set(props(FL_RECEIPT, "rows")["properties"]))


def test_fl_flows_write_known_columns():
    import check_datasources as cds
    schema = cds.load_schema() or {}
    provisioned = cds.provisioned_columns()

    def known(lst, col):
        return col in schema.get(lst, {}).get("cols", {}) or (lst, col) in provisioned

    writes = {
        "FunctionalLocationRequests": set(load(FLOW, "fl-ordre-3-merge-request.json")) |
                                      set(load(FLOW, "fl-ordre-4-merge-request-reset.json")) |
                                      set(load(FLOW, "fl-kvittering-4-merge-request.json")),
        "FunctionalLocationItems": set(load(FLOW, "fl-kvittering-3-merge-row.json")),
        "MD_RequestIndex": set(load(FLOW, "fl-kvittering-5-merge-index.json")),
    }
    missing = [(l, c) for l, cols in writes.items() for c in sorted(cols) if not known(l, c)]
    assert not missing, missing


def test_fl_status_values_are_known():
    """FL-anmodningernes status er MD_RequestIndex-ordforraadet
    (tools/request_index.py). En stavefejl giver en betingelse, der aldrig
    er sand - eller en anmodning, hubben ikke kan farve."""
    import request_index as ri
    known = {name for name, _label, _step in ri.STATUS}
    text = "\n".join(open(os.path.join(FLOW, f), encoding="utf-8").read()
                     for f in ("fl-ordre-0-trigger.txt", "fl-kvittering-2-betingelse.txt"))
    used = set()
    for arr in re.findall(r"createArray\(([^)]*)\)", text):
        used |= set(re.findall(r"'([^']+)'", arr))
    used.add(load(FLOW, "fl-kvittering-4-merge-request.json")["Status"])
    index = load(FLOW, "fl-kvittering-5-merge-index.json")
    used.add(index["Status"])
    assert {"Indsendt", "OprettetISAP"} <= used
    assert used <= known, sorted(used - known)
    assert index["StatusStep"] == ri.step(index["Status"])


def test_fl_order_trigger_and_reset():
    trigger = _expressions()["fl-ordre-0-trigger.txt"]
    assert trigger.startswith("@")
    assert trigger.count("SapOrderGuid") == 2
    assert set(load(FLOW, "fl-ordre-4-merge-request-reset.json")) == set(load(FLOW, "fl-ordre-3-merge-request.json"))
    assert all(v == "" for v in load(FLOW, "fl-ordre-4-merge-request-reset.json").values())
    # Det, der aabner for en ordre, er ogsaa det, kvitteringen godkendes i.
    open_states = re.findall(r"createArray\(([^)]*)\)", trigger)[0]
    assert open_states in _expressions()["fl-kvittering-2-betingelse.txt"]


def test_vba_fl_status_matches_receipt_schema():
    text = open(os.path.join(RUNNER, "VhpFlRun.bas"), encoding="utf-8").read()
    status = set(re.findall(r'\bs\.Add "(\w+)"', text))
    row = set(re.findall(r'\bst\.Add "(\w+)"', text))
    assert status == set(FL_RECEIPT["properties"]), \
        f"mangler: {sorted(set(FL_RECEIPT['properties']) - status)}, ukendte: {sorted(status - set(FL_RECEIPT['properties']))}"
    assert row == set(props(FL_RECEIPT, "rows")["properties"])


def test_vba_reads_only_fl_contract_fields():
    """Det samme som test_vba_reads_only_contract_fields, for FL-modulerne:
    hvert J*-opslag er et felt i FL-ordren, FL-kvitteringen eller et af
    opretterens egne."""
    allowed = all_property_names(FL_ORDER) | all_property_names(FL_RECEIPT) | INTERNAL
    used = {}
    for name in ("VhpFl.bas", "VhpFlSteps.bas", "VhpFlRun.bas"):
        text = open(os.path.join(RUNNER, name), encoding="utf-8").read()
        for m in J_CALL.finditer(text):
            used.setdefault(m.group(1), name)
    assert used
    unknown = {k: v for k, v in used.items() if k not in allowed}
    assert not unknown, unknown


def _vba_string_consts():
    """Strengkonstanterne i VhpConfig, med & mellem konstanter regnet ud."""
    src = open(os.path.join(RUNNER, "VhpConfig.bas"), encoding="utf-8").read()
    consts = {}
    for m in re.finditer(r'^(?:Public|Private) Const (\w+) As String = (.+)$', src, re.M):
        parts = [p.strip() for p in m.group(2).split("&")]
        value = ""
        for p in parts:
            if p.startswith('"'):
                value += p.strip('"')
            elif p in consts:
                value += consts[p]
            else:
                break
        else:
            consts[m.group(1)] = value
    return consts


# Felter, appen ikke viser eller skriver laengere (issue #166). Opretteren
# laeser dem stadig, saa anmodninger, der allerede har dem i
# SpoolValuesJson, oprettes som foer.
RETIRED_FL_FIELDS = {"RISIKO", "ASBESTOS", "PTW", "SUPERIOR FL"}


def test_fl_app_fields_exist():
    """Feltnavnene i VhpConfig (FLF_*) er appens - ellers er vaerdien bare tom."""
    rules = load(ROOT, "Functional Location App", "build", "fl_rules.generated.json")
    fields = {c["Field"] for c in rules["columns"]}
    consts = {k: v for k, v in _vba_string_consts().items() if k.startswith("FLF_")}
    assert len(consts) >= 16
    missing = {k: v for k, v in consts.items() if v not in fields and v not in RETIRED_FL_FIELDS}
    assert not missing, missing
    # Og de udgaaede felter er faktisk ude af appen.
    assert not RETIRED_FL_FIELDS & fields, sorted(RETIRED_FL_FIELDS & fields)


def test_fl_screen_ids_are_spools():
    """Hvert FL-felt-ID i VhpConfig staar ordret i SPOOL-arkets GUI_SCRIPT.bas.
    En tastefejl i et ID ville foerst vise sig midt i SAP."""
    spool = open(SPOOL_GUI, encoding="utf-8").read()
    ids = {k: v for k, v in _vba_string_consts().items()
           if re.match(r"(FL_|IL0|POPUP)", k) and v.startswith("wnd[")}
    assert len(ids) >= 40
    missing = {k: v for k, v in ids.items() if v not in spool}
    assert not missing, missing


def _vba_characteristic_seed():
    text = open(os.path.join(RUNNER, "VhpFl.bas"), encoding="utf-8").read()
    body = "".join(re.findall(r'^\s*s = s & "([^"]*)"\s*$', text, re.M))
    return [tuple(r.split("|")) for r in body.split(";") if r]


def test_fl_characteristic_seed_is_spools():
    """Tabellen Karakteristikker (VhpFl.CharacteristicSeed) er SPOOL-arkets
    DictionaryTable, raekke for raekke."""
    openpyxl = pytest.importorskip("openpyxl")
    if not os.path.exists(SPOOL_XLSM):
        pytest.skip("SPOOL-arket findes ikke i excel/artifact")
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        wb = openpyxl.load_workbook(SPOOL_XLSM, read_only=True, data_only=True)
    spool = []
    for r in wb["DictionaryTable"].iter_rows(min_row=2, max_col=3, values_only=True):
        if r[0] is None and r[1] is None:
            continue
        spool.append(tuple("" if x is None else str(x).strip() for x in r))
    assert _vba_characteristic_seed() == spool


def test_fl_characteristics_are_app_fields():
    """Hver karakteristik i tabellen er et felt, appen har for klassen. TRM,
    GIV_EXT og WCM er ekstra klasser - deres felter skal findes i mindst een."""
    rules = load(ROOT, "Functional Location App", "build", "fl_rules.generated.json")
    by_class = {}
    for c in rules["columns"]:
        by_class.setdefault(c["Cls"], set()).add(c["Field"])
    every = set().union(*by_class.values())
    extra = {"TRM", "GIV_EXT", "WCM"}
    missing = []
    not_in_app = set()
    for cls, field, _sap in _vba_characteristic_seed():
        if cls in extra:
            fields = every
        elif cls in by_class:
            fields = by_class[cls]
        else:
            # SPOOL kender klassen, appen goer ikke. RBR var den sidste - den
            # er med siden issue #166.
            not_in_app.add(cls)
            continue
        if field.upper() not in fields:
            missing.append((cls, field))
    assert not missing, missing
    assert not not_in_app, sorted(not_in_app)


def test_fl_receipt_folder_is_provisioned():
    const = _vba_string_consts()
    ps1 = open(os.path.join(ROOT, "sharepoint", "provision", "Provision-SapCreation.ps1"),
               encoding="utf-8-sig").read()
    folder = f"{const['FOLDER_RECEIPTS']}/{const['FOLDER_FL_RECEIPTS']}"
    for sub in ("", "/Behandlet", "/Afvist"):
        assert f"'{folder}{sub}'" in ps1, folder + sub
