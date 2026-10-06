# -*- coding: utf-8 -*-
"""
Noterne ved indsendelse af en VH-plan (issue #115) - EET sted for VH-plan-
skaermen og hubben (listen, Approval flow og Activity).

TO NOTER, TO STEDER
-------------------
    Note to approver   MaintenancePlans.NoteToApprover (Note)
                       Laeses af ejer, admins og godkendere.
    Note to self       en raekke i VHP_NoteToSelf (Note, RequestGuid,
                       OwnerEmail, PlanId). Listen har "Read access: Only
                       their own" og "Create and Edit access: Only their
                       own" - SharePoint selv giver kun ejeren raekken. Admins
                       ser alle raekker via listens Override List Behaviors-
                       rettighed (Full Control/Design).

SharePoint har ingen kolonnesikkerhed: en kolonne paa planen kunne enhver,
der kan laese planen, hente via API'et. Derfor ligger Note to self i sin
egen liste og ikke paa planen (Peters valg B).

To afledte kolonner, saa intet skal slaas op pr. raekke:
    MD_RequestIndex.HasApproverNote   hubben viser ikonet uden et kald
    MaintenancePlans.SubmittedBy      forfatteren i Activity

REGLEN - samme udtryk i data og i formler
-----------------------------------------
    Note to self       ejer eller admin (permissions.IS_ADMIN)
    Note to approver   ejer, admin, eller godkender: AssignedToEmail
                       (flowenes aktuelle godkender), en beslutning i
                       MD_ApprovalLog paa anmodningen, eller en raekke i
                       MD_Approver (permissions.IS_APPROVER).

Systemgodkenderen af et item findes via Power BI i flowet og kendes ikke i
appen. Derfor er en godkender i MD_Approver godkender for alle planer - det
er "godkender i processen", ikke "godkender af netop det item".

Noterne skrives KUN ved Submit (build_save._step_notes og _step_status).
Save draft og flowene roerer dem ikke.
"""
import layout_tokens as lay
from layout_tokens import below
from gen_screen import (Ctrl, C_OVERLAY, C_MODAL_BG, C_PRIMARY_SOFT, C_MUTED, C_TITLE,
                        C_CARD_BORDER, C_PRIMARY)
from build_helpers import group, text_ctrl, button, text_input, fit_button_width
import permissions as perm

LIST = "VHP_NoteToSelf"
PLANS = "MaintenancePlans"
COL_APPROVER = "NoteToApprover"
COL_BY = "SubmittedBy"
FLAG = "HasApproverNote"
LOG = "MD_ApprovalLog"
MAX_LEN = 4000

T_APPROVER = "Note to approver"
T_SELF = "Note to self"
TIP = "View notes"
# Hvem kan se hvad - samme tekst i indsendelsen og i visningen.
HINT_APPROVER = ('If({edit}, "Shared with the approvers of this plan. You and administrators '
                 'can also see it.", "Visible to the requester, administrators and the approvers '
                 'of this plan.")')
HINT_SELF = ('If({edit}, "Private. Only you and administrators can see it - it is never shared '
             'with approvers.", "Private to the requester and administrators. Never shared with '
             'approvers.")')


def may_self(owner_email, me):
    """Maa brugeren se Note to self?"""
    return f"({perm.is_owner(owner_email, me)} || {perm.IS_ADMIN})"


def may_approver(owner_email, me, assigned_email, decided):
    """Maa brugeren se Note to approver? decided: et udtryk, der er sandt,
    naar brugeren har en beslutning i MD_ApprovalLog paa anmodningen."""
    return (f"({perm.is_owner(owner_email, me)} || {perm.IS_ADMIN} || {perm.IS_APPROVER} || "
            f'Lower(Coalesce({assigned_email}, "")) = {me} || {decided})')


def decided_in(log, guid, me):
    """Har brugeren en beslutning paa anmodningen i log (liste eller samling)?
    Flowene og admin-loggen skriver DecidedByEmail med smaa bogstaver, saa
    sammenligningen delegeres uden Lower."""
    return f'!IsBlank(LookUp({log}, RequestGuid = {guid} && DecidedByEmail = {me}))'


def has_self(guid, coll):
    """Har anmodningen en Note to self, som brugeren maa se? coll er
    samlingen af de raekker, SharePoint gav brugeren (hub_self_refresh)."""
    return f"({guid} in {coll}.RequestGuid)"


def hub_self_refresh(me):
    """Hubbens ene hentning af de Note to self-raekker, brugeren maa se -
    kun RequestGuid, ingen tekst. Listen giver kun ejerens egne raekker
    (admins alle); formlen siger det samme."""
    return (f"ClearCollect(colMdSelfNotes, If({perm.IS_ADMIN}, ShowColumns({LIST}, RequestGuid), "
            f"ShowColumns(Filter({LIST}, OwnerEmail = {me}), RequestGuid)))")


# ---------------------------------------------------------------------------
# Popuppen: to felter side om side - eller under hinanden paa en telefon.
# Samme kontrol til indsendelsen (edit) og til visningen (view).
# ---------------------------------------------------------------------------
POP_MAX_W = 760
PAD = 18
GAP = 16
PANE_PAD = 12
INPUT_H = 132
HINT_H = 34
INTRO_H = 40


def _pane(prefix, key, title, hint, default, edit, show, pane_w, placeholder):
    inp = text_input(f"inp{prefix}Note{key}", default, placeholder=placeholder,
                     max_length=MAX_LEN, height=INPUT_H, ttype="Multiline",
                     display_mode=f"If({edit}, DisplayMode.Edit, DisplayMode.View)",
                     label=f'"{title}"')
    head = text_ctrl(f"txt{prefix}Note{key}Title", f'"{title}"', size=14, weight="Semibold",
                     height=20, wrap="false")
    sub = text_ctrl(f"txt{prefix}Note{key}Hint", hint.format(edit=edit), size=12, color=C_MUTED,
                    height=HINT_H, wrap="true")
    pane = group(f"con{prefix}Note{key}", [head, sub, inp], direction="Vertical", gap=6,
                 width=pane_w, border_color=C_CARD_BORDER, radius=8,
                 pad=(PANE_PAD, PANE_PAD, PANE_PAD, PANE_PAD), visible=show)
    pane.props["LayoutMinWidth"] = "0"
    return pane, inp


def popup(prefix, open_var, edit, title_fx, intro_fx, a_default, s_default, show_a, show_s,
          submit_fx=None, submit_name=None):
    """[sloer med popuppen].

    edit:      sandt i indsendelsen (felterne kan skrives, Submit vises).
    show_a/s:  maa brugeren se noten - en skjult note fylder intet, og den
               anden faar hele bredden.
    submit_fx: Submits handling. Close er den eneste anden vej ud; et tryk
               paa sloeret lukker ikke (issue #115).
    Returnerer (kontroller, inputA, inputS)."""
    vis = f"IfError({open_var}, false)"
    pop_w = f"Min({POP_MAX_W}, App.Width - 24)"
    inner = f"({pop_w} - {2 * PAD})"
    narrow = below("Tablet")
    both = f"(({show_a}) && ({show_s}))"
    pane_w = f"If({narrow} || !{both}, {inner}, ({inner} - {GAP}) / 2)"
    pa, inp_a = _pane(prefix, "A", T_APPROVER, HINT_APPROVER, a_default, edit, show_a, pane_w,
                      f'If({edit}, "Optional - for example context for the approval", "No note was added.")')
    ps, inp_s = _pane(prefix, "S", T_SELF, HINT_SELF, s_default, edit, show_s, pane_w,
                      f'If({edit}, "Optional - a private reminder", "No note was added.")')
    ph = max(int(pa.h), int(ps.h))
    row_h = f"If({narrow} && {both}, {2 * ph + GAP}, {ph})"
    split = group(f"con{prefix}NotesSplit", [pa, ps], direction="Horizontal", gap=GAP,
                  height=row_h, width=inner, align_items="Start")
    split.props["LayoutDirection"] = f"If({narrow}, LayoutDirection.Vertical, LayoutDirection.Horizontal)"
    split.h = 2 * ph + GAP

    title = text_ctrl(f"txt{prefix}NotesTitle", title_fx, size=lay.SIZE_CARD_TITLE,
                      weight="Semibold", height=26, wrap="false")
    intro = text_ctrl(f"txt{prefix}NotesIntro", intro_fx, size=13, color=C_MUTED,
                      height=INTRO_H, wrap="true")
    close = button(f"btn{prefix}NotesClose", '"Close"', f"Set({open_var}, false)",
                   width=fit_button_width('"Close"'), height=36)
    btns = [close]
    if submit_fx:
        ok = button(submit_name or f"btn{prefix}NotesSubmit", '"Submit"',
                    f"Set({open_var}, false);\n{submit_fx}", primary=True,
                    width=fit_button_width('"Submit"'), height=36)
        ok.props["Visible"] = edit
        ok.vis = edit
        btns.append(ok)
    footer = group(f"con{prefix}NotesFooter", btns, direction="Horizontal", gap=8,
                   height=36, justify="End", align_items="Center")
    modal = group(f"con{prefix}NotesModal", [title, intro, split, footer], direction="Vertical",
                  gap=12, fill=C_MODAL_BG, border_color=C_PRIMARY_SOFT, radius=lay.RADIUS_MODAL,
                  pad=(PAD, PAD, PAD, PAD), width=pop_w, drop_shadow="ExtraBold",
                  align_in_container="Center")
    modal.props["Height"] = f"{2 * PAD + 26 + INTRO_H + 36 + 3 * 12} + {row_h}"
    backdrop = group(f"con{prefix}NotesBackdrop", [modal], direction="Vertical", gap=0,
                     height="App.Height", width="App.Width", fill=C_OVERLAY, visible=vis,
                     justify="Start", align_items="Center", pad=(16, 0, 16, 0), overflow_y="Scroll")
    backdrop.props["X"] = "0"
    backdrop.props["Y"] = "0"
    return [backdrop], inp_a, inp_s


# ---------------------------------------------------------------------------
# Hubben: indlaesning af noterne til visningen.
# ---------------------------------------------------------------------------
def hub_may_approver(req):
    return may_approver(f"{req}.RequesterEmail", "varMdMe", f"{req}.AssignedToEmail",
                        decided_in("colMdAprAll", f"{req}.RequestGuid", "varMdMe"))


def hub_may_self(req):
    return may_self(f"{req}.RequesterEmail", "varMdMe")


def hub_has_visible(req):
    """Har anmodningen en note, brugeren maa se? Ingen kald: flaget staar
    i indeksraekken, og Note to self-raekkerne er hentet een gang."""
    return (f'({req}.Domain.Value = "MaintenancePlan" && (({req}.{FLAG} && {hub_may_approver(req)}) || '
            f'({has_self(req + ".RequestGuid", "colMdSelfNotes")} && {hub_may_self(req)})))')


def hub_open_fx(req):
    """Hent noterne for req og aabn popuppen. Hver note hentes kun, naar
    den findes og brugeren maa se den - et opslag hver, paa ID og paa den
    indekserede RequestGuid."""
    r = "varMdNoteReq"
    return ";\n".join([
        f"Set({r}, {req})",
        f"Set(varMdNoteShowA, {hub_may_approver(r)})",
        f"Set(varMdNoteShowS, {hub_may_self(r)})",
        f'Set(varMdNoteA, If(varMdNoteShowA && {r}.{FLAG}, '
        f'Coalesce(LookUp({PLANS}, ID = {r}.SourceItemId).{COL_APPROVER}, ""), ""))',
        f'Set(varMdNoteS, If(varMdNoteShowS && {has_self(r + ".RequestGuid", "colMdSelfNotes")}, '
        f'Coalesce(LookUp({LIST}, RequestGuid = {r}.RequestGuid).Note, ""), ""))',
        "Set(varMdNotesOpen, true)",
    ])


def hub_popup():
    ctrls, _a, _s = popup(
        "Md", "varMdNotesOpen", "false", '"Submission notes"',
        '"Notes added when " & varMdNoteReq.RequestNo & " was submitted. They are read-only."',
        "varMdNoteA", "varMdNoteS", "IfError(varMdNoteShowA, false)",
        "IfError(varMdNoteShowS, false)")
    return ctrls
