# -*- coding: utf-8 -*-
"""
Issue #471: kolonnen SAP OBJECT i hubbens Closed-visning og popuppen med
de SAP-objekter, anmodningen har oprettet.

    python3 -m pytest tests/test_hub_sap_objects.py
"""
import os
import re
import sys

from conftest import ROOT

for p in (os.path.join(ROOT, "tools"), os.path.join(ROOT, "Masterdata Hub", "build")):
    if p not in sys.path:
        sys.path.insert(0, p)
import build_hub as bh  # noqa: E402
import sap_objects as so  # noqa: E402
from test_hub_approval_pill_mine import _eval, _layout  # noqa: E402

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenMdHub.pa.yaml")
APP = os.path.join(ROOT, "BIO SAP App", "App.pa.yaml")


def _yaml():
    return open(SCREEN, encoding="utf-8").read()


def _block(text, name):
    i = text.index(f"- {name}:")
    j = text.find("\n" + " " * (len(text[:i]) - len(text[:i].rstrip(" "))) + "- ", i + 1)
    return text[i:j if j > 0 else None]


def test_column_sits_between_status_and_updated():
    keys = [k for k, _w in bh.COLS]
    assert keys.index(bh.SAP_COL) == keys.index("STATUS") + 1
    assert keys.index("UPDATED") == keys.index(bh.SAP_COL) + 1
    assert bh.SAP_COL == "SAP OBJECT"


def test_only_text_gives_room_and_only_in_closed():
    for width in (1366, 1600, 1920, 2560):
        for view in ("mine", "all"):
            w = {c: {k: _eval(bh.CWF[k], view, width=width, closed=c) for k, _w in bh.COLS}
                 for c in (False, True)}
            assert w[False][bh.SAP_COL] == 0
            assert w[True][bh.SAP_COL] == bh.SAP_W
            assert w[False]["TEXT"] - w[True]["TEXT"] == bh.SAP_W + bh.GAP
            for k, _w in bh.COLS:
                if k not in ("TEXT", bh.SAP_COL):
                    assert w[False][k] == w[True][k], (k, width, view)
            # Updated og Actions staar stille; col_x passer med containeren.
            lo, lc = _layout(view, width=width), _layout(view, width=width, closed=True)
            for k in ("UPDATED", "ACTIONS"):
                assert abs(lo[k] - lc[k]) < 1e-6, (k, width, view)
            assert abs(_eval(bh.col_x(bh.SAP_COL), view, width=width, closed=True)
                       - lc[bh.SAP_COL]) < 1e-6
            assert abs(_eval(bh.col_x("ACTIONS"), view, width=width, closed=True)
                       - lc["ACTIONS"]) < 1e-6


def test_header_and_icon_only_in_closed_and_icon_from_index_row():
    y = _yaml()
    i = [k for k, _w in bh.COLS].index(bh.SAP_COL)
    head = _block(y, f"txtMdH{i}")
    assert '="SAP OBJECT"' in head and bh.SAP_SHOWN in head
    icon = _block(y, "imgMdRowSap")
    assert '="View SAP objects"' in icon
    vis = re.search(r"Visible: \|-\n\s+=(.*)\n", icon).group(1)
    assert bh.SAP_SHOWN in vis and "ThisItem.SapObjectNo" in vis and '"OprettetISAP"' in vis
    # Intet opslag pr. raekke - kun indeksraekkens egne felter.
    assert "LookUp(" not in vis and "Filter(" not in vis


def test_objects_are_loaded_only_when_the_popup_opens():
    y = _yaml()
    app = open(APP, encoding="utf-8").read()
    assert "colMdSapRows" not in app and so.OPTION not in app
    on_select = _block(y, "imgMdRowSap").split("OnSelect:", 1)[1].split("PressedFill:", 1)[0]
    for lst in ("MaintenancePlans", "MaintenanceItems", "FunctionalLocationItems",
                "MaterialItems", "EquipmentItems", "AppSettings"):
        assert lst in on_select, lst
    # Ingen af dem i galleriets Items eller OnVisible.
    assert "AppSettings" not in bh.HUB_ON_VISIBLE and "colMdSapRows" not in bh.ITEMS
    # Delegerede filtre paa de samme kolonner som sletningen.
    assert "Filter(MaintenanceItems, MaintenancePlanNo.Value = varMdSapKey)" in on_select
    assert "LookUp(MaintenancePlans, ID = varMdSapSp)" in on_select
    for lst in ("FunctionalLocationItems", "MaterialItems", "EquipmentItems"):
        assert f"Filter({lst}, RequestGuid = varMdSapGuid)" in on_select


def test_no_sap_host_in_the_app():
    for path in (SCREEN, APP):
        text = open(path, encoding="utf-8").read()
        assert not re.search(r"https?://[^\"' ]*webgui", text, re.I), path
    assert f'Option.Value = "{so.OPTION}"' in so.BASE_FX
    assert ".AppUrl" in so.BASE_FX


def _fx_eval(expr, base):
    """url_fx med tekstkonstanter som Python: If, &&, !IsBlank, Trim, EncodeUrl."""
    py = (expr.replace(so.BASE, repr(base)).replace("&&", " and ").replace("!IsBlank(", "not IsBlank(")
          .replace(" & ", " + "))
    env = {"If": lambda c, a, b: a if c else b, "IsBlank": lambda v: v in (None, ""),
           "Trim": lambda v: v.strip(), "EncodeUrl": lambda v: v.replace(" ", "%20")}
    return eval(py, env)


def test_urls_use_each_objects_own_number():
    b = "https://sap.example/webgui"
    assert _fx_eval(so.url_fx("plan", '"37013402"'), b) == (
        b + "?~transaction=*IP03%20RMIPM-WARPL=37013402;&sap-language=EN")
    assert _fx_eval(so.url_fx("item", '"34014290"'), b) == (
        b + "?~transaction=*IP06%20RMIPM-WAPOS=34014290&sap-language=EN")
    assert _fx_eval(so.url_fx("tasklist", '"PMSSV01"', '"2"'), b) == (
        b + "?~transaction=*IA06%20RC271-PLNNR=PMSSV01;RC271-PLNAL=2;&sap-language=EN;DYNP_OKCODE=VOUE")
    # Ingen link uden adresse eller uden et helt saet vaerdier.
    assert _fx_eval(so.url_fx("plan", '"37013402"'), "") == ""
    assert _fx_eval(so.url_fx("tasklist", '"PMSSV01"', '""'), b) == ""
    assert _fx_eval(so.url_fx("item", '" "'), b) == ""


def test_plan_hierarchy_reads_the_stored_receipt_fields():
    fx = so.open_fx()
    for field in ("SAPNum", "SapItemNo", "TaskListGroup", "TaskListGroupCounter",
                  "CreatedMaterialNo", "EquipmentNumber", "FunctionalLocation"):
        assert field in fx, field
    if so.MP_ON:
        assert "CreatedMeasuringPointNo" in fx
    assert "Lvl: 0" in fx and "Lvl: 1" in fx and "Lvl: 2" in fx


def test_popup_is_read_only_with_the_x_close():
    y = _yaml()
    pop = _block(y, "conMdSapBackdrop")
    assert "- btnMdSapClose:" in pop
    no = _block(pop, "inpMdSapNo")
    assert "DisplayMode.View" in no
    link = _block(pop, "imgMdSapLogo")
    assert "=Launch(ThisItem.Url)" in link and "=!IsBlank(ThisItem.Url)" in link
    # Ingen Patch/Remove i popuppen.
    assert "Patch(" not in pop and "Remove(" not in pop


# ---------------------------------------------------------------------------
# Issue #488: kolonnen ogsaa i All, og popuppen som mockuppen
# (pictures/sap_popup.png).
# ---------------------------------------------------------------------------
def _prop(block, key):
    m = re.search(rf"\n\s+{key}: \|-\n\s+=(.*)\n", block)
    return m.group(1) if m else None


def test_column_shows_in_closed_and_all_but_not_open():
    def shown(mode):
        return eval(bh.SAP_SHOWN.replace("varMdStatusMode", repr(mode))
                    .replace("||", " or ").replace(" = ", " == "))
    assert shown("done") and shown("all") and not shown("open")
    y = _yaml()
    i = [k for k, _w in bh.COLS].index(bh.SAP_COL)
    assert bh.SAP_SHOWN in _prop(_block(y, f"txtMdH{i}"), "Visible")
    # Ikonet kun for anmodninger med SAP-objekter - ellers er cellen tom.
    vis = _prop(_block(y, "imgMdRowSap"), "Visible")
    assert bh.SAP_SHOWN in vis and so.HAS_SAP in vis
    assert bh.SAP_SHOWN in _prop(_block(y, "txtMdRowSap"), "Visible")


def test_popup_rows_follow_the_hierarchy_and_right_icons_line_up():
    pop = _block(_yaml(), "conMdSapBackdrop")
    lvl = f"ThisItem.Lvl * {so.INDENT}"
    # Bjaelken med objekttypen og nummeret rykkes ind pr. niveau.
    assert _prop(_block(pop, "txtMdSapKind"), "X") == lvl
    assert _prop(_block(pop, "inpMdSapNo"), "X").startswith(lvl)
    assert _prop(_block(pop, "txtMdSapKind"), "Text") == "ThisItem.Kind"
    # "L"-et foran under-niveauerne.
    for name in ("rctMdSapTreeV", "rctMdSapTreeH"):
        assert _prop(_block(pop, name), "Visible") == "ThisItem.Lvl > 0"
    # SAP-maerket: samme x i alle niveauer, kun med en URL.
    logo = _block(pop, "imgMdSapLogo")
    assert "ThisItem.Lvl" not in _prop(logo, "X")
    assert _prop(logo, "Visible") == "!IsBlank(ThisItem.Url)"
    assert _prop(logo, "OnSelect") == "Launch(ThisItem.Url)"
    # Nummeret er markerbar tekst uden ramme, med kopier-ikonet lige efter.
    no = _block(pop, "inpMdSapNo")
    assert _prop(no, "BorderThickness") == "0" and "DisplayMode.View" in no
    copy = _block(pop, "btnMdSapCopy")
    assert "Copy(ThisItem.No)" in copy
    assert _prop(copy, "X").startswith(_prop(no, "X") + " + ")


# ---------------------------------------------------------------------------
# Issue #500: een "Open in SAP"-handling (SAP-maerket) yderst til hoejre, og
# kopier-ikonet taet ved nummeret: nummer -> kopier -> beskrivelse -> SAP.
# ---------------------------------------------------------------------------
def _px(expr, no="37013402", lvl=0, rank=3, hit=32, w=1366):
    """Et X/Width-udtryk fra popuppen som tal (Min/Max/If/RoundUp/Len)."""
    py = (expr.replace("ThisItem.Lvl", str(lvl)).replace("ThisItem.No", repr(no))
          .replace("LayoutRank", str(rank)).replace("H.hit", str(hit))
          .replace("App.Width", str(w)).replace("!IsBlank(ThisItem.Url)", "True"))
    env = {"Min": min, "Max": max, "Len": len, "If": lambda c, a, b: a if c else b,
           "RoundUp": lambda v, d: -(-v // 1),
           "IsMatch": lambda v, pat: re.fullmatch(pat, v) is not None}
    return eval(py, env)


def test_only_one_open_in_sap_action_at_the_far_right():
    pop = _block(_yaml(), "conMdSapBackdrop")
    assert "imgMdSapLink" not in pop
    assert pop.count("=Launch(ThisItem.Url)") == 1
    logo = _block(pop, "imgMdSapLogo")
    assert _prop(logo, "Tooltip") == '"Open in SAP"'
    assert _prop(logo, "AccessibleLabel") == '"Open in SAP"'
    # Hover, tryk og tastaturfokus kan ses.
    for key in ("HoverFill", "PressedFill", "HoverBorderColor", "PressedBorderColor",
                "FocusedBorderColor"):
        assert _prop(logo, key), key
    assert _prop(logo, "HoverFill") != _prop(logo, "PressedFill")
    assert _prop(logo, "FocusedBorderThickness") == "2" and _prop(logo, "TabIndex") == "0"
    # Hoejre kant = bjaelkernes hoejre kant - 8, paa alle bredder.
    for w in (390, 800, 1366):
        right = _px(so.RIGHT, w=w)
        assert _px(_prop(logo, "X"), w=w) + so.SAP_LOGO_W == right


def test_copy_icon_sits_close_to_the_number_before_the_description():
    pop = _block(_yaml(), "conMdSapBackdrop")
    no, copy, desc = (_block(pop, k) for k in ("inpMdSapNo", "btnMdSapCopy", "txtMdSapDesc"))
    assert '"Copy SAP number"' in _prop(copy, "Tooltip")
    assert '"Copy SAP number"' in _prop(copy, "AccessibleLabel")
    for number in ("37013402", "PMSSV01", "1"):
        for rank, hit in ((3, 32), (1, 44)):
            for lvl in (0, 1, 2):
                kw = dict(no=number, lvl=lvl, rank=rank, hit=hit)
                size = 16 if rank < 2 else 14
                ch = so.NO_CH_DIGITS if number.isdigit() else so.NO_CH
                text_end = (_px(_prop(no, "X"), **kw) + so.NO_PAD
                            + len(number) * ch * size)
                cx, cw = _px(_prop(copy, "X"), **kw), hit
                icon_left = cx + (cw - so.COPY_ICON) / 2
                # Issue #504: kun et mellemrums afstand (ca. 4 px).
                assert 3 <= icon_left - text_end <= 5, (number, rank, lvl)
                # Feltet daekker teksten; knappen slutter foer beskrivelsen.
                assert (_px(_prop(no, "X"), **kw) + _px(_prop(no, "Width"), **kw)
                        >= text_end)
                dx = _px(_prop(desc, "X"), **kw)
                assert dx >= cx + cw and dx - (icon_left + so.COPY_ICON) >= 12
                # Beskrivelsen slutter foer SAP-knappen.
                assert dx + _px(_prop(desc, "Width"), **kw) <= _px(_prop(
                    _block(pop, "imgMdSapLogo"), "X"), **kw) - 10


# ---------------------------------------------------------------------------
# Issue #504 (pictures/sap_popup_copy.png): een indrammet Open in SAP-knap
# uden skillestreg foran, een skillestreg mellem nummer/kopier og
# beskrivelse, og en kort lokal "Copied"-kvittering.
# ---------------------------------------------------------------------------
def test_open_in_sap_is_one_outlined_button_without_a_separator_before_it():
    pop = _block(_yaml(), "conMdSapBackdrop")
    assert "- rctMdSapSep:" not in pop
    logo = _block(pop, "imgMdSapLogo")
    # Rammen ses i hvile (ikke gennemsigtig) - og hele knappen er een Image.
    assert _prop(logo, "BorderColor") == "C.'border-input'"
    assert _prop(logo, "BorderThickness") == "1"
    img = _prop(logo, "Image")
    assert ">SAP</text>" in img and "M69 9l-8 8" in img
    assert f"width='{so.SAP_LOGO_W}'" in img
    assert _prop(logo, "Width") == str(so.SAP_LOGO_W)
    # Ingen kolonneoverskrift for handlingen.
    assert "Open in SAP" not in _prop(_block(pop, "txtMdSapKind"), "Text")


def test_one_separator_between_number_group_and_description():
    pop = _block(_yaml(), "conMdSapBackdrop")
    sep, copy, desc = (_block(pop, k) for k in ("rctMdSapNoSep", "btnMdSapCopy", "txtMdSapDesc"))
    assert _prop(sep, "Visible") is None
    for number in ("37013402", "PMSSV01"):
        for rank, hit in ((3, 32), (1, 44)):
            kw = dict(no=number, rank=rank, hit=hit)
            sx = _px(_prop(sep, "X"), **kw)
            assert _px(_prop(copy, "X"), **kw) + hit <= sx < _px(_prop(desc, "X"), **kw)


def test_copy_gives_brief_local_feedback():
    y = _yaml()
    pop = _block(y, "conMdSapBackdrop")
    copy = _block(pop, "btnMdSapCopy")
    assert "Copy(ThisItem.No)" in copy and f"Set({so.COPIED_VAR}, {so.ROW_KEY})" in copy
    assert "gblToast" not in copy and "Notify(" not in copy
    assert _prop(copy, "Icon") == f'If({so.COPIED}, "Checkmark", "Copy")'
    done = _block(pop, "txtMdSapCopied")
    assert _prop(done, "Text") == '"Copied"' and _prop(done, "Visible") == so.COPIED
    assert _prop(_block(pop, "txtMdSapDesc"), "Visible") == f"!{so.COPIED}"
    # Timeren nulstiller kvitteringen, og popuppen starter uden.
    tmr = _block(y, "tmrMdSapCopied")
    assert _prop(tmr, "Duration") == str(so.COPIED_MS)
    assert _prop(tmr, "OnTimerEnd") == f'Set({so.COPIED_VAR}, "")'
    assert f'Set({so.COPIED_VAR}, "")' in so.open_fx()
