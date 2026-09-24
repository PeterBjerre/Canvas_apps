# -*- coding: utf-8 -*-
"""
Efter et deploy: er det, der ligger i Studio, det samme TRAE som det, vi
byggede?

HVORFOR DEN HER FIL FINDES
--------------------------
Driftrapporten i canvas_mcp.py sammenlignede serverens YAML med den byggede
LINJE FOR LINJE og kaldte hele forskellen "normalisering". Power Apps
fjerner egenskaber, den regner for standardvaerdier, og skriver formatet om
- saa forskellen var altid tusindvis af linjer, og en rigtig fejl druknede
i den.

Og der VAR en rigtig fejl. Da listekortet i Equipment blev flyttet fra en
halv spalte op i kroppen, og bjaelkens knapper ud af deres indlejrede
gruppe, stod de i Studio i en anden raekkefoelge end i den byggede YAML -
indsend-kortet over listen, knapperne i bjaelken byttet rundt - og listens
raekker havde mistet deres bredde. Den byggede fil var rigtig; Studio var
det ikke. Rapporten sagde "normalisering - ikke fejl".

Her sammenlignes TRAEET i stedet:

  1. Findes de samme kontroller begge steder?
  2. Har hver kontrol den samme foraelder?
  3. Staar soeskende i den samme raekkefoelge?
  4. Har en egenskab, begge sider har, den samme VAERDI?

En egenskab, serveren har fjernet, er normalisering og taelles ikke. En
egenskab, serveren har med en ANDEN vaerdi, er en fejl.

    python3 tools/deploy_verify.py <bygget.pa.yaml> <server.pa.yaml>
"""
import re
import sys

import yaml


def _norm_value(v):
    s = str(v).strip()
    if s.startswith("="):
        s = s[1:]
    return re.sub(r"\s+", "", s)


def _control(c):
    return re.sub(r"@.*$", "", str(c or ""))


def tree(path):
    """navn -> (foraelder, plads blandt soeskende, kontroltype, egenskaber),
    og foraelder -> boernenes navne i raekkefoelge."""
    doc = yaml.safe_load(open(path, encoding="utf-8")) or {}
    nodes, kids = {}, {}

    def walk(items, parent):
        names = []
        for i, item in enumerate(items or []):
            (name, body), = item.items()
            body = body or {}
            names.append(name)
            nodes[name] = (parent, i, _control(body.get("Control")),
                           body.get("Properties") or {})
            walk(body.get("Children"), name)
        kids[parent] = names

    for sname, screen in (doc.get("Screens") or {}).items():
        walk((screen or {}).get("Children"), sname)
    return nodes, kids


def compare(built_path, server_path, limit=40):
    """Liste af fund. Tom liste = Studio har praecis det byggede trae."""
    a, ak = tree(built_path)
    b, bk = tree(server_path)
    found = []
    for n in sorted(set(a) - set(b)):
        found.append("mangler i Studio: %s (under %s)" % (n, a[n][0]))
    for n in sorted(set(b) - set(a)):
        found.append("findes KUN i Studio: %s (under %s)" % (n, b[n][0]))
    for n in sorted(set(a) & set(b)):
        if a[n][0] != b[n][0]:
            found.append("%s: foraelder %s i Studio, %s i det byggede"
                         % (n, b[n][0], a[n][0]))
    for parent in sorted(set(ak) & set(bk)):
        mine = [x for x in ak[parent] if x in b]
        theirs = [x for x in bk[parent] if x in a]
        if mine != theirs and sorted(mine) == sorted(theirs):
            found.append("%s: boernene staar i en anden raekkefoelge i Studio\n"
                         "        bygget: %s\n        Studio: %s"
                         % (parent, ", ".join(mine), ", ".join(theirs)))
    for n in sorted(set(a) & set(b)):
        pa, pb = a[n][3], b[n][3]
        # STUDIO EJER SKABELONENS STOERRELSE.
        #
        # Et galleris oeverste barn faar sin bredde af Studio, uanset hvad
        # vi skriver. Aflaest i egenskabspanelet stod der foerst 320 og
        # siden Parent.Width - aldrig builderens udtryk. Det er ikke en
        # fejl, og det maa ikke stoppe et deploy. Cellerne INDE i raekken
        # maales i stedet mod et budget med luft (GALLERY_RESERVE).
        in_gallery = a.get(a[n][0], (None, 0, "", {}))[2] == "Gallery"
        for key in sorted(set(pa) & set(pb)):
            if in_gallery and key in ("Width", "Height"):
                continue
            if _norm_value(pa[key]) != _norm_value(pb[key]):
                found.append("%s.%s: Studio har en anden vaerdi\n"
                             "        bygget: %s\n        Studio: %s"
                             % (n, key, str(pa[key]).strip()[:120],
                                str(pb[key]).strip()[:120]))
    return found[:limit] + (["... og %d mere" % (len(found) - limit)]
                            if len(found) > limit else [])


def blank_screen(built_path, out_path):
    """Skaermen UDEN boern og uden egenskaber, der kunne naevne dem.

    Bruges af 'deploy --clean': foerst sendes den tomme skaerm, saa alle
    kontroller fjernes i Studio, og derefter den rigtige - saa bygges hele
    traeet paa ny i den raekkefoelge, der staar i filen, i stedet for at
    flytte rundt paa det gamle."""
    doc = yaml.safe_load(open(built_path, encoding="utf-8"))
    lines = ["Screens:"]
    for sname, screen in doc["Screens"].items():
        fill = (screen.get("Properties") or {}).get("Fill")
        lines.append("  %s:" % sname)
        if fill:
            lines.append("    Properties:")
            lines.append("      Fill: |-")
            lines.append("          =%s" % str(fill).strip().lstrip("="))
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    res = compare(sys.argv[1], sys.argv[2])
    for r in res:
        print("  " + r)
    print("Samme trae." if not res else "%d fund." % len(res))
    sys.exit(1 if res else 0)
