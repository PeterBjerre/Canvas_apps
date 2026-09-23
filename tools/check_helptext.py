# -*- coding: utf-8 -*-
"""
EEN kilde pr. hjaelpetekst.

HVORFOR
-------
Hjaelpeteksterne bor nu to steder, og det er med vilje:

    MD_HelpText     ren tekst. Rettes af dem, der kender fagligheden.
    build_help.py   de syv DYNAMISKE hints. De er Power Fx og saetter
                    appens egne vaerdier ind i beskeden.

Delingen er kun sund, saa laenge en noegle staar PRAECIS eet af stederne.
Staar "PlanText" begge steder, vinder koden - og den, der retter raekken i
SharePoint, ser ingen forskel i appen. Det er den vaerste slags fejl: den
ligner en tilfaeldighed og bliver ikke meldt af nogen.

Tjekket laeser HINTS-noeglerne ud af build_help.py og holder dem op mod
seedet, sharepoint/seed/MD_HelpText.csv.

HVAD DET IKKE KAN
-----------------
Seedet er det, listen blev fyldt med - ikke det, den indeholder NU.
Opretter nogen en raekke med noeglen "PlanText" direkte i SharePoint,
opdager tjekket det ikke. Det kraever et opslag mod listen, og byggeriet
laeser ikke SharePoint. Prisen er kendt; alternativet var ingen vagt.
"""
import ast
import csv
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HELP = os.path.join(ROOT, "Maintenance Plan App", "build", "build_help.py")
SEED = os.path.join(ROOT, "sharepoint", "seed", "MD_HelpText.csv")


def code_keys():
    """Noeglerne i HINTS - dem, koden stadig svarer paa."""
    tree = ast.parse(io.open(HELP, encoding="utf-8").read())
    for node in tree.body:
        if (isinstance(node, ast.Assign)
                and getattr(node.targets[0], "id", "") == "HINTS"):
            return {k.value for k in node.value.keys}
    return set()


def seed_rows():
    if not os.path.exists(SEED):
        return []
    with io.open(SEED, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def check():
    code = code_keys()
    rows = seed_rows()
    seed_hints = {r["HelpKey"] for r in rows if r.get("Kind") == "Hint"}
    both = sorted(code & seed_hints)
    if both:
        raise SystemExit(
            "Hjaelpetekst: %d noegle(r) staar BAADE i koden og i listen.\n"
            % len(both)
            + "\n".join("  %s" % k for k in both) +
            "\n\nKoden vinder, saa den, der retter raekken i SharePoint, ser\n"
            "ingen forskel i appen. Vaelg eet sted:\n"
            "  dynamisk (Power Fx) -> bliv i build_help.HINTS, slet raekken\n"
            "  ren tekst           -> slet den fra HINTS, behold raekken")

    # Den anden vej: en statisk hint, der er faldet ud af BEGGE. Den ville
    # ikke braekke noget - feltet viser bare ingenting - og det er netop
    # derfor, den skal siges hoejt.
    if rows:
        print("Hjaelpetekst-tjek: %d dynamisk(e) i koden, %d raekke(r) i seedet, "
              "ingen overlappende noegler." % (len(code), len(rows)))
    else:
        print("Hjaelpetekst-tjek: intet seed (%s). Koer "
              "tools/gen_helptext_seed.py." % os.path.relpath(SEED, ROOT))


if __name__ == "__main__":
    check()
