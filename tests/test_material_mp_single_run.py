# -*- coding: utf-8 -*-
"""
R2-084 pkt. 2: Material- og MP-flowet (Request-trigger) kan startes to gange
paa samme RequestGuid (dobbeltklik, hurtig genindsendelse). En koersel
stopper (Cancelled), hvis en ANDEN koersel inden for det seneste doegn har
spurgt en raekke (Requested), som endnu ikke er afgjort. Vinduet er kort med
vilje: en koersel, der er endt i Catch, efterlader uafgjorte Requested-
raekker, og den maa ikke spaerre en ny indsendelse i 14 dage. Concurrency 1
paa triggeren er ikke en mulighed: den ville stille alle anmodninger i koe
bag en 14-dages ventetid.

    python3 -m pytest tests/test_material_mp_single_run.py
"""
from datetime import datetime, timedelta, timezone

import pytest

import flowkit as fk
import wdl_eval

FLOWS = ["BioSap-Material-SystemApproval", "BioSap-MeasuringPoint-Approval"]


def _ts(days_ago):
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


@pytest.mark.parametrize("name", FLOWS)
def test_the_check_runs_before_anything_is_asked(name):
    d = fk.definition(name)
    sib = fk.siblings(name, "Get_log", d)
    assert sib["Decided_rows"]["runAfter"] == {"Get_log": ["Succeeded"]}
    stop = sib["Already_running"]
    assert stop["actions"]["Stop_already_running"]["inputs"]["runStatus"] == "Cancelled"
    after = [k for k, v in sib.items() if v.get("runAfter") == {"Already_running": ["Succeeded"]}]
    assert len(after) == 1


@pytest.mark.parametrize("name", FLOWS)
def test_running_rows(name):
    d = fk.definition(name)
    log = [
        {"Title": "other", "ItemGuid": "a", "Decision": "Requested", "DecidedOn": _ts(0.1)},
        {"Title": "other", "ItemGuid": "b", "Decision": "Requested", "DecidedOn": _ts(0.1)},
        {"Title": "other", "ItemGuid": "b", "Decision": "Approve", "DecidedOn": _ts(0)},
        {"Title": "old", "ItemGuid": "c", "Decision": "Requested", "DecidedOn": _ts(2)},
        {"Title": "me", "ItemGuid": "d", "Decision": "Requested", "DecidedOn": _ts(0)},
    ]
    running = dict(fk.find(name, "Running_rows", d))
    cutoff = _ts(1.0 / 24 * 23)   # lidt under et doegn - wdl_eval kender ikke addDays
    where = running["inputs"]["where"]
    assert "addDays(utcNow(), -1)" in where
    running["inputs"] = dict(running["inputs"],
                             where=where.replace("addDays(utcNow(), -1)", "'%s'" % cutoff))
    acts = {"RunName": {"type": "Compose", "inputs": "me"},
            "Get_log": {"type": "Compose", "inputs": {"body/value": log}},
            "Decided_rows": fk.find(name, "Decided_rows", d),
            "Decided_keys": fk.find(name, "Decided_keys", d),
            "Running_rows": running}
    out = wdl_eval.run(acts, list(acts), {}, {}).outputs["Running_rows"]
    assert [(r["Title"], r["ItemGuid"]) for r in out] == [("other", "a")]
