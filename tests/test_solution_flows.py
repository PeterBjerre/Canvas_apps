# -*- coding: utf-8 -*-
"""
R2-022/R2-023: repoets solution/ er kilden til flowene (docs/22).

Flow-rettelser laves i Workflows/*.json med kontrakttests, og Peter
importerer solutionen. Det holder kun, hvis JSON'en er importerbar og ikke
baerer hemmeligheder. Vaernet her:

- hver flow-JSON kan parses og har en definition;
- "***REDACTED***" staar KUN som defaultValue paa en parameter (en
  miljoevariabel, hvis vaerdi saettes i miljoeet) - aldrig midt i en
  handling, hvor den ville blive sendt som den bogstavelige tekst;
- API-noeglen (x-apikey) og client secret laeses fra miljoevariabler;
- hver miljoevariabel, et flow bruger, har en definition i solutionen,
  og definitionernes standardvaerdier er tomme eller redigerede;
- scrub_solution.py finder intet at fjerne.

    python3 -m pytest tests/test_solution_flows.py
"""
import glob
import json
import os
import re

from conftest import ROOT
import scrub_solution

SRC = os.path.join(ROOT, "solution", "BIOSAP", "src")
FLOWS = sorted(glob.glob(os.path.join(SRC, "Workflows", "*.json")))
EV_DIR = os.path.join(SRC, "environmentvariabledefinitions")
REDACTED = "***REDACTED***"
API_KEY = "BioSap-WOC-ApiKey (orsted_BioSapWocApiKey)"
# WOE- og lager-flowene (docs/44) kalder DEV-gatewayen med sine egne noegler.
DEV_API_KEYS = ("BioSap-WOE-Dev-ApiKey (orsted_BioSapWoeDevApiKey)",
                "BioSap-Inventory-Dev-ApiKey (orsted_BioSapInventoryDevApiKey)")


def _load(path):
    return json.load(open(path, encoding="utf-8-sig"))


def _strings(node, path=()):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _strings(v, path + (k,))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _strings(v, path + (i,))
    elif isinstance(node, str):
        yield path, node


def test_every_flow_parses():
    assert len(FLOWS) >= 20
    for path in FLOWS:
        d = _load(path)
        assert "triggers" in d["properties"]["definition"], path
        assert os.path.exists(path + ".data.xml"), path


def test_redacted_only_as_parameter_defaults():
    for path in FLOWS:
        for where, value in _strings(_load(path)):
            if REDACTED in value:
                assert where[:3] == ("properties", "definition", "parameters") \
                    and where[-1] == "defaultValue", \
                    "%s: %s er redigeret midt i flowet - JSON'en er ikke " \
                    "importerbar" % (os.path.basename(path), "/".join(map(str, where)))


def test_api_key_and_client_secret_come_from_environment_variables():
    seen = 0
    for path in FLOWS:
        for where, value in _strings(_load(path)):
            if where and where[-1] == "x-apikey":
                assert value in ["@parameters('%s')" % k for k in (API_KEY,) + DEV_API_KEYS], path
                seen += 1
            if "client_secret=" in value:
                assert re.search(r"client_secret=@\{parameters\('[^']+'\)\}", value), path
    assert seen == 4


def test_flow_environment_variables_are_defined_in_the_solution():
    defined = set(os.listdir(EV_DIR))
    for path in FLOWS:
        params = _load(path)["properties"]["definition"]["parameters"]
        for name, p in params.items():
            schema = p.get("metadata", {}).get("schemaName")
            if schema:
                assert schema in defined, "%s: %s" % (os.path.basename(path), schema)


def test_environment_variable_defaults_are_empty_or_redacted():
    for xml in glob.glob(os.path.join(EV_DIR, "*", "environmentvariabledefinition.xml")):
        text = open(xml, encoding="utf-8-sig").read()
        for value in re.findall(r"<defaultvalue>(.*?)</defaultvalue>", text, re.S):
            assert value == REDACTED, xml
    for name in ("orsted_BioSapWOCClientSecret", "orsted_BioSapWocApiKey",
                 "orsted_BioSapWoeDevApiKey", "orsted_BioSapInventoryDevApiKey"):
        text = open(os.path.join(EV_DIR, name, "environmentvariabledefinition.xml"),
                    encoding="utf-8-sig").read()
        assert "<defaultvalue>" not in text, name


def test_scrub_finds_nothing():
    for path in FLOWS + glob.glob(os.path.join(EV_DIR, "*", "*.xml")):
        text = open(path, encoding="utf-8-sig").read()
        _new, hits = scrub_solution.scrub_text(text, path)
        assert hits == [], "%s: %s" % (path, hits)


def _containers(acts):
    yield acts
    for a in acts.values():
        if "actions" in a:
            yield from _containers(a["actions"])
        if "else" in a:
            yield from _containers(a["else"].get("actions", {}))
        for case in a.get("cases", {}).values():
            yield from _containers(case.get("actions", {}))
        if "default" in a:
            yield from _containers(a["default"].get("actions", {}))


def test_every_run_after_names_a_sibling_and_names_are_unique():
    """En handledt JSON-rettelse maa ikke efterlade en runAfter, der peger
    ud af sit scope, eller to handlinger med samme navn - begge afvises
    foerst ved import."""
    for path in FLOWS:
        d = _load(path)["properties"]["definition"]
        names = []
        for acts in _containers(d["actions"]):
            names.extend(acts)
            for n, a in acts.items():
                for dep in (a.get("runAfter") or {}):
                    assert dep in acts, "%s: %s -> %s" % (os.path.basename(path), n, dep)
        dup = {n for n in names if names.count(n) > 1}
        assert not dup, "%s: %s" % (os.path.basename(path), dup)


def test_parameter_names_have_no_stray_spaces():
    """R2-084 pkt. 5: ' BioSap-EmailDomain (...)' med foranstillet mellemrum
    knaekkede copy/paste af udtryk mellem flows."""
    for path in FLOWS:
        for name in _load(path)["properties"]["definition"]["parameters"]:
            assert name == name.strip(), "%s: %r" % (os.path.basename(path), name)


def test_outlook_runs_as_the_service_connection():
    """R2-084 pkt. 4: DelayFlows fejlmail sendes med den delte forbindelse,
    ikke som den bruger, der startede flowet."""
    for name in ("BioSap-DelayFlow",):
        path, = glob.glob(os.path.join(SRC, "Workflows", name + "-*.json"))
        refs = _load(path)["properties"]["connectionReferences"]
        for ref in refs.values():
            if ref["api"]["name"] == "shared_office365":
                assert ref["runtimeSource"] == "embedded"
