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
from gen_screen import (Ctrl, stack_height, C_APP_BG, C_CARD_BG, C_CARD_BORDER, C_DIVIDER, C_INFO_BG,
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
    "    !IfError(varIbInit, false),\n"
    "    Set(varIbInit, true);\n"
    # Scopet saettes foerst efter hentningen (LOAD): IsAdmin er et opslag,
    # og det skal ikke staa i koe foran de to forespoergsler (issue #177).
    '    Set(varIbScope, "");\n'
    '    Set(varIbState, "open");\n'
    '    Set(varIbApp, "");\n'
    '    Set(varIbSection, "");\n'
    '    Set(varIbStatusF, "");\n'
    '    Set(varIbPriF, "");\n'
    '    Set(varIbSort, "Last updated");\n'
    "    Set(varIbMe, Lower(User().Email));\n"
    '    Set(varIbTab, "details");\n'
    '    Set(varIbFormMode, "new");\n'
    "    Set(varIbFormOn, false);\n"
    "    Set(varIbDetailOn, false);\n"
    "    Set(varIbDelOn, false);\n"
    "    Set(varIbMore, false);\n"
    "    Set(varIbActsOn, false);\n"
    "    Set(varIbInternal, false);\n"
    "    Set(varIbFilesFor, -1);\n"
    "    Set(varIbSelFullFor, -1);\n"
    "    Set(varIbTried, false);\n"
    "    Set(varIbBusy, false);\n"
    "    Set(varIbSharedBusy, false);\n"
    "    Set(varIbUploading, false);\n"
    "    Set(varIbPosting, false)\n"
    ")"
)


def _rank(field, pairs, fallback):
    body = ", ".join(f'"{k}", {r}' for k, r in pairs)
    return f"Switch({field}, {body}, {fallback})"


STATUS_RANK = [(s, r) for s, _c, r in cfg.STATUS]

# Felterne, der kun bruges i popuppen. Oversigten henter dem ikke (de er
# lange tekster); de kommer med sagens eget opslag, naar den aabnes.
DETAIL_ONLY = ("Steps", "Expected", "Actual", "Other", "RelatedNo", "Resolution")


def _row(r, *, shared, full=True):
    """Een raekke i colIbMine/colIbAll/colIbShared. De tre har SAMME skema,
    saa listen kan vaelge mellem dem med et Switch. Den anonyme kopi har
    ingen rapportoer og ingen tildeling - felterne er tomme. full=False:
    oversigtens raekke - popup-felterne er tomme, til sagen aabnes."""
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
        if not full:
            for k in DETAIL_ONLY:
                f[k] = '""'
        pri, st = f"{r}.Priority.Value", f"{r}.Status.Value"
    f["PriRank"] = _rank(pri, cfg.PRIORITY, 5)
    f["StatusRank"] = _rank(st, STATUS_RANK, 9)
    return "{ " + ", ".join(f"{k}: {v}" for k, v in f.items()) + " }"


# Oversigtens kolonner i IB_Tickets - ShowColumns giver SharePoint et
# $select, saa de lange tekster (trin, forventet/faktisk resultat,
# loesning) ikke hentes for hver sag (issue #177).
OVERVIEW_COLS = ["ID", "Title", "TicketNo", "Description", "Application", "Section", "Severity",
                 "Priority", "Status", "AssignedToName", "ReporterEmail", "AssignedToEmail",
                 "Created", "LastActivityOn", "IsArchived"]
_SHOW = ", ".join(OVERVIEW_COLS)

# Hentningerne. Hver sammenligner med en global variabel eller en konstant,
# saa SharePoint udfoerer filteret og sorteringen (check_layout regel 30).
FETCH_SECTIONS = (f"ForAll(Filter({cfg.L_SECTIONS}, IsActive = true) As r, "
                  '{ Application: Coalesce(r.Application, ""), Section: Coalesce(r.Section, ""), '
                  "AppOrder: Coalesce(r.AppOrder, 0), SectionOrder: Coalesce(r.SectionOrder, 0), "
                  'ScreenKey: Coalesce(r.ScreenKey, "") })')
FETCH_MINE = (f"ForAll(ShowColumns(Sort(Filter({cfg.L_TICKETS}, ReporterEmail = varIbMe), LastActivityOn, "
              f"SortOrder.Descending), {_SHOW}) As r, {_row('r', shared=False, full=False)})")
FETCH_SHARED = (f"ForAll(Sort({cfg.L_SHARED}, LastActivityOn, SortOrder.Descending) As r, "
                f"{_row('r', shared=True)})")
# Admin-boardet: alle sager, brugeren har ret til at laese. For en admin er
# det alle (Contribute paa hver raekke). En admins egne sager er en del af
# dem, saa de hentes IKKE en gang til (IbMine filtrerer i hukommelsen).
FETCH_ALL = (f"ForAll(ShowColumns(Sort({cfg.L_TICKETS}, LastActivityOn, SortOrder.Descending), "
             f"{_SHOW}) As r, {_row('r', shared=False, full=False)})")

RELOAD_MINE = f"Set(varIbMineFailed, IfError(ClearCollect(colIbMine, {FETCH_MINE}); false, true))"
RELOAD_ALL = f"Set(varIbAllFailed, IfError(ClearCollect(colIbAll, {FETCH_ALL}); false, true))"
# Den ene liste, brugeren har: en admin alle sager, alle andre deres egne.
RELOAD_MAIN = (f"If({IS_ADMIN}, {RELOAD_ALL}; Set(varIbMineFailed, false), "
               f"{RELOAD_MINE}; Set(varIbAllFailed, false))")

# FLASKEHALSEN (issue #177): foer hentede en admin konfigurationen og sine
# egne sager (Concurrent) og FOERST DEREFTER alle sager - to runder mod
# IB_Tickets efter hinanden, hvor den foerste var en delmaengde af den
# anden - og IsAdmin blev slaaet op foran det hele. Nu er det een runde:
# konfigurationen og den ene liste samtidig.
LOAD = (
    "If(\n"
    "    !varIbLoaded,\n"
    "    Set(varIbLoading, true);\n"
    "    " + concurrent(
        f"Set(varIbCfgFailed, IfError(ClearCollect(colIbSections, {FETCH_SECTIONS}); false, true))",
        RELOAD_MAIN, indent=4) + ";\n"
    "    Set(varIbLoaded, !varIbCfgFailed && !varIbMineFailed && !varIbAllFailed);\n"
    "    Set(varIbLoading, false)\n"
    ")"
)

# Den anonyme liste: kun for "All issues" (almindelig bruger) og forslagene
# i New issue. Den har sin egen ventevariabel, saa den ikke laegger
# ventespinneren hen over formularen.
LOAD_SHARED = (
    "If(\n"
    "    !varIbSharedLoaded,\n"
    "    Set(varIbSharedBusy, true);\n"
    f"    Set(varIbSharedFailed, IfError(ClearCollect(colIbShared, {FETCH_SHARED}); false, true));\n"
    "    Set(varIbSharedLoaded, !varIbSharedFailed);\n"
    "    Set(varIbSharedBusy, false)\n"
    ")"
)

SET_SCOPE = f'If(IsBlank(varIbScope), Set(varIbScope, If({IS_ADMIN}, "all", "mine")))'

RETRY = ("Set(varIbLoaded, false);\nSet(varIbSharedLoaded, false);\n"
         + LOAD + ";\n" + SET_SCOPE + ';\nIf(varIbScope = "shared", ' + LOAD_SHARED + ")")


def on_visible():
    return INIT_STATE + ";\n" + LOAD + ";\n" + SET_SCOPE


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
    f'{_initials("varIbSel.Reporter")}), Role: "User", Body: "Reported the issue.", '
    'At: varIbSel.CreatedOn, Internal: false, IsSystem: true, File: "", SizeKb: 0, Initial: false },\n'
    f"    ForAll(Sort(Filter({cfg.L_COMMENTS}, TicketId = varIbSelId), ID, SortOrder.Ascending) As r,\n"
    '        With({ k: Coalesce(r.EventType.Value, "Comment"), who: Lower(Coalesce(r.AuthorEmail, "")), '
    'role: Coalesce(r.AuthorRole.Value, ""), atSub: Coalesce(r.AtSubmission, false) },\n'
    "            { Kind: k,\n"
    # Rollen staar i sit eget maerke ved siden af (User, Admin, System) -
    # ikke laengere som " (admin)" efter initialerne (issue #177).
    '              Actor: If(role = "System", "Issue Board", who = varIbMe, "You", '
    f'{_initials("who")}),\n'
    '              Role: Switch(role, "Admin", "Admin", "System", "System", "User"),\n'
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
    "        Set(varIbSelFullFor, varIbSelId);\n"
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

# Naar en sag aabnes: sagens egen raekke (de lange tekster, som oversigten
# ikke hentede) og dens Activity SAMTIDIG - to opslag paa ID, ikke to i
# koe. Popuppen staar allerede fremme med det, oversigten havde.
# Vedhaeftningerne hentes foerst, naar fanen vaelges (LOAD_FILES).
LOAD_OPEN = (
    "Set(varIbSelRow, Blank());\n"
    + concurrent(
        f"Set(varIbSelRow, IfError(LookUp({cfg.L_TICKETS}, ID = varIbSelId), Blank()))",
        LOAD_ACTIVITY) + ";\n"
    "If(\n"
    "    !IsBlank(varIbSelRow) && varIbSelRow.ID = varIbSelId,\n"
    f"    Set(varIbSel, {_row('varIbSelRow', shared=False)});\n"
    "    Set(varIbSelFullFor, varIbSelId);\n"
    "    UpdateIf(colIbMine, Id = varIbSelId, varIbSel);\n"
    "    UpdateIf(colIbAll, Id = varIbSelId, varIbSel)\n"
    ")"
)


def open_ticket(rec, shared):
    """Aabn en sag i View mode. rec: raekken; shared: sand for den anonyme
    kopi (ingen Activity, ingen filer, ingen handlinger)."""
    return (
        f"Set(varIbSel, {rec});\n"
        "Set(varIbSelId, varIbSel.Id);\n"
        f"Set(varIbSelShared, {shared});\n"
        'Set(varIbTab, "details");\n'
        "Set(varIbInternal, false);\n"
        "Set(varIbActsOn, false);\n"
        "Set(varIbFilesFor, -1);\n"
        "Reset(inpIbComment);\n"
        "Clear(colIbActivity);\n"
        "Set(varIbDetailOn, true);\n"
        "If(!varIbSelShared, " + LOAD_OPEN + ")"
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
ACT = {"Kind": '""', "Actor": '""', "Role": '""', "Body": '""', "At": "Now()", "Internal": "false",
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
# Fliser og den anonyme kopi: "Updated" kun, naar sagen er aendret mere end
# saa mange minutter efter indmeldingen - flowets egen opsaetning (nummer,
# delt kopi, filerne med indmeldingen) er ikke en aendring.
UPDATED_AFTER_MIN = 5

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
IbFailed = IfError(varIbCfgFailed, false) || IfError(varIbMineFailed, false) || IfError(varIbAllFailed, false) || (varIbScope = "shared" && IfError(varIbSharedFailed, false));
// En admin henter kun colIbAll (alle sager); hans egne er en del af dem og
// hentes ikke en gang til. Alle andre har colIbMine.
IbMine = If({IS_ADMIN}, Filter(colIbAll, Reporter = varIbMe), colIbMine);
// Scopet: All issues (admin: alle sager; ellers den anonyme liste), My
// issues og - for admin - Assigned to me. Filtrene regnes oven paa det.
IbScopeRows = Switch(varIbScope, "shared", colIbShared, "all", colIbAll, "assigned", Filter(colIbAll, AssignedEmail = varIbMe), IbMine);
// Updated vises kun efter en reel aendring: en haendelse efter
// indmeldingen (ikke filerne, der kom med den). Den anonyme kopi har ingen
// Activity - der taeller kun en aendring mere end {UPDATED_AFTER_MIN} minutter efter.
IbSelUpdatedOn = If(varIbSelShared, If(DateDiff(varIbSel.CreatedOn, varIbSel.UpdatedOn, TimeUnit.Minutes) >= {UPDATED_AFTER_MIN}, varIbSel.UpdatedOn, Blank()), Max(Filter(colIbActivity, Kind <> "Reported" && !Initial), At));
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

# Formularen staar fremme med det samme. Forslagene til lignende sager
# kommer bagefter - for en almindelig bruger fra den anonyme liste, som
# hentes uden ventespinner hen over formularen; en admin har dem allerede
# i colIbAll (issue #177).
OPEN_FORM = (
    'Set(varIbFormMode, "new");\n'
    "Set(varIbFormApp, IbFrom);\n"
    'Set(varIbFormSection, "");\n'
    "Set(varIbMore, false);\n"
    "Set(varIbTried, false);\n"
    + RESET_FORM + ";\n"
    "Set(varIbFormOn, true);\n"
    f"If(!{IS_ADMIN}, " + LOAD_SHARED + ")"
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
SEG_H = 34


def _seg(name, label, selected, onselect, width, accessible):
    """Et segment i en kontakt: valgt = fyldt, ikke valgt = kant."""
    b = button(name, label if label.startswith("If(") else f'"{label}"', onselect, width=width,
               height=SEG_H, accessible=accessible)
    b.props["Appearance"] = f"If({selected}, ButtonAppearance.Primary, ButtonAppearance.Outline)"
    b.props["BasePaletteColor"] = C_PRIMARY
    b.props["BorderColor"] = f"If({selected}, {C_PRIMARY}, {C_CARD_BORDER})"
    b.props["BorderThickness"] = "1"
    b.props["Color"] = f"If({selected}, {_t('text-on-primary')}, {C_TITLE})"
    b.props["Size"] = str(lay.SIZE_SMALL)
    b.props["LayoutMinWidth"] = b.props["Width"]
    return b


def _filter_dd(name, all_text, values, var, label, display_mode=None):
    """En filterliste: "All ..." foerst og derefter vaerdierne."""
    return themed_dropdown(name, _table([all_text] + list(values)),
                           f'If(IsBlank({var}), "{all_text}", {var})', label=label,
                           display_mode=display_mode,
                           onchange=f'Set({var}, If(Self.Selected.Value = "{all_text}", "", '
                                    "Self.Selected.Value))")


# Scopet "All issues": for en admin alle sager (colIbAll), for alle andre
# den anonyme liste (colIbShared) - saa kan alle finde ogsaa de arkiverede
# sager, uden at se hvem der meldte dem (issue #177).
SCOPE_ALL = 'varIbScope in ["all", "shared"]'
ADMIN_BOARD = f'{IS_ADMIN} && varIbScope in ["all", "assigned"]'
FILTERED = ("!IsBlank(varIbApp) || !IsBlank(varIbSection) || !IsBlank(varIbStatusF) || "
            "!IsBlank(varIbPriF) || !IsBlank(Trim(inpIbSearch.Text))")
CLEAR_FILTERS = ('Set(varIbApp, "");\nSet(varIbSection, "");\nSet(varIbStatusF, "");\n'
                 'Set(varIbPriF, "");\nReset(inpIbSearch);\nReset(drpIbFltApp);\n'
                 "Reset(drpIbFltSection);\nReset(drpIbFltStatus);\nReset(drpIbFltPriority)")

# Kontakternes bredder paa en bred skaerm. Paa en smal deler segmenterne
# kortets bredde.
SCOPE_W = {"btnIbScopeAll": 96, "btnIbScopeMine": 100, "btnIbScopeAssigned": 128}
STATE_W = {"btnIbStateOpen": 76, "btnIbStateClosed": 84, "btnIbStateArchived": 92}
SCOPE_ADMIN_W = sum(SCOPE_W.values()) + 2 * 4
SCOPE_USER_W = SCOPE_W["btnIbScopeAll"] + SCOPE_W["btnIbScopeMine"] + 4
STATE_ALL_W = sum(STATE_W.values()) + 2 * 4
TOP_OK = f"({CARD_W}) >= {SCOPE_ADMIN_W + 16 + STATE_ALL_W}"


def build_filters():
    n_scope = f"If({IS_ADMIN}, 3, 2)"
    narrow_scope = f"(({CARD_W}) - 4 * ({n_scope} - 1)) / {n_scope}"
    all_seg = _seg("btnIbScopeAll", "All issues", SCOPE_ALL,
                   f'If({IS_ADMIN}, Set(varIbScope, "all"), Set(varIbScope, "shared");\n'
                   + LOAD_SHARED + ")",
                   SCOPE_W["btnIbScopeAll"],
                   f'If({IS_ADMIN}, "Show all issues", '
                   '"Show all issues from all testers, without names")')
    mine_seg = _seg("btnIbScopeMine", "My issues", 'varIbScope = "mine"',
                    'Set(varIbScope, "mine")', SCOPE_W["btnIbScopeMine"],
                    '"Show the issues you reported"')
    asg_seg = _seg("btnIbScopeAssigned", f'If({NARROW}, "Assigned", "Assigned to me")',
                   'varIbScope = "assigned"', 'Set(varIbScope, "assigned")',
                   SCOPE_W["btnIbScopeAssigned"], '"Show the issues assigned to me"')
    asg_seg.props["Visible"] = IS_ADMIN
    asg_seg.vis = IS_ADMIN
    for s in (all_seg, mine_seg, asg_seg):
        s.props["Width"] = f"If({TOP_OK}, {SCOPE_W[s.name]}, {narrow_scope})"
        s.props["LayoutMinWidth"] = s.props["Width"]
    scope = group("conIbScope", [all_seg, mine_seg, asg_seg], direction="Horizontal", gap=4,
                  height=SEG_H, align_items="Center",
                  width=f"If({TOP_OK}, If({IS_ADMIN}, {SCOPE_ADMIN_W}, {SCOPE_USER_W}), {CARD_W})")
    scope.props["LayoutMinWidth"] = scope.props["Width"]

    states = [("btnIbStateOpen", "Open", "open", '"Show open issues"'),
              ("btnIbStateClosed", "Closed", "closed", '"Show closed issues"'),
              ("btnIbStateArchived", "Archived", "archived", '"Show archived issues"')]
    segs = []
    for name, label, key, acc in states:
        s = _seg(name, label, f'varIbState = "{key}"', f'Set(varIbState, "{key}")', STATE_W[name],
                 acc)
        s.props["Width"] = f"If({TOP_OK}, {STATE_W[name]}, (({CARD_W}) - 8) / 3)"
        s.props["LayoutMinWidth"] = s.props["Width"]
        segs.append(s)
    state = group("conIbState", segs, direction="Horizontal", gap=4, height=SEG_H,
                  align_items="Center", width=f"If({TOP_OK}, {STATE_ALL_W}, {CARD_W})")
    state.props["LayoutMinWidth"] = state.props["Width"]
    top = group("conIbSwitches", [scope, state], direction="Horizontal", gap=16,
                height=f"If({TOP_OK}, {SEG_H}, {SEG_H} + 8 + {SEG_H})", align_items="Start")
    top.props["LayoutDirection"] = f"If({TOP_OK}, LayoutDirection.Horizontal, LayoutDirection.Vertical)"
    top.props["LayoutGap"] = f"If({TOP_OK}, 16, 8)"

    # Soegning og sortering paa een linje; under hinanden paa en telefon.
    search = text_input("inpIbSearch", '""', placeholder='"Search number, title or description"',
                        label='"Search issues"')
    # Listen filtreres i hukommelsen - et lille ophold, saa den ikke regnes
    # om for hvert tegn.
    search.props["TriggerOutput"] = "TriggerOutput.Delayed"
    drp_sort = themed_dropdown("drpIbSort", '["Last updated", "Newest", "Oldest", "Priority", "Status"]',
                               "varIbSort", label='"Sort issues"',
                               onchange="Set(varIbSort, Self.Selected.Value)")
    sort_w = 160
    ok1 = f"({CARD_W}) >= {sort_w + 8 + 280}"
    drp_sort.props["Width"] = f"If({ok1}, {sort_w}, {CARD_W})"
    drp_sort.props["LayoutMinWidth"] = f"If({ok1}, {sort_w}, 0)"
    search.props["Width"] = f"If({ok1}, {CARD_W} - {sort_w + 8}, {CARD_W})"
    row = group("conIbFltRow", [search, drp_sort], direction="Horizontal", gap=8,
                height=f"If({ok1}, 36, 2 * 36 + 8)")
    row.props["LayoutDirection"] = f"If({ok1}, LayoutDirection.Horizontal, LayoutDirection.Vertical)"

    # Application og den afhaengige Section, status og prioritet: fire paa
    # een linje, ellers to og to.
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
    # Status: Closed er sin egen kontakt, saa listen er de aabne trin. Under
    # Closed er der kun een status - listen er da laast.
    drp_status = _filter_dd("drpIbFltStatus", "All statuses",
                            [s for s, _c, _r in cfg.STATUS if s != cfg.STATUS_CLOSED],
                            "varIbStatusF", '"Filter by status"',
                            display_mode='If(varIbState = "closed", DisplayMode.Disabled, DisplayMode.Edit)')
    drp_pri = _filter_dd("drpIbFltPriority", "All priorities", [p for p, _r in cfg.PRIORITY],
                         "varIbPriF", '"Filter by priority"')
    ok4 = f"({CARD_W}) >= {4 * 150 + 3 * 8}"
    half = f"(({CARD_W}) - 8) / 2"
    quarter = f"(({CARD_W}) - 24) / 4"
    # To og to paa en smal skaerm: hver liste er halvdelen af kortet.
    for c in (drp_app, drp_sec, drp_status, drp_pri):
        c.props["Width"] = f"If({ok4}, {quarter}, {half})"
        c.props["LayoutMinWidth"] = "0"
    pair_a = group("conIbFltPairA", [drp_app, drp_sec], direction="Horizontal", gap=8,
                   height=36, width=f"If({ok4}, {half}, {CARD_W})")
    pair_b = group("conIbFltPairB", [drp_status, drp_pri], direction="Horizontal", gap=8,
                   height=36, width=f"If({ok4}, {half}, {CARD_W})")
    row2 = group("conIbFltRow2", [pair_a, pair_b], direction="Horizontal", gap=8,
                 height=f"If({ok4}, 36, 2 * 36 + 8)")
    row2.props["LayoutDirection"] = f"If({ok4}, LayoutDirection.Horizontal, LayoutDirection.Vertical)"

    note = text_ctrl("txtIbSharedNote",
                     '"All issues from all testers are anonymous here: you see what was reported '
                     'and its status, never who reported it, the comments or the files."',
                     size=lay.SIZE_SMALL, color=C_INFO_FG, height=50, wrap="true",
                     visible='varIbScope = "shared"',
                     extra={"Fill": C_INFO_BG, "PaddingLeft": "12", "PaddingRight": "12",
                            "PaddingTop": "8", **lay.radius(10)})
    return card("conIbFilterCard", [top, row, row2, note], gap=12)


# ---------------------------------------------------------------------------
# Oversigten: fliser i et gitter (issue #177)
# ---------------------------------------------------------------------------
NO_W = 96
TILE_MIN_W = 240
TILE_H = 196
TILE_M = 6          # luft om hver flise - 12 px mellem to
TILE_PAD = 14       # flisens indre polstring
TILE_CHIP_W = 112
TILE_PRI_W = 80
# Antal kolonner: saa mange fliser paa mindst TILE_MIN_W, der kan staa.
TILE_COLS = f"Max(1, RoundDown(({CARD_W}) / {TILE_MIN_W}, 0))"
# Galleriet er saa hoejt som raekkerne - hoejst det, der er plads til paa
# skaermen (mindst to raekker); resten scroller i galleriet.
TILE_ROWS = f"RoundUp(galIbList.AllItemsCount / {TILE_COLS}, 0)"
TILE_MAX_ROWS = f"Max(2, RoundDown((App.Height - 280) / {TILE_H}, 0))"

# Den rigtige sag, naar man trykker paa en anonym kopi af sin EGEN sag: saa
# faar man den fulde visning med Activity og filer.
OWN_OF_SHARED = 'If(varIbScope = "shared", LookUp(colIbMine, TicketNo = ThisItem.TicketNo))'
OPEN_TILE = ("With(\n    { own: " + OWN_OF_SHARED + " },\n"
             + "".join("    " + l + "\n" for l in open_ticket(
                 "If(IsBlank(own), ThisItem, own)",
                 'varIbScope = "shared" && IsBlank(own)').split("\n"))
             + ")")

LIST_ITEMS = (
    "With(\n"
    "    { q: Trim(inpIbSearch.Text) },\n"
    "    With(\n"
    "        { f: Filter(IbScopeRows,\n"
    f'              Switch(varIbState, "closed", !Archived && Status = "{cfg.STATUS_CLOSED}", '
    f'"archived", Archived, !Archived && Status <> "{cfg.STATUS_CLOSED}"),\n'
    "              IsBlank(varIbApp) || Application = varIbApp,\n"
    "              IsBlank(varIbSection) || Section = varIbSection,\n"
    '              IsBlank(varIbStatusF) || varIbState = "closed" || Status = varIbStatusF,\n'
    "              IsBlank(varIbPriF) || Priority = varIbPriF,\n"
    "              IsBlank(q) || q in TicketNo || q in Title || q in Description) },\n"
    "        Switch(\n"
    "            varIbSort,\n"
    '            "Newest", SortByColumns(f, "CreatedOn", SortOrder.Descending),\n'
    '            "Oldest", SortByColumns(f, "CreatedOn", SortOrder.Ascending),\n'
    '            "Priority", SortByColumns(f, "PriRank", SortOrder.Ascending, "UpdatedOn", SortOrder.Descending),\n'
    '            "Status", SortByColumns(f, "StatusRank", SortOrder.Ascending, "UpdatedOn", SortOrder.Descending),\n'
    '            SortByColumns(f, "UpdatedOn", SortOrder.Descending)\n'
    "        )\n"
    "    )\n"
    ")"
)

DATE_FMT = '"dd mmm yyyy"'
DATETIME_FMT = '"dd mmm yyyy hh:mm"'
TILE_UPDATED = f"DateDiff(ThisItem.CreatedOn, ThisItem.UpdatedOn, TimeUnit.Minutes) >= {UPDATED_AFTER_MIN}"
PRIORITY_TONE = {"Urgent": "error", "High": "warn", "Normal": "neutral", "Low": "neutral"}


def _priority_tokens(expr):
    def sw(part):
        body = ", ".join(f'"{p}", {_t("state-" + PRIORITY_TONE[p] + "-" + part)}'
                         for p, _r in cfg.PRIORITY)
        return f"Switch({expr}, {body}, {_t('state-neutral-' + part)})"
    return sw("fg"), sw("bg")


# Hvem - kun det, brugeren maa se (anonymiteten er uaendret): en admin ser
# rapportoerens initialer paa andres sager og tildelingen; rapportoeren ser
# tildelingen paa sin egen sag; paa den anonyme liste staar der kun
# "Reported by you" paa ens egne sager - aldrig andres initialer.
TILE_PEOPLE = (
    f'If(varIbScope = "shared", If(IsBlank({OWN_OF_SHARED}), "", "Reported by you"), '
    f'If({IS_ADMIN} && ThisItem.Reporter <> varIbMe, {_initials("ThisItem.Reporter")} & "  ·  ", "") & '
    'If(IsBlank(ThisItem.Assigned), "Unassigned", "To " & ThisItem.Assigned))'
)


def build_list():
    tw = "Parent.TemplateWidth"
    th = TILE_H
    inner = f"{tw} - {2 * (TILE_M + TILE_PAD)}"
    x0 = str(TILE_M + TILE_PAD)
    bg = text_ctrl("txtIbTileBg", '""', size=lay.SIZE_MICRO, height=th - 2 * TILE_M,
                   width=f"{tw} - {2 * TILE_M}", accessible='"Issue tile"',
                   fill=f"If(ThisItem.Archived, {C_MUTED_BG}, {C_APP_BG})",
                   extra={"X": str(TILE_M), "Y": str(TILE_M), **lay.radius(lay.RADIUS_CARD),
                          "BorderColor": C_CARD_BORDER, "BorderStyle": "BorderStyle.Solid",
                          "BorderThickness": "1"})
    no = text_ctrl("txtIbTileNo", "ThisItem.TicketNo", size=lay.SIZE_BODY, weight="Semibold",
                   color=C_PRIMARY, height=20, width=f"{inner} - {TILE_CHIP_W} - 8",
                   extra={"X": x0, "Y": str(TILE_M + TILE_PAD + 2)})
    chip = _chip("txtIbTileStatus", "ThisItem.Status", "ThisItem.Archived",
                 x=f"{tw} - {TILE_M + TILE_PAD} - {TILE_CHIP_W}", y=str(TILE_M + TILE_PAD),
                 width=TILE_CHIP_W)
    title = text_ctrl("txtIbTileTitle", "ThisItem.Title", size=lay.SIZE_INPUT, weight="Semibold",
                      height=40, width=inner, wrap="true",
                      extra={"X": x0, "Y": "50", "VerticalAlign": "VerticalAlign.Top"})
    where = text_ctrl("txtIbTileWhere", 'ThisItem.Application & "  ·  " & ThisItem.Section',
                      size=lay.SIZE_SMALL, color=C_MUTED, height=18, width=inner,
                      extra={"X": x0, "Y": "96"})
    dates = text_ctrl("txtIbTileDates",
                      f'"Reported " & Text(ThisItem.CreatedOn, {DATE_FMT}) & '
                      f'If({TILE_UPDATED}, "  ·  Updated " & Text(ThisItem.UpdatedOn, {DATE_FMT}), "")',
                      size=lay.SIZE_SMALL, color=C_MUTED, height=34, width=inner, wrap="true",
                      extra={"X": x0, "Y": "116", "VerticalAlign": "VerticalAlign.Top"})
    bottom_y = th - TILE_M - TILE_PAD - 22
    pfg, pbg = _priority_tokens("ThisItem.Priority")
    pri = text_ctrl("txtIbTilePriority", "ThisItem.Priority", size=lay.SIZE_MICRO,
                    weight="Semibold", height=22, width=TILE_PRI_W, align="Center", color=pfg,
                    fill=pbg, accessible='"Priority: " & Self.Text',
                    visible="!IsBlank(ThisItem.Priority)",
                    extra={"X": x0, "Y": str(bottom_y), "VerticalAlign": "VerticalAlign.Middle",
                           **lay.radius(11)})
    people = text_ctrl("txtIbTilePeople", TILE_PEOPLE, size=lay.SIZE_SMALL, color=C_MUTED,
                       height=18, align="Right", width=f"{inner} - {TILE_PRI_W} - 8",
                       extra={"X": f"{x0} + {TILE_PRI_W} + 8", "Y": str(bottom_y + 2)})
    hit = row_hit("btnIbTileOpen", OPEN_TILE,
                  '"Open " & ThisItem.TicketNo & " - " & ThisItem.Title & ", " & '
                  'If(ThisItem.Archived, "Archived", ThisItem.Status)',
                  f"{tw} - {2 * TILE_M}", th - 2 * TILE_M, radius=lay.RADIUS_CARD,
                  hover_border=True)
    hit.props["X"] = str(TILE_M)
    hit.props["Y"] = str(TILE_M)
    gal_h = f"Max(1, Min({TILE_ROWS}, {TILE_MAX_ROWS})) * {TILE_H}"
    gal = Ctrl("galIbList", "Gallery", variant="Vertical", props={
        "AccessibleLabel": '"Issues"',
        "BorderStyle": "BorderStyle.None", "Fill": C_CARD_BG, "FillPortions": "0",
        "Height": gal_h, "Items": LIST_ITEMS, "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None", "Selectable": "false",
        "ShowScrollbar": "true", "TabIndex": "0", "TemplatePadding": "0",
        "TemplateSize": str(TILE_H), "Width": "Parent.Width", "WrapCount": TILE_COLS,
    }, children=[bg, no, chip, title, where, dates, pri, people, hit], h=gal_h,
        vis="galIbList.AllItemsCount > 0")

    state_word = 'Switch(varIbState, "closed", " closed", "archived", " archived", " open")'
    count = grow(text_ctrl(
        "txtIbCount",
        f'With({{ n: galIbList.AllItemsCount }}, n & {state_word} & If(n = 1, " issue", " issues") & '
        f'If({FILTERED}, If(n = 1, " matches", " match") & " the filters", ""))',
        size=lay.SIZE_BODY, weight="Semibold", color=C_MUTED, height=20))
    clear = button("btnIbClearFlt", '"Clear filters"', CLEAR_FILTERS,
                   width=fit_button_width('"Clear filters"', size=lay.SIZE_SMALL), height=30,
                   visible=FILTERED, accessible='"Clear all filters and the search"')
    clear.props["Size"] = str(lay.SIZE_SMALL)
    clear.props["LayoutMinWidth"] = clear.props["Width"]
    count_row = group("conIbCountRow", [count, clear], direction="Horizontal", gap=8, height=30,
                      align_items="Center")
    # Admin-boardets taellere: det, der venter paa en admin.
    open_all = f'!Archived && Status <> "{cfg.STATUS_CLOSED}"'
    counts = text_ctrl(
        "txtIbAdminCounts",
        f'CountIf(colIbAll, {open_all}) & " open  ·  " & '
        f'CountIf(colIbAll, !Archived && Status = "{cfg.STATUS_NEW}") & " new  ·  " & '
        f'CountIf(colIbAll, {open_all} && IsBlank(AssignedEmail)) & " unassigned  ·  " & '
        f'CountIf(colIbAll, {open_all} && AssignedEmail = varIbMe) & " assigned to you  ·  " & '
        'CountIf(colIbAll, Archived) & " archived"',
        size=lay.SIZE_SMALL, color=C_MUTED, height=34, wrap="true", visible=ADMIN_BOARD)
    loading = 'varIbLoading || (varIbScope = "shared" && varIbSharedBusy)'
    empty_fx = (
        f'If({loading}, "Loading issues...", '
        "IbFailed, \"The issues could not be loaded. Check your connection and try again.\", "
        'varIbScope = "mine" && IsEmpty(IbMine), '
        '"You have not reported any issues yet. Use New issue to report one.", '
        'varIbScope = "all" && IsEmpty(colIbAll), "No issues have been reported yet.", '
        'varIbScope = "assigned" && IsEmpty(Filter(colIbAll, AssignedEmail = varIbMe)), '
        '"No issues are assigned to you.", '
        'varIbScope = "shared" && IsEmpty(colIbShared), "No issues have been reported yet.", '
        f'{FILTERED}, "No issues match the filters. Clear the filters to see more.", '
        'Switch(varIbState, "closed", "There are no closed issues here.", "archived", '
        '"There are no archived issues here.", "There are no open issues here."))')
    empty = text_ctrl("txtIbEmpty", empty_fx, size=lay.SIZE_BODY, height=40, wrap="true",
                      color=f"If(IbFailed, {C_INVALID_FG}, {C_MUTED})",
                      visible="galIbList.AllItemsCount = 0")
    retry = button("btnIbRetry", '"Retry"', RETRY, width=fit_button_width('"Retry"'), height=36,
                   visible="IbFailed && !varIbLoading", accessible='"Load the issues again"')
    retry.props["AlignInContainer"] = "AlignInContainer.Start"
    return card("conIbListCard", [count_row, counts, gal, empty, retry], gap=8)


# ---------------------------------------------------------------------------
# Popupperne - faelles maal
# ---------------------------------------------------------------------------
POP_PAD = 18
POP_W = "Min(760, App.Width - 24)"
POP_IN = f"({POP_W} - {2 * POP_PAD})"
LINE_H = 19


def _lines_h(text, width, px=7.2, line_h=LINE_H):
    """Hoejden af en ombrudt tekst: antal linjer regnet af laengden og
    linjeskiftene. Hellere en linje luft end en klippet linje."""
    cpl = f"Max(12, RoundDown(({width}) / {px}, 0))"
    return (f"With({{ t: {text} }}, (RoundUp(Len(t) / {cpl}, 0) + "
            f"CountRows(Split(t, Char(10))) - 1) * {line_h} + 2)")


POP_GAP = 12
POP_MARGIN = 16


def _popup(prefix, kids, vis, width=POP_W, foot=None):
    """Popuppen holder sig inden for skaermen (issue #177): hovedet (titel
    og Close) og en eventuel fod staar fast; kun indholdet imellem scroller,
    og kun naar det ikke kan staa. Close kan altid naas.

    kids[0] er hovedet; resten er indholdet."""
    head, rest = kids[0], list(kids[1:])
    fixed = f"({head.h})" + (f" + {POP_GAP} + ({foot.h})" if foot is not None else "")
    room = f"App.Height - {2 * POP_MARGIN} - {2 * POP_PAD} - {POP_GAP} - {fixed}"
    natural = stack_height(rest, POP_GAP)
    body = group(f"con{prefix}Body", rest, direction="Vertical", gap=POP_GAP,
                 height=f"Max(60, Min({natural}, {room}))", overflow_y="Scroll")
    parts = [head, body] + ([foot] if foot is not None else [])
    modal = group(f"con{prefix}Modal", parts, direction="Vertical", gap=POP_GAP, fill=C_MODAL_BG,
                  border_color=C_PRIMARY_SOFT, radius=lay.RADIUS_MODAL,
                  pad=(POP_PAD, POP_PAD, POP_PAD, POP_PAD), width=width,
                  drop_shadow="ExtraBold", align_in_container="Center")
    backdrop = group(f"con{prefix}Backdrop", [modal], direction="Vertical", gap=0,
                     height="App.Height", width="App.Width", fill=C_OVERLAY, visible=vis,
                     justify="Center", align_items="Center",
                     pad=(POP_MARGIN, 0, POP_MARGIN, 0))
    backdrop.props["X"] = "0"
    backdrop.props["Y"] = "0"
    return backdrop


def _head(prefix, title_fx, close_fx, lead=(), title_w=None):
    """Titel og Close. title_w: titlens bredde - saa ombrydes en lang titel
    paa op til tre linjer i stedet for at blive klippet."""
    h = 26
    if title_w is not None:
        h = f"Min(3 * 23 + 2, Max(26, {_lines_h(title_fx, title_w, px=9.2, line_h=23)}))"
    title = grow(text_ctrl(f"txt{prefix}Title", title_fx, size=lay.SIZE_CARD_TITLE,
                           weight="Semibold", height=h, wrap="true" if title_w else "false"))
    close = button(f"btn{prefix}Close", '"Close"', close_fx,
                   width=fit_button_width('"Close"'), height=32,
                   accessible='"Close"')
    close.props["LayoutMinWidth"] = close.props["Width"]
    return group(f"con{prefix}Head", [*lead, title, close], direction="Horizontal", gap=10,
                 height=32 if title_w is None else f"Max(32, {h})", align_items="Center")


def _field(name, label, ctrl, required=False, visible=None):
    g = group(name, [label_row(name, label, required=required), ctrl], direction="Vertical",
              gap=6, visible=visible)
    return g


# ---------------------------------------------------------------------------
# New issue
# ---------------------------------------------------------------------------
FORM_ON = "IfError(varIbFormOn, false)"
# Hvad der mangler, for at sagen kan sendes - samme regler som VALID.
MISSING_FX = (
    "Concat(Filter(Table("
    '{ m: "an application", ok: !IsBlank(varIbFormApp) }, '
    '{ m: "a section", ok: !IsBlank(varIbFormSection) }, '
    '{ m: "where it happened", ok: !IbOtherNeeded || !IsBlank(Trim(inpIbOther.Text)) }, '
    '{ m: "a title of at least 4 characters", ok: Len(Trim(inpIbTitle.Text)) >= 4 }, '
    '{ m: "what happened", ok: !IsBlank(Trim(inpIbDesc.Text)) }), !ok), m, ", ")'
)
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

# Den nye sag ind i listen: EET opslag paa flowets ID - ikke hele listen
# forfra (issue #177). Fejler opslaget, hentes listen som foer.
ADD_NEW = (
    "Set(varIbSelId, Value(varIbRes.ticketid));\n"
    f"Set(varIbSelRow, IfError(LookUp({cfg.L_TICKETS}, ID = varIbSelId), Blank()));\n"
    "If(\n"
    "    IsBlank(varIbSelRow),\n"
    f"    {RELOAD_MAIN},\n"
    f"    Set(varIbNew, {_row('varIbSelRow', shared=False)});\n"
    f"    If({IS_ADMIN},\n"
    "        RemoveIf(colIbAll, Id = varIbSelId); Collect(colIbAll, varIbNew),\n"
    "        RemoveIf(colIbMine, Id = varIbSelId); Collect(colIbMine, varIbNew))\n"
    ")"
)

# Den nye sag i View mode - som et tryk paa flisen, men fra listen paa
# flowets ID, og raekken er allerede hel. Er den ikke i listen (hentningen
# fejlede), staar sagsnummeret stadig i beskeden.
SHOW_NEW = (
    "Set(varIbSel, LookUp(IbMine, Id = varIbSelId));\n"
    "If(\n"
    "    !IsBlank(varIbSel),\n"
    "    Set(varIbSelShared, false);\n"
    "    Set(varIbSelFullFor, varIbSelId);\n"
    '    Set(varIbTab, "details");\n'
    "    Set(varIbInternal, false);\n"
    "    Set(varIbActsOn, false);\n"
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
    "    " + ADD_NEW.replace("\n", "\n    ") + ";\n"
    "    Set(varIbSharedLoaded, false);\n"
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
    # En admin har alle sager i colIbAll; alle andre den anonyme liste.
    f"                ForAll(Filter(If({IS_ADMIN}, colIbAll, colIbShared), !Archived) As S,\n"
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
# Indholdet staar i popuppens scrollende krop - scrollbaren er trukket fra.
FORM_IN = f"({FORM_W} - {2 * POP_PAD} - {lay.SCROLLBAR_W})"


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
    # Altid den anonyme visning: formularen er aaben bagved, og intet herfra
    # maa kunne aendre en sag (Edit ville overskrive formularen).
    s_hit = row_hit("btnIbSimOpen", open_ticket("ThisItem.Row", "true"),
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
    # Felterne, Submit afhaenger af, opdaterer Text for hvert tegn - ikke
    # foerst, naar de mister fokus (saa naaede trykket paa Submit ikke frem,
    # foer den regnede felterne for udfyldt, issue #177).
    for c in (other, title, desc):
        c.props["TriggerOutput"] = "TriggerOutput.Keypress"
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
    # Hvad mangler der? Staar i foden lige under Submit - og i beskeden, hvis
    # man trykker for tidligt (issue #177).
    missing_text = f'"To submit, add " & {MISSING_FX} & "."'
    missing = text_ctrl("txtIbFormMissing", missing_text, size=lay.SIZE_SMALL,
                        color=f"If(varIbTried, {C_INVALID_FG}, {C_MUTED})",
                        height=_lines_h(missing_text, f"{FORM_W} - {2 * POP_PAD}", px=6.6),
                        wrap="true", visible=f"!({VALID})")
    # Submit er footerens eneste handling (issue #135). Den er ikke laast,
    # mens felterne er ufuldstaendige - et tryk siger, hvad der mangler.
    # Kun mens et kald koerer er den laast, og OnSelect tjekker det selv:
    # et hurtigt dobbeltklik naar ikke at sende sagen to gange.
    submit = button("btnIbFormSubmit", f'If({EDITING}, "Save changes", "Submit issue")',
                    "If(\n    varIbBusy,\n    false,\n"
                    f"    !({VALID}),\n"
                    "    Set(varIbTried, true);\n"
                    f"    Notify({missing_text}, NotificationType.Warning),\n"
                    f"    If(\n        {EDITING},\n        "
                    + SAVE_EDIT.replace("\n", "\n        ") + ",\n        "
                    + SUBMIT.replace("\n", "\n        ") + "\n    )\n)", primary=True,
                    width=fit_button_width('"Save changes"') + ICON_W, height=36,
                    icon=f'If({EDITING}, "Save", "Send")',
                    display_mode="If(varIbBusy, DisplayMode.Disabled, DisplayMode.Edit)")
    footer = group("conIbFormFooter", [submit], direction="Horizontal", gap=8,
                   height=36, justify="End", align_items="Center")
    foot = group("conIbFormFoot", [footer, missing], direction="Vertical", gap=8)
    kids = [head, intro, where, sec_hint, other_f, title_f, similar, desc_f, more, details,
            files, manage, context]
    # Foden staar fast under det, der scroller: Submit kan altid naas.
    return [_popup("IbForm", kids, FORM_ON, width=FORM_W, foot=foot), *build_discard()]


# ---------------------------------------------------------------------------
# En sag i View mode
# ---------------------------------------------------------------------------
DETAIL_ON = "IfError(varIbDetailOn, false)"
SEL = "varIbSel"
MINE = "!varIbSelShared"
DET_IN = f"({POP_IN} - {lay.SCROLLBAR_W})"
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
    navngivne formler IbCan*). Paa en bred skaerm staar de til hoejre.
    Archive og Delete ligger under More actions (kun admin), Delete sidst
    og i fare-farven; selve sletningen har sin egen bekraeftelse."""
    # Edit foerst, naar sagens hele raekke er hentet - ellers kunne de
    # felter, oversigten ikke henter, blive gemt tomme.
    ready = "varIbSelFullFor = varIbSelId"
    edit = icon_on_mobile(button("btnIbEdit", '"Edit"', OPEN_EDIT,
                                 width=fit_button_width('"Edit"') + ICON_W, height=34, icon="Edit",
                                 visible="IbCanEdit", accessible='"Edit this issue"',
                                 display_mode=f"If({ready} && !varIbBusy, DisplayMode.Edit, "
                                              "DisplayMode.Disabled)"))
    reopen = button("btnIbReopen", '"Reopen"', REOPEN, width=fit_button_width('"Reopen"'),
                    height=34, visible="IbCanReopen",
                    accessible='"Reopen this issue - the problem is still there"',
                    display_mode="If(varIbBusy, DisplayMode.Disabled, DisplayMode.Edit)")
    more_w = fit_button_width('"More actions"') + ICON_W
    more = icon_on_mobile(button("btnIbMoreActs", '"More actions"', "Set(varIbActsOn, !varIbActsOn)",
                                 width=more_w, height=34,
                                 icon='If(varIbActsOn, "ChevronUp", "MoreHorizontal")',
                                 visible="IbCanManage",
                                 accessible='If(varIbActsOn, "Hide more actions", '
                                            '"More actions: archive or delete")'))
    for b in (edit, reopen, more):
        b.props["LayoutMinWidth"] = b.props["Width"]
    row = group("conIbDetActions", [edit, reopen, more], direction="Horizontal", gap=8,
                height=34, align_items="Center", justify="End",
                visible="IbCanEdit || IbCanReopen || IbCanManage")
    row.props["LayoutJustifyContent"] = (f"If({NARROW}, LayoutJustifyContent.Start, "
                                         "LayoutJustifyContent.End)")

    # More actions: en lille flade lige under knapperne.
    archive = button("btnIbArchive", f'If({SEL}.Archived, "Restore", "Archive")',
                     ARCHIVE + ";\nSet(varIbActsOn, false)",
                     width=fit_button_width('"Restore"') + ICON_W, height=34,
                     icon=f'If({SEL}.Archived, "ArrowUndo", "Archive")',
                     accessible=f'If({SEL}.Archived, "Restore this issue from the archive", '
                                '"Archive this issue - it is kept with its history, but leaves '
                                'the active lists")',
                     display_mode="If(varIbBusy, DisplayMode.Disabled, DisplayMode.Edit)")
    delete = button("btnIbDelete", '"Delete"',
                    "Reset(inpIbDelConfirm);\nSet(varIbActsOn, false);\nSet(varIbDelOn, true)",
                    width=fit_button_width('"Delete"') + ICON_W, height=34, icon="Delete",
                    danger=True, accessible='"Delete this issue permanently"',
                    display_mode="If(varIbBusy, DisplayMode.Disabled, DisplayMode.Edit)")
    for b in (archive, delete):
        b.props["LayoutMinWidth"] = b.props["Width"]
    btns = group("conIbActsBtns", [archive, delete], direction="Horizontal", gap=8, height=34,
                 align_items="Center", justify="End")
    hint = text_ctrl("txtIbActsHint",
                     f'If({SEL}.Archived, "Restore brings the issue back to the active lists.", '
                     '"Archive keeps the issue, its comments, activity and files, and anyone can '
                     'still find it under Archived.") & " Delete removes it permanently for '
                     'everyone and asks you to confirm first."',
                     size=lay.SIZE_SMALL, color=C_MUTED, height=34, wrap="true")
    menu = group("conIbActsMenu", [hint, btns], direction="Vertical", gap=8, fill=C_MUTED_BG,
                 radius=10, pad=(10, 10, 10, 10), visible="IbCanManage && varIbActsOn")
    return row, menu


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
        "OnSelect": "false", "TabIndex": "0", **lay.radius(6),
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


FACT_H = 40
FACT_GAP = 12
# Seks fakta paa een linje, naar popuppen er bred nok; ellers to og to.
FACTS_OK = f"({DET_IN}) >= 600"
FACT_W = f"If({FACTS_OK}, (({DET_IN}) - 5 * {FACT_GAP}) / 6, (({DET_IN}) - {FACT_GAP}) / 2)"


def _fact(name, label, value_fx, visible=None):
    """Et faktum: en lille etiket over vaerdien."""
    lab = text_ctrl(f"txt{name}Label", f'"{label}"', size=lay.SIZE_MICRO, weight="Semibold",
                    color=C_MUTED, height=16)
    val = text_ctrl(f"txt{name}", value_fx, size=lay.SIZE_BODY, height=20,
                    accessible=f'"{label}: " & Self.Text')
    g = group(f"con{name}", [lab, val], direction="Vertical", gap=2, height=FACT_H, width=FACT_W,
              visible=visible)
    g.props["LayoutMinWidth"] = "0"
    return g


def _facts():
    """Fakta om sagen som et lille gitter - ikke en lang tekststreng.
    Hvem: kun det, brugeren maa se (samme regler som foer): rapportoeren
    ser "You", en admin rapportoerens initialer, den anonyme visning
    ingen."""
    def blank_as(expr, text):
        return f'If(IsBlank({expr}), "{text}", {expr})'
    sev = _fact("IbFactSeverity", "Severity", blank_as(f"{SEL}.Severity", "Not set"))
    pri = _fact("IbFactPriority", "Priority", blank_as(f"{SEL}.Priority", "Not set"))
    asg = _fact("IbFactAssigned", "Assigned to",
                f'If(varIbSelShared, "Not shown", {blank_as(SEL + ".Assigned", "Not assigned")})')
    rep = _fact("IbFactReporter", "Reported by",
                f'If(varIbSelShared, "Anonymous", IbSelMine, "You", {IS_ADMIN}, '
                f'{_initials(SEL + ".Reporter")}, "Not shown")')
    reported = _fact("IbFactReported", "Reported", f"Text({SEL}.CreatedOn, {DATE_FMT})")
    # Updated kun efter en reel aendring (IbSelUpdatedOn) - den staar sidst,
    # saa der ikke opstaar et hul, naar den ikke vises.
    updated = _fact("IbFactUpdated", "Updated", f"Text(IbSelUpdatedOn, {DATE_FMT})",
                    visible="!IsBlank(IbSelUpdatedOn)")
    pair_w = f"If({FACTS_OK}, 2 * {FACT_W} + {FACT_GAP}, {DET_IN})"
    pairs = [group(f"conIbFacts{i}", cells, direction="Horizontal", gap=FACT_GAP, height=FACT_H,
                   width=pair_w)
             for i, cells in enumerate([(sev, pri), (asg, rep), (reported, updated)], 1)]
    for p in pairs:
        p.props["LayoutMinWidth"] = "0"
    g = group("conIbDetFacts", pairs, direction="Horizontal", gap=FACT_GAP,
              height=f"If({FACTS_OK}, {FACT_H}, 3 * {FACT_H} + 2 * 8)")
    g.props["LayoutDirection"] = (f"If({FACTS_OK}, LayoutDirection.Horizontal, "
                                  "LayoutDirection.Vertical)")
    g.props["LayoutGap"] = f"If({FACTS_OK}, {FACT_GAP}, 8)"
    return g


ROLE_TONE = {"User": "info", "Admin": "violet", "System": "neutral"}
ROLE_W = 56


def _role_tokens(expr):
    def sw(part):
        body = ", ".join(f'"{r}", {_t("state-" + c + "-" + part)}' for r, c in ROLE_TONE.items())
        return f"Switch({expr}, {body}, {_t('state-neutral-' + part)})"
    return sw("fg"), sw("bg")


def build_detail():
    # 1. Sagsnummeret som maerke, titlen og Close.
    no = text_ctrl("txtIbDetNo", f"{SEL}.TicketNo", size=lay.SIZE_SMALL, weight="Semibold",
                   color=C_PRIMARY, height=24, width=NO_W, align="Center", fill=C_MUTED_BG,
                   extra={"VerticalAlign": "VerticalAlign.Middle", **lay.radius(12)})
    no.props["LayoutMinWidth"] = str(NO_W)
    close_w = fit_button_width('"Close"')
    head = _head("IbDet", f"{SEL}.Title", "Set(varIbDetailOn, false);\nSet(varIbActsOn, false)",
                 lead=[no], title_w=f"({POP_IN}) - {NO_W} - {close_w} - 20")

    # 2. Status, Application og Section.
    chip = _chip("txtIbDetStatus", f"{SEL}.Status", f"{SEL}.Archived")
    chip.props["LayoutMinWidth"] = str(CHIP_W)
    where = grow(text_ctrl("txtIbDetWhere", f'{SEL}.Application & "  ·  " & {SEL}.Section',
                           size=lay.SIZE_BODY, weight="Semibold", height=20))
    meta = group("conIbDetMeta", [chip, where], direction="Horizontal", gap=10, height=24,
                 align_items="Center")

    # 3. Fakta.  4. Handlinger (og More actions).
    facts = _facts()
    actions, menu = _actions()

    shared_note = text_ctrl("txtIbDetShared",
                            '"Anonymous view. Who reported it, their details, the comments and '
                            'the files are private and not shown here."',
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

    # 5. Navigationen i indholdet - adskilt fra handlingerne af en streg.
    rule = group("conIbDetRule", [], direction="Horizontal", height=1, fill=C_DIVIDER)
    n_act = "CountRows(Filter(colIbActivity, Kind <> \"Reported\"))"
    tabs = group("conIbDetTabs", [
        _tab("btnIbTabDetails", '"Description"', "details", '"Show the description"'),
        _tab("btnIbTabActivity", f'"Activity (" & {n_act} & ")"', "activity",
             '"Show the activity and comments, " & ' + n_act + ' & " entries"'),
        _tab("btnIbTabFiles", '"Attachments (" & IbFileCount & ")"', "files",
             '"Show the attachments, " & IbFileCount & " files"',
             onselect='Set(varIbTab, "files");\nIf(varIbFilesFor <> varIbSelId, ' + LOAD_FILES + ")"),
    ], direction="Horizontal", gap=8, height=32, align_items="Center", visible=MINE)
    # Tre faner skal kunne staa paa en telefon: de deler bredden.
    for t in tabs.children:
        t.props["Width"] = f"Min({TAB_W}, ({DET_IN} - 16) / 3)"

    # 6. Det valgte indhold.
    show_details = f'varIbSelShared || varIbTab = "details"'
    loading_more = text_ctrl("txtIbDetLoading", '"Loading the rest of the issue..."',
                             size=lay.SIZE_SMALL, color=C_MUTED, height=18,
                             visible=f"{MINE} && varIbSelFullFor <> varIbSelId")
    blocks = [
        _text_block("IbDetDesc", "Description", f"{SEL}.Description"),
        loading_more,
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
    # noter i advarselsfarven - og med teksten "internal note", ikke kun
    # farve. Ved hver linje et maerke: User, Admin eller System (issue #177).
    tw = "Parent.TemplateWidth"
    body_h = _lines_h("ThisItem.Body", ACT_BODY_W)
    row_h = f"(30 + {body_h} + 10)"
    bg = text_ctrl("txtIbActBg", '""', size=lay.SIZE_MICRO, height=f"{row_h} - 4", width=tw,
                   accessible='"Background"',
                   fill=(f"If(ThisItem.Internal, {C_WARN_BG}, ThisItem.IsSystem, {C_TRANSPARENT}, "
                         f"{C_MUTED_BG})"),
                   extra={"X": "0", "Y": "2", **lay.radius(8),
                          "BorderColor": f"If(ThisItem.IsSystem, {C_CARD_BORDER}, {C_TRANSPARENT})",
                          "BorderStyle": "BorderStyle.Dashed",
                          "BorderThickness": "If(ThisItem.IsSystem, 1, 0)"})
    rfg, rbg = _role_tokens("ThisItem.Role")
    role = text_ctrl("txtIbActRole", "ThisItem.Role", size=lay.SIZE_MICRO, weight="Semibold",
                     height=20, width=ROLE_W, align="Center", color=rfg, fill=rbg,
                     accessible='"Role: " & Self.Text',
                     extra={"X": str(ACT_ROW_PAD), "Y": "8", "VerticalAlign": "VerticalAlign.Middle",
                            **lay.radius(10)})
    actor_x = ACT_ROW_PAD + ROLE_W + 8
    actor = text_ctrl("txtIbActActor",
                      'ThisItem.Actor & If(ThisItem.Internal, "  ·  internal note, admins only", '
                      'ThisItem.Kind = "Comment", "  ·  comment", "")',
                      size=lay.SIZE_BODY, weight="Semibold",
                      color=(f"If(ThisItem.Internal, {C_WARN_FG}, ThisItem.IsSystem, {C_MUTED}, "
                             f"{C_TITLE})"), height=20,
                      width=f"{tw} - {actor_x} - {ACT_ROW_PAD} - 150",
                      extra={"X": str(actor_x), "Y": "8"})
    when = text_ctrl("txtIbActWhen", f"Text(ThisItem.At, {DATETIME_FMT})",
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
    }, children=[bg, role, actor, when, body], h=gal_h, vis="!varIbActBusy")
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
    # Post comment laases op, mens man skriver - ikke foerst, naar feltet
    # mister fokus (saa ville det foerste klik paa knappen gaa tabt).
    comment.props["TriggerOutput"] = "TriggerOutput.Keypress"
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
    archived_hint = text_ctrl("txtIbArchivedHint",
                              '"This issue is archived. Its history is kept, and comments are '
                              'closed."',
                              size=lay.SIZE_SMALL, color=C_MUTED, height=18,
                              visible=f"{SEL}.Archived")
    activity = group("conIbDetActivity", [act_state, gal, composer, archived_hint],
                     direction="Vertical", gap=12, visible=f'{MINE} && varIbTab = "activity"')

    kids = [head, meta, facts, actions, menu, shared_note, retest, rule, tabs, details, activity,
            _files_panel()]
    return [_popup("IbDet", kids, DETAIL_ON)]


def build_delete():
    """Permanent sletning - sin egen popup oven paa sagen. Nummeret skal
    skrives, teksten siger, at det ikke kan fortrydes, og knappen er laast,
    til nummeret passer, og mens kaldet koerer. Close er eneste vej ud."""
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
    confirm.props["TriggerOutput"] = "TriggerOutput.Keypress"
    confirm_f = group("conIbDelConfirmF", [
        text_ctrl("txtIbDelConfirmLabel", f'"Type " & {SEL}.TicketNo & " to confirm"',
                  size=lay.SIZE_BODY, weight="Semibold", height=20),
        confirm], direction="Vertical", gap=6)
    ok = button("btnIbDelConfirm", '"Delete permanently"', DELETE, danger=True,
                width=fit_button_width('"Delete permanently"') + ICON_W, height=36, icon="Delete",
                accessible=f'"Delete " & {SEL}.TicketNo & " permanently"',
                display_mode=f"If({match} && !varIbBusy, DisplayMode.Edit, DisplayMode.Disabled)")
    footer = group("conIbDelFooter", [ok], direction="Horizontal", gap=8, height=36,
                   justify="End", align_items="Center")
    return [_popup("IbDel", [head, warn, confirm_f], del_on, width="Min(480, App.Width - 24)",
                   foot=footer)]


def build_loading():
    return [loading_overlay("imgIbLoading", "varIbLoading", "Loading issues, please wait"),
            loading_overlay("imgIbBusy", "(varIbBusy || varIbPosting) && !varIbUploading",
                            "Sending, please wait"),
            loading_overlay("imgIbUploading", "varIbUploading", "Uploading files, please wait",
                            caption="Uploading files...")]
