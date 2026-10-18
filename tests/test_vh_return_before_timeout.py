# -*- coding: utf-8 -*-
"""
R2-029: SystemApproval har concurrency 1 paa triggeren (som Cost/Quality/
ToMasterData), og i System og Cost vinder et *Return* over en timeout: har
ét item faaet Return og et andet er timet ud, sendes planen retur med
kommentaren i stedet for at starte forfra og spoerge igen.

    python3 -m pytest tests/test_vh_return_before_timeout.py
"""
import pytest

import flowkit as fk

TRIGGER = "When_an_item_is_created_or_modified"


@pytest.mark.parametrize("name", ["BioSap-VhPlan-SystemApproval",
                                  "BioSap-VhPlan-CostApproval",
                                  "BioSap-VhPlan-QualityReview",
                                  "BioSap-VhPlan-ToMasterData"])
def test_one_run_at_a_time(name):
    trig = fk.definition(name)["triggers"][TRIGGER]
    assert trig["runtimeConfiguration"]["concurrency"]["runs"] == 1


@pytest.mark.parametrize("name", ["BioSap-VhPlan-SystemApproval",
                                  "BioSap-VhPlan-CostApproval"])
def test_return_is_decided_before_timeout(name):
    d = fk.definition(name)
    ret = fk.find(name, "Any_return", d)
    assert ret["runAfter"] == {"Timeout_rows": ["Succeeded"]}
    assert ret["expression"] == {"greater": ["@length(body('Return_rows'))", 0]}
    assert "Set_plan_returned" in ret["actions"]
    timeout = ret["else"]["actions"]["Any_timeout"]
    assert list(timeout["actions"]) == ["Release_stage_after_timeout"]
    assert "Set_stage_next" in timeout["else"]["actions"]
    # Kun én Any_timeout, og den ligger under Any_return.
    assert fk.siblings(name, "Any_timeout", d) is ret["else"]["actions"]
