# -*- coding: utf-8 -*-
"""
Materials' systemgodkendelse (issue #204): de to flows.

Flowene kan ikke koeres her, saa testene laeser deres JSON og koerer de
udtryk, der afgoer udfaldet, med tests/wdl_eval.py - samme metode som
test_feedback_mail.py.

    python3 -m pytest tests/test_material_approval.py
"""
import glob
import json
import os
import re

from conftest import ROOT
import wdl_eval

SRC = os.path.join(ROOT, "solution", "BIOSAP", "src")
FLOWS = os.path.join(SRC, "Workflows")
RESOLVE = "BioSap-Material-ResolveApprovers"
APPROVAL = "BioSap-Material-SystemApproval"
# Servicekontoens forbindelser - aldrig brugerens egne.
SVC = {
    "shared_sharepointonline": "orsted_BioSapSharePointConn",
    "shared_powerbi": "orsted_BioSapPowerBIConn",
    "shared_approvals": "orsted_BioSapApprovalsConn",
    "shared_office365": "orsted_BioSapOutlookConn",
}


def _path(name):
    path, = glob.glob(os.path.join(FLOWS, name + "-*.json"))
    return path


def _flow(name):
    return json.load(open(_path(name), encoding="utf-8-sig"))


def _definition(name):
    return _flow(name)["properties"]["definition"]


def _actions(acts):
    """Alle handlinger, ogsaa dem i scopes, loekker og If-grene."""
    for name, a in acts.items():
        yield name, a
        if "actions" in a:
            yield from _actions(a["actions"])
        if "else" in a:
            yield from _actions(a["else"].get("actions", {}))


def _find(name, action):
    for n, a in _actions(_definition(name)["actions"]):
        if n == action:
            return a
    raise AssertionError("handlingen %s findes ikke i %s" % (action, name))


def _op(action):
    """Handlingens operationId - en Compose har ingen."""
    inputs = action.get("inputs")
    if not isinstance(inputs, dict):
        return None
    return inputs.get("host", {}).get("operationId")


def _params(action):
    inputs = action.get("inputs")
    return inputs.get("parameters", {}) if isinstance(inputs, dict) else {}


def _posts(name, table):
    out = []
    for _n, a in _actions(_definition(name)["actions"]):
        p = _params(a)
        if p.get("table") == table and _op(a) == "PostItem":
            out.append(p)
    return out


def _patches(name, table):
    out = []
    for _n, a in _actions(_definition(name)["actions"]):
        p = _params(a)
        if p.get("table") == table and _op(a) == "PatchItem":
            out.append(p)
    return out


# ---------------------------------------------------------------------------
# Forbindelser og registrering
# ---------------------------------------------------------------------------
def test_both_flows_run_as_the_service_account():
    for name, apis in ((RESOLVE, ["shared_powerbi", "shared_sharepointonline"]),
                       (APPROVAL, ["shared_approvals", "shared_office365",
                                   "shared_powerbi", "shared_sharepointonline"])):
        refs = _flow(name)["properties"]["connectionReferences"]
        assert sorted(refs) == apis, name
        for api, ref in refs.items():
            assert ref["runtimeSource"] == "embedded", (name, api)
            assert ref["connection"]["connectionReferenceLogicalName"] == SVC[api], (name, api)


def test_both_flows_are_in_the_solution():
    xml = open(os.path.join(SRC, "Other", "Solution.xml"), encoding="utf-8-sig").read()
    ids = set(re.findall(r'<RootComponent type="29" id="\{([^}]+)\}"', xml))
    for name in (RESOLVE, APPROVAL):
        guid = os.path.basename(_path(name))[len(name) + 1:-5].lower()
        assert guid in ids, name
        # Hver flow har sin data.xml - uden den importeres den ikke.
        assert os.path.exists(_path(name) + ".data.xml"), name


def test_the_connection_references_exist_in_the_solution():
    xml = open(os.path.join(SRC, "Other", "Customizations.xml"), encoding="utf-8-sig").read()
    have = set(re.findall(r'connectionreferencelogicalname="([^"]+)"', xml))
    for name in (RESOLVE, APPROVAL):
        for ref in _flow(name)["properties"]["connectionReferences"].values():
            assert ref["connection"]["connectionReferenceLogicalName"] in have, name


# ---------------------------------------------------------------------------
# Systemnummeret
# ---------------------------------------------------------------------------
def _sysno(flow, raw):
    """Koer SysNoRaw og SysNo paa et traef fra Power BI."""
    acts = {
        "Filter_FL_rows": {"type": "Compose",
                           "inputs": [{"[SystemNo]": raw}] if raw is not None else []},
        "SysNoRaw": _find(flow, "SysNoRaw"),
        "SysNo": _find(flow, "SysNo"),
    }
    return wdl_eval.run(acts, ["Filter_FL_rows", "SysNoRaw", "SysNo"], {}, {}).outputs["SysNo"]


def test_leading_zeros_are_stripped_from_the_system_number():
    # MD_Approver's Title er skrevet UDEN foranstillede nuller, mens Power
    # BI svarer med dem. Uden det her matcher opslaget aldrig.
    for flow in (RESOLVE, APPROVAL):
        assert _sysno(flow, "00123") == "123", flow
        assert _sysno(flow, "0123") == "123", flow
        assert _sysno(flow, "123") == "123", flow
        assert _sysno(flow, " 123 ") == "123", flow
        assert _sysno(flow, None) == "", flow


# ---------------------------------------------------------------------------
# ResolveApprovers: hvem og hvorfor ikke
# ---------------------------------------------------------------------------
def _resolve_case(fl, rows, approvers):
    acts = {
        "For_each_code": {"inputs": fl},
        "FL": {"inputs": "@trim(coalesce(outputs('For_each_code'), ''))"},
        "Run_a_query_against_a_dataset": {"inputs": {"body/firstTableRows": rows}},
        "Get_approvers": {"inputs": {"body/value": approvers}},
    }
    names = ["For_each_code", "FL", "Run_a_query_against_a_dataset", "Get_approvers"]
    for n in ("Filter_FL_rows", "SysNoRaw", "SysNo", "Filter_approver_rows",
              "Initials", "Error"):
        a = dict(_find(RESOLVE, n))
        # items('For_each_code') er loekkens element - her en Compose.
        a["inputs"] = json.loads(json.dumps(a["inputs"]).replace(
            "items('For_each_code')", "outputs('For_each_code')"))
        acts[n] = a
        names.append(n)
    return wdl_eval.run(acts, names, {}, {}).outputs


def test_an_unknown_functional_location_says_no_system():
    out = _resolve_case("SSV13 HFC10AJ010", [], [])
    assert out["SysNo"] == ""
    assert out["Error"] == "No system found for SSV13 HFC10AJ010"


def test_a_system_without_a_manager_says_so():
    out = _resolve_case("SSV13 HFC10AJ010",
                        [{"[FL]": "SSV13 HFC10AJ010", "[SystemNo]": "00123"}], [])
    assert out["SysNo"] == "123"
    assert out["Error"] == "No System Manager is configured for system 123"


def test_the_first_approver_is_used_unless_absent():
    rows = [{"[FL]": "SSV13 HFC10AJ010", "[SystemNo]": "00123"}]
    out = _resolve_case("SSV13 HFC10AJ010", rows,
                        [{"Title": "123", "Approver1": "abc", "Approver2": "xyz",
                          "Approver1Absent": False}])
    assert out["Initials"] == "abc" and out["Error"] == ""
    out = _resolve_case("SSV13 HFC10AJ010", rows,
                        [{"Title": "123", "Approver1": "abc", "Approver2": "xyz",
                          "Approver1Absent": True}])
    assert out["Initials"] == "xyz"


def test_an_empty_code_is_an_error_not_a_lookup():
    out = _resolve_case("   ", [], [])
    assert out["Error"] == "No functional location"


def test_the_app_gets_one_json_string_back():
    resp = _find(RESOLVE, "Respond_to_a_Power_App_or_flow")
    assert resp["kind"] == "PowerApp"
    assert list(resp["inputs"]["body"]) == ["resolveoutput"]
    props = resp["inputs"]["schema"]["properties"]["resolveoutput"]
    assert props["type"] == "string" and props["x-ms-dynamically-added"] is True


# ---------------------------------------------------------------------------
# SystemApproval: enheden, fingerprintet og udfaldet
# ---------------------------------------------------------------------------
def test_the_app_is_answered_before_the_approval_starts():
    # En godkendelse kan tage dage. Svarede flowet foerst bagefter, stod
    # brugeren med en spinner indtil da.
    acts = _definition(APPROVAL)["actions"]
    assert acts["Respond_accepted"]["kind"] == "PowerApp"
    assert "Respond_accepted" in acts["Try"]["runAfter"]


def test_the_unit_is_one_row_per_system():
    # Flere objekter i SAMME system paa samme raekke er EEN enhed.
    unit = _find(APPROVAL, "New_system")
    assert unit["expression"]["and"][1]["not"]["contains"] == [
        "@variables('RowSystems')", "@outputs('SysNo')"]
    append = _find(APPROVAL, "Append_unit")["inputs"]["value"]
    assert append["sysNo"] == "@outputs('SysNo')"
    # Enhedens noegle er raekke + system.
    guid = _find(APPROVAL, "Append_resolved")["inputs"]["value"]["itemGuid"]
    assert "'#'" in guid and "sysNo" in guid


def test_the_fingerprint_is_the_content_not_the_sap_number():
    fp = _find(APPROVAL, "Append_unit")["inputs"]["value"]["fingerprint"]
    for field in ("ObjectList", "Title", "StrategicPart"):
        assert field in fp, field
    # Created material no. findes foerst EFTER godkendelsen (Q16). Stod den
    # i fingerprintet, ville den starte godkendelsen forfra.
    assert "CreatedMaterialNo" not in fp
    full = json.dumps(_definition(APPROVAL))
    assert "CreatedMaterialNo" not in full


def test_the_fingerprint_fits_the_text_column():
    # MD_ApprovalLog.Fingerprint er et tekstfelt - 255 tegn.
    fx = _find(APPROVAL, "Fingerprint")["inputs"]
    assert "240" in fx and "substring" in fx


def test_an_approved_unit_is_not_asked_again():
    prev = _find(APPROVAL, "Filter_prev_rows")["inputs"]["where"]
    assert "'Approve'" in prev and "outputs('Fingerprint')" in prev
    done = _find(APPROVAL, "Append_resolved")["inputs"]["value"]["done"]
    assert done == "@greater(length(body('Filter_prev_rows')), 0)"
    mine = _find(APPROVAL, "My_units")["inputs"]["where"]
    assert "'done'" in mine


def test_each_approver_gets_one_task_for_all_their_rows():
    # Godkenderlisten er de FORSKELLIGE adresser (union med sig selv).
    assert _find(APPROVAL, "Approver_list")["inputs"].startswith("@union(")
    loop = _find(APPROVAL, "For_each_approver")
    assert loop["runtimeConfiguration"]["concurrency"]["repetitions"] > 1
    task = _find(APPROVAL, "Start_and_wait_for_an_approval")["inputs"]["parameters"]
    assert task["WebhookApprovalCreationInput/responseOptions"] == ["Approve", "Return"]
    assert task["approvalType"] == "CustomResponse"
    assert "join(body('My_lines')" in task["WebhookApprovalCreationInput/details"]


def test_the_approval_times_out_after_fourteen_days():
    assert _find(APPROVAL, "Start_and_wait_for_an_approval")["limit"]["timeout"] == "P14D"


def test_the_approver_email_is_initials_plus_the_domain_parameter():
    acts = {
        "Initials": {"inputs": "abc"},
        "Approver_email": _find(APPROVAL, "Approver_email"),
    }
    fx = acts["Approver_email"]["inputs"]
    # Domaenet er en miljoevariabel, ikke en konstant i flowet.
    assert "parameters(' BioSap-EmailDomain (orsted_BioSapEmailDomain)')" in fx
    assert fx.startswith("@if(empty(outputs('Initials')), ''")


def test_every_log_row_is_the_system_stage_with_no_plan_id():
    posts = _posts(APPROVAL, "MD_ApprovalLog")
    assert len(posts) >= 4
    for p in posts:
        assert p["item/Stage"] == "System"
        # PlanId er VH-planens. Stod den her, ville planens taellinger
        # tage Materials' raekker med.
        assert "item/PlanId" not in p
        assert p["item/RequestGuid"] == "@outputs('RequestGuid')"
        assert p["item/Decision"] in ("Approve", "Return", "Requested")


def test_an_open_unit_is_logged_as_requested_so_progress_can_be_counted():
    req = [p for p in _posts(APPROVAL, "MD_ApprovalLog")
           if p["item/Decision"] == "Requested"]
    assert len(req) == 1
    assert req[0]["item/ItemGuid"] == "@items('For_each_open_unit')?['itemGuid']"


def test_a_return_unlocks_the_rows_and_asks_the_requester():
    idx = {p["item/Status/Value"]: p for p in _patches(APPROVAL, "MD_RequestIndex")}
    assert set(idx) == {"UnderBehandling", "Indsendt", "AfventerInfo"}
    assert idx["AfventerInfo"]["item/StatusStep"] == 4
    assert idx["Indsendt"]["item/StatusStep"] == 2
    for p in idx.values():
        assert p["item/LastActionBy"] == "System approval"
    rows, = _patches(APPROVAL, "MaterialItems")
    assert rows["item/RowStatus/Value"] == "valid"


def test_only_the_rows_that_need_approval_are_asked_about():
    where = _find(APPROVAL, "Strategic_rows")["inputs"]["where"]
    assert where == "@equals(item()?['ApprovalRequired'], true)"


def test_the_mails_come_from_the_service_account():
    mails = [a for _n, a in _actions(_definition(APPROVAL)["actions"])
             if _op(a) == "SendEmailV2"]
    # Rekvirenten faar baade et nej og et ja - og udviklerne en fejl.
    assert len(mails) == 3
    for m in mails:
        assert m["inputs"]["host"]["connectionName"] == "shared_office365"


def test_an_error_notifies_the_development_team():
    acts = _definition(APPROVAL)["actions"]
    assert set(acts["Catch"]["runAfter"]["Try"]) == {"TimedOut", "Skipped", "Failed"}
    notify = _find(APPROVAL, "Send_notification_to_development_team")
    assert notify["inputs"]["parameters"]["emailMessage/To"] == \
        "@parameters('BioSap-ErrorNotifiers (orsted_BioSapErrorNotifiers)')"
