# -*- coding: utf-8 -*-
"""Strategiplaner i opretteren (VhpStrategy): ordren baerer strategiens
pakker, flowet i solution'en er det samme som snippets, og felterne er
Export_Script.bas' felter vendt om."""
import csv
import glob
import json
import os
import re

import check_datasources as cds
from conftest import ROOT

FLOW = os.path.join(ROOT, "flow", "sap-ordre")
RUNNER = os.path.join(ROOT, "excel", "opretter")


def _bas(name):
    with open(os.path.join(RUNNER, name), encoding="latin-1") as f:
        return f.read()


def _workflow():
    path = glob.glob(os.path.join(ROOT, "solution", "BIOSAP", "src", "Workflows",
                                  "BioSap-VhPlan-SapOrder-*.json"))[0]
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _actions():
    acts = _workflow()["properties"]["definition"]["actions"]
    return acts["Try"]["actions"]["Condition_New_Order"]["actions"]


def test_solution_flow_selects_the_snippet_fields():
    with open(os.path.join(FLOW, "ordre-7-select-strategy-packages.json"), encoding="utf-8") as f:
        snippet = json.load(f)
    acts = _actions()
    assert acts["Select_strategy_packages"]["inputs"]["select"] == snippet
    assert acts["Select_strategy_packages"]["inputs"]["from"] == "@body('Get_items_StrategyPackage')?['value']"
    compose = acts["Compose_order"]
    assert compose["inputs"]["strategyPackages"] == "@body('Select_strategy_packages')"
    assert "Select_strategy_packages" in compose["runAfter"]
    params = acts["Get_items_StrategyPackage"]["inputs"]["parameters"]
    assert params["table"] == "MD_StrategyPackage"
    assert "StrategyKey eq" in params["$filter"]


def test_strategy_package_columns_exist():
    with open(os.path.join(FLOW, "ordre-7-select-strategy-packages.json"), encoding="utf-8") as f:
        text = f.read()
    cols = set(re.findall(r"item\(\)\?\['(\w+)'\]", text)) | {"StrategyKey"}
    schema = cds.load_schema() or {}
    known = schema.get("MD_StrategyPackage", {}).get("cols", {})
    if not known:
        return
    # Udtraekket bruger visningsnavne; Title hedder PackageLabel.
    assert cols <= set(known), sorted(cols - set(known))


def test_every_seeded_package_unit_is_known():
    """UnitKind skal kende hver enhed i MD_StrategyPackage, ellers kan en
    strategi hverken oprettes eller afvises med en klar besked."""
    with open(os.path.join(ROOT, "sharepoint", "seed", "MD_StrategyPackage.csv"), encoding="utf-8-sig") as f:
        units = {r["CycleUnit"] for r in csv.DictReader(f)}
    src = _bas("VhpStrategy.bas")
    i = src.find("Public Function UnitKind(")
    body = src[i:src.find("End Function", i)]
    known = set(re.findall(r'"([A-Z]+)"', body)) - {"TIME", "COUNTER"}
    assert units <= known, sorted(units - known)


def test_package_fields_come_from_the_export_script():
    export = _bas(os.path.join("..", "vba", "Export_Script.bas"))
    config = _bas("VhpConfig.bas")
    const = dict(re.findall(r'Public Const (\w+) As String = "([^"]*)"', config))
    assert const["IA05_BTN_PACKAGES"] in export
    assert const["IA05_PKG_TABLE"] in export
    assert const["IP04_STRATEGY"] in export
    assert const["IA05_PKG_COL_SHORTTEXT"].split("[")[0] in export
    assert const["IA05_PKG_COL_MARK"] in export


def test_steps_only_branch_for_strategy_plans():
    steps = _bas("VhpSteps.bas")
    assert steps.count("If IsStrategy(ctx) Then VhpStrategy.") == 3
    run = _bas("VhpRun.bas")
    assert "VhpStrategy.CreatePlan(sess, order, itemNos, ctx)" in run
    assert 'ctx.Add "strategyKey", VhpStrategy.StrategyKey(order)' in run


def test_counter_strategies_are_stopped_by_validation():
    """Maalepunktet er ikke klar: en taellerstrategi maa ikke naa SAP."""
    order = _bas("VhpOrder.bas")
    i = order.find("Private Sub ValidateStrategy(")
    body = order[i:order.find("End Sub", i)]
    assert 'Case "COUNTER"' in body and 'Case "MIXED"' in body
    assert "measuringPoint" not in _bas("VhpStrategy.bas")
