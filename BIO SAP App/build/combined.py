# -*- coding: utf-8 -*-
"""
DEN SAMLEDE APP - de fem apps som skaerme i een app.

HVORFOR
-------
Med sidebaren blev skift mellem domaener det vigtigste navigations-
moenster. I de fem enkelte apps er hvert klik Launch() af en anden app:
en kold start paa 3-8 sekunder, og det, man var i gang med, er vaek.
Her er hvert domaene en skaerm, og et klik er Navigate().

DE FEM APPS ER URORTE
---------------------
Den samlede app har ingen egne skaermbyggere. Den genbruger de fem appers
- deres sektioner, deres App.Formulas og deres OnStart - og aendrer kun
det, der SKAL vaere anderledes i een app:

  navigation     Launch() -> Navigate() (side_nav.SCREENS, build_hub.*_ACTION)
  navne          Equipments og Materials deler 177 kontrolnavne og alle
                 variabler (varDom*, colDom*), fordi de er bygget af de
                 samme dele. Her faar de hver sit praefiks: Eq og Mat.
  opstart        hvert domaenes OnStart flyttes til dets skaerms OnVisible
                 og koeres FOERST, naar skaermen aabnes. App.OnStart har
                 kun temaet og hubbens fire variabler.
  indlaesning    en ventespinner, mens et domaene klargoeres (loading_overlay
                 i build_screens.py), og skaermens egen LoadingSpinner.

Stopper en af de fem apps med at se ud, som denne fil forventer, stopper
byggeriet med en besked - den glider ikke tavst fra dem.

Se README.md i app-mappen for, hvordan appen oprettes og testes.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(HERE)
ROOT = os.path.dirname(APP_DIR)
TOOLS = os.path.join(ROOT, "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import design_tokens as tok

# Noeglen i tools/canvas_apps.json.
APP_KEY = "biosap"

# ---------------------------------------------------------------------------
# Domaenerne. key = noeglen i canvas_apps.json OG i side_nav.ITEMS.
#
#   tag     praefikset i domaenets egne navne. For Equipments og Materials
#           er det det NYE praefiks; "Dom" doebes om til det.
#   screen  skaermen, sidebaren og hubben navigerer til.
#   onvis   hvordan skaermens OnVisible bygges (se build_screens.py).
# ---------------------------------------------------------------------------
DOMAINS = [
    {"key": "hub", "folder": "Masterdata Hub", "screen": "ScreenMdHub",
     "tag": "Md"},
    {"key": "functionallocation", "folder": "Functional Location App",
     "screen": "ScreenFunctionalLocation", "tag": "Fl"},
    {"key": "vhplan", "folder": "Maintenance Plan App", "screen": "ScreenVhPlan",
     "tag": "Vhp"},
    {"key": "equipment", "folder": "Equipment App", "screen": "ScreenEquipment",
     "tag": "Eq", "rename": "Dom"},
    {"key": "material", "folder": "Material App", "screen": "ScreenMaterial",
     "tag": "Mat", "rename": "Dom"},
]
BY_KEY = {d["key"]: d for d in DOMAINS}

# side_nav.SCREENS og StartScreen.
SCREENS = {d["key"]: d["screen"] for d in DOMAINS}

# Dyblink: <play-url>?domain=vhplan&reqid=<RequestGuid>. Uden domain
# aabner appen paa hubben.
DOMAIN_PARAM = "domain"

# Taelleren bag "New request". Hvert tryk giver en ny noegle, saa ogsaa et
# tryk nummer to paa samme flise starter forfra.
NEW_SEQ = "gblNewSeq"


def want_var(tag):
    """Hvad hubben (eller dyblinket) har bedt domaeneskaermen om at vise:
    "new:<n>" eller "req:<RequestGuid>". Blank = intet - behold det, der er."""
    return f"gbl{tag}Want"


def opened_var(tag):
    """Det, skaermen sidst blev klargjort til. Er want det samme, roeres
    intet: man kommer tilbage til det, man forlod."""
    return f"var{tag}Opened"


def loading_var(tag):
    """Sand, mens skaermen klargoeres - saa laenge staar ventespinneren."""
    return f"var{tag}Loading"


def reqid_var(tag):
    """Den anmodning, der skal hentes. Erstatter Param("reqid") i
    domaenets egen kode - i een app er Param() det samme for alle skaerme
    og hele sessionen."""
    return f"gbl{tag}ReqId"


# ---------------------------------------------------------------------------
# Omdoebning: Equipments og Materials
# ---------------------------------------------------------------------------
# Alle deres navne er <type>Dom<Navn>: conDomForm, varDomMe, colDomRows,
# btnDomSave. "Domain" (en SharePoint-vaerdi) rammes ikke: efter "Dom"
# skal der staa et stort bogstav, et tal eller en understreg.
_RENAME = re.compile(r"(?<![A-Za-z0-9_])([a-z]{2,5})Dom(?=[A-Z0-9_])")


def rename(text, domain):
    """Doeb domaenets faelles praefiks om til dets eget. Andre domaener
    roeres ikke."""
    old = domain.get("rename")
    if not old:
        return text
    assert old == "Dom", old
    return _RENAME.sub(lambda m: m.group(1) + domain["tag"], text)


def leftover_shared_names(text):
    """Navne med det faelles praefiks, der overlevede omdoebningen. Skal
    vaere tom - ellers deler de to domaener stadig noget."""
    return sorted(set(re.findall(r"\b[a-z]{2,5}Dom[A-Z0-9_]\w*", text)))


# ---------------------------------------------------------------------------
# De fem appers App.pa.yaml
# ---------------------------------------------------------------------------
def app_yaml(domain):
    """App.Properties fra domaenets App.pa.yaml, uden det foranstillede '='."""
    import yaml
    path = os.path.join(ROOT, domain["folder"], "App.pa.yaml")
    doc = yaml.safe_load(open(path, encoding="utf-8"))
    props = doc["App"]["Properties"]
    return {k: (v[1:] if isinstance(v, str) and v.startswith("=") else v)
            for k, v in props.items()}


def prefs_block():
    """Samlingen bag SaveData - skrevet ordret som i alle fem apps."""
    name, schema = tok.prefs_schema()
    return "ClearCollect(%s, { %s });\nClear(%s);" % (
        name, ", ".join("%s: %s" % kv for kv in schema.items()), name)


def theme_block():
    return tok.onstart_block()


def domain_onstart(domain):
    """Domaenets egen del af OnStart: alt undtagen temaet.

    Temaet (samlingen bag SaveData + LoadData + darkModeEnabled) staar
    EEN gang i den samlede apps App.OnStart. Resten - skemaerne for
    arbejdssamlingerne, Set() af skaermens tilstand og VH-planens
    indlaesning af et dyblink - er domaenets, og det flyttes til skaermen.

    Blokkene fjernes som ORDRET tekst. Findes de ikke, har en af de fem
    apps faaet en anden OnStart, og saa skal det ses her - ikke gaettes."""
    on = app_yaml(domain)["OnStart"]
    for block in (prefs_block(), theme_block()):
        if block not in on:
            raise SystemExit(
                "%s/App.pa.yaml: OnStart indeholder ikke temablokken ordret.\n"
                "BIO SAP App/build/combined.py fjerner den som tekst - ret\n"
                "domain_onstart(), saa den passer til den nye OnStart."
                % domain["folder"])
        on = on.replace(block, "")
    # Der, hvor blokkene stod, er der nu tomme linjer i traek.
    on = re.sub(r"\n\s*\n(\s*\n)+", "\n\n", on).strip()
    if on.endswith(";"):
        on = on[:-1].rstrip()
    return rename(on, domain)


def with_reqid(text, domain):
    """Param("reqid") -> domaenets egen variabel. Se reqid_var()."""
    return text.replace('Param("reqid")', reqid_var(domain["tag"]))


# ---------------------------------------------------------------------------
# App.Formulas: del op i navngivne formler
# ---------------------------------------------------------------------------
def split_formulas(text):
    """[(navn, tekst)] - een pr. navngiven formel, med kommentarerne over den.

    En formel slutter ved et semikolon paa niveau 0: uden for parenteser,
    klammer og tuborger, strenge og kommentarer. Power Fx' strenge har ""
    for et anfoerselstegn og ingen backslash-escapes."""
    out, start, depth, i, n = [], 0, 0, 0, len(text)
    while i < n:
        c = text[i]
        if c == '"':
            i += 1
            while i < n:
                if text[i] == '"':
                    if i + 1 < n and text[i + 1] == '"':
                        i += 2
                        continue
                    break
                i += 1
        elif c == "'":
            i = text.index("'", i + 1)
        elif text.startswith("//", i):
            j = text.find("\n", i)
            i = n if j < 0 else j
            continue
        elif text.startswith("/*", i):
            i = text.index("*/", i) + 1
        elif c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == ";" and depth == 0:
            out.append(text[start:i + 1].strip())
            start = i + 1
        i += 1
    rest = text[start:].strip()
    if rest:
        out.append(rest.rstrip(";") + ";")
    named = []
    for f in out:
        code = re.sub(r"(?m)^\s*//.*$", "", f).strip()
        m = re.match(r"([A-Za-z_]\w*)\s*=", code)
        if not m:
            raise SystemExit("App.Formulas: kan ikke finde navnet i:\n  "
                             + f[:200])
        named.append((m.group(1), f))
    return named
