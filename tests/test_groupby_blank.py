# -*- coding: utf-8 -*-
"""
GroupBy paa en blank tabel giver "Det foerste argument for funktionen
GroupBy maa ikke vaere tomt". Hubbens strip laeser varMdAprAll, som er
blank, til skaermens OnVisible har kaldt Set - og galleriets raekker
tegnes foer det, saa fejlen kom een gang pr. raekke ved opstart.
Hver GroupBy over raekkens log (L) skal derfor vaere vagtet med IsEmpty.

    python3 -m pytest tests/test_groupby_blank.py
"""
import os
import re

from conftest import ROOT

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenMdHub.pa.yaml")


def test_row_log_groupby_is_guarded():
    text = open(SCREEN, encoding="utf-8").read()
    hits = [m.start() for m in re.finditer(r"GroupBy\(Filter\(L, ", text)]
    assert hits, "stripens GroupBy over L blev ikke fundet"
    for pos in hits:
        before = text[max(0, pos - 80):pos]
        assert re.search(r'If\(IsEmpty\(Filter\(L, Stage = "\w+"\)\), Blank\(\), ForAll\($', before), \
            "GroupBy over L uden IsEmpty-vagt: " + text[pos:pos + 60]
