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
     (knapraekken var 336 px bred i et kort med 324 px indhold, ombroed til
     to linjer og fik sin sidste knap klippet af).

Hoejdeudtrykkene evalueres for flere skaermbredder og datamaengder.

    python3 check_layout.py
"""
import os, re, sys, yaml

HERE = os.path.dirname(os.path.abspath(__file__))
SCREEN = os.path.join(HERE, "..", "ScreenVhPlan.pa.yaml")

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

    print(f"Kontroller i alt: {len(all_nodes)}")
    if problems:
        print(f"\n{len(problems)} problem(er):\n")
        for x in problems:
            print("  " + x)
        return 1
    print("Layout-tjek OK: ingen kontrol-til-kontrol hoejdereferencer, "
          "og alle containere er hoeje og brede nok til deres indhold.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
