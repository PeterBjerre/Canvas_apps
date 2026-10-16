# -*- coding: utf-8 -*-
"""
Functional Location: Submit og sidepanelet (issue #277 og #278).

  - Submit kan trykkes, saa laenge anmodningen kan aendres, og et tryk
    siger altid noget: bekraeftelsen eller hvorfor den er blokeret.
  - Sidepanelet har raekkens raekkefoelge og etiketter og ingen
    Status-sektion.
  - Panelet regnes ikke om, mens man skriver (kun ved en ny klasse), og
    dets sloer ligger aldrig under selve panelet.
  - Class data-popuppen ligger over panelet.

Power Fx kan ikke koeres her, saa testene laeser den GENEREREDE skaerm.

    python3 -m pytest tests/test_fl_panel_order.py
"""
import os
import sys

from conftest import ROOT

import test_fl_spool_row as T

BUILD = os.path.join(ROOT, "Functional Location App", "build")
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)
import fl_config as cfg  # noqa: E402

BIO_APP = os.path.join(ROOT, "BIO SAP App", "App.pa.yaml")


def _parts():
    return T._parts()


def test_panel_follows_the_row_order_and_labels():
    """Panelets felter i raekkefoelge = raekkens kolonner fra Functional
    Location til Warranty, med de samme etiketter."""
    p = _parts()
    row = [l for n, l, _w, _v in p.V_SPEC if n not in ("No", "Status", "Act")]
    assert row == ["Functional Location", "Description", "KKS type", "Assigned class",
                   "Class data", "Room", "Sort field", "ABC indicator", "ATEX",
                   "Manufacturer", "Warranty"]
    # Panelet: Master-felterne, med Class data (Class-sektionen) paa sin
    # plads, og Manufacturer/Warranty som deres sektioner.
    panel = []
    for key, title in cfg.PANEL_SECTIONS:
        if key == "Class":
            panel.append("Class data")
        elif key in ("Mfr", "War"):
            panel.append(title)
        else:
            panel += [l for _f, k, l in cfg.PANEL_FIELDS if k == key]
    assert panel[:len(row)] == row
    assert [k for k, _t in cfg.PANEL_SECTIONS][-2:] == ["TRM", "Ext"]
    # Hele Manufacturer- og Warranty-gruppen staar samlet.
    assert [f for f, k, _l in cfg.PANEL_FIELDS if k == "Mfr"] == p.MFR_FIELDS
    assert [f for f, k, _l in cfg.PANEL_FIELDS if k == "War"] == p.WAR_FIELDS
    assert "StrIndicator" not in [l for _f, _k, l in cfg.PANEL_FIELDS]


def test_generated_panel_sections_and_no_status():
    kids = T._children("conFlEditorSections")
    assert kids == ["btnFlPanelShowAll"] + [f"conFlPanel{k}" for k, _t in cfg.PANEL_SECTIONS]
    assert T._ctrl("conFlPanelStatus") is None
    on = T._prop("btnFlRowClassData", "OnSelect")
    assert 'Section <> "Status"' in on
    # Hver sektion: sine felter, i panelets raekkefoelge.
    for k, _t in cfg.PANEL_SECTIONS:
        assert T._prop(f"galFlPanel{k}Fields", "Items") == f'Sort(Filter(colFlDet, Pane = "{k}"), PaneOrd)'
    # Plads og etiket staar i colFlPane i den samlede app.
    app = open(BIO_APP, encoding="utf-8").read()
    assert "colFlPane = Table(" in app
    assert '{ Field: "STRINDICATOR", Pane: "Main", Ord: 3, Label: "KKS type" }' in app


def test_editing_does_not_rebuild_or_close_the_panel():
    verify = T._prop("btnFlVerify", "OnSelect")
    # Afsnit H: kun ved en ny klasse - ikke efter hver aendring.
    h = verify.split("// H.")[1].split("// I.")[0]
    assert "<> varFlDetCls" in h
    assert "ClearCollect(colFlDet" in h
    assert "Set(varFlPanelOpen, false)" not in verify
    # Felterne laeser vaerdi og besked selv - ikke samlingens kopi.
    for n in ("inpFlPanelClassVal", "drpFlPanelClassVal", "chkFlPanelTRMVal", "txtFlPanelMainRo"):
        props = T._ctrl(n)["Properties"]
        # ItemDisplayText er undtaget: den maa kun bruge dropdownens egen
        # ThisItem (issue #300).
        assert not any("ThisItem.Value" in str(v) for k, v in props.items()
                       if k != "ItemDisplayText"), n
    assert "LookUp(colFlVals, RowGuid = varFlDetailRow && Field = ThisItem.Field)" in \
        T._prop("inpFlPanelClassVal", "Default")
    # Sloeret bag panelet daekker kun siden VED SIDEN AF panelet.
    w = T._prop("imgFlEditorBackdrop", "Width")
    assert w.startswith("Max(0, App.Width - (")
    assert "> 0" in T._prop("imgFlEditorBackdrop", "Visible")


def test_class_popup_is_above_the_panel_and_blocks_it():
    top = T._screen_children()
    assert top.index("conFlEditorPanel") < top.index("imgFlClsBlock") < top.index("conFlClsBackdrop")
    assert T._prop("imgFlClsBlock", "Visible") == "IfError(varFlClsOpen, false)"
    assert T._prop("imgFlClsBlock", "Width") == "App.Width"
    assert "OnSelect" not in T._ctrl("imgFlClsBlock")["Properties"]
    # Popuppen roerer ikke panelet: Close og Apply nulstiller det ikke.
    for n in ("btnFlClsClose", "btnFlClsApply"):
        on = T._prop(n, "OnSelect")
        assert "varFlPanelOpen" not in on and "colFlDet," not in on, n


def test_submit_always_answers():
    assert T._prop("btnFlSubmit", "DisplayMode") == (
        'If(varFlViewOnly || varFlStatus = "Indsendt", DisplayMode.Disabled, DisplayMode.Edit)')
    on = T._prop("btnFlSubmit", "OnSelect")
    assert "Set(varFlConfirmSubmit, true)" in on
    # Validering ikke faerdig: koer den, og svar bagefter.
    assert "Set(varFlSubmitAsk, true);" in on and "Select(btnFlVerify)" in on
    # Blokeret: beskeden under raekkerne og som toast/notifikation.
    assert "Set(varFlInfo, If(" in on
    assert "gblToast" in on or "Notify(" in on
    verify = T._prop("btnFlVerify", "OnSelect")
    assert "IfError(varFlSubmitAsk, false)" in verify
    # Bundbjaelken under Desktop har den samme knap.
    assert T._prop("btnFlFootSubmit", "OnSelect") == on
