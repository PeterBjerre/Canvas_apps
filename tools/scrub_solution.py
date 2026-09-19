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

# Mapper hvis INDHOLD er vaerdier og ikke definitioner.
VALUE_DIRS = {"environmentvariablevalues", "environmentvariablevalue"}

# Noeglenavne, hvis vaerdi aldrig hoerer hjemme i et repo. Matcher baade
# JSON ("key": "vaerdi") og XML (<key>vaerdi</key>).
SECRET_KEYS = [
    "clientsecret", "client_secret", "secret", "secretvalue",
    "password", "pwd", "apikey", "api_key", "x-functions-key",
    "functionkey", "accountkey", "sharedaccesskey", "primarykey",
    "secondarykey", "connectionstring", "authorization", "access_token",
    "refresh_token", "id_token", "privatekey", "certificatepassword",
]

# Moenstre der er hemmelige uanset hvad de hedder.
INLINE_PATTERNS = [
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9\-._~+/]{20,}=*"), "Bearer-token"),
    (re.compile(r"(?i)\bsig=[A-Za-z0-9%\-._~+/]{20,}"), "SAS-signatur"),
    (re.compile(r"(?i)\bAccountKey=[A-Za-z0-9+/=]{20,}"), "storage-noegle"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"), "JWT"),
]

REDACTED = "***REDACTED***"


def _key_patterns():
    """Eet moenster pr. noeglenavn, for JSON og for XML."""
    out = []
    for k in SECRET_KEYS:
        esc = re.escape(k)
        out.append((re.compile(r'(?i)("' + esc + r'"\s*:\s*")([^"]{1,4096})(")'),
                    k, lambda m: m.group(1) + REDACTED + m.group(3)))
        out.append((re.compile(r'(?i)(<' + esc + r'>)([^<]{1,4096})(</' + esc + r'>)'),
                    k, lambda m: m.group(1) + REDACTED + m.group(3)))
    return out


KEY_PATTERNS = _key_patterns()


def scrub_text(text):
    """Returnerer (ny tekst, [hvad der blev roert])."""
    hits = []
    for rx, name, repl in KEY_PATTERNS:
        def _sub(m):
            if m.group(2).strip() in ("", REDACTED):
                return m.group(0)
            hits.append(name)
            return repl(m)
        text = rx.sub(_sub, text)
    for rx, name in INLINE_PATTERNS:
        text, n = rx.subn(REDACTED, text)
        hits.extend([name] * n)
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

    # 1) vaerdifilerne
    if not args.keep_values:
        for d, subdirs, _ in os.walk(root):
            for sub in list(subdirs):
                if sub.lower() in VALUE_DIRS:
                    path = os.path.join(d, sub)
                    removed.append(os.path.relpath(path, root))
                    if not args.report_only:
                        shutil.rmtree(path, ignore_errors=True)
                    subdirs.remove(sub)

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
