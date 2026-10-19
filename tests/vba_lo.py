# -*- coding: utf-8 -*-
"""
Koerer rene VBA-moduler i LibreOffice Basic (Option VBASupport 1).

    from vba_lo import VbaRunner
    with VbaRunner(["excel/opretter/VhpUtil.bas", ...]) as vba:
        vba.call("VhpUtil", "Dk", "V{ae}lg")

HVORFOR
-------
Opretteren er VBA og kan kun kompileres i Excel paa Windows. Det, der ikke
roerer SAP, ark eller filer - oversaettelserne i VhpMap, langteksten i
VhpItf, hjaelperne i VhpUtil - kan derimod koere her. LibreOffice Basic
med VBASupport har de samme strengfunktioner, Collection, DateAdd og
Format$, saa en fejl i en regel viser sig i testen og ikke foerst i SAP.

Kraever LibreOffice (soffice) og Python-UNO (python3-uno). Mangler de,
springer testene over (pytest.skip) - de er en ekstra sikkerhed, ikke en
forudsaetning for byggeriet. Med VBA_LO_REQUIRED=1 (CI-jobbet "vba-lo" i
.github/workflows/build.yml) fejler de i stedet, saa et manglende
LibreOffice ikke gemmer sig som et "s" i loggen.

EGEN FORBINDELSE PR. KOERSEL (R2-066)
------------------------------------
Hver VbaRunner starter soffice paa et navngivet ROER med et unikt navn
(uuid4) - ikke en fast port. Med port 2099 talte en anden samtidig
pytest-koersel med den foerstes soffice og fejlede, naar den lukkede.
Stopper vores soffice, mens vi venter paa forbindelsen, siges det straks.
"""
import os
import re
import shutil
import subprocess
import tempfile
import time
import uuid

LIB = "VhpTestLib"


def required():
    """Skal LibreOffice-testene koere (ikke springes over)?"""
    return os.environ.get("VBA_LO_REQUIRED") == "1"


def available():
    if not shutil.which("soffice"):
        return False
    try:
        import uno  # noqa: F401
    except ImportError:
        return False
    return True


def _basic_source(path):
    """En .bas-fil som LibreOffice-modul: (navn, kildekode).

    Navnet er VB_Name - det, VBA-koden kalder modulet ved (VhpUtil.Dk).
    Attribute-linjerne fjernes, og VBASupport slaas til."""
    with open(path, encoding="utf-8") as f:
        lines = f.read().replace("\r\n", "\n").split("\n")
    name = os.path.splitext(os.path.basename(path))[0]
    for l in lines:
        if l.startswith('Attribute VB_Name = "'):
            name = l.split('"')[1]
    body = [l for l in lines if not l.startswith("Attribute VB_")]
    return name, "Option VBASupport 1\n" + "\n".join(body)


# LibreOffice Basic kan ikke regne konstantudtryk ud (Const A = B & "x",
# Const E = vbObjectError + 1). VBA kan. Til syntakstjekket erstattes
# udtrykket af en tom vaerdi af samme type - det er ikke dem, der tjekkes.
_CONST = re.compile(r'^(\s*(?:Public\s+|Private\s+)?Const\s+\w+\s+As\s+(\w+)\s*=\s*)(.+)$', re.I)
_SIMPLE = re.compile(r'^(?:"(?:[^"]|"")*"|-?\d+(?:\.\d+)?#?|&H[0-9A-F]+&?|vb\w+|True|False)\s*(?:\'.*)?$', re.I)


def _syntax_source(code):
    out = []
    for line in code.split("\n"):
        m = _CONST.match(line)
        if m and not _SIMPLE.match(m.group(3).strip()):
            filler = '""' if m.group(2).lower() == "string" else "0"
            line = m.group(1) + filler
        out.append(line)
    return "\n".join(out)


class VbaRunner:
    def __init__(self, modules, pipe=None):
        self.modules = modules
        # Unikt roernavn: to samtidige koersler deler aldrig forbindelse.
        self.pipe = pipe or "vhp_lo_" + uuid.uuid4().hex
        self.proc = None
        self.profile = None

    def __enter__(self):
        import uno
        self.profile = tempfile.mkdtemp(prefix="vhp_lo_")
        self.proc = subprocess.Popen(
            ["soffice", "--headless", "--invisible", "--nologo", "--norestore",
             f"--accept=pipe,name={self.pipe};urp;",
             f"-env:UserInstallation=file://{self.profile}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        local = uno.getComponentContext()
        resolver = local.ServiceManager.createInstanceWithContext(
            "com.sun.star.bridge.UnoUrlResolver", local)
        ctx = None
        for _ in range(240):
            if self.proc.poll() is not None:
                shutil.rmtree(self.profile, ignore_errors=True)
                raise RuntimeError("soffice stoppede (exit %s), foer der var forbindelse"
                                   % self.proc.returncode)
            try:
                ctx = resolver.resolve(
                    f"uno:pipe,name={self.pipe};urp;StarOffice.ComponentContext")
                break
            except Exception:
                time.sleep(0.25)
        if ctx is None:
            self.proc.kill()
            shutil.rmtree(self.profile, ignore_errors=True)
            raise RuntimeError("LibreOffice startede ikke")
        self.ctx = ctx
        smgr = ctx.ServiceManager
        libs = smgr.createInstanceWithContext(
            "com.sun.star.script.ApplicationScriptLibraryContainer", ctx)
        if not libs.hasByName(LIB):
            libs.createLibrary(LIB)
        libs.loadLibrary(LIB)
        lib = libs.getByName(LIB)
        for path in self.modules:
            name, code = _basic_source(path)
            if lib.hasByName(name):
                lib.removeByName(name)
            lib.insertByName(name, code)
        factory = smgr.createInstanceWithContext(
            "com.sun.star.script.provider.MasterScriptProviderFactory", ctx)
        self.provider = factory.createScriptProvider("")
        return self

    def syntax_ok(self, path):
        """Kan LibreOffice oversaette modulet? Modulet laegges i sit eget
        bibliotek med en proevefunktion: fejler oversaettelsen, svarer den
        tomt i stedet for "ok". (Et bibliotek oversaettes samlet, saa eet
        modul med en fejl ville ellers vaelte de andres proever.)"""
        name, code = _basic_source(path)
        lib_name = "VhpSyn" + name
        smgr = self.ctx.ServiceManager
        libs = smgr.createInstanceWithContext(
            "com.sun.star.script.ApplicationScriptLibraryContainer", self.ctx)
        if not libs.hasByName(lib_name):
            libs.createLibrary(lib_name)
        libs.loadLibrary(lib_name)
        lib = libs.getByName(lib_name)
        if lib.hasByName(name):
            lib.removeByName(name)
        probe = '\nPublic Function ZzSyntaxProbe() As String\n    ZzSyntaxProbe = "ok"\nEnd Function\n'
        lib.insertByName(name, _syntax_source(code) + probe)
        uri = (f"vnd.sun.star.script:{lib_name}.{name}.ZzSyntaxProbe"
               "?language=Basic&location=application")
        result = self.provider.getScript(uri).invoke((), (), ())[0]
        return result == "ok"

    def call(self, module, func, *args):
        uri = (f"vnd.sun.star.script:{LIB}.{module}.{func}"
               "?language=Basic&location=application")
        script = self.provider.getScript(uri)
        result = script.invoke(tuple(args), (), ())
        return result[0]

    def __exit__(self, *exc):
        try:
            desktop = self.ctx.ServiceManager.createInstanceWithContext(
                "com.sun.star.frame.Desktop", self.ctx)
            desktop.terminate()
        except Exception:
            pass
        try:
            self.proc.wait(timeout=30)
        except Exception:
            self.proc.kill()
        shutil.rmtree(self.profile, ignore_errors=True)
        return False
