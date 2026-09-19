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

# Equipment og Materials bygges IKKE herfra. De er haandbyggede i Studio,
# og deres .pa.yaml laeses i solution-eksporten. Her laa engang to
# build-mapper, skrevet ud fra at apperne var tomme - det var de ikke, det
# var eksporten der manglede en publicering. Se docs/23-eq-mat-apps.md.
DOMAIN_APPS = []
DOMAIN_SHARED = []


def build_dirs():
    return [(app, os.path.join(ROOT, app, "build")) for app, _ in APPS]


def _compare(dirs, names, bad):
    base_app, base_dir = dirs[0]
    for name in names:
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


def check_shared():
    """De faelles filer skal vaere ordret ens - de tre i ALLE build-mapper,
    og de fire domaenefiler i de to domaeneapper."""
    bad = []
    _compare(build_dirs(), SHARED, bad)
    if DOMAIN_APPS:
        _compare([(a, os.path.join(ROOT, a, "build")) for a in DOMAIN_APPS],
                 DOMAIN_SHARED, bad)
    return bad


def check_app_ids():
    """Det samme app-id skal staa de samme steder.

    En domaeneapp har sit id TRE steder: tools/canvas_apps.json (hvor der
    deployes til), hub_config.py (hvad flisen aabner) og appens egen
    PLAY_URL (hvad der skrives i MD_RequestIndex.AppUrl, saa "Open" lander
    paa den rigtige indmelding).

    Glider de fra hinanden, fejler ingenting - builderne deployer bare eet
    sted, flisen aabner et andet, og dyblinket et tredje. Det ses foerst,
    naar en bruger klikker "Open" og lander i en tom app.
    """
    import json, re
    bad = []
    cfg_path = os.path.join(ROOT, "tools", "canvas_apps.json")
    hub_path = os.path.join(ROOT, "Masterdata Hub", "build", "hub_config.py")
    if not (os.path.exists(cfg_path) and os.path.exists(hub_path)):
        return bad

    with open(cfg_path, encoding="utf-8") as f:
        apps = json.load(f).get("apps", {})
    sys.path.insert(0, os.path.dirname(hub_path))
    hub = {}
    try:
        import hub_config
        hub = {d["key"]: d.get("app_id") for d in hub_config.DOMAINS}
    except Exception as e:                      # hub_config er ikke vores
        bad.append(f"kan ikke laese hub_config.py: {e}")
        return bad

    # (noeglen i canvas_apps.json, noeglen i hub_config.DOMAINS, app-mappe)
    for key, domain, folder in (("equipment", "Equipment", "Equipment App"),
                                ("material", "Material", "Material App")):
        want = (apps.get(key) or {}).get("app_id")
        if not want:
            continue
        if hub.get(domain) != want:
            bad.append(f"{key}: canvas_apps.json har {want}, men "
                       f"hub_config.py har {hub.get(domain)}")
        dc = os.path.join(ROOT, folder, "build", "domain_config.py")
        if os.path.exists(dc):
            with open(dc, encoding="utf-8") as f:
                m = re.search(r'PLAY_URL\s*=\s*"([^"]*)"', f.read())
            url = m.group(1) if m else ""
            if url and not url.endswith("/" + want):
                bad.append(f"{key}: PLAY_URL i {folder} peger ikke paa {want}")
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

    bad = check_app_ids()
    if bad:
        print("App-id'erne er gledet fra hinanden:\n")
        for b in bad:
            print("  " + b)
        print("\nDe skal vaere det samme tre steder: tools/canvas_apps.json,")
        print("hub_config.py og appens egen PLAY_URL.")
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
