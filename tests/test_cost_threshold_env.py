# -*- coding: utf-8 -*-
"""
R2-082: CostApproval laeser omkostningsgraensen fra AppSettings for SIT
miljoe (BioSap-Environment), ikke den foerste raekke, SharePoint returnerer.
Provisioneringen skriver en raekke pr. Environment (DEV/TEST/PROD).

    python3 -m pytest tests/test_cost_threshold_env.py
"""
import flowkit as fk

NAME = "BioSap-VhPlan-CostApproval"
ENV = "BioSap-Environment (orsted_BioSapEnvironment)"


def test_threshold_is_filtered_on_environment():
    p = fk.params(fk.find(NAME, "Get_settings"))
    assert p["$filter"] == ("Option eq 'CostApprovalThresholdDkk' and "
                            "Environment eq '@{parameters('%s')}'" % ENV)
    assert p["$top"] == 1
    assert fk.evaluate(p["$filter"], parameters={ENV: "PROD"}) == \
        "Option eq 'CostApprovalThresholdDkk' and Environment eq 'PROD'"


def test_environment_is_an_environment_variable():
    par = fk.definition(NAME)["parameters"][ENV]
    assert par["metadata"]["schemaName"] == "orsted_BioSapEnvironment"


def test_fallback_stays_300000():
    assert "300000" in fk.find(NAME, "Threshold")["inputs"]
