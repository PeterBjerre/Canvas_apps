# -*- coding: utf-8 -*-
"""
Issue #391: kortet "Opening request" vises kun, naar en eksisterende
VH-plan aabnes. Functional Location, Equipments, Measuring Points og
Materials aabner en gemt anmodning uden kort (en ny anmodning og en fejl
viser det stadig). Kortet styres af indlaesningsflaget - ingen fast pause.

    python3 -m pytest tests/test_open_card_vhplan_only.py
"""
import os
import re

import pytest

from conftest import ROOT

APP = os.path.join(ROOT, "BIO SAP App")
QUIET = {"ScreenFunctionalLocation": "Fl", "ScreenEquipment": "Eq",
         "ScreenMaterial": "Mat", "ScreenMeasuringPoint": "Mp"}


def _text(screen):
    return open(os.path.join(APP, screen + ".pa.yaml"), encoding="utf-8").read()


def _visible(text, name):
    m = re.search(r"- %s:\n(?:.*\n)*?\s+Visible: \|-\n\s+=(.*)\n" % name, text)
    assert m, name + " mangler"
    return m.group(1)


@pytest.mark.parametrize("screen,tag", sorted(QUIET.items()))
def test_quick_domains_open_saved_request_without_card(screen, tag):
    text = _text(screen)
    want = ("(IfError(var%sLoading, false) && IfError(var%sLoadCard, false))"
            " || IfError(var%sLoadFailed, false)" % (tag, tag, tag))
    assert _visible(text, "img%sLoading" % tag) == want
    assert _visible(text, "con%sLoadCard" % tag) == want
    # Kortet er kun til en ny anmodning - afgjort i OnVisible og igen,
    # naar anmodningens id kendes.
    assert 'Set(var%sLoadCard, StartsWith(If(gblNavTo = "%s", "new:0"' % (tag, tag) in text
    assert "Set(var%sLoadCard, IsBlank(gbl%sReqId));" % (tag, tag) in text


def test_vhplan_keeps_card_until_loaded():
    text = _text("ScreenVhPlan")
    assert "varVhpLoadCard" not in text
    want = "IfError(varVhpLoading, false) || IfError(varVhpLoadFailed, false)"
    assert _visible(text, "imgVhpLoading") == want
    assert _visible(text, "conVhpLoadCard") == want
    assert '"Opening request"' in text
    # Kortet forsvinder, saa snart klargoeringen er faerdig - ingen timer
    # skjuler det (timeren saetter kun "tager lang tid").
    assert "Set(varVhpLoading, false);" in text
    timer = re.search(r"- tmrVhpLoadSlow:\n(?:.*\n)*?\s+OnTimerEnd: \|-\n\s+=(.*)\n", text)
    assert timer and timer.group(1) == "Set(varVhpLoadSlow, true)"
