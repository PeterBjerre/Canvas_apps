# -*- coding: utf-8 -*-
"""
Testflowet BioSap-Test-DevApis (docs/44): token via client credentials og
kald til WOE og inventory management i DEV.

    python3 -m pytest -q tests/test_dev_api_test.py

Repoet er offentligt. Secret og noegler skal derfor komme fra
miljoevariabler, og hvert API skal have sit eget scope.
"""
import os

import flowkit as fk

NAME = "BioSap-Test-DevApis"
SECRET = "BioSap-WOC-Client-Secret (orsted_BioSapWOCClientSecret)"
KEYS = {"Woe": "BioSap-WOE-Dev-ApiKey (orsted_BioSapWoeDevApiKey)",
        "Inventory": "BioSap-Inventory-Dev-ApiKey (orsted_BioSapInventoryDevApiKey)"}


def _a(action):
    return fk.find(NAME, action)


def test_flow_is_in_the_solution():
    solution = open(os.path.join(fk.FLOWS, "..", "Other", "Solution.xml"), encoding="utf-8-sig").read()
    assert "{8e2f4c71-5b3a-4d96-a1e7-3c0b9d6f2a58}" in solution
    assert fk.flow(NAME)["properties"]["connectionReferences"] == {}


def test_setup_has_endpoints_and_scopes():
    s = _a("Setup")["inputs"]
    assert s["clientId"] == "6b699286-72e8-4e8a-8e93-ce166f5c22d0"
    assert s["tokenUrl"].endswith("/100b3c99-f3e2-4da0-9c8a-b9d345742c36/oauth2/v2.0/token")
    assert s["woeScope"].endswith("/b6608a78-4d04-462b-a5da-d5488f8b164c/.default")
    assert s["inventoryScope"].endswith("/70b9b214-2a2b-41ed-a9e2-aa639525d063/.default")
    assert s["woeBaseUrl"] == "https://dev.api.orsted.dk/woe/api"
    assert s["inventoryBaseUrl"] == "https://dev.api.orsted.dk/inventorymanagement"


def test_each_api_gets_its_own_token_and_key():
    for tag, key in KEYS.items():
        tok = _a("Get_token_" + tag)
        assert "client_secret=@{parameters('%s')}" % SECRET in tok["inputs"]["body"]
        assert "['%sScope']" % tag.lower() in tok["inputs"]["body"]
        assert tok["runtimeConfiguration"]["secureData"]["properties"] == ["inputs", "outputs"]
        call = _a("Call_" + tag)
        assert call["inputs"]["headers"]["x-apikey"] == "@parameters('%s')" % key
        assert "body('Get_token_%s')?['access_token']" % tag in call["inputs"]["headers"]["Authorization"]
        assert call["runtimeConfiguration"]["secureData"]["properties"] == ["inputs"]


def test_paths():
    assert _a("Call_Woe")["inputs"]["uri"].endswith(
        "/workorders/@{encodeUriComponent(variables('Order'))}/objects")
    assert "/materialonstocks/@{encodeUriComponent(variables('Plant'))}/" \
           "@{encodeUriComponent(variables('Material'))}" in _a("Call_Inventory")["inputs"]["uri"]


def test_missing_values_stop_the_run():
    clauses = _a("Check_environment_variables")["expression"]["or"]
    text = str(clauses)
    for p in (SECRET,) + tuple(KEYS.values()):
        assert text.count(p) == 2, p
    assert _a("Stop_missing_value")["inputs"]["runStatus"] == "Failed"
