# -*- coding: utf-8 -*-
"""
Er maskinen klar til at bygge og teste lokalt? Een kommando, ogsaa paa
Windows - CI kan ikke koere i Oersteds repo (hostede runnere er slaaet fra).

    python tools/doctor.py           # tjek forudsaetninger, byg, test
    python tools/doctor.py --fix     # slet desuden gamle filer i de
                                     # udfasede apps' mapper
    python tools/doctor.py --no-build   # kun forudsaetningerne

Den goer det samme som .github/workflows/build.yml: byg alle apps og koer
alle tjek, kraev at det committede .pa.yaml er det builderne laver, og koer
testene. Foer det tjekker den det, der plejer at fejle paa en ny pc:
Python-version, PyYAML/pytest/pyflakes, Node, gamle filer fra foer
udfasningen, PowerShell 7 med PnP.PowerShell (til sharepoint/*.ps1),
dnx/pac (til deploy og solution-eksport) og linjeskift i git.
"""
import argparse
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

OK, WARN, FAIL = "OK  ", "NB  ", "FEJL"
results = []


def report(level, what, fix=""):
    results.append(level)
    print(f"[{level}] {what}")
    if fix:
        for line in fix.splitlines():
            print(f"         {line}")


def check_python():
    v = sys.version_info
    if v < (3, 10):
        report(FAIL, f"Python {v.major}.{v.minor} - kraever 3.10+",
               "Installer Python 3.11 fra python.org (eller: winget install Python.Python.3.11)")
    else:
        report(OK, f"Python {v.major}.{v.minor}.{v.micro} ({sys.executable})")


def check_packages():
    missing = []
    for mod, pkg in (("yaml", "PyYAML"), ("pytest", "pytest"), ("pyflakes", "pyflakes")):
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    if missing:
        report(FAIL, "Mangler Python-pakker: " + ", ".join(missing),
               f'"{sys.executable}" -m pip install -r requirements.txt')
    else:
        report(OK, "PyYAML, pytest og pyflakes er installeret")


def check_node():
    node = shutil.which("node")
    if not node:
        report(WARN, "Node findes ikke - FL-reglerne efterproeves ikke",
               "winget install OpenJS.NodeJS.LTS  (aabn derefter en ny terminal)")
        return
    out = subprocess.run([node, "--version"], capture_output=True, text=True).stdout.strip()
    report(OK, f"Node {out}")


def stale_files():
    import env_config
    out = []
    for folder in env_config.retired_folders():
        d = os.path.join(ROOT, folder)
        if os.path.isdir(d):
            out += [os.path.join(folder, f) for f in sorted(os.listdir(d))
                    if f.endswith(".pa.yaml") and f != "App.pa.yaml"]
    return out


def check_stale(fix):
    stale = stale_files()
    if not stale:
        report(OK, "Ingen gamle filer i de udfasede apps' mapper")
        return
    if fix:
        for rel in stale:
            os.remove(os.path.join(ROOT, rel))
        report(OK, f"Slettede {len(stale)} gammel(le) fil(er) fra foer udfasningen:",
               "\n".join(stale))
    else:
        report(WARN, f"{len(stale)} gammel(le) fil(er) fra foer udfasningen (bruges ikke):",
               "\n".join(stale) + "\nSlet dem med: python tools/doctor.py --fix")


def check_powershell():
    """Kun til sharepoint/*.ps1. PnP.PowerShell 2.x/3.x kraever PowerShell 7
    (pwsh) - i Windows PowerShell 5.1 findes Connect-PnPOnline ikke."""
    pwsh = shutil.which("pwsh")
    if not pwsh:
        level = WARN
        report(level, "PowerShell 7 (pwsh) findes ikke - sharepoint/*.ps1 kan ikke koere",
               "winget install Microsoft.PowerShell\n"
               "Vaelg derefter 'pwsh' som terminal i VS Code (pilen ved +).")
        return
    r = subprocess.run(
        [pwsh, "-NoProfile", "-Command",
         "(Get-Module -ListAvailable PnP.PowerShell | Sort-Object Version -Descending"
         " | Select-Object -First 1).Version.ToString()"],
        capture_output=True, text=True)
    ver = r.stdout.strip()
    if r.returncode != 0 or not ver:
        report(WARN, "PnP.PowerShell er ikke installeret i pwsh - sharepoint/*.ps1 fejler "
                     "med 'Connect-PnPOnline is not recognized'",
               "Koer i pwsh:  Install-Module PnP.PowerShell -Scope CurrentUser")
    else:
        report(OK, f"PowerShell 7 med PnP.PowerShell {ver}")


def check_dnx():
    """dnx (fra .NET 10 SDK) starter MCP-serveren i tools/canvas_mcp.py og
    henter pac i tools/export_solution.ps1, naar pac ikke er installeret.
    Uden nogen af dem kan der hverken deployes eller eksporteres."""
    dnx = shutil.which("dnx")
    pac = shutil.which("pac")
    dotnet = shutil.which("dotnet")
    if dnx or pac:
        report(OK, "dnx/pac: " + ", ".join(n for n, p in (("dnx", dnx), ("pac", pac)) if p)
               + " findes (deploy og solution-eksport)")
    elif dotnet:
        report(WARN, "dnx og pac findes ikke i PATH - canvas_mcp.py bruger 'dotnet dnx', "
                     "men export_solution.ps1 kraever dnx eller pac",
               "Installer .NET 10 SDK (ikke kun runtime), og aabn en ny terminal:\n"
               "https://dotnet.microsoft.com/download/dotnet/10.0")
    else:
        report(WARN, "Hverken dnx, pac eller dotnet findes - canvas_mcp.py (deploy) og "
                     "export_solution.ps1 kan ikke koere",
               "Installer .NET 10 SDK (ikke kun runtime):\n"
               "https://dotnet.microsoft.com/download/dotnet/10.0")


def check_eol():
    """Filer, git har gemt med CRLF, selvom .gitattributes siger LF (R2-027).
    De giver en diff paa hele filen, saa snart nogen gemmer dem igen."""
    git = shutil.which("git")
    if not git:
        return
    r = subprocess.run([git, "ls-files", "--eol"], cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        return
    bad = [l.split("\t", 1)[-1] for l in r.stdout.splitlines()
           if l.startswith("i/crlf") and "eol=lf" in l]
    if bad:
        report(WARN, f"{len(bad)} fil(er) ligger i git med CRLF, men .gitattributes siger LF "
                     f"(fx {bad[0]})",
               "Normaliseres i een commit for sig (R2-027):  git add --renormalize .")
    else:
        report(OK, "Linjeskift i git foelger .gitattributes")


def run_build():
    print("\n=== Byg alle apps og koer alle tjek ===", flush=True)
    if subprocess.run([sys.executable, os.path.join("tools", "build_all.py")], cwd=ROOT).returncode:
        report(FAIL, "Byggeriet fejlede - se fejlene ovenfor")
        return
    report(OK, "Byggeriet er groent")

    git = shutil.which("git")
    if git:
        r = subprocess.run([git, "status", "--porcelain", "--", "*.pa.yaml"],
                           cwd=ROOT, capture_output=True, text=True)
        changed = [l[3:] for l in r.stdout.splitlines() if l.strip()]
        if changed:
            report(WARN, "Builderne aendrede committede .pa.yaml - commit dem med "
                         "din aendring (ellers er de ude af trit med kilden):",
                   "\n".join(changed))
        else:
            report(OK, "Det committede .pa.yaml er det, builderne laver")

    print("\n=== Tests ===", flush=True)
    if subprocess.run([sys.executable, "-m", "pytest", "-q", "tests"], cwd=ROOT).returncode:
        report(FAIL, "Testene fejlede - se fejlene ovenfor")
    else:
        report(OK, "Alle tests bestaar")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--fix", action="store_true",
                    help="slet gamle filer i de udfasede apps' mapper")
    ap.add_argument("--no-build", action="store_true",
                    help="tjek kun forudsaetningerne")
    a = ap.parse_args()

    print("=== Forudsaetninger ===")
    check_python()
    check_packages()
    check_node()
    check_stale(a.fix)
    check_powershell()
    check_dnx()
    check_eol()

    if FAIL in results:
        print("\nRet FEJL ovenfor, og koer igen.")
        return 1
    if not a.no_build:
        run_build()

    print()
    if FAIL in results:
        print("FEJL - se ovenfor.")
        return 1
    print("Klar." + (" (NB-linjerne er ikke fejl, men se dem igennem.)" if WARN in results else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
