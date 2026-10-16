# -*- coding: utf-8 -*-
"""
Sync-StandardTaskOperations.ps1: standardoperationerne ud i Excel og ind
igen. Kolonnerne i scriptet skal findes i MD_StandardTaskOperations med
samme type - ellers skriver importen til et felt, der ikke er der.

    python3 -m pytest tests/test_std_ops_sync.py
"""
import json
import os
import re

from conftest import ROOT

SCRIPT = os.path.join(ROOT, "sharepoint", "provision", "Sync-StandardTaskOperations.ps1")
SCHEMA = os.path.join(ROOT, "sharepoint", "inspect", "out", "schema.json")
APP = os.path.join(ROOT, "BIO SAP App", "App.pa.yaml")


def _columns():
    text = open(SCRIPT, encoding="utf-8-sig").read()
    block = re.search(r"\$COLUMNS = @\((.*?)\n\)", text, re.S).group(1)
    return re.findall(r"Name = '(\w+)';\s*Type = '(\w+)'", block)


def _list_fields():
    d = json.load(open(SCHEMA, encoding="utf-8-sig"))
    lst = next(l for l in d["lists"] if l["title"] == "MD_StandardTaskOperations")
    return {f["internalName"]: f["type"] for f in lst["fields"]}


def test_columns_exist_in_list_with_same_type():
    fields = _list_fields()
    cols = _columns()
    assert len(cols) == 24
    for name, typ in cols:
        assert name in fields, name + " findes ikke i listen"
        assert fields[name] == typ, "%s er %s i listen, ikke %s" % (name, fields[name], typ)


def test_every_editable_field_is_in_the_file():
    """Alle redigerbare felter undtagen noeglen og TaskLabel staar i filen,
    saa en eksport/import ikke stille taber et felt."""
    fields = _list_fields()
    readonly = {"ID", "Modified", "Created", "Author", "Editor"}
    skip = readonly | {"Title", "Plant", "OperationNo"}
    names = {n for n, _ in _columns()}
    assert set(fields) - skip == names


def test_fields_the_app_reads_are_covered():
    app = open(APP, encoding="utf-8").read()
    m = re.search(r"colVhpStdOps = ForAll\(MD_StandardTaskOperations As O, \{(.*?)\}\)", app)
    used = set(re.findall(r"O\.(\w+)", m.group(1))) - {"Plant", "OperationNo"}
    names = {n for n, _ in _columns()}
    assert used <= names, used - names
