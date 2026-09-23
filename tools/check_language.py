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
    r"maks|hoejst|mindst|nedenfor|paakraevet)\b|[ÆØÅæøå])",
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
}

# Ting, der ikke er saetninger: farver, tal, egenskabsnavne, URL'er.
SKIP = re.compile(r"^(#|RGBA|Font\.|https?:|[A-Za-z]+\.[A-Za-z]|@odata|[\d\s,.:;/|<>_-]+$)")


def screens():
    out = []
    for d in sorted(os.listdir(ROOT)):
        p = os.path.join(ROOT, d)
        if not os.path.isdir(p):
            continue
        for f in sorted(os.listdir(p)):
            if f.endswith(".pa.yaml") and not f.startswith("_"):
                out.append(os.path.join(p, f))
    return out


def check():
    bad = []
    n_files = 0
    for path in screens():
        n_files += 1
        txt = io.open(path, encoding="utf-8").read()
        for m in re.finditer(r'"((?:[^"\\]|"")*)"', txt):
            v = m.group(1).strip()
            if len(v) < 3 or v in ALLOW or SKIP.match(v):
                continue
            words = re.findall(r"[A-Za-zÆØÅæøå]+", v)
            single = (len(words) <= 3
                      and any(w.lower() in SINGLE for w in words))
            if not DANISH.search(v) and not single:
                continue
            # En VAERDI, ikke en visning: { Value: "..." } eller en
            # Switch-noegle. Begge skrives i en liste og er ikke sprog.
            before = txt[max(0, m.start() - 40):m.start()]
            if re.search(r"Value:\s*$", before):
                continue
            bad.append("  %-24s %s" % (os.path.basename(os.path.dirname(path)), v[:90]))
    if bad:
        raise SystemExit(
            "Sprogtjek: %d dansk(e) streng(e) paa skaermene.\n" % len(bad)
            + "\n".join(sorted(set(bad))) +
            "\n\nAppernes sprog er engelsk. Er strengen en LAGRET vaerdi - en\n"
            "SharePoint-valgvaerdi eller en Switch-noegle - saa skal den ikke\n"
            "oversaettes; skriv den i ALLOW i tools/check_language.py i stedet.")
    print("Sprogtjek: %d skaerm(e), ingen dansk visningstekst." % n_files)


if __name__ == "__main__":
    check()
