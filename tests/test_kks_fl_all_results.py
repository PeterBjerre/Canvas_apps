# -*- coding: utf-8 -*-
"""KKS-opslaget: Search Functional Locations viser ALLE resultater (issue #514).

Beskeden sagde "6 Functional Locations found", men popuppen viste kun det
ene valgte resultat. Nu er der en liste over hele colKksFl - samme samling,
som beskeden taeller - med kode, beskrivelse og en kopier-knap pr. raekke.
Listen er saa hoej som sit indhold og scroller kun, naar den ikke kan staa
i popuppen."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenKks.pa.yaml")


def _modal():
    y = open(SCREEN, encoding="utf-8").read()
    return y[y.index("- conKksFlModal:"):y.index("- imgKksLoading:")]


def _prop(block, prop):
    i = block.index(f"{prop}: |-")
    return block[i:i + 4000].split("\n")[1].strip()


def _block(text, name):
    i = text.index(f"- {name}:")
    nxt = text.find("\n            - ", i + 1)
    return text[i:nxt if nxt > 0 else None]


def test_list_shows_every_result():
    gal = _block(_modal(), "galKksFlRows")
    assert _prop(gal, "Items") == "=colKksFl"
    assert "FirstN" not in gal and "First(" not in gal
    assert _prop(gal, "Visible") == "=CountRows(colKksFl) > 0"
    assert "- txtKksFlRowCode:" in gal and "- txtKksFlRowDesc:" in gal
    assert _prop(gal, "Text") == "=ThisItem.Code"
    # Det gamle "kun det valgte"-felt er vaek.
    assert "conKksFlSelected" not in _modal()


def test_every_row_has_a_copy_button():
    gal = _block(_modal(), "galKksFlRows")
    copy = gal[gal.index("- btnKksFlCopy:"):]
    assert "Copy(ThisItem.Code)" in copy
    assert '="Copy " & ThisItem.Code' in copy


def test_height_follows_the_content_and_scrolls_only_when_needed():
    gal = _block(_modal(), "galKksFlRows")
    h = _prop(gal, "Height")
    assert h.startswith("=If(CountRows(colKksFl) > 0, Min(Sum(colKksFl, ")
    assert "App.Height - 24" in h
    sb = _prop(gal, "ShowScrollbar")
    assert sb.startswith("=Sum(colKksFl, ") and "> Max(120, App.Height - 24" in sb


def test_selected_result_is_highlighted():
    gal = _block(_modal(), "galKksFlRows")
    assert "If(ThisItem.Code = varKksFlPick, " in gal
