# -*- coding: utf-8 -*-
"""Issue #384: en kommentar sendes hurtigere.

Flowet BioSap-IssueBoard-Submit lavede 7 + 2 x (antal admins)
SharePoint-kald efter hinanden, foer det svarede appen. Nu hentes sagen
og admin-listen samtidig, rapportoeren slaas op samtidig med Action, og
admins' rettigheder paa raekken gives efter svaret. Raekken, nedarvningen
og rapportoerens Read er stadig paa plads, foer appen faar svar, og en
fejl dér ruller stadig kommentaren tilbage. Ventetilstanden i appen
foelger kaldet og lover ingen fast tid."""
import glob
import json
import os
import sys

from conftest import ROOT

sys.path.insert(0, os.path.join(ROOT, "Issue Board", "build"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

FLOWS = os.path.join(ROOT, "solution", "BIOSAP", "src", "Workflows")
ALL = ["Succeeded", "Failed", "Skipped", "TimedOut"]


def _try():
    path, = glob.glob(os.path.join(FLOWS, "BioSap-IssueBoard-Submit-*.json"))
    d = json.load(open(path, encoding="utf-8-sig"))
    return d["properties"]["definition"]["actions"]


def _deps(actions, name):
    return set(actions[name]["runAfter"])


def _ancestors(actions, name):
    seen, todo = set(), [name]
    while todo:
        for dep in actions[todo.pop()]["runAfter"]:
            if dep not in seen:
                seen.add(dep)
                todo.append(dep)
    return seen


def test_lookups_run_in_parallel():
    t = _try()["Try"]["actions"]
    # Sagen venter ikke paa admin-listen, og Action venter paa begge.
    assert _deps(t, "Load_ticket") == {"Payload"}
    assert _deps(t, "Action") == {"Load_ticket", "Is_admin"}
    # Rapportoeren og admins slaas op ved siden af Action - ikke efter den.
    assert _deps(t, "Resolve_reporter") == {"Load_ticket"}
    assert _deps(t, "Resolve_admins") == {"Select_admins"}
    assert "Ensure_event_reporter" in t["Resolve_reporter"]["actions"]["Has_reporter"]["actions"]
    loop = t["Resolve_admins"]["actions"]["For_each_admin_id"]
    # AdminIds er en variabel - loekken skal fortsat koere een ad gangen.
    assert loop["runtimeConfiguration"]["concurrency"]["repetitions"] == 1


def test_reply_does_not_wait_for_admin_lookups_or_grants():
    t = _try()["Try"]["actions"]
    before_reply = _ancestors(t, "Respond")
    assert "Resolve_admins" not in before_reply
    assert {"Action", "Resolve_reporter", "Log_events"} <= before_reply
    ev = t["Log_events"]["actions"]["For_each_event"]["actions"]
    # Foer svaret: raekken, nedarvningen og rapportoerens Read.
    for name in ("Create_comment", "Break_comment_inheritance", "Grant_event_reporter"):
        assert name in ev, name
    assert "For_each_event_admin" not in ev
    assert ev["Remember_comment_id"]["inputs"] == {"name": "CommentIds",
                                                   "value": "@variables('CommentId')"}
    # Efter svaret: admins' rettigheder paa hver skrevet raekke.
    grant = t["Grant_admins"]
    assert grant["runAfter"] == {"Respond": ["Succeeded"], "Resolve_admins": ALL}
    per_row = grant["actions"]["For_each_comment_id"]
    assert per_row["foreach"] == "@variables('CommentIds')"
    admins = per_row["actions"]["For_each_event_admin"]
    uri = admins["actions"]["Grant_event_admin"]["inputs"]["parameters"]["parameters/uri"]
    assert "items(@{items('For_each_comment_id')})" in uri
    # En fejlet admin-rettighed maa aldrig faa Try til at fejle efter svaret
    # (saa ville Catch slette en kommentar, appen har vist som sendt).
    assert admins["actions"]["Admin_event_handled"]["runAfter"] == {"Grant_event_admin": ALL}
    adm = t["Resolve_admins"]["actions"]["For_each_admin_id"]["actions"]
    assert adm["Admin_id_handled"]["runAfter"] == {"Remember_admin_id": ALL}
    assert t["Notify_reporter"]["runAfter"] == {"Respond": ["Succeeded"]}


def test_comment_ids_variable_is_initialised():
    a = _try()
    init = a["Init_comment_ids"]["inputs"]["variables"][0]
    assert init == {"name": "CommentIds", "type": "array", "value": []}
    assert a["Try"]["runAfter"] == {"Init_comment_ids": ["Succeeded"]}


def test_sequential_calls_before_reply_are_fewer():
    """Kritisk vej for en kommentar (SharePoint-kald foer svaret)."""
    t = _try()["Try"]["actions"]
    ev = t["Log_events"]["actions"]["For_each_event"]["actions"]
    calls_in_event = [n for n, a in ev.items() if a["type"] == "OpenApiConnection"]
    assert calls_in_event == ["Create_comment", "Break_comment_inheritance"]
    # + Grant_comment_reporter_read (kun ved Reporter) = 3; foer var 3 + N.


def test_posting_state_promises_no_fixed_time():
    import ib_parts as P
    assert "10 seconds" not in P.POST_STAGE_TEXT
    assert "Saving it to the issue" not in P.POST_STAGE_TEXT
    screen = open(os.path.join(ROOT, "BIO SAP App", "ScreenIssueBoard.pa.yaml"),
                  encoding="utf-8").read()
    assert "takes about 10 seconds" not in screen
    # Hjulet staar, saa laenge kaldet koerer - det styres af svaret, ikke af tiden.
    assert 'varIbPostStage = "posting"' in P.POSTING_HERE
    assert P.POST.index("Run(") < P.POST.index('Set(varIbPostStage, "done")')
