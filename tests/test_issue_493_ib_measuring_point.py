# -*- coding: utf-8 -*-
"""Issue #493: Measuring Point i Issue Board.

Issue Boards Applications og Sections kommer IKKE fra en hardkodet liste
i appen, men fra SharePoint-listen IB_AppSections (seedet fra
sharepoint/seed/IB_AppSections.csv). Measuring Point stod i seedet med
IsActive = FALSE og uden ScreenKey, saa den aldrig blev vist. Nu er den
aktiv, staar mellem Equipments og KKS lookup og har Sections, der passer
til Measuring Point-skaermen.

    python3 -m pytest tests/test_issue_493_ib_measuring_point.py
"""
import csv
import os
import sys

from conftest import ROOT

sys.path.insert(0, os.path.join(ROOT, "Issue Board", "build"))
import ib_config as cfg  # noqa: E402

MP = "Measuring Point"
MP_BUILD = os.path.join(ROOT, "Measuring Point App", "build")
PS1 = os.path.join(ROOT, "sharepoint", "provision", "Provision-IssueBoard.ps1")


def _seed():
    with open(cfg.SEED_CSV, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _mp_rows():
    return [r for r in _seed() if r["Application"] == MP]


def _read(*p):
    return open(os.path.join(*p), encoding="utf-8").read()


def test_measuring_point_sections_are_active_with_screen_icon_and_color():
    rows = _mp_rows()
    assert rows
    for r in rows:
        assert r["IsActive"] == "TRUE", r
        assert r["ScreenKey"] == "measuringpoint", r
        assert r["IconRef"] == "measuringpoint", r
        assert r["DomainColor"] == "domain-mp", r


def test_measuring_point_sits_between_equipments_and_kks_lookup():
    order = {}
    for r in _seed():
        order.setdefault(r["Application"], int(r["AppOrder"]))
    assert len({int(r["AppOrder"]) for r in _mp_rows()}) == 1
    assert order["Equipments"] < order[MP] < order["KKS lookup"]
    apps = sorted(order, key=order.get)
    assert apps[apps.index("Equipments") + 1] == MP
    assert apps[apps.index(MP) + 1] == "KKS lookup"


def test_measuring_point_sections_match_the_screen():
    secs = [r["Section"] for r in sorted(_mp_rows(), key=lambda r: int(r["SectionOrder"]))]
    assert secs == ["Request header", "Measuring Point Form", "Characteristic lookup",
                    "Saved Rows", "Row actions", "Functional Location search",
                    "View mode", "Edit mode", "Mobile layout", cfg.OTHER]
    assert len(set(int(r["SectionOrder"]) for r in _mp_rows())) == len(secs)
    config = _read(MP_BUILD, "domain_config.py")
    parts = _read(MP_BUILD, "mp_parts.py")
    # Skaermen har ingen dokumenter (issue #300) - derfor ingen Documents.
    assert "DOCS_ENABLED = False" in config
    assert "Documents" not in secs
    # Karakteristik-opslaget og FL-soegningen findes paa skaermen.
    assert "colDomChars" in parts
    assert "build_fl_msg" in parts


def test_issue_board_reads_applications_from_the_list_not_a_hardcoded_table():
    import ib_parts as P
    # Kun aktive raekker hentes, og dropdowns og filtre bygger paa dem.
    assert "IsActive = true" in P.FETCH_SECTIONS
    assert "colIbSections" in P.APPS_FX and '"AppOrder"' in P.APPS_FX
    assert "colIbSections" in P.FORM_SECTIONS_FX
    assert MP not in P.APPS_FX


def test_measuring_point_has_its_icon_in_the_overview():
    import app_icons
    import ib_parts as P
    assert app_icons.APPLICATIONS[MP] == "measuringpoint"
    assert f'Application: "{MP}"' in app_icons.formula(P.APP_ICONS)


def test_provisioning_can_refresh_one_application_without_force():
    ps1 = open(PS1, encoding="utf-8-sig").read()
    assert "[string[]] $Application" in ps1
    assert "$Force -or ($Application -contains $values.Title)" in ps1
    # Gamle Sections under Applicationen skjules, de slettes ikke.
    assert "IsActive = $false" in ps1
    assert "-Application 'Measuring Point'" in ps1
