# -*- coding: utf-8 -*-
"""
En VH-plan, der er sendt retur i godkendelsen (Returned / AfventerInfo),
kan ejeren rette og indsende igen - kun VH-planen, og uden at kunne slette.

    python3 -m pytest tests/test_vh_resubmit.py
"""
import json
import os
import re

from conftest import ROOT

import permissions as perm

VH = os.path.join(ROOT, "BIO SAP App", "ScreenVhPlan.pa.yaml")
HUB = os.path.join(ROOT, "BIO SAP App", "ScreenMdHub.pa.yaml")
FLOWS = os.path.join(ROOT, "solution", "BIOSAP", "src", "Workflows")

OWNER_BACK = ('Lower(Coalesce(varVhpIdxNow.RequesterEmail, "")) = varVhpMe && '
              '(varVhpIdxNow.Status.Value = "Kladde" || varVhpIdxNow.Status.Value = "AfventerInfo")')


def _vh():
    return open(VH, encoding="utf-8").read()


def test_permission_default_is_unchanged():
    """Equipment, Material, MP og FL: ejeren stadig kun i Kladde."""
    rule = perm.may_change("R.RequesterEmail", "R.Status.Value", "me")
    owner_part = rule.split("||")[0]
    assert "AfventerInfo" not in owner_part
    assert "AfventerInfo" in perm.may_change("R.RequesterEmail", "R.Status.Value", "me", resubmit=True).split("||")[1]


def test_vh_owner_may_edit_and_save_returned_plan():
    text = _vh()
    # Indlaesning (Edit) og rettigheden i selve gemningen.
    assert ('Set(varVhpCanEdit, ((Lower(Coalesce(idx.RequesterEmail, "")) = varVhpMe && '
            '(idx.Status.Value = "Kladde" || idx.Status.Value = "AfventerInfo"))') in text
    assert OWNER_BACK in text


def test_save_draft_keeps_returned_status():
    assert re.search(r'Status: If\(!IsBlank\(varVhpPlanNow\) && \(.*'
                     r'varVhpPlanNow\.Status\.Value = "Returned"\), varVhpPlanNow\.Status, '
                     r'\{ Value: "Draft" \}\)', _vh())


def test_owner_cannot_delete_returned_plan():
    assert '(varVhpFlow.Status <> "Returned" || IsAdmin)' in _vh()
    # Sletningen selv bruger reglen uden resubmit.
    import request_delete as rd
    assert "AfventerInfo" not in rd.may_delete("I", "me").split("||")[0]


def test_hub_edit_enabled_for_returned_vh_plan_only():
    text = open(HUB, encoding="utf-8").read()
    assert ('ThisItem.Status.Value = "AfventerInfo") && '
            '(ThisItem.Domain.Value = "MaintenancePlan")') in text


def _actions(path):
    d = json.load(open(path, encoding="utf-8"))["properties"]["definition"]["actions"]
    out = {}

    def walk(acts):
        for k, v in acts.items():
            out[k] = v
            walk(v.get("actions", {}))
            walk(v.get("else", {}).get("actions", {}))
            for c in v.get("cases", {}).values():
                walk(c.get("actions", {}))
    walk(d)
    return out


def _flow(name):
    f = [f for f in os.listdir(FLOWS) if f.startswith(name) and f.endswith(".json")]
    assert len(f) == 1, name
    return _actions(os.path.join(FLOWS, f[0]))


def test_flows_reuse_earlier_approvals():
    """Genindsendelsen fortsaetter fra trinnet: System og Cost springer
    items over, der er godkendt tidligere (samme ItemGuid)."""
    for name in ("BioSap-VhPlan-SystemApproval", "BioSap-VhPlan-CostApproval"):
        a = _flow(name)
        assert "'Prev'" in a["Path"]["inputs"], name
        assert "ItemGuid" in a["Filter_prev_rows"]["inputs"]["where"], name
        assert a["Log_skipped_previous"]["inputs"]["parameters"]["item/Decision"] == "Skipped"
