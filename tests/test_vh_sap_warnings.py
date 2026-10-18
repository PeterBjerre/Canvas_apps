# -*- coding: utf-8 -*-
"""
SAP-kvitteringens advarsler og afviste kvitteringer (R2-018).

Opretteren skriver i kvitteringen, hvad den ikke kunne oprette (fx
materialer, der skal tilfoejes i IA06), men intet flow laeste `warnings`,
og en Partial/NeedsCheck/Failed-kvittering gav kun en mail til udviklerne
med filnavnet. Nu:

  - BioSap-VhPlan-SapReceipt skriver advarslerne, een pr. linje, i den nye
    Note-kolonne MaintenancePlans.SapWarnings i samme MERGE, der saetter
    planen til Published.
  - Afvisningsmailen baerer kvitteringens og planens vaerdier, og Master
    Data er paa Cc, naar opretteren selv meldte Partial/NeedsCheck/Failed.
  - BioSap-EmailNotification-PlanPublished viser advarslerne under "To be
    added manually in SAP" og saetter Master Data paa Cc.

    python3 -m pytest -q tests/test_vh_sap_warnings.py
"""
import glob
import json
import os
import re

import pytest

from conftest import ROOT
import wdl_eval

FLOWS = os.path.join(ROOT, "solution", "BIOSAP", "src", "Workflows")
MD = "BioSap-MasterDataEmail (orsted_BioSapMasterDataEmail)"
MD_MAIL = "md@example.test"
DEV_MAIL = "dev@example.test"
PARAMS = {MD: MD_MAIL, "BioSap-ErrorNotifiers (orsted_BioSapErrorNotifiers)": DEV_MAIL,
          "BioSap-SapSystem (orsted_BioSapSapSystem)": "GQ1",
          "BioSap-SiteUrl (orsted_BioSapSiteUrl)": "https://example.test/teams/BioSAPDev"}


def _flow(name):
    path, = glob.glob(os.path.join(FLOWS, name + "-*.json"))
    return json.load(open(path, encoding="utf-8-sig"))["properties"]["definition"]


def _valid():
    d = _flow("BioSap-VhPlan-SapReceipt")
    h = d["actions"]["Try"]["actions"]["Each_receipt"]["actions"]["Handle_receipt"]["actions"]
    return h["Valid_receipt"]


def _published():
    return _flow("BioSap-EmailNotification-PlanPublished")["actions"]["Try"]["actions"]


@pytest.mark.parametrize("name", ["BioSap-VhPlan-SapReceipt",
                                  "BioSap-EmailNotification-PlanPublished"])
def test_the_master_data_parameter_is_the_solutions(name):
    p = _flow(name)["parameters"][MD]
    assert p["metadata"]["schemaName"] == "orsted_BioSapMasterDataEmail"
    assert os.path.isdir(os.path.join(ROOT, "solution", "BIOSAP", "src",
                                      "environmentvariabledefinitions",
                                      "orsted_BioSapMasterDataEmail"))
    other = _flow("BioSap-VhPlan-ToMasterData")["parameters"][MD]
    assert p == other


def test_sap_warnings_is_a_provisioned_plain_note():
    ps1 = open(os.path.join(ROOT, "sharepoint", "provision", "Provision-SapCreation.ps1"),
               encoding="utf-8-sig").read()
    assert "New-MdNoteField 'MaintenancePlans' 'SapWarnings'" in ps1
    common = open(os.path.join(ROOT, "sharepoint", "provision", "_Common.psm1"),
                  encoding="utf-8-sig").read()
    note = common[common.index("function New-MdNoteField"):]
    assert "RichText = $false" in note[:note.index("\n}")]


#==============================================================================
# Kvitteringsflowet skriver advarslerne
#==============================================================================
def _write_plan(warnings):
    v = _valid()
    acts = {"Receipt": {"type": "Compose", "inputs": {"sapPlanNo": "12345678", "lockedBy": "PKBJE",
                                                      "warnings": warnings}},
            "Warning_lines": v["actions"]["Warning_lines"],
            "Warnings_json": v["actions"]["Warnings_json"],
            "Body": {"type": "Compose",
                     "inputs": v["actions"]["Set_plan_published"]["inputs"]["parameters"]["parameters/body"]}}
    out = wdl_eval.run(acts, list(acts), {}, {}).outputs
    return json.loads(out["Body"])


def test_the_warnings_are_written_one_per_line():
    w = ['Material 4711 on operation 0020 - add in IA06',
         'Text with "quotes", a back\\slash and <b>tags</b>',
         'Two\r\nlines\tand a tab']
    body = _write_plan(w)
    assert body["Status"] == "Published" and body["SAPNum"] == "12345678"
    assert body["SapWarnings"].split("\n") == [
        w[0], w[1], "Two lines and a tab"]


@pytest.mark.parametrize("warnings", [None, []])
def test_no_warnings_clears_the_column(warnings):
    assert _write_plan(warnings)["SapWarnings"] == ""


def test_the_warnings_are_read_before_the_items():
    acts = _valid()["actions"]
    assert acts["Warning_lines"]["runAfter"] == {}
    assert acts["Warnings_json"]["runAfter"] == {"Warning_lines": ["Succeeded"]}
    assert acts["Each_item"]["runAfter"] == {"Warnings_json": ["Succeeded"]}
    assert acts["Set_plan_published"]["runAfter"] == {"Each_item": ["Succeeded"]}


#==============================================================================
# Afvisningsmailen
#==============================================================================
def _rejected(receipt, plan):
    p = _valid()["else"]["actions"]["Send_rejected_notification"]["inputs"]["parameters"]

    def fix(s):
        # items() og variables() kender wdl_eval ikke - de bliver til outputs().
        return (s.replace("items('Each_receipt')", "outputs('Each_receipt')")
                 .replace("variables('FlowRunHistoryLink')", "outputs('FlowRunHistoryLink')"))
    acts = {"Receipt": {"type": "Compose", "inputs": receipt},
            "Get_plan": {"type": "Compose", "inputs": plan},
            "Each_receipt": {"type": "Compose", "inputs": {"{FilenameWithExtension}": "MP0099.kvittering.json"}},
            "FlowRunHistoryLink": {"type": "Compose", "inputs": "RUN"}}
    for k in ("emailMessage/To", "emailMessage/Cc", "emailMessage/Subject", "emailMessage/Body"):
        acts[k] = {"type": "Compose", "inputs": fix(p[k])}
    return wdl_eval.run(acts, list(acts), {}, {}, parameters=PARAMS).outputs


PLAN = {"Status": {"Value": "Ready for creation in SAP"}, "SapOrderGuid": "g-plan"}


@pytest.mark.parametrize("state,cc", [
    ("Partial", MD_MAIL), ("NeedsCheck", MD_MAIL), ("Failed", MD_MAIL),
    ("Created", ""), ("InProgress", ""), (None, ""),
])
def test_master_data_is_told_about_incomplete_runs(state, cc):
    out = _rejected({"state": state, "planId": "MP0099"}, PLAN)
    assert out["emailMessage/Cc"] == cc
    assert out["emailMessage/To"] == DEV_MAIL


def test_the_rejection_says_why():
    receipt = {"state": "NeedsCheck", "planId": "MP0099", "sapSystem": "GQ1", "orderGuid": "g-receipt",
               "sapPlanNo": None, "lastError": "IP42 <stopped> & saved nothing",
               "warnings": ["Material 4711 - add in IA06"]}
    out = _rejected(receipt, PLAN)
    body = out["emailMessage/Body"]
    for text in ("NeedsCheck", "MP0099", "GQ1", "g-receipt", "g-plan", "Ready for creation in SAP",
                 "IP42 &lt;stopped&gt; &amp; saved nothing", "Material 4711 - add in IA06",
                 "MP0099.kvittering.json", "RUN"):
        assert text in body, text
    assert "<stopped>" not in body
    assert out["emailMessage/Subject"].startswith("Maintenance plan creator: receipt rejected (NeedsCheck)")


#==============================================================================
# Mailen "Created in SAP" viser dem
#==============================================================================
PLAN_ROW = {"ID": 7, "PlanID": "MP0099", "SAPNum": "12345678", "Title": "Pump",
            "PlantsInitial/Value": "SSV", "PlannedDate": "2026-01-31T23:00:00Z", "Cycle": 6,
            "Unit/Value": "MON", "SapCreatedOn": "2026-10-18T08:30:00Z",
            "Author/DisplayName": "Ann", "Author/Email": "ann@example.test",
            "Editor/Email": "svc@example.test"}


def _mail(warnings):
    t = _published()
    plan = dict(PLAN_ROW, SapWarnings=warnings)
    acts = {"Get_request_index": {"type": "Compose", "inputs": {"body/value": []}},
            "Compose-EmailContent": t["Compose-EmailContent"],
            "Cc": {"type": "Compose",
                   "inputs": t["Send_an_email_(V2)-EmailRequestor"]["inputs"]["parameters"]["emailMessage/Cc"]}}
    out = wdl_eval.run(acts, list(acts), plan, {}, parameters=PARAMS).outputs
    return out["Compose-EmailContent"], out["Cc"]


def test_the_mail_lists_what_to_add_manually():
    html, cc = _mail("Material 4711 on operation 0020 - add in IA06\r\nText <b>&</b>")
    assert "To be added manually in SAP" in html
    assert ("<li>Material 4711 on operation 0020 - add in IA06</li>"
            "<li>Text &lt;b&gt;&amp;&lt;/b&gt;</li>") in html
    assert "Master Data adds what is listed" in html
    # R2-048: servicekontoen (Editor) er ikke laengere paa Cc.
    assert cc == MD_MAIL


@pytest.mark.parametrize("warnings", [None, "", "  \n "])
def test_without_warnings_the_section_is_gone(warnings):
    html, cc = _mail(warnings)
    assert "To be added manually in SAP" not in html
    assert "<li>" not in html
    assert "Nothing more is needed from you." in html
    assert cc == ""
