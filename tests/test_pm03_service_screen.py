"""PM03: Enter paa operationen aabner selv ydelsesskaermen (SAPLMLSP 201).
Opretteren maa ikke lede efter operationstabellen der (MP0146, 2026-10-18)."""
import os

from conftest import ROOT


def _add_service():
    src = open(os.path.join(ROOT, "excel", "opretter", "VhpSteps.bas"), encoding="latin-1").read()
    i = src.find("Private Sub AddService(")
    return src[i:src.find("End Sub", i)]


def test_add_service_starts_on_the_service_screen():
    body = _add_service()
    assert "IA05_OP_TABLE" not in body
    assert "VisibleOperationRow" not in body
    assert body.index("VhpSap.Exists(sess, IA05_SRV_TABLE)") < body.index("IA05_SRV_MODELSPEC_BTN")


def test_ip01_stops_clearly_when_no_free_item_is_found():
    src = open(os.path.join(ROOT, "excel", "opretter", "VhpSteps.bas"), encoding="latin-1").read()
    i = src.find('VhpSap.Fnd(sess, IP01_ITEM_GRID).SelectedRows = "0"')
    assert "If Not VhpSap.Exists(sess, IP01_ITEM_GRID) Then" in src[i - 600:i]


def test_ip01_finds_the_sort_field_by_name_and_does_not_stop_on_it():
    src = open(os.path.join(ROOT, "excel", "opretter", "VhpSteps.bas"), encoding="latin-1").read()
    assert 'FindByName("RMIPM-PLAN_SORT", "GuiComboBox")' in src
    i = src.find("sortId = SortFieldId(sess)")
    assert i > 0 and "AddStepWarning" in src[i:i + 400]
    assert "VhpSap.SelectCombo(sess, IP01_SORT_FIELD" not in src
