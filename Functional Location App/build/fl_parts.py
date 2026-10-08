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
                        C_CARD_BG, C_DIVIDER, C_ROW_HOVER, C_MUTED_BG)
from design_tokens import ref_hex
import layout_tokens as lay
from layout_tokens import SCROLLBAR_W, GALLERY_RESERVE, at_least, below
import icons
from build_helpers import (tap_backdrop, checkbox_theme, new_text_on_mobile, text_ctrl, group, button, text_input, themed_dropdown, card,
                           pin_widths, top_bar, grow, badge, fit_button_width, row_rule,
                           loading_overlay, with_busy, confirm_modal, delete_button, delete_modal, ICON_SAVE, ICON_SUBMIT,
                           ICON_W)

NARROW = below("Tablet")

# Indsendt = laast (FL69).
DM_EDIT = 'If(varFlViewOnly || varFlStatus = "Indsendt", DisplayMode.View, DisplayMode.Edit)'


def norm_fl(expr):
    """FL1: normalizeFlTyped + trim (app-functional-location.js:2368,
    fl-rule-engine.js:395)."""
    return (f"Upper(Trim(Substitute(Substitute(Substitute({expr}, Char(160), \" \"), "
            f"Char(13), \"\"), Char(10), \"\")))")


def add_row_fx():
    """FL63: en ny, tom raekke. Den bliver den valgte og foldes ud
    (issue #166, #184)."""
    return ("With({ g: Text(GUID()) },\n"
            "    Collect(colFlRows, { RowGuid: g, RowNo: varFlNextRowNo, SpId: 0, "
            "FL: \"\", Description: \"\", KksType: \"\", AssignedClass: \"\", Status: \"draft\", "
            "FirstIssue: \"\", FirstWarning: \"\", IssueCount: 0, WarningCount: 0, "
            "Pos: 0, FlBad: false, DescBad: false, Hint: \"\" });\n"
            "    Set(varFlDetailRow, g);\n"
            "    Set(varFlFoldOpen, true)\n"
            ");\n"
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
    save = _fit(button("btnFlSaveDraft", '"Save draft"', with_busy("varFlSaving", S.save_fx()),
                       icon=ICON_SAVE,
                       display_mode=(f'If(varFlViewOnly || varFlStatus = "Indsendt" || CountRows({S.LIVE}) = 0, '
                                     f'DisplayMode.Disabled, DisplayMode.Edit)')), icon=True)
    save.props["Tooltip"] = ('"Puts the request on the landing page as Draft - '
                             'it can still be edited."')
    # Submit spoerger foerst (build_submit_confirm, issue #54).
    submit = _fit(button("btnFlSubmit", '"Submit"', "Set(varFlConfirmSubmit, true)",
                         primary=True, icon=ICON_SUBMIT, display_mode=S.SUBMIT_DM),
                  icon=bool(ICON_SUBMIT))
    submit.props["Tooltip"] = S.SUBMIT_WHY
    new = _fit(button("btnFlNew", '"New request"', NEW_FX, icon="Add"), icon=True)
    edit = _fit(button("btnFlEdit", '"Edit"', "Set(varFlViewOnly, false)", icon="Edit",
                       visible="varFlViewOnly && varFlCanEdit",
                       display_mode="If(varFlCanEdit, DisplayMode.Edit, DisplayMode.Disabled)"),
                icon=True)
    _bar_btn(edit)
    _bar_btn(save)
    new_text_on_mobile(new, new.props["Width"])
    # Temaskiftet og vejen til hubben staar i sidebaren (tools/side_nav.py).
    bar = top_bar("Fl", f'"{cfg.TITLE}"', SUBTITLE,
                  [edit, delete_button("Fl", "varFlViewOnly", "varFlRequestGuid"), save, submit, new],
                  icon=cfg.APP_KEY, mode_var="varFlViewOnly")
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
# Naar Room, Sort Field og Warranty staar i raekken (issue #184).
EXTRA_PAIR = 240
EXTRA_VAL = 140


class Cols:
    """Kolonnebredderne for een tabel - de SAMME udtryk i overskriften og
    i raekken, saa de altid flugter (check_layout regel 29).

    Raekken maa aldrig blive bredere end tabellen - saa kommer der en
    vandret scrollbar, og Delete/Open ryger ud over kanten:
      - de to midterste kolonner skjules, naar Validation/Info ikke kan faa
        160 px ved siden af dem (som foer);
      - extra (issue #184: Room, Sort Field og Warranty) skjules FOER de
        midterste - kun naar der er plads til dem OG parret i fuld bredde;
      - Functional Location og Description deler PAIR_MAX, men krymper
        sammen ned til PAIR_MIN, foer Validation/Info kommer under VAL_MIN;
      - under Tablet skjules # (raekkenummeret), og act_narrow er
        handlingsknappens bredde dér (Delete bliver et ikon);
      - lead er en fast kolonne helt til venstre, der altid staar (fold-ud-
        pilen, issue #184)."""

    def __init__(self, mid, act_w, act_narrow=None, lead=0, extra=()):
        self.mid = mid                      # [(navn, overskrift, bredde)]
        self.extra = list(extra)            # [(navn, overskrift, bredde)]
        self.lead = lead
        self.act = (f"If({NARROW}, {act_narrow}, {act_w})" if act_narrow is not None
                    else str(act_w))
        lead_sum = lead + GAP if lead else 0
        full = (lead_sum + 28 + PAIR_MAX + sum(w for _n, _l, w in mid) + act_w
                + GAP * (4 + len(mid)))
        self.show_mid = f"({ROWS_W}) >= {full} + 160"
        extra_sum = sum(w + GAP for _n, _l, w in self.extra)
        # Med extra maa parret give lidt (EXTRA_PAIR) og Validation noejes
        # med EXTRA_VAL - ellers kom de foerst paa skaerme bredere end 1450.
        full_extra = full - PAIR_MAX + EXTRA_PAIR + extra_sum
        self.show_extra = (f"({self.show_mid}) && ({ROWS_W}) >= {full_extra} + {EXTRA_VAL}"
                           if self.extra else "false")
        self.show_no = at_least("Tablet")
        mid_sum = sum(w + GAP for _n, _l, w in mid)
        # Alt andet end parret: #, midten, handlingen, Validation-minimum og
        # de tre mellemrum mellem FL, Description, Validation og handlingen.
        self.others = (f"If({self.show_no}, {28 + GAP}, 0) + {self.act} + "
                       f"If({self.show_mid}, {mid_sum}, 0) + {VAL_MIN} + {3 * GAP}")
        if lead:
            self.others = f"{lead_sum} + " + self.others
        if self.extra:
            self.others += f" + If({self.show_extra}, {extra_sum}, 0)"
        self.pmax = f"If({NARROW}, 190, {PAIR_MAX})"
        self.pair = f"Min({self.pmax}, Max(If({NARROW}, 100, {PAIR_MIN}), ({ROWS_W}) - ({self.others})))"
        self.fl = f"({self.pair}) * 160 / ({self.pmax})"
        self.desc = f"({self.pair}) * 140 / ({self.pmax})"
        # Resten - regnet af det samme udtryk, ikke af galleriets Parent.Width.
        self.rest = f"Max(48, ({ROWS_W}) - ({self.others}) + {VAL_MIN} - ({self.pair}))"

    def spec(self, rest_name, rest_label, act_name, act_label, lead_name=None):
        """(navn, overskrift, bredde, synlig) i raekkefoelge."""
        lead = [(lead_name, "", self.lead, None)] if self.lead else []
        return (lead
                + [("No", "#", 28, self.show_no),
                   ("Fl", "Functional Location", self.fl, None),
                   ("Desc", "Description", self.desc, None)]
                + [(n, l, w, self.show_mid) for n, l, w in self.mid]
                + [(n, l, w, self.show_extra) for n, l, w in self.extra]
                + [(rest_name, rest_label, self.rest, None),
                   (act_name, act_label, self.act, None)])


def table_head(name, spec):
    """Kolonneoverskrifterne og stregen under dem (Masterdata Hub's
    moenster, issue #70)."""
    head = group(name,
                 pin_widths([text_ctrl(f"txt{name[3:]}{n}", f'"{lbl}"', size=11, color=C_MUTED,
                                       weight="Semibold", height=18, width=w, wrap="false",
                                       visible=vis,
                                       # Fold-ud-kolonnen har ingen overskrift (issue #184).
                                       accessible=None if lbl else '"Expand or collapse"')
                             for n, lbl, w, vis in spec]),
                 direction="Horizontal", gap=GAP, height=18, align_items="Center")
    return head


def divider(name, visible=None):
    return group(name, [], direction="Horizontal", height=1, fill=C_DIVIDER, visible=visible)


def table_gallery(name, label, items, count, cells, row_name, visible=None, row_fill=None):
    """Et galleri med een raekke pr. element og en streg mellem raekkerne.

    INGEN RAEKKE-SCROLLBAR. Foer var hoejden n x (ROW_H + 2), men med
    TemplatePadding 2 fylder n raekker n x (ROW_H + 2) + 2 - saa selv een
    raekke fik sin egen scrollbar. Nu er TemplatePadding 0, og hoejden er
    praecis n x ROW_H. Galleriet scroller KUN, naar der er flere end
    GAL_MAX raekker - saa er det sektionens scrollbar, og overskriften
    staar fast over den."""
    tpl = group(row_name, pin_widths(cells), direction="Horizontal", gap=GAP,
                height="Parent.TemplateHeight - 1", align_items="Center", justify="Start",
                width="Parent.TemplateWidth", fill=row_fill)
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


# Fold-ud-pilen staar forrest, Delete bagerst (issue #184). Edit-knappen
# fra #166 er vaek: pilen goer det samme - viser raekkens oevrige felter.
FOLD_W = 32
# Stamdatafelterne, der staar i den kompakte raekke (issue #184) - i
# raekkefoelge, med kolonnens bredde. Etiket og maks.-laengde er reglernes
# (fl_rules.generated.json, ens for alle klasser - tests/test_fl_sections).
_NO_CLASS = {c["Field"]: c for c in V.R["columns"] if c["Cls"] == "NO CLASS"}
COMPACT_VALS = [("Room", "ROOM", 64), ("Sort", "SORT FIELD", 100),
                ("WStart", "WARRANTY START", 96), ("WEnd", "WARRANTY END", 96)]
VCOLS = Cols([("Kks", "KKS Type", 64), ("Cls", "Assigned Class", 96)],
             act_w=76, act_narrow=36, lead=FOLD_W,
             extra=[(n, _NO_CLASS[f]["Column"], w) for n, f, w in COMPACT_VALS])
V_SPEC = VCOLS.spec("Val", "Validation", "Act", "Action", lead_name="Fold")

ERRS = 'CountRows(Filter(colFlRows, Status = "invalid"))'

# Den udfoldede raekke: varFlDetailRow (den valgte) og varFlFoldOpen.
# Kun een raekke er foldet ud ad gangen. Tabellen er to gallerier - raekkerne
# til og med den udfoldede og raekkerne efter den - med fold-ud-sektionen
# imellem, saa den staar direkte under sin raekke. Sammenklappet staar alle
# raekkerne i det foerste.
SEL_NO = "LookUp(colFlRows, RowGuid = varFlDetailRow).RowNo"
TOP_TEST = f"!varFlFoldOpen || RowNo <= {SEL_NO}"
BOTTOM_TEST = f"varFlFoldOpen && RowNo > {SEL_NO}"


def verify_button():
    """HELE valideringen - skjult. Alle aendringer kalder den med
    Select(btnFlVerify) (REVERIFY, docs/31 PX7). Select virker paa en
    skjult knap; den skal bare staa paa samme skaerm."""
    b = button("btnFlVerify", '"Verify"', V.verify_fx(DET_ITEMS, after=CLS_AFTER_VERIFY),
               width=100, visible="false", accessible='"Validate the rows"')
    return b


def _issue_on(guid, field):
    """Er der en fejl paa feltet? Samme udvalg som V.field_issue for
    spool-felterne (Ord >= 100)."""
    return (f'!IsBlank(LookUp(colFlIssues, RowGuid = {guid} && Sev = "Error" && '
            f'Field = "{field}" && Ord >= 100).Short)')


def row_cells(tag):
    """Cellerne i een kompakt raekke. tag skiller de to gallerier (Row og
    RowB) - et kontrolnavn maa kun findes een gang (regel 0)."""
    row = "ThisItem"
    is_open = "(ThisItem.RowGuid = varFlDetailRow && varFlFoldOpen)"
    fold = button(f"btnFl{tag}Fold", '"Expand"',
                  f"If({is_open}, Set(varFlFoldOpen, false), {SELECT_FX})",
                  width=FOLD_W, height=30,
                  icon=f'If({is_open}, "{icons.FLUENT["collapse"]}", "{icons.FLUENT["expand"]}")',
                  accessible=f'If({is_open}, "Collapse row ", "Expand row ") & ThisItem.Pos',
                  tooltip=f'If({is_open}, "Hide the other fields of this row", '
                          '"Show the other fields of this row")')
    fold.props["Layout"] = "ButtonLayout.IconOnly"
    # Pos, FlBad, DescBad og Hint regnes i valideringen (B6).
    no = text_ctrl(f"txtFl{tag}No", "Text(ThisItem.Pos)",
                   size=13, color=C_MUTED, height=20, wrap="false")
    fl = text_input(f"inpFl{tag}Fl", "ThisItem.FL", max_length=40, width="160",
                    display_mode=DM_EDIT, label='"Functional Location"',
                    onchange=set_row_fx("ThisItem.RowGuid", "FL", norm_fl("Self.Text")))
    fl.props["BorderColor"] = _field_border(f"{row}.FlBad", f'{row}.Status <> "draft"')
    desc = text_input(f"inpFl{tag}Desc", "ThisItem.Description", max_length=40, width="140",
                      display_mode=DM_EDIT, label='"Description"',
                      onchange=set_row_fx("ThisItem.RowGuid", "Description", "Trim(Self.Text)"))
    desc.props["BorderColor"] = _field_border(
        f"{row}.DescBad", f'{row}.Status <> "draft" && !IsBlank({row}.Description)')
    kks = text_ctrl(f"txtFl{tag}Kks", 'If(IsBlank(ThisItem.KksType), "-", ThisItem.KksType)',
                    size=13, height=20, wrap="false")
    cls = text_ctrl(f"txtFl{tag}Cls",
                    'If(IsBlank(ThisItem.AssignedClass), "-", ThisItem.AssignedClass)',
                    size=13, weight="Semibold", height=20, wrap="false")

    # Room, Sort Field og Warranty: de samme spool-felter og regler som i
    # fold-ud-sektionen (colFlVals, set_val_fx, FL56) - bare i raekken.
    vals = []
    for n, f, w in COMPACT_VALS:
        col = _NO_CLASS[f]
        inp = text_input(f"inpFl{tag}{n}",
                         f'LookUp(colFlVals, RowGuid = ThisItem.RowGuid && Field = "{f}").Value',
                         max_length=col["MaxLen"], width=str(w), display_mode=DM_EDIT,
                         label=f'"{col["Column"]}"',
                         placeholder='"DD.MM.YYYY"' if f.startswith("WARRANTY") else '""',
                         onchange=set_val_fx("ThisItem.RowGuid", f'"{f}"', "Self.Text"))
        inp.props["BorderColor"] = _field_border(_issue_on("ThisItem.RowGuid", f), "false")
        vals.append(inp)

    # FL26: chippen og den foerste fejl eller advarsel (renderValidationBadges).
    # Teksten afkortes med vilje - hele forklaringen staar bag "?".
    msg = ('Switch(ThisItem.Status, "draft", "Draft", "valid", "Valid", '
           '"warning", "Warning" & If(IsBlank(ThisItem.FirstWarning), "", " - " & ThisItem.FirstWarning), '
           'If(IsBlank(ThisItem.FirstIssue), "Invalid", ThisItem.FirstIssue))')
    hint_expr = "ThisItem.Hint"
    has_hint = f"!IsBlank({hint_expr})"
    val_txt = text_ctrl(f"txtFl{tag}Issue", msg, size=13, color=_status_color(row), height=20,
                        wrap="false", width=f"({VCOLS.rest}) - If({has_hint}, 36, 0)")
    hint = button(f"btnFl{tag}Hint", '"?"', f"Notify({hint_expr}, NotificationType.Information)",
                  width=30, height=30, visible=has_hint,
                  accessible='"What does this message mean?"')
    hint.props["Tooltip"] = hint_expr
    val = group(f"conFl{tag}Val", [val_txt, hint], direction="Horizontal", gap=6,
                height=30, align_items="Center")

    # Under Tablet er Delete et ikon, saa hele raekken kan staa (issue #77).
    delete = button(f"btnFl{tag}Delete", '"Delete"', f"""Collect(colFlDeleted, {{ RowGuid: ThisItem.RowGuid }});
Remove(colFlRows, LookUp(colFlRows, RowGuid = ThisItem.RowGuid));
RemoveIf(colFlVals, RowGuid = ThisItem.RowGuid);
RemoveIf(colFlIssues, RowGuid = ThisItem.RowGuid);
If(CountRows(colFlRows) = 0, {add_row_fx()});
{REVERIFY}""", danger=True, width=76, height=30, display_mode=DM_EDIT, icon="Delete",
                    accessible='"Delete row " & ThisItem.Pos')
    delete.props["Layout"] = f"If({NARROW}, ButtonLayout.IconOnly, ButtonLayout.TextOnly)"
    delete.props["Width"] = f"If({NARROW}, 36, 76)"
    return _cells(V_SPEC, [fold, no, fl, desc, kks, cls] + vals + [val, delete])


def build_rows():
    title = grow(text_ctrl("txtFlRowsH", '"Validation"', size=lay.SIZE_CARD_TITLE, weight="Semibold",
                           height=26, wrap="false"))
    add = _fit(button("btnFlAddRow", '"Add row"', add_row_fx() + ";\n" + REVERIFY,
                      display_mode=DM_EDIT))
    head_row = group("conFlRowsTop", pin_widths([title, add]), direction="Horizontal",
                     gap=12, align_items="Center")

    head = table_head("conFlRowsHead", V_SPEC)

    # Den udfoldede raekke er markeret.
    fill = f"If(ThisItem.RowGuid = varFlDetailRow && varFlFoldOpen, {C_ROW_HOVER}, {C_TRANSPARENT})"
    top = table_gallery("galFlRows", '"Functional Location rows"',
                        f"Sort(Filter(colFlRows, {TOP_TEST}), RowNo)",
                        f"CountRows(Filter(colFlRows, {TOP_TEST}))", row_cells("Row"), "conFlRow",
                        row_fill=fill)
    bottom = table_gallery("galFlRowsB", '"Functional Location rows below the expanded row"',
                           f"Sort(Filter(colFlRows, {BOTTOM_TEST}), RowNo)",
                           f"CountRows(Filter(colFlRows, {BOTTOM_TEST}))", row_cells("RowB"),
                           "conFlRowB", row_fill=fill)
    # Ingen afstand mellem galleri, fold-ud og galleri - det er een tabel.
    table = group("conFlTable", [top, build_fold(), bottom], direction="Vertical", gap=0)

    # Kun noget at sige, naar der ER noget: en fejl ved gem/indsend, eller
    # raekker, der blokerer Submit. Ingen "Ready."/"Done." (issue #77).
    info = text_ctrl("txtFlInfo",
                     f'Coalesce(varFlInfo, "Submit is blocked: " & {ERRS} & " row(s) have errors.")',
                     size=12, color=C_INVALID_FG, height=18, wrap="false",
                     visible=f"!IsBlank(varFlInfo) || {ERRS} > 0")
    return card("conFlRowsCard", [head_row, head, divider("conFlRowsRule"), table, info,
                                  verify_button()], gap=10)


# ---------------------------------------------------------------------------
# Klassefanerne (functional-location.html:77-81, FL28 og FL60)
# ---------------------------------------------------------------------------
CCOLS = Cols([("Str", "StrIndicator", 76), ("Cls", "Class", 96)], act_w=72)
C_SPEC = CCOLS.spec("Info", "Info", "Open", "Edit")

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
            "          FirstIssue: r.FirstIssue, FirstWarning: r.FirstWarning,\n"
            "          FlBad: r.FlBad, DescBad: r.DescBad })))")
TAB_W = 136


def build_classes():
    """Uden klassificerede raekker er kortet KUN titlen og een linje - ingen
    tom fanebjaelke, overskrift eller tom raekke (issue #77)."""
    title = text_ctrl("txtFlClassesH", '"Classes"', size=lay.SIZE_CARD_TITLE, weight="Semibold", height=26,
                      wrap="false")

    tab = button("btnFlTab", "ThisItem.Label", "Set(varFlTab, ThisItem.Key)", width=130, height=34)
    sel = "varFlTab = ThisItem.Key"
    tab.props["Appearance"] = f"If({sel}, ButtonAppearance.Primary, ButtonAppearance.Outline)"
    tab.props["BasePaletteColor"] = C_PRIMARY
    tab.props["Color"] = f"If({sel}, {C_WHITE}, {C_TITLE})"
    # FL65: klassens hjaelpetekst (resolveClassHelpText :2353-2357).
    tab.props["Tooltip"] = ('With({ hp: LookUp(colFlClassHelp, Key = ThisItem.Key).Help }, '
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
                     '"Compact view - Edit expands the row in the table above."',
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
    fl.props["BorderColor"] = _field_border("ThisItem.FlBad", "true")
    desc = text_input("inpFlCDesc", "ThisItem.Description", max_length=40, width="140",
                      display_mode=DM_EDIT, label='"Description"',
                      onchange=set_row_fx("ThisItem.RowGuid", "Description", "Trim(Self.Text)"))
    desc.props["BorderColor"] = _field_border("ThisItem.DescBad",
                                              "!IsBlank(ThisItem.Description)")
    strc = text_ctrl("txtFlCStr", "ThisItem.KksType", size=13, height=20, wrap="false")
    clsc = text_ctrl("txtFlCCls", "ThisItem.AssignedClass", size=13, weight="Semibold",
                     height=20, wrap="false")
    info_msg = "Coalesce(ThisItem.FirstIssue, ThisItem.FirstWarning, \"\")"
    info = text_ctrl("txtFlCInfo", info_msg, size=13, color=_status_color("ThisItem"),
                     height=20, wrap="false")
    open_ = button("btnFlCOpen", '"Edit"', SELECT_FX, width=72, height=30,
                   accessible='"Edit " & ThisItem.FL & " in the table above"')
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
# Fold-ud-sektionen og Class data-popuppen (issue #184, afloeser #166's
# formular under listen)
#
#   Fold-ud  - under den udfoldede raekke: de stamdatafelter, der IKKE staar
#              i den kompakte raekke, og knappen Class data.
#   Popuppen - klassens karakteristikker, TRM og GIV_EXT/WCM for netop den
#              raekke. Den redigerer en KOPI (colFlClsDet); Apply skriver
#              kopien tilbage og validerer, Cancel og luk kasserer den.
# Hvilke felter der er hvor, er Section i colFlColumns (harnessens
# buildPlan), og editoren er Kind (generate_app_onstart.editor_kind).
# ---------------------------------------------------------------------------
DR = "LookUp(colFlRows, RowGuid = varFlDetailRow)"
# Klassen bestemmes af KKS-koden (FL16-FL23) - ingen overstyring. En raekke
# uden klasse viser stamdata fra NO CLASS (ens for alle klasser, se
# tests/test_fl_sections.py) og ingen klassedata.
HAS_CLASS = f"!IsBlank({DR}.AssignedClass)"


def _display_val(dr, field):
    """getSpoolColumnValue (:2205-2242) for de felter, formularen viser."""
    raw = f"LookUp(colFlVals, RowGuid = {dr}.RowGuid && Field = {field}).Value"
    return (f'Switch({field},\n'
            f'    "STRINDICATOR", {dr}.KksType,\n'
            f'    "STR. INDICATOR", {dr}.KksType,\n'
            f'    "FUNCTIONAL LOCATION", {dr}.FL,\n'
            f'    "DESCRIPTION", {dr}.Description,\n'
            f'    Coalesce({raw}, ""))')


def det_items(row_var, section_test):
    """Felterne i een sektion for raekken row_var - med vaerdi og besked.
    Regnet EEN gang (ved valg, aabning og validering); gallerierne
    filtrerer kun den lille, lokale samling (ingen kald)."""
    return f"""With(
    {{ dr: LookUp(colFlRows, RowGuid = {row_var}) }},
    With(
        {{ dc: Coalesce(dr.AssignedClass, "NO CLASS") }},
        ForAll(
            Sort(Filter(colFlColumns, Cls = dc && {section_test}), Ord) As K,
            {{
                Column: K.Column, Field: K.Field, Editable: K.Editable,
                List: K.List, MaxLen: K.MaxLen, Section: K.Section, Kind: K.Kind,
                Value: {_display_val("dr", "K.Field")},
                Issue: {V.field_issue("dr.RowGuid", "K.Field")}
            }}
        )
    )
)"""


# Fold-ud-sektionens felter: stamdata for den valgte raekke - regnet, naar
# raekken vaelges, og efter hver validering (fl_validation.verify_fx, H).
DET_ITEMS = det_items("varFlDetailRow", 'Section = "Master"')

# At vaelge en raekke: den foldes ud, og sektionen viser den med det samme.
SELECT_FX = ("Set(varFlDetailRow, ThisItem.RowGuid);\nSet(varFlFoldOpen, true);\n"
             "ClearCollect(colFlDet, " + DET_ITEMS + ")")

# Dropdownens valg: tom, den gemte vaerdi hvis den er ugyldig, og listen
# (renderSpoolEditor :2112-2131).
DD_ITEMS = """Ungroup(
    Table(
        { G: Table({ Value: "" }) },
        { G: Filter(Table({ Value: ThisItem.Value }), !IsBlank(Value) &&
                    !(Upper(Value) in With({ lid: ThisItem.List }, Filter(colFlLists, List = lid)).UValue)) },
        { G: ForAll(Sort(With({ lid: ThisItem.List }, Filter(colFlLists, List = lid)), Ord) As O, { Value: O.Value }) }
    ),
    G
)"""

# To felter pr. linje - eet paa mobil (issue #184).
FORM_COLS = lay.if_below("Tablet", "1", "2")
TILE_H = 86
TILE_GAP = 16

# En kort hjaelp under feltet, naar det ikke har en besked.
FIELD_HELP = ('Switch(ThisItem.Field, '
              '"STRINDICATOR", "Derived from the KKS code.", '
              '"ABC INDIC.", "Set automatically from the TRM fields.", '
              '"TRM ASSIGNMENT", "Set automatically from the TRM fields.", '
              '"WARRANTY START", "Format DD.MM.YYYY", '
              '"WARRANTY END", "Format DD.MM.YYYY", '
              '"")')


def _set_detail(value):
    """Fold-ud-sektionens felter skriver direkte i raekkens data."""
    return set_val_fx("varFlDetailRow", "ThisItem.Field", value)


def _set_copy(value):
    """Popuppens felter skriver KUN i kopien - Apply overfoerer den."""
    return (f"Patch(colFlClsDet, LookUp(colFlClsDet, Field = ThisItem.Field), "
            f"{{ Value: {value} }})")


def field_grid(tag, section_test, label, source="colFlDet", set_fx=_set_detail):
    """Et gitter af felter fra source (colFlDet eller popuppens kopi). Hvert
    felt: etiket, editor (efter Kind) og en linje med beskeden - eller en
    kort hjaelp."""
    items = f"Filter({source}, {section_test})"
    n = f"CountRows({items})"
    w = "Parent.Width"
    lbl = text_ctrl(f"txtFl{tag}Lbl",
                    'ThisItem.Column & If(ThisItem.Field = "DESCRIPTION", " *", "")',
                    size=12, color=C_MUTED, weight="Semibold", height=18, wrap="false")
    txt = text_input(f"inpFl{tag}Val", "ThisItem.Value", width=w, display_mode=DM_EDIT,
                     label="ThisItem.Column",
                     placeholder='If(ThisItem.Field = "WARRANTY START" || ThisItem.Field = "WARRANTY END", '
                                 '"DD.MM.YYYY", "")',
                     onchange=set_fx("Self.Text"))
    txt.props["MaxLength"] = "If(ThisItem.MaxLen > 0, ThisItem.MaxLen, 4000)"
    txt.props["BorderColor"] = _field_border("!IsBlank(ThisItem.Issue)", "!IsBlank(ThisItem.Value)")
    txt.vis = 'ThisItem.Kind = "text"'
    dd = themed_dropdown(f"drpFl{tag}Val", DD_ITEMS,
                         f"LookUp({DD_ITEMS}, Upper(Value) = Upper(ThisItem.Value)).Value",
                         width=w, display_mode=DM_EDIT, label="ThisItem.Column")
    dd.props["OnChange"] = set_fx("Coalesce(Self.Selected.Value, \"\")")
    dd.props["BorderColor"] = _field_border("!IsBlank(ThisItem.Issue)", "!IsBlank(ThisItem.Value)")
    dd.vis = 'ThisItem.Kind = "list"'
    # X-felterne (Atex, TRM assignment, GIV_EXT assignment): afkrydsning,
    # der gemmer X eller intet. Samme ModernCheckbox som Equipment/Material.
    chk = Ctrl(f"chkFl{tag}Val", "ModernCheckbox", props=checkbox_theme({
        "AccessibleLabel": "ThisItem.Column",
        "Default": 'Upper(Trim(ThisItem.Value)) = "X"',
        "DisplayMode": DM_EDIT,
        "Height": "36",
        "Label": '"Yes"',
        "OnCheck": set_fx('"X"'),
        "OnUncheck": set_fx('""'),
        "Width": w,
    }), h=36, vis='ThisItem.Kind = "check"')
    ro = text_ctrl(f"txtFl{tag}Ro", 'If(IsBlank(ThisItem.Value), "-", ThisItem.Value)',
                   size=14, weight="Semibold", height=36, wrap="false",
                   visible='ThisItem.Kind = "ro"')
    issue = text_ctrl(f"txtFl{tag}Issue", f"Coalesce(ThisItem.Issue, {FIELD_HELP})",
                      size=12, color=f"If(IsBlank(ThisItem.Issue), {C_MUTED}, {C_INVALID_FG})",
                      height=18, wrap="false")
    tile = group(f"conFl{tag}Tile", [lbl, txt, dd, chk, ro, issue], direction="Vertical", gap=2,
                 width="Parent.TemplateWidth", height="Parent.TemplateHeight",
                 pad=(0, TILE_GAP, 10, 0))
    gal_h = f"RoundUp({n} / ({FORM_COLS}), 0) * {TILE_H}"
    vis = f"IfError({n} > 0, false)"
    gal = Ctrl(f"galFl{tag}Fields", "Gallery", variant="Vertical", props={
        "AccessibleLabel": label,
        "BorderStyle": "BorderStyle.None",
        "Fill": C_TRANSPARENT,
        "FillPortions": "0",
        "Height": gal_h,
        "Items": items,
        "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None",
        "Selectable": "false",
        "ShowScrollbar": "false",
        "TabIndex": "0",
        "TemplatePadding": "0",
        "TemplateSize": str(TILE_H),
        "Visible": vis,
        "Width": "Parent.Width",
        "WrapCount": FORM_COLS,
    }, children=[tile], h=gal_h, vis=vis)
    return gal


def _group_title(name, text, visible):
    return text_ctrl(name, text, size=14, weight="Semibold", height=22, wrap="false",
                     visible=visible)


# Felterne, der staar i den kompakte raekke, vises ikke igen her. KKS Type
# og Room/Sort Field/Warranty kun, naar deres kolonner faktisk staar i
# raekken - paa en smal skaerm er de skjult dér og staar i stedet her.
_COMPACT_ALWAYS = '["FUNCTIONAL LOCATION", "DESCRIPTION"]'
_COMPACT_EXTRA = "[" + ", ".join(f'"{f}"' for _n, f, _w in COMPACT_VALS) + "]"
FOLD_TEST = (f'Section = "Master" && !(Field in {_COMPACT_ALWAYS}) && '
             f'!(Field = "STRINDICATOR" && {VCOLS.show_mid}) && '
             f'!(Field in {_COMPACT_EXTRA} && {VCOLS.show_extra})')
FOLD_OPEN = f"varFlFoldOpen && !IsBlank({DR}.RowGuid)"
CLS_TIP = ('If(' + HAS_CLASS + ', "Edit the class characteristics, TRM and GIV_EXT / WCM fields of this row", '
           '"No class yet - the class is determined by the KKS code. Enter a valid Functional Location first.")')


def build_fold():
    """Fold-ud-sektionen under den udfoldede raekke (issue #184)."""
    grid = field_grid("M", FOLD_TEST, '"Other fields of the expanded row"')
    btn = _fit(button("btnFlClassData", '"Class data"', OPEN_CLS_FX,
                      display_mode=f"If({HAS_CLASS}, DisplayMode.Edit, DisplayMode.Disabled)",
                      tooltip=CLS_TIP, accessible='"Class data of row " & ' + DR + '.Pos'))
    # Uden klasse siges hvorfor - en tooltip paa en deaktiveret knap ses
    # ikke paa en touchskaerm. Paa en smal skaerm, hvor klassekolonnen er
    # skjult, staar klassen her (ellers staar den kun i raekken).
    note_fx = (f'If(!({HAS_CLASS}), "No class yet - the class is determined by the KKS code.", '
               f'!({VCOLS.show_mid}), "Assigned Class: " & {DR}.AssignedClass, "")')
    note = grow(text_ctrl("txtFlFoldNote", note_fx, size=12, color=C_MUTED, height=18,
                          wrap="false", visible=f"!({HAS_CLASS}) || !({VCOLS.show_mid})"))
    foot = group("conFlFoldFoot", pin_widths([btn, note]), direction="Horizontal", gap=12,
                 align_items="Center")
    return group("conFlFold", [grid, foot], direction="Vertical", gap=8,
                 fill=C_MUTED_BG, border_color=C_DIVIDER, radius=lay.RADIUS_INPUT,
                 pad=(12, 12, 12, 12), visible=FOLD_OPEN)


# --- Class data-popuppen ----------------------------------------------------
CR = "LookUp(colFlRows, RowGuid = varFlClsRow)"
CLS_TEST = 'Section in ["Class", "TRM", "Ext"]'
CLS_ITEMS = det_items("varFlClsRow", CLS_TEST)
CLS_LOCKED = 'varFlViewOnly || varFlStatus = "Indsendt"'
CLS_OPEN = "IfError(varFlClsOpen, false)"
# Kopien laves af raekkens GEMTE vaerdier, hver gang popuppen aabnes - en
# anden raekkes popup kan derfor aldrig se denne raekkes kladde.
OPEN_CLS_FX = ("Set(varFlClsRow, varFlDetailRow);\n"
               "ClearCollect(colFlClsDet, " + CLS_ITEMS + ");\n"
               "Set(varFlClsOpen, true)")
CLOSE_CLS_FX = "Set(varFlClsOpen, false);\nClear(colFlClsDet)"
# Apply: kopiens redigerbare felter erstatter raekkens (samme form som
# set_val_fx: trimmet, tomt = intet), og valideringen koerer.
APPLY_CLS_FX = f"""With(
    {{ r: varFlClsRow, ed: Filter(colFlClsDet, Editable) }},
    RemoveIf(colFlVals, RowGuid = r && Field in ed.Field);
    Collect(colFlVals, ForAll(Filter(ed, !IsBlank(Trim(Value))) As E, {{ RowGuid: r, Field: E.Field, Value: Trim(E.Value) }}))
);
Set(varFlClsCheck, true);
{REVERIFY}"""
# Efter valideringen (fl_validation.verify_fx, I): uden fejl i popuppens
# felter lukker den; ellers bliver den staaende med beskederne. Select
# koerer foerst, naar Apply er faerdig - derfor her, ikke i Apply.
CLS_AFTER_VERIFY = f"""If(varFlClsCheck,
    Set(varFlClsCheck, false);
    If(
        IsEmpty(Filter(colFlIssues, RowGuid = varFlClsRow && Sev = "Error" && Ord >= 100 && Field in colFlClsDet.Field)),
        {CLOSE_CLS_FX.replace(chr(10), " ")},
        ClearCollect(colFlClsDet, {CLS_ITEMS})
    )
)"""
CLS_W = "Min(900, App.Width - 32)"


def build_class_modal():
    """[sloer, popup] - klassedata for raekken varFlClsRow (issue #184)."""
    backdrop = tap_backdrop("conFlClsBackdrop", CLS_OPEN, CLOSE_CLS_FX)
    title = text_ctrl("txtFlClsH", '"Class data"', size=lay.SIZE_CARD_TITLE, weight="Semibold",
                      height=26, wrap="false")
    sub = text_ctrl("txtFlClsSub",
                    f'With({{ r: {CR} }}, "Row " & r.Pos & " - " & '
                    f'If(IsBlank(r.FL), "no Functional Location", r.FL) & " - class " & r.AssignedClass & '
                    f'With({{ hp: LookUp(colFlClassHelp, Key = r.AssignedClass).Help }}, '
                    f'If(IsBlank(hp), "", " (" & hp & ")")))',
                    size=12, color=C_MUTED, height=18, wrap="false")
    left = grow(group("conFlClsHeadL", [title, sub], direction="Vertical", gap=2))
    close = button("btnFlClsClose", '"Close"', CLOSE_CLS_FX, width=36, height=36,
                   icon=icons.FLUENT["dismiss"], accessible='"Close without applying"',
                   tooltip='"Close without applying"')
    close.props["Layout"] = "ButtonLayout.IconOnly"
    head = group("conFlClsTop", pin_widths([left, close]), direction="Horizontal", gap=8,
                 align_items="Center")

    groups = []
    for tag, test, head_txt, label in (
            ("C", 'Section = "Class"', '"Class characteristics"', '"Characteristics of the class"'),
            ("T", 'Section = "TRM"', '"TRM"', '"TRM fields"'),
            ("X", 'Section = "Ext"', '"GIV_EXT / WCM"', '"GIV_EXT and WCM fields"')):
        grid = field_grid(tag, test, label, source="colFlClsDet", set_fx=_set_copy)
        groups.append(_group_title(f"txtFl{tag}GroupH", head_txt, grid.props["Visible"]))
        groups.append(grid)
    groups.append(text_ctrl("txtFlClsNone", '"This class has no class data fields."', size=13,
                            color=C_MUTED, height=20, wrap="false",
                            visible="IfError(CountRows(colFlClsDet) = 0, false)"))
    inner = group("conFlClsFields", groups, direction="Vertical", gap=8)
    # Popuppen er aldrig hoejere end skaermen: felterne scroller, titel og
    # knapper staar fast. Hoejre polstring = scrollbarens plads.
    body = group("conFlClsBody", [inner], direction="Vertical", gap=0,
                 height=f"Min({inner.h}, App.Height - 220)", overflow_y="Scroll",
                 pad=(0, SCROLLBAR_W, 0, 0))

    cancel = _fit(button("btnFlClsCancel", '"Cancel"', CLOSE_CLS_FX,
                         tooltip='"Discard the changes made since the dialog was opened"'))
    apply_ = _fit(button("btnFlClsApply", '"Apply"', APPLY_CLS_FX, primary=True,
                         visible=f"!({CLS_LOCKED})",
                         tooltip='"Validate and apply the changes to this row"'))
    foot = group("conFlClsFoot", [cancel, apply_], direction="Horizontal", gap=8, height=36,
                 justify="End", align_items="Center")
    modal = group("conFlClsModal", [head, body, foot], direction="Vertical", gap=12,
                  fill=C_MODAL_BG, border_color=C_PRIMARY_SOFT, radius=lay.RADIUS_MODAL,
                  pad=(18, 18, 18, 18), width=CLS_W, drop_shadow="ExtraBold", visible=CLS_OPEN)
    modal.props["X"] = "(App.Width - Self.Width) / 2"
    modal.props["Y"] = "Max(20, (App.Height - Self.Height) / 3)"
    return [backdrop, modal]


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
    title = text_ctrl("txtFlStructH", '"Structure"', size=lay.SIZE_CARD_TITLE, weight="Semibold",
                      height=26, wrap="false")
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
Clear(colFlDeleted);
Clear(colFlVals);
Clear(colFlIssues);
Clear(colFlTabs);
Set(varFlRequestGuid, "");
Set(varFlRequestNo, "");
Set(varFlStatus, "");
Set(varFlViewOnly, false);
Set(varFlCanEdit, false);
Set(varFlTab, "ALL");
Set(varFlDetailRow, "");
Set(varFlFoldOpen, true);
Set(varFlClsOpen, false);
Set(varFlClsCheck, false);
Set(varFlClsRow, "");
Clear(colFlClsDet);
Set(varFlStale, false);
Set(varFlNextRowNo, 1);
""" + add_row_fx() + """;
Set(varFlInfo, "");
// Den nye, tomme raekke er foldet ud (issue #166, #184).
Select(btnFlVerify)"""


def build_submit_confirm():
    """Bekraeftelsen foer Submit og ventespinneren (issue #54).
    [sloer, popup, spinner] - SIDST i skaermens boern."""
    return confirm_modal(
        "Fl", "varFlConfirmSubmit", "Submit request?",
        '"A JSON snapshot is frozen and the rows are locked."',
        "Submit", with_busy("varFlSaving", S.submit_fx()), "btnFlSubmitConfirm") + delete_modal(
        "Fl", "varFlRequestGuid", cfg.L_INDEX, cfg.DOMAIN) + [
        loading_overlay("imgFlSaving", "varFlSaving")]
