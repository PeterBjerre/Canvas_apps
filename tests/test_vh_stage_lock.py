# -*- coding: utf-8 -*-
"""
VH-godkendelsens trinlaas (R2-017).

Hvert trinflow (System, Cost, Quality) starter med Claim_stage, der skriver
koerslens navn i planens StageRunId. Triggeren kraever, at StageRunId er
tom. Fejlede et trin, blev laasen staaende, og planen kunne aldrig koere
det trin igen. Catch frigiver nu laasen - men kun hvis det stadig er DENNE
koersels laas - og afslutter koerslen som Failed.

    python3 -m pytest -q tests/test_vh_stage_lock.py
"""
import glob
import json
import os

import pytest

from conftest import ROOT

FLOWS = os.path.join(ROOT, "solution", "BIOSAP", "src", "Workflows")
STAGES = ("BioSap-VhPlan-SystemApproval", "BioSap-VhPlan-CostApproval",
          "BioSap-VhPlan-QualityReview")
ALL = {"Succeeded", "Failed", "Skipped", "TimedOut"}


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


@pytest.mark.parametrize("name", STAGES)
def test_the_stage_is_claimed_with_the_run_name(name):
    d = _definition(name)
    trigger, = d["triggers"].values()
    assert {"expression": "@empty(triggerBody()?['StageRunId'])"} in trigger["conditions"]
    claim = d["actions"]["Try"]["actions"]["Claim_stage"]
    assert "\"StageRunId\": \"@{workflow()?['run']?['name']}\"" in \
        claim["inputs"]["parameters"]["parameters/body"]


@pytest.mark.parametrize("name", STAGES)
def test_a_failed_stage_releases_its_own_lock(name):
    d = _definition(name)
    catch = d["actions"]["Catch"]["actions"]
    get = catch["Get_plan_after_error"]
    assert get["inputs"]["host"]["operationId"] == "GetItem"
    assert get["inputs"]["parameters"]["id"] == "@triggerBody()?['ID']"
    assert get["inputs"]["parameters"]["table"] == \
        d["triggers"]["When_an_item_is_created_or_modified"]["inputs"]["parameters"]["table"]

    cond = catch["Stage_still_claimed_by_this_run"]
    assert cond["type"] == "If"
    assert cond["runAfter"] == {"Get_plan_after_error": ["Succeeded"]}
    # Kun denne koersels laas - en nyere koersel kan have taget trinnet.
    assert cond["expression"] == {"equals": [
        "@body('Get_plan_after_error')?['StageRunId']", "@workflow()?['run']?['name']"]}
    release = cond["actions"]["Release_stage_after_error"]
    p = release["inputs"]["parameters"]
    assert p["parameters/headers"]["X-HTTP-Method"] == "MERGE"
    assert p["parameters/body"].endswith("\"StageRunId\": \"\"}")
    # Samme kald som den eksisterende frigivelse efter timeout.
    timeout = dict(_actions(d["actions"]))["Release_stage_after_timeout"]
    assert release["inputs"] == timeout["inputs"]


@pytest.mark.parametrize("name", STAGES)
def test_the_catch_still_mails_and_then_ends_failed(name):
    catch = _definition(name)["actions"]["Catch"]["actions"]
    assert catch["Send_notification_to_development_team"]["inputs"]["host"]["operationId"] == \
        "SendEmailV2"
    last = list(catch)[-1]
    term = catch[last]
    assert term["type"] == "Terminate"
    assert term["inputs"]["runStatus"] == "Failed"
    # Efter baade mailen og frigivelsen, uanset hvordan de gik.
    assert {k: set(v) for k, v in term["runAfter"].items()} == {
        "Send_notification_to_development_team": ALL,
        "Stage_still_claimed_by_this_run": ALL,
    }


@pytest.mark.parametrize("name", STAGES)
def test_every_run_after_points_at_a_sibling(name):
    """Et runAfter maa kun naevne handlinger i samme scope."""
    def check(acts):
        for n, a in acts.items():
            for dep in a.get("runAfter", {}):
                assert dep in acts, (name, n, dep)
            for sub in [a.get("actions"), a.get("else", {}).get("actions")] + \
                    [c.get("actions") for c in a.get("cases", {}).values()] + \
                    [a.get("default", {}).get("actions")]:
                if sub:
                    check(sub)
    check(_definition(name)["actions"])
