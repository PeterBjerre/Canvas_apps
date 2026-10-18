# -*- coding: utf-8 -*-
"""
Sikkerhed, rettigheder og repo-hygiejne (review 2026-10: R2-024, R2-025,
R2-026, R2-032, R2-060, R2-089, R2-090, R2-091).

Hver test planter fejlen eller laeser den kilde, der skal holde den ude.

    python3 -m pytest -q tests/test_r2_hygiene.py
"""
import glob
import io
import json
import os
import re
import zipfile

import pytest
import yaml

from conftest import ROOT

PROV = os.path.join(ROOT, "sharepoint", "provision")


def _read(*parts):
    return open(os.path.join(ROOT, *parts), encoding="utf-8-sig").read()


# ---------------------------------------------------------------------------
# R2-090: een koersel pr. PR-push, og et nyt push annullerer det gamle.
# ---------------------------------------------------------------------------
def test_build_workflow_runs_once_per_push():
    wf = yaml.safe_load(_read(".github", "workflows", "build.yml"))
    on = wf.get("on", wf.get(True))
    assert on["push"] == {"branches": ["main"]}
    assert "pull_request" in on
    assert wf["concurrency"]["cancel-in-progress"] is True
    assert "github.ref" in wf["concurrency"]["group"]
    assert list(wf["jobs"]) == ["build"]


# ---------------------------------------------------------------------------
# R2-091: unpack_msapp skriver aldrig uden for <navn>.src.
# ---------------------------------------------------------------------------
def test_unpack_msapp_rejects_paths_outside_the_folder(tmp_path):
    import unpack_msapp
    msapp = tmp_path / "evil.msapp"
    with zipfile.ZipFile(msapp, "w") as z:
        z.writestr("Src/App.pa.yaml", "App: {}\n")
        z.writestr("Src/../../evil.pa.yaml", "x: 1\n")
    with pytest.raises(SystemExit):
        unpack_msapp.unpack_one(str(msapp), [])
    assert not (tmp_path / "evil.pa.yaml").exists()
    assert not (tmp_path.parent / "evil.pa.yaml").exists()


def test_unpack_msapp_wanted_refuses_dotdot_and_absolute():
    import unpack_msapp
    assert not unpack_msapp.wanted("src/../../x.pa.yaml")
    assert not unpack_msapp.wanted("/src/x.pa.yaml")
    assert unpack_msapp.wanted("Src/Screen1.pa.yaml")
