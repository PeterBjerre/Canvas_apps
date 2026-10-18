# -*- coding: utf-8 -*-
"""
R2-087: naar Wait udloeber efter P14D, kan den gamle godkendelse ikke
laengere besvares. Paamindelsen maa derfor ikke bede om at svare paa den,
men skal sige, at den er udloebet, og at en ny kommer.

    python3 -m pytest tests/test_vh_expired_reminder.py
"""
import pytest

import flowkit as fk


@pytest.mark.parametrize("name", ["BioSap-VhPlan-SystemApproval",
                                  "BioSap-VhPlan-CostApproval",
                                  "BioSap-VhPlan-QualityReview"])
def test_reminder_says_the_request_expired(name):
    a = fk.find(name, "Send_reminder")
    assert a["runAfter"] == {"Log_timeout": ["Succeeded"]}
    p = fk.params(a)
    body = p["emailMessage/Body"]
    assert "expired after 14 days" in body
    assert "can no longer be answered" in body
    assert "respond to th" in body and "new" in body
    assert "has not been answered" not in body
    assert "in the email from Power Automate" not in body
    assert "expired" in p["emailMessage/Subject"]
    wait = fk.find(name, "Start_and_wait_for_an_approval")
    assert wait["limit"]["timeout"] == "P14D"
