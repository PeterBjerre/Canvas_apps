# -*- coding: utf-8 -*-
"""Issue #565: First call i Plan header maa ikke ligge foer i dag.

- Datovaelgerens kalender starter i dag (Today(), ikke en fast dato) - eller
  ved den gemte dato, hvis den er aeldre, saa den stadig kan vises.
- Under feltet staar "First call cannot be before today", kun i redigering
  (aldrig i View, aldrig naar planhovedet er laast/gemt).
- Save i Plan header afviser datoen, og Submit-reglen (VhpPlanRuleErrors)
  afviser en gemt plan med en gammel dato, til den er indsendt.
- Formatet er uaendret.

    python3 -m pytest tests/test_first_call_today_565.py
"""
import os

import yaml

from conftest import ROOT

import layout_tokens as lay

SCREEN_PATH = os.path.join(ROOT, "BIO SAP App", "ScreenVhPlan.pa.yaml")
APP_PATH = os.path.join(ROOT, "BIO SAP App", "App.pa.yaml")
SCREEN = next(iter(yaml.safe_load(open(SCREEN_PATH, encoding="utf-8").read())["Screens"].values()))
APP_TEXT = open(APP_PATH, encoding="utf-8").read()

PAST = "dteVhpFirstCall.SelectedDate < Today()"


def _find(node, name):
    for c in node.get("Children") or []:
        for n, v in c.items():
            if n == name:
                return v
            hit = _find(v, name)
            if hit is not None:
                return hit
    return None


def _kids(name):
    return [n for c in (_find(SCREEN, name).get("Children") or []) for n in c]


def _prop(name, key):
    v = str((_find(SCREEN, name).get("Properties") or {}).get(key, ""))
    return v.strip().lstrip("=").strip()


def test_calendar_starts_today_or_at_saved_date():
    start = _prop("dteVhpFirstCall", "StartDate")
    assert "Today()" in start
    assert "varVhpPlan.FirstCallYear" in start
    assert "Date(19" not in start and "Date(20" not in start


def test_field_message_below_picker_only_while_editing():
    kids = _kids("conVhpCellFirstCall")
    assert kids.index("txtVhpFirstCallErr") == kids.index("dteVhpFirstCall") + 1
    assert _prop("txtVhpFirstCallErr", "Text") == '"First call cannot be before today"'
    vis = _prop("txtVhpFirstCallErr", "Visible")
    assert PAST in vis
    assert "!varVhpViewOnly" in vis and "!varVhpPlanLocked" in vis
    # Cellen vokser kun, naar beskeden vises.
    assert PAST in _prop("conVhpCellFirstCall", "Height")


def test_border_is_red_and_view_border_kept():
    bc = _prop("dteVhpFirstCall", "BorderColor")
    assert bc.startswith("If(varVhpViewOnly, C.'border-default'")
    assert PAST in bc and "C.'border-error'" in bc


def test_save_rejects_date_before_today():
    onselect = _prop("btnVhpPlanSave", "OnSelect")
    i = onselect.index(PAST)
    assert "First call cannot be before today." in onselect[i:]
    # Afvisningen kommer foer gemningen, som laaser planhovedet.
    assert i < onselect.index("Set(varVhpPlanLocked, true)")


def test_submit_rule_blocks_unsubmitted_plan_only():
    i = APP_TEXT.index('"First call cannot be before today - choose today')
    rule = APP_TEXT[APP_TEXT.rindex("{ m: If(", 0, i):i]
    assert "!VhpSubmitted" in rule
    assert "Date(varVhpPlan.FirstCallYear, varVhpPlan.FirstCallMonth, " \
           "varVhpPlan.FirstCallDay) < Today()" in rule


def test_format_unchanged():
    assert _prop("dteVhpFirstCall", "Format") == f'"{lay.DATE_PICKER_FMT}"'
