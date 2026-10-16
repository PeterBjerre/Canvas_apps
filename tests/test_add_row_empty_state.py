# -*- coding: utf-8 -*-
"""
Issue #310: uden raekker staar Add row kun i den tomme tilstand - ikke
ogsaa i vaerktoejslinjen. Paste rows bliver staaende. Gaelder Materials,
Equipment og Measuring Points.

    python3 -m pytest tests/test_add_row_empty_state.py
"""
import os
import re

import pytest

from conftest import ROOT

SCREENS = [("ScreenMaterial", "Mat"), ("ScreenEquipment", "Eq"),
           ("ScreenMeasuringPoint", "Mp")]


def _visible(text, name):
    m = re.search(r"- %s:\n(?:\s{20,}.*\n)*?\s+Visible: \|-\n\s+=(.*)\n" % name, text)
    assert m, name + " mangler eller har ingen Visible"
    return m.group(1).strip()


@pytest.mark.parametrize("screen,p", SCREENS)
def test_toolbar_add_row_hidden_without_rows(screen, p):
    text = open(os.path.join(ROOT, "BIO SAP App", screen + ".pa.yaml"),
                encoding="utf-8").read()
    assert _visible(text, "btn%sNewRow" % p) == \
        "!var%sViewOnly && !IsEmpty(col%sRows)" % (p, p)
    # Den tomme tilstands knap vises netop, naar listen er tom.
    assert _visible(text, "btn%sRowsEmptyAdd" % p) == \
        "IsEmpty(col%sRows) && !var%sViewOnly" % (p, p)
    # Paste rows staar stadig i vaerktoejslinjen, ogsaa uden raekker.
    assert _visible(text, "btn%sPasteRows" % p) == "!var%sViewOnly" % p
