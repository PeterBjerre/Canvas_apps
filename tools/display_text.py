# -*- coding: utf-8 -*-
"""
LAGRET VAERDI -> ENGELSK VISNING, EET STED (issue #162).

Appens tekster er engelske, men noget af det, den VISER, kommer fra data:

  - statusvaerdierne i MD_RequestIndex (Kladde, Indsendt, AfventerInfo ...).
    De laeses af flowene og forretningslogikken og maa IKKE oversaettes i
    listen. Ordforraadet staar i request_index.STATUS.
  - tekst, flowene har skrevet i MD_ApprovalLog (Detail, ItemText), i
    MD_RequestIndex.LastActionBy og i MaintenancePlans.ReturnComment.
    Flowene skriver nu engelsk (solution/BIOSAP/src/Workflows), men raekker
    skrevet foer det staar stadig paa dansk.

Begge dele oversaettes HER, ved visning - aldrig i data og aldrig i et
filter. Et filter paa en lagret vaerdi bruger stadig den lagrede vaerdi.

STATUS er en navngiven formel (en tabel) i App.Formulas, saa der er een
oversaettelse i appen; status() slaar op i den. Flowteksterne har dynamiske
dele ("system 2", "intet svar fra X"), saa de kan ikke slaas op som en
noegle: log() bygger et udtryk af de faste saetninger nedenfor. UDF er ikke
slaaet til (docs/31, PX7), saa udtrykket indsaettes, hvor det bruges -
men det bygges kun her.
"""
import request_index as ri

STATUS_TABLE = "RequestStatusLabels"


def formula():
    """Den navngivne formel til App.Formulas. Ordret ens i alle apps, saa
    BIO SAP App's sammenlaegning beholder een."""
    rows = ",\n    ".join(f'{{ Key: "{k}", Label: "{lab}" }}' for k, lab, _s in ri.STATUS)
    return (
        "// STATUSETIKETTER. Genereret af tools/display_text.py - ret ikke her.\n"
        "// Noeglen er den LAGREDE vaerdi (laeses af flowene); Label er visningen.\n"
        f"{STATUS_TABLE} = Table(\n    {rows}\n);"
    )


def plural(n_expr, one, many=None):
    """'1 row' / '2 rows' - aldrig 'row(s)' (UX-review 2026-10, B4).

    n_expr er et Power Fx-tal. Udtrykket regnes een gang (With)."""
    many = many or one + "s"
    return f'With({{ _c: {n_expr} }}, Text(_c) & If(_c = 1, " {one}", " {many}"))'


# GAMLE OPSUMMERINGER (B4). MD_RequestIndex.ShortText blev skrevet som
# "Materials: 1 raekke(r)" og senere "Equipment: 2 row(s)". Raekkerne
# staar stadig i listen; de vises paa engelsk her - data roeres ikke.
LEGACY_SHORT = ((" 1 raekke(r)", " 1 row"), (" raekke(r)", " rows"),
                (" 1 row(s)", " 1 row"), (" row(s)", " rows"))


def short_text(expr):
    """ShortText til visning: gamle "raekke(r)"/"row(s)" som "row"/"rows"."""
    e = expr
    for old, new in LEGACY_SHORT:
        e = f'Substitute({e}, "{old}", "{new}")'
    return e


def status(expr, fallback=None):
    """Den engelske etiket for en lagret statusvaerdi. En ukendt vaerdi
    vises som den er (eller som fallback, et Power Fx-udtryk)."""
    return (f"Coalesce(LookUp({STATUS_TABLE}, Key = {expr}, Label), "
            f"{expr if fallback is None else fallback})")


def status_label(key):
    """Etiketten til Python-siden (fx en fast tekst i en Notify)."""
    return dict((k, lab) for k, lab, _s in ri.STATUS)[key]


# ---------------------------------------------------------------------------
# Flowtekst. Kilden er de danske saetninger, flowene skrev foer issue #162
# (og sharepoint/inspect/out/sample-MD_ApprovalLog.json). Det engelske er
# ORDRET det, flowene skriver nu - saa gamle og nye raekker ser ens ud.
# ---------------------------------------------------------------------------

# Hele vaerdien.
EXACT = (
    ("omkostning", "Cost"),
    ("godkendt tidligere", "Approved earlier"),
    ("systemgodkendelsen", "System approval"),
    ("omkostningsgodkendelsen", "Cost approval"),
    ("Planen har ingen items.", "The plan has no items."),
    ("Omkostningsgodkenderen (COST) findes ikke i MD_Approver eller i Office 365.",
     "The cost approver (COST) is not in MD_Approver or Office 365."),
    ("Kvalitetsgodkenderen for værket findes ikke i MD_Approver eller i Office 365.",
     "The quality approver for the plant is not in MD_Approver or Office 365."),
)

# Starten af vaerdien (StartsWith skelner ikke store og smaa bogstaver).
# Den laengste foerst: "kvalitetsgennemgang (" foer "kvalitet ".
PREFIX = (
    ("opretter er 1. eller 2. godkender for system ", "Requester is 1st or 2nd approver for system "),
    ("intet svar fra ", "No response from "),
    ("kvalitetsgennemgang (", "Quality review ("),
    ("kvalitet ", "Quality "),
    ("system ", "System "),
    ("SAP-plan ", "SAP plan "),
)

# Et stykke midt i vaerdien. Kun saetningsdele, der ikke ligner almindelig
# tekst, saa en brugers kommentar ikke aendres.
FRAGMENT = (
    (" kr. (grænse ", " DKK (threshold "),
    (" kr.)", " DKK)"),
    (" findes ikke i systemmodellen", " is not in the system model"),
    (" hører til ", " belongs to "),
    (", planen er til ", ", the plan is for "),
    (" har ingen gyldig godkender i listen", " has no valid approver in the list"),
    (" har ingen godkender i listen", " has no approver in the list"),
    (" har ingen godkender, der findes i Office 365", " has no approver found in Office 365"),
    ("(ingen kommentar)", "(no comment)"),
) + tuple(
    # "Request deleted (AfventerInfo, owner ...)" (tools/request_delete.py
    # foer issue #162): statusnoeglen i parentesen.
    (f"({k}, ", f"({lab}, ") for k, lab, _s in ri.STATUS
)


def _q(s):
    return '"' + s.replace('"', '""') + '"'


def log(expr):
    """Power Fx: flowtekst (Detail, ItemText, LastActionBy, ReturnComment)
    paa engelsk. Engelsk tekst gaar uaendret igennem."""
    exact = ", ".join(f"{_q(da)}, {_q(en)}" for da, en in EXACT)
    pre = ", ".join(f"StartsWith(t, {_q(da)}), {_q(en)} & Mid(t, {len(da) + 1})"
                    for da, en in PREFIX)
    out = "x"
    for da, en in FRAGMENT:
        out = f"Substitute({out}, {_q(da)}, {_q(en)})"
    return (f"With({{ t: Coalesce({expr}, \"\") }}, "
            f"With({{ x: Switch(t, {exact}, If({pre}, t)) }}, {out}))")


def log_py(text):
    """Samme oversaettelse i Python - til testene."""
    t = text or ""
    x = dict(EXACT).get(t)
    if x is None:
        x = t
        for da, en in PREFIX:
            if t.lower().startswith(da.lower()):
                x = en + t[len(da):]
                break
    for da, en in FRAGMENT:
        x = x.replace(da, en)
    return x
