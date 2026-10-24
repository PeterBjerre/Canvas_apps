# -*- coding: utf-8 -*-
"""
BioSap-Integration-WoeOrder (docs/45): ET flow, der henter alt om en
SAP-ordre fra WOE-API'et, inventory og SAP Utility i een omgang. De ni
WOE-kald koerer parallelt paa ordrenummeret (Peter 2026-10-24: headeren
behoever ikke gaa foerst); inventory henter materialbevaegelserne; SAP
Utility attachments, HeaderText og OperationText + attachments pr. operation.

    python3 -m pytest -q tests/test_woe_order_flow.py

Repoet er offentligt. Secret og noegler kommer fra miljoevariabler - det
goer base-URL'erne ogsaa, for de skifter, naar solutionen flyttes til et
andet miljoe. Appen faar altid et svar (ok/status/message/result), ogsaa
naar et af kaldene giver 403, fordi API-teamet endnu ikke har aabnet
endpointet.
"""
import os

import flowkit as fk

NAME = "BioSap-Integration-WoeOrder"
FLOW_ID = "4a7e2c15-9b3d-4f68-a2c1-7d5e8b3f0c92"
SECRET = "BioSap-WOC-Client-Secret (orsted_BioSapWOCClientSecret)"
WOE_KEY = "BioSap-WOE-Dev-ApiKey (orsted_BioSapWoeDevApiKey)"
SU_KEY = "BioSap-SapUtility-Test-ApiKey (orsted_BioSapSapUtilityTestApiKey)"
INV_KEY = "BioSap-Inventory-Dev-ApiKey (orsted_BioSapInventoryDevApiKey)"
WOE_URL = "BioSap-WOE-BaseUrl (orsted_BioSapWoeBaseUrl)"
SU_URL = "BioSap-SapUtility-BaseUrl (orsted_BioSapSapUtilityBaseUrl)"
INV_URL = "BioSap-Inventory-BaseUrl (orsted_BioSapInventoryBaseUrl)"

WOE = "@{parameters('%s')}" % WOE_URL
SU = "@{parameters('%s')}" % SU_URL
INV = "@{parameters('%s')}" % INV_URL
ORDER = "@{encodeUriComponent(trim(triggerBody()?['text']))}"
OBJ = "@{encodeUriComponent(outputs('Compose_object_id'))}"

WOE_CALLS = {
    "Call_header": WOE + "/workorders/" + ORDER + "/header",
    "Call_operations": WOE + "/operations/" + ORDER,
    "Call_tasklistitems": WOE + "/operations/" + ORDER + "/tasklistitems",
    "Call_objects": WOE + "/workorders/" + ORDER + "/objects",
    "Call_status": WOE + "/workorders/" + OBJ + "/status",
    "Call_partner": WOE + "/workorders/" + ORDER + "/partner",
    "Call_activities": WOE + "/workorders/" + ORDER + "/activities",
    "Call_causes": WOE + "/workorders/" + ORDER + "/causes",
    "Call_feedback": WOE + "/workorders/" + ORDER + "/feedback",
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


def test_base_urls_come_from_environment_variables():
    """Peter 2026-10-24: base-URL'erne skifter, naar solutionen flyttes til et
    andet miljoe, saa de maa ikke staa i flowet."""
    s = fk.find(NAME, "Setup")["inputs"]
    assert not any("api.orsted.dk" in str(v) for v in s.values())
    for n, a, _p in fk.walk(fk.definition(NAME)["actions"]):
        if a.get("type") == "Http" and a["inputs"]["method"] == "GET":
            assert a["inputs"]["uri"].startswith("@{parameters('BioSap-"), n
            assert "BaseUrl" in a["inputs"]["uri"][:60], n
    params = fk.definition(NAME)["parameters"]
    for p in (WOE_URL, INV_URL, SU_URL):
        assert params[p]["defaultValue"] == "***REDACTED***", p


def test_one_app_registration_three_tokens():
    s = fk.find(NAME, "Setup")["inputs"]
    assert s["clientId"] == "6b699286-72e8-4e8a-8e93-ce166f5c22d0"
    assert s["woeScope"].endswith("/b6608a78-4d04-462b-a5da-d5488f8b164c/.default")
    assert s["inventoryScope"].endswith("/70b9b214-2a2b-41ed-a9e2-aa639525d063/.default")
    assert s["sapUtilityScope"].endswith("/9ab1e626-a2c7-4202-b325-398d6f68ee24/.default")
    for action, scope in (("Get_token", "woeScope"), ("Get_token_inventory", "inventoryScope"),
                          ("Get_token_saputility", "sapUtilityScope")):
        tok = fk.find(NAME, action)
        assert "client_id=@{encodeUriComponent(outputs('Setup')?['clientId'])}" in tok["inputs"]["body"]
        assert "client_secret=@{parameters('%s')}" % SECRET in tok["inputs"]["body"]
        assert "outputs('Setup')?['%s']" % scope in tok["inputs"]["body"]
        assert tok["runtimeConfiguration"]["secureData"]["properties"] == ["inputs", "outputs"]


def test_the_nine_woe_calls_run_in_parallel_on_the_order_number():
    for action, uri in WOE_CALLS.items():
        call = fk.find(NAME, action)
        assert call["inputs"]["uri"] == uri, action
        assert call["runAfter"] == {}, action
        assert call["inputs"]["headers"]["x-apikey"] == "@parameters('%s')" % WOE_KEY, action
        assert "body('Get_token')?['access_token']" in call["inputs"]["headers"]["Authorization"]
        assert call["runtimeConfiguration"]["secureData"]["properties"] == ["inputs"]
    assert "Header_found" not in str(fk.definition(NAME)["actions"])


def test_object_id_is_or_plus_twelve_digits():
    """Status, attachments og HeaderText slaas op paa ordrens objektnummer,
    fx OR000026436811 for ordre 26436811 (API-teamets eksempel)."""
    obj = fk.find(NAME, "Compose_object_id")["inputs"]
    assert fk.evaluate(obj, trigger={"text": " 26436811 "}) == "OR000026436811"
    assert fk.evaluate(obj, trigger={"text": "25711067"}) == "OR000025711067"


def test_sap_utility_is_optional_and_tolerant():
    cfg = fk.find(NAME, "SapUtility_configured")
    assert cfg["runAfter"] == {"Call_operations": ALL}  # kun loekken venter paa operationerne
    text = str(cfg["expression"])
    assert SU_KEY in text and SU_URL in text
    assert fk.find(NAME, "Set_variable_Attachments_not_configured")["inputs"]["name"] == "Attachments"
    att = fk.find(NAME, "Call_attachments")
    assert att["inputs"]["uri"] == SU + "/attachments/" + OBJ
    assert att["inputs"]["headers"]["x-apikey"] == "@parameters('%s')" % SU_KEY
    assert "body('Get_token_saputility')?['access_token']" in att["inputs"]["headers"]["Authorization"]
    # Ordrens langtekst (Peter 2026-10-24), parallelt med attachments.
    hdr = fk.find(NAME, "Call_header_text")
    assert hdr["inputs"]["uri"] == SU + "/descriptions/" + OBJ + "/HeaderText"
    assert hdr["runAfter"] == {}
    assert fk.find(NAME, "Set_variable_HeaderText")["runAfter"] == {"Call_header_text": ALL}
    loop = fk.find(NAME, "For_each_operation")
    assert loop["foreach"] == "@body('Call_operations')"
    assert loop["runtimeConfiguration"]["concurrency"]["repetitions"] == 1
    assert fk.find(NAME, "Operations_found")["expression"] == \
        {"and": [{"equals": ["@outputs('Call_operations')?['statusCode']", 200]}]}
    txt = fk.find(NAME, "Call_operation_text")
    assert txt["inputs"]["uri"] == \
        SU + "/descriptions/@{encodeUriComponent(outputs('Compose_operation_object_id'))}/OperationText"
    # Operationens egne vedhaeftninger (Peter 2026-10-24), parallelt med teksten.
    oatt = fk.find(NAME, "Call_operation_attachments")
    assert oatt["inputs"]["uri"] == \
        SU + "/attachments/@{encodeUriComponent(outputs('Compose_operation_object_id'))}"
    assert oatt["runAfter"] == {}
    assert oatt["inputs"]["headers"]["x-apikey"] == "@parameters('%s')" % SU_KEY
    app = fk.find(NAME, "Append_operation_text")
    assert app["runAfter"] == {"Call_operation_text": ALL, "Call_operation_attachments": ALL}
    assert set(app["inputs"]["value"]) == \
        {"objectId", "operation", "status", "data", "attachmentsStatus", "attachments"}


def test_material_movements_from_inventory_next_to_the_woe_calls():
    """Excels Raw_Ordre_Components: vareudtag og returer paa ordren. Eget token
    (inventory-scope, samme app-registrering), valgfri noegle og base-URL."""
    inv = fk.find(NAME, "Inventory_configured")
    assert inv["runAfter"] == {}
    text = str(inv["expression"])
    assert INV_KEY in text and INV_URL in text and SU_KEY not in text
    call = fk.find(NAME, "Call_movements")
    assert call["inputs"]["uri"] == INV + "/materialonstocks/movements/" + ORDER
    assert call["inputs"]["headers"]["x-apikey"] == "@parameters('%s')" % INV_KEY
    assert "body('Get_token_inventory')?['access_token']" in call["inputs"]["headers"]["Authorization"]
    assert fk.find(NAME, "Set_variable_Movements")["runAfter"] == {"Call_movements": ALL}
    assert fk.find(NAME, "Set_variable_Movements_not_configured")["inputs"]["name"] == "Movements"


def test_app_always_gets_the_same_answer_shape():
    for r in ("Respond_missing_value", "Respond_result", "Respond_token_error"):
        a = fk.find(NAME, r)
        assert a["kind"] == "PowerApp", r
        assert list(a["inputs"]["body"]) == SHAPE, r
        assert list(a["inputs"]["schema"]["properties"]) == SHAPE, r
    result = fk.find(NAME, "Result")
    expected = {name: ALL for name in WOE_CALLS}
    expected.update({"SapUtility_configured": ALL + ["Skipped"], "Inventory_configured": ALL + ["Skipped"]})
    assert result["runAfter"] == expected
    assert list(result["inputs"]) == ["orderNumber", "objectId", "maintenanceItem"] + \
        SECTIONS + ["headerText", "attachments", "movements", "operationTexts"]
    # Vedligeholdelsesposten (WAPOS) binder ordren til VH-planens item (Excel: IW33).
    assert "body('Call_header')?['maintenanceItem']" in result["inputs"]["maintenanceItem"]
    for s in SECTIONS:
        assert list(result["inputs"][s]) == ["status", "data"], s
    resp = fk.find(NAME, "Respond_result")
    assert resp["runAfter"] == {"Result": ["Succeeded"]}
    assert resp["inputs"]["body"]["result"] == "@{string(outputs('Result'))}"
    assert "Call_header" in resp["inputs"]["body"]["ok"]


def test_missing_values_answer_the_app_and_stop():
    text = str(fk.find(NAME, "Check_environment_variables")["expression"]["or"])
    for p in (SECRET, WOE_KEY, WOE_URL):
        assert text.count(p) == 2, p
    for p in (SU_KEY, SU_URL, INV_KEY, INV_URL):
        assert p not in text, p  # valgfri: flowet stopper ikke uden dem
    assert fk.find(NAME, "Respond_missing_value")["inputs"]["body"]["ok"] == "no"
    assert fk.find(NAME, "Stop_missing_value")["runAfter"] == {"Respond_missing_value": ["Succeeded"]}
