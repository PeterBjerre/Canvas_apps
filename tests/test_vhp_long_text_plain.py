# -*- coding: utf-8 -*-
"""
Lang tekst uden HTML-tags.

MaintenanceItems.ItemDescription og TaskListMain.LongText har vaeret rich
text, saa SharePoint gav lang tekst tilbage som
<div class="ExternalClass...">tekst</div>. Long text-popuppen viste taggene.

  - indlaesningen af items og operationer renser lang tekst,
  - admin-loggens "foer" renses ens, saa en uaendret tekst ikke logges
    som aendret,
  - provisioneringen goer de to kolonner til ren tekst.

    python3 -m pytest tests/test_vhp_long_text_plain.py
"""
import os
import sys

from conftest import ROOT

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenVhPlan.pa.yaml")
PROVISION = os.path.join(ROOT, "sharepoint", "provision", "Provision-VHPlanColumns.ps1")
BUILD = os.path.join(ROOT, "Maintenance Plan App", "build")
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)

import sp_config as cfg  # noqa: E402


def _screen():
    with open(SCREEN, encoding="utf-8") as f:
        return f.read()


def test_helper_only_touches_html():
    fx = cfg.plain_long_text("X.Y")
    assert 'StartsWith(_lt, "<")' in fx
    assert "PlainText(" in fx
    for tag in ('"</p>"', '"</div>"', '"<br>"'):
        assert tag in fx
    assert fx.count("(") == fx.count(")")


def test_load_cleans_items_and_operations():
    s = _screen()
    assert "LongText: IT.ItemDescription," not in s
    assert "LongText: " + cfg.plain_long_text("IT.ItemDescription") in s
    assert "LongText: " + cfg.plain_long_text("OP.LongText") in s


def test_admin_log_compares_clean_text():
    s = _screen()
    assert "ItemDescription: I.ItemDescription," not in s
    assert "ItemDescription: " + cfg.plain_long_text("I.ItemDescription") in s


def test_provisioning_makes_columns_plain_text():
    with open(PROVISION, encoding="utf-8-sig") as f:
        ps = f.read()
    assert "@('MaintenanceItems', 'ItemDescription')" in ps
    assert "@('TaskListMain', 'LongText')" in ps
    assert "RichText = $false" in ps
