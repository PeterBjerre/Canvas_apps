# -*- coding: utf-8 -*-
"""
R2-084 pkt. 3: Material- og MP-flowet slaar godkenderen op i Office 365
(Entra) som VH-flowene. Findes 1. godkender ikke, bruges 2. godkender, og
findes ingen af dem, er raekken uden godkender (Log_no_approver) i stedet
for at Start_and_wait fejler og anmodningen strander i Catch.

    python3 -m pytest tests/test_material_mp_resolve.py
"""
import pytest

import flowkit as fk
import wdl_eval

FLOWS = ["BioSap-Material-SystemApproval", "BioSap-MeasuringPoint-Approval"]
DOM = "BioSap-EmailDomain (orsted_BioSapEmailDomain)"


@pytest.mark.parametrize("name", FLOWS)
def test_resolution_chain(name):
    d = fk.definition(name)
    sib = fk.siblings(name, "Approver_email", d)
    for a in ("Resolve_primary", "Resolve_secondary"):
        assert sib[a]["inputs"]["host"]["operationId"] == "UserProfile_V2"
        assert sib[a]["inputs"]["retryPolicy"] == {"type": "none"}
    assert sib["Resolve_primary"]["inputs"]["parameters"]["id"] == "@outputs('Approver_email')"
    assert sib["Resolve_secondary"]["inputs"]["parameters"]["id"] == "@outputs('Approver_email_alt')"
    assert sib["Resolve_secondary"]["runAfter"] == {"Resolve_primary": ["Failed"]}
    assert sib["Resolved_email"]["runAfter"] == {
        "Resolve_primary": ["Succeeded", "Failed"],
        "Resolve_secondary": ["Succeeded", "Failed", "Skipped"]}
    ar = fk.find(name, "Append_resolved", d)["inputs"]["value"]
    assert ar["approver"] == "@outputs('Resolved_email')"
    assert ar["initials"] == "@toUpper(outputs('Resolved_initials'))"


@pytest.mark.parametrize("name", FLOWS)
@pytest.mark.parametrize("absent,expected", [(False, "y@x.test"), (True, "a@x.test")])
def test_alternative_is_the_other_approver(name, absent, expected):
    d = fk.definition(name)
    rows = [{"Approver1": "A", "Approver2": "Y", "Approver1Absent": absent}]
    acts = {"Filter_approver_rows": {"type": "Compose", "inputs": rows},
            "Initials_alt": fk.find(name, "Initials_alt", d),
            "Approver_email_alt": fk.find(name, "Approver_email_alt", d)}
    out = wdl_eval.run(acts, list(acts), {}, {}, parameters={DOM: "x.test"}).outputs
    assert out["Approver_email_alt"] == expected
