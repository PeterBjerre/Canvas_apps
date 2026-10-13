# -*- coding: utf-8 -*-
"""De faelles hjaelpere fra UX-review 2026-10 (etape 1).

status_chip (T4), empty_state (F4/T9), breadcrumb (F9), request_actions
og Submit-taelleren (T1), H.hit og ensure_hit (F6/T10, check_layout regel
40), Title Case-reglen i check_language (F1/T7), prefs_save (F8), plural
og short_text (B4), Stuck-reglen og num_text (B2) - og datoformatet."""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import build_helpers as bh  # noqa: E402
import check_language as cl  # noqa: E402
import design_tokens as tok  # noqa: E402
import display_text as dt  # noqa: E402
import layout_tokens as lay  # noqa: E402
import request_index as ri  # noqa: E402
import status_chip as sc  # noqa: E402


# --- datoer -----------------------------------------------------------------
def test_dates_are_dd_mm_yyyy_everywhere():
    # Organisationens datoformat - tekst og datovaelgere ens.
    assert lay.DATE_FMT == "dd-mm-yyyy"
    assert lay.DATETIME_FMT == "dd-mm-yyyy hh:mm"
    assert lay.DATE_PICKER_FMT == lay.DATE_FMT


def test_the_built_screens_use_no_other_date_format():
    import glob
    import re
    for path in glob.glob(os.path.join(ROOT, "BIO SAP App", "Screen*.pa.yaml")):
        y = open(path, encoding="utf-8").read()
        for fmt in ("yyyy-mm-dd", "dd/mm/yyyy", "dd mmm yyyy", "mm/dd/yyyy"):
            assert fmt not in y, (os.path.basename(path), fmt)
        assert not re.search(r"DateTimeFormat\.(Short|Long)Date", y), path


# --- tal --------------------------------------------------------------------
def test_num_text_is_culture_locked_and_blank_safe():
    fx = lay.num_text("x")
    assert '"en-US"' in fx and "IsBlank(_n)" in fx and '"#,##0.##"' in fx


# --- statuschippen -------------------------------------------------------------
def test_one_chip_per_status_with_icon_and_sentence_case_label():
    for table in (sc.REQUEST, sc.ROW):
        for key, label, path, tone in table:
            assert label[0].isupper() and label[1:] == label[1:].lower() or " " in label, label
            assert path and tone in ("neutral", "info", "violet", "warn", "ok", "lime",
                                     "error", "rose"), (key, tone)


def test_the_chip_is_an_image_as_wide_as_the_widest_label():
    c = sc.status_chip("imgXStatus", "ThisItem.Status", sc.ROW)
    assert c.control == "Image"
    assert c.props["Width"] == str(sc.table_width(sc.ROW))
    assert c.props["TabIndex"] == "0" and c.props["OnSelect"] == "false"
    assert '"Status: "' in c.props["AccessibleLabel"]
    for key, label, _p, _t in sc.ROW:
        assert f'"{key}"' in c.props["Image"] and label in c.props["Image"]


def test_normal_priority_is_plain_text_and_only_urgent_and_high_have_colour():
    tones = {k: t for k, _l, _p, t in sc.PRIORITY}
    assert tones["Normal"] == tones["Low"] == "plain"
    assert tones["Urgent"] == "error" and tones["High"] == "warn"
    svg = sc._chip_svg("Normal", None, "plain", 60)
    assert "<rect" not in svg


# --- tom liste ---------------------------------------------------------------
def test_empty_state_has_icon_sentence_and_one_button():
    g = bh.empty_state("conXEmpty", '"No rows yet."', "Add row", "Set(a, 1)",
                       button_name="btnXEmptyAdd")
    names = [c.name for c in g.children]
    assert names == ["imgXEmptyIcon", "txtXEmptyText", "btnXEmptyAdd"]
    assert g.children[2].props["OnSelect"] == "Set(a, 1)"


def test_empty_state_without_action_has_no_button():
    g = bh.empty_state("conXEmpty", '"Nothing here."')
    assert [c.control for c in g.children] == ["Image", "ModernText"]


# --- broedkrummen --------------------------------------------------------------
def test_breadcrumb_links_back_to_the_hub_and_shows_the_page_and_id():
    g = bh.breadcrumb("Eq", "equipment", "varEqReqNo")
    hub, tail = g.children
    assert hub.control == "Image" and hub.props["OnSelect"] != "false"
    assert hub.props["AccessibleLabel"] == '"Back to Masterdata Hub"'
    assert "Equipments" in tail.props["Text"] and "varEqReqNo" in tail.props["Text"]
    assert g.props["Height"] == str(bh.CRUMB_H)


# --- headerens knapper ---------------------------------------------------------
def test_request_actions_order_and_submit_counter():
    new = bh.button("btnXNew", '"New request"', "false", width=100, height=36)
    save = bh.button("btnXSave", '"Save draft"', "false", width=100, height=36)
    sub = bh.button("btnXSubmit", '"Submit"', "false", width=100, height=36)
    out = bh.request_actions("X", new, save, sub, fix_expr="CountRows(colErr)")
    assert [c.name for c in out] == ["btnXNew", "conXHeadSep", "btnXSave", "btnXSubmit"]
    assert '" to fix)"' in sub.props["Text"] and "CountRows(colErr)" in sub.props["Text"]
    assert sub.props["Width"] == str(bh.fit_button_width(bh.SUBMIT_FIX_LONGEST))


def test_row_list_uses_direct_template_controls_and_accessible_selection():
    text = bh.text_ctrl("txtXRowTitle", "ThisItem.Title")
    gallery = bh.row_list("X", "colRows", [text], 360, 56,
                          onselect="Set(varSelected, ThisItem.ID)",
                          accessible="Saved request rows")
    assert gallery.name == "galXRows"
    assert gallery.control == "Gallery" and gallery.children == [text]
    assert gallery.props["Items"] == "colRows"
    assert gallery.props["OnSelect"] == "Set(varSelected, ThisItem.ID)"
    assert gallery.props["TabIndex"] == "0"
    assert gallery.props["AccessibleLabel"] == '"Saved request rows"'


def test_row_editor_panel_has_responsive_width_navigation_and_fixed_footer():
    section = bh.group("conXSection", [])
    footer = bh.group("conXFooter", [])
    backdrop, panel = bh.row_editor_panel(
        "X", '"Row 2 of 3"', [section], footer,
        "Set(varRow, varRow - 1)", "Set(varRow, varRow + 1)",
        "Set(varEditorOpen, false)", "varEditorOpen",
        previous_mode="If(varRow = 1, DisplayMode.Disabled, DisplayMode.Edit)")
    assert backdrop.name == "imgXEditorBackdrop"
    assert backdrop.props["OnSelect"] == "Set(varEditorOpen, false)"
    assert panel.name == "conXEditorPanel"
    assert "LayoutRank >= 3" in panel.props["Width"] and "480" in panel.props["Width"]
    heading, scroll, panel_footer = panel.children
    assert heading.children[0].props["Text"] == '"Row 2 of 3"'
    assert [child.props["OnSelect"] for child in heading.children[1].children] == [
        "Set(varRow, varRow - 1)", "Set(varRow, varRow + 1)", "Set(varEditorOpen, false)"]
    assert heading.children[1].children[0].props["DisplayMode"].startswith("If(varRow = 1")
    assert scroll.children == [section] and scroll.props["LayoutOverflowY"] == "LayoutOverflow.Scroll"
    assert panel_footer is footer


def test_request_shell_keeps_editor_overlay_above_the_app_frame():
    header = bh.group("conXHeaderContent", [])
    crumb = bh.group("conXCrumb", [])
    actions = bh.group("conXActions", [])
    rows = bh.group("conXRows", [])
    backdrop = bh.group("conXBackdrop", [])
    panel = bh.group("conXPanel", [])
    screen = bh.request_shell("X", header, crumb, actions, rows,
                              editor=[backdrop, panel])
    assert screen[0].name == "conXRoot"
    assert screen[1:] == [backdrop, panel]
    assert screen[0].children[1].children == [crumb, actions, rows]


# --- klikfladen ----------------------------------------------------------------
def test_h_hit_is_32_on_desktop_and_44_on_touch():
    assert lay.named_value("H", "hit", 1366) == lay.HIT_DESKTOP == 32
    assert lay.named_value("H", "hit", 390) == lay.HIT_TOUCH == 44
    assert "H = {" in lay.formula()


def test_ensure_hit_grows_the_hit_area_not_the_icon():
    b = bh.button("btnXDel", '"Delete"', "false", width=30, height=30, icon="Delete")
    bh.ensure_hit(b)
    assert b.props["Height"] == lay.HIT and b.props["Width"] == lay.HIT
    wide = bh.button("btnXWide", '"Delete"', "false", width=40, height=30)
    bh.ensure_hit(wide)
    assert wide.props["Width"] == f"Max(40, {lay.HIT})"
    assert bh.hit_size(36) == f"Max(36, {lay.HIT})"


def test_rule_40_flags_a_small_icon_button():
    import check_layout as ck

    class Ctx:
        problems = []
        all_nodes = [("p", "btnXTiny", {"Control": "ModernButton", "Properties": {
            "Layout": "=ButtonLayout.IconOnly", "Height": "=28", "Width": "=28"}}),
            ("p", "btnXOk", {"Control": "ModernButton", "Properties": {
                "Layout": "=ButtonLayout.IconOnly", "Height": "=H.hit", "Width": "=H.hit"}})]
    ck.rule_40(Ctx)
    assert len(Ctx.problems) == 1 and "btnXTiny" in Ctx.problems[0]


# --- sprog ---------------------------------------------------------------------
@pytest.mark.parametrize("text,bad", [
    ("Save Row Changes", ["Row", "Changes"]),
    # Statusnavne er egennavne (Draft, Valid ...) og maa staa med stort.
    ("Saved as Draft", []),
    ("Save draft", []),
    ("Back to Masterdata Hub", []),
    ("Add the row first. Then Submit.", []),
    ("Exists in SAP", []),
])
def test_title_case_rule(text, bad):
    assert cl.title_case_words(text) == bad


# --- husk valgene ----------------------------------------------------------------
def test_prefs_save_patches_only_the_given_fields():
    fx = tok.prefs_save({"prefMdView": '"mine"'})
    assert "Patch(colAppPrefs, First(colAppPrefs), { prefMdView: \"mine\" })" in fx
    assert 'SaveData(colAppPrefs, "prefs")' in fx
    with pytest.raises(KeyError):
        tok.prefs_save({"Unknown": "1"})
    assert tok.pref_get("prefMdView", '"all"') == 'Coalesce(First(colAppPrefs).prefMdView, "all")'


def test_every_hub_and_row_pref_is_in_the_schema():
    _name, schema = tok.prefs_schema()
    for f in tok.PREF_HUB + tok.PREF_ROWS:
        assert f in schema, f


# --- tekster -------------------------------------------------------------------
def test_plural_says_1_row_and_2_rows():
    fx = dt.plural("n", "row")
    assert '" row"' in fx and '" rows"' in fx and "row(s)" not in fx
    assert '" entries"' in dt.plural("n", "entry", "entries")


def test_short_text_rewrites_the_legacy_summaries():
    fx = dt.short_text("ThisItem.ShortText")
    for old, new in dt.LEGACY_SHORT:
        assert f'"{old}"' in fx and f'"{new}"' in fx


def test_stuck_is_only_for_requests_waiting_on_someone_else():
    assert ri.STUCK_STATUSES == ("Indsendt", "UnderBehandling", "AfventerInfo")
    assert ri.STUCK_DAYS == 5
    assert "Kladde" not in ri.STUCK_STATUSES
