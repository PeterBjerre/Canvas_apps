# -*- coding: utf-8 -*-
"""
R2-051 / R2-084 pkt. 1: ToMasterData saetter MasterDataNotified EFTER
mailen (fejler mailen, fyrer triggeren igen), og item- og godkendelses-
linjerne escapes, saa "P<10 bar" ikke klipper mailen.

    python3 -m pytest tests/test_vh_to_master_data.py
"""
import flowkit as fk
import wdl_eval

NAME = "BioSap-VhPlan-ToMasterData"


def test_flag_is_set_after_the_mail():
    try_ = fk.find(NAME, "Try")["actions"]
    assert try_["Get_request_index"]["runAfter"] == {}
    assert try_["Set_notified"]["runAfter"] == {"Send_to_master_data": ["Succeeded"]}
    assert list(try_)[-1] == "Set_notified"
    assert '"MasterDataNotified": true' in fk.params(try_["Set_notified"])["parameters/body"]


def test_lines_are_escaped():
    d = fk.definition(NAME)
    items = [{"Title": "Test <A&B>", "FunctionalLocation": "SSV-<1>"}]
    log = [{"Stage": "System", "ItemText": "P<10 bar", "Decision": "Approve",
            "DecidedByEmail": "x@example.test", "Detail": "a & b"}]
    acts = {"Get_items_MaintenanceItems": {"type": "Compose", "inputs": {"body/value": items}},
            "Filter_approval_rows": {"type": "Compose", "inputs": log},
            "Select_item_lines": fk.find(NAME, "Select_item_lines", d),
            "Select_approval_lines": fk.find(NAME, "Select_approval_lines", d)}
    out = wdl_eval.run(acts, list(acts), {}, {}).outputs
    assert out["Select_item_lines"] == ["- Test &lt;A&amp;B&gt; (SSV-&lt;1&gt;)"]
    assert out["Select_approval_lines"] == ["System - P&lt;10 bar - x@example.test a &amp; b"]
