"""Sorteringsfeltet sendes som SAP's noegle (010, 020 ...), og DAY kan ikke
vaelges som cyklusenhed (Peter 2026-10-18)."""
import csv
import json
import os
import re

from conftest import ROOT

SEED = os.path.join(ROOT, "sharepoint", "seed", "SortFieldList.csv")


def _app():
    return open(os.path.join(ROOT, "BIO SAP App", "App.pa.yaml"), encoding="utf-8").read()


def _seed():
    return list(csv.DictReader(open(SEED, encoding="utf-8-sig")))


def test_seed_keys_are_three_digits_and_unique():
    keys = [r["SortKey"] for r in _seed()]
    assert all(re.fullmatch(r"\d{3}", k) for k in keys)
    assert len(keys) == len(set(keys))


def test_seed_covers_every_row_in_the_list():
    # Foer provisionering staar beskrivelsen i Title; bagefter noeglen i Title og
    # beskrivelsen i SortFieldDescription. Begge former skal passe med seed'en.
    by_desc = {r["Description"].lower(): r["SortKey"] for r in _seed()}
    pairs = {(r["SortKey"], r["Description"].lower()) for r in _seed()}
    sample = json.load(open(os.path.join(ROOT, "sharepoint", "inspect", "out",
                                         "sample-SortFieldList.json"), encoding="utf-8-sig"))
    unknown = [r["Title"] for r in sample
               if r["Title"].lower() not in by_desc
               and (r["Title"], (r.get("SortFieldDescription") or "").lower()) not in pairs]
    assert unknown == []


def test_dropdown_shows_key_and_description_but_keeps_the_key():
    assert ('colVhpSortFieldOptions = Sort(ForAll(SortFieldList As R, { Id: R.ID, Value: R.Title, '
            'Name: Trim(R.Title & " " & R.SortFieldDescription) }), Value)') in _app()
    screen = open(os.path.join(ROOT, "BIO SAP App", "ScreenVhPlan.pa.yaml"), encoding="utf-8").read()
    i = screen.find("- drpVhpSortField:")
    assert "=ThisItem.Name" in screen[i:i + 6000]
    assert "SortField: drpVhpSortField.Selected.Value" in screen


def test_opretter_uses_the_key_not_the_lookup_id():
    steps = open(os.path.join(ROOT, "excel", "opretter", "VhpSteps.bas"), encoding="ascii").read()
    assert "sortFieldId" not in steps
    assert "Array(VhpMap.SortKey(sortText))" in steps


def test_day_is_not_a_cycle_unit():
    assert 'colVhpUnitOptions = Filter(Choices(MaintenancePlans.Unit), Value <> "DAY")' in _app()
