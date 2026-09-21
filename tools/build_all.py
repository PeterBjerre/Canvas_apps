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
import argparse
import os, shutil, subprocess, sys, filecmp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHARED = ["gen_screen.py", "build_helpers.py", "check_layout.py"]

# (app-mappe, [scripts der skal koeres, i raekkefoelge])
APPS = [
    ("Maintenance Plan App", ["generate_app_onstart.py", "assemble_screen.py"]),
    ("Masterdata Hub",       ["generate_hub_onstart.py", "assemble_hub.py"]),
    ("Equipment App",        ["generate_app_onstart.py", "assemble_screen.py"]),
    ("Material App",         ["generate_app_onstart.py", "assemble_screen.py"]),
]

# Equipment og Materials er DEN SAMME app. Kun domain_config.py skiller
# dem - felterne og listenavnet. Resten skal derfor ogsaa vaere ordret
# ens, og bliver det kun, hvis nogen tjekker det.
DOMAIN_APPS = ["Equipment App", "Material App"]
DOMAIN_SHARED = ["build_domain.py", "attflows.py",
                 "generate_app_onstart.py", "assemble_screen.py"]


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

    # Hubbens eget id staar i canvas_apps.json OG i de to domaeneapps'
    # HUB_URL - knappen "Tilbage til hubben". Glider de fra hinanden,
    # aabner knappen en anden app end den, flisen kom fra.
    hub_id = (apps.get("hub") or {}).get("app_id")

    # (noeglen i canvas_apps.json, noeglen i hub_config.DOMAINS, app-mappe)
    # VH-plan har ogsaa en knap til hubben - dens HUB_URL staar i
    # sp_config.py og skal foelge det samme id.
    vp = os.path.join(ROOT, "Maintenance Plan App", "build", "sp_config.py")
    if hub_id and os.path.exists(vp):
        with open(vp, encoding="utf-8") as f:
            m = re.search(r'HUB_URL\s*=\s*\(?\s*"([^"]*)"[^)]*\)?', f.read(), re.S)
        if m:
            with open(vp, encoding="utf-8") as f:
                joined = "".join(re.findall(r'"([^"]*)"',
                                            re.search(r"HUB_URL\s*=\s*\((.*?)\)",
                                                      f.read(), re.S).group(1)))
            if not joined.endswith("/" + hub_id):
                bad.append("vhplan: HUB_URL i sp_config.py peger ikke paa "
                           f"hubbens app_id {hub_id}")

    for key, domain, folder in (("equipment", "Equipment", "Equipment App"),
                                ("material", "Material", "Material App")):
        dc_path = os.path.join(ROOT, folder, "build", "domain_config.py")
        if hub_id and os.path.exists(dc_path):
            with open(dc_path, encoding="utf-8") as f:
                m = re.search(r'HUB_URL\s*=\s*\(?\s*"([^"]*)"', f.read())
            if m and not m.group(1).endswith("/" + hub_id):
                bad.append(f"{key}: HUB_URL i {folder} peger ikke paa "
                           f"hubbens app_id {hub_id}")
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


def pick_apps(which):
    """Hvilke apps der skal bygges.

    Uden argument: alle. Med: den ene, valgt paa mappenavn eller paa
    noeglen i tools/canvas_apps.json (equipment, material, vhplan, hub).

    Hvorfor overhovedet kunne vaelge? Ikke for tidens skyld - hele
    byggeriet tager fire sekunder. Men naar deploy bygger alle fire, ruller
    de tre andre apps' output det vaek, man faktisk skulle se, og en
    advarsel i VH-plan dukker op midt i et Equipment-deploy som om den
    hoerte til."""
    if not which:
        return APPS
    alias = {"vhplan": "Maintenance Plan App", "hub": "Masterdata Hub",
             "equipment": "Equipment App", "material": "Material App"}
    want = alias.get(which.lower(), which)
    hit = [(a, s) for a, s in APPS if a.lower() == want.lower()]
    if not hit:
        raise SystemExit(
            "Kender ikke app '%s'. Vaelg en af:\n  %s\neller en noegle:\n  %s"
            % (which, "\n  ".join(a for a, _ in APPS),
               ", ".join(sorted(alias))))
    return hit


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Bygger canvas apps og efterregner layoutet.")
    ap.add_argument("--app", help="byg kun denne app (mappenavn eller noegle)")
    args = ap.parse_args(argv)
    apps = pick_apps(args.app)

    drop_pycache()

    # PowerShell-scripterne hoerer ikke til canvas-byggeriet, men det her er
    # den ene kommando alle koerer - saa tjekket ligger her, hvor det ikke
    # kan glemmes. Se tools/check_ps1.py for hvorfor det er noedvendigt.
    #
    # Ved en maalrettet bygning springes det over: det har intet med den
    # app at goere, og et deploy skal ikke stoppe paa en kommentar i et
    # PowerShell-script.
    if not args.app:
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "check_ps1.py")])
        if r.returncode:
            return r.returncode

    # De to tjek nedenfor koerer ALTID, ogsaa maalrettet. De tager
    # millisekunder, og de handler netop om det, en maalrettet bygning
    # ellers ville springe over: at apperne ikke glider fra hinanden.
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
    for app, scripts in apps:
        d = os.path.join(ROOT, app, "build")
        print(f"\n=== {app} ===")
        for s in scripts + ["check_layout.py"]:
            r = subprocess.run([sys.executable, s], cwd=d)
            if r.returncode:
                rc = r.returncode

    # Til sidst, fordi det laeser de .pa.yaml, byggeriet lige har skrevet:
    # findes hver SharePoint-kolonne, formlerne bruger, i virkeligheden?
    #
    # Den laeser ALLE skaerme, ogsaa ved en maalrettet bygning. De oevrige
    # ligger paa disken i forvejen, og et kolonnenavn, der aendrer sig eet
    # sted, kan braekke en anden app - det er billigere at opdage her end
    # ved dens naeste deploy.
    print()
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "check_datasources.py")])
    if r.returncode:
        rc = r.returncode
    return rc


if __name__ == "__main__":
    sys.exit(main())
