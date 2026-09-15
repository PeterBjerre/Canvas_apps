# -*- coding: utf-8 -*-
"""
Traekker SPOOL-arkets valideringsregler ud af VBA-kilden og skriver dem som
CSV, klar til to SharePoint-lister.

    excel/vba/spool-validation/*.bas
        -> sharepoint/seed/MD_FLClass.csv
        -> sharepoint/seed/MD_FLCharacteristic.csv

HVORFOR EN PARSER OG IKKE EN HAANDSKREVET TABEL
-----------------------------------------------
Reglerne er 15 klasser gange op til 12 karakteristikker. Skrevet af i
haanden ville tabellen vaere forkert inden for et aar, og ingen ville
opdage det. Naar den traekkes ud af kilden, kan den koeres igen, naar
arket aendrer sig, og forskellen kan ses i et diff.

HVAD KILDEN SER UD TIL
----------------------
Hver klasseblok i Verification_ClassBlocks.bas har samme form:

    Public Sub ELF_Core(ByVal Class As String)
        formatColumns.Add "Power [kW]", Array(13, "^[0-9,]*$")
        ...
        Verification_Functions.ValidateTable Class, formatColumns
    End Sub

    formatColumns   navn -> (maxlaengde, regex [, paakraevet])
    specialColumns  navn -> tilladte vaerdier, enten en Array(...) i koden
                    eller en navngiven Excel-tabel paa arket "List data"

Verification_StepsConfig.LegacyDefaultStepsFor siger hvilke blokke der
koeres for hvilken klasse. Det er den relation, der goer klasse -> regler
komplet: en klasses regler er dens egen blok PLUS de faelles blokke, dens
trinliste peger paa.
"""

import csv
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VBA = os.path.join(ROOT, "excel", "vba", "spool-validation")
SEED = os.path.join(ROOT, "sharepoint", "seed")

# Blokke der ikke er en FL-klasse, men en faelles regelblok som flere
# klasser deler. De bliver ikke til raekker i MD_FLClass.
SHARED_BLOCKS = {
    "Verify_Master_Data_FL", "TRMNEW", "KKS_Syntax",
    "VerifyFunctionalLocationClasses", "Typekreds", "TestMethod",
    "Design_pressure_", "Operating_pressure_", "Design_temperature_",
    "Operating_temperature_", "Design_flow_", "Equipment_Numbers",
}


def _read(name):
    with open(os.path.join(VBA, name), encoding="utf-8") as fh:
        return fh.read()


def _subs(text):
    """Split en .bas op i {procedurenavn: krop}."""
    out = {}
    cur, body = None, []
    for line in text.splitlines():
        m = re.match(r"^(?:Public |Private )?Sub (\w+)\(", line)
        if m:
            cur, body = m.group(1), []
            continue
        if line.strip() == "End Sub":
            if cur:
                out[cur] = "\n".join(body)
            cur = None
            continue
        if cur is not None:
            body.append(line)
    return out


# Reglerne staar som .Add-kald. Vaerdien er enten en Array(...) i koden
# eller et variabelnavn, der er fyldt fra en navngiven Excel-tabel paa
# arket "List data".
_FMT = re.compile(
    r'formatColumns\.Add\s+(?:"([^"]+)"|(\w+))\s*,\s*'
    r'Array\((\d+)\s*,\s*"((?:[^"]|"")*)"\s*(?:,\s*(True|False))?\)')
_SPECIAL_VAR = re.compile(
    r'specialColumns\.Add\s+(?:"([^"]+)"|(\w+))\s*,\s*(?!Array\b)(\w+)')
_SPECIAL_INLINE = re.compile(
    r'specialColumns\.Add\s+(?:"([^"]+)"|(\w+))\s*,\s*Array\(([^)]*)\)')


def _consts(text):
    """Private Const NAME As String = "value" -> {NAME: value}."""
    out = {}
    for m in re.finditer(r'Const\s+(\w+)\s+As String\s*=\s*"([^"]*)"', text):
        out[m.group(1)] = m.group(2)
    return out


def _table_for_var(body):
    """{variabelnavn: Excel-tabel}.

    Kilden gaar altid gennem det samme mellemled:

        Set tableRange = listWs.ListObjects("Design_flow_uom").Range
        Set tableColumn = tableRange.Columns(1)
        designFlowUOM = Application.Transpose(tableColumn.value)

    Tabellerne LAESES i en anden raekkefoelge end de TILDELES, saa en
    positionsbaseret kobling giver forkerte par. Her bindes variablen i
    stedet til den ListObjects, der staar naermest FOER tildelingen.
    """
    out = {}
    last = None
    for line in body.splitlines():
        m = re.search(r'ListObjects\("([^"]+)"\)', line)
        if m:
            last = m.group(1)
        m = re.match(r'\s*(?:Set\s+)?(\w+)\s*=\s*'
                     r'(?:Application\.Transpose|.*\.DataBodyRange|.*Value2)', line)
        if m and last:
            out[m.group(1)] = last
    return out


def _class_guard(body):
    """Linjenummer -> den klasseliste, linjen er indhegnet af.

    TRMNEW tilfoejer Fire Classification og Fire Sealing KUN for MKP og
    NO CLASS. Uden det her ville ELF arve regler, den ikke har.
    """
    guard = {}
    stack = []
    for n, line in enumerate(body.splitlines()):
        t = line.strip()
        m = re.match(r'If\s+Class\s*=\s*"([^"]+)"'
                     r'(?:\s+Or\s+Class\s*=\s*"([^"]+)")*\s+Then', t)
        if m:
            stack.append([g for g in re.findall(r'"([^"]+)"', t)])
        elif t.startswith("If ") and t.endswith(" Then"):
            stack.append(None)          # en betingelse vi ikke laeser
        elif t == "End If" and stack:
            stack.pop()
        classes = None
        for s_ in stack:
            if s_ is not None:
                classes = s_ if classes is None else classes
        guard[n] = classes
    return guard


def _line_of(body, pos):
    return body.count("\n", 0, pos)


def parse_block(body, consts):
    """En _Core-krop -> liste af regeldicts."""
    rules = []
    tvar = _table_for_var(body)
    guard = _class_guard(body)

    def add(name, maxlen, pattern, required, allowed, table, pos):
        rules.append({"name": name, "maxlen": maxlen, "pattern": pattern,
                      "required": required, "allowed": allowed, "table": table,
                      "only": guard.get(_line_of(body, pos))})

    for m in _SPECIAL_VAR.finditer(body):
        name = m.group(1) or consts.get(m.group(2), m.group(2))
        add(name, "", "", "", "", tvar.get(m.group(3), ""), m.start())

    for m in _SPECIAL_INLINE.finditer(body):
        name = m.group(1) or consts.get(m.group(2), m.group(2))
        allowed = ";".join(v.strip().strip('"') for v in m.group(3).split(",")
                           if v.strip().strip('"'))
        add(name, "", "", "", allowed, "", m.start())

    for m in _FMT.finditer(body):
        name = m.group(1) or consts.get(m.group(2), m.group(2))
        add(name, m.group(3), m.group(4).replace('""', '"'),
            "Ja" if m.group(5) == "True" else "Nej", "", "", m.start())
    return rules


def parse_steps():
    """LegacyDefaultStepsFor -> {klasse: [trin, ...]}."""
    text = _read("Verification_StepsConfig.bas")
    out = {}
    for m in re.finditer(r'd\("([^"]+)"\)\s*=\s*Array\(([^)]*)\)', text):
        out[m.group(1)] = [s.strip().strip('"')
                           for s in m.group(2).split(",") if s.strip()]
    return out


def main():
    blocks, consts = {}, {}
    for fname in ("Verification_ClassBlocks.bas", "Verification_MasterData.bas",
                  "Verification_EquipmentNumbers.bas",
                  "Verification_ClassRules.bas"):
        text = _read(fname)
        consts.update(_consts(text))
        for sub, body in _subs(text).items():
            if sub.endswith("_Core"):
                # Design_pressure_Core hedder Design_pressure_ i trinlisten,
                # ELF_Core hedder ELF. Begge former slaas op.
                base = sub[:-len("_Core")]
                blocks[base] = body
                blocks[base + "_"] = body

    steps = parse_steps()
    os.makedirs(SEED, exist_ok=True)

    # --- MD_FLClass: en raekke pr. klasse, med dens trinliste ---
    classes = sorted(k for k in steps if k not in SHARED_BLOCKS)
    p1 = os.path.join(SEED, "MD_FLClass.csv")
    with open(p1, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["ClassKey", "VerifySteps", "StepCount"])
        for c in classes:
            w.writerow([c, ";".join(steps[c]), len(steps[c])])

    # --- MD_FLCharacteristic: en raekke pr. klasse x karakteristik ---
    # En klasses regler er dens egen blok plus de faelles blokke, dens
    # trinliste peger paa. Derfor udfoldes trinlisten her.
    p2 = os.path.join(SEED, "MD_FLCharacteristic.csv")
    rows, missing = [], set()
    for c in classes:
        # Et felt kan staa i BEGGE ordboeger - Plant har baade en
        # vaerdiliste og en maks. laengde med Required. De to regler skal
        # samles til EEN raekke, ikke konkurrere om pladsen: droppes
        # format-raekken, forsvinder Required lydloest.
        merged = {}
        order = []
        for step in steps[c]:
            body = blocks.get(step)
            if body is None:
                missing.add(step)
                continue
            for r in parse_block(body, consts):
                if r["only"] and c not in r["only"]:
                    continue
                cur = merged.get(r["name"])
                if cur is None:
                    merged[r["name"]] = dict(r, step=step)
                    order.append(r["name"])
                    continue
                for k in ("maxlen", "pattern", "required", "allowed", "table"):
                    if not cur[k] and r[k]:
                        cur[k] = r[k]
        for name in order:
            r = merged[name]
            rows.append([c, name, r["maxlen"], r["pattern"], r["required"],
                         r["allowed"], r["table"], r["step"]])
    with open(p2, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["ClassKey", "Characteristic", "MaxLength", "Pattern",
                    "Required", "AllowedValues", "SourceTable", "FromStep"])
        w.writerows(rows)

    print("MD_FLClass.csv          %3d klasser" % len(classes))
    print("MD_FLCharacteristic.csv %3d regler" % len(rows))
    if missing:
        # Trin uden en _Core-blok er ikke felt-validering (KKS-syntaks,
        # klasseopslag). De hoerer til i appens kode, ikke i en liste.
        print("trin uden regelblok:    %s" % ", ".join(sorted(missing)))


if __name__ == "__main__":
    main()
