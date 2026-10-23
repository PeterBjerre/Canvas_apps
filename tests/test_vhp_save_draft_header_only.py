# -*- coding: utf-8 -*-
"""
Issue #566: Save draft kraever kun et gemt planhoved.

  - knappen er aktiv, saa snart planhovedet er gemt - uden items,
  - ufaerdige items gemmes; item-kravene (R2-008) gaelder kun Submit,
  - gemningen og reglerne foer Submit ser de SAMME items,
  - en kladde uden items aabner med eet tomt item,
  - MaintenanceItems' paakraevede kolonner goeres valgfri af
    provisioneringen (ingen nye kolonner),
  - intet flow laeser items fra en kladde (alle VH-planflows starter paa
    MaintenancePlans' status efter Submit).

    python3 -m pytest tests/test_vhp_save_draft_header_only.py
"""
import glob
import json
import os
import re
import sys

from conftest import ROOT

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenVhPlan.pa.yaml")
PROVISION = os.path.join(ROOT, "sharepoint", "provision", "Provision-VHPlanColumns.ps1")
SCHEMA = os.path.join(ROOT, "sharepoint", "inspect", "out", "schema.json")
FLOWS = os.path.join(ROOT, "solution", "BIOSAP", "src", "Workflows")
BUILD = os.path.join(ROOT, "Maintenance Plan App", "build")
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)

import build_load  # noqa: E402
import build_save  # noqa: E402
import build_status  # noqa: E402

RELAXED = ("Title", "ItemDescription", "FunctionalLocation",
           "MaintenanceActivityType", "MainWorkCenter")


def test_draft_button_needs_only_the_plan_header():
    dm = build_save.DRAFT_DM
    assert "!varVhpPlanCommitted" in dm
    assert "CountRows" not in dm
    assert "colVhpItems" not in dm


def test_item_checks_only_block_submit():
    fx = build_save.save_action()
    head = fx[:fx.index("Patch(")]
    # Planhovedet er eneste krav til en kladde.
    assert "    !varVhpPlanCommitted,\n" in head
    # Mindst eet item og de paakraevede felter - kun ved Submit.
    assert f"varVhpSubmitting && {build_save.SAVEABLE_COUNT} = 0" in head
    assert f"varVhpSubmitting && CountRows({build_save.NO_REQ}) > 0" in head
    assert f"!varVhpPlanCommitted || {build_save.SAVEABLE_COUNT}" not in head


def test_save_and_rules_share_one_item_definition():
    assert build_save.SAVEABLE_ITEMS == build_status.SAVEABLE
    s = build_status.SAVEABLE
    for part in ("ShortText", "FunctionalLocation", "MainWorkCenter", "ActivityType",
                 "LongText", "SpId", "colVhpOperations.ItemId"):
        assert part in s, part
    # Det tomme startitem har kun Initials (og en tom tasklist) - de maa
    # ikke goere det "gemmeligt".
    assert "Initials" not in s
    assert "TasklistKey" not in s


def test_loaded_draft_without_items_gets_an_empty_item():
    lb = build_load.load_block()
    i = lb.index("IsEmpty(colVhpItems)")
    assert i < lb.index("Set(varVhpActiveItemId, First(colVhpItems).ItemId)")
    assert "Collect(colVhpItems," in lb[i:i + 200]


def test_generated_screen():
    text = open(SCREEN, encoding="utf-8").read()
    assert "Add at least one item with a short text or functional location first." not in text
    assert "Create the plan and at least one item first." not in text
    assert "Add at least one item before submitting." in text


def _fields(list_title):
    s = json.load(open(SCHEMA, encoding="utf-8-sig"))
    lst = next(l for l in s["lists"] if l["title"] == list_title)
    return {f["internalName"]: f for f in lst["fields"]}


def test_provisioning_relaxes_exactly_the_blocking_columns():
    f = _fields("MaintenanceItems")
    # Kolonnerne findes og er (i udtraekket) paakraevede - derfor scriptet.
    for name in RELAXED:
        assert name in f and f[name]["required"], name
    ps = open(PROVISION, encoding="utf-8-sig").read()
    m = re.search(r"foreach \(\$name in @\(([^)]*)\)\)", ps)
    assert m, "loekken over kolonnerne mangler"
    names = re.findall(r"'([^']+)'", m.group(1))
    assert tuple(names) == RELAXED
    assert "Required = $false" in ps
    # Ingen nye kolonner paa MaintenanceItems ud over den eksisterende.
    assert re.findall(r"New-MdField 'MaintenanceItems' '(\w+)'", ps) == ["OrstedResponsibleEmail"]


def test_no_flow_triggers_on_maintenance_items():
    for p in glob.glob(os.path.join(FLOWS, "BioSap-*.json")):
        d = json.load(open(p, encoding="utf-8-sig"))
        trig = d.get("properties", {}).get("definition", {}).get("triggers", {})
        blob = json.dumps(trig)
        assert "BioSapListMaintenanceItems" not in blob, os.path.basename(p)
