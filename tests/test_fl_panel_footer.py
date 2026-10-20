# -*- coding: utf-8 -*-
"""
Functional Location-sidepanelet som Materials' (issue #308).

  - Bundbjaelken: Delete row og Reset til venstre, Cancel og Save til
    hoejre - samme byggeklods som Materials (build_helpers.editor_footer),
    uden for det, der scroller.
  - GIV_EXT/WCM (Section "Ext") vises ingen steder - kun i visningen;
    reglerne og de gemte vaerdier er uroert.
  - KKS type og Assigned class staar paa een linje lige foer Class data,
    uden "Derived from/Determined by the KKS code".
  - Dropdowns har samme stil som Materials'.

Power Fx kan ikke koeres her, saa testene laeser den GENEREREDE skaerm.

    python3 -m pytest tests/test_fl_panel_footer.py
"""
import os

from conftest import ROOT

import test_fl_spool_row as T

MAT = os.path.join(ROOT, "BIO SAP App", "ScreenMaterial.pa.yaml")


def _mat(ctrl):
    import yaml
    if MAT not in T._TREE:
        T._TREE[MAT] = yaml.safe_load(open(MAT, encoding="utf-8").read())
    return T._find(T._TREE[MAT], ctrl)


def _mat_children(ctrl):
    return [list(c)[0] for c in _mat(ctrl).get("Children", [])]


def test_footer_like_materials_outside_the_scroll():
    assert T._children("conFlEditorPanel") == [
        "conFlEditorHeading", "conFlEditorSections", "conFlEditorSaveStatus",
        "conFlEditorFooter"]
    assert T._children("conFlEditorFooter") == ["conFlEditorDeleteAction", "conFlEditorSaveActions"]
    assert T._children("conFlEditorDeleteAction") == ["btnFlEditorDelete", "btnFlEditorReset"]
    assert T._children("conFlEditorSaveActions") == ["btnFlEditorCancel", "btnFlEditorSave"]
    # Samme opbygning og samme regler for een/to linjer som Materials.
    assert _mat_children("conMatEditorFooter") == ["conMatEditorDeleteAction",
                                                   "conMatEditorSaveActions"]
    for prop in ("Height", "LayoutDirection", "LayoutAlignItems", "LayoutJustifyContent"):
        assert T._prop("conFlEditorFooter", prop) == \
            str(_mat("conMatEditorFooter")["Properties"][prop]).lstrip("="), prop
    # Scrollen giver plads til bundbjaelken.
    assert "conFlEditorFooter" not in T._children("conFlEditorSections")
    assert "If((" in T._prop("conFlEditorSections", "Height")
    for a, b in (("btnFlEditorDelete", "btnMatEditorDelete"),
                 ("btnFlEditorCancel", "btnMatEditorCancel"),
                 ("btnFlEditorSave", "btnMatSave")):
        for prop in ("Text", "Width", "Height", "Appearance"):
            mine = T._ctrl(a)["Properties"].get(prop)
            theirs = _mat(b)["Properties"].get(prop)
            # Panelets tilstand hedder hver sin variabel ("Saving...", #420).
            assert str(mine) == str(theirs).replace("varMatPanelSave", "varFlPanelSave"), (a, prop)


def test_footer_actions():
    locked = 'If(varFlViewOnly || varFlStatus = "Indsendt", DisplayMode.Disabled, DisplayMode.Edit)'
    assert T._prop("btnFlEditorDelete", "OnSelect") == "Set(varFlPanelDelAsk, true)"
    assert T._prop("btnFlEditorDelete", "DisplayMode") == locked
    # Reset spoerger foerst, naar der er aendringer (issue #450); ellers
    # gaar den direkte tilbage til aftrykket.
    reset = T._prop("btnFlEditorReset", "OnSelect")
    assert reset.startswith("If(\n    With({ s: First(colFlPanelSnap)")
    assert "Set(varFlPanelResetAsk, true)" in reset
    assert "Collect(colFlVals, colFlPanelSnapVals)" in T._prop("btnFlRowResetConfirm", "OnSelect")
    cancel = T._prop("btnFlEditorCancel", "OnSelect")
    assert "Collect(colFlVals, colFlPanelSnapVals)" in cancel
    assert cancel.rstrip().endswith("Clear(colFlPanelSnapVals)")
    # Save er det samme gem som Save draft og lukker kun, naar det lykkedes.
    # Tilstanden vises i panelet - ikke sidens sloer (issue #402).
    save = T._prop("btnFlEditorSave", "OnSelect")
    assert save.startswith('Set(varFlPanelSave, "saving");\nClear(colFlSaveErrors);')
    assert save.rstrip().endswith('Clear(colFlPanelSnapVals), Set(varFlPanelSave, "failed"))')
    assert ('If(CountRows(colFlSaveErrors) = 0, Set(varFlPanelSave, ""); '
            'Set(varFlPanelOpen, false);') in save
    assert "varFlSaving" not in save
    # Save draft har sin egen ventetilstand udenom (issue #420); indeni er
    # det de samme regler som panelets Save.
    act = 'If(IfError(!IsBlank(varFlAct) && !(":" in varFlAct), false), DisplayMode.Disabled, '
    draft = T._prop("btnFlSaveDraft", "DisplayMode")
    assert draft.startswith(act) and draft.endswith(")")
    assert T._prop("btnFlEditorSave", "DisplayMode") == (
        'If(IfError(varFlPanelSave = "saving", false), DisplayMode.Disabled, '
        + draft[len(act):-1] + ")")
    # Panelet tager aftrykket, naar det aabnes paa en raekke.
    on = T._prop("btnFlRowClassData", "OnSelect")
    assert "ClearCollect(colFlPanelSnap, LookUp(colFlRows, RowGuid = varFlDetailRow));" in on
    # Bekraeftelserne ligger over panelet.
    top = T._screen_children()
    assert top.index("conFlEditorPanel") < top.index("conFlRowDelConfirmModal")
    confirm = T._prop("btnFlRowDelConfirm", "OnSelect")
    assert "Collect(colFlDeleted, { RowGuid: varFlDetailRow });" in confirm
    assert "Set(varFlPanelOpen, false)" in confirm
    # Den samlede app koerer FL's opstart i skaermen.
    app = T._text()
    assert "Set(varFlPanelDelAsk, false);" in app
    assert "If(false, ClearCollect(colFlPanelSnap, {" in app


def test_giv_ext_and_wcm_are_gone_from_the_ui():
    text = T._text()
    assert "GIV_EXT" not in text and "WCM" not in text
    for gone in ("conFlPanelExt", "galFlPanelExtFields", "galFlXFields", "txtFlXGroupH"):
        assert T._ctrl(gone) is None, gone
    assert 'Section <> "Status" && Section <> "Ext"' in T._prop("btnFlRowClassData", "OnSelect")
    # Edit i Classes aabner samme panel (issue #346).
    assert 'Section <> "Status" && Section <> "Ext"' in T._prop("btnFlCOpen", "OnSelect")


def test_kks_type_beside_assigned_class_before_class_data():
    text = T._text()
    assert "Derived from the KKS code." not in text
    assert "Determined by the KKS code." not in text
    main = T._children("conFlPanelMain")
    assert main == ["txtFlPanelMainTitle", "galFlPanelMainFields", "galFlPanelKksFields"]
    assert T._prop("galFlPanelKksFields", "Items") == 'Sort(Filter(colFlDet, Pane = "Kks"), PaneOrd)'
    cols = T._prop("galFlPanelKksFields", "WrapCount")
    assert cols.startswith("If((") and cols.endswith(", 2, 1)")
    sections = T._children("conFlEditorSections")
    assert sections.index("conFlPanelMain") + 1 == sections.index("conFlPanelClass")


def test_dropdowns_use_the_materials_style():
    ref = _mat("drpMatPlant")["Properties"]
    for name in ("drpFlPanelMainVal", "drpFlPanelClassVal", "drpFlPanelLocVal",
                 "drpFlPanelTRMVal"):
        props = T._ctrl(name)["Properties"]
        for prop in ("BasePaletteColor", "Font", "Size"):
            assert str(props[prop]) == str(ref[prop]), (name, prop)
        assert "Appearance.FilledDarker" in str(props["Appearance"]), name
        assert "C.'input-fg'" in str(props["Color"]), name
        assert "C.'input-bg'" in str(props["Fill"]), name
        assert str(props["ItemDisplayText"]).lstrip("=").strip() == "ThisItem.Value", name
