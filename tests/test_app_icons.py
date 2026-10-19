# -*- coding: utf-8 -*-
"""Issue #415: Issue Boards Application-kolonne viser appens ikon.

EEN tabel (tools/app_icons.py) giver hver Application ikon og farve - de
samme som sidebaren og hubben (tools/icons.DOMAIN). Tabellen skal daekke
praecis de Applications, IB_AppSections seedes med, og seed-filens
IconRef/DomainColor skal sige det samme som tabellen."""
import csv
import os
import sys

from conftest import ROOT

sys.path.insert(0, os.path.join(ROOT, "Issue Board", "build"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

SEED = os.path.join(ROOT, "sharepoint", "seed", "IB_AppSections.csv")
SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenIssueBoard.pa.yaml")
APP = os.path.join(ROOT, "BIO SAP App", "App.pa.yaml")


def _seed():
    with open(SEED, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def test_mapping_covers_exactly_the_seeded_applications():
    import app_icons
    seeded = {r["Application"] for r in _seed()}
    assert seeded == set(app_icons.APPLICATIONS)
    assert app_icons.FALLBACK in app_icons.APPLICATIONS


def test_seed_icon_and_color_agree_with_the_mapping():
    import app_icons
    import icons
    for r in _seed():
        k = app_icons.APPLICATIONS[r["Application"]]
        assert r["IconRef"] == k, r
        assert r["DomainColor"] == icons.token(k), r


def test_apps_reuse_the_sidebar_and_hub_icons():
    import app_icons
    a = app_icons.APPLICATIONS
    assert a["Masterdata Hub"] == "hub"
    assert a["Functional Location"] == "functionallocation"
    assert a["Maintenance Plan"] == "vhplan"
    assert a["Materials"] == "material"
    assert a["Equipments"] == "equipment"
    assert a["Measuring Point"] == "measuringpoint"
    assert a["KKS lookup"] == "kks"
    assert a["Issue Board"] == "issueboard"
    # De tre nye: kompas (indigo), skydere (blaagraa), prikker (graa).
    assert a["Navigation and shared layout"] == "navigation"
    assert a["General"] == "general"
    assert a["Other"] == "other"


def test_new_colors_exist_in_both_themes_and_are_distinct():
    import math
    import design_tokens as tok
    import icons
    for k in ("navigation", "general", "other"):
        t = icons.token(k)
        assert t in tok.LIGHT and t in tok.DARK
        assert t in tok.HTML_TOKENS
    for theme in (tok.LIGHT, tok.DARK):
        toks = ["app-nav", "app-general", "app-other", "text-muted"]
        for i, a in enumerate(toks):
            for b in toks[i + 1:]:
                assert math.dist(tok._lab(theme[a]), tok._lab(theme[b])) > 10, (a, b)


def test_icons_are_one_named_formula():
    import app_icons
    import ib_parts as P
    f = app_icons.formula(P.APP_ICONS)
    for a in app_icons.APPLICATIONS:
        assert f'Application: "{a}"' in f
    assert f"{P.APP_ICONS} = Table(" in open(APP, encoding="utf-8").read()


def test_application_cell_keeps_its_width_and_shows_the_name():
    import ib_parts as P
    cell = P._app_cell()
    assert cell.props["Width"] == P.COL_W["APP"]
    names = [c.name for c in cell.children]
    assert names == ["imgIbRowApp", "txtIbRowApp"]
    img, txt = cell.children
    assert "IbAppIcons" in img.props["Image"]
    assert txt.props["Text"] == "ThisItem.Application"
    # Filter og sortering er uaendret: listen filtrerer stadig paa teksten.
    assert "IsBlank(varIbApp) || Application = varIbApp" in P.LIST_ITEMS
    screen = open(SCREEN, encoding="utf-8").read()
    assert "imgIbRowApp:" in screen and "txtIbRowApp:" in screen
