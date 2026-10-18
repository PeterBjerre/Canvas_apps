# -*- coding: utf-8 -*-
"""
Hubbens "Waiting for me" / "My queue" filtrerer paa
MD_RequestIndex.AssignedToEmail (R2-015). Feltet skal derfor skrives af
godkendelsesflowene: den foerste aabne godkender, naar anmodningen er
UnderBehandling, og tomt, naar den er sendt retur, godkendt eller klar.

Adressen dannes som godkendelsens modtager i samme flow - saa den, der
faar godkendelsen, ogsaa ser den i hubben (varMdMe = Lower(User().Email)).

    python3 -m pytest -q tests/test_request_index_assignee.py
"""
import glob
import json
import os

import pytest

from conftest import ROOT
import wdl_eval

FLOWS = os.path.join(ROOT, "solution", "BIOSAP", "src", "Workflows")
SCHEMA = os.path.join(ROOT, "sharepoint", "inspect", "out", "schema.json")
EMAIL, NAME = "item/AssignedToEmail", "item/AssignedToName"

MD = ("BioSap-Material-SystemApproval", "BioSap-MeasuringPoint-Approval")
VH = ("BioSap-VhPlan-SystemApproval", "BioSap-VhPlan-CostApproval",
      "BioSap-VhPlan-QualityReview")


def _definition(name):
    path, = glob.glob(os.path.join(FLOWS, name + "-*.json"))
    return json.load(open(path, encoding="utf-8-sig"))["properties"]["definition"]


def _actions(acts):
    for name, a in acts.items():
        yield name, a
        if "actions" in a:
            yield from _actions(a["actions"])
        if "else" in a:
            yield from _actions(a["else"].get("actions", {}))
        for c in a.get("cases", {}).values():
            yield from _actions(c.get("actions", {}))
        if "default" in a:
            yield from _actions(a["default"].get("actions", {}))


def _all(name):
    return dict(_actions(_definition(name)["actions"]))


def _index_patches(name):
    """{handling: (status, parametre)} for PatchItem paa MD_RequestIndex."""
    out = {}
    for n, a in _all(name).items():
        inputs = a.get("inputs")
        if not isinstance(inputs, dict) or inputs.get("host", {}).get("operationId") != "PatchItem":
            continue
        p = inputs["parameters"]
        if "MD_RequestIndex" not in p.get("table", ""):
            continue
        status = p.get("item/Status/Value") or p.get("item/Status", {}).get("Value")
        out[n] = (status, p)
    return out


def test_the_columns_exist_in_the_schema():
    lists = json.load(open(SCHEMA, encoding="utf-8-sig"))["lists"]
    idx, = [l for l in lists if l["title"] == "MD_RequestIndex"]
    names = {f["internalName"] for f in idx["fields"]}
    assert {"AssignedToEmail", "AssignedToName"} <= names


@pytest.mark.parametrize("name", MD + VH)
def test_in_progress_names_the_approver_and_closed_clears_it(name):
    patches = _index_patches(name)
    assert patches, name
    assigned = []
    for n, (status, p) in patches.items():
        assert EMAIL in p, (name, n)
        if status == "UnderBehandling":
            if p[EMAIL]:
                assert p[EMAIL].startswith("@toLower("), (name, n)
                assigned.append(n)
        else:
            assert status in ("AfventerInfo", "Indsendt", "KlarTilSAP"), (name, n, status)
            assert p[EMAIL] == "" and p.get(NAME) == "", (name, n)
    assert assigned, name


@pytest.mark.parametrize("name", MD)
def test_md_flows_assign_the_first_approver_of_the_list_they_ask(name):
    acts = _all(name)
    progress = _index_patches(name)["Patch_index_progress"][1]
    assert progress[EMAIL] == "@toLower(coalesce(first(outputs('Approver_list')), ''))"
    # Det er den liste, godkendelserne sendes til.
    assert acts["For_each_approver"]["foreach"] == "@outputs('Approver_list')"
    assert acts["Start_and_wait_for_an_approval"]["inputs"]["parameters"][
        "WebhookApprovalCreationInput/assignedTo"] == "@items('For_each_approver')"
    # Og den er kendt, foer indeksraekken skrives - og foer der spoerges.
    assert acts["Patch_index_progress"]["runAfter"] == {"Approver_list": ["Succeeded"]}
    assert acts["For_each_approver"]["runAfter"] == {"Patch_index_progress": ["Succeeded"]}
    # Kun e-mail: flowet kender ikke godkenderens navn.
    assert NAME not in progress


def test_mp_counter_step_assigns_the_first_creator():
    acts = _all("BioSap-MeasuringPoint-Approval")
    p = _index_patches("BioSap-MeasuringPoint-Approval")["Patch_index_counter"][1]
    assert p[EMAIL] == "@toLower(coalesce(first(outputs('Creator_list')), ''))"
    assert acts["For_each_creator"]["foreach"] == "@outputs('Creator_list')"
    assert acts["Patch_index_counter"]["runAfter"] == {"Creator_list": ["Succeeded"]}
    assert acts["For_each_creator"]["runAfter"] == {"Patch_index_counter": ["Succeeded"]}


@pytest.mark.parametrize("approvers,want", [
    (["ab@example.test", "cd@example.test"], "ab@example.test"),
    (["AB@Example.Test"], "ab@example.test"),
    ([], ""),
])
def test_the_first_approver_expression(approvers, want):
    expr = _index_patches(MD[0])["Patch_index_progress"][1][EMAIL]
    acts = {"Approver_list": {"type": "Compose", "inputs": approvers},
            "Assigned": {"type": "Compose", "inputs": expr}}
    out = wdl_eval.run(acts, ["Approver_list", "Assigned"], {}, {}).outputs
    assert out["Assigned"] == want


@pytest.mark.parametrize("name", VH)
def test_vh_flows_assign_the_approver_just_before_asking(name):
    acts = _all(name)
    p = acts["Patch_index_assigned"]["inputs"]["parameters"]
    ask = acts["Start_and_wait_for_an_approval"]["inputs"]["parameters"][
        "WebhookApprovalCreationInput/assignedTo"]
    assert p[EMAIL] == "@toLower(%s)" % ask[1:]
    assert "displayName" in p[NAME]
    guard = acts["Index_assigned"]
    assert guard["expression"] == {"greater": [
        "@length(outputs('Get_request_index')?['body/value'])", 0]}
    # Godkendelsen (Cost: loekken) venter paa indeksraekken, men ikke paa
    # at den lykkes.
    first = "For_each_item" if name.endswith("CostApproval") else "Start_and_wait_for_an_approval"
    assert acts[first]["runAfter"] == {"Index_assigned": ["Succeeded", "Failed"]}


@pytest.mark.parametrize("name", VH[:2])
def test_vh_handover_to_the_next_stage_clears_the_approver(name):
    """Patch_index_progress koerer, naar trinnet er faerdigt. Naeste trins
    flow skriver sin egen godkender."""
    status, p = _index_patches(name)["Patch_index_progress"]
    assert status == "UnderBehandling"
    assert p[EMAIL] == "" and p[NAME] == ""
