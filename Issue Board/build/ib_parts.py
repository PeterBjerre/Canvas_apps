# -*- coding: utf-8 -*-
"""
Issue Board-skaermen (issue #114, trin 1 og 2): delene, formlerne og
hentningen.

    [ikon] Issue Board                              [Refresh] [+ New issue]
           Report what you find while testing ...
    +------------------------------------------------------------------+
    | [All issues|My issues|Assigned to me] [Open|Closed|Arch.] [Search...] |
    | [Application v][Section v] [Status v][Priority v]          [Sort v] |
    | 12 open issues                                   [Clear filters] |
    | TICKET ID  REQUESTER TITLE        APPLICATION ... STATUS  UPDATED  |
    | ISS-000142 UFFES     Save does... VH-plan     ... [New]   09 Oct [@]|
    +------------------------------------------------------------------+
    Issue #229: en liste som Masterdata Hub i stedet for fliser. Filtrene
    er en kompakt vaerktoejslinje oeverst i listekortet, og galleriet er
    aldrig hoejere end pladsen under den. Under Desktop er hver raekke et
    kompakt kort paa tre linjer. Vaerktoejslinjen er to flow_row-raekker
    direkte i kortet (issue #244 - se build_filters).

    New issue   -> popup: Application/Section, titel, lignende sager,
                   "What happened?", flere detaljer (valgfrit), Submit ->
                   Patch direkte i IB_Tickets (issue #193). Filer laegges
                   paa bagefter: papirclipsen i raekken.
    En raekke   -> popup i View mode (issue #229): 1) nummer, titel og
                   Close-ikonet; 2) status, prioritet, Application og
                   Section; 3) metadata (Requester, Assigned to, Severity,
                   Reported, Updated); 4) handlingerne som ikoner (Reopen,
                   Edit, Archive, Delete) - hver kun, naar brugeren maa
                   (IbCan*); 5) fanerne Description, Activity og
                   Attachments, centreret; 6) indholdet. Alt til og med
                   fanerne staar fast; kun indholdet scroller, og det har
                   samme hoejde for alle tre faner (issue #212).
    Edit        -> samme formular som New issue, udfyldt (Edit mode). En
                   admin faar desuden status, prioritet, tildeling og
                   loesning.
    Delete      -> egen bekraeftelse: sagsnummeret skal skrives.

SIKKERHED ER IKKE HER
---------------------
Alle filtre og knapper paa skaermen er UX. Siden issue #193 kan alle
laese alle sager i IB_Tickets (ingen anonymisering), og appen opretter
og retter sagen selv med Patch. SharePoint haandhaever, at en bruger kun
kan rette sine egne sager, og at admins (Design paa listen) kan rette
alle - IKKE hvilke felter: at kun en admin flytter status, prioritet og
tildeling, og at rapportoeren kun retter, mens sagen er New, er appens
regel. Kommentarer og haendelser (IB_TicketComments) skrives stadig af
flowet med rettigheder paa raekken: kun rapportoeren og admins kan laese
dem - det haandhaever SharePoint (ib_config.py).

HENTNING (issue #177)
--------
  * Konfigurationen og EEN liste hentes samtidig, foerste gang skaermen
    vises: alle sager (issue #193 - "My issues" er et filter paa dem).
    Oversigten henter ikke de lange tekster (ShowColumns).
  * Naar en sag aabnes, hentes dens hele raekke og - for rapportoeren og
    admins - dens Activity samtidig.
    Antallet af vedhaeftninger regnes af Activity; selve filerne hentes
    foerst, naar fanen Attachments vaelges.
  * Efter en aendring hentes kun den ene sag igen (LookUp paa ID) og
    dens Activity - ikke hele listen.
  * Soegning, filtre og sortering regnes i hukommelsen paa de hentede
    raekker - intet kald pr. filtervalg eller tastetryk.
  * En kommentar eller intern note saettes ind lokalt i feeden, naar
    flowet har svaret ok - Activity hentes ikke igen (issue #212).
  * Andres aendringer: en stille opdatering af oversigten, naar man kommer
    tilbage til skaermen (hoejst hvert SYNC_AFTER_MIN minut) og fra
    Refresh. Ingen timer. Listerne hentes i en midlertidig samling, saa en
    fejlet hentning aldrig toemmer det, der staar.
"""
from gen_screen import (Ctrl, stack_height, C_APP_BG, C_CARD_BG, C_CARD_BORDER, C_DIVIDER, C_INFO_BG,
                        C_INFO_FG, C_INVALID_FG, C_MUTED, C_MUTED_BG, C_MODAL_BG, C_OVERLAY,
                        C_PRIMARY, C_PRIMARY_SOFT, C_TITLE, C_TRANSPARENT, C_WARN_BG,
                        C_WARN_FG)
from build_helpers import (button, card, checkbox_theme, concurrent, confirm_modal,
                           fit_button_width, group,
                           flow_row, grow, icon_on_mobile, label_row, loading_overlay, row_hit, row_rule,
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
    "    Set(varIbInternal, false);\n"
    "    Set(varIbFilesFor, -1);\n"
    "    Set(varIbSelFullFor, -1);\n"
    "    Set(varIbTried, false);\n"
    "    Set(varIbBusy, false);\n"
    "    Set(varIbUploading, false);\n"
    "    Set(varIbSelPeek, false);\n"
    "    Set(varIbPosting, false);\n"
    "    Set(varIbSyncing, false)\n"
    ")"
)


def _rank(field, pairs, fallback):
    body = ", ".join(f'"{k}", {r}' for k, r in pairs)
    return f"Switch({field}, {body}, {fallback})"


STATUS_RANK = [(s, r) for s, _c, r in cfg.STATUS]

# Felterne, der kun bruges i popuppen. Oversigten henter dem ikke (de er
# lange tekster); de kommer med sagens eget opslag, naar den aabnes.
DETAIL_ONLY = ("Steps", "Expected", "Actual", "Other", "RelatedNo", "Resolution")


def _row(r, *, full=True):
    """Een raekke i colIbAll. full=False: oversigtens raekke - popup-
    felterne er tomme, til sagen aabnes. Nummeret saettes af flowet
    BioSap-IssueBoard-OnCreated op til et minut efter oprettelsen; indtil
    da regnes det af ID i samme format (issue #193)."""
    f = {
        "Id": f"{r}.ID",
        "TicketNo": f'If(IsBlank({r}.TicketNo), "ISS-" & Text({r}.ID, "000000"), {r}.TicketNo)',
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
        "ReporterName": f'Coalesce({r}.ReporterName, "")',
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
                 "Priority", "Status", "AssignedToName", "ReporterEmail", "ReporterName",
                 "AssignedToEmail", "Created", "LastActivityOn", "IsArchived"]
_SHOW = ", ".join(OVERVIEW_COLS)

# Hentningerne. Hver sammenligner med en global variabel eller en konstant,
# saa SharePoint udfoerer filteret og sorteringen (check_layout regel 30).
FETCH_SECTIONS = (f"ForAll(Filter({cfg.L_SECTIONS}, IsActive = true) As r, "
                  '{ Application: Coalesce(r.Application, ""), Section: Coalesce(r.Section, ""), '
                  "AppOrder: Coalesce(r.AppOrder, 0), SectionOrder: Coalesce(r.SectionOrder, 0), "
                  'ScreenKey: Coalesce(r.ScreenKey, "") })')
# Alle sager - siden issue #193 kan alle laese dem. "My issues" er et
# filter i hukommelsen (IbMine), ikke en hentning mere.
FETCH_ALL = (f"ForAll(ShowColumns(Sort({cfg.L_TICKETS}, LastActivityOn, SortOrder.Descending), "
             f"{_SHOW}) As r, {_row('r', full=False)})")

RELOAD_ALL = f"Set(varIbAllFailed, IfError(ClearCollect(colIbAll, {FETCH_ALL}); false, true))"
RELOAD_MAIN = RELOAD_ALL

# FLASKEHALSEN (issue #177): een runde - konfigurationen og den ene liste
# samtidig, og IsAdmin staar ikke i koe foran hentningen.
LOAD = (
    "If(\n"
    "    !varIbLoaded,\n"
    "    Set(varIbLoading, true);\n"
    "    " + concurrent(
        f"Set(varIbCfgFailed, IfError(ClearCollect(colIbSections, {FETCH_SECTIONS}); false, true))",
        RELOAD_MAIN, indent=4) + ";\n"
    "    Set(varIbLoaded, !varIbCfgFailed && !varIbAllFailed);\n"
    "    Set(varIbSyncedAt, Now());\n"
    "    Set(varIbLoading, false)\n"
    ")"
)

SET_SCOPE = f'If(IsBlank(varIbScope), Set(varIbScope, If({IS_ADMIN}, "all", "mine")))'

RETRY = "Set(varIbLoaded, false);\n" + LOAD + ";\n" + SET_SCOPE

# STILLE OPDATERING (issue #212): oversigten hentes igen uden ventespinner
# og uden at filtre, sortering, scope eller en aaben sag roeres. Den nye
# liste hentes i en midlertidig samling og skrives foerst over, naar den
# kom hjem - fejler hentningen, staar den gamle liste der stadig, og en
# besked siger det. Ingen timer: den koerer, naar man kommer tilbage til
# skaermen (hoejst hvert SYNC_AFTER_MIN minut), og fra Refresh.
SYNC_AFTER_MIN = 2
SYNC = (
    "Set(varIbSyncing, true);\n"
    f"Set(varIbSyncFailed, IfError(ClearCollect(colIbFresh, {FETCH_ALL}); false, true));\n"
    "If(\n"
    "    varIbSyncFailed,\n"
    '    Notify("The issues could not be refreshed. The list shows what was loaded last.", '
    "NotificationType.Error),\n"
    "    ClearCollect(colIbAll, colIbFresh);\n"
    "    Clear(colIbFresh);\n"
    "    Set(varIbSyncedAt, Now())\n"
    ");\n"
    "Set(varIbSyncing, false)"
)
# Refresh: stille, naar listen er hentet; ellers som Retry.
REFRESH = f"If(\n    varIbLoaded,\n    {SYNC.replace(chr(10), chr(10) + '    ')},\n    {RETRY.replace(chr(10), chr(10) + '    ')}\n)"
# Tilbage paa skaermen: stille opdatering, hvis listen er mere end
# SYNC_AFTER_MIN minutter gammel. Foerste gang koerer LOAD i stedet.
SYNC_ON_RETURN = (
    f"If(\n    varIbLoaded && !varIbSyncing && DateDiff(varIbSyncedAt, Now(), TimeUnit.Minutes) >= "
    f"{SYNC_AFTER_MIN},\n    {SYNC.replace(chr(10), chr(10) + '    ')}\n)"
)


def on_visible():
    return INIT_STATE + ";\n" + SYNC_ON_RETURN + ";\n" + LOAD + ";\n" + SET_SCOPE


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
    "    colIbActFresh,\n"
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
    # Hentes i en midlertidig samling og skrives foerst over, naar den kom
    # hjem (issue #212): fejler en genhentning, staar den gamle feed der
    # stadig - og ingen dobbelte raekker.
    "If(!varIbActFailed, ClearCollect(colIbActivity, colIbActFresh); Clear(colIbActFresh));\n"
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
    "        RemoveIf(colIbAll, Id = varIbSelId);\n"
    "        Set(varIbDetailOn, false),\n"
    f"        Set(varIbSel, {_row('r', )});\n"
    "        Set(varIbSelFullFor, varIbSelId);\n"
    # r.Attachments kan ikke laeses fra With's LookUp - compile: "The
    # specified column is not accessible in this context" (issue #133).
    # Er fanen aaben, hentes filerne igen med LOAD_FILES' egen LookUp;
    # ellers hentes de foerst, naar fanen vaelges.
    "        If(varIbTab = \"files\",\n"
    + "".join("            " + l + "\n" for l in LOAD_FILES.split("\n")) +
    "        , Set(varIbFilesFor, -1));\n"
    "        UpdateIf(colIbAll, Id = varIbSelId, varIbSel)\n"
    "    )\n"
    ")"
)

# Naar en sag aabnes: sagens egen raekke (de lange tekster, som oversigten
# ikke hentede) og dens Activity SAMTIDIG - to opslag paa ID, ikke to i
# koe. Popuppen staar allerede fremme med det, oversigten havde. Activity
# hentes kun for rapportoeren og admins (IbSeeActivity): andre har ingen
# rettighed til kommentarerne, og hentningen ville give en tom liste.
# Vedhaeftningerne hentes foerst, naar fanen vaelges (LOAD_FILES).
LOAD_OPEN = (
    "Set(varIbSelRow, Blank());\n"
    + concurrent(
        f"Set(varIbSelRow, IfError(LookUp({cfg.L_TICKETS}, ID = varIbSelId), Blank()))",
        "If(IbSeeActivity,\n" + LOAD_ACTIVITY + "\n)") + ";\n"
    "If(\n"
    "    !IsBlank(varIbSelRow) && varIbSelRow.ID = varIbSelId,\n"
    f"    Set(varIbSel, {_row('varIbSelRow', )});\n"
    "    Set(varIbSelFullFor, varIbSelId);\n"
    "    UpdateIf(colIbAll, Id = varIbSelId, varIbSel)\n"
    ")"
)


def open_ticket(rec, peek, tab="details"):
    """Aabn en sag i View mode. rec: raekken; peek: sand, naar sagen
    aabnes fra forslagene i New issue - kun laesning, ingen handlinger
    (Edit ville overskrive formularen bagved). tab: fanen, der vises -
    "files" fra papirclipsen paa flisen (issue #193)."""
    files = tab == "files"
    return (
        f"Set(varIbSel, {rec});\n"
        "Set(varIbSelId, varIbSel.Id);\n"
        f"Set(varIbSelPeek, {peek});\n"
        f'Set(varIbTab, "{tab}");\n'
        "Set(varIbInternal, false);\n"
        "Set(varIbFilesFor, -1);\n"
        "Reset(inpIbComment);\n"
        "Clear(colIbActivity);\n"
        "Set(varIbDetailOn, true);\n"
        + (LOAD_FILES + ";\n" if files else "")
        + LOAD_OPEN
    )



# Skemaerne for samlingerne. If(false, ...): kun skemaet (check_layout
# regel 34) - App.OnStart maa ikke toemme det, OnVisible fylder.
ROW = {"Id": "0", "TicketNo": '""', "Title": '""', "Description": '""', "Steps": '""',
       "Expected": '""', "Actual": '""', "Application": '""', "Section": '""', "Other": '""',
       "RelatedNo": '""', "Severity": '""', "Priority": '""', "Status": '""',
       "Resolution": '""', "Assigned": '""', "CreatedOn": "Now()", "UpdatedOn": "Now()",
       "Archived": "false", "Reporter": '""', "ReporterName": '""', "AssignedEmail": '""',
       "PriRank": "0",
       "StatusRank": "0"}
SEC = {"Application": '""', "Section": '""', "AppOrder": "0", "SectionOrder": "0",
       "ScreenKey": '""'}
ACT = {"Kind": '""', "Actor": '""', "Role": '""', "Body": '""', "At": "Now()", "Internal": "false",
       "IsSystem": "false", "File": '""', "SizeKb": "0", "Initial": "false"}
ADMINS = {"Email": '""', "Name": '""'}
UPLOAD = {"Name": '""', "Msg": '""'}


def collections():
    return [("colIbAll", ROW), ("colIbSections", SEC), ("colIbActivity", ACT), ("colIbAdmins", ADMINS),
            ("colIbUp", UPLOAD), ("colIbFresh", ROW), ("colIbActFresh", ACT)]


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
# Fliser og en sag uden Activity: "Updated" kun, naar sagen er aendret mere end
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
IbFailed = IfError(varIbCfgFailed, false) || IfError(varIbAllFailed, false);
// Alle henter alle sager (issue #193); "My issues" er et filter paa dem.
IbMine = Filter(colIbAll, Reporter = varIbMe);
// Scopet: All issues, My issues og - for admin - Assigned to me. Filtrene
// regnes oven paa det.
IbScopeRows = Switch(varIbScope, "all", colIbAll, "assigned", Filter(colIbAll, AssignedEmail = varIbMe), IbMine);
// Hvad maa brugeren paa den aabne sag? EET sted for knapperne. Kun
// kommentarerne er beskyttet af SharePoint (rettigheder paa raekken i
// IB_TicketComments); resten er appens regler (issue #193).
IbSelMine = varIbSel.Reporter = varIbMe;
// Activity og kommentarer: kun rapportoeren og admins.
IbSeeActivity = IbSelMine || {IS_ADMIN};
// Updated vises kun efter en reel aendring: en haendelse efter
// indmeldingen. Uden Activity taeller kun en aendring mere end
// {UPDATED_AFTER_MIN} minutter efter indmeldingen.
IbSelUpdatedOn = If(IbSeeActivity, Max(Filter(colIbActivity, Kind <> "Reported" && !Initial), At), If(DateDiff(varIbSel.CreatedOn, varIbSel.UpdatedOn, TimeUnit.Minutes) >= {UPDATED_AFTER_MIN}, varIbSel.UpdatedOn, Blank()));
IbCanEdit = !varIbSelPeek && !varIbSel.Archived && ({IS_ADMIN} || (IbSelMine && varIbSel.Status = "{cfg.STATUS_EDITABLE}"));
IbCanReopen = !varIbSelPeek && !varIbSel.Archived && ({IS_ADMIN} || IbSelMine) && varIbSel.Status in {REOPENABLE_FX};
IbCanManage = !varIbSelPeek && {IS_ADMIN};
IbCanComment = !varIbSelPeek && IbSeeActivity && !varIbSel.Archived;
// Filer paa en sag: rapportoeren og admins (flowet tjekker det igen).
IbCanAttach = !varIbSelPeek && IbSeeActivity && !varIbSel.Archived;
// Antallet af filer paa sagen - af Activity, saa fanen kan vise det uden
// at hente filerne. Uden Activity: de hentede filer, naar fanen er valgt.
IbFileCount = If(IbSeeActivity, CountRows(Filter(colIbActivity, Kind = "Attachment")), varIbFilesFor = varIbSelId, CountRows(varIbFiles), Blank());'''


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
              "Reset(inpIbRelated);\nReset(drpIbSeverity);\n"
              "Reset(drpIbStatus);\nReset(drpIbPriority);\nReset(drpIbAssignee);\nReset(inpIbResolution)")

# Formularen staar fremme med det samme. Forslagene til lignende sager
# kommer fra colIbAll, der allerede er hentet.
OPEN_FORM = (
    'Set(varIbFormMode, "new");\n'
    "Set(varIbFormApp, IbFrom);\n"
    'Set(varIbFormSection, "");\n'
    "Set(varIbMore, false);\n"
    "Set(varIbTried, false);\n"
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
    # Refresh er ikke laengere en del af det normale arbejde - hver aendring
    # opdaterer selv det, den roerer (issue #212). Den henter andres
    # aendringer stille, uden at filtrene eller en aaben sag roeres.
    refresh = button("btnIbRefresh", '"Refresh"', REFRESH,
                     width=fit_button_width('"Refresh"'), height=36,
                     accessible='"Load the latest changes from everyone"',
                     display_mode="If(varIbLoading || varIbSyncing, DisplayMode.Disabled, DisplayMode.Edit)")
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


# Scopet "All issues": alle sager, med navn (issue #193).
SCOPE_ALL = 'varIbScope = "all"'
ADMIN_BOARD = f'{IS_ADMIN} && varIbScope in ["all", "assigned"]'
FILTERED = ("!IsBlank(varIbApp) || !IsBlank(varIbSection) || !IsBlank(varIbStatusF) || "
            "!IsBlank(varIbPriF) || !IsBlank(Trim(inpIbSearch.Text))")
CLEAR_FILTERS = ('Set(varIbApp, "");\nSet(varIbSection, "");\nSet(varIbStatusF, "");\n'
                 'Set(varIbPriF, "");\nReset(inpIbSearch);\nReset(drpIbFltApp);\n'
                 "Reset(drpIbFltSection);\nReset(drpIbFltStatus);\nReset(drpIbFltPriority)")

# VAERKTOEJSLINJEN (issue #244) - to raekker direkte i listekortet.
#
#   [All issues|My issues|Assigned to me] [Open|Closed|Archived] [Search......]
#   [Application v][Section v] [Status v][Priority v]            [Sort v]
#
# HVORFOR KNAPPERNE IKKE KUNNE SES (issue #229 -> #244)
# -----------------------------------------------------
# Foer stod kontrollerne tre-fire containere nede: conIbToolbar (lodret) >
# conIbSwitches / conIbFltLine (raekker, der SKIFTEDE RETNING med en
# formel, men havde en KONSTANT LayoutAlignItems.Start) > conIbScope /
# conIbState / conIbFltRow / conIbFltRow2 (indlejrede grupper med
# LayoutMinWidth = Width) > conIbFltPairA/B > kontrollerne. Hoejderne gik
# op - 34 + 10 + 36 = 80 px paa en bred skaerm, og regel 2/3 var groen -
# men i den udgivne app var de 80 px TOMME: indholdet blev tegnet under
# sin raekkes overkant og skjult af LayoutOverflow.Hide. Det er den samme
# fejl, topbjaelken havde (build_helpers.top_bar: "en indlejret gruppe
# ... og en retning, der skiftede efter bredden. I Studio stod knapperne
# en linje for lavt og blev skaaret over"). De raekker, der VISES i det
# samme kort (taelleren og overskrifterne), staar direkte i kortet.
#
# Nu: hver linje er en build_helpers.flow_row DIREKTE i kortet - samme
# konstruktion som hubbens filterlinje og KKS-opslagets knapper, der begge
# ses i den udgivne app: vandret med LayoutAlignItems.Center, eller lodret
# med Stretch (begge som formel). Hoejst EEN fast, vandret gruppe inde i
# raekken (segmenterne og listeparrene), og den har sin egen hoejde.
# Kontrollernes bredder regnes af kortets indre bredde (TB_W, en nedre
# graense), og soegefeltet tager resten (grow). Ingen Y, ingen forskydning.
TB_W = CARD_W
SEG_GAP = 4
SCOPE_W = {"btnIbScopeAll": 96, "btnIbScopeMine": 100, "btnIbScopeAssigned": 128}
STATE_W = {"btnIbStateOpen": 76, "btnIbStateClosed": 84, "btnIbStateArchived": 92}
SCOPE_ADMIN_W = sum(SCOPE_W.values()) + 2 * SEG_GAP
SCOPE_USER_W = SCOPE_W["btnIbScopeAll"] + SCOPE_W["btnIbScopeMine"] + SEG_GAP
STATE_ALL_W = sum(STATE_W.values()) + 2 * SEG_GAP
TB_GAP = 12          # mellem grupperne i en linje
SEARCH_MIN = 240
SORT_W = 150
DD_MIN = 130         # en filterliste ("All applications" + pilen)
PAIR_MIN = 2 * DD_MIN + 8
# Linje 1 paa een linje: begge kontakter + soegefeltets mindstebredde.
TOP_OK = f"{TB_W} >= {SCOPE_ADMIN_W + TB_GAP + STATE_ALL_W + TB_GAP + SEARCH_MIN}"
# Linje 2 paa een linje: to listepar + sorteringen.
FLT_OK = f"{TB_W} >= {2 * PAIR_MIN + TB_GAP + TB_GAP + SORT_W}"
# Hver linjes hoejde, naar den staar vandret.
TB_LINE_H = 36


def _seg_group(name, segs, wide_w, ok):
    """En fast, vandret gruppe af segmenter. Paa een linje: de faste
    bredder. Under hinanden (flow_row lodret, Stretch): hele linjen, og
    segmenterne deler den."""
    g = group(name, segs, direction="Horizontal", gap=SEG_GAP, height=SEG_H,
              align_items="Center", width=f"If({ok}, {wide_w}, {TB_W})")
    return g


def build_filters():
    """Vaerktoejslinjens to raekker - de staar direkte i listekortet."""
    n_scope = f"If({IS_ADMIN}, 3, 2)"
    narrow_scope = f"(({TB_W}) - {SEG_GAP} * ({n_scope} - 1)) / {n_scope}"
    all_seg = _seg("btnIbScopeAll", "All issues", SCOPE_ALL,
                   'Set(varIbScope, "all")', SCOPE_W["btnIbScopeAll"],
                   '"Show all issues from all testers"')
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
    scope = _seg_group("conIbScope", [all_seg, mine_seg, asg_seg],
                       f"If({IS_ADMIN}, {SCOPE_ADMIN_W}, {SCOPE_USER_W})", TOP_OK)

    states = [("btnIbStateOpen", "Open", "open", '"Show open issues"'),
              ("btnIbStateClosed", "Closed", "closed", '"Show closed issues"'),
              ("btnIbStateArchived", "Archived", "archived", '"Show archived issues"')]
    segs = []
    for name, label, key, acc in states:
        s = _seg(name, label, f'varIbState = "{key}"', f'Set(varIbState, "{key}")', STATE_W[name],
                 acc)
        s.props["Width"] = f"If({TOP_OK}, {STATE_W[name]}, (({TB_W}) - {2 * SEG_GAP}) / 3)"
        s.props["LayoutMinWidth"] = s.props["Width"]
        segs.append(s)
    state = _seg_group("conIbState", segs, STATE_ALL_W, TOP_OK)

    search = text_input("inpIbSearch", '""', placeholder='"Search number, title or description"',
                        label='"Search issues"')
    # Listen filtreres i hukommelsen - et lille ophold, saa den ikke regnes
    # om for hvert tegn.
    search.props["TriggerOutput"] = "TriggerOutput.Delayed"
    search.props["Width"] = str(SEARCH_MIN)
    top = flow_row("conIbTbTop", [scope, state, search], TB_W, gap=TB_GAP, flex=search,
                   flex_min=SEARCH_MIN, ok=TOP_OK)

    # Application og den afhaengige Section, status og prioritet - to og
    # to - og sorteringen. Paa een linje deler parrene bredden efter
    # sorteringen; under hinanden faar hvert par hele linjen.
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
    drp_sort = themed_dropdown("drpIbSort", '["Last updated", "Newest", "Oldest", "Priority", "Status"]',
                               "varIbSort", label='"Sort issues"',
                               onchange="Set(varIbSort, Self.Selected.Value)")
    drp_sort.props["Width"] = f"If({FLT_OK}, {SORT_W}, {TB_W})"
    pair_w = f"If({FLT_OK}, (({TB_W}) - {SORT_W + 2 * TB_GAP}) / 2, {TB_W})"
    for c in (drp_app, drp_sec, drp_status, drp_pri):
        c.props["Width"] = f"(({pair_w}) - 8) / 2"
        c.props["LayoutMinWidth"] = c.props["Width"]
    pair_a = group("conIbFltPairA", [drp_app, drp_sec], direction="Horizontal", gap=8,
                   height=TB_LINE_H, align_items="Center", width=pair_w)
    pair_b = group("conIbFltPairB", [drp_status, drp_pri], direction="Horizontal", gap=8,
                   height=TB_LINE_H, align_items="Center", width=pair_w)
    filters = flow_row("conIbTbFilters", [pair_a, pair_b, drp_sort], TB_W, gap=TB_GAP, ok=FLT_OK)
    return [top, filters]


# ---------------------------------------------------------------------------
# Oversigten: en liste/tabel som Masterdata Hub (issue #229)
# ---------------------------------------------------------------------------
# Fliserne (issue #177, #212) er erstattet af raekker: fra Desktop en tabel
# med kolonneoverskrifter, der flugter med raekkerne; under Desktop en
# kompakt raekke paa tre linjer (som hubbens). Hele raekken aabner sagen i
# View mode (build_helpers.row_hit - hover, tryk og fokus som i hubben).
NO_W = 96
TBL_ROW_H = 48       # tabelraekken (Desktop og op)
CMP_ROW_H = 92       # den kompakte raekke (under Desktop)
ROW_PAD = 10         # raekkens luft til venstre og hoejre
COL_GAP = 8
ACT_BTN = 40         # papirclipsen (issue #193) - kolonnen ACTIONS (raekken under Desktop)
ACT_W = 52           # kolonnen ACTIONS i tabellen - plads til ikonet og overskriften

# (noegle, overskrift, mindstebredde, vaegt, kun Wide). Raekkefoelgen er
# issue #244's: Ticket ID | Requester | Title | Application | Section |
# Priority | Status | Assigned to | Reported | Updated | Actions.
#
# Den frie bredde deles efter vaegtene, saa tabellen fylder hele kortet.
# Issue #244: titlen fik 4 af 6 dele og blev ~950 px bred paa en bred
# skaerm, mens resten stod klemt til hoejre. Nu deles den paa tekst-
# kolonnerne (titel 3, Application/Section/Assigned to 2, Requester og
# datoerne 1); maerkerne (Ticket ID, Priority, Status) og handlingen har
# fast bredde, saa de aldrig klippes og aldrig vokser. Section, Assigned to
# og Reported vises kun paa en bred skaerm (Wide); paa Desktop staar de i
# popuppen, og under Desktop er raekken et kompakt kort.
LIST_COLS = [
    ("ID", "TICKET ID", 88, 0, False),
    ("REQ", "REQUESTER", 64, 1, False),
    ("TITLE", "TITLE", 140, 3, False),
    ("APP", "APPLICATION", 100, 2, False),
    ("SECTION", "SECTION", 104, 2, True),
    ("PRI", "PRIORITY", 72, 0, False),
    ("STATUS", "STATUS", 116, 0, False),
    ("ASG", "ASSIGNED TO", 92, 2, True),
    ("REP", "REPORTED", 84, 1, True),
    ("UPD", "UPDATED", 84, 1, False),
    ("ACT", "ACTIONS", ACT_W, 0, False),
]
WIDE = at_least("Wide")
TABLE_ON = at_least("Desktop")


def _fixed(wide):
    cols = [c for c in LIST_COLS if wide or not c[4]]
    return sum(c[2] for c in cols) + COL_GAP * (len(cols) - 1) + 2 * ROW_PAD


def _units(wide):
    return sum(c[3] for c in LIST_COLS if wide or not c[4])


# Bredden, raekken har: kortets indre bredde minus kant, galleriets
# scrollbar og GALLERY_RESERVE - den samme nedre graense som hubben
# (build_hub.AVAIL). Summen af kolonnerne er aldrig mere end den.
LIST_AVAIL = f"({SHELL_W} - {2 * lay.CARD_PAD} - 4 - {lay.SCROLLBAR_W} - {lay.GALLERY_RESERVE})"
LIST_FREE = f"Max(0, {LIST_AVAIL} - If({WIDE}, {_fixed(True)}, {_fixed(False)}))"
LIST_UNIT = f"({LIST_FREE} / If({WIDE}, {_units(True)}, {_units(False)}))"
COL_W = {k: (str(base) if grow == 0 else f"({base} + {grow} * {LIST_UNIT})")
         for k, _h, base, grow, _w in LIST_COLS}
if _fixed(False) > 1024 - lay.NAV_W - lay.SHELL_INSET - 2 * lay.CARD_PAD - 4 - lay.SCROLLBAR_W - lay.GALLERY_RESERVE:
    raise SystemExit("ib_parts: tabellens kolonner er bredere end Desktop-skaermen")

OPEN_ROW = open_ticket("ThisItem", "false")
# Papirclipsen (issue #193): sagen aabnes direkte paa fanen Attachments,
# hvor filerne vises og nye laegges paa.
OPEN_ROW_FILES = open_ticket("ThisItem", "false", tab="files")
# Kun rapportoeren og admins kan laegge filer paa - flowet tjekker det igen.
ROW_CAN_ATTACH = f"!ThisItem.Archived && (ThisItem.Reporter = varIbMe || {IS_ADMIN})"

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
# "Updated" kun efter en reel aendring - samme regel som popuppen uden
# Activity (UPDATED_AFTER_MIN).
ROW_UPDATED = f"DateDiff(ThisItem.CreatedOn, ThisItem.UpdatedOn, TimeUnit.Minutes) >= {UPDATED_AFTER_MIN}"
PRIORITY_TONE = {"Urgent": "error", "High": "warn", "Normal": "neutral", "Low": "neutral"}
PRI_W = 72


def _priority_tokens(expr):
    def sw(part):
        body = ", ".join(f'"{p}", {_t("state-" + PRIORITY_TONE[p] + "-" + part)}'
                         for p, _r in cfg.PRIORITY)
        return f"Switch({expr}, {body}, {_t('state-neutral-' + part)})"
    return sw("fg"), sw("bg")


def _pri_badge(name, expr, width=PRI_W, visible=None):
    """Prioriteten som maerke - tekst OG farve. I tabellen er cellen altid
    synlig (en skjult celle ville flytte de naeste kolonner); uden
    prioritet staar en streg uden flade."""
    pfg, pbg = _priority_tokens(expr)
    extra = {"VerticalAlign": "VerticalAlign.Middle", **lay.radius(12)}
    if visible is None:
        return text_ctrl(name, f'If(IsBlank({expr}), "-", {expr})', size=lay.SIZE_MICRO,
                         weight="Semibold", height=CHIP_H, width=width, align="Center",
                         color=f"If(IsBlank({expr}), {C_MUTED}, {pfg})",
                         fill=f"If(IsBlank({expr}), {C_TRANSPARENT}, {pbg})",
                         accessible='"Priority: " & Self.Text', extra=extra)
    return text_ctrl(name, expr, size=lay.SIZE_MICRO, weight="Semibold", height=CHIP_H,
                     width=width, align="Center", color=pfg, fill=pbg,
                     accessible='"Priority: " & Self.Text',
                     visible=f"({visible}) && !IsBlank({expr})", extra=extra)


def _no_badge(name, expr, width=NO_W):
    """Sagsnummeret som kompakt maerke."""
    return text_ctrl(name, expr, size=lay.SIZE_SMALL, weight="Semibold", color=C_PRIMARY,
                     height=CHIP_H, width=width, align="Center", fill=C_MUTED_BG,
                     accessible='"Ticket " & Self.Text',
                     extra={"VerticalAlign": "VerticalAlign.Middle", **lay.radius(12)})


# Hvem (issue #212): rapportoeren som kort bruger-id - delen foer @ med
# store bogstaver (uffes@orsted.com -> UFFES), samme metode som MyUserId
# (tools/permissions.py) og initialerne i Activity. Aldrig hele mailen.
def requester(r):
    return f'If(IsBlank({r}.Reporter), "-", {_initials(r + ".Reporter")})'


REPORTER_FX = requester("{r}")


def _attach_btn(name, visible, width=ACT_BTN):
    b = button(name, '"Attach files"', OPEN_ROW_FILES, width=width, height=32, icon="Attach",
               visible=visible, accessible='"Add screenshots or files to " & ThisItem.TicketNo',
               tooltip='"Add screenshots or files"')
    b.props["Layout"] = "ButtonLayout.IconOnly"
    b.props["BorderColor"] = C_TRANSPARENT
    # Oven paa raekkens klikflade - klikket er knappens eget (gen_screen).
    b.props["_OnTop"] = "true"
    return b


def _table_row():
    """Tabelraekken (Desktop og op) - een celle pr. kolonne i LIST_COLS."""
    def txt(name, key, expr, **kw):
        kw.setdefault("size", lay.SIZE_BODY)
        return text_ctrl(name, expr, height=20, width=COL_W[key], wrap="false", **kw)

    cells = {
        "ID": _no_badge("txtIbRowNo", "ThisItem.TicketNo", width=COL_W["ID"]),
        # Kun titlen, paa een linje - en lang titel afkortes med ellipse.
        "TITLE": txt("txtIbRowTitle", "TITLE", "ThisItem.Title", weight="Semibold",
                     accessible='"Title: " & ThisItem.Title'),
        "APP": txt("txtIbRowApp", "APP", "ThisItem.Application",
                   accessible='"Application: " & Self.Text'),
        "SECTION": txt("txtIbRowSection", "SECTION", "ThisItem.Section", color=C_MUTED,
                       accessible='"Section: " & Self.Text'),
        "REQ": txt("txtIbRowReq", "REQ", requester("ThisItem"),
                   accessible='"Requester: " & Self.Text'),
        "PRI": _pri_badge("txtIbRowPriority", "ThisItem.Priority", width=COL_W["PRI"]),
        "STATUS": _chip("txtIbRowStatus", "ThisItem.Status", "ThisItem.Archived",
                        width=COL_W["STATUS"]),
        "ASG": txt("txtIbRowAssigned", "ASG",
                   'If(IsBlank(ThisItem.Assigned), "Unassigned", ThisItem.Assigned)',
                   size=lay.SIZE_SMALL,
                   color=f"If(IsBlank(ThisItem.Assigned), {C_MUTED}, {C_TITLE})",
                   accessible='"Assigned to: " & Self.Text'),
        "REP": txt("txtIbRowReported", "REP", f"Text(ThisItem.CreatedOn, {DATE_FMT})",
                   size=lay.SIZE_SMALL, color=C_MUTED, accessible='"Reported: " & Self.Text'),
        "UPD": txt("txtIbRowUpdated", "UPD",
                   f'If({ROW_UPDATED}, Text(ThisItem.UpdatedOn, {DATE_FMT}), "-")',
                   size=lay.SIZE_SMALL, color=C_MUTED, accessible='"Updated: " & Self.Text'),
        "ACT": _attach_btn("btnIbRowAttach", f"{TABLE_ON} && {ROW_CAN_ATTACH}", width=COL_W["ACT"]),
    }
    kids = []
    for key, _h, _b, _g, wide_only in LIST_COLS:
        c = cells[key]
        if wide_only:
            c.props["Visible"] = WIDE
            c.vis = WIDE
        kids.append(c)
    return group("conIbRow", kids, direction="Horizontal", gap=COL_GAP,
                 height="Parent.TemplateHeight - 1", align_items="Center",
                 width="Parent.TemplateWidth", pad=(0, ROW_PAD, 0, ROW_PAD), visible=TABLE_ON)


def _list_head():
    """Kolonneoverskrifterne - samme bredder som raekken (check_layout 29)."""
    kids = []
    for i, (key, head, _b, _g, wide_only) in enumerate(LIST_COLS):
        h = text_ctrl(f"txtIbListH{i}", f'"{head}"', size=lay.SIZE_MICRO, weight="Semibold",
                      color=C_MUTED, height=20, wrap="false", width=COL_W[key],
                      accessible=f'"{head.capitalize()} column"',
                      visible=WIDE if wide_only else None)
        kids.append(h)
    return group("conIbListHead", kids, direction="Horizontal", gap=COL_GAP, height=20,
                 align_items="Center", pad=(0, ROW_PAD, 0, ROW_PAD), visible=TABLE_ON)


def _compact_row():
    """Under Desktop: nummer, prioritet og status; titlen; hvem og hvor
    (rapportoeren foerst - samme raekkefoelge som tabellen, issue #244)."""
    no = _no_badge("txtIbRowNoC", "ThisItem.TicketNo")
    pri = _pri_badge("txtIbRowPriorityC", "ThisItem.Priority", visible=at_least("Tablet"))
    gap = grow(group("conIbRowGapC", [], direction="Horizontal", height=0))
    chip = _chip("txtIbRowStatusC", "ThisItem.Status", "ThisItem.Archived")
    line1 = group("conIbRowLineC1", [no, pri, gap, chip], direction="Horizontal", gap=8,
                  height=CHIP_H, align_items="Center")
    title = text_ctrl("txtIbRowTitleC", "ThisItem.Title", size=lay.SIZE_INPUT, weight="Semibold",
                      height=21, wrap="false", accessible='"Title: " & ThisItem.Title')
    meta_fx = (f'{requester("ThisItem")} & "  ·  " & ThisItem.Application & "  ·  " & ThisItem.Section & '
               f'If({below("Tablet")} && !IsBlank(ThisItem.Priority), "  ·  " & ThisItem.Priority, "") & '
               f'If({ROW_UPDATED}, "  ·  Updated " & Text(ThisItem.UpdatedOn, {DATE_FMT}), '
               f'"  ·  Reported " & Text(ThisItem.CreatedOn, {DATE_FMT}))')
    meta = grow(text_ctrl("txtIbRowMetaC", meta_fx, size=lay.SIZE_SMALL, color=C_MUTED,
                          height=18, wrap="false"))
    # Plads til papirclipsen til hoejre (den ligger oven paa raekken).
    room = group("conIbRowAttRoomC", [], direction="Horizontal", height=0, width=ACT_BTN + 4)
    line3 = group("conIbRowLineC3", [meta, room], direction="Horizontal", gap=8, height=18,
                  align_items="Center")
    return group("conIbRowC", [line1, title, line3], direction="Vertical", gap=4,
                 height="Parent.TemplateHeight - 1", width="Parent.TemplateWidth",
                 pad=(10, 12, 10, 12), visible=below("Desktop"))


def build_list():
    """Listekortet: vaerktoejslinjens to raekker, taelleren, overskrifterne
    og raekkerne.

    Galleriet er aldrig hoejere end pladsen, der er TILBAGE under bjaelken,
    vaerktoejslinjen og kortets egne linjer - kun galleriet scroller (issue
    #229: foer var kroppens indhold hoejere end kroppen). Hvorfor
    vaerktoejslinjen stadig ikke kunne ses, og hvordan den er bygget nu,
    staar over build_filters (issue #244)."""
    toolbar = build_filters()
    row = _table_row()
    crow = _compact_row()
    rule = row_rule("rctIbRowRule", TBL_ROW_H)
    rule.props["Y"] = "Parent.TemplateHeight - 1"
    hit = row_hit("btnIbRowOpen", OPEN_ROW,
                  '"Open " & ThisItem.TicketNo & " - " & ThisItem.Title & ", " & '
                  'If(ThisItem.Archived, "Archived", ThisItem.Status)',
                  "Parent.TemplateWidth", "Parent.TemplateHeight - 1")
    att_c = _attach_btn("btnIbRowAttachC", f"{below('Desktop')} && {ROW_CAN_ATTACH}")
    att_c.props["X"] = f"Parent.TemplateWidth - 12 - {ACT_BTN}"
    att_c.props["Y"] = str(CMP_ROW_H - 1 - 10 - 32 + 7)
    att_c.props.pop("_OnTop")

    row_h = if_below("Desktop", str(CMP_ROW_H), str(TBL_ROW_H))
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
    head = _list_head()
    head_rule = group("conIbListRule", [], direction="Horizontal", height=1, fill=C_DIVIDER,
                      visible=TABLE_ON)
    empty_fx = (
        'If(varIbLoading, "Loading issues...", '
        "IbFailed, \"The issues could not be loaded. Check your connection and try again.\", "
        'varIbScope = "mine" && IsEmpty(IbMine), '
        '"You have not reported any issues yet. Use New issue to report one.", '
        'varIbScope = "all" && IsEmpty(colIbAll), "No issues have been reported yet.", '
        'varIbScope = "assigned" && IsEmpty(Filter(colIbAll, AssignedEmail = varIbMe)), '
        '"No issues are assigned to you.", '
        f'{FILTERED}, "No issues match the filters. Clear the filters to see more.", '
        'Switch(varIbState, "closed", "There are no closed issues here.", "archived", '
        '"There are no archived issues here.", "There are no open issues here."))')
    empty = text_ctrl("txtIbEmpty", empty_fx, size=lay.SIZE_BODY, height=40, wrap="true",
                      color=f"If(IbFailed, {C_INVALID_FG}, {C_MUTED})",
                      visible="galIbList.AllItemsCount = 0")
    retry = button("btnIbRetry", '"Retry"', RETRY, width=fit_button_width('"Retry"'), height=36,
                   visible="IbFailed && !varIbLoading", accessible='"Load the issues again"')
    retry.props["AlignInContainer"] = "AlignInContainer.Start"

    # Pladsen, galleriet har: skaermen minus mobilbjaelken, sidens bjaelke,
    # kroppens luft, kortets polstring og kant og kortets andre linjer.
    before = [*toolbar, count_row, counts, head, head_rule]
    bar = build_bar()
    header_h = f"{lay.HEADER_PAD_T} + ({bar.h}) + {lay.HEADER_PAD_B} + 1"
    room = (f"App.Height - {lay.BAR_OFFSET} - ({header_h}) - {lay.BODY_PAD_T} - {lay.BODY_PAD_B} - "
            f"{2 * 18} - 2 - ({stack_height(before, 8)}) - 8")
    # Saa hoej som raekkerne - hoejst pladsen (dog mindst tre raekker).
    gal_h = f"Min(galIbList.AllItemsCount * ({row_h}), Max(3 * ({row_h}), {room}))"
    gal = Ctrl("galIbList", "Gallery", variant="Vertical", props={
        "AccessibleLabel": '"Issues"',
        "BorderStyle": "BorderStyle.None", "Fill": C_CARD_BG, "FillPortions": "0",
        "Height": gal_h, "Items": LIST_ITEMS, "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None", "Selectable": "false",
        "ShowScrollbar": "true", "TabIndex": "0", "TemplatePadding": "0",
        "TemplateSize": row_h, "Width": "Parent.Width", "WrapCount": "1",
    }, children=[row, crow, rule, hit, att_c], h=gal_h, vis="galIbList.AllItemsCount > 0")
    return card("conIbListCard", before + [gal, empty, retry], gap=8)


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


def _popup(prefix, kids, vis, width=POP_W, foot=None, own_scroll=False):
    """Popuppen holder sig inden for skaermen (issue #177): hovedet (titel
    og Close) og en eventuel fod staar fast; kun indholdet imellem scroller,
    og kun naar det ikke kan staa. Close kan altid naas.

    kids[0] er hovedet; resten er indholdet. own_scroll: indholdet styrer
    selv sin hoejde og sin scrolling (sagens popup, issue #212) - saa
    pakkes det ikke i en scrollende krop."""
    head, rest = kids[0], list(kids[1:])
    if own_scroll:
        parts = [head] + rest + ([foot] if foot is not None else [])
    else:
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


def _head(prefix, title_fx, close_fx, lead=(), title_w=None, close_icon=False):
    """Titel og Close. title_w: titlens bredde - saa ombrydes en lang titel
    paa op til tre linjer i stedet for at blive klippet. close_icon: Close
    som ikon (Dismiss) oeverst til hoejre - sagens popup (issue #229)."""
    h = 26
    if title_w is not None:
        h = f"Min(3 * 23 + 2, Max(26, {_lines_h(title_fx, title_w, px=9.2, line_h=23)}))"
    title = grow(text_ctrl(f"txt{prefix}Title", title_fx, size=lay.SIZE_CARD_TITLE,
                           weight="Semibold", height=h, wrap="true" if title_w else "false"))
    close = button(f"btn{prefix}Close", '"Close"', close_fx,
                   width=fit_button_width('"Close"'), height=32,
                   accessible='"Close"')
    if close_icon:
        close.props["Width"] = "34"
        close.props["Height"] = "34"
        close.h = 34
        close.props["Icon"] = '"Dismiss"'
        close.props["Layout"] = "ButtonLayout.IconOnly"
        close.props["Tooltip"] = '"Close"'
        close.props["BorderColor"] = C_TRANSPARENT
        close.props["AlignInContainer"] = "AlignInContainer.Start"
    close.props["LayoutMinWidth"] = close.props["Width"]
    hmin = 34 if close_icon else 32
    return group(f"con{prefix}Head", [*lead, title, close], direction="Horizontal", gap=10,
                 height=hmin if title_w is None else f"Max({hmin}, {h})", align_items="Center")


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

# Den nye sag ind i listen - Patch gav raekken tilbage, saa der er intet
# opslag og ingen ny hentning af listen (issue #177, #193).
ADD_NEW = (
    "Set(varIbSelId, varIbNewRow.ID);\n"
    f"Set(varIbNew, {_row('varIbNewRow')});\n"
    "RemoveIf(colIbAll, Id = varIbSelId);\n"
    "Collect(colIbAll, varIbNew)"
)

# Den nye sag i View mode - som et tryk paa flisen, og raekken er hel.
SHOW_NEW = (
    "Set(varIbSel, varIbNew);\n"
    "Set(varIbSelPeek, false);\n"
    "Set(varIbSelFullFor, varIbSelId);\n"
    'Set(varIbTab, "details");\n'
    "Set(varIbInternal, false);\n"
    "Set(varIbFilesFor, -1);\n"
    "Reset(inpIbComment);\n"
    + LOAD_ACTIVITY + ";\n"
    "Set(varIbDetailOn, true)"
)
UP_FAILED_TEXT = f'Concat({UP_FAILED}, Name & " (" & Msg & ")", "; ")'

# Ny sag (issue #193): appen opretter raekken selv med Patch - ikke
# gennem flowet. Nummeret, rapportoeren (ud fra Created By) og
# starttilstanden saettes igen paa serveren af flowet
# BioSap-IssueBoard-OnCreated, der ogsaa sender mailen til admins og
# rapportoeren. Filer laegges paa bagefter (papirclipsen paa flisen).
NEW_FIELDS = (
    "        Title: Trim(inpIbTitle.Text),\n"
    "        Description: Trim(inpIbDesc.Text),\n"
    "        ReproSteps: Trim(inpIbSteps.Text),\n"
    "        ExpectedResult: Trim(inpIbExpected.Text),\n"
    "        ActualResult: Trim(inpIbActual.Text),\n"
    "        Application: varIbFormApp,\n"
    "        Section: varIbFormSection,\n"
    '        OtherContext: If(IbOtherNeeded, Trim(inpIbOther.Text), ""),\n'
    "        RelatedRequestNo: Trim(inpIbRelated.Text),\n"
    f'        Severity: {{ Value: Coalesce(drpIbSeverity.Selected.Value, "{cfg.SEVERITY_DEFAULT}") }},\n'
)
SUBMIT = (
    "Set(varIbBusy, true);\n"
    "Set(varIbSaved, false);\n"
    "IfError(\n"
    "    Set(varIbNewRow, Patch(\n"
    f"        {cfg.L_TICKETS},\n"
    f"        Defaults({cfg.L_TICKETS}),\n"
    "        {\n"
    + NEW_FIELDS.replace("\n        ", "\n            ").replace("        Title", "            Title", 1) +
    f"            LayoutContext: {LAYOUT_FX},\n"
    f"            ClientContext: {CLIENT_FX},\n"
    f'            Priority: {{ Value: "{cfg.PRIORITY_DEFAULT}" }},\n'
    f'            Status: {{ Value: "{cfg.STATUS_NEW}" }},\n'
    "            ReporterEmail: varIbMe,\n"
    "            ReporterName: Left(User().FullName, 255),\n"
    "            LastActivityOn: Now(),\n"
    "            IsArchived: false\n"
    "        }\n"
    "    ));\n"
    "    Set(varIbSaved, true),\n"
    # Fejler det, bliver popuppen staaende med det indtastede (issue #135).
    '    Notify("The issue could not be submitted. " & FirstError.Message, NotificationType.Error)\n'
    ");\n"
    "If(\n"
    "    varIbSaved,\n"
    "    " + ADD_NEW.replace("\n", "\n    ") + ";\n"
    '    Set(varIbScope, "mine");\n'
    '    Set(varIbState, "open");\n'
    # Foerst nu lukkes og nulstilles formularen - sagen findes (issue #135).
    "    Set(varIbFormOn, false);\n"
    "    " + CLEAR_FORM.replace("\n", "\n    ") + ";\n"
    # Den nye sag vises med det samme - et aktivt filter eller en soegning
    # kan ikke skjule den.
    "    " + SHOW_NEW.replace("\n", "\n    ") + ";\n"
    '    Notify("Thank you. Issue " & varIbNew.TicketNo & " has been submitted. To add screenshots '
    'or files, select Attachments here or the paperclip on the issue.", NotificationType.Success)\n'
    ");\n"
    "Set(varIbBusy, false)"
)

# Edit (issue #193): appen retter sagen selv med Patch - rapportoeren
# felterne, mens sagen er New; en admin desuden status, prioritet,
# tildeling og loesning. Raekken hentes foerst (varIbCur), saa en admins
# aendring imens ikke overskrives, og saa reglerne tjekkes paa det, der
# staar i SharePoint nu. Bagefter faar flowet vaerdierne FOER (prev): det
# sammenligner med raekken, som den staar nu, skriver een haendelse pr.
# aendring i Activity og sender mailen ved Ready for retest/Closed.
ASG_EMAIL = 'Lower(Coalesce(drpIbAssignee.Selected.Email, ""))'
SAVE_EDIT = (
    "Set(varIbBusy, true);\n"
    "Set(varIbSaved, false);\n"
    f"Set(varIbCur, IfError(LookUp({cfg.L_TICKETS}, ID = varIbSelId), Blank()));\n"
    "If(\n"
    "    IsBlank(varIbCur),\n"
    '    Notify("The issue could not be loaded. It may have been deleted - close it and try again.", '
    "NotificationType.Error),\n"
    f'    !{IS_ADMIN} && (varIbCur.Status.Value <> "{cfg.STATUS_EDITABLE}" || Coalesce(varIbCur.IsArchived, false)),\n'
    '    Notify("You can edit your issue only while it is New. Add a comment instead.", '
    "NotificationType.Warning),\n"
    "    IfError(\n"
    "        Set(varIbEdited, Patch(\n"
    f"            {cfg.L_TICKETS},\n"
    "            varIbCur,\n"
    "            {\n"
    + NEW_FIELDS.replace("        ", "                ") +
    f"                Status: {{ Value: If({IS_ADMIN}, Coalesce(drpIbStatus.Selected.Value, varIbCur.Status.Value), "
    "varIbCur.Status.Value) },\n"
    f"                Priority: {{ Value: If({IS_ADMIN}, Coalesce(drpIbPriority.Selected.Value, "
    f'varIbCur.Priority.Value, "{cfg.PRIORITY_DEFAULT}"), Coalesce(varIbCur.Priority.Value, '
    f'"{cfg.PRIORITY_DEFAULT}")) }},\n'
    f"                AssignedToEmail: If({IS_ADMIN}, {ASG_EMAIL}, varIbCur.AssignedToEmail),\n"
    f'                AssignedToName: If({IS_ADMIN}, If(IsBlank({ASG_EMAIL}), "", '
    f"{_initials(ASG_EMAIL)}), varIbCur.AssignedToName),\n"
    f"                Resolution: If({IS_ADMIN}, Trim(inpIbResolution.Text), varIbCur.Resolution),\n"
    "                LastActivityOn: Now()\n"
    "            }\n"
    "        ));\n"
    "        Set(varIbSaved, true),\n"
    '        Notify("The changes could not be saved. " & FirstError.Message, NotificationType.Error)\n'
    "    )\n"
    ");\n"
    "If(\n"
    "    varIbSaved,\n"
    f"    Set(varIbRes, IfError({cfg.FLOW}.Run(\n"
    f'        "{cfg.ACT_EDIT}",\n'
    "        JSON({\n"
    "            ticketId: varIbSelId,\n"
    "            prev: {\n"
    '                title: Coalesce(varIbCur.Title, ""),\n'
    '                description: Coalesce(varIbCur.Description, ""),\n'
    '                steps: Coalesce(varIbCur.ReproSteps, ""),\n'
    '                expected: Coalesce(varIbCur.ExpectedResult, ""),\n'
    '                actual: Coalesce(varIbCur.ActualResult, ""),\n'
    '                application: Coalesce(varIbCur.Application, ""),\n'
    '                section: Coalesce(varIbCur.Section, ""),\n'
    '                other: Coalesce(varIbCur.OtherContext, ""),\n'
    '                relatedNo: Coalesce(varIbCur.RelatedRequestNo, ""),\n'
    '                severity: Coalesce(varIbCur.Severity.Value, ""),\n'
    f'                status: Coalesce(varIbCur.Status.Value, "{cfg.STATUS_NEW}"),\n'
    f'                priority: Coalesce(varIbCur.Priority.Value, "{cfg.PRIORITY_DEFAULT}"),\n'
    '                assignee: Lower(Coalesce(varIbCur.AssignedToEmail, "")),\n'
    '                resolution: Coalesce(varIbCur.Resolution, "")\n'
    "            }\n"
    "        })\n"
    f"    ), {FALLBACK}));\n"
    f"    Set(varIbSel, {_row('varIbEdited')});\n"
    "    Set(varIbSelFullFor, varIbSelId);\n"
    "    UpdateIf(colIbAll, Id = varIbSelId, varIbSel);\n"
    "    " + LOAD_ACTIVITY.replace("\n", "\n    ") + ";\n"
    "    Set(varIbFormOn, false);\n"
    "    Set(varIbDetailOn, true);\n"
    "    If(\n"
    '        varIbRes.ok = "yes",\n'
    '        Notify("Your changes have been saved.", NotificationType.Success),\n'
    '        Notify("Your changes have been saved, but they could not be added to the activity. " & '
    "Coalesce(varIbRes.message, \"\"), NotificationType.Warning)\n"
    "    )\n"
    ");\n"
    "Set(varIbBusy, false)"
)

SIMILAR_ITEMS = (
    "With(\n"
    '    { w: Filter(ForAll(Split(Trim(inpIbTitle.Text), " ") As s, { Word: s.Value }), Len(Word) >= 4) },\n'
    "    FirstN(\n"
    "        SortByColumns(\n"
    "            Filter(\n"
    # Alle har alle sager i colIbAll (issue #193).
    "                ForAll(Filter(colIbAll, !Archived) As S,\n"
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
    f'    Coalesce(drpIbSeverity.Selected.Value, "{cfg.SEVERITY_DEFAULT}") <> "{cfg.SEVERITY_DEFAULT}"\n'
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
                      '"Tell us what happened. Fields marked * are required. Everyone can see the '
                      'issue and your name; only you and the administrators can see the comments. '
                      'Add screenshots and files after you submit.")',
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

    # Lignende sager - fra alle sager (issue #193).
    sim_head = text_ctrl("txtIbSimHead", '"Similar issues - is yours already reported?"',
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
    # Kun laesning: formularen er aaben bagved, og intet herfra maa kunne
    # aendre en sag (Edit ville overskrive formularen).
    s_hit = row_hit("btnIbSimOpen", open_ticket("ThisItem.Row", "true"),
                    '"Open similar issue " & ThisItem.TicketNo & " - " & ThisItem.Title',
                    tw, SIM_ROW_H - 2, radius=8)
    sim_h = f"galIbSimilar.AllItemsCount * {SIM_ROW_H}"
    sim = Ctrl("galIbSimilar", "Gallery", variant="Vertical", props={
        "AccessibleLabel": '"Similar issues"',
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

    # Skaermbilleder og filer laegges paa EFTER oprettelsen (issue #193):
    # papirclipsen paa flisen eller fanen Attachments.

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
                     placeholder='"What was done - shown to everyone with the issue"',
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
    missing_text = f'If({EDITING}, "To save, add ", "To submit, add ") & {MISSING_FX} & "."'
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
            manage, context]
    # Foden staar fast under det, der scroller: Submit kan altid naas.
    return [_popup("IbForm", kids, FORM_ON, width=FORM_W, foot=foot), *build_discard()]


# ---------------------------------------------------------------------------
# En sag i View mode
# ---------------------------------------------------------------------------
DETAIL_ON = "IfError(varIbDetailOn, false)"
SEL = "varIbSel"
DET_IN = f"({POP_IN} - {lay.SCROLLBAR_W})"
ACT_ROW_PAD = 12
ACT_W = f"({DET_IN} - {lay.SCROLLBAR_W} - {lay.GALLERY_RESERVE})"
ACT_BODY_W = f"({ACT_W} - {2 * ACT_ROW_PAD})"
# Indholdsfladen i sagens popup: mindst saa hoej, naar skaermen tillader det -
# og aldrig lavere end DET_SAFE_MIN_H (issue #212).
DET_MIN_H = 360
DET_SAFE_MIN_H = 160

# Efter enhver aendring gennem flowet (issue #229 - live): KUN den ene
# sag (LookUp paa ID, skrevet ind i listen med UpdateIf) og dens Activity
# - ingen ny hentning af listen. Filtre, sortering, den aabne sag og den
# valgte fane bliver staaende. Activity kun for rapportoeren og admins.
AFTER_CHANGE = RELOAD_SEL + ";\nIf(IbSeeActivity,\n" + LOAD_ACTIVITY + "\n)"


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


# Kommentar og intern note (issue #212): flowet svarer foerst, naar
# raekken er skrevet. Saa saettes den samme raekke ind sidst i feeden - den
# nyeste, altsaa i den rigtige raekkefoelge - uden at hente hele Activity
# igen: intet blink, intet ekstra kald. Rollen er flowets egen regel (Admin,
# naar en admin skriver paa en andens sag). Feltet toemmes foerst nu;
# fejler kaldet, staar teksten der stadig.
POST_ROW = (
    '{ Kind: "Comment", Actor: "You", '
    f'Role: If({IS_ADMIN} && !IbSelMine, "Admin", "User"), '
    "Body: Trim(inpIbComment.Text), At: Now(), "
    f"Internal: varIbInternal && {IS_ADMIN}, IsSystem: false, "
    'File: "", SizeKb: 0, Initial: false }'
)
POST = _run(
    cfg.ACT_COMMENT,
    f"{{ ticketId: varIbSelId, content: Trim(inpIbComment.Text), internal: varIbInternal && {IS_ADMIN} }}",
    f"Collect(colIbActivity, {POST_ROW});\n"
    "Reset(inpIbComment);\n"
    "UpdateIf(colIbAll, Id = varIbSelId, { UpdatedOn: Now() });\n"
    "Set(varIbSel, Patch(varIbSel, { UpdatedOn: Now() }));\n"
    'Notify(If(varIbInternal, "Internal note added.", "Comment posted."), NotificationType.Success);\n'
    "Set(varIbInternal, false);\n"
    "Reset(chkIbInternal)",
    "The comment could not be posted.", busy="varIbPosting")

REOPEN = _run(
    cfg.ACT_REOPEN, '{ ticketId: varIbSelId, reason: "" }',
    AFTER_CHANGE + ";\n"
    # Filtrene roeres ikke (issue #229) - raekken er opdateret i listen.
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
    "RemoveIf(colIbAll, Id = varIbSelId);\n"
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


TAB_W = 140
TAB_H = 32


def _tab(name, label_fx, key, accessible, onselect=None):
    """En fane i popuppens navigation - samme kontakt som filtrenes (_seg):
    valgt = fyldt i primaerfarven, ellers kant (issue #229)."""
    b = _seg(name, label_fx, f'varIbTab = "{key}"', onselect or f'Set(varIbTab, "{key}")',
             TAB_W, accessible)
    b.props["Text"] = label_fx
    b.props["Height"] = str(TAB_H)
    b.h = TAB_H
    b.props["LayoutMinWidth"] = "0"
    return b


ICON_BTN = 34


def _icon_action(name, icon, onselect, visible, label, tooltip, display_mode, danger=False):
    """En handling paa sagen som ikon (issue #229): kun ikonet, engelsk
    tooltip og etiket, ingen kant - deaktiveret er den graa, ikke indrammet."""
    b = button(name, label, onselect, width=ICON_BTN, height=ICON_BTN, icon=icon,
               visible=visible, accessible=label, tooltip=tooltip, display_mode=display_mode,
               danger=danger)
    b.props["Layout"] = "ButtonLayout.IconOnly"
    b.props["BorderColor"] = C_TRANSPARENT
    b.props["LayoutMinWidth"] = str(ICON_BTN)
    return b


# Handlingsraekken vises, naar mindst een af handlingerne er tilladt.
CAN_ACT = "IbCanReopen || IbCanEdit || IbCanManage"


def _actions():
    """Handlingerne paa den aabne sag - hver kun, naar brugeren maa (de
    navngivne formler IbCan*). Issue #229: ingen overloebsmenu (More
    actions) laengere. Edit (blyant), Archive (arkivkassen; Restore er en
    pil tilbage) og Delete (skraldespanden) staar direkte som ikoner i een
    kompakt raekke lige under fakta - Delete sidst, i fare-farven og med
    sin egen bekraeftelse. Reopen er en arbejdsgang for rapportoeren og
    staar som tekstknap forrest."""
    reopen = button("btnIbReopen", '"Reopen"', REOPEN, width=fit_button_width('"Reopen"'),
                    height=ICON_BTN, visible="IbCanReopen",
                    accessible='"Reopen this issue - the problem is still there"',
                    display_mode="If(varIbBusy, DisplayMode.Disabled, DisplayMode.Edit)")
    reopen.props["LayoutMinWidth"] = reopen.props["Width"]
    reopen.props["Size"] = str(lay.SIZE_SMALL)
    # Edit foerst, naar sagens hele raekke er hentet - ellers kunne de
    # felter, oversigten ikke henter, blive gemt tomme.
    ready = "varIbSelFullFor = varIbSelId"
    edit = _icon_action("btnIbEdit", "Edit", OPEN_EDIT, "IbCanEdit", '"Edit issue"',
                        f'If({ready}, "Edit issue", "Edit issue - loading the issue...")',
                        f"If({ready} && !varIbBusy, DisplayMode.Edit, DisplayMode.Disabled)")
    archive = _icon_action(
        "btnIbArchive", f'If({SEL}.Archived, "ArrowUndo", "Archive")', ARCHIVE, "IbCanManage",
        f'If({SEL}.Archived, "Restore issue", "Archive issue")',
        f'If({SEL}.Archived, "Restore issue - bring it back to the active lists", '
        '"Archive issue - keeps the issue, its comments, activity and files under Archived")',
        "If(varIbBusy, DisplayMode.Disabled, DisplayMode.Edit)")
    delete = _icon_action("btnIbDelete", "Delete", "Reset(inpIbDelConfirm);\nSet(varIbDelOn, true)",
                          "IbCanManage", '"Delete issue"',
                          '"Delete issue permanently - you confirm first"',
                          "If(varIbBusy, DisplayMode.Disabled, DisplayMode.Edit)", danger=True)
    delete.props["BorderColor"] = C_TRANSPARENT
    row = group("conIbDetActions", [reopen, edit, archive, delete], direction="Horizontal",
                gap=4, height=ICON_BTN, align_items="Center", justify="End", visible=CAN_ACT)
    row.props["LayoutJustifyContent"] = (f"If({NARROW}, LayoutJustifyContent.Start, "
                                         "LayoutJustifyContent.End)")
    return row


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
    # Alle filer i fuld hoejde - fanens flade scroller (issue #212).
    gal_h = f"galIbFiles.AllItemsCount * {row_h}"
    gal = Ctrl("galIbFiles", "Gallery", variant="Vertical", props={
        "AccessibleLabel": '"Attachments"',
        "BorderStyle": "BorderStyle.None", "Fill": C_TRANSPARENT, "FillPortions": "0",
        "Height": gal_h, "Items": files_items, "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None", "Selectable": "false",
        "ShowScrollbar": "false", "TabIndex": "0", "TemplatePadding": "0",
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
                     f'"Up to {cfg.MAX_FILES} files at a time, {cfg.MAX_FILE_MB} MB each. Everyone '
                     'who uses the Issue Board can open the files - leave out personal data."',
                     size=lay.SIZE_SMALL, color=C_MUTED, height=34, wrap="true")
    adder = group("conIbFileAdd", [picker, hint, up], direction="Vertical", gap=8,
                  visible="IbCanAttach")
    return group("conIbDetFiles", [state, gal, adder], direction="Vertical", gap=12,
                 visible='varIbTab = "files"')


FACT_H = 38
FACT_GAP = 12
# Fem fakta paa een linje, naar popuppen er bred nok; ellers tre og to.
FACTS_OK = f"({DET_IN}) >= 600"
FACT_W = f"If({FACTS_OK}, (({DET_IN}) - 4 * {FACT_GAP}) / 5, (({DET_IN}) - 2 * {FACT_GAP}) / 3)"


def _fact(name, label, value_fx, visible=None):
    """Et faktum: en lille etiket over vaerdien - kompakt, ingen lang streng."""
    lab = text_ctrl(f"txt{name}Label", f'"{label}"', size=lay.SIZE_MICRO, weight="Semibold",
                    color=C_MUTED, height=16)
    val = text_ctrl(f"txt{name}", value_fx, size=lay.SIZE_BODY, height=20,
                    accessible=f'"{label}: " & Self.Text')
    g = group(f"con{name}", [lab, val], direction="Vertical", gap=0, height=FACT_H, width=FACT_W,
              visible=visible)
    g.props["LayoutMinWidth"] = "0"
    return g


def _facts():
    """Metadata om sagen som etiket/vaerdi (issue #229): Requester,
    Assigned to, Severity, Reported og Updated. Rapportoeren som kort
    bruger-id (UFFES) - ingen anonymisering (issue #193, #212). Updated
    kun efter en reel aendring, og sidst, saa der ikke opstaar et hul."""
    def blank_as(expr, text):
        return f'If(IsBlank({expr}), "{text}", {expr})'
    rep = _fact("IbFactReporter", "Requester", REPORTER_FX.format(r=SEL))
    asg = _fact("IbFactAssigned", "Assigned to", blank_as(SEL + ".Assigned", "Unassigned"))
    sev = _fact("IbFactSeverity", "Severity", blank_as(f"{SEL}.Severity", "Not set"))
    reported = _fact("IbFactReported", "Reported", f"Text({SEL}.CreatedOn, {DATE_FMT})")
    updated = _fact("IbFactUpdated", "Updated", f"Text(IbSelUpdatedOn, {DATE_FMT})",
                    visible="!IsBlank(IbSelUpdatedOn)")
    a = group("conIbFacts1", [rep, asg, sev], direction="Horizontal", gap=FACT_GAP,
              height=FACT_H, width=f"If({FACTS_OK}, 3 * {FACT_W} + 2 * {FACT_GAP}, {DET_IN})")
    b = group("conIbFacts2", [reported, updated], direction="Horizontal", gap=FACT_GAP,
              height=FACT_H, width=f"If({FACTS_OK}, 2 * {FACT_W} + {FACT_GAP}, {DET_IN})")
    for p in (a, b):
        p.props["LayoutMinWidth"] = "0"
    g = group("conIbDetFacts", [a, b], direction="Horizontal", gap=FACT_GAP,
              height=f"If({FACTS_OK}, {FACT_H}, 2 * {FACT_H} + 8)")
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
    # 1. Sagsnummeret som maerke, titlen og Close (kun ikonet, oeverst til
    #    hoejre - popuppens eneste vej ud).
    no = _no_badge("txtIbDetNo", f"{SEL}.TicketNo")
    no.props["LayoutMinWidth"] = str(NO_W)
    head = _head("IbDet", f"{SEL}.Title", "Set(varIbDetailOn, false)",
                 lead=[no], title_w=f"({POP_IN}) - {NO_W} - {ICON_BTN} - 20", close_icon=True)

    # 2. Status, prioritet, Application og Section - maerker og to korte
    #    vaerdier, ikke en lang streng. Paa en smal popup paa to linjer.
    chip = _chip("txtIbDetStatus", f"{SEL}.Status", f"{SEL}.Archived")
    chip.props["LayoutMinWidth"] = str(CHIP_W)
    pri = _pri_badge("txtIbDetPriority", f"{SEL}.Priority", visible="true")
    pri.props["LayoutMinWidth"] = str(PRI_W)
    badges_w = f"({CHIP_W} + 8 + If(IsBlank({SEL}.Priority), 0, {PRI_W} + 8))"
    badges = group("conIbDetBadges", [chip, pri], direction="Horizontal", gap=8, height=CHIP_H,
                   width=f"({badges_w} - 8)", align_items="Center")
    badges.props["LayoutMinWidth"] = badges.props["Width"]
    where_w = f"If({FACTS_OK}, ({DET_IN}) - {badges_w} - 4, {DET_IN})"
    app = text_ctrl("txtIbDetApp", f"{SEL}.Application", size=lay.SIZE_BODY, weight="Semibold",
                    height=20, width=f"(({where_w}) - 12) / 2",
                    accessible='"Application: " & Self.Text')
    sec = text_ctrl("txtIbDetSection", f"{SEL}.Section", size=lay.SIZE_BODY, color=C_MUTED,
                    height=20, width=f"(({where_w}) - 12) / 2",
                    accessible='"Section: " & Self.Text')
    where = group("conIbDetWhere", [app, sec], direction="Horizontal", gap=12, height=20,
                  width=where_w, align_items="Center")
    where.props["LayoutMinWidth"] = "0"
    meta = group("conIbDetMeta", [badges, where], direction="Horizontal", gap=12,
                 height=f"If({FACTS_OK}, {CHIP_H}, {CHIP_H} + 6 + 20)", align_items="Center")
    meta.props["LayoutDirection"] = (f"If({FACTS_OK}, LayoutDirection.Horizontal, "
                                     "LayoutDirection.Vertical)")
    meta.props["LayoutGap"] = f"If({FACTS_OK}, 12, 6)"
    meta.props["LayoutAlignItems"] = (f"If({FACTS_OK}, LayoutAlignItems.Center, "
                                      "LayoutAlignItems.Start)")

    # 3. Metadata.  4. Handlingerne (ikoner).
    facts = _facts()
    actions = _actions()

    peek_note = text_ctrl("txtIbDetPeek",
                          '"Read only - opened from your new report. Close it to continue '
                          'your report."',
                          size=lay.SIZE_SMALL, color=C_INFO_FG, height=34, wrap="true",
                          visible="varIbSelPeek",
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
        _tab("btnIbTabFiles",
             '"Attachments" & If(IsBlank(IbFileCount), "", " (" & IbFileCount & ")")', "files",
             '"Show the attachments"',
             onselect='Set(varIbTab, "files");\nIf(varIbFilesFor <> varIbSelId, ' + LOAD_FILES + ")"),
    ], direction="Horizontal", gap=8, height=TAB_H, align_items="Center", justify="Center")
    # Activity (kommentarerne) kun for rapportoeren og admins (issue #193).
    tabs.children[1].props["Visible"] = "IbSeeActivity"
    tabs.children[1].vis = "IbSeeActivity"
    # Tre faner skal kunne staa paa en telefon: de deler bredden.
    for t in tabs.children:
        t.props["Width"] = f"Min({TAB_W}, ({DET_IN} - 16) / 3)"

    # 6. Det valgte indhold.
    show_details = 'varIbTab = "details"'
    loading_more = text_ctrl("txtIbDetLoading", '"Loading the rest of the issue..."',
                             size=lay.SIZE_SMALL, color=C_MUTED, height=18,
                             visible="varIbSelFullFor <> varIbSelId")
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
    # Hele feeden i fuld hoejde: fanens flade scroller - ikke galleriet
    # inden i den (issue #212).
    act_sum = f"Sum(colIbActivity, {_lines_h('Body', ACT_BODY_W)} + 40)"
    gal_h = f"Max(40, {act_sum})"
    gal = Ctrl("galIbActivity", "Gallery", variant="VariableHeight", props={
        "AccessibleLabel": '"Activity, oldest first"',
        "BorderStyle": "BorderStyle.None", "Fill": C_TRANSPARENT, "FillPortions": "0",
        "Height": gal_h, "Items": "colIbActivity", "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None", "Selectable": "false",
        "ShowScrollbar": "false", "TabIndex": "0", "TemplatePadding": "0",
        "TemplateSize": "60", "Width": "Parent.Width",
    }, children=[bg, role, actor, when, body], h=gal_h, vis="!IsEmpty(colIbActivity)")
    # Feeden bliver staaende, mens den hentes igen (issue #212) - kun en
    # tom feed viser "Loading". Fejler en genhentning, staar den gamle
    # feed der stadig, med en besked over.
    act_loading = "varIbActBusy && IsEmpty(colIbActivity)"
    act_state = text_ctrl("txtIbActState",
                          f'If({act_loading}, "Loading activity...", IsEmpty(colIbActivity), '
                          '"The activity could not be loaded. Close the issue and open it again.", '
                          '"The activity could not be refreshed. It shows what was loaded last - '
                          'close the issue and open it again to retry.")',
                          size=lay.SIZE_BODY, color=f"If({act_loading}, {C_MUTED}, {C_INVALID_FG})",
                          height=34, wrap="true",
                          visible=f"({act_loading}) || IfError(varIbActFailed, false)")

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
                     direction="Vertical", gap=12, visible='IbSeeActivity && varIbTab = "activity"')

    # STABIL HOEJDE (issue #212). Toppen - status, fakta, handlingerne og
    # fanerne - staar fast; under den EEN indholdsflade med samme hoejde for
    # alle tre faner: den fane, der kraever mest, bestemmer den (mindst
    # DET_MIN_H), og den er aldrig hoejere end skaermen tillader. Hver fane
    # scroller selv, saa hver har sin egen scrollposition.
    top = group("conIbDetTop", [meta, facts, actions, peek_note, retest, rule, tabs],
                direction="Vertical", gap=POP_GAP)
    files = _files_panel()
    panels = [details, activity, files]
    natural = [stack_height(p.children, 12) for p in panels]
    natural[1] = f"If(IbSeeActivity, {natural[1]}, 0)"
    room = (f"App.Height - {2 * POP_MARGIN} - {2 * POP_PAD} - ({head.h}) - {POP_GAP} - "
            f"({top.h}) - {POP_GAP}")
    content_h = (f"Max({DET_SAFE_MIN_H}, Min({room}, Max({DET_MIN_H}, "
                 + ", ".join(f"({n})" for n in natural) + ")))")
    for p in panels:
        p.props["Height"] = "Parent.Height"
        p.props["LayoutOverflowY"] = "LayoutOverflow.Scroll"
        p.h = "Parent.Height"
    content = group("conIbDetContent", panels, direction="Vertical", gap=0, height=content_h)
    return [_popup("IbDet", [head, top, content], DETAIL_ON, own_scroll=True)]


def build_delete():
    """Permanent sletning - sin egen popup oven paa sagen. Nummeret skal
    skrives, teksten siger, at det ikke kan fortrydes, og knappen er laast,
    til nummeret passer, og mens kaldet koerer. Close er eneste vej ud."""
    del_on = "IfError(varIbDelOn, false)"
    head = _head("IbDel", f'"Delete " & {SEL}.TicketNo & " permanently?"', "Set(varIbDelOn, false)")
    warn = text_ctrl(
        "txtIbDelWarn",
        '"This cannot be undone. The issue, all its comments and activity, and its attachments '
        'are deleted for everyone. '
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
