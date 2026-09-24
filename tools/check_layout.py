# -*- coding: utf-8 -*-
"""
Layout-tjek af ScreenVhPlan.pa.yaml.

Canvas-layout kan ikke koeres her, saa i stedet regnes hoejderne efter.
Tjekket foretager fire kontroller:

  1. Ingen Height-formel maa referere en ANDEN kontrols .Height.
     Det var rodaarsagen: i en AutoLayout-container saetter forelderen
     boernenes stoerrelse, saa naar forelderen laeser barnets .Height,
     laeser den sin egen udregning tilbage. Resultatet var enten en
     formelfejl (der faldt tilbage til IfError-konstanten) eller den
     kaskade-vaekst, hvor containerne voksede for hver genberegning.

  2. Hver lodret container skal vaere hoej nok til sine boern plus gaps
     plus sin egen polstring. Det er her hvert kort var 36 px for lavt,
     fordi padding ikke var talt med.

  3. Hver vandret container skal vaere hoej nok til sit hoejeste barn.

  4. Faste bredder i en vandret raekke maa ikke overstige raekkens bredde
  4c. Hver wrap-raekke SPILLES: boernene pakkes i linjer, som autolayout
     goer det, i den bredde containeren faktisk faar - med scrollbaren
     trukket fra. Hoejden skal rumme de linjer, der kommer ud af det
  4d. En raekke, der skifter retning, skal passe i sin vandrette tilstand
  24. Parent.Width maa ikke indgaa i et regnestykke - den er foraelderens
     Width-EGENSKAB, ikke pladsen inden i den
  25. En knap er mindst 30 px hoej
  26. Ingen Parent.Template* - og en gallerirakke skal rumme sine celler
  27. En tekst er mindst 1,5 x sin skriftstoerrelse hoej
  28. Ingen FillPortions i en vandret raekke, der ikke ombryder
  29. Listens overskrift og dens raekke har de samme kolonnebredder
  23. Rammen: con<X>Root -> header med fast hoejde + een krop, der
     scroller. Headerens hoejde maa ikke afhaenge af data, og padding +
     scrollbar + luft skal vaere mindst SHELL_INSET. Se
     docs/30-responsivt-layout.md
  8. Enhver samling, skaermen bruger, findes i App.pa.yaml - som navngiven
     formel eller som ClearCollect
  8b. Enhver designtoken, skaermen bruger, findes i temaformlen C. En
     token, der ikke findes, giver BLANK - og blank er gennemsigtig, saa
     kontrollen ville forsvinde uden en fejlmeddelelse
  8c. Ingen formel sammenligner App.Width med et tal. Braekpunkter staar i
     tools/layout_tokens.py og laeses som LayoutRank/LayoutContext
  18. Enhver Gallery har TabIndex. Uden den er den ikke et tab stop, og
     App checker melder det foerst ved deploy
  19. Ingen AccessibleLabel er kontrollens eget navn - en skaermlaeser
     ville laese "inpManufacturer" op i stedet for "Fabrikat"
  20. ADVARSEL: flere uafhaengige hentninger i kaede boer samles i
     Concurrent() - uden den venter appen paa summen i stedet for paa
     det laengste kald
  9. Ingen LODRET container har et barn med FillPortions <> 0
     (knapraekken var 336 px bred i et kort med 324 px indhold, ombroed til
     to linjer og fik sin sidste knap klippet af).

Hoejdeudtrykkene evalueres for flere skaermbredder og datamaengder -
bredderne kommer fra braekpunkterne i tools/layout_tokens.py, saa
baade graensen og pixlen under den bliver proevet.

    python3 check_layout.py            # finder skaermen selv
    python3 check_layout.py ../ScreenVhPlan.pa.yaml
"""
import os, re, sys, yaml

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "tools"))
import layout_tokens as lay

# Skaermen findes af sig selv, saa denne fil er ordret ens i alle apps i
# repoet (se .github/skills/canvas-build/SKILL.md). Er der mere end een
# skaerm, angives den paa kommandolinjen.
def _find_screen():
    """Skaermen findes ud af HVOR TJEKKET KOERES FRA, ikke ud af hvor filen
    ligger.

    Foer laa en kopi af den her fil i hver app's build-mappe, saa HERE var
    app'ens egen mappe. Nu ligger den i tools/ - een udgave for alle fire -
    og HERE ville pege paa tools/. Arbejdsmappen er app'ens build-mappe,
    baade naar tools/build_all.py koerer den (cwd=build) og naar nogen selv
    goer det."""
    if len(sys.argv) > 1:
        return sys.argv[1]
    app_dir = os.path.join(os.getcwd(), "..")
    found = sorted(f for f in os.listdir(app_dir)
                   if f.startswith("Screen") and f.endswith(".pa.yaml"))
    if len(found) == 1:
        return os.path.join(app_dir, found[0])
    raise SystemExit(
        "Angiv skaermen: python3 check_layout.py ../<Screen>.pa.yaml\n"
        "Fundet: " + (", ".join(found) or "ingen"))




# BREDDERNE KOMMER FRA BRAEKPUNKTERNE, IKKE FRA EN HAANDPLUKKET LISTE.
#
# Her stod [420, 640, 900, 1024, 1366, 1920]. Den sprang henover 1023 -
# altsaa pixlen lige foer layoutet skifter - og det er praecis dér,
# layoutfejl bor: en container, der er hoej nok paa 1024 og tolv pixels
# for lav paa 1023, var usynlig for tjekket.
#
# lay.test_widths() giver hver graense OG pixlen under den.
WIDTHS = lay.test_widths()
ITEM_COUNTS = [0, 1, 3, 8]
OP_COUNTS = [0, 1, 4, 12]
PKG_COUNTS = [3, 4]

CTRL_HEIGHT_REF = re.compile(r"\b(?:con|gal|txt|btn|drp|num|chk)[A-Za-z0-9_]*\.Height\b")


def _if(c, a, b):
    return a if c else b


def _iferror(a, b):
    return a


def _balanced(expr, start):
    """Slutindekset paa den parentes, der aabner ved 'start'."""
    depth, i, in_str = 0, start, False
    while i < len(expr):
        c = expr[i]
        if c == '"':
            in_str = not in_str
        elif not in_str:
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    return i
        i += 1
    return -1


def _sub_countrows(e, n):
    """Erstat ETHVERT CountRows(...) med et proevetal.

    Her stod foer tre erstatninger paa ORDRET tekst - og de tre var
    VH-plans. Enhver anden apps CountRows overlevede, udtrykket indeholdt
    dermed et navn, tjekket ikke kendte, og hele hoejden blev sprunget over
    med et tavst "kan ikke". Det var derfor Equipment og Material havde
    deres skal og alle fire kort uefterregnet.

    Hvad der staar INDE i CountRows er tjekket uvedkommende: det er data,
    ikke hoejdealgebra. Filtret kan indeholde Trim, Coalesce, StartsWith,
    SortByColumns - det aendrer ikke, at resultatet er et tal, og at
    hoejden skal passe for baade 0 og mange raekker."""
    out, i = [], 0
    while True:
        j = e.find("CountRows(", i)
        if j < 0:
            out.append(e[i:])
            return "".join(out)
        k = _balanced(e, j + len("CountRows"))
        if k < 0:
            out.append(e[i:])
            return "".join(out)
        out.append(e[i:j])
        out.append(str(n))
        i = k + 1


def _isblank(x):
    """Alt, tjekket har sat ind, ER noget. En variabel er erstattet med
    True, et CountRows med et tal - saa svaret er altid nej."""
    return False


# DET, evaluate KAN REGNE PAA - EEN liste, brugt begge steder.
#
# Her stod to vagter med hver sin haandskrevne opremsning: een der
# afviste ukendte FUNKTIONSKALD og een der afviste ukendte NAVNE. Begge
# naevnte "max" med lille og ingen af dem "Max" med stort - som er den,
# Power Fx skriver, og den row_height() saetter i hver eneste vandrette
# containers hoejde. Resultatet var, at 48 hoejder blev sprunget over med
# et tavst "kan ikke", fordi vagten ikke kendte sin egen regnemaskine.
#
# Naar de to vagter deler een liste, kan de ikke laengere vaere uenige.
KNOWN = ("_if", "_iferror", "_isblank", "_coalesce", "max", "Max", "min", "Min")
_KNOWN_RE = "|".join(KNOWN)


def _coalesce(*a):
    for x in a:
        if x not in (None, False, ""):
            return x
    return a[-1] if a else None


def evaluate(expr, w, n_items, n_ops, n_pkgs):
    """Evaluer et genereret hoejdeudtryk. Returnerer None hvis udtrykket
    indeholder noget, tjekket ikke kan regne paa (fx Parent.TemplateHeight
    inde i en gallery-skabelon)."""
    if expr is None:
        return None
    e = expr.strip()
    if e.startswith("="):
        e = e[1:]
    if "Parent." in e or "Self." in e:
        return None

    # De tre specifikke erstatninger her var VH-plans egne, paa ORDRET
    # tekst. _sub_countrows tager dem alle - ogsaa de tre andre apps'.
    e = _sub_countrows(e, max(n_items, n_ops, n_pkgs))
    # IsEmpty(...) -> sand: ugunstigste tilfaelde, "tom"-beskeden vises.
    # Hvad der staar inde i den, er data og ikke hoejdealgebra - samme
    # begrundelse som for CountRows.
    while "IsEmpty(" in e:
        j = e.find("IsEmpty(")
        k = _balanced(e, j + len("IsEmpty"))
        if k < 0:
            break
        e = e[:j] + "True" + e[k + 1:]
    # LayoutContext og LayoutRank er NAVNGIVNE FORMLER i App.pa.yaml, ikke
    # tal i udtrykket. Uden de to linjer kunne tjekket ikke regne paa en
    # eneste hoejde, der afhaenger af et braekpunkt - altsaa netop dem, der
    # skifter. De blev alle 15 sprunget over med et tavst "kan ikke".
    e = re.sub(r'LayoutContext\s*=\s*"(\w+)"',
               lambda m: "True" if m.group(1) == lay.tier_for(w) else "False", e)
    e = re.sub(r"\bLayoutRank\b", str(lay.rank_for(w)), e)

    e = e.replace("App.Width", str(w)).replace("App.Height", "900")

    # Booleske testvaerdier: det ugunstigste tilfaelde er at alt er synligt.
    e = re.sub(r"varVhpPlan\.PlanType\s*=\s*\"Strategy\"", "True", e)
    e = re.sub(r"IsBlank\(varVhpPlan\.Strategy\)", "False", e)
    e = re.sub(r"IsBlank\(varVhpActiveItemId\)", "False", e)
    e = re.sub(r"\bvarVhp[A-Za-z0-9_]*\b", "True", e)
    # ALLE APPS' VARIABLER, IKKE KUN VH-PLANS.
    #
    # Her stod kun varVhp*. En hoejde med varDom* eller gbl* kunne derfor
    # ikke regnes ud, og blev sprunget over med et tavst "kan ikke". Det
    # skjulte, at conDomSplit i Equipment og Material kun havde hoejde til
    # EEN linje, mens listen og dokumentruden stod under hinanden paa
    # enhver skaerm under 1600 px - hele dokumentruden, knapperne med, var
    # klippet vaek.
    #
    # Samme regel som for varVhp*: ugunstigste tilfaelde. "Er den blank?"
    # svares nej, saa det, der kun vises for en valgt raekke, ER vist.
    e = re.sub(r"IsBlank\(\s*(?:var|gbl)[A-Z][\w.]*\s*\)", "False", e)
    e = re.sub(r"\b(?:var|gbl)[A-Z]\w*(?:\.\w+)*", "True", e)

    # IsBlank og Coalesce staar i de betingelser, hoejderne haenger paa.
    # De maa erstattes FOER If, ellers bliver "IsBlank(" til "Is_if("...
    e = e.replace("IsBlank(", "_isblank(").replace("Coalesce(", "_coalesce(")
    e = e.replace("IfError(", "_iferror(").replace("If(", "_if(")
    e = e.replace("&&", " and ").replace("||", " or ")
    e = e.replace("<>", "!=")
    e = re.sub(r"!(?!=)", " not ", e)
    e = re.sub(r"\btrue\b", "True", e)
    e = re.sub(r"\bfalse\b", "False", e)
    e = re.sub(r"(?<![<>!=])=(?!=)", "==", e)

    # Et funktionskald, tjekket ikke kender, kan det ikke regne paa.
    # Tekst i anfoerselstegn er data, ikke navne - "submitted" er ikke en
    # ukendt variabel.
    stripped = re.sub(r'"[^"]*"', '""', e)
    for fn in KNOWN:
        stripped = stripped.replace(fn + "(", "")
    if re.search(r"[A-Za-z_][A-Za-z0-9_.]*\s*\(", stripped):
        return None
    # HVIDLISTEN SKAL NAEVNE Max MED STORT.
    #
    # Her stod kun "max". Power Fx skriver Max(), og row_height() saetter
    # den i hver eneste vandrette containers hoejde. Vagten saa derfor et
    # "ukendt navn" i 41 af de 81 hoejder, den sprang over - og det var
    # ikke data den ikke kunne regne paa, det var dens egen hvidliste.
    if re.search(r"\b(?!True|False|and|or|not|" + _KNOWN_RE + r")"
                 r"[A-Za-z_][A-Za-z0-9_.]*", stripped):
        return None
    try:
        return float(eval(e, {"__builtins__": {}},
                          {"_if": _if, "_iferror": _iferror,
                           "max": max, "Max": max,
                           "min": min, "Min": min,
                           "_isblank": _isblank, "_coalesce": _coalesce,
                           "True": True, "False": False}))
    except Exception:
        return None


def _enum_state(expr, w, true_word, false_word):
    """En LayoutDirection eller LayoutAlignItems, der kan vaere en FORMEL.

    flow_row() skifter retning efter bredden:
        If(<passer>, LayoutDirection.Horizontal, LayoutDirection.Vertical)
    Tjekket skal derfor spoerge ved HVER bredde, hvilken af de to det er.
    Her stod "Vertical" in tekst - og en formel indeholder begge ord.
    Returnerer True/False, eller None hvis det ikke kan afgoeres."""
    e = (expr or "").strip()
    if e.startswith("="):
        e = e[1:].strip()
    if not e:
        return None
    if "If(" not in e:
        return true_word in e
    e = re.sub(r"\b(?:LayoutDirection|LayoutAlignItems)\.%s\b" % true_word, "1", e)
    e = re.sub(r"\b(?:LayoutDirection|LayoutAlignItems)\.\w+", "0", e)
    v = evaluate(e, w, 0, 0, 3)
    return None if v is None else bool(v)


def is_vertical(props, w):
    v = _enum_state(props.get("LayoutDirection"), w, "Vertical", "Horizontal")
    return bool(v)


def is_stretch(props, w):
    v = _enum_state(props.get("LayoutAlignItems"), w, "Stretch", "")
    return bool(v)


def collect(nodes, path="", out=None):
    out = [] if out is None else out
    for item in nodes or []:
        (name, body), = item.items()
        p = f"{path}/{name}"
        out.append((p, name, body))
        collect(body.get("Children"), p, out)
    return out


def main():
    SCREEN = _find_screen()
    doc = yaml.safe_load(open(SCREEN, encoding="utf-8"))
    screen = list(doc["Screens"].values())[0]
    all_nodes = collect(screen["Children"])
    problems = []

    # --- 1. Ingen kontrol-til-kontrol hoejdereferencer ---------------------
    for p, name, body in all_nodes:
        h = (body.get("Properties") or {}).get("Height")
        if h and CTRL_HEIGHT_REF.search(h):
            problems.append(f"[1] {name}: Height refererer en anden kontrols .Height -> {h[:90]}")

    # --- 2/3. Hoejde vs. indhold ------------------------------------------
    for p, name, body in all_nodes:
        props = body.get("Properties") or {}
        kids = body.get("Children") or []
        if body.get("Control") != "GroupContainer" or not kids:
            continue
        gap = float(re.sub(r"[^0-9.]", "", props.get("LayoutGap", "=8")) or 8)
        pt = float(re.sub(r"[^0-9.]", "", props.get("PaddingTop", "=0")) or 0)
        pb = float(re.sub(r"[^0-9.]", "", props.get("PaddingBottom", "=0")) or 0)

        # Et barn med Visible = false udelades af AutoLayout - det fylder
        # hverken hoejde eller gap. Det skal taelles paa samme maade her, som
        # gen_screen.stack_height goer, ellers ville en skjult hjaelpekontrol
        # (fx den usynlige soege-timer) blive rapporteret som overloeb.
        # Kun det LITTERALE "false" springes over; en Visible-FORMEL kan jo
        # vaere sand, og saa skal pladsen vaere der.
        kids = [k for k in kids
                if ((list(k.values())[0].get("Properties") or {})
                    .get("Visible", "").strip() not in ("=false", "= false"))]
        if not kids:
            continue

        for w in WIDTHS:
            vertical = is_vertical(props, w)
            for ni in ITEM_COUNTS:
                for no in OP_COUNTS:
                    for npk in PKG_COUNTS:
                        own = evaluate(props.get("Height"), w, ni, no, npk)
                        if own is None:
                            continue
                        kid_h = []
                        ok = True
                        for k in kids:
                            (kn, kb), = k.items()
                            kprops = kb.get("Properties") or {}
                            # ER BARNET SYNLIGT I NETOP DETTE TILFAELDE?
                            #
                            # gen_screen.stack_height skriver forelderens
                            # hoejde som "If(betingelse, gap + h, 0)" - altsaa
                            # kun naar barnet vises. Taeller tjekket barnet
                            # med ALTID, sammenligner det forelderens
                            # betingede hoejde med et ubetinget indhold, og
                            # melder overloeb der ikke findes.
                            #
                            # Det var skjult, saa laenge hoejderne ikke kunne
                            # regnes ud. Da de kunne, gav det seks fund i tre
                            # apps - alle falske, alle paa den tomme-liste-
                            # besked, der netop KUN vises naar listen er tom.
                            #
                            # Kan betingelsen ikke regnes ud, taelles barnet
                            # med som foer: hellere et fund for meget end en
                            # container, der klipper sit indhold.
                            vis = kprops.get("Visible")
                            if vis is not None:
                                shown = evaluate(vis, w, ni, no, npk)
                                if shown is not None and not shown:
                                    continue
                            kh = evaluate(kprops.get("Height"), w, ni, no, npk)
                            if kh is None:
                                ok = False
                                break
                            kid_h.append(kh)
                        if not ok or not kid_h:
                            continue
                        need = (sum(kid_h) + gap * (len(kid_h) - 1) if vertical else max(kid_h)) + pt + pb
                        if own + 0.01 < need:
                            problems.append(
                                f"[{2 if vertical else 3}] {name}: hoejde {own:.0f} < indhold {need:.0f} "
                                f"(App.Width={w}, items={ni}, ops={no}, pkgs={npk})")
                            break
                    else:
                        continue
                    break
                else:
                    continue
                break
            else:
                continue
            break

    # Stien -> kontrollen. Regel 4 bruger den til at slaa Parent.Width op.
    by_path = {pp: bb for pp, _nn, bb in all_nodes}

    def avail_width(path, w, ni, no, npk, depth=0):
        """Den bredde en kontrol FAKTISK har, med Parent.Width slaaet op.

        evaluate() giver None paa Parent.*, fordi den ikke kan vide hvad
        foraelderen er. Her VED vi det - stien siger det. Uden det kunne
        regel 4 ikke regne paa en eneste raekke i en autolayout-container:
        de bruger alle Parent.Width, og det var netop derfor bjaelken i de
        to domaeneapper kunne vaere 10 px for bred i maanedsvis."""
        if depth > 20:
            return None
        body = by_path.get(path)
        if body is None:
            return None
        props = body.get("Properties") or {}
        e = (props.get("Width") or "").strip()
        if e.startswith("="):
            e = e[1:].strip()
        if e != "Parent.Width":
            return evaluate(props.get("Width"), w, ni, no, npk)
        parent = path.rsplit("/", 1)[0]
        if not parent:                      # barn af skaermen selv
            return float(w)
        pw = avail_width(parent, w, ni, no, npk, depth + 1)
        if pw is None:
            return None
        pp_ = by_path[parent].get("Properties") or {}
        pad = 0.0
        for k in ("PaddingLeft", "PaddingRight"):
            v = evaluate(pp_.get(k), w, ni, no, npk)
            pad += float(v or 0)
        return pw - pad

    # DEN BREDDE, PLATFORMEN FAKTISK GIVER - med scrollbaren trukket fra.
    #
    # avail_width() ovenfor stoler paa, at en kontrols Width er det, den
    # tegnes med. Det passer ikke i to tilfaelde, og begge ramte:
    #
    #   1. En LODRET container med Stretch saetter selv boernenes bredde
    #      til sin egen indre bredde. Barnets Width-formel ignoreres.
    #   2. En container med LayoutOverflowY = Scroll bruger bredden til
    #      scrollbaren, naar indholdet er hoejere end den - og det er det
    #      altid i de fire apps. Paa Windows er den ~17 px bred. Paa en Mac
    #      ligger den OVEN PAA indholdet og koster ingenting.
    #
    # Nummer 2 er grunden til, at fejlen saa ud som "hit and miss": den
    # samme skaerm var hel paa een maskine og klippet paa en anden.
    # Tjekket regner derfor altid med den UGUNSTIGE side - scrollbaren
    # tager plads.
    def _num(v, w, ni, no, npk):
        x = evaluate(v, w, ni, no, npk)
        return float(x or 0)

    def real_width(path, w, ni, no, npk, depth=0):
        if depth > 30:
            return None
        body = by_path.get(path)
        if body is None:
            return None
        props = body.get("Properties") or {}
        parent = path.rsplit("/", 1)[0]
        if not parent:
            e = (props.get("Width") or "").replace("Parent.Width", str(w))
            return evaluate(e, w, ni, no, npk)
        pb = by_path[parent]
        if pb.get("Control") == "Gallery":
            return None
        pp_ = pb.get("Properties") or {}
        pw = real_width(parent, w, ni, no, npk, depth + 1)
        if pw is None:
            return None
        inner = (pw - _num(pp_.get("PaddingLeft"), w, ni, no, npk)
                 - _num(pp_.get("PaddingRight"), w, ni, no, npk))
        if (pp_.get("LayoutOverflowY") or "").strip() == "=LayoutOverflow.Scroll":
            inner -= lay.SCROLLBAR_W
        vertical = is_vertical(pp_, w)
        stretch = is_stretch(pp_, w)
        own_align = (props.get("AlignInContainer") or "")
        if vertical and stretch and not re.search(r"\.(Start|Center|End)\b", own_align):
            return inner
        if (not vertical) and (evaluate(props.get("FillPortions"), w, ni, no, npk) or 0) > 0:
            return None     # platformen fordeler resten - ikke et tal her
        # Parent.Width er FORAELDERENS WIDTH-EGENSKAB, ikke pladsen inden i
        # den. Her stod pladsen inden i den - og saa kunne tjekket ikke se,
        # at "Parent.Width - 545" i topbjaelken var 57 px for bredt.
        pwp = prop_width(parent, w, ni, no, npk)
        if pwp is None and "Parent.Width" in (props.get("Width") or ""):
            return None
        e = (props.get("Width") or "").replace("Parent.Width", "(%s)" % pwp)
        return evaluate(e, w, ni, no, npk)

    def prop_width(path, w, ni, no, npk, depth=0):
        """Vaerdien af en kontrols Width-EGENSKAB - det, Parent.Width i et
        barn svarer. Den er IKKE traekket fri af padding eller scrollbar."""
        if depth > 30:
            return None
        body = by_path.get(path)
        if body is None:
            return None
        e = (body.get("Properties") or {}).get("Width") or ""
        parent = path.rsplit("/", 1)[0]
        if "Parent.Width" in e:
            pv = float(w) if not parent else prop_width(parent, w, ni, no, npk, depth + 1)
            if pv is None:
                return None
            e = e.replace("Parent.Width", "(%s)" % pv)
        return evaluate(e, w, ni, no, npk)

    # --- 4c. Ombrydningen, som platformen faktisk laver den --------------
    #
    # Regel 4 og 4b ser paa formlerne. Den her SPILLER layoutet: for hver
    # wrap-raekke, ved hver testbredde, pakkes boernene i raekker paa
    # samme maade som autolayout goer det - fra venstre, ny linje naar
    # det naeste barn ikke kan vaere der - i den bredde, containeren
    # FAKTISK faar. Derefter skal Height kunne rumme de linjer, der kom
    # ud af det.
    #
    # Det er praecis den fejl, der fik bjaelker og knapper til at
    # forsvinde: en raekke regnet til at fylde SHELL_W paa pixlen, i en
    # container der var 17 px smallere, fordi scrollbaren tog dem. Sidste
    # barn ombroed til en linje, hoejden ikke havde plads til - og blev
    # klippet vaek. Ingen formel var forkert; det var bredden, der loej.
    for p, name, body in all_nodes:
        props = body.get("Properties") or {}
        kids = body.get("Children") or []
        if body.get("Control") != "GroupContainer" or len(kids) < 2:
            continue
        if "true" not in (props.get("LayoutWrap") or "").lower():
            continue
        gap = float(re.sub(r"[^0-9.]", "", props.get("LayoutGap", "=8")) or 8)
        found = None
        for w in WIDTHS:
            for ni in ITEM_COUNTS:
                own_h = evaluate(props.get("Height"), w, ni, 4, 4)
                avail = real_width(p, w, ni, 4, 4)
                if own_h is None or avail is None:
                    continue
                avail -= (_num(props.get("PaddingLeft"), w, ni, 4, 4)
                          + _num(props.get("PaddingRight"), w, ni, 4, 4))
                prop_w = prop_width(p, w, ni, 4, 4)
                if prop_w is None:
                    prop_w = avail
                lines, cur_w, cur_h, ok = [], None, 0.0, True
                for k in kids:
                    (kn, kb), = k.items()
                    kp = kb.get("Properties") or {}
                    vis = kp.get("Visible")
                    if vis is not None:
                        shown = evaluate(vis, w, ni, 4, 4)
                        if shown is not None and not shown:
                            continue
                    # Parent.Width i barnet er raekkens Width-EGENSKAB -
                    # ikke den plads, der er (avail). Det er forskellen, der
                    # sendte topbjaelkens knapper ned under kanten.
                    kw = evaluate((kp.get("Width") or "").replace(
                        "Parent.Width", "(%s)" % prop_w), w, ni, 4, 4)
                    kh = evaluate(kp.get("Height"), w, ni, 4, 4)
                    if kw is None or kh is None:
                        ok = False
                        break
                    if cur_w is None:
                        cur_w, cur_h = kw, kh
                    elif cur_w + gap + kw <= avail + 0.5:
                        cur_w, cur_h = cur_w + gap + kw, max(cur_h, kh)
                    else:
                        lines.append(cur_h)
                        cur_w, cur_h = kw, kh
                if not ok or cur_w is None:
                    continue
                lines.append(cur_h)
                need = (sum(lines) + gap * (len(lines) - 1)
                        + _num(props.get("PaddingTop"), w, ni, 4, 4)
                        + _num(props.get("PaddingBottom"), w, ni, 4, 4))
                if own_h + 0.5 < need:
                    found = (f"[4c] {name}: ombryder til {len(lines)} linje(r) i "
                             f"{avail:.0f} px (App.Width={w}, scrollbar "
                             f"medregnet) og skal bruge {need:.0f} px - "
                             f"hoejden er {own_h:.0f}. Det nederste klippes vaek")
                    break
            if found:
                break
        if found:
            problems.append(found)

    # --- 4d. En raekke, der skifter retning, skal passe, naar den er vandret
    #
    # flow_row() staar vandret, naar dens graense siger "passer", og
    # lodret ellers. Graensen er regnet af SHELL_W; her efterproeves den mod
    # den bredde, raekken FAKTISK faar - padding, scrollbar og Stretch
    # medregnet. De faste boern plus den fleksibles mindstebredde skal
    # kunne staa paa linjen, ellers skubbes det sidste ud over kanten.
    for p, name, body in all_nodes:
        props = body.get("Properties") or {}
        if "If(" not in (props.get("LayoutDirection") or ""):
            continue
        gap = float(re.sub(r"[^0-9.]", "", props.get("LayoutGap", "=8")) or 8)
        for w in WIDTHS:
            if is_vertical(props, w):
                continue
            avail = real_width(p, w, 3, 4, 4)
            if avail is None:
                problems.append(f"[4d] {name}: bredden kan ikke efterregnes ved "
                                f"App.Width={w}")
                break
            avail -= (_num(props.get("PaddingLeft"), w, 3, 4, 4)
                      + _num(props.get("PaddingRight"), w, 3, 4, 4))
            need, n = 0.0, 0
            for k in body.get("Children") or []:
                (kn, kb), = k.items()
                kp = kb.get("Properties") or {}
                vis = evaluate(kp.get("Visible"), w, 3, 4, 4)
                if vis is not None and not vis:
                    continue
                if (evaluate(kp.get("FillPortions"), w, 3, 4, 4) or 0) > 0:
                    kw = evaluate(kp.get("LayoutMinWidth"), w, 3, 4, 4) or 0
                else:
                    kw = evaluate(kp.get("Width"), w, 3, 4, 4)
                if kw is None:
                    need = None
                    break
                need += kw
                n += 1
            if need is None:
                continue
            need += gap * max(0, n - 1)
            if need > avail + 0.5:
                problems.append(f"[4d] {name}: vandret ved App.Width={w}, men "
                                f"boernene fylder {need:.0f} px i {avail:.0f} px "
                                f"(scrollbar medregnet) - det sidste skubbes ud")
                break

    # --- 24. Parent.Width maa ikke indgaa i regnestykker ----------------
    #
    # Parent.Width er FORAELDERENS WIDTH-EGENSKAB - ikke pladsen inden i
    # den. Padding traekkes ikke fra, og en scrollbar heller ikke. Inde i et
    # kort med 18 px padding i en krop med 58 px er "Parent.Width" som regel
    # hele skaermens bredde.
    #
    # Topbjaelken regnede titlen som "Parent.Width - 545". Headerens
    # padding var ikke trukket fra, raekken var 57 px for bred, og
    # knapperne ombroed ned under bjaelkens kant - usynlige.
    #
    # Tilladt er kun:
    #   Parent.Width           alene, hvor foraelderen alligevel straekker
    #                          barnet (lodret + Stretch) - vaerdien bruges
    #                          ikke til noget
    #   Parent.TemplateWidth   alene, paa et galleris direkte barn
    # Alt andet: en fleksibel del (FillPortions = 1) eller en bredde regnet
    # af SHELL_W.
    for p, name, body in all_nodes:
        props = body.get("Properties") or {}
        wv = (props.get("Width") or "").strip()
        if "Parent." not in wv:
            continue
        parent = p.rsplit("/", 1)[0]
        pb = by_path.get(parent) if parent else None
        pp_ = (pb or {}).get("Properties") or {}
        if wv == "=Parent.TemplateWidth" and (pb or {}).get("Control") == "Gallery":
            continue
        if wv == "=Parent.Width":
            if pb is None:
                continue
            if all(is_vertical(pp_, w) and is_stretch(pp_, w) for w in WIDTHS) \
                    and not re.search(r"\.(Start|Center|End)\b",
                                      props.get("AlignInContainer") or ""):
                continue
        problems.append(
            f"[24] {name}: Width = {wv[1:][:60]} - Parent.Width er "
            f"foraelderens Width-EGENSKAB, ikke pladsen inden i den (padding "
            f"og scrollbar er ikke trukket fra). Brug FillPortions "
            f"(build_helpers.grow) eller en bredde regnet af SHELL_W")

    # --- 25. En knap skal vaere mindst 30 px hoej -------------------------
    #
    # Raekkeknapperne i Equipment og Material var 26 px med 14 pt tekst, og
    # de stod som tomme kanter i bunden af raekken. Den moderne knap har en
    # mindstehoejde; den haandbyggede Materials-app brugte 30 px og 13 pt,
    # og de knapper virkede.
    for p, name, body in all_nodes:
        if body.get("Control") != "ModernButton":
            continue
        h = evaluate((body.get("Properties") or {}).get("Height"), 1366, 3, 4, 4)
        if h is not None and h < 30:
            problems.append(f"[25] {name}: knappen er {h:.0f} px hoej - mindst 30")

    # --- 26. Galleriernes skabeloner -------------------------------------
    #
    # Parent.TemplateWidth gav 320 i Studio - containerens standardbredde.
    # Listens raekke var 320 px bred til 1200 px indhold, og alt efter
    # beskrivelsen laa uden for den. gen_screen.resolve_templates skriver nu
    # skabelonens bredde og hoejde ud som udtryk; her efterproeves det, og at
    # raekken kan rumme sine celler ved hver skaermbredde.
    for p, name, body in all_nodes:
        for key, val in (body.get("Properties") or {}).items():
            if isinstance(val, str) and "Parent.Template" in val:
                problems.append(f"[26] {name}.{key}: Parent.Template* - Studio gav "
                                f"320. Brug gen_screen.resolve_templates")
        if body.get("Control") != "Gallery":
            continue
        for k in body.get("Children") or []:
            (kn, kb), = k.items()
            kp = kb.get("Properties") or {}
            if "Horizontal" not in (kp.get("LayoutDirection") or "") or \
                    "true" in (kp.get("LayoutWrap") or ""):
                continue
            gap = float(re.sub(r"[^0-9.]", "", kp.get("LayoutGap", "=0")) or 0)
            # Tabeller med kolonner kraever mindst Tablet. Apperne er tablet-
            # og desktoplayouts; paa en telefon kan syv kolonner ikke staa.
            for w in [x for x in WIDTHS if x >= lay.min_width("Tablet")]:
                own = evaluate(kp.get("Width"), w, 3, 4, 4)
                if own is None:
                    problems.append(f"[26] {kn}: skabelonens bredde kan ikke "
                                    f"efterregnes ved App.Width={w}")
                    break
                need, n, ok = 0.0, 0, True
                for c in kb.get("Children") or []:
                    (cn, cb), = c.items()
                    cp = cb.get("Properties") or {}
                    vis = evaluate(cp.get("Visible"), w, 3, 4, 4)
                    if vis is not None and not vis:
                        continue
                    if (evaluate(cp.get("FillPortions"), w, 3, 4, 4) or 0) > 0:
                        cw = evaluate(cp.get("LayoutMinWidth"), w, 3, 4, 4) or 0
                    else:
                        cw = evaluate(cp.get("Width"), w, 3, 4, 4)
                    if cw is None:
                        ok = False
                        break
                    need += cw
                    n += 1
                if not ok:
                    continue
                need += gap * max(0, n - 1) + _num(kp.get("PaddingLeft"), w, 3, 4, 4) \
                    + _num(kp.get("PaddingRight"), w, 3, 4, 4)
                if need > own + 0.5:
                    problems.append(f"[26] {kn}: cellerne fylder {need:.0f} px i en "
                                    f"raekke paa {own:.0f} px (App.Width={w}) - det "
                                    f"sidste er skjult")
                    break

    # --- 29. Overskriften og raekken skal have SAMME kolonnebredder ------
    #
    # Regel 5 goer det for de overskrifter, der er en HtmlViewer. Den her
    # goer det for dem, der er rigtige kontroller.
    #
    # Hubben viste hvorfor: baade overskriften og raekken skrev
    # "Parent.Width - 580". Samme formel - men overskriftens foraelder er
    # kortet (~1600 px), og raekkens er gallerirakken, som Studio gav en
    # helt anden bredde. Overskrifterne stod spredt ud over hele kortet,
    # mens raekkens felter var klemt sammen i venstre side.
    #
    # Naar de to maales mod hinanden, kan den slags ikke staa.
    for p, name, body in all_nodes:
        if body.get("Control") != "Gallery":
            continue
        kids = body.get("Children") or []
        if not kids:
            continue
        (rname, rbody), = kids[0].items()
        rcells = rbody.get("Children") or []
        parent = p.rsplit("/", 1)[0]
        pb = by_path.get(parent) or {}
        head = None
        for sib in (pb.get("Children") or []):
            (sn, sbody), = sib.items()
            if "Head" not in sn or sbody.get("Control") != "GroupContainer":
                continue
            hk = sbody.get("Children") or []
            # EN TABELOVERSKRIFT BESTAAR KUN AF ETIKETTER. Uden det krav
            # blev VH-plans sektionshoved (titel + knapper) parret med
            # item-kortet, fordi de tilfaeldigvis har lige mange boern.
            if len(hk) != len(rcells) or not hk:
                continue
            if any(list(x.values())[0].get("Control") != "ModernText" for x in hk):
                continue
            head = (sn, sbody)
            break
        if head is None or not rcells:
            continue
        hname, hbody = head
        for w in [x for x in WIDTHS if x >= lay.min_width("Tablet")]:
            bad = None
            for hc, rc in zip(hbody.get("Children") or [], rcells):
                (hn, hb), = hc.items()
                (rn, rb), = rc.items()
                hw = evaluate((hb.get("Properties") or {}).get("Width"), w, 3, 4, 4)
                rw = evaluate((rb.get("Properties") or {}).get("Width"), w, 3, 4, 4)
                if hw is None or rw is None or abs(hw - rw) < 0.51:
                    continue
                bad = (hn, hw, rn, rw)
                break
            if bad:
                problems.append(
                    f"[29] {hname} og {rname} flugter ikke ved App.Width={w}: "
                    f"{bad[0]} er {bad[1]:.0f} px, {bad[2]} er {bad[3]:.0f} px")
                break

    # --- 27. En tekst skal vaere mindst een linje hoej --------------------
    #
    # Ellers viser den moderne Text-kontrol sin egen scrollbar. Det var den
    # moerke streg i topbjaelken: titlen var 22 pt i 30 px.
    for p, name, body in all_nodes:
        if body.get("Control") != "ModernText":
            continue
        pr = body.get("Properties") or {}
        size = evaluate(pr.get("Size", "=14"), 1366, 3, 4, 4)
        h = evaluate(pr.get("Height"), 1366, 3, 4, 4)
        if size and h is not None and h < size * 1.5 - 0.01:
            problems.append(f"[27] {name}: {size:.0f} pt i {h:.0f} px - mindst "
                            f"{size * 1.5:.0f}, ellers faar teksten sin egen scrollbar")

    # --- 28. Ingen FillPortions i en raekke, der ikke ombryder ----------
    #
    # I topbjaelken og detaljepopuppens hoved stod knapperne ved siden af en
    # FillPortions-venstreside - og i Studio blev de tegnet en linje for
    # lavt, skaaret over af kanten. Listens raekker har faste, udregnede
    # bredder, og dér stod knapperne rigtigt. build_helpers.grow() giver nu
    # en udregnet bredde (gen_screen._resolve_grow).
    for p, name, body in all_nodes:
        props = body.get("Properties") or {}
        if "Horizontal" not in (props.get("LayoutDirection") or "") or \
                "true" in (props.get("LayoutWrap") or "").lower():
            continue
        for k in body.get("Children") or []:
            (kn, kb), = k.items()
            fp = ((kb.get("Properties") or {}).get("FillPortions") or "=0").strip()
            if fp not in ("=0", "0"):
                problems.append(f"[28] {kn}: FillPortions {fp[1:40]} i raekken {name} "
                                f"- brug build_helpers.grow() (en udregnet bredde)")

    # --- 23. Rammen ------------------------------------------------------
    #
    # Alle fire skaerme har den samme ramme (build_helpers.app_frame):
    #
    #     con<X>Root     Parent.Width x Parent.Height, scroller IKKE
    #       con<X>Header   fast hoejde, der kun afhaenger af App.Width
    #       con<X>Body     FillPortions > 0, LayoutOverflowY = Scroll
    #
    # Reglen fanger de tre maader, rammen kan gaa i stykker paa:
    #
    #   a. Bjaelken havner i det, der scroller - saa kan den scrolles vaek,
    #      og dens hoejde bliver en del af en sum igen.
    #   b. Headerens hoejde afhaenger af data. En hoejde med CountRows,
    #      Filter eller en variabel kan fejle eller blive blank - og en
    #      blank hoejde er en bjaelke, der er vaek.
    #   c. SHELL_W bliver usand. Paddingen, scrollbaren og luften SKAL
    #      tilsammen vaere mindst SHELL_INSET, ellers regner hver raekke
    #      med plads, den ikke har. Det var den fejl, der fik knapperne
    #      til at forsvinde.
    root_items = screen.get("Children") or []
    if not root_items:
        problems.append("[23] skaermen har ingen boern")
    else:
        (rname, rbody), = root_items[0].items()
        rprops = rbody.get("Properties") or {}
        rkids = rbody.get("Children") or []

        def _eq(k, v):
            return (rprops.get(k) or "").strip() == v

        if not (rname.endswith("Root") and _eq("Height", "=Parent.Height")
                and _eq("Width", "=Parent.Width")
                and "Vertical" in (rprops.get("LayoutDirection") or "")):
            problems.append(f"[23] {rname}: skaermens foerste barn skal vaere "
                            f"rammen - lodret, Parent.Width x Parent.Height. "
                            f"Byg den med build_helpers.app_frame()")
        elif "Scroll" in (rprops.get("LayoutOverflowY") or ""):
            problems.append(f"[23a] {rname}: rammen selv maa ikke scrolle - saa "
                            f"scroller bjaelken med. Det er kroppen, der scroller")
        else:
            bodies = [k for k in rkids
                      if "Scroll" in ((list(k.values())[0].get("Properties") or {})
                                      .get("LayoutOverflowY") or "")]
            if len(bodies) != 1:
                problems.append(f"[23a] {rname}: rammen skal have praecis een krop "
                                f"med LayoutOverflowY = Scroll (fandt {len(bodies)})")
            for k in rkids:
                (kn, kb), = k.items()
                kp = kb.get("Properties") or {}
                is_body = k in bodies
                pl = _num(kp.get("PaddingLeft"), 1920, 0, 0, 3)
                pr = _num(kp.get("PaddingRight"), 1920, 0, 0, 3)
                if is_body:
                    if evaluate(kp.get("FillPortions"), 1920, 0, 0, 3) in (None, 0):
                        problems.append(f"[23a] {kn}: kroppen skal have "
                                        f"FillPortions > 0 og fylde resten af skaermen")
                    inset = pl + pr + lay.SCROLLBAR_W
                else:
                    h = (kp.get("Height") or "")
                    if re.search(r"\b(CountRows|Filter|LookUp|IsEmpty|col[A-Z]\w*|"
                                 r"var[A-Z]\w*|gbl[A-Z]\w*|Parent\.|Self\.)", h):
                        problems.append(f"[23b] {kn}: headerens hoejde afhaenger af "
                                        f"andet end skaermbredden -> {h.strip()[:80]}")
                    elif any(evaluate(h, w, 0, 0, 3) is None for w in WIDTHS):
                        problems.append(f"[23b] {kn}: headerens hoejde kan ikke "
                                        f"efterregnes -> {h.strip()[:80]}")
                    inset = pl + pr
                if inset + lay.FIT_SLACK > lay.SHELL_INSET:
                    problems.append(
                        f"[23c] {kn}: padding {pl:.0f} + {pr:.0f}"
                        + (f" + scrollbar {lay.SCROLLBAR_W}" if is_body else "")
                        + f" + luft {lay.FIT_SLACK} = {inset + lay.FIT_SLACK:.0f} > "
                        f"SHELL_INSET {lay.SHELL_INSET}. SHELL_W ville love "
                        f"mere plads, end der er")

    # --- 4. En vandret raekke skal kunne rumme sine boern ------------------
    #
    # TO TILFAELDE, OG DE ER IKKE DET SAMME
    #
    # UDEN wrap kan Power Apps' autolayout KRYMPE boernene (LayoutMinWidth
    # 0), saa en raekke, hvis boern tilsammen er bredere end den, er ikke
    # noedvendigvis en fejl. Her efterproeves derfor kun de raekker, hvor
    # BAADE raekken og hvert barn har en bredde skrevet som et RENT TAL -
    # dér er der ingen krympning at regne med. Det er den oprindelige
    # regel, uaendret.
    #
    # MED wrap ombryder raekken i stedet. Det er meningen paa en smal
    # skaerm - men ombryder den ved ALLE de bredder, tjekket proever, er
    # der ikke tale om et braekpunkt: raekken passer aldrig, og wrap'en
    # skjuler fejlen ved bare at stable de to grupper.
    #
    # Det var praecis, hvad der skete: domaeneappernes topbjaelke brugte
    # gap 20 mellem sine to grupper, mens venstresiden kun reserverede
    # BAR_GAP (10) til den. 10 px for bred ved enhver skaermbredde, altid
    # ombrudt - og den oeverste sektion i BAADE Equipment og Material stod
    # i to rader med en tom foerste rad. Ingenting klagede.
    for p, name, body in all_nodes:
        props = body.get("Properties") or {}
        kids = body.get("Children") or []
        if body.get("Control") != "GroupContainer" or not kids:
            continue
        if "Horizontal" not in (props.get("LayoutDirection") or ""):
            continue
        gap = float(re.sub(r"[^0-9.]", "", props.get("LayoutGap", "=8")) or 8)

        if "true" not in (props.get("LayoutWrap") or "").lower():
            # -- rene tal, ingen krympning -----------------------------
            widths = []
            for k in kids:
                (kn, kb), = k.items()
                ws = (kb.get("Properties") or {}).get("Width", "")
                m = re.fullmatch(r"=\s*(\d+(?:\.\d+)?)", ws.strip()) if ws else None
                if not m:
                    widths = None
                    break
                widths.append(float(m.group(1)))
            own_w = props.get("Width", "")
            m = re.fullmatch(r"=\s*(\d+(?:\.\d+)?)", own_w.strip()) if own_w else None
            if widths and m:
                need = sum(widths) + gap * (len(widths) - 1)
                if need > float(m.group(1)) + 0.01:
                    problems.append(
                        f"[4] {name}: boern {need:.0f} px bredere end raekken "
                        f"{float(m.group(1)):.0f} px")
            continue

        # -- wrap: passer raekken ved den BREDESTE skaerm? ---------------
        #
        # Kun den bredeste. En wrap-raekke SKAL ombryde paa smalle
        # skaerme - det er meningen - saa et fund dér siger ingenting.
        # Men ombryder den selv paa 1920, er wrap'en ikke et braekpunkt:
        # raekken passer aldrig, og de to grupper staar altid i to rader.
        #
        # At proeve alle bredder og kraeve overloeb i dem alle lyder
        # strengere, men er det ikke: mange bredder kan ikke efterregnes,
        # og saa blev "alle" til "alle de smalle". Den formulering gav
        # tre falske fund i VH-plan.
        ni, no, npk = max(ITEM_COUNTS), max(OP_COUNTS), max(PKG_COUNTS)
        w = max(WIDTHS)
        own = avail_width(p, w, ni, no, npk)
        if own is None:
            continue
        need, ok = 0.0, True
        for k in kids:
            (kn, kb), = k.items()
            kp = kb.get("Properties") or {}
            vis = evaluate(kp.get("Visible"), w, ni, no, npk)
            if vis is not None and not vis:
                continue
            kwe = kp.get("Width") or ""
            # Parent.Width eller FillPortions: barnet tager det, der er,
            # og kan ikke goere raekken for bred.
            if "Parent." in kwe or "Self." in kwe:
                ok = False
                break
            if evaluate(kp.get("FillPortions"), w, ni, no, npk):
                ok = False
                break
            kw = evaluate(kp.get("Width"), w, ni, no, npk)
            if kw is None:
                ok = False
                break
            need += kw + gap
        if not ok:
            continue
        need = max(0.0, need - gap)
        if need > own + 0.01:
            problems.append(
                f"[4] {name}: ombryder OGSAA paa {w} px - boern {need:.0f} px, "
                f"raekken {own:.0f} px. Wrap er til smalle skaerme, ikke til "
                f"en raekke der aldrig passer")

    # --- 4b. En wrap-raekke maa ikke have en KONSTANT hoejde -------------
    #
    # group(..., wrap_rows=2) ganger uden betingelse: hoejden blev
    # Max(52, 36) * 2 + 20 = 124 ved enhver skaermbredde. Men bjaelken
    # ombryder kun UNDER braekpunktet; over det staar den paa een raekke a
    # 52 px, og de resterende 72 px blev et tomt baelte oeverst i baade
    # Equipment og Material.
    #
    # Ombrydningen er betinget, saa hoejden skal vaere det ogsaa. En
    # KONSTANT hoejde paa en wrap-raekke er enten for hoej over
    # braekpunktet eller for lav under det - den kan ikke vaere rigtig
    # begge steder.
    for p, name, body in all_nodes:
        props = body.get("Properties") or {}
        if "true" not in (props.get("LayoutWrap") or "").lower():
            continue
        if len(body.get("Children") or []) < 2:
            continue
        h = (props.get("Height") or "").strip()
        if h.startswith("="):
            h = h[1:].strip()
        if re.fullmatch(r"\d+(?:\.\d+)?", h):
            problems.append(
                f"[4b] {name}: LayoutWrap med fast hoejde {h}. Ombrydningen er "
                f"betinget, saa hoejden skal vaere det ogsaa - brug samme "
                f"fits()-graense som bredden")

    # --- 5. HTML-overskriften skal flugte med kontrollerne i raekken -------
    by_name = {n: b for _, n, b in all_nodes}
    for html_name, row_name in (("conVhpOpsHeaderHtml", "conVhpOpRow"),
                                ("conVhpPickerHeaderHtml", "conVhpPickerRow")):
        if html_name not in by_name or row_name not in by_name:
            continue
        html = (by_name[html_name].get("Properties") or {}).get("HtmlText", "")
        cols = [float(x) for x in re.findall(r"(\d+)px", html.split("grid-template-columns:")[-1].split(";")[0])] \
            if "grid-template-columns:" in html else []
        gapm = re.search(r"column-gap:(\d+)px", html)
        hgap = float(gapm.group(1)) if gapm else 0
        rowb = by_name[row_name]
        rw = []
        for k in rowb.get("Children") or []:
            (kn, kb), = k.items()
            m = re.fullmatch(r"=\s*(\d+(?:\.\d+)?)", ((kb.get("Properties") or {}).get("Width") or "").strip())
            rw.append(float(m.group(1)) if m else None)
        if cols and all(x is not None for x in rw):
            if len(cols) != len(rw):
                problems.append(f"[5] {html_name}: {len(cols)} kolonner mod {len(rw)} kontroller i {row_name}")
            elif any(abs(a - b) > 0.01 for a, b in zip(cols, rw)):
                problems.append(f"[5] {html_name}: kolonnebredder {cols} flugter ikke med {row_name} {rw}")
            else:
                rgap = float(re.sub(r"[^0-9.]", "", (rowb.get("Properties") or {}).get("LayoutGap", "=0")) or 0)
                if abs(hgap - rgap) > 0.01:
                    problems.append(f"[5] {html_name}: column-gap {hgap} mod LayoutGap {rgap} i {row_name}")

    # --- 6. Balancerede parenteser og anfoerselstegn i alle formler --------
    for p_, name, body in all_nodes:
        for key, val in (body.get("Properties") or {}).items():
            if not isinstance(val, str):
                continue
            txt = val[1:] if val.startswith("=") else val
            depth = 0
            in_str = False
            i = 0
            while i < len(txt):
                ch = txt[i]
                if in_str:
                    if ch == '"':
                        if i + 1 < len(txt) and txt[i + 1] == '"':
                            i += 1
                        else:
                            in_str = False
                elif ch == '"':
                    in_str = True
                elif ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                    if depth < 0:
                        break
                i += 1
            if depth != 0 or in_str:
                problems.append(f"[6] {name}.{key}: ubalancerede parenteser/anfoerselstegn")

    # --- 7. Ingen formel maa referere en kontrol, der ikke findes ----------
    # En Reset() eller .Text paa et slettet kontrolnavn faar compile_canvas
    # til at fejle paa et ukendt navn - og det opdages ellers foerst i Studio.
    known = {n for _, n, _ in all_nodes}
    ref = re.compile(r"\b((?:con|gal|txt|btn|drp|num|chk|cmb|tmr)[A-Za-z0-9_]+)\s*\.")
    reset = re.compile(r"Reset\(\s*([A-Za-z0-9_]+)\s*\)")
    for p_, name, body in all_nodes:
        for key, val in (body.get("Properties") or {}).items():
            if not isinstance(val, str):
                continue
            for m in set(ref.findall(val)) | set(reset.findall(val)):
                if m not in known and m not in ("Parent", "Self", "ThisItem", "ThisRecord"):
                    problems.append(f"[7] {name}.{key}: refererer ukendt kontrol '{m}'")

    # --- 9. FillPortions i en lodret container -----------------------------
    # FillPortions fordeler plads LANGS containerens retning: bredde i en
    # vandret, HOEJDE i en lodret.
    #
    # I dette projekt regnes enhver containers hoejde ud af sine boern, saa
    # der ER ingen overskydende hoejde at fordele. Har et barn alligevel
    # FillPortions <> 0, vokser det, saa snart forelderen selv bliver
    # straekket af SIN forelder - og saa passer den udregnede hoejde ikke
    # laengere til det, der faktisk tegnes.
    #
    # Det skete, da FL- og objektlisteblokken blev flyttet fra en vandret
    # gitterraekke (hvor FillPortions fordelte BREDDE og var rigtig) ned i
    # en lodret kolonne. Begge blokke voksede til hele kolonnens hoejde.
    #
    # DEN ENE UNDTAGELSE ER RAMMENS KROP (regel 23). Rammen er skaermhoej -
    # dens hoejde er Parent.Height, ikke regnet af boernene - og kroppen
    # SKAL fylde resten under headeren. Det er netop den overskydende
    # hoejde, FillPortions er til.
    for p, name, body in all_nodes:
        props = body.get("Properties") or {}
        if props.get("LayoutDirection", "").strip() != "=LayoutDirection.Vertical":
            continue
        screen_tall = (props.get("Height") or "").strip() == "=Parent.Height"
        for kid in (body.get("Children") or []):
            kname = list(kid.keys())[0]
            kprops = (list(kid.values())[0].get("Properties") or {})
            fp = kprops.get("FillPortions", "=0").strip()
            if (screen_tall and (kprops.get("LayoutOverflowY") or "").strip()
                    == "=LayoutOverflow.Scroll"):
                continue
            if fp not in ("=0", "0"):
                problems.append(f"[9] {kname}: FillPortions {fp[:40]} i den LODRETTE "
                                f"container {name} - barnet straekkes i hoejden")

    # --- 8. Samlinger skal findes i App.pa.yaml ---------------------------
    # En skaerm, der bruger colVhpNoget, som ingen definerer, kompilerer ikke
    # - men fejlen dukker foerst op i Studio. Da opslagslisterne blev flyttet
    # fra haardkodede tabeller til navngivne formler, blev tre referencer
    # haengende. Det her fanger det inden synk.
    # Kontrollernes egenskaber PLUS skaermens egne. De to sidste regler
    # herunder skal se begge dele.
    screen_and_controls = [(body.get("Properties") or {}) for _, _, body in all_nodes]
    screen_and_controls.append(screen.get("Properties") or {})

    app_path = os.path.join(os.path.dirname(SCREEN), "App.pa.yaml")
    app = open(app_path, encoding="utf-8").read() if os.path.exists(app_path) else ""
    if os.path.exists(app_path):
        defined = set(re.findall(r"^\s*=?(col[A-Z]\w*)\s*=", app, re.M))
        defined |= set(re.findall(r"ClearCollect\(\s*(col\w+)", app))
        # SKAERMENS EGNE EGENSKABER TAELLER MED.
        #
        # Her stod foer kun all_nodes, altsaa kontrollerne. Men skaermens
        # OnVisible er netop dér, Equipment og Material henter deres
        # raekker - saa en samling, der KUN bruges i OnVisible, blev ikke
        # efterproevet af det her tjek overhovedet.
        used = set()
        for props in screen_and_controls:
            for val in props.values():
                if isinstance(val, str):
                    used |= set(re.findall(r"\bcol[A-Z]\w*", val))
        for name in sorted(used - defined):
            problems.append(f"[8] samlingen '{name}' bruges i skaermen, "
                            f"men defineres ikke i App.pa.yaml")

    # --- 8c. Ingen skaerm maa sammenligne App.Width med et tal ------------
    # Et braekpunkt hoerer til i tools/layout_tokens.py, ikke i en kontrol.
    #
    # Hvorfor det skal haandhaeves PAA SKAERMEN og ikke i builderne: tallet
    # bliver som regel interpoleret ind i en f-streng, saa en vagt, der
    # laeser Python-kildens strengkonstanter, ser hverken bredden eller
    # tallet. I den byggede YAML staar begge dele.
    #
    # Det, reglen beskytter: apperne havde fire braekpunkter mellem 996 og
    # 1024 i fire filer. Ingen af dem var valgt i forhold til de tre andre.
    # Mindst to par af dem SKULLE have vaeret ens - skinnens bredde og
    # splittets hoejde, flisernes bredde og deres beholders hoejde - og
    # intet i koden sagde det.
    #
    # Aritmetik er i orden: SHELL_W er "(App.Width - 64)". Det er kun
    # SAMMENLIGNINGEN, der er en beslutning om enhedsklasse.
    bp = re.compile(r"App\.Width\s*[<>]=?\s*[0-9]")
    for props in screen_and_controls:
        for key, val in props.items():
            if isinstance(val, str) and bp.search(val):
                problems.append(f"[8c] {key}: sammenligner App.Width med et tal "
                                f"- braekpunkter hoerer i tools/layout_tokens.py "
                                f"(below()/if_below()/fits())")

    # --- 8b. Designtokens skal findes i temaformlen -----------------------
    # Hver farve i skaermen staar som C.'et-navn', og navnene defineres af
    # den navngivne formel C i App.pa.yaml (skrevet af
    # tools/design_tokens.py).
    #
    # Power Fx siger IKKE fra, hvis et felt ikke findes i en record - den
    # giver blank. Og en blank farve er GENNEMSIGTIG. En stavefejl ville
    # derfor ikke fejle i compile; kontrollen ville bare forsvinde, og det
    # ville ses foerst i den koerende app - maaske kun i det ene tema.
    #
    # ref() i design_tokens.py fanger det allerede paa vej ud. Det her
    # fanger den anden vej: at de to generatorer er kommet ud af trit, saa
    # skaermen er bygget med en token, App.pa.yaml ikke laengere kender.
    if os.path.exists(app_path):
        known = set(re.findall(r"'([a-z0-9-]+)'\s*:", app))
        # Skaermens egen Fill ER appbaggrunden - den vigtigste farve i
        # appen og den ene, der ikke staar paa en kontrol.
        used_tokens = set()
        for props in screen_and_controls:
            for val in props.values():
                if isinstance(val, str):
                    used_tokens |= set(re.findall(r"\bC\.'([a-z0-9-]+)'", val))
        for name in sorted(used_tokens - known):
            problems.append(f"[8b] designtokenen '{name}' bruges i skaermen, "
                            f"men staar ikke i temaformlen C i App.pa.yaml")
        if used_tokens and not known:
            problems.append("[8b] skaermen bruger designtokens, men App.pa.yaml "
                            "har ingen temaformel C")

    # --- 10. Egenskaber kontroltypen ikke kender ---------------------------
    # Studio afviser en ukendt egenskab ved compile, ikke ved synk, saa
    # fejlen kommer foerst efter en fuld runde gennem VS Code. Den er
    # billig at fange her.
    #
    # Gallery har ingen Radius*. Den fik dem, da objektlisten blev lavet om
    # fra en raekke afkrydsningsfelter til et galleri: radius fulgte med fra
    # den gamle beholder, og compile fejlede med fire ukendte egenskaber.
    # Tooltip findes kun paa de INTERAKTIVE moderne kontroller. En
    # ModernText er en label, ikke en kontrol man kan naa med tastaturet,
    # og den kender den ikke. Et forsoeg paa at laegge feltforklaringerne
    # der fejlede i compile 21 gange.
    #
    # ModernDatePicker: SelectedDate LAESER datoen, DefaultDate saetter
    # den. Forskellen ses ikke i en skaerm, der ser rigtig ud - kun i
    # compile, efter en hel runde gennem Studio. Den kostede et deploy.
    UNSUPPORTED = {
        "Gallery": ("RadiusBottomLeft", "RadiusBottomRight",
                    "RadiusTopLeft", "RadiusTopRight"),
        "ModernText": ("Tooltip",),
        "GroupContainer": ("Tooltip",),
        "HtmlViewer": ("Tooltip",),
        "ModernDatePicker": ("SelectedDate", "DateTimeZone"),
    }
    for p_, name, body in all_nodes:
        bad = UNSUPPORTED.get((body.get("Control") or "").strip())
        if not bad:
            continue
        for key in sorted(set(body.get("Properties") or {}) & set(bad)):
            problems.append(f"[10] {name}: {body['Control']} kender ikke "
                            f"egenskaben '{key}' - compile vil fejle")

    # --- 11. Efterstillet komma i Power Fx ---------------------------------
    # Power Fx tillader ikke et komma lige foer en lukkeparentes. Det sker,
    # naar nogen sletter den sidste gren af et If() og glemmer kommaet paa
    # linjen foer - og fejlen ses foerst ved compile.
    TRAILING = re.compile(r",\s*\)")
    for p_, name, body in all_nodes:
        for key, val in (body.get("Properties") or {}).items():
            if isinstance(val, str) and TRAILING.search(val):
                problems.append(f"[11] {name}.{key}: komma lige foer ')' "
                                f"- Power Fx afviser det ved compile")

    # --- 12. Uescapet anfoerselstegn i en Power Fx-streng ------------------
    # En dansk hjaelpetekst, der selv naevner noget i anfoerselstegn, lukker
    # strengen midt i saetningen, hvis tegnene ikke er doblet. Power Fx
    # laeser saa resten som navne. Det gav 144 fejl fordelt paa fire
    # hjaelpepaneler, fordi kilde-linjen naevner "Den gode VH-plan".
    #
    # At taelle anfoerselstegn er IKKE nok: "Kilde: "Den gode VH-plan" ..."
    # har seks - et lige tal - og ser derfor rigtigt ud. Tegnene parrer
    # bare forkert. Det der afsloerer fejlen er, hvad der staar EFTER en
    # lukkende anfoersel: et bogstav. Efter en rigtig streng kommer altid
    # en operator, et komma eller en parentes - eller et af de faa
    # noegleord, der er operatorer i Power Fx.
    KEYWORD_OPS = {"in", "exactin", "and", "or", "not", "as"}

    def unescaped_quote(expr):
        i, n = 0, len(expr)
        while i < n:
            if expr[i] != '"':
                i += 1
                continue
            j = i + 1
            while j < n:
                if expr[j] == '"':
                    if j + 1 < n and expr[j + 1] == '"':
                        j += 2          # doblet "" - en escaped anfoersel
                        continue
                    break
                j += 1
            if j >= n:
                return "strengen lukker aldrig"
            k = j + 1
            while k < n and expr[k] in " \t\n":
                k += 1
            if k < n and (expr[k].isalnum() or expr[k] == "_"):
                w = re.match(r"\w+", expr[k:]).group(0)
                if w.lower() not in KEYWORD_OPS:
                    return f"'{w}' staar lige efter en lukket streng"
            i = j + 1
        return None

    for p_, name, body in all_nodes:
        for key, val in (body.get("Properties") or {}).items():
            if not isinstance(val, str):
                continue
            why = unescaped_quote(val)
            if why:
                problems.append(f"[12] {name}.{key}: {why} - et anfoerselstegn "
                                f"i teksten er ikke doblet. Brug build_help._q()")

    # --- 13. Parent.Template* uden for et galleris direkte barn ------------
    # TemplateWidth og TemplateHeight findes kun paa Gallery. Bruger en
    # kontrol dem, skal dens FORAELDER vaere galleriet - ellers er navnet
    # ukendt ved compile. Raekketeksten i objektlisten laa et niveau for
    # dybt: dens Parent var raekkebeholderen.
    # p_ er STIEN inkl. kontrollen selv - forelderen er naestsidste led.
    TPL = re.compile(r"Parent\.Template(?:Width|Height)")
    for p_, name, body in all_nodes:
        for key, val in (body.get("Properties") or {}).items():
            if not isinstance(val, str) or not TPL.search(val):
                continue
            parts = [x for x in (p_ or "").split("/") if x]
            pname = parts[-2] if len(parts) >= 2 else None
            if (by_name.get(pname) or {}).get("Control") != "Gallery":
                problems.append(f"[13] {name}.{key}: bruger Parent.Template*, "
                                f"men forelderen '{pname}' er ikke et Gallery")

    # --- 14. Vandret scroll under Stretch ----------------------------------
    # I en LODRET container tvinger LayoutAlignItems.Stretch boernene ned i
    # containerens bredde. En tabel, der er bredere end kortet MED VILJE,
    # bliver derfor klemt sammen i stedet for at overflyde - og
    # LayoutOverflowX.Scroll udloeses aldrig, fordi der ikke er noget at
    # scrolle. Operationstabellen stod saadan: kun den bredeste kolonne var
    # laesbar, resten var presset ned i ingenting.
    for p_, name, body in all_nodes:
        props = body.get("Properties") or {}
        if props.get("LayoutOverflowX", "").strip() != "=LayoutOverflow.Scroll":
            continue
        if props.get("LayoutDirection", "").strip() != "=LayoutDirection.Vertical":
            continue
        if props.get("LayoutAlignItems", "").strip() == "=LayoutAlignItems.Stretch":
            problems.append(f"[14] {name}: vandret scroll, men Stretch klemmer "
                            f"indholdet ned i containerens bredde - brug Start")

    # --- 15. Mutation inde i ForAll (ADVARSEL, ikke fejl) ------------------
    #
    # Den her staar for sig og staekker ikke byggeriet. VH-plan-appen har
    # otte af dem og har koert i lang tid; det er en ydelsessag, ikke en
    # oversaettelsesfejl, og at goere den til en stopklods ville betyde,
    # at ingen kunne bygge noget som helst, foer de otte var lavet om.
    #
    # App checker melder den samme sag ved deploy. Forskellen er, at den
    # staar HER, foer en hel runde gennem Studio.
    # Collect, Patch, Remove og deres slaegtninge inde i et ForAll muterer
    # maalet EEN gang pr. gennemloeb. Mod en samling betyder det en
    # regelgenberegning pr. raekke; mod en DATAKILDE betyder det et
    # netvaerkskald pr. raekke. App checker melder det som
    # ForAllWithMutation - men foerst efter en hel runde gennem Studio.
    #
    # ForAll returnerer en TABEL. Skrivningen kan derfor samles:
    #     ClearCollect(col, ForAll(kilde, { ... }))
    #     Patch(kilde, ForAll(raekker), ForAll(aendringer))
    # Flowkald eller anden per-raekke-adfaerd maa gerne blive i loekken -
    # det er kun SKRIVNINGEN, der skal ud.
    warnings = []
    MUTATORS = ("Collect", "ClearCollect", "Patch", "Remove", "RemoveIf",
                "UpdateIf", "Clear")
    MUT_RE = re.compile(r"\b(" + "|".join(MUTATORS) + r")\s*\(")

    def mut_target(expr, at):
        """FOERSTE argument til en mutator - altsaa det, der skrives I.

        Reglen sagde foer "eet kald pr. raekke" om alle otte fund i
        VH-plan. Det var kun sandt for de fire, der skriver i en
        SharePoint-liste. De fire andre skriver i en samling i
        hukommelsen, hvor der ikke er noget kald overhovedet - og en
        advarsel, der overdriver fire ud af otte gange, bliver laest som
        stoej i alle otte."""
        i = expr.index("(", at)
        depth, j, q = 0, i, None
        while j < len(expr):
            c = expr[j]
            if q:
                if c == q:
                    q = None
            elif c in "\"'":
                q = c
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    return expr[i + 1:j].strip()
            elif c == "," and depth == 1:
                return expr[i + 1:j].strip()
            j += 1
        return ""

    # Navnekonventionen i hele repoet: en arbejdssamling hedder col + stort
    # bogstav. Alt andet, en mutator kan skrive i, er en datakilde.
    COL_RE = re.compile(r"^col[A-Z]\w*$")

    def forall_bodies(expr):
        """Indholdet af hvert ForAll( ... ), parenteserne talt efter."""
        for m in re.finditer(r"\bForAll\s*\(", expr):
            i, depth = m.end() - 1, 0
            while i < len(expr):
                if expr[i] == "(":
                    depth += 1
                elif expr[i] == ")":
                    depth -= 1
                    if depth == 0:
                        break
                i += 1
            yield expr[m.end():i]

    for p_, name, body in all_nodes:
        for key, val in (body.get("Properties") or {}).items():
            if not isinstance(val, str) or "ForAll" not in val:
                continue
            for inner in forall_bodies(val):
                remote, local = {}, {}
                for m in MUT_RE.finditer(inner):
                    tgt = mut_target(inner, m.start())
                    (local if COL_RE.match(tgt) else remote)[m.group(1)] = tgt
                if remote:
                    warnings.append(
                        f"[15] {name}.{key}: {', '.join(sorted(remote))} inde i "
                        f"ForAll mod {', '.join(sorted(set(remote.values())))} "
                        f"- et NETVAERKSKALD pr. raekke. Saml skrivningen udenfor")
                elif local:
                    warnings.append(
                        f"[15] {name}.{key}: {', '.join(sorted(local))} inde i "
                        f"ForAll mod {', '.join(sorted(set(local.values())))} "
                        f"- samling i hukommelsen, saa intet kald, men App "
                        f"checker melder ForAllWithMutation")
                if remote or local:
                    break

    # --- 21. ButtonAppearance.Secondary ------------------------------------
    #
    # Den moderne Button har INGEN Fill-egenskab. Appearance afgoer
    # fyldet, og Secondary er dokumenteret som "subtle FILLED style" -
    # fyldet kommer fra Fluent-temaet, ikke fra en token.
    #
    # I lys tilstand lignede det en almindelig graa knap, saa ingen
    # opdagede det. I MOERK tilstand blev hver sekundaer knap en LYS
    # pille med vores egen naesten-hvide C_TITLE ovenpaa. Proceslinjen,
    # "Til hubben", "Send as email" - alle sammen.
    #
    # Outline er "outlined button with NO background fill": kun kant og
    # tekst, og dem saetter vi selv. Subtle og Transparent har heller
    # intet fyld og er derfor ogsaa i orden.
    for p_, name, body in all_nodes:
        for key, val in (body.get("Properties") or {}).items():
            if isinstance(val, str) and "ButtonAppearance.Secondary" in val:
                problems.append(
                    f"[21] {name}.{key}: ButtonAppearance.Secondary henter sit "
                    f"fyld fra Fluent-temaet, ikke fra en token - brug "
                    f"ButtonAppearance.Outline")

    # --- 22. Concurrent med en indbyrdes afhaengighed ----------------------
    #
    # Regel 20 foreslaar Concurrent, hvor der er noget at hente. Den her er
    # dens modstykke: den ser paa et Concurrent, der ALLEREDE staar der.
    #
    # Power Apps afviser at compile, og det stod ikke i noget byggeoutput -
    # det kom foerst ud af deploy:
    #
    #   [App, OnStart] There is a dependency on 'colVhpSavedItems' between
    #   two different formulas in the Concurrent function. One formula is
    #   changing it while another may be reading or also trying to change it.
    #
    # Og den har ret: dyblinket fyldte colVhpSavedItems i eet argument og
    # slog op i den fra to andre. Concurrent lover ingen raekkefoelge, saa
    # de to kunne laese en tom samling.
    #
    # Reglen deler Concurrent'ens argumenter paa komma i dybde 1 og
    # sammenligner: skriver eet argument i colX, maa ingen ANDEN naevne
    # colX. Det er en FEJL og ikke en advarsel - compile afviser den.
    def split_args(text, at):
        """Argumenterne i et kald, delt paa komma i dybde 1."""
        i = text.index("(", at)
        depth, j, q, start, out = 0, i, None, i + 1, []
        while j < len(text):
            c = text[j]
            if q:
                if c == q:
                    q = None
            elif c in "\"'":
                q = c
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    out.append(text[start:j])
                    return out
            elif c == "," and depth == 1:
                out.append(text[start:j])
                start = j + 1
            j += 1
        return out

    WRITES = re.compile(r"\b(?:Clear)?Collect\(\s*(col[A-Z]\w*)\s*,|"
                        r"\bClear\(\s*(col[A-Z]\w*)\s*\)")
    # App.OnStart ligger i App.pa.yaml, ikke i skaermen - og det var
    # NETOP dér fejlen sad. Filen laeses som raa tekst af regel 8; den
    # bruges her som een stor "egenskab".
    conc_targets = [((b.get("Properties") or {}), n) for _p, n, b in all_nodes]
    conc_targets.append((screen.get("Properties") or {}, "<skaermen>"))
    if app:
        conc_targets.append(({"OnStart (App.pa.yaml)": app}, "App"))
    for props, owner in conc_targets:
        for key, val in props.items():
            if not isinstance(val, str) or "Concurrent(" not in val:
                continue
            for m in re.finditer(r"\bConcurrent\s*\(", val):
                args = split_args(val, m.start())
                if len(args) < 2:
                    continue
                written = []
                for a in args:
                    ws = set()
                    for wm in WRITES.finditer(a):
                        ws.add(wm.group(1) or wm.group(2))
                    written.append(ws)
                for i, ws in enumerate(written):
                    for col in ws:
                        for j, other in enumerate(args):
                            if i == j:
                                continue
                            if re.search(r"\b%s\b" % re.escape(col), other):
                                problems.append(
                                    f"[22] {owner}.{key}: Concurrent skriver "
                                    f"'{col}' i eet argument og laeser den i et "
                                    f"andet. Power Apps afviser at compile - "
                                    f"del det i to Concurrent efter hinanden")

    # --- 16. Dropdown-Default der ikke er en RECORD ------------------------
    # ModernDropdown.Default vil have en RECORD fra kontrollens egen
    # Items-tabel - ikke vaerdien inde i den. Staar der en variabel eller
    # en streng, svarer compile:
    #     [Control 'drpX', Property 'Default'] Expected a valid input
    #     matching Items
    # Det koster en hel runde gennem Studio at faa at vide.
    #
    # En record kommer fra LookUp(), First(), en record-literal, ThisItem
    # eller Blank(). Er ingen af dem i udtrykket, er det en skalar.
    RECORDISH = ("LookUp(", "First(", "Last(", "{", "ThisItem", "Blank()",
                 "Self.Selected", ".Selected")
    for p_, name, body in all_nodes:
        if (body.get("Control") or "").strip().split("@")[0] != "ModernDropdown":
            continue
        props = body.get("Properties") or {}
        default = (props.get("Default") or "").strip().lstrip("=").strip()
        if not default:
            continue
        if not any(tok in default for tok in RECORDISH):
            problems.append(f"[16] {name}.Default: '{default}' er ikke en "
                            f"record fra Items - compile vil fejle")
            continue

    # Her stod en regel 17: "Default laeser en variabel, men der er ingen
    # OnChange". Den er FJERNET igen. Den gav elleve fund i VH-plan-appen,
    # og alle elleve var falske: dropdownene der laeses som
    # drpVhpPlant.Selected.Value, hvor variablen kun saetter startvaerdien.
    # Moenstret er fuldt gyldigt.
    #
    # Den fejl, den skulle have fanget - at brugerens valg aldrig naaede
    # frem til den variabel, gem-knappen laeser - kraever at vide HVEM der
    # forbruger vaerdien. Det kan en regel paa een kontrol ikke se.
    #
    # Elleve falske fund ville laere nogen at springe advarsler over, og
    # saa gaar regel 15's rigtige fund samme vej.

    # --- 18. Enhver Gallery skal have TabIndex ----------------------------
    # En Gallery er en interaktiv kontrol for tastaturet - ogsaa naar
    # Selectable er false. Uden TabIndex er den ikke et tab stop, og
    # indholdet kan ikke naas uden mus.
    #
    # Den her regel findes, fordi praecis EEN af repoets femten gallerier
    # manglede den. De fjorten andre havde TabIndex: 0, saa det var en
    # forglemmelse og ikke et valg - men den blev foerst fundet af App
    # checker ved et deploy, altsaa efter en hel runde gennem Studio.
    #
    # Reglen daekker KUN Gallery. Knapper og inputs har ikke TabIndex i
    # dette repo, og App checker meldte dem ikke: de faar deres tab stop
    # af sig selv. En bredere regel ville give snesevis af falske fund,
    # og saa ville ingen laese dem (se regel 17, der blev fjernet igen).
    for _p, name, body in all_nodes:
        if body.get("Control") != "Gallery":
            continue
        if "TabIndex" not in (body.get("Properties") or {}):
            problems.append(f"[18] {name}: Gallery uden TabIndex - App checker "
                            f"melder 'Missing tab stop'. Saet TabIndex til 0")

    # --- 19. AccessibleLabel maa ikke vaere kontrollens navn --------------
    # En skaermlaeser laeser AccessibleLabel op. Staar der "inpManufacturer",
    # hoerer brugeren "inp Manufacturer" i stedet for "Fabrikat".
    #
    # Det var 75 felter i tre apps, og det stod der, fordi inputbyggerne
    # falder tilbage paa kontrollens navn, naar kalderen ikke giver en
    # etiket. field_cell retter det nu selv - men et input UDEN for en
    # field_cell har ingen, der kender etiketten, og det er dem, den her
    # regel fanger.
    for _p, name, body in all_nodes:
        acc = (body.get("Properties") or {}).get("AccessibleLabel")
        if acc is None:
            continue
        v = str(acc).strip().lstrip("=").strip().strip('"')
        if v == name:
            problems.append(f"[19] {name}.AccessibleLabel er kontrollens navn "
                            f"- en skaermlaeser laeser det op. Giv label=")

    # --- 20. Flere UAFHAENGIGE hentninger i kaede -> Concurrent -----------
    # Uden Concurrent venter appen paa SUMMEN af kaldene; med den kun paa
    # det laengste.
    #
    # REGLEN SKAL SELV SE AFHAENGIGHEDERNE
    # Foerste udgave taalte kun til to hentninger og advarede. Den gav fire
    # fund, og alle fire var forkerte: dokumentruden laeser den gamle
    # samling, kalder et flow, parser svaret og skriver tilbage - hvert
    # skridt afhaenger af det foer. Concurrent ville have givet en
    # kapploebsfejl, der kun optraadte nogle gange.
    #
    # Nu springes en kaede over, hvis et senere led laeser et tidligere -
    # enten en samling, der lige er fyldt, eller en variabel, der er sat
    # undervejs. Tilbage staar kun de kaeder, hvor der FAKTISK er noget at
    # goere parallelt.
    #
    # Stadig en ADVARSEL og ikke en fejl: om to hentninger er uafhaengige,
    # er til syvende og sidst et menneskes vurdering.
    cc = re.compile(r"\b(?:Clear)?Collect\(\s*(col[A-Z]\w*)\s*,")
    setv = re.compile(r"\bSet\(\s*(var[A-Za-z0-9_]*)\s*,")

    def arg2(text, at):
        """KILDEN i ClearCollect(col, <KILDEN>) - altsaa ANDET argument.

        Foerste udgave returnerede hele argumentlisten, samlingsnavnet
        med. Enhver kilde saa dermed ud til at begynde med "col...", hvert
        hit blev filtreret vaek som "laeser bare en anden samling", og
        reglen kunne ALDRIG fyre. Den stod groen, fordi den var tom."""
        i = text.index("(", at)
        depth, j, q, comma = 0, i, None, -1
        while j < len(text):
            c = text[j]
            if q:
                if c == q:
                    q = None
            elif c in "\"'":
                q = c
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    return text[comma + 1:j] if comma > 0 else ""
            elif c == "," and depth == 1 and comma < 0:
                comma = j
            j += 1
        return ""

    def call_end(text, at):
        """Positionen lige efter det kalds afsluttende parentes."""
        i = text.index("(", at)
        depth, j, q = 0, i, None
        while j < len(text):
            c = text[j]
            if q:
                if c == q:
                    q = None
            elif c in "\"'":
                q = c
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    return j + 1
            j += 1
        return len(text)

    targets = [((b.get("Properties") or {}), n) for _p, n, b in all_nodes]
    targets.append((screen.get("Properties") or {}, "<skaermen>"))
    for props, owner in targets:
        for key, val in props.items():
            if (not isinstance(val, str) or not key.startswith("On")
                    or "Concurrent(" in val):
                continue
            hits = []
            for m in cc.finditer(val):
                src = arg2(val, m.start())
                hits.append((m.group(1), src, m.start()))
            # KUN kilder, der kan naa nettet.
            #
            # En col* er en samling, der allerede ligger i hukommelsen.
            # En literal record eller tabel - { ... } eller [ ... ] - er
            # et skema eller en akkumulering inde i et ForAll. Ingen af
            # delene koster en rundtur, og Concurrent ville derfor ikke
            # goere dem hurtigere; den ville kun goere dem svaerere at
            # laese. Begge gav falske fund, foer de blev filtreret fra:
            # gem/indsend i VH-plan samler raekker i hukommelsen med
            # Collect(col, { ... }) og blev meldt to gange.
            hits = [h for h in hits
                    if not re.match(r"\s*(col[A-Z]|[{\[])", h[1])]
            if len(hits) < 2:
                continue
            # afhaenger et senere led af et tidligere?
            #
            # VINDUET ER HELE TEKSTEN IMELLEM, IKKE KUN KILDEARGUMENTET.
            # Foerste udgave saa kun i den senere Collects ANDET argument.
            # Da gemningen blev lagt om til batch, flyttede afhaengigheden
            # OP i et With, der omslutter kaldet:
            #
            #     With(
            #         { srcOps: Filter(..., LookUp(colVhpSavedItems, ...)) },
            #         ...  ClearCollect(colVhpSavedOps, ForAll(Sequence(...)))
            #     )
            #
            # colVhpSavedItems staar ikke i kildeargumentet, saa reglen
            # meldte to KLART afhaengige hentninger som uafhaengige og bad
            # om et Concurrent, der ville have givet en kapploebsfejl.
            # Nu laeses alt fra det tidligere leds eget navn og frem til
            # enden af det senere kald.
            dependent = False
            for i, (name, _src, pos) in enumerate(hits):
                # start lige EFTER samlingens eget navn, saa Collect'ens
                # egen maalangivelse ikke taeller som en laesning
                here = val.index(name, pos) + len(name)
                for later_name, later_src, lp in hits[i + 1:]:
                    end = call_end(val, lp)
                    if re.search(r"\b%s\b" % re.escape(name), val[here:end]):
                        dependent = True
            for vm in setv.finditer(val):
                v, vpos = vm.group(1), vm.start()
                for _n, src, pos in hits:
                    if pos > vpos and re.search(r"\b%s\b" % re.escape(v), src):
                        dependent = True
            if dependent:
                continue
            names = ", ".join(n for n, _s, _p in hits)
            warnings.append(
                f"[20] {owner}.{key}: {len(hits)} uafhaengige hentninger i "
                f"kaede ({names}). Saml dem i Concurrent() - appen venter "
                f"ellers paa summen. Se build_helpers.concurrent()")

    print(f"Kontroller i alt: {len(all_nodes)}")
    if warnings:
        print(f"\n{len(warnings)} advarsel(er) - byggeriet stopper ikke:\n")
        for x in warnings:
            print("  " + x)
    if problems:
        print(f"\n{len(problems)} problem(er):\n")
        for x in problems:
            print("  " + x)
        return 1
    print("Layout-tjek OK: ingen kontrol-til-kontrol hoejdereferencer, "
          "alle containere er hoeje og brede nok til deres indhold, "
          "alle samlinger findes i App.pa.yaml, og ingen kontrol baerer "
          "en egenskab dens type ikke kender.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
