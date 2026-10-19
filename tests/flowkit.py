# -*- coding: utf-8 -*-
"""
Faelles hjaelp til kontrakttests af flow-JSON'en i solution/ (R2-022: repoet
er kilden). Laeser et flow, finder handlinger i scopes/grene/loekker og
koerer et udtryk med tests/wdl_eval.py.
"""
import glob
import json
import os

from conftest import ROOT
import wdl_eval

FLOWS = os.path.join(ROOT, "solution", "BIOSAP", "src", "Workflows")


def path(name):
    p, = glob.glob(os.path.join(FLOWS, name + "-*.json"))
    return p


def flow(name):
    return json.load(open(path(name), encoding="utf-8-sig"))


def definition(name):
    return flow(name)["properties"]["definition"]


def walk(acts):
    """(navn, handling, foraelder-dict) for alle handlinger, ogsaa indlejrede."""
    for n, a in acts.items():
        yield n, a, acts
        if "actions" in a:
            yield from walk(a["actions"])
        if "else" in a:
            yield from walk(a["else"].get("actions", {}))
        for case in a.get("cases", {}).values():
            yield from walk(case.get("actions", {}))
        if "default" in a:
            yield from walk(a["default"].get("actions", {}))


def find(name, action, d=None):
    d = d or definition(name)
    for n, a, _p in walk(d["actions"]):
        if n == action:
            return a
    raise AssertionError("handlingen %s findes ikke i %s" % (action, name))


def siblings(name, action, d=None):
    d = d or definition(name)
    for n, _a, parent in walk(d["actions"]):
        if n == action:
            return parent
    raise AssertionError("handlingen %s findes ikke i %s" % (action, name))


def params(action):
    inputs = action.get("inputs")
    return inputs.get("parameters", {}) if isinstance(inputs, dict) else {}


def evaluate(expr, trigger=None, outputs=None, parameters=None):
    """Koer et "@udtryk" eller en tekst med @{...} med de givne outputs."""
    acts = {k: {"type": "Compose", "inputs": v} for k, v in (outputs or {}).items()}
    acts["__x"] = {"type": "Compose", "inputs": expr}
    return wdl_eval.run(acts, list(acts), trigger or {}, {},
                        parameters=parameters or {}).outputs["__x"]
