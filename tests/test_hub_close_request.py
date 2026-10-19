# -*- coding: utf-8 -*-
"""R2-021: en admin lukker en Equipment-, Material-, MP- eller FL-anmodning
fra hubben - "Mark created in SAP" eller "Cancel". Kun indeksraekken
skrives (request_index.close_record), og lukningen logges
(admin_log.CLOSE).

    python3 -m pytest -q tests/test_hub_close_request.py
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (os.path.join(ROOT, "tools"), os.path.join(ROOT, "Masterdata Hub", "build")):
    if p not in sys.path:
        sys.path.insert(0, p)

import admin_log as alog  # noqa: E402
import permissions as perm  # noqa: E402
import request_index as ri  # noqa: E402

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenMdHub.pa.yaml")


def test_close_record_writes_status_step_and_closes():
    rec = ri.close_record(ri.CREATED, "varMdMe")
    assert 'Status: { Value: "OprettetISAP" }' in rec
    assert f"StatusStep: {ri.step('OprettetISAP')}" in rec and "StatusStep: 5" in rec
    assert "IsOpen: false" in rec and "LastActionBy: varMdMe" in rec
    rec = ri.close_record(ri.CANCELLED, "varMdMe")
    assert 'Status: { Value: "Annulleret" }' in rec and "StatusStep: 0" in rec


@pytest.mark.parametrize("status", ["Kladde", "Indsendt", "KlarTilSAP", "Afvist", "Nope"])
def test_close_record_only_closes(status):
    with pytest.raises(KeyError):
        ri.close_record(status, "varMdMe")


def test_close_statuses_are_known_and_closed():
    known = {k for k, _l, _s in ri.STATUS}
    assert set(ri.CLOSE_STATUSES) <= known and set(ri.CLOSABLE_FROM) <= known
    assert ri.DRAFT not in ri.CLOSABLE_FROM
    # VH-planen lukkes af sit flow, ikke her.
    assert "MaintenancePlan" not in ri.CLOSE_DOMAINS
    assert set(ri.CLOSE_DOMAINS) == set(ri.DOMAINS) - {"MaintenancePlan"}


def test_only_admins_may_close():
    rule = perm.may_close("R")
    assert rule.startswith(f"({perm.IS_ADMIN} && R.IsOpen")
    for st in ri.CLOSABLE_FROM:
        assert f'R.Status.Value = "{st}"' in rule


def test_the_hub_has_the_close_action_and_logs_it():
    y = open(SCREEN, encoding="utf-8").read()
    for name in ("btnMdRowClose:", "btnMdRowCloseC:", "btnMdCloseCreated:", "btnMdCloseCancelled:"):
        assert "- " + name in y, name
    assert '"OprettetISAP"' in y and '"Annulleret"' in y
    assert f'Decision: "{alog.CLOSE}"' in y
    # Popuppens tidslinje viser lukningen som en admin-haendelse.
    assert '"Admin close"' in y
