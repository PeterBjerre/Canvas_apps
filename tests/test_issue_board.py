# -*- coding: utf-8 -*-
"""
Issue Board (issue #114): skaermen, provisioneringen, seedet og flowet
bruger de samme navne. Kolonnerne findes ikke i schema.json foer
provisioneringen er koert, saa det er HER, de holdes i trit.

    python3 -m pytest tests/test_issue_board.py
"""
import csv
import glob
import json
import os
import re
import sys

from conftest import ROOT

sys.path.insert(0, os.path.join(ROOT, "Issue Board", "build"))
import ib_config as cfg  # noqa: E402

PS1 = os.path.join(ROOT, "sharepoint", "provision", "Provision-IssueBoard.ps1")
FLOWS = os.path.join(ROOT, "solution", "BIOSAP", "src", "Workflows")
# Kolonner, SharePoint selv har paa hver liste.
# Attachments: SharePoint-vedhaeftningerne paa raekken (trin 2).
BUILTIN = {"ID", "Title", "Created", "Modified", "Attachments"}


def _ps1():
    return open(PS1, encoding="utf-8-sig").read()


def _provisioned():
    cols = {}
    for lst, col in re.findall(r"^Add-Col '([^']+)' '([^']+)'", _ps1(), re.M):
        cols.setdefault(lst, set()).add(col)
    # IB_AppSections: Title hedder Application (Set-PnPField ... Title = 'Application').
    assert "Title = 'Application'" in _ps1()
    cols.setdefault(cfg.L_SECTIONS, set()).add("Application")
    return cols


def _ps1_choices(var):
    m = re.search(r"^\$" + var + r"\s*=\s*((?:'[^']*'\s*,?\s*)+)$", _ps1(), re.M)
    assert m, var
    return re.findall(r"'([^']*)'", m.group(1))


def _flow():
    path, = glob.glob(os.path.join(FLOWS, "BioSap-IssueBoard-Submit-*.json"))
    return json.load(open(path, encoding="utf-8-sig"))


def _walk(actions):
    for name, a in actions.items():
        yield name, a
        for key in ("actions",):
            if key in a:
                yield from _walk(a[key])
        if "else" in a:
            yield from _walk(a["else"]["actions"])
        for case in (a.get("cases") or {}).values():
            yield from _walk(case["actions"])
        if "default" in a:
            yield from _walk(a["default"]["actions"])


def _op(a):
    inputs = a.get("inputs")
    return ((inputs.get("host") or {}).get("operationId")) if isinstance(inputs, dict) else None


def test_screen_reads_only_provisioned_columns():
    cols = _provisioned()
    for lst, read in cfg.COLS.items():
        missing = set(read) - BUILTIN - cols.get(lst, set())
        assert not missing, (lst, missing)


def test_vocabulary_matches_provisioning():
    assert _ps1_choices("STATUS") == [s for s, _c, _r in cfg.STATUS]
    assert _ps1_choices("SEVERITY") == cfg.SEVERITY
    assert _ps1_choices("PRIORITY") == [p for p, _r in cfg.PRIORITY]
    assert _ps1_choices("EVENTTYPE") == cfg.EVENT_TYPES
    assert _ps1_choices("AUTHORROLE") == cfg.AUTHOR_ROLES
    assert _ps1_choices("VISIBILITY") == cfg.VISIBILITY
    assert cfg.SEVERITY_DEFAULT in cfg.SEVERITY
    assert cfg.PRIORITY_DEFAULT in [p for p, _r in cfg.PRIORITY]


def test_flow_writes_only_provisioned_columns():
    cols = _provisioned()
    for name, a in _walk(_flow()["properties"]["definition"]["actions"]):
        if _op(a) not in ("PostItem", "PatchItem"):
            continue
        params = a["inputs"]["parameters"]
        lst = params["table"]
        for key in params:
            if key.startswith("item/"):
                col = key.split("/")[1]
                assert col in BUILTIN or col in cols.get(lst, set()), (name, lst, col)


def test_flow_uses_the_existing_admin_list():
    import permissions
    flow = _flow()
    gets = [a for _n, a in _walk(flow["properties"]["definition"]["actions"])
            if _op(a) == "GetItems"]
    assert any(g["inputs"]["parameters"]["table"] == permissions.ADMIN_LIST
               and f"Title eq '{permissions.ADMIN_GROUP}'" in g["inputs"]["parameters"]["$filter"]
               for g in gets)
    text = json.dumps(flow)
    # Ingen hardkodede personer - kalderen kommer fra Power Apps' header.
    assert not re.search(r"[\w.]+@[\w-]+\.(com|dk)", text)
    assert "x-ms-user-email" in text


def test_flow_locks_the_item_before_it_answers():
    actions = dict(_walk(_flow()["properties"]["definition"]["actions"]))
    assert "breakroleinheritance" in json.dumps(actions["Break_ticket_inheritance"])
    assert "breakroleinheritance" in json.dumps(actions["Break_comment_inheritance"])
    # Svaret kommer efter den anonyme kopi, som kommer efter rettighederne.
    assert actions["Ticket_no"]["runAfter"] == {"For_each_ticket_admin": ["Succeeded"]}


def test_screen_calls_the_flow_by_its_name():
    path, = glob.glob(os.path.join(FLOWS, "BioSap-IssueBoard-Submit-*.json.data.xml"))
    assert 'Name="BioSap-IssueBoard-Submit"' in open(path, encoding="utf-8-sig").read()
    assert cfg.FLOW == "'BioSap-IssueBoard-Submit'"


def test_seed_is_consistent():
    with open(cfg.SEED_CSV, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    keys = [(r["Application"], r["Section"]) for r in rows]
    assert len(keys) == len(set(keys)), "dobbelt Application/Section i seedet"
    apps = {r["Application"] for r in rows}
    for app in apps:
        assert (app, cfg.OTHER) in keys, f"{app} mangler Section Other"
    import env_config
    known = set(env_config.APPS)
    for r in rows:
        assert not r["ScreenKey"] or r["ScreenKey"] in known, r


def test_feature_flag_hides_the_screen(monkeypatch):
    import env_config
    assert env_config.APPS[cfg.APP_KEY]["feature"] == cfg.FEATURE
    monkeypatch.setattr(env_config, "FEATURES", {})
    assert not env_config._app_enabled(cfg.APP_KEY)
    assert env_config._app_enabled("kks")
    monkeypatch.setattr(env_config, "FEATURES", {cfg.FEATURE: True})
    assert env_config._app_enabled(cfg.APP_KEY)


# ---------------------------------------------------------------------------
# Trin 2: admin-board, redigering, vedhaeftninger, mail
# ---------------------------------------------------------------------------
def _cases():
    try_ = _flow()["properties"]["definition"]["actions"]["Try"]["actions"]
    return {c["case"]: c["actions"] for c in try_["Action"]["cases"].values()}


def test_flow_has_every_action_the_screen_calls():
    cases = _cases()
    for act in (cfg.ACT_CREATE, cfg.ACT_COMMENT, cfg.ACT_EDIT, cfg.ACT_REOPEN,
                cfg.ACT_ARCHIVE, cfg.ACT_DELETE, cfg.ACT_ATTACH):
        assert act in cases, act
    import ib_parts as P
    text = "\n".join([P.SUBMIT, P.SAVE_EDIT, P.POST, P.REOPEN, P.ARCHIVE, P.DELETE,
                      P.UPLOAD_FILES])
    for act in cases:
        assert f'"{act}"' in text, act


def test_admin_only_actions_are_checked_on_the_server():
    cases = _cases()
    for act in (cfg.ACT_ARCHIVE, cfg.ACT_DELETE):
        problem = json.dumps(next(iter(cases[act].values())))
        assert "not(outputs('Is_admin'))" in problem, act
    # Rapportoeren maa kun rette en sag, der er New; admin altid.
    edit = json.dumps(cases[cfg.ACT_EDIT]["Edit_problem"])
    assert f"equals(outputs('Current_status'), '{cfg.STATUS_EDITABLE}')" in edit
    # Status, prioritet, tildeling og loesning tages kun fra en admin.
    ok = cases[cfg.ACT_EDIT]["Edit_ok"]["actions"]
    for name in ("New_status", "New_priority", "New_assignee", "New_resolution"):
        assert ok[name]["inputs"].startswith("@if(outputs('Is_admin')"), name
    # Intern note kun fra en admin.
    assert "Only administrators can add internal notes." in json.dumps(cases[cfg.ACT_COMMENT])


def test_delete_needs_the_ticket_number_and_takes_the_history_with_it():
    delete = _cases()[cfg.ACT_DELETE]
    assert "confirm" in json.dumps(delete["Delete_problem"])
    ok = json.dumps(delete["Delete_ok"])
    for table in (cfg.L_COMMENTS, cfg.L_SHARED, cfg.L_TICKETS):
        assert f'"table": "{table}"' in ok, table


def test_internal_notes_never_reach_the_reporter():
    actions = dict(_walk(_flow()["properties"]["definition"]["actions"]))
    grant = actions["Grant_event_reporter"]
    assert grant["expression"] == {"equals": ["@items('For_each_event')?['visibility']", "Reporter"]}
    assert "Grant_comment_reporter_read" in grant["actions"]
    # Haendelserne skrives i raekkefoelge - ID er Activity's sortering.
    assert actions["For_each_event"]["runtimeConfiguration"]["concurrency"]["repetitions"] == 1


def test_attachments_live_on_the_ticket_row():
    attach = json.dumps(_cases()[cfg.ACT_ATTACH])
    assert '"operationId": "CreateAttachment"' in attach
    assert f'"table": "{cfg.L_TICKETS}"' in attach
    trigger = _flow()["properties"]["definition"]["triggers"]["manual"]["inputs"]["schema"]
    assert trigger["properties"]["file"]["x-ms-content-hint"] == "FILE"
    assert "file" not in trigger["required"]


def test_archiving_removes_the_issue_from_the_shared_board():
    archive = json.dumps(_cases()[cfg.ACT_ARCHIVE])
    assert '"operationId": "DeleteItem"' in archive and f'"table": "{cfg.L_SHARED}"' in archive
    assert '"item/SharedItemId": 0' in archive


def test_mail_only_goes_to_the_reporter_on_three_events():
    actions = dict(_walk(_flow()["properties"]["definition"]["actions"]))
    mails = [n for n, a in actions.items() if _op(a) == "SendEmailV2"]
    assert mails == ["Send_mail_to_reporter"]
    to = actions["Send_mail_to_reporter"]["inputs"]["parameters"]["emailMessage/To"]
    assert "ReporterEmail" in to
    setters = [n for n, a in actions.items()
               if a.get("type") == "SetVariable" and a["inputs"]["name"] == "MailSubject"]
    assert sorted(setters) == ["Reply_subject", "Status_subject"]
    assert "'Ready for retest', 'Closed'" in json.dumps(actions["Mail_on_status"])


def test_admin_scope_and_actions_follow_is_admin():
    import ib_parts as P
    from permissions import IS_ADMIN
    assert f"{IS_ADMIN} && !varIbAllLoaded" in P.LOAD_ALL
    assert f"IbCanManage = !varIbSelShared && {IS_ADMIN};" in P.FORMULAS
    assert "IbCanEdit = " in P.FORMULAS and f'varIbSel.Status = "{cfg.STATUS_EDITABLE}"' in P.FORMULAS


def test_attachments_are_never_read_from_a_with_record():
    # Issue #133: Studio afviser r.Attachments fra With({ r: LookUp(...) })
    # med "The specified column is not accessible in this context". Filerne
    # hentes kun med LookUp(...).Attachments direkte (LOAD_FILES).
    text = open(os.path.join(ROOT, "BIO SAP App", "ScreenIssueBoard.pa.yaml"),
                encoding="utf-8").read()
    bad = re.findall(r"\b(?!att)\w+\.Attachments\b", text)
    assert not bad, bad
