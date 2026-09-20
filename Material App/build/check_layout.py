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
  8. Enhver samling, skaermen bruger, findes i App.pa.yaml - som navngiven
     formel eller som ClearCollect
  9. Ingen LODRET container har et barn med FillPortions <> 0
     (knapraekken var 336 px bred i et kort med 324 px indhold, ombroed til
     to linjer og fik sin sidste knap klippet af).

Hoejdeudtrykkene evalueres for flere skaermbredder og datamaengder.

    python3 check_layout.py            # finder skaermen selv
    python3 check_layout.py ../ScreenVhPlan.pa.yaml
"""
import os, re, sys, yaml

HERE = os.path.dirname(os.path.abspath(__file__))

# Skaermen findes af sig selv, saa denne fil er ordret ens i alle apps i
# repoet (se .github/skills/canvas-build/SKILL.md). Er der mere end een
# skaerm, angives den paa kommandolinjen.
def _find_screen():
    if len(sys.argv) > 1:
        return sys.argv[1]
    app_dir = os.path.join(HERE, "..")
    found = sorted(f for f in os.listdir(app_dir)
                   if f.startswith("Screen") and f.endswith(".pa.yaml"))
    if len(found) == 1:
        return os.path.join(app_dir, found[0])
    raise SystemExit(
        "Angiv skaermen: python3 check_layout.py ../<Screen>.pa.yaml\n"
        "Fundet: " + (", ".join(found) or "ingen"))


SCREEN = _find_screen()

WIDTHS = [420, 640, 900, 1024, 1366, 1920]
ITEM_COUNTS = [0, 1, 3, 8]
OP_COUNTS = [0, 1, 4, 12]
PKG_COUNTS = [3, 4]

CTRL_HEIGHT_REF = re.compile(r"\b(?:con|gal|txt|btn|drp|num|chk)[A-Za-z0-9_]*\.Height\b")


def _if(c, a, b):
    return a if c else b


def _iferror(a, b):
    return a


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

    e = e.replace("CountRows(colVhpItems)", str(n_items))
    e = e.replace("CountRows(Filter(colVhpOperations, ItemId = varVhpActiveItemId))", str(n_ops))
    e = e.replace("CountRows(Filter(colVhpStrategyPackages, StrategyKey = varVhpPlan.Strategy))", str(n_pkgs))
    e = e.replace("App.Width", str(w)).replace("App.Height", "900")

    # Booleske testvaerdier: det ugunstigste tilfaelde er at alt er synligt.
    e = re.sub(r"varVhpPlan\.PlanType\s*=\s*\"Strategy\"", "True", e)
    e = re.sub(r"IsBlank\(varVhpPlan\.Strategy\)", "False", e)
    e = re.sub(r"IsBlank\(varVhpActiveItemId\)", "False", e)
    e = re.sub(r"\bvarVhp[A-Za-z0-9_]*\b", "True", e)

    e = e.replace("IfError(", "_iferror(").replace("If(", "_if(")
    e = e.replace("&&", " and ").replace("||", " or ")
    e = re.sub(r"\btrue\b", "True", e)
    e = re.sub(r"\bfalse\b", "False", e)
    e = re.sub(r"(?<![<>!=])=(?!=)", "==", e)

    if re.search(r"[A-Za-z_][A-Za-z0-9_.]*\s*\(", e.replace("_if(", "").replace("_iferror(", "").replace("max(", "")):
        return None
    if re.search(r"\b(?!True|False|max|_if|_iferror|and|or|not)[A-Za-z_][A-Za-z0-9_.]*", e):
        return None
    try:
        return float(eval(e, {"__builtins__": {}}, {"_if": _if, "_iferror": _iferror, "max": max, "Max": max,
                                                    "True": True, "False": False}))
    except Exception:
        return None


def collect(nodes, path="", out=None):
    out = [] if out is None else out
    for item in nodes or []:
        (name, body), = item.items()
        p = f"{path}/{name}"
        out.append((p, name, body))
        collect(body.get("Children"), p, out)
    return out


def main():
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
        vertical = "Vertical" in (props.get("LayoutDirection") or "")
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
                            kh = evaluate((kb.get("Properties") or {}).get("Height"), w, ni, no, npk)
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

    # --- 4. Faste bredder i en vandret raekke ------------------------------
    for p, name, body in all_nodes:
        props = body.get("Properties") or {}
        kids = body.get("Children") or []
        if body.get("Control") != "GroupContainer" or not kids:
            continue
        if "Horizontal" not in (props.get("LayoutDirection") or ""):
            continue
        gap = float(re.sub(r"[^0-9.]", "", props.get("LayoutGap", "=8")) or 8)
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
                problems.append(f"[4] {name}: boern {need:.0f} px bredere end raekken {float(m.group(1)):.0f} px")

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
    for p, name, body in all_nodes:
        props = body.get("Properties") or {}
        if props.get("LayoutDirection", "").strip() != "=LayoutDirection.Vertical":
            continue
        for kid in (body.get("Children") or []):
            kname = list(kid.keys())[0]
            kprops = (list(kid.values())[0].get("Properties") or {})
            fp = kprops.get("FillPortions", "=0").strip()
            if fp not in ("=0", "0"):
                problems.append(f"[9] {kname}: FillPortions {fp[:40]} i den LODRETTE "
                                f"container {name} - barnet straekkes i hoejden")

    # --- 8. Samlinger skal findes i App.pa.yaml ---------------------------
    # En skaerm, der bruger colVhpNoget, som ingen definerer, kompilerer ikke
    # - men fejlen dukker foerst op i Studio. Da opslagslisterne blev flyttet
    # fra haardkodede tabeller til navngivne formler, blev tre referencer
    # haengende. Det her fanger det inden synk.
    app_path = os.path.join(os.path.dirname(SCREEN), "App.pa.yaml")
    if os.path.exists(app_path):
        app = open(app_path, encoding="utf-8").read()
        defined = set(re.findall(r"^\s*=?(col[A-Z]\w*)\s*=", app, re.M))
        defined |= set(re.findall(r"ClearCollect\(\s*(col\w+)", app))
        used = set()
        for _, _, body in all_nodes:
            for val in (body.get("Properties") or {}).values():
                if isinstance(val, str):
                    used |= set(re.findall(r"\bcol[A-Z]\w*", val))
        for name in sorted(used - defined):
            problems.append(f"[8] samlingen '{name}' bruges i skaermen, "
                            f"men defineres ikke i App.pa.yaml")

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
                hits = sorted(set(MUT_RE.findall(inner)))
                if hits:
                    warnings.append(
                        f"[15] {name}.{key}: {', '.join(hits)} inde i ForAll "
                        f"- eet kald pr. raekke. Saml skrivningen udenfor")
                    break

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
