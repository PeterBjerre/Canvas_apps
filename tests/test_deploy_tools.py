# -*- coding: utf-8 -*-
"""
Deploy-vaerktoejerne: det, der afgoer om der synkes, og om et deploy
lykkedes (R2-062, R2-064, R2-065, R2-068, R2-092).

Studio kan ikke naas herfra, saa cmd_deploy koeres mod en FALSK klient,
der holder "serverens" filer i en dict: compile_canvas laegger mappens
filer paa serveren, sync_canvas skriver dem ned igen.

    python3 -m pytest -q tests/test_deploy_tools.py
"""
import argparse
import os
import subprocess
import textwrap

import pytest

import canvas_mcp
import deploy_verify as dv
import env_config


# ------------------------------------------------------------ compile_errors

@pytest.mark.parametrize("text, n", [
    ("Errors: 2\nScreenX.pa.yaml(1,1): error: a\nScreenX.pa.yaml(2,1): error: b", 2),
    ("ScreenX.pa.yaml(1,1): error: Unknown property 'Foo'", 1),
    ("No errors", 0),
    ("", 0),
])
def test_compile_errors(text, n):
    assert canvas_mcp.compile_errors(text) == n


# ------------------------------------------------------------ deploy_verify

SCREEN = textwrap.dedent("""\
    Screens:
      ScreenT:
        Children:
          - conA:
              Control: GroupContainer@1.3.0
              Properties:
                Width: =100
                Fill: =RGBA(0, 0, 0, 1)
              Children:
                - lblA:
                    Control: Label@2.5.1
                    Properties:
                      Text: ="A"
                - lblB:
                    Control: Label@2.5.1
                    Properties:
                      Text: ="B"
          - conB:
              Control: GroupContainer@1.3.0
              Properties:
                Width: =50
    """)


def _pair(tmp_path, server_text):
    a, b = tmp_path / "built.pa.yaml", tmp_path / "server.pa.yaml"
    a.write_text(SCREEN, encoding="utf-8")
    b.write_text(server_text, encoding="utf-8")
    return str(a), str(b)


def test_compare_same_tree(tmp_path):
    assert dv.compare(*_pair(tmp_path, SCREEN)) == []


def test_compare_swapped_order(tmp_path):
    swapped = SCREEN.replace("lblA", "TMP").replace("lblB", "lblA").replace("TMP", "lblB")
    swapped = swapped.replace('="A"', "X").replace('="B"', '="A"').replace("X", '="B"')
    found = dv.compare(*_pair(tmp_path, swapped))
    assert len(found) == 1 and "raekkefoelge" in found[0]


def test_compare_other_parent(tmp_path):
    moved = SCREEN.replace("""                - lblB:
                    Control: Label@2.5.1
                    Properties:
                      Text: ="B"
""", "") + """          Children:
            - lblB:
                Control: Label@2.5.1
                Properties:
                  Text: ="B"
"""
    found = dv.compare(*_pair(tmp_path, moved))
    assert any("lblB: foraelder conB" in x for x in found), found


def test_compare_other_value(tmp_path):
    found = dv.compare(*_pair(tmp_path, SCREEN.replace("Width: =100", "Width: =120")))
    assert len(found) == 1 and "conA.Width" in found[0]


def test_compare_removed_property_is_normalisation(tmp_path):
    pair = _pair(tmp_path, SCREEN.replace("            Fill: =RGBA(0, 0, 0, 1)\n", ""))
    assert dv.compare(*pair) == []
    # ... men mellem to serverudgaver (drift-kontrollen) er det en aendring.
    found = dv.compare(*pair, strict=True)
    assert found == ["conA.Fill: fjernet"]


APP = textwrap.dedent("""\
    App:
      Properties:
        OnError: =Notify(FirstError.Message)
        OnStart: =Set(varX, 1)
    """)


def test_compare_app(tmp_path):
    a, b = tmp_path / "a" / "App.pa.yaml", tmp_path / "b" / "App.pa.yaml"
    a.parent.mkdir()
    b.parent.mkdir()
    a.write_text(APP, encoding="utf-8")
    b.write_text(APP, encoding="utf-8")
    assert dv.compare_app(str(a), str(b)) == []
    b.write_text(APP.replace("Notify(FirstError.Message)", "Notify(\"x\")"), encoding="utf-8")
    found = dv.compare_app(str(a), str(b))
    assert len(found) == 1 and found[0].startswith("App.OnError")


# --------------------------------------------------------- cmd_deploy (falsk)

class FakeClient:
    def __init__(self, server):
        self.server = dict(server)       # filnavn -> indhold
        self.calls = []
        self.compile_reply = None        # None = tag imod, uden fejl

    def has(self, name):
        return False

    def call(self, name, args, timeout=None):
        self.calls.append(name)
        if name == "connect":
            return "Connected."
        d = args.get("directoryPath")
        if name == "sync_canvas":
            os.makedirs(d, exist_ok=True)
            for f, text in self.server.items():
                with open(os.path.join(d, f), "w", encoding="utf-8") as fh:
                    fh.write(text)
            return "Synced %d file(s)" % len(self.server)
        if name == "compile_canvas":
            # Studio tager imod skaermen, OGSAA naar valideringen fejler.
            for f in os.listdir(d):
                if f.endswith(".pa.yaml"):
                    self.server[f] = open(os.path.join(d, f), encoding="utf-8").read()
            return self.compile_reply or "Errors: 0"
        raise AssertionError(name)


@pytest.fixture
def repo(tmp_path, monkeypatch):
    app = tmp_path / "app"
    app.mkdir()
    (app / "App.pa.yaml").write_text(APP, encoding="utf-8")
    (app / "ScreenT.pa.yaml").write_text(SCREEN, encoding="utf-8")
    monkeypatch.setattr(canvas_mcp, "ROOT", str(tmp_path))
    return tmp_path


CFG = {"name": "test", "apps": {"biosap": {"folder": "app", "app_id": "a",
                                           "environment_id": "e"}}}


def _args(**kw):
    a = dict(app="biosap", stage=None, login_hint=None, auth_flow=None, clean=False,
             compile_only=False, timeout=5, overwrite_studio=False)
    a.update(kw)
    return argparse.Namespace(**a)


def _server(repo):
    return {f: open(os.path.join(repo, "app", f), encoding="utf-8").read()
            for f in ("App.pa.yaml", "ScreenT.pa.yaml")}


def _snaps(repo):
    base = os.path.join(repo, ".canvas-sync", "biosap")
    return sorted(os.listdir(base)) if os.path.isdir(base) else []


def test_deploy_takes_snapshot_before_compile(repo, capsys):
    c = FakeClient(_server(repo))
    canvas_mcp.cmd_deploy(c, _args(compile_only=True), CFG)
    assert c.calls[:3] == ["connect", "sync_canvas", "compile_canvas"]
    snaps = _snaps(repo)
    assert len(snaps) == 1
    assert os.path.exists(os.path.join(repo, ".canvas-sync", "biosap", snaps[0],
                                       "ScreenT.pa.yaml"))
    out = capsys.readouterr().out
    assert "Aftryk foer deploy" in out and "ingen baseline" in out
    # compile-only synker ikke tilbage, saa der gemmes ingen baseline.
    assert not os.path.isdir(os.path.join(repo, ".canvas-deploy", "biosap-sidst"))


def test_second_deploy_sees_unchanged_studio(repo, capsys):
    c = FakeClient(_server(repo))
    canvas_mcp.cmd_deploy(c, _args(), CFG)
    assert os.path.isdir(os.path.join(repo, ".canvas-deploy", "biosap-sidst"))
    capsys.readouterr()
    canvas_mcp.cmd_deploy(c, _args(), CFG)
    out = capsys.readouterr().out
    assert "Studio uaendret siden sidste deploy" in out
    assert "Faerdig" in out and "commit" in out


def test_deploy_stops_when_studio_changed(repo, capsys):
    c = FakeClient(_server(repo))
    canvas_mcp.cmd_deploy(c, _args(), CFG)
    # En kollega retter en tekst i Studio.
    c.server["ScreenT.pa.yaml"] = c.server["ScreenT.pa.yaml"].replace('="B"', '="Bee"')
    capsys.readouterr()
    with pytest.raises(SystemExit) as e:
        canvas_mcp.cmd_deploy(c, _args(), CFG)
    assert e.value.code == 3
    out = capsys.readouterr().out
    assert "lblB.Text" in out and "--overwrite-studio" in out
    assert "Bee" in c.server["ScreenT.pa.yaml"], "intet maa vaere sendt"
    # --overwrite-studio deployer alligevel.
    canvas_mcp.cmd_deploy(c, _args(overwrite_studio=True), CFG)
    assert "Bee" not in c.server["ScreenT.pa.yaml"]


def test_failed_compile_prints_restore_hint_and_drops_baseline(repo, capsys):
    c = FakeClient(_server(repo))
    canvas_mcp.cmd_deploy(c, _args(), CFG)
    c.compile_reply = "Errors: 1\nScreenT.pa.yaml(1,1): error: x"
    with pytest.raises(SystemExit) as e:
        canvas_mcp.cmd_deploy(c, _args(), CFG)
    assert e.value.code == 1
    out = capsys.readouterr().out
    assert "Gendan:" in out and "Versions" in out
    # Studio kan vaere delvist aendret: naeste deploy maa ikke kalde vores
    # egen halve aendring for en Studio-aendring.
    assert not os.path.isdir(os.path.join(repo, ".canvas-deploy", "biosap-sidst"))


def test_snapshots_are_pruned(repo):
    base = os.path.join(repo, ".canvas-sync", "biosap")
    for i in range(6):
        os.makedirs(os.path.join(base, "20200101-00000%d" % i))
    os.makedirs(os.path.join(base, "andet"))   # pull's egne filer roeres ikke
    canvas_mcp.cmd_deploy(FakeClient(_server(repo)), _args(compile_only=True), CFG)
    snaps = [d for d in _snaps(repo) if d != "andet"]
    assert len(snaps) == canvas_mcp.KEEP_SNAPSHOTS
    assert "20200101-000000" not in snaps
    assert os.path.isdir(os.path.join(base, "andet"))


# ------------------------------------------------------- --no-build (R2-064)

def _git(repo, *a):
    subprocess.run(["git", *a], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def git_repo(repo):
    _git(repo, "init", "-q")
    _git(repo, "-c", "user.email=t@example.invalid", "-c", "user.name=t", "add", "-A")
    _git(repo, "-c", "user.email=t@example.invalid", "-c", "user.name=t",
         "commit", "-q", "-m", "x")
    return repo


def test_no_build_accepts_committed_yaml(git_repo):
    canvas_mcp.check_committed_yaml({"folder": "app"})


def test_no_build_refuses_edited_yaml(git_repo):
    p = git_repo / "app" / "ScreenT.pa.yaml"
    p.write_text(SCREEN.replace("=100", "=101"), encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        canvas_mcp.check_committed_yaml({"folder": "app"})
    assert "ucommittede" in str(e.value) and "--allow-dirty" in str(e.value)


# ----------------------------------------------------- miljoeer (R2-061)

def test_template_environments_cannot_be_selected():
    envs = env_config._CFG["environments"]
    assert env_config._CFG["default_environment"] == "dev"
    assert env_config.placeholders(envs["dev"]) == []
    for name in ("test", "prod"):
        assert env_config.placeholders(envs[name]), name
        assert not any(envs[name]["features"].values()), name
        with pytest.raises(SystemExit, match="skabelon"):
            env_config.resolve(name)
