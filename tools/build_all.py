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
import os, re, shutil, subprocess, sys, filecmp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# EN UDGAVE, IKKE FIRE KOPIER
#
# gen_screen.py, build_helpers.py, check_layout.py, build_domain.py,
# attflows.py og build_flsearch.py laa foer som ordrette kopier i hver
# app's build-mappe - 5.863 af 14.825 linjer Python, 39%. De ligger nu i
# tools/ i EEN udgave, og indgangene saetter tools/ paa sys.path.
#
# Derfor er check_shared() og _compare() vaek: der ER ikke kopier, der kan
# glide fra hinanden. De to domaeneindgange staar stadig hver for sig -
# se "EQUIPMENTS OG MATERIALS MAA AFVIGE" nedenfor for hvorfor.
#
# attflows.py var laenge den sidste undtagelse: VH-plan havde sin EGEN
# udgave, som ikke var ordret ens med tools/attflows.py, saa ingen vagt
# kunne se de to som kopier. Flowkontrakten staar nu eet sted, og VH-plans
# fil er skrumpet til de seks navne og den ene metode, appen faktisk goer
# anderledes.
#
# Begrundelsen for kopierne var, at Power Apps' VS Code-vaerktoejskaede
# fjernede et delt modul udenfor app-mappen igen. Den gaelder ikke den vej,
# der bruges i dag: canvas_mcp.stage() kopierer KUN *.pa.yaml over til
# serveren, saa hverken build/ eller tools/ naar nogensinde derud.

# (app-mappe, [scripts der skal koeres, i raekkefoelge])
APPS = [
    ("Maintenance Plan App", ["generate_app_onstart.py", "assemble_screen.py"]),
    ("Masterdata Hub",       ["generate_hub_onstart.py", "assemble_hub.py"]),
    ("Equipment App",        ["generate_app_onstart.py", "assemble_screen.py"]),
    ("Material App",         ["generate_app_onstart.py", "assemble_screen.py"]),
    ("Functional Location App", ["generate_app_onstart.py", "assemble_screen.py"]),
]

# EQUIPMENTS OG MATERIALS MAA AFVIGE
#
# Her stod DOMAIN_APPS og DOMAIN_SHARED, og check_domain_shared() naegtede
# at bygge, hvis de to apps' indgange ikke var ORDRET ens. Det var rigtigt,
# saa laenge de to kun havde forskellige felter.
#
# Det gaelder ikke laengere: de skal kunne to forskellige ting. Vagten er
# derfor vaek - ikke glemt. Byggeklodserne er stadig faelles og ligger eet
# sted (tools/domain_parts.py); det er KOMPOSITIONEN, der er appens egen.


def build_dirs():
    return [(app, os.path.join(ROOT, app, "build")) for app, _ in APPS]


def check_no_raw_colors():
    """Ingen builder maa skrive en farve. Farver er DESIGNTOKENS.

    Fanger to ting:

      RGBA(...)   en farve skrevet direkte i en kontrol. Den ville ikke
                  skifte med temaet - kontrollen ville blive staaende lys
                  i moerk tilstand.
      #rrggbb     det samme inde i en HTML-streng. Den fejl er vaerre,
                  fordi den ikke ligner en farve for den, der laeser
                  koden: den staar midt i "font-family:Segoe UI".

    Begge har vaeret der. Se tools/design_tokens.py for hvor farven hoerer
    hjemme, og brug ref() eller ref_hex().

    HVORFOR ast OG IKKE ET REGEX OVER LINJERNE
    ------------------------------------------
    Foerste udgave laeste linjer og forsoegte at klippe kommentarer af ved
    et '#'. Den gav to falske fund med det samme - begge var en kommentar,
    der FORKLAREDE, at farven ikke maa staa der. En vagt, der melder om
    sin egen dokumentation, bliver slaaet fra.

    Her laeses kun STRENGKONSTANTER, og docstrings springes over. En
    kommentar findes slet ikke i et syntakstrae, saa den kan ikke tages
    fejl af kode. f-strenge er med: deres faste dele er ogsaa konstanter.
    """
    import ast, glob
    rgba = re.compile(r"RGBA\s*\(")
    hexc = re.compile(r"#[0-9a-fA-F]{6}\b")
    bad = []
    for app, _ in APPS:
        for path in sorted(glob.glob(os.path.join(ROOT, app, "build", "*.py"))):
            rel = os.path.relpath(path, ROOT)
            src = open(path, encoding="utf-8").read()
            try:
                tree = ast.parse(src)
            except SyntaxError as e:
                bad.append(f"{rel}: kan ikke parses ({e})")
                continue
            docs = set()
            for node in ast.walk(tree):
                if isinstance(node, (ast.Module, ast.FunctionDef,
                                     ast.AsyncFunctionDef, ast.ClassDef)):
                    b = node.body
                    if (b and isinstance(b[0], ast.Expr)
                            and isinstance(b[0].value, ast.Constant)
                            and isinstance(b[0].value.value, str)):
                        docs.add(id(b[0].value))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Constant):
                    continue
                if not isinstance(node.value, str) or id(node) in docs:
                    continue
                if rgba.search(node.value):
                    bad.append(f"{rel}:{node.lineno}: RGBA(...) i en builder "
                               f"- brug design_tokens.ref()")
                elif hexc.search(node.value):
                    bad.append(f"{rel}:{node.lineno}: hex-farve i en builder "
                               f"- brug design_tokens.ref_hex()")
    return bad


# check_app_ids() stod her: 60 linjer, der laeste hub_config.py med import
# og tre andre filer med REGEX for at tjekke, at det samme app-id stod de
# samme steder. Den er slettet, fordi id'erne nu kun staar EET sted -
# tools/canvas_apps.json, laest af tools/env_config.py. Den fejlklasse,
# vagten vogtede over, kan ikke opstaa laengere.


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
             "equipment": "Equipment App", "material": "Material App",
             "functionallocation": "Functional Location App"}
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
    ap.add_argument("--env", help="byg mod dette miljoe (se 'environments' i "
                                  "tools/canvas_apps.json)")
    args = ap.parse_args(argv)

    # Miljoeet gives videre til byggescripterne gennem omgivelserne.
    # env_config laeser den samme variabel, saa alle fire apps bygges mod
    # det SAMME miljoe - ogsaa naar de koeres som hver sit subprocess.
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import env_config
    if args.env:
        env_config.resolve(args.env)      # fejler hoejlydt paa et ukendt navn
        os.environ[env_config.ENV_VAR] = args.env
    active = env_config.resolve(args.env)
    print("Miljoe: %s (%s)" % (active["name"], active["environment_id"]))

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

        # Og solution-eksporten: baerer den en hemmelighed?
        #
        # Den stod her ikke foer, og det kostede: en client secret laa
        # committet i tre filer, fordi scrub_solution.py kun blev koert i
        # haanden - og den gang gik den alligevel forbi, fordi den kun saa
        # paa FELTNAVNET. Begge dele er rettet; det her er den anden
        # spaerring. En eksport er sjaelden, og tjekket tager under et
        # sekund paa 118 filer.
        sol = os.path.join(ROOT, "solution")
        if os.path.isdir(sol):
            r = subprocess.run([sys.executable,
                                os.path.join(ROOT, "tools", "scrub_solution.py"),
                                sol, "--report-only"])
            if r.returncode:
                print("\nSolution-eksporten baerer noget hemmeligt. Koer:")
                print("    python3 tools/scrub_solution.py solution")
                print("og ROTER hemmeligheden - en committet noegle kan ikke "
                      "kaldes tilbage.")
                return r.returncode

    # De to tjek nedenfor koerer ALTID, ogsaa maalrettet. De tager
    # millisekunder, og de handler netop om det, en maalrettet bygning
    # ellers ville springe over: at apperne ikke glider fra hinanden.
    bad = check_no_raw_colors()
    if bad:
        print("Der staar farver i builderne:\n")
        for b in bad:
            print("  " + b)
        print("\nFarver hoerer i tools/design_tokens.py. En farve skrevet")
        print("her ville ikke skifte med temaet.")
        return 1

    # FUNCTIONAL LOCATION: REGLERNE SKAL VAERE I TRIT MED HTML'EN
    #
    # Appens regler er foldet ud af html/*.js til fl_rules.generated.json.
    # "test" koerer testmatrixen og differentialtesten mod de ORIGINALE
    # JS-filer og fejler, hvis planen er gaaet ud af trit med dem. Uden
    # Node kan det ikke koeres - saa siges det hoejt, men byggeriet stopper
    # ikke: den genererede plan er committet.
    if any(a == "Functional Location App" for a, _ in apps):
        node = shutil.which("node")
        if node:
            print("\n=== Functional Location: regler mod html/*.js ===")
            r = subprocess.run([node, os.path.join(ROOT, "tools", "fl", "harness.js"), "test"])
            if r.returncode:
                print("  -> reglerne er ikke i trit. Koer: node tools/fl/harness.js plan")
                return r.returncode
        else:
            print("\nNB: node findes ikke - FL-reglerne er IKKE efterproevet mod html/*.js.")

    rc = 0
    for app, scripts in apps:
        d = os.path.join(ROOT, app, "build")
        print(f"\n=== {app} ===")
        # STOPPER VED FOERSTE FEJL I DENNE APP.
        #
        # Foer koerte den videre: fejlede assemble_screen.py, laa den
        # FORRIGE skaerm stadig paa disken, og check_layout.py svarede
        # "Layout-tjek OK" paa den. Beskeden var sand om filen og loegn om
        # byggeriet - og den stod nedenfor fejlen, saa den var det sidste,
        # man saa.
        for s in scripts + ["check_layout.py"]:
            r = subprocess.run([sys.executable, s], cwd=d)
            if r.returncode:
                rc = r.returncode
                print(f"  -> {s} fejlede. Springer resten af '{app}' over, "
                      f"saa tjekkene ikke svarer paa en gammel skaerm.")
                break

    # Landede der en skaerm det forkerte sted?
    #
    # Den her fandtes ikke, og det kostede: da gen_screen.py flyttede fra
    # hver app's build-mappe til tools/, blev dens OUT_DIR ("HERE/..") til
    # REPO-RODEN. Alle fire skaerme blev skrevet dér, app-mapperne beholdt
    # deres gamle udgaver, og layout-tjekket sagde "OK" - fordi det laeste
    # de gamle filer. Groent byggeri, ingen aendring, ingen fejl.
    #
    # gen_screen regner nu OUT_DIR ud af indgangen og siger selv fra. Det
    # her er den anden spaerring, og den er to linjer.
    stray = sorted(f for f in os.listdir(ROOT) if f.endswith(".pa.yaml"))
    if stray:
        print("\nDer ligger skaerme i repo-roden:\n")
        for f in stray:
            print("  " + f)
        print("\nDe hoerer i app-mapperne. Slet dem, og find ud af hvilken")
        print("builder der skrev dem det forkerte sted.")
        return 1

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

    # SPROGTJEKKET LIGGER SIDST, OG PAA ALLE SKAERME
    #
    # Samme grund som datakilde-tjekket: en dansk streng, der glider ind i
    # en faelles builder, rammer alle fire apps. Og den vigtigste halvdel
    # af tjekket er den omvendte - at de seks SharePoint-valgvaerdier
    # (Kladde, Indsendt ...) IKKE bliver oversat. Se tools/check_language.py.
    print()
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "check_language.py")])
    if r.returncode:
        rc = r.returncode

    # EEN kilde pr. hjaelpetekst. De dynamiske hints er Power Fx og bliver i
    # koden; resten er raekker i MD_HelpText. Staar en noegle begge steder,
    # vinder koden - og den, der retter raekken i SharePoint, ser ingen
    # forskel i appen.
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "check_helptext.py")])
    if r.returncode:
        rc = r.returncode
    return rc


if __name__ == "__main__":
    sys.exit(main())
