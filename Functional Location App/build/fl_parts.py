# -*- coding: utf-8 -*-
"""
SKAERMENS DELE - Functional Location App.

HVORFOR IKKE tools/domain_parts.py
----------------------------------
domain_parts er Equipment- og Material-appernes byggeklodser, og de er
bundet til DEN raekkemodel: colDomRows, et paakraevet Plant-felt, FL-
soegning mod flowet og RowStatus draft/valid/submitted. Her er raekken en
Functional Location med KKS-syntaks, klasse og 30-50 spool-felter pr.
klasse, og de er valideret af reglerne i docs/31 - ikke af et Plant-krav,
HTML-siden ikke har.

Repoets regel er, at en del, der kun passer til een app, skrives i dens
EGEN build-mappe (SKILL.md, "Hvordan en af dem afviger", punkt 2). Det er
det, filen her er. De faelles ting bruges, som de er: rammen og bjaelken
(build_helpers.app_frame / top_bar), kortene, felterne og knapperne, temaet
(theme_button), alle farver (design_tokens) og alle breakpoints
(layout_tokens). Ingen farve og intet breakpoint staar her.

Kolonnerne i tabellerne er HTML-sidens (functional-location.html:62-70 og
app-functional-location.js:67-73).
"""
import fl_config as cfg
import fl_validation as V
import fl_save as S
from gen_screen import (Ctrl, SHELL_W, C_CARD_BORDER, C_TITLE, C_MUTED, C_WHITE,
                        C_PRIMARY, C_TRANSPARENT, C_MODAL_BG, C_PRIMARY_SOFT, C_OVERLAY,
                        C_BORDER_OK, C_BORDER_ERROR, C_INVALID_FG, C_WARN_FG, C_VALID_FG)
from design_tokens import theme_query, ref_hex
from layout_tokens import SCROLLBAR_W, GALLERY_RESERVE, at_least
from build_helpers import (text_ctrl, group, button, text_input, dropdown, card,
                           pin_widths, top_bar, grow, theme_button, button_row, badge)

# Indsendt = laast (FL69).
DM_EDIT = 'If(varFlStatus = "Indsendt", DisplayMode.View, DisplayMode.Edit)'


def norm_fl(expr):
    """FL1: normalizeFlTyped + trim (app-functional-location.js:2368,
    fl-rule-engine.js:395)."""
    return (f"Upper(Trim(Substitute(Substitute(Substitute({expr}, Char(160), \" \"), "
            f"Char(13), \"\"), Char(10), \"\")))")


def add_row_fx():
    """FL63: en ny, tom raekke."""
    return ("Collect(colFlRows, { RowGuid: Text(GUID()), RowNo: varFlNextRowNo, SpId: 0, "
            "FL: \"\", Description: \"\", KksType: \"\", AssignedClass: \"\", Status: \"draft\", "
            "FirstIssue: \"\", FirstWarning: \"\", IssueCount: 0, WarningCount: 0 });\n"
            "Set(varFlNextRowNo, varFlNextRowNo + 1)")


# FL62: en aendring validerer igen. Formlen staar KUN i btnFlVerify.
REVERIFY = "Set(varFlStale, true);\nSelect(btnFlVerify)"


def set_row_fx(guid, field, value):
    return (f"Patch(colFlRows, LookUp(colFlRows, RowGuid = {guid}), {{ {field}: {value} }});\n"
            + REVERIFY)


def set_val_fx(guid, field, value):
    """FL56: vaerdien trimmes, og en tom vaerdi fjerner feltet
    (setSpoolColumnValue, app-functional-location.js:582-606). FL og
    Description er raekkens egne felter."""
    return f"""With(
    {{ f: {field}, nv: Trim({value}) }},
    Switch(
        f,
        "FUNCTIONAL LOCATION",
        Patch(colFlRows, LookUp(colFlRows, RowGuid = {guid}), {{ FL: {norm_fl("nv")} }}),
        "DESCRIPTION",
        Patch(colFlRows, LookUp(colFlRows, RowGuid = {guid}), {{ Description: nv }}),
        RemoveIf(colFlVals, RowGuid = {guid} && Field = f);
        If(!IsBlank(nv), Collect(colFlVals, {{ RowGuid: {guid}, Field: f, Value: nv }}))
    )
);
{REVERIFY}"""


def _status_color(row):
    return (f'Switch({row}.Status, "invalid", {C_INVALID_FG}, "warning", {C_WARN_FG}, '
            f'"valid", {C_VALID_FG}, {C_MUTED})')


def _field_border(bad, ok):
    """FL29: roed ved en besked paa feltet, groen naar raekken er valideret
    og feltet er i orden - getFieldStateClass (:2284-2300)."""
    return f"If({bad}, {C_BORDER_ERROR}, {ok}, {C_BORDER_OK}, {C_CARD_BORDER})"


# ---------------------------------------------------------------------------
# Bjaelken
# ---------------------------------------------------------------------------
COUNTS = ('"Rows: " & CountRows(colFlRows) & "  Ready: " & '
          'CountRows(Filter(colFlRows, Status = "valid" || Status = "warning")) & '
          '"  Issues: " & CountRows(Filter(colFlRows, Status = "invalid"))')


def build_bar():
    """Knapperne er HTML-sidens: Verify og Export JSON
    (functional-location.html:43-44). Tallene er renderMetrics (FL66)."""
    count = badge("txtFlCount", COUNTS, width=220)
    verify = button("btnFlVerify", '"Verify"', V.verify_fx(), primary=True, width=100)
    export = button("btnFlExport", '"Export JSON"', S.export_fx(), width=120)
    theme = theme_button("imgFlTheme")
    back = button("btnFlBack", '"To the hub"',
                  f'Launch("{cfg.HUB_URL}" & {theme_query("?")}, {{ }}, LaunchTarget.Replace)',
                  width=120)
    bar = top_bar("Fl", f'"{cfg.TITLE}"', f'"{cfg.SUBTITLE}"',
                  [count, verify, export, theme, back])
    count.vis = at_least("Desktop")
    return bar


# ---------------------------------------------------------------------------
# Validation-tabellen (functional-location.html:52-74)
# ---------------------------------------------------------------------------
GAP = 8
# Budgettet for en gallerirakkes celler: kortets padding, TemplatePadding,
# scrollbar og GALLERY_RESERVE (se docs/30, regel J).
ROWS_W = f"({SHELL_W} - 36 - 4 - {SCROLLBAR_W} - {GALLERY_RESERVE})"

# (navn, overskrift, bredde). 0 = resten. De to midterste skjules, naar der
# ikke er plads - som listen i domaeneapperne.
V_COLS = [("No", "#", 28), ("Fl", "Functional Location", 160),
          ("Desc", "Description", 140), ("Kks", "KKS Type", 64),
          ("Cls", "Assigned Class", 96), ("Val", "Validation", 0),
          ("Act", "Action", 76)]
V_MID = ("Kks", "Cls")
V_FIXED = sum(w for _n, _l, w in V_COLS) + GAP * (len(V_COLS) - 1)
V_SMALL = V_FIXED - sum(w + GAP for n, _l, w in V_COLS if n in V_MID)
V_SHOW_MID = f"({ROWS_W}) >= {V_FIXED} + 160"
V_VAL_W = f"Max(120, ({ROWS_W}) - If({V_SHOW_MID}, {V_FIXED}, {V_SMALL}))"
ROW_H = 44
GAL_MAX = 12


def _vw(n, w):
    return V_VAL_W if w == 0 else w


def build_rows():
    title = grow(text_ctrl("txtFlRowsH", '"Validation"', size=16, weight="Semibold",
                           height=22, wrap="false"))
    add = button("btnFlAddRow", '"Add row"', add_row_fx(), width=110,
                 display_mode=DM_EDIT)
    head_row = group("conFlRowsTop", pin_widths([title, add]), direction="Horizontal",
                     gap=12, align_items="Center")

    head = group("conFlRowsHead",
                 pin_widths([text_ctrl(f"txtFlHead{n}", f'"{lbl}"', size=11, color=C_MUTED,
                                       weight="Semibold", height=18, width=_vw(n, w),
                                       wrap="false",
                                       visible=V_SHOW_MID if n in V_MID else None)
                             for n, lbl, w in V_COLS]),
                 direction="Horizontal", gap=GAP, height=18, align_items="Center")

    row = "ThisItem"
    no = text_ctrl("txtFlRowNo", "Text(CountRows(Filter(colFlRows, RowNo <= ThisItem.RowNo)))",
                   size=13, color=C_MUTED, height=20, width=28, wrap="false")
    fl = text_input("inpFlRowFl", "ThisItem.FL", max_length=40, width="160",
                    display_mode=DM_EDIT, label='"Functional Location"',
                    onchange=set_row_fx("ThisItem.RowGuid", "FL", norm_fl("Self.Text")))
    fl.props["BorderColor"] = _field_border(V.fl_bad(row), f'{row}.Status <> "draft"')
    desc = text_input("inpFlRowDesc", "ThisItem.Description", max_length=40, width="140",
                      display_mode=DM_EDIT, label='"Description"',
                      onchange=set_row_fx("ThisItem.RowGuid", "Description", "Trim(Self.Text)"))
    desc.props["BorderColor"] = _field_border(
        V.desc_bad(row), f'{row}.Status <> "draft" && !IsBlank({row}.Description)')
    kks = text_ctrl("txtFlRowKks", 'If(IsBlank(ThisItem.KksType), "-", ThisItem.KksType)',
                    size=13, height=20, width=64, wrap="false", visible=V_SHOW_MID)
    cls = text_ctrl("txtFlRowCls",
                    'If(IsBlank(ThisItem.AssignedClass), "-", ThisItem.AssignedClass)',
                    size=13, weight="Semibold", height=20, width=96, wrap="false",
                    visible=V_SHOW_MID)

    # FL26: chippen og den foerste fejl eller advarsel (renderValidationBadges).
    shown = 'If(ThisItem.Status = "invalid", ThisItem.FirstIssue, ThisItem.FirstWarning)'
    val_txt = grow(text_ctrl(
        "txtFlRowIssue",
        'Switch(ThisItem.Status, "draft", "Draft", "valid", "Valid", '
        '"warning", "Warning" & If(IsBlank(ThisItem.FirstWarning), "", " - " & ThisItem.FirstWarning), '
        'If(IsBlank(ThisItem.FirstIssue), "Invalid", ThisItem.FirstIssue))',
        size=13, color=_status_color(row), height=20, wrap="false"))
    hint_expr = V.hint_fx(shown, "ThisItem.FL")
    hint = button("btnFlRowHint", '"?"', f"Notify({hint_expr}, NotificationType.Information)",
                  width=30, height=30, visible=f"!IsBlank({hint_expr})",
                  accessible='"What does this message mean?"')
    hint.props["Tooltip"] = hint_expr
    val = group("conFlRowVal", [val_txt, hint], direction="Horizontal", gap=6,
                width=V_VAL_W, height=30, align_items="Center")

    delete = button("btnFlRowDelete", '"Delete"', f"""Remove(colFlRows, LookUp(colFlRows, RowGuid = ThisItem.RowGuid));
RemoveIf(colFlVals, RowGuid = ThisItem.RowGuid);
RemoveIf(colFlIssues, RowGuid = ThisItem.RowGuid);
If(CountRows(colFlRows) = 0, {add_row_fx()});
{V.TABS};
Set(varFlStale, true)""", danger=True, width=76, height=30, display_mode=DM_EDIT)

    cells = [no, fl, desc, kks, cls, val, delete]
    tpl = group("conFlRow", pin_widths(cells), direction="Horizontal", gap=GAP,
                height="Parent.TemplateHeight - 2", align_items="Center", justify="Start",
                width="Parent.TemplateWidth")
    gal_h = f"Min(Max(CountRows(colFlRows), 1), {GAL_MAX}) * {ROW_H + 2}"
    gal = Ctrl("galFlRows", "Gallery", variant="Vertical", props={
        "AccessibleLabel": '"Functional Location rows"',
        "BorderStyle": "BorderStyle.None",
        "Fill": C_TRANSPARENT,
        "FillPortions": "0",
        "Height": gal_h,
        "Items": "Sort(colFlRows, RowNo)",
        "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None",
        "Selectable": "false",
        "ShowScrollbar": "true",
        "TabIndex": "0",
        "TemplatePadding": "2",
        "TemplateSize": str(ROW_H),
        "Width": "Parent.Width",
        "WrapCount": "1",
    }, children=[tpl], h=gal_h)

    info = text_ctrl("txtFlInfo", "varFlInfo", size=12, color=C_MUTED, height=18,
                     wrap="false")
    return card("conFlRowsCard", [head_row, head, gal, info])


# ---------------------------------------------------------------------------
# Klassefanerne (functional-location.html:77-81, FL28 og FL60)
# ---------------------------------------------------------------------------
C_COLS = [("No", "#", 28), ("Fl", "Functional Location", 160),
          ("Desc", "Description", 140), ("Str", "StrIndicator", 76),
          ("Cls", "Class", 96), ("Info", "Info", 0), ("Open", "Details", 72)]
C_MID = ("Str", "Cls")
C_FIXED = sum(w for _n, _l, w in C_COLS) + GAP * (len(C_COLS) - 1)
C_SMALL = C_FIXED - sum(w + GAP for n, _l, w in C_COLS if n in C_MID)
C_SHOW_MID = f"({ROWS_W}) >= {C_FIXED} + 160"
C_INFO_W = f"Max(120, ({ROWS_W}) - If({C_SHOW_MID}, {C_FIXED}, {C_SMALL}))"

# Faneindholdet: ALL = alle klasser, sorteret paa klasse og saa FL (renderClassTabs
# :1661-1664); en klasse = dens raekker sorteret paa FL (:1487).
VIEW = (f'SortByColumns(Filter({V.BUCKETS}, varFlTab = "ALL" || AssignedClass = varFlTab), '
        '"AssignedClass", SortOrder.Ascending, "FL", SortOrder.Ascending)')
# Pos er raekkens nummer i fanen (#, renderSpoolColumnCell :2057-2059).
VIEW_POS = ("With({ vw: " + VIEW + " },\n"
            "    ForAll(Sequence(CountRows(vw)) As S, With({ r: Index(vw, S.Value) },\n"
            "        { Pos: S.Value, RowGuid: r.RowGuid, FL: r.FL, Description: r.Description,\n"
            "          KksType: r.KksType, AssignedClass: r.AssignedClass, Status: r.Status,\n"
            "          FirstIssue: r.FirstIssue, FirstWarning: r.FirstWarning })))")


def build_classes():
    title = text_ctrl("txtFlClassesH", '"Classes"', size=16, weight="Semibold", height=22,
                      wrap="false")

    tab = button("btnFlTab", "ThisItem.Label",
                 'Set(varFlTab, ThisItem.Key);\nSet(varFlDetailRow, "")', width=130, height=34)
    sel = "varFlTab = ThisItem.Key"
    tab.props["Appearance"] = f"If({sel}, ButtonAppearance.Primary, ButtonAppearance.Outline)"
    tab.props["BasePaletteColor"] = C_PRIMARY
    tab.props["Color"] = f"If({sel}, {C_WHITE}, {C_TITLE})"
    # FL65: klassens hjaelpetekst (resolveClassHelpText :2353-2357).
    tab.props["Tooltip"] = ('With({ hp: LookUp(nfFlClassHelp, Key = ThisItem.Key).Help }, '
                            'If(IsBlank(hp), "", ThisItem.Key & ": " & hp))')
    tabs = Ctrl("galFlTabs", "Gallery", variant="Horizontal", props={
        "AccessibleLabel": '"Class tabs"',
        "BorderStyle": "BorderStyle.None",
        "Fill": C_TRANSPARENT,
        "FillPortions": "0",
        "Height": "44",
        "Items": "colFlTabs",
        "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None",
        "Selectable": "false",
        "ShowScrollbar": "true",
        "TabIndex": "0",
        "TemplatePadding": "3",
        "TemplateSize": "136",
        "Width": "Parent.Width",
        "WrapCount": "1",
    }, children=[tab], h=44)

    note = text_ctrl("txtFlClassNote",
                     '"Compact view - open a row for all columns of its class."',
                     size=12, color=C_MUTED, height=18, wrap="false")

    head = group("conFlClsHead",
                 pin_widths([text_ctrl(f"txtFlCHead{n}", f'"{lbl}"', size=11, color=C_MUTED,
                                       weight="Semibold", height=18,
                                       width=C_INFO_W if w == 0 else w, wrap="false",
                                       visible=C_SHOW_MID if n in C_MID else None)
                             for n, lbl, w in C_COLS]),
                 direction="Horizontal", gap=GAP, height=18, align_items="Center")

    # FL og Description kan ogsaa rettes her (renderSpoolEditor, :2098).
    no = text_ctrl("txtFlCNo", "Text(ThisItem.Pos)", size=13, color=C_MUTED, height=20,
                   width=28, wrap="false")
    fl = text_input("inpFlCFl", "ThisItem.FL", max_length=40, width="160",
                    display_mode=DM_EDIT, label='"Functional Location"',
                    onchange=set_row_fx("ThisItem.RowGuid", "FL", norm_fl("Self.Text")))
    fl.props["BorderColor"] = _field_border(V.fl_bad("ThisItem"), "true")
    desc = text_input("inpFlCDesc", "ThisItem.Description", max_length=40, width="140",
                      display_mode=DM_EDIT, label='"Description"',
                      onchange=set_row_fx("ThisItem.RowGuid", "Description", "Trim(Self.Text)"))
    desc.props["BorderColor"] = _field_border(V.desc_bad("ThisItem"),
                                              "!IsBlank(ThisItem.Description)")
    strc = text_ctrl("txtFlCStr", "ThisItem.KksType", size=13, height=20, width=76,
                     wrap="false", visible=C_SHOW_MID)
    clsc = text_ctrl("txtFlCCls", "ThisItem.AssignedClass", size=13, weight="Semibold",
                     height=20, width=96, wrap="false", visible=C_SHOW_MID)
    info = text_ctrl("txtFlCInfo", "Coalesce(ThisItem.FirstIssue, ThisItem.FirstWarning, \"\")",
                     size=13, color=_status_color("ThisItem"), height=20, width=C_INFO_W,
                     wrap="false")
    open_ = button("btnFlCOpen", '"Open"',
                   'Set(varFlDetailRow, ThisItem.RowGuid);\n'
                   'Set(varFlDetailClass, Coalesce(ThisItem.AssignedClass, "NO CLASS"));\n'
                   'Set(varFlShowEmpty, false)', width=72, height=30)
    tpl = group("conFlCRow", pin_widths([no, fl, desc, strc, clsc, info, open_]),
                direction="Horizontal", gap=GAP, height="Parent.TemplateHeight - 2",
                align_items="Center", justify="Start", width="Parent.TemplateWidth")
    gal_h = f"Min(Max(CountRows({V.BUCKETS}), 1), {GAL_MAX}) * {ROW_H + 2}"
    gal = Ctrl("galFlClassRows", "Gallery", variant="Vertical", props={
        "AccessibleLabel": '"Rows in the selected class"',
        "BorderStyle": "BorderStyle.None",
        "Fill": C_TRANSPARENT,
        "FillPortions": "0",
        "Height": gal_h,
        "Items": VIEW_POS,
        "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None",
        "Selectable": "false",
        "ShowScrollbar": "true",
        "TabIndex": "0",
        "TemplatePadding": "2",
        "TemplateSize": str(ROW_H),
        "Width": "Parent.Width",
        "WrapCount": "1",
    }, children=[tpl], h=gal_h)
    empty = text_ctrl("txtFlNoClassRows", '"No rows."', size=13, color=C_MUTED, height=22,
                      wrap="false", visible=f"IfError(CountRows({V.BUCKETS}) = 0, false)")
    return card("conFlClassesCard", [title, tabs, note, head, gal, empty])


# ---------------------------------------------------------------------------
# Detaljeruden (FL57-FL61, renderDetailModal :1960-2034)
# ---------------------------------------------------------------------------
DET_W = "Min(900, App.Width - 32)"
MODAL_X = "(App.Width - Self.Width) / 2"
MODAL_Y = "Max(20, (App.Height - Self.Height) / 3)"
DR = "LookUp(colFlRows, RowGuid = varFlDetailRow)"
DET_OPEN = (f'!IsBlank(varFlDetailRow) && !IsBlank({DR}.RowGuid) && '
            f'Coalesce({DR}.AssignedClass, "NO CLASS") = varFlDetailClass')


def _display_val(dr, field):
    """getSpoolColumnValue (:2205-2242) for visning."""
    raw = f"LookUp(colFlVals, RowGuid = {dr}.RowGuid && Field = {field}).Value"
    return (f'Switch({field},\n'
            f'    "INFO", Coalesce({dr}.FirstIssue, {dr}.FirstWarning, ""),\n'
            f'    "STRINDICATOR", {dr}.KksType,\n'
            f'    "STR. INDICATOR", {dr}.KksType,\n'
            f'    "FUNCTIONAL LOCATION", {dr}.FL,\n'
            f'    "DESCRIPTION", {dr}.Description,\n'
            f'    "LONG TEXT", Coalesce({raw}, {dr}.Description, ""),\n'
            f'    "USER STATUS", Upper({dr}.Status),\n'
            f'    "SYSTEM STATUS", "LOCAL",\n'
            f'    Coalesce({raw}, ""))')


DET_ITEMS = f"""With(
    {{ dr: {DR}, dc: varFlDetailClass }},
    Filter(
        ForAll(
            Sort(Filter(nfFlColumns, Cls = dc), Ord) As K,
            {{
                Column: K.Column, Field: K.Field, Editable: K.Editable,
                List: K.List, MaxLen: K.MaxLen,
                Value: {_display_val("dr", "K.Field")},
                Issue: {V.field_issue("dr.RowGuid", "K.Field")}
            }}
        ),
        varFlShowEmpty || !IsBlank(Value) || !IsBlank(Issue)
    )
)"""

# Dropdownens valg: tom, den gemte vaerdi hvis den er ugyldig, og listen
# (renderSpoolEditor :2112-2131).
DD_ITEMS = """Ungroup(
    Table(
        { G: Table({ Value: "" }) },
        { G: Filter(Table({ Value: ThisItem.Value }), !IsBlank(Value) &&
                    !(Upper(Value) in With({ lid: ThisItem.List }, Filter(nfFlLists, List = lid)).UValue)) },
        { G: ForAll(Sort(With({ lid: ThisItem.List }, Filter(nfFlLists, List = lid)), Ord) As O, { Value: O.Value }) }
    ),
    G
)"""

LBL_W = 200
ISSUE_W = 220


def build_detail():
    title = text_ctrl("txtFlDetH", '"Row details"', size=17, weight="Semibold", height=26,
                      wrap="false")
    sub = text_ctrl("txtFlDetSub",
                    f'"Class: " & varFlDetailClass & " | FL: " & Coalesce({DR}.FL, "-")',
                    size=12, color=C_MUTED, height=18, wrap="false")
    left = grow(group("conFlDetHeadL", [title, sub], direction="Vertical", gap=2))
    empty = button("btnFlDetEmpty", 'If(varFlShowEmpty, "Hide empty", "Show empty")',
                   "Set(varFlShowEmpty, !varFlShowEmpty)", width=120, height=32)
    close = button("btnFlDetClose", '"Close"', 'Set(varFlDetailRow, "")', primary=True,
                   width=90, height=32)
    head = group("conFlDetHead", [left] + pin_widths([empty, close]), direction="Horizontal",
                 gap=8, align_items="Center")

    inner = f"({DET_W}) - 36"
    # Galleriets bredde er Parent.Width - en NEDRE graense, saa reserven
    # traekkes fra (docs/30, regel J).
    tpl_w = f"({inner}) - 4 - {SCROLLBAR_W} - {GALLERY_RESERVE}"
    ed_w = f"({tpl_w}) - {LBL_W} - {ISSUE_W} - 2 * {GAP} - 2"

    lbl = text_ctrl("txtFlDetCol", "ThisItem.Column", size=13, weight="Semibold",
                    height=20, width=LBL_W, wrap="false")
    txt = text_input("inpFlDetVal", "ThisItem.Value", width="Parent.Width",
                     display_mode=DM_EDIT, label="ThisItem.Column",
                     onchange=set_val_fx("varFlDetailRow", "ThisItem.Field", "Self.Text"))
    txt.props["MaxLength"] = "If(ThisItem.MaxLen > 0, ThisItem.MaxLen, 4000)"
    txt.props["BorderColor"] = _field_border("!IsBlank(ThisItem.Issue)",
                                             "!IsBlank(ThisItem.Value)")
    txt.vis = "ThisItem.Editable && IsBlank(ThisItem.List)"
    dd = dropdown("drpFlDetVal", DD_ITEMS,
                  f"LookUp({DD_ITEMS}, Upper(Value) = Upper(ThisItem.Value))",
                  width="Parent.Width", display_mode=DM_EDIT, label="ThisItem.Column")
    dd.props["OnChange"] = set_val_fx("varFlDetailRow", "ThisItem.Field",
                                      "Coalesce(Self.Selected.Value, \"\")")
    dd.props["BorderColor"] = _field_border("!IsBlank(ThisItem.Issue)",
                                            "!IsBlank(ThisItem.Value)")
    dd.vis = "ThisItem.Editable && !IsBlank(ThisItem.List)"
    ro = text_ctrl("txtFlDetRo", "ThisItem.Value", size=13, height=36, wrap="false",
                   visible="!ThisItem.Editable")
    slot = group("conFlDetEd", [txt, dd, ro], direction="Vertical", gap=0, width=ed_w)
    issue = text_ctrl("txtFlDetIssue", "ThisItem.Issue", size=12, color=C_INVALID_FG,
                      height=20, width=ISSUE_W, wrap="false")
    tpl = group("conFlDetRow", pin_widths([lbl, slot, issue]), direction="Horizontal",
                gap=GAP, height="Parent.TemplateHeight - 2", align_items="Center",
                justify="Start", width="Parent.TemplateWidth")
    # Hoejden regnes af Items-udtrykket - ikke af galleriets egen AllItems,
    # som ville goere hoejden afhaengig af kontrollen selv.
    gal_h = f"Min(Max(CountRows({DET_ITEMS}), 1) * 46, App.Height - 220)"
    gal = Ctrl("galFlDetail", "Gallery", variant="Vertical", props={
        "AccessibleLabel": '"Columns of the selected row"',
        "BorderStyle": "BorderStyle.None",
        "Fill": C_TRANSPARENT,
        "FillPortions": "0",
        "Height": gal_h,
        "Items": DET_ITEMS,
        "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None",
        "Selectable": "false",
        "ShowScrollbar": "true",
        "TabIndex": "0",
        "TemplatePadding": "2",
        "TemplateSize": "44",
        "Width": "Parent.Width",
        "WrapCount": "1",
    }, children=[tpl], h=gal_h)
    none = text_ctrl("txtFlDetNone", '"No populated fields for this row."', size=13,
                     color=C_MUTED, height=22, wrap="false",
                     visible=f"IfError(CountRows({DET_ITEMS}) = 0, false)")
    modal = group("conFlDetailModal", [head, gal, none], direction="Vertical", gap=12,
                  fill=C_MODAL_BG, border_color=C_PRIMARY_SOFT, radius=16,
                  pad=(18, 18, 18, 18), width=DET_W, drop_shadow="ExtraBold",
                  visible=DET_OPEN)
    modal.props["X"] = MODAL_X
    modal.props["Y"] = MODAL_Y
    return modal


# ---------------------------------------------------------------------------
# Strukturen - HTML, KUN til visning (README, beslutning 3)
# ---------------------------------------------------------------------------
LIVE = 'Filter(colFlRows, Status <> "draft" && !IsBlank(FL))'


def _esc(x):
    return f'Substitute(Substitute(Substitute({x}, "&", "&amp;"), "<", "&lt;"), ">", "&gt;")'


def _cell(x, muted=False, bold=False):
    color = ref_hex("text-muted") if muted else ref_hex("text-primary")
    weight = "font-weight:600;" if bold else ""
    return (f'"<td style=\'padding:3px 10px 3px 0;{weight}color:" & {color} & "\'>" & '
            f'{x} & "</td>"')


def structure_html():
    """FL-hierarkiet: vaerk -> KKS-noeglerne i positionerne, som motoren
    laeser dem (0: 1-3, 7: 7-9, 12: 12-13, 17: 17-18, 18: 18-19). Hver
    raekke viser sin klasse og status. Laeses, redigeres ikke."""
    head_cells = ["Plant", "Unit", "Function key", "No.", "Aggregate", "Pos. 14-16",
                  "Pos. 17-21", "Class", "Status"]
    th = "".join(
        f"<th style='text-align:left;padding:3px 10px 3px 0;font-weight:600;color:\" & "
        f"{ref_hex('text-muted')} & \"'>{h}</th>" for h in head_cells)
    row = " & ".join([
        _cell('""'),
        _cell(_esc("Mid(R.FL, 4, 3)"), muted=True),
        _cell(_esc("Mid(R.FL, 7, 3)"), bold=True),
        _cell(_esc("Mid(R.FL, 10, 2)"), muted=True),
        _cell(_esc("Mid(R.FL, 12, 2)"), bold=True),
        _cell(_esc("Mid(R.FL, 14, 3)"), muted=True),
        _cell(_esc("Mid(R.FL, 17, 5)"), bold=True),
        _cell(_esc('Coalesce(R.AssignedClass, "-")'), bold=True),
        _cell('Switch(R.Status, "valid", "&#10004; Ready", "warning", "&#9888; Warning", '
              '"&#10006; Error")'),
    ])
    return (f'"<div style=\'font-family:Segoe UI;font-size:13px;color:" & {ref_hex("text-primary")} & "\'>" &\n'
            f'"<table style=\'border-collapse:collapse;width:100%\'><tr>{th}</tr>" &\n'
            f"Concat(\n"
            f"    Sort(Distinct({LIVE}, Left(FL, 3)), Value) As P,\n"
            f'    "<tr><td colspan=\'9\' style=\'padding:8px 0 2px 0;font-weight:700;color:" & {ref_hex("text-primary")} & "\'>" & {_esc("P.Value")} & "</td></tr>" &\n'
            f"    Concat(\n"
            f"        Sort(Filter({LIVE}, Left(FL, 3) = P.Value), FL) As R,\n"
            f'        "<tr>" & {row} & "</tr>"\n'
            f"    )\n"
            f") &\n"
            f'"</table></div>"')


def build_structure():
    title = text_ctrl("txtFlStructH", '"Structure"', size=16, weight="Semibold",
                      height=22, wrap="false")
    sub = text_ctrl("txtFlStructSub",
                    '"The KKS keys the rules read, per plant. For viewing only - edit the rows above."',
                    size=12, color=C_MUTED, height=18, wrap="false")
    h = f"Min(40 + 26 * (CountRows({LIVE}) + CountRows(Distinct({LIVE}, Left(FL, 3)))), 600)"
    html = Ctrl("htmFlStructure", "HtmlViewer", props={
        "Fill": C_TRANSPARENT,
        "Height": h,
        "HtmlText": structure_html(),
        "PaddingBottom": "0", "PaddingLeft": "0", "PaddingRight": "0", "PaddingTop": "0",
        "Width": "Parent.Width",
    }, h=h)
    empty = text_ctrl("txtFlStructNone", '"Verify the rows to see their structure."',
                      size=13, color=C_MUTED, height=22, wrap="false",
                      visible=f"IfError(CountRows({LIVE}) = 0, false)")
    return card("conFlStructCard", [title, sub, html, empty])


# ---------------------------------------------------------------------------
# Gem og indsend (FL68, FL69)
# ---------------------------------------------------------------------------
NEW_FX = """Clear(colFlRows);
Clear(colFlVals);
Clear(colFlIssues);
Clear(colFlTabs);
Set(varFlRequestGuid, "");
Set(varFlRequestNo, "");
Set(varFlStatus, "");
Set(varFlTab, "ALL");
Set(varFlDetailRow, "");
Set(varFlStale, false);
Set(varFlNextRowNo, 1);
""" + add_row_fx() + """;
Set(varFlInfo, "Ready.")"""


def build_submit():
    state = text_ctrl("txtFlSubmitState", S.SUBMIT_WHY, size=13, height=20, wrap="false")
    save = button("btnFlSaveDraft", '"Save draft"', S.save_fx(), width=150,
                  display_mode=(f'If(varFlStatus = "Indsendt" || CountRows({S.LIVE}) = 0, '
                                f'DisplayMode.Disabled, DisplayMode.Edit)'))
    submit = button("btnFlSubmit", '"Submit"', S.submit_fx(), primary=True, width=150,
                    display_mode=S.SUBMIT_DM)
    new = button("btnFlNew", '"New request"', NEW_FX, width=150)
    note = text_ctrl(
        "txtFlSubmitNote",
        ('"Save draft puts the request on the landing page as Draft - it can still be '
         'edited. Submit freezes a JSON snapshot and locks the rows."'),
        size=12, color=C_MUTED, height=18, wrap="false")
    no = text_ctrl("txtFlReqNo",
                   'If(IsBlank(varFlRequestNo), "Not saved yet.", "Request " & varFlRequestNo & '
                   '" (" & Coalesce(varFlStatus, "Kladde") & ")")',
                   size=13, color=C_MUTED, height=20, wrap="false")
    return card("conFlSubmitCard",
                [no, state, button_row("conFlSubmitRow", [save, submit, new], SHELL_W), note])


# ---------------------------------------------------------------------------
# Eksport (FL64)
# ---------------------------------------------------------------------------
EXP_W = "Min(820, App.Width - 32)"


def build_export():
    title = grow(text_ctrl("txtFlExpH", '"Export JSON"', size=17, weight="Semibold",
                           height=26, wrap="false"))
    close = button("btnFlExpClose", '"Close"', "Set(varFlExportOpen, false)", primary=True,
                   width=90, height=32)
    head = group("conFlExpHead", pin_widths([title, close]), direction="Horizontal", gap=8,
                 align_items="Center")
    box = text_input("inpFlExpJson", "varFlExportJson", width="Parent.Width", height=360,
                     display_mode="DisplayMode.View", ttype="Multiline",
                     label='"Exported JSON"')
    hint = text_ctrl("txtFlExpHint", '"Select all and copy - the app cannot save a file."',
                     size=12, color=C_MUTED, height=18, wrap="false")
    modal = group("conFlExportModal", [head, box, hint], direction="Vertical", gap=12,
                  fill=C_MODAL_BG, border_color=C_PRIMARY_SOFT, radius=16,
                  pad=(18, 18, 18, 18), width=EXP_W, drop_shadow="ExtraBold",
                  visible="varFlExportOpen")
    modal.props["X"] = MODAL_X
    modal.props["Y"] = MODAL_Y
    return modal


def build_backdrop():
    vis = f"({DET_OPEN}) || varFlExportOpen"
    return Ctrl("conFlBackdrop", "GroupContainer", variant="AutoLayout", props={
        "BorderStyle": "BorderStyle.None",
        "DropShadow": "DropShadow.None",
        "Fill": C_OVERLAY,
        "Height": "App.Height",
        "LayoutDirection": "LayoutDirection.Vertical",
        "LayoutOverflowX": "LayoutOverflow.Hide",
        "LayoutOverflowY": "LayoutOverflow.Hide",
        "Visible": vis,
        "Width": "App.Width",
        "X": "0",
        "Y": "0",
    }, children=[], vis=vis)
