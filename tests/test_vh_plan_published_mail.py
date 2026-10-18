# -*- coding: utf-8 -*-
"""
Mailen "Oprettet i SAP" (R2-019): BioSap-EmailNotification-PlanPublished.

Flowet sendte den gamle 6-raekkers tabel uden SAP-nummer, uden link og med
en raa ISO-dato. Nu bruger det NewPlanCreateds skabelon (docs/17) med
succes-banneret, SAP-nummeret og en knap til appen, og alt fritekst
escapes. Spaerren (RequesterNotified), loggen og indeksopdateringen er
uaendrede.

    python3 -m pytest -q tests/test_vh_plan_published_mail.py
"""
import glob
import json
import os

import pytest

from conftest import ROOT
import wdl_eval

FLOWS = os.path.join(ROOT, "solution", "BIOSAP", "src", "Workflows")
SITE = "BioSap-SiteUrl (orsted_BioSapSiteUrl)"
SITE_URL = "https://example.test/teams/BioSAPDev"


def _definition(name):
    path, = glob.glob(os.path.join(FLOWS, name + "-*.json"))
    return json.load(open(path, encoding="utf-8-sig"))["properties"]["definition"]


def _scopes(acts, path="root"):
    """(sti, handlinger) for hvert niveau - runAfter peger kun inden for
    sit eget niveau."""
    yield path, acts
    for name, a in acts.items():
        if "actions" in a:
            yield from _scopes(a["actions"], name)
        if "else" in a:
            yield from _scopes(a["else"].get("actions", {}), name + "/else")


def _try():
    return _definition("BioSap-EmailNotification-PlanPublished")["actions"]["Try"]["actions"]


@pytest.mark.parametrize("name", ["BioSap-EmailNotification-PlanPublished",
                                  "BioSap-VhPlan-SapReceipt"])
def test_every_run_after_names_a_sibling(name):
    d = _definition(name)
    for path, acts in _scopes(d["actions"]):
        for a_name, a in acts.items():
            for dep in a.get("runAfter", {}):
                assert dep in acts, (path, a_name, dep)
        # Mindst een handling starter niveauet - ellers venter de alle paa
        # hinanden i ring, og intet koerer.
        roots = [n for n, a in acts.items() if not a.get("runAfter")]
        assert roots or not acts, path


def test_the_guard_and_the_order():
    d = _definition("BioSap-EmailNotification-PlanPublished")
    trigger, = d["triggers"].values()
    assert {"expression": "@not(equals(triggerBody()?['RequesterNotified'], true))"} \
        in trigger["conditions"]
    assert {"expression": "@not(empty(triggerBody()?['SAPNum']))"} in trigger["conditions"]
    t = _try()
    assert t["Get_request_index"]["runAfter"] == {}
    assert t["Compose-EmailContent"]["runAfter"] == {"Get_request_index": ["Succeeded"]}
    assert t["Send_an_email_(V2)-EmailRequestor"]["runAfter"] == \
        {"Compose-EmailContent": ["Succeeded"]}
    assert t["Set_requester_notified"]["runAfter"] == \
        {"Send_an_email_(V2)-EmailRequestor": ["Succeeded"]}
    assert t["RequestGuid"]["runAfter"] == {"Set_requester_notified": ["Succeeded"]}
    assert t["Log_sap_created"]["runAfter"] == {"RequestGuid": ["Succeeded"]}
    assert t["Index_published"]["runAfter"] == {"Log_sap_created": ["Succeeded"]}
    # Spaerren skrives stadig, og indekset faar SAP-nummeret.
    assert "\"RequesterNotified\": true" in \
        t["Set_requester_notified"]["inputs"]["parameters"]["parameters/body"]
    patch = t["Index_published"]["actions"]["Patch_index_published"]["inputs"]["parameters"]
    assert patch["item/SapObjectNo"] == "@triggerBody()?['SAPNum']"
    assert patch["item/Status"] == {"Value": "OprettetISAP"}


PLAN = {
    "ID": 7, "PlanID": "MP0099", "SAPNum": "12345678",
    "Title": "Pump <b>A</b> & B", "PlantsInitial/Value": "SSV",
    "PlannedDate": "2026-01-31T23:00:00Z", "Cycle": 6, "Unit/Value": "MON",
    "StrategyKey": "IP41", "SchedulingPeriod": 2, "SortField/Value": "Pumps & co",
    "SapCreatedBy": "PKBJE", "SapCreatedOn": "2026-10-18T08:30:00Z",
    "Author/DisplayName": "Ann Author", "Author/Email": "ann@example.test",
    "Status/Value": "Published",
}
INDEX = {"ID": 3, "Title": "VH-0042", "AppUrl": "https://apps.example.test/play?domain=vhplan&reqid=g-1",
         "RequesterName": "Rita Requester", "RequesterEmail": "rita@example.test"}


def _render(plan, index_rows):
    t = _try()
    acts = {"Get_request_index": {"type": "Compose", "inputs": {"body/value": index_rows}},
            "Compose-EmailContent": t["Compose-EmailContent"],
            "Subject": {"type": "Compose",
                        "inputs": t["Send_an_email_(V2)-EmailRequestor"]["inputs"]
                        ["parameters"]["emailMessage/Subject"]}}
    out = wdl_eval.run(acts, list(acts), plan, {}, parameters={SITE: SITE_URL}).outputs
    return out["Compose-EmailContent"], out["Subject"]


def test_the_mail_names_the_sap_plan_and_links_to_the_app():
    html, subject = _render(PLAN, [INDEX])
    assert subject == "Maintenance plan MP0099 created in SAP (12345678) - SSV"
    assert "SAP maintenance plan 12345678" in html
    assert "background-color:#e7f5ec;border-left:4px solid #2f855a" in html   # succes
    assert 'href="%s"' % INDEX["AppUrl"] in html
    assert "Open the plan in the app" in html
    # Dansk dato: midnat dansk tid er 23:00 UTC dagen foer.
    assert ">01-02-2026<" in html
    assert "2026-01-31T" not in html
    assert "created in SAP 18-10-2026 10:30" in html
    assert ">2 years<" in html
    assert ">- years<" not in _render(dict(PLAN, SchedulingPeriod=None), [INDEX])[0]
    assert "Rita Requester" in html and "mailto:rita@example.test" in html


def test_free_text_is_escaped():
    html, _ = _render(PLAN, [INDEX])
    assert "<b>A</b>" not in html
    assert "Pump &lt;b&gt;A&lt;/b&gt; &amp; B" in html
    assert "Pumps &amp; co" in html


def test_without_index_row_and_date_the_mail_still_renders():
    plan = dict(PLAN, PlannedDate=None)
    html, subject = _render(plan, [])
    assert 'href="%s"' % SITE_URL in html
    assert ">-<" in html
    assert "Ann Author" in html and "mailto:ann@example.test" in html
    assert "Request <strong style=\"color:#6b7b8c;\">MP0099</strong>" in html
    assert subject.endswith("(12345678) - SSV")
