# -*- coding: utf-8 -*-
"""
R2-012: Appen skriver RowStatus "draft", "valid" og "submitted" paa
EquipmentItems, MaterialItems og MeasuringPointItems. Valgene skal derfor
staa i provisioneringen, og New-MdField skal tilfoeje manglende valg paa
en kolonne, der findes i forvejen - ellers faar listerne fra foer #204
aldrig "draft".

schema.json er det gamle udtraek (EquipmentItems/MaterialItems har kun
valid og submitted), indtil Provision-EqMatLists.ps1 er koert og skemaet
eksporteret igen. Testen tjekker derfor provisioneringen og New-MdField -
ikke schema.json.

    python3 -m pytest tests/test_rowstatus_choices.py
"""
import os
import re

from conftest import ROOT

PROV = os.path.join(ROOT, "sharepoint", "provision")
WANTED = {"draft", "valid", "submitted"}


def _read(name):
    with open(os.path.join(PROV, name), encoding="utf-8-sig") as f:
        return f.read().replace("\r\n", "\n")


def _ps1_list(text, name):
    m = re.search(r"^\$" + name + r"\s*=\s*((?:'[^']*'\s*,?\s*)+)", text, re.M)
    assert m, "$" + name + " mangler"
    return re.findall(r"'([^']*)'", m.group(1))


def _function(text, name):
    m = re.search(r"^function " + name + r" \{\n(.*?)^\}", text, re.S | re.M)
    assert m, name + " mangler"
    return m.group(1)


def test_eqmat_provisions_all_row_statuses():
    text = _read("Provision-EqMatLists.ps1")
    assert set(_ps1_list(text, "ROWSTATUS")) >= WANTED
    batch = _function(text, "Add-BatchColumns")
    assert re.search(r"New-MdField \$List 'RowStatus'\s+Choice -Choices \$ROWSTATUS", batch)
    # Begge lister faar batch-kolonnerne - og dermed RowStatus.
    for lst, fn in (("EquipmentItems", "New-EquipmentList"),
                    ("MaterialItems", "New-MaterialList")):
        assert "Add-BatchColumns '%s'" % lst in _function(text, fn), lst
        assert re.search(r"^\s+" + fn + r"\s*$", text, re.M), fn + " kaldes ikke"


def test_measuring_point_provisions_all_row_statuses():
    text = _read("Provision-MeasuringPointLists.ps1")
    assert set(_ps1_list(text, "ROWSTATUS")) >= WANTED
    assert re.search(r"New-MdField 'MeasuringPointItems' 'RowStatus'\s+Choice -Choices \$ROWSTATUS",
                     text)


def test_new_md_field_adds_missing_choices_to_existing_field():
    body = _function(_read("_Common.psm1"), "New-MdField")
    # Eksisterende felt + -Choices: laes de nuvaerende valg og tilfoej de
    # manglende bagefter (foreningsmaengde, raekkefoelgen beholdes).
    assert "if ($f -and $Choices)" in body
    assert "$current = Get-MdChoices $f" in body
    assert "$Choices | Where-Object { $current -notcontains $_ }" in body
    assert "Set-MdChoices $List $Name ([string[]]($current + $missing))" in body
    # Set-PnPField -Values @{ Choices = ... } ignoreres paa nogle
    # PnP-versioner (kun en advarsel) - den maa ikke komme igen.
    assert "Values @{ Choices" not in body
    assert '"    ~ $Name (choices +' in body
    # Kolonnen oprettes stadig kun, naar den ikke findes.
    assert body.index("if ($f -and $Choices)") < body.index("Add-PnPField @p")


def test_set_md_choices_writes_schemaxml_and_verifies():
    text = _read("_Common.psm1")
    body = _function(text, "Set-MdChoices")
    assert "Values @{ SchemaXml = $xml.OuterXml }" in body
    # Kolonnen laeses igen, og et manglende valg er en fejl, ikke en succes.
    assert "Get-MdChoices (Get-PnPField -List $List -Identity $Name" in body
    assert "throw " in body
    assert "Get-MdChoices" in text.split("Export-ModuleMember", 1)[1]
    assert "Set-MdChoices" in text.split("Export-ModuleMember", 1)[1]


def test_no_script_sets_choices_through_set_pnpfield():
    for name in os.listdir(PROV):
        if name.endswith((".ps1", ".psm1")):
            assert "Values @{ Choices" not in _read(name), name
