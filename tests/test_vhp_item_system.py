# -*- coding: utf-8 -*-
"""
Itemets system paa VH-planen. Flowet BioSap-VhPlan-ItemSystem slaar
systemet op i Power BI i baggrunden, naar et item er gemt med en ny FL, og
skriver det i MaintenanceItems.SystemNo/SystemFL. Appen laeser kolonnerne
med itemet og viser systemet paa item-kortet - uden ekstra kald.

    python3 -m pytest tests/test_vhp_item_system.py
"""
import json
import os
import re

from conftest import ROOT
import flowkit as fk

FLOW = "BioSap-VhPlan-ItemSystem"
APPROVAL = "BioSap-VhPlan-SystemApproval"
SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenVhPlan.pa.yaml")
PROVISION = os.path.join(ROOT, "sharepoint", "provision", "Provision-VHPlanColumns.ps1")


def _trigger():
    return fk.definition(FLOW)["triggers"]["When_an_item_is_created_or_modified"]


def _condition(body):
    return fk.evaluate(_trigger()["conditions"][0]["expression"], trigger=body)


def test_trigger_watches_maintenance_items():
    p = _trigger()["inputs"]["parameters"]
    assert p["table"] == "@parameters('BioSap-List-MaintenanceItems (orsted_BioSapListMaintenanceItems)')"
    assert _trigger()["inputs"]["host"]["operationId"] == "GetOnUpdatedItems"


def test_runs_only_when_fl_differs_from_looked_up_fl():
    # Nyt item: intet slaaet op endnu.
    assert _condition({"FunctionalLocation": "ASV-1234", "SystemFL": None}) is True
    # FL'en er aendret siden opslaget.
    assert _condition({"FunctionalLocation": "ASV-9999", "SystemFL": "ASV-1234"}) is True
    # Flowets egen opdatering (og hvert Save draft uden ny FL) koerer ikke igen.
    assert _condition({"FunctionalLocation": "ASV-1234", "SystemFL": "ASV-1234"}) is False
    assert _condition({"FunctionalLocation": " asv-1234 ", "SystemFL": "ASV-1234"}) is False
    assert _condition({"FunctionalLocation": None, "SystemFL": None}) is False


def test_same_power_bi_lookup_as_the_approval_flow():
    q = fk.params(fk.find(FLOW, "Run_a_query_against_a_dataset"))
    a = fk.params(fk.find(APPROVAL, "Run_a_query_against_a_dataset"))
    for k in ("groupid", "datasetid"):
        assert q[k] == a[k]
    assert "'Functional Locations'[Plant Section Key]" in q["specification/query"]
    assert "'Functional Locations'[Plant Section Key]" in a["specification/query"]
    # Et anfoerselstegn i FL'en kan ikke bryde DAX-strengen.
    text = fk.evaluate(q["specification/query"], outputs={"FL": 'A"B'})
    assert '= "A""B")' in text


def test_system_number_is_normalised_like_the_approval_flow():
    mine = fk.find(FLOW, "SysNo")["inputs"]
    theirs = fk.find(APPROVAL, "SysNo")["inputs"]
    assert mine == theirs
    for raw, want in (("00123", "123"), ("0456", "456"), ("789", "789"), ("", "")):
        assert fk.evaluate(mine, outputs={"SysNoRaw": raw}) == want


def test_writes_system_and_the_fl_it_was_looked_up_for():
    body = fk.find(FLOW, "Body_system")["inputs"]
    assert body == {"SystemNo": "@outputs('SysNo')", "SystemFL": "@outputs('FL')"}
    assert fk.find(FLOW, "Body_clear")["inputs"] == {"SystemNo": "", "SystemFL": ""}
    for act in ("Set_item_system", "Clear_item_system"):
        p = fk.params(fk.find(FLOW, act))
        assert p["parameters/headers"]["X-HTTP-Method"] == "MERGE"
        assert "BioSap-List-MaintenanceItems" in p["parameters/uri"]
        assert "triggerBody()?['ID']" in p["parameters/uri"]


def test_flow_is_in_the_solution():
    path = fk.path(FLOW)
    guid = re.search(r"-([0-9A-F-]{36})\.json$", path).group(1).lower()
    sol = open(os.path.join(fk.FLOWS, "..", "Other", "Solution.xml"), encoding="utf-8-sig").read()
    assert '<RootComponent type="29" id="{%s}" behavior="0" />' % guid in sol
    assert os.path.exists(path + ".data.xml")


def test_columns_are_provisioned():
    ps = open(PROVISION, encoding="utf-8-sig").read()
    assert "New-MdField 'MaintenanceItems' 'SystemNo' Text" in ps
    assert "New-MdField 'MaintenanceItems' 'SystemFL' Text" in ps


def test_app_reads_the_columns_with_the_item_and_shows_them_on_the_card():
    y = open(SCREEN, encoding="utf-8").read()
    assert 'SystemNo: Coalesce(IT.SystemNo, "")' in y
    assert 'SystemFL: Coalesce(IT.SystemFL, "")' in y
    card = y[y.index("- txtVhpItemCardFl:"):]
    card = card[:card.index("Width:")]
    # Kun naar opslaget er lavet for itemets nuvaerende FL.
    assert "Upper(Trim(ThisItem.SystemFL)) = Upper(Trim(ThisItem.FunctionalLocation))" in card
    assert '"System " & ThisItem.SystemNo' in card
    # Ingen datakald paa kortet.
    assert "MaintenanceItems" not in card and ".Run(" not in card
    # Appen skriver aldrig systemet til SharePoint - det goer kun flowet.
    for v in re.findall(r"SystemNo:\s*([^,\n}]+)", y):
        assert v.startswith(("Coalesce(IT.", '""', "If(keepFl")), v
