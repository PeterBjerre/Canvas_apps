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

UD OVER INLINE_PATTERNS (R2-026, R2-025)
---------------------------------------
  * ASSIGN: en tildeling af en hemmelighed i kode - `$ClientSecret = "..."`
    i .ps1, `Const API_KEY = "..."` i .bas, `password: '...'` i YAML.
  * scrub_text fra scrub_solution.py paa tekstformater (.json, .xml, .md,
    .yml, .yaml, .txt): de samme navne-regler (clientsecret, x-apikey ...),
    som renser solution/, gaelder nu ogsaa uden for den. Henvisninger som
    @{parameters('k')} er stadig ikke et fund.
  * Personlige firmaadresser i schema/, flow/, html/, docs/ og
    sharepoint/ (udtraek og seed). Repoet er offentligt; brug roller eller
    pseudonymer (user12@example.invalid).
"""
import os
import re
import subprocess
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scrub_solution import INLINE_PATTERNS, scrub_text  # noqa: E402

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


# En hemmelighed tildelt i kode. Vaerdien skal vaere en lang, tegnsaets-
# agtig streng i anfoerselstegn; en henvisning ($env:X, @{parameters()})
# rammer ikke.
ASSIGN = re.compile(
    r"(?i)\b(client_?secret|api[-_]?key|x-apikey|password|pwd|token|sas)\w*"
    r"\s*(?:=|:)\s*[\"'][A-Za-z0-9+/=_\-~.]{16,}[\"']")

# Tekstformater, hvor navne-reglerne fra scrub_solution giver mening.
SCRUB_EXT = (".json", ".xml", ".md", ".yml", ".yaml", ".txt")

# Personlige firmaadresser. Kun i de mapper, hvor data og eksempler bor -
# ikke i kildekode, hvor domaenet kan staa i en kommentar.
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@orsted\.(?:com|dk)\b", re.I)
EMAIL_DIRS = ("schema/", "flow/", "html/", "docs/", "sharepoint/inspect/out/",
              "sharepoint/seed/")
# Faelles funktionspostkasser er ikke persondata. Brugerne skal kunne se
# dem (hjaelpeteksten, mailskabelonen), saa de maa staa.
SHARED_MAILBOXES = ("sapvedligehold@",)


def personal_emails(text):
    return [m.group(0) for m in EMAIL.finditer(text)
            if not m.group(0).lower().startswith(SHARED_MAILBOXES)]


def scan_bytes(data, name=""):
    """Navnene paa de moenstre, der rammer. Aldrig selve vaerdien."""
    text = data.decode("latin-1")
    labels = {label for rx, label in INLINE_PATTERNS if rx.search(text)}
    if ASSIGN.search(text):
        labels.add("tildeling af en hemmelighed")
    low = name.lower().replace("\\", "/")
    if low.endswith(SCRUB_EXT):
        _new, hits = scrub_text(text, name)
        labels.update(hits)
    if low.startswith(EMAIL_DIRS) and personal_emails(text):
        labels.add("personlig firmaadresse (offentligt repo)")
    return sorted(labels)


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
                    for label in scan_bytes(z.read(member), member):
                        hits.append((f"{rel} [{member}]", label))
        except zipfile.BadZipFile:
            pass
        return hits
    with open(path, "rb") as f:
        return [(rel, label) for label in scan_bytes(f.read(), rel)]


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
