# -*- coding: utf-8 -*-
"""
Generatoren til html/lookups.generated.js (R2-076).

1. Formatet: tools/extract_spool_lists.format_lookups_js skriver den
   committede fil byte for byte igen ud fra dens eget indhold. Saa er en
   forskel efter --write-js arkets, ikke formatets.
2. Noeglerne: de tabeller, Functional Location-reglerne bygger paa, er de
   samme i SPOOL-arket i repoet og i FL_LOOKUPS (docs/31 AQ8).

Arket i repoet (excel/artifact/) er AELDRE end lookups.generated.js: fem
tabeller, der ikke bruges af reglerne, afviger (se docs/31 AQ8). Derfor
tjekkes kun noegletabellerne mod arket.
"""
import os

import pytest

from conftest import ROOT

import extract_spool_lists as esl

XLSM = os.path.join(ROOT, "excel", "artifact", "FL indberetninger udgave SPOOL V3.xlsm")
KEY_TABLES = ("ClassDeterminationComponentKey", "ClassDeterminationAggregateKey",
              "FunctionKeyDict", "BR18_Keys", "Plant", "Char")


def test_format_reproduces_committed_file_byte_for_byte():
    with open(esl.JS_OUT, "rb") as f:
        committed = f.read()
    assert esl.format_lookups_js(esl.read_lookups_js(), esl.js_eol()) == committed


def test_js_string_escaping():
    assert esl._js_string('a"b\\c<&>\n') == '"a\\"b\\\\c\\u003c\\u0026\\u003e\\n"'
    assert esl._js_string("Sønderskov") == '"Sønderskov"'


def test_empty_list_and_nesting_format():
    js = esl.format_lookups_js({"T": {"sheet": "S", "headers": ["H"], "rows": []}})
    assert js == ("﻿window.FL_LOOKUPS = {\r\n"
                  '    "T":  {\r\n'
                  '              "sheet":  "S",\r\n'
                  '              "headers":  [\r\n'
                  '                              "H"\r\n'
                  '                          ],\r\n'
                  '              "rows":  [\r\n'
                  '\r\n'
                  '                       ]\r\n'
                  '          }\r\n'
                  '};\r\n').encode("utf-8")


def test_key_tables_match_the_spool_sheet():
    openpyxl = pytest.importorskip("openpyxl")
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        wb = openpyxl.load_workbook(XLSM, data_only=True)
    sheet = esl.lookups_from_workbook(wb)
    js = esl.read_lookups_js()
    for name in KEY_TABLES:
        assert sheet[name] == js[name], name
