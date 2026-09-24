# -*- coding: utf-8 -*-
"""
Efterproever, at hver SharePoint-kolonne en skaerm bruger, FINDES.

    python3 tools/check_datasources.py

HVORFOR
-------
Power Fx binder SharePoint-kolonner paa VISNINGSNAVN. En tastefejl - eller en
kolonne, der hedder noget andet end man tror - opdages foerst, naar Studio
kompilerer. Hver af de runder koster tid og tokens.

Udtraekket i sharepoint/inspect/out/schema.json er facit. Det her tjek
sammenholder formlerne med det, saa fejlen findes her i stedet.

Tre gange i dette projekt har praecis den fejl kostet en runde:
    MD_RequestIndex.Title      -> hedder RequestNo i Power Fx
    MD_Strategy.Title          -> hedder StrategyKey
    MaintenancePlans.CallHorizon0 -> hedder CallHorizon

HVAD DER TJEKKES
----------------
    Patch(Liste, ..., { felt: ... })     felterne oeverst i recorden
    Choices(Liste.Kolonne)
    LookUp/Filter/Sort/Distinct/RemoveIf(Liste, Kolonne ...)
    ForAll(Liste As R, ...) efterfulgt af R.Kolonne
    valgvaerdier: { Value: "X" } paa en Choice-kolonne

Moenstre, der ikke kan afgoeres sikkert, springes over frem for at melde
falsk alarm. Tjekket siger til sidst, hvor meget det naaede at daekke.
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(ROOT, "sharepoint", "inspect", "out", "schema.json")

# Felter enhver liste har, uanset hvad udtraekket viser.
#
# "Title" staar bevidst IKKE her. Den er ganske vist indbygget, men dens
# VISNINGSNAVN kan vaere aendret - MD_RequestIndex.Title hedder RequestNo og
# MD_Strategy.Title hedder StrategyKey i Power Fx. Skemaet ved det; en
# haardkodet undtagelse ville lukke oejnene for praecis den fejl.
BUILTIN = {"ID", "Created", "Modified", "Author", "Editor"}

# Power Fx-funktioner der tager (kilde, kolonneudtryk ...).
COL_FUNCS = ("LookUp", "Filter", "Sort", "SortByColumns", "Distinct",
             "RemoveIf", "UpdateIf", "First", "CountRows", "Search")


def load_schema():
    if not os.path.exists(SCHEMA):
        return None
    d = json.load(open(SCHEMA, encoding="utf-8-sig"))
    out = {}
    for l in d["lists"]:
        cols, choices = {}, {}
        for f in l["fields"]:
            name = f.get("displayName") or f.get("internalName")
            cols[name] = f.get("type")
            ch = f.get("choices")
            if isinstance(ch, str):
                ch = [ch]
            if ch:
                choices[name] = [str(c).replace("<CHOICE>", "").strip() for c in ch]
        out[l["title"]] = {"cols": cols, "choices": choices}
    return out


def formulas(path):
    """Alle Power Fx-udtryk i en .pa.yaml, som een streng pr. egenskab."""
    txt = open(path, encoding="utf-8").read()
    # Egenskaber staar som "Navn: |-" efterfulgt af indrykkede linjer med "=".
    out = []
    cur, indent = None, 0
    for line in txt.split("\n"):
        m = re.match(r"^(\s*)([A-Za-z_][\w]*): \|-?\s*$", line)
        if m:
            if cur is not None:
                out.append("\n".join(cur))
            cur, indent = [], len(m.group(1))
            continue
        if cur is not None:
            if line.strip() == "" or len(line) - len(line.lstrip()) > indent:
                cur.append(line.strip())
            else:
                out.append("\n".join(cur))
                cur = None
    if cur is not None:
        out.append("\n".join(cur))
    return out


def split_args(s, open_paren):
    """Argumenterne i et funktionskald, delt paa kommaer i TOPNIVEAU.

    Uden det bliver et hvilket som helst "{" efter Patch( laest som en
    feltrecord - ogsaa With-blokke og opslagsvaerdier. Det gav 90 falske
    alarmer i foerste udgave."""
    args, depth, cur, i, n = [], 0, [], open_paren + 1, len(s)
    in_str = False
    while i < n:
        c = s[i]
        if in_str:
            cur.append(c)
            if c == '"':
                in_str = False
        elif c == '"':
            in_str = True
            cur.append(c)
        elif c in "([{":
            depth += 1
            cur.append(c)
        elif c in ")]}":
            if depth == 0 and c == ")":
                args.append("".join(cur))
                return args, i
            depth -= 1
            cur.append(c)
        elif c == "," and depth == 0:
            args.append("".join(cur))
            cur = []
        else:
            cur.append(c)
        i += 1
    args.append("".join(cur))
    return args, n


def calls(fx, name):
    """(argumenter, slutposition) for hvert kald af funktionen `name`."""
    out = []
    for m in re.finditer(rf"\b{name}\(", fx):
        args, end = split_args(fx, m.end() - 1)
        out.append((args, end))
    return out


def top_keys(rec):
    """Noeglerne oeverst i en record-literal "{ a: .., b: .. }"."""
    rec = rec.strip()
    if not rec.startswith("{"):
        return None
    inner, _ = split_args(rec.replace("{", "(", 1)[:-1] + ")", 0) if False else (None, None)
    # Del paa kommaer i topniveau inde i klammerne.
    body = rec[1:-1]
    parts, depth, cur, in_str = [], 0, [], False
    for c in body:
        if in_str:
            cur.append(c)
            if c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True; cur.append(c); continue
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        if c == "," and depth == 0:
            parts.append("".join(cur)); cur = []
        else:
            cur.append(c)
    parts.append("".join(cur))
    keys = []
    for part in parts:
        m = re.match(r"\s*('[^']+'|[A-Za-z_]\w*)\s*:", part)
        if m:
            keys.append((m.group(1).strip("'"), part[m.end():]))
    return keys


def first_ident(expr):
    m = re.match(r"\s*('[^']+'|[A-Za-z_]\w*)", expr)
    return m.group(1).strip("'") if m else None


# Kolonnetyper der SKAL have en record: { Value: .. } eller { Id: .., Value: .. }
RECORD_TYPES = {"Choice", "MultiChoice", "Lookup", "LookupMulti", "User", "UserMulti"}
# Kolonnetyper der skal have en skalar
SCALAR_TYPES = {"Text", "Note", "Number", "Currency", "DateTime", "Boolean", "URL"}


def check_shape(lst, col, val, meta):
    """Passer formen paa vaerdien til kolonnens type?

    Kun LITTERALE former afgoeres. Er vaerdien et udtryk - LookUp(..).Felt,
    en variabel, en If - kan typen ikke ses herfra, og saa siges der intet
    frem for at melde falsk alarm.

    Det er praecis den fejl, compile fandt og dette tjek IKKE fangede:
    'CallHorizon' fik et tal, men datakilden ventede en record. Vaerdien var
    et LookUp-udtryk, saa formen alene kunne ikke afgoere det - men den
    omvendte fejl, en record i en talkolonne eller en bar streng i en
    valgkolonne, fanges nu."""
    t = meta["cols"].get(col)
    v = val.strip()
    if not t:
        return None

    is_record = v.startswith("{")
    # Blank(), If(...) og udtryk kan vaere begge dele - de springes over.
    is_literal = is_record or v.startswith('"') or re.fullmatch(r"-?\d+(\.\d+)?", v) \
        or v in ("true", "false")

    if t in RECORD_TYPES:
        if is_literal and not is_record:
            return (f"{col}: kolonnen er {t} og skal have en record "
                    f"(fx {{ Value: \"...\" }}), men faar {v[:40]}")
        if is_record and meta["choices"].get(col):
            m = re.match(r'\{\s*Value:\s*"([^"]*)"\s*\}\s*$', v)
            if m and m.group(1) not in meta["choices"][col]:
                return (f"{col}: valgvaerdien \"{m.group(1)}\" findes ikke. "
                        f"Gyldige: " + ", ".join(meta["choices"][col][:6]))
    elif t in SCALAR_TYPES and is_record:
        return (f"{col}: kolonnen er {t}, men faar en record {v[:40]}")
    return None


def check(path, schema, problems, stats, used=None):
    def scoped_names(fx):
        """Navne, der er LOKALE i formlen - ikke lister.

        With({ ops: ... }) og "Filter(...) As SEL" laver navne, der ligner
        et listenavn i Filter(ops, ...). Uden den her blev de meldt som
        stavefejl i et listenavn, saa snart en liste, der kun LAESES,
        begyndte at taelle med."""
        out = set(re.findall(r"\bAs\s+([A-Za-z_]\w*)", fx))
        for m in re.finditer(r"\bWith\s*\(\s*\{", fx):
            i, depth = m.end() - 1, 0
            j = i
            while j < len(fx):
                if fx[j] == "{":
                    depth += 1
                elif fx[j] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            body = fx[i + 1:j]
            out.update(re.findall(r"(?:^|,)\s*([A-Za-z_]\w*)\s*:", body))
        return out

    for fx in formulas(path):
        scoped = scoped_names(fx)
        # --- Patch(Liste, base, {felter} ...) ----------------------------
        for args, _ in calls(fx, "Patch"):
            if len(args) < 3:
                continue
            lst = args[0].strip()
            if used is not None:
                used.add(lst)
            if lst not in schema:
                continue
            meta = schema[lst]
            for rec in args[2:]:
                keys = top_keys(rec)
                if not keys:
                    continue
                if set(k for k, _ in keys) <= {"Id", "Value"}:
                    continue          # en opslagsvaerdi, ikke felter
                for k, val in keys:
                    stats["checked"] += 1
                    if k not in meta["cols"] and k not in BUILTIN:
                        problems.append((lst, f"Patch skriver '{k}', som ikke "
                                              f"findes som kolonne"))
                    else:
                        shape_problem = check_shape(lst, k, val, meta)
                        if shape_problem:
                            problems.append((lst, shape_problem))

        # --- Choices(Liste.Kolonne) -------------------------------------
        for m in re.finditer(r"Choices\(\s*([A-Za-z_]\w*)\.([A-Za-z_]\w*)\s*\)", fx):
            lst, col = m.group(1), m.group(2)
            if lst not in schema:
                continue
            stats["checked"] += 1
            meta = schema[lst]
            if col not in meta["cols"] and col not in BUILTIN:
                problems.append((lst, f"Choices() paa '{col}', som ikke findes"))
            elif meta["cols"].get(col) != "Choice":
                problems.append((lst, f"{col}: Choices() bruges, men kolonnen er "
                                      f"{meta['cols'].get(col)}, ikke Choice"))

        # --- fn(Liste, Kolonne ...) -------------------------------------
        for fn in COL_FUNCS:
            for args, _ in calls(fx, fn):
                if len(args) < 2:
                    continue
                lst = args[0].strip()
                # EN LISTE, DER KUN LAESES, TAELLER OGSAA SOM BRUGT
                #
                # used blev foer kun fyldt af Patch. En liste, appen
                # aldrig skriver i, kunne derfor hedde hvad som helst -
                # den blev sprunget over i stilhed sammen med alle sine
                # kolonner. MD_HelpText var praecis saadan en: laest af
                # en navngiven formel, skrevet af ingen.
                if (used is not None and re.fullmatch(r"[A-Za-z_]\w*", lst)
                        and lst not in scoped):
                    used.add(lst)
                if lst not in schema:
                    continue
                col = first_ident(args[1])
                if not col or col in ("SortOrder", "true", "false", "Value", "Blank"):
                    continue
                # Kun naar det FAKTISK ligner en kolonne: efterfulgt af en
                # operator eller argumentets slutning.
                if not re.match(rf"\s*'?{re.escape(col)}'?\s*($|[=<>,)])", args[1]):
                    continue
                stats["checked"] += 1
                if col not in schema[lst]["cols"] and col not in BUILTIN:
                    problems.append((lst, f"{fn}() bruger kolonnen '{col}', "
                                          f"som ikke findes"))

        # --- ForAll(Liste As R, krop) -> R.Kolonne ----------------------
        for args, _ in calls(fx, "ForAll"):
            if len(args) < 2:
                continue
            m = re.match(r"\s*(.+?)\s+As\s+([A-Za-z_]\w*)\s*$", args[0], re.S)
            if not m:
                continue
            src, alias = m.group(1).strip(), m.group(2)
            # KILDEN BEHOEVER IKKE VAERE ET NAVN
            #
            # Her stod ([A-Za-z_]\w*), altsaa kun "ForAll(Liste As R".
            # Den navngivne formel for hjaelpeteksterne er
            # "ForAll(Filter(MD_HelpText, ...) As R, { Key: R.HelpKey ... })",
            # og dens fem kolonner blev derfor aldrig efterproevet.
            lst = src if re.fullmatch(r"[A-Za-z_]\w*", src) else first_ident(src)
            if not lst or lst not in schema:
                continue
            body = ",".join(args[1:])
            for m2 in re.finditer(rf"\b{alias}\.('[^']+'|[A-Za-z_]\w*)", body):
                col = m2.group(1).strip("'")
                stats["checked"] += 1
                if col not in schema[lst]["cols"] and col not in BUILTIN:
                    problems.append((lst, f"{alias}.{col} - kolonnen findes ikke"))


def provisioned_columns():
    """Kolonner, som et provisioneringsscript opretter.

    En kolonne, der er lagt ind i scriptet, men endnu ikke oprettet i
    SharePoint, er ikke en kodefejl - den er en paamindelse om at koere
    scriptet. De to skal holdes fra hinanden, ellers er tjekket roedt af
    gode grunde og bliver ignoreret."""
    out = set()
    d = os.path.join(ROOT, "sharepoint", "provision")
    if not os.path.isdir(d):
        return out
    for fn in os.listdir(d):
        if not fn.endswith(".ps1"):
            continue
        txt = open(os.path.join(d, fn), encoding="utf-8-sig").read()
        for m in re.finditer(r"(?:Add-Col|New-MdField|New-MdNoteField|New-IdxField)\s+'?([\w ]+)'?\s+'?([\w]+)'?", txt):
            out.add((m.group(1).strip(), m.group(2).strip()))
        for m in re.finditer(r"Add-Col\s+'([^']+)'\s+'?([\w]+)'?", txt):
            out.add((m.group(1).strip(), m.group(2).strip()))
    return out


def provisioned_choices():
    """Valgvaerdier, som et provisioneringsscript opretter.

    Samme sondring som for kolonner: en vaerdi, der er lagt ind i
    scriptet, men endnu ikke oprettet i SharePoint, er ikke en kodefejl -
    den er en paamindelse om at koere scriptet og eksportere skemaet igen.
    Uden den blev byggeriet roedt af en god grund, og saa bliver det
    ignoreret naeste gang det er roedt af en daarlig.

    To former laeses:
        -Choices 'a','b','c'        direkte paa feltet
        $NAVN = 'a', 'b', 'c'       en variabel, der sendes som -Choices
    """
    out = set()
    d = os.path.join(ROOT, "sharepoint", "provision")
    if not os.path.isdir(d):
        return out
    for fn in os.listdir(d):
        if not fn.endswith(".ps1"):
            continue
        txt = open(os.path.join(d, fn), encoding="utf-8-sig").read()
        for m in re.finditer(r"-Choices\s+((?:'[^']*'\s*,\s*)*'[^']*')", txt):
            out.update(re.findall(r"'([^']*)'", m.group(1)))
        for m in re.finditer(r"^\s*\$[A-Za-z_]\w*\s*=\s*"
                             r"((?:'[^']*'\s*,\s*)+'[^']*')\s*$", txt, re.M):
            out.update(re.findall(r"'([^']*)'", m.group(1)))
    return out


def provisioned_lists():
    """Lister, som et provisioneringsscript opretter."""
    out = set()
    d = os.path.join(ROOT, "sharepoint", "provision")
    if not os.path.isdir(d):
        return out
    for fn in os.listdir(d):
        if not fn.endswith(".ps1"):
            continue
        txt = open(os.path.join(d, fn), encoding="utf-8-sig").read()
        for m in re.finditer(r"(?:New-MdList|New-PnPList)\s+(?:-Title\s+)?'([^']+)'", txt):
            out.add(m.group(1).strip())
        # New-PnPList -Title $LIST_NAME: navnet staar i en variabel
        # oeverst i scriptet. Uden den her linje var listen usynlig
        # for tjekket, og alle dens kolonner med den.
        for m in re.finditer(r"(?:New-MdList|New-PnPList)\s+(?:-Title\s+)?\$(\w+)", txt):
            v = re.search(r"^\s*\$%s\s*=\s*'([^']+)'" % m.group(1),
                          txt, re.M)
            if v:
                out.add(v.group(1).strip())
    return out


def named_formulas():
    """Navnene i hver apps App.Formulas: linjer paa formen "navn = ..."."""
    out = set()
    for app in os.listdir(ROOT):
        path = os.path.join(ROOT, app, "App.pa.yaml")
        if not os.path.isfile(path):
            continue
        txt = open(path, encoding="utf-8").read()
        m = re.search(r"^    Formulas: \|\n((?:      .*\n|\n)*)", txt, re.M)
        if m:
            out.update(re.findall(r"^      =?([A-Za-z_]\w*)\s*=", m.group(1), re.M))
    return out


def main():
    schema = load_schema()
    if schema is None:
        print(f"Finder ikke {SCHEMA}.")
        print("Koer Export-ListSchema.ps1 foerst - uden udtraekket kan "
              "kolonnenavnene ikke efterproeves.")
        return 0   # ikke en fejl i koden, blot manglende facit

    problems, stats = [], {"checked": 0}
    prov = provisioned_columns()
    prov_choices = provisioned_choices()
    screens = []
    for app in ("Maintenance Plan App", "Masterdata Hub",
                "Equipment App", "Material App", "Functional Location App"):
        d = os.path.join(ROOT, app)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".pa.yaml"):
                screens.append(os.path.join(d, fn))

    used = set()
    for path in screens:
        check(path, schema, problems, stats, used)

    # En liste, der slet ikke findes i skemaet, blev foer sprunget over i
    # STILHED - saa en tastefejl i et listenavn, eller en liste ingen havde
    # oprettet, gik lige igennem. Det var praecis, hvad der skete, da
    # MD_TasklistMaterial og MD_TasklistAttachment blev taget i brug: hele
    # skrivningen var ukontrolleret, og tjekket sagde god for den.
    #
    # colVhp* er appens EGNE samlinger, ikke SharePoint-lister. De patches
    # praecis som en liste, saa de ender i samme opsamling og skal sorteres
    # fra her - ellers melder tjekket dem som stavefejl.
    prov_lists = provisioned_lists()
    # NAVNGIVNE FORMLER er heller ikke lister. De bruges i LookUp og Filter
    # ligesom en liste, men de er defineret i App.Formulas - fx
    # Functional Location-appens regeltabeller (nfFlPlan ...).
    named = named_formulas()
    missing = {l for l in used - set(schema)
               if not l.startswith("col") and l not in named}
    missing_known = sorted(l for l in missing if l in prov_lists)
    missing_unknown = sorted(l for l in missing if l not in prov_lists)

    # Dubletter: samme fejl staar typisk i flere egenskaber.
    seen, uniq, pending = set(), [], []
    for lst, msg in problems:
        key = (lst, msg)
        if key in seen:
            continue
        seen.add(key)
        m = re.search(r"'([\w]+)'", msg)
        mv = re.search(r'valgvaerdien "([^"]*)" findes ikke', msg)
        if m and (lst, m.group(1)) in prov:
            pending.append(f"{lst}.{m.group(1)}")
        elif mv and mv.group(1) in prov_choices:
            pending.append("%s (valgvaerdi \"%s\")" % (lst, mv.group(1)))
        else:
            uniq.append(f"{lst}: {msg}")

    print(f"Datakilde-tjek: {len(screens)} fil(er), {len(schema)} lister i skemaet, "
          f"{stats['checked']} kolonnereferencer efterproevet.")
    if missing_known:
        print(f"\n{len(missing_known)} liste(r) oprettes af provisioneringen, men "
              f"findes ikke i udtraekket endnu:")
        for x in missing_known:
            print("  " + x)
        print("  -> koer provisioneringen, og eksporter skemaet igen. "
              "Kolonnerne i dem er IKKE efterproevet.")
    if pending:
        print(f"\n{len(pending)} kolonne(r) oprettes af provisioneringen, men "
              f"findes ikke i udtraekket endnu:")
        for x in sorted(set(pending)):
            print("  " + x)
        print("  -> koer sharepoint/provision-scriptet, og eksporter skemaet igen.")
    for l in missing_unknown:
        uniq.append(f"{l}: listen findes hverken i skemaet eller i et "
                    f"provisioneringsscript - er navnet stavet rigtigt?")
    if uniq:
        print(f"\n{len(uniq)} problem(er):\n")
        for p in uniq:
            print("  " + p)
        print("\nFacit er sharepoint/inspect/out/schema.md. Husk at Power Fx "
              "binder paa VISNINGSNAVN.")
        print("Er kolonnen NETOP oprettet, er udtraekket forældet - koer "
              "Export-ListSchema.ps1 igen.")
        return 1
    print("Alle kolonner og valgvaerdier findes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
