# -*- coding: utf-8 -*-
"""
Skriver ../App.pa.yaml: navngivne formler + OnStart.

REGLERNE ER NAVNGIVNE FORMLER
-----------------------------
Planen pr. klasse, listerne, kolonnerne og noeglerne er DATA - foldet ud af
html/*.js af tools/fl/harness.js til fl_rules.generated.json. De staar her
som navngivne formler: de evalueres foerst, naar de bruges, og koster
ingen datahentning ved opstart (SKILL.md, regel 7).

De ligger IKKE i SharePoint-lister, af to grunde (docs/31 PX1, PX5):
IsMatch kraever konstante moenstre, og de 6.441 funktionsnoegler kan ikke
slaas op delegerbart pr. raekke. Siden har dem ogsaa i klienten
(lookups.generated.js).

OnStart HENTER INGEN DATA
-------------------------
Her staar kun skemaet for de samlinger, appen skriver i, og de variabler,
skaermen laeser, foer den er vist. Dyblinket (?reqid=) haandteres i
skaermens OnVisible.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "tools"))

import design_tokens as tok
import layout_tokens as lay
import fl_config as cfg
from fl_validation import CALC_SCHEMA

OUT_DIR = os.path.join(HERE, "..")
R = cfg.rules()


def _q(s):
    return '"' + str(s).replace('"', '""') + '"'


def _v(x):
    if isinstance(x, bool):
        return "true" if x else "false"
    if isinstance(x, (int, float)):
        return str(x)
    return _q(x)


def _table(name, rows, cols, comment):
    lines = [f"// {comment}", f"{name} = Table("]
    recs = []
    for r in rows:
        recs.append("    { " + ", ".join(f"{c}: {_v(r[c])}" for c in cols) + " }")
    lines.append(",\n".join(recs))
    lines.append(");")
    return "\n".join(lines)


def _function_keys():
    """De 6.441 noegler som EEN streng "0ABA0ABB0...0", delt i stykker a
    ca. 4.000 tegn, saa ingen linje i formlen bliver uoverskuelig lang.
    Separatoren er et ciffer - se fl_validation.fk_hit."""
    keys = R["functionKeys"]
    bad = [k for k in keys if not k.isalpha()]
    if bad:
        raise SystemExit("Funktionsnoegler med andet end bogstaver: %s - separatoren "
                         "'0' i nfFlFunctionKeys holder ikke laengere." % bad[:5])
    chunks, cur = [], "0"
    for k in keys:
        piece = k + "0"
        if len(cur) + len(piece) > 4000:
            chunks.append(cur)
            cur = ""
        cur += piece
    chunks.append(cur)
    body = " &\n    ".join(_q(c) for c in chunks)
    return ("// FL12: FunctionKeyDict (lookups.generated.js), normaliseret til\n"
            "// versaler - %d noegler. Se fl_validation.fk_hit.\n"
            "nfFlFunctionKeys =\n    %s;" % (len(keys), body))


def formulas_block():
    parts = [tok.formula(), lay.formula()]
    parts.append(_table(
        "nfFlPlan", R["plan"],
        ["Cls", "Ord", "Rule", "Field", "Label", "Chk", "Num", "List", "Msg"],
        "Tjeklisten pr. klasse (FL30-FL53). Ord 0 = klassens TRM-flag (FL48)."))
    parts.append(_table(
        "nfFlLists", [dict(r, UValue=r["Value"].upper()) for r in R["lists"]],
        ["List", "Ord", "Value", "UValue"],
        "Dropdown-listerne (FL31, FL35, FL37-FL47). UValue er til FL54."))
    parts.append(_table(
        "nfFlColumns", R["columns"],
        ["Cls", "Ord", "Column", "Field", "Editable", "List", "MaxLen"],
        "Kolonnerne pr. klasse og deres editor (FL58-FL61, FL_SPOOL_COLUMNS)."))
    parts.append(_table("nfFlAggregate", R["aggregate"], ["Key", "Cls"],
                        "ClassDeterminationAggregateKey (FL17, FL18)."))
    parts.append(_table("nfFlComponent", R["component"], ["Key", "Cls"],
                        "ClassDeterminationComponentKey (FL17)."))
    parts.append(_table("nfFlBr18", R["br18"], ["Key12", "Key17", "Description"],
                        "BR18_Keys (FL13-FL15)."))
    parts.append(_table("nfFlPlants", [{"Key": k} for k in R["plants"]], ["Key"],
                        "Plant (FL11)."))
    parts.append(_table("nfFlClassHelp",
                        [{"Key": k, "Help": v} for k, v in R["classHelp"].items()],
                        ["Key", "Help"], "CLASS_HELP (FL65)."))
    trm = sorted({p["Cls"] for p in R["plan"] if p["Ord"] == 0 and p["Chk"] == "TRMSET"})
    parts.append(_table("nfFlTrmClasses", [{"Cls": c} for c in trm], ["Cls"],
                        "Klasserne med trinet TRMNEW (FL48)."))
    parts.append(_function_keys())
    parts.append("// FL12: tjekket springes over, hvis ordbogen er tom (fl-rule-engine.js:130).\n"
                 f"nfFlHasFunctionKeys = {'true' if R['functionKeys'] else 'false'};\n"
                 f"nfFlFunctionKeyCount = {len(R['functionKeys'])};\n"
                 "// FL24: reglerne er 'indlaest', naar planen findes.\n"
                 "nfFlRulesLoaded = CountRows(nfFlPlan) > 0;")
    return "\n\n".join(parts)


ROW = {"RowGuid": '""', "RowNo": "0", "SpId": "0", "FL": '""', "Description": '""',
       "KksType": '""', "AssignedClass": '""', "Status": '""', "FirstIssue": '""',
       "FirstWarning": '""', "IssueCount": "0", "WarningCount": "0"}
ISSUE = {"RowGuid": '""', "Ord": "0", "Sev": '""', "Code": '""', "Field": '""',
         "Short": '""', "Msg": '""'}

COLLECTIONS = [
    # Raekkerne - Validation-tabellen (functional-location.html:59-74).
    ("colFlRows", ROW),
    # Spool-felterne: een raekke pr. udfyldt felt. Feltnavnet er
    # normaliseret (versaler), som noeglerne i controllerens spoolValues.
    ("colFlVals", {"RowGuid": '""', "Field": '""', "Value": '""'}),
    # MEDDELELSESTABELLEN - moenstret fra powerfx/03-validering.fx.
    ("colFlIssues", ISSUE),
    ("colFlIssuesRaw", ISSUE),
    # Mellemregningerne i Verify (fl_validation.py, afsnit B og E).
    ("colFlCalc", CALC_SCHEMA),
    ("colFlTmp", ROW),
    ("colFlTrm", {"RowGuid": '""', "AnyTrm": "false", "Ue": "false"}),
    # Klassefanerne (FL28).
    ("colFlTabs", {"Key": '""', "Label": '""'}),
    # Gem: raekkerne i SharePoint paa RowGuid, og hvad der fejlede.
    ("colFlSp", {"RowGuid": '""', "ID": "0"}),
    ("colFlSaveErrors", {"Where": '""', "Msg": '""'}),
    # Dyblink: raekkerne, som de blev hentet.
    ("colFlLoad", dict(ROW, Json='""')),
    tok.prefs_schema(),
]


def collection_block():
    out = []
    for name, schema in COLLECTIONS:
        fields = ", ".join(f"{k}: {v}" for k, v in schema.items())
        out.append(f"ClearCollect({name}, {{ {fields} }});\nClear({name});")
    return "\n\n".join(out)


STATE = '''Set(varFlMe, Lower(User().Email));
Set(varFlRequestGuid, "");
Set(varFlRequestNo, "");
// Kladde / Indsendt - som i FunctionalLocationRequests.Status.
Set(varFlStatus, "");
Set(varFlNextRowNo, 1);
// Aktiv klassefane. "ALL" som i renderClassTabs.
Set(varFlTab, "ALL");
// Detaljeruden: raekkens RowGuid og den klasse, den blev aabnet i.
Set(varFlDetailRow, "");
Set(varFlDetailClass, "");
Set(varFlShowEmpty, false);
// Er der aendret noget siden sidste Verify? Submit kraever false (FL68).
Set(varFlStale, false);
Set(varFlInfo, "Ready.");
Set(varFlExportJson, "");
Set(varFlExportOpen, false);
Set(varFlPayload, "");
Set(varFlReq, Blank());
Set(varFlIdx, Blank())'''


def main():
    onstart = (collection_block() + "\n\n" + tok.onstart_block() + "\n\n" + STATE)
    lines = ["App:", "  Properties:", "    Formulas: |"]
    first = True
    for line in formulas_block().split("\n"):
        lines.append(("      =" if first else "      ") + line if line.strip() else "")
        first = False
    lines.append("    OnStart: |")
    first = True
    for line in onstart.split("\n"):
        if not line.strip():
            lines.append("")
            continue
        lines.append(("      =" if first else "      ") + line)
        first = False
    lines += ["    StartScreen: |-", f"        ={cfg.SCREEN}",
              "    Theme: |-", "        =PowerAppsTheme"]
    content = "\n".join(lines) + "\n"
    with open(os.path.join(OUT_DIR, "App.pa.yaml"), "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print("App.pa.yaml skrevet.", content.count(chr(10)) + 1, "linjer,",
          len(COLLECTIONS), "arbejdssamlinger, 0 datahentninger i OnStart,",
          len(R["plan"]), "tjek i nfFlPlan.")
    if not cfg.PLAY_URL:
        print("  NB: 'functionallocation' har intet app_id i tools/canvas_apps.json endnu -\n"
              "      AppUrl i MD_RequestIndex bliver tom, til id'et er sat og appen bygget igen.")


if __name__ == "__main__":
    main()
