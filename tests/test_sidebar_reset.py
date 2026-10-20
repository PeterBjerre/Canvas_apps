# -*- coding: utf-8 -*-
"""
Reset i sidepanelerne (issue #403, #405, #450).

  - Reset kasserer KUN de ugemte aendringer og lader panelet staa aabent:
    FL gaar tilbage til aftrykket fra aabningen; Materials, Equipment og
    Measuring Point indlaeser den gemte raekke igen (eller rydder en ny).
  - Knappen er slaaet fra, naar intet er aendret.
  - Reset spoerger foerst (issue #450) med den faelles bekraeftelse
    (tests/test_reset_confirm.py). Dens sloer kan ikke blive staaende
    (issue #405): det lukker ved et tryk og vises kun, mens der er noget at
    kassere.

Power Fx kan ikke koeres her, saa testene laeser den GENEREREDE skaerm.

    python3 -m pytest tests/test_sidebar_reset.py
"""
import os
import re

import pytest

from conftest import ROOT

import test_material_objects as M

APP = os.path.join(ROOT, "BIO SAP App")
FL = os.path.join(APP, "ScreenFunctionalLocation.pa.yaml")
DOMAIN = {
    "Mat": os.path.join(APP, "ScreenMaterial.pa.yaml"),
    "Eq": os.path.join(APP, "ScreenEquipment.pa.yaml"),
    "Mp": os.path.join(APP, "ScreenMeasuringPoint.pa.yaml"),
}


def test_reset_overlay_cannot_get_stuck():
    """Issue #405: Reset-bekraeftelsens sloer lukker ved et tryk paa alle
    skaermbredder, og det vises kun sammen med popuppen."""
    for p, path in [("Fl" + "Row", FL)] + [(k, v) for k, v in DOMAIN.items()]:
        back = M._prop(f"con{p}ResetConfirmBackdrop", "OnSelect", path)
        ask = "varFlPanelResetAsk" if p == "FlRow" else f"var{p}ResetAsk"
        assert back == f"Set({ask}, false)", p
        assert M._prop(f"con{p}ResetConfirmBackdrop", "Visible", path) == \
            M._prop(f"con{p}ResetConfirmModal", "Visible", path)


def test_fl_reset_restores_the_snapshot_and_keeps_the_panel_open():
    reset = M._prop("btnFlRowResetConfirm", "OnSelect", FL)
    assert reset.startswith("Set(varFlPanelResetAsk, false);")
    assert "Patch(colFlRows, LookUp(colFlRows, RowGuid = s.RowGuid), s);" in reset
    assert "Collect(colFlVals, colFlPanelSnapVals)" in reset
    assert "Select(btnFlVerify)" in reset
    # Panelet og aftrykket bliver - kun Cancel og Close lukker.
    assert "varFlPanelOpen" not in reset
    assert "Clear(colFlPanelSnap)" not in reset
    # Slaaet fra, naar raekken er som ved aabningen, og i visning.
    mode = M._prop("btnFlEditorReset", "DisplayMode", FL)
    assert mode.startswith('If(varFlViewOnly || varFlStatus = "Indsendt" || !(With({ s: First(colFlPanelSnap)')
    assert mode.endswith("DisplayMode.Disabled, DisplayMode.Edit)")


@pytest.mark.parametrize("p", sorted(DOMAIN))
def test_domain_reset_reloads_the_saved_row_and_keeps_the_panel_open(p):
    path = DOMAIN[p]
    reset = M._prop(f"btn{p}ResetConfirm", "OnSelect", path)
    assert reset.startswith(f"Set(var{p}ResetAsk, false);")
    active = f"LookUp(col{p}Rows, RowId = var{p}ActiveRowId)"
    # Gemt raekke: de gemte vaerdier fra colRows; ny raekke: ryddes.
    assert f"If( IsBlank({active})," in " ".join(reset.split())
    assert f"Set(var{p}FText, {active}." in reset
    # Panelet staar aabent bagefter i begge grene.
    assert reset.count(f"Set(var{p}EditorOpen, true)") == 2
    assert not reset.rstrip().endswith(f"Set(var{p}EditorOpen, false)")
    # Intet gemmes eller slettes.
    for gone in ("Patch(", "Remove(", "RemoveIf(", "Set(var" + p + "Saving"):
        assert gone not in reset, gone
    mode = M._prop(f"btn{p}New", "DisplayMode", path)
    assert mode.startswith(f"If(IfError(var{p}ViewOnly, false) || !(If(")
    assert f"{{ o: {active} }}" in mode
    assert M._prop(f"btn{p}New", "Text", path) == '"Reset"'
