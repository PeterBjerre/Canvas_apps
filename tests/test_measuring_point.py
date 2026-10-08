# -*- coding: utf-8 -*-
"""
Measuring Point-skaermen (issue #210).

Testene laeser den BYGGEDE skaerm i BIO SAP App og provisioneringens seed.
De to kan ikke importeres i samme proces som Equipment og Materials (tre
moduler hedder domain_config), og det er netop derfor, de bygges hver i
sin proces - saa facit her er outputtet.

    python3 -m pytest tests/test_measuring_point.py
"""
import csv
import io
import os
import re

from conftest import ROOT

APP = os.path.join(ROOT, "BIO SAP App")
MP = os.path.join(APP, "ScreenMeasuringPoint.pa.yaml")


def _mp():
    return open(MP, encoding="utf-8").read()


def _mat():
    return open(os.path.join(APP, "ScreenMaterial.pa.yaml"), encoding="utf-8").read()


# ---------------------------------------------------------------------------
# Betingede sektioner (fase 2)
# ---------------------------------------------------------------------------
NEW = 'varMpFExistsInSap = "No"'
OLD = 'varMpFExistsInSap = "Yes"'


def test_the_screen_is_built():
    assert os.path.exists(MP), "ScreenMeasuringPoint.pa.yaml er ikke bygget"


def test_sections_are_shown_only_when_they_apply():
    t = _mp()
    # Et eksisterende punkt: kun nummeret. Et nyt: resten.
    assert "=" + OLD in t
    assert "conMpGridType" in t and "conMpGridCounter" in t
    for cond in (f'{NEW} && varMpFMeasuringPointType = "MeasuringPoint"',
                 f'{NEW} && varMpFMeasuringPointType = "Counter"',
                 f'{NEW} && varMpFInProdos = "Yes"'):
        assert cond in t, cond


def test_hidden_fields_are_cleared_when_the_row_is_saved():
    """Skifter brugeren type, maa den gamle types vaerdier ikke blive
    staaende paa raekken."""
    t = _mp()
    # ProdosTag gemmes kun, naar PRODOS = Yes.
    assert re.search(r'ProdosTag: If\(varMpFExistsInSap = "No" && '
                     r'varMpFInProdos = "Yes", Trim\(Coalesce\(varMpFProdosTag, ""\)\), ""\)', t)
    # Et eksisterende nummer gemmes kun, naar punktet findes i forvejen.
    assert 'MeasuringPoint: If(varMpFExistsInSap = "Yes"' in t


def test_is_counter_and_approval_required_are_derived():
    """Typevalget erstatter "Is it a counter?" (Q14), og kun en NY Counter
    skal godkendes (Q16)."""
    t = _mp()
    assert 'IsCounter: varMpFMeasuringPointType = "Counter"' in t
    assert ('ApprovalRequired: (varMpFMeasuringPointType = "Counter" && '
            'varMpFExistsInSap = "No")') in t


def test_the_characteristic_brings_its_unit():
    t = _mp()
    assert "drpMpCharacteristic" in t
    for setter in ("Set(varMpFCharacteristicUnit, Self.Selected.Unit)",
                   "Set(varMpFCharacteristicDescription, Self.Selected.Description)",
                   "Set(varMpFDecimalPlaces, Self.Selected.DefaultDecimalPlaces)"):
        assert setter in t, setter
    # Listen filtreres paa typen, og tom type betyder begge typer.
    assert ("Filter(colMpChars, IsBlank(MeasuringPointType) || "
            "MeasuringPointType = varMpFMeasuringPointType)") in t


def test_the_characteristic_list_is_a_named_formula_on_active_rows():
    app = open(os.path.join(APP, "App.pa.yaml"), encoding="utf-8").read()
    assert "colMpChars = Sort(" in app
    assert "Filter(MD_MpCharacteristic, Active = true)" in app


def test_validation_covers_every_combination():
    t = _mp()
    for msg in ("Select whether the measuring point already exists in SAP.",
                "Enter the existing measuring point no.",
                "Select the measuring point type.",
                "Select a characteristic from the list.",
                "Decimal places must be between 0 and 3.",
                "Enter the PRODOS tag.",
                "Select whether the counter already exists in PRODOS.",
                "Select whether the counter is created in PRODOS or SRO.",
                "Lower limit must be less than or equal to upper limit."):
        assert msg in t, msg


def test_the_duplicate_warning_does_not_block():
    t = _mp()
    assert "txtMpDuplicate" in t
    # Advarslen er en tekst, ikke et krav i gem.
    assert "already on another row in this request" in t


# ---------------------------------------------------------------------------
# Submit uden godkendelse (Q12) - godkendelsen kommer efter #204
# ---------------------------------------------------------------------------
def test_submit_goes_straight_to_master_data():
    t = _mp()
    assert 'Status: { Value: "KlarTilSAP" }' in t
    # Og den gamle vej er ikke tilbage.
    assert 'Status: { Value: "Indsendt" }' not in t


# ---------------------------------------------------------------------------
# Saved Rows: eet fast layout (Q13)
# ---------------------------------------------------------------------------
def test_saved_rows_has_no_compact_or_all_columns():
    t = _mp()
    assert "btnMpViewCompact" not in t and "btnMpViewAll" not in t
    # Og uden de to visninger findes variablen slet ikke.
    assert "varMpAllCols" not in t
    # Efter #204 har Materials (og Equipment) dem heller ikke.
    assert "btnMatViewCompact" not in _mat() and "varMatAllCols" not in _mat()


def test_saved_rows_columns_are_the_ones_the_issue_asks_for():
    t = _mp()
    for head in ('"PLANT"', '"FUNCTIONAL LOCATION"', '"MEASURING POINT"', '"TYPE"',
                 '"CHARACTERISTIC"', '"UNIT"', '"PRODOS TAG"', '"ACTIONS"'):
        assert head in t, head


def _onselect(ctrl):
    """En kontrols OnSelect i den byggede skaerm."""
    import yaml

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == ctrl and isinstance(v, dict) and "Control" in v:
                    return (v.get("Properties") or {}).get("OnSelect", "")
                hit = walk(v)
                if hit is not None:
                    return hit
        elif isinstance(node, list):
            for v in node:
                hit = walk(v)
                if hit is not None:
                    return hit
        return None

    return walk(yaml.safe_load(_mp()))


def test_rows_can_be_copied_without_the_existing_number():
    assert "btnMpRowCopy" in _mp()
    copy = _onselect("btnMpRowCopy")
    # Kopien er den samme maaling et andet sted - men ikke det SAMME punkt,
    # saa et eksisterende nummer foelger ikke med.
    assert 'Set(varMpFMeasuringPoint, "")' in copy
    assert "Set(varMpFMeasuringPoint, ThisItem.MeasuringPoint)" not in copy
    # Karakteristikken foelger med.
    assert "Set(varMpFCharacteristic, ThisItem.Characteristic)" in copy
    # Og Edit henter stadig nummeret.
    assert ("Set(varMpFMeasuringPoint, ThisItem.MeasuringPoint)"
            in _onselect("btnMpRowOpen"))


# ---------------------------------------------------------------------------
# Details: Master Data udfylder nummeret (Q8/Q19)
# ---------------------------------------------------------------------------
def test_master_data_can_fill_in_the_measuring_point_number_in_details():
    t = _mp()
    assert "inpMpDetMpNo" in t and "btnMpDetSaveMpNo" in t
    assert "CreatedMeasuringPointNo: Trim(inpMpDetMpNo.Text)" in t
    # Rettigheden staar baade i UI'et og i handlingen.
    assert "If(IsAdmin, DisplayMode.Edit, DisplayMode.View)" in t
    assert "Only Master Data and admins can fill in the measuring point no." in t
    # AEndringen logges som alle andre admin-aendringer.
    assert "AdminEdit" in t


# ---------------------------------------------------------------------------
# Hubben og sletningen
# ---------------------------------------------------------------------------
def test_the_hub_tile_opens_the_screen():
    import request_delete as rd
    hub = os.path.join(ROOT, "Masterdata Hub", "build", "hub_config.py")
    text = open(hub, encoding="utf-8").read()
    assert '"app": "measuringpoint"' in text
    assert rd.TAGS["MeasuringPoint"] == "Mp"
    steps = rd._steps("MeasuringPoint", "varMdDelGuid", "sp", "key")
    assert steps[0][0] == "MeasuringPointItems"
    assert "RequestGuid = varMdDelGuid" in steps[0][2]


def test_the_request_number_has_its_own_prefix():
    t = _mp()
    assert '"MP-" & Text(' in t


# ---------------------------------------------------------------------------
# Fase 0: provisioneringen og seedet
# ---------------------------------------------------------------------------
PROV = os.path.join(ROOT, "sharepoint", "provision",
                    "Provision-MeasuringPointLists.ps1")


def _rows(name):
    with io.open(os.path.join(ROOT, "sharepoint", "seed", name),
                 encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def test_every_field_in_the_app_is_provisioned():
    """Felterne er kontrakten: staar et felt i appen, skal kolonnen
    oprettes af provisioneringen."""
    prov = open(PROV, encoding="utf-8-sig").read()
    cfg_text = open(os.path.join(ROOT, "Measuring Point App", "build",
                                 "domain_config.py"), encoding="utf-8").read()
    cols = set(re.findall(r'^\s*\("(\w+)", "[^"]*", "\w+", ', cfg_text, re.M))
    assert "Characteristic" in cols and "ProdosTag" in cols
    for col in cols:
        assert re.search(r"'MeasuringPointItems' +'%s' " % col, prov), col


def test_the_prodos_creator_is_a_row_per_plant_in_the_approver_table():
    """Q17: rollen staar i MD_Approver med noeglen PRODOS-<vaerk>, saa der
    hverken skal en ny kolonne eller en gruppe i UserAndGroups til."""
    rows = _rows("MD_Approver_MeasuringPoint.csv")
    keys = sorted(r["ApproverKey"] for r in rows)
    assert keys == ["PRODOS-ASV", "PRODOS-AVV", "PRODOS-HEV", "PRODOS-KYV",
                    "PRODOS-SKV", "PRODOS-SSV"]
    # Start: Peter, som han staar i det eksisterende seed.
    assert {r["Approver1"] for r in rows} == {"PKBJE"}


def test_the_characteristic_seed_has_a_unit_on_every_row():
    rows = _rows("MD_MpCharacteristic.csv")
    assert rows, "seedet er tomt"
    for r in rows:
        assert r["Title"] and r["Unit"], r
        assert r["MeasuringPointType"] in ("", "Counter", "MeasuringPoint"), r
        assert r["Active"] in ("TRUE", "FALSE"), r
        assert 0 <= int(r["DefaultDecimalPlaces"]) <= 3, r


def test_the_help_texts_belong_to_the_measuring_point_area():
    rows = _rows("MD_HelpText_MeasuringPoint.csv")
    assert rows
    assert {r["AppArea"] for r in rows} == {"MeasuringPoint"}
    assert {r["Kind"] for r in rows} <= {"Hint", "Panel"}
