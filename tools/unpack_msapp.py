# -*- coding: utf-8 -*-
"""
Pakker hver .msapp i en solution-eksport ud som LAESBAR tekst.

    python tools/unpack_msapp.py solution

HVORFOR
-------
En .msapp er en zip. Inden i ligger app'ens skaerme som .pa.yaml - praecis
den tekst, der skal laeses for at vide, hvad app'en er. Men .msapp er
binaer og staar i .gitignore, og export_solution.ps1 tager den ovenikoebet
ud af sporingen hver gang. Den naar altsaa ALDRIG GitHub.

Det betyder, at en app, der kun findes i solutionen - Equipment, Materialer
- ikke kan laeses af nogen, der arbejder mod repoet. Eksporten lovede at
vaere "hele solutionen", men canvas apps var i praksis en sort kasse.

Her pakkes de ud. Teksten committes, zip'en goer ikke.

HVAD DER PAKKES UD
------------------
    Src/*.pa.yaml            skaermene og App - selve app'en
    References/DataSources.json   hvad app'en er bundet til
    Properties.json          navn og id

_EditorState.pa.yaml springes over. Den er studiets eget bogholderi over
markeringer og foldede noder - stoej i enhver diff, og ikke app'en.

Controls/*.json springes ogsaa over. Det er den samme app en gang til, i
maskinform; formlerne staar allerede laesbart i .pa.yaml.

REKKEFOELGEN ER IKKE LIGEGYLDIG
-------------------------------
Det her skal koere FOER scrub_solution.py. En app kan baere en URL eller en
noegle i en formel, og rensningen kan kun fjerne det, den kan se. Pakkes
der ud bagefter, er teksten ureniet.
"""
import argparse
import io
import json
import os
import shutil
import sys
import zipfile

# Hvad der er vaerd at tage med. Alt andet i zip'en er enten binaert,
# maskinform af noget vi allerede har, eller studiets bogholderi.
WANTED_EXACT = {
    "references/datasources.json",
    "properties.json",
}
WANTED_PREFIX = "src/"
SKIP_NAMES = {"_editorstate.pa.yaml"}


def entries(z):
    """Zip-navne med skraastreg samme vej.

    .msapp skriver stier med BACKSLASH - unzip advarer selv om det. Det
    maa ikke smitte af paa mappenavnene paa disken."""
    for info in z.infolist():
        if info.is_dir():
            continue
        yield info, info.filename.replace("\\", "/")


def wanted(rel):
    low = rel.lower()
    if os.path.basename(low) in SKIP_NAMES:
        return False
    if low in WANTED_EXACT:
        return True
    return low.startswith(WANTED_PREFIX) and low.endswith(".pa.yaml")


def as_text(raw):
    """UTF-8 uden BOM, linjeskift som LF.

    Repoet er LF - se .gitattributes. Lander en msapp's CRLF i en committet
    fil, er den beskidt paa hver eneste maskine, der checker ud."""
    text = raw.decode("utf-8-sig")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def app_name(z):
    """App'ens rigtige navn - det, den hedder i Studio."""
    for info, rel in entries(z):
        if rel.lower() == "properties.json":
            try:
                return json.loads(as_text(z.read(info))).get("Name")
            except Exception:
                return None
    return None


def unpack_one(msapp, report):
    """Een .msapp -> een <navn>.src-mappe ved siden af."""
    base = os.path.basename(msapp)
    for tail in ("_DocumentUri.msapp", ".msapp"):
        if base.endswith(tail):
            base = base[: -len(tail)]
            break
    out = os.path.join(os.path.dirname(msapp), base + ".src")

    # Mappen bygges forfra. Bliver en skaerm slettet i Studio, skal filen
    # ogsaa vaere vaek her - ellers staar der en skaerm i repoet, som
    # app'en ikke har.
    if os.path.isdir(out):
        shutil.rmtree(out)

    written = 0
    with zipfile.ZipFile(msapp) as z:
        name = app_name(z)
        for info, rel in entries(z):
            if not wanted(rel):
                continue
            dest = os.path.join(out, *rel.split("/"))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with io.open(dest, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(as_text(z.read(info)))
            written += 1

    report.append((base, name, written, out))
    return written


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Pak canvas apps ud af en solution-eksport som laesbar tekst.")
    ap.add_argument("root", help="eksportmappen, fx solution")
    args = ap.parse_args(argv)

    if not os.path.isdir(args.root):
        print("Mappen findes ikke: %s" % args.root, file=sys.stderr)
        return 2

    found = []
    for d, _subdirs, files in os.walk(args.root):
        for f in files:
            if f.lower().endswith(".msapp"):
                found.append(os.path.join(d, f))
    found.sort()

    if not found:
        print("Ingen .msapp fundet under %s - ingenting at pakke ud." % args.root)
        return 0

    report = []
    for msapp in found:
        unpack_one(msapp, report)

    width = max(len(b) for b, _n, _w, _o in report)
    print("Canvas apps pakket ud som tekst:")
    for base, name, written, out in report:
        label = name if name else "(uden navn)"
        note = "" if written else "   <- TOM, ingen skaerme i app'en"
        print("  %-*s  %-28s %2d fil(er)%s" % (width, base, label, written, note))
    print("")
    print("Teksten ligger i <navn>.src ved siden af hver .msapp og committes;")
    print(".msapp selv gaar ikke med - den staar i .gitignore.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
