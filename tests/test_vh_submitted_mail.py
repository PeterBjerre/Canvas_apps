# -*- coding: utf-8 -*-
"""
R2-085: NewPlanCreated ("submitted for approval") - fodnotens tid i dansk
tid, "-" i stedet for "- years", knappen falder tilbage paa sitet uden
indeksraekke, og en tom PlannedDate faar ikke mailen til at fejle.
SharePoint-datoer kan mangle "Z"; de tolkes som UTC.

R2-052: fodnotens postkasse er miljoevariablen BioSap-MasterDataEmail.

    python3 -m pytest tests/test_vh_submitted_mail.py
"""
import flowkit as fk
import wdl_eval

NAME = "BioSap-EmailNotification-NewPlanCreated"
SITE = "BioSap-SiteUrl (orsted_BioSapSiteUrl)"
MD = "BioSap-MasterDataEmail (orsted_BioSapMasterDataEmail)"
PARAMS = {SITE: "https://sp.example.test/sites/bio", MD: "box@example.test"}
PLAN = {"ID": 7, "PlanID": "MP0099", "Title": "Pump", "PlantsInitial/Value": "SSV",
        "PlannedDate": "2026-01-31T23:00:00Z", "Cycle": 6, "Unit/Value": "MON",
        "StrategyKey": "IP41", "SchedulingPeriod": 2, "SortField/Value": "Pumps",
        "Author/DisplayName": "Ann", "Author/Email": "ann@example.test",
        "Status/Value": "In Progress", "ApprovalStage/Value": "System"}
INDEX = {"Title": "VH-0042", "RequesterName": "Rita", "RequesterEmail": "rita@example.test",
         "LastActionOn": "2026-10-18T08:30:00", "AppUrl": "https://apps.example.test/x"}


def _render(plan, rows, edit_link=""):
    d = fk.definition(NAME)
    compose = fk.find(NAME, "Compose-EmailContent", d)
    # wdl_eval kender ikke variables(); EditLink gives som et output.
    html = compose["inputs"].replace("variables('EditLink')", "outputs('EditLink')")
    acts = {
        "Get_AppUrl_based_on_environment": {"type": "Compose", "inputs": {"body/value": rows}},
        "Get_items_MaintenanceItems": {"type": "Compose", "inputs": {"body/value": []}},
        "Get_items_TaskListMain": {"type": "Compose", "inputs": {"body/value": []}},
        "Select_item_rows": fk.find(NAME, "Select_item_rows", d),
        "Select_op_rows": fk.find(NAME, "Select_op_rows", d),
        "Total_work": {"type": "Compose", "inputs": 0},
        "EditLink": {"type": "Compose", "inputs": edit_link},
        "Compose-EmailContent": {"type": "Compose", "inputs": html},
    }
    return wdl_eval.run(acts, list(acts), plan, {}, parameters=PARAMS).outputs["Compose-EmailContent"]


def test_footer_time_is_danish_even_without_z():
    html = _render(PLAN, [INDEX], INDEX["AppUrl"])
    assert "submitted 18-10-2026 10:30." in html


def test_dates_and_period():
    html = _render(PLAN, [INDEX], INDEX["AppUrl"])
    assert ">01-02-2026<" in html
    assert ">2 years<" in html
    html = _render(dict(PLAN, SchedulingPeriod=None, PlannedDate=None), [INDEX])
    assert "- years" not in html
    assert "years" not in html.split("Scheduling period")[1].split("</tr>")[0]


def test_button_falls_back_to_the_site():
    html = _render(PLAN, [], "")
    assert 'href="https://sp.example.test/sites/bio"' in html
    assert 'href=""' not in html
    html = _render(PLAN, [INDEX], INDEX["AppUrl"])
    assert 'href="https://apps.example.test/x"' in html


def test_footer_mailbox_is_the_environment_variable():
    html = _render(PLAN, [INDEX], INDEX["AppUrl"])
    assert "mailto:box@example.test" in html
    raw = fk.find(NAME, "Compose-EmailContent")["inputs"]
    assert "@orsted" not in raw
    assert fk.definition(NAME)["parameters"][MD]["metadata"]["schemaName"] == \
        "orsted_BioSapMasterDataEmail"
