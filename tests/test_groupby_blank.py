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
        before = text[max(0, pos - 140):pos]
        assert re.search(r'If\(IsBlank\(Filter\(L, Stage = "\w+"\)\) \|\| IsEmpty\(Filter\(L, Stage = "\w+"\)\), Blank\(\), ForAll\($', before), \
            "GroupBy over L uden IsEmpty-vagt: " + text[pos:pos + 60]


def test_both_domains_groupby_is_guarded():
    """Materials gren i striben (issue #204) laeser den samme L.

    VH-planen grupperer System og Cost (Quality tager kun den nyeste
    raekke), og Materials grupperer System. Alle tre skal vaere vagtet -
    ellers er fejlen tilbage, bare for et andet domaene."""
    text = open(SCREEN, encoding="utf-8").read()
    hits = re.findall(r'If\(IsBlank\(Filter\(L, Stage = "(\w+)"\)\)', text)
    assert hits.count("System") >= 2, hits
    assert "Cost" in hits
