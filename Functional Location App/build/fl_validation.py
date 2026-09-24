# -*- coding: utf-8 -*-
"""
VERIFY - reglerne som EEN meddelelsestabel (colFlIssues).

Moenstret er powerfx/03-validering.fx: hver regel er en raekke i en tabel
med kode, alvor og besked, og alt andet - raekkens status, den foerste
fejl, feltets roede kant, Submit-knappen - laeses ud af den tabel. Koderne
er ID'erne i docs/31-functional-location-regler.md (FL4, FL30 ...).

HVORDAN FORMLEN PASSER TIL JS'EN
--------------------------------
Denne fil skriver Power Fx, og Power Fx kan ikke koeres her. Det, der
efterproeves, er den FLADE EVALUATOR i tools/fl/harness.js
(flatValidate) - en linje-for-linje-model af det, der staar herunder -
mod den ORIGINALE html/app-functional-location.js:

    node tools/fl/harness.js test

Aendres en formel her, skal flatValidate aendres paa samme maade. De to
er skrevet i samme raekkefoelge, afsnit for afsnit (A-H), saa det kan
ses, at de siger det samme.

Alt, hvad der er DATA - planen pr. klasse, listerne, noeglerne, moenstrene
- kommer fra fl_rules.generated.json. Her staar kun maskineriet.
"""
import fl_config as cfg

R = cfg.rules()
PAT = R["patterns"]
FIELD_PAT = R["fieldPatterns"]


def _q(s):
    """En Power Fx-strengkonstant."""
    return '"' + str(s).replace('"', '""') + '"'


def _any_match(expr, patterns):
    return "(" + " || ".join(f"IsMatch({expr}, {_q(p)})" for p in patterns) + ")"


# ---------------------------------------------------------------------------
# A. Funktionsnoeglerne (FL12, docs/31 PX5)
# ---------------------------------------------------------------------------
# De 6.441 noegler ligger i appen som EEN streng, "0ABA0ABB0...0", i den
# navngivne formel nfFlFunctionKeys - ligesom siden har dem i
# lookups.generated.js. Et opslag i SharePoint pr. raekke kan ikke
# delegeres (check_layout regel 30), og SharePoint ville saa kun lede i de
# foerste 500-2000 raekker: en gyldig noegle laengere nede ville blive
# afvist i stilhed.
#
# Separatoren er "0": noeglerne er rene bogstaver (generate_app_onstart.py
# efterproever det). Et ciffer holder hele strengen som eet "ord", saa
# sprogtjekket ikke laeser noeglen AA eller SOM som dansk.
#
# exactin, ikke in: Set.has() i JS skelner store og smaa bogstaver. En
# noegle med "0" i kan aldrig findes (den ville ellers kunne matche hen over
# to naboer i strengen).
def fk_hit(k7):
    return f'(!("0" in {k7}) && ("0" & {k7} & "0") exactin nfFlFunctionKeys)'


# ---------------------------------------------------------------------------
# B. Raekken: syntaks, klasse og raekkebeskederne
# ---------------------------------------------------------------------------
# Beskederne staar i SAMME raekkefoelge som i applyLocalValidation
# (app-functional-location.js:1085-1113) og determineClass
# (fl-rule-engine.js:101-165). Raekkefoelgen er ikke pynt: tabellen viser
# den FOERSTE fejl (FL26).
ROW_MSGS = [
    # (kolonne i colFlCalc, kode, felt)
    ("MFlReq", "FL4", "FUNCTIONAL LOCATION"),
    ("MDup", "FL5", "FUNCTIONAL LOCATION"),
    ("MDescReq", "FL6", "DESCRIPTION"),
    ("MDescLen", "FL7", "DESCRIPTION"),
    ("MKks", "FL10", "FUNCTIONAL LOCATION"),
    ("MRules", "FL24", "FUNCTIONAL LOCATION"),
    ("MPlant", "FL11", "FUNCTIONAL LOCATION"),
    ("MFunc", "FL12", "FUNCTIONAL LOCATION"),
    ("MU", "FL13", "FUNCTIONAL LOCATION"),
    ("MBrMiss", "FL14", "FUNCTIONAL LOCATION"),
    ("MBrK17", "FL15", "FUNCTIONAL LOCATION"),
    ("MComp", "FL17", "FUNCTIONAL LOCATION"),
    ("MEq18", "FL17", "FUNCTIONAL LOCATION"),
    ("MEq12", "FL19", "FUNCTIONAL LOCATION"),
    ("MNoCls", "FL22", "FUNCTIONAL LOCATION"),
]

# Skemaet for colFlCalc - generate_app_onstart.py skriver det i OnStart.
CALC_SCHEMA = dict(
    [("RowGuid", '""'), ("RowNo", "0"), ("SpId", "0"), ("FL", '""'),
     ("Description", '""'), ("IsBlankRow", "false"), ("KksType", '""'),
     ("SynIssue", '""'), ("Legacy", "false"), ("K12", '""'), ("K17", '""'),
     ("Cls", '""'), ("SpoolCls", '""')]
    + [(c, '""') for c, _k, _f in ROW_MSGS])


def calc_rows():
    """colFlCalc: een record pr. raekke med alt, der er afledt af FL og
    Description. Beskederne staar som tekstkolonner; tom = ingen besked."""
    kks_ok = _any_match("fl", PAT["kks"])
    kv = _any_match("fl", PAT["kks"][10:12])
    ka = _any_match("fl", PAT["kks"][9:10])
    legacy = f"IsMatch(fl, {_q(PAT['legacy'])})"
    short = _any_match("fl", PAT["short"])
    elf = f"IsMatch(fl, {_q(PAT['elf'])})"
    mkp = f"(IsMatch(fl, {_q(PAT['mkp'])}) || IsMatch(fl, {_q(PAT['fp'])}))"
    # Beskederne, der taeller med i FL23 ("ingen klasse og ingen fejl").
    any_msg = " + ".join(f"If(IsBlank({c}), 0, 1)" for c, _k, _f in ROW_MSGS)
    return f"""ClearCollect(
    colFlCalc,
    ForAll(
        colFlRows As R,
        With(
            {{ fl: R.FL, d: Trim(R.Description) }},
            With(
                {{
                    k0: Left(fl, 3), k7: Mid(fl, 7, 3), k12: Mid(fl, 12, 2),
                    k17: Mid(fl, 17, 2), k18: Mid(fl, 18, 2),
                    blankRow: IsBlank(fl) && IsBlank(d),
                    // FL8-FL10: syntaksen
                    ok: {kks_ok},
                    kv: {kv},
                    ka: {ka}
                }},
                With(
                    {{
                        legacy: !IsBlank(fl) && !ok && {legacy},
                        synKab: ok && (kv || ka),
                        live: !IsBlank(fl) && !blankRow && nfFlRulesLoaded,
                        agg: LookUp(nfFlAggregate, Key = k12),
                        comp: LookUp(nfFlComponent, Key = k18),
                        br: k12 = "UE" || k12 = "UF"
                    }},
                    With(
                        {{
                            // FL16-FL22: klassebestemmelsen (fl-rule-engine.js:138-235)
                            p18: live && !synKab && Len(k18) = 2,
                            p12: live && !synKab && Len(k18) <> 2,
                            isMkp: {mkp},
                            isShort: {short},
                            isElf: {elf}
                        }},
                        With(
                            {{
                                MFlReq: If(!blankRow && IsBlank(fl), "FL required.", ""),
                                MDup: If(!blankRow && !IsBlank(fl) && CountRows(Filter(colFlRows As X, X.FL = fl)) > 1, "Duplicate FL.", ""),
                                MDescReq: If(!blankRow && IsBlank(d), "Description required before Ready for SAP.", ""),
                                MDescLen: If(!blankRow && Len(d) > 40, "Description > 40.", ""),
                                MKks: If(!blankRow && !IsBlank(fl) && !ok && !legacy, "KKS invalid.", ""),
                                MRules: If(!blankRow && !IsBlank(fl) && !nfFlRulesLoaded, "Rules data missing.", ""),
                                MPlant: If(live && !(k0 in nfFlPlants.Key), "Plant key invalid.", ""),
                                MFunc: If(live && nfFlHasFunctionKeys && !{fk_hit("k7")}, "Function key invalid.", ""),
                                MU: If(live && br && Left(k7, 1) <> "U", "UF/UE requires U function key.", ""),
                                MBrMiss: If(live && br && IsBlank(LookUp(nfFlBr18, Key12 = k12)), "BR18 rules missing for " & k12 & ".", ""),
                                MBrK17: If(live && br && !IsBlank(LookUp(nfFlBr18, Key12 = k12)) && IsBlank(LookUp(nfFlBr18, Key12 = k12 && Key17 = k17)), "BR18 key17 invalid for " & k12 & ".", ""),
                                MComp: If(p18 && IsBlank(comp), "Component key invalid.", ""),
                                MEq18: If(p18 && IsBlank(agg), "Equipment key invalid.", ""),
                                MEq12: If(p12 && IsBlank(agg) && isMkp, "Equipment key invalid.", ""),
                                MNoCls: If(p12 && IsBlank(agg) && !isMkp && !isShort && !isElf, "Class not determined.", ""),
                                cls: If(
                                    !live, "",
                                    synKab, "KAB",
                                    p18, If(!IsBlank(comp) && !IsBlank(agg), comp.Cls, ""),
                                    !IsBlank(agg), agg.Cls,
                                    isMkp, "",
                                    isShort, "NO CLASS",
                                    isElf, "ELF",
                                    ""
                                )
                            }},
                            With(
                                {{
                                    // FL23: ingen klasse og ingen fejl -> NO CLASS
                                    cls2: If(blankRow, "", IsBlank(cls) && ({any_msg}) = 0, "NO CLASS", cls)
                                }},
                                {{
                                    RowGuid: R.RowGuid, RowNo: R.RowNo, SpId: R.SpId,
                                    FL: fl, Description: d, IsBlankRow: blankRow,
                                    KksType: If(blankRow || IsBlank(fl), "", ok, If(kv, "KKSKV", ka, "KKSKA", "KKS"), legacy, "KKS", ""),
                                    SynIssue: If(!IsBlank(fl) && !ok && !legacy, "KKS invalid.", ""),
                                    Legacy: !blankRow && legacy,
                                    K12: k12, K17: k17,
                                    Cls: cls2,
                                    SpoolCls: Coalesce(cls2, "NO CLASS"),
                                    {", ".join(f"{c}: {c}" for c, _k, _f in ROW_MSGS)}
                                }}
                            )
                        )
                    )
                )
            )
        )
    )
)"""


# ---------------------------------------------------------------------------
# C. Spool-felterne: planen pr. klasse (FL30-FL53)
# ---------------------------------------------------------------------------
# Vaerdien af et felt, som getSpoolColumnValue (app-functional-location.js
# :2205-2242) giver den for de felter, planen tjekker.
def _val(r, field):
    raw = f"LookUp(colFlVals, RowGuid = {r}.RowGuid && Field = {field}).Value"
    return (f"Trim(Switch({field},\n"
            f"    \"STRINDICATOR\", {r}.KksType,\n"
            f"    \"STR. INDICATOR\", {r}.KksType,\n"
            f"    \"FUNCTIONAL LOCATION\", {r}.FL,\n"
            f"    \"DESCRIPTION\", {r}.Description,\n"
            f"    \"LONG TEXT\", Coalesce({raw}, {r}.Description),\n"
            f"    Coalesce({raw}, \"\")))")


# FL54: alle |-adskilte vaerdier skal vaere i listen, uden forskel paa store
# og smaa bogstaver. Tomme stykker taeller ikke.
def in_list_bad(v, list_id):
    return (f"CountRows(Filter(Split({v}, \"|\") As T, !IsBlank(Trim(T.Value)) && "
            f"!(Upper(Trim(T.Value)) in Filter(nfFlLists, List = {list_id}).UValue))) > 0")


# FL34 / PX4: datoen som ren aritmetik. new Date(y, m-1, d) i JS giver et
# andet aar for y < 100, og Power Fx' Date() laegger 1900 til alt under
# 1900 - derfor ingen af dem. Aar >= 100, maaned 1-12, dag i maaneden.
def date_bad(v):
    return f"""With(
    {{ c8: IsMatch({v}, "[0-9]{{8}}"), dt: IsMatch({v}, "[0-9]{{2}}\\.[0-9]{{2}}\\.[0-9]{{4}}") }},
    If(
        !c8 && !dt, true,
        With(
            {{
                y: Value(If(c8, Left({v}, 4), Right({v}, 4))),
                m: Value(Mid({v}, If(c8, 5, 4), 2)),
                dd: Value(If(c8, Right({v}, 2), Left({v}, 2)))
            }},
            !(y >= 100 && m >= 1 && m <= 12 && dd >= 1 &&
              dd <= Switch(m, 2, If(Mod(y, 4) = 0 && (Mod(y, 100) <> 0 || Mod(y, 400) = 0), 29, 28),
                           4, 30, 6, 30, 9, 30, 11, 30, 31))
        )
    )
)"""


def rgx_bad(v, list_id):
    parts = []
    for key, pat in FIELD_PAT.items():
        parts.append(f"{_q(key)}, !IsMatch({v}, {_q(pat)})")
    return f"Switch({list_id}, " + ", ".join(parts) + ", false)"


def spool_issues():
    v = "v"
    bad = (f"Switch(P.Chk,\n"
           f"    \"MAX\", !IsBlank({v}) && Len({v}) > P.Num,\n"
           f"    \"DROP\", !IsBlank({v}) && {in_list_bad(v, 'lid')},\n"
           f"    \"ALLOW\", !IsBlank({v}) && {in_list_bad(v, 'lid')},\n"
           f"    \"REQ\", IsBlank({v}),\n"
           f"    \"RGX\", !IsBlank({v}) && {rgx_bad(v, 'lid')},\n"
           f"    \"DATE\", !IsBlank({v}) && {date_bad(v)},\n"
           f"    \"UE\", R.K12 = \"UE\" && IsBlank({v}),\n"
           f"    \"UEFP\", R.K12 = \"UE\" && R.K17 = \"FP\" && IsBlank({v}),\n"
           f"    \"KKS\", !IsBlank(R.FL) && !IsBlank(R.SynIssue),\n"
           f"    false)")
    return f"""DropColumns(
    Ungroup(
        ForAll(
            Filter(colFlCalc, !IsBlankRow) As R,
            {{
                Items: Filter(
                    ForAll(
                        With({{ sc: R.SpoolCls }}, Filter(nfFlPlan, Cls = sc && Ord > 0)) As P,
                        With(
                            {{ v: {_val('R', 'P.Field')}, lid: P.List }},
                            {{
                                RowGuid: R.RowGuid,
                                Ord: 100 + P.Ord,
                                Sev: "Error",
                                Code: P.Rule,
                                Field: P.Field,
                                Short: If(P.Chk = "KKS", R.SynIssue, P.Msg),
                                Msg: P.Label & ": " & If(P.Chk = "KKS", R.SynIssue, P.Msg),
                                Bad: {bad}
                            }}
                        )
                    ),
                    Bad
                )
            }}
        ),
        Items
    ),
    Bad
)"""


def issues_raw():
    """Den samlede, uafkortede tabel: raekkebeskeder, advarslen og spool."""
    parts = []
    for i, (col, code, field) in enumerate(ROW_MSGS, start=1):
        parts.append(
            f"    ForAll(Filter(colFlCalc, !IsBlank({col})) As R,\n"
            f"        {{ RowGuid: R.RowGuid, Ord: {i}, Sev: \"Error\", Code: \"{code}\", "
            f"Field: \"{field}\", Short: R.{col}, Msg: R.{col} }})")
    parts.append(
        "    ForAll(Filter(colFlCalc, Legacy) As R,\n"
        "        { RowGuid: R.RowGuid, Ord: 50, Sev: \"Warning\", Code: \"FL9\", "
        "Field: \"FUNCTIONAL LOCATION\", Short: \"Legacy format.\", Msg: \"Legacy format.\" })")
    parts.append("    " + spool_issues().replace("\n", "\n    "))
    return "ClearCollect(\n    colFlIssuesRaw,\n" + ",\n".join(parts) + "\n)"


# FL55: samme besked een gang, paa sin FOERSTE plads.
DEDUPE = """ClearCollect(
    colFlIssues,
    ForAll(
        GroupBy(colFlIssuesRaw, RowGuid, Sev, Msg, Grp) As G,
        With(
            { f: First(Sort(G.Grp, Ord)) },
            { RowGuid: G.RowGuid, Sev: G.Sev, Msg: G.Msg, Ord: f.Ord, Code: f.Code,
              Field: f.Field, Short: f.Short }
        )
    )
)"""

# FL25/FL26: raekkens status og dens foerste fejl og advarsel.
STATUS = """ClearCollect(
    colFlTmp,
    ForAll(
        colFlCalc As R,
        With(
            {
                errs: Sort(Filter(colFlIssues, RowGuid = R.RowGuid && Sev = "Error"), Ord),
                warns: Sort(Filter(colFlIssues, RowGuid = R.RowGuid && Sev = "Warning"), Ord)
            },
            {
                RowGuid: R.RowGuid, RowNo: R.RowNo, SpId: R.SpId,
                FL: R.FL, Description: R.Description,
                KksType: R.KksType, AssignedClass: R.Cls,
                Status: If(R.IsBlankRow, "draft", CountRows(errs) > 0, "invalid",
                           CountRows(warns) > 0, "warning", "valid"),
                FirstIssue: Coalesce(First(errs).Msg, ""),
                FirstWarning: Coalesce(First(warns).Msg, ""),
                IssueCount: CountRows(errs),
                WarningCount: CountRows(warns)
            }
        )
    )
);
ClearCollect(colFlRows, colFlTmp)"""

# FL48/FL49: TRM-automatikken - EFTER tjekkene, ligesom i runTrmValidation
# (TRM ASSIGNMENT og ABC INDIC. er tjekket med de gamle vaerdier).
TRM_FIELDS = '["EX-MARKING", "SAFETY CRITICAL EQUIPMENT", "FIRE CLASSIFICATION", "FIRE SEALING TYPE", "FIRE SEALING PRODUCT"]'
TRM_SET = f"""ClearCollect(
    colFlTrm,
    ForAll(
        Filter(colFlCalc, !IsBlankRow && SpoolCls in nfFlTrmClasses.Cls) As R,
        {{
            RowGuid: R.RowGuid,
            AnyTrm: CountRows(Filter(colFlVals, RowGuid = R.RowGuid && Field in {TRM_FIELDS} && !IsBlank(Trim(Value)))) > 0,
            Ue: R.SpoolCls = "MKP" && R.K12 = "UE"
        }}
    )
);
RemoveIf(colFlVals, Field = "TRM ASSIGNMENT" && RowGuid in colFlTrm.RowGuid);
RemoveIf(colFlVals, Field = "ABC INDIC." && RowGuid in Filter(colFlTrm, AnyTrm).RowGuid);
Collect(colFlVals, ForAll(Filter(colFlTrm, AnyTrm || Ue) As T, {{ RowGuid: T.RowGuid, Field: "TRM ASSIGNMENT", Value: "X" }}));
Collect(colFlVals, ForAll(Filter(colFlTrm, AnyTrm) As T, {{ RowGuid: T.RowGuid, Field: "ABC INDIC.", Value: "A" }}))"""

# FL28: klassefanerne. Bruges ogsaa, naar en raekke slettes - dér
# fordeler JS'en raekkerne igen uden at validere (app-functional-location.js
# :472-478).
BUCKETS = 'Filter(colFlRows, Status <> "draft" && !IsBlank(AssignedClass))'
TABS = f"""ClearCollect(
    colFlTabs,
    {{ Key: "ALL", Label: "ALL (" & CountRows({BUCKETS}) & ")" }},
    ForAll(
        Sort(Distinct({BUCKETS}, AssignedClass), Value) As K,
        {{ Key: K.Value, Label: K.Value & " (" & CountRows(Filter({BUCKETS}, AssignedClass = K.Value)) & ")" }}
    )
);
If(varFlTab <> "ALL" && IsBlank(LookUp(colFlTabs, Key = varFlTab)), Set(varFlTab, "ALL"))"""


def verify_fx():
    """btnFlVerify.OnSelect - HELE valideringen. Kaldes alle andre steder
    med Select(btnFlVerify) (docs/31 PX7)."""
    return ";\n\n".join([
        "// B. Syntaks, klasse og raekkebeskeder (FL4-FL24)\n" + calc_rows(),
        "// C. Meddelelsestabellen - raekke + spool (FL30-FL53)\n" + issues_raw(),
        "// D. Samme besked een gang (FL55)\n" + DEDUPE,
        "// E. Status og foerste besked (FL25, FL26)\n" + STATUS,
        "// F. TRM og ABC (FL48, FL49)\n" + TRM_SET,
        "// G. Klassefanerne (FL28)\n" + TABS,
        "// H. Faerdig. varFlStale styrer Submit (FL68).\n"
        "Set(varFlStale, false);\n"
        'Set(varFlInfo, If(CountRows(Filter(colFlRows, Status <> "draft")) = 0, '
        '"No rows to verify.", "Done."))',
    ])


# ---------------------------------------------------------------------------
# Hjaelpetekster og feltmarkering
# ---------------------------------------------------------------------------
def hint_fx(issue, fl):
    """FL27: resolveValidationIssueHelpText (app-functional-location.js
    :1573-1630), ordret. Noeglerne tages KUN, naar FL er lang nok - ellers
    'missing', som i originalen."""
    return f"""With(
    {{
        i: {issue},
        h0: If(Len({fl}) >= 3, Left({fl}, 3), ""),
        h7: If(Len({fl}) >= 9, Mid({fl}, 7, 3), ""),
        h12: If(Len({fl}) >= 13, Mid({fl}, 12, 2), ""),
        h17: If(Len({fl}) >= 18, Mid({fl}, 17, 2), ""),
        h18: If(Len({fl}) >= 19, Mid({fl}, 18, 2), "")
    }},
    Switch(
        i,
        "Function key invalid.", "Function key is FL position 7-9 (" & Coalesce(h7, "missing") & "). It must exist in FunctionKeyDict lookup.",
        "Plant key invalid.", "Plant key is FL position 1-3 (" & Coalesce(h0, "missing") & "). It must exist in Plant lookup.",
        "Component key invalid.", "Component key is FL position 18-19 (" & Coalesce(h18, "missing") & "). No class mapping was found for this key.",
        "Equipment key invalid.", "Equipment/Aggregate key is FL position 12-13 (" & Coalesce(h12, "missing") & "). No aggregate mapping was found.",
        "UF/UE requires U function key.", "For aggregate " & Coalesce(h12, "missing") & ", function key (position 7-9) must start with U. Current value: " & Coalesce(h7, "missing") & ".",
        "KKS invalid.", "Functional Location does not match the allowed KKS patterns.",
        "Class not determined.", "KKS structure is valid, but no class rule matched component/aggregate/fallback mapping.",
        If(
            StartsWith(i, "BR18 key17 invalid for ") && Left(i, 23) = "BR18 key17 invalid for ",
            "BR18 check failed: for aggregate " & Coalesce(h12, "missing") & ", key17 (position 17-18) value " & Coalesce(h17, "missing") & " is not allowed.",
            StartsWith(i, "BR18 rules missing for ") && Left(i, 23) = "BR18 rules missing for ",
            "No BR18 rule set is loaded for aggregate key " & Coalesce(h12, "missing") & ".",
            ""
        )
    )
)"""


# FL29: isFunctionalLocationIssue / isDescriptionIssue. includes() er
# forskel paa store og smaa bogstaver - derfor exactin, ikke in.
FL_WORDS = ["FL", "KKS", "Plant", "Function", "Component", "Equipment", "BR18", "Class"]


def is_fl_issue(msg):
    return "(" + " || ".join(f'"{w}" exactin {msg}' for w in FL_WORDS) + ")"


def is_desc_issue(msg):
    return f'("Description" exactin {msg})'


def fl_bad(row):
    return (f'({row}.Status <> "draft" && CountRows(Filter(colFlIssues, RowGuid = {row}.RowGuid && '
            f'Sev = "Error" && {is_fl_issue("Msg")})) > 0)')


def desc_bad(row):
    return (f'({row}.Status <> "draft" && CountRows(Filter(colFlIssues, RowGuid = {row}.RowGuid && '
            f'Sev = "Error" && {is_desc_issue("Msg")})) > 0)')


def field_issue(row, field):
    """resolveSpoolFieldIssue (app-functional-location.js:2157-2186): den
    foerste besked for feltet - for FL og Description efter ordlisten."""
    return f"""Switch(
    {field},
    "FUNCTIONAL LOCATION", Coalesce(First(Sort(Filter(colFlIssues, RowGuid = {row} && Sev = "Error" && {is_fl_issue("Msg")}), Ord)).Msg, ""),
    "DESCRIPTION", Coalesce(First(Sort(Filter(colFlIssues, RowGuid = {row} && Sev = "Error" && {is_desc_issue("Msg")}), Ord)).Msg, ""),
    Coalesce(First(Sort(Filter(colFlIssues, RowGuid = {row} && Sev = "Error" && Field = {field} && Ord >= 100), Ord)).Short, "")
)"""
