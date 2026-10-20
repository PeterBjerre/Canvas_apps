# -*- coding: utf-8 -*-
"""
Issue #390: en gemt Maintenance Plan aabnet i View maa ikke kunne aendres.
varVhpViewOnly styrer alle kontroller, der aendrer data - ogsaa i
popup'erne (materialer, dokumenter, varegruppe) og pakkerne.

    python3 -m pytest tests/test_vhp_view_lock.py
"""
import os
import re

import yaml

from conftest import ROOT

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenVhPlan.pa.yaml")
VIEW = "varVhpViewOnly"
HANDLERS = ("OnSelect", "OnCheck", "OnUncheck", "OnChange")
# Skriver til planens data (samlingerne, der gemmes).
WRITES = re.compile(r"(Patch|Collect|RemoveIf|Remove|UpdateIf)\(\s*colVhp(Operations|Materials|Items|ItemObjects)\b")
# Indlaesning, ny anmodning og sletning er ikke redigering af planen.
# Docs-knapperne skriver kun det hentede filantal (FileCount) paa linjen.
NOT_EDITING = {"btnVhpOpen", "btnVhpNewConfirm", "btnVhpReqDelConfirm", "btnVhpNewRequest",
               "btnVhpOpDocs", "btnVhpOpMDocs"}


# Issue #433: en gemt sektion (Item, Task list and operations) er laast som
# i View - laasen staar som "(varVhpViewOnly || <sektionens laas>)". Her
# laeses den som varVhpViewOnly, saa View-reglerne nedenfor tjekkes som foer.
_LOCK = r'IfError\(varVhpActiveItemId in Filter\(colVhpSectionLocks, Section = "(?:Item|Ops)"\)\.ItemId, false\)'
_VIEW_OR_LOCK = re.compile(
    r'\(varVhpViewOnly \|\| (?:%s|If\(varVhpLongTextTarget = "item", %s, %s\))\)' % (_LOCK, _LOCK, _LOCK))


def without_section_locks(text):
    return _VIEW_OR_LOCK.sub(VIEW, text)


def _controls():
    d = yaml.safe_load(without_section_locks(open(SCREEN, encoding="utf-8").read()))
    out = {}

    def walk(nodes, guards):
        for item in nodes or []:
            for name, c in item.items():
                p = c.get("Properties") or {}
                own = str(p.get("DisplayMode", "")) + str(p.get("Visible", ""))
                out[name] = (c.get("Control", ""), p, own, guards)
                walk(c.get("Children"), guards + own)

    for s in d["Screens"].values():
        walk(s.get("Children"), "")
    return out


def test_every_data_change_is_locked_in_view():
    bad = []
    for name, (_ctl, p, own, guards) in _controls().items():
        acts = " ".join(str(p.get(k, "")) for k in HANDLERS)
        if name in NOT_EDITING or not WRITES.search(acts):
            continue
        # Laast paa kontrollen, en forfader - eller i selve handlingen.
        if VIEW not in own + guards + acts:
            bad.append(name)
    assert not bad, "kan aendre data i View: " + ", ".join(sorted(bad))


def test_named_controls_follow_view_mode():
    c = _controls()
    # Materialepopup'en: Add/Remove slaaet fra, raekkevalg skrivebeskyttet.
    for name in ("btnVhpAddMaterial", "btnVhpRemoveMaterial"):
        assert VIEW in c[name][1]["DisplayMode"] and "DisplayMode.Disabled" in c[name][1]["DisplayMode"], name
    for name in ("chkVhpMatSel", "btnVhpMgHit"):
        assert c[name][1]["DisplayMode"].strip() == f"=If({VIEW}, DisplayMode.View, DisplayMode.Edit)", name
    # Felterne i materialepopup'en laases af gen_screen.
    for name in ("inpVhpMatNo", "inpVhpMatQty"):
        assert VIEW in c[name][1]["DisplayMode"], name
    # Pakkerne: Fill by hierarchy, All og Clear.
    for name in ("btnVhpPkgHierarchy", "btnVhpPkgAll", "btnVhpPkgClear", "btnVhpOpMRemove"):
        assert VIEW in c[name][1]["DisplayMode"], name
    # Dokumenter: View (kan stadig aabnes og hentes), ingen gem-knap.
    att = c["attVhpAttPicker"][1]["DisplayMode"]
    assert VIEW in att and "DisplayMode.View" in att
    assert VIEW in c["btnVhpAttUpload"][2] + c["btnVhpAttUpload"][3]
    # Tom item-liste: ingen egen Add item mere (issue #459) - kun kortets.
    assert "btnVhpItemsEmptyAdd" not in c


def test_view_and_read_actions_stay_open():
    c = _controls()
    for name in ("btnVhpOpMaterials", "btnVhpOpDocs", "btnVhpOpMMat", "btnVhpOpMDocs"):
        assert VIEW not in str(c[name][1].get("DisplayMode", "")), name


PILLS = ("VhpPkg", "VhpOp", "VhpOpM")   # matricen, operationsraekken, popup'en


def test_package_pills_are_inert_in_view():
    """Issue #408: i View er pakke-pillerne kun et billede af det gemte
    valg. Kliklaget er skjult og slaaet fra, saa et klik hverken skifter
    pakken, koerer en formel eller tegner noget ekstra ved pillen."""
    c = _controls()
    for p in PILLS:
        hit = c[f"btn{p}PillHit"][1]
        assert hit["Visible"].strip() == f"=!{VIEW}", p
        assert hit["DisplayMode"].strip() == f"=If({VIEW}, DisplayMode.Disabled, DisplayMode.Edit)", p
        assert hit["OnSelect"].strip().startswith(f"=If(!{VIEW},"), p
        # Pillen selv bliver staaende og viser det gemte valg - ogsaa for
        # skaermlaeseren, nu hvor laget med teksten er vaek.
        img = c[f"img{p}Pill"][1]
        assert "Visible" not in img, p
        assert "ThisItem.Sel" in img["Image"] and VIEW in img["AccessibleLabel"], p
        assert not any(k in img for k in HANDLERS), p
