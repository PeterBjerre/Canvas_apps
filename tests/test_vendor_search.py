# -*- coding: utf-8 -*-
"""Leverandoersoegningen paa PM02-operationer i VH-planen.

Kontrakten i tools/vendor_search.py skal passe til flowet, som det ligger
i solution-eksporten, og den genererede skaerm skal bruge den."""
import glob
import json
import os

import vendor_search as vs

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenVhPlan.pa.yaml")


def _flow():
    [path] = glob.glob(os.path.join(
        ROOT, "solution", "BIOSAP", "src", "Workflows",
        "BioSap-Integration-VendorsAll-*.json"))
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)["properties"]["definition"]


def test_flow_name_and_output_match_the_solution():
    d = _flow()
    assert d["triggers"]["manual"]["kind"] == "PowerAppV2"
    props = d["triggers"]["manual"]["inputs"]["schema"]["properties"]
    assert list(props) == ["text"], "flowet tager eet tekst-input"
    resp = d["actions"]["Finally"]["actions"]["Respond_to_a_Power_App_or_flow"]
    assert vs.FLOW_OUTPUT in resp["inputs"]["schema"]["properties"]
    assert vs.FLOW_NAME == "'BioSap-Integration-VendorsAll'"


def test_query_searches_the_vendor_search_column():
    q = _flow()["actions"]["Try"]["actions"]["Run_a_query_against_a_dataset"]
    dax = q["inputs"]["parameters"]["specification/query"]
    assert "'Vendors'[Vendor Search]" in dax
    assert vs.JSON_SEARCH_FIELD.strip("'") == "Vendors[Vendor Search]"


def test_screen_uses_the_vendor_flow_and_no_free_text_vendor():
    with open(SCREEN, encoding="utf-8") as f:
        y = f.read()
    assert "'BioSap-Integration-VendorsAll'.Run(" in y
    assert "cmbVhpVendor:" in y and "btnVhpVenSearch:" in y
    assert "btnVhpOpVendor:" in y and "btnVhpOpMVendor:" in y
    # Det frie tekstfelt er vaek - leverandoeren kan kun soeges frem.
    assert "inpVhpOpVendor:" not in y and "inpVhpOpMVendor:" not in y
    assert "{ Vendor: Self.Text }" not in y


def test_fl_picker_names_unchanged():
    """Generaliseringen af fl_picker maa ikke omdoebe FL-vaelgerens kontroller."""
    with open(SCREEN, encoding="utf-8") as f:
        y = f.read()
    for n in ("btnVhpFlSearch:", "imgVhpFlBusy:", "conVhpFlWrap:", "tmrVhpFlCapture:"):
        assert n in y
