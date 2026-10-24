# -*- coding: utf-8 -*-
"""
APPENS SPROG ER ENGELSK - og de LAGREDE vaerdier er ikke sprog.

HVORFOR DEN HER FIL FINDES
--------------------------
Apperne var bygget paa dansk og blev oversat til engelsk. Det var 120
strenge, og de laa spredt i femten buildere. Uden en vagt glider en dansk
knaplabel ind igen foerste gang nogen tilfoejer et felt.

MEN DET FARLIGE VAR DET MODSATTE
--------------------------------
Seks af de danske ord paa skaermen maatte IKKE oversaettes:

    Kladde  Indsendt  UnderBehandling  AfventerInfo  Afvist  Annulleret

De er SharePoint-VALGVAERDIER. De skrives af de fem domaeneapps, laeses af
flowene og staar i rigtige raekker i produktionen. Oversaetter man dem,
holder appen op med at kunne skrive - og fejlen viser sig ikke i
byggeriet, men naar en bruger trykker Indsend.

Det samme gaelder "Ny", "AEndre" og "Slettes": de var noegler i en
Switch, der oversatte til SharePoints egne valg. (Den Switch ramte i
oevrigt aldrig - se build_save.py.)

Vagten skelner derfor de to ting:

    DISPLAY   alt hvad brugeren laeser  ->  skal vaere engelsk
    VAERDI    alt der skrives i en liste ->  maa ikke roeres

En VAERDI kendes paa, at den staar som { Value: "..." }, som en noegle i
en Switch, eller i ALLOW nedenfor.
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Danske ord, der afsloerer en dansk streng. Ikke en ordbog - en stikproeve
# stor nok til at fange en saetning, og lille nok til ikke at ramme
# engelsk. "og", "til", "med" udelades: de findes ogsaa i produktnavne.
# HELE ORD, DER ER DANSKE
#
# Foerste udgave var en liste over almindelige danske ORD i saetninger.
# Den fangede saetninger fint og missede fire enkeltord, fordi de er korte
# eller staar med stort:
#
#     "Aabn"  "MATERIALE"  "FABRIKANTENS NR."  "FILER"
#
# De blev fundet i haanden, ikke af tjekket. To ting rettet: listen her,
# og reglen nedenfor - en streng paa EET ord taeller nu ogsaa, hvor
# saetningsreglen kraever to.
SINGLE = {
    "aabn", "luk", "gem", "ryd", "fjern", "slet", "soeg", "hent", "vis",
    "skjul", "vaelg", "tilfoej", "opret", "indsend", "annuller", "kopier",
    "rediger", "filer", "mappe", "raekke", "raekker", "felt",
    "felter", "materiale", "materialer", "udstyr", "vaerk", "vaerker",
    "lager", "beskrivelse", "leverandoer",
    "fabrikant", "fabrikantens", "noegle", "noeglen", "detaljer",
    "kladde", "moerk", "lys", "tema", "hjaelp", "tilbage", "naeste",
    "forrige", "gemte", "valgte", "ingen", "alle",
    # Issue #29: Materials-appens feltnavne og sektioner stod paa dansk i
    # domain_config.py - og slap igennem, fordi ingen af ordene stod her.
    "stamdata", "modelnummer", "varenr", "leveringstid", "dage",
    "prisenhed", "lagerenhed", "klassificering", "sliddel",
    "bemaerkninger", "langtekst", "fundet", "gemning", "fejlede",
    # "Gemning afbrudt - kontakt SAP masterdata." stod i to Notify'er i
    # VH-plan og slap igennem: fem ord, og kun "gemning" stod her.
    "afbrudt", "kontakt", "fejl", "gemmer", "venligst", "mislykkedes",
    # Issue #162: godkendelsesflowenes tekster ("intet svar fra ...").
    "svar", "retur",
}

DANISH = re.compile(
    r"(?:\b(?:aa|ae|oe|ikke|skal|foerst|vaelg|vaelge|gem|gemt|ryd|fjern|fjernet|tilfoej|"
    r"raekke|raekken|raekker|felt|felter|indsend|indsendt|kladde|opret|oprettet|slet|"
    r"slettet|luk|annuller|soeg|soeger|hent|hentet|skjul|mangler|findes|naar|hvor|hvad|"
    r"denne|dette|pakker|pakke|noegle|noeglen|vaerk|vaerket|udfyld|udfyldes|paa|som|"
    r"uden|kun|alle|ingen|flere|valgt|valgte|dokument|dokumenter|lagt|godkendt|moerk|"
    r"lys|tema|underliggende|objekter|landingssiden|hierarki|beskrivelse|aendre|aendret|"
    r"advarsel|traek|gennemse|laeg|filtrer|antal|personer|leverandoer|pris|lager|"
    r"reservedele|meld|indberetningen|indmeldingen|biblioteket|indsnaevre|mappen|hedder|"
    r"sendt|forfra|garanti|sidder|strategi|strategier|arbejdsplaner|arbejdscentre|tegn|"
    r"maks|hoejst|mindst|nedenfor|paakraevet|"
    # Issue #162: ordene i godkendelsesflowenes log-, retur- og mailtekster.
    r"godkender|godkendelse|godkendelsen|omkostning|kvalitet|intet|planen|tidligere|"
    r"opretter|strategiplan|cyklus|rekvirent|funktionsplads|kvittering|varighed)\b|[ÆØÅæøå])",
    re.I)

# Strenge, der er danske MED VILJE.
ALLOW = {
    # SharePoint-valgvaerdier. Se docstringen.
    "Kladde", "Indsendt", "UnderBehandling", "AfventerInfo", "Afvist",
    "Annulleret", "KlarTilSAP", "OprettetISAP",
    "Ny", "AEndre", "Slettes",
    # Rigtige danske dokumenttitler i kildehenvisningen. At oversaette dem
    # ville goere dem umulige at finde.
    'Source: ""Den gode VH-plan"" (May 2025) and ""Planlaegning af en VH '
    'ordre"" (2026). Ask SAPvedligehold@orsted.dk.',
    # Godkendelseskortets gamle svar. Udfaldet godtager det stadig, saa et
    # kort startet foer issue #162 godkender (solution/.../Workflows).
    "Godkend",
}
# De danske saetninger, flowene skrev foer issue #162. De staar i appen som
# OPSLAG i tools/display_text.py (dansk -> engelsk ved visning), ikke som
# visningstekst. Kun paa skaermene: et FLOW maa ikke skrive dem igen.
sys.path.insert(0, os.path.join(ROOT, "tools"))
import display_text as _dt  # noqa: E402
ALLOW_SCREENS = (ALLOW | {da.strip() for da, _en in _dt.EXACT + _dt.PREFIX + _dt.FRAGMENT}
                 # Gamle opsummeringer i MD_RequestIndex (UX-review B4).
                 | {da.strip() for da, _en in _dt.LEGACY_SHORT})

# Ting, der ikke er saetninger: farver, tal, egenskabsnavne, URL'er.
SKIP = re.compile(r"^(#|RGBA|Font\.|https?:|[A-Za-z]+\.[A-Za-z]|@odata|[\d\s,.:;/|<>_-]+$)")


def screens():
    # Udfasede enkeltapps springes over: deres .pa.yaml ignoreres af git og
    # kan vaere gamle (docs/33-udfasning.md).
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import env_config
    skip = set(env_config.retired_folders())
    out = []
    for d in sorted(os.listdir(ROOT)):
        p = os.path.join(ROOT, d)
        if not os.path.isdir(p) or d in skip:
            continue
        for f in sorted(os.listdir(p)):
            if f.endswith(".pa.yaml") and not f.startswith("_"):
                out.append(os.path.join(p, f))
    return out


def _danish(v, allow=ALLOW):
    """Er v (en streng uden omgivende mellemrum) dansk visningstekst?"""
    if len(v) < 3 or v in allow or SKIP.match(v):
        return False
    words = re.findall(r"[A-Za-zÆØÅæøå]+", v)
    # Kort streng: eet dansk ord er nok. Laengere streng: to - saa
    # en enkelt tilfaeldighed ("alle" i et navn) ikke giver et fund,
    # men en dansk saetning med kun SINGLE-ord gaar ikke igennem.
    hits = sum(1 for w in words if w.lower() in SINGLE)
    single = hits >= (1 if len(words) <= 3 else 2)
    return bool(DANISH.search(v)) or single


# ---------------------------------------------------------------------------
# FLOWENE (issue #162)
#
# Godkendelsesflowene skrev dansk i MD_ApprovalLog ("opretter er 1. eller 2.
# godkender for system 2"), i ReturnComment og i mails - og appen viste det.
# Skaermtjekket ovenfor ser kun .pa.yaml. Her laeses de tekster i flow-
# eksporten, som en bruger kan se: kolonner, flowet skriver (item/...,
# HTTP-body), godkendelseskortet, mails og Compose-tekster. Ikke: navne paa
# handlinger, beskrivelser (kun i designeren), valgvaerdier ("Value") og
# mappestier.
# ---------------------------------------------------------------------------
FLOWS = os.path.join("solution", "BIOSAP", "src", "Workflows")
_EXPR = re.compile(r"@\{(?:[^{}]|\{[^{}]*\})*\}")


def _flow_texts(o, key=""):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ("description", "runAfter", "Value", "folderPath", "type", "kind",
                     "metadata", "operationMetadataId") or k.startswith("$"):
                continue
            yield from _flow_texts(v, k)
    elif isinstance(o, list):
        for v in o:
            yield from _flow_texts(v, key)
    elif isinstance(o, str):
        if o.startswith("@"):
            # Et udtryk: kun dets tekstkonstanter ('...').
            for m in re.finditer(r"'((?:[^']|'')*)'", o):
                yield m.group(1)
        else:
            # Tekst med indlejrede udtryk: konstanterne i udtrykkene og
            # teksten imellem dem, uden HTML-maerker.
            for m in _EXPR.finditer(o):
                for c in re.finditer(r"'((?:[^']|'')*)'", m.group(0)):
                    yield c.group(1)
            rest = _EXPR.sub(" ", o)
            for t in re.split(r"<[^>]*>|&[a-z]+;|\\n|\n", rest):
                yield t


def check_flows():
    import json
    d = os.path.join(ROOT, FLOWS)
    if not os.path.isdir(d):
        return [], 0
    bad, n = [], 0
    for f in sorted(os.listdir(d)):
        if not f.endswith(".json"):
            continue
        n += 1
        with io.open(os.path.join(d, f), encoding="utf-8-sig") as fh:
            try:
                data = json.load(fh)
            except ValueError as e:
                # Ellers kom kun en traceback uden filnavn (issue #585). Den
                # typiske aarsag er en halvt loest git-konflikt (<<<<<<<).
                sys.exit(f"{FLOWS}/{f} er ikke gyldig JSON: {e}\n"
                         "  -> se efter <<<<<<< / ======= / >>>>>>> fra en git-konflikt, "
                         "eller hent filen igen: git checkout origin/main -- <filen>")
        name = re.sub(r"-[0-9A-Fa-f]{8}-.*$", "", f)
        for t in _flow_texts(data):
            v = t.strip()
            # Mappestier og filendelser (/SAP-oprettelse/..., .kvittering.json)
            # er navne i SharePoint, ikke tekst.
            if v.startswith(("/", ".")) or not _danish(v):
                continue
            bad.append("  %-24s %s" % (name, v[:90]))
    return bad, n


# ---------------------------------------------------------------------------
# SENTENCE CASE (UX-review 2026-10, F1/T7)
#
# Kortene hed "Equipment Form", "Saved Rows", "Plan Header", "Item Editor"
# og "Tasklist For Active Item" - ved siden af "Add item" og "Save draft".
# Appen skriver sentence case: kun foerste ord med stort, plus egennavne og
# forkortelser. Reglen laeser hver tekstlitteral i Text og Label og afviser
# et ord med stort forbogstav midt i en saetning, med mindre det hoerer til
# et egennavn i PROPER.
# ---------------------------------------------------------------------------
PROPER = (
    # Domaenerne og skaermene - de er navne, ogsaa midt i en saetning.
    "Masterdata Hub", "Functional Locations", "Functional Location",
    "Maintenance Plans", "Maintenance Plan", "Measuring Points", "Measuring Point",
    "Issue Board", "Equipments", "Equipment", "Materials", "Material",
    "KKS lookup", "BIO SAP",
    # Roller og systemer, appen henviser til.
    "Master Data", "System Manager", "SharePoint", "Power Apps", "Outlook",
    "Excel", "Teams", "Office", "Microsoft", "Windows", "Edge", "Chrome",
    # Knap- og feltnavne, en hjaelpetekst citerer ("choose Add row").
    "Add row", "Update row", "Save draft", "Submit", "New request", "Edit",
    "Documents", "Details", "Objects", "Copy row", "Delete row", "Search",
    "Clear filters", "Valid FL", "Paste rows", "Add item", "Add material", "Add",
    "Upload", "Reopen", "New issue", "Done", "Manual operation", "Add lines from task list", "Save changes", "Save", "None", "ZBOW", "Office 365",
    # Kortene, en hjaelpetekst henviser til ved navn.
    "Task list and operations", "Strategy packages", "Plan header", "Row details",
    "Classes",  # FL-kortet - klik-lagets "Expand Classes" (issue #548)
    # SharePoint-kolonner, en hjaelpetekst naevner ved navn.
    "Hierarchical",
    # Issue Boards statusser (Issue Board/build/ib_config.STATUS).
    "Ready for retest", "Closed",
    # Ugedage og maaneder.
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
    "January", "February", "March", "April", "May", "June", "July", "August",
    "September", "October", "November", "December",
)
# Egenskaberne, brugeren laeser som overskrift eller etiket.
CASE_PROPS = ("Text", "Label")
_WORD = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_'’]*")
# En ny saetning: starten, efter . : ! ? ( · | / , efter " - " og efter
# to eller flere mellemrum (to tekster sat sammen med &).
_SENTENCE = re.compile(r"(?:^|[.:!?(·•|/]|\s-\s|\s–\s|\s{2,})\s*$")


def _proper():
    """PROPER + appens statusetiketter (Submitted, Ready for SAP ...)."""
    import request_index as ri
    return PROPER + tuple(lab for _k, lab, _s in ri.STATUS)


def title_case_words(v):
    """Ordene i v, der staar med stort forbogstav midt i en saetning."""
    t = v
    for p in sorted(_proper(), key=len, reverse=True):
        t = re.sub(r"\b%s\b" % re.escape(p), lambda m: "_" * len(m.group(0)), t)
    out = []
    for m in _WORD.finditer(t):
        w = m.group(0)
        if not re.match(r"^[A-Z][a-z]+$", w):
            continue                      # smaa ord, FORKORTELSER, MD_Navne, CamelCase
        if _SENTENCE.search(t[:m.start()]):
            continue                      # foerste ord i en saetning
        out.append(w)
    return out


def _yaml_props(path):
    import yaml
    doc = yaml.safe_load(io.open(path, encoding="utf-8"))
    def walk(nodes):
        for item in nodes or []:
            for name, body in item.items():
                yield name, body.get("Properties") or {}
                yield from walk(body.get("Children"))
    for scr in (doc.get("Screens") or {}).values():
        yield from walk(scr.get("Children"))


def check_case(paths=None):
    """Title Case i Text/Label -> fund (liste af tekstlinjer)."""
    bad = []
    for path in paths or screens():
        if not os.path.basename(path).startswith("Screen"):
            continue
        for name, props in _yaml_props(path):
            for key in CASE_PROPS:
                val = props.get(key)
                if not isinstance(val, str):
                    continue
                for m in re.finditer(r'"((?:[^"]|"")*)"', val):
                    lit = m.group(1).replace('""', '"').strip()
                    if " " not in lit:
                        continue
                    words = title_case_words(lit)
                    if words:
                        bad.append("  %-24s %s.%s: %s  (%s)" % (
                            os.path.basename(os.path.dirname(path)), name, key,
                            lit[:70], ", ".join(words)))
    return bad


def check():
    bad = []
    n_files = 0
    for path in screens():
        n_files += 1
        txt = io.open(path, encoding="utf-8").read()
        # Power Fx har ingen backslash-escapes i strenge - kun "" for et
        # anfoerselstegn. Her stod [^"\\], og saa var et regex-moenster som
        # "[0-9\s]" nok til at forskyde parringen af anfoerselstegn resten af
        # filen: tjekket laeste kode som tekst og meldte den som dansk.
        for m in re.finditer(r'"((?:[^"]|"")*)"', txt):
            v = m.group(1).strip()
            if not _danish(v, ALLOW_SCREENS):
                continue
            # En VAERDI, ikke en visning: { Value: "..." } eller en
            # Switch-noegle. Begge skrives i en liste og er ikke sprog.
            before = txt[max(0, m.start() - 40):m.start()]
            if re.search(r"Value:\s*$", before):
                continue
            bad.append("  %-24s %s" % (os.path.basename(os.path.dirname(path)), v[:90]))
    flow_bad, n_flows = check_flows()
    bad += flow_bad
    case_bad = check_case()
    if case_bad:
        raise SystemExit(
            "Sprogtjek: %d tekst(er) i Title Case.\n" % len(case_bad)
            + "\n".join(sorted(set(case_bad))) +
            "\n\nAppen skriver sentence case (UX-review F1): kun foerste ord med\n"
            "stort, plus egennavne. Er ordet et egennavn, saa skriv det i PROPER\n"
            "i tools/check_language.py.")
    if bad:
        raise SystemExit(
            "Sprogtjek: %d dansk(e) streng(e) paa skaermene.\n" % len(bad)
            + "\n".join(sorted(set(bad))) +
            "\n\nAppernes sprog er engelsk. Er strengen en LAGRET vaerdi - en\n"
            "SharePoint-valgvaerdi eller en Switch-noegle - saa skal den ikke\n"
            "oversaettes; skriv den i ALLOW i tools/check_language.py i stedet.")
    print("Sprogtjek: %d skaerm(e) og %d flow(s), ingen dansk visningstekst."
          % (n_files, n_flows))


if __name__ == "__main__":
    check()
