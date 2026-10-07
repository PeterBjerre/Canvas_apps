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
BUILTIN = {"ID", "Title", "Created", "Modified"}


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
