# -*- coding: utf-8 -*-
"""
R2-030: Material- og MP-godkendelsen haandterer en timeout (P14D) som VH-
flowene: hver ubesvaret raekke logges som Timeout, godkenderen faar besked
om, at anmodningen er udloebet, og anmodningen sendes RETUR til rekvirenten
med forklaringen "No answer from ... within 14 days" (Peters valg: retur,
ikke genstart). Foer endte den i Catch uden ejer.

    python3 -m pytest tests/test_material_mp_timeout.py
"""
import pytest

import flowkit as fk
import wdl_eval

FLOWS = ["BioSap-Material-SystemApproval", "BioSap-MeasuringPoint-Approval"]


@pytest.mark.parametrize("name", FLOWS)
def test_timeout_is_logged_and_the_approver_told(name):
    loop = fk.find(name, "For_each_approver")["actions"]
    wait = loop["Start_and_wait_for_an_approval"]
    assert wait["limit"]["timeout"] == "P14D"
    tl = loop["For_each_my_unit_timeout"]
    assert tl["runAfter"] == {"Start_and_wait_for_an_approval": ["TimedOut"]}
    p = fk.params(tl["actions"]["Log_timeout"])
    assert p["item/Decision"] == "Timeout"
    assert p["item/Title"] == "@outputs('RunName')"
    assert p["item/ItemGuid"] == "@items('For_each_my_unit_timeout')?['itemGuid']"
    assert "within 14 days" in p["item/Detail"]
    mail = loop["Send_reminder"]
    assert mail["runAfter"] == {"For_each_my_unit_timeout": ["Succeeded"]}
    mp = fk.params(mail)
    assert mp["emailMessage/To"] == "@items('For_each_approver')"
    assert "expired after 14 days" in mp["emailMessage/Body"]
    assert "returned to the requester" in mp["emailMessage/Body"]


@pytest.mark.parametrize("name", FLOWS)
def test_results_are_read_after_a_timeout_and_returned(name):
    g = fk.find(name, "Get_log_results")
    assert g["runAfter"] == {"For_each_approver": ["Succeeded", "TimedOut"]}
    q = fk.find(name, "Return_rows")
    rows = [{"Decision": "Timeout", "Title": "run-1", "ItemText": "X",
             "Detail": "No answer from a@x within 14 days"},
            {"Decision": "Return", "Title": "run-1"},
            {"Decision": "Approve", "Title": "run-1"},
            {"Decision": "Timeout", "Title": "old-run"}]
    acts = {"RunName": {"type": "Compose", "inputs": "run-1"},
            "Get_log_results": {"type": "Compose", "inputs": {"body/value": rows}},
            "Return_rows": q}
    out = wdl_eval.run(acts, list(acts), {}, {}).outputs["Return_rows"]
    assert [r["Decision"] for r in out] == ["Timeout", "Return"]
