# -*- coding: utf-8 -*-
"""
Issue Board-skaermen (issue #114, trin 1 og 2): delene, formlerne og
hentningen.

    [ikon] Issue Board                              [Refresh] [+ New issue]
           Report what you find while testing ...
    +------------------------------------------------------------------+
    | [All issues | My issues | Shared issues]  [Open | Closed | Archived]
    | [Search .................] [Application v] [Section v] [Sort v]  |
    | [Status v] [Priority v] [Severity v] [Assigned to me]            |
    +------------------------------------------------------------------+
    | 12 issues                                                        |
    | ISS-000142  Save draft fails on ...                 [ New      ] |
    |             Maintenance Plan · Items · Major · Updated ...       |
    +------------------------------------------------------------------+

    New issue   -> popup: Application/Section, titel, lignende sager fra
                   den anonyme liste, "What happened?", flere detaljer
                   (valgfrit), Submit -> flowet.
    En raekke   -> popup i View mode: beskrivelsen og (egne sager og
                   admin) Activity og Attachments. Handlingerne staar
                   under hovedet: Edit, Reopen, Archive/Restore, Delete -
                   hver kun, naar brugeren maa (IbCanEdit osv.).
    Edit        -> samme formular som New issue, udfyldt (Edit mode). En
                   admin faar desuden status, prioritet, tildeling og
                   loesning.
    Delete      -> egen bekraeftelse: sagsnummeret skal skrives.

SIKKERHED ER IKKE HER
---------------------
Alle filtre og knapper paa skaermen er UX. Det, en bruger kan hente,
afgoeres af rettighederne paa raekken, som flowet saetter, og alt, der
aendrer noget, gaar gennem flowet, som tjekker admin og rapportoer paa
serveren (ib_config.py). "All issues" er kun et scope for admins - en
almindelig bruger, der fik det, ville stadig kun kunne hente sine egne
raekker.

HENTNING
--------
  * Konfigurationen og brugerens egne sager hentes EEN gang, foerste gang
    skaermen vises (Concurrent, to delegerbare forespoergsler).
  * Den anonyme liste hentes foerst, naar man vaelger "Shared issues" eller
    aabner "New issue" (forslag til lignende sager).
  * "All issues" (kun admin) hentes, naar scopet vaelges - for en admin
    er det startvisningen.
  * Activity hentes, naar man aabner en af sine egne sager (eller en
    admin aabner en sag). Antallet af vedhaeftninger regnes af Activity;
    selve filerne hentes foerst, naar fanen Attachments vaelges.
  * Efter en aendring hentes kun den ene sag igen (LookUp paa ID) og
    dens Activity - ikke hele listen.
  * Soegning, filtre og sortering regnes i hukommelsen paa de hentede
    raekker - intet kald pr. tastetryk.
"""
from gen_screen import (Ctrl, C_APP_BG, C_CARD_BG, C_CARD_BORDER, C_DIVIDER, C_INFO_BG,
                        C_INFO_FG, C_INVALID_FG, C_MUTED, C_MUTED_BG, C_MODAL_BG, C_OVERLAY,
                        C_PRIMARY, C_PRIMARY_SOFT, C_TITLE, C_TRANSPARENT, C_WARN_BG,
                        C_WARN_FG)
from build_helpers import (button, card, checkbox_theme, concurrent, confirm_modal,
                           fit_button_width, group,
                           grow, icon_on_mobile, label_row, loading_overlay, row_hit, row_rule,
                           text_ctrl, text_input, themed_dropdown, top_bar, ICON_W)
from permissions import IS_ADMIN, ADMIN_LIST, ADMIN_GROUP
from design_tokens import ref as _t
import layout_tokens as lay
from layout_tokens import SHELL_W, below, at_least, if_below

import ib_config as cfg
import doc_upload as du

P = "Ib"
NARROW = below("Tablet")

# ---------------------------------------------------------------------------
# Tilstand
# ---------------------------------------------------------------------------
INIT_STATE = (
    "If(\n"
    "    IsBlank(varIbScope),\n"
    # En admin starter paa admin-boardet (alle sager), alle andre paa
    # deres egne. IsAdmin er een delegerbar LookUp (tools/permissions.py).
    f'    Set(varIbScope, If({IS_ADMIN}, "all", "mine"));\n'
    '    Set(varIbState, "open");\n'
    '    Set(varIbApp, "");\n'
    '    Set(varIbSection, "");\n'
    '    Set(varIbStatusF, "");\n'
    '    Set(varIbPriF, "");\n'
    '    Set(varIbSevF, "");\n'
    "    Set(varIbAssignedMe, false);\n"
    '    Set(varIbSort, "Last updated");\n'
    "    Set(varIbMe, Lower(User().Email));\n"
    '    Set(varIbTab, "details");\n'
    '    Set(varIbFormMode, "new");\n'
    "    Set(varIbFormOn, false);\n"
    "    Set(varIbDetailOn, false);\n"
    "    Set(varIbDelOn, false);\n"
    "    Set(varIbMore, false);\n"
    "    Set(varIbInternal, false);\n"
    "    Set(varIbFilesFor, -1);\n"
    "    Set(varIbBusy, false);\n"
    "    Set(varIbUploading, false);\n"
    "    Set(varIbPosting, false)\n"
    ")"
)


def _rank(field, pairs, fallback):
    body = ", ".join(f'"{k}", {r}' for k, r in pairs)
    return f"Switch({field}, {body}, {fallback})"


STATUS_RANK = [(s, r) for s, _c, r in cfg.STATUS]


def _row(r, *, shared):
    """Een raekke i colIbMine/colIbAll/colIbShared. De tre har SAMME skema,
    saa listen kan vaelge mellem dem med et Switch. Den anonyme kopi har
    ingen rapportoer og ingen tildeling - felterne er tomme."""
    if shared:
        f = {
            "Id": f"{r}.ID", "TicketNo": f'Coalesce({r}.TicketNo, "")',
            "Title": f'Coalesce({r}.Title, "")', "Description": f'Coalesce({r}.Summary, "")',
            "Steps": '""', "Expected": '""', "Actual": '""',
            "Application": f'Coalesce({r}.Application, "")', "Section": f'Coalesce({r}.Section, "")',
            "Other": '""', "RelatedNo": '""',
            "Severity": f'Coalesce({r}.Severity, "")', "Priority": f'Coalesce({r}.Priority, "")',
            "Status": f'Coalesce({r}.Status, "{cfg.STATUS_NEW}")',
            "Resolution": f'Coalesce({r}.Resolution, "")', "Assigned": '""',
            "CreatedOn": f"Coalesce({r}.ReportedOn, {r}.Created)",
            "UpdatedOn": f"Coalesce({r}.LastActivityOn, {r}.ReportedOn, {r}.Created)",
            "Archived": f"Coalesce({r}.IsArchived, false)",
            "Reporter": '""', "AssignedEmail": '""',
        }
        pri, st = f"{r}.Priority", f"{r}.Status"
    else:
        f = {
            "Id": f"{r}.ID", "TicketNo": f'Coalesce({r}.TicketNo, "")',
            "Title": f'Coalesce({r}.Title, "")', "Description": f'Coalesce({r}.Description, "")',
            "Steps": f'Coalesce({r}.ReproSteps, "")', "Expected": f'Coalesce({r}.ExpectedResult, "")',
            "Actual": f'Coalesce({r}.ActualResult, "")',
            "Application": f'Coalesce({r}.Application, "")', "Section": f'Coalesce({r}.Section, "")',
            "Other": f'Coalesce({r}.OtherContext, "")', "RelatedNo": f'Coalesce({r}.RelatedRequestNo, "")',
            "Severity": f'Coalesce({r}.Severity.Value, "")', "Priority": f'Coalesce({r}.Priority.Value, "")',
            "Status": f'Coalesce({r}.Status.Value, "{cfg.STATUS_NEW}")',
            "Resolution": f'Coalesce({r}.Resolution, "")', "Assigned": f'Coalesce({r}.AssignedToName, "")',
            "CreatedOn": f"{r}.Created",
            "UpdatedOn": f"Coalesce({r}.LastActivityOn, {r}.Created)",
            "Archived": f"Coalesce({r}.IsArchived, false)",
            "Reporter": f'Lower(Coalesce({r}.ReporterEmail, ""))',
            "AssignedEmail": f'Lower(Coalesce({r}.AssignedToEmail, ""))',
        }
        pri, st = f"{r}.Priority.Value", f"{r}.Status.Value"
    f["PriRank"] = _rank(pri, cfg.PRIORITY, 5)
    f["StatusRank"] = _rank(st, STATUS_RANK, 9)
    return "{ " + ", ".join(f"{k}: {v}" for k, v in f.items()) + " }"


# Hentningerne. Hver sammenligner med en global variabel eller en konstant,
# saa SharePoint udfoerer filteret og sorteringen (check_layout regel 30).
FETCH_SECTIONS = (f"ForAll(Filter({cfg.L_SECTIONS}, IsActive = true) As r, "
                  '{ Application: Coalesce(r.Application, ""), Section: Coalesce(r.Section, ""), '
                  "AppOrder: Coalesce(r.AppOrder, 0), SectionOrder: Coalesce(r.SectionOrder, 0), "
                  'ScreenKey: Coalesce(r.ScreenKey, "") })')
FETCH_MINE = (f"ForAll(Sort(Filter({cfg.L_TICKETS}, ReporterEmail = varIbMe), LastActivityOn, "
              f"SortOrder.Descending) As r, {_row('r', shared=False)})")
FETCH_SHARED = (f"ForAll(Sort({cfg.L_SHARED}, LastActivityOn, SortOrder.Descending) As r, "
                f"{_row('r', shared=True)})")
# Admin-boardet: alle sager, brugeren har ret til at laese. For en admin er
# det alle (Contribute paa hver raekke); for andre ville det kun vaere deres
# egne - scopet vises kun for admins.
FETCH_ALL = (f"ForAll(Sort({cfg.L_TICKETS}, LastActivityOn, SortOrder.Descending) As r, "
             f"{_row('r', shared=False)})")

RELOAD_MINE = f"Set(varIbMineFailed, IfError(ClearCollect(colIbMine, {FETCH_MINE}); false, true))"

LOAD = (
    "If(\n"
    "    !varIbLoaded,\n"
    "    Set(varIbLoading, true);\n"
    "    " + concurrent(
        f"Set(varIbCfgFailed, IfError(ClearCollect(colIbSections, {FETCH_SECTIONS}); false, true))",
        RELOAD_MINE, indent=4) + ";\n"
    "    Set(varIbLoaded, !varIbCfgFailed && !varIbMineFailed);\n"
    "    Set(varIbLoading, false)\n"
    ")"
)

LOAD_SHARED = (
    "If(\n"
    "    !varIbSharedLoaded,\n"
    "    Set(varIbLoading, true);\n"
    f"    Set(varIbSharedFailed, IfError(ClearCollect(colIbShared, {FETCH_SHARED}); false, true));\n"
    "    Set(varIbSharedLoaded, !varIbSharedFailed);\n"
    "    Set(varIbLoading, false)\n"
    ")"
)

LOAD_ALL = (
    "If(\n"
    f"    {IS_ADMIN} && !varIbAllLoaded,\n"
    "    Set(varIbLoading, true);\n"
    f"    Set(varIbAllFailed, IfError(ClearCollect(colIbAll, {FETCH_ALL}); false, true));\n"
    "    Set(varIbAllLoaded, !varIbAllFailed);\n"
    "    Set(varIbLoading, false)\n"
    ")"
)

RETRY = ("Set(varIbLoaded, false);\nSet(varIbSharedLoaded, false);\nSet(varIbAllLoaded, false);\n"
         + LOAD + ';\nIf(varIbScope = "shared", ' + LOAD_SHARED + ")"
         + ';\nIf(varIbScope = "all", ' + LOAD_ALL + ")")


def on_visible():
    return INIT_STATE + ";\n" + LOAD + ';\nIf(varIbScope = "all", ' + LOAD_ALL + ")"


def _initials(email):
    """Brugerens id (delen foer @) med store bogstaver - som MyUserId."""
    return f'Upper(First(Split({email}, "@")).Value)'


# Haendelser, der flytter status. Body viser "fra -> til".
STATUS_EVENTS = '["StatusChange", "Closed", "Reopened"]'

# Activity for den aabne sag. Foerste raekke er selve indmeldingen (fra
# sagen), resten er raekkerne i IB_TicketComments - kun dem, brugeren har
# ret til at se: en intern note har rapportoeren ingen rettighed til, saa
# den kommer aldrig med i hans hentning. Filteret paa TicketId er
# delegerbart (tal = variabel); ID stiger med tiden, saa ID er raekkefoelgen
# - ogsaa for flere haendelser, flowet skriver i samme sekund.
LOAD_ACTIVITY = (
    "Set(varIbActBusy, true);\n"
    "Set(varIbActFailed, IfError(ClearCollect(\n"
    "    colIbActivity,\n"
    '    { Kind: "Reported", Actor: If(varIbSel.Reporter = varIbMe, "You", '
    f'{_initials("varIbSel.Reporter")}), Body: "Reported the issue.", At: varIbSel.CreatedOn, '
    'Internal: false, IsSystem: true, File: "", SizeKb: 0, Initial: false },\n'
    f"    ForAll(Sort(Filter({cfg.L_COMMENTS}, TicketId = varIbSelId), ID, SortOrder.Ascending) As r,\n"
    '        With({ k: Coalesce(r.EventType.Value, "Comment"), who: Lower(Coalesce(r.AuthorEmail, "")), '
    'role: Coalesce(r.AuthorRole.Value, ""), atSub: Coalesce(r.AtSubmission, false) },\n'
    "            { Kind: k,\n"
    '              Actor: If(role = "System", "System", who = varIbMe, "You", '
    f'{_initials("who")} & If(role = "Admin", " (admin)", "")),\n'
    f"              Body: If(k in {STATUS_EVENTS} && !IsBlank(r.NewStatus), "
    '"Status changed from " & Coalesce(r.PreviousStatus, "-") & " to " & r.NewStatus & '
    'If(IsBlank(r.Content), ".", ". " & r.Content),\n'
    '                    k = "Attachment", If(atSub, "Attached ", "Added ") & Coalesce(r.FileName, "a file") & '
    'If(IsBlank(r.FileSizeKb), "", " (" & r.FileSizeKb & " KB)") & If(atSub, " with the report.", "."),\n'
    '                    Coalesce(r.Content, "")),\n'
    "              At: Coalesce(r.EventOn, r.Created),\n"
    '              Internal: r.Visibility.Value = "Internal",\n'
    '              IsSystem: k <> "Comment",\n'
    '              File: Coalesce(r.FileName, ""),\n'
    "              SizeKb: Coalesce(r.FileSizeKb, 0),\n"
    "              Initial: atSub })))\n"
    "; false, true));\n"
    "Set(varIbActBusy, false)"
)

# Vedhaeftningerne er SharePoint-vedhaeftninger paa sagens raekke: de
# hentes med brugerens egen forbindelse og kun, hvis brugeren maa laese
# raekken. Foerst naar fanen vaelges.
LOAD_FILES = (
    "Set(varIbFilesBusy, true);\n"
    f"Set(varIbFilesFailed, IfError(Set(varIbFiles, LookUp({cfg.L_TICKETS}, ID = varIbSelId).Attachments); "
    "false, true));\n"
    "Set(varIbFilesFor, varIbSelId);\n"
    "Set(varIbFilesBusy, false)"
)

# Den aabne sag hentes igen efter en aendring - een LookUp paa ID - og
# skrives tilbage i listerne, saa raekken i oversigten passer. Er sagen
# vaek (slettet af en anden admin), lukkes popuppen.
RELOAD_SEL = (
    "With(\n"
    f"    {{ r: LookUp({cfg.L_TICKETS}, ID = varIbSelId) }},\n"
    "    If(\n"
    "        IsBlank(r),\n"
    "        RemoveIf(colIbMine, Id = varIbSelId);\n"
    "        RemoveIf(colIbAll, Id = varIbSelId);\n"
    "        Set(varIbDetailOn, false),\n"
    f"        Set(varIbSel, {_row('r', shared=False)});\n"
    # r.Attachments kan ikke laeses fra With's LookUp - compile: "The
    # specified column is not accessible in this context" (issue #133).
    # Er fanen aaben, hentes filerne igen med LOAD_FILES' egen LookUp;
    # ellers hentes de foerst, naar fanen vaelges.
    "        If(varIbTab = \"files\",\n"
    + "".join("            " + l + "\n" for l in LOAD_FILES.split("\n")) +
    "        , Set(varIbFilesFor, -1));\n"
    "        UpdateIf(colIbMine, Id = varIbSelId, varIbSel);\n"
    "        UpdateIf(colIbAll, Id = varIbSelId, varIbSel)\n"
    "    )\n"
    ")"
)



# Skemaerne for samlingerne. If(false, ...): kun skemaet (check_layout
# regel 34) - App.OnStart maa ikke toemme det, OnVisible fylder.
ROW = {"Id": "0", "TicketNo": '""', "Title": '""', "Description": '""', "Steps": '""',
       "Expected": '""', "Actual": '""', "Application": '""', "Section": '""', "Other": '""',
       "RelatedNo": '""', "Severity": '""', "Priority": '""', "Status": '""',
       "Resolution": '""', "Assigned": '""', "CreatedOn": "Now()", "UpdatedOn": "Now()",
       "Archived": "false", "Reporter": '""', "AssignedEmail": '""', "PriRank": "0",
       "StatusRank": "0"}
SEC = {"Application": '""', "Section": '""', "AppOrder": "0", "SectionOrder": "0",
       "ScreenKey": '""'}
ACT = {"Kind": '""', "Actor": '""', "Body": '""', "At": "Now()", "Internal": "false",
       "IsSystem": "false", "File": '""', "SizeKb": "0", "Initial": "false"}
ADMINS = {"Email": '""', "Name": '""'}
UPLOAD = {"Name": '""', "Msg": '""'}


def collections():
    return [("colIbMine", ROW), ("colIbAll", ROW), ("colIbShared", ROW),
            ("colIbSections", SEC), ("colIbActivity", ACT), ("colIbAdmins", ADMINS),
            ("colIbUp", UPLOAD)]


# ---------------------------------------------------------------------------
# Navngivne formler
# ---------------------------------------------------------------------------
# Formularens to lister staar som udtryk direkte i Items: en dropdowns
# Default er LookUp(Items As _dd, ...), og check_layout regel 30 kan ikke
# se forskel paa en navngiven formel og en SharePoint-liste.
APPS_FX = ('ForAll(Distinct(SortByColumns(colIbSections, "AppOrder", SortOrder.Ascending, '
           '"SectionOrder", SortOrder.Ascending), Application) As a, { Application: a.Value })')
FORM_SECTIONS_FX = ('SortByColumns(Filter(colIbSections, Application = varIbFormApp), '
                    '"SectionOrder", SortOrder.Ascending)')

def _table(values):
    """En literal tabel: ["a", "b"]."""
    return "[" + ", ".join(f'"{v}"' for v in values) + "]"


REOPENABLE_FX = _table(cfg.REOPENABLE)

# ---------------------------------------------------------------------------
FORMULAS = f'''// Issue Board (Issue Board/build/ib_parts.py). Samlingerne hentes i
// skaermens OnVisible; alt herunder regnes i hukommelsen.
// Applications i konfigurationens raekkefoelge.
IbApps = {APPS_FX};
IbFilterSections = SortByColumns(Filter(colIbSections, Application = varIbApp), "SectionOrder", SortOrder.Ascending);
// "Other" i Application eller Section kraever en beskrivelse.
IbOtherNeeded = varIbFormApp = "{cfg.OTHER}" || varIbFormSection = "{cfg.OTHER}";
// Den Application, skaermen man kom fra, hoerer til (gblNavFrom saettes af
// sidebaren). Kun naar konfigurationen siger det - ellers intet gaet.
IbFrom = Coalesce(LookUp(colIbSections, ScreenKey = gblNavFrom && !IsBlank(gblNavFrom)).Application, "");
IbFailed = IfError(varIbCfgFailed, false) || IfError(varIbMineFailed, false) || (varIbScope = "shared" && IfError(varIbSharedFailed, false)) || (varIbScope = "all" && IfError(varIbAllFailed, false));
// Hvad maa brugeren paa den aabne sag? EET sted for knapperne - og samme
// regler som flowet BioSap-IssueBoard-Submit, der afgoer det paa serveren.
// En anonym (delt) sag kan ingen aendre herfra.
IbSelMine = !varIbSelShared && varIbSel.Reporter = varIbMe;
IbCanEdit = !varIbSelShared && !varIbSel.Archived && ({IS_ADMIN} || (IbSelMine && varIbSel.Status = "{cfg.STATUS_EDITABLE}"));
IbCanReopen = !varIbSelShared && !varIbSel.Archived && ({IS_ADMIN} || IbSelMine) && varIbSel.Status in {REOPENABLE_FX};
IbCanManage = !varIbSelShared && {IS_ADMIN};
IbCanComment = !varIbSelShared && !varIbSel.Archived;
// Antallet af filer paa sagen - af Activity, saa fanen kan vise det uden
// at hente filerne.
IbFileCount = CountRows(Filter(colIbActivity, Kind = "Attachment"));'''


# ---------------------------------------------------------------------------
# Status som maerke - tekst OG farve, aldrig kun farve
# ---------------------------------------------------------------------------
def _status_tokens(status_expr, archived_expr):
    def sw(part):
        body = ", ".join(f'"{s}", {_t("state-" + c + "-" + part)}' for s, c, _r in cfg.STATUS)
        return (f"If({archived_expr}, {_t('state-neutral-' + part)}, "
                f"Switch({status_expr}, {body}, {_t('state-neutral-' + part)}))")
    return sw("fg"), sw("bg")


def _status_label(status_expr, archived_expr):
    return f'If({archived_expr}, "Archived", {status_expr})'


CHIP_W = 124
CHIP_H = 24


def _chip(name, status_expr, archived_expr, x=None, y=None, width=CHIP_W):
    fg, bg = _status_tokens(status_expr, archived_expr)
    extra = {"VerticalAlign": "VerticalAlign.Middle", "PaddingLeft": "8", "PaddingRight": "8",
             **lay.radius(12)}
    if x is not None:
        extra["X"] = x
        extra["Y"] = y
    return text_ctrl(name, _status_label(status_expr, archived_expr), size=lay.SIZE_MICRO,
                     weight="Semibold", height=CHIP_H, align="Center", color=fg, fill=bg,
                     width=width, accessible='"Status: " & Self.Text', extra=extra)


# ---------------------------------------------------------------------------
# Bjaelken
# ---------------------------------------------------------------------------
RESET_FORM = ("Reset(drpIbFormApp);\nReset(drpIbFormSection);\nReset(inpIbOther);\nReset(inpIbTitle);\n"
              "Reset(inpIbDesc);\nReset(inpIbSteps);\nReset(inpIbExpected);\nReset(inpIbActual);\n"
              "Reset(inpIbRelated);\nReset(drpIbSeverity);\nReset(attIbNewFiles);\n"
              "Reset(drpIbStatus);\nReset(drpIbPriority);\nReset(drpIbAssignee);\nReset(inpIbResolution)")

OPEN_FORM = (
    LOAD_SHARED + ";\n"
    'Set(varIbFormMode, "new");\n'
    "Set(varIbFormApp, IbFrom);\n"
    'Set(varIbFormSection, "");\n'
    "Set(varIbMore, false);\n"
    + RESET_FORM + ";\n"
    "Set(varIbFormOn, true)"
)

# Admins til "Assigned to" - samme liste som IsAdmin, hentet een gang og
# kun af en admin, der aabner Edit.
LOAD_ADMINS = (
    "If(\n"
    f"    {IS_ADMIN} && !IfError(varIbAdminsLoaded, false),\n"
    "    Set(varIbAdminsLoaded, !IfError(ClearCollect(colIbAdmins,\n"
    f'        ForAll(Filter({ADMIN_LIST}, Title = "{ADMIN_GROUP}") As a,\n'
    f'            {{ Email: Lower(Coalesce(a.Member, "")), Name: {_initials("Coalesce(a.Member, " + chr(34) * 2 + ")")} }})); false, true))\n'
    ")"
)

# Edit: formularen udfyldes fra sagen. View-popuppen lukkes imens og
# aabnes igen, naar man gemmer eller fortryder.
OPEN_EDIT = (
    'Set(varIbFormMode, "edit");\n'
    "Set(varIbFormApp, varIbSel.Application);\n"
    "Set(varIbFormSection, varIbSel.Section);\n"
    "Set(varIbMore, true);\n"
    + LOAD_ADMINS + ";\n"
    + RESET_FORM + ";\n"
    "Set(varIbDetailOn, false);\n"
    "Set(varIbFormOn, true)"
)
CLOSE_FORM = 'Set(varIbFormOn, false);\nIf(varIbFormMode = "edit", Set(varIbDetailOn, true))'


def build_bar():
    new = button("btnIbNew", '"New issue"', OPEN_FORM, primary=True,
                 width=fit_button_width('"New issue"') + ICON_W, height=36, icon="Add",
                 accessible='"Report a new issue"')
    icon_on_mobile(new)
    refresh = button("btnIbRefresh", '"Refresh"', RETRY,
                     width=fit_button_width('"Refresh"'), height=36,
                     accessible='"Load the issues again"',
                     display_mode="If(varIbLoading, DisplayMode.Disabled, DisplayMode.Edit)")
    return top_bar(P, f'"{cfg.TITLE}"',
                   '"Report what you find while testing, and follow it until it is fixed."',
                   [refresh, new], narrow_hide=("btnIbRefresh",), icon=cfg.APP_KEY)


# ---------------------------------------------------------------------------
# Filtre
# ---------------------------------------------------------------------------
CARD_W = f"({SHELL_W} - 2 * {lay.CARD_PAD})"


def _seg(name, label, selected, onselect, width, accessible):
    """Et segment i en kontakt: valgt = fyldt, ikke valgt = kant."""
    b = button(name, f'"{label}"', onselect, width=width, height=34, accessible=accessible)
    b.props["Appearance"] = f"If({selected}, ButtonAppearance.Primary, ButtonAppearance.Outline)"
    b.props["BasePaletteColor"] = C_PRIMARY
    b.props["BorderColor"] = f"If({selected}, {C_PRIMARY}, {C_CARD_BORDER})"
    b.props["BorderThickness"] = "1"
    b.props["Color"] = f"If({selected}, {_t('text-on-primary')}, {C_TITLE})"
    b.props["Size"] = str(lay.SIZE_SMALL)
    b.props["LayoutMinWidth"] = b.props["Width"]
    return b


def _switch_group(name, segs):
    w = sum(int(s.props["Width"]) for s in segs) + 4 * (len(segs) - 1)
    g = group(name, segs, direction="Horizontal", gap=4, height=34, width=str(w),
              align_items="Center")
    g.props["LayoutMinWidth"] = str(w)
    return g


def _filter_dd(name, all_text, values, var, label):
    """En filterliste: "All ..." foerst og derefter vaerdierne."""
    return themed_dropdown(name, _table([all_text] + list(values)),
                           f'If(IsBlank({var}), "{all_text}", {var})', label=label,
                           onchange=f'Set({var}, If(Self.Selected.Value = "{all_text}", "", '
                                    "Self.Selected.Value))")


ADMIN_ALL = f'{IS_ADMIN} && varIbScope = "all"'


def build_filters():
    all_seg = _seg("btnIbScopeAll", "All issues", 'varIbScope = "all"',
                   'Set(varIbScope, "all");\n' + LOAD_ALL, 96,
                   '"Show all issues (administrators)"')
    all_seg.props["Visible"] = IS_ADMIN
    all_seg.vis = IS_ADMIN
    scope = _switch_group("conIbScope", [
        all_seg,
        _seg("btnIbScopeMine", "My issues", 'varIbScope = "mine"',
             'Set(varIbScope, "mine")', 104, '"Show my issues"'),
        _seg("btnIbScopeShared", "Shared issues", 'varIbScope = "shared"',
             'Set(varIbScope, "shared");\n' + LOAD_SHARED, 120,
             '"Show shared issues from all testers, without names"'),
    ])
    # "All issues" staar der kun for en admin - saa er gruppen bredere.
    w_all = int(scope.props["Width"])
    w_user = w_all - 96 - 4
    scope.props["Width"] = f"If({IS_ADMIN}, {w_all}, {w_user})"
    scope.props["LayoutMinWidth"] = scope.props["Width"]
    state = _switch_group("conIbState", [
        _seg("btnIbStateOpen", "Open", 'varIbState = "open"', 'Set(varIbState, "open")', 76,
             '"Show open issues"'),
        _seg("btnIbStateClosed", "Closed", 'varIbState = "closed"', 'Set(varIbState, "closed")', 84,
             '"Show closed issues"'),
        _seg("btnIbStateArchived", "Archived", 'varIbState = "archived"',
             'Set(varIbState, "archived")', 92, '"Show archived issues"'),
    ])
    top_w = w_all + 16 + int(state.props["Width"])
    top_ok = f"({CARD_W}) >= {top_w}"
    top = group("conIbSwitches", [scope, state], direction="Horizontal", gap=16,
                height=f"If({top_ok}, 34, 34 + 8 + 34)", align_items="Start")
    top.props["LayoutDirection"] = f"If({top_ok}, LayoutDirection.Horizontal, LayoutDirection.Vertical)"
    top.props["LayoutGap"] = f"If({top_ok}, 16, 8)"

    search = text_input("inpIbSearch", '""', placeholder='"Search number, title or description"',
                        label='"Search issues"')
    app_items = ('Ungroup(Table({ x: Table({ Application: "All applications" }) }, '
                 "{ x: IbApps }), x)")
    drp_app = themed_dropdown("drpIbFltApp", app_items,
                              'If(IsBlank(varIbApp), "All applications", varIbApp)',
                              value_col="Application", label='"Filter by application"',
                              onchange=('Set(varIbApp, If(Self.Selected.Application = "All applications", '
                                        '"", Self.Selected.Application));\nSet(varIbSection, "");\n'
                                        "Reset(drpIbFltSection)"))
    sec_items = ('Ungroup(Table({ x: Table({ Section: "All sections" }) }, '
                 "{ x: ShowColumns(IbFilterSections, Section) }), x)")
    drp_sec = themed_dropdown("drpIbFltSection", sec_items,
                              'If(IsBlank(varIbSection), "All sections", varIbSection)',
                              value_col="Section", label='"Filter by section"',
                              display_mode="If(IsBlank(varIbApp), DisplayMode.Disabled, DisplayMode.Edit)",
                              onchange=('Set(varIbSection, If(Self.Selected.Section = "All sections", '
                                        '"", Self.Selected.Section))'))
    drp_sort = themed_dropdown("drpIbSort", '["Last updated", "Newest", "Priority", "Status"]',
                               "varIbSort", label='"Sort issues"',
                               onchange="Set(varIbSort, Self.Selected.Value)")
    # Soegefeltet tager resten; de tre lister har faste bredder. Er der
    # ikke plads paa een linje, staar alt under hinanden i fuld bredde.
    widths = {"drpIbFltApp": 210, "drpIbFltSection": 210, "drpIbSort": 150}
    fixed = sum(widths.values()) + 3 * 8 + 220
    ok = f"({CARD_W}) >= {fixed}"
    for c in (drp_app, drp_sec, drp_sort):
        c.props["Width"] = f"If({ok}, {widths[c.name]}, {CARD_W})"
        c.props["LayoutMinWidth"] = f"If({ok}, {widths[c.name]}, 0)"
    search.props["Width"] = f"If({ok}, {CARD_W} - {fixed - 220}, {CARD_W})"
    row = group("conIbFltRow", [search, drp_app, drp_sec, drp_sort], direction="Horizontal",
                gap=8, height=f"If({ok}, 36, 4 * 36 + 3 * 8)")
    row.props["LayoutDirection"] = f"If({ok}, LayoutDirection.Horizontal, LayoutDirection.Vertical)"

    # Anden raekke: status, prioritet, alvor - og for admin "Assigned to me".
    drp_status = _filter_dd("drpIbFltStatus", "All statuses", [s for s, _c, _r in cfg.STATUS],
                            "varIbStatusF", '"Filter by status"')
    drp_pri = _filter_dd("drpIbFltPriority", "All priorities", [p for p, _r in cfg.PRIORITY],
                         "varIbPriF", '"Filter by priority"')
    drp_sev = _filter_dd("drpIbFltSeverity", "All severities", cfg.SEVERITY,
                         "varIbSevF", '"Filter by severity"')
    mine_seg = _seg("btnIbAssignedMe", "Assigned to me", "varIbAssignedMe",
                    "Set(varIbAssignedMe, !varIbAssignedMe)", 136,
                    'If(varIbAssignedMe, "Show all assignments", "Show only issues assigned to me")')
    mine_seg.props["Height"] = "36"
    mine_seg.h = 36
    mine_seg.props["Visible"] = ADMIN_ALL
    mine_seg.vis = ADMIN_ALL
    widths2 = {"drpIbFltStatus": 180, "drpIbFltPriority": 170, "drpIbFltSeverity": 170,
               "btnIbAssignedMe": 136}
    fixed2 = sum(widths2.values()) + 3 * 8
    ok2 = f"({CARD_W}) >= {fixed2}"
    for c in (drp_status, drp_pri, drp_sev, mine_seg):
        c.props["Width"] = f"If({ok2}, {widths2[c.name]}, {CARD_W})"
        c.props["LayoutMinWidth"] = f"If({ok2}, {widths2[c.name]}, 0)"
    row2 = group("conIbFltRow2", [drp_status, drp_pri, drp_sev, mine_seg], direction="Horizontal",
                 gap=8, height=f"If({ok2}, 36, If({ADMIN_ALL}, 4 * 36 + 3 * 8, 3 * 36 + 2 * 8))")
    row2.props["LayoutDirection"] = f"If({ok2}, LayoutDirection.Horizontal, LayoutDirection.Vertical)"

    note = text_ctrl("txtIbSharedNote",
                     '"Shared issues are anonymous: they never show who reported them, '
                     'and comments stay private."',
                     size=lay.SIZE_SMALL, color=C_INFO_FG, height=34, wrap="true",
                     visible='varIbScope = "shared"',
                     extra={"Fill": C_INFO_BG, "PaddingLeft": "12", "PaddingRight": "12",
                            "PaddingTop": "8", **lay.radius(10)})
    return card("conIbFilterCard", [top, row, row2, note], gap=12)


# ---------------------------------------------------------------------------
# Listen
# ---------------------------------------------------------------------------
ROW_H = 68
ROW_PAD = 12
NO_W = 96
GAL_ROWS = 10
OPEN_ROW = (
    "Set(varIbSel, ThisItem);\n"
    "Set(varIbSelId, ThisItem.Id);\n"
    'Set(varIbSelShared, varIbScope = "shared");\n'
    'Set(varIbTab, "details");\n'
    "Set(varIbInternal, false);\n"
    "Set(varIbFilesFor, -1);\n"
    "Reset(inpIbComment);\n"
    "Clear(colIbActivity);\n"
    "Set(varIbDetailOn, true);\n"
    "If(!varIbSelShared, " + LOAD_ACTIVITY + ")"
)

LIST_ITEMS = (
    "With(\n"
    '    { q: Trim(inpIbSearch.Text), t: Switch(varIbScope, "shared", colIbShared, "all", colIbAll, '
    "colIbMine) },\n"
    "    With(\n"
    "        { f: Filter(t,\n"
    f'              Switch(varIbState, "closed", !Archived && Status = "{cfg.STATUS_CLOSED}", '
    f'"archived", Archived, !Archived && Status <> "{cfg.STATUS_CLOSED}"),\n'
    "              IsBlank(varIbApp) || Application = varIbApp,\n"
    "              IsBlank(varIbSection) || Section = varIbSection,\n"
    "              IsBlank(varIbStatusF) || Status = varIbStatusF,\n"
    "              IsBlank(varIbPriF) || Priority = varIbPriF,\n"
    "              IsBlank(varIbSevF) || Severity = varIbSevF,\n"
    f"              !(varIbAssignedMe && {ADMIN_ALL}) || AssignedEmail = varIbMe,\n"
    "              IsBlank(q) || q in TicketNo || q in Title || q in Description) },\n"
    "        Switch(\n"
    "            varIbSort,\n"
    '            "Newest", SortByColumns(f, "CreatedOn", SortOrder.Descending),\n'
    '            "Priority", SortByColumns(f, "PriRank", SortOrder.Ascending, "UpdatedOn", SortOrder.Descending),\n'
    '            "Status", SortByColumns(f, "StatusRank", SortOrder.Ascending, "UpdatedOn", SortOrder.Descending),\n'
    '            SortByColumns(f, "UpdatedOn", SortOrder.Descending)\n'
    "        )\n"
    "    )\n"
    ")"
)

WHEN = 'Text(ThisItem.UpdatedOn, "dd mmm yyyy")'


def build_list():
    tw = "Parent.TemplateWidth"
    no = text_ctrl("txtIbRowNo", "ThisItem.TicketNo", size=lay.SIZE_BODY, weight="Semibold",
                   color=C_PRIMARY, height=20, width=NO_W, visible=at_least("Tablet"),
                   extra={"X": str(ROW_PAD), "Y": "12"})
    title_x = if_below("Tablet", str(ROW_PAD), str(ROW_PAD + NO_W + 8))
    title = text_ctrl("txtIbRowTitle", "ThisItem.Title", size=lay.SIZE_INPUT, weight="Semibold",
                      height=21, width=f"{tw} - ({title_x}) - {ROW_PAD} - {CHIP_W} - 12",
                      extra={"X": title_x, "Y": "11"})
    meta = text_ctrl(
        "txtIbRowMeta",
        f'If({NARROW}, ThisItem.TicketNo & "  ·  ", "") & ThisItem.Application & "  ·  " & '
        'ThisItem.Section & If(IsBlank(ThisItem.Severity), "", "  ·  " & ThisItem.Severity) & '
        f'"  ·  Updated " & {WHEN} & '
        'If(varIbScope = "all", "  ·  " & If(IsBlank(ThisItem.Assigned), "Unassigned", '
        '"Assigned to " & ThisItem.Assigned), "")',
        size=lay.SIZE_SMALL, color=C_MUTED, height=18,
        width=f"{tw} - {2 * ROW_PAD} - {CHIP_W} - 12", extra={"X": str(ROW_PAD), "Y": "40"})
    chip = _chip("txtIbRowStatus", "ThisItem.Status", "ThisItem.Archived",
                 x=f"{tw} - {ROW_PAD} - {CHIP_W}", y="11")
    pri = text_ctrl("txtIbRowPriority",
                    'If(IsBlank(ThisItem.Priority), "", ThisItem.Priority & " priority")',
                    size=lay.SIZE_SMALL, color=C_MUTED, height=18, align="Right", width=CHIP_W,
                    visible=at_least("Tablet"),
                    extra={"X": f"{tw} - {ROW_PAD} - {CHIP_W}", "Y": "40"})
    rule = row_rule("rctIbRowRule", ROW_H)
    hit = row_hit("btnIbRowOpen", OPEN_ROW,
                  '"Open " & ThisItem.TicketNo & " - " & ThisItem.Title', tw, ROW_H - 1)
    gal_h = f"Max(1, Min(galIbList.AllItemsCount, {GAL_ROWS})) * {ROW_H}"
    gal = Ctrl("galIbList", "Gallery", variant="Vertical", props={
        "AccessibleLabel": '"Issues"',
        "BorderStyle": "BorderStyle.None", "Fill": C_CARD_BG, "FillPortions": "0",
        "Height": gal_h, "Items": LIST_ITEMS, "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None", "Selectable": "false",
        "ShowScrollbar": "true", "TabIndex": "0", "TemplatePadding": "0",
        "TemplateSize": str(ROW_H), "Width": "Parent.Width", "WrapCount": "1",
    }, children=[no, title, meta, chip, pri, rule, hit], h=gal_h,
        vis="galIbList.AllItemsCount > 0")

    count = text_ctrl("txtIbCount",
                      'galIbList.AllItemsCount & If(galIbList.AllItemsCount = 1, '
                      '" issue", " issues")',
                      size=lay.SIZE_BODY, weight="Semibold", color=C_MUTED, height=20)
    # Admin-boardets taellere: det, der venter paa en admin.
    open_all = f'!Archived && Status <> "{cfg.STATUS_CLOSED}"'
    counts = text_ctrl(
        "txtIbAdminCounts",
        f'CountIf(colIbAll, {open_all}) & " open  ·  " & '
        f'CountIf(colIbAll, !Archived && Status = "{cfg.STATUS_NEW}") & " new  ·  " & '
        f'CountIf(colIbAll, {open_all} && IsBlank(AssignedEmail)) & " unassigned  ·  " & '
        f'CountIf(colIbAll, {open_all} && AssignedEmail = varIbMe) & " assigned to you"',
        size=lay.SIZE_SMALL, color=C_MUTED, height=34, wrap="true", visible=ADMIN_ALL)
    empty_fx = (
        'If(varIbLoading, "Loading issues...", '
        "IbFailed, \"The issues could not be loaded. Check your connection and try again.\", "
        'varIbScope = "mine" && IsEmpty(colIbMine), '
        '"You have not reported any issues yet. Use New issue to report one.", '
        'varIbScope = "all" && IsEmpty(colIbAll), "No issues have been reported yet.", '
        'varIbScope = "shared" && IsEmpty(colIbShared), "No issues have been shared yet.", '
        '"No issues match the filters.")')
    empty = text_ctrl("txtIbEmpty", empty_fx, size=lay.SIZE_BODY, height=40, wrap="true",
                      color=f"If(IbFailed, {C_INVALID_FG}, {C_MUTED})",
                      visible="galIbList.AllItemsCount = 0")
    retry = button("btnIbRetry", '"Retry"', RETRY, width=fit_button_width('"Retry"'), height=36,
                   visible="IbFailed && !varIbLoading", accessible='"Load the issues again"')
    retry.props["AlignInContainer"] = "AlignInContainer.Start"
    return card("conIbListCard", [count, counts, gal, empty, retry], gap=8)


# ---------------------------------------------------------------------------
# Popupperne - faelles maal
# ---------------------------------------------------------------------------
POP_PAD = 18
POP_W = "Min(760, App.Width - 24)"
POP_IN = f"({POP_W} - {2 * POP_PAD})"
LINE_H = 19


def _lines_h(text, width, px=7.2):
    """Hoejden af en ombrudt tekst: antal linjer regnet af laengden og
    linjeskiftene. Hellere en linje luft end en klippet linje."""
    cpl = f"Max(12, RoundDown(({width}) / {px}, 0))"
    return (f"With({{ t: {text} }}, (RoundUp(Len(t) / {cpl}, 0) + "
            f"CountRows(Split(t, Char(10))) - 1) * {LINE_H} + 2)")


def _popup(prefix, kids, vis, width=POP_W):
    modal = group(f"con{prefix}Modal", kids, direction="Vertical", gap=12, fill=C_MODAL_BG,
                  border_color=C_PRIMARY_SOFT, radius=lay.RADIUS_MODAL,
                  pad=(POP_PAD, POP_PAD, POP_PAD, POP_PAD), width=width,
                  drop_shadow="ExtraBold", align_in_container="Center")
    backdrop = group(f"con{prefix}Backdrop", [modal], direction="Vertical", gap=0,
                     height="App.Height", width="App.Width", fill=C_OVERLAY, visible=vis,
                     justify="Start", align_items="Center", pad=(16, 0, 16, 0),
                     overflow_y="Scroll")
    backdrop.props["X"] = "0"
    backdrop.props["Y"] = "0"
    return backdrop


def _head(prefix, title_fx, close_fx, lead=()):
    title = grow(text_ctrl(f"txt{prefix}Title", title_fx, size=lay.SIZE_CARD_TITLE,
                           weight="Semibold", height=26))
    close = button(f"btn{prefix}Close", '"Close"', close_fx,
                   width=fit_button_width('"Close"'), height=32)
    return group(f"con{prefix}Head", [*lead, title, close], direction="Horizontal", gap=10,
                 height=32, align_items="Center")


def _field(name, label, ctrl, required=False, visible=None):
    g = group(name, [label_row(name, label, required=required), ctrl], direction="Vertical",
              gap=6, visible=visible)
    return g


# ---------------------------------------------------------------------------
# New issue
# ---------------------------------------------------------------------------
FORM_ON = "IfError(varIbFormOn, false)"
VALID = ("!IsBlank(varIbFormApp) && !IsBlank(varIbFormSection) && "
         "(!IbOtherNeeded || !IsBlank(Trim(inpIbOther.Text))) && "
         "Len(Trim(inpIbTitle.Text)) >= 4 && !IsBlank(Trim(inpIbDesc.Text))")
PAGE_FX = 'Coalesce(If(IbFrom = "", Blank(), IbFrom), "the Issue Board")'
LAYOUT_FX = (f'Left("Opened from " & {PAGE_FX} & " · " & LayoutContext & " layout · " & '
             'App.Width & " x " & App.Height, 250)')
CLIENT_FX = 'Left(Host.OSType & " · " & Host.BrowserUserAgent, 250)'
FALLBACK = '{ ok: "no", message: FirstError.Message, ticketno: "", ticketid: "" }'


def _upload(picker, ticket_id, initial, dup_check=None):
    """Hver valgt fil gennem flowet (handlingen attach) - som dokument-
    ruden (tools/attflows.py): ForAll giver een tabel, og ClearCollect
    skriver den i eet kald. Msg er tom, naar filen kom igennem, ellers
    grunden. dup_check: udtryk, der er sandt, naar F.Name allerede findes."""
    run = (f"IfError({cfg.FLOW}.Run(\n"
           f'                \"{cfg.ACT_ATTACH}\",\n'
           f"                JSON({{ ticketId: {ticket_id}, initial: {initial} }}),\n"
           "                { file: { contentBytes: F.Value, name: F.Name } }\n"
           f"            ), {FALLBACK})")
    msg = (f'With({{ res: {run} }}, If(res.ok = "yes", "", Coalesce(res.message, "not saved")))')
    if dup_check:
        msg = f'If({dup_check}, "a file with this name is already attached", {msg})'
    return (
        "ClearCollect(\n"
        "    colIbUp,\n"
        f"    ForAll({picker}.Attachments As F, {{ Name: F.Name, Msg: {msg} }})\n"
        ")"
    )


UP_FAILED = "Filter(colIbUp, !IsBlank(Msg))"

# Formularen tom igen efter en indsendt sag. Variablerne foerst - Default
# paa Application og Section laeser dem.
CLEAR_FORM = ('Set(varIbFormApp, "");\nSet(varIbFormSection, "");\nSet(varIbMore, false);\n'
              + RESET_FORM)

# Den nye sag i View mode - som et klik paa raekken (OPEN_ROW), men fra
# colIbMine paa flowets ID. Er den ikke i listen (hentningen fejlede),
# staar sagsnummeret stadig i beskeden.
SHOW_NEW = (
    "Set(varIbSelId, Value(varIbRes.ticketid));\n"
    "Set(varIbSel, LookUp(colIbMine, Id = varIbSelId));\n"
    "If(\n"
    "    !IsBlank(varIbSel),\n"
    "    Set(varIbSelShared, false);\n"
    '    Set(varIbTab, "details");\n'
    "    Set(varIbInternal, false);\n"
    "    Set(varIbFilesFor, -1);\n"
    "    Reset(inpIbComment);\n"
    "    " + LOAD_ACTIVITY.replace("\n", "\n    ") + ";\n"
    "    Set(varIbDetailOn, true)\n"
    ")"
)
UP_FAILED_TEXT = f'Concat({UP_FAILED}, Name & " (" & Msg & ")", "; ")'

SUBMIT = (
    "Set(varIbBusy, true);\n"
    f"Set(varIbRes, IfError({cfg.FLOW}.Run(\n"
    f'    "{cfg.ACT_CREATE}",\n'
    "    JSON({\n"
    "        title: Trim(inpIbTitle.Text),\n"
    "        description: Trim(inpIbDesc.Text),\n"
    "        steps: Trim(inpIbSteps.Text),\n"
    "        expected: Trim(inpIbExpected.Text),\n"
    "        actual: Trim(inpIbActual.Text),\n"
    "        application: varIbFormApp,\n"
    "        section: varIbFormSection,\n"
    '        other: If(IbOtherNeeded, Trim(inpIbOther.Text), ""),\n'
    "        relatedNo: Trim(inpIbRelated.Text),\n"
    f'        severity: Coalesce(drpIbSeverity.Selected.Value, "{cfg.SEVERITY_DEFAULT}"),\n'
    f"        layout: {LAYOUT_FX},\n"
    f"        client: {CLIENT_FX}\n"
    "    })\n"
    f"), {FALLBACK}));\n"
    "If(\n"
    '    varIbRes.ok = "yes",\n'
    # Filerne foerst nu: de laegges paa den raekke, flowet lige har oprettet
    # og laast. Fejler en fil, er sagen stadig meldt - beskeden siger hvilke.
    "    Clear(colIbUp);\n"
    "    If(\n"
    "        CountRows(attIbNewFiles.Attachments) > 0,\n"
    "        Set(varIbUploading, true);\n"
    "        " + _upload("attIbNewFiles", "Value(varIbRes.ticketid)", "true").replace("\n", "\n        ")
    + ";\n"
    "        Set(varIbUploading, false)\n"
    "    );\n"
    f"    {RELOAD_MINE};\n"
    "    Set(varIbSharedLoaded, false);\n"
    "    Set(varIbAllLoaded, false);\n"
    '    Set(varIbScope, "mine");\n'
    '    Set(varIbState, "open");\n'
    # Foerst nu lukkes og nulstilles formularen - sagen findes, og
    # rettighederne er sat, foer flowet svarer ok (issue #135).
    "    Set(varIbFormOn, false);\n"
    "    " + CLEAR_FORM.replace("\n", "\n    ") + ";\n"
    # Den nye sag vises med det samme: den aabnes fra den friske liste, saa
    # et aktivt filter eller en soegning ikke kan skjule den.
    "    " + SHOW_NEW.replace("\n", "\n    ") + ";\n"
    "    If(\n"
    f"        CountRows({UP_FAILED}) > 0,\n"
    '        Notify("Issue " & varIbRes.ticketno & " has been submitted, but these files were not '
    f'attached: " & {UP_FAILED_TEXT} & ". Open the issue to try again.", NotificationType.Warning),\n'
    '        Notify("Thank you. Issue " & varIbRes.ticketno & " has been submitted.", '
    "NotificationType.Success)\n"
    "    ),\n"
    # Fejler det, bliver popuppen staaende med det indtastede (issue #135).
    '    Notify("The issue could not be submitted. " & Coalesce(varIbRes.message, "Please try again."), '
    "NotificationType.Error)\n"
    ");\n"
    "Set(varIbBusy, false)"
)

# Edit: rapportoeren sender felterne; en admin desuden status, prioritet,
# tildeling og loesning. Flowet afgoer, hvad der maa aendres, og skriver
# een haendelse pr. aendring.
SAVE_EDIT = (
    "Set(varIbBusy, true);\n"
    f"Set(varIbRes, IfError({cfg.FLOW}.Run(\n"
    f'    "{cfg.ACT_EDIT}",\n'
    "    JSON({\n"
    "        ticketId: varIbSelId,\n"
    "        title: Trim(inpIbTitle.Text),\n"
    "        description: Trim(inpIbDesc.Text),\n"
    "        steps: Trim(inpIbSteps.Text),\n"
    "        expected: Trim(inpIbExpected.Text),\n"
    "        actual: Trim(inpIbActual.Text),\n"
    "        application: varIbFormApp,\n"
    "        section: varIbFormSection,\n"
    '        other: If(IbOtherNeeded, Trim(inpIbOther.Text), ""),\n'
    "        relatedNo: Trim(inpIbRelated.Text),\n"
    f'        severity: Coalesce(drpIbSeverity.Selected.Value, "{cfg.SEVERITY_DEFAULT}"),\n'
    "        status: Coalesce(drpIbStatus.Selected.Value, varIbSel.Status),\n"
    f'        priority: Coalesce(drpIbPriority.Selected.Value, varIbSel.Priority, "{cfg.PRIORITY_DEFAULT}"),\n'
    '        assignee: Coalesce(drpIbAssignee.Selected.Email, ""),\n'
    "        resolution: Trim(inpIbResolution.Text)\n"
    "    })\n"
    f"), {FALLBACK}));\n"
    "If(\n"
    '    varIbRes.ok = "yes",\n'
    "    " + RELOAD_SEL.replace("\n", "\n    ") + ";\n"
    "    " + LOAD_ACTIVITY.replace("\n", "\n    ") + ";\n"
    "    Set(varIbSharedLoaded, false);\n"
    "    Set(varIbFormOn, false);\n"
    "    Set(varIbDetailOn, true);\n"
    '    Notify("Your changes have been saved.", NotificationType.Success),\n'
    '    Notify("The changes could not be saved. " & Coalesce(varIbRes.message, "Please try again."), '
    "NotificationType.Error)\n"
    ");\n"
    "Set(varIbBusy, false)"
)

SIMILAR_ITEMS = (
    "With(\n"
    '    { w: Filter(ForAll(Split(Trim(inpIbTitle.Text), " ") As s, { Word: s.Value }), Len(Word) >= 4) },\n'
    "    FirstN(\n"
    "        SortByColumns(\n"
    "            Filter(\n"
    "                ForAll(Filter(colIbShared, !Archived) As S,\n"
    "                    { TicketNo: S.TicketNo, Title: S.Title, Status: S.Status, Archived: S.Archived,\n"
    "                      Where: S.Application & \"  ·  \" & S.Section, Row: S,\n"
    "                      Hits: CountRows(Filter(w, Word in S.Title)),\n"
    "                      Score: CountRows(Filter(w, Word in S.Title || Word in S.Description)) +\n"
    "                             If(S.Application = varIbFormApp, 2, 0) + If(S.Section = varIbFormSection, 1, 0) }),\n"
    "                Hits > 0),\n"
    '            "Score", SortOrder.Descending),\n'
    "        3)\n"
    ")"
)

SIM_ROW_H = 44


FORM_W = "Min(680, App.Width - 24)"
FORM_IN = f"({FORM_W} - {2 * POP_PAD})"


def _pair(name, a, b, inner=FORM_IN):
    """To felter side om side - under hinanden paa en telefon."""
    ok = at_least("Tablet")
    w = f"If({ok}, ({inner} - 12) / 2, {inner})"
    for c in (a, b):
        c.props["Width"] = w
        c.props["LayoutMinWidth"] = "0"
    one = f"Max({a.h}, {b.h})"
    g = group(name, [a, b], direction="Horizontal", gap=12,
              height=f"If({ok}, {one}, ({a.h}) + 12 + ({b.h}))", align_items="Start")
    g.props["LayoutDirection"] = f"If({ok}, LayoutDirection.Horizontal, LayoutDirection.Vertical)"
    return g


EDITING = 'varIbFormMode = "edit"'


def _dflt(field, empty='""'):
    """Feltets Default: sagens vaerdi i Edit, ellers tomt."""
    return f"If({EDITING}, {SEL_REF}.{field}, {empty})"


SEL_REF = "varIbSel"


def _attachments(name, label):
    """Vaelg filer - den faelles moderne Attachments-kontrol
    (tools/doc_upload.py, issue #134). Filerne sendes foerst, naar man
    trykker; flowkaldet (_upload) laeser Name og Value som foer."""
    return du.picker(name, label, cfg.MAX_FILES, cfg.MAX_FILE_MB,
                     display_mode="If(varIbUploading, DisplayMode.Disabled, DisplayMode.Edit)")


def _differs(ctrl, field):
    return f"Trim({ctrl}.Text) <> Trim({SEL_REF}.{field})"


# Har brugeren skrevet noget, der ikke er gemt? Ny sag: noget udfyldt ud
# over den Application, skaermen selv foreslog. Edit: noget aendret i
# forhold til sagen. Admin-felterne taeller kun for en admin - kun han
# ser dem (issue #135).
_TEXTS = [("inpIbOther", "Other"), ("inpIbTitle", "Title"), ("inpIbDesc", "Description"),
          ("inpIbSteps", "Steps"), ("inpIbExpected", "Expected"), ("inpIbActual", "Actual"),
          ("inpIbRelated", "RelatedNo")]
FORM_DIRTY = (
    "If(\n"
    f"    {EDITING},\n"
    f"    varIbFormApp <> {SEL_REF}.Application || varIbFormSection <> {SEL_REF}.Section ||\n"
    + "".join(f"    {_differs(c, f)} ||\n" for c, f in _TEXTS) +
    f'    Coalesce(drpIbSeverity.Selected.Value, "") <> If(IsBlank({SEL_REF}.Severity), '
    f'"{cfg.SEVERITY_DEFAULT}", {SEL_REF}.Severity) ||\n'
    f"    ({IS_ADMIN} && (\n"
    f'        Coalesce(drpIbStatus.Selected.Value, "") <> {SEL_REF}.Status ||\n'
    f'        Coalesce(drpIbPriority.Selected.Value, "") <> Coalesce({SEL_REF}.Priority, '
    f'"{cfg.PRIORITY_DEFAULT}") ||\n'
    f"        If(IsBlank(drpIbAssignee.Selected), {SEL_REF}.AssignedEmail, "
    f"drpIbAssignee.Selected.Email) <> {SEL_REF}.AssignedEmail ||\n"
    f'        {_differs("inpIbResolution", "Resolution")})),\n'
    '    Coalesce(varIbFormApp, "") <> IbFrom || !IsBlank(varIbFormSection) ||\n'
    + "".join(f"    !IsBlank(Trim({c}.Text)) ||\n" for c, _f in _TEXTS) +
    f'    Coalesce(drpIbSeverity.Selected.Value, "{cfg.SEVERITY_DEFAULT}") <> "{cfg.SEVERITY_DEFAULT}" ||\n'
    "    CountRows(attIbNewFiles.Attachments) > 0\n"
    ")"
)

# Close er formularens eneste vej ud (Cancel er fjernet, issue #135). Med
# noget usagt spoerges der foerst - samme bekraeftelse som "New request"
# i VH-planen (build_helpers.confirm_modal). Ikke mens et kald koerer.
CLOSE_ASK = (
    "If(\n"
    "    !varIbBusy,\n"
    "    If(\n"
    "        " + FORM_DIRTY.replace("\n", "\n        ") + ",\n"
    "        Set(varIbDiscardOn, true),\n"
    "        " + CLOSE_FORM.replace("\n", "\n        ") + "\n"
    "    )\n"
    ")"
)


def build_discard():
    return confirm_modal(
        "IbDiscard", "varIbDiscardOn", "Discard unsaved changes?",
        f'If({EDITING}, "Your changes to " & {SEL_REF}.TicketNo & " have not been saved. '
        'They are lost if you close.", "The issue has not been submitted. What you have '
        'entered is lost if you close.")',
        "Discard and close", CLOSE_FORM, "btnIbDiscardConfirm", icon=None)


def build_form():
    head = _head("IbForm", f'If({EDITING}, "Edit " & {SEL_REF}.TicketNo, "New issue")', CLOSE_ASK)
    intro = text_ctrl("txtIbFormIntro",
                      f'If({EDITING}, "Edit mode. Change what is needed and select Save changes - '
                      'every change is recorded in the activity.", '
                      '"Tell us what happened. Fields marked * are required. Only you and the '
                      'administrators can see your name and the comments.")',
                      size=lay.SIZE_BODY, color=C_MUTED, height=40, wrap="true")

    app = themed_dropdown("drpIbFormApp", APPS_FX, "varIbFormApp", value_col="Application",
                          required_formula="true", label='"Application, required"',
                          onchange=("Set(varIbFormApp, Self.Selected.Application);\n"
                                    'Set(varIbFormSection, "");\nReset(drpIbFormSection)'))
    sec = themed_dropdown("drpIbFormSection", FORM_SECTIONS_FX, "varIbFormSection",
                          value_col="Section", required_formula="true",
                          label='"Section, required"',
                          display_mode="If(IsBlank(varIbFormApp), DisplayMode.Disabled, DisplayMode.Edit)",
                          onchange="Set(varIbFormSection, Self.Selected.Section)")
    where = _pair("conIbFormWhere", _field("conIbFormApp", "Application", app, required=True),
                  _field("conIbFormSec", "Section", sec, required=True))
    sec_hint = text_ctrl("txtIbFormSecHint", '"Pick an application first."', size=lay.SIZE_SMALL,
                         color=C_MUTED, height=18, visible="IsBlank(varIbFormApp)")

    other = text_input("inpIbOther", _dflt("Other"), placeholder='"Which application or part of the app?"',
                       max_length=250, required_formula="true",
                       label='"Describe the application or section, required"')
    other_f = _field("conIbFormOther", "Describe where it happened", other, required=True,
                     visible="IbOtherNeeded")

    title = text_input("inpIbTitle", _dflt("Title"), placeholder='"A short summary, e.g. Save draft does nothing"',
                       max_length=120, required_formula="true", label='"Title, required"')
    title_f = _field("conIbFormTitleF", "Title", title, required=True)

    # Lignende sager - fra den ANONYME liste. Intet her kan vise en anden
    # brugers navn eller kommentarer.
    sim_head = text_ctrl("txtIbSimHead", '"Similar shared issues - is yours already reported?"',
                         size=lay.SIZE_SMALL, weight="Semibold", color=C_INFO_FG, height=18)
    tw = "Parent.TemplateWidth"
    s_no = text_ctrl("txtIbSimNo", "ThisItem.TicketNo", size=lay.SIZE_SMALL, weight="Semibold",
                     color=C_PRIMARY, height=18, width=NO_W, extra={"X": "8", "Y": "4"})
    s_title = text_ctrl("txtIbSimTitle", "ThisItem.Title", size=lay.SIZE_BODY, height=20,
                        width=f"{tw} - {NO_W + 16} - {CHIP_W} - 8",
                        extra={"X": str(NO_W + 16), "Y": "3"})
    s_where = text_ctrl("txtIbSimWhere", "ThisItem.Where", size=lay.SIZE_SMALL, color=C_MUTED,
                        height=18, width=f"{tw} - 16 - {CHIP_W} - 8", extra={"X": "8", "Y": "23"})
    s_chip = _chip("txtIbSimStatus", "ThisItem.Status", "ThisItem.Archived",
                   x=f"{tw} - {CHIP_W} - 4", y="10")
    s_hit = row_hit("btnIbSimOpen",
                    "Set(varIbSel, ThisItem.Row);\nSet(varIbSelId, ThisItem.Row.Id);\n"
                    'Set(varIbSelShared, true);\nSet(varIbTab, "details");\nSet(varIbDetailOn, true)',
                    '"Open shared issue " & ThisItem.TicketNo & " - " & ThisItem.Title',
                    tw, SIM_ROW_H - 2, radius=8)
    sim_h = f"galIbSimilar.AllItemsCount * {SIM_ROW_H}"
    sim = Ctrl("galIbSimilar", "Gallery", variant="Vertical", props={
        "AccessibleLabel": '"Similar shared issues"',
        "BorderStyle": "BorderStyle.None", "Fill": C_TRANSPARENT, "FillPortions": "0",
        "Height": sim_h, "Items": SIMILAR_ITEMS, "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None", "Selectable": "false",
        "ShowScrollbar": "false", "TabIndex": "0", "TemplatePadding": "0",
        "TemplateSize": str(SIM_ROW_H), "Width": "Parent.Width", "WrapCount": "1",
    }, children=[s_no, s_title, s_where, s_chip, s_hit], h=sim_h)
    similar = group("conIbSimilar", [sim_head, sim], direction="Vertical", gap=6,
                    fill=C_INFO_BG, radius=10, pad=(10, 10, 10, 10),
                    visible=f"!({EDITING}) && galIbSimilar.AllItemsCount > 0")

    desc = text_input("inpIbDesc", _dflt("Description"), placeholder='"What did you do, and what went wrong?"',
                      max_length=4000, required_formula="true", height=110, ttype="Multiline",
                      label='"What happened, required"')
    desc_f = _field("conIbFormDesc", "What happened?", desc, required=True)

    more = button("btnIbMore", 'If(varIbMore, "Hide details", "Add more details (optional)")',
                  "Set(varIbMore, !varIbMore)",
                  width=fit_button_width('"Add more details (optional)"'), height=34,
                  icon='If(varIbMore, "ChevronUp", "ChevronDown")',
                  accessible='If(varIbMore, "Hide the optional details", "Show the optional details")')
    more.props["AlignInContainer"] = "AlignInContainer.Start"
    more.props["Width"] = str(fit_button_width('"Add more details (optional)"') + ICON_W)

    def area(name, label, placeholder, field):
        c = text_input(name, _dflt(field), placeholder=f'"{placeholder}"', max_length=4000,
                       height=72, ttype="Multiline", label=f'"{label}"')
        return _field(f"con{name[3:]}F", label, c)

    steps = area("inpIbSteps", "Steps to reproduce", "1. Open ... 2. Select ... 3. ...", "Steps")
    expected = area("inpIbExpected", "Expected result", "What should have happened?", "Expected")
    actual = area("inpIbActual", "Actual result", "What happened instead?", "Actual")
    related = text_input("inpIbRelated", _dflt("RelatedNo"), placeholder='"e.g. MP0142"',
                         max_length=40, label='"Related request number"')
    severity = themed_dropdown("drpIbSeverity", _table(cfg.SEVERITY),
                               f'If({EDITING} && !IsBlank({SEL_REF}.Severity), {SEL_REF}.Severity, '
                               f'"{cfg.SEVERITY_DEFAULT}")',
                               label='"How serious is it?"')
    extra_row = _pair("conIbFormExtra", _field("conIbFormRelated", "Related request number", related),
                      _field("conIbFormSeverity", "How serious is it?", severity))
    details = group("conIbFormMore", [steps, expected, actual, extra_row], direction="Vertical",
                    gap=12, visible="varIbMore")

    # Skaermbilleder og filer - kun ved en ny sag; paa en gemt sag ligger
    # de under fanen Attachments.
    files = _field("conIbFormFiles", "Screenshots and files (optional)",
                   _attachments("attIbNewFiles", '"Screenshots and files for the new issue"'),
                   visible=f"!({EDITING})")

    # Admin: livsforloebet, prioriteten, tildelingen og loesningen.
    st = themed_dropdown("drpIbStatus", _table([s for s, _c, _r in cfg.STATUS]),
                         f"{SEL_REF}.Status", label='"Status"')
    pr = themed_dropdown("drpIbPriority", _table([p for p, _r in cfg.PRIORITY]),
                         f'Coalesce({SEL_REF}.Priority, "{cfg.PRIORITY_DEFAULT}")',
                         label='"Priority"')
    asg_items = ('Ungroup(Table({ x: Table({ Email: "", Name: "Not assigned" }) }, '
                 '{ x: SortByColumns(colIbAdmins, "Name", SortOrder.Ascending) }), x)')
    asg = themed_dropdown("drpIbAssignee", asg_items,
                          f'If(IsBlank({SEL_REF}.AssignedEmail), "Not assigned", '
                          f'Coalesce(LookUp(colIbAdmins, Email = {SEL_REF}.AssignedEmail).Name, '
                          f'{SEL_REF}.Assigned, "Not assigned"))',
                          value_col="Name", label='"Assigned to"')
    res = text_input("inpIbResolution", f"{SEL_REF}.Resolution",
                     placeholder='"What was done - shown to the reporter and on the shared board"',
                     max_length=4000, height=72, ttype="Multiline", label='"Resolution"')
    manage_head = text_ctrl("txtIbManageHead", '"Administration"', size=lay.SIZE_BODY,
                            weight="Semibold", height=20)
    manage_hint = text_ctrl("txtIbManageHint",
                            f'"The reporter gets an email when the status changes to {cfg.STATUS_RETEST} '
                            f'or {cfg.STATUS_CLOSED}."',
                            size=lay.SIZE_SMALL, color=C_MUTED, height=34, wrap="true")
    manage = group("conIbManage", [
        manage_head,
        _pair("conIbManage1", _field("conIbFormStatus", "Status", st),
              _field("conIbFormPriority", "Priority", pr), inner=f"({FORM_IN} - 24)"),
        _field("conIbFormAssignee", "Assigned to", asg),
        _field("conIbFormResolution", "Resolution", res),
        manage_hint,
    ], direction="Vertical", gap=12, fill=C_MUTED_BG, radius=10, pad=(12, 12, 12, 12),
        visible=f"{EDITING} && {IS_ADMIN}")

    context = text_ctrl("txtIbFormContext",
                        f'"Also recorded with the issue: opened from " & {PAGE_FX} & ", " & '
                        'LayoutContext & " layout, " & Host.OSType & ", and the date and time."',
                        size=lay.SIZE_SMALL, color=C_MUTED, height=34, wrap="true",
                        visible=f"!({EDITING})")
    missing = text_ctrl("txtIbFormMissing",
                        '"To submit, pick an application and a section, and fill in the title '
                        '(at least 4 characters) and what happened."',
                        size=lay.SIZE_SMALL, color=C_MUTED, height=34, wrap="true",
                        visible=f"!({VALID})")
    # Submit er footerens eneste handling (issue #135). OnSelect tjekker
    # selv, at intet kald koerer, og at felterne er gyldige - et hurtigt
    # dobbeltklik naar ikke at sende sagen to gange.
    submit = button("btnIbFormSubmit", f'If({EDITING}, "Save changes", "Submit issue")',
                    f"If(\n    !varIbBusy && ({VALID}),\n    If(\n        {EDITING},\n        "
                    + SAVE_EDIT.replace("\n", "\n        ") + ",\n        "
                    + SUBMIT.replace("\n", "\n        ") + "\n    )\n)", primary=True,
                    width=fit_button_width('"Save changes"') + ICON_W, height=36,
                    icon=f'If({EDITING}, "Save", "Send")',
                    display_mode=f"If(({VALID}) && !varIbBusy, DisplayMode.Edit, DisplayMode.Disabled)")
    footer = group("conIbFormFooter", [submit], direction="Horizontal", gap=8,
                   height=36, justify="End", align_items="Center")
    kids = [head, intro, where, sec_hint, other_f, title_f, similar, desc_f, more, details,
            files, manage, context, missing, footer]
    return [_popup("IbForm", kids, FORM_ON, width=FORM_W), *build_discard()]


# ---------------------------------------------------------------------------
# En sag i View mode
# ---------------------------------------------------------------------------
DETAIL_ON = "IfError(varIbDetailOn, false)"
SEL = "varIbSel"
MINE = "!varIbSelShared"
DET_IN = POP_IN
ACT_ROW_PAD = 12
ACT_W = f"({DET_IN} - {lay.SCROLLBAR_W} - {lay.GALLERY_RESERVE})"
ACT_BODY_W = f"({ACT_W} - {2 * ACT_ROW_PAD})"
ACT_MAX_H = 420

# Efter enhver aendring gennem flowet: sagen og dens Activity igen, og den
# delte liste hentes forfra naeste gang, den vises.
AFTER_CHANGE = (RELOAD_SEL + ";\n" + LOAD_ACTIVITY + ";\nSet(varIbSharedLoaded, false)")


def _run(action, payload, ok_fx, fail_text, busy="varIbBusy"):
    """Et kald til flowet med ventespinner og svar. ok_fx koeres kun, naar
    flowet svarer ok - ellers staar flowets egen grund i beskeden."""
    return (
        f"Set({busy}, true);\n"
        f"Set(varIbRes, IfError({cfg.FLOW}.Run(\n"
        f'    "{action}",\n'
        f"    JSON({payload})\n"
        f"), {FALLBACK}));\n"
        "If(\n"
        '    varIbRes.ok = "yes",\n'
        "    " + ok_fx.replace("\n", "\n    ") + ",\n"
        f'    Notify("{fail_text} " & varIbRes.message, NotificationType.Error)\n'
        ");\n"
        f"Set({busy}, false)"
    )


POST = _run(
    cfg.ACT_COMMENT,
    f"{{ ticketId: varIbSelId, content: Trim(inpIbComment.Text), internal: varIbInternal && {IS_ADMIN} }}",
    "Reset(inpIbComment);\n"
    + LOAD_ACTIVITY + ";\n"
    "UpdateIf(colIbMine, Id = varIbSelId, { UpdatedOn: Now() });\n"
    "UpdateIf(colIbAll, Id = varIbSelId, { UpdatedOn: Now() });\n"
    'Notify(If(varIbInternal, "Internal note added.", "Comment posted."), NotificationType.Success);\n'
    "Set(varIbInternal, false);\n"
    "Reset(chkIbInternal)",
    "The comment could not be posted.", busy="varIbPosting")

REOPEN = _run(
    cfg.ACT_REOPEN, '{ ticketId: varIbSelId, reason: "" }',
    AFTER_CHANGE + ";\n"
    'Set(varIbState, "open");\n'
    'Notify("The issue has been reopened. An administrator will look at it again.", '
    "NotificationType.Success)",
    "The issue could not be reopened.")

ARCHIVE = _run(
    cfg.ACT_ARCHIVE, f"{{ ticketId: varIbSelId, archived: !{SEL}.Archived }}",
    AFTER_CHANGE + ";\n"
    f'Notify(If({SEL}.Archived, "The issue has been archived. It is kept under Archived.", '
    '"The issue has been restored."), NotificationType.Success)',
    "The issue could not be changed.")

# Permanent sletning: kun fra sin egen bekraeftelse, kun naar nummeret er
# skrevet, og varIbBusy saettes, foer kaldet gaar - et dobbeltklik rammer
# en laast knap. Flowet tjekker nummeret igen.
DELETE = _run(
    cfg.ACT_DELETE, "{ ticketId: varIbSelId, confirm: Trim(inpIbDelConfirm.Text) }",
    "RemoveIf(colIbMine, Id = varIbSelId);\n"
    "RemoveIf(colIbAll, Id = varIbSelId);\n"
    "Set(varIbSharedLoaded, false);\n"
    "Set(varIbDelOn, false);\n"
    "Set(varIbDiscardOn, false);\n"
    "Set(varIbDetailOn, false);\n"
    f'Notify({SEL}.TicketNo & " has been deleted permanently.", NotificationType.Success)',
    "The issue could not be deleted.")

UPLOAD_FILES = (
    "If(\n"
    "    CountRows(attIbFiles.Attachments) = 0,\n"
    '    Notify("Choose one or more files first.", NotificationType.Warning),\n'
    "    Set(varIbUploading, true);\n"
    "    " + _upload("attIbFiles", "varIbSelId", "false",
                     dup_check="F.Name in ShowColumns(varIbFiles, DisplayName)").replace("\n", "\n    ")
    + ";\n"
    "    Reset(attIbFiles);\n"
    "    " + AFTER_CHANGE.replace("\n", "\n    ") + ";\n"
    "    Set(varIbUploading, false);\n"
    "    If(\n"
    f"        CountRows({UP_FAILED}) > 0,\n"
    f'        Notify("Not attached: " & {UP_FAILED_TEXT}, NotificationType.Error),\n'
    '        Notify("The file(s) have been attached.", NotificationType.Success)\n'
    "    )\n"
    ")"
)


def _text_block(name, label, expr, visible=None):
    """En overskrift og en tekst, der ombrydes - laest, ikke redigeret."""
    lab = text_ctrl(f"txt{name}Label", f'"{label}"', size=lay.SIZE_SMALL, weight="Semibold",
                    color=C_MUTED, height=18)
    h = _lines_h(expr, DET_IN)
    body = text_ctrl(f"txt{name}", expr, size=lay.SIZE_BODY, height=h, wrap="true")
    return group(f"con{name}", [lab, body], direction="Vertical", gap=4, visible=visible)


TAB_W = 132


def _tab(name, label_fx, key, accessible, onselect=None):
    b = button(name, label_fx, onselect or f'Set(varIbTab, "{key}")', width=TAB_W, height=32,
               accessible=accessible)
    sel = f'varIbTab = "{key}"'
    b.props["Appearance"] = "ButtonAppearance.Outline"
    b.props["BorderColor"] = f"If({sel}, {C_PRIMARY}, {C_CARD_BORDER})"
    b.props["BorderThickness"] = f"If({sel}, 2, 1)"
    b.props["Color"] = f"If({sel}, {C_PRIMARY}, {C_TITLE})"
    b.props["Size"] = str(lay.SIZE_SMALL)
    b.props["LayoutMinWidth"] = "0"
    return b


def _actions():
    """Handlingerne paa den aabne sag - hver kun, naar brugeren maa (de
    navngivne formler IbCan*). Edit og Delete er kun ikoner paa en telefon."""
    edit = icon_on_mobile(button("btnIbEdit", '"Edit"', OPEN_EDIT,
                                 width=fit_button_width('"Edit"') + ICON_W, height=34, icon="Edit",
                                 visible="IbCanEdit", accessible='"Edit this issue"'))
    reopen = button("btnIbReopen", '"Reopen"', REOPEN, width=fit_button_width('"Reopen"'),
                    height=34, visible="IbCanReopen",
                    accessible='"Reopen this issue - the problem is still there"',
                    display_mode="If(varIbBusy, DisplayMode.Disabled, DisplayMode.Edit)")
    archive = button("btnIbArchive", f'If({SEL}.Archived, "Restore", "Archive")', ARCHIVE,
                     width=fit_button_width('"Restore"'), height=34, visible="IbCanManage",
                     accessible=f'If({SEL}.Archived, "Restore this issue from the archive", '
                                '"Archive this issue - it is kept, but leaves the active lists")',
                     display_mode="If(varIbBusy, DisplayMode.Disabled, DisplayMode.Edit)")
    delete = icon_on_mobile(button("btnIbDelete", '"Delete"',
                                   "Reset(inpIbDelConfirm);\nSet(varIbDelOn, true)",
                                   width=fit_button_width('"Delete"') + ICON_W, height=34,
                                   icon="Delete", danger=True, visible="IbCanManage",
                                   accessible='"Delete this issue permanently"'))
    for b in (edit, reopen, archive, delete):
        b.props["LayoutMinWidth"] = b.props["Width"]
    return group("conIbDetActions", [edit, reopen, archive, delete], direction="Horizontal", gap=8,
                 height=34, align_items="Center",
                 visible="IbCanEdit || IbCanReopen || IbCanManage")


def _files_panel():
    """Fanen Attachments: filerne paa sagens raekke, et lille billede af
    billedfiler, Open, og - mens sagen ikke er arkiveret - Upload."""
    tw = "Parent.TemplateWidth"
    row_h = 60
    ext = 'Lower(Last(Split(ThisItem.DisplayName, ".")).Value)'
    is_img = f"{ext} in {_table(cfg.IMAGE_EXT)}"
    thumb = Ctrl("imgIbFileThumb", "Image", props={
        "AccessibleLabel": '"Preview of " & ThisItem.DisplayName',
        "BorderColor": C_CARD_BORDER, "BorderStyle": "BorderStyle.Solid", "BorderThickness": "1",
        "Height": "44", "Image": "ThisItem.Value", "ImagePosition": "ImagePosition.Fill",
        "OnSelect": "false", "TabIndex": "-1", **lay.radius(6),
        "Visible": is_img, "Width": "44", "X": "0", "Y": "8",
    }, h=44, vis=is_img)
    kind = text_ctrl("txtIbFileKind", f"Upper(Left({ext}, 4))", size=lay.SIZE_MICRO,
                     weight="Semibold", color=C_MUTED, height=44, width=44, align="Center",
                     visible=f"!({is_img})",
                     extra={"X": "0", "Y": "8", "VerticalAlign": "VerticalAlign.Middle",
                            "Fill": C_MUTED_BG, **lay.radius(6)})
    open_w = fit_button_width('"Open"')
    name = text_ctrl("txtIbFileName", "ThisItem.DisplayName", size=lay.SIZE_BODY, weight="Semibold",
                     height=20, width=f"{tw} - 56 - {open_w} - 12",
                     extra={"X": "56", "Y": "9"})
    meta = text_ctrl(
        "txtIbFileMeta",
        'With({ e: LookUp(colIbActivity, Kind = "Attachment" && File = ThisItem.DisplayName) }, '
        f'Upper({ext}) & If(IsBlank(e), "", "  ·  " & e.SizeKb & " KB  ·  " & e.Actor & "  ·  " & '
        'Text(e.At, "dd mmm yyyy hh:mm") & If(e.Initial, "  ·  with the report", "  ·  added later")))',
        size=lay.SIZE_SMALL, color=C_MUTED, height=18, width=f"{tw} - 56 - {open_w} - 12",
        extra={"X": "56", "Y": "31"})
    # NY fane: en fil er ikke en app, og Replace ville smide appen vaek.
    opn = button("btnIbFileOpen", '"Open"', "Launch(ThisItem.AbsoluteUri, { }, LaunchTarget.New)",
                 width=open_w, height=32, accessible='"Open or download " & ThisItem.DisplayName')
    opn.props["X"] = f"{tw} - {open_w}"
    opn.props["Y"] = "14"
    files_items = "If(varIbFilesFor = varIbSelId, varIbFiles, FirstN(varIbFiles, 0))"
    gal_h = f"Min(5, galIbFiles.AllItemsCount) * {row_h}"
    gal = Ctrl("galIbFiles", "Gallery", variant="Vertical", props={
        "AccessibleLabel": '"Attachments"',
        "BorderStyle": "BorderStyle.None", "Fill": C_TRANSPARENT, "FillPortions": "0",
        "Height": gal_h, "Items": files_items, "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None", "Selectable": "false",
        "ShowScrollbar": "true", "TabIndex": "0", "TemplatePadding": "0",
        "TemplateSize": str(row_h), "Width": "Parent.Width", "WrapCount": "1",
    }, children=[thumb, kind, name, meta, opn], h=gal_h,
        vis="galIbFiles.AllItemsCount > 0")
    state = text_ctrl(
        "txtIbFilesState",
        'If(varIbFilesBusy, "Loading attachments...", IfError(varIbFilesFailed, false), '
        '"The attachments could not be loaded. Select the tab again to retry.", '
        '"No files yet. Screenshots help a lot.")',
        size=lay.SIZE_BODY, color=f"If(IfError(varIbFilesFailed, false), {C_INVALID_FG}, {C_MUTED})",
        height=20, wrap="true", visible="galIbFiles.AllItemsCount = 0")
    picker = _attachments("attIbFiles", '"Choose files to attach"')
    up = button("btnIbUpload", '"Upload"', UPLOAD_FILES, primary=True,
                width=fit_button_width('"Upload"') + ICON_W, height=36, icon="ArrowUpload",
                accessible='"Upload the chosen files to this issue"',
                display_mode=("If(CountRows(attIbFiles.Attachments) = 0 || "
                              "varIbUploading, DisplayMode.Disabled, DisplayMode.Edit)"))
    up.props["AlignInContainer"] = "AlignInContainer.End"
    hint = text_ctrl("txtIbFilesHint",
                     f'"Up to {cfg.MAX_FILES} files at a time, {cfg.MAX_FILE_MB} MB each. Files are '
                     'only visible to you and the administrators - never on the shared board."',
                     size=lay.SIZE_SMALL, color=C_MUTED, height=34, wrap="true")
    adder = group("conIbFileAdd", [picker, hint, up], direction="Vertical", gap=8,
                  visible=f"!{SEL}.Archived")
    return group("conIbDetFiles", [state, gal, adder], direction="Vertical", gap=12,
                 visible=f'{MINE} && varIbTab = "files"')


def build_detail():
    no = text_ctrl("txtIbDetNo", f"{SEL}.TicketNo", size=lay.SIZE_BODY, weight="Semibold",
                   color=C_PRIMARY, height=20, width=NO_W)
    no.props["LayoutMinWidth"] = str(NO_W)
    head = _head("IbDet", f"{SEL}.Title", "Set(varIbDetailOn, false)", lead=[no])

    chip = _chip("txtIbDetStatus", f"{SEL}.Status", f"{SEL}.Archived")
    chip.props["LayoutMinWidth"] = str(CHIP_W)
    where = grow(text_ctrl(
        "txtIbDetWhere",
        f'{SEL}.Application & "  ·  " & {SEL}.Section & "  ·  Reported " & '
        f'Text({SEL}.CreatedOn, "dd mmm yyyy") & "  ·  Updated " & Text({SEL}.UpdatedOn, "dd mmm yyyy")',
        size=lay.SIZE_SMALL, color=C_MUTED, height=18))
    meta = group("conIbDetMeta", [chip, where], direction="Horizontal", gap=10, height=24,
                 align_items="Center")
    facts = text_ctrl(
        "txtIbDetFacts",
        f'"Severity: " & Coalesce(If(IsBlank({SEL}.Severity), Blank(), {SEL}.Severity), "-") & '
        f'"  ·  Priority: " & Coalesce(If(IsBlank({SEL}.Priority), Blank(), {SEL}.Priority), "-") & '
        f'If({MINE}, "  ·  Assigned to: " & Coalesce(If(IsBlank({SEL}.Assigned), Blank(), '
        f'{SEL}.Assigned), "not yet assigned"), "") & '
        # Kun en admin ser, hvem der meldte en andens sag.
        f'If({MINE} && {IS_ADMIN} && !IbSelMine, "  ·  Reported by " & {_initials(SEL + ".Reporter")}, "")',
        size=lay.SIZE_SMALL, height=34, wrap="true")

    shared_note = text_ctrl("txtIbDetShared",
                            '"Shared issue. Who reported it, their details, the comments and the '
                            'files are private and not shown here."',
                            size=lay.SIZE_SMALL, color=C_INFO_FG, height=34, wrap="true",
                            visible="varIbSelShared",
                            extra={"Fill": C_INFO_BG, "PaddingLeft": "12", "PaddingRight": "12",
                                   "PaddingTop": "8", **lay.radius(10)})
    retest = text_ctrl("txtIbDetRetest",
                       f'"This issue is ready for retest. Please try it again - if the problem is '
                       'still there, select Reopen."',
                       size=lay.SIZE_SMALL, color=C_WARN_FG, height=34, wrap="true",
                       visible=f'IbSelMine && {SEL}.Status = "{cfg.STATUS_RETEST}" && !{SEL}.Archived',
                       extra={"Fill": C_WARN_BG, "PaddingLeft": "12", "PaddingRight": "12",
                              "PaddingTop": "8", **lay.radius(10)})

    n_act = "CountRows(colIbActivity)"
    tabs = group("conIbDetTabs", [
        _tab("btnIbTabDetails", '"Description"', "details", '"Show the description"'),
        _tab("btnIbTabActivity", f'"Activity (" & {n_act} & ")"', "activity",
             '"Show the activity and comments"'),
        _tab("btnIbTabFiles", '"Attachments (" & IbFileCount & ")"', "files",
             '"Show the attachments"',
             onselect='Set(varIbTab, "files");\nIf(varIbFilesFor <> varIbSelId, ' + LOAD_FILES + ")"),
    ], direction="Horizontal", gap=8, height=32, align_items="Center", visible=MINE)
    # Tre faner skal kunne staa paa en telefon: de deler bredden.
    for t in tabs.children:
        t.props["Width"] = f"Min({TAB_W}, ({DET_IN} - 16) / 3)"

    show_details = f'varIbSelShared || varIbTab = "details"'
    blocks = [
        _text_block("IbDetDesc", "Description", f"{SEL}.Description"),
        _text_block("IbDetSteps", "Steps to reproduce", f"{SEL}.Steps",
                    visible=f"!IsBlank({SEL}.Steps)"),
        _text_block("IbDetExpected", "Expected result", f"{SEL}.Expected",
                    visible=f"!IsBlank({SEL}.Expected)"),
        _text_block("IbDetActual", "Actual result", f"{SEL}.Actual",
                    visible=f"!IsBlank({SEL}.Actual)"),
        _text_block("IbDetOther", "Where it happened", f"{SEL}.Other",
                    visible=f"!IsBlank({SEL}.Other)"),
        _text_block("IbDetRelated", "Related request", f"{SEL}.RelatedNo",
                    visible=f"!IsBlank({SEL}.RelatedNo)"),
        _text_block("IbDetResolution", "Resolution", f"{SEL}.Resolution",
                    visible=f"!IsBlank({SEL}.Resolution)"),
    ]
    details = group("conIbDetDetails", blocks, direction="Vertical", gap=12, visible=show_details)

    # Activity: kommentarer som flader, haendelser med stiplet kant, interne
    # noter i advarselsfarven - og med teksten "internal note", ikke kun farve.
    tw = "Parent.TemplateWidth"
    body_h = _lines_h("ThisItem.Body", ACT_BODY_W)
    row_h = f"(30 + {body_h} + 10)"
    bg = text_ctrl("txtIbActBg", '""', size=lay.SIZE_MICRO, height=f"{row_h} - 4", width=tw,
                   accessible='""',
                   fill=(f"If(ThisItem.Internal, {C_WARN_BG}, ThisItem.IsSystem, {C_TRANSPARENT}, "
                         f"{C_MUTED_BG})"),
                   extra={"X": "0", "Y": "2", **lay.radius(8),
                          "BorderColor": f"If(ThisItem.IsSystem, {C_CARD_BORDER}, {C_TRANSPARENT})",
                          "BorderStyle": "BorderStyle.Dashed",
                          "BorderThickness": "If(ThisItem.IsSystem, 1, 0)"})
    actor = text_ctrl("txtIbActActor",
                      'ThisItem.Actor & If(ThisItem.Internal, "  ·  internal note, admins only", "")',
                      size=lay.SIZE_BODY, weight="Semibold",
                      color=(f"If(ThisItem.Internal, {C_WARN_FG}, ThisItem.IsSystem, {C_MUTED}, "
                             f"{C_TITLE})"), height=20,
                      width=f"{tw} - {2 * ACT_ROW_PAD} - 150",
                      extra={"X": str(ACT_ROW_PAD), "Y": "8"})
    when = text_ctrl("txtIbActWhen", 'Text(ThisItem.At, "dd mmm yyyy hh:mm")',
                     size=lay.SIZE_SMALL, color=C_MUTED, height=18, align="Right", width=150,
                     extra={"X": f"{tw} - {ACT_ROW_PAD} - 150", "Y": "9"})
    body = text_ctrl("txtIbActBody", "ThisItem.Body", size=lay.SIZE_BODY, wrap="true",
                     height=body_h, width=f"{tw} - {2 * ACT_ROW_PAD}",
                     extra={"X": str(ACT_ROW_PAD), "Y": "30"})
    act_sum = f"Sum(colIbActivity, {_lines_h('Body', ACT_BODY_W)} + 40)"
    gal_h = f"Min({ACT_MAX_H}, Max(40, {act_sum}))"
    gal = Ctrl("galIbActivity", "Gallery", variant="VariableHeight", props={
        "AccessibleLabel": '"Activity, oldest first"',
        "BorderStyle": "BorderStyle.None", "Fill": C_TRANSPARENT, "FillPortions": "0",
        "Height": gal_h, "Items": "colIbActivity", "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None", "Selectable": "false",
        "ShowScrollbar": "true", "TabIndex": "0", "TemplatePadding": "0",
        "TemplateSize": "60", "Width": "Parent.Width",
    }, children=[bg, actor, when, body], h=gal_h, vis="!varIbActBusy")
    act_state = text_ctrl("txtIbActState",
                          'If(varIbActBusy, "Loading activity...", '
                          '"The activity could not be loaded. Close the issue and open it again.")',
                          size=lay.SIZE_BODY, color=f"If(varIbActBusy, {C_MUTED}, {C_INVALID_FG})",
                          height=20, wrap="true",
                          visible="varIbActBusy || IfError(varIbActFailed, false)")

    comment = text_input("inpIbComment", '""',
                         placeholder=(f'If(varIbInternal, "Write an internal note for the administrators", '
                                      f'{IS_ADMIN} && !IbSelMine, "Write a reply to the reporter", '
                                      '"Write a comment for the administrators")'),
                         max_length=2000, height=72, ttype="Multiline", label='"Comment"')
    internal = Ctrl("chkIbInternal", "ModernCheckbox", props=checkbox_theme({
        "AccessibleLabel": '"Internal note - only administrators can see it"',
        "Default": "varIbInternal",
        "Height": "24",
        "Label": '"Internal note - only administrators can see it"',
        "OnCheck": "Set(varIbInternal, true)",
        "OnUncheck": "Set(varIbInternal, false)",
        "Visible": IS_ADMIN,
        "Width": "Parent.Width",
    }), h=24, vis=IS_ADMIN)
    closed_hint = text_ctrl(
        "txtIbCommentHint",
        f'If(varIbInternal, "Internal notes are never shown to the reporter.", '
        f'{SEL}.Status = "{cfg.STATUS_CLOSED}", '
        '"This issue is closed. If the problem is back, select Reopen - or add a comment.", '
        '"Comments are visible to the reporter and the administrators only.")',
        size=lay.SIZE_SMALL, color=C_MUTED, height=34, wrap="true")
    post = button("btnIbPost", 'If(varIbInternal, "Add internal note", "Post comment")', POST,
                  primary=True, width=fit_button_width('"Add internal note"') + ICON_W, height=36,
                  icon="Send",
                  display_mode=("If(IsBlank(Trim(inpIbComment.Text)) || varIbPosting, "
                                "DisplayMode.Disabled, DisplayMode.Edit)"))
    post.props["AlignInContainer"] = "AlignInContainer.End"
    composer = group("conIbComposer", [comment, internal, closed_hint, post], direction="Vertical",
                     gap=8, visible="IbCanComment")
    activity = group("conIbDetActivity", [act_state, gal, composer], direction="Vertical", gap=12,
                     visible=f'{MINE} && varIbTab = "activity"')

    rule = group("conIbDetRule", [], direction="Horizontal", height=1, fill=C_DIVIDER)
    kids = [head, meta, facts, _actions(), shared_note, retest, tabs, rule, details, activity,
            _files_panel()]
    return [_popup("IbDet", kids, DETAIL_ON)]


def build_delete():
    """Permanent sletning - sin egen popup oven paa sagen. Nummeret skal
    skrives, teksten siger, at det ikke kan fortrydes, og knappen er laast,
    til nummeret passer, og mens kaldet koerer."""
    del_on = "IfError(varIbDelOn, false)"
    head = _head("IbDel", f'"Delete " & {SEL}.TicketNo & " permanently?"', "Set(varIbDelOn, false)")
    warn = text_ctrl(
        "txtIbDelWarn",
        '"This cannot be undone. The issue, all its comments and activity, and its attachments '
        'are deleted for everyone, and it disappears from the shared board. '
        'To keep the history, archive the issue instead."',
        size=lay.SIZE_BODY, color=C_INVALID_FG, height=58, wrap="true")
    match = f"Upper(Trim(inpIbDelConfirm.Text)) = Upper({SEL}.TicketNo)"
    confirm = text_input("inpIbDelConfirm", '""', placeholder=f'{SEL}.TicketNo', max_length=20,
                         label=f'"Type " & {SEL}.TicketNo & " to confirm"')
    confirm_f = group("conIbDelConfirmF", [
        text_ctrl("txtIbDelConfirmLabel", f'"Type " & {SEL}.TicketNo & " to confirm"',
                  size=lay.SIZE_BODY, weight="Semibold", height=20),
        confirm], direction="Vertical", gap=6)
    cancel = button("btnIbDelCancel", '"Cancel"', "Set(varIbDelOn, false)",
                    width=fit_button_width('"Cancel"'), height=36)
    ok = button("btnIbDelConfirm", '"Delete permanently"', DELETE, danger=True,
                width=fit_button_width('"Delete permanently"') + ICON_W, height=36, icon="Delete",
                accessible=f'"Delete " & {SEL}.TicketNo & " permanently"',
                display_mode=f"If({match} && !varIbBusy, DisplayMode.Edit, DisplayMode.Disabled)")
    footer = group("conIbDelFooter", [cancel, ok], direction="Horizontal", gap=8, height=36,
                   justify="End", align_items="Center")
    return [_popup("IbDel", [head, warn, confirm_f, footer], del_on, width="Min(480, App.Width - 24)")]


def build_loading():
    return [loading_overlay("imgIbLoading", "varIbLoading", "Loading issues, please wait"),
            loading_overlay("imgIbBusy", "(varIbBusy || varIbPosting) && !varIbUploading",
                            "Sending, please wait"),
            loading_overlay("imgIbUploading", "varIbUploading", "Uploading files, please wait",
                            caption="Uploading files...")]
