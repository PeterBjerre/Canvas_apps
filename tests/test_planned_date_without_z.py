"""SharePoint sender PlannedDate uden Z (2027-10-18T00:00:00.0000000), og
convertFromUtc afviser saa vaerdien (Peter 2026-10-18, Compose order:
InvalidTemplate). Begge flows skal klare baade med og uden Z."""
import glob
import json
import os

import pytest

import wdl_eval
from conftest import ROOT

WF = os.path.join(ROOT, "solution", "BIOSAP", "src", "Workflows")


def _defn(name):
    f = glob.glob(os.path.join(WF, name + "-*.json"))[0]
    return json.load(open(f, encoding="utf-8-sig"))["properties"]["definition"]


def _find(acts, name):
    for k, v in acts.items():
        if k == name:
            return v
        for sub in ("actions",):
            if sub in v:
                r = _find(v[sub], name)
                if r:
                    return r
        if "else" in v:
            r = _find(v["else"].get("actions", {}), name)
            if r:
                return r
    return None


def test_the_evaluator_rejects_a_date_without_z_like_power_automate():
    with pytest.raises(ValueError):
        wdl_eval.evaluate("convertFromUtc('2027-10-18T00:00:00.0000000', 'Romance Standard Time')", {})


@pytest.mark.parametrize("value, expected", [
    ("2027-10-18T00:00:00.0000000", "2027-10-18"),   # datokolonne uden Z
    ("2027-10-17T22:00:00Z", "2027-10-18"),          # midnat dansk sommertid i UTC
])
def test_order_planned_date(value, expected):
    expr = _find(_defn("BioSap-VhPlan-SapOrder")["actions"], "Compose_order")["inputs"]["plan"]["plannedDate"]
    assert expr.startswith("@{") and expr.endswith("}")
    ctx = {"triggerBody": {"PlannedDate": value}}
    out = wdl_eval.run({"X": {"type": "Compose", "inputs": expr}}, ["X"], {"PlannedDate": value}, {}).outputs
    assert out["X"] == expected


def test_repo_snippet_matches_the_solution():
    snip = json.load(open(os.path.join(ROOT, "flow", "sap-ordre", "ordre-4-compose-order.json"), encoding="utf-8-sig"))
    sol = _find(_defn("BioSap-VhPlan-SapOrder")["actions"], "Compose_order")["inputs"]["plan"]["plannedDate"]
    assert json.dumps(snip).count("endsWith(string(triggerBody()?['PlannedDate']), 'Z')") == 1
    assert "endsWith(string(triggerBody()?['PlannedDate']), 'Z')" in sol


def test_mail_dates_accept_values_without_z():
    acts = _defn("BioSap-EmailNotification-PlanPublished")["actions"]
    body = json.dumps(_find(acts, "Compose-EmailContent")["inputs"])
    assert "convertFromUtc(triggerBody()?['PlannedDate']" not in body
    assert "convertFromUtc(coalesce(triggerBody()?['SapCreatedOn']" not in body
