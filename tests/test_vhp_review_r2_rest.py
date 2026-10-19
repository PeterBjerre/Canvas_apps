# -*- coding: utf-8 -*-
"""
VH-planens rettelser fra review 2026-10 (docs/43-review-2026-10.md):
R2-034, R2-035, R2-036, R2-037, R2-050, R2-070, R2-071, R2-082, R2-093.

Tjekkene laeser builderne, ikke den genererede YAML, saa de gaelder
uanset om skaermen er bygget igen.

    python3 -m pytest tests/test_vhp_review_r2_rest.py
"""
import os
import sys

from conftest import ROOT

BUILD = os.path.join(ROOT, "Maintenance Plan App", "build")
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)

import build_items  # noqa: E402
import build_load  # noqa: E402
import build_save  # noqa: E402
import sp_config as cfg  # noqa: E402


# --- R2-034: ItemGuid -------------------------------------------------------
def test_item_guid_in_working_collection():
    assert "ItemGuid" in dict(cfg.WORKING_COLLECTIONS)["colVhpItems"]


def test_item_guid_is_saved_and_loaded():
    assert "ItemGuid: IT.ItemGuid" in build_save.item_fields()
    assert ("ItemGuid", "Coalesce(IT.ItemGuid, Text(GUID()))") in build_load.ITEM_FIELDS
    assert ("ItemGuid", "Text(GUID())") in build_load.EMPTY_ITEM_FIELDS


def test_add_and_copy_item_make_a_new_guid():
    src = open(os.path.join(BUILD, "build_items.py"), encoding="utf-8").read()
    # Add item og Copy item: hver sin nye identitet - kopien arver ikke kildens.
    assert src.count("SpId: 0, ItemGuid: Text(GUID())") == 2
    assert "src.ItemGuid" not in src


# --- R2-035: Submit afhaenger ikke af en deaktiveret knap -------------------
def test_submit_checks_save_button_display_mode():
    assert "btnVhpSaveDraft.DisplayMode = DisplayMode.Edit" in build_save.SUBMIT_FX
    src = open(os.path.join(BUILD, "build_save.py"), encoding="utf-8").read()
    assert "+ SUBMIT_FX)," in src
    assert "Set(varVhpSubmitting, true);\\nSelect(" not in src


def test_submitting_flag_is_reset_before_the_message():
    fx = build_save.save_action()
    reset = fx.index("{ sub: varVhpSubmitting },\n    Set(varVhpSubmitting, false);")
    assert reset < fx.index("Set(varVhpSavedJson, VhpStateJson)")
    # Spinneren via with_busy (A12): taendt foerst, slukket til sidst.
    assert fx.rstrip().endswith("Set(varVhpSaving, false)\n)")
    assert fx.count("Set(varVhpSaving, true)") == 1


# --- R2-036: gem og indlaesning regner rettigheden paa samme status ---------
def test_save_permission_uses_plan_status_like_load():
    keys = build_save._step_keys()
    assert 'varVhpFlow.Status = "Returned"' in keys
    assert 'If(varVhpFlow.Status = "Returned", "AfventerInfo", varVhpIdxNow.Status.Value)' in keys


def test_draft_save_of_returned_plan_heals_index():
    st = build_save._step_status()
    i = st.index('varVhpPlanRec.Status.Value = "Returned"')
    assert 'Status: { Value: "AfventerInfo" }' in st[i:]


# --- R2-037: en raekke uden noegle stopper ikke noegleserien ----------------
def test_offset_skips_rows_without_key():
    off = build_save._offset("MaintenanceItems", "ItemID", "MI")
    assert 'Filter(MaintenanceItems, StartsWith(ItemID, "MI"))' in off
    # Sidste vaern: et nummer, der ikke er et tal, stopper stadig.
    assert "IsNumeric(Mid(r.ItemID, 3))" in off


# --- R2-050: Submit nulstiller InitialEmailSent -----------------------------
def test_submit_resets_initial_email_flag():
    st = build_save._step_status()
    i = st.index('Status: { Value: "In Progress" }')
    assert "InitialEmailSent: false" in st[i:st.index("varVhpFlow", i)]
    # Kun ved Submit - Save draft roerer ikke flaget.
    assert st.count("InitialEmailSent") == 1


# --- R2-070: strategiplanens tomme Unit skrives som Blank() ------------------
def test_blank_unit_is_written_as_blank():
    f = build_save.plan_fields()
    assert "Unit: If(IsBlank(varVhpPlan.Unit), Blank(), { Value: varVhpPlan.Unit })" in f
    assert "Cycle: varVhpPlan.Cycle" in f


# --- R2-071: de gamle dokumentraekker laeses, men skrives/slettes ikke -------
def test_save_does_not_touch_old_document_rows():
    fx = build_save.save_action()
    assert "MD_TasklistAttachment" not in fx
    assert "colVhpOldAtts" not in fx
    assert not hasattr(build_save, "_step_attachments")


def test_old_document_rows_are_still_read():
    assert "Filter(MD_TasklistAttachment, PlanKey = varVhpPlanKey)" in build_load.load_block()


def test_hub_url_dead_code_is_gone():
    assert not hasattr(cfg, "HUB_URL")


# --- R2-082: omkostningsgraensen vises, filtreret paa miljoeet --------------
def test_cost_threshold_formula_is_environment_filtered():
    f = dict((n, e) for n, e, _w in cfg.named_formulas())["VhpCostThreshold"]
    assert 'LookUp(AppSettings, Option.Value = "CostApprovalThresholdDkk"' in f
    assert 'Environment.Value = "%s"' % cfg.SETTINGS_ENV in f
    assert cfg.SETTINGS_ENV in ("DEV", "TEST", "PROD")


def test_cost_over_shown_on_the_totals_card():
    import build_tasklist as bt
    # Graensen gaelder hele planen (Peter 2026-10-19), ikke det enkelte item.
    assert "Sum(colVhpOperations, Cost) > VhpCostThreshold" in bt.COST_OVER_ON
    screen = open(os.path.join(ROOT, "BIO SAP App", "ScreenVhPlan.pa.yaml"), encoding="utf-8").read()
    assert "crdVhpOpsTotals" in screen
    assert "txtVhpOpsCostOver" not in screen and "htmVhpOpsTotals" not in screen


# --- R2-093: VH-konstanter ud af de faelles moduler -------------------------
def test_vh_constants_live_in_vh_build():
    import build_helpers
    import gen_screen
    import build_help
    for name in ("RAIL_W", "SPLIT_GAP", "EDITOR_W"):
        assert not hasattr(gen_screen, name), name
        assert hasattr(build_items, name), name
    assert not hasattr(build_helpers, "HINTS_ON")
    assert build_help.HINTS_ON == "IfError(varVhpShowHints, false)"


def test_field_cell_hint_needs_explicit_switch():
    import pytest
    import build_helpers
    from gen_screen import Ctrl
    inp = Ctrl("inpX", "TextInput", props={})
    with pytest.raises(ValueError):
        build_helpers.field_cell("conX", "X", inp, hint_text='"hint"')
    build_helpers.field_cell("conY", "Y", Ctrl("inpY", "TextInput", props={}),
                             hint_text='"hint"', hints_on="varShow")
