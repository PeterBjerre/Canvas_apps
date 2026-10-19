# -*- coding: utf-8 -*-
"""
R2-021/R2-055/R2-057: FL-flowene C og D (docs/36 afsnit 5) ligger i
solutionen, og deres JSON er bygget af snippets i flow/sap-ordre/.

Snippets og skema tjekkes mod opretteren i test_sap_contract.py. Her
tjekkes, at flowene bruger snippets ordret, at kvitteringsflowet har
R2-057-opbygningen (Is created med en Partial-gren), og at de rigtige
mapper og miljoevariabler bruges. Udtrykkene koeres med tests/wdl_eval.py.

    python3 -m pytest tests/test_fl_sap_flows.py
"""
import json
import os
import re

from conftest import ROOT
import flowkit as fk
import request_index
import wdl_eval

ORDER = "BioSap-FL-SapOrder"
RECEIPT = "BioSap-FL-SapReceipt"
SNIP = os.path.join(ROOT, "flow", "sap-ordre")
REQ = "BioSap-List-FunctionalLocationRequests (orsted_BioSapListFunctionalLocationRequests)"
ITEMS = "BioSap-List-FunctionalLocationItems (orsted_BioSapListFunctionalLocationItems)"
SAP = "BioSap-SapSystem (orsted_BioSapSapSystem)"
SVC = {"shared_sharepointonline": "orsted_BioSapSharePointConn",
       "shared_office365": "orsted_BioSapOutlookConn"}
EV = os.path.join(fk.FLOWS, "..", "environmentvariabledefinitions")
OPEN = ("Indsendt", "UnderBehandling", "KlarTilSAP")


def _text(name):
    return open(os.path.join(SNIP, name), encoding="utf-8").read().strip()


def _json(name):
    return json.loads(_text(name))


def _body(snippet):
    """MERGE-body som i VH-flowene: snippet-vaerdierne ordret i teksten."""
    parts = []
    for k, v in _json(snippet).items():
        parts.append('"%s":%s' % (k, '"%s"' % v if isinstance(v, str) else json.dumps(v)))
    return "{" + ",".join(parts) + "}"


def _p(flow, action):
    return fk.params(fk.find(flow, action))


# ---------------------------------------------------------------------------
# Begge flows
# ---------------------------------------------------------------------------
def test_both_flows_are_in_the_solution():
    solution = open(os.path.join(fk.FLOWS, "..", "Other", "Solution.xml"), encoding="utf-8-sig").read()
    for name in (ORDER, RECEIPT):
        path = fk.path(name)
        gid = re.search(r"-([0-9A-F-]{36})\.json$", path).group(1)
        assert '<RootComponent type="29" id="{%s}"' % gid.lower() in solution, name
        xml = open(path + ".data.xml", encoding="utf-8-sig").read()
        assert 'WorkflowId="{%s}"' % gid.lower() in xml
        assert 'Name="%s"' % name in xml
        assert "<StateCode>1</StateCode>" in xml and "<StatusCode>2</StatusCode>" in xml


def test_service_connections_and_list_variables():
    for name in (ORDER, RECEIPT):
        refs = fk.flow(name)["properties"]["connectionReferences"]
        assert {k: v["connection"]["connectionReferenceLogicalName"] for k, v in refs.items()} == SVC
        params = fk.definition(name)["parameters"]
        for key in (REQ, ITEMS):
            schema = params[key]["metadata"]["schemaName"]
            assert os.path.isdir(os.path.join(EV, schema))
            xml = open(os.path.join(EV, schema, "environmentvariabledefinition.xml"), encoding="utf-8").read()
            assert "<type>100000004</type>" in xml and "<parameterkey>table</parameterkey>" in xml


def test_try_catch_mails_the_error_notifiers():
    for name in (ORDER, RECEIPT):
        d = fk.definition(name)
        assert d["actions"]["Catch"]["runAfter"] == {"Try": ["TimedOut", "Skipped", "Failed"]}
        p = _p(name, "Send_error_notification")
        assert p["emailMessage/To"] == "@parameters('BioSap-ErrorNotifiers (orsted_BioSapErrorNotifiers)')"
        assert "FlowRunHistoryLink" in p["emailMessage/Body"]


# ---------------------------------------------------------------------------
# Flow C
# ---------------------------------------------------------------------------
def test_order_trigger_is_the_snippet_with_concurrency_1():
    trig = fk.definition(ORDER)["triggers"]["When_an_item_is_created_or_modified"]
    assert trig["conditions"] == [{"expression": _text("fl-ordre-0-trigger.txt")}]
    assert trig["inputs"]["parameters"]["table"] == "@parameters('%s')" % REQ
    assert trig["runtimeConfiguration"]["concurrency"]["runs"] == 1


def test_order_condition_matches_the_trigger():
    expr = fk.find(ORDER, "Condition_New_Order")["expression"]["equals"]
    for status in OPEN + ("Kladde", "AfventerInfo", "Afvist", "Annulleret", "OprettetISAP"):
        got = fk.evaluate(expr[0], trigger={"Status": {"Value": status}})
        assert (got == expr[1]) == (status in OPEN), status


def test_order_select_and_compose_are_the_snippets():
    get = _p(ORDER, "Get_items_FunctionalLocationItems")
    assert get["table"] == "@parameters('%s')" % ITEMS
    assert get["$filter"] == "RequestGuid eq '@{triggerBody()?['RequestGuid']}'"
    assert get["$orderby"] == "RowNo" and get["$top"] == 5000
    sel = fk.find(ORDER, "Select_rows")["inputs"]
    assert sel["from"] == "@body('Get_items_FunctionalLocationItems')?['value']"
    assert sel["select"] == _json("fl-ordre-1-select-rows.json")
    assert fk.find(ORDER, "Compose_order")["inputs"] == _json("fl-ordre-2-compose-order.json")


def test_order_file_lands_where_the_creator_reads():
    p = _p(ORDER, "Create_file")
    assert p["folderPath"] == "/SAP-oprettelse/Til oprettelse"
    assert p["name"] == "@variables('OrderFile')"
    init = fk.find(ORDER, "Initialize_OrderFile")["inputs"]["variables"][0]["value"]
    assert init.startswith("@{concat(triggerBody()?['Title'], '_', ") and "'.json')" in init


def test_order_merges_are_the_snippets():
    uri = "_api/web/lists(guid'@{parameters('%s')}')/items(@{triggerBody()?['ID']})" % REQ
    for action, snippet in (("Set_SapOrderGuid", "fl-ordre-3-merge-request.json"),
                            ("Clear_SapOrderGuid", "fl-ordre-4-merge-request-reset.json")):
        p = _p(ORDER, action)
        assert p["parameters/uri"] == uri
        assert p["parameters/headers"]["X-HTTP-Method"] == "MERGE"
        assert p["parameters/body"] == _body(snippet)
    assert "Clear_SapOrderGuid" in fk.find(ORDER, "Condition_New_Order")["else"]["actions"]


# ---------------------------------------------------------------------------
# Flow D
# ---------------------------------------------------------------------------
def test_receipt_reads_the_fl_folder():
    assert _p(RECEIPT, "Get_files_(properties_only)")["folderPath"] == "/SAP-oprettelse/Kvitteringer/FL"
    assert fk.find(RECEIPT, "Receipt_files")["inputs"]["where"] == "@" + _text("kvittering-0-filter.txt")
    assert fk.find(RECEIPT, "Receipt")["inputs"] == "@" + _text("kvittering-1-compose.txt")
    assert fk.find(RECEIPT, "Each_receipt")["runtimeConfiguration"]["concurrency"]["repetitions"] == 1
    get = _p(RECEIPT, "Get_request")
    assert get["table"] == "@parameters('%s')" % REQ
    assert get["id"] == "@outputs('Receipt')?['requestSpId']"


def test_valid_receipt_is_the_snippet():
    cond = fk.find(RECEIPT, "Valid_receipt")["expression"]
    assert cond == {"equals": ["@" + _text("fl-kvittering-2-betingelse.txt"), True]}


def _valid(state="Created", name="FL-000012_20261003-081500.kvittering.json", status="UnderBehandling"):
    expr = fk.find(RECEIPT, "Valid_receipt")["expression"]["equals"][0]
    return fk.evaluate(expr, outputs={
        "Each_receipt": {"{FilenameWithExtension}": name},
        "Receipt": {"kind": "fl-sap-receipt", "state": state, "orderGuid": "g1", "sapSystem": "GQ1"},
        "Get_request": {"SapOrderGuid": "g1", "Status": {"Value": status}},
    }, parameters={SAP: "GQ1"})


def test_valid_receipt_accepts_created_and_partial_only():
    assert _valid("Created") is True
    assert _valid("Partial") is True
    assert _valid("Failed") is False
    assert _valid("InProgress") is False
    assert _valid(name="FL-000012_20261003-081500.kvittering-PC042.json") is False
    assert _valid(status="OprettetISAP") is False


def test_each_row_writes_the_row_result():
    each = fk.find(RECEIPT, "Each_row")
    assert each["foreach"] == "@outputs('Receipt')?['rows']"
    p = _p(RECEIPT, "Set_row_result")
    assert p["parameters/uri"] == \
        "_api/web/lists(guid'@{parameters('%s')}')/items(@{items('Each_row')?['spId']})" % ITEMS
    assert p["parameters/body"] == _body("fl-kvittering-3-merge-row.json")


def test_row_body_is_valid_json_for_awkward_errors():
    body = _p(RECEIPT, "Set_row_result")["parameters/body"]
    err = 'Field "Room" \\ too long\r\nsecond\tline' + "x" * 300
    out = fk.evaluate(body, outputs={"Each_row": {"done": False, "lastError": err}})
    got = json.loads(out)
    assert got["SapResult"] == "Failed"
    assert got["SapMessage"].startswith('Field "Room" \\ too long second line')
    assert len(got["SapMessage"]) <= 255
    ok = json.loads(fk.evaluate(body, outputs={"Each_row": {"done": True, "result": "Updated",
                                                            "sapMessage": "Saved"}}))
    assert ok == {"SapResult": "Updated", "SapMessage": "Saved"}


def test_is_created_and_partial_branches():
    valid = fk.find(RECEIPT, "Valid_receipt")
    is_created = valid["actions"]["Is_created"]
    assert is_created["runAfter"] == {"Each_row": ["Succeeded"]}
    assert is_created["expression"] == {"equals": ["@equals(outputs('Receipt')?['state'], 'Created')", True]}
    yes, no = is_created["actions"], is_created["else"]["actions"]
    assert {"Has_index_row", "Set_request_created", "Move_file_to_Behandlet",
            "Mail_rows", "Send_requester_email"} <= set(yes)
    assert {"Has_index_row_partial", "Set_request_in_progress",
            "Move_partial_file_to_Behandlet", "Send_partial_notification"} <= set(no)
    # Anmodningen lukkes efter raekkerne og landingssiden.
    assert yes["Set_request_created"]["runAfter"] == {"Has_index_row": ["Succeeded"]}
    assert yes["Move_file_to_Behandlet"]["runAfter"] == {"Set_request_created": ["Succeeded"]}
    assert yes["Mail_rows"]["runAfter"] == {"Move_file_to_Behandlet": ["Succeeded"]}


def test_created_branch_closes_request_and_index():
    req_uri = "_api/web/lists(guid'@{parameters('%s')}')/items(@{outputs('Receipt')?['requestSpId']})" % REQ
    idx_uri = "_api/web/lists/GetByTitle('MD_RequestIndex')/items(@{body('Get_request')?['IndexItemId']})"
    has = {"equals": ["@not(empty(body('Get_request')?['IndexItemId']))", True]}
    assert fk.find(RECEIPT, "Has_index_row")["expression"] == has
    assert fk.find(RECEIPT, "Has_index_row_partial")["expression"] == has
    for action, uri, snippet in (
            ("Set_index_row", idx_uri, "fl-kvittering-5-merge-index.json"),
            ("Set_request_created", req_uri, "fl-kvittering-4-merge-request.json"),
            ("Set_index_row_partial", idx_uri, "fl-kvittering-8-merge-index-partial.json"),
            ("Set_request_in_progress", req_uri, "fl-kvittering-7-merge-request-partial.json")):
        p = _p(RECEIPT, action)
        assert p["parameters/uri"] == uri, action
        assert p["parameters/body"] == _body(snippet), action
    created = json.loads(_p(RECEIPT, "Set_index_row")["parameters/body"])
    assert created["Status"] == request_index.CREATED == "OprettetISAP"
    assert created["StatusStep"] == request_index.step(created["Status"]) == 5
    assert created["IsOpen"] is False
    partial = json.loads(_p(RECEIPT, "Set_index_row_partial")["parameters/body"])
    assert partial["StatusStep"] == request_index.step(partial["Status"])
    assert partial["IsOpen"] is True


def test_requester_mail_is_english_with_the_rows():
    sel = fk.find(RECEIPT, "Mail_rows")["inputs"]
    assert sel == {"from": "@outputs('Receipt')?['rows']", "select": "@" + _text("fl-kvittering-6-mail-row.txt")}
    p = _p(RECEIPT, "Send_requester_email")
    assert p["emailMessage/To"] == "@body('Get_request')?['RequesterEmail']"
    assert p["emailMessage/Subject"] == \
        "Functional location request @{outputs('Receipt')?['requestNo']} created in SAP"
    assert "<table>@{join(body('Mail_rows'), '')}</table>" in p["emailMessage/Body"]


def test_partial_mail_goes_to_master_data_with_the_failed_rows():
    p = _p(RECEIPT, "Send_partial_notification")
    assert p["emailMessage/To"] == "@parameters('BioSap-MasterDataEmail (orsted_BioSapMasterDataEmail)')"
    assert p["emailMessage/Subject"] == "FL request @{outputs('Receipt')?['requestNo']} partly created in SAP"
    assert "FlowRunHistoryLink" in p["emailMessage/Body"]
    rows = [{"functionalLocation": "A1", "done": True, "result": "Created"},
            {"functionalLocation": "A2", "done": False, "lastError": "Field <Room> & co"}]
    failed = fk.find(RECEIPT, "Failed_rows")
    sel = fk.find(RECEIPT, "Failed_mail_rows")
    ctx = wdl_eval.run({"Receipt": {"type": "Compose", "inputs": {"rows": rows}},
                        "Failed_rows": failed, "Failed_mail_rows": sel},
                       ["Receipt", "Failed_rows", "Failed_mail_rows"], {}, {})
    html = "".join(ctx.outputs["Failed_mail_rows"])
    assert "A2" in html and "A1" not in html
    assert "Field &lt;Room&gt; &amp; co" in html


def test_invalid_receipt_goes_to_afvist_with_a_mail():
    no = fk.find(RECEIPT, "Valid_receipt")["else"]["actions"]
    assert no["Move_file_to_Afvist"]["inputs"]["parameters"]["parameters/destinationFolderPath"] == \
        "/SAP-oprettelse/Kvitteringer/FL/Afvist"
    assert no["Send_rejected_notification"]["inputs"]["parameters"]["emailMessage/To"] == \
        "@parameters('BioSap-ErrorNotifiers (orsted_BioSapErrorNotifiers)')"
    assert _p(RECEIPT, "Move_file_to_Afvist_on_error")["parameters/destinationFolderPath"] == \
        "/SAP-oprettelse/Kvitteringer/FL/Afvist"
    for action in ("Move_file_to_Behandlet", "Move_partial_file_to_Behandlet"):
        assert _p(RECEIPT, action)["parameters/destinationFolderPath"] == \
            "/SAP-oprettelse/Kvitteringer/FL/Behandlet"
