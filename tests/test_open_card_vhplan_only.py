# -*- coding: utf-8 -*-
"""
Issue #391/#407: kortet "Opening request" vises kun, naar en eksisterende
VH-plan aabnes. En NY anmodning viser aldrig et blokerende kort (issue
#407 fjernede "Preparing a new request") - hverken i VH-planen eller i
Functional Location, Equipments, Measuring Points og Materials, som heller
ikke viser kort, naar en gemt anmodning aabnes. En fejl viser altid kortet
(Retry/Close). Kortet styres af indlaesningsflaget - ingen fast pause.

    python3 -m pytest tests/test_open_card_vhplan_only.py
"""
import os
import re

import pytest

from conftest import ROOT

APP = os.path.join(ROOT, "BIO SAP App")
QUIET = {"ScreenFunctionalLocation": "Fl", "ScreenEquipment": "Eq",
         "ScreenMaterial": "Mat", "ScreenMeasuringPoint": "Mp"}
ALL = dict(QUIET, ScreenVhPlan="Vhp")


def _text(screen):
    return open(os.path.join(APP, screen + ".pa.yaml"), encoding="utf-8").read()


def _visible(text, name):
    m = re.search(r"- %s:\n(?:.*\n)*?\s+Visible: \|-\n\s+=(.*)\n" % name, text)
    assert m, name + " mangler"
    return m.group(1)


@pytest.mark.parametrize("screen,tag", sorted(QUIET.items()))
def test_quick_domains_show_card_only_on_error(screen, tag):
    text = _text(screen)
    want = "IfError(var%sLoadFailed, false)" % tag
    assert _visible(text, "img%sLoading" % tag) == want
    assert _visible(text, "con%sLoadCard" % tag) == want
    assert "var%sLoadCard" % tag not in text


@pytest.mark.parametrize("screen,tag", sorted(ALL.items()))
def test_no_preparing_new_request_card(screen, tag):
    text = _text(screen)
    assert "Preparing a new request" not in text


def test_vhplan_card_only_for_saved_plan_until_loaded():
    text = _text("ScreenVhPlan")
    want = ("(IfError(varVhpLoading, false) && IfError(varVhpLoadCard, false))"
            " || IfError(varVhpLoadFailed, false)")
    assert _visible(text, "imgVhpLoading") == want
    assert _visible(text, "conVhpLoadCard") == want
    assert '"Opening request"' in text
    # Kun en gemt plan viser kortet - afgjort i OnVisible og igen, naar
    # anmodningens id kendes.
    assert 'Set(varVhpLoadCard, !StartsWith(If(gblNavTo = "Vhp", "new:0"' in text
    assert "Set(varVhpLoadCard, !IsBlank(gblVhpReqId));" in text
    # Kortet forsvinder, saa snart klargoeringen er faerdig - ingen timer
    # skjuler det (timeren saetter kun "tager lang tid").
    assert "Set(varVhpLoading, false);" in text
    timer = re.search(r"- tmrVhpLoadSlow:\n(?:.*\n)*?\s+OnTimerEnd: \|-\n\s+=(.*)\n", text)
    assert timer and timer.group(1) == "Set(varVhpLoadSlow, true)"
