# -*- coding: utf-8 -*-
"""
Alt, der er KKS-opslagets eget: navne, lister og de tre noegleomraader.

DATA LIGGER I SHAREPOINT, IKKE I APPEN
--------------------------------------
Den oprindelige app (powerapp-kks, haandbygget) havde de tre noegleomraader
som Table(...)-literaler i App.Formulas - 3.071 raekker, 440 KB formel.
Nu henter skaermen dem fra to lister, hvoraf den ene GENBRUGES:

    Funktionsnoegle   MD_KksFunctionKey  (ny, Provision-KksLists.ps1)
    Aggregatnoegle    MD_FLKey, KeyType = "Aggregate"   (Functional Location)
    Komponentnoegle   MD_FLKey, KeyType = "Component"   (Functional Location)

Hvorfor den ene genbruges og den anden ikke, staar i tools/gen_kks_seed.py.
Den tjekker ogsaa ved hver bygning, at MD_FLKey stadig ER KKS-vejledningens
raekker.
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools"))

# --- appen ------------------------------------------------------------
APP_KEY = "kks"
SCREEN = "ScreenKks"
TITLE = "KKS lookup"

# --- listerne, som de hedder naar de er tilfoejet som datakilder -------
# Power Fx binder paa VISNINGSNAVN: Title hedder Code i MD_KksFunctionKey
# og KeyValue i MD_FLKey.
L_FUNCTION = "MD_KksFunctionKey"
L_FLKEY = "MD_FLKey"

# --- noegleomraaderne ----------------------------------------------------
# (noegle, knaptekst, undertitel). Noeglen er vaerdien i varKksKey.
# Positionerne er KKS-noeglens - se docs/02-datamodel-sharepoint.md, MD_FLKey.
KEYS = [
    ("function", "Function key",
     "Function keys - KKS positions 7-9. Pick a letter, a group and a subgroup, or search."),
    ("aggregate", "Aggregate key",
     "Aggregate keys - KKS positions 12-13. Pick a letter, or search."),
    ("component", "Component key",
     "Component keys - KKS positions 18-19. Pick a letter, or search."),
]
# MD_FLKey.KeyType for de to genbrugte omraader.
FLKEY_TYPES = {"aggregate": "Aggregate", "component": "Component"}

# --- hentningen i bidder -----------------------------------------------
# En SharePoint-forespoergsel giver hoejst datagraensen (500 som standard)
# raekker. Funktionsnoeglerne hentes derfor i bidder efter SortNo - et
# indekseret tal, saa hver bid kan delegeres. (Ikke "SortOrder": det navn
# er ogsaa Power Fx' enum, og i et Filter uden kvalifikation er det
# tvetydigt.) Antallet regnes af seedet, plus een bid uden oevre graense:
# vokser listen med op til CHUNK raekker, kommer de stadig med uden en ny
# bygning.
CHUNK = 500
SEED_CSV = os.path.join(ROOT, "sharepoint", "seed", "MD_KksFunctionKey.csv")


def seed_rows():
    with open(SEED_CSV, encoding="utf-8-sig", newline="") as f:
        return sum(1 for _ in csv.DictReader(f))


def chunk_count():
    n = seed_rows()
    if n == 0:
        raise SystemExit("%s er tom - koer python3 tools/gen_kks_seed.py" % SEED_CSV)
    return -(-n // CHUNK) + 1
