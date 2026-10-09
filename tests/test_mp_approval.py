# -*- coding: utf-8 -*-
"""
Measuring Points godkendelse af nye Counter-raekker (issue #210, fase 4-6).

Godkendelsen staar bag flaget features.measuring_point_approval, og det er
SLUKKET i repoet. Den byggede skaerm i BIO SAP App viser derfor kun, at
intet har aendret sig. Delene bag flaget bygges her i en egen proces med
flaget taendt (domain_config og domain_parts kan ikke importeres i samme
proces som de andre domaeneapps - tre moduler hedder domain_config).

    python3 -m pytest tests/test_mp_approval.py
"""
import json
import os
import re
import subprocess
import sys

import pytest

from conftest import ROOT

APP = os.path.join(ROOT, "BIO SAP App")
MP = os.path.join(APP, "ScreenMeasuringPoint.pa.yaml")

# Bygger Measuring Point-skaermen (enkeltskaermen, praefiks Dom) med flaget
# taendt og skriver YAML'en paa stdout.
_BUILD = r'''
import os, sys
root = sys.argv[1]
sys.path.insert(0, os.path.join(root, "tools"))
import env_config as env
env.FEATURES["measuring_point_approval"] = True
sys.path.insert(0, os.path.join(root, "Measuring Point App", "build"))
import assemble_screen
from gen_screen import render_screen
sys.stdout.write(assemble_screen.build_screen(render_screen))
'''


@pytest.fixture(scope="module")
def on():
    out = subprocess.run([sys.executable, "-c", _BUILD, ROOT], cwd=ROOT,
                         capture_output=True, text=True, encoding="utf-8")
    assert out.returncode == 0, out.stderr[-2000:]
    return out.stdout


def _off():
    return open(MP, encoding="utf-8").read()


def _features():
    cfg = json.load(open(os.path.join(ROOT, "tools", "canvas_apps.json"), encoding="utf-8"))
    return cfg["environments"]["dev"]["features"]


# ---------------------------------------------------------------------------
# Flaget
# ---------------------------------------------------------------------------
def test_the_flag_is_off_by_default():
    assert _features()["measuring_point_approval"] is False


def test_without_the_flag_the_screen_works_as_before():
    """Slukket: intet opslag, ingen vagt, ingen stribe og intet flow - og
    Submit gaar direkte til Master Data (Q12), som i fase 1-3."""
    t = _off()
    assert "BioSap-Material-ResolveApprovers" not in t
    assert "BioSap-MeasuringPoint-Approval" not in t
    assert "imgMpSteps" not in t
    assert "colMpCreators" not in t
    assert 'Status: { Value: "KlarTilSAP" }' in t


# ---------------------------------------------------------------------------
# Valgkolonnerne i SharePoint (skema.md: Choice)
# ---------------------------------------------------------------------------
CHOICES = ("ExistsInSap", "MeasuringPointType", "InProdos", "ProdosCounterExists",
           "CounterCreateIn")


def test_choice_columns_are_written_as_records_and_read_as_value():
    """Kolonnerne er Choice i udtraekket. En tekst i Patch og Coalesce paa
    en valgrecord compiler ikke i Studio."""
    t = _off()
    for col in CHOICES:
        assert f"{col}: Coalesce(R.{col}.Value, \"\")" in t, col
        assert f"Coalesce(R.{col}, \"\")" not in t, col
        assert re.search(r"%s: (If\([^\n]*)?If\(IsBlank\(Trim\(Coalesce\(varMpF%s, \"\"\)\)\), "
                         r"Blank\(\), \{ Value: Trim\(varMpF%s\) \}\)" % (col, col, col), t), col


def test_the_choice_columns_are_choice_in_the_schema():
    schema = json.load(open(os.path.join(ROOT, "sharepoint", "inspect", "out", "schema.json"),
                            encoding="utf-8-sig"))
    lst, = [l for l in schema["lists"] if l["title"] == "MeasuringPointItems"]
    types = {f.get("displayName"): f.get("type") for f in lst["fields"]}
    for col in CHOICES:
        assert types[col] == "Choice", col


def test_equipment_and_materials_keep_their_text_columns():
    for name in ("ScreenEquipment", "ScreenMaterial"):
        t = open(os.path.join(APP, name + ".pa.yaml"), encoding="utf-8").read()
        assert "{ Value: Trim(var" not in t, name


# ---------------------------------------------------------------------------
# Vagten foer Submit (fase 4)
# ---------------------------------------------------------------------------
def _submit(t):
    """Submit-knappens OnSelect i den byggede skaerm."""
    i = t.index("btnDomSubmit:")
    j = t.index("OnSelect:", i)
    return t[j:t.index("Text:", j)]


def test_submit_looks_up_the_system_manager_only_for_new_counters(on):
    fx = _submit(on)
    assert ("'BioSap-Material-ResolveApprovers'.Run(Concat(Filter(colDomRows, "
            'Status = "valid" && Coalesce(ApprovalRequired, false)), '
            'FunctionalLocation, "; "))') in fx
    # Ingen raekker at slaa op -> intet kald.
    assert '!IsBlank(Trim(Coalesce(Concat(' in fx


def test_submit_looks_up_the_prodos_creator_per_plant(on):
    fx = _submit(on)
    assert 'LookUp(MD_Approver, ApproverKey = "PRODOS-" & P.Value)' in fx
    # Eet opslag pr. vaerk - kun for raekker, hvis taeller mangler.
    assert ('Distinct(Filter(colDomRows, Status = "valid" && MeasuringPointType = '
            '"Counter" && ExistsInSap = "No" && InProdos = "Yes" && '
            'ProdosCounterExists = "No"), Upper(Left(Trim(Coalesce(Plant, "")), 3)))') in fx
    # Fravaerende 1. godkender -> 2. godkender, som i flowene.
    assert "If(a.Approver1Absent, a.Approver2, a.Approver1)" in fx


def test_a_missing_manager_or_creator_stops_the_confirmation(on):
    fx = _submit(on)
    # Spaerret -> en besked; ellers aabner bekraeftelsen.
    assert fx.index("Notify(If(") < fx.index("Set(varDomConfirmSubmit, true)")
    for msg in ('"Cannot submit: " & First(Filter(colDomApprovers',
                '"Cannot submit: no PRODOS/SRO creator is configured for plant " & '
                'First(Filter(colDomCreators, IsBlank(Creator))).Plant & "."',
                '"Could not look up the system managers: "'):
        assert msg in fx, msg


def test_the_resolver_error_names_the_system():
    """Beskeden kommer fra flowet: "No System Manager is configured for
    system 8" - appen tilfoejer kun "Cannot submit: " og et punktum."""
    path, = [p for p in os.listdir(os.path.join(ROOT, "solution", "BIOSAP", "src", "Workflows"))
             if p.startswith("BioSap-Material-ResolveApprovers-") and p.endswith(".json")]
    txt = open(os.path.join(ROOT, "solution", "BIOSAP", "src", "Workflows", path),
               encoding="utf-8-sig").read()
    assert "No System Manager is configured for system " in txt


def test_the_collections_are_declared_only_with_the_flag():
    t = _off()
    assert "colMpApprovers" not in t and "colMpCreators" not in t


# ---------------------------------------------------------------------------
# Trinstriben (fase 4) - tools/stepper.py fra #204
# ---------------------------------------------------------------------------
def test_the_strip_has_the_same_four_nodes_before_and_after_submit(on):
    assert "imgDomSteps" in on and "txtDomStepsHint" in on
    for before, after in (('"Rows"', '"Submitted"'), ('"Approvers"', '"Approval"'),
                          ('"PRODOS / SRO"', '"PRODOS / SRO counter"'),
                          ('"Ready to submit"', '"Master Data (SAP)"')):
        assert before in on and after in on, before
    assert '"Created in SAP"' in on


def test_steps_that_do_not_apply_say_not_required(on):
    # Ingen ny Counter -> Approvers springes over; ingen manglende taeller
    # -> PRODOS / SRO springes over. Stribens "Skipped" er "Not required".
    assert ('CountRows(Filter(colDomRows, Status = "valid" && '
            'Coalesce(ApprovalRequired, false))) = 0, "Skipped"') in on
    assert ('CountRows(Filter(colDomRows, Status = "valid" && MeasuringPointType = "Counter" '
            '&& ExistsInSap = "No" && InProdos = "Yes" && ProdosCounterExists = "No")) = 0, '
            '"Skipped"') in on
    assert '"Not required"' in on


def test_after_submit_is_the_open_request_not_any_old_row(on):
    """colDomRows er ALLE brugerens raekker. "Efter Submit" maa kun vaere
    den aabne anmodning - ellers stod striben fast i "Submitted", saa
    snart brugeren havde indsendt een gang."""
    assert "varDomIdx.RequestGuid = varDomRequestGuid" in on
    assert 'Filter(colDomRows, Status = "submitted")' not in on.split("imgDomSteps")[1][:20000]


def test_the_hint_says_what_submit_would_say(on):
    for msg in ("Add a row and save it to get started.",
                "Finish the draft row before submitting.",
                "New counters are approved by the System Manager.",
                "The request is with Master Data for creation in SAP."):
        assert msg in on, msg


def test_the_hub_and_the_screen_agree_on_the_stage_names():
    """Striben laeser stadiet af LastActionBy, som flowet skriver."""
    src = open(os.path.join(ROOT, "Measuring Point App", "build", "mp_parts.py"),
               encoding="utf-8").read()
    assert 'COUNTER_ACTOR = "PRODOS/SRO counter"' in src
    assert 'APPROVAL_ACTOR = "System approval"' in src


# ---------------------------------------------------------------------------
# FLOWET BioSap-MeasuringPoint-Approval (fase 5)
#
# Flowet kan ikke koeres her. Testene laeser dets JSON og koerer de udtryk,
# der afgoer udfaldet, med tests/wdl_eval.py - samme metode som
# test_material_approval.py.
# ---------------------------------------------------------------------------
import glob

import wdl_eval

SRC = os.path.join(ROOT, "solution", "BIOSAP", "src")
FLOWS = os.path.join(SRC, "Workflows")
FLOW = "BioSap-MeasuringPoint-Approval"
SVC = {
    "shared_sharepointonline": "orsted_BioSapSharePointConn",
    "shared_powerbi": "orsted_BioSapPowerBIConn",
    "shared_approvals": "orsted_BioSapApprovalsConn",
    "shared_office365": "orsted_BioSapOutlookConn",
}


def _path():
    path, = glob.glob(os.path.join(FLOWS, FLOW + "-*.json"))
    return path


def _flow():
    return json.load(open(_path(), encoding="utf-8-sig"))


def _definition():
    return _flow()["properties"]["definition"]


def _actions(acts):
    for name, a in acts.items():
        yield name, a
        if "actions" in a:
            yield from _actions(a["actions"])
        if "else" in a:
            yield from _actions(a["else"].get("actions", {}))


def _find(action):
    for n, a in _actions(_definition()["actions"]):
        if n == action:
            return a
    raise AssertionError("handlingen %s findes ikke" % action)


def _op(a):
    inputs = a.get("inputs")
    return inputs.get("host", {}).get("operationId") if isinstance(inputs, dict) else None


def _params(a):
    inputs = a.get("inputs")
    return inputs.get("parameters", {}) if isinstance(inputs, dict) else {}


def _writes(table, op):
    return [_params(a) for _n, a in _actions(_definition()["actions"])
            if _params(a).get("table") == table and _op(a) == op]


def _run(names, given):
    """Koer handlingerne names efter de givne outputs (navn -> vaerdi)."""
    acts = {n: {"type": "Compose", "inputs": v} for n, v in given.items()}
    for n in names:
        acts[n] = _find(n)
    return wdl_eval.run(acts, list(given) + names, {}, {}).outputs


def _row(key, typ="Counter", exists="No", prodos="Yes", ctr="No", status="submitted",
         approval=None, created=None, plant="SSV", fl="SSV13 HFC10AJ010"):
    ch = lambda v: {"Value": v} if v is not None else None
    return {"ID": int(key[-1]), "ItemKey": key, "Title": "Pump " + key, "Plant": plant,
            "FunctionalLocation": fl, "RowStatus": ch(status),
            "MeasuringPointType": ch(typ), "ExistsInSap": ch(exists),
            "InProdos": ch(prodos), "ProdosCounterExists": ch(ctr),
            "ApprovalRequired": (typ == "Counter" and exists == "No") if approval is None
            else approval, "CounterCreatedOn": created, "Characteristic": "RUNNING_HOURS",
            "CharacteristicUnit": "H", "DecimalPlaces": 0, "ExpectedAnnualUsage": 8000,
            "ProdosTag": "TAG1", "CounterCreateIn": ch("PRODOS")}


def test_the_flow_runs_as_the_service_account():
    refs = _flow()["properties"]["connectionReferences"]
    assert sorted(refs) == sorted(SVC)
    for api, ref in refs.items():
        assert ref["runtimeSource"] == "embedded", api
        assert ref["connection"]["connectionReferenceLogicalName"] == SVC[api], api


def test_the_flow_is_in_the_solution():
    xml = open(os.path.join(SRC, "Other", "Solution.xml"), encoding="utf-8-sig").read()
    ids = set(re.findall(r'<RootComponent type="29" id="\{([^}]+)\}"', xml))
    guid = os.path.basename(_path())[len(FLOW) + 1:-5].lower()
    assert guid in ids
    data = open(_path() + ".data.xml", encoding="utf-8-sig").read()
    assert 'Name="%s"' % FLOW in data and guid in data
    cust = open(os.path.join(SRC, "Other", "Customizations.xml"), encoding="utf-8-sig").read()
    have = set(re.findall(r'connectionreferencelogicalname="([^"]+)"', cust))
    assert set(SVC.values()) <= have


def test_the_app_is_answered_before_the_approval_starts():
    acts = _definition()["actions"]
    assert acts["Respond_accepted"]["kind"] == "PowerApp"
    assert "Respond_accepted" in acts["Try"]["runAfter"]
    trig = _definition()["triggers"]["manual"]["inputs"]["schema"]["properties"]["text"]
    assert trig["title"] == "RequestGuid"


def test_only_submitted_new_counters_are_approved():
    """Q1/Q16: kun NYE Counter-raekker. En eksisterende Counter, et
    Measuring Point og en kladderaekke med anmodningens GUID er ikke med."""
    rows = [_row("MP-1"),                                   # ny Counter -> godkendes
            _row("MP-2", exists="Yes"),                     # findes -> registreres
            _row("MP-3", typ="MeasuringPoint", prodos="No", ctr=None),
            _row("MP-4", status="draft")]                   # ikke sendt med
    out = _run(["Submitted_rows", "Approval_rows"], {"Get_rows": {"body/value": rows}})
    assert [r["ItemKey"] for r in out["Approval_rows"]] == ["MP-1"]


def test_a_counter_missing_in_prodos_is_found_from_the_choice_values():
    rows = [_row("MP-1"),                                   # mangler -> opretter
            _row("MP-2", ctr="Yes"),                        # findes i PRODOS
            _row("MP-3", prodos="No", ctr=None),            # ikke i PRODOS
            _row("MP-4", exists="Yes"),                     # eksisterende punkt
            _row("MP-5", status="draft")]
    out = _run(["Submitted_rows", "Counter_rows"], {"Get_rows": {"body/value": rows}})
    assert [r["ItemKey"] for r in out["Counter_rows"]] == ["MP-1"]


def test_the_system_number_loses_its_leading_zeros():
    for raw, want in (("00123", "123"), ("0123", "123"), ("123", "123"), (None, "")):
        out = _run(["SysNoRaw", "SysNo"],
                   {"Filter_FL_rows": [{"[SystemNo]": raw}] if raw is not None else []})
        assert out["SysNo"] == want, raw


def test_the_unit_is_the_row_and_its_system():
    guid = _find("Append_resolved")["inputs"]["value"]["itemGuid"]
    assert "'#'" in guid and "outputs('SysNo')" in guid and "ItemKey" in guid


def test_the_fingerprint_is_the_content_not_what_comes_after_approval():
    fp = _find("FingerprintRaw")["inputs"]
    for field in ("Title", "Characteristic", "CharacteristicUnit", "DecimalPlaces",
                  "ExpectedAnnualUsage", "ProdosTag", "ProdosCounterExists"):
        assert field in fp, field
    full = json.dumps(_definition())
    # Nummeret fra SAP og taellerens oprettelse kommer EFTER godkendelsen.
    assert "CreatedMeasuringPointNo" not in full
    assert "CounterCreatedBy" not in fp and "CounterCreatedOn" not in fp
    # Og det passer i tekstkolonnen.
    assert "240" in _find("Fingerprint")["inputs"]


def test_the_fingerprint_can_be_computed_for_a_row():
    acts = {"For_each_row": {"type": "Compose", "inputs": _row("MP-1")},
            "FL": {"type": "Compose", "inputs": "SSV13 HFC10AJ010"},
            "SysNo": {"type": "Compose", "inputs": "8"}}
    a = dict(_find("FingerprintRaw"))
    a["inputs"] = a["inputs"].replace("items('For_each_row')", "outputs('For_each_row')")
    acts["FingerprintRaw"] = a
    out = wdl_eval.run(acts, ["For_each_row", "FL", "SysNo", "FingerprintRaw"], {}, {}).outputs
    assert out["FingerprintRaw"] == "8|SSV13 HFC10AJ010|PUMP MP-1|RUNNING_HOURS|H|0|8000|TAG1|NO|PRODOS"


def test_an_approved_unit_is_not_asked_again():
    prev = _find("Filter_prev_rows")["inputs"]["where"]
    assert "'Approve'" in prev and "outputs('Fingerprint')" in prev
    assert "'done'" in _find("My_units")["inputs"]["where"]


def test_each_approver_gets_one_task_for_all_their_rows():
    assert _find("Approver_list")["inputs"].startswith("@union(")
    task = _find("Start_and_wait_for_an_approval")
    p = task["inputs"]["parameters"]
    assert p["WebhookApprovalCreationInput/responseOptions"] == ["Approve", "Return"]
    assert "join(body('My_lines')" in p["WebhookApprovalCreationInput/details"]
    assert task["limit"]["timeout"] == "P14D"


def test_only_this_runs_returns_send_the_request_back():
    """En Return fra en TIDLIGERE indsendelse er rettet. Talte den med,
    blev en genindsendt anmodning sendt tilbage igen og igen."""
    log = [{"Decision": "Return", "Title": "old-run"},
           {"Decision": "Approve", "Title": "this-run"}]
    out = _run(["Return_rows"], {"RunName": "this-run",
                                 "Get_log_results": {"body/value": log}})
    assert out["Return_rows"] == []
    log.append({"Decision": "Return", "Title": "this-run"})
    out = _run(["Return_rows"], {"RunName": "this-run",
                                 "Get_log_results": {"body/value": log}})
    assert len(out["Return_rows"]) == 1


def test_a_request_that_no_longer_needs_approval_is_closed_as_skipped():
    log = [{"Decision": "Requested", "ItemGuid": "MP-1#8"},
           {"Decision": "Requested", "ItemGuid": "MP-2#8"},
           {"Decision": "Requested", "ItemGuid": "MP-3#8"},
           {"Decision": "Skipped", "ItemGuid": "MP-3#8"}]
    # Resolved er en variabel - her givet direkte som Select_unit_guids.
    out = wdl_eval.run(
        {"Select_unit_guids": {"type": "Compose", "inputs": ["MP-1#8"]},
         "Get_log": {"type": "Compose", "inputs": {"body/value": log}},
         "Skipped_guids": _find("Skipped_guids"),
         "Stale_requests": _find("Stale_requests")},
        ["Select_unit_guids", "Get_log", "Skipped_guids", "Stale_requests"], {}, {}).outputs
    assert [r["ItemGuid"] for r in out["Stale_requests"]] == ["MP-2#8"]


def test_a_counter_that_is_no_longer_missing_is_closed_as_skipped():
    log = [{"Decision": "Requested", "ItemGuid": "MP-1#counter"},
           {"Decision": "Requested", "ItemGuid": "MP-2#counter"},
           {"Decision": "Requested", "ItemGuid": "MP-3#counter"},
           {"Decision": "Done", "ItemGuid": "MP-3#counter"}]
    out = wdl_eval.run(
        {"Select_counter_guids": {"type": "Compose", "inputs": ["MP-1#counter"]},
         "Get_counter_log": {"type": "Compose", "inputs": {"body/value": log}},
         "Closed_counter_guids": _find("Closed_counter_guids"),
         "Stale_counters": _find("Stale_counters")},
        ["Select_counter_guids", "Get_counter_log", "Closed_counter_guids",
         "Stale_counters"], {}, {}).outputs
    assert [r["ItemGuid"] for r in out["Stale_counters"]] == ["MP-2#counter"]


def test_the_prodos_creator_is_the_plants_row_in_md_approver():
    approvers = [{"Title": "PRODOS-SSV", "Approver1": "abc", "Approver2": "xyz",
                  "Approver1Absent": False},
                 {"Title": "PRODOS-AVV", "Approver1": "abc", "Approver2": "xyz",
                  "Approver1Absent": True},
                 {"Title": "8", "Approver1": "sys", "Approver2": "", "Approver1Absent": False}]
    names = ["Plant_code", "Filter_creator_rows", "Creator_initials"]

    def creator(plant):
        acts = {"For_each_counter_row": {"type": "Compose", "inputs": {"Plant": plant}},
                "Get_approvers": {"type": "Compose", "inputs": {"body/value": approvers}}}
        for n in names:
            a = json.loads(json.dumps(_find(n)).replace(
                "items('For_each_counter_row')", "outputs('For_each_counter_row')"))
            acts[n] = a
        return wdl_eval.run(acts, ["For_each_counter_row", "Get_approvers"] + names,
                            {}, {}).outputs["Creator_initials"]

    assert creator("SSV") == "abc"
    assert creator(" ssv ") == "abc"
    assert creator("AVV") == "xyz"          # 1. godkender fravaerende
    assert creator("HEV") == ""             # ingen raekke for vaerket
    email = _find("Creator_email")["inputs"]
    assert "parameters(' BioSap-EmailDomain (orsted_BioSapEmailDomain)')" in email


def test_a_counter_is_requested_once_and_only_while_it_is_missing():
    counters = [{"itemGuid": "MP-1#counter", "known": False, "open": True},
                {"itemGuid": "MP-2#counter", "known": True, "open": True},
                {"itemGuid": "MP-3#counter", "known": False, "open": False}]
    out = wdl_eval.run({"New_counters": {
        "type": "Query", "inputs": {"from": counters,
                                    "where": _find("New_counters")["inputs"]["where"]}}},
        ["New_counters"], {}, {}).outputs
    assert [c["itemGuid"] for c in out["New_counters"]] == ["MP-1#counter"]
    guid = _find("Counter_guid")["inputs"]
    assert "'#counter'" in guid


def test_every_log_row_is_system_or_counter_with_no_plan_id():
    posts = _writes("MD_ApprovalLog", "PostItem")
    assert posts
    for p in posts:
        assert p["item/Stage"] in ("System", "Counter"), p["item/Stage"]
        # PlanId er VH-planens - stod den her, talte planens trin MP med.
        assert "item/PlanId" not in p
        assert p["item/RequestGuid"] == "@outputs('RequestGuid')"
        assert p["item/Title"] == "@outputs('RunName')"
        assert p["item/Decision"] in ("Approve", "Return", "Requested", "Skipped")
    counter = {p["item/Decision"] for p in posts if p["item/Stage"] == "Counter"}
    # "Done" skriver appen, naar opretteren markerer i Details.
    assert counter == {"Requested", "Skipped"}


def test_the_status_moves_as_q12_and_the_counter_step_say():
    idx = {}
    for p in _writes("MD_RequestIndex", "PatchItem"):
        idx.setdefault(p["item/Status/Value"], []).append(p)
    assert set(idx) == {"UnderBehandling", "AfventerInfo", "KlarTilSAP"}
    by = {p["item/LastActionBy"] for p in idx["UnderBehandling"]}
    # Appens trinstribe laeser stadiet af LastActionBy.
    assert by == {"System approval", "PRODOS/SRO counter"}
    assert idx["KlarTilSAP"][0]["item/StatusStep"] == 4
    assert idx["AfventerInfo"][0]["item/StatusStep"] == 3
    rows, = _writes("MeasuringPointItems", "PatchItem")
    assert rows["item/RowStatus/Value"] == "valid"


def test_the_counter_rows_are_read_again_after_the_approval():
    """En godkendelse kan tage dage; opretteren kan have markeret en taeller
    i mellemtiden."""
    get = _find("Get_rows_now")
    assert _params(get)["table"] == "MeasuringPointItems"
    assert "CounterCreatedOn" in _find("Open_counters_now")["inputs"]["where"]


def test_the_mails_come_from_the_service_account():
    mails = [(n, a) for n, a in _actions(_definition()["actions"]) if _op(a) == "SendEmailV2"]
    names = {n for n, _a in mails}
    assert names == {"Send_returned_mail", "Send_counter_mail", "Send_approved_mail",
                     "Send_notification_to_development_team"}
    for _n, m in mails:
        assert m["inputs"]["host"]["connectionName"] == "shared_office365"
    assert _params(_find("Send_counter_mail"))["emailMessage/To"] == "@items('For_each_creator')"
    assert "Mark counter created" in _params(_find("Send_counter_mail"))["emailMessage/Body"]


def test_an_error_notifies_the_development_team():
    acts = _definition()["actions"]
    assert set(acts["Catch"]["runAfter"]["Try"]) == {"TimedOut", "Skipped", "Failed"}


# ---------------------------------------------------------------------------
# Appen og flowet (fase 5) - med flaget taendt
# ---------------------------------------------------------------------------
def test_with_the_flag_submit_starts_the_flow_and_the_flow_sets_the_status(on):
    assert "'BioSap-MeasuringPoint-Approval'.Run(varDomRequestGuid)" in on
    assert 'Status: { Value: "Indsendt" }' in on
    assert 'Status: { Value: "KlarTilSAP" }' in on      # kun i taellerens knap
    assert "The request was submitted, but the approval could not be started" in on


def test_the_creator_marks_the_counter_in_details(on):
    assert "btnDomDetCtrDone" in on and '"Mark counter created"' in on
    # Kun opretteren for raekkens vaerk - eller en admin.
    assert ('LookUp(MD_Approver, ApproverKey = "PRODOS-" & '
            'Upper(Left(Trim(Coalesce(r.Plant, "")), 3)))') in on
    assert "(IsAdmin || varDomCtrMay)" in on
    for frag in ("CounterCreatedOn: Now(), CounterCreatedBy: Lower(User().Email)",
                 'Stage: "Counter"', 'Decision: "Done"', 'ItemGuid: varDomCtrRow.ItemKey & "#counter"'):
        assert frag in on, frag


def test_the_last_counter_hands_the_request_to_master_data(on):
    i = on.index("btnDomDetCtrDone:")
    j = on.index("OnSelect:", i)
    fx = on[j:re.search(r"\n {0,%d}\w+:" % (j - on.rindex("\n", 0, j) - 1), on[j + 9:]).start() + j + 9]
    assert ('varDomCtrIdx.Status.Value = "UnderBehandling"' in fx and
            'Coalesce(varDomCtrIdx.LastActionBy, "") = "PRODOS/SRO counter"' in fx)
    assert 'Status: { Value: "KlarTilSAP" }' in fx
