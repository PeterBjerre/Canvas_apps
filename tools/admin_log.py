# -*- coding: utf-8 -*-
"""
Log af en admins aendringer i en ANDENS anmodning (2026-10-05).

Loggen er MD_ApprovalLog - den samme liste, hubbens aktivitetspopup
allerede viser (Masterdata Hub/build/approval_flow.timeline_fx). En
admin-raekke har

    Stage           "Admin"
    Decision        "AdminEdit" eller "AdminDelete"
    DecidedByEmail  adminens e-mail       (hvem)
    DecidedOn       Now()                 (hvornaar)
    Comment         "Felt: gammel -> ny; ..." (hvad - hele teksten)
    Detail          de foerste 255 tegn af det samme
    Title           anmodningsnummeret
    RequestGuid     anmodningen

PlanId staar TOM med vilje: flowene QualityReview og ToMasterData laeser
loggen paa PlanId uden at se paa Stage, og en admin-raekke maa ikke
taelle som en godkendelse. Stage er ikke System/Cost/Quality, saa
hubbens strip (approval_flow.LOG_REFRESH) og godkendelsestrinene ser
heller ikke raekken.

En admin i sin EGEN anmodning er en almindelig aendring og logges ikke
(tools/permissions.as_admin).
"""
LIST = "MD_ApprovalLog"
STAGE = "Admin"
EDIT = "AdminEdit"
DELETE = "AdminDelete"
ARROW = "→"


def write(guid, request_no, decision, comment, indent=0):
    """Skriv een lograekke. Fejler den, er aendringen alligevel gemt - det
    siges, men gemningen meldes ikke som fejlet. Begge grene slutter i en
    boolean (check_layout regel 32)."""
    body = (
        "IfError(\n"
        f"    Patch({LIST}, Defaults({LIST}), {{\n"
        f"        Title: {request_no},\n"
        f"        RequestGuid: {guid},\n"
        f'        Stage: "{STAGE}",\n'
        f'        Decision: "{decision}",\n'
        f"        Detail: Left({comment}, 255),\n"
        f"        Comment: {comment},\n"
        "        DecidedByEmail: Lower(User().Email),\n"
        "        DecidedOn: Now()\n"
        "    });\n"
        "    true,\n"
        '    Notify("The change was saved, but the admin log entry failed: " & FirstError.Message, '
        "NotificationType.Warning);\n"
        "    false\n"
        ")"
    )
    pad = " " * indent
    return "\n".join(pad + l for l in body.split("\n"))


def diff(pairs, prefix='""'):
    """Tekst med de felter, der er aendret: 'Felt: gammel -> ny; ...'.
    pairs: [(etiket, gammelt udtryk, nyt udtryk)] - udtrykkene skal kunne
    gives til Text() (tekst, tal, dato, sandhed - ikke en valgrecord; brug
    .Value). Tom tekst, naar intet er aendret. prefix foran hvert felt,
    fx raekkens noegle."""
    rows = ",\n        ".join(
        f'{{ f: "{label}", a: Text({old}), b: Text({new}) }}' for label, old, new in pairs)
    return (
        "Concat(\n"
        "    Filter(\n"
        "        Table(\n"
        f"        {rows}\n"
        "        ),\n"
        '        Coalesce(a, "") <> Coalesce(b, "")\n'
        "    ),\n"
        f'    {prefix} & f & ": " & Coalesce(a, "(blank)") & " {ARROW} " & Coalesce(b, "(blank)"),\n'
        '    "; "\n'
        ")"
    )


def join(*parts):
    """Saml flere tekststykker med '; ' og spring de tomme over."""
    rows = ", ".join(f"{{ t: {p} }}" for p in parts)
    return f'Concat(Filter(Table({rows}), !IsBlank(t)), t, "; ")'


def submitted(old_status):
    """'Status: <foer> -> Submitted' med statussernes engelske navne
    (request_index.STATUS) - appens tekster er engelske."""
    import request_index as ri
    labels = ", ".join(f'"{k}", "{lab}"' for k, lab, _s in ri.STATUS)
    new = dict((k, lab) for k, lab, _s in ri.STATUS)[ri.SUBMITTED]
    return f'"Status: " & Switch({old_status}, {labels}, {old_status}) & " {ARROW} {new}"'
