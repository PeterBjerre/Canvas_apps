"""Review 2026-10: domaeneskaermene (Equipment, Materials, Measuring Point)
og FL-gemmet i den genererede BIO SAP-app.

R2-038 beskrivelsens 40 tegn og SAP-feltlaengder ved gem og Paste rows.
R2-040 Equipment: udstyrstype og FL kraeves, garanti til >= fra.
R2-041 loftadvarslen (ROW_LIMIT) under tabellen og ved Save/Submit.
R2-043 FL-gemmet henter anmodningens raekker een gang; raekkeloft.
R2-072 Equipment-listens overskrifter: STATUS og REQUEST TYPE.
R2-073 nye raekker faar praefikset <PREFIX>R-.
R2-074 eet vaerk pr. anmodning (Submit-vagt, stabilt indeks-Plant, FL71).
R2-075 decimaltal i en-US.
"""
import os
import re

import pytest

from conftest import ROOT

SCREENS = {"Eq": ("ScreenEquipment", "EQ"), "Mat": ("ScreenMaterial", "MAT"),
           "Mp": ("ScreenMeasuringPoint", "MP")}


def _screen(name):
    return open(os.path.join(ROOT, "BIO SAP App", name + ".pa.yaml"), encoding="utf-8").read()


def _control(screen, name):
    lines = _screen(screen).split("\n")
    for i, l in enumerate(lines):
        if l.strip() == f"- {name}:":
            ind = len(l) - len(l.lstrip())
            out = [l]
            for m in lines[i + 1:]:
                if m.strip().startswith("- ") and len(m) - len(m.lstrip()) <= ind:
                    break
                out.append(m)
            return "\n".join(out)
    raise AssertionError(f"{name} findes ikke i {screen}")


# --- R2-038 -----------------------------------------------------------------
@pytest.mark.parametrize("tag", sorted(SCREENS))
def test_save_checks_description_length(tag):
    save = _control(SCREENS[tag][0], f"btn{tag}Save")
    assert f'Len(Trim(Coalesce(var{tag}FText, ""))) > 40' in save


@pytest.mark.parametrize("tag", sorted(SCREENS))
def test_paste_rejects_long_description(tag):
    prev = _control(SCREENS[tag][0], f"btn{tag}PastePreview")
    assert 'Len(IfError(Trim(Index(c, 1).Value), "")) > 40' in prev
    assert "longer than 40 characters" in prev


def test_sap_field_lengths():
    save = _control("ScreenMaterial", "btnMatSave")
    assert 'Len(Trim(Coalesce(varMatFStorageBin, ""))) > 10' in save
    assert '"Storage bin can have at most 10 characters."' in save
    assert re.search(r"MaxLength: \|-\n\s+=10\n", _control("ScreenMaterial", "inpMatStorageBin"))
    assert re.search(r"MaxLength: \|-\n\s+=20\n", _control("ScreenEquipment", "inpEqTypeDesignation"))


# --- R2-040 -----------------------------------------------------------------
def test_equipment_rules():
    save = _control("ScreenEquipment", "btnEqSave")
    assert "Warranty to must be on or after warranty from." in save
    assert "varEqFWarrantyEnd < varEqFWarrantyStart" in save
    assert "Equipment type is required." in save
    assert "A functional location is required." in save


# --- R2-041 -----------------------------------------------------------------
@pytest.mark.parametrize("tag", sorted(SCREENS))
def test_row_limit_warning(tag):
    scr = SCREENS[tag][0]
    assert f"CountRows(col{tag}Rows) >= 500" in _control(scr, f"txt{tag}RowsCap")
    assert "older rows are not included when you submit" in _control(scr, f"btn{tag}SubmitConfirm")


# --- R2-043 -----------------------------------------------------------------
def test_fl_save_reads_rows_once():
    save = _control("ScreenFunctionalLocation", "btnFlSaveDraft")
    assert save.count("Filter(FunctionalLocationItems, RequestGuid = varFlRequestGuid)") == 1
    assert "LookUp(colFlEx, RowGuid = R.RowGuid)" in save
    assert "Remove(FunctionalLocationItems, Filter(colFlEx," in save


def test_fl_row_cap():
    assert "CountRows(colFlRows) >= 400" in _control("ScreenFunctionalLocation", "btnFlAddRow")
    assert "+ CountRows(lines) > 400" in _control("ScreenFunctionalLocation", "btnFlPasteAdd")


# --- R2-072 -----------------------------------------------------------------
def test_equipment_list_headers():
    y = _screen("ScreenEquipment")
    assert '"VALIDATION"' not in y
    assert '"REQUEST TYPE"' in y


# --- R2-073 -----------------------------------------------------------------
@pytest.mark.parametrize("tag", sorted(SCREENS))
def test_row_key_prefix(tag):
    scr, prefix = SCREENS[tag]
    assert f'ItemKey: "{prefix}R-" & Text(' in _control(scr, f"btn{tag}PasteAdd")
    assert f'"{prefix}R-" & Text(var{tag}SpRow.ID, "000000")' in _control(scr, f"btn{tag}Save")
    # Anmodningsnummeret er uaendret.
    assert f'"{prefix}-" & Text(var{tag}Idx.ID, "000000")' in _control(scr, f"btn{tag}SubmitConfirm")


# --- R2-074 -----------------------------------------------------------------
@pytest.mark.parametrize("tag", sorted(SCREENS))
def test_one_plant_per_request(tag):
    scr = SCREENS[tag][0]
    mix = f'CountRows(Distinct(Filter(col{tag}Rows, Status = "valid"), Plant)) > 1'
    sub = _control(scr, f"btn{tag}SubmitConfirm")
    assert mix in sub
    assert f'Plant: First(Sort(Filter(col{tag}Rows, Status = "valid"), RowId)).Plant' in sub
    assert mix in _control(scr, f"btn{tag}Submit")


def test_fl_plant_mix_rule():
    verify = _control("ScreenFunctionalLocation", "btnFlVerify")
    assert "Set(varFlPlantMix, CountRows(Distinct(Filter(colFlRows, !IsBlank(FL)), Left(FL, 3))) > 1)" in verify
    assert 'Code: "FL71"' in verify


# --- R2-075 -----------------------------------------------------------------
def test_decimals_are_en_us():
    save = _control("ScreenMeasuringPoint", "btnMpSave")
    assert 'Value(Trim(varMpFTargetValue), "en-US")' in save
    assert '"Target value: use . as decimal separator."' in save
    assert 'Text(R.TargetValue, "0.###", "en-US")' in save
    assert "Use . as decimal separator" in _control("ScreenMeasuringPoint", "inpMpTargetValue")
