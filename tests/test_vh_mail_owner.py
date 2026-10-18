# -*- coding: utf-8 -*-
"""
R2-049: VH-mails gaar til anmodningens ejer (MD_RequestIndex.RequesterEmail),
ikke til SharePoint-itemets Author. Indsenderen (SubmittedBy) faar Cc, naar
han ikke er ejeren. Godkendelseskortet viser ejerens navn.

R2-048: PlanPublished saetter ikke laengere Editor (servicekontoen efter
kvitteringsflowets MERGE) paa Cc.

    python3 -m pytest tests/test_vh_mail_owner.py
"""
import pytest

import flowkit as fk

INDEX = {"RequesterEmail": "owner@example.test", "RequesterName": "Olga Owner"}
PLAN = {"Author/Email": "author@example.test", "Author/DisplayName": "Arne Author",
        "SubmittedBy": "submitter@example.test", "SapWarnings": None}
MD = "BioSap-MasterDataEmail (orsted_BioSapMasterDataEmail)"

MAILS = [
    ("BioSap-VhPlan-SystemApproval", "Send_returned_mail", "Get_request_index"),
    ("BioSap-VhPlan-CostApproval", "Send_returned_mail", "Get_request_index"),
    ("BioSap-VhPlan-QualityReview", "Send_returned_mail", "Get_request_index"),
    ("BioSap-EmailNotification-NewPlanCreated", "Send_an_email_(V2)-EmailRequestor",
     "Get_AppUrl_based_on_environment"),
    ("BioSap-EmailNotification-PlanPublished", "Send_an_email_(V2)-EmailRequestor",
     "Get_request_index"),
]


def _to_cc(flow, action, lookup, plan, rows):
    p = fk.params(fk.find(flow, action))
    out = {lookup: {"body/value": rows}}
    to = fk.evaluate(p["emailMessage/To"], plan, out, {MD: "md@example.test"})
    cc = fk.evaluate(p.get("emailMessage/Cc", ""), plan, out, {MD: "md@example.test"})
    return to, cc


@pytest.mark.parametrize("flow,action,lookup", MAILS)
def test_mail_goes_to_the_owner_and_cc_the_submitter(flow, action, lookup):
    to, cc = _to_cc(flow, action, lookup, PLAN, [INDEX])
    assert to == "owner@example.test"
    assert cc == "submitter@example.test"


@pytest.mark.parametrize("flow,action,lookup", MAILS)
def test_no_cc_when_the_owner_submitted(flow, action, lookup):
    plan = dict(PLAN, SubmittedBy="OWNER@example.test")
    _to, cc = _to_cc(flow, action, lookup, plan, [INDEX])
    assert cc == ""


@pytest.mark.parametrize("flow,action,lookup", MAILS)
def test_falls_back_to_submitter_then_author(flow, action, lookup):
    to, cc = _to_cc(flow, action, lookup, PLAN, [])
    assert to == "submitter@example.test" and cc == ""
    to, cc = _to_cc(flow, action, lookup, dict(PLAN, SubmittedBy=None), [])
    assert to == "author@example.test" and cc == ""


def test_published_mail_never_cc_the_editor():
    p = fk.params(fk.find("BioSap-EmailNotification-PlanPublished",
                          "Send_an_email_(V2)-EmailRequestor"))
    assert "Editor" not in p["emailMessage/Cc"]
    plan = dict(PLAN, SapWarnings="Add text manually")
    _to, cc = _to_cc("BioSap-EmailNotification-PlanPublished",
                     "Send_an_email_(V2)-EmailRequestor", "Get_request_index", plan, [INDEX])
    assert cc == "submitter@example.test;md@example.test"
    plan = dict(plan, SubmittedBy=None)
    _to, cc = _to_cc("BioSap-EmailNotification-PlanPublished",
                     "Send_an_email_(V2)-EmailRequestor", "Get_request_index", plan, [INDEX])
    assert cc == "md@example.test"


@pytest.mark.parametrize("flow", ["BioSap-VhPlan-SystemApproval",
                                  "BioSap-VhPlan-CostApproval",
                                  "BioSap-VhPlan-QualityReview"])
def test_approval_card_names_the_owner(flow):
    det = fk.params(fk.find(flow, "Start_and_wait_for_an_approval"))[
        "WebhookApprovalCreationInput/details"]
    assert "?['RequesterName'], triggerBody()?['Author/DisplayName']" in det


def test_master_data_mail_names_the_owner():
    body = fk.params(fk.find("BioSap-VhPlan-ToMasterData", "Send_to_master_data"))[
        "emailMessage/Body"]
    assert "@{triggerBody()?['Author/DisplayName']}" not in body
    assert "['RequesterName'], triggerBody()?['Author/DisplayName']" in body
