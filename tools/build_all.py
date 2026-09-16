# -*- coding: utf-8 -*-
"""
Bygger alle canvas apps i repoet og efterregner layoutet.

    python3 tools/build_all.py

Hver app har sin egen build-mappe med sine egne kopier af de tre faelles
filer (gen_screen.py, build_helpers.py, check_layout.py). Det er med vilje:
Power Apps' egen VS Code-vaerktoejskaede arbejder pr. app-mappe, og et
delt modul udenfor mappen blev fjernet igen af den. Prisen er, at kopierne
kan naa at glide fra hinanden - derfor tjekker dette script, at de er
ordret ens, FOER der bygges. Er de ikke, staar der hvilken fil det er, og
hvilken app der har den nyeste udgave.
"""
import os, shutil, subprocess, sys, filecmp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHARED = ["gen_screen.py", "build_helpers.py", "check_layout.py"]

# (app-mappe, [scripts der skal koeres, i raekkefoelge])
APPS = [
    ("Maintenance Plan App", ["generate_app_onstart.py", "assemble_screen.py"]),
    ("Masterdata Hub",       ["generate_hub_onstart.py", "assemble_hub.py"]),
]


def build_dirs():
    return [(app, os.path.join(ROOT, app, "build")) for app, _ in APPS]


def check_shared():
    """De tre faelles filer skal vaere ordret ens i alle build-mapper."""
    dirs = build_dirs()
    base_app, base_dir = dirs[0]
    bad = []
    for name in SHARED:
        base = os.path.join(base_dir, name)
        if not os.path.exists(base):
            bad.append(f"{name}: mangler i '{base_app}'")
            continue
        for app, d in dirs[1:]:
            other = os.path.join(d, name)
            if not os.path.exists(other):
                bad.append(f"{name}: mangler i '{app}'")
            elif not filecmp.cmp(base, other, shallow=False):
                newer = base_app if os.path.getmtime(base) > os.path.getmtime(other) else app
                bad.append(f"{name}: '{base_app}' og '{app}' er ikke ens "
                           f"(nyest rettet i '{newer}' - kopier derfra)")
    return bad


def drop_pycache():
    """Slet __pycache__ foer der bygges.

    Python vaelger cachet bytekode ud fra filens mtime. Gaar mtime BAGLAENS
    - fx naar en fil gendannes fra en kopi med 'cp' - bliver .pyc'en
    liggende, og builderen koerer paa den GAMLE kode, mens kilden ser
    rigtig ud. Det skete under en test her: sp_config.py var rettet
    tilbage, men den byggede skaerm indeholdt stadig fejlen.

    At slette dem koster under et sekund og fjerner hele klassen af fejl."""
    n = 0
    for d, subs, _ in os.walk(ROOT):
        if ".git" in d:
            continue
        if "__pycache__" in subs:
            shutil.rmtree(os.path.join(d, "__pycache__"), ignore_errors=True)
            subs.remove("__pycache__")
            n += 1
    return n


def main():
    # PowerShell-scripterne hoerer ikke til canvas-byggeriet, men det her er
    # den ene kommando alle koerer - saa tjekket ligger her, hvor det ikke
    # kan glemmes. Se tools/check_ps1.py for hvorfor det er noedvendigt.
    drop_pycache()
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "check_ps1.py")])
    if r.returncode:
        return r.returncode

    bad = check_shared()
    if bad:
        print("De faelles filer er gledet fra hinanden:\n")
        for b in bad:
            print("  " + b)
        print("\nRet i EEN app-mappe og kopier filen til de oevrige.")
        return 1

    rc = 0
    for app, scripts in APPS:
        d = os.path.join(ROOT, app, "build")
        print(f"\n=== {app} ===")
        for s in scripts + ["check_layout.py"]:
            r = subprocess.run([sys.executable, s], cwd=d)
            if r.returncode:
                rc = r.returncode

    # Til sidst, fordi det laeser de .pa.yaml, byggeriet lige har skrevet:
    # findes hver SharePoint-kolonne, formlerne bruger, i virkeligheden?
    print()
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "check_datasources.py")])
    if r.returncode:
        rc = r.returncode
    return rc


if __name__ == "__main__":
    sys.exit(main())
