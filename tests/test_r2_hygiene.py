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
# R2-060: -WhatIfOnly i alle scripts, og hjaelperne i _Common.psm1 skriver
# ikke i et toerloeb.
# ---------------------------------------------------------------------------
def _provision_scripts():
    return sorted(glob.glob(os.path.join(PROV, "Provision-*.ps1")))


def test_every_provisioning_script_has_a_dry_run():
    for path in _provision_scripts():
        text = open(path, encoding="utf-8-sig").read()
        name = os.path.basename(path)
        assert "[switch] $WhatIfOnly" in text, name
        assert re.search(r"^Connect-MdSite [^\n]*\n\s*Set-MdWhatIf \$WhatIfOnly", text, re.M), name


def test_there_is_one_set_of_list_and_column_helpers():
    for path in glob.glob(os.path.join(PROV, "*.ps1")):
        text = open(path, encoding="utf-8-sig").read()
        assert not re.search(r"^function (New-List|Add-Col)\b", text, re.M), path


def test_common_helpers_respect_the_dry_run():
    common = _read("sharepoint", "provision", "_Common.psm1")
    assert "$script:MdWhatIf = $false" in common
    for fn in ("New-MdList", "New-MdField", "New-MdNoteField", "Rename-MdTitle",
               "Set-MdIndexed", "Set-MdReadOnlyList", "Set-MdOwnItemsList"):
        body = common[common.index("function %s {" % fn):]
        body = body[:body.index("\n}\n")] if "\n}\n" in body else body
        # Toerloebet tjekkes, FOER der kaldes en PnP-cmdlet, der skriver.
        first_write = re.search(r"\b(New|Set|Add|Remove)-PnP\w+", body)
        assert "$script:MdWhatIf" in body, fn
        if first_write:
            assert body.index("$script:MdWhatIf") < first_write.start(), fn


# ---------------------------------------------------------------------------
# R2-024 / R2-032: rettighederne paa admin-, godkender- og loglisten.
# ---------------------------------------------------------------------------
def test_admin_lists_are_provisioned_and_locked():
    ps = _read("sharepoint", "provision", "Provision-AdminLists.ps1")
    assert "New-MdList $ADMINS" in ps and "New-MdField 'UserAndGroups' 'Member' Text -Indexed" in ps
    for lst in ("$ADMINS", "$l", "$LibraryName"):
        assert "Set-MdReadOnlyList %s $FlowAccount" % lst in ps, lst
    assert "Set-MdOwnItemsList $LOG $FlowAccount" in ps
    common = _read("sharepoint", "provision", "_Common.psm1")
    own = common[common.index("function Set-MdOwnItemsList {"):]
    assert "-ReadSecurity 1 -WriteSecurity 2" in own
    ro = common[common.index("function Set-MdReadOnlyList {"):]
    assert "Get-MdRoleName 'Reader'" in ro[:ro.index("\n}\n")]


def _quality_review():
    path, = glob.glob(os.path.join(ROOT, "solution", "BIOSAP", "src", "Workflows",
                                   "BioSap-VhPlan-QualityReview-*.json"))
    return json.load(open(path, encoding="utf-8-sig"))["properties"]["definition"]


def _find(acts, name):
    for n, a in acts.items():
        if n == name:
            return a
        for sub in ([a.get("actions", {})] + [a.get("else", {}).get("actions", {})]):
            if sub:
                hit = _find(sub, name)
                if hit:
                    return hit
    return None


SVC_PARAM = "BioSap-ServiceAccountEmail (orsted_BioSapServiceAccountEmail)"


def _log(stage, author):
    return {"Stage": stage, "Decision": "Approve", "ItemGuid": "g1",
            "Author": {"Email": author}}


@pytest.mark.parametrize("stage, action", [("System", "Filter_sys_ok"), ("Cost", "Filter_cost_ok")])
def test_quality_review_only_trusts_log_rows_written_by_the_service_account(stage, action):
    import wdl_eval
    d = _quality_review()
    assert SVC_PARAM in d["parameters"]
    acts = {"Get_log_all": {"type": "Compose", "inputs": {"body/value": [
        _log(stage, "SVC@example.invalid"), _log(stage, "user1@example.invalid")]}},
        action: _find(d["actions"], action)}
    out = wdl_eval.run(acts, ["Get_log_all", action], {}, {},
                       parameters={SVC_PARAM: "svc@example.invalid"}).outputs
    assert [r["Author"]["Email"] for r in out[action]] == ["SVC@example.invalid"]
    # Ikke sat endnu: tjekket er slaaet fra, som foer.
    out = wdl_eval.run(acts, ["Get_log_all", action], {}, {}, parameters={SVC_PARAM: ""}).outputs
    assert len(out[action]) == 2


def test_service_account_variable_is_defined_without_a_value():
    p = os.path.join(ROOT, "solution", "BIOSAP", "src", "environmentvariabledefinitions",
                     "orsted_BioSapServiceAccountEmail", "environmentvariabledefinition.xml")
    text = open(p, encoding="utf-8").read()
    assert 'schemaname="orsted_BioSapServiceAccountEmail"' in text
    assert "<defaultvalue>" not in text


# ---------------------------------------------------------------------------
# R2-089: doctor fejler, hvor CI fejler.
# ---------------------------------------------------------------------------
def test_doctor_fails_on_uncommitted_yaml(monkeypatch):
    import doctor

    class R:
        def __init__(self, rc=0, out=""):
            self.returncode, self.stdout = rc, out

    def fake_run(cmd, *a, **k):
        if "status" in cmd:
            return R(0, " M BIO SAP App/ScreenX.pa.yaml\n")
        return R(0)

    monkeypatch.setattr(doctor.subprocess, "run", fake_run)
    monkeypatch.setattr(doctor.shutil, "which", lambda n: "/usr/bin/" + n)
    monkeypatch.setattr(doctor, "results", [])
    with io.StringIO() as buf:
        import contextlib
        with contextlib.redirect_stdout(buf):
            doctor.run_build()
        assert "[FEJL]" in buf.getvalue()
    assert doctor.FAIL in doctor.results


def test_doctor_warns_without_dotnet(monkeypatch, capsys):
    import doctor
    monkeypatch.setattr(doctor.shutil, "which", lambda n: None)
    monkeypatch.setattr(doctor, "results", [])
    doctor.check_dotnet()
    assert ".NET 10 / dnx mangler - canvas_mcp.py deploy virker ikke" in capsys.readouterr().out


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
