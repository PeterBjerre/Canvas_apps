# -*- coding: utf-8 -*-
"""
Renser en solution-eksport, foer den kan committes.

    python tools/scrub_solution.py solution
    python tools/scrub_solution.py solution --report-only

HVORFOR
-------
En eksporteret solution er ikke uskyldig tekst. Flow-definitioner baerer
endpoint-URL'er og nogle gange noegler; miljoevariablernes VAERDIER er
praecis det sted, hvor en client secret ender. Lander det paa GitHub, kan
det ikke kaldes tilbage - heller ikke ved at slette filen bagefter, for
historikken bliver.

Derfor koerer det her ALTID mellem eksporten og git. Standarden er at
redigere - ikke at advare og lade det ligge - saa en glemt gennemlaesning
ikke er nok til at lave skaden.

HVAD DER SKER
-------------
1. Miljoevariablernes vaerdifiler slettes. Definitionerne bliver: det er
   dem, der fortaeller hvad en variabel HEDDER og goer. Vaerdien hoerer til
   miljoeet, ikke til koden.
2. Felter, der ligner en hemmelighed, overskrives med ***REDACTED***.
3. Alt, der blev roert, skrives ud. Intet sker i stilhed.

Med --report-only aendres ingen filer; scriptet siger kun hvad det ville
goere og slutter med exitkode 1, hvis der var noget. Brug den, hvis du vil
se listen foer du beslutter dig.
"""
import argparse
import os
import re
import shutil
import sys

# Filer vi overhovedet kigger i. Resten er binaert eller ligegyldigt.
TEXT_EXT = {".json", ".xml", ".yml", ".yaml", ".txt", ".config", ".resx",
            ".csv", ".md", ".cdsproj", ".props", ".targets"}

# Miljoevariablernes VAERDIER. pac skriver dem som en fil inde i hver
# definitionsmappe - ikke som en mappe for sig, som foerste udgave af det
# her script gik ud fra. Begge former haandteres nu.
VALUE_DIRS = {"environmentvariablevalues", "environmentvariablevalue"}
VALUE_FILES = {"environmentvariablevalues.json", "environmentvariablevalue.json"}

# Ord i et FELTNAVN, der goer vaerdien hemmelig. Der matches paa
# DELSTRENG, ikke paa hele navnet: den foerste udgave ledte efter feltet
# "apikey" og gik derfor lige forbi "x-apikey", som er praecis det navn,
# de to SAP-flows bruger. Et feltnavn kan hedde hvad som helst rundt om
# ordet - ocp-apim-subscription-key, X-API-Key, clientSecret.
SECRET_WORDS = (
    "secret", "password", "pwd", "apikey", "api-key", "api_key",
    "accountkey", "sharedaccesskey", "subscriptionkey", "subscription-key",
    "functionskey", "functions-key", "privatekey", "access_token",
    "refresh_token", "id_token", "sastoken", "connectionstring",
    "authorization", "credential",
)

# Moenstre der er hemmelige uanset hvad feltet hedder.
INLINE_PATTERNS = [
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9\-._~+/]{20,}=*"), "Bearer-token"),
    (re.compile(r"(?i)\bsig=[A-Za-z0-9%\-._~+/]{20,}"), "SAS-signatur"),
    (re.compile(r"(?i)\bAccountKey=[A-Za-z0-9+/=]{20,}"), "storage-noegle"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"), "JWT"),
]

# Et felt og dets vaerdi - vilkaarligt navn. Navnet vurderes bagefter, saa
# et nyt feltnavn ikke kraever et nyt moenster.
JSON_PAIR = re.compile(r'"([A-Za-z0-9_\-.:]{1,80})"\s*:\s*"((?:[^"\\]|\\.){0,4096})"')
XML_PAIR = re.compile(r"<([A-Za-z0-9_\-.:]{1,80})>([^<>]{1,4096})</\1>")

REDACTED = "***REDACTED***"


def is_secret_key(name):
    low = name.lower()
    return any(w in low for w in SECRET_WORDS)


def looks_like_credential(value):
    """Er vaerdien noget, der KAN vaere en hemmelighed?

    Det vigtigste nej staar foerst: "@{parameters('...')}" er en henvisning
    til en miljoevariabel - altsaa netop den rigtige maade at holde
    hemmeligheden UDE af flowet. Overskrev man den, ville filen lyve om,
    hvordan flowet virker, og den rigtige hemmelighed var der alligevel
    ikke.

    Derefter det trivielle: tal, ja/nej og korte vaerdier. <secretstore>0<>
    hedder noget hemmeligt og er det ikke."""
    v = value.strip()
    if not v or "@{" in v or v.startswith("@"):
        return False
    if len(v) < 8:
        return False
    if v.isdigit() or v.lower() in ("true", "false", "null", "none"):
        return False
    return True


def scrub_text(text):
    """Returnerer (ny tekst, [hvad der blev roert])."""
    hits = []

    def _pair(m, joiner):
        name, value = m.group(1), m.group(2)
        if not is_secret_key(name) or not looks_like_credential(value):
            return m.group(0)
        if value == REDACTED:
            return m.group(0)
        hits.append(name)
        return joiner(name)

    text = JSON_PAIR.sub(lambda m: _pair(m, lambda n: f'"{n}": "{REDACTED}"'), text)
    text = XML_PAIR.sub(lambda m: _pair(m, lambda n: f"<{n}>{REDACTED}</{n}>"), text)
    for rx, label in INLINE_PATTERNS:
        text, n = rx.subn(REDACTED, text)
        hits.extend([label] * n)
    return text, hits


def walk(root):
    for d, subdirs, files in os.walk(root):
        subdirs[:] = [s for s in subdirs if s not in (".git", "obj", "bin")]
        for f in files:
            yield os.path.join(d, f)


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="scrub_solution.py",
        description="Fjern hemmeligheder fra en solution-eksport, foer den committes.")
    p.add_argument("folder", nargs="?", default="solution",
                   help="mappen med den udpakkede solution (standard: solution)")
    p.add_argument("--report-only", action="store_true",
                   help="ret ingenting - sig kun hvad der ville ske")
    p.add_argument("--keep-values", action="store_true",
                   help="behold miljoevariablernes vaerdifiler (frarraades)")
    args = p.parse_args(argv)

    root = os.path.abspath(args.folder)
    if not os.path.isdir(root):
        print(f"Mappen findes ikke: {root}")
        print("Koer tools\\export_solution.ps1 foerst.")
        return 2

    removed, edited, scanned = [], [], 0

    # 1) vaerdifilerne - baade som mappe og som enkeltfil
    if not args.keep_values:
        for d, subdirs, files in os.walk(root):
            for sub in list(subdirs):
                if sub.lower() in VALUE_DIRS:
                    path = os.path.join(d, sub)
                    removed.append(os.path.relpath(path, root))
                    if not args.report_only:
                        shutil.rmtree(path, ignore_errors=True)
                    subdirs.remove(sub)
            for f in files:
                if f.lower() in VALUE_FILES:
                    path = os.path.join(d, f)
                    removed.append(os.path.relpath(path, root))
                    if not args.report_only:
                        os.remove(path)

    # 2) hemmeligheder i teksten
    for path in walk(root):
        if os.path.splitext(path)[1].lower() not in TEXT_EXT:
            continue
        scanned += 1
        try:
            raw = open(path, encoding="utf-8-sig").read()
        except (UnicodeDecodeError, OSError):
            continue
        new, hits = scrub_text(raw)
        if hits:
            edited.append((os.path.relpath(path, root), sorted(set(hits)), len(hits)))
            if not args.report_only:
                with open(path, "w", encoding="utf-8", newline="") as f:
                    f.write(new)

    verb = "ville blive" if args.report_only else "blev"
    print(f"Gennemgaaet: {scanned} tekstfil(er) i {root}")
    if removed:
        print(f"\nMiljoevariabel-vaerdier ({verb} fjernet):")
        for r in removed:
            print("  " + r)
    if edited:
        print(f"\nHemmeligheder ({verb} overskrevet):")
        for rel, names, n in edited:
            print(f"  {rel}  ({n}x: {', '.join(names)})")
    if not removed and not edited:
        print("\nIntet fundet. Eksporten indeholder ingen af de moenstre, "
              "scriptet kender.")

    print("\nDet her er et sikkerhedsnet, ikke en garanti. Laes selv "
          "flow-definitionerne igennem,")
    print("foer du committer - et hemmeligt felt kan hedde noget, ingen har "
          "taenkt paa.")
    return 1 if (args.report_only and (removed or edited)) else 0


if __name__ == "__main__":
    sys.exit(main())
