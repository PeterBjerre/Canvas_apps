# -*- coding: utf-8 -*-
"""
Leder efter hemmeligheder i HELE repoet - ikke kun i solution/.

    python3 tools/check_secrets.py

HVORFOR
-------
scrub_solution.py kigger kun i solution-eksporten. En signeret Power
Automate-trigger-URL (sig=...) stod derfor i excel/src/Modules/Constants.bas
og i VBA-projektet inde i en .xlsm, uden at noget tjek saa den. Signaturen
ER adgangen: alle med URL'en kan starte flowet.

Det her bruger de samme moenstre som scrub_solution.py (INLINE_PATTERNS),
saa de to ikke kan glide fra hinanden, og laeser:

  * alle tekstfiler, git kender (git ls-files)
  * medlemmerne i zip-baserede Office-filer (.xlsm/.xlsx/.docx/.pptx/.msapp).
    VBA-projektet (xl/vbaProject.bin) er delvist komprimeret, saa et fund
    der er et sikkert fund - men intet fund er ikke en garanti.

Det RETTER intet. En hemmelighed, der er committet, skal roteres - at
slette den fra filen bagefter hjaelper ikke, historikken husker den.
Exitkode 1, hvis der er fund. Vaerdien skrives aldrig ud.
"""
import os
import subprocess
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scrub_solution import INLINE_PATTERNS  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ZIP_EXT = {".xlsm", ".xlsx", ".docx", ".pptx", ".msapp", ".zip"}
SKIP_EXT = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".db", ".frx", ".pdf"}
MAX_BYTES = 50 * 1024 * 1024


def tracked_files():
    try:
        out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT,
                             capture_output=True, check=True).stdout
        return [p for p in out.decode("utf-8").split("\0") if p]
    except (OSError, subprocess.CalledProcessError):
        files = []
        for d, subs, names in os.walk(ROOT):
            subs[:] = [s for s in subs if s != ".git"]
            files += [os.path.relpath(os.path.join(d, n), ROOT) for n in names]
        return files


def scan_bytes(data):
    """Navnene paa de moenstre, der rammer. Aldrig selve vaerdien."""
    text = data.decode("latin-1")
    return sorted({label for rx, label in INLINE_PATTERNS if rx.search(text)})


def scan_file(rel):
    path = os.path.join(ROOT, rel)
    ext = os.path.splitext(rel)[1].lower()
    if ext in SKIP_EXT or not os.path.isfile(path):
        return []
    if os.path.getsize(path) > MAX_BYTES:
        return []
    hits = []
    if ext in ZIP_EXT:
        try:
            with zipfile.ZipFile(path) as z:
                for member in z.namelist():
                    for label in scan_bytes(z.read(member)):
                        hits.append((f"{rel} [{member}]", label))
        except zipfile.BadZipFile:
            pass
        return hits
    with open(path, "rb") as f:
        return [(rel, label) for label in scan_bytes(f.read())]


def main():
    files = tracked_files()
    hits = []
    for rel in files:
        hits += scan_file(rel)
    if not hits:
        print(f"Hemmelighedstjek: {len(files)} fil(er), intet fundet.")
        return 0
    print("Der ligger noget, der ligner en hemmelighed:\n")
    for where, label in hits:
        print(f"  {where}: {label}")
    print("\nFjern den fra filen, ROTER den (en committet noegle kan ikke")
    print("kaldes tilbage), og laeg vaerdien uden for git.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
