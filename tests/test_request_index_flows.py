# -*- coding: utf-8 -*-
"""
R2-020: flowene skriver indeksets Status og StatusStep som literaler.

Hver PatchItem mod MD_RequestIndex i solution/BIOSAP/src/Workflows skal
skrive et trin, der passer til statussen efter request_index.STATUS - ellers
tegner hubben forloebsstriben forkert, og Stuck-filteret (StatusStep 2-3)
rammer ved siden af. Trin 0 og 5 er afsluttet og skal lukke raekken.

Apperne skriver Kladde/Indsendt; flowene skriver resten. Et flow maa derfor
aldrig skrive Kladde eller Indsendt.

    python3 -m pytest tests/test_request_index_flows.py
"""
import glob
import json
import os

from conftest import ROOT
import request_index

FLOWS = os.path.join(ROOT, "solution", "BIOSAP", "src", "Workflows")


def _walk(acts):
    for name, a in acts.items():
        yield name, a
        if "actions" in a:
            yield from _walk(a["actions"])
        if "else" in a:
            yield from _walk(a["else"].get("actions", {}))
        for case in a.get("cases", {}).values():
            yield from _walk(case.get("actions", {}))
        if "default" in a:
            yield from _walk(a["default"].get("actions", {}))


def _index_patches():
    out = []
    for path in sorted(glob.glob(os.path.join(FLOWS, "*.json"))):
        flow = os.path.basename(path)
        d = json.load(open(path, encoding="utf-8-sig"))["properties"]["definition"]
        for name, a in _walk(d["actions"]):
            inputs = a.get("inputs")
            if not isinstance(inputs, dict):
                continue
            p = inputs.get("parameters", {})
            op = inputs.get("host", {}).get("operationId")
            if op == "PatchItem" and "MD_RequestIndex" in str(p.get("table")):
                out.append((flow, name, p))
            elif (op == "HttpRequest"
                    and "GetByTitle('MD_RequestIndex')" in str(p.get("parameters/uri"))):
                # FL-kvitteringsflowet (docs/36) skriver med REST MERGE.
                body = json.loads(p["parameters/body"])
                out.append((flow, name, {"item/" + k: v for k, v in body.items()}))
    return out


def test_fl_receipt_flow_index_merges_are_checked():
    names = {n for f, n, _p in _index_patches() if f.startswith("BioSap-FL-SapReceipt-")}
    assert names == {"Set_index_row", "Set_index_row_partial"}


def _status(p):
    if "item/Status/Value" in p:
        return p["item/Status/Value"]
    s = p.get("item/Status")
    return s.get("Value") if isinstance(s, dict) else s


def test_there_are_index_patches_to_check():
    # Vaernet maa ikke blive groent, fordi soegningen ikke finder noget.
    assert len(_index_patches()) >= 15


def test_every_index_patch_writes_the_step_of_its_status():
    for flow, name, p in _index_patches():
        status = _status(p)
        assert status in dict((k, s) for k, _l, s in request_index.STATUS), \
            "%s/%s: ukendt status %r" % (flow, name, status)
        assert p.get("item/StatusStep") == request_index.step(status), \
            "%s/%s: %s skal have StatusStep %s, ikke %r" % (
                flow, name, status, request_index.step(status),
                p.get("item/StatusStep"))


def test_closed_steps_close_the_row():
    for flow, name, p in _index_patches():
        if request_index.step(_status(p)) in (0, 5):
            assert p.get("item/IsOpen") is False, "%s/%s" % (flow, name)
        elif "item/IsOpen" in p:
            assert p["item/IsOpen"] is True, "%s/%s" % (flow, name)


def test_flows_never_write_the_app_statuses():
    for flow, name, p in _index_patches():
        assert _status(p) not in (request_index.DRAFT, request_index.SUBMITTED), \
            "%s/%s skriver en app-status" % (flow, name)
