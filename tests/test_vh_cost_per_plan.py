# -*- coding: utf-8 -*-
"""
Omkostningsgodkendelsen gaelder HELE planen (Peter 2026-10-19): een
godkendelse, sammenlignet med summen af alle items' operationer, og een
raekke i MD_ApprovalLog med ItemGuid "PLAN". Kvalitetsflowets vaern
kraever den raekke i stedet for en pr. item.

    python3 -m pytest tests/test_vh_cost_per_plan.py
"""
import json

import flowkit as fk

COST = "BioSap-VhPlan-CostApproval"
QUALITY = "BioSap-VhPlan-QualityReview"


def test_cost_flow_has_no_loop_over_items():
    s = json.dumps(fk.find(COST, "Plan_cost"))
    assert fk.find(COST, "Plan_cost")["type"] == "Scope"
    assert "For_each_item" not in s and "items('" not in s


def test_cost_is_one_decision_for_the_plan():
    assert fk.find(COST, "ItemGuid")["inputs"] == "PLAN"
    ops = fk.find(COST, "Filter_ops")["inputs"]
    assert ops["from"] == "@outputs('Get_tasks')?['body/value']"
    assert "body('Select_item_ids')" in ops["where"]
    for name in ("Log_skipped_under", "Log_skipped_previous", "Log_approve",
                 "Log_return_by_approver", "Log_timeout"):
        assert fk.params(fk.find(COST, name))["item/ItemText"] == "Whole plan", name
    title = fk.params(fk.find(COST, "Start_and_wait_for_an_approval"))[
        "WebhookApprovalCreationInput/title"]
    assert "triggerBody()?['Title']" in title


def test_quality_guard_needs_the_plan_cost_row():
    where = fk.find(QUALITY, "Filter_missing")["inputs"]["where"]
    assert "contains(body('Select_cost_guids'), 'PLAN')" in where
    assert "contains(body('Select_sys_guids'), coalesce(item()?['ItemGuid']" in where
