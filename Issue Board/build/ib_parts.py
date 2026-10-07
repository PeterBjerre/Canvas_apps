# -*- coding: utf-8 -*-
"""
Issue Board-skaermen (issue #114, trin 1): delene, formlerne og hentningen.

    [ikon] Issue Board                              [Refresh] [+ New issue]
           Report what you find while testing ...
    +------------------------------------------------------------------+
    | [My issues | Shared issues]   [Open | Closed | Archived]         |
    | [Search .................] [Application v] [Section v] [Sort v]  |
    +------------------------------------------------------------------+
    | 12 issues                                                        |
    | ISS-000142  Save draft fails on ...                 [ New      ] |
    |             Maintenance Plan · Items · Major · Updated ...       |
    +------------------------------------------------------------------+

    New issue   -> popup: Application/Section, titel, lignende sager fra
                   den anonyme liste, "What happened?", flere detaljer
                   (valgfrit), Submit -> flowet.
    En raekke   -> popup i View mode: beskrivelsen og (egne sager)
                   Activity med kommentarer og et kommentarfelt.

SIKKERHED ER IKKE HER
---------------------
Alle filtre paa skaermen er UX. Det, en bruger kan hente, afgoeres af
rettighederne paa raekken, som flowet saetter (ib_config.py). "My issues"
filtrerer paa ReporterEmail, saa en admin - der kan laese alle sager - ogsaa
kun ser sine egne her; admin-boardet er trin 2.

HENTNING
--------
  * Konfigurationen og brugerens egne sager hentes EEN gang, foerste gang
    skaermen vises (Concurrent, to delegerbare forespoergsler).
  * Den anonyme liste hentes foerst, naar man vaelger "Shared issues" eller
    aabner "New issue" (forslag til lignende sager).
  * Activity hentes, naar man aabner en af sine egne sager.
  * Soegning, filtre og sortering regnes i hukommelsen paa de hentede
    raekker - intet kald pr. tastetryk.
"""
from gen_screen import (Ctrl, C_APP_BG, C_CARD_BG, C_CARD_BORDER, C_DIVIDER, C_INFO_BG,
                        C_INFO_FG, C_INVALID_FG, C_MUTED, C_MUTED_BG, C_MODAL_BG, C_OVERLAY,
                        C_PRIMARY, C_PRIMARY_SOFT, C_TITLE, C_TRANSPARENT)
from build_helpers import (button, card, concurrent, fit_button_width, group, grow,
                           icon_on_mobile, label_row, loading_overlay, row_hit, row_rule,
                           text_ctrl, text_input, themed_dropdown, top_bar, ICON_W)
from design_tokens import ref as _t
import layout_tokens as lay
from layout_tokens import SHELL_W, below, at_least, if_below

import ib_config as cfg

P = "Ib"
NARROW = below("Tablet")

# ---------------------------------------------------------------------------
# Tilstand
# ---------------------------------------------------------------------------
INIT_STATE = (
    "If(\n"
    "    IsBlank(varIbScope),\n"
    '    Set(varIbScope, "mine");\n'
    '    Set(varIbState, "open");\n'
    '    Set(varIbApp, "");\n'
    '    Set(varIbSection, "");\n'
    '    Set(varIbSort, "Last updated");\n'
    "    Set(varIbMe, Lower(User().Email));\n"
    '    Set(varIbTab, "details");\n'
    "    Set(varIbFormOn, false);\n"
    "    Set(varIbDetailOn, false);\n"
    "    Set(varIbMore, false);\n"
    "    Set(varIbBusy, false);\n"
    "    Set(varIbPosting, false)\n"
    ")"
)


def _rank(field, pairs, fallback):
    body = ", ".join(f'"{k}", {r}' for k, r in pairs)
    return f"Switch({field}, {body}, {fallback})"


STATUS_RANK = [(s, r) for s, _c, r in cfg.STATUS]


def _row(r, *, shared):
    """Een raekke i colIbMine/colIbShared. De to har SAMME skema, saa
    listen kan vaelge mellem dem med et If."""
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

RETRY = ("Set(varIbLoaded, false);\nSet(varIbSharedLoaded, false);\n" + LOAD
         + ';\nIf(varIbScope = "shared", ' + LOAD_SHARED + ")")


def on_visible():
    return INIT_STATE + ";\n" + LOAD


# Activity for den aabne sag. Foerste raekke er selve indmeldingen (fra
# sagen), resten er raekkerne i IB_TicketComments - kun dem, brugeren har
# ret til at se. Filteret paa TicketId er delegerbart (tal = variabel).
LOAD_ACTIVITY = (
    "Set(varIbActBusy, true);\n"
    "Set(varIbActFailed, IfError(ClearCollect(\n"
    "    colIbActivity,\n"
    '    { Kind: "Reported", Actor: "You", Body: "Reported the issue.", At: varIbSel.CreatedOn, '
    "Internal: false, IsSystem: true },\n"
    f"    ForAll(Sort(Filter({cfg.L_COMMENTS}, TicketId = varIbSelId), EventOn, SortOrder.Ascending) As r,\n"
    '        With({ k: Coalesce(r.EventType.Value, "Comment"), who: Lower(Coalesce(r.AuthorEmail, "")), '
    'role: Coalesce(r.AuthorRole.Value, "") },\n'
    "            { Kind: k,\n"
    '              Actor: If(role = "System", "System", who = varIbMe, "You", '
    'Upper(First(Split(who, "@")).Value) & If(role = "Admin", " (admin)", "")),\n'
    '              Body: If(k = "StatusChange", "Status changed from " & Coalesce(r.PreviousStatus, "-") & '
    '" to " & Coalesce(r.NewStatus, "-") & If(IsBlank(r.Content), ".", ". " & r.Content), '
    'Coalesce(r.Content, "")),\n'
    "              At: Coalesce(r.EventOn, r.Created),\n"
    '              Internal: r.Visibility.Value = "Internal",\n'
    '              IsSystem: k <> "Comment" })))\n'
    "; false, true));\n"
    "Set(varIbActBusy, false)"
)


# Skemaerne for samlingerne. If(false, ...): kun skemaet (check_layout
# regel 34) - App.OnStart maa ikke toemme det, OnVisible fylder.
ROW = {"Id": "0", "TicketNo": '""', "Title": '""', "Description": '""', "Steps": '""',
       "Expected": '""', "Actual": '""', "Application": '""', "Section": '""', "Other": '""',
       "RelatedNo": '""', "Severity": '""', "Priority": '""', "Status": '""',
       "Resolution": '""', "Assigned": '""', "CreatedOn": "Now()", "UpdatedOn": "Now()",
       "Archived": "false", "PriRank": "0", "StatusRank": "0"}
SEC = {"Application": '""', "Section": '""', "AppOrder": "0", "SectionOrder": "0",
       "ScreenKey": '""'}
ACT = {"Kind": '""', "Actor": '""', "Body": '""', "At": "Now()", "Internal": "false",
       "IsSystem": "false"}


def collections():
    return [("colIbMine", ROW), ("colIbShared", ROW), ("colIbSections", SEC),
            ("colIbActivity", ACT)]


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
IbFailed = IfError(varIbCfgFailed, false) || IfError(varIbMineFailed, false) || (varIbScope = "shared" && IfError(varIbSharedFailed, false));'''


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
OPEN_FORM = (
    LOAD_SHARED + ";\n"
    "Set(varIbFormApp, IbFrom);\n"
    'Set(varIbFormSection, "");\n'
    "Set(varIbMore, false);\n"
    "Reset(drpIbFormApp);\nReset(drpIbFormSection);\nReset(inpIbOther);\nReset(inpIbTitle);\n"
    "Reset(inpIbDesc);\nReset(inpIbSteps);\nReset(inpIbExpected);\nReset(inpIbActual);\n"
    "Reset(inpIbRelated);\nReset(drpIbSeverity);\n"
    "Set(varIbFormOn, true)"
)


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


def build_filters():
    scope = _switch_group("conIbScope", [
        _seg("btnIbScopeMine", "My issues", 'varIbScope = "mine"',
             'Set(varIbScope, "mine")', 104, '"Show my issues"'),
        _seg("btnIbScopeShared", "Shared issues", 'varIbScope = "shared"',
             'Set(varIbScope, "shared");\n' + LOAD_SHARED, 120,
             '"Show shared issues from all testers, without names"'),
    ])
    state = _switch_group("conIbState", [
        _seg("btnIbStateOpen", "Open", 'varIbState = "open"', 'Set(varIbState, "open")', 76,
             '"Show open issues"'),
        _seg("btnIbStateClosed", "Closed", 'varIbState = "closed"', 'Set(varIbState, "closed")', 84,
             '"Show closed issues"'),
        _seg("btnIbStateArchived", "Archived", 'varIbState = "archived"',
             'Set(varIbState, "archived")', 92, '"Show archived issues"'),
    ])
    top_w = int(scope.props["Width"]) + 16 + int(state.props["Width"])
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

    note = text_ctrl("txtIbSharedNote",
                     '"Shared issues are anonymous: they never show who reported them, '
                     'and comments stay private."',
                     size=lay.SIZE_SMALL, color=C_INFO_FG, height=34, wrap="true",
                     visible='varIbScope = "shared"',
                     extra={"Fill": C_INFO_BG, "PaddingLeft": "12", "PaddingRight": "12",
                            "PaddingTop": "8", **lay.radius(10)})
    return card("conIbFilterCard", [top, row, note], gap=12)


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
    "Clear(colIbActivity);\n"
    "Set(varIbDetailOn, true);\n"
    "If(!varIbSelShared, " + LOAD_ACTIVITY + ")"
)

LIST_ITEMS = (
    "With(\n"
    '    { q: Trim(inpIbSearch.Text), t: If(varIbScope = "shared", colIbShared, colIbMine) },\n'
    "    With(\n"
    "        { f: Filter(t,\n"
    f'              Switch(varIbState, "closed", !Archived && Status = "{cfg.STATUS_CLOSED}", '
    f'"archived", Archived, !Archived && Status <> "{cfg.STATUS_CLOSED}"),\n'
    "              IsBlank(varIbApp) || Application = varIbApp,\n"
    "              IsBlank(varIbSection) || Section = varIbSection,\n"
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
        f'"  ·  Updated " & {WHEN}',
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
    gal_h = f"Max(1, Min(CountRows(galIbList.AllItems), {GAL_ROWS})) * {ROW_H}"
    gal = Ctrl("galIbList", "Gallery", variant="Vertical", props={
        "AccessibleLabel": '"Issues"',
        "BorderStyle": "BorderStyle.None", "Fill": C_CARD_BG, "FillPortions": "0",
        "Height": gal_h, "Items": LIST_ITEMS, "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None", "Selectable": "false",
        "ShowScrollbar": "true", "TabIndex": "0", "TemplatePadding": "0",
        "TemplateSize": str(ROW_H), "Width": "Parent.Width", "WrapCount": "1",
    }, children=[no, title, meta, chip, pri, rule, hit], h=gal_h,
        vis="CountRows(galIbList.AllItems) > 0")

    count = text_ctrl("txtIbCount",
                      'CountRows(galIbList.AllItems) & If(CountRows(galIbList.AllItems) = 1, '
                      '" issue", " issues")',
                      size=lay.SIZE_BODY, weight="Semibold", color=C_MUTED, height=20)
    empty_fx = (
        'If(varIbLoading, "Loading issues...", '
        "IbFailed, \"The issues could not be loaded. Check your connection and try again.\", "
        'varIbScope = "mine" && IsEmpty(colIbMine), '
        '"You have not reported any issues yet. Use New issue to report one.", '
        'varIbScope = "shared" && IsEmpty(colIbShared), "No issues have been shared yet.", '
        '"No issues match the filters.")')
    empty = text_ctrl("txtIbEmpty", empty_fx, size=lay.SIZE_BODY, height=40, wrap="true",
                      color=f"If(IbFailed, {C_INVALID_FG}, {C_MUTED})",
                      visible="CountRows(galIbList.AllItems) = 0")
    retry = button("btnIbRetry", '"Retry"', RETRY, width=fit_button_width('"Retry"'), height=36,
                   visible="IbFailed && !varIbLoading", accessible='"Load the issues again"')
    retry.props["AlignInContainer"] = "AlignInContainer.Start"
    return card("conIbListCard", [count, gal, empty, retry], gap=8)


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
    f"    {RELOAD_MINE};\n"
    "    Set(varIbSharedLoaded, false);\n"
    "    Set(varIbFormOn, false);\n"
    '    Set(varIbScope, "mine");\n'
    '    Set(varIbState, "open");\n'
    '    Notify("Thank you. Issue " & varIbRes.ticketno & " has been submitted.", '
    "NotificationType.Success),\n"
    '    Notify("The issue could not be submitted. " & varIbRes.message, NotificationType.Error)\n'
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


def build_form():
    head = _head("IbForm", '"New issue"', "Set(varIbFormOn, false)")
    intro = text_ctrl("txtIbFormIntro",
                      '"Tell us what happened. Fields marked * are required. Only you and the '
                      'administrators can see your name and the comments."',
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

    other = text_input("inpIbOther", '""', placeholder='"Which application or part of the app?"',
                       max_length=250, required_formula="true",
                       label='"Describe the application or section, required"')
    other_f = _field("conIbFormOther", "Describe where it happened", other, required=True,
                     visible="IbOtherNeeded")

    title = text_input("inpIbTitle", '""', placeholder='"A short summary, e.g. Save draft does nothing"',
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
    sim_h = f"CountRows(galIbSimilar.AllItems) * {SIM_ROW_H}"
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
                    visible="CountRows(galIbSimilar.AllItems) > 0")

    desc = text_input("inpIbDesc", '""', placeholder='"What did you do, and what went wrong?"',
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

    def area(name, label, placeholder):
        c = text_input(name, '""', placeholder=f'"{placeholder}"', max_length=4000, height=72,
                       ttype="Multiline", label=f'"{label}"')
        return _field(f"con{name[3:]}F", label, c)

    steps = area("inpIbSteps", "Steps to reproduce", "1. Open ... 2. Select ... 3. ...")
    expected = area("inpIbExpected", "Expected result", "What should have happened?")
    actual = area("inpIbActual", "Actual result", "What happened instead?")
    related = text_input("inpIbRelated", '""', placeholder='"e.g. MP0142"', max_length=40,
                         label='"Related request number"')
    severity = themed_dropdown("drpIbSeverity",
                               "[" + ", ".join(f'"{s}"' for s in cfg.SEVERITY) + "]",
                               f'"{cfg.SEVERITY_DEFAULT}"', label='"How serious is it?"')
    extra_row = _pair("conIbFormExtra", _field("conIbFormRelated", "Related request number", related),
                      _field("conIbFormSeverity", "How serious is it?", severity))
    details = group("conIbFormMore", [steps, expected, actual, extra_row], direction="Vertical",
                    gap=12, visible="varIbMore")

    context = text_ctrl("txtIbFormContext",
                        f'"Also recorded with the issue: opened from " & {PAGE_FX} & ", " & '
                        'LayoutContext & " layout, " & Host.OSType & ", and the date and time."',
                        size=lay.SIZE_SMALL, color=C_MUTED, height=34, wrap="true")
    missing = text_ctrl("txtIbFormMissing",
                        '"To submit, pick an application and a section, and fill in the title '
                        '(at least 4 characters) and what happened."',
                        size=lay.SIZE_SMALL, color=C_MUTED, height=34, wrap="true",
                        visible=f"!({VALID})")
    cancel = button("btnIbFormCancel", '"Cancel"', "Set(varIbFormOn, false)",
                    width=fit_button_width('"Cancel"'), height=36)
    submit = button("btnIbFormSubmit", '"Submit issue"', SUBMIT, primary=True,
                    width=fit_button_width('"Submit issue"') + ICON_W, height=36, icon="Send",
                    display_mode=f"If(({VALID}) && !varIbBusy, DisplayMode.Edit, DisplayMode.Disabled)")
    footer = group("conIbFormFooter", [cancel, submit], direction="Horizontal", gap=8,
                   height=36, justify="End", align_items="Center")
    kids = [head, intro, where, sec_hint, other_f, title_f, similar, desc_f, more, details,
            context, missing, footer]
    return [_popup("IbForm", kids, FORM_ON, width=FORM_W)]


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

POST = (
    "Set(varIbPosting, true);\n"
    f"Set(varIbRes, IfError({cfg.FLOW}.Run(\n"
    f'    "{cfg.ACT_COMMENT}",\n'
    "    JSON({ ticketId: varIbSelId, content: Trim(inpIbComment.Text) })\n"
    f"), {FALLBACK}));\n"
    "If(\n"
    '    varIbRes.ok = "yes",\n'
    "    Reset(inpIbComment);\n"
    "    " + LOAD_ACTIVITY.replace("\n", "\n    ") + ";\n"
    "    Patch(colIbMine, LookUp(colIbMine, Id = varIbSelId), { UpdatedOn: Now() });\n"
    '    Notify("Comment posted.", NotificationType.Success),\n'
    '    Notify("The comment could not be posted. " & varIbRes.message, NotificationType.Error)\n'
    ");\n"
    "Set(varIbPosting, false)"
)


def _text_block(name, label, expr, visible=None):
    """En overskrift og en tekst, der ombrydes - laest, ikke redigeret."""
    lab = text_ctrl(f"txt{name}Label", f'"{label}"', size=lay.SIZE_SMALL, weight="Semibold",
                    color=C_MUTED, height=18)
    h = _lines_h(expr, DET_IN)
    body = text_ctrl(f"txt{name}", expr, size=lay.SIZE_BODY, height=h, wrap="true")
    return group(f"con{name}", [lab, body], direction="Vertical", gap=4, visible=visible)


def _tab(name, label_fx, key, accessible):
    b = button(name, label_fx, f'Set(varIbTab, "{key}")', width=132, height=32,
               accessible=accessible)
    sel = f'varIbTab = "{key}"'
    b.props["Appearance"] = "ButtonAppearance.Outline"
    b.props["BorderColor"] = f"If({sel}, {C_PRIMARY}, {C_CARD_BORDER})"
    b.props["BorderThickness"] = f"If({sel}, 2, 1)"
    b.props["Color"] = f"If({sel}, {C_PRIMARY}, {C_TITLE})"
    b.props["Size"] = str(lay.SIZE_SMALL)
    b.props["LayoutMinWidth"] = "132"
    return b


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
        f'{SEL}.Assigned), "not yet assigned"), "")',
        size=lay.SIZE_SMALL, height=18)

    shared_note = text_ctrl("txtIbDetShared",
                            '"Shared issue. Who reported it, their details and the comments are '
                            'private and not shown here."',
                            size=lay.SIZE_SMALL, color=C_INFO_FG, height=34, wrap="true",
                            visible="varIbSelShared",
                            extra={"Fill": C_INFO_BG, "PaddingLeft": "12", "PaddingRight": "12",
                                   "PaddingTop": "8", **lay.radius(10)})

    n_act = "CountRows(colIbActivity)"
    tabs = group("conIbDetTabs", [
        _tab("btnIbTabDetails", '"Description"', "details", '"Show the description"'),
        _tab("btnIbTabActivity", f'"Activity (" & {n_act} & ")"', "activity",
             '"Show the activity and comments"'),
    ], direction="Horizontal", gap=8, height=32, align_items="Center", visible=MINE)

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

    # Activity: kommentarer som flader, haendelser med stiplet kant.
    tw = "Parent.TemplateWidth"
    body_h = _lines_h("ThisItem.Body", ACT_BODY_W)
    row_h = f"(30 + {body_h} + 10)"
    bg = text_ctrl("txtIbActBg", '""', size=lay.SIZE_MICRO, height=f"{row_h} - 4", width=tw,
                   accessible='""',
                   fill=f"If(ThisItem.IsSystem, {C_TRANSPARENT}, {C_MUTED_BG})",
                   extra={"X": "0", "Y": "2", **lay.radius(8),
                          "BorderColor": f"If(ThisItem.IsSystem, {C_CARD_BORDER}, {C_TRANSPARENT})",
                          "BorderStyle": "BorderStyle.Dashed",
                          "BorderThickness": "If(ThisItem.IsSystem, 1, 0)"})
    actor = text_ctrl("txtIbActActor",
                      'ThisItem.Actor & If(ThisItem.Internal, "  ·  internal note", "")',
                      size=lay.SIZE_BODY, weight="Semibold",
                      color=f"If(ThisItem.IsSystem, {C_MUTED}, {C_TITLE})", height=20,
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

    comment = text_input("inpIbComment", '""', placeholder='"Write a comment for the administrators"',
                         max_length=2000, height=72, ttype="Multiline", label='"Comment"')
    closed_hint = text_ctrl(
        "txtIbCommentHint",
        f'If({SEL}.Status = "{cfg.STATUS_CLOSED}", '
        '"This issue is closed. If the problem is back, say so here and an administrator will reopen it.", '
        '"Comments are visible to you and the administrators only.")',
        size=lay.SIZE_SMALL, color=C_MUTED, height=34, wrap="true")
    post = button("btnIbPost", '"Post comment"', POST, primary=True,
                  width=fit_button_width('"Post comment"') + ICON_W, height=36, icon="Send",
                  display_mode=("If(IsBlank(Trim(inpIbComment.Text)) || varIbPosting, "
                                "DisplayMode.Disabled, DisplayMode.Edit)"))
    post.props["AlignInContainer"] = "AlignInContainer.End"
    composer = group("conIbComposer", [comment, closed_hint, post], direction="Vertical", gap=8,
                     visible=f"!{SEL}.Archived")
    activity = group("conIbDetActivity", [act_state, gal, composer], direction="Vertical", gap=12,
                     visible=f'{MINE} && varIbTab = "activity"')

    rule = group("conIbDetRule", [], direction="Horizontal", height=1, fill=C_DIVIDER)
    kids = [head, meta, facts, shared_note, tabs, rule, details, activity]
    return [_popup("IbDet", kids, DETAIL_ON)]


def build_loading():
    return [loading_overlay("imgIbLoading", "varIbLoading", "Loading issues, please wait"),
            loading_overlay("imgIbBusy", "varIbBusy || varIbPosting", "Sending, please wait")]
