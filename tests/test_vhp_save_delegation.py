# -*- coding: utf-8 -*-
"""
Gemmekaedens filtre mod MaintenanceItems/TaskListMain er delegerbare
(review R2-007).

With({ex: Filter(<liste>, ...)}) bryder delegeringen: ex har kun de
foerste 500/2.000 raekker af LISTEN, ikke af planen. Naar listen voksede
forbi loftet, fandt opdateringen ikke planens raekker (dubletter), og
oprydningen lod foraeldreloese raekker staa. Nu hentes planens raekker
med et rent filter mod en global variabel ind i en samling, og opslag og
sletning sker i den.

    python3 -m pytest tests/test_vhp_save_delegation.py
"""
import os
import re
import sys

from conftest import ROOT

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenVhPlan.pa.yaml")
BUILD = os.path.join(ROOT, "Maintenance Plan App", "build")
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)

import build_save  # noqa: E402


def _text():
    return open(SCREEN, encoding="utf-8").read()


def test_no_with_filter_on_items_or_tasks_in_screen():
    text = _text()
    assert "ex: Filter(MaintenanceItems" not in text
    assert "ex: Filter(TaskListMain" not in text


def test_save_steps_have_no_with_filter_on_lists():
    for fn in (build_save._step_items, build_save._step_ops, build_save._step_cleanup):
        fx = fn()
        for lst in ("MaintenanceItems", "TaskListMain", "MD_TasklistMaterial",
                    "MD_TasklistAttachment"):
            assert not re.search(r"\{\s*ex:\s*Filter\(" + lst, fx), (fn.__name__, lst)
            # Ingen opslag i en scope-variabel om listen.
            assert "LookUp(ex," not in fx and "Filter(ex," not in fx, fn.__name__


def test_plan_filters_compare_with_a_plain_global():
    fx = build_save._step_items() + build_save._step_ops()
    assert "Filter(MaintenanceItems, MaintenancePlanNo.Value = varVhpPlanKeyQ)" in fx
    assert "Filter(TaskListMain, MaintenancePlanID.Value = varVhpPlanKeyQ)" in fx
    assert 'Coalesce(varVhpPlanKey, "-")' not in fx
    # Variablen saettes, saa snart noeglen er kendt (trin 3).
    assert 'Set(varVhpPlanKeyQ, Coalesce(varVhpPlanKey, "-"))' in build_save._step_plan()


def test_update_and_cleanup_use_the_plans_own_rows():
    items, ops, clean = build_save._step_items(), build_save._step_ops(), build_save._step_cleanup()
    assert "LookUp(colVhpSpItemRows, ID = IT.SpId)" in items
    assert "LookUp(colVhpSpOpRows, ID = OP.SpId)" in ops
    assert "Remove(MaintenanceItems, Filter(colVhpSpItemRows, !(ID in colVhpSavedItems.SpId)))" in clean
    assert "Remove(TaskListMain, Filter(colVhpSpOpRows, !(ID in colVhpSavedOps.SpId)))" in clean
