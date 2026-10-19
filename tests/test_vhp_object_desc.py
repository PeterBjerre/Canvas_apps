# -*- coding: utf-8 -*-
"""
Issue #389: en gemt VH-plans Object list viser KKS-nummer OG beskrivelse,
som ved oprettelsen. Beskrivelsen gemmes ikke dobbelt - ObjectList er
stadig kun koderne - men slaas op i FL-flowet (samme kilde som Search),
naar Object list aabnes.

    python3 -m pytest tests/test_vhp_object_desc.py
"""
import os
import sys

from conftest import ROOT

BUILD = os.path.join(ROOT, "Maintenance Plan App", "build")
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)

import build_items as bi  # noqa: E402
import build_flsearch as fl  # noqa: E402

SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenVhPlan.pa.yaml")
FALLBACK = ('Coalesce(O.Description, LookUp(colVhpFl, Code = O.Code).Description, '
            'LookUp(colVhpObjDesc, Code = O.Code).Description, "")')


def test_rows_and_tooltip_fall_back_to_kks_source():
    # Popup'ens raekker og knappens tooltip bruger den gemte beskrivelse,
    # ellers KKS-kildens (soegeresultatet eller cachen fra flowet).
    assert FALLBACK in bi.OBJ_ROWS_FX
    assert FALLBACK in bi.OBJ_TOOLTIP
    # Samme format som ved oprettelsen: "KKS - beskrivelse", uden " - "
    # naar der ingen beskrivelse er.
    assert 'O.Code & If(IsBlank(' in bi.OBJ_TOOLTIP


def test_fetch_uses_fl_flow_and_only_fills_cache():
    f = bi.FETCH_OBJ_DESC
    assert f"{fl.FLOW_NAME}.Run(fl)" in f
    assert f".{fl.FLOW_OUTPUT}" in f and fl.JSON_DESC_FIELD in f
    # Kun manglende beskrivelser i kladden - ingen kald, naar alt er kendt.
    assert "miss: Filter(colVhpObjDraft, IsBlank(Description)" in f
    assert "CountRows(miss) > 0" in f
    # Svaret havner i cachen; itemets objekter og soegeresultatet roeres
    # ikke, saa en vist plan ikke bliver "aendret" (VhpStateJson).
    assert "Collect(\n                    colVhpObjDesc" in f
    for bad in ("colVhpItemObjects", "Collect(colVhpFl", "ClearCollect(colVhpFl"):
        assert bad not in f, bad


def test_object_list_button_fetches_after_opening():
    text = open(SCREEN, encoding="utf-8").read()
    i = text.index("- imgVhpObjList:")
    block = text[i:text.index("Tooltip:", i)]
    assert block.index("Set(varVhpObjListOpen, true);") < block.index(".Run(fl)")


def test_saved_object_list_stays_codes_only():
    # Ingen dobbelt lagring: ObjectList er stadig kun koderne.
    import build_load as bl
    import inspect
    src = inspect.getsource(bi)
    assert 'ObjectList: Concat(Sort(Filter(colVhpItemObjects, ItemId = varVhpActiveItemId), Code), Code, \\"; \\")' in src
    assert '{ ItemId: I.ItemId, Code: Trim(S.Value), Description: \\"\\" }' in inspect.getsource(bl)


def test_iferror_value_and_fallback_have_same_type():
    # Issue #400: IfError kraever samme type i vaerdi og fallback. Notify
    # giver Boolean, saa kaeden maa ikke ende med Collect (en tabel).
    f = bi.FETCH_OBJ_DESC
    value, fallback = f.split("IfError(", 1)[1].rsplit("Notify(", 1)
    assert value.rstrip().endswith("true,")
