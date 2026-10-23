# -*- coding: utf-8 -*-
"""
App-flowene til API-gatewayen i DEV (docs/44): BioSap-Integration-WoeOrderObjects
og BioSap-Integration-MaterialStock. Hvert flow henter sit eget token med
client credentials og kalder sit endpoint med x-apikey.

    python3 -m pytest -q tests/test_dev_api_flows.py

Repoet er offentligt. Secret og noegler skal derfor komme fra
miljoevariabler, og appen skal altid faa et svar (ok/status/message/result).
"""
import os

import flowkit as fk

SECRET = "BioSap-WOC-Client-Secret (orsted_BioSapWOCClientSecret)"
FLOWS = {
    "BioSap-Integration-WoeOrderObjects": {
        "id": "5d1e8a43-7c2f-4b90-9e36-a84f0c27b1d5",
        "key": "BioSap-WOE-Dev-ApiKey (orsted_BioSapWoeDevApiKey)",
        "scope": "/b6608a78-4d04-462b-a5da-d5488f8b164c/.default",
        "base": "https://dev.api.orsted.dk/woe/api",
        "inputs": ["OrderNumber"],
        "path": "/workorders/@{encodeUriComponent(trim(triggerBody()?['text']))}/objects",
    },
    "BioSap-Integration-MaterialStock": {
        "id": "b7a4c1e9-2d6f-4e83-a51b-6f09d3c82e47",
        "key": "BioSap-Inventory-Dev-ApiKey (orsted_BioSapInventoryDevApiKey)",
        "scope": "/70b9b214-2a2b-41ed-a9e2-aa639525d063/.default",
        "base": "https://dev.api.orsted.dk/inventorymanagement",
        "inputs": ["Plant", "Material"],
        "path": "/materialonstocks/@{encodeUriComponent(trim(triggerBody()?['text']))}"
                "/@{encodeUriComponent(trim(triggerBody()?['text_1']))}",
    },
}
RESPONSES = ("Respond_missing_value", "Respond_result", "Respond_token_error")


def test_flows_are_in_the_solution():
    solution = open(os.path.join(fk.FLOWS, "..", "Other", "Solution.xml"), encoding="utf-8-sig").read()
    for name, f in FLOWS.items():
        assert "{%s}" % f["id"] in solution, name
        assert os.path.exists(fk.path(name) + ".data.xml"), name
        assert fk.flow(name)["properties"]["connectionReferences"] == {}, name
    assert "8e2f4c71" not in solution  # testflowet er afloest af de to


def test_power_apps_trigger_inputs():
    for name, f in FLOWS.items():
        trig = fk.definition(name)["triggers"]["manual"]
        assert trig["kind"] == "PowerAppV2"
        props = trig["inputs"]["schema"]["properties"]
        assert [p["title"] for p in props.values()] == f["inputs"]
        assert trig["inputs"]["schema"]["required"] == list(props)


def test_setup_token_and_call():
    for name, f in FLOWS.items():
        s = fk.find(name, "Setup")["inputs"]
        assert s["clientId"] == "6b699286-72e8-4e8a-8e93-ce166f5c22d0"
        assert s["tokenUrl"].endswith("/100b3c99-f3e2-4da0-9c8a-b9d345742c36/oauth2/v2.0/token")
        assert s["scope"].endswith(f["scope"])
        assert s["baseUrl"] == f["base"]
        tok = fk.find(name, "Get_token")
        assert "client_secret=@{parameters('%s')}" % SECRET in tok["inputs"]["body"]
        assert tok["runtimeConfiguration"]["secureData"]["properties"] == ["inputs", "outputs"]
        call = fk.find(name, "Call_API")
        assert call["inputs"]["uri"] == "@{outputs('Setup')?['baseUrl']}" + f["path"]
        assert call["inputs"]["headers"]["x-apikey"] == "@parameters('%s')" % f["key"]
        assert "body('Get_token')?['access_token']" in call["inputs"]["headers"]["Authorization"]
        assert call["runtimeConfiguration"]["secureData"]["properties"] == ["inputs"]


def test_app_always_gets_the_same_answer_shape():
    for name in FLOWS:
        for r in RESPONSES:
            a = fk.find(name, r)
            assert a["kind"] == "PowerApp", (name, r)
            assert list(a["inputs"]["body"]) == ["ok", "status", "message", "result"], (name, r)
            assert list(a["inputs"]["schema"]["properties"]) == ["ok", "status", "message", "result"]
        assert fk.find(name, "Respond_result")["runAfter"] == {"Call_API": ["Succeeded", "Failed", "TimedOut"]}


def test_missing_values_answer_the_app_and_stop():
    for name, f in FLOWS.items():
        text = str(fk.find(name, "Check_environment_variables")["expression"]["or"])
        for p in (SECRET, f["key"]):
            assert text.count(p) == 2, (name, p)
        assert fk.find(name, "Respond_missing_value")["inputs"]["body"]["ok"] == "no"
        assert fk.find(name, "Stop_missing_value")["runAfter"] == {"Respond_missing_value": ["Succeeded"]}
