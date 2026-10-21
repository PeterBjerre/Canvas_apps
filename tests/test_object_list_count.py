# -*- coding: utf-8 -*-
"""
Issue #454: soegningens resultattal (beskeden under feltet, "6 Functional
Locations found ...") laeses af samme samling og nulstilles, naar
soegeteksten aendres, resultaterne ryddes, eller en ny soegning starter.

Mockup 2026-10-21: Object list-knappens tal er kun de VALGTE objekter.

    python3 -m pytest tests/test_object_list_count.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from fl_picker import result_count_fx  # noqa: E402
import build_flsearch as fl  # noqa: E402
from test_vhp_view_lock import _controls  # noqa: E402

COUNT = result_count_fx(combo="cmbVhpItemFL", results="colVhpFl",
                        busy_var="varVhpFlBusy", last_var="varVhpFlLast")


def _p(name, prop):
    return str(_controls()[name][1].get(prop, ""))


def test_count_reads_the_same_collection_as_the_message():
    msg = fl.search_action("cmbVhpItemFL", "colVhpFl", "varVhpFlMsg",
                           raw_var="varVhpFlRaw", busy_var="varVhpFlBusy",
                           last_var="varVhpFlLast")
    assert "{ n: CountRows(colVhpFl) }" in msg
    assert COUNT.endswith(", 0, CountRows(colVhpFl))")


def test_count_resets():
    # Ny soegning (busy), nulstillet/ryddet (tom last), aendret soegetekst.
    assert COUNT.startswith("If(varVhpFlBusy || IsBlank(varVhpFlLast) || ")
    assert ("Upper(Trim(cmbVhpItemFL.SearchText)) <> Upper(Trim(varVhpFlLast))"
            in COUNT)
    # Et valgt resultat i feltet (tom SearchText) nulstiller ikke.
    assert "!IsBlank(Upper(Trim(cmbVhpItemFL.SearchText))) &&" in COUNT
    # Ikke-praecedens (tests/test_not_precedence.py).
    assert "!IsBlank(" in COUNT and "!Upper" not in COUNT


def test_button_shows_only_the_selected_objects():
    # Mockup 2026-10-21: "(X) skal kun vise selected" - tallet er de valgte
    # objekter paa itemet, ikke soegeresultaterne (issue #454) og ikke
    # planens egen Functional Location.
    img = _p("imgVhpObjList", "Image")
    chosen = "CountRows(Filter(colVhpItemObjects, ItemId = varVhpActiveItemId))"
    assert '"Object list (" & Text(' + chosen + ') & ")"' in img
    assert '"Object list (" & Text(' + COUNT not in img
    label = _p("imgVhpObjList", "AccessibleLabel")
    assert chosen in label and '" selected"' in label and '" found, "' not in label
    # Tooltip'en viser stadig de valgte objekter.
    assert '"Selected:"' in _p("imgVhpObjList", "Tooltip")
