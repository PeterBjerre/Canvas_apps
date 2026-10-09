# -*- coding: utf-8 -*-
"""
Measuring Points godkendelse af nye Counter-raekker (issue #210, fase 4-6).

Godkendelsen staar bag flaget features.measuring_point_approval, og det er
SLUKKET i repoet. Den byggede skaerm i BIO SAP App viser derfor kun, at
intet har aendret sig. Delene bag flaget bygges her i en egen proces med
flaget taendt (domain_config og domain_parts kan ikke importeres i samme
proces som de andre domaeneapps - tre moduler hedder domain_config).

    python3 -m pytest tests/test_mp_approval.py
"""
import json
import os
import re
import subprocess
import sys

import pytest

from conftest import ROOT

APP = os.path.join(ROOT, "BIO SAP App")
MP = os.path.join(APP, "ScreenMeasuringPoint.pa.yaml")

# Bygger Measuring Point-skaermen (enkeltskaermen, praefiks Dom) med flaget
# taendt og skriver YAML'en paa stdout.
_BUILD = r'''
import os, sys
root = sys.argv[1]
sys.path.insert(0, os.path.join(root, "tools"))
import env_config as env
env.FEATURES["measuring_point_approval"] = True
sys.path.insert(0, os.path.join(root, "Measuring Point App", "build"))
import assemble_screen
from gen_screen import render_screen
sys.stdout.write(assemble_screen.build_screen(render_screen))
'''


@pytest.fixture(scope="module")
def on():
    out = subprocess.run([sys.executable, "-c", _BUILD, ROOT], cwd=ROOT,
                         capture_output=True, text=True, encoding="utf-8")
    assert out.returncode == 0, out.stderr[-2000:]
    return out.stdout


def _off():
    return open(MP, encoding="utf-8").read()


def _features():
    cfg = json.load(open(os.path.join(ROOT, "tools", "canvas_apps.json"), encoding="utf-8"))
    return cfg["environments"]["dev"]["features"]


# ---------------------------------------------------------------------------
# Flaget
# ---------------------------------------------------------------------------
def test_the_flag_is_off_by_default():
    assert _features()["measuring_point_approval"] is False


def test_without_the_flag_the_screen_works_as_before():
    """Slukket: intet opslag, ingen vagt, ingen stribe og intet flow - og
    Submit gaar direkte til Master Data (Q12), som i fase 1-3."""
    t = _off()
    assert "BioSap-Material-ResolveApprovers" not in t
    assert "BioSap-MeasuringPoint-Approval" not in t
    assert "imgMpSteps" not in t
    assert "colMpCreators" not in t
    assert 'Status: { Value: "KlarTilSAP" }' in t


# ---------------------------------------------------------------------------
# Valgkolonnerne i SharePoint (skema.md: Choice)
# ---------------------------------------------------------------------------
CHOICES = ("ExistsInSap", "MeasuringPointType", "InProdos", "ProdosCounterExists",
           "CounterCreateIn")


def test_choice_columns_are_written_as_records_and_read_as_value():
    """Kolonnerne er Choice i udtraekket. En tekst i Patch og Coalesce paa
    en valgrecord compiler ikke i Studio."""
    t = _off()
    for col in CHOICES:
        assert f"{col}: Coalesce(R.{col}.Value, \"\")" in t, col
        assert f"Coalesce(R.{col}, \"\")" not in t, col
        assert re.search(r"%s: (If\([^\n]*)?If\(IsBlank\(Trim\(Coalesce\(varMpF%s, \"\"\)\)\), "
                         r"Blank\(\), \{ Value: Trim\(varMpF%s\) \}\)" % (col, col, col), t), col


def test_the_choice_columns_are_choice_in_the_schema():
    schema = json.load(open(os.path.join(ROOT, "sharepoint", "inspect", "out", "schema.json"),
                            encoding="utf-8-sig"))
    lst, = [l for l in schema["lists"] if l["title"] == "MeasuringPointItems"]
    types = {f.get("displayName"): f.get("type") for f in lst["fields"]}
    for col in CHOICES:
        assert types[col] == "Choice", col


def test_equipment_and_materials_keep_their_text_columns():
    for name in ("ScreenEquipment", "ScreenMaterial"):
        t = open(os.path.join(APP, name + ".pa.yaml"), encoding="utf-8").read()
        assert "{ Value: Trim(var" not in t, name


# ---------------------------------------------------------------------------
# Vagten foer Submit (fase 4)
# ---------------------------------------------------------------------------
def _submit(t):
    """Submit-knappens OnSelect i den byggede skaerm."""
    i = t.index("btnDomSubmit:")
    j = t.index("OnSelect:", i)
    return t[j:t.index("Text:", j)]


def test_submit_looks_up_the_system_manager_only_for_new_counters(on):
    fx = _submit(on)
    assert ("'BioSap-Material-ResolveApprovers'.Run(Concat(Filter(colDomRows, "
            'Status = "valid" && Coalesce(ApprovalRequired, false)), '
            'FunctionalLocation, "; "))') in fx
    # Ingen raekker at slaa op -> intet kald.
    assert '!IsBlank(Trim(Coalesce(Concat(' in fx


def test_submit_looks_up_the_prodos_creator_per_plant(on):
    fx = _submit(on)
    assert 'LookUp(MD_Approver, ApproverKey = "PRODOS-" & P.Value)' in fx
    # Eet opslag pr. vaerk - kun for raekker, hvis taeller mangler.
    assert ('Distinct(Filter(colDomRows, Status = "valid" && MeasuringPointType = '
            '"Counter" && ExistsInSap = "No" && InProdos = "Yes" && '
            'ProdosCounterExists = "No"), Upper(Left(Trim(Coalesce(Plant, "")), 3)))') in fx
    # Fravaerende 1. godkender -> 2. godkender, som i flowene.
    assert "If(a.Approver1Absent, a.Approver2, a.Approver1)" in fx


def test_a_missing_manager_or_creator_stops_the_confirmation(on):
    fx = _submit(on)
    # Spaerret -> en besked; ellers aabner bekraeftelsen.
    assert fx.index("Notify(If(") < fx.index("Set(varDomConfirmSubmit, true)")
    for msg in ('"Cannot submit: " & First(Filter(colDomApprovers',
                '"Cannot submit: no PRODOS/SRO creator is configured for plant " & '
                'First(Filter(colDomCreators, IsBlank(Creator))).Plant & "."',
                '"Could not look up the system managers: "'):
        assert msg in fx, msg


def test_the_resolver_error_names_the_system():
    """Beskeden kommer fra flowet: "No System Manager is configured for
    system 8" - appen tilfoejer kun "Cannot submit: " og et punktum."""
    path, = [p for p in os.listdir(os.path.join(ROOT, "solution", "BIOSAP", "src", "Workflows"))
             if p.startswith("BioSap-Material-ResolveApprovers-") and p.endswith(".json")]
    txt = open(os.path.join(ROOT, "solution", "BIOSAP", "src", "Workflows", path),
               encoding="utf-8-sig").read()
    assert "No System Manager is configured for system " in txt


def test_the_collections_are_declared_only_with_the_flag():
    t = _off()
    assert "colMpApprovers" not in t and "colMpCreators" not in t


# ---------------------------------------------------------------------------
# Trinstriben (fase 4) - tools/stepper.py fra #204
# ---------------------------------------------------------------------------
def test_the_strip_has_the_same_four_nodes_before_and_after_submit(on):
    assert "imgDomSteps" in on and "txtDomStepsHint" in on
    for before, after in (('"Rows"', '"Submitted"'), ('"Approvers"', '"Approval"'),
                          ('"PRODOS / SRO"', '"PRODOS / SRO counter"'),
                          ('"Ready to submit"', '"Master Data (SAP)"')):
        assert before in on and after in on, before
    assert '"Created in SAP"' in on


def test_steps_that_do_not_apply_say_not_required(on):
    # Ingen ny Counter -> Approvers springes over; ingen manglende taeller
    # -> PRODOS / SRO springes over. Stribens "Skipped" er "Not required".
    assert ('CountRows(Filter(colDomRows, Status = "valid" && '
            'Coalesce(ApprovalRequired, false))) = 0, "Skipped"') in on
    assert ('CountRows(Filter(colDomRows, Status = "valid" && MeasuringPointType = "Counter" '
            '&& ExistsInSap = "No" && InProdos = "Yes" && ProdosCounterExists = "No")) = 0, '
            '"Skipped"') in on
    assert '"Not required"' in on


def test_after_submit_is_the_open_request_not_any_old_row(on):
    """colDomRows er ALLE brugerens raekker. "Efter Submit" maa kun vaere
    den aabne anmodning - ellers stod striben fast i "Submitted", saa
    snart brugeren havde indsendt een gang."""
    assert "varDomIdx.RequestGuid = varDomRequestGuid" in on
    assert 'Filter(colDomRows, Status = "submitted")' not in on.split("imgDomSteps")[1][:20000]


def test_the_hint_says_what_submit_would_say(on):
    for msg in ("Add a row and save it to get started.",
                "Finish the draft row before submitting.",
                "New counters are approved by the System Manager.",
                "The request is with Master Data for creation in SAP."):
        assert msg in on, msg


def test_the_hub_and_the_screen_agree_on_the_stage_names():
    """Striben laeser stadiet af LastActionBy, som flowet skriver."""
    src = open(os.path.join(ROOT, "Measuring Point App", "build", "mp_parts.py"),
               encoding="utf-8").read()
    assert 'COUNTER_ACTOR = "PRODOS/SRO counter"' in src
    assert 'APPROVAL_ACTOR = "System approval"' in src
