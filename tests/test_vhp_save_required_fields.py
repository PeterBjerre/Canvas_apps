# -*- coding: utf-8 -*-
"""
Save draft stopper, foer noget skrives, naar et item mangler et af
MaintenanceItems' paakraevede felter (review R2-008).

Foer tjekkede guarden kun MainWorkCenter. Et item med funktionsplads men
uden kort tekst (Title), uden funktionsplads eller uden aktivitetstype fik
hele Items-Patch'et afvist af SharePoint - efter planhovedet var skrevet.
Beslutning: blokér gemningen (samme regel som for arbejdscentret, bare
komplet).

Issue #566: reglen gaelder nu kun Submit. Save draft gemmer ufaerdige
items (kolonnerne goeres valgfri af Provision-VHPlanColumns.ps1) - se
tests/test_vhp_save_draft_header_only.py.

    python3 -m pytest tests/test_vhp_save_required_fields.py
"""
import os
import sys

from conftest import ROOT

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenVhPlan.pa.yaml")
BUILD = os.path.join(ROOT, "Maintenance Plan App", "build")
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)

import build_save  # noqa: E402

MSG = ("Fill in short text, functional location, activity type and main work "
       "center on every item before submitting: ")


def _guard():
    fx = build_save.save_action()
    i = fx.index(MSG)
    return fx[:i + 400]


def test_guard_covers_all_required_item_columns():
    g = _guard()
    assert "IsBlank(Trim(IT.ShortText))" in g
    assert "IsBlank(IT.FunctionalLocation)" in g
    assert "LookUp(colVhpActivityTypeOptions, Value = IT.ActivityType).Id" in g
    assert "LookUp(colVhpMainWorkCenters, Value = Trim(IT.MainWorkCenter)).Id" in g
    assert f"CountRows({build_save.NO_REQ}) > 0" in g


def test_guard_comes_before_the_first_patch():
    fx = build_save.save_action()
    assert fx.index(MSG) < fx.index("Patch(")


def test_message_is_in_the_generated_screen():
    text = open(SCREEN, encoding="utf-8").read()
    assert MSG in text
    assert "Select a main work center on every item before saving" not in text
