# -*- coding: utf-8 -*-
"""
Issue Board-skaermen (issue #114, trin 1 og 2): delene, formlerne og
hentningen.

    [ikon] Issue Board                              [Refresh] [+ New issue]
           Report what you find while testing ...
    +------------------------------------------------------------------+
    | [All issues|My issues|Assigned to me] [Open|Closed|Arch.]  [Sort v]     |
    | [Search......] [Application v] [Section v] [Status v] [Priority v]     |
    | 12 issues                                        [Clear filters] |
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
                   Close-ikonet; 2) status som maerke; 3) Issue
                   information (Application, Section, Priority) og Ticket
                   details (Requester, Assigned to, Severity, Reported,
                   Updated) - issue #369; 4) handlingerne som ikoner (Reopen,
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
  * Samtidig hentes IB_TicketComments' TicketId een gang og taelles i
    hukommelsen - kolonnen ACTIVITY (issue #422). Papirclipsen laeser
    'Has attachments' fra sagernes egen hentning.
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
from gen_screen import (Ctrl, stack_height, C_INPUT_BORDER, C_CARD_BG, C_CARD_BORDER, C_DIVIDER, C_INFO_BG,
                        C_INFO_FG, C_INVALID_FG, C_MUTED, C_MUTED_BG, C_MODAL_BG, C_OVERLAY,
                        C_PRIMARY, C_PRIMARY_SOFT, C_TITLE, C_TRANSPARENT, C_WARN_BG,
                        C_WARN_FG, C_VALID_FG, C_VALID_BG)
from build_helpers import (empty_state, fluent, fluent_icon, skeleton_rows, ensure_hit, hit_size, button, card, checkbox_theme, concurrent, confirm_modal,
                           fit_button_width, group, icon_button, SEG_H, tab_list, tabs_w,
                           flow_row, grow, icon_on_mobile, label_row, row_hit, row_rule,
                           tap_backdrop,
                           label_px, text_ctrl, text_input, text_min_height, text_px, themed_dropdown, top_bar,
                           ICON_W, modern_badge, spinner, panel_save_fx, panel_save_mode,
                           panel_save_status, panel_save_block, panel_save_text,
                           act_fx, act_mark, act_button, act_status, act_layers, icon_only_when)
from permissions import IS_ADMIN, ADMIN_LIST, ADMIN_GROUP
from design_tokens import ref as _t, ref_hex as _hex
import icons
import status_chip as sc
import app_icons
import layout_tokens as lay
from layout_tokens import SHELL_W, below, at_least, if_below

import ib_config as cfg
import doc_upload as du
import attflows

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
    '    Set(varIbPanelSave, "");\n'
    "    Set(varIbUploading, false);\n"
    # Knappernes ventetilstand (issue #420): tom = ingen handling, ingen besked.
    '    Set(varIbAct, "");\n'
    "    Set(varIbSelPeek, false);\n"
    "    Set(varIbPosting, false);\n"
    '    Set(varIbPostStage, "");\n'
    "    Set(varIbPostFor, -1);\n"
    '    Set(varIbPostText, "");\n'
    '    Set(varIbPostErr, "");\n'
    "    Set(varIbPostInternal, false);\n"
    "    Set(varIbPostAt, Now());\n"
    "    Set(varIbPostTick, Now());\n"
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


# Connectorens felt for "har raekken vedhaeftninger" - visningsnavnet paa
# {HasAttachments} (References/DataSources.json). Ikke en kolonne i
# SharePoint-udtraekket: SharePoint-connectoren regner den selv.
HAS_FILES_COL = "'Has attachments'"


def _row(r, *, full=True, has_files=None):
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
    # Har sagen filer (issue #422)? Oversigten laeser connectorens
    # {HasAttachments} ('Has attachments') - et felt pr. raekke i den
    # samme hentning, ingen opslag pr. sag. Sagens eget opslag (LookUp)
    # beholder listens vaerdi: laest fra With/LookUp er connectorens
    # vedhaeftningsfelter ikke til at stole paa (issue #133). LOAD_FILES
    # retter den, naar filerne er hentet.
    # has_files: en kendt vaerdi (en ny sag har ingen filer endnu).
    f["HasFiles"] = (has_files if has_files is not None
                     else f"Coalesce({r}.{HAS_FILES_COL}, false)" if not full
                     else f"Coalesce(LookUp(colIbAll, Id = {r}.ID).HasFiles, false)")
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
_SHOW = ", ".join(OVERVIEW_COLS + [HAS_FILES_COL])

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

# ANTAL HAENDELSER PR. SAG (issue #422): EEN hentning af IB_TicketComments
# - kun kolonnen TicketId ($select) - samtidig med sagerne, og saa en
# optaelling i hukommelsen (GroupBy). Ingen CountRows mod SharePoint pr.
# raekke. SharePoint giver kun de raekker, brugeren har ret til: en
# bruger faar sine egne sagers haendelser, en admin alle. Nyeste foerst,
# saa det er de aeldste haendelser, der falder ud over ROW_LIMIT; aabnes
# sagen, rettes dens tal af dens Activity (SET_ACT_N).
FETCH_ACT_N = (f"Set(varIbActNFailed, IfError(ClearCollect(colIbActRaw, "
               f"ShowColumns(Sort({cfg.L_COMMENTS}, ID, SortOrder.Descending), TicketId)); "
               "false, true))")
COUNT_ACT_N = ("If(!varIbActNFailed, ClearCollect(colIbActN, ForAll(GroupBy(colIbActRaw, TicketId, Grp) As g, "
               "{ TicketId: g.TicketId, N: CountRows(g.Grp) })); Clear(colIbActRaw); "
               "Set(varIbActNOk, true))")
# varIbActNOk: tallene er hentet mindst een gang. En fejlet genhentning
# (stille opdatering) beholder de gamle tal i stedet for at skjule dem.


def set_act_n(id_fx, n_fx):
    """Saet antallet for een sag i colIbActN (indsaet, hvis den mangler).
    Tallet regnes FOER UpdateIf (With) - n_fx maa laese colIbActN selv."""
    return (f"With({{ cnt: {n_fx} }}, If(IsBlank(LookUp(colIbActN, TicketId = {id_fx})), "
            f"Collect(colIbActN, {{ TicketId: {id_fx}, N: cnt }}), "
            f"UpdateIf(colIbActN, TicketId = {id_fx}, {{ N: cnt }})))")


# Den aabne sags Activity er facit for dens tal (samme optaelling som
# fanen "Activity (n)").
SET_ACT_N = set_act_n("varIbSelId", 'CountRows(Filter(colIbActivity, Kind <> "Reported"))')
RELOAD_MAIN = RELOAD_ALL

# FLASKEHALSEN (issue #177): een runde - konfigurationen og den ene liste
# samtidig, og IsAdmin staar ikke i koe foran hentningen.
LOAD = (
    "If(\n"
    "    !varIbLoaded,\n"
    "    Set(varIbLoading, true);\n"
    "    " + concurrent(
        f"Set(varIbCfgFailed, IfError(ClearCollect(colIbSections, {FETCH_SECTIONS}); false, true))",
        RELOAD_MAIN, FETCH_ACT_N, indent=4) + ";\n"
    "    " + COUNT_ACT_N + ";\n"
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
    + concurrent(f"Set(varIbSyncFailed, IfError(ClearCollect(colIbFresh, {FETCH_ALL}); false, true))",
                 FETCH_ACT_N) + ";\n"
    + COUNT_ACT_N + ";\n"
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
    "If(!varIbActFailed, ClearCollect(colIbActivity, colIbActFresh); Clear(colIbActFresh); "
    + SET_ACT_N + ");\n"
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
    # Issue #422: papirclipsen i oversigten foelger de hentede filer -
    # ogsaa lige efter Save paa fanen (AFTER_CHANGE henter dem igen).
    "If(!varIbFilesFailed,\n"
    "    Set(varIbSel, Patch(varIbSel, { HasFiles: !IsEmpty(varIbFiles) }));\n"
    "    UpdateIf(colIbAll, Id = varIbSelId, { HasFiles: !IsEmpty(varIbFiles) }));\n"
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
       "StatusRank": "0", "HasFiles": "false"}
SEC = {"Application": '""', "Section": '""', "AppOrder": "0", "SectionOrder": "0",
       "ScreenKey": '""'}
ACT = {"Kind": '""', "Actor": '""', "Role": '""', "Body": '""', "At": "Now()", "Internal": "false",
       "IsSystem": "false", "File": '""', "SizeKb": "0", "Initial": "false"}
ADMINS = {"Email": '""', "Name": '""'}
ACT_N = {"TicketId": "0", "N": "0"}
ACT_RAW = {"TicketId": "0"}


def collections():
    return [("colIbAll", ROW), ("colIbSections", SEC), ("colIbActivity", ACT), ("colIbAdmins", ADMINS),
            ("colIbFresh", ROW), ("colIbActFresh", ACT), ("colIbActN", ACT_N),
            ("colIbActRaw", ACT_RAW)]


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
// Filer paa en sag: rapportoeren og admins. Appen Patch'er selv raekken
// (issue #300); SharePoint lader kun rapportoeren (Created By) og
// admins (Design) rette den.
IbCanAttach = !varIbSelPeek && IbSeeActivity && !varIbSel.Archived;
// Antallet af filer paa sagen: de hentede vedhaeftninger, naar fanen er
// hentet. Ellers af Activity (Attachment-haendelserne fra foer #300), saa
// fanen kan vise et tal uden at hente filerne.
IbFileCount = If(varIbFilesFor = varIbSelId, CountRows(varIbFiles), IbSeeActivity, CountRows(Filter(colIbActivity, Kind = "Attachment")), Blank());'''

# Application-kolonnens ikoner (issue #415): den FAELLES tabel
# (tools/app_icons.py) - samme ikon og farve som sidebaren og hubben.
# Regnet een gang pr. tema, ikke pr. raekke (som hubbens MdIcons).
APP_ICONS = "IbAppIcons"
FORMULAS += "\n" + app_icons.formula(APP_ICONS)


# Statussen er den faelles statuschip (tools/status_chip.py, UX-review T4):
# ikon + tekst + statussens farver - som i hubben og domaenerne.
ISSUE_STATUS = sc.issue_table(cfg.STATUS) + [sc.ARCHIVED]
CHIP_W = sc.table_width(ISSUE_STATUS)
CHIP_H = sc.H


def _chip(name, status_expr, archived_expr, x=None, y=None, width=CHIP_W):
    key = f'If({archived_expr}, "Archived", {status_expr})'
    chip = sc.status_chip(name.replace("txtIb", "imgIb", 1), key, ISSUE_STATUS,
                          default=("", "Unknown", sc.ISSUE_ICONS["New"], "neutral"), width=width)
    if x is not None:
        chip.props["X"] = x
        chip.props["Y"] = y
    return chip


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
    "Set(varIbDetailOn, false);\n"
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
# Formularens gem-tilstand i panelet: saving, failed eller tom (issue #402,
# build_helpers.panel_save_status). Nulstilles, naar formularen lukkes.
IB_SAVE = "varIbPanelSave"
CLOSE_FORM = ('Set(varIbFormOn, false);\nIf(varIbFormMode = "edit", Set(varIbDetailOn, true));\n'
              f'Set({IB_SAVE}, "")')


def build_bar():
    new = button("btnIbNew", '"New issue"', OPEN_FORM, primary=True,
                 width=fit_button_width('"New issue"') + ICON_W, height=36, icon="Add",
                 accessible='"Report a new issue"')
    icon_on_mobile(new)
    # Refresh er ikke laengere en del af det normale arbejde - hver aendring
    # opdaterer selv det, den roerer (issue #212). Den henter andres
    # aendringer stille, uden at filtrene eller en aaben sag roeres.
    # Refresh er en lille ikonknap (UX-review T1) - listen opdateres selv
    # ved hvert besoeg og efter hvert gem. New issue er den primaere.
    refresh = button("btnIbRefresh", '""', REFRESH, width=40, height=36,
                     icon=icons.FLUENT["refresh"],
                     accessible='"Load the latest changes from everyone"',
                     tooltip='"Refresh - load the latest changes from everyone"',
                     display_mode="If(varIbLoading || varIbSyncing, DisplayMode.Disabled, DisplayMode.Edit)")
    refresh.props["Layout"] = "ButtonLayout.IconOnly"
    ensure_hit(refresh)
    return top_bar(P, f'"{cfg.TITLE}"',
                   '"Report what you find while testing, and follow it until it is fixed."',
                   [refresh, new], narrow_hide=("btnIbRefresh",), icon=cfg.APP_KEY)


# ---------------------------------------------------------------------------
# Filtre
# ---------------------------------------------------------------------------
CARD_W = f"({SHELL_W} - 2 * {lay.CARD_PAD})"


def _seg(name, label, selected, onselect, width, accessible):
    """Et segment i en fane-raekke: valgt = fyldt, ikke valgt = kant."""
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
FILTERED = ("!IsBlank(varIbApp) || !IsBlank(varIbSection) || !IsBlank(varIbStatusF) || "
            "!IsBlank(varIbPriF) || !IsBlank(Trim(inpIbSearch.Text))")
CLEAR_FILTERS = ('Set(varIbApp, "");\nSet(varIbSection, "");\nSet(varIbStatusF, "");\n'
                 'Set(varIbPriF, "");\nReset(inpIbSearch);\nReset(drpIbFltApp);\n'
                 "Reset(drpIbFltSection);\nReset(drpIbFltStatus);\nReset(drpIbFltPriority)")

# VAERKTOEJSLINJEN (issue #244) - to raekker direkte i listekortet.
#
#   [All issues|My issues|Assigned to me] [Open|Closed|Archived]   [Sort v]      (luft)
#   [Search......] [Application v] [Section v] [Status v] [Priority v]       (luft)
#
# Issue #301: linjerne er kompakte grupper til venstre - ingen kontrol
# straekkes for at fylde kortet, og den ubrugte plads bliver til hoejre.
# Sorteringen ("Last updated") staar kort efter kontakterne med en tydelig
# afstand (rctIbTbSortGap), ikke yderst til hoejre. Soegefeltet har en
# moderat bredde (SEARCH_W), og listerne staar lige efter det med samme
# afstand. Er der plads nok (FLT_ROOMY), er listerne lidt bredere, saa
# vaerdier som "Functional Location" kan laeses.
#
# Issue #291: soegefeltet staar nu forrest i filterlinjen (ikke paa sin egen
# linje), sorteringen stod alene yderst til hoejre i linje 1 (det fyld er
# fjernet igen i issue #301 - se ovenfor) - og kontakterne er
# smallere (kun den luft, teksten og fluebenet skal bruge).
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
#
# UX-review (screenshots 2026-10-13): de to indlejrede grupper (kontakterne
# og listeparrene) blev stadig tegnet som tomme rammer. Nu staar hver knap
# og hver liste DIREKTE i sin flow_row, som i hubbens filterlinje.
TB_W = CARD_W
# Kontakterne er faner (ModernTabList, issue #303): (vaerdi, tekst, kort
# tekst). Den korte tekst bruges, naar kortet er for smalt til de lange -
# fanerne ruller ikke (Learn: "Tab buttons don't automatically scroll").
SCOPE_TABS = (("all", "All issues", "All"), ("mine", "My issues", "Mine"),
              ("assigned", "Assigned to me", "Assigned"))
STATE_TABS = (("open", "Open"), ("closed", "Closed"), ("archived", "Archived"))
SCOPE_ADMIN_W = tabs_w([t for _k, t, _s in SCOPE_TABS])
SCOPE_USER_W = tabs_w([t for _k, t, _s in SCOPE_TABS[:2]])
STATE_ALL_W = tabs_w([t for _k, t in STATE_TABS])
TB_GAP = 8           # mellem grupperne i en linje
SEARCH_MIN = 176     # soegefeltet + luppen, naar linje 2 staar vandret
SEARCH_W = 240       # soegefeltet + luppen, naar der er plads (issue #301)
SORT_GAP = 16        # ekstra luft foer sorteringen (issue #301)
SORT_OPTIONS = ("Last updated", "Newest", "Oldest", "Priority", "Status")


def _dd_w(*texts):
    """En filterlistes bredde: den laengste tekst + polstring og pil."""
    return max(text_px(t, lay.SIZE_INPUT) for t in texts) + 56


# 150 px som foer: "Last updated" staar helt i den (set i den udgivne app).
SORT_W = min(150, _dd_w(*SORT_OPTIONS))


DD_APP_W = _dd_w("All applications")
DD_SEC_W = _dd_w("All sections")
DD_STATUS_W = _dd_w("All statuses", *[x for x, _c, _r in cfg.STATUS if x != cfg.STATUS_CLOSED])
DD_PRI_W = _dd_w("All priorities", *[x for x, _r in cfg.PRIORITY])
PAIR_A_W = DD_APP_W + 8 + DD_SEC_W
PAIR_B_W = DD_STATUS_W + 8 + DD_PRI_W
PAIR_MIN = max(PAIR_A_W, PAIR_B_W)
# Issue #301: med god plads er Application og Section bredere, saa de
# typiske vaerdier ("Functional Location", "Issue list and filters") kan
# laeses. Status og Priority er allerede brede nok til deres vaerdier.
DD_APP_ROOMY = _dd_w("All applications", "Functional Location", "Maintenance Plan")
DD_SEC_ROOMY = _dd_w("All sections", "Issue list and filters")
PAIR_A_ROOMY = DD_APP_ROOMY + 8 + DD_SEC_ROOMY
# Linje 1 paa een linje: begge kontakter, luften (mindst 0) og sorteringen
# - tre mellemrum. Regnet med adminens tre scope-knapper, saa graensen er
# den samme for alle (og passer ved Desktop-graensen, 1024 px).
TOP_NEED = SCOPE_ADMIN_W + STATE_ALL_W + SORT_W + 3 * TB_GAP
TOP_OK = f"{TB_W} >= {TOP_NEED}"
# Linje 2 paa een linje: soegefeltets mindstebredde + de to listepar.
FLT_NEED = SEARCH_MIN + PAIR_A_W + PAIR_B_W + 2 * TB_GAP
FLT_OK = f"{TB_W} >= {FLT_NEED}"
# Linje 2 med fuld soegebredde og de brede lister (issue #301).
FLT_ROOMY_NEED = SEARCH_W + PAIR_A_ROOMY + PAIR_B_W + 2 * TB_GAP + 2
FLT_ROOMY = f"{TB_W} >= {FLT_ROOMY_NEED}"
# Hver linjes hoejde, naar den staar vandret.
TB_LINE_H = 36


def build_filters():
    """Vaerktoejslinjens to raekker - de staar direkte i listekortet."""
    # Issue #303: kontakterne er faner (build_helpers.tab_list). Samme
    # variabler og vaerdier som knapperne: varIbScope ("all", "mine",
    # "assigned" - kun for admin) og varIbState ("open", "closed",
    # "archived"). Filtreringen er uaendret.
    roomy = f"({TB_W}) >= {SCOPE_ADMIN_W}"
    scope = tab_list("tabIbScope", "varIbScope", [
        (k, f'If({roomy}, "{t}", "{s}")') + ((IS_ADMIN,) if k == "assigned" else ())
        for k, t, s in SCOPE_TABS], label="Show issues",
        # Smalt: fanerne faar hele linjen (de staar til venstre i den).
        width=f"If({TOP_OK}, If({IS_ADMIN}, {SCOPE_ADMIN_W}, {SCOPE_USER_W}), {TB_W})")
    scope.props["LayoutMinWidth"] = "0"

    state = tab_list("tabIbState", "varIbState", [(k, f'"{t}"') for k, t in STATE_TABS],
                     label="Show issues by state",
                     width=f"If({TOP_OK}, {STATE_ALL_W}, {TB_W})")
    state.props["LayoutMinWidth"] = "0"

    search = text_input("inpIbSearch", '""', placeholder='"Search issues"',
                        label='"Search issues"', height=TB_LINE_H)
    # Listen filtreres i hukommelsen - et lille ophold, saa den ikke regnes
    # om for hvert tegn.
    search.props["TriggerOutput"] = "TriggerOutput.Delayed"
    grow(search, 0)
    # Lupen er Fluents "Search" (issue #306) - pynt ved feltet, ingen klik.
    ico = fluent_icon("icoIbSearchIcon", fluent("search"), C_MUTED, '"Search"', size=20)
    ico.props["AlignInContainer"] = "AlignInContainer.Center"
    ico.props["LayoutMinWidth"] = "20"
    # Issue #301: vandret er soegefeltet hoejst SEARCH_W bredt - kun paa en
    # smal Desktop giver det efter (ned til SEARCH_MIN), saa listerne kan
    # staa paa samme linje. Under hinanden faar det hele linjen. Bredden er
    # en formel af TB_W (en nedre graense), saa feltet inden i kan regne sin
    # egen bredde ud af den.
    sw = (f"If({FLT_ROOMY}, {SEARCH_W}, {FLT_OK}, "
          f"Min({SEARCH_W}, ({TB_W}) - {PAIR_A_W + PAIR_B_W + 2 * TB_GAP + 2}), {TB_W})")
    search_row = group("conIbSearchRow", [search, ico], direction="Horizontal", gap=8,
                       height=TB_LINE_H, align_items="Center",
                       width=sw, align_in_container="Start")

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
    drp_sort = themed_dropdown("drpIbSort", "[" + ", ".join(f'"{o}"' for o in SORT_OPTIONS) + "]",
                               "varIbSort", label='"Sort issues"',
                               onchange="Set(varIbSort, Self.Selected.Value)")
    drp_sort.props["Width"] = f"Min({SORT_W}, {TB_W})"
    # Listerne er saa brede som deres tekst; under hinanden deler et par
    # linjen. Issue #301: med god plads er Application og Section bredere.
    for c, w, roomy in ((drp_app, DD_APP_W, DD_APP_ROOMY), (drp_sec, DD_SEC_W, DD_SEC_ROOMY),
                        (drp_status, DD_STATUS_W, DD_STATUS_W), (drp_pri, DD_PRI_W, DD_PRI_W)):
        ww = str(w) if roomy == w else f"If({FLT_ROOMY}, {roomy}, {w})"
        c.props["Width"] = f"Min({ww}, (({TB_W}) - 8) / 2)"
        c.props["LayoutMinWidth"] = c.props["Width"]
        # Round 4: listerne blev tegnet ~30 px under parrets overkant og
        # klippet af raekken (Center i et par, der er lige saa hoejt som
        # listen). Nu flugter de med parrets top - som kontakterne, der ses.
        c.props["AlignInContainer"] = "AlignInContainer.Start"
        c.props["Height"] = str(TB_LINE_H)
        c.h = TB_LINE_H
    pair_a = group("conIbFltPairA", [drp_app, drp_sec], direction="Horizontal", gap=8,
                   height=TB_LINE_H, align_items="Start",
                   width=f"Min(If({FLT_ROOMY}, {PAIR_A_ROOMY}, {PAIR_A_W}), {TB_W})",
                   align_in_container="Start")
    pair_b = group("conIbFltPairB", [drp_status, drp_pri], direction="Horizontal", gap=8,
                   height=TB_LINE_H, align_items="Start", width=f"Min({PAIR_B_W}, {TB_W})",
                   align_in_container="Start")
    drp_sort.props["LayoutMinWidth"] = drp_sort.props["Width"]
    # Issue #301: sorteringen staar kort efter kontakterne - en fast,
    # usynlig luft (SORT_GAP) skiller dem, og resten af linjen er tom til
    # hoejre. Luften giver efter paa en smal Desktop, saa graensen for een
    # linje er den samme som foer. Under hinanden er den skjult (den ville
    # kun give en tom linje).
    gap_w = f"Max(0, Min({SORT_GAP}, ({TB_W}) - {TOP_NEED}))"
    sort_gap = Ctrl("rctIbTbSortGap", "Rectangle", props={
        "AccessibleLabel": '"Space between the switches and the sort order"',
        "BorderStyle": "BorderStyle.None", "BorderThickness": "0",
        "Fill": C_TRANSPARENT, "Height": "1", "OnSelect": "false", "TabIndex": "0",
        "Visible": TOP_OK, "Width": gap_w,
    }, h=1, vis=TOP_OK)
    top = flow_row("conIbTbTop", [scope, state, sort_gap, drp_sort], TB_W, gap=TB_GAP,
                   ok=TOP_OK)
    filters = flow_row("conIbTbFilters", [search_row, pair_a, pair_b], TB_W, gap=TB_GAP,
                       ok=FLT_OK)
    # Staar listerne under hinanden, holder de deres tekstbredde (Start) i
    # stedet for at strakke sig til hele linjen.
    filters.props["LayoutAlignItems"] = (f"If({FLT_OK}, LayoutAlignItems.Center, "
                                         "LayoutAlignItems.Start)")
    # Luft over og under linjerne: Studio tegnede kontrollerne helt op i
    # raekkens overkant, og toppen blev skaaret af.
    # Issue #291: lidt mindre luft end foer - kun saa meget, at Studio ikke
    # tegner kontrollerne helt oppe i raekkens overkant.
    _air(top, 6, 2)
    _air(filters, 4, 2)
    return [top, filters]


def _air(row, top, bottom):
    """Polstring over/under en flow_row; hoejden vokser med det samme."""
    row.props["PaddingTop"] = str(top)
    row.props["PaddingBottom"] = str(bottom)
    row.props["Height"] = f"({row.props['Height']}) + {top + bottom}"
    row.h = row.props["Height"]


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
ACT_BTN = 40         # papirclipsen (issue #193) - kolonnen FILES og raekken under Desktop
ACTV_W = 52          # kolonnen ACTIVITY (issue #422): ikonet, tallet og overskriften
ACTV_ICON = 16
FILES_W = 44         # kolonnen FILES: papirclipsen med sin klikflade (hit_size, regel 40)

# (noegle, overskrift, mindstebredde, vaegt, kun Wide). Raekkefoelgen er
# issue #244's: Ticket ID | Requester | Title | Application | Section |
# Priority | Status | Assigned to | Reported | Updated | Activity | Files.
# Issue #422: ACTIVITY (antal haendelser) kom til, og ACTIONS hedder nu
# FILES - papirclipsen staar kun, naar sagen har filer. Pladsen paa den
# smalleste Desktop-skaerm (806 px) kom fra titlen (140 -> 106) og
# Updated (84 -> 80): de vokser stadig med den frie bredde paa en bredere
# skaerm. Application beholder 100 px: med app-ikonet foran (issue #415)
# faar navnet 100 - 26 = 74 px, nok til fx "Equipments" og "Issue Board".
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
    ("TITLE", "TITLE", 106, 3, False),
    ("APP", "APPLICATION", 100, 2, False),
    ("SECTION", "SECTION", 104, 2, True),
    ("PRI", "PRIORITY", 72, 0, False),
    ("STATUS", "STATUS", 116, 0, False),
    ("ASG", "ASSIGNED TO", 92, 2, True),
    ("REP", "REPORTED", 84, 1, True),
    ("UPD", "UPDATED", 80, 1, False),
    ("ACTV", "ACTIVITY", ACTV_W, 0, False),
    ("ACT", "FILES", FILES_W, 0, False),
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
# hvor filerne vises (og nye laegges paa af rapportoeren og admins).
OPEN_ROW_FILES = open_ticket("ThisItem", "false", tab="files")
# Issue #422: papirclipsen er et tegn paa, at sagen HAR filer - ikke en
# upload-knap paa hver raekke. Uden filer er cellen tom. Fanen
# Attachments kan alle se, saa tegnet staar for alle.
ROW_HAS_FILES = "ThisItem.HasFiles"
# Activity-taelleren (issue #422): antallet af haendelser fra colIbActN -
# opslag i hukommelsen, intet kald pr. raekke. Kun for rapportoeren og
# admins (som fanen Activity); andre har ingen rettighed til
# kommentarerne og faar en tom celle - ikke et misvisende 0.
ROW_ACT_N = "Coalesce(LookUp(colIbActN, TicketId = ThisItem.Id).N, 0)"
ROW_SEE_ACT = f"(ThisItem.Reporter = varIbMe || {IS_ADMIN}) && Coalesce(varIbActNOk, false)"

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

# Datoer som i resten af appen (layout_tokens.DATE_FMT, UX-review B5): her
# stod "dd mmm yyyy", og maaneden kom paa brugerens sprog ("08 okt 2026").
DATE_FMT = '"%s"' % lay.DATE_FMT
DATETIME_FMT = '"%s"' % lay.DATETIME_FMT
# "Updated" kun efter en reel aendring - samme regel som popuppen uden
# Activity (UPDATED_AFTER_MIN).
ROW_UPDATED = f"DateDiff(ThisItem.CreatedOn, ThisItem.UpdatedOn, TimeUnit.Minutes) >= {UPDATED_AFTER_MIN}"
# PRIORITETEN MAA IKKE LIGNE STATUS (UX-review T4): Normal og Low er
# almindelig tekst, kun Urgent og High faar ikon og farve
# (tools/status_chip.PRIORITY). Foer var begge farvede piller.
PRI_W = sc.table_width(sc.PRIORITY)
_NO_PRIORITY = ("", "-", None, "plain")


def _pri_badge(name, expr, width=PRI_W, visible=None):
    """Prioriteten. Uden prioritet staar en streg."""
    vis = None if visible is None else f"({visible}) && !IsBlank({expr})"
    chip = sc.status_chip(name.replace("txtIb", "imgIb", 1), expr, sc.PRIORITY,
                          default=_NO_PRIORITY, width=width, visible=vis)
    chip.props["AccessibleLabel"] = chip.props["AccessibleLabel"].replace('"Status: "', '"Priority: "', 1)
    return chip


def _no_badge(name, expr, width=NO_W):
    """Sagsnummeret som kompakt maerke - en ModernBadge (#304), samme
    farver og maal som teksten foer."""
    return modern_badge(name, expr, size=lay.SIZE_SMALL, color=C_PRIMARY, fill=C_MUTED_BG,
                        height=CHIP_H, width=width, radius=12,
                        accessible='"Ticket " & Self.Content')


def _text_chip(name, key, table, prefix, visible=None):
    """Et statusmaerke som tekst: etiketten i tonens farvepar
    (state-*-fg/bg) paa en pille, saa bred som teksten. Tonen "plain"
    (Normal/Low-prioritet) er almindelig tekst uden pille."""
    pad = 10

    def sw(pick, default):
        return (f"Switch({key}, " + ", ".join(f'"{k}", {pick(lbl, tone)}'
                                              for k, lbl, _p, tone in table) + f", {default})")
    width = sw(lambda lbl, tone: label_px(lbl, sc.SIZE + (1 if tone == "plain" else 0))
               + (2 if tone == "plain" else 2 * pad), label_px("Unknown", sc.SIZE) + 2 * pad)
    fill = sw(lambda lbl, tone: C_TRANSPARENT if tone == "plain" else _t(f"state-{tone}-bg"),
              _t("state-neutral-bg"))
    color = sw(lambda lbl, tone: C_TITLE if tone == "plain" else _t(f"state-{tone}-fg"),
               _t("state-neutral-fg"))
    align = sw(lambda lbl, tone: "Align.Left" if tone == "plain" else "Align.Center", "Align.Center")
    text = sw(lambda lbl, tone: f'"{lbl}"', '"Unknown"')
    # En ModernBadge (#304): samme tekst, farvepar, bredde og hjoerner.
    t = modern_badge(name, text, size=sc.SIZE, color=color, fill=fill, height=CHIP_H,
                     width=width, accessible=f"{prefix} & Self.Content", visible=visible,
                     extra={"Align": align, "LayoutMinWidth": width})
    return t, f"({width})"


# Hvem (issue #212): rapportoeren som kort bruger-id - delen foer @ med
# store bogstaver (uffes@orsted.com -> UFFES), samme metode som MyUserId
# (tools/permissions.py) og initialerne i Activity. Aldrig hele mailen.
def requester(r):
    return f'If(IsBlank({r}.Reporter), "-", {_initials(r + ".Reporter")})'


REPORTER_FX = requester("{r}")


def _attach_btn(name, visible, width=ACT_BTN):
    b = button(name, '"Attachments"', OPEN_ROW_FILES, width=width, height=32, icon="Attach",
               visible=visible, accessible='"Show the attachments on " & ThisItem.TicketNo',
               tooltip='"Show attachments"')
    b.props["Layout"] = "ButtonLayout.IconOnly"
    b.props["BorderColor"] = C_TRANSPARENT
    # Oven paa raekkens klikflade - klikket er knappens eget (gen_screen).
    b.props["_OnTop"] = "true"
    ensure_hit(b)                      # H.hit (UX-review F6, regel 40)
    return b


def _act_count(suffix, width):
    """Activity-taelleren (issue #422): et lille kommentarikon og tallet.
    Containeren staar altid (cellen flytter aldrig kolonnerne); ikonet og
    tallet kun, naar brugeren maa se sagens Activity. 0 er dempet."""
    n = ROW_ACT_N
    ico = fluent_icon(f"icoIbRowAct{suffix}", fluent("comment"), C_MUTED, '"Activity"',
                      size=ACTV_ICON, visible=ROW_SEE_ACT)
    # Opslaget staar een gang (Text); farve, vaegt og etiket laeser Self.Text.
    txt = text_ctrl(f"txtIbRowAct{suffix}", f"Text({n})", size=lay.SIZE_SMALL, height=20, wrap="false",
                    width=f"({width}) - {ACTV_ICON + 4}",
                    color=f'If(Self.Text = "0", {C_MUTED}, {C_TITLE})',
                    visible=ROW_SEE_ACT,
                    accessible='"Activity: " & Self.Text & If(Self.Text = "1", " entry", " entries")',
                    extra={"FontWeight": 'If(Self.Text = "0", FontWeight.Normal, FontWeight.Semibold)'})
    return group(f"conIbRowAct{suffix}", [ico, txt], direction="Horizontal", gap=4, height=20,
                 width=width, align_items="Center")


# CLAUDE-ikonet i kolonnen Assigned to (issue #423): en lille gnist foran
# navnet, kun naar sagen er tildelt CLAUDE. Kun her i oversigten - ikke i
# dropdown'en, popuppen eller det kompakte kort.
CLAUDE_ICON = 14
CLAUDE_GAP = 4
IS_CLAUDE_ROW = f'ThisItem.AssignedEmail = "{cfg.CLAUDE_EMAIL}"'


def claude_svg():
    """Gnisten som data-URI i tokenfarven (foelger temaet)."""
    color = '" & %s & "' % _hex(icons.CLAUDE_TOKEN)
    body = icons.svg(icons.CLAUDE, color, size=CLAUDE_ICON, width=icons.CLAUDE_STROKE)
    return f'"data:image/svg+xml;utf8," & EncodeUrl("{body}")'


def _assigned_cell(txt):
    """Kolonnen Assigned to: [gnist] navn. Cellen er een gruppe i
    kolonnens bredde, saa overskrift og raekke flugter som foer; ikonet
    tager kun plads, naar det vises, og teksten rykker ind efter det."""
    icon = Ctrl("imgIbRowClaude", "Image", props={
        "AccessibleLabel": '"Claude"',
        "AlignInContainer": "AlignInContainer.Center",
        "BorderStyle": "BorderStyle.None",
        "BorderThickness": "0",
        "Height": str(CLAUDE_ICON),
        "Image": claude_svg(),
        "ImagePosition": "ImagePosition.Fit",
        "OnSelect": "false",
        "TabIndex": "0",
        "Visible": IS_CLAUDE_ROW,
        "Width": str(CLAUDE_ICON),
    }, h=CLAUDE_ICON, vis=IS_CLAUDE_ROW)
    # Synligheden naevner ThisItem og kan ikke regnes paa i galleritjekket
    # (gen_screen._gallery_checks); cellen staar kun paa en bred skaerm.
    icon.props["_FitGuard"] = WIDE
    name = txt("txtIbRowAssigned", "ASG",
               'If(IsBlank(ThisItem.Assigned), "Unassigned", ThisItem.Assigned)',
               size=lay.SIZE_SMALL,
               color=f"If(IsBlank(ThisItem.Assigned), {C_MUTED}, {C_TITLE})",
               accessible='"Assigned to: " & Self.Text')
    name.props["Width"] = f'({COL_W["ASG"]} - If({IS_CLAUDE_ROW}, {CLAUDE_ICON + CLAUDE_GAP}, 0))'
    return group("conIbRowAssigned", [icon, name], direction="Horizontal", gap=CLAUDE_GAP,
                 height=20, width=COL_W["ASG"], align_items="Center")


# Application med sit ikon foran (issue #415): det kompakte, farvede ikon
# fra hubbens anmodningsliste (tools/app_icons.py) og navnet ved siden af.
# Cellen er praecis lige saa bred som foer (COL_W["APP"]); teksten faar
# resten efter ikonet og afkortes med ellipse som foer.
APP_ICON_GAP = 6


def _app_cell():
    has = "!IsBlank(ThisItem.Application)"
    img = Ctrl("imgIbRowApp", "Image", props={
        # Pynt ved teksten. App checker kraever alligevel et tab stop og en
        # etiket paa et Image (issue #165) - som hubbens domaeneikon.
        "AccessibleLabel": '"Application icon: " & ThisItem.Application',
        "AlignInContainer": "AlignInContainer.Center",
        "BorderStyle": "BorderStyle.None",
        "BorderThickness": "0",
        "Fill": C_TRANSPARENT,
        "Height": str(app_icons.TILE),
        "Image": app_icons.uri(APP_ICONS, "ThisItem.Application"),
        "ImagePosition": "ImagePosition.Fit",
        "LayoutMinWidth": str(app_icons.TILE),
        "OnSelect": "false",
        "TabIndex": "0",
        "Visible": has,
        "Width": str(app_icons.TILE),
    }, h=app_icons.TILE, vis=has)
    text_w = f'({COL_W["APP"]} - If({has}, {app_icons.TILE + APP_ICON_GAP}, 0))'
    txt = text_ctrl("txtIbRowApp", "ThisItem.Application", size=lay.SIZE_BODY, height=20,
                    width=text_w, wrap="false", accessible='"Application: " & Self.Text')
    return group("conIbRowApp", [img, txt], direction="Horizontal", gap=APP_ICON_GAP,
                 height=20, width=COL_W["APP"], align_items="Center",
                 layout_min_width=COL_W["APP"])


def _table_row():
    """Tabelraekken (Desktop og op) - een celle pr. kolonne i LIST_COLS."""
    def txt(name, key, expr, **kw):
        kw.setdefault("size", lay.SIZE_BODY)
        return text_ctrl(name, expr, height=20, width=COL_W[key], wrap="false", **kw)

    cells = {
        "ID": _no_badge("bdgIbRowNo", "ThisItem.TicketNo", width=COL_W["ID"]),
        # Kun titlen, paa een linje - en lang titel afkortes med ellipse.
        "TITLE": txt("txtIbRowTitle", "TITLE", "ThisItem.Title", weight="Semibold",
                     accessible='"Title: " & ThisItem.Title'),
        "APP": _app_cell(),
        "SECTION": txt("txtIbRowSection", "SECTION", "ThisItem.Section", color=C_MUTED,
                       accessible='"Section: " & Self.Text'),
        "REQ": txt("txtIbRowReq", "REQ", requester("ThisItem"),
                   accessible='"Requester: " & Self.Text'),
        "PRI": _pri_badge("txtIbRowPriority", "ThisItem.Priority", width=COL_W["PRI"]),
        "STATUS": _chip("txtIbRowStatus", "ThisItem.Status", "ThisItem.Archived",
                        width=COL_W["STATUS"]),
        "ASG": _assigned_cell(txt),
        "REP": txt("txtIbRowReported", "REP", f"Text(ThisItem.CreatedOn, {DATE_FMT})",
                   size=lay.SIZE_SMALL, color=C_MUTED, accessible='"Reported: " & Self.Text'),
        "UPD": txt("txtIbRowUpdated", "UPD",
                   f'If({ROW_UPDATED}, Text(ThisItem.UpdatedOn, {DATE_FMT}), "-")',
                   size=lay.SIZE_SMALL, color=C_MUTED, accessible='"Updated: " & Self.Text'),
        "ACTV": _act_count("", COL_W["ACTV"]),
        "ACT": _attach_btn("btnIbRowAttach", f"{TABLE_ON} && {ROW_HAS_FILES}", width=COL_W["ACT"]),
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
    no = _no_badge("bdgIbRowNoC", "ThisItem.TicketNo")
    pri = _pri_badge("txtIbRowPriorityC", "ThisItem.Priority", visible=at_least("Tablet"))
    gap = grow(group("conIbRowGapC", [], direction="Horizontal", height=0))
    chip = _chip("txtIbRowStatusC", "ThisItem.Status", "ThisItem.Archived")
    act = _act_count("C", 44)
    line1 = group("conIbRowLineC1", [no, pri, gap, act, chip], direction="Horizontal", gap=8,
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
    att_c = _attach_btn("btnIbRowAttachC", f"{below('Desktop')} && {ROW_HAS_FILES}")
    att_c.props["X"] = "Parent.TemplateWidth - 12 - Self.Width"
    att_c.props["Y"] = f"{CMP_ROW_H - 1 - 10 + 7} - Self.Height"
    att_c.props.pop("_OnTop")

    row_h = if_below("Desktop", str(CMP_ROW_H), str(TBL_ROW_H))
    # Issue #291: EEN taeller - antallet i listen, som den staar efter
    # visningen, soegningen og filtrene ("3 issues").
    count = grow(text_ctrl(
        "txtIbCount",
        'With({ n: galIbList.AllItemsCount }, n & If(n = 1, " issue", " issues"))',
        size=lay.SIZE_BODY, weight="Semibold", color=C_MUTED, height=20))
    clear = button("btnIbClearFlt", '"Clear filters"', CLEAR_FILTERS,
                   width=fit_button_width('"Clear filters"', size=lay.SIZE_SMALL), height=30,
                   visible=FILTERED, accessible='"Clear all filters and the search"')
    clear.props["Size"] = str(lay.SIZE_SMALL)
    clear.props["LayoutMinWidth"] = clear.props["Width"]
    count_row = group("conIbCountRow", [count, clear], direction="Horizontal", gap=8, height=30,
                      align_items="Center")
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
    # Tom tilstand (UX-review F4/T9): ikon, beskeden og een handling -
    # Clear filters, naar et filter er skyld i den tomme liste, og ellers
    # New issue i "My issues". Retry staar under ved en fejl.
    empty = empty_state("conIbEmpty", empty_fx, "Clear filters", CLEAR_FILTERS,
                        icon_key=cfg.APP_KEY, primary=False, button_name="btnIbEmptyAction",
                        action_visible=f"({FILTERED}) && !IbFailed && !varIbLoading",
                        visible="galIbList.AllItemsCount = 0 && !varIbLoading")
    empty.children[1].props["Color"] = f"If(IbFailed, {C_INVALID_FG}, {C_MUTED})"
    retry = button("btnIbRetry", '"Retry"', RETRY, width=fit_button_width('"Retry"'), height=36,
                   visible="IbFailed && !varIbLoading", accessible='"Load the issues again"')
    retry.props["AlignInContainer"] = "AlignInContainer.Start"

    # Pladsen, galleriet har: skaermen minus mobilbjaelken, sidens bjaelke,
    # kroppens luft, kortets polstring og kant og kortets andre linjer.
    before = [*toolbar, count_row, head, head_rule]
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
    # Pladsholder-raekker mens sagerne hentes (UX-review M7) - i stedet for
    # hjulet over hele skaermen. Saa mange raekker, som listen ville vise.
    loading = skeleton_rows("conIbSkeleton", "varIbLoading", label="Loading issues...")
    return card("conIbListCard", before + [loading, gal, empty, retry], gap=8)


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


def _popup(prefix, kids, vis, width=POP_W, foot=None, own_scroll=False,
           side_panel=False, close_fx="Set(varIbDetailOn, false)"):
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
        # Issue #413: hele det faste (hoved, fod og deres luft) traekkes fra -
        # foer stod foden uden parentes, saa dens hoejde blev LAGT TIL pladsen,
        # kroppen blev for hoej, og Save changes blev skubbet ud under kanten
        # (modalen klipper), naar "Add more details" var foldet ud.
        foot_parts = []
        if foot is not None and side_panel:
            # Sidepanelet: en tynd streg skiller den faste fod fra det, der
            # scroller - og kroppen har luft forneden, saa det sidste felt
            # (Resolution) ikke staar klemt op mod foden.
            foot_parts.append(group(f"con{prefix}FootRule", [], direction="Horizontal",
                                    height=1, fill=C_DIVIDER))
        if foot is not None:
            foot_parts.append(foot)
        fixed = " + ".join([f"({head.h})"] + [f"{POP_GAP} + ({f.h})" for f in foot_parts])
        # Sidepanelet staar i fuld hoejde (App.Height) uden margen omkring.
        margin = "" if side_panel else f" - {2 * POP_MARGIN}"
        room = f"App.Height{margin} - {2 * POP_PAD} - {POP_GAP} - ({fixed})"
        body_pad_b = 8 if side_panel and foot is not None else 0
        natural = stack_height(rest, POP_GAP, pad_b=body_pad_b)
        body = group(f"con{prefix}Body", rest, direction="Vertical", gap=POP_GAP,
                     height=f"Max(60, Min({natural}, {room}))", overflow_y="Scroll",
                     pad=(0, 0, body_pad_b, 0) if body_pad_b else None)
        parts = [head, body] + foot_parts
    modal = group(f"con{prefix}Modal", parts, direction="Vertical", gap=POP_GAP, fill=C_MODAL_BG,
                  border_color=C_PRIMARY_SOFT, radius=lay.RADIUS_MODAL,
                  pad=(POP_PAD, POP_PAD, POP_PAD, POP_PAD), width=width,
                  drop_shadow="ExtraBold", align_in_container="Center")
    if side_panel:
        backdrop = tap_backdrop(f"img{prefix}Backdrop", f"({vis}) && {lay.INSET} = 0",
                                close_fx, fill=C_TRANSPARENT)
        # Et klik paa siden bag panelet lukker det paa ALLE bredder (tap_backdrop
        # lukker kun under Tablet); et tab stop, saa tastaturet kan det samme.
        backdrop.props["OnSelect"] = close_fx
        backdrop.props["TabIndex"] = "0"
        modal.props["Visible"] = vis
        modal.vis = vis
        modal.props["Height"] = "App.Height"
        modal.h = "App.Height"
        modal.props["Width"] = lay.PANEL_W_AT
        modal.props["X"] = f"If({at_least('Desktop')}, App.Width - Self.Width, 0)"
        modal.props["Y"] = "0"
        modal.props["RadiusTopRight"] = "0"
        modal.props["RadiusBottomRight"] = "0"
        modal.props["AlignInContainer"] = "AlignInContainer.Start"
        # Panelet staar frit paa skaermen (ikke i sloeret), saa det skal
        # selv skjules. Uden det stod Description- og New issue-panelet
        # altid halvt synlige over listen (screenshots 2026-10-13).
        modal.props["Visible"] = vis
        modal.vis = vis
        return [backdrop, modal]
    backdrop = group(f"con{prefix}Backdrop", [modal], direction="Vertical", gap=0,
                     height="App.Height", width="App.Width", fill=C_OVERLAY, visible=vis,
                     justify="Center", align_items="Center",
                     pad=(POP_MARGIN, 0, POP_MARGIN, 0))
    backdrop.props["X"] = "0"
    backdrop.props["Y"] = "0"
    return backdrop


def _head(prefix, title_fx, close_fx, lead=(), title_w=None, close_icon=False, nav=()):
    """Titel og Close. title_w: titlens bredde - saa ombrydes en lang titel
    paa op til tre linjer i stedet for at blive klippet. close_icon: Close
    som ikon (Dismiss) oeverst til hoejre - sagens popup (issue #229)."""
    h = 26
    if title_w is not None:
        h = f"Min(3 * 23 + 2, Max(26, {_lines_h(title_fx, title_w, px=9.2, line_h=23)}))"
    title = grow(text_ctrl(f"txt{prefix}Title", title_fx, size=lay.SIZE_CARD_TITLE,
                           weight="Semibold", height=h, wrap="true" if title_w else "false"))
    close = icon_button(f"btn{prefix}Close", "Close", close_fx, icons.CLOSE)
    close.props["AlignInContainer"] = "AlignInContainer.Start"
    close.props["LayoutMinWidth"] = close.props["Width"]
    hmin = lay.HIT_TOUCH
    return group(f"con{prefix}Head", [*lead, title, *nav, close], direction="Horizontal", gap=10 if not nav else 4,
                 height=hmin if title_w is None else f"Max({hmin}, {h})",
                 align_items="Center" if title_w is None else "Start")


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


# Formularen tom igen efter en indsendt sag. Variablerne foerst - Default
# paa Application og Section laeser dem.
CLEAR_FORM = ('Set(varIbFormApp, "");\nSet(varIbFormSection, "");\nSet(varIbMore, false);\n'
              + RESET_FORM)

# Den nye sag ind i listen - Patch gav raekken tilbage, saa der er intet
# opslag og ingen ny hentning af listen (issue #177, #193).
ADD_NEW = (
    "Set(varIbSelId, varIbNewRow.ID);\n"
    f"Set(varIbNew, {_row('varIbNewRow', has_files='false')});\n"
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

def _in_panel(fx):
    """SUBMIT/SAVE_EDIT fra formularens sidepanel (issue #402): samme gem,
    men tilstanden er panelets (IB_SAVE) i stedet for sidens varIbBusy."""
    on, off = "Set(varIbBusy, true);\n", ";\nSet(varIbBusy, false)"
    assert fx.startswith(on) and fx.endswith(off), fx[:40]
    return panel_save_fx(IB_SAVE, fx[len(on):-len(off)],
                         f'Set({IB_SAVE}, If(varIbSaved, "", "failed"))')


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


FORM_W = lay.PANEL_W_AT
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


# Sagens vedhaeftninger, naar de er hentet for DENNE sag (LOAD_FILES).
FILES_ITEMS = "If(varIbFilesFor = varIbSelId, varIbFiles, FirstN(varIbFiles, 0))"


def _attachments(name, label):
    """Sagens filer - den faelles moderne Attachments-kontrol
    (tools/doc_upload.py, issue #134/#161), bundet til raekkens
    vedhaeftninger (issue #300). Kontrollen viser, aabner og fjerner selv
    filerne; UPLOAD_FILES gemmer dem med een Patch paa IB_Tickets - ikke
    gennem flowet (Peter, 2026-10-17: "En bruger maa gerne redigere sit
    eget issue")."""
    return du.picker(name, label, cfg.MAX_FILES, cfg.MAX_FILE_MB, FILES_ITEMS,
                     display_mode=("If(!IbCanAttach, DisplayMode.View, varIbUploading || "
                                   "varIbFilesBusy || varIbFilesFor <> varIbSelId, "
                                   "DisplayMode.Disabled, DisplayMode.Edit)"))


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
        "Discard and close", CLOSE_FORM, "btnIbDiscardConfirm", icon=None, danger=True)


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
    # CLAUDE (issue #423) staar lige under "Not assigned", foer admins -
    # en fast pseudo-bruger (cfg.CLAUDE_EMAIL), ikke en raekke i
    # colIbAdmins. Kun navnet - ikonet vises ikke i dropdown'en.
    asg_items = ('Ungroup(Table({ x: Table({ Email: "", Name: "Not assigned" }, '
                 f'{{ Email: "{cfg.CLAUDE_EMAIL}", Name: "{cfg.CLAUDE_NAME}" }}) }}, '
                 '{ x: SortByColumns(colIbAdmins, "Name", SortOrder.Ascending) }), x)')
    asg = themed_dropdown("drpIbAssignee", asg_items,
                          f'If(IsBlank({SEL_REF}.AssignedEmail), "Not assigned", '
                          f'{SEL_REF}.AssignedEmail = "{cfg.CLAUDE_EMAIL}", "{cfg.CLAUDE_NAME}", '
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
    # Gemmets tilstand vises i panelet under knappen - ikke som sidens sloer
    # og bjaelke (issue #402). Retry er det samme tryk.
    submit_fx = ("If(\n    varIbBusy,\n    false,\n"
                 f"    !({VALID}),\n"
                 "    Set(varIbTried, true);\n"
                 f"    Notify({missing_text}, NotificationType.Warning),\n"
                 f"    If(\n        {EDITING},\n        "
                 + _in_panel(SAVE_EDIT).replace("\n", "\n        ") + ",\n        "
                 + _in_panel(SUBMIT).replace("\n", "\n        ") + "\n    )\n)")
    idle = "If(varIbBusy, DisplayMode.Disabled, DisplayMode.Edit)"
    submit = button("btnIbFormSubmit", f'If({EDITING}, "Save changes", "Submit issue")',
                    submit_fx, primary=True,
                    width=fit_button_width('"Save changes"') + ICON_W, height=36,
                    icon=f'If({EDITING}, "Save", "Send")',
                    display_mode=panel_save_mode(IB_SAVE, idle))
    # "Saving..." / "Submitting..." i knappen, mens der gemmes (issue #420).
    panel_save_text(submit, IB_SAVE, "Submitting...",
                    f'If({EDITING}, "Saving...", "Submitting...")')
    footer = group("conIbFormFooter", [submit], direction="Horizontal", gap=8,
                   height=36, justify="End", align_items="Center")
    status = panel_save_status("Ib", IB_SAVE, submit_fx, idle)
    foot = group("conIbFormFoot", [footer, status, missing], direction="Vertical", gap=8)
    kids = [head, intro, where, sec_hint, other_f, title_f, similar, desc_f, more, details,
            manage, context]
    # Foden staar fast under det, der scroller: Submit kan altid naas.
    return [*_popup("IbForm", kids, FORM_ON, width=FORM_W, foot=foot, side_panel=True,
                    close_fx=CLOSE_ASK), *build_discard()]


# ---------------------------------------------------------------------------
# En sag i View mode
# ---------------------------------------------------------------------------
DETAIL_ON = "IfError(varIbDetailOn, false)"
SEL = "varIbSel"
DETAIL_PANEL_W = lay.PANEL_W_AT
DETAIL_PANEL_IN = f"({DETAIL_PANEL_W} - {2 * POP_PAD})"
DET_IN = f"({DETAIL_PANEL_IN} - {lay.SCROLLBAR_W})"
ACT_ROW_PAD = 12
# Kommentarfeltet (issue #411): hoejden og ikonets afstand til feltets kant.
COMMENT_H = 72
SEND_INSET = 4
ACT_W = f"({DET_IN} - {lay.SCROLLBAR_W} - {lay.GALLERY_RESERVE})"
ACT_BODY_W = f"({ACT_W} - {2 * ACT_ROW_PAD})"
# Indholdsfladen i sagens popup: mindst saa hoej, naar skaermen tillader det -
# og aldrig lavere end DET_SAFE_MIN_H (issue #212).
DET_MIN_H = 200
DET_SAFE_MIN_H = 160

# Efter enhver aendring gennem flowet (issue #229 - live): KUN den ene
# sag (LookUp paa ID, skrevet ind i listen med UpdateIf) og dens Activity
# - ingen ny hentning af listen. Filtre, sortering, den aabne sag og den
# valgte fane bliver staaende. Activity kun for rapportoeren og admins.
AFTER_CHANGE = RELOAD_SEL + ";\nIf(IbSeeActivity,\n" + LOAD_ACTIVITY + "\n)"


# Knappernes ventetilstand (issue #420, build_helpers.act_fx): "reopen",
# "archive", "delete" eller "upload", mens kaldet koerer, og
# "<noegle>:ok"/":failed" bagefter. Foer var det et graat sloer med en
# bjaelke midt paa skaermen (varIbBusy/varIbUploading - de spaerrer stadig
# de andre knapper).
IB_ACT = "varIbAct"


def _run(action, payload, ok_fx, fail_text, key, busy="varIbBusy"):
    """Et kald til flowet med knappens ventetilstand og svar. ok_fx koeres
    kun, naar flowet svarer ok - ellers staar flowets egen grund i
    beskeden, og "Reopen failed" o.l. ved knappen."""
    body = (
        f"Set(varIbRes, IfError({cfg.FLOW}.Run(\n"
        f'    "{action}",\n'
        f"    JSON({payload})\n"
        f"), {FALLBACK}));\n"
        "If(\n"
        '    varIbRes.ok = "yes",\n'
        f"    {act_mark(IB_ACT, key)};\n"
        "    " + ok_fx.replace("\n", "\n    ") + ",\n"
        f"    {act_mark(IB_ACT, key, False)};\n"
        f'    Notify("{fail_text} " & varIbRes.message, NotificationType.Error)\n'
        ")"
    )
    return act_fx(IB_ACT, key, body, busy_var=busy)


# Kommentar og intern note (issue #212): flowet svarer foerst, naar
# raekken er skrevet. Saa saettes den samme raekke ind sidst i feeden - den
# nyeste, altsaa i den rigtige raekkefoelge - uden at hente hele Activity
# igen: intet blink, intet ekstra kald. Rollen er flowets egen regel (Admin,
# naar en admin skriver paa en andens sag).
#
# VENTETIDEN STAAR I KOMMENTARFELTET (issue #370). Intet sloer over hele skaermen: send-ikonet erstattes af et lille hjul
# (issue #411) og teksten under feltet skifter (varIbPostStage: "posting" -> "updating" ->
# "done" eller "failed"). Resten af appen kan bruges imens. Teksten, sagen og
# "intern" gemmes FOER kaldet (varIbPostText/-For/-Internal): svaret skrives
# paa den sag, kommentaren hoerer til, ogsaa hvis man har aabnet en anden
# imens - og feeden faar kun raekken, naar den samme sag stadig er aaben.
# Feltet toemmes foerst ved succes; fejler kaldet, staar teksten der igen
# (inpIbComment.Default) med Retry. Eget svar (varIbPostRes): Reopen eller
# Archive imens maa ikke overskrive varIbRes under kommentaren.
#
# HURTIGERE (issue #384). Kaldet tog omkring 10 sekunder, fordi flowet
# lavede 7 + 2 x (antal admins) SharePoint-kald efter hinanden, foer det
# svarede. Nu: sagen og admin-listen hentes samtidig, rapportoeren slaas op
# samtidig med Touch_ticket, og admins' rettigheder paa raekken gives EFTER
# svaret (en fejl der har aldrig rullet kommentaren tilbage). Foer svaret:
# raekken skrevet, nedarvningen brudt og rapportoeren Read. Ventetilstanden
# foelger kaldet: hjulet staar, til svaret er der - ingen fast varighed, og
# teksten lover ingen bestemt tid.
POSTING_HERE = ('varIbPostFor = varIbSelId && '
                '(varIbPostStage = "posting" || varIbPostStage = "updating")')
POST_FAILED_HERE = 'varIbPostFor = varIbSelId && varIbPostStage = "failed"'
POST_DONE_HERE = 'varIbPostFor = varIbSelId && varIbPostStage = "done"'
# Sekunder siden klik - timeren tmrIbPost flytter varIbPostTick.
POST_SECS = "DateDiff(varIbPostAt, varIbPostTick, TimeUnit.Seconds)"
POST_STAGE_TEXT = (
    'If(varIbPostStage = "updating", "Updating activity...", '
    f'{POST_SECS} >= 3, "Still posting, please wait...", '
    'If(varIbPostInternal, "Adding internal note...", "Posting comment..."))'
)
POST_ROW = (
    '{ Kind: "Comment", Actor: "You", '
    f'Role: If({IS_ADMIN} && !IbSelMine, "Admin", "User"), '
    "Body: varIbPostText, At: Now(), "
    "Internal: varIbPostInternal, IsSystem: false, "
    'File: "", SizeKb: 0, Initial: false }'
)
POST_ACT_N = set_act_n("varIbPostFor", "Coalesce(LookUp(colIbActN, TicketId = varIbPostFor).N, 0) + 1")
POST = (
    "If(\n"
    "    !varIbPosting && !IsBlank(Trim(inpIbComment.Text)),\n"
    "    Set(varIbPostText, Trim(inpIbComment.Text));\n"
    f"    Set(varIbPostInternal, varIbInternal && {IS_ADMIN});\n"
    "    Set(varIbPostFor, varIbSelId);\n"
    "    Set(varIbPostAt, Now());\n"
    "    Set(varIbPostTick, Now());\n"
    '    Set(varIbPostErr, "");\n'
    '    Set(varIbPostStage, "posting");\n'
    "    Set(varIbPosting, true);\n"
    f"    Set(varIbPostRes, IfError({cfg.FLOW}.Run(\n"
    f'        "{cfg.ACT_COMMENT}",\n'
    "        JSON({ ticketId: varIbPostFor, content: varIbPostText, internal: varIbPostInternal })\n"
    f"    ), {FALLBACK}));\n"
    "    If(\n"
    '        varIbPostRes.ok = "yes",\n'
    '        Set(varIbPostStage, "updating");\n'
    "        If(\n"
    "            varIbSelId = varIbPostFor,\n"
    f"            Collect(colIbActivity, {POST_ROW});\n"
    "            Reset(inpIbComment);\n"
    "            Set(varIbSel, Patch(varIbSel, { UpdatedOn: Now() }));\n"
    "            Set(varIbInternal, false);\n"
    "            Reset(chkIbInternal)\n"
    "        );\n"
    "        UpdateIf(colIbAll, Id = varIbPostFor, { UpdatedOn: Now() });\n"
    # Issue #422: taelleren i oversigten - een mere paa den sag,
    # kommentaren hoerer til.
    f"        {POST_ACT_N};\n"
    "        Set(varIbPostAt, Now());\n"
    "        Set(varIbPostTick, Now());\n"
    '        Set(varIbPostStage, "done"),\n'
    "        Set(varIbPostErr, varIbPostRes.message);\n"
    '        Set(varIbPostStage, "failed")\n'
    "    );\n"
    "    Set(varIbPosting, false)\n"
    ")"
)

REOPEN = _run(
    cfg.ACT_REOPEN, '{ ticketId: varIbSelId, reason: "" }',
    AFTER_CHANGE + ";\n"
    # Filtrene roeres ikke (issue #229) - raekken er opdateret i listen.
    'Notify("The issue has been reopened. An administrator will look at it again.", '
    "NotificationType.Success)",
    "The issue could not be reopened.", "reopen")

ARCHIVE = _run(
    cfg.ACT_ARCHIVE, f"{{ ticketId: varIbSelId, archived: !{SEL}.Archived }}",
    AFTER_CHANGE + ";\n"
    f'Notify(If({SEL}.Archived, "The issue has been archived. It is kept under Archived.", '
    '"The issue has been restored."), NotificationType.Success)',
    "The issue could not be changed.", "archive")

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
    "The issue could not be deleted.", "delete")

# Gem filerne (issue #300): EEN Patch af sagens Attachments med kontrollens
# Attachments-output - nye filer laegges paa, fjernede slettes. Ingen flow
# og ingen Attachment-haendelse i Activity. En fil med et navn, der
# allerede findes, faar selv et suffiks af kontrollen (MS Learn), saa
# appens eget dublet-tjek er ikke noedvendigt mere. Bagefter hentes sagen
# og filerne igen (AFTER_CHANGE).
# Knappens tilstand (issue #420): "upload" mens der gemmes; succes-grenen
# skriver ":ok", og en Patch, der fejlede, efterlader ":failed".
UPLOAD_FILES = act_fx(IB_ACT, "upload", attflows.save_fx(
    cfg.L_TICKETS, f"LookUp({cfg.L_TICKETS}, ID = varIbSelId)", "attIbFiles",
    "varIbUploading", None, AFTER_CHANGE + ";",
    on_ok=act_mark(IB_ACT, "upload") + ";",
    extra_fields=", LastActivityOn: Now()"), left="failed")


# Issue #369: indholdet i fanen Description staar hver i sin diskrete
# flade (tynd kant, runde hjoerner) med etiketten lige over, og teksten
# er en anelse stoerre end broedteksten. Fladen er lige saa hoej som
# teksten (_lines_h) plus sin luft - aldrig en fast hoejde.
DET_TEXT_SIZE = lay.SIZE_BODY + 1
DET_TEXT_LINE = text_min_height(DET_TEXT_SIZE)
DET_TEXT_PX = 7.8
BOX_PAD_X = 12
BOX_PAD_Y = 8
# Kanten (1 px paa hver side) tages ogsaa fra tekstens bredde.
BOX_TEXT_W = f"({DET_IN} - {2 * BOX_PAD_X} - 2)"


def _text_block(name, label, expr, visible=None):
    """En etiket og en tekst, der ombrydes, i en diskret flade - laest,
    ikke redigeret (issue #369)."""
    lab = text_ctrl(f"txt{name}Label", f'"{label}"', size=lay.SIZE_SMALL, weight="Semibold",
                    color=C_MUTED, height=18)
    h = _lines_h(expr, BOX_TEXT_W, px=DET_TEXT_PX, line_h=DET_TEXT_LINE)
    body = text_ctrl(f"txt{name}", expr, size=DET_TEXT_SIZE, height=h, wrap="true",
                     accessible=f'"{label}: " & Self.Text')
    box = group(f"con{name}Box", [body], direction="Vertical", gap=0, fill=C_CARD_BG,
                border_color=C_CARD_BORDER, radius=8, pad=(BOX_PAD_Y, BOX_PAD_X, BOX_PAD_Y, BOX_PAD_X))
    return group(f"con{name}", [lab, box], direction="Vertical", gap=4, visible=visible)


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


ICON_BTN = lay.HIT_TOUCH


def _icon_action(name, icon, onselect, visible, label, tooltip, display_mode, danger=False):
    """En handling paa sagen som ikon (issue #229): kun ikonet, engelsk
    tooltip og etiket, med kant (som de andre knapper)."""
    b = button(name, label, onselect, width=ICON_BTN, height=ICON_BTN, icon=icon,
               visible=visible, accessible=label, tooltip=tooltip, display_mode=display_mode,
               danger=danger)
    b.props["Layout"] = "ButtonLayout.IconOnly"
    b.props["Appearance"] = "ButtonAppearance.Outline"
    b.props["BorderColor"] = C_INVALID_FG if danger else C_INPUT_BORDER
    b.props["BorderThickness"] = "1"
    b.props["BorderStyle"] = "BorderStyle.Solid"
    b.props["LayoutMinWidth"] = str(ICON_BTN)
    ensure_hit(b)
    return b


# Handlingsraekken vises, naar mindst een af handlingerne er tilladt.
CAN_ACT = "IbCanReopen || IbCanEdit || IbCanManage"
ACT_PAD = 3


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
    # "Reopening..." i knappen (issue #420). Ikon-knapperne har ingen tekst
    # at skifte - hjulet foran raekken viser, at kaldet koerer (kun for
    # dem, issue #441).
    act_button(reopen, IB_ACT, "reopen")
    # Edit foerst, naar sagens hele raekke er hentet - ellers kunne de
    # felter, oversigten ikke henter, blive gemt tomme.
    ready = "varIbSelFullFor = varIbSelId"
    edit = _icon_action("btnIbEdit", "Edit", OPEN_EDIT, "IbCanEdit", '"Edit issue"',
                        f'If({ready}, "Edit issue", "Edit issue - loading the issue...")',
                        f"If({ready} && !varIbBusy, DisplayMode.Edit, DisplayMode.Disabled)")
    idle = "If(varIbBusy, DisplayMode.Disabled, DisplayMode.Edit)"
    show_archive = f"IbCanManage && !{SEL}.Archived"
    # ModernButton kender ikke Fluent-navnet "Archive" (knappen blev tom),
    # saa arkivkassen er vores eget stregikon - med samme kant som de andre.
    archive = icon_button("btnIbArchive", "Archive issue", ARCHIVE, icons.ARCHIVE, idle)
    archive.props["Tooltip"] = ('"Archive issue - keeps the issue, its comments, activity and '
                                'files under Archived"')
    archive.props["BorderColor"] = C_INPUT_BORDER
    archive.props["BorderStyle"] = "BorderStyle.Solid"
    archive.props["BorderThickness"] = "1"
    archive.props["Visible"] = show_archive
    archive.vis = show_archive
    show_restore = f"IbCanManage && {SEL}.Archived"
    restore = _icon_action("btnIbRestore", "ArrowUndo", ARCHIVE, show_restore, '"Restore issue"',
                           '"Restore issue - bring it back to the active lists"', idle)
    delete = _icon_action("btnIbDelete", "Delete", "Reset(inpIbDelConfirm);\nSet(varIbDelOn, true)",
                          "IbCanManage", '"Delete issue"',
                          '"Delete issue permanently - you confirm first"',
                          "If(varIbBusy, DisplayMode.Disabled, DisplayMode.Edit)", danger=True)
    # "Reopened"/"Update failed" foran knapperne (issue #420). Hjulet kun
    # for Archive/Restore - de er ikoner uden tekst; Reopen siger selv
    # "Reopening..." (issue #441). Delete koerer i sin egen popup og viser
    # sin tilstand dér.
    status = act_status("IbDetAct", IB_ACT, ("reopen", "archive"),
                        spin={"archive": icon_only_when(archive)})
    assert icon_only_when(restore) == "true"
    row = group("conIbDetActions", [*status, reopen, edit, archive, restore, delete],
                direction="Horizontal",
                gap=4, height=f"{hit_size(ICON_BTN)} + 2 * {ACT_PAD}", align_items="Center",
                justify="End", visible=CAN_ACT)
    # Luft over og under knapperne: kanten og fokusrammen tegnes uden for
    # knappen, og en raekke paa praecis knappens hoejde skar dem af
    # (Archive blev skaaret i toppen).
    row.props["PaddingTop"] = str(ACT_PAD)
    row.props["PaddingBottom"] = str(ACT_PAD)
    row.props["LayoutJustifyContent"] = (f"If({NARROW}, LayoutJustifyContent.Start, "
                                         "LayoutJustifyContent.End)")
    return row


def _files_panel():
    """Fanen Attachments: sagens vedhaeftninger i den moderne kontrol
    (issue #300). Den viser, aabner og - mens sagen kan rettes - fjerner
    filerne selv; "Save documents" gemmer aendringerne."""
    state = text_ctrl(
        "txtIbFilesState",
        'If(varIbFilesBusy, "Loading attachments...", IfError(varIbFilesFailed, false), '
        '"The attachments could not be loaded. Select the tab again to retry.", '
        '"No files yet. Screenshots help a lot.")',
        size=lay.SIZE_BODY, color=f"If(IfError(varIbFilesFailed, false), {C_INVALID_FG}, {C_MUTED})",
        height=20, wrap="true",
        visible=f"varIbFilesBusy || IfError(varIbFilesFailed, false) || CountRows({FILES_ITEMS}) = 0")
    picker = _attachments("attIbFiles", '"Attachments on this issue"')
    up = button("btnIbUpload", du.SAVE_TEXT, UPLOAD_FILES, primary=True,
                width=fit_button_width(du.SAVE_TEXT) + ICON_W, height=36, icon="Save",
                accessible='"Save the attachments on this issue"',
                display_mode=("If(attIbFiles.IsUploading || varIbUploading || "
                              "varIbFilesFor <> varIbSelId, DisplayMode.Disabled, DisplayMode.Edit)"))
    # "Saving..." i knappen og hjulet/beskeden lige foran den (issue #420).
    act_button(up, IB_ACT, "upload")
    up_row = group("conIbFileSave", [*act_status("IbFilesAct", IB_ACT, ("upload",)), up],
                   direction="Horizontal", gap=8, height=36, justify="End",
                   align_items="Center")
    hint = text_ctrl("txtIbFilesHint",
                     f'"Up to {cfg.MAX_FILES} files, {cfg.MAX_FILE_MB} MB each. Everyone '
                     'who uses the Issue Board can open the files - leave out personal data."',
                     size=lay.SIZE_SMALL, color=C_MUTED, height=34, wrap="true")
    adder = group("conIbFileAdd", [hint, up_row], direction="Vertical", gap=8,
                  visible="IbCanAttach")
    panel = group("conIbDetFiles", [state, picker, adder], direction="Vertical", gap=12,
                  visible='varIbTab = "files"')
    # Kontrollen fylder fanens flade (issue #344) - fanen er lige saa hoej
    # som indholdsfladen (build_detail: Height = Parent.Height).
    du.fit_picker(picker, panel.children, 12)
    return panel


FACT_VAL_H = 20
FACT_INNER = 2
FACT_LAB_H = text_min_height(lay.SIZE_MICRO)
FACT_H = FACT_LAB_H + FACT_INNER + FACT_VAL_H
FACT_GAP = 12
# Fem fakta paa een linje, naar popuppen er bred nok; ellers tre og to.
FACTS_OK = f"({DET_IN}) >= 540"
FACT_W = f"If({FACTS_OK}, (({DET_IN}) - 4 * {FACT_GAP}) / 5, (({DET_IN}) - 2 * {FACT_GAP}) / 3)"
# Issue information (issue #369): Application, Section og Priority - altid
# tre kolonner, saa de flugter med de tre foerste fakta paa en smal popup.
INFO_W = f"((({DET_IN}) - 2 * {FACT_GAP}) / 3)"
SECTION_H = 18


def _section_title(name, title):
    """En sektions overskrift i sagens popup - som formularernes
    (domain_parts.form_section): lille, fed, daempet og med versaler."""
    return text_ctrl(name, f'Upper("{title}")', size=lay.SIZE_MICRO, weight="Semibold",
                     color=C_MUTED, height=SECTION_H, accessible=f'"{title}"')


_MID = {"VerticalAlign": "VerticalAlign.Middle", "LayoutMinWidth": "0"}


def _fact(name, label, value_fx, visible=None, width=FACT_W, height=FACT_VAL_H, wrap="false"):
    """Etiket og vaerdi (to tekster med egen bredde og hoejde)."""
    lab = text_ctrl(f"txt{name}Label", f'"{label}"', size=lay.SIZE_MICRO, weight="Semibold",
                    color=C_MUTED, height=FACT_LAB_H, width=width, visible=visible,
                    extra=dict(_MID))
    extra = dict(_MID)
    if wrap == "true":
        extra["VerticalAlign"] = "VerticalAlign.Top"
    val = text_ctrl(f"txt{name}", value_fx, size=lay.SIZE_BODY, height=height, width=width,
                    accessible=f'"{label}: " & Self.Text', visible=visible, wrap=wrap,
                    extra=extra)
    return lab, val


def _fact_block(name, labels, values, width, val_h=FACT_VAL_H):
    """En raekke etiketter over en raekke vaerdier."""
    labs = group(f"con{name}Labels", labels, direction="Horizontal",
                 gap=FACT_GAP, height=FACT_LAB_H, width=width, align_items="Start")
    vals = group(f"con{name}Values", values, direction="Horizontal",
                 gap=FACT_GAP, height=val_h, width=width, align_items="Start")
    g = group(f"con{name}", [labs, vals], direction="Vertical", gap=FACT_INNER,
              height=f"{FACT_LAB_H} + {FACT_INNER} + {val_h}", width=width, align_items="Start")
    for c in (labs, vals, g):
        c.props["LayoutMinWidth"] = "0"
    return g


def _info():
    """Issue information (issue #369): Application, Section og Priority
    under en overskrift - prioriteten som sit farvede maerke. En lang
    Application eller Section ombrydes, og raekken vokser med den."""
    val_h = (f"Max({CHIP_H}, {_lines_h(SEL + '.Application', INFO_W)}, "
             f"{_lines_h(SEL + '.Section', INFO_W)})")
    app_lab, app = _fact("IbDetApp", "Application", f"{SEL}.Application", width=INFO_W,
                         height=val_h, wrap="true")
    app.props["FontWeight"] = "FontWeight.Semibold"
    sec_lab, sec = _fact("IbDetSection", "Section", f"{SEL}.Section", width=INFO_W,
                         height=val_h, wrap="true")
    pri_lab = text_ctrl("txtIbDetPriorityLabel", '"Priority"', size=lay.SIZE_MICRO,
                        weight="Semibold", color=C_MUTED, height=FACT_LAB_H, width=INFO_W,
                        extra=dict(_MID))
    pri, _pri_w = _text_chip("bdgIbDetPriority", f"{SEL}.Priority", sc.PRIORITY, '"Priority: "',
                             visible=f"!IsBlank({SEL}.Priority)")
    no_pri = text_ctrl("txtIbDetPriorityNone", '"Not set"', size=lay.SIZE_BODY, color=C_MUTED,
                       height=CHIP_H, width=INFO_W, visible=f"IsBlank({SEL}.Priority)",
                       accessible='"Priority: not set"', extra=dict(_MID))
    block = _fact_block("IbDetInfoFacts", [app_lab, sec_lab, pri_lab], [app, sec, pri, no_pri],
                        DET_IN, val_h=val_h)
    return group("conIbDetInfo", [_section_title("txtIbDetInfoTitle", "Issue information"), block],
                 direction="Vertical", gap=4)


def _facts():
    """Metadata om sagen som etiket/vaerdi (issue #229): Requester,
    Assigned to, Severity, Reported og Updated. Rapportoeren som kort
    bruger-id (UFFES) - ingen anonymisering (issue #193, #212). Updated
    kun efter en reel aendring, og sidst, saa der ikke opstaar et hul.
    Issue #369: under overskriften "Ticket details".

    Bygget som vandrette raekker af tekster med egen bredde og hoejde. De
    lodrette etiket/vaerdi-grupper med strakte tekster og den dynamiske
    LayoutDirection viste sig i Studio, men var tomme i Play og preview.
    Blok 1 (tre fakta) og blok 2 (to) staar paa een linje, naar popuppen
    er bred nok; ellers brydes blok 2 ned under (LayoutWrap)."""
    def blank_as(expr, text):
        return f'If(IsBlank({expr}), "{text}", {expr})'

    def block(name, facts, n):
        w = f"{n} * {FACT_W} + {n - 1} * {FACT_GAP}"
        return _fact_block(name, [f[0] for f in facts], [f[1] for f in facts], w)

    rep = _fact("IbFactReporter", "Requester", REPORTER_FX.format(r=SEL))
    asg = _fact("IbFactAssigned", "Assigned to", blank_as(SEL + ".Assigned", "Unassigned"))
    sev = _fact("IbFactSeverity", "Severity", blank_as(f"{SEL}.Severity", "Not set"))
    reported = _fact("IbFactReported", "Reported", f"Text({SEL}.CreatedOn, {DATE_FMT})")
    updated = _fact("IbFactUpdated", "Updated", f"Text(IbSelUpdatedOn, {DATE_FMT})",
                    visible="!IsBlank(IbSelUpdatedOn)")
    a = block("IbFacts1", [rep, asg, sev], 3)
    b = block("IbFacts2", [reported, updated], 2)
    g = group("conIbDetFactRows", [a, b], direction="Horizontal", gap=FACT_GAP,
              height=f"If({FACTS_OK}, {FACT_H}, 2 * {FACT_H} + {FACT_GAP})", align_items="Start")
    g.props["LayoutWrap"] = "true"
    g.props["LayoutMinWidth"] = "0"
    return group("conIbDetFacts", [_section_title("txtIbDetFactsTitle", "Ticket details"), g],
                 direction="Vertical", gap=4)


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
    no = _no_badge("bdgIbDetNo", f"{SEL}.TicketNo")
    no.props["LayoutMinWidth"] = str(NO_W)
    # Bladring: raekkefoelgen er listens (filtreret og sorteret) - galIbList.AllItems.
    nav_list = "galIbList.AllItems"
    pos = (f"Coalesce(First(Filter(ForAll(Sequence(galIbList.AllItemsCount), "
           f"{{n: Value, id: IfError(Index({nav_list}, Value).Id, Blank())}}), id = varIbSelId)).n, 0)")
    prev_mode = f"If(varIbSelPeek || {pos} <= 1, DisplayMode.Disabled, DisplayMode.Edit)"
    next_mode = (f"If(varIbSelPeek || {pos} = 0 || {pos} >= galIbList.AllItemsCount, "
                 f"DisplayMode.Disabled, DisplayMode.Edit)")
    prev_fx = f"With({{r: LookUp(colIbAll, Id = Index({nav_list}, {pos} - 1).Id)}}, {open_ticket('r', 'false')})"
    next_fx = f"With({{r: LookUp(colIbAll, Id = Index({nav_list}, {pos} + 1).Id)}}, {open_ticket('r', 'false')})"
    nav = [icon_button("btnIbDetPrevious", "Previous issue", prev_fx, icons.CHEVRON_LEFT, prev_mode),
           icon_button("btnIbDetNext", "Next issue", next_fx, icons.CHEVRON_RIGHT, next_mode)]
    # Kun en sag i listen: ingen pile.
    for arrow in nav:
        arrow.props["Visible"] = "galIbList.AllItemsCount > 1"
        arrow.vis = "galIbList.AllItemsCount > 1"
    head = _head("IbDet", f"{SEL}.Title", "Set(varIbDetailOn, false)",
                 lead=[no], title_w=f"({DETAIL_PANEL_IN}) - {NO_W} - {3 * lay.HIT_TOUCH} - 30",
                 close_icon=True, nav=nav)

    # 2. Status som maerke lige under titlen (issue #369). Prioriteten,
    #    Application og Section staar under Issue information - ikke to
    #    steder.
    # Maerkerne er tekster med statussens farvepar (som sagsnummeret,
    # _no_badge) - SVG-billederne (sc.status_chip) var tomme i Play her.
    key = f'If({SEL}.Archived, "Archived", {SEL}.Status)'
    chip, _chip_w = _text_chip("bdgIbDetStatus", key, ISSUE_STATUS, '"Status: "')
    meta = group("conIbDetMeta", [chip], direction="Horizontal", gap=8, height=CHIP_H,
                 align_items="Start")
    info = _info()

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
                       '"This issue is ready for retest. Please try it again - if the problem is '
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
    # Rollen som ModernBadge (#304) - samme farvepar og maal.
    role = modern_badge("bdgIbActRole", "ThisItem.Role", color=rfg, fill=rbg, height=20,
                        width=ROLE_W, radius=10, accessible='"Role: " & Self.Content',
                        extra={"X": str(ACT_ROW_PAD), "Y": "8"})
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

    # Fejler kaldet, kommer teksten tilbage (issue #370): Default er den
    # gemte tekst, saa laenge kommentaren paa DENNE sag er fejlet - ogsaa
    # efter et skift til en anden sag og tilbage (open_ticket nulstiller).
    # KOMMENTARFELTET MED SEND-IKONET (issue #411). Feltet og ikonet staar i
    # EEN ManualLayout-container (conIbCommentBox), der er lige saa bred som
    # Activity-fanens indhold (Parent.Width - ingen egen bredde): ikonet
    # ligger nederst til hoejre inden i feltet, og feltet har polstring til
    # hoejre, saa teksten aldrig loeber ind under ikonet. Venstre polstring
    # er ACT_ROW_PAD - teksten flugter med teksten i kommentarerne over.
    # Mens kommentaren sendes, staar et lille hjul i ikonets sted (kun
    # her), feltet er skrivebeskyttet, og teksten under feltet siger, hvor
    # langt den er (issue #370's trin). Toemmes foerst ved succes.
    #
    # Fejler kaldet, kommer teksten tilbage (issue #370): Default er den
    # gemte tekst, saa laenge kommentaren paa DENNE sag er fejlet - ogsaa
    # efter et skift til en anden sag og tilbage (open_ticket nulstiller).
    comment = text_input("inpIbComment", f'If({POST_FAILED_HERE}, varIbPostText, "")',
                         placeholder=(f'If(varIbInternal, "Write an internal note for the administrators", '
                                      f'{IS_ADMIN} && !IbSelMine, "Write a reply to the reporter", '
                                      '"Write a comment for the administrators")'),
                         max_length=2000, height=COMMENT_H, ttype="Multiline", label='"Comment"',
                         display_mode=f"If({POSTING_HERE}, DisplayMode.View, DisplayMode.Edit)")
    # Send-ikonet laases op, mens man skriver - ikke foerst, naar feltet
    # mister fokus (saa ville det foerste klik paa ikonet gaa tabt).
    comment.props["TriggerOutput"] = "TriggerOutput.Keypress"
    comment.props.pop("LayoutMinWidth", None)
    comment.props.update({
        "X": "0", "Y": "0", "Width": "Parent.Width",
        "PaddingLeft": str(ACT_ROW_PAD),
        "PaddingRight": f"{lay.HIT} + {2 * SEND_INSET}",
        "PaddingTop": "8", "PaddingBottom": "8",
    })
    send_label = 'If(varIbInternal, "Add internal note", "Post comment")'
    post = button("btnIbPost", send_label, POST, width=lay.HIT, height=lay.HIT, icon="Send",
                  accessible=send_label, tooltip=send_label,
                  display_mode=("If(IsBlank(Trim(inpIbComment.Text)) || varIbPosting, "
                                "DisplayMode.Disabled, DisplayMode.Edit)"),
                  visible=f"!({POSTING_HERE})")
    for k in ("AlignInContainer", "LayoutMinWidth", "BorderColor", "BorderThickness"):
        post.props.pop(k, None)
    post.props.update({
        "Layout": "ButtonLayout.IconOnly",
        "Appearance": "ButtonAppearance.Transparent",
        "BasePaletteColor": C_PRIMARY,
        "Color": C_PRIMARY,
        "X": f"Parent.Width - Self.Width - {SEND_INSET}",
        "Y": f"Parent.Height - Self.Height - {SEND_INSET}",
    })
    post_spin = spinner("spnIbPosting", POSTING_HERE, POST_STAGE_TEXT,
                        width=lay.HIT, height=lay.HIT)
    post_spin.props.update({
        "X": f"Parent.Width - Self.Width - {SEND_INSET}",
        "Y": f"Parent.Height - Self.Height - {SEND_INSET}",
    })
    box = Ctrl("conIbCommentBox", "GroupContainer", variant="ManualLayout", props={
        "BorderStyle": "BorderStyle.None", "DropShadow": "DropShadow.None",
        "FillPortions": "0", "Height": str(COMMENT_H), "LayoutMinWidth": "0",
        "Width": "Parent.Width",
    }, children=[comment, post, post_spin], h=COMMENT_H)
    internal = Ctrl("chkIbInternal", "ModernCheckbox", props=checkbox_theme({
        "AccessibleLabel": '"Internal note - only administrators can see it"',
        "Default": "varIbInternal",
        "DisplayMode": f"If({POSTING_HERE}, DisplayMode.Disabled, DisplayMode.Edit)",
        "Height": "24",
        "Label": '"Internal note - only administrators can see it"',
        "OnCheck": "Set(varIbInternal, true)",
        "OnUncheck": "Set(varIbInternal, false)",
        "Visible": IS_ADMIN,
        "Width": "Parent.Width",
    }), h=24, vis=IS_ADMIN)
    # Hjaelpeteksten er kun saa hoej, som teksten kraever (een linje paa en
    # bred skaerm) - ikke en fast to-linjers flade. Mens der sendes, siger
    # den, hvor langt kommentaren er (som hjulets tekst foer #411).
    hint_fx = (f'If({POSTING_HERE}, {POST_STAGE_TEXT} & " You can keep using the app meanwhile.", '
               f'varIbInternal, "Internal notes are never shown to the reporter.", '
               f'{SEL}.Status = "{cfg.STATUS_CLOSED}", '
               '"This issue is closed. If the problem is back, select Reopen - or add a comment.", '
               '"Comments are visible to the reporter and the administrators only.")')
    hint_h = f"Max(18, {_lines_h(hint_fx, DET_IN, px=6.6, line_h=17)})"
    closed_hint = text_ctrl("txtIbCommentHint", hint_fx, size=lay.SIZE_SMALL, color=C_MUTED,
                            height=hint_h, wrap="true")
    composer = group("conIbComposer", [box, internal, closed_hint], direction="Vertical",
                     gap=4, visible="IbCanComment")
    # Sendt: en kort bekraeftelse over det tomme felt - timeren (tmrIbPost)
    # fjerner den efter et par sekunder, og den gaar ogsaa, naar man skriver.
    posted = text_ctrl("txtIbPosted",
                       'If(varIbPostInternal, "Internal note added.", "Comment posted.")',
                       size=lay.SIZE_BODY, weight="Semibold", color=C_VALID_FG, height=36,
                       visible=f"IbCanComment && ({POST_DONE_HERE}) && IsBlank(inpIbComment.Text)",
                       extra={"Fill": C_VALID_BG, "PaddingLeft": "12", "PaddingRight": "12",
                              "VerticalAlign": "VerticalAlign.Middle", **lay.radius(10)})
    # Fejlet: grunden og Retry. Teksten staar i feltet nedenunder igen.
    retry_w = fit_button_width('"Retry"') + ICON_W
    fail_msg = ('If(varIbPostInternal, "The internal note could not be added.", '
                '"The comment could not be posted.") & " Your text is kept below." & '
                'If(IsBlank(varIbPostErr), "", " " & Left(varIbPostErr, 200))')
    fail_h = f"Max(36, {_lines_h(fail_msg, f'{DET_IN} - 20 - {retry_w} - 8', px=6.6)})"
    fail_text = text_ctrl("txtIbPostFailed", fail_msg, size=lay.SIZE_SMALL, color=C_INVALID_FG,
                          height=fail_h, wrap="true",
                          extra={"VerticalAlign": "VerticalAlign.Middle"})
    grow(fail_text)
    retry = button("btnIbPostRetry", '"Retry"', POST, width=retry_w, height=36,
                   icon="ArrowClockwise", accessible='"Retry posting the comment"',
                   display_mode=("If(IsBlank(Trim(inpIbComment.Text)) || varIbPosting, "
                                 "DisplayMode.Disabled, DisplayMode.Edit)"))
    failed = group("conIbPostFailed", [fail_text, retry], direction="Horizontal", gap=8,
                   height=f"({fail_h}) + 16", align_items="Center", fill=C_MUTED_BG, radius=10,
                   pad=(8, 8, 8, 12), visible=f"IbCanComment && ({POST_FAILED_HERE})")
    archived_hint = text_ctrl("txtIbArchivedHint",
                              '"This issue is archived. Its history is kept, and comments are '
                              'closed."',
                              size=lay.SIZE_SMALL, color=C_MUTED, height=18,
                              visible=f"{SEL}.Archived")
    activity = group("conIbDetActivity", [act_state, gal, posted, failed, composer,
                                          archived_hint],
                     direction="Vertical", gap=8, visible='IbSeeActivity && varIbTab = "activity"')

    # STABIL HOEJDE (issue #212). Toppen - status, fakta, handlingerne og
    # fanerne - staar fast; under den EEN indholdsflade med samme hoejde for
    # alle tre faner: den fane, der kraever mest, bestemmer den (mindst
    # DET_MIN_H), og den er aldrig hoejere end skaermen tillader. Hver fane
    # scroller selv, saa hver har sin egen scrollposition.
    top = group("conIbDetTop", [meta, info, facts, actions, peek_note, retest, rule, tabs],
                direction="Vertical", gap=8)
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
    return _popup("IbDet", [head, top, content], DETAIL_ON, own_scroll=True,
                  side_panel=True)


def build_delete():
    """Permanent sletning - sin egen popup oven paa sagen. Nummeret skal
    skrives, teksten siger, at det ikke kan fortrydes, og knappen er laast,
    til nummeret passer, og mens kaldet koerer. Close er eneste vej ud."""
    del_on = "IfError(varIbDelOn, false)"
    head = _head("IbDel", f'"Delete " & {SEL}.TicketNo & " permanently?"',
                 'Set(varIbDelOn, false);\nIf(IfError(varIbAct = "delete:failed", false), '
                 'Set(varIbAct, ""))')
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
    # "Deleting..." i knappen (eet ventetegn, #441); popuppen lukker, naar
    # sagen er slettet - ellers staar "Delete failed" her (issue #420).
    act_button(ok, IB_ACT, "delete")
    footer = group("conIbDelFooter", [*act_status("IbDelAct", IB_ACT, ("delete",)), ok],
                   direction="Horizontal", gap=8, height=36,
                   justify="End", align_items="Center")
    return [_popup("IbDel", [head, warn, confirm_f], del_on, width="Min(480, App.Width - 24)",
                   foot=footer)]


def _post_timer():
    """Mens en kommentar sendes og lige efter (issue #370): hvert sekund
    flyttes varIbPostTick, saa teksten ved hjulet kan skifte; "Comment
    posted." staar i 2,5 sekunder. Taeller kun i de to tilstande."""
    return Ctrl("tmrIbPost", "Timer", props={
        "AutoPause": "false",
        "AutoStart": "false",
        "Duration": "1000",
        "Height": "1",
        "OnTimerEnd": ("Set(varIbPostTick, Now());\n"
                       'If(\n    varIbPostStage = "done" &&\n'
                       "    DateDiff(varIbPostAt, varIbPostTick, TimeUnit.Milliseconds) >= 2500,\n"
                       '    Set(varIbPostStage, "")\n)'),
        "Repeat": "true",
        "Start": 'varIbPostStage = "posting" || varIbPostStage = "done"',
        "Visible": "false",
        "Width": "1",
    }, h=1, vis="false")


def build_loading():
    # Hentningen af listen har pladsholder-raekker (conIbSkeleton, M7);
    # hjulet daekker kun det, brugeren selv har sat i gang.
    # Gem og upload viser deres tilstand i knappen, der startede dem (issue
    # #420) - ingen bjaelke midt paa skaermen.
    # En kommentar har sin egen ventetilstand i kommentarfeltet (issue #370) -
    # varIbPosting daekker ikke skaermen.
    return [_post_timer(),
            # Formularens gem: et gennemsigtigt lag, ingen sloer (issue #402).
            panel_save_block("Ib", IB_SAVE),
            # Reopen, Archive, Delete og Save documents: knappen viser det
            # selv (issue #420) - et gennemsigtigt lag, ingen bjaelke.
            *act_layers("Ib", IB_ACT)]
