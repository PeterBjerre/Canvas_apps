# -*- coding: utf-8 -*-
"""
Issue #515: hvert handlingsikon har et tooltip, der siger handlingen - og
antallet, hvor ikonet har data - med en matchende AccessibleLabel. Ordlyden
staar eet sted (tools/action_tips.py).

Testene laeser den GENEREREDE skaerm i BIO SAP App og regner de enkle
udtryk ud med en lille Power Fx-fortolker for tallene 0, 1 og 3.

    python3 -m pytest tests/test_action_tips_515.py
"""
import glob
import os
import re
import sys

import yaml

from conftest import ROOT

sys.path.insert(0, os.path.join(ROOT, "tools"))
import action_tips as tips  # noqa: E402

APP = os.path.join(ROOT, "BIO SAP App")


def _controls(path):
    out = {}

    def walk(name, node):
        out[name] = node
        for ch in node.get("Children", []) or []:
            for k, v in ch.items():
                walk(k, v)

    for sk, sv in (yaml.safe_load(open(path, encoding="utf-8")).get("Screens") or {}).items():
        walk(sk, sv)
    return out


def _screen(name):
    return _controls(os.path.join(APP, name))


def _props(ctrls, name):
    assert name in ctrls, name
    return ctrls[name].get("Properties", {})


def _fx_eval(expr, n, locked=False):
    """Regn et tooltip-udtryk fra action_tips ud for antallet n - kun de
    former, modulet selv bygger (With/If/Text/&)."""
    e = expr.lstrip("=")
    e = e.replace("With({ _n: Coalesce(N, 0) }, ", "(").replace("With({ _c: _n }, ", "(")
    e = e.replace("Text(_c)", "str(_n)").replace("_c", "_n")
    e = re.sub(r"\bIf\(", "_if(", e).replace("&", "+").replace(" = ", " == ")
    e = e.replace("LOCKED", "_locked")

    def _if(*a):
        for i in range(0, len(a) - 1, 2):
            if a[i]:
                return a[i + 1]
        return a[-1] if len(a) % 2 else ""

    return eval(e, {"_if": _if, "_n": n, "_locked": locked})


def test_counts_use_singular_and_plural_and_say_none():
    fl = tips.functional_locations("N")
    assert _fx_eval(fl, 0) == "No Functional Locations selected"
    assert _fx_eval(fl, 1) == "1 Functional Location selected"
    assert _fx_eval(fl, 3) == "3 Functional Locations selected"
    docs = tips.documents("N", "LOCKED")
    assert _fx_eval(docs, 0) == "Add documents"
    assert _fx_eval(docs, 0, locked=True) == "No documents"
    assert _fx_eval(docs, 1) == "View 1 document"
    assert _fx_eval(docs, 3) == "View 3 documents"
    att = tips.attachments("N")
    assert _fx_eval(att, 0) == "No attachments"
    assert _fx_eval(att, 2) == "View 2 attachments"
    mfr = tips.filled("manufacturer", "N", "LOCKED")
    assert _fx_eval(mfr, 0) == "Add manufacturer"
    assert _fx_eval(mfr, 0, locked=True) == "No manufacturer"
    assert _fx_eval(mfr, 2) == "Edit manufacturer - 2 fields filled"
    assert _fx_eval(mfr, 1, locked=True) == "View manufacturer - 1 field filled"
    assert _fx_eval(tips.edit_row("LOCKED"), 0) == "Edit row"
    assert _fx_eval(tips.edit_row("LOCKED"), 0, locked=True) == "View row"


def test_shared_row_icons_have_action_tooltips_and_matching_labels():
    pages = {"Mat": ("ScreenMaterial.pa.yaml", ["Open", "Docs", "Objects", "Copy", "Delete"]),
             "Eq": ("ScreenEquipment.pa.yaml", ["Open", "Docs", "Copy", "Delete"]),
             "Mp": ("ScreenMeasuringPoint.pa.yaml", ["Open", "Copy", "Delete"])}
    for p, (screen, acts) in pages.items():
        ctrls = _screen(screen)
        for a in acts:
            for suffix in ("", "C"):
                pr = _props(ctrls, f"btn{p}Row{a}{suffix}")
                tip, lab = pr["Tooltip"], pr["AccessibleLabel"]
                # Tooltippet gentager ikke raekkens noegle; etiketten er
                # tooltippet + noeglen.
                assert "ItemKey" not in tip, (p, a)
                assert lab == tip + ' & " - " & ThisItem.ItemKey', (p, a)
        assert _props(ctrls, f"btn{p}RowCopy")["Tooltip"] == '="Copy row"'
        assert _props(ctrls, f"btn{p}RowDelete")["Tooltip"] == '="Delete row"'
        if "Docs" in acts:
            tip = _props(ctrls, f"btn{p}RowDocs")["Tooltip"]
            # Raekkens egen kolonne - samme tal som Documents-fanen.
            assert "ThisItem.FileCount" in tip and '"View "' in tip
            assert "LookUp(" not in tip and "Filter(" not in tip
    tip = _props(_screen("ScreenMaterial.pa.yaml"), "btnMatRowObjects")["Tooltip"]
    assert '"No Functional Locations selected"' in tip and '" selected"' in tip
    # Den gemte objektliste paa raekken - ingen datakald pr. raekke.
    assert "ThisItem.ObjectList" in tip and "LookUp(" not in tip


def test_toggles_and_other_icon_only_actions_have_tooltips():
    for path in glob.glob(os.path.join(APP, "Screen*.pa.yaml")):
        ctrls = _controls(path)
        for name, node in ctrls.items():
            pr = node.get("Properties", {}) or {}
            if re.match(r"img\w+Theme(Open)?$", name):
                assert "Switch to dark theme" in pr.get("Tooltip", ""), (path, name)
            if re.match(r"img\w+FbSubjectChevron$", name):
                assert pr.get("Tooltip") == pr.get("AccessibleLabel"), (path, name)
    vhp = _screen("ScreenVhPlan.pa.yaml")
    for n in ("imgVhpHelp", "imgVhpHelpOpen"):
        assert "Show help" in _props(vhp, n)["Tooltip"]
    hub = _screen("ScreenMdHub.pa.yaml")
    assert _props(hub, "imgMdRowTimeline")["Tooltip"] == '="View activity"'
    for n in ("btnMdRowDelete", "btnMdRowDeleteC"):
        assert _props(hub, n)["Tooltip"] == '="Delete request"'
    ib = _screen("ScreenIssueBoard.pa.yaml")
    assert _props(ib, "btnIbNew")["Tooltip"] == '="Report a new issue"'
    for n in ("btnIbRowAttach", "btnIbRowAttachC"):
        tip = _props(ib, n)["Tooltip"]
        assert "ThisItem.FileCount" in tip and '"No attachments"' in tip
    fl = _screen("ScreenFunctionalLocation.pa.yaml")
    assert _props(fl, "btnFlEdit")["Tooltip"] == '="Edit this request"'
    for n in ("btnFlRowMfr", "btnFlRowWar", "btnFlRowClassData"):
        tip = _props(fl, n)["Tooltip"]
        # Tallet er de udfyldte felter i colFlVals - samme samling som popuppen.
        assert "CountRows(Filter(colFlVals, RowGuid = ThisItem.RowGuid" in tip, n
        assert '" filled"' in tip, n


def test_every_clickable_icon_only_control_has_a_tooltip_and_a_label():
    """Alle ikoner, der kan klikkes, og som kun er et ikon. Undtaget:
    sidebarens aabne menu (teksten staar ved ikonet), sloer/baggrunde og
    hubbens fliser og New-menu (teksten staar i billedet)."""
    skip = re.compile(r"Nav\w*Open$|Nav(Brand|Lang|PageIcon|Scrim)|Scrim$|Backdrop|Outside|"
                      r"imgMdTile[A-Z]+$|imgMdNew[A-Z]+$")
    missing = []
    for path in glob.glob(os.path.join(APP, "Screen*.pa.yaml")):
        for name, node in _controls(path).items():
            ctl = node.get("Control", "")
            pr = node.get("Properties", {}) or {}
            on = str(pr.get("OnSelect", "")).strip()
            if not on or on == "=false" or skip.search(name):
                continue
            if ctl == "Image" or str(pr.get("Layout", "")) == "=ButtonLayout.IconOnly":
                if not pr.get("Tooltip") or not pr.get("AccessibleLabel"):
                    missing.append((os.path.basename(path), name))
    assert not missing, missing
