# -*- coding: utf-8 -*-
"""
Traekker SPOOL-arkets vaerdilister og opslagstabeller ud til seed-CSV.

    python3 tools/extract_spool_lists.py <sti til FL_indberetninger...xlsm>

        -> sharepoint/seed/MD_FLValueList.csv   dropdown-vaerdier
        -> sharepoint/seed/MD_FLKey.csv         klassebestemmelsens opslag

HVORFOR TO LISTER OG IKKE EEN
------------------------------
De to slags data bruges forskellige steder. Vaerdilisterne fylder en
dropdown og valideres mod, naar brugeren har skrevet noget.
Opslagstabellerne laeses derimod ud fra selve KKS-koden, foer brugeren har
udfyldt noget som helst, og afgoer hvilken klasse raekken faar - og dermed
hvilke felter der overhovedet skal vises.

SCEq ER IKKE EN LISTE, MEN SEKSTEN
-----------------------------------
SCEq-tabellen har en kolonne pr. klasse, hver med sine egne gyldige
vaerdier. VBA'en slaar op med sceTable.ListColumns(Class). Den foldes ud
her, saa hver klasse faar sine egne raekker under ListName "SCEq:<klasse>"
- ellers ville en ELF kunne vaelge en MKP-vaerdi.
"""

import csv
import io
import os
import sys
import warnings

warnings.filterwarnings("ignore")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = os.path.join(ROOT, "sharepoint", "seed")

# Vaerdilister paa arket "List data". Navnet i arket -> navnet i appen.
# Table20 og Table10 hedder ikke noget i Excel; her faar de et navn, der
# siger hvad de er.
VALUE_TABLES = {
    "TypekredsTabel": "Typekreds",
    "TestMethod": "TestMethod",
    "FireClassification": "FireClassification",
    "Table20": "FireSealingType",
    "Design_pressure_uom": "Design_pressure_uom",
    "Design_Temp_uom": "Design_Temp_uom",
    "Design_flow_uom": "Design_flow_uom",
    "Plant": "Plant",
    "EQ_Cat": "EquipmentCategory",
}

# Opslagstabeller paa arket "DictionaryTable".
# navn -> (KeyType, kolonne med noeglen, kolonne med klassen/vaerdien)
KEY_TABLES = {
    "ClassDeterminationComponentKey": ("Component", 0, 1),
    "ClassDeterminationAggregateKey": ("Aggregate", 0, 1),
    "FunctionKeyDict": ("Function", 0, None),
    "BR18_Keys": ("BR18", 0, 1),
}


def write_seed(path, header, rows):
    """Samme format som de oevrige seed-filer: komma, BOM, alt citeret."""
    with io.open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL)
        w.writerow(header)
        w.writerows(rows)


def table_rows(wb, sheet, name):
    """En navngiven Excel-tabel -> liste af raekker, uden overskriften."""
    ws = wb[sheet]
    ref = ws.tables[name].ref
    rows = [[c.value for c in r] for r in ws[ref]]
    return rows[0], rows[1:]


def _clean(v):
    if v is None:
        return ""
    return str(v).strip()


def main():
    if len(sys.argv) < 2:
        sys.exit("brug: extract_spool_lists.py <sti til .xlsm>")
    path = sys.argv[1]
    if not os.path.exists(path):
        sys.exit("findes ikke: %s" % path)

    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True)

    # ---- vaerdilister ----------------------------------------------------
    values = []
    for xl_name, list_name in sorted(VALUE_TABLES.items()):
        head, rows = table_rows(wb, "List data", xl_name)
        for i, r in enumerate(rows, 1):
            v = _clean(r[0])
            if not v:
                continue
            # Plant og EQ_Cat har en ekstra kolonne (nummer / beskrivelse).
            # Den er det, brugeren ser; noeglen er det, der gemmes.
            extra = _clean(r[1]) if len(r) > 1 else ""
            values.append([list_name, v, extra, i])

    # SCEq foldes ud pr. klasse
    head, rows = table_rows(wb, "List data", "SCEq")
    for col, cls in enumerate(head):
        cls = _clean(cls)
        if not cls or cls == "SCEq":
            continue
        n = 0
        for r in rows:
            v = _clean(r[col]) if col < len(r) else ""
            if not v:
                continue
            n += 1
            values.append(["SCEq:" + cls, v, "", n])

    write_seed(os.path.join(SEED, "MD_FLValueList.csv"),
               ["ListName", "Value", "Value2", "Sort"], values)

    # ---- opslagstabeller -------------------------------------------------
    keys, dropped = [], 0
    for xl_name, (kind, ki, vi) in sorted(KEY_TABLES.items()):
        head, rows = table_rows(wb, "DictionaryTable", xl_name)
        # VBA laeser tabellen med dict(key) = value - en TILDELING, ikke
        # .Add. Dubletter overskriver derfor hinanden, og den sidste
        # vinder. Her gores det samme, saa listen indeholder praecis det
        # arket selv ender med.
        seen = {}
        order = []
        for r in rows:
            k = _clean(r[ki]).upper()
            if not k:
                continue
            val = _clean(r[vi]) if vi is not None and vi < len(r) else ""
            # BR18: noeglen er key12, vaerdien er den tilladte key17.
            # Beskrivelsen staar i tredje kolonne.
            desc = _clean(r[2]) if len(r) > 2 else ""
            # BR18 har flere raekker pr. key12 med vilje - det er en
            # vaerdiliste, ikke et opslag. Der maa ikke dedupliceres.
            uniq = (k, val) if kind == "BR18" else k
            if uniq in seen:
                dropped += 1
            else:
                order.append(uniq)
            seen[uniq] = [kind, k, val, desc]
        keys.extend(seen[u] for u in order)

    write_seed(os.path.join(SEED, "MD_FLKey.csv"),
               ["KeyType", "KeyValue", "Value", "Description"], keys)

    # ---- opsummering -----------------------------------------------------
    names = {}
    for r in values:
        names[r[0]] = names.get(r[0], 0) + 1
    print("MD_FLValueList.csv %4d vaerdier i %d lister" % (len(values), len(names)))
    for n in sorted(names):
        print("    %-28s %4d" % (n, names[n]))
    kinds = {}
    for r in keys:
        kinds[r[0]] = kinds.get(r[0], 0) + 1
    print("MD_FLKey.csv       %4d opslag (%d dubletter overskrevet)"
          % (len(keys), dropped))
    for n in sorted(kinds):
        print("    %-28s %4d" % (n, kinds[n]))


if __name__ == "__main__":
    main()
