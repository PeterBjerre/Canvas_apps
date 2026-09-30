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
(tools/side_nav.py), alle farver (design_tokens) og alle breakpoints
(layout_tokens). Ingen farve og intet breakpoint staar her.

Kolonnerne i tabellerne er HTML-sidens (functional-location.html:62-70 og
app-functional-location.js:67-73).
"""
import fl_config as cfg
import fl_validation as V
import fl_save as S
from gen_screen import (Ctrl, SHELL_W, C_CARD_BORDER, C_TITLE, C_MUTED, C_WHITE,
                        C_PRIMARY, C_TRANSPARENT, C_MODAL_BG, C_PRIMARY_SOFT, C_OVERLAY,
                        C_BORDER_OK, C_BORDER_ERROR, C_INVALID_FG, C_WARN_FG, C_VALID_FG,
                        C_CARD_BG, C_DIVIDER)
from design_tokens import ref_hex
from layout_tokens import SCROLLBAR_W, GALLERY_RESERVE, at_least, below
from build_helpers import (text_ctrl, group, button, text_input, dropdown, card,
                           pin_widths, top_bar, grow, badge, fit_button_width, row_rule,
                           loading_overlay, with_busy, confirm_modal, ICON_SAVE, ICON_SUBMIT,
                           ICON_W)

NARROW = below("Tablet")

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


# FL62: validering er AUTOMATISK (issue #77) - der er ingen Verify-knap.
# Formlen staar KUN i den skjulte btnFlVerify (build_rows), og hver
# aendring - ny raekke, rettet felt, slettet raekke, indlaest anmodning -
# kalder den. Den er lokal Power Fx mod de navngivne formler (nf*), saa
# den koster ingen kald til SharePoint eller flows.
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

# Undertitlen siger, hvilken anmodning man staar i, naar den er gemt -
# det stod foer i indsend-kortet, som ikke findes mere (issue #77).
SUBTITLE = (f'If(IsBlank(varFlRequestNo), "{cfg.SUBTITLE}", "Request " & varFlRequestNo & '
            f'If(varFlStatus = "Indsendt", " - submitted and locked.", " - draft."))')


def _fit(btn, icon=False):
    """Knappen saa bred som sin tekst (+ ikon) - aldrig straekt."""
    w = fit_button_width(btn.props["Text"]) + (ICON_W if icon else 0)
    btn.props["Width"] = str(w)
    btn.props["LayoutMinWidth"] = str(w)
    return btn


def _bar_btn(btn):
    """Under Tablet er bjaelkens knapper kun deres ikon, saa alle tre kan
    staa ved siden af titlen - ingen af dem skjules."""
    w = btn.props["Width"]
    btn.props["Width"] = f"If({NARROW}, 40, {w})"
    btn.props["Layout"] = f"If({NARROW}, ButtonLayout.IconOnly, ButtonLayout.IconBefore)"
    return btn


def build_bar():
    """Save draft, Submit og New request staar dér, hvor Verify og Export
    JSON stod (issue #77). Valideringen koerer af sig selv (REVERIFY), og
    eksporten er vaek - snapshottet fryses stadig ved Submit (payload_fx).
    Tallene er renderMetrics (FL66)."""
    count = badge("txtFlCount", COUNTS, width=220)
    save = _fit(button("btnFlSaveDraft", '"Save draft"', with_busy("varFlSaving", S.save_fx()),
                       icon=ICON_SAVE,
                       display_mode=(f'If(varFlStatus = "Indsendt" || CountRows({S.LIVE}) = 0, '
                                     f'DisplayMode.Disabled, DisplayMode.Edit)')), icon=True)
    save.props["Tooltip"] = ('"Puts the request on the landing page as Draft - '
                             'it can still be edited."')
    # Submit spoerger foerst (build_submit_confirm, issue #54).
    submit = _fit(button("btnFlSubmit", '"Submit"', "Set(varFlConfirmSubmit, true)",
                         primary=True, icon=ICON_SUBMIT, display_mode=S.SUBMIT_DM), icon=True)
    submit.props["Tooltip"] = S.SUBMIT_WHY
    new = _fit(button("btnFlNew", '"New request"', NEW_FX, icon="Add"), icon=True)
    for b in (save, submit, new):
        _bar_btn(b)
    # Temaskiftet og vejen til hubben staar i sidebaren (tools/side_nav.py).
    bar = top_bar("Fl", f'"{cfg.TITLE}"', SUBTITLE, [count, save, submit, new],
                  icon=cfg.APP_KEY)
    count.vis = at_least("Desktop")
    return bar


# ---------------------------------------------------------------------------
# Tabellerne - Validation og Classes deler kolonnemodellen (issue #77)
# ---------------------------------------------------------------------------
GAP = 8
# Budgettet for en gallerirakkes celler: kortets padding, scrollbar og
# GALLERY_RESERVE (se docs/30, regel J). Galleriet har TemplatePadding 0.
ROWS_W = f"({SHELL_W} - 36 - {SCROLLBAR_W} - {GALLERY_RESERVE})"
ROW_H = 44
GAL_MAX = 12
# Validation's mindste bredde, og Functional Location + Description tilsammen.
VAL_MIN = 64
PAIR_MAX = 300
PAIR_MIN = 144


class Cols:
    """Kolonnebredderne for een tabel - de SAMME udtryk i overskriften og
    i raekken, saa de altid flugter (check_layout regel 29).

    Raekken maa aldrig blive bredere end tabellen - saa kommer der en
    vandret scrollbar, og Delete/Open ryger ud over kanten:
      - de to midterste kolonner skjules, naar Validation/Info ikke kan faa
        160 px ved siden af dem (som foer);
      - Functional Location og Description deler PAIR_MAX, men krymper
        sammen ned til PAIR_MIN, foer Validation/Info kommer under VAL_MIN;
      - under Tablet skjules # (raekkenummeret), og act_narrow er
        handlingsknappens bredde dér (Delete bliver et ikon)."""

    def __init__(self, mid, act_w, act_narrow=None):
        self.mid = mid                      # [(navn, overskrift, bredde)]
        self.act = (f"If({NARROW}, {act_narrow}, {act_w})" if act_narrow is not None
                    else str(act_w))
        full = 28 + PAIR_MAX + sum(w for _n, _l, w in mid) + act_w + GAP * (4 + len(mid))
        self.show_mid = f"({ROWS_W}) >= {full} + 160"
        self.show_no = at_least("Tablet")
        mid_sum = sum(w + GAP for _n, _l, w in mid)
        # Alt andet end parret: #, midten, handlingen, Validation-minimum og
        # de tre mellemrum mellem FL, Description, Validation og handlingen.
        self.others = (f"If({self.show_no}, {28 + GAP}, 0) + {self.act} + "
                       f"If({self.show_mid}, {mid_sum}, 0) + {VAL_MIN} + {3 * GAP}")
        self.pair = f"Min({PAIR_MAX}, Max({PAIR_MIN}, ({ROWS_W}) - ({self.others})))"
        self.fl = f"({self.pair}) * 160 / {PAIR_MAX}"
        self.desc = f"({self.pair}) * 140 / {PAIR_MAX}"
        # Resten - regnet af det samme udtryk, ikke af galleriets Parent.Width.
        self.rest = f"Max(48, ({ROWS_W}) - ({self.others}) + {VAL_MIN} - ({self.pair}))"

    def spec(self, rest_name, rest_label, act_name, act_label):
        """(navn, overskrift, bredde, synlig) i raekkefoelge."""
        return ([("No", "#", 28, self.show_no),
                 ("Fl", "Functional Location", self.fl, None),
                 ("Desc", "Description", self.desc, None)]
                + [(n, l, w, self.show_mid) for n, l, w in self.mid]
                + [(rest_name, rest_label, self.rest, None),
                   (act_name, act_label, self.act, None)])


def table_head(name, spec):
    """Kolonneoverskrifterne og stregen under dem (Masterdata Hub's
    moenster, issue #70)."""
    head = group(name,
                 pin_widths([text_ctrl(f"txt{name[3:]}{n}", f'"{lbl}"', size=11, color=C_MUTED,
                                       weight="Semibold", height=18, width=w, wrap="false",
                                       visible=vis)
                             for n, lbl, w, vis in spec]),
                 direction="Horizontal", gap=GAP, height=18, align_items="Center")
    return head


def divider(name, visible=None):
    return group(name, [], direction="Horizontal", height=1, fill=C_DIVIDER, visible=visible)


def table_gallery(name, label, items, count, cells, row_name, visible=None):
    """Et galleri med een raekke pr. element og en streg mellem raekkerne.

    INGEN RAEKKE-SCROLLBAR. Foer var hoejden n x (ROW_H + 2), men med
    TemplatePadding 2 fylder n raekker n x (ROW_H + 2) + 2 - saa selv een
    raekke fik sin egen scrollbar. Nu er TemplatePadding 0, og hoejden er
    praecis n x ROW_H. Galleriet scroller KUN, naar der er flere end
    GAL_MAX raekker - saa er det sektionens scrollbar, og overskriften
    staar fast over den."""
    tpl = group(row_name, pin_widths(cells), direction="Horizontal", gap=GAP,
                height="Parent.TemplateHeight - 1", align_items="Center", justify="Start",
                width="Parent.TemplateWidth")
    # Stregen er sin egen figur nederst i raekken (build_helpers.row_rule) -
    # ikke galleriets fyld, der ogsaa ville ses under den sidste raekke.
    rule = row_rule(f"rct{row_name[3:]}Rule", ROW_H)
    gal_h = f"Min({count}, {GAL_MAX}) * {ROW_H}"
    props = {
        "AccessibleLabel": label,
        "BorderStyle": "BorderStyle.None",
        "Fill": C_CARD_BG,
        "FillPortions": "0",
        "Height": gal_h,
        "Items": items,
        "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None",
        "Selectable": "false",
        "ShowScrollbar": f"{count} > {GAL_MAX}",
        "TabIndex": "0",
        "TemplatePadding": "0",
        "TemplateSize": str(ROW_H),
        "Width": "Parent.Width",
        "WrapCount": "1",
    }
    if visible is not None:
        props["Visible"] = visible
    return Ctrl(name, "Gallery", variant="Vertical", props=props, children=[tpl, rule],
                h=gal_h, vis=visible)


def _cells(spec, ctrls):
    """Saetter kolonnens bredde og synlighed paa cellen."""
    out = []
    for (_n, _l, w, vis), c in zip(spec, ctrls):
        c.props["Width"] = str(w)
        if vis is not None:
            c.props["Visible"] = vis if not c.props.get("Visible") else f"({vis}) && ({c.props['Visible']})"
            c.vis = c.props["Visible"]
        out.append(c)
    return out


VCOLS = Cols([("Kks", "KKS Type", 64), ("Cls", "Assigned Class", 96)], act_w=76, act_narrow=36)
V_SPEC = VCOLS.spec("Val", "Validation", "Act", "Action")

ERRS = 'CountRows(Filter(colFlRows, Status = "invalid"))'


def verify_button():
    """HELE valideringen - skjult. Alle aendringer kalder den med
    Select(btnFlVerify) (REVERIFY, docs/31 PX7). Select virker paa en
    skjult knap; den skal bare staa paa samme skaerm."""
    b = button("btnFlVerify", '"Verify"', V.verify_fx(), width=100, visible="false",
               accessible='"Validate the rows"')
    return b


def build_rows():
    title = grow(text_ctrl("txtFlRowsH", '"Validation"', size=16, weight="Semibold",
                           height=22, wrap="false"))
    add = _fit(button("btnFlAddRow", '"Add row"', add_row_fx() + ";\n" + REVERIFY,
                      display_mode=DM_EDIT))
    head_row = group("conFlRowsTop", pin_widths([title, add]), direction="Horizontal",
                     gap=12, align_items="Center")

    head = table_head("conFlRowsHead", V_SPEC)

    row = "ThisItem"
    no = text_ctrl("txtFlRowNo", "Text(CountRows(Filter(colFlRows, RowNo <= ThisItem.RowNo)))",
                   size=13, color=C_MUTED, height=20, wrap="false")
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
                    size=13, height=20, wrap="false")
    cls = text_ctrl("txtFlRowCls",
                    'If(IsBlank(ThisItem.AssignedClass), "-", ThisItem.AssignedClass)',
                    size=13, weight="Semibold", height=20, wrap="false")

    # FL26: chippen og den foerste fejl eller advarsel (renderValidationBadges).
    # Teksten afkortes med vilje - hele forklaringen staar bag "?".
    shown = 'If(ThisItem.Status = "invalid", ThisItem.FirstIssue, ThisItem.FirstWarning)'
    msg = ('Switch(ThisItem.Status, "draft", "Draft", "valid", "Valid", '
           '"warning", "Warning" & If(IsBlank(ThisItem.FirstWarning), "", " - " & ThisItem.FirstWarning), '
           'If(IsBlank(ThisItem.FirstIssue), "Invalid", ThisItem.FirstIssue))')
    hint_expr = V.hint_fx(shown, "ThisItem.FL")
    has_hint = f"!IsBlank({hint_expr})"
    val_txt = text_ctrl("txtFlRowIssue", msg, size=13, color=_status_color(row), height=20,
                        wrap="false", width=f"({VCOLS.rest}) - If({has_hint}, 36, 0)")
    hint = button("btnFlRowHint", '"?"', f"Notify({hint_expr}, NotificationType.Information)",
                  width=30, height=30, visible=has_hint,
                  accessible='"What does this message mean?"')
    hint.props["Tooltip"] = hint_expr
    val = group("conFlRowVal", [val_txt, hint], direction="Horizontal", gap=6,
                height=30, align_items="Center")

    # Under Tablet er Delete et ikon, saa hele raekken kan staa (issue #77).
    delete = button("btnFlRowDelete", '"Delete"', f"""Remove(colFlRows, LookUp(colFlRows, RowGuid = ThisItem.RowGuid));
RemoveIf(colFlVals, RowGuid = ThisItem.RowGuid);
RemoveIf(colFlIssues, RowGuid = ThisItem.RowGuid);
If(CountRows(colFlRows) = 0, {add_row_fx()});
{REVERIFY}""", danger=True, width=76, height=30, display_mode=DM_EDIT, icon="Delete",
                    accessible='"Delete row " & ThisItem.RowNo')
    delete.props["Layout"] = f"If({NARROW}, ButtonLayout.IconOnly, ButtonLayout.TextOnly)"

    cells = _cells(V_SPEC, [no, fl, desc, kks, cls, val, delete])
    gal = table_gallery("galFlRows", '"Functional Location rows"', "Sort(colFlRows, RowNo)",
                        "CountRows(colFlRows)", cells, "conFlRow")

    # Kun noget at sige, naar der ER noget: en fejl ved gem/indsend, eller
    # raekker, der blokerer Submit. Ingen "Ready."/"Done." (issue #77).
    info = text_ctrl("txtFlInfo",
                     f'Coalesce(varFlInfo, "Submit is blocked: " & {ERRS} & " row(s) have errors.")',
                     size=12, color=C_INVALID_FG, height=18, wrap="false",
                     visible=f"!IsBlank(varFlInfo) || {ERRS} > 0")
    return card("conFlRowsCard", [head_row, head, divider("conFlRowsRule"), gal, info,
                                  verify_button()], gap=10)


# ---------------------------------------------------------------------------
# Klassefanerne (functional-location.html:77-81, FL28 og FL60)
# ---------------------------------------------------------------------------
CCOLS = Cols([("Str", "StrIndicator", 76), ("Cls", "Class", 96)], act_w=72)
C_SPEC = CCOLS.spec("Info", "Info", "Open", "Details")

# Faneindholdet: ALL = alle klasser, sorteret paa klasse og saa FL (renderClassTabs
# :1661-1664); en klasse = dens raekker sorteret paa FL (:1487).
VIEW = (f'SortByColumns(Filter({V.BUCKETS}, varFlTab = "ALL" || AssignedClass = varFlTab), '
        '"AssignedClass", SortOrder.Ascending, "FL", SortOrder.Ascending)')
# Hoejden foelger den VALGTE fane - ikke alle klassificerede raekker, som
# gav tom plads under en lille fane.
VIEW_N = (f'CountRows(Filter({V.BUCKETS}, varFlTab = "ALL" || AssignedClass = varFlTab))')
HAS_CLASSES = f"IfError(CountRows({V.BUCKETS}) > 0, false)"
# Pos er raekkens nummer i fanen (#, renderSpoolColumnCell :2057-2059).
VIEW_POS = ("With({ vw: " + VIEW + " },\n"
            "    ForAll(Sequence(CountRows(vw)) As S, With({ r: Index(vw, S.Value) },\n"
            "        { Pos: S.Value, RowGuid: r.RowGuid, FL: r.FL, Description: r.Description,\n"
            "          KksType: r.KksType, AssignedClass: r.AssignedClass, Status: r.Status,\n"
            "          FirstIssue: r.FirstIssue, FirstWarning: r.FirstWarning })))")
TAB_W = 136


def build_classes():
    """Uden klassificerede raekker er kortet KUN titlen og een linje - ingen
    tom fanebjaelke, overskrift eller tom raekke (issue #77)."""
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
        "Fill": C_CARD_BG,
        "FillPortions": "0",
        "Height": "40",
        "Items": "colFlTabs",
        "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None",
        "Selectable": "false",
        # Kun naar fanerne ikke kan staa paa een linje.
        "ShowScrollbar": f"CountRows(colFlTabs) * {TAB_W} > {SHELL_W} - 36",
        "TabIndex": "0",
        "TemplatePadding": "3",
        "TemplateSize": str(TAB_W - 6),
        "Visible": HAS_CLASSES,
        "Width": "Parent.Width",
        "WrapCount": "1",
    }, children=[tab], h=40, vis=HAS_CLASSES)

    note = text_ctrl("txtFlClassNote",
                     '"Compact view - open a row for all columns of its class."',
                     size=12, color=C_MUTED, height=18, wrap="false", visible=HAS_CLASSES)

    head = table_head("conFlClsHead", C_SPEC)
    head.props["Visible"] = HAS_CLASSES
    head.vis = HAS_CLASSES

    # FL og Description kan ogsaa rettes her (renderSpoolEditor, :2098).
    no = text_ctrl("txtFlCNo", "Text(ThisItem.Pos)", size=13, color=C_MUTED, height=20,
                   wrap="false")
    fl = text_input("inpFlCFl", "ThisItem.FL", max_length=40, width="160",
                    display_mode=DM_EDIT, label='"Functional Location"',
                    onchange=set_row_fx("ThisItem.RowGuid", "FL", norm_fl("Self.Text")))
    fl.props["BorderColor"] = _field_border(V.fl_bad("ThisItem"), "true")
    desc = text_input("inpFlCDesc", "ThisItem.Description", max_length=40, width="140",
                      display_mode=DM_EDIT, label='"Description"',
                      onchange=set_row_fx("ThisItem.RowGuid", "Description", "Trim(Self.Text)"))
    desc.props["BorderColor"] = _field_border(V.desc_bad("ThisItem"),
                                              "!IsBlank(ThisItem.Description)")
    strc = text_ctrl("txtFlCStr", "ThisItem.KksType", size=13, height=20, wrap="false")
    clsc = text_ctrl("txtFlCCls", "ThisItem.AssignedClass", size=13, weight="Semibold",
                     height=20, wrap="false")
    info_msg = "Coalesce(ThisItem.FirstIssue, ThisItem.FirstWarning, \"\")"
    info = text_ctrl("txtFlCInfo", info_msg, size=13, color=_status_color("ThisItem"),
                     height=20, wrap="false")
    open_ = button("btnFlCOpen", '"Open"',
                   'Set(varFlDetailRow, ThisItem.RowGuid);\n'
                   'Set(varFlDetailClass, Coalesce(ThisItem.AssignedClass, "NO CLASS"));\n'
                   'Set(varFlShowEmpty, false)', width=72, height=30,
                   accessible='"Open details for " & ThisItem.FL')
    cells = _cells(C_SPEC, [no, fl, desc, strc, clsc, info, open_])
    gal = table_gallery("galFlClassRows", '"Rows in the selected class"', VIEW_POS, VIEW_N,
                        cells, "conFlCRow", visible=HAS_CLASSES)
    empty = text_ctrl("txtFlNoClassRows",
                      '"No classified rows yet - a row appears here once its Functional Location is valid."',
                      size=13, color=C_MUTED, height=20, wrap="false",
                      visible=f"!({HAS_CLASSES})")
    return card("conFlClassesCard",
                [title, tabs, note, head, divider("conFlClsRule", HAS_CLASSES), gal, empty],
                gap=10)


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
    # TemplatePadding 0 og hoejden n x 46 - ingen scrollbar, foer der ER
    # flere felter end ruden kan vise (issue #77).
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
        "ShowScrollbar": f"CountRows({DET_ITEMS}) * 46 > App.Height - 220",
        "TabIndex": "0",
        "TemplatePadding": "0",
        "TemplateSize": "46",
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


# Skillelinjen mellem raekkerne - samme token som galleriernes (C_DIVIDER).
_RULE = f'border-bottom:1px solid " & {ref_hex("border-subtle")} & ";'


def _cell(x, muted=False, bold=False):
    color = ref_hex("text-muted") if muted else ref_hex("text-primary")
    weight = "font-weight:600;" if bold else ""
    return (f'"<td style=\'padding:6px 10px 6px 0;{_RULE}{weight}color:" & {color} & "\'>" & '
            f'{x} & "</td>"')


def structure_html():
    """FL-hierarkiet: vaerk -> KKS-noeglerne i positionerne, som motoren
    laeser dem (0: 1-3, 7: 7-9, 12: 12-13, 17: 17-18, 18: 18-19). Hver
    raekke viser sin klasse og status. Laeses, redigeres ikke."""
    head_cells = ["Plant", "Unit", "Function key", "No.", "Aggregate", "Pos. 14-16",
                  "Pos. 17-21", "Class", "Status"]
    th = "".join(
        f"<th style='text-align:left;padding:3px 10px 6px 0;{_RULE}font-weight:600;color:\" & "
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
            f'    "<tr><td colspan=\'9\' style=\'padding:10px 0 4px 0;font-weight:700;color:" & {ref_hex("text-primary")} & "\'>" & {_esc("P.Value")} & "</td></tr>" &\n'
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
    # Hoejden er indholdets: overskrift + en raekke pr. FL og pr. vaerk.
    # Uden raekker er HTML'en skjult - ingen tom tabeloverskrift.
    has = f"IfError(CountRows({LIVE}) > 0, false)"
    h = f"Min(34 + 30 * (CountRows({LIVE}) + CountRows(Distinct({LIVE}, Left(FL, 3)))), 600)"
    html = Ctrl("htmFlStructure", "HtmlViewer", props={
        "Fill": C_TRANSPARENT,
        "Height": h,
        "HtmlText": structure_html(),
        "PaddingBottom": "0", "PaddingLeft": "0", "PaddingRight": "0", "PaddingTop": "0",
        "Visible": has,
        "Width": "Parent.Width",
    }, h=h, vis=has)
    empty = text_ctrl("txtFlStructNone",
                      '"Enter a Functional Location above to see its structure."',
                      size=13, color=C_MUTED, height=20, wrap="false", visible=f"!({has})")
    return card("conFlStructCard", [title, sub, html, empty], gap=10)


# ---------------------------------------------------------------------------
# New request (FL70). Save draft, Submit og New request staar i bjaelken.
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
Set(varFlInfo, "")"""


def build_backdrop():
    vis = DET_OPEN
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


def build_submit_confirm():
    """Bekraeftelsen foer Submit og ventespinneren (issue #54).
    [sloer, popup, spinner] - SIDST i skaermens boern."""
    return confirm_modal(
        "Fl", "varFlConfirmSubmit", "Submit request?",
        '"A JSON snapshot is frozen and the rows are locked."',
        "Submit", with_busy("varFlSaving", S.submit_fx()), "btnFlSubmitConfirm") + [
        loading_overlay("imgFlSaving", "varFlSaving")]
