# -*- coding: utf-8 -*-
"""
Tjek, som kun giver mening, naar flere apps er blevet til een.

Hver af de fem apps er efterproevet alene - men i een app deler de
navnerum. Det her fanger det, der gaar galt, naar de flyttes sammen:

  1. Et kontrolnavn findes kun een gang i HELE appen. Studio afviser
     ellers skaermen: "An entity with name 'X' already exists".
  2. Ingen formel refererer en kontrol paa en ANDEN skaerm. Det virker i
     Power Apps, men tvinger den anden skaerm til at blive indlaest, og
     med forsinket indlaesning kan vaerdien vaere blank.
  3. Et domaenes variabler og samlinger bruges kun paa dets egne
     skaerme. Deler Equipments og Materials en variabel, har
     omdoebningen fejlet, og de to formularer skriver i hinanden.
  4. Ingen skaerm starter en anden app. Domaenerne er skaerme her.
  5. Param("reqid") laeses kun dér, hvor skaermen klargoeres
     (build_screens.open_block). Alle andre steder er det domaenets egen
     variabel - Param() er det samme hele sessionen og for alle skaerme.
     Hubben og opslagsskaermene (combined.LOOKUPS) laeser den slet ikke.
  6. Hver variabel, der saettes med Set(), laeses ogsaa et sted i appen
     (App.pa.yaml og alle skaerme). App checker melder ellers
     UnusedVariables (issue #188: syv slettevariabler, der kun blev sat).
     Navnet skal blot forekomme uden for Set(navn, - en omtale i en
     kommentar taeller ogsaa, saa tjekket giver ingen falske fund.

Til sidst en optaelling af kontroller pr. skaerm.
"""
import os
import re
import sys

import yaml

import combined as cb

# Navne uden domaenepraefiks, der er FAELLES med vilje.
SHARED = {"gblFbOpen", "gblFbMe", "gblFbSel", "gblFbPick", "gblFbBusy", "gblFbAtt", "colFbRequests", "gblNavOpen", "colAppPrefs", "darkModeEnabled", cb.NEW_SEQ, "gblNavigating", "gblNavTo",
          # Skaermen, man kom fra, naar man aabner Issue Board (issue #114).
          "gblNavFrom"}
# Hubbens egne - de har aldrig haft et praefiks.
HUB_OWN = {"varMdMe", "varMdView", "varMdDomain", "varMdStatusMode", "varMdNewMenu", "varMdClosedPeek"}

TAGS = sorted({d["tag"] for d in cb.DOMAINS}, key=len, reverse=True)
TAGGED = re.compile(r"\b(?:var|col|gbl)(%s)(?=[A-Z0-9_])\w*" % "|".join(TAGS))
UNTAGGED = re.compile(r"\b(?:var|col|gbl)[A-Z]\w*")
WANT = re.compile(r"\b(?:gbl(?:%s)(?:Want|Stale)|var(?:%s)Opened)\b" % ("|".join(TAGS), "|".join(TAGS)))


def screens():
    out = {}
    for fn in sorted(os.listdir(cb.APP_DIR)):
        if fn.startswith("Screen") and fn.endswith(".pa.yaml"):
            doc = yaml.safe_load(open(os.path.join(cb.APP_DIR, fn), encoding="utf-8"))
            (name, body), = doc["Screens"].items()
            out[name] = body
    return out


def walk(children):
    for item in children or []:
        (name, body), = item.items()
        yield name, body
        yield from walk(body.get("Children"))


def formulas(body):
    """Alle Power Fx-udtryk paa skaermen: dens egne og kontrollernes."""
    for v in (body.get("Properties") or {}).values():
        if isinstance(v, str):
            yield v
    for _n, b in walk(body.get("Children")):
        for v in (b.get("Properties") or {}).values():
            if isinstance(v, str):
                yield v


def all_text():
    """Hver streng i App.pa.yaml og skaermene - formler, ogsaa Formulas."""
    def strings(o):
        if isinstance(o, dict):
            for v in o.values():
                yield from strings(v)
        elif isinstance(o, list):
            for v in o:
                yield from strings(v)
        elif isinstance(o, str):
            yield o
    out = []
    for fn in sorted(os.listdir(cb.APP_DIR)):
        if fn.endswith(".pa.yaml"):
            doc = yaml.safe_load(open(os.path.join(cb.APP_DIR, fn), encoding="utf-8"))
            out.extend(strings(doc))
    return "\n".join(out)


SET_VAR = re.compile(r"\bSet\(\s*([A-Za-z_]\w*)\s*,")


def unused_vars(text):
    """Variabler, der kun forekommer som Set(navn, ...) - aldrig laest."""
    out = []
    for v in sorted(set(SET_VAR.findall(text))):
        uses = len(re.findall(r"\b%s\b" % re.escape(v), text))
        sets = len(re.findall(r"\bSet\(\s*%s\s*," % re.escape(v), text))
        if uses == sets:
            out.append(v)
    return out


def domain_of(screen):
    for d in cb.DOMAINS:
        if d["screen"] == screen:
            return d
    raise SystemExit("Ukendt skaerm %s - hoerer den til et domaene i combined.DOMAINS?" % screen)


def main():
    scr = screens()
    expected = set(cb.SCREENS.values())
    problems = []
    if set(scr) != expected:
        problems.append("skaermene er %s, forventet %s" % (sorted(scr), sorted(expected)))

    # 1. unikke kontrolnavne
    where = {}
    for s, body in scr.items():
        for n, _b in walk(body.get("Children")):
            where.setdefault(n, []).append(s)
    for n, ss in sorted(where.items()):
        if len(ss) > 1:
            problems.append("[1] kontrolnavnet '%s' findes paa %s" % (n, ", ".join(ss)))

    # 2. referencer til en kontrol paa en anden skaerm
    ident = re.compile(r"\b[a-z]{2,5}[A-Z]\w*\b")
    for s, body in scr.items():
        foreign = set()
        for f in formulas(body):
            for m in ident.findall(f):
                if m in where and s not in where[m]:
                    foreign.add((m, where[m][0]))
        for m, other in sorted(foreign):
            problems.append("[2] %s refererer %s, som staar paa %s" % (s, m, other))

    # 3. variabler og samlinger hoerer til eet domaene
    for s, body in scr.items():
        d = domain_of(s)
        own = {d["tag"]}
        bad = set()
        for f in formulas(body):
            for m in TAGGED.finditer(f):
                tag, name = m.group(1), m.group(0)
                if tag in own:
                    continue
                # Hubben saetter hvert domaenes want - det er vejen ind - og
        # gbl<X>Stale, naar den har slettet noget, skaermen viser.
                if d["key"] == "hub" and WANT.fullmatch(name):
                    continue
                bad.add(name)
            for name in UNTAGGED.findall(f):
                if TAGGED.fullmatch(name) or name in SHARED:
                    continue
                if d["key"] == "hub" and name in HUB_OWN:
                    continue
                bad.add(name)
        for name in sorted(bad):
            problems.append("[3] %s bruger %s, som ikke hoerer til domaenet %s"
                            % (s, name, d["key"]))

    # 4. og 5.
    for s, body in scr.items():
        text = "\n".join(formulas(body))
        if "Launch(\"https://apps.powerapps.com" in text:
            problems.append("[4] %s starter en anden app med Launch()" % s)
        n = text.count('Param("reqid")')
        # Hubben og opslagsskaermene (KKS) aabner ingen anmodning.
        want = 0 if s in {cb.SCREENS[k] for k in ("hub", *cb.LOOKUPS)} else 1
        if n != want:
            problems.append('[5] %s laeser Param("reqid") %d gang(e), forventet %d'
                            % (s, n, want))

    # 6. variabler, der saettes, men aldrig laeses (App checker UnusedVariables)
    for v in unused_vars(all_text()):
        problems.append("[6] %s saettes med Set(), men laeses intet sted - App checker "
                        "melder UnusedVariables. Fjern Set-kaldet i byggeren" % v)

    total = 0
    print("Kontroller pr. skaerm:")
    for s, body in scr.items():
        c = sum(1 for _ in walk(body.get("Children")))
        total += c
        print("  %-26s %4d" % (s, c))
    print("  %-26s %4d" % ("I alt", total))
    if problems:
        print("\n%d problem(er) i den samlede app:\n" % len(problems))
        for p in problems:
            print("  " + p)
        return 1
    print("Samlet-tjek OK: unikke kontrolnavne, ingen referencer paa tvaers af "
          "skaerme, hvert domaenes variabler kun paa dets egne skaerme, "
          "ingen variabel, der kun saettes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
