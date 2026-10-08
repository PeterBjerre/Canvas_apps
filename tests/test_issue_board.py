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


def _flow(name="Submit"):
    path, = glob.glob(os.path.join(FLOWS, f"BioSap-IssueBoard-{name}-*.json"))
    return json.load(open(path, encoding="utf-8-sig"))


FLOW_NAMES = ("Submit", "OnCreated")


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
    for flow in FLOW_NAMES:
        for name, a in _walk(_flow(flow)["properties"]["definition"]["actions"]):
            if _op(a) not in ("PostItem", "PatchItem"):
                continue
            params = a["inputs"]["parameters"]
            lst = params["table"]
            for key in params:
                if key.startswith("item/"):
                    col = key.split("/")[1]
                    assert col in BUILTIN or col in cols.get(lst, set()), (flow, name, lst, col)


def test_flow_uses_the_existing_admin_list():
    import permissions
    for name in FLOW_NAMES:
        flow = _flow(name)
        gets = [a for _n, a in _walk(flow["properties"]["definition"]["actions"])
                if _op(a) == "GetItems"]
        assert any(g["inputs"]["parameters"]["table"] == permissions.ADMIN_LIST
                   and f"Title eq '{permissions.ADMIN_GROUP}'" in g["inputs"]["parameters"]["$filter"]
                   for g in gets), name
        # Ingen hardkodede personer.
        assert not re.search(r"[\w.]+@[\w-]+\.(com|dk)", json.dumps(flow)), name
    # Submit: kalderen kommer fra Power Apps' header.
    assert "x-ms-user-email" in json.dumps(_flow())


def test_comments_stay_private_per_row_and_tickets_are_open():
    # Issue #193: alle laeser sagerne, men kun rapportoeren og admins en
    # sags kommentarer - ogsaa en admins. Kommentarlisten er privat paa
    # listen, og flowet giver rettigheder paa hver raekke.
    actions = dict(_walk(_flow()["properties"]["definition"]["actions"]))
    assert "breakroleinheritance" in json.dumps(actions["Break_comment_inheritance"])
    assert "roledefid=1073741826" in json.dumps(actions["Grant_comment_reporter_read"])
    assert "roledefid=1073741827" in json.dumps(actions["Grant_event_admin"])
    # Sagerne faar ingen egne rettigheder laengere - de arver listen.
    for name in FLOW_NAMES:
        text = json.dumps(_flow(name))
        assert "GetByTitle('IB_Tickets')/items" not in text, name
    ps1 = _ps1()
    assert f"Set-PrivateList $COMMENTS" in ps1
    assert "Set-OpenTicketList $TICKETS" in ps1
    assert "-ReadSecurity 1 -WriteSecurity 2" in ps1
    assert "Reset-TicketItemPermissions $TICKETS" in ps1
    assert "Set-PrivateList $TICKETS" not in ps1


def test_on_created_flow_numbers_the_issue_and_mails_admins_and_reporter():
    flow = _flow("OnCreated")
    d = flow["properties"]["definition"]
    trig, = d["triggers"].values()
    assert trig["inputs"]["host"]["operationId"] == "GetOnNewItems"
    assert trig["inputs"]["parameters"]["table"] == cfg.L_TICKETS
    a = d["actions"]
    assert a["Ticket_no"]["inputs"] == "@concat('ISS-', formatNumber(int(triggerBody()?['ID']), '000000'))"
    # Rapportoeren er Created By - ikke det, klienten skrev.
    assert "['Author']?['Email']" in a["Reporter"]["inputs"]
    upd = a["Update_ticket"]["inputs"]["parameters"]
    assert upd["table"] == cfg.L_TICKETS
    assert upd["item/TicketNo"] == "@{outputs('Ticket_no')}"
    assert upd["item/ReporterEmail"] == "@{outputs('Reporter')}"
    assert upd["item/Status/Value"] == cfg.STATUS_NEW
    assert upd["item/Priority/Value"] == cfg.PRIORITY_DEFAULT
    acts = dict(_walk(d["actions"]))
    mails = {n: x for n, x in acts.items() if _op(x) == "SendEmailV2"}
    assert sorted(mails) == ["Send_mail_to_admins", "Send_mail_to_reporter"]
    assert mails["Send_mail_to_admins"]["inputs"]["parameters"]["emailMessage/To"] == "@{outputs('Admin_to')}"
    assert mails["Send_mail_to_reporter"]["inputs"]["parameters"]["emailMessage/To"] == "@{outputs('Reporter')}"
    for m in mails.values():
        p = m["inputs"]["parameters"]
        assert "emailMessage/From" not in p
        assert p["emailMessage/Body"].startswith('<div style="font-family: Segoe UI, Arial, sans-serif; font-size: 14px">')
    # Samme forbindelser (servicekontoen) som Submit-flowet.
    assert flow["properties"]["connectionReferences"] == _flow()["properties"]["connectionReferences"]
    # I solutionen.
    path, = glob.glob(os.path.join(FLOWS, "BioSap-IssueBoard-OnCreated-*.json.data.xml"))
    xml = open(path, encoding="utf-8-sig").read()
    assert 'Name="BioSap-IssueBoard-OnCreated"' in xml
    wid = re.search(r'WorkflowId="\{([0-9a-f-]+)\}"', xml).group(1)
    assert wid.upper() in os.path.basename(path)
    sol = open(os.path.join(ROOT, "solution", "BIOSAP", "src", "Other", "Solution.xml"),
               encoding="utf-8-sig").read()
    assert f'<RootComponent type="29" id="{{{wid}}}" behavior="0" />' in sol
    assert cfg.FLOW_ON_CREATED == "BioSap-IssueBoard-OnCreated"


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
    # Issue #193: ingen create - appen opretter sagen med Patch.
    assert set(cases) == {cfg.ACT_COMMENT, cfg.ACT_EDIT, cfg.ACT_REOPEN, cfg.ACT_ARCHIVE,
                          cfg.ACT_DELETE, cfg.ACT_ATTACH}
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
    # Edit (issue #193): appen har rettet sagen med Patch. Flowet logger kun,
    # og kun for rapportoeren eller en admin; de nye vaerdier laeses fra
    # raekken, ikke fra appen - kun "foer" kommer fra appen.
    edit = json.dumps(cases[cfg.ACT_EDIT]["Edit_problem"])
    assert "not(or(outputs('Is_admin'), outputs('Is_reporter')))" in edit
    ok = cases[cfg.ACT_EDIT]["Edit_ok"]["actions"]
    assert ok["New_status"]["inputs"] == "@outputs('Current_status')"
    for name in ("New_priority", "New_assignee", "New_resolution"):
        assert "outputs('Ticket')" in ok[name]["inputs"] and "Payload" not in ok[name]["inputs"], name
    assert not [n for n, a in _walk(ok) if _op(a) == "PatchItem" and "Stamp" not in n]
    # Appen: status, prioritet, tildeling og loesning kun fra en admin, og
    # rapportoeren kun mens sagen er New - paa raekken, som den staar nu.
    import ib_parts as P
    from permissions import IS_ADMIN
    for col in ("Status", "Priority"):
        assert f"{col}: {{ Value: If({IS_ADMIN}," in P.SAVE_EDIT
    for col in ("AssignedToEmail", "AssignedToName", "Resolution"):
        assert f"{col}: If({IS_ADMIN}," in P.SAVE_EDIT
    assert (f'!{IS_ADMIN} && (varIbCur.Status.Value <> "{cfg.STATUS_EDITABLE}"' in P.SAVE_EDIT)
    assert P.SAVE_EDIT.index(f"LookUp({cfg.L_TICKETS}, ID = varIbSelId)") < P.SAVE_EDIT.index("Patch(")
    assert P.SAVE_EDIT.index("Patch(") < P.SAVE_EDIT.index(f'"{cfg.ACT_EDIT}"')
    # Intern note kun fra en admin.
    assert "Only administrators can add internal notes." in json.dumps(cases[cfg.ACT_COMMENT])


def test_delete_needs_the_ticket_number_and_takes_the_history_with_it():
    delete = _cases()[cfg.ACT_DELETE]
    assert "confirm" in json.dumps(delete["Delete_problem"])
    ok = json.dumps(delete["Delete_ok"])
    for table in (cfg.L_COMMENTS, cfg.L_TICKETS):
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


def test_no_anonymous_copy_anymore():
    # Issue #193: ingen anonymisering - den delte kopi (IB_SharedIssues)
    # bruges hverken af flowene eller appen, og den slettes kun med en
    # eksplicit switch.
    for name in FLOW_NAMES:
        text = json.dumps(_flow(name))
        assert "IB_SharedIssues" not in text and "SharedItemId" not in text, name
    yaml = open(os.path.join(ROOT, "BIO SAP App", "ScreenIssueBoard.pa.yaml"), encoding="utf-8").read()
    for word in ("IB_SharedIssues", "colIbShared", "colIbMine", "Anonymous", "anonymous"):
        assert word not in yaml, word
    assert not hasattr(cfg, "L_SHARED")
    ps1 = _ps1()
    assert "Add-Col 'IB_SharedIssues'" not in ps1
    assert "[switch] $RemoveSharedIssues" in ps1
    removal = ps1[ps1.index("Remove-PnPList"):]
    before = ps1[:ps1.index("Remove-PnPList")]
    assert "elseif (-not $RemoveSharedIssues)" in before[-600:]
    assert removal.count("Remove-PnPList") == 1


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
    # Issue #193: alle henter alle sager; "My issues" er et filter.
    assert P.RELOAD_MAIN == P.RELOAD_ALL
    assert "IbMine = Filter(colIbAll, Reporter = varIbMe);" in P.FORMULAS
    assert f"IbCanManage = !varIbSelPeek && {IS_ADMIN};" in P.FORMULAS
    # Kommentarer (Activity) og filer kun for rapportoeren og admins.
    assert f"IbSeeActivity = IbSelMine || {IS_ADMIN};" in P.FORMULAS
    assert "IbCanComment = !varIbSelPeek && IbSeeActivity" in P.FORMULAS
    assert "IbCanAttach = !varIbSelPeek && IbSeeActivity" in P.FORMULAS
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
    # Issue #135/#193: Submit er footerens eneste knap og laaser sig selv;
    # sagen oprettes med Patch direkte i IB_Tickets (ikke gennem flowet),
    # og popuppen lukkes, nulstilles og sagen vises foerst, naar Patch lykkedes.
    import ib_parts as P
    text = open(os.path.join(ROOT, "BIO SAP App", "ScreenIssueBoard.pa.yaml"),
                encoding="utf-8").read()
    assert "btnIbFormCancel" not in text
    assert f"Patch(\n        {cfg.L_TICKETS},\n        Defaults({cfg.L_TICKETS})," in P.SUBMIT
    assert cfg.FLOW not in P.SUBMIT
    attempt, after = P.SUBMIT.split("If(\n    varIbSaved,\n")
    assert "Set(varIbSaved, true)" in attempt and "Set(varIbFormOn, false)" not in attempt
    assert "FirstError.Message" in attempt
    assert "Set(varIbFormOn, false)" in after
    assert P.CLEAR_FORM.replace("\n", "\n    ") in after
    assert "Set(varIbDetailOn, true)" in P.SHOW_NEW and "varIbNewRow.ID" in P.ADD_NEW
    assert P.SUBMIT.rstrip().endswith("Set(varIbBusy, false)")
    # Rapportoeren og starttilstanden - OnCreated-flowet saetter dem igen.
    for field in ("ReporterEmail: varIbMe", f'Status: {{ Value: "{cfg.STATUS_NEW}" }}',
                  f'Priority: {{ Value: "{cfg.PRIORITY_DEFAULT}" }}', "IsArchived: false"):
        assert field in P.SUBMIT, field
    form = {c.name: c for c in _walk_ctrls(P.build_form())}
    submit = form["btnIbFormSubmit"].props["OnSelect"]
    # Issue #177: Submit er kun laast, mens et kald koerer. Mangler der noget,
    # siger et tryk hvad - valgfrie felter indgaar ikke i VALID.
    assert submit.startswith(f"If(\n    varIbBusy,\n    false,\n    !({P.VALID}),\n"
                             "    Set(varIbTried, true);\n    Notify(")
    assert form["btnIbFormSubmit"].props["DisplayMode"] == \
        "If(varIbBusy, DisplayMode.Disabled, DisplayMode.Edit)"
    for optional in ("inpIbSteps", "inpIbExpected", "inpIbActual", "inpIbRelated", "drpIbSeverity"):
        assert optional not in P.VALID
    for required in ("inpIbTitle", "inpIbDesc", "inpIbOther"):
        assert required in P.VALID
        assert form[required].props["TriggerOutput"] == "TriggerOutput.Keypress"
    assert "varIbFormApp" in P.VALID and "varIbFormSection" in P.VALID
    assert form["btnIbFormClose"].props["OnSelect"] == P.CLOSE_ASK
    assert "Set(varIbDiscardOn, true)" in P.CLOSE_ASK and "!varIbBusy" in P.CLOSE_ASK
    assert [k.name for k in form["conIbFormFooter"].children] == ["btnIbFormSubmit"]
    assert "btnIbDiscardConfirm" in form
    # Issue #193: ingen filvaelger i New issue - filerne kommer bagefter.
    assert "attIbNewFiles" not in text


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
    assert "colIbMine" not in on_visible
    assert IS_ADMIN not in P.INIT_STATE
    # Oversigten henter ikke de lange tekster - de kommer, naar sagen aabnes.
    for col in ("ReproSteps", "ExpectedResult", "ActualResult", "OtherContext",
                "RelatedRequestNo", "Resolution"):
        assert col not in P.OVERVIEW_COLS
        assert f"r.{col}" not in P.FETCH_ALL
    assert set(P.OVERVIEW_COLS) <= set(cfg.COLS[cfg.L_TICKETS])
    # Aabnes en sag: dens raekke og Activity samtidig; filerne foerst paa fanen.
    assert "Concurrent(" in P.LOAD_OPEN and "colIbActivity" in P.LOAD_OPEN
    assert "Attachments" not in P.LOAD_OPEN


def test_new_issue_is_added_without_reloading_the_list():
    import ib_parts as P
    # Patch gav raekken tilbage - intet opslag og ingen ny hentning.
    assert P.FETCH_ALL not in P.SUBMIT
    assert "LookUp(" not in P.ADD_NEW and "Collect(colIbAll, varIbNew)" in P.ADD_NEW
    assert P.OPEN_FORM.rstrip().endswith("Set(varIbFormOn, true)")


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
    # Issue #193: rapportoerens navn for alle ("You" paa ens egne).
    rep = ctrls["txtIbFactReporter"].props["Text"]
    assert rep == P.REPORTER_FX.format(r="varIbSel")
    assert "varIbSel.ReporterName" in rep
    # Activity-fanen kun for rapportoeren og admins; Attachments for alle.
    assert ctrls["btnIbTabActivity"].props["Visible"] == "IbSeeActivity"
    assert "Visible" not in ctrls["btnIbTabFiles"].props
    assert ctrls["conIbDetActivity"].props["Visible"].startswith("IbSeeActivity")
    assert ctrls["conIbFileAdd"].props["Visible"] == "IbCanAttach"
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


def test_tile_fits_its_people_line():
    """Issue #177: flisen klipper ikke 'hvem' - linjen maa ombrydes, og den
    staar inden for flisen."""
    import ib_parts as P
    tile = {c.name: c for c in _walk_ctrls([P.build_list()])}
    people = tile["txtIbTilePeople"]
    assert people.props["Wrap"] == "true"
    bottom = int(people.props["Y"]) + int(people.props["Height"])
    assert bottom <= P.TILE_H - P.TILE_M
    assert tile["galIbList"].props["TemplateSize"] == str(P.TILE_H)


def test_tile_has_an_attach_button_after_creation():
    """Issue #193: vedhaeftninger er en knap paa flisen - kun for
    rapportoeren og admins, oven paa flisens klikflade, og den aabner sagen
    paa fanen Attachments (klassisk Attachments-kontrol + flowet)."""
    import ib_parts as P
    from permissions import IS_ADMIN
    gal = {c.name: c for c in _walk_ctrls([P.build_list()])}["galIbList"]
    names = [c.name for c in gal.children]
    assert names[-1] == "btnIbTileAttach" and names.index("btnIbTileOpen") < names.index("btnIbTileAttach")
    att = gal.children[-1]
    assert att.props["Visible"] == f"!ThisItem.Archived && (ThisItem.Reporter = varIbMe || {IS_ADMIN})"
    assert 'Set(varIbTab, "files")' in att.props["OnSelect"]
    assert P.LOAD_FILES in att.props["OnSelect"]
    assert att.props["Layout"] == "ButtonLayout.IconOnly" and att.props["AccessibleLabel"]
    # Inden for flisen og ikke oven paa nummeret.
    no = {c.name: c for c in gal.children}["txtIbTileNo"]
    assert f"{P.TILE_ATT_W}" in no.props["Width"]
    text = open(os.path.join(ROOT, "BIO SAP App", "ScreenIssueBoard.pa.yaml"), encoding="utf-8").read()
    assert "Control: Attachments@2.3.0" in text and "ModernAttachments" not in text
    assert f'"{cfg.ACT_ATTACH}"' in P.UPLOAD_FILES


def test_github_script_reads_provisioned_columns_and_vocabulary():
    """UAT: Send-IssueBoardToGitHub.ps1 laeser IB_Tickets direkte - samme
    kolonner og statusvaerdier som provisioneringen, og samme sagsnummer
    som flowet. Scriptet skriver intet i SharePoint og gemmer intet token."""
    path = os.path.join(ROOT, "sharepoint", "github", "Send-IssueBoardToGitHub.ps1")
    s = open(path, encoding="utf-8-sig").read()
    m = re.search(r"^\$FIELDS = ((?:'[^']*'[\s,]*)+)", s, re.M)
    assert m
    fields = set(re.findall(r"'([^']*)'", m.group(1)))
    missing = fields - BUILTIN - _provisioned()[cfg.L_TICKETS]
    assert not missing, missing
    assert re.search(r"^\$TICKETS = '" + cfg.L_TICKETS + "'", s, re.M)
    status = re.search(r"\[string\] \$Status = '([^']+)'", s).group(1)
    assert status in [x for x, _c, _r in cfg.STATUS]
    assert "concat('ISS-', formatNumber(int(triggerBody()?['ID']), '000000'))" in json.dumps(
        _flow("OnCreated"))
    assert "'ISS-{0:000000}'" in s
    code = "\n".join(l for l in s.splitlines() if not l.lstrip().startswith("#"))
    assert not re.search(r"\b(Set|Add|Remove|New)-PnP", code)
    assert not re.search(r"gh[pousr]_[A-Za-z0-9]{20,}|github_pat_", s)


def test_github_script_never_sends_who_reported_it():
    """Issue #193: rapportoerens navn staar nu paa sagen, men det offentlige
    GitHub-issue maa aldrig faa navn, mail, tildeling, kommentarer eller
    filer. Scriptet henter kun $FIELDS, og teksten bygges kun af dem."""
    path = os.path.join(ROOT, "sharepoint", "github", "Send-IssueBoardToGitHub.ps1")
    s = open(path, encoding="utf-8-sig").read()
    fields = set(re.findall(r"'([^']*)'", re.search(r"^\$FIELDS = ((?:'[^']*'[\s,]*)+)", s, re.M).group(1)))
    private = {"ReporterEmail", "ReporterName", "AssignedToEmail", "AssignedToName", "Author",
               "Editor", "LayoutContext", "ClientContext"}
    assert not fields & private
    body = s[s.index("\n#>") + 3:]             # uden hjaelpeteksten
    code = "\n".join(l for l in body.splitlines() if not l.lstrip().startswith("#"))
    for word in private | {cfg.L_COMMENTS, "AuthorEmail", "AuthorName", "OpenBinaryStream",
                           "Get-PnPFile"}:
        assert not re.search(r"\b" + word + r"\b", code), word
    # Kun $FIELDS hentes, og hvert felt, teksten laeser, er i $FIELDS.
    assert "Get-PnPListItem -List $TICKETS -PageSize 500 -Fields $FIELDS" in code
    used = set(re.findall(r"Get-Text \$(?:Item|it|_) '([^']+)'", code))
    used |= set(re.findall(r"@\('[^']+', '([^']+)'\)", code))
    assert used and used <= fields, used - fields
