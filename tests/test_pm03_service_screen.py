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
