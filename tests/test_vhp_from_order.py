# -*- coding: utf-8 -*-
"""
Item fra en SAP-ordre i VH-plan (docs/45, build_order.py, Peter 2026-10-24):
en ikonknap i Items-kortets hoved aabner en popup med ordrenummeret; Fetch
koerer BioSap-Integration-WoeOrder og opretter et nyt item med ordrens
header og en operationslinje pr. operation efter feltmappingen i docs/45.

    python3 -m pytest -q tests/test_vhp_from_order.py
"""
import os
import re

import yaml

from conftest import ROOT

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenVhPlan.pa.yaml")


def _controls():
    d = yaml.safe_load(open(SCREEN, encoding="utf-8").read())
    out, order = {}, []

    def walk(nodes):
        for item in nodes or []:
            for name, c in item.items():
                out[name] = c.get("Properties") or {}
                order.append(name)
                walk(c.get("Children"))

    for s in d["Screens"].values():
        walk(s.get("Children"))
    return out, order


def test_button_in_items_header_between_copy_and_add():
    c, order = _controls()
    head = order.index("btnVhpCopyItem"), order.index("btnVhpFromOrder"), order.index("btnVhpAddItem")
    assert head[0] < head[1] < head[2]
    b = c["btnVhpFromOrder"]
    assert b["Layout"] == "=ButtonLayout.IconOnly"
    assert "SAP order" in b["Tooltip"]
    assert "Set(varVhpOrderOpen, true)" in b["OnSelect"]
    assert "!varVhpViewOnly" in b["Visible"]


def test_popup_has_one_field_and_fetch():
    c, _ = _controls()
    for name in ("conVhpOrderModal", "txtVhpOrderTitle", "btnVhpOrderClose", "txtVhpOrderNote",
                 "inpVhpOrderNo", "btnVhpOrderFetch", "txtVhpOrderMsg"):
        assert name in c, name
    assert c["conVhpOrderModal"]["Visible"] == "=varVhpOrderOpen"
    assert "25711067" in c["inpVhpOrderNo"]["Placeholder"]
    assert "varVhpOrderBusy" in c["btnVhpOrderFetch"]["DisplayMode"]
    # X lukker ikke, mens opslaget koerer; sloeret heller ikke.
    assert "!varVhpOrderBusy" in c["btnVhpOrderClose"]["OnSelect"]
    bd = c["conVhpPickerBackdrop"]
    assert "varVhpOrderOpen" in bd["Visible"] and "!varVhpOrderBusy" in bd["OnSelect"]


def test_fetch_maps_the_order_as_decided():
    """Peter 2026-10-24: hovedarbejdsplads fra foerste operation, actual
    hours (ikke planned), ingen taskliste-gruppe nu; status/partner/
    activities/causes/feedback bruges ikke."""
    c, _ = _controls()
    fx = c["btnVhpOrderFetch"]["OnSelect"]
    assert "'BioSap-Integration-WoeOrder'.Run(o)" in fx
    assert "ParseJSON(varVhpOrderRaw.result)" in fx
    assert "Press Save in the plan header before adding items." in fx
    # Item: header -> ShortText/LongText/FL/Initials, foerste operations workCenter.
    assert "hdr.shortDescription" in fx and "Text(ht.text)" in fx
    assert "Text(hdr.functionalLocation)" in fx
    assert 'r.header.data, ParseJSON("{}")' in fx and 'r.headerText.data, ParseJSON("{}")' in fx
    assert "hdr.responsibleInitials" in fx
    assert "First(ops).Value.workCenter" in fx
    assert "LookUp(colVhpMainWorkCenters, Value = wc)" in fx
    assert '= "ZBOW"' in fx
    assert "TasklistKey: \"\"" in fx
    # Operationer: id, description, actualHours, workCenter, controlKey, vendor, langtekst.
    assert 'Text(Value(O.Value.id), "0000")' in fx
    assert "O.Value.actualHours" in fx and "plannedHours" not in fx
    assert "O.Value.controlKey" in fx and "O.Value.vendorId" in fx
    assert "Text(ThisRecord.Value.objectId) = Text(O.Value.objectId)" in fx
    # Objekter: udstyr eller FL, minus itemets egen FL; som Copy ryddes FL fra et andet vaerk.
    assert "Code <> \"\" && Code <> fl" in fx
    assert "keepFl" in fx and "Collect(\n" in fx
    for sec in ("partner", "activities", "causes", "feedback"):
        assert f"r.{sec}" not in fx, sec
    # Sektioner uden 200 bliver tomme tabeller, ikke en fejl.
    assert 'Table(ParseJSON("[]"))' in fx
    # Collect uden om ForAll (App checker).
    assert not re.search(r"ForAll\([^)]*Collect\(", fx)


def test_open_sets_the_popup_variables():
    """Domaenets OnStart koerer paa den skjulte knap btnVhpOpen i den samlede app."""
    c, _ = _controls()
    on = c["btnVhpOpen"]["OnSelect"]
    for v in ("Set(varVhpOrderOpen, false)", "Set(varVhpOrderBusy, false)", 'Set(varVhpOrderMsg, "")'):
        assert v in on, v
