# -*- coding: utf-8 -*-
"""
R2-028: alle grene, der sender en VH-plan retur, opdaterer indekset
(AfventerInfo, trin 3) og mailer ejeren - ogsaa "ingen items" og "ingen
godkender". Foer stod indekset i UnderBehandling, og rekvirenten hoerte
intet.

    python3 -m pytest tests/test_vh_return_branches.py
"""
import json

import pytest

import flowkit as fk

OWNER = "@coalesce(first(outputs('Get_request_index')?['body/value'])?['RequesterEmail']"

BRANCHES = [
    ("BioSap-VhPlan-SystemApproval", "Return_no_items", "no_items"),
    ("BioSap-VhPlan-CostApproval", "Return_no_items", "no_items"),
    ("BioSap-VhPlan-CostApproval", "Set_plan_returned_no_approver", "no_approver"),
    ("BioSap-VhPlan-QualityReview", "Set_plan_returned_no_approver", "no_approver"),
]


def _returns(name):
    """Handlinger, der saetter planens Status = Returned."""
    d = fk.definition(name)
    out = []
    for n, a, _p in fk.walk(d["actions"]):
        body = json.dumps(a.get("inputs"))
        if a.get("type") in ("OpenApiConnection", "Compose") and \
                ('\\"Status\\": \\"Returned\\"' in body or '"Status": "Returned"' in body):
            out.append(n)
    return out


@pytest.mark.parametrize("name", ["BioSap-VhPlan-SystemApproval",
                                  "BioSap-VhPlan-CostApproval",
                                  "BioSap-VhPlan-QualityReview"])
def test_every_return_is_covered(name):
    found = set(_returns(name))
    known = {a for n, a, _s in BRANCHES if n == name} | {"Body_return"}
    assert found == known, found


@pytest.mark.parametrize("name,action,suffix", BRANCHES)
def test_branch_patches_index_and_mails_owner(name, action, suffix):
    d = fk.definition(name)
    sib = fk.siblings(name, action, d)
    cond = sib["Index_returned_" + suffix]
    assert cond["runAfter"] == {action: ["Succeeded"]}
    p = fk.params(cond["actions"]["Patch_index_returned_" + suffix])
    assert p["item/Status"] == {"Value": "AfventerInfo"}
    assert p["item/StatusStep"] == 3
    mail = sib["Send_returned_mail_" + suffix]
    assert mail["runAfter"] == {"Index_returned_" + suffix: ["Succeeded", "Failed", "Skipped"]}
    mp = fk.params(mail)
    assert mp["emailMessage/To"].startswith(OWNER)
    assert "returned by the" in mp["emailMessage/Body"]
    assert "submit it again" in mp["emailMessage/Body"]


def test_error_notifiers_still_get_the_no_approver_mail():
    for name in ("BioSap-VhPlan-CostApproval", "BioSap-VhPlan-QualityReview"):
        p = fk.params(fk.find(name, "Mail_no_approver"))
        assert "ErrorNotifiers" in p["emailMessage/To"]
