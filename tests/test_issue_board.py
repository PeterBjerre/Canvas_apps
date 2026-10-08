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


def test_archived_issues_stay_on_the_shared_board_marked_archived():
    # Issue #177: alle skal kunne finde de arkiverede sager - uden private
    # oplysninger. Den anonyme kopi slettes ikke, den markeres.
    archive = _cases()[cfg.ACT_ARCHIVE]
    text = json.dumps(archive)
    assert '"operationId": "DeleteItem"' not in text
    assert '"item/SharedItemId": 0' not in text
    branch = archive["Archive_ok"]["actions"]["Archive_or_restore"]
    patch = branch["actions"]["Archive_shared"]["actions"]["Patch_shared_archived"]
    assert patch["inputs"]["parameters"]["table"] == cfg.L_SHARED
    assert patch["inputs"]["parameters"]["item/IsArchived"] is True
    restore = branch["else"]["actions"]["Restore_shared"]
    assert restore["actions"]["Patch_shared_restored"]["inputs"]["parameters"]["item/IsArchived"] is False
    # Sager arkiveret foer #177 har ingen kopi - den laves igen ved gendannelse.
    assert "Recreate_shared" in restore["else"]["actions"]
    # Den anonyme liste har stadig kun de sanerede kolonner.
    assert not {"ReporterEmail", "ReporterName", "AssignedToEmail", "AssignedToName"} & set(
        cfg.COLS[cfg.L_SHARED])


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
    # En admin henter alle sager (colIbAll), alle andre kun deres egne.
    assert P.RELOAD_MAIN.startswith(f"If({IS_ADMIN}, {P.RELOAD_ALL};")
    assert f"IbMine = If({IS_ADMIN}, Filter(colIbAll, Reporter = varIbMe), colIbMine);" in P.FORMULAS
    assert f"IbCanManage = !varIbSelShared && {IS_ADMIN};" in P.FORMULAS
    assert "IbCanEdit = " in P.FORMULAS and f'varIbSel.Status = "{cfg.STATUS_EDITABLE}"' in P.FORMULAS


def test_attachments_are_never_read_from_a_with_record():
    # Issue #133: Studio afviser r.Attachments fra With({ r: LookUp(...) })
    # med "The specified column is not accessible in this context". Filerne
    # hentes kun med LookUp(...).Attachments direkte (LOAD_FILES).
    text = open(os.path.join(ROOT, "BIO SAP App", "ScreenIssueBoard.pa.yaml"),
                encoding="utf-8").read()
    bad = re.findall(r"\b(?!att|Self\b)\w+\.Attachments\b", text)
    assert not bad, bad


def test_new_issue_popup_submits_once_and_closes_only_on_success():
    # Issue #135: Submit er footerens eneste knap og laaser sig selv; popuppen
    # lukkes, nulstilles og sagen vises foerst, naar flowet har svaret ok.
    import ib_parts as P
    text = open(os.path.join(ROOT, "BIO SAP App", "ScreenIssueBoard.pa.yaml"),
                encoding="utf-8").read()
    assert "btnIbFormCancel" not in text
    ok, fail = P.SUBMIT.split('NotificationType.Success)\n    ),\n')
    assert "Set(varIbFormOn, false)" in ok and "Set(varIbFormOn, false)" not in fail
    assert P.CLEAR_FORM.replace("\n", "\n    ") in ok
    assert "Set(varIbDetailOn, true)" in P.SHOW_NEW and "Value(varIbRes.ticketid)" in P.ADD_NEW
    assert ok.index("Set(varIbSelId, Value(varIbRes.ticketid))") < ok.index("LookUp(IbMine, Id = varIbSelId)")
    assert "Coalesce(varIbRes.message" in fail
    assert P.SUBMIT.rstrip().endswith("Set(varIbBusy, false)")
    form = {c.name: c for c in _walk_ctrls(P.build_form())}
    submit = form["btnIbFormSubmit"].props["OnSelect"]
    # Issue #177: Submit er kun laast, mens et kald koerer. Mangler der noget,
    # siger et tryk hvad - valgfrie felter og filer indgaar ikke i VALID.
    assert submit.startswith(f"If(\n    varIbBusy,\n    false,\n    !({P.VALID}),\n"
                             "    Set(varIbTried, true);\n    Notify(")
    assert form["btnIbFormSubmit"].props["DisplayMode"] == \
        "If(varIbBusy, DisplayMode.Disabled, DisplayMode.Edit)"
    for optional in ("inpIbSteps", "inpIbExpected", "inpIbActual", "inpIbRelated", "drpIbSeverity",
                     "attIbNewFiles"):
        assert optional not in P.VALID
    for required in ("inpIbTitle", "inpIbDesc", "inpIbOther"):
        assert required in P.VALID
        assert form[required].props["TriggerOutput"] == "TriggerOutput.Keypress"
    assert "varIbFormApp" in P.VALID and "varIbFormSection" in P.VALID
    assert form["btnIbFormClose"].props["OnSelect"] == P.CLOSE_ASK
    assert "Set(varIbDiscardOn, true)" in P.CLOSE_ASK and "!varIbBusy" in P.CLOSE_ASK
    assert [k.name for k in form["conIbFormFooter"].children] == ["btnIbFormSubmit"]
    assert "btnIbDiscardConfirm" in form


def _walk_ctrls(nodes):
    for n in nodes:
        yield n
        yield from _walk_ctrls(n.children)


# ---------------------------------------------------------------------------
# Issue #177: oversigt, filtre, arkiv, popup, Activity, indsendelse, hentning
# ---------------------------------------------------------------------------
def test_screen_opens_with_one_round_of_queries():
    # Konfigurationen og den ene liste (admin: alle sager, ellers egne) hentes
    # samtidig - ingen anden runde mod IB_Tickets, og IsAdmin staar ikke i
    # koe foran hentningen.
    import ib_parts as P
    from permissions import IS_ADMIN
    on_visible = P.on_visible()
    assert on_visible.count("Concurrent(") == 1
    assert on_visible.count(f"ClearCollect(colIbAll,") == 1
    assert on_visible.count(f"ClearCollect(colIbMine,") == 1
    assert "colIbShared" not in on_visible
    assert IS_ADMIN not in P.INIT_STATE
    # Oversigten henter ikke de lange tekster - de kommer, naar sagen aabnes.
    for col in ("ReproSteps", "ExpectedResult", "ActualResult", "OtherContext",
                "RelatedRequestNo", "Resolution"):
        assert col not in P.OVERVIEW_COLS
        assert f"r.{col}" not in P.FETCH_MINE and f"r.{col}" not in P.FETCH_ALL
    assert set(P.OVERVIEW_COLS) <= set(cfg.COLS[cfg.L_TICKETS])
    # Aabnes en sag: dens raekke og Activity samtidig; filerne foerst paa fanen.
    assert "Concurrent(" in P.LOAD_OPEN and "colIbActivity" in P.LOAD_OPEN
    assert "Attachments" not in P.LOAD_OPEN


def test_new_issue_is_added_without_reloading_the_list():
    import ib_parts as P
    ok, _fail = P.SUBMIT.split('NotificationType.Success)\n    ),\n')
    assert P.FETCH_MINE not in ok.split("IsBlank(varIbSelRow)")[0]
    assert f"LookUp({cfg.L_TICKETS}, ID = varIbSelId)" in P.ADD_NEW
    # Formularen venter ikke paa den anonyme liste.
    assert P.OPEN_FORM.index("Set(varIbFormOn, true)") < P.OPEN_FORM.index("colIbShared")
    assert "varIbLoading" not in P.LOAD_SHARED


def test_detail_popup_hierarchy_and_single_close():
    import ib_parts as P
    nodes = P.build_detail()
    ctrls = {c.name: c for c in _walk_ctrls(nodes)}
    modal = ctrls["conIbDetModal"]
    # Hovedet (nummer, titel, Close) staar fast; kun kroppen scroller.
    assert [k.name for k in modal.children] == ["conIbDetHead", "conIbDetBody"]
    assert [k.name for k in ctrls["conIbDetHead"].children] == ["txtIbDetNo", "txtIbDetTitle",
                                                               "btnIbDetClose"]
    assert "Scroll" in ctrls["conIbDetBody"].props["LayoutOverflowY"]
    body = [k.name for k in ctrls["conIbDetBody"].children]
    order = ["conIbDetMeta", "conIbDetFacts", "conIbDetActions", "conIbActsMenu", "conIbDetRule",
             "conIbDetTabs"]
    assert [b for b in body if b in order] == order
    # Ingen Cancel - Close er eneste vej ud, ogsaa i sletningen.
    assert not [n for n in ctrls if "Cancel" in n]
    dels = {c.name for c in _walk_ctrls(P.build_delete())}
    assert "btnIbDelCancel" not in dels and "btnIbDelClose" in dels
    # Archive og Delete under More actions (kun admin), Delete sidst.
    assert [k.name for k in ctrls["conIbActsBtns"].children] == ["btnIbArchive", "btnIbDelete"]
    assert "IbCanManage" in ctrls["conIbActsMenu"].props["Visible"]
    assert ctrls["btnIbMoreActs"].props["Visible"] == "IbCanManage"
    # Edit kun, naar hele raekken er hentet.
    assert "varIbSelFullFor = varIbSelId" in ctrls["btnIbEdit"].props["DisplayMode"]
    # Rapportoeren vises kun, hvor det var tilladt foer: You / admin / anonym.
    rep = ctrls["txtIbFactReporter"].props["Text"]
    assert rep.startswith('If(varIbSelShared, "Anonymous", IbSelMine, "You", IsAdmin,')
    # Updated kun efter en reel aendring.
    assert ctrls["conIbFactUpdated"].props["Visible"] == "!IsBlank(IbSelUpdatedOn)"


def test_activity_shows_role_badges():
    import ib_parts as P
    ctrls = {c.name: c for c in _walk_ctrls(P.build_detail())}
    assert ctrls["txtIbActRole"].props["Text"] == "ThisItem.Role"
    assert 'Role: Switch(role, "Admin", "Admin", "System", "System", "User")' in P.LOAD_ACTIVITY
    assert '" (admin)"' not in P.LOAD_ACTIVITY
    # Interne noter kun for admin; Post comment laast, naar feltet er tomt.
    assert "internal: varIbInternal && IsAdmin" in P.POST
    assert ctrls["btnIbPost"].props["DisplayMode"].startswith("If(IsBlank(Trim(inpIbComment.Text))")
    assert ctrls["inpIbComment"].props["TriggerOutput"] == "TriggerOutput.Keypress"
