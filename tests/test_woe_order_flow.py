# -*- coding: utf-8 -*-
"""
BioSap-Integration-WoeOrder (docs/45): ET flow, der henter alt om en
SAP-ordre fra WOE-API'et og SAP Utility i een omgang. Header foerst (den
giver id'erne), derefter de otte WOE-kald parallelt, og til sidst
attachments og OperationText pr. operation fra SAP Utility.

    python3 -m pytest -q tests/test_woe_order_flow.py

Repoet er offentligt. Secret og noegler kommer fra miljoevariabler, og
appen faar altid et svar (ok/status/message/result), ogsaa naar et af
kaldene giver 403, fordi API-teamet endnu ikke har aabnet endpointet.
"""
import os

import flowkit as fk

NAME = "BioSap-Integration-WoeOrder"
FLOW_ID = "4a7e2c15-9b3d-4f68-a2c1-7d5e8b3f0c92"
SECRET = "BioSap-WOC-Client-Secret (orsted_BioSapWOCClientSecret)"
WOE_KEY = "BioSap-WOE-Dev-ApiKey (orsted_BioSapWoeDevApiKey)"
SU_SECRET = "BioSap-SapUtility-Client-Secret (orsted_BioSapSapUtilityClientSecret)"
SU_KEY = "BioSap-SapUtility-Test-ApiKey (orsted_BioSapSapUtilityTestApiKey)"

WOE = "@{outputs('Setup')?['woeBaseUrl']}"
SU = "@{outputs('Setup')?['sapUtilityBaseUrl']}"
WO = "@{encodeUriComponent(variables('WorkOrderId'))}"
OBJ = "@{encodeUriComponent(variables('ObjectId'))}"

# Raekkefoelgen fra Peters billede: header giver id'erne, resten foelger.
WOE_CALLS = {
    "Call_operations": WOE + "/operations/" + WO,
    "Call_tasklistitems": WOE + "/operations/" + WO + "/tasklistitems",
    "Call_objects": WOE + "/workorders/" + WO + "/objects",
    "Call_status": WOE + "/workorders/" + OBJ + "/status",
    "Call_partner": WOE + "/workorders/" + WO + "/partner",
    "Call_activities": WOE + "/workorders/" + WO + "/activities",
    "Call_causes": WOE + "/workorders/" + WO + "/causes",
    "Call_feedback": WOE + "/workorders/" + WO + "/feedback",
}
ALL = ["Succeeded", "Failed", "TimedOut"]
SHAPE = ["ok", "status", "message", "result"]
SECTIONS = ["header", "operations", "tasklistitems", "objects", "status", "partner",
            "activities", "causes", "feedback"]


def test_flow_is_in_the_solution():
    solution = open(os.path.join(fk.FLOWS, "..", "Other", "Solution.xml"), encoding="utf-8-sig").read()
    assert "{%s}" % FLOW_ID in solution
    assert os.path.exists(fk.path(NAME) + ".data.xml")
    assert fk.flow(NAME)["properties"]["connectionReferences"] == {}
    trig = fk.definition(NAME)["triggers"]["manual"]
    assert trig["kind"] == "PowerAppV2"
    assert [p["title"] for p in trig["inputs"]["schema"]["properties"].values()] == ["OrderNumber"]


def test_two_tokens_two_app_registrations():
    s = fk.find(NAME, "Setup")["inputs"]
    assert s["woeClientId"] == "6b699286-72e8-4e8a-8e93-ce166f5c22d0"
    assert s["woeBaseUrl"] == "https://dev.api.orsted.dk/woe/api"
    # SAP Utility: samme app-registrering og base-URL som testflowet i PR #124.
    assert s["sapUtilityClientId"] == "9ab1e626-a2c7-4202-b325-398d6f68ee24"
    assert s["sapUtilityScope"].endswith("/9ab1e626-a2c7-4202-b325-398d6f68ee24/.default")
    assert s["sapUtilityBaseUrl"] == "https://test.api.orsted.dk/saputility"
    for action, secret, prefix in (("Get_token", SECRET, "woe"),
                                   ("Get_token_saputility", SU_SECRET, "sapUtility")):
        tok = fk.find(NAME, action)
        assert "client_secret=@{parameters('%s')}" % secret in tok["inputs"]["body"]
        assert "outputs('Setup')?['%sScope']" % prefix in tok["inputs"]["body"]
        assert tok["runtimeConfiguration"]["secureData"]["properties"] == ["inputs", "outputs"]


def test_header_first_then_the_eight_woe_calls_in_parallel():
    header = fk.find(NAME, "Call_header")
    assert header["inputs"]["uri"] == WOE + "/workorders/" + WO + "/header"
    assert header["runAfter"] == {}
    found = fk.find(NAME, "Header_found")
    assert found["runAfter"] == {"Call_header": ALL}
    assert found["expression"] == {"and": [{"equals": ["@outputs('Call_header')?['statusCode']", 200]}]}
    # Id'erne starter fra ordrenummeret og erstattes af headerens, naar den svarer.
    assert "variables('WorkOrderId')" in fk.find(NAME, "Set_variable_WorkOrderId")["inputs"]["value"]
    assert "body('Call_header')?['objectId']" in fk.find(NAME, "Set_variable_ObjectId")["inputs"]["value"]
    for action, uri in WOE_CALLS.items():
        call = fk.find(NAME, action)
        assert call["inputs"]["uri"] == uri, action
        assert call["runAfter"] == {"Header_found": ALL + ["Skipped"]}, action
        assert call["inputs"]["headers"]["x-apikey"] == "@parameters('%s')" % WOE_KEY, action
        assert "body('Get_token')?['access_token']" in call["inputs"]["headers"]["Authorization"]
        assert call["runtimeConfiguration"]["secureData"]["properties"] == ["inputs"]


def test_object_id_defaults_to_or_plus_twelve_digits():
    """Attachments og status slaas op paa ordrens objektnummer, fx
    OR000026436811 for ordre 26436811, naar headeren ikke giver det."""
    init = fk.find(NAME, "Initialize_variable_ObjectId")["inputs"]["variables"][0]["value"]
    assert fk.evaluate(init, trigger={"text": " 26436811 "}) == "OR000026436811"
    assert fk.evaluate(init, trigger={"text": "25711067"}) == "OR000025711067"


def test_sap_utility_is_optional_and_tolerant():
    cfg = fk.find(NAME, "SapUtility_configured")
    assert cfg["runAfter"] == {name: ALL for name in WOE_CALLS}
    text = str(cfg["expression"])
    assert SU_SECRET in text and SU_KEY in text
    assert fk.find(NAME, "Set_variable_Attachments_not_configured")["inputs"]["name"] == "Attachments"
    att = fk.find(NAME, "Call_attachments")
    assert att["inputs"]["uri"] == SU + "/attachments/" + OBJ
    assert att["inputs"]["headers"]["x-apikey"] == "@parameters('%s')" % SU_KEY
    assert "body('Get_token_saputility')?['access_token']" in att["inputs"]["headers"]["Authorization"]
    loop = fk.find(NAME, "For_each_operation")
    assert loop["foreach"] == "@body('Call_operations')"
    assert loop["runtimeConfiguration"]["concurrency"]["repetitions"] == 1
    assert fk.find(NAME, "Operations_found")["expression"] == \
        {"and": [{"equals": ["@outputs('Call_operations')?['statusCode']", 200]}]}
    txt = fk.find(NAME, "Call_operation_text")
    assert txt["inputs"]["uri"] == \
        SU + "/descriptions/@{encodeUriComponent(outputs('Compose_operation_object_id'))}/OperationText"
    app = fk.find(NAME, "Append_operation_text")
    assert app["runAfter"] == {"Call_operation_text": ALL}
    assert set(app["inputs"]["value"]) == {"objectId", "operation", "status", "data"}


def test_app_always_gets_the_same_answer_shape():
    for r in ("Respond_missing_value", "Respond_result", "Respond_token_error"):
        a = fk.find(NAME, r)
        assert a["kind"] == "PowerApp", r
        assert list(a["inputs"]["body"]) == SHAPE, r
        assert list(a["inputs"]["schema"]["properties"]) == SHAPE, r
    result = fk.find(NAME, "Result")
    assert result["runAfter"] == {"SapUtility_configured": ALL + ["Skipped"]}
    assert list(result["inputs"]) == ["orderNumber", "workOrderId", "objectId"] + SECTIONS + \
        ["attachments", "operationTexts"]
    for s in SECTIONS:
        assert list(result["inputs"][s]) == ["status", "data"], s
    resp = fk.find(NAME, "Respond_result")
    assert resp["runAfter"] == {"Result": ["Succeeded"]}
    assert resp["inputs"]["body"]["result"] == "@{string(outputs('Result'))}"
    assert "Call_header" in resp["inputs"]["body"]["ok"]


def test_missing_values_answer_the_app_and_stop():
    text = str(fk.find(NAME, "Check_environment_variables")["expression"]["or"])
    for p in (SECRET, WOE_KEY):
        assert text.count(p) == 2, p
    assert SU_KEY not in text  # SAP Utility er valgfri: flowet stopper ikke uden den
    assert fk.find(NAME, "Respond_missing_value")["inputs"]["body"]["ok"] == "no"
    assert fk.find(NAME, "Stop_missing_value")["runAfter"] == {"Respond_missing_value": ["Succeeded"]}
