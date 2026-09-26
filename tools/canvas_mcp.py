# -*- coding: utf-8 -*-
"""
Kommandolinje-klient til canvas-authoring MCP-serveren.

Samme server som VS Code starter - men uden VS Code, uden agent og uden
credits. Scriptet starter serveren selv, taler MCP (JSON-RPC over stdio)
med den og kalder vaerktoejerne i den rigtige raekkefoelge.

    python tools/canvas_mcp.py deploy --app vhplan
    python tools/canvas_mcp.py pull   --app vhplan
    python tools/canvas_mcp.py tools

FOERST i Power Apps Studio:
  1. Aabn appen i Studio (make.powerapps.com) og lad fanen staa aaben.
  2. Settings -> Updates -> Coauthoring skal vaere slaaet TIL.
Serveren taler med appen gennem netop den coauthoring-session. Lukker du
fanen, holder compile og sync op med at virke.

Kraever .NET 10 SDK (ikke kun runtime):  dotnet --list-sdks

Vaerktoejerne paa serveren (navnene er serverens egne):
  connect            aabner sessionen mod et miljoe + en app. Skal kaldes
                     foerst; alt andet fejler uden.
  compile_canvas     validerer .pa.yaml i en mappe MOD den aabne session -
                     det er her aendringerne naar Studio.
  sync_canvas        skriver sessionens tilstand fra serveren NED i en
                     lokal mappe. Den overskriver filer i mappen, saa
                     scriptet peger den aldrig paa repoets kilder.
  list_controls, describe_control, list_apis, describe_api,
  list_data_sources, get_data_source_schema
  get_appchecker_errors, get_accessibility_errors  (findes ikke i alle
                     serverudgaver - scriptet springer dem over, hvis
                     serveren ikke har dem)
"""
import argparse
import difflib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "tools", "canvas_apps.json")
PROTOCOL_VERSION = "2025-06-18"


# ---------------------------------------------------------------- udskrift

def out(*parts):
    """print(), men uden at vaelte paa en Windows-konsol i cp1252.

    Serverens svar indeholder bl.a. et haeveflueben. Skrives det til en
    konsol med cp1252, giver print() UnicodeEncodeError - og saa taber man
    hele compile-resultatet paa et tegn."""
    s = " ".join(str(p) for p in parts)
    enc = (sys.stdout.encoding or "ascii")
    try:
        s.encode(enc)
    except UnicodeEncodeError:
        s = s.encode(enc, "replace").decode(enc)
    print(s)
    sys.stdout.flush()


class McpError(RuntimeError):
    pass


# ------------------------------------------------------------ MCP-klienten

class McpClient:
    """Minimal MCP-klient over stdio.

    MCP rammer beskeder som EEN JSON pr. linje - ikke LSP's Content-Length.
    Serveren holder sessionen i sin egen proces, saa connect, compile og
    sync skal koere i samme proceslevetid. Derfor et script og ikke tre.
    """

    def __init__(self, command, verbose=False, timeout=900):
        self.command = command
        self.verbose = verbose
        self.timeout = timeout
        self.proc = None
        self._next_id = 0
        self._stderr = []

    # -- proces

    def start(self):
        if self.verbose:
            out("[mcp] starter:", " ".join(self.command))
        try:
            self.proc = subprocess.Popen(
                self.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                cwd=ROOT,
            )
        except FileNotFoundError:
            raise McpError(
                "Kunne ikke starte MCP-serveren med: %s\n"
                "Er .NET 10 SDK installeret? Tjek med:  dotnet --list-sdks\n"
                "Hent den paa https://dotnet.microsoft.com/download/dotnet/10.0"
                % " ".join(self.command))
        t = threading.Thread(target=self._drain_stderr, daemon=True)
        t.start()
        self._handshake()

    def _drain_stderr(self):
        for line in self.proc.stderr:
            line = line.rstrip("\n")
            self._stderr.append(line)
            del self._stderr[:-200]
            if self.verbose:
                out("[server]", line)

    def close(self):
        if not self.proc:
            return
        try:
            self.proc.stdin.close()
        except Exception:
            pass
        try:
            self.proc.wait(timeout=10)
        except Exception:
            self.proc.kill()

    def server_log(self):
        return "\n".join(self._stderr[-40:])

    # -- protokol

    def _send(self, msg):
        if self.verbose:
            out("[->]", json.dumps(msg)[:400])
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()

    def _read_message(self, deadline):
        """Laeser een JSON-besked. Tomme linjer springes over."""
        while True:
            if self.proc.poll() is not None:
                raise McpError("MCP-serveren stoppede.\n" + self.server_log())
            if time.time() > deadline:
                raise McpError("Timeout - serveren svarede ikke i tide.\n"
                               + self.server_log())
            line = self.proc.stdout.readline()
            if line == "":
                raise McpError("MCP-serveren lukkede forbindelsen.\n"
                               + self.server_log())
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except ValueError:
                # Serveren kan finde paa at skrive almindelig tekst ud.
                if self.verbose:
                    out("[server-stdout]", line)
                continue
            if self.verbose:
                out("[<-]", json.dumps(msg)[:400])
            return msg

    def request(self, method, params=None, timeout=None):
        self._next_id += 1
        rid = self._next_id
        self._send({"jsonrpc": "2.0", "id": rid, "method": method,
                    "params": params or {}})
        deadline = time.time() + (timeout or self.timeout)
        while True:
            msg = self._read_message(deadline)
            if msg.get("id") == rid and ("result" in msg or "error" in msg):
                if "error" in msg:
                    raise McpError("%s fejlede: %s"
                                   % (method, json.dumps(msg["error"])))
                return msg["result"]
            if "method" in msg:
                self._handle_server_message(msg)

    def notify(self, method, params=None):
        self._send({"jsonrpc": "2.0", "method": method, "params": params or {}})

    def _handle_server_message(self, msg):
        """Serveren spoerger ogsaa os om ting midt i et kald."""
        method = msg.get("method", "")
        rid = msg.get("id")
        if rid is None:
            if method == "notifications/message" and self.verbose:
                out("[server]", json.dumps(msg.get("params", {}))[:400])
            return
        if method == "ping":
            self._send({"jsonrpc": "2.0", "id": rid, "result": {}})
        elif method == "roots/list":
            self._send({"jsonrpc": "2.0", "id": rid, "result": {"roots": []}})
        elif method == "elicitation/create":
            # Bruges bl.a. af devicecode-login: serveren beder om, at du
            # aabner en URL og taster en kode.
            p = msg.get("params", {})
            out("")
            out("  >> Serveren beder om noget:", p.get("message", ""))
            try:
                input("     Tryk Enter naar du er klar (Ctrl+C afbryder): ")
                res = {"action": "accept", "content": {}}
            except (EOFError, KeyboardInterrupt):
                res = {"action": "cancel"}
            self._send({"jsonrpc": "2.0", "id": rid, "result": res})
        else:
            self._send({"jsonrpc": "2.0", "id": rid,
                        "error": {"code": -32601,
                                  "message": "Klienten kan ikke " + method}})

    def _handshake(self):
        self.request("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"roots": {}, "elicitation": {}},
            "clientInfo": {"name": "canvas_mcp.py", "version": "1.0.0"},
        }, timeout=180)
        self.notify("notifications/initialized")

    # -- vaerktoejer

    def tools(self):
        if getattr(self, "_tools", None) is None:
            self._tools = self.request("tools/list").get("tools", [])
        return self._tools

    def tool(self, name):
        """Serveren har baade bare navne og VS Code-praefiks i omloeb."""
        for t in self.tools():
            n = t.get("name", "")
            if n == name or n.endswith("-" + name) or n.endswith("__" + name):
                return t
        return None

    def has(self, name):
        return self.tool(name) is not None

    def call(self, name, arguments, timeout=None):
        t = self.tool(name)
        if t is None:
            raise McpError("Serveren har ikke vaerktoejet '%s'. Den har: %s"
                           % (name, ", ".join(x.get("name", "?")
                                              for x in self.tools())))
        # Serverudgaverne er ikke enige om parameterlisten - fx kender kun
        # de nyere 'environment_category'. Send kun det, skemaet kender.
        props = (t.get("inputSchema") or {}).get("properties")
        args = dict(arguments)
        if isinstance(props, dict) and props:
            args = {k: v for k, v in args.items() if k in props}
        args = {k: v for k, v in args.items() if v is not None}
        res = self.request("tools/call",
                           {"name": t["name"], "arguments": args},
                           timeout=timeout)
        text = "\n".join(c.get("text", "") for c in res.get("content", [])
                         if c.get("type") == "text").strip()
        if res.get("isError"):
            raise McpError("%s fejlede:\n%s" % (name, text or res))
        return text


# ------------------------------------------------------------ konfiguration

def load_config(env_name=None):
    """Det valgte miljoe, fladt - som resten af filen forventer.

    Selve laesningen ligger i tools/env_config.py, saa builderne og deploy
    ser PRAECIS det samme miljoe. Laa den to steder, kunne man bygge mod
    eet miljoe og deploye til et andet - og det ville ingenting sige."""
    import env_config
    cfg = env_config.resolve(env_name)
    return cfg


def pick_app(cfg, key):
    apps = cfg["apps"]
    if key is None:
        if len(apps) == 1:
            key = list(apps)[0]
        else:
            raise SystemExit("Vaelg en app med --app. Kendte: "
                             + ", ".join(sorted(apps)))
    if key not in apps:
        raise SystemExit("Ukendt app '%s'. Kendte: %s"
                         % (key, ", ".join(sorted(apps))))
    app = dict(apps[key])
    app["key"] = key
    if not app.get("app_id"):
        raise SystemExit(
            "app_id mangler for '%s' i tools/canvas_apps.json.\n"
            "Den staar i Studio-URL'en efter 'app-id=' (sidste led efter /apps/)."
            % key)
    for k in ("environment_id", "environment_category"):
        if not app.get(k):
            app[k] = cfg.get(k)
    if not app.get("environment_id"):
        raise SystemExit("environment_id mangler i tools/canvas_apps.json "
                         "for miljoeet '%s'." % cfg.get("name"))
    return app


def split_command(s):
    """Windows-stier er fulde af backslash - posix-split aeder dem."""
    parts = shlex.split(s, posix=(os.name != "nt"))
    return [p.strip('"') for p in parts]


def resolve_command(cfg, override):
    """Find kommandoen, der starter serveren.

    VS Code starter den med 'dnx' - en genvej, .NET 10 SDK laegger i PATH.
    Findes den ikke som fil, koerer vi den gennem 'dotnet dnx' i stedet."""
    if override:
        return split_command(override)
    env = os.environ.get("CANVAS_MCP_COMMAND")
    if env:
        return split_command(env)
    if cfg.get("mcp_command"):
        return list(cfg["mcp_command"])
    pkg_args = list(cfg.get("mcp_package_args",
                            ["Microsoft.PowerApps.CanvasAuthoring.McpServer",
                             "--yes"]))
    dnx = shutil.which("dnx")
    if dnx:
        return [dnx] + pkg_args
    dotnet = shutil.which("dotnet")
    if dotnet:
        return [dotnet, "dnx"] + pkg_args
    raise SystemExit(
        "Hverken 'dnx' eller 'dotnet' findes i PATH.\n"
        "Installer .NET 10 SDK (ikke kun runtime) fra\n"
        "https://dotnet.microsoft.com/download/dotnet/10.0 og aabn en ny terminal.")


def connect(client, app, login_hint=None, auth_flow=None, tenant_id=None,
            force_account_select=None):
    out("connect: miljoe %s, app %s"
        % (app["environment_id"], app["app_id"]))
    txt = client.call("connect", {
        "environment_id": app["environment_id"],
        "app_id": app["app_id"],
        "environment_category": app.get("environment_category"),
        "login_hint": login_hint or app.get("login_hint"),
        "auth_flow": auth_flow,
        "tenant_id": tenant_id,
        "force_account_select": force_account_select,
    }, timeout=600)
    if txt:
        out(indent(txt))
    return txt


def indent(text, pad="   "):
    return "\n".join(pad + l for l in (text or "").splitlines())


# ------------------------------------------------------------------ filer

def app_dir(app):
    """Mappen med appens byggede .pa.yaml.

    folder = null betyder: der er kilder i repoet, men de er IKKE godkendt
    som sandheden om den app endnu. Deploy sender YAML ind i en LEVENDE
    app og erstatter dens indhold - saa et halvfaerdigt skelet ville
    slette det, nogen har bygget i Studio. Det skal fejle hoejlydt her og
    ikke stille med en TypeError midt i en kopiering.

    'pull' rammer ikke herned: den skriver i .canvas-sync/ og kan derfor
    bruges til at HENTE appen ned, ogsaa mens folder er null. Det er
    netop den vej rundt, man skal, naar man vil se hvad der staar i en app
    man ikke selv har bygget."""
    if not app.get("folder"):
        raise SystemExit(
            "App '%s' har folder = null i tools/canvas_apps.json.\n"
            "Det er med vilje: deploy ville ERSTATTE appens indhold med\n"
            "repoets kilder, og de er ikke godkendt som sandheden om den\n"
            "app endnu.\n\n"
            "Vil du se hvad der faktisk staar i appen, saa hent den ned:\n"
            "    python tools/canvas_mcp.py pull --app %s\n\n"
            "Skal der deployes, saa saet folder - og vid at appens\n"
            "nuvaerende indhold forsvinder." % (app.get("key"), app.get("key")))
    return os.path.join(ROOT, app["folder"])


def yaml_files(d):
    return sorted(f for f in os.listdir(d) if f.endswith(".pa.yaml"))


def stage(app, staging):
    """Kopier appens .pa.yaml til en arbejdsmappe.

    Serveren skriver i den mappe, den faar besked paa (sync_canvas henter
    serverens tilstand NED). Peger man den paa repoet, overskriver den de
    genererede kilder - og saa er byggeriet ikke laengere sandheden.
    Derfor arbejder vi paa en kopi."""
    src = app_dir(app)
    files = yaml_files(src)
    if "App.pa.yaml" not in files:
        raise SystemExit("Fandt ingen App.pa.yaml i %s - er 'folder' rigtig i "
                         "tools/canvas_apps.json?" % src)
    if os.path.isdir(staging):
        shutil.rmtree(staging)
    os.makedirs(staging)
    for f in files:
        shutil.copy2(os.path.join(src, f), os.path.join(staging, f))
    out("kopieret til %s: %s" % (staging, ", ".join(files)))
    return files


def verify_tree(staging, app, files):
    """Er traeet i Studio det, vi byggede? Se tools/deploy_verify.py.

    Returnerer antallet af fund. Normalisering (egenskaber, serveren har
    fjernet) taelles ikke - kun en anden foraelder, en anden raekkefoelge,
    en manglende kontrol eller en egenskab med en ANDEN vaerdi."""
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import deploy_verify as dv
    src = app_dir(app)
    total = 0
    out("")
    out("=== Traeet i Studio mod det byggede ===")
    for f in files:
        if not f.startswith("Screen"):
            continue
        a = os.path.join(src, f)
        b = os.path.join(staging, f)
        if not os.path.exists(b):
            out("   %-28s findes ikke paa serveren" % f)
            total += 1
            continue
        found = dv.compare(a, b)
        total += len(found)
        out("   %-28s %s" % (f, "samme trae" if not found else "%d fund" % len(found)))
        for x in found:
            out("      " + x)
    return total


def _app_without_onstart(src, dst):
    """App.pa.yaml UDEN OnStart - kun til den tomme skaerm.

    OnStart saetter varDomActiveRowId, varDomDetailsId og varDomDocsId til
    Blank(). Deres TYPE kan Power Fx kun udlede af kontrollerne, der bruger
    dem - og paa en tom skaerm er der ingen. Det gav tre compile-fejl. Den
    rigtige App.pa.yaml, med OnStart, sendes lige bagefter."""
    import yaml
    doc = yaml.safe_load(open(src, encoding="utf-8"))
    props = doc["App"]["Properties"]
    # darkModeEnabled SKAL stadig saettes: App.Formulas' C laeser den, og
    # uden OnStart kendte den tomme skaerm den ikke - to compile-fejl
    # (issue #37). Typen er boolsk, og det kan en enkelt Set() fortaelle.
    from design_tokens import DARK_VAR
    props["OnStart"] = "=Set(%s, false)" % DARK_VAR
    lines = ["App:", "  Properties:"]
    for k, v in props.items():
        lines.append("    %s: |-" % k)
        for i, line in enumerate(str(v).split("\n")):
            lines.append("        " + ("=" + line.lstrip("=") if i == 0 else line))
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


def clean_stage(app, staging, files):
    """En udgave af appen, hvor hver skaerm er TOM.

    Studio flytter ikke paalideligt en kontrol fra een foraelder til en
    anden: da listekortet og bjaelkens knapper blev flyttet, havnede de i
    en anden raekkefoelge, og listens raekker mistede deres bredde. Sendes
    den tomme skaerm foerst, fjernes alle kontroller, og den rigtige bygger
    derefter hele traeet paa ny - i den raekkefoelge, der staar i filen."""
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import deploy_verify as dv
    src = app_dir(app)
    if os.path.isdir(staging):
        shutil.rmtree(staging)
    os.makedirs(staging)
    for f in files:
        if f.startswith("Screen"):
            dv.blank_screen(os.path.join(src, f), os.path.join(staging, f))
        elif f == "App.pa.yaml":
            _app_without_onstart(os.path.join(src, f), os.path.join(staging, f))
    out("tom udgave til %s" % staging)


def report_drift(staging, app, files):
    """Hvad aendrede serveren i det, vi sendte?

    Power Apps normaliserer egenskaber, den regner for standardvaerdier,
    vaek. Det er normalt og skal IKKE rettes tilbage i kilderne - men det
    er rart at se, at forskellen er den forventede lille."""
    src = app_dir(app)
    out("")
    out("Serverens udgave mod den byggede (normalisering - ikke fejl):")
    for f in sorted(set(files) | set(yaml_files(staging))):
        a = os.path.join(src, f)
        b = os.path.join(staging, f)
        if not os.path.exists(b):
            out("   %-28s kun lokalt" % f)
            continue
        if not os.path.exists(a):
            out("   %-28s kun paa serveren" % f)
            continue
        la = open(a, encoding="utf-8").read().splitlines()
        lb = open(b, encoding="utf-8").read().splitlines()
        if la == lb:
            out("   %-28s uaendret" % f)
        else:
            d = list(difflib.unified_diff(la, lb, n=0))
            plus = sum(1 for x in d if x.startswith("+") and not x.startswith("+++"))
            minus = sum(1 for x in d if x.startswith("-") and not x.startswith("---"))
            out("   %-28s %d linjer vaek, %d til (%d -> %d linjer)"
                % (f, minus, plus, len(la), len(lb)))
    out("")
    out("   Kopier ALDRIG serverens YAML tilbage over kilderne - de "
        "egenskaber,")
    out("   builderne bevidst saetter, er netop dem normaliseringen fjerner.")


def run_build(app_key=None):
    """Byg FOER serveren startes - fejler layout-tjekket, er der ingen
    grund til at logge ind.

    Kun den app, der skal deployes. Det er ikke tiden, det handler om -
    hele byggeriet tager fire sekunder - men om at de tre andre apps'
    output ikke skal rulle det vaek, man faktisk skulle se. En advarsel i
    VH-plan midt i et Equipment-deploy ligner en, der hoerer til.

    build_all.py koerer stadig sine to sammenhaengstjek (faelles filer og
    app-id'er) og datakilde-tjekket paa ALLE apps - de tager
    millisekunder, og de handler netop om det, en maalrettet bygning
    ellers ville springe over."""
    cmd = [sys.executable, os.path.join(ROOT, "tools", "build_all.py")]
    if app_key:
        cmd += ["--app", app_key]
    out("=== byg (%s) ===" % " ".join(
        ["tools/build_all.py"] + (["--app", app_key] if app_key else [])))
    r = subprocess.run(cmd, cwd=ROOT)
    if r.returncode:
        raise SystemExit("Byggeriet eller layout-tjekket fejlede - stopper her. "
                         "Synk aldrig en app, der ikke er groen.")


def checkers(client):
    """De to tjek findes ikke i alle serverudgaver."""
    for name, label in (("get_appchecker_errors", "App checker"),
                        ("get_accessibility_errors", "Tilgaengelighed")):
        if not client.has(name):
            out("%s: findes ikke i denne serverudgave - sprunget over" % label)
            continue
        out("=== %s ===" % label)
        try:
            txt = client.call(name, {}, timeout=300)
            out(indent(txt) if txt else "   (tomt svar)")
        except McpError as e:
            out(indent(str(e)))


# ------------------------------------------------------------- kommandoer

def cmd_tools(client, args, cfg):
    for t in client.tools():
        req = (t.get("inputSchema") or {}).get("required") or []
        props = list(((t.get("inputSchema") or {}).get("properties") or {}))
        out("- %s" % t.get("name"))
        desc = (t.get("description") or "").strip().splitlines()
        if desc:
            out("     " + desc[0])
        if props:
            out("     parametre: " + ", ".join(
                p + ("*" if p in req else "") for p in props))
    out("")
    out("   * = paakraevet")


def cmd_pull(client, args, cfg):
    app = pick_app(cfg, args.app)
    dest = os.path.abspath(args.out or os.path.join(
        ROOT, ".canvas-sync", app["key"]))
    os.makedirs(dest, exist_ok=True)
    connect(client, app, args.login_hint, args.auth_flow)
    out("=== sync_canvas -> %s ===" % dest)
    out(indent(client.call("sync_canvas", {"directoryPath": dest},
                           timeout=args.timeout)))
    out("")
    out("Hentet fra Studio. Det er serverens tilstand - IKKE repoets kilder.")
    for f in yaml_files(dest):
        n = sum(1 for _ in open(os.path.join(dest, f), encoding="utf-8"))
        out("   %-28s %6d linjer" % (f, n))


def compile_errors(text):
    """Antallet af fejl i compile_canvas' svar.

    Serveren svarer med tekst, ikke med en statuskode, saa den skal
    laeses. To former ses:

        Errors: 2
        ScreenEquipment.pa.yaml(2799,55): error: Unknown property ...

    Begge taelles; den foerste vinder, hvis den findes, fordi den er
    serverens eget tal."""
    if not text:
        return 0
    m = re.search(r"^\s*Errors:\s*(\d+)", text, re.M)
    if m:
        return int(m.group(1))
    return len(re.findall(r"\berror:", text))


def cmd_deploy(client, args, cfg):
    app = pick_app(cfg, args.app)
    staging = os.path.abspath(args.stage or os.path.join(
        ROOT, ".canvas-deploy", app["key"]))
    files = stage(app, staging)

    connect(client, app, args.login_hint, args.auth_flow)

    if args.clean:
        blank = staging + "-tom"
        clean_stage(app, blank, files)
        out("=== compile_canvas: TOM skaerm (--clean) ===")
        txt = client.call("compile_canvas", {"directoryPath": blank},
                          timeout=args.timeout)
        out(indent(txt))
        # IKKE STOP HER.
        #
        # Foerste udgave stoppede, hvis den tomme skaerm gav fejl, og sagde
        # "appen er uaendret". Det passede ikke: Studio tager imod skaermen,
        # OGSAA naar valideringen fejler - skaermen var tom bagefter. At
        # stoppe efterlod altsaa appen uden en skaerm, og det er det
        # vaerste udfald. Den rigtige skaerm sendes derfor altid bagefter;
        # det er DENS compile, der afgoer, om deployet lykkedes.
        n = compile_errors(txt)
        if n:
            out("")
            out("   (den tomme skaerm gav %d fejl - fortsaetter med den rigtige;" % n)
            out("    det er den, der taeller)")

    out("=== compile_canvas (her naar aendringen Studio) ===")
    txt = client.call("compile_canvas", {"directoryPath": staging},
                      timeout=args.timeout)
    out(indent(txt))

    # Compile FOER sync - og stop, hvis compile fejlede.
    #
    # Her blev der synket videre uanset hvad. Et deploy med to fejl saa
    # derfor ud til at lykkes: "Synced 3 file(s)", "No app checker issues
    # found", og til sidst "Faerdig. Tjek appen i Studio". Fejlene stod
    # fire linjer laengere oppe og blev rullet vaek af resten.
    #
    # OBS: en afvist compile er IKKE noedvendigvis uden virkning. Et
    # --clean-deploy viste, at Studio tog imod en tom skaerm, selvom
    # valideringen fejlede. Beskeden nedenfor lover derfor ikke laengere,
    # at appen er uaendret.
    n = compile_errors(txt)
    if n:
        out("")
        out("STOP: compile afviste %d fejl. Der synkes ikke." % n)
        out("Appen i Studio kan vaere DELVIST aendret - Studio tager imod")
        out("skaermen, ogsaa naar valideringen fejler.")
        out("")
        out("Ret fejlen i builderen, ikke i YAML'en:")
        out("    python3 tools/build_all.py")
        out("og koer saa deploy igen.")
        raise SystemExit(1)

    if args.compile_only:
        out("")
        out("--compile-only: stopper foer sync.")
        return

    out("=== sync_canvas (serverens tilstand tilbage) ===")
    out(indent(client.call("sync_canvas", {"directoryPath": staging},
                           timeout=args.timeout)))

    checkers(client)
    report_drift(staging, app, files)
    bad = verify_tree(staging, app, files)
    out("")
    if bad:
        out("FEJL: Studio har IKKE det byggede trae (%d fund ovenfor)." % bad)
        out("Det sker, naar en kontrol er flyttet til en ny foraelder -")
        out("Studio flytter den ikke paalideligt. Byg traeet paa ny:")
        out("")
        out("    python tools\\canvas_mcp.py deploy --app %s --clean" % app["key"])
        out("")
        raise SystemExit(2)
    out("Faerdig. Traeet i Studio er det byggede.")


def cmd_check(client, args, cfg):
    app = pick_app(cfg, args.app)
    connect(client, app, args.login_hint, args.auth_flow)
    checkers(client)


def cmd_raw(client, args, cfg):
    app = pick_app(cfg, args.app) if args.app else None
    if app and args.tool != "connect":
        connect(client, app, args.login_hint, args.auth_flow)
    payload = json.loads(args.args) if args.args else {}
    out(indent(client.call(args.tool, payload, timeout=args.timeout)))


COMMANDS = {
    "tools": cmd_tools,
    "pull": cmd_pull,
    "deploy": cmd_deploy,
    "check": cmd_check,
    "raw": cmd_raw,
}


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="canvas_mcp.py",
        description="Pull, byg og synk canvas apps via canvas-authoring "
                    "MCP-serveren - uden VS Code.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Studio-fanen skal vaere aaben med coauthoring slaaet til.")
    p.add_argument("command", choices=sorted(COMMANDS),
                   help="tools: vis serverens vaerktoejer | pull: hent "
                        "Studios tilstand | deploy: byg, compile og synk | "
                        "check: app checker + tilgaengelighed | raw: kald et "
                        "vaerktoej direkte")
    p.add_argument("--app", help="noeglen i tools/canvas_apps.json")
    p.add_argument("--out", help="pull: mappen der hentes ned i")
    p.add_argument("--stage", help="deploy: arbejdsmappen der sendes fra")
    p.add_argument("--no-build", action="store_true",
                   help="deploy: spring tools/build_all.py over")
    p.add_argument("--clean", action="store_true",
                   help="deploy: send foerst en TOM skaerm, saa hele traeet "
                        "bygges paa ny (brug den, naar en kontrol er flyttet)")
    p.add_argument("--compile-only", action="store_true",
                   help="deploy: stop efter compile")
    p.add_argument("--login-hint", help="e-mail, hvis du skal logge ind som "
                                        "en bestemt bruger")
    p.add_argument("--auth-flow", choices=["broker", "browser", "devicecode"],
                   help="login-maade, hvis standarden driller")
    p.add_argument("--tool", help="raw: vaerktoejets navn")
    p.add_argument("--args", help="raw: argumenter som JSON")
    p.add_argument("--mcp-command", help="hele kommandoen der starter serveren")
    p.add_argument("--timeout", type=int, default=900,
                   help="sekunder pr. kald (standard 900)")
    p.add_argument("-v", "--verbose", action="store_true",
                   help="vis alt, der gaar over stdio")
    args = p.parse_args(argv)

    if args.command == "raw" and not args.tool:
        raise SystemExit("raw kraever --tool NAVN")

    cfg = load_config()

    # Tjek konfigurationen foer der bygges og logges ind - en manglende
    # app_id skal ikke koste et byg og et login foerst.
    if args.command in ("pull", "deploy", "check") or (
            args.command == "raw" and args.app):
        pick_app(cfg, args.app)

    if args.command == "deploy" and not args.no_build:
        run_build(args.app)

    client = McpClient(resolve_command(cfg, args.mcp_command),
                       verbose=args.verbose, timeout=args.timeout)
    out("=== starter MCP-serveren (foerste gang henter den pakken - det "
        "tager lidt) ===")
    try:
        client.start()
        out("forbundet til: %s" % ", ".join(
            t.get("name", "?") for t in client.tools()))
        out("")
        COMMANDS[args.command](client, args, cfg)
    except McpError as e:
        out("")
        out("FEJL: %s" % e)
        return 1
    except KeyboardInterrupt:
        out("\nAfbrudt.")
        return 130
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
