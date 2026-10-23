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
from gen_screen import (Ctrl, SHELL_W, C_CARD_BORDER, C_MUTED,
                        C_TRANSPARENT, C_MODAL_BG, C_PRIMARY_SOFT,
                        C_BORDER_OK, C_BORDER_ERROR, C_INVALID_FG, C_WARN_FG, C_VALID_FG,
                        C_CARD_BG, C_DIVIDER, C_INFO_BG, C_ROW_PRESSED)
import layout_tokens as lay
from layout_tokens import SCROLLBAR_W, GALLERY_RESERVE, at_least, below
import icons
import action_tips as tips
import display_text as dt
import mobile
from build_helpers import (C_INPUT_BORDER, label_px, ACT_NOTE_SIZE, act_running, ensure_hit, checkbox_theme, new_request_label, request_actions, breadcrumb, text_ctrl, group, button, text_input, themed_dropdown, card, date_picker,
                           pin_widths, top_bar, grow, fit_button_width, row_rule, mark_done,
                           act_fx, act_button, act_status, act_layers, panel_save_text,
                           confirm_modal, delete_button, delete_modal, ICON_SAVE, ICON_SUBMIT,
                           ICON_W, text_px, stable_scrim, icon_button, icon_heading, editor_footer,
                           mobile_pad, seg_style,
                           panel_save_fx, panel_save_mode, panel_save_status, panel_save_space,
                           panel_save_block, reset_click_fx, reset_confirm,
                           row_hit_under_actions)

# Under Desktop er headerens Edit, Save draft og Submit kun deres ikon
# (_bar_btn). FL har ingen bundbjaelke (issue #392), saa knapperne SKAL
# staa i headeren - og titlen skal stadig kunne staa ved siden af dem
# paa en tablet.
NARROW = below("Desktop")

# Indsendt = laast (FL69).
DM_EDIT = 'If(varFlViewOnly || varFlStatus = "Indsendt", DisplayMode.View, DisplayMode.Edit)'


def norm_fl(expr):
    """FL1: normalizeFlTyped + trim (app-functional-location.js:2368,
    fl-rule-engine.js:395)."""
    return (f"Upper(Trim(Substitute(Substitute(Substitute({expr}, Char(160), \" \"), "
            f"Char(13), \"\"), Char(10), \"\")))")


def add_row_fx(pos="0"):
    """FL63: en ny, tom raekke. Alle felter staar i raekken eller bag
    dens popup-knapper - der er intet at folde ud (issue #232). pos er
    raekkens nummer (#) - 0, til valideringen regner det."""
    return ("Collect(colFlRows, { RowGuid: Text(GUID()), RowNo: varFlNextRowNo, SpId: 0, "
            "FL: \"\", Description: \"\", KksType: \"\", AssignedClass: \"\", Status: \"draft\", "
            "FirstIssue: \"\", FirstWarning: \"\", IssueCount: 0, WarningCount: 0, "
            f"Pos: {pos}, FlBad: false, DescBad: false, Hint: \"\" }});\n"
            "Set(varFlNextRowNo, varFlNextRowNo + 1)")


# RAEKKELOFT (R2-043). Gem henter anmodningens raekker med eet Filter, og
# det materialiseres kun op til appens data row limit (500, maks 2000). Over
# loftet ville LookUp mod de hentede raekker ikke finde de sidste, og de
# ville blive oprettet igen. Derfor stopper Add row og Paste rows ved
# MAX_ROWS - under graensen, saa der er luft.
MAX_ROWS = 400
MAX_ROWS_MSG = f"Max {MAX_ROWS} rows per request - split it into more requests."


def capped_add_row_fx():
    """Add row - men ikke over MAX_ROWS (R2-043)."""
    return (f"If(\n    CountRows(colFlRows) >= {MAX_ROWS},\n"
            f'    Notify("{MAX_ROWS_MSG}", NotificationType.Error),\n'
            "    " + add_row_fx().replace("\n", "\n    ") + ";\n"
            "    " + REVERIFY.replace("\n", "\n    ") + "\n)")


# EN TOM RAEKKE (issue #467): en raekke uden Functional Location og
# Description - den samme definition som Paste rows' tomme raekker.
EMPTY_ROW = "IsBlank(FL) && IsBlank(Description)"

# NY RAEKKE AF SIG SELV (issue #467). Naar den SIDSTE raekke (hoejeste
# RowNo) er Ready ("valid", btnFlRowStatus), tilfoejes een tom raekke -
# men kun naar der ikke allerede er en tom raekke, og kun naar anmodningen
# kan aendres. En tidligere raekke, der bliver Ready, goer intet. Koerer i
# valideringen (fl_validation.verify_fx, afsnit G2) lige efter, at status
# er regnet; den nye raekke er tom, saa dens status ("draft") og nummer er
# allerede de rigtige - der skal ikke valideres igen. Add row er uaendret.
AUTO_ROW_FX = (
    "If(\n"
    '    !varFlViewOnly && varFlStatus <> "Indsendt" &&\n'
    f"    CountRows(colFlRows) < {MAX_ROWS} &&\n"
    '    Last(Sort(colFlRows, RowNo)).Status = "valid" &&\n'
    f"    IsEmpty(Filter(colFlRows, {EMPTY_ROW})),\n"
    "    " + add_row_fx("CountRows(colFlRows) + 1").replace("\n", "\n    ") + "\n"
    ")")


# FL62: validering er AUTOMATISK (issue #77) - der er ingen Verify-knap.
# Formlen staar KUN i den skjulte btnFlVerify (build_rows), og hver
# aendring - ny raekke, rettet felt, slettet raekke, indlaest anmodning -
# kalder den. Den er lokal Power Fx mod de navngivne formler (nf*), saa
# den koster ingen kald til SharePoint eller flows.
REVERIFY = "Set(varFlStale, true);\nSelect(btnFlVerify)"

# UGEMTE AENDRINGER (issue #533). varFlDirty er sand, naar der er rettet
# noget, som et gem vil skrive, siden anmodningen sidst blev gemt eller
# aabnet. Den saettes KUN af brugerens rettelser - og kun naar vaerdien
# faktisk aendres (et felt, der skriver samme vaerdi igen, fx naar en
# kontrol tegnes paa ny, goer intet). Gem (S.save_fx) nulstiller den,
# naar gemmet lykkedes; fejler gemmet, bliver den staaende - og vaerdierne
# med. En tom raekke (Add row, den automatiske nederst) gemmes ikke og
# taeller derfor ikke. Vises i headeren ("Unsaved changes") og i Rows'
# taeller (UNSAVED_NOTE).
DIRTY = "varFlDirty"
MARK_DIRTY = f"Set({DIRTY}, true)"
# Kun naar anmodningen kan aendres - en laast anmodning har intet at gemme.
UNSAVED = f'(Coalesce({DIRTY}, false) && !varFlViewOnly && varFlStatus <> "Indsendt")'


def delete_row_fx(guid):
    """Raekken guid fjernes lokalt; Save draft sletter den i SharePoint
    (colFlDeleted, fl_save trin 3). Den sidste raekke afloeses af en tom."""
    # Issue #533: ugemt, naar raekken havde indhold eller staar i SharePoint.
    return f"""With({{ dr: LookUp(colFlRows, RowGuid = {guid}) }},
    If(dr.SpId <> 0 || !(IsBlank(dr.FL) && IsBlank(dr.Description)), {MARK_DIRTY})
);
Collect(colFlDeleted, {{ RowGuid: {guid} }});
Remove(colFlRows, LookUp(colFlRows, RowGuid = {guid}));
RemoveIf(colFlVals, RowGuid = {guid});
RemoveIf(colFlIssues, RowGuid = {guid});
If(CountRows(colFlRows) = 0, {add_row_fx()});
{REVERIFY}"""


def copy_row_fx(guid):
    """COPY (issue #467): raekken guid kopieres til en ny, ugemt raekke -
    Description og alle raekkens felter (colFlVals: Room, Sort field,
    ATEX, Manufacturer, Warranty, klassedata ...). IKKE med: RowGuid,
    RowNo og SpId (genereres), status og beskeder (regnes af
    valideringen) og Functional Location - den skal vaere unik (FL5), saa
    kopien faar et tomt felt at skrive den nye i. KKS type og klasse
    regnes af den. Kopien staar i colFlCopies, til anmodningen er gemt
    (row_cells markerer den). Staar der en tom raekke, rykkes den ned
    under kopien, saa den tomme raekke bliver sidst."""
    return f"""If(
    CountRows(colFlRows) >= {MAX_ROWS},
    Notify("{MAX_ROWS_MSG}", NotificationType.Error),
    With(
        {{ src: LookUp(colFlRows, RowGuid = {guid}), ng: Text(GUID()),
           blank: First(Filter(colFlRows, {EMPTY_ROW})) }},
        ClearCollect(colFlCopyVals,
            ForAll(Filter(colFlVals, RowGuid = src.RowGuid) As V,
                {{ RowGuid: ng, Field: V.Field, Value: V.Value }}));
        Collect(colFlRows, {{ RowGuid: ng, RowNo: varFlNextRowNo, SpId: 0,
            FL: "", Description: src.Description, KksType: "", AssignedClass: "",
            Status: "draft", FirstIssue: "", FirstWarning: "", IssueCount: 0,
            WarningCount: 0, Pos: 0, FlBad: false, DescBad: false, Hint: "" }});
        Collect(colFlVals, colFlCopyVals);
        Clear(colFlCopyVals);
        Collect(colFlCopies, {{ RowGuid: ng }});
        {MARK_DIRTY};
        If(!IsBlank(blank.RowGuid),
            Patch(colFlRows, LookUp(colFlRows, RowGuid = blank.RowGuid), {{ RowNo: varFlNextRowNo + 1 }});
            Set(varFlNextRowNo, varFlNextRowNo + 2),
            Set(varFlNextRowNo, varFlNextRowNo + 1));
        Notify("Row " & src.Pos & " copied to a new row. Enter its Functional Location.",
            NotificationType.Information)
    );
    {REVERIFY.replace(chr(10), chr(10) + "    ")}
)"""


def set_row_fx(guid, field, value):
    return (f"With({{ nv: {value} }},\n"
            f"    If(Coalesce(LookUp(colFlRows, RowGuid = {guid}).{field}, \"\") <> Coalesce(nv, \"\"), "
            f"{MARK_DIRTY});\n"
            f"    Patch(colFlRows, LookUp(colFlRows, RowGuid = {guid}), {{ {field}: nv }})\n);\n"
            + REVERIFY)


def set_val_fx(guid, field, value):
    """FL56: vaerdien trimmes, og en tom vaerdi fjerner feltet
    (setSpoolColumnValue, app-functional-location.js:582-606). FL og
    Description er raekkens egne felter - og begge store bogstaver
    (Description: issue #490, som FL)."""
    # Issue #533: ugemt, kun naar vaerdien faktisk aendres (MARK_DIRTY).
    old = (f'Switch(f, "FUNCTIONAL LOCATION", LookUp(colFlRows, RowGuid = {guid}).FL, '
           f'"DESCRIPTION", LookUp(colFlRows, RowGuid = {guid}).Description, '
           f'LookUp(colFlVals, RowGuid = {guid} && Field = f).Value)')
    new = f'Switch(f, "FUNCTIONAL LOCATION", {norm_fl("nv")}, "DESCRIPTION", Upper(nv), nv)'
    return f"""With(
    {{ f: {field}, nv: Trim({value}) }},
    If(Coalesce({old}, "") <> Coalesce({new}, ""), {MARK_DIRTY});
    Switch(
        f,
        "FUNCTIONAL LOCATION",
        Patch(colFlRows, LookUp(colFlRows, RowGuid = {guid}), {{ FL: {norm_fl("nv")} }}),
        "DESCRIPTION",
        Patch(colFlRows, LookUp(colFlRows, RowGuid = {guid}), {{ Description: Upper(nv) }}),
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
    """Under Desktop er bjaelkens knapper kun deres ikon, saa alle tre kan
    staa ved siden af titlen - ingen af dem skjules (issue #392)."""
    w = btn.props["Width"]
    btn.props["Width"] = f"If({NARROW}, 40, {w})"
    btn.props["Layout"] = f"If({NARROW}, ButtonLayout.IconOnly, ButtonLayout.IconBefore)"
    return btn


# Knappernes ventetilstand (issue #420, build_helpers.act_fx): "save" eller
# "submit", mens der gemmes, og "<noegle>:ok"/":failed" bagefter.
ACT = "varFlAct"
SAVE_DRAFT_FX = act_fx(ACT, "save", S.save_fx(), ok="CountRows(colFlSaveErrors) = 0")
# Indsend: lykkedes, naar anmodningen staar som Indsendt bagefter.
SUBMIT_FX = act_fx(ACT, "submit", S.submit_fx(), ok='varFlStatus = "Indsendt"')

# Save draft - og panelets Save, som er det samme gem (issue #308).
SAVE_DM = (f'If(varFlViewOnly || varFlStatus = "Indsendt" || CountRows({S.LIVE}) = 0, '
           f'DisplayMode.Disabled, DisplayMode.Edit)')

def build_bar():
    """Save draft, Submit og New request staar dér, hvor Verify og Export
    JSON stod (issue #77). Valideringen koerer af sig selv (REVERIFY), og
    eksporten er vaek - snapshottet fryses stadig ved Submit (payload_fx).
    Tallene er renderMetrics (FL66)."""
    save = _fit(button("btnFlSaveDraft", '"Save draft"', SAVE_DRAFT_FX,
                       icon=ICON_SAVE, display_mode=SAVE_DM), icon=True)
    # Issue #533: Save draft gemmer HELE anmodningen (S.save_fx) - det samme
    # gem som sidepanelets Save. Tooltippet siger, om der er noget ugemt.
    save.props["Tooltip"] = (f'If({UNSAVED}, "Unsaved changes. ", "") & '
                             '"Saves the complete request and puts it on the landing page as Draft - '
                             'it can still be edited."')
    # Submit spoerger foerst (build_submit_confirm, issue #54) - eller siger,
    # hvorfor den er blokeret (S.submit_click_fx, issue #277).
    submit = _fit(button("btnFlSubmit", '"Submit"', S.submit_click_fx(),
                         primary=True, icon=ICON_SUBMIT, display_mode=S.SUBMIT_DM),
                  icon=bool(ICON_SUBMIT))
    submit.props["Tooltip"] = S.SUBMIT_WHY
    # "New Request" uden plus-ikon (issue #243) - build_helpers.new_request_label.
    new = new_request_label(button("btnFlNew", '"New request"', NEW_FX))
    edit = _fit(button("btnFlEdit", '"Edit"', "Set(varFlViewOnly, false)", icon="Edit",
                       visible="varFlViewOnly && varFlCanEdit",
                       display_mode="If(varFlCanEdit, DisplayMode.Edit, DisplayMode.Disabled)"),
                icon=True)
    # Under Desktop er knappen kun sit ikon (_bar_btn) - tooltip som de
    # andre domaeners Edit (issue #515).
    edit.props["Tooltip"] = '"Edit this request"'
    edit.props["AccessibleLabel"] = '"Edit this request"'
    # SAMME RAEKKEFOELGE SOM ALLE DOMAENER (UX-review T1):
    # [New request] | [Edit] [Save draft] [Submit (N to fix)] [Delete].
    # Taelleren er raekkerne med fejl (renderMetrics, S.ERRS).
    # "Saved"/"Save failed" lige foran Save draft (issue #420). Mens der
    # gemmes, siger knappen det selv (#441) - kun under Desktop, hvor
    # knapperne er deres ikon alene (_bar_btn), staar hjulet ved dem.
    status = act_status("FlAct", ACT, ("save", "submit"),
                        spin={"save": NARROW, "submit": NARROW if ICON_SUBMIT else None})
    # "Unsaved changes" foran Save draft (issue #533) - fra Desktop, hvor
    # der er plads; under Desktop staar det i Rows' taeller (build_rows).
    # Ikke mens et gem koerer (knappen siger det selv).
    unsaved_txt = "Unsaved changes"
    unsaved_w = label_px(unsaved_txt, ACT_NOTE_SIZE) + 4
    unsaved = text_ctrl("txtFlUnsaved", f'"{unsaved_txt}"', size=ACT_NOTE_SIZE, weight="Semibold",
                        color=C_WARN_FG, height=20, width=unsaved_w, wrap="false",
                        visible=(f"{at_least('Desktop')} && {UNSAVED} && "
                                 f"!({act_running(ACT)})"))
    unsaved.props["LayoutMinWidth"] = str(unsaved_w)
    unsaved.props["AlignInContainer"] = "AlignInContainer.Center"
    status = [unsaved, *status]
    actions = request_actions("Fl", new, save, submit, fix_expr=S.ERRS, extra=[edit, *status])
    # Ingen bundbjaelke paa FL (issue #392): Save draft og Submit staar i
    # headeren paa alle skaermbredder.
    # Synlig kant rundt om alle sekundaere knapper (feedback).
    for b in (new, edit, save):
        b.props["Appearance"] = "ButtonAppearance.Outline"
        b.props["BorderColor"] = C_INPUT_BORDER
        b.props["BorderThickness"] = "1"
    _bar_btn(edit)
    _bar_btn(save)
    # Submit ogsaa kun sit ikon paa en telefon, saa "New request" kan staa
    # med hele sin tekst (issue #243).
    if ICON_SUBMIT:
        _bar_btn(submit)
    # "Saving..." / "Submitting..." paa knapperne, mens der gemmes (#420).
    act_button(save, ACT, "save")
    act_button(submit, ACT, "submit")
    delete = delete_button("Fl", "varFlViewOnly", "varFlRequestGuid")
    # TELEFONEN (issue #508): knapperne bliver i headeren (issue #392), men
    # de er 44 px hoeje, og ikonknapperne (Edit, Save draft, Submit, Delete)
    # er 44 x 44 - en tommelfinger rammer dem. New Request beholder sin tekst
    # (issue #243). Tablet og desktop er uaendrede.
    for b in (edit, save, delete) + ((submit,) if ICON_SUBMIT else ()):
        b.props["Width"] = lay.mobile_or(mobile.TOUCH, b.props["Width"])
        b.props["LayoutMinWidth"] = b.props["Width"]
    for b in (new, edit, save, submit, delete):
        mobile.touch(b)
    # Temaskiftet og vejen til hubben staar i sidebaren (tools/side_nav.py).
    bar = top_bar("Fl", f'"{cfg.TITLE}"', SUBTITLE,
                  actions + [delete],
                  icon=cfg.APP_KEY, mode_var="varFlViewOnly",
                  crumb=breadcrumb("Fl", cfg.APP_KEY, "varFlRequestNo"))
    return bar


# ---------------------------------------------------------------------------
# Tabellerne - raekkerne og Classes
# ---------------------------------------------------------------------------
GAP = 8
# Budgettet for en gallerirakkes celler: kortets padding, scrollbar og
# GALLERY_RESERVE (se docs/30, regel J). Galleriet har TemplatePadding 0.
ROWS_W = f"({SHELL_W} - 36 - {SCROLLBAR_W} - {GALLERY_RESERVE})"
ROW_H = 44
GAL_MAX = 12
# Info's mindste bredde, og Functional Location + Description tilsammen.
VAL_MIN = 64
PAIR_MAX = 300
PAIR_MIN = 144


def table_head(name, spec, gap=GAP, width="Parent.Width"):
    """Kolonneoverskrifterne og stregen under dem (Masterdata Hub's
    moenster, issue #70)."""
    # En kolonne uden overskrift (Classes' Gap, issue #490) er en tom
    # container - ingen tom tekst, som en skaermlaeser ville standse ved.
    head = group(name,
                 pin_widths([text_ctrl(f"txt{name[3:]}{n}", f'"{lbl}"', size=11, color=C_MUTED,
                                       weight="Semibold", height=18, width=w, wrap="false",
                                       visible=vis) if lbl else
                             group(f"con{name[3:]}{n}", [], direction="Horizontal", height=18,
                                   width=w, visible=vis)
                             for n, lbl, w, vis in spec]),
                 direction="Horizontal", gap=gap, height=18, align_items="Center", width=width)
    return head


def divider(name, visible=None, width="Parent.Width"):
    return group(name, [], direction="Horizontal", height=1, fill=C_DIVIDER, visible=visible,
                 width=width)


def table_gallery(name, label, items, count, cells, row_name, visible=None, row_fill=None,
                  row_h=ROW_H, gap=GAP, width="Parent.Width", tpl_h=None, extra=()):
    """Et galleri med een raekke pr. element og en streg mellem raekkerne.

    INGEN RAEKKE-SCROLLBAR. Foer var hoejden n x (ROW_H + 2), men med
    TemplatePadding 2 fylder n raekker n x (ROW_H + 2) + 2 - saa selv een
    raekke fik sin egen scrollbar. Nu er TemplatePadding 0, og hoejden er
    praecis n x ROW_H. Galleriet scroller KUN, naar der er flere end
    GAL_MAX raekker - saa er det sektionens scrollbar, og overskriften
    staar fast over den.

    row_h kan vaere et udtryk (raekkerne, issue #232): saa staar stregen
    ved Parent.TemplateHeight, og raekkens celler har hoejden tpl_h.
    extra er flere figurer i raekken (beskedlinjen under cellerne)."""
    tpl = group(row_name, pin_widths(cells), direction="Horizontal", gap=gap,
                height=tpl_h or "Parent.TemplateHeight - 1", align_items="Center", justify="Start",
                width="Parent.TemplateWidth", fill=row_fill)
    # Stregen er sin egen figur nederst i raekken (build_helpers.row_rule) -
    # ikke galleriets fyld, der ogsaa ville ses under den sidste raekke.
    fixed = isinstance(row_h, int)
    rule = row_rule(f"rct{row_name[3:]}Rule", row_h if fixed else ROW_H)
    if not fixed:
        rule.props["Y"] = "Parent.TemplateHeight - 1"
    gal_h = f"Min({count}, {GAL_MAX}) * {row_h if fixed else '(' + row_h + ')'}"
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
        "TemplateSize": str(row_h),
        "Width": width,
        "WrapCount": "1",
    }
    if visible is not None:
        props["Visible"] = visible
    return Ctrl(name, "Gallery", variant="Vertical", props=props,
                children=[tpl, *extra, rule], h=gal_h, vis=visible)


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


# --- Raekkerne (issue #232) --------------------------------------------------
# Ingen fold-ud: hvert felt staar i raekken eller bag en popup-knap. Efter
# Assigned Class kommer Class Data (issue #242), efter Sort Field:
#   ABC Indicator | ATEX | Manufacturer | Warranty | Actions
# Etiket og maks.-laengde for Room og Sort Field er reglernes
# (fl_rules.generated.json, ens for alle klasser - tests/test_fl_sections).
_NO_CLASS = {c["Field"]: c for c in V.R["columns"] if c["Cls"] == "NO CLASS"}
ROW_VALS = [("Room", "ROOM", 56), ("Sort", "SORT FIELD", 72)]
# Popup-knapperne har tekst i 13 px - saa brede som deres tekst.
BTN_SIZE = 13


def _btn_w(text):
    # Smalt (feedback): text_px er allerede et skoen med 10 %, saa kun 20 px luft.
    return text_px(text, BTN_SIZE) + 20


def _pop_w(text):
    """Popup-knappen med plads til fluebenet foran teksten (UX-review)."""
    return _btn_w(text) + 16


# MANUFACTURER OG WARRANTY MED FLUEBEN PAA EEN LINJE (issue #362)
#
# _pop_w gav kun 16 px til fluebenet, men den moderne knap (Fluent 2,
# medium) bruger: 12 px padding i hver side, 1 px kant i hver side, et
# 20 px ikon og 6 px mellem ikon og tekst. Saa blev "Warranty" klippet,
# naar der var data. Bredden regnes nu af de dele - og de to knapper faar
# SAMME bredde (den bredeste tekst), saa de ser ens ud. Fluents knap er
# mindst 96 px bred.
BTN_PAD_X = 12
BTN_BORDER = 1
BTN_ICON = 20
BTN_ICON_GAP = 6
BTN_MIN_W = 96


def _pop_icon_w(*texts):
    """Mindste bredde, hvor fluebenet og den HELE tekst staar paa een linje
    (text_px er allerede et skoen med 10 % luft)."""
    chrome = 2 * (BTN_PAD_X + BTN_BORDER) + BTN_ICON + BTN_ICON_GAP
    return max(BTN_MIN_W, *(text_px(t, BTN_SIZE) + chrome for t in texts))


MFR_WAR_W = _pop_icon_w("Manufacturer", "Warranty")

VGAP = 6
FL_MIN = 140
# Tabellens mindste bredde foer issue #362 (V_BASE). De bredere Manufacturer-
# og Warranty-knapper maa ikke goere raekken bredere: pladsen tages fra
# Description's minimum (den kolonne med mest luft over sin overskrift),
# og Sort Field er 72 px i stedet for 88 (ROW_VALS; overskriften er 56 px).
V_BASE_MAX = 1258 + 12 + 54 + 6 * 6
# Actions: Copy og Delete, hver en ikonknap paa ACT_BTN (issue #467). De
# 54 px og StrIndicators 12 ekstra (overskriften er bredere end "KKS type")
# laegges til V_BASE_MAX, saa Description beholder sit minimum. Issue #532:
# + 6 x COL_AIR (de seks kompakte faelles kolonner).
ACT_BTN = 48
ACT_W = 2 * ACT_BTN + VGAP
# LIDT MERE LUFT MELLEM DE KOMPAKTE FAELLES KOLONNER (issue #532).
# StrIndicator, Class, Room, Sort field, ABC indicator og ATEX faar hver
# COL_AIR px mere (V_SHARED herunder). Cellerne staar til venstre i deres
# kolonne, saa luften staar til hoejre for vaerdien: det synlige mellemrum
# mellem dem gaar fra VGAP (6) til 12 px. Room og Sort fields felter bliver
# ogsaa 6 px bredere. De 6 x 6 = 36 px tages fra FL og Description: ved
# 1920 (1080p) har de kun ca. 47 px over deres lofter (FL_MAX, DESC_MAX),
# saa de beholder begge deres loft (tests/test_fl_columns_532.py).
# Tabellens mindstebredde (V_BASE) vokser tilsvarende - FL og Description
# kan ikke give mere under deres minimum uden at klippe overskrifterne.
COL_AIR = 6
# (navn, overskrift, bredde) efter Description.
#
# EET TABELMOENSTER FOR ROWS OG CLASSES (issue #468). Foerst de FAELLES
# kolonner - de samme felter i begge tabeller, i samme raekkefoelge og med
# samme bredder, saa de staar lige under hinanden:
#   # | Functional Location | Description | StrIndicator | Class | Room |
#   Sort field | ABC indicator | ATEX
# og saa hver tabels egne: Rows har Class data, Manufacturer, Warranty,
# Status og Actions; Classes har Edit (C_SPEC). Class data stod foer lige
# efter Class (issue #242) - nu efter de faelles kolonner.
# StrIndicator og Class: samme navne som i Classes og sidepanelet (issue
# #467 - foer "KKS type" og "Assigned class"). Kun etiketterne er nye.
# Class er saa bred som det laengste klassenavn ("NO CLASS", 13 px semibold)
# og ikke bredere (issue #479 - foer 96 px).
CLS_W = max(text_px("Class", 11), *(text_px(c, 13) for c in V.R["classes"])) + 4
V_SHARED = [(n, lbl, w + COL_AIR) for n, lbl, w in
            ([("Kks", "StrIndicator", 76), ("Cls", "Class", CLS_W)]
             # Reglernes etiket ("Sort Field") i appens sentence case (F1).
             + [(n, _NO_CLASS[f]["Column"][:1] + _NO_CLASS[f]["Column"][1:].lower(), w)
                for n, f, w in ROW_VALS]
             + [("Abc", "ABC indicator", 88), ("Atex", "ATEX", 40)])]
assert COL_AIR * len(V_SHARED) == 6 * 6
V_FIXED = (V_SHARED
           + [("ClsData", "Class data", _pop_w("Class data")),
              ("Mfr", "Manufacturer", MFR_WAR_W),
              ("War", "Warranty", MFR_WAR_W),
              ("Status", "Status", 80),
              # Copy og Delete: to ikonknapper (issue #467).
              ("Act", "Actions", ACT_W)])
# Description er mindst sin overskrift plus feltets padding (issue #479 -
# foer fik den resten af V_BASE_MAX, saa en smallere kolonne ikke gav FL og
# Description mere plads).
DESC_MIN = text_px("Description", 11) + 24
V_SHOW_NO = at_least("Tablet")
# Raekkens mindste bredde: # (fra Tablet), FL, Description, resten og
# mellemrummene. Er kortet smallere, scroller TABELLEN vandret i kortet
# (som Equipment/Materials' raekker) - intet skjules, klippes eller
# laegges oven i hinanden.
V_BASE = FL_MIN + DESC_MIN + sum(w for _n, _l, w in V_FIXED) + VGAP * (len(V_FIXED) + 1)
assert V_BASE <= V_BASE_MAX, V_BASE
V_MIN = f"(If({V_SHOW_NO}, {28 + VGAP}, 0) + {V_BASE})"
V_SPARE = f"Max(0, ({ROWS_W}) - {V_MIN})"
# KUN FUNCTIONAL LOCATION OG DESCRIPTION VOKSER - OG KUN TIL ET LOFT
# (issue #468). De andre kolonner har fast, kompakt bredde; resten af kortet
# staar tomt til hoejre for tabellen - Actions/Edit staar lige efter den
# sidste kolonne. (Issue #490: over lofterne fylder tabellen nu kortet -
# se V_REST herunder.)
#
# LOFTET ER INDHOLDET, OG FL FAAR PLADSEN FOERST (issue #479). Foer var
# lofterne 240 og 300 px, og FL og Description delte pladsen 2/5 og 3/5 -
# saa FL naaede foerst sit loft ved ca. 1820 px, og en 40 tegns Description
# blev klippet selv ved 1920. Nu:
#   - FL_MAX er den laengste FL (FL_SAMPLE) i feltets skrift plus feltets
#     kant og padding, DESC_MAX en Description paa 40 tegn (DESC_SAMPLE).
#   - FL faar den ekstra plads foerst, til den er FL_MAX; saa Description.
#     Er vinduet smallere, klippes Description altsaa foer FL.
# Ved 1920 (1080p) har begge deres loft, og tabellen er smallere end kortet
# - ingen vandret scroll. Tallene regnes af fontens maal (text_px, et skoen
# der rammer lidt for bredt), ikke af een skaermbredde.
FL_SAMPLE = "SSV13 HFC10AP001 -M01"
DESC_SAMPLE = "Smoereoliepumpe Kulmoelle 10, Pumpemotor"
assert len(DESC_SAMPLE) == 40
# Fluents tekstfelt (medium): 1 px kant, 10 px padding og 2 px om selve
# feltet i hver side - og 4 px luft, saa teksten aldrig staar paa pixlen.
INPUT_CHROME = 2 * (1 + 10 + 2) + 4
FL_MAX = text_px(FL_SAMPLE, lay.SIZE_INPUT, semibold=False) + INPUT_CHROME
DESC_MAX = text_px(DESC_SAMPLE, lay.SIZE_INPUT, semibold=False) + INPUT_CHROME
#
# RESTEN AF KORTET GAAR OGSAA TIL FL OG DESCRIPTION (issue #490). Foer
# stoppede tabellen ved lofterne, og paa store skaerme stod resten af kortet
# tomt til hoejre. Nu fylder tabellen kortet: det, der er tilbage, naar
# begge har deres loft (V_REST), deles mellem FL (FL_SHARE) og Description
# (resten - den kolonne med mest tekst). De kompakte kolonner har stadig
# deres faste bredde. Ved 1920 er resten kun ca. 50 px, saa 1080p-layoutet
# er det samme; under lofterne er reglerne uaendrede, og tabellen scroller
# kun vandret, naar kortet er smallere end V_MIN.
FL_SHARE = 0.4
V_REST = f"Max(0, ({V_SPARE}) - {FL_MAX - FL_MIN + DESC_MAX - DESC_MIN})"
V_FL_EXTRA = f"RoundDown(({V_REST}) * {FL_SHARE}, 0)"
V_FL_W = f"{FL_MIN} + Min({FL_MAX - FL_MIN}, {V_SPARE}) + {V_FL_EXTRA}"
V_DESC_W = (f"{DESC_MIN} + Min({DESC_MAX - DESC_MIN}, "
            f"Max(0, ({V_SPARE}) - {FL_MAX - FL_MIN})) + ({V_REST}) - {V_FL_EXTRA}")


V_SPEC = ([("No", "#", 28, V_SHOW_NO),
           ("Fl", "Functional Location", V_FL_W, None),
           ("Desc", "Description", V_DESC_W, None)]
          + [(n, l, w, None) for n, l, w in V_FIXED])


def spec_width(spec, gap=VGAP):
    """Tabellens bredde: kolonnerne og mellemrummene mellem dem."""
    parts = [f"If({vis}, ({w}) + {gap}, 0)" if vis is not None else f"({w}) + {gap}"
             for _n, _l, w, vis in spec]
    return f"({' + '.join(parts)} - {gap})"


V_W = spec_width(V_SPEC)
V_GAL_W = f"({V_W}) + {SCROLLBAR_W} + {GALLERY_RESERVE}"
V_WIDE = f"({ROWS_W}) < ({V_W})"

ROW_TOP = 40
# Delete er en ikonknap med klikfladen H.hit (UX-review F6, regel 40):
# under Desktop er cellelinjen 44 hoej, og resten af raekken rykker
# TOUCH_EXTRA (0 fra Desktop, 4 under) ned.
ROW_TOP_F = f"Max({ROW_TOP}, {lay.HIT})"
TOUCH_EXTRA = f"({ROW_TOP_F} - {ROW_TOP})"
V_ROW_H = f"{ROW_H} + {TOUCH_EXTRA}"

ERRS = 'CountRows(Filter(colFlRows, Status = "invalid"))'

# --- Telefonen: raekkerne som kort (issue #508) ------------------------------
# Under Tablet er tabellen (V_MIN, ca. 1300 px) et kort pr. raekke - ingen
# vandret scroll og ingen kolonneoverskrifter. Cellerne er de SAMME kontroller
# (samme navne, bindinger og regler); kun placeringen er en anden
# (mobile.gallery_place). Galleriets raekker har een hoejde, saa kortet har
# to tilstande for alle raekker: kompakt (standard) og "Row details"
# (ROWS_MORE, chevronen over listen):
#   A  #3 . CLASS . Str. X . ABC Y          [Status] [Delete]
#   B  Functional Location
#   C  Description
#   -- Row details --
#   D  Room | Sort field | [ ] ATEX
#   E  [Class data]  [Manufacturer]
#   F  [Warranty]    [Copy]
# Status (fejl og advarsler) og Delete staar altid paa kortet. Alle felter
# er ogsaa i sidepanelet (Class data/Manufacturer/Warranty -> Show all).
M_CARD_W = f"({SHELL_W} - {2 * lay.MOBILE_CARD_PAD})"
M_TW = M_CARD_W
M_LINE = mobile.TOUCH
M_GAP = 8
M_PAD_T = 8
M_PAD_B = 12


def _m_y(i):
    """Y for kortets linje i (0 = A)."""
    return M_PAD_T + i * (M_LINE + M_GAP)


M_ROW_H_COMPACT = _m_y(3) - M_GAP + M_PAD_B
M_ROW_H_MORE = _m_y(6) - M_GAP + M_PAD_B
ROWS_MORE = "varFlRowsMoreOpen"
ROWS_MORE_ON = mobile.state(ROWS_MORE)
M_ROW_H = f"If({ROWS_MORE_ON}, {M_ROW_H_MORE}, {M_ROW_H_COMPACT})"
# Saa mange kort staar uden egen scroll; flere (sjaeldent - loftet er
# MAX_ROWS) scroller i listen, som tabellen goer efter GAL_MAX raekker.
M_ROWS_MAX = 50
M_HALF = f"(({M_TW}) - {M_GAP}) / 2"
M_STATUS_W = 80
M_ATEX_W = 72
# Popup-knappernes flueben kraever MFR_WAR_W (ca. 143 px). Er en halv linje
# smallere (under ca. 360 px skaermbredde), viser kun den groenne kant og
# tekst (mark_done) og skaermlaeserens "filled in", at der er data.

# Felterne bag popup-knapperne (Master, ens for alle klasser).
MFR_FIELDS = ["MANUFACTURER", "MODEL NUMBER", "MANUFACTURER PART NUMBER",
              "MANUFACTURER SERIAL NUMBER"]
WAR_FIELDS = ["WARRANTY START", "WARRANTY END"]


def _fields(fields):
    return "[" + ", ".join(f'"{f}"' for f in fields) + "]"


def has_vals(guid, fields_expr):
    """DATA I POPUPPEN: mindst een gemt vaerdi i felterne. set_val_fx
    trimmer og fjerner tomme vaerdier, saa en raekke i colFlVals ER en
    vaerdi. Regnes af samlingen - ingen variabel, der kan glemme at blive
    nulstillet (build_helpers.mark_done)."""
    return f"!IsEmpty(Filter(colFlVals, RowGuid = {guid} && Field in {fields_expr}))"


def n_vals(guid, fields_expr):
    """Antallet af udfyldte felter i popuppen - samme samling som has_vals
    (colFlVals, i hukommelsen), intet opslag pr. raekke. Tooltippet paa
    raekkens Class data, Manufacturer og Warranty (issue #515)."""
    return f"CountRows(Filter(colFlVals, RowGuid = {guid} && Field in {fields_expr}))"


def verify_button():
    """HELE valideringen - skjult. Alle aendringer kalder den med
    Select(btnFlVerify) (REVERIFY, docs/31 PX7). Select virker paa en
    skjult knap; den skal bare staa paa samme skaerm."""
    b = button("btnFlVerify", '"Verify"',
               V.verify_fx(PANEL_REFRESH, after=S.submit_after_verify(), grow=AUTO_ROW_FX),
               width=100, visible="false", accessible='"Validate the rows"')
    return b


def _issue_on(guid, field):
    """Er der en fejl paa feltet? Samme udvalg som V.field_issue for
    spool-felterne (Ord >= 100)."""
    return (f'!IsBlank(LookUp(colFlIssues, RowGuid = {guid} && Sev = "Error" && '
            f'Field = "{field}" && Ord >= 100).Short)')


def _val(field):
    return f'LookUp(colFlVals, RowGuid = ThisItem.RowGuid && Field = "{field}").Value'


def _pop_button(name, text, onselect, has, accessible, tooltip, display_mode):
    """En popup-knap i raekken med Long Text-knappens udfyldt-tilstand
    (build_helpers.mark_done, VH-plan): groen kant og tekst, naar popuppen
    har data - neutral, naar den er tom. Groen er data, ikke gyldighed."""
    b = button(name, f'"{text}"', onselect, width=_pop_w(text), height=30,
               display_mode=display_mode, accessible=accessible, tooltip=tooltip)
    b.props["Size"] = str(BTN_SIZE)
    # UDFYLDT KAN SES (UX-review, FL Spool): et flueben foran teksten, naar
    # popuppen har data - ikke kun den groenne kant.
    b.props["Icon"] = f'If({has}, "Checkmark", "")'
    b.props["Layout"] = f"If({has}, ButtonLayout.IconBefore, ButtonLayout.TextOnly)"
    b.props["AccessibleLabel"] = f'{accessible} & If({has}, ", filled in", ", empty")'
    return mark_done(b, has)


# En kopi, der ikke er gemt endnu (Copy, issue #467): colFlCopies toemmes,
# naar anmodningen er gemt, hentet eller ny.
COPIED = "ThisItem.RowGuid in colFlCopies.RowGuid"


def row_cells():
    """Cellerne i een raekke (issue #232)."""
    row = "ThisItem"
    # Pos, FlBad, DescBad og Hint regnes i valideringen (B6).
    no = text_ctrl("txtFlRowNo", "Text(ThisItem.Pos)",
                   size=13, color=C_MUTED, height=20, wrap="false")
    fl = text_input("inpFlRowFl", "ThisItem.FL", max_length=40, width="160",
                    display_mode=DM_EDIT, label='"Functional Location"',
                    onchange=set_row_fx("ThisItem.RowGuid", "FL", norm_fl("Self.Text")))
    fl.props["BorderColor"] = _field_border(f"{row}.FlBad", f'{row}.Status <> "draft"')
    # En kopi (Copy, issue #467) beder om sin nye Functional Location.
    fl.props["Placeholder"] = f'If({COPIED}, "New copy - enter FL", "")'
    desc = text_input("inpFlRowDesc", "ThisItem.Description", max_length=40, width="140",
                      display_mode=DM_EDIT, label='"Description"',
                      onchange=set_row_fx("ThisItem.RowGuid", "Description", "Upper(Trim(Self.Text))"))
    desc.props["BorderColor"] = _field_border(
        f"{row}.DescBad", f'{row}.Status <> "draft" && !IsBlank({row}.Description)')
    kks = text_ctrl("txtFlRowKks", 'If(IsBlank(ThisItem.KksType), "-", ThisItem.KksType)',
                    size=13, height=20, wrap="false")
    cls = text_ctrl("txtFlRowCls",
                    'If(IsBlank(ThisItem.AssignedClass), "-", ThisItem.AssignedClass)',
                    size=13, weight="Semibold", height=20, wrap="false")

    # Room og Sort Field: spool-felter med reglerne (colFlVals, set_val_fx,
    # FL56) - roed kant ved en fejl, groen naar raekken er valideret og
    # feltet er udfyldt (som Description).
    vals = []
    for n, f, w in ROW_VALS:
        col = _NO_CLASS[f]
        inp = text_input(f"inpFlRow{n}", _val(f),
                         max_length=col["MaxLen"], width=str(w), display_mode=DM_EDIT,
                         label=f'"{col["Column"]}"',
                         onchange=set_val_fx("ThisItem.RowGuid", f'"{f}"', "Self.Text"))
        inp.props["BorderColor"] = _field_border(
            _issue_on("ThisItem.RowGuid", f), f'{row}.Status <> "draft" && !IsBlank({_val(f)})')
        vals.append(inp)

    # ABC Indicator: kun til visning - TRM-automatikken saetter den (FL49).
    abc = text_ctrl("txtFlRowAbc", f'With({{ v: {_val("ABC INDIC.")} }}, If(IsBlank(v), "-", v))',
                    size=13, weight="Semibold", height=20, wrap="false",
                    accessible='"ABC indicator, set automatically: " & Self.Text')
    # ATEX: afkrydsning, der gemmer X eller intet (som i formularen, #166).
    atex = Ctrl("chkFlRowAtex", "ModernCheckbox", props=checkbox_theme({
        "AccessibleLabel": '"ATEX, row " & ThisItem.Pos',
        "Default": f'Upper(Trim({_val("ATEX")})) = "X"',
        "DisplayMode": DM_EDIT,
        "Height": "36",
        "Label": '""',
        "OnCheck": set_val_fx("ThisItem.RowGuid", '"ATEX"', '"X"'),
        "OnUncheck": set_val_fx("ThisItem.RowGuid", '"ATEX"', '""'),
        "Width": "40",
    }), h=36)

    has_cls = "!IsBlank(ThisItem.AssignedClass)"
    cls_fields = f"Filter(colFlColumns, Cls = ThisItem.AssignedClass && {CLS_TEST}).Field"
    # Tooltippet (issue #515): handlingen og antallet af udfyldte felter -
    # "Edit class data - 3 fields filled" / "Add class data".
    cls_data = _pop_button(
        "btnFlRowClassData", "Class data", open_row_panel_fx("ThisItem.RowGuid", f'"{PANEL_CLS_JUMP}"'),
        f"{has_cls} && " + has_vals("ThisItem.RowGuid", cls_fields),
        '"Class data of row " & ThisItem.Pos',
        (f'If({has_cls}, {tips.filled("class data", n_vals("ThisItem.RowGuid", cls_fields), CLS_LOCKED)}, '
         '"Valid FL first - the class is determined by the KKS code of a valid Functional Location.")'),
        f"If({has_cls}, DisplayMode.Edit, DisplayMode.Disabled)")
    pops = [cls_data]
    for name, kind, fields in (("btnFlRowMfr", "Manufacturer", MFR_FIELDS),
                               ("btnFlRowWar", "Warranty", WAR_FIELDS)):
        has = has_vals("ThisItem.RowGuid", _fields(fields))
        tip = tips.filled(kind.lower(), n_vals("ThisItem.RowGuid", _fields(fields)), CLS_LOCKED)
        # Som Long Text: laast og tom = deaktiveret; ellers kan den aabnes
        # (i View kun til at laese).
        pops.append(_pop_button(
            name, kind, open_row_panel_fx("ThisItem.RowGuid", f'"{PANEL_JUMP[kind]}"'), has,
            f'"{kind} of row " & ThisItem.Pos', tip,
            f"If(({CLS_LOCKED}) && !({has}), DisplayMode.Disabled, DisplayMode.Edit)"))

    status = button(
        "btnFlRowStatus",
        'Switch(ThisItem.Status, "valid", "Ready", "warning", "Warning", '
        '"invalid", "Error", "Draft")',
        'Notify(Coalesce(ThisItem.FirstIssue, ThisItem.FirstWarning, "Row status: " & Self.Text), '
        'NotificationType.Information)',
        width=80, height=30, accessible='"Row status: " & Self.Text',
        tooltip=('Switch(ThisItem.Status, "draft", "Draft", "valid", "Ready for SAP", '
                 '"warning", "Warning" & If(IsBlank(ThisItem.FirstWarning), "", " - " & ThisItem.FirstWarning), '
                 'If(IsBlank(ThisItem.FirstIssue), "Error", "Error - " & ThisItem.FirstIssue)) '
                 '& If(IsBlank(ThisItem.Hint), "", ". " & ThisItem.Hint)'))
    status.props["Color"] = _status_color("ThisItem")
    status.props["Size"] = str(lay.SIZE_SMALL)

    delete = button("btnFlRowDelete", '"Delete"', delete_row_fx("ThisItem.RowGuid"), danger=True, width=48, height=30, display_mode=DM_EDIT, icon="Delete",
                    accessible=tips.label(tips.DELETE_ROW, "ThisItem.Pos"), tooltip=tips.DELETE_ROW)
    delete.props["Layout"] = "ButtonLayout.IconOnly"
    ensure_hit(delete, square=False)
    # Copy (issue #467): raekken til en ny, ugemt raekke - foran Delete.
    copy = button("btnFlRowCopy", '"Copy"', copy_row_fx("ThisItem.RowGuid"),
                  width=ACT_BTN, height=30, icon="Copy",
                  # En tom raekke kopieres ikke - der maa kun vaere een.
                  display_mode=("If(varFlViewOnly || varFlStatus = \"Indsendt\", DisplayMode.View, "
                                "IsBlank(ThisItem.FL) && IsBlank(ThisItem.Description), "
                                "DisplayMode.Disabled, DisplayMode.Edit)"),
                  accessible=tips.label(tips.COPY_ROW, "ThisItem.Pos"), tooltip=tips.COPY_ROW)
    copy.props["Layout"] = "ButtonLayout.IconOnly"
    ensure_hit(copy, square=False)
    delete.props["Width"] = str(ACT_BTN)
    actions = group("conFlRowAct", [copy, delete], direction="Horizontal", gap=VGAP,
                    height=lay.HIT, align_items="Center")
    _mobile_card(fl, desc, [kks, cls, abc], vals, atex, pops, status, copy, delete)
    # Samme raekkefoelge som V_FIXED: de faelles kolonner, saa Class data
    # (issue #468).
    return _cells(V_SPEC, [no, fl, desc, kks, cls] + vals + [abc, atex]
                  + pops + [status, actions])


def _more(ctrl):
    """Kun i "Row details" paa en telefon; ellers som foer."""
    ctrl.vis = lay.mobile_or(ROWS_MORE_ON, ctrl.props.get("Visible") or "true")
    return ctrl


def _mobile_card(fl, desc, meta_cells, vals, atex, pops, status, copy, delete):
    """Raekkens celler som et kort paa en telefon (se M_CARD_W ovenfor)."""
    tw = M_TW
    for c in meta_cells:
        # Klasse, StrIndicator og ABC staar i kortets linje A (row_meta_m).
        mobile.hide_on_mobile(c)
    mobile.gallery_place(status, x=f"({tw}) - {ACT_BTN + M_GAP + M_STATUS_W}", y=M_PAD_T,
                         w=M_STATUS_W, h=M_LINE)
    mobile.gallery_place(delete, x=f"({tw}) - {ACT_BTN}", y=M_PAD_T, w=ACT_BTN, h=M_LINE)
    # Felterne i fuld bredde og 44 px; uden kolonneoverskrift siger
    # pladsholderen, hvad feltet er (etiketten har skaermlaeseren i forvejen).
    for i, (inp, ph) in enumerate(((fl, '"Functional Location"'), (desc, '"Description"'))):
        mobile.gallery_place(inp, x=0, y=_m_y(1 + i), w=tw, h=M_LINE)
        cur = inp.props.get("Placeholder", '""')
        new = ph if cur == '""' else cur.replace('"")', ph + ")")
        inp.props["Placeholder"] = lay.mobile_or(new, cur)
    # D: Room | Sort field | ATEX
    vw = f"(({tw}) - {M_ATEX_W} - {2 * M_GAP}) / 2"
    for i, inp in enumerate(vals):
        lbl = _NO_CLASS[ROW_VALS[i][1]]["Column"]
        mobile.gallery_place(inp, x=0 if i == 0 else f"{vw} + {M_GAP}", y=_m_y(3), w=vw, h=M_LINE)
        ph = '"' + lbl[:1] + lbl[1:].lower() + '"'
        inp.props["Placeholder"] = lay.mobile_or(ph, inp.props.get("Placeholder", '""'))
        _more(inp)
    # Hele linjens hoejde (44) er klikfladen (issue #508, fase 6).
    mobile.gallery_place(atex, x=f"({tw}) - {M_ATEX_W}", y=_m_y(3), w=M_ATEX_W, h=M_LINE)
    atex.props["Label"] = lay.mobile_or('"ATEX"', atex.props["Label"])
    _more(atex)
    # E/F: Class data, Manufacturer, Warranty - og Copy (med tekst).
    for b, (x, line) in zip(pops, ((0, 4), (f"{M_HALF} + {M_GAP}", 4), (0, 5))):
        mobile.gallery_place(b, x=x, y=_m_y(line), w=M_HALF, h=M_LINE)
        has = b.props["Icon"][3:].split(', "Checkmark"')[0]
        b.props["Layout"] = lay.mobile_or(
            f"If(({has}) && ({M_HALF}) >= {MFR_WAR_W}, ButtonLayout.IconBefore, "
            "ButtonLayout.TextOnly)", b.props["Layout"])
        _more(b)
    mobile.gallery_place(copy, x=f"{M_HALF} + {M_GAP}", y=_m_y(5), w=M_HALF, h=M_LINE)
    copy.props["Layout"] = lay.mobile_or("ButtonLayout.IconBefore", copy.props["Layout"])
    _more(copy)


def row_meta_m():
    """Kortets linje A paa en telefon: raekkens nummer, klasse,
    StrIndicator og ABC indicator i een linje (kun mobil)."""
    txt = (f'With({{ c: ThisItem.AssignedClass, k: ThisItem.KksType, a: {_val("ABC INDIC.")} }}, '
           '"#" & ThisItem.Pos & "  \u00b7  " & If(IsBlank(c), "No class yet", c) & '
           'If(IsBlank(k), "", "  \u00b7  Str. " & k) & If(IsBlank(a), "", "  \u00b7  ABC " & a))')
    t = text_ctrl("txtFlRowMetaM", txt, size=13, weight="Semibold", height=20, wrap="false",
                  visible=lay.MOBILE,
                  accessible='"Row " & ThisItem.Pos & ", class " & '
                             'Coalesce(ThisItem.AssignedClass, "not set yet")')
    t.props["X"] = "0"
    t.props["Y"] = str(M_PAD_T + (M_LINE - 20) // 2)
    t.props["Width"] = f"Max(0, ({M_TW}) - {ACT_BTN + M_STATUS_W + 3 * M_GAP})"
    return t


# --- Sidepanelet (raekkens editor, issue #278) -------------------------------
# Felterne staar i samme raekkefoelge som raekkens kolonner (cfg.PANEL_SECTIONS
# og cfg.PANEL_FIELDS), med raekkens etiketter. colFlDet er panelets felter
# for raekken varFlDetailRow - KUN hvilke felter, ikke deres vaerdier.
# Vaerdien og beskeden laeser hvert felt selv (PANEL_VALUE, PANEL_ISSUE), saa
# samlingen ikke skal regnes om, mens man skriver: galleriet beholder sine
# felter, fokus og panelets scroll. Foer regnede valideringen samlingen om
# med KUN Manufacturer/Warranty-felterne efter hver aendring, og resten af
# panelet forsvandt. Nu regnes den kun om, naar raekken skifter klasse
# (PANEL_REFRESH) - saa er felterne nogle andre.
PANEL_KEYS = [k for k, _t in cfg.PANEL_SECTIONS]
PANE_ORD = {f: i + 1 for i, (f, _p, _l) in enumerate(cfg.PANEL_FIELDS)}
# Raekkens Manufacturer- og Warranty-knap aabner panelet ved DEN sektion.
PANEL_JUMP = {"Manufacturer": "Mfr", "Warranty": "War"}
# Class data (Rows) og Edit (Classes) aabner panelet med KUN klassens felter:
# Class characteristics og TRM - det, Class data-popuppen viste (issue #346).
PANEL_CLS_JUMP = "Class"
# Hvilke sektioner hvert spring viser; resten er foldet sammen bag "Show
# all fields". Manufacturer/Warranty: den sektion og dem efter den.
PANEL_FOCUS = {j: PANEL_KEYS[PANEL_KEYS.index(j):] for j in PANEL_JUMP.values()}
PANEL_FOCUS[PANEL_CLS_JUMP] = ["Class", "TRM"]
PANEL_DR = "LookUp(colFlRows, RowGuid = varFlDetailRow)"
PANEL_CLS = f'Coalesce({PANEL_DR}.AssignedClass, "NO CLASS")'


def _panel_row_only():
    """Class: raekkens klasse, kun til visning."""
    f = cfg.PANEL_ROW_ONLY
    pane, lbl = next((p, l) for x, p, l in cfg.PANEL_FIELDS if x == f)
    return (f'{{ Column: "{lbl}", Field: "{f}", Editable: false, List: "", MaxLen: 0, '
            f'Section: "Master", Kind: "ro", Pane: "{pane}", PaneOrd: {PANE_ORD[f]}, '
            'Value: "", Issue: "" }')


# Status-sektionen (SAP status, Info, User status, System status) er ikke
# med i panelet (issue #278) - status vises stadig i raekken og i Classes.
# GIV_EXT/WCM (Ext) er fjernet fra panelet (issue #308); deres vaerdier
# bliver i colFlVals og gemmes uaendret. Master-felterne faar sektion,
# plads og etiket fra colFlPane; Class og TRM beholder reglernes sektion og
# raekkefoelge.
PANEL_HIDE = " && ".join(f'Section <> "{x}"' for x in cfg.HIDDEN_SECTIONS)
PANEL_ITEMS = f"""With(
    {{ dc: {PANEL_CLS} }},
    ForAll(
        Filter(colFlColumns, Cls = dc && {PANEL_HIDE}) As K,
        With(
            {{ pm: LookUp(colFlPane, Field = K.Field) }},
            {{
                Column: Coalesce(pm.Label, K.Column), Field: K.Field, Editable: K.Editable,
                List: K.List, MaxLen: K.MaxLen, Section: K.Section, Kind: K.Kind,
                Pane: Coalesce(pm.Pane, K.Section), PaneOrd: Coalesce(pm.Ord, 100 + K.Ord),
                Value: "", Issue: ""
            }}
        )
    )
)"""
PANEL_FILL = (f"Set(varFlDetCls, {PANEL_CLS});\n"
              f"ClearCollect(colFlDet, {PANEL_ITEMS});\n"
              f"Collect(colFlDet, {_panel_row_only()})")
# Valideringens afsnit H (fl_validation.verify_fx).
PANEL_REFRESH = (f"If(\n"
                 f"    IfError(varFlPanelOpen, false) && !IsBlank({PANEL_DR}) &&\n"
                 f"    {PANEL_CLS} <> varFlDetCls,\n"
                 f"    {PANEL_FILL.replace(chr(10), chr(10) + '    ')}\n"
                 f")")
# Feltets vaerdi og besked - laest direkte, ikke fra colFlDet.
PANEL_VALUE = (f"With({{ dr: {PANEL_DR} }}, Switch(ThisItem.Field, "
               '"STRINDICATOR", dr.KksType, "STR. INDICATOR", dr.KksType, '
               '"FUNCTIONAL LOCATION", dr.FL, "DESCRIPTION", dr.Description, '
               '"ASSIGNED CLASS", dr.AssignedClass, '
               'Coalesce(LookUp(colFlVals, RowGuid = varFlDetailRow && Field = ThisItem.Field).Value, "")))')
PANEL_ISSUE = V.field_issue("varFlDetailRow", "ThisItem.Field").replace("\n", " ")


# --- Bundbjaelken (issue #308): Delete row | Reset ... Cancel | Save ------
# Som Materials' panel (build_helpers.editor_footer). Felterne skriver
# stadig direkte i raekken (de skal valideres, mens man skriver), saa
# panelet tager et AFTRYK af raekken, naar det aabnes paa den (PANEL_SNAP):
#   Reset   raekken tilbage til aftrykket, og panelet bliver aabent
#           (issue #403). Slaaet fra, naar intet er aendret. Spoerger
#           foerst med den faelles Reset-bekraeftelse (issue #450,
#           build_helpers.reset_confirm): den vises kun, mens der er noget
#           at kassere, og et tryk paa dens sloer lukker den altid, saa
#           sloeret ikke kan blive staaende (issue #405).
#   Cancel  raekken tilbage til aftrykket, og panelet lukker.
#   Save    anmodningen gemmes (samme gem som Save draft), og panelet
#           lukker, naar gemmet lykkedes.
#   Delete row  bekraeftelse, saa raekken fjernes (som raekkens ikon).
# Close (X), et klik ved siden af og Previous/Next beholder aendringerne,
# som foer.
PANEL_SNAP = ("ClearCollect(colFlPanelSnap, LookUp(colFlRows, RowGuid = varFlDetailRow));\n"
              "ClearCollect(colFlPanelSnapVals, Filter(colFlVals, RowGuid = varFlDetailRow))")
PANEL_DIRTY = ("With({ s: First(colFlPanelSnap), r: LookUp(colFlRows, RowGuid = varFlDetailRow) }, "
               "!IsBlank(s.RowGuid) && ("
               "Coalesce(r.FL, \"\") <> Coalesce(s.FL, \"\") || "
               "Coalesce(r.Description, \"\") <> Coalesce(s.Description, \"\") || "
               "CountRows(Filter(colFlVals, RowGuid = s.RowGuid)) <> CountRows(colFlPanelSnapVals) || "
               "CountRows(Filter(colFlPanelSnapVals As o, "
               "Coalesce(LookUp(colFlVals, RowGuid = o.RowGuid && Field = o.Field).Value, \"\") <> o.Value)) > 0))")
PANEL_RESTORE = f"""With(
    {{ s: First(colFlPanelSnap) }},
    If(
        !IsBlank(s.RowGuid) && !IsBlank(LookUp(colFlRows, RowGuid = s.RowGuid)),
        Patch(colFlRows, LookUp(colFlRows, RowGuid = s.RowGuid), s);
        RemoveIf(colFlVals, RowGuid = s.RowGuid);
        Collect(colFlVals, colFlPanelSnapVals)
    )
);
// Issue #533: raekken er som ved aabningen, og varFlDirty ogsaa.
Set({DIRTY}, Coalesce(varFlDirtyAtOpen, true));
{REVERIFY}"""
PANEL_LOCKED = 'varFlViewOnly || varFlStatus = "Indsendt"'
PANEL_DM = f"If({PANEL_LOCKED}, DisplayMode.Disabled, DisplayMode.Edit)"
# Reset spoerger foerst (issue #450, build_helpers.reset_confirm).
RESET_ASK = "varFlPanelResetAsk"
# Reset er slaaet fra, naar raekken allerede er som ved aabningen (#403).
RESET_DM = f"If({PANEL_LOCKED} || !({PANEL_DIRTY}), DisplayMode.Disabled, DisplayMode.Edit)"


def open_row_panel_fx(guid, jump='""'):
    """Aabn panelet for raekken guid. jump: hvad knappen aabner (PANEL_FOCUS)
    - Manufacturer/Warranty: den sektion og dem efter (issue #278); Class
    data/Edit i Classes: klassens felter (issue #346). De andre sektioner er
    foldet sammen bag "Show all fields". Tom = alle sektioner."""
    return (f"Set(varFlDetailRow, {guid});\n"
            f"Set(varFlPanelJump, {jump});\n"
            f"{PANEL_FILL};\n"
            f"{PANEL_SNAP};\n"
            f'Set({PANEL_SAVE}, "");\n'
            f"Set(varFlDirtyAtOpen, Coalesce({DIRTY}, false));\n"
            "Set(varFlPanelOpen, true)")


def _panel_grid(key, label, cols):
    items = f'Sort(Filter(colFlDet, Pane = "{key}"), PaneOrd)'
    return field_grid(f"Panel{key}", f'Pane = "{key}"', label, cols=cols, items=items, live=True)


def _panel_section(key, title):
    fields = [_panel_grid(key, f'"{title}"', PANEL_COLS)]
    sub = cfg.PANEL_SUB.get(key)
    if sub:
        # StrIndicator og Class paa een linje (issue #308, navne #467).
        fields.append(_panel_grid(sub, f'"{title} - StrIndicator and class"', PANEL_SUB_COLS))
    has = f'CountRows(Filter(colFlDet, Pane = "{key}")) > 0'
    # Aabnet fra en knap (PANEL_FOCUS): sektionerne, den ikke viser, er
    # foldet sammen.
    hide = [j for j, shown in PANEL_FOCUS.items() if key not in shown]
    vis = has
    if hide:
        keys = ", ".join(f'"{k}"' for k in hide)
        vis = f'{has} && !(IfError(varFlPanelJump, "") in [{keys}])'
    heading = text_ctrl(f"txtFlPanel{key}Title", f'"{title}"', size=lay.SIZE_BODY,
                        weight="Semibold", height=22, wrap="false", visible=vis)
    # TELEFONEN (issue #508): sektionerne kan klappes sammen (chevron), saa
    # panelet ikke er en lang formular. Aabnet fra en knap (Class data,
    # Manufacturer, Warranty) er knappens sektioner altid aabne - de andre
    # er skjult som foer. Under "Show all fields" er Functional location og
    # sektioner med en fejl aabne; resten viser antal udfyldte og fejl.
    mobile.hide_on_mobile(heading)
    fold = mobile.collapsible(f"FlPanel{key}", title, fields, _sec_var(key),
                              summary=_sec_summary(key), size=lay.SIZE_BODY,
                              open_expr=_sec_open(key))
    # Chevronen kun, naar sektionen KAN klappes (ikke aabnet fra en knap).
    chev = mobile.find(fold[0], f"btnFlPanel{key}Fold")
    chev.vis = f"{chev.vis} && IsBlank(IfError(varFlPanelJump, \"\"))"
    return group(f"conFlPanel{key}", [heading] + fold, direction="Vertical",
                 gap=PANEL_HEAD_GAP, visible=vis)


def _sec_var(key):
    return f"varFlPanel{key}Open"


def _sec_fields(key):
    """Sektionens felter (og dens undergitter: Main har StrIndicator/Class)."""
    panes = [key] + ([cfg.PANEL_SUB[key]] if key in cfg.PANEL_SUB else [])
    test = " || ".join(f'Pane = "{k}"' for k in panes)
    return f"Filter(colFlDet, {test}).Field"


def _sec_errors(key):
    """Felter i sektionen med en fejl (samme udvalg som field_issue for
    spool-felterne). Main's FL/Description har deres egen besked - Main er
    altid aaben, saa den taeller ikke."""
    return (f'CountRows(Filter(colFlIssues, RowGuid = varFlDetailRow && Sev = "Error" && '
            f'Ord >= 100 && Field in {_sec_fields(key)}))')


def _sec_open(key):
    """Er sektionen aaben paa telefonen? Aabnet fra en knap: altid (de
    andre sektioner er skjult). Ellers brugerens valg, og som standard
    Main og sektioner med en fejl."""
    default = "true" if key == "Main" else f"IfError({_sec_errors(key)} > 0, false)"
    return (f'If(!IsBlank(IfError(varFlPanelJump, "")), true, '
            f"Coalesce({_sec_var(key)}, {default}))")


def _sec_summary(key):
    """Opsummeringen, mens sektionen er lukket: fejl og udfyldte felter."""
    fields = _sec_fields(key)
    return (f'IfError(With({{ e: {_sec_errors(key)}, '
            f"f: CountRows(Filter(colFlVals, RowGuid = varFlDetailRow && Field in {fields})), "
            f"n: CountRows({fields}) }}, "
            'If(e > 0, e & " to fix  \u00b7  ", "") & f & " of " & n & " filled"), "")')


# Afstanden mellem sektionerne (issue #347). Hvert felt slutter allerede
# med sin beskedlinje og 10 px luft (field_grid, TILE_H), saa sektionerne
# skal kun have lidt ekstra - foer gav 16 + 8 en stor tom flade mellem dem.
# Een afstand overalt, med og uden "Show all fields"; afstanden MELLEM
# felterne (TILE_H) er uaendret.
PANEL_SECTION_GAP = 4
# Overskriften og dens felter (og Main-sektionens to gitre).
PANEL_HEAD_GAP = 4
PANEL_PAD = 20
# Panelets formularbredde: panelet minus pad, scrollens pad og scrollbaren.
# Paa telefonen (issue #508) er polstringen 12 + 0 (lay.PANEL_INNER_W).
assert PANEL_PAD == 20, "lay.PANEL_INNER_W regner med 2 x 20 + 2 x 20 fra Tablet"
PANEL_FORM_W = lay.PANEL_INNER_W
PANEL_COL_MIN = 200
# 3 kolonner naar de kan faa PANEL_COL_MIN hver, ellers 2, ellers 1. Paa
# telefonen altid EEN kolonne (issue #508) - ogsaa paa en bred telefon.
PANEL_COLS = lay.mobile_or("1", f"If(({PANEL_FORM_W}) >= 3 * {PANEL_COL_MIN}, 3, "
                                f"If(({PANEL_FORM_W}) >= 2 * {PANEL_COL_MIN}, 2, 1))")
# KKS type + Assigned class: side om side, og under hinanden (KKS type
# foerst), naar to kolonner ikke kan faa PANEL_COL_MIN hver.
PANEL_SUB_COLS = lay.mobile_or("1", f"If(({PANEL_FORM_W}) >= 2 * {PANEL_COL_MIN}, 2, 1)")
# Panelets gem-tilstand: "saving", "failed" eller tom (issue #402,
# build_helpers.panel_save_status). Hoerer til den raekke, der er aaben -
# den nulstilles, naar panelet aabnes paa en raekke og naar det lukkes.
PANEL_SAVE = "varFlPanelSave"
CLOSE_PANEL_FX = (f'Set({PANEL_SAVE}, ""); '
                  'Set(varFlPanelOpen, false); Set(varFlPanelJump, ""); '
                  'Set(varFlDetailRow, ""); Clear(colFlDet); '
                  'Clear(colFlPanelSnap); Clear(colFlPanelSnapVals)')


def build_row_panel():
    position = ('"Row " & Text(LookUp(colFlRows, RowGuid = varFlDetailRow).Pos) & '
                '" of " & Text(CountRows(colFlRows))')
    current = "LookUp(colFlRows, RowGuid = varFlDetailRow).Pos"
    rows = "Sort(colFlRows, RowNo)"
    previous_id = f"Index({rows}, Max(1, {current} - 1)).RowGuid"
    next_id = f"Index({rows}, Min(CountRows({rows}), {current} + 1)).RowGuid"
    previous_mode = f"If({current} <= 1, DisplayMode.Disabled, DisplayMode.Edit)"
    next_mode = f"If({current} >= CountRows({rows}), DisplayMode.Disabled, DisplayMode.Edit)"
    close_fx = CLOSE_PANEL_FX
    vis = "IfError(varFlPanelOpen, false)"

    # Gennemsigtigt sloer VED SIDEN AF panelet: et tryk paa siden bag lukker
    # det (som side_nav's NavScrim). Det ligger ALDRIG under selve panelet
    # (issue #278): foer daekkede det hele skaermen, saa et tryk eller et rul
    # paa panelets tomme flader - mellem felterne, eller dér hvor et felt
    # lige var forsvundet - kunne ramme sloeret og lukke panelet. Under
    # Desktop fylder panelet hele skaermen, og der er intet sloer.
    side_w = f"App.Width - ({lay.PANEL_W_AT})"
    scrim_vis = f"{vis} && ({side_w}) > 0"
    backdrop = Ctrl("imgFlEditorBackdrop", "Image", props={
        "AccessibleLabel": '"Close row editor"',
        "BorderStyle": "BorderStyle.None",
        "BorderThickness": "0",
        **stable_scrim(C_TRANSPARENT),
        "Height": "App.Height",
        "Image": '""',
        "OnSelect": close_fx,
        "TabIndex": "0",
        "Visible": scrim_vis,
        "Width": f"Max(0, {side_w})",
        "X": "0",
        "Y": "0",
    }, h="App.Height", vis=scrim_vis)

    prev = icon_button("btnFlEditorPrevious", "Previous row", open_row_panel_fx(previous_id),
                       icons.CHEVRON_LEFT, previous_mode)
    next_ = icon_button("btnFlEditorNext", "Next row", open_row_panel_fx(next_id),
                        icons.CHEVRON_RIGHT, next_mode)
    prev.vis = next_.vis = "CountRows(colFlRows) > 1"
    close = icon_button("btnFlEditorClose", "Close", close_fx, icons.CLOSE)
    title = grow(text_ctrl("txtFlEditorPosition", position, size=lay.SIZE_CARD_TITLE,
                           weight="Semibold", height=28, wrap="false"))
    heading = icon_heading("conFlEditorHeading", title, [prev, next_, close])

    # Aabnet fra en knap (PANEL_FOCUS): dens sektioner staar oeverst, og de
    # sammenfoldede sektioner kan vises igen med denne knap.
    jumped = '!IsBlank(IfError(varFlPanelJump, ""))'
    show_all = _fit(button("btnFlPanelShowAll", '"Show all fields"', 'Set(varFlPanelJump, "")',
                           visible=jumped, icon="ChevronUp",
                           tooltip='"Show all the fields of this row"'), icon=True)
    show_all.props["Appearance"] = "ButtonAppearance.Outline"
    show_all.props["BorderColor"] = C_INPUT_BORDER
    show_all.props["BorderThickness"] = "1"
    show_all.props["AlignInContainer"] = "AlignInContainer.Start"
    mobile.touch(show_all)
    # Klassen uden klassefelter (som popuppens "This class has no class
    # data fields.") - ellers stod panelet tomt under "Show all fields".
    cls_keys = ", ".join(f'"{k}"' for k in PANEL_FOCUS[PANEL_CLS_JUMP])
    no_cls = text_ctrl("txtFlPanelClsNone", '"This class has no class data fields."',
                       size=13, color=C_MUTED, height=20, wrap="false",
                       visible=(f'IfError(varFlPanelJump, "") = "{PANEL_CLS_JUMP}" && '
                                f'IfError(CountRows(Filter(colFlDet, Pane in [{cls_keys}])) = 0, false)'))
    sections = ([show_all] + [_panel_section(k, t) for k, t in cfg.PANEL_SECTIONS]
                + [no_cls])
    footer = _panel_footer()
    # Gemmets tilstand lige over bundbjaelken (issue #402).
    status = panel_save_status("Fl", PANEL_SAVE, PANEL_SAVE_FX, SAVE_DM)
    # Pad (2 x 16), overskrift, bundbjaelken og to mellemrum: bunden
    # klippes aldrig, og bundbjaelken staar fast under det, der scroller.
    # Statuslinjen tager kun plads, mens den vises.
    scroll_h = (f"App.Height - ({2 * 16 + lay.HIT_TOUCH + 2 * 12} + ({footer.h}))"
                f" - {panel_save_space(status)}")
    scroll = group("conFlEditorSections", sections, direction="Vertical", gap=PANEL_SECTION_GAP,
                   height=scroll_h, overflow_y="Scroll",
                   pad=(16, PANEL_PAD, 16, PANEL_PAD))
    panel = group("conFlEditorPanel", [heading, scroll, status, footer], direction="Vertical", gap=12,
                  height="App.Height", width=lay.PANEL_W_AT, fill=C_CARD_BG,
                  border_color=C_CARD_BORDER, pad=(16, PANEL_PAD, 16, PANEL_PAD),
                  visible=vis, drop_shadow="Bold")
    panel.props["X"] = f"If({at_least('Desktop')}, App.Width - Self.Width, 0)"
    panel.props["Y"] = "0"
    # TELEFONEN (issue #508): panelet er allerede hele skaermen under Desktop
    # (PANEL_W_AT), med overskriften (Row n of m, pilene og Luk) fast
    # oeverst og bundbjaelken fast nederst. Som row_editor_panel: 12 px i
    # siderne, formularen uden ekstra polstring (PANEL_FORM_W regner med det).
    mobile.full_screen(panel, pad_x=lay.MOBILE_PAD_X)
    mobile_pad(scroll, x=0)
    # Mens panelet gemmer: et gennemsigtigt lag over alt. Bekraeftelserne
    # ligger OVER panelet.
    return [backdrop, panel, panel_save_block("Fl", PANEL_SAVE)] + _panel_confirms()


PANEL_SAVE_W = fit_button_width('"Save"') + ICON_W + 8
# Panelets Save - og Retry: det samme gem som Save draft, men uden sidens
# sloer og bjaelke (issue #402). Lykkes det, lukker panelet; ellers staar
# raekken, som brugeren efterlod den, med "Save failed" og Retry.
PANEL_SAVE_FX = panel_save_fx(
    PANEL_SAVE, S.save_fx(),
    f'If(CountRows(colFlSaveErrors) = 0, {CLOSE_PANEL_FX}, Set({PANEL_SAVE}, "failed"))')


def _panel_footer():
    """Delete row og Reset til venstre, Cancel og Save til hoejre - samme
    knapper, maal og raekkefoelge som Materials (issue #308)."""
    delete = button("btnFlEditorDelete", '"Delete row"', "Set(varFlPanelDelAsk, true)",
                    danger=True, width=fit_button_width('"Delete row"'), height=lay.HIT_TOUCH,
                    display_mode=PANEL_DM, visible="!IsBlank(varFlDetailRow)")
    # Reset: tilbage til aftrykket efter bekraeftelsen (issue #450) - kun
    # naar der er noget at kassere. Panelet bliver aabent (issue #403).
    reset = button("btnFlEditorReset", '"Reset"',
                   reset_click_fx(RESET_ASK, PANEL_DIRTY, PANEL_RESTORE),
                   width=fit_button_width('"Reset"'), height=lay.HIT_TOUCH, display_mode=RESET_DM,
                   tooltip='"Undo the changes made to this row since it was opened"')
    cancel = button("btnFlEditorCancel", '"Cancel"',
                    f"If(\n    {PANEL_DIRTY},\n    {PANEL_RESTORE.replace(chr(10), chr(10) + '    ')}\n);\n"
                    f"{CLOSE_PANEL_FX}",
                    width=fit_button_width('"Cancel"'), height=lay.HIT_TOUCH,
                    tooltip='"Undo the changes made to this row since it was opened and close the panel"')
    save = button("btnFlEditorSave", '"Save"', PANEL_SAVE_FX,
                  primary=True, width=PANEL_SAVE_W, height=lay.HIT_TOUCH,
                  display_mode=panel_save_mode(PANEL_SAVE, SAVE_DM), icon='"Save"',
                  # Issue #533: et RIGTIGT gem af hele anmodningen (S.save_fx) - det
                  # samme som Save draft, saa den skal ikke gemmes igen bagefter.
                  tooltip='"Saves the complete request (same as Save draft) and closes the panel"')
    save.props["AccessibleLabel"] = "Self.Text"
    panel_save_text(save, PANEL_SAVE)
    return editor_footer("Fl", delete, reset, cancel, save)


def _panel_confirms():
    """Delete row og Reset spoerger foerst - som Materials (issue #450).
    Reset kasserer kun aendringerne siden panelet blev aabnet."""
    pos = 'Text(LookUp(colFlRows, RowGuid = varFlDetailRow).Pos)'
    delete = confirm_modal(
        "FlRowDel", "varFlPanelDelAsk", "Delete row?",
        f'"Row " & {pos} & " is removed from the request. Save the request to delete it in SharePoint too."',
        "Delete", delete_row_fx("varFlDetailRow") + ";\n" + CLOSE_PANEL_FX,
        "btnFlRowDelConfirm", icon="Delete")
    reset = reset_confirm("FlRowReset", RESET_ASK, PANEL_RESTORE, PANEL_DIRTY, "this row",
                          guard=f"IfError(varFlPanelOpen, false) && !({PANEL_LOCKED})")
    return delete + reset


def build_rows():
    # "Rows" og hvor mange der er gyldige (UX-review F1/T7 og FL Spool):
    # kortet hed "Validation".
    title = text_ctrl("txtFlRowsH", '"Rows"', size=lay.SIZE_CARD_TITLE, weight="Semibold",
                      height=26, wrap="false", width=text_px("Rows", lay.SIZE_CARD_TITLE))
    # Issue #533: "Unsaved changes" ogsaa her, saa det ses paa alle
    # skaermbredder (headeren viser det kun fra Desktop).
    count = grow(text_ctrl("txtFlRowsCount",
                           f'Text({S.READY}) & " of " & Text(CountRows(colFlRows)) & " valid" & '
                           f'If({UNSAVED}, "  \u00b7  Unsaved changes", "")',
                           size=13, color=C_MUTED, height=20, wrap="false"))
    add = _fit(button("btnFlAddRow", '"Add row"', capped_add_row_fx(),
                      display_mode=DM_EDIT, icon="Add", primary=True), icon=True)
    paste = _fit(button("btnFlPasteRows", '"Paste rows"', PASTE_OPEN,
                        display_mode=DM_EDIT, icon=icons.FLUENT["paste"],
                        tooltip='"Paste functional locations and descriptions copied from Excel"'),
                 icon=True)
    # Telefonen (issue #508): Paste rows og Add row er 44 x 44 ikoner, saa
    # titlen og taelleren kan staa paa linjen ved 320 px.
    for b in (paste, add):
        b.props["Width"] = lay.mobile_or(mobile.TOUCH, b.props["Width"])
        b.props["LayoutMinWidth"] = b.props["Width"]
        b.props["Layout"] = lay.mobile_or("ButtonLayout.IconOnly", b.props["Layout"])
        mobile.touch(b)
    head_row = group("conFlRowsTop", pin_widths([title, count, paste, add]), direction="Horizontal",
                     gap=12, align_items="Center", height=lay.mobile_or(mobile.TOUCH, 36))
    # "Row details" (kun telefonen): kortenes ekstra linjer - se M_CARD_W.
    more, = mobile.collapsible("FlRowsMore", "Row details", [], ROWS_MORE,
                               summary='"Room, sort, class, maker, warranty"')

    head = mobile.hide_on_mobile(table_head("conFlRowsHead", V_SPEC, gap=VGAP, width=V_GAL_W))
    n = "CountRows(colFlRows)"
    gal = table_gallery("galFlRows", '"Functional Location rows"',
                        "Sort(colFlRows, RowNo)", n, row_cells(), "conFlRow",
                        row_h=V_ROW_H, gap=VGAP, width=lay.mobile_or(M_CARD_W, V_GAL_W),
                        tpl_h=ROW_TOP_F,
                        # En ny kopi kan ses paa sin baggrund (issue #467).
                        row_fill=f"If({COPIED}, {C_INFO_BG}, {C_TRANSPARENT})",
                        extra=[row_meta_m()])
    # Kortene paa telefonen: hele listen uden egen scroll (op til M_ROWS_MAX),
    # og raekkens baggrund (en ny kopi) daekker hele kortet.
    gal.props["TemplateSize"] = lay.mobile_or(M_ROW_H, gal.props["TemplateSize"])
    gal.props["Height"] = lay.mobile_or(f"Min({n}, {M_ROWS_MAX}) * ({M_ROW_H})", gal.props["Height"])
    gal.h = gal.props["Height"]
    gal.props["ShowScrollbar"] = lay.mobile_or(f"{n} > {M_ROWS_MAX}", gal.props["ShowScrollbar"])
    mobile.gallery_place(mobile.find(gal, "conFlRow"), w=M_TW, h=f"({M_ROW_H}) - 1")
    # Vandret scroll, naar tabellen er bredere end kortet (Equipment/
    # Materials' moenster, domain_parts). Start, ikke Stretch - check_layout
    # regel 14. Den vandrette scrollbar tager hoejde, saa den laegges til.
    table = group("conFlTable", [head, mobile.hide_on_mobile(divider("conFlRowsRule", width=V_GAL_W)),
                                 gal],
                  direction="Vertical", gap=10, overflow_x="Scroll", align_items="Start")
    # Paa telefonen er tabellen kun kortene - kortet er aldrig bredere end
    # pladsen, saa der er ingen vandret scrollbar.
    table.props["Height"] = lay.mobile_or(
        f"Min({n}, {M_ROWS_MAX}) * ({M_ROW_H})",
        f"{table.props['Height']} + If({V_WIDE}, {SCROLLBAR_W}, 0)")
    table.h = table.props["Height"]

    # Kun noget at sige, naar der ER noget: en fejl ved gem/indsend, eller
    # raekker, der blokerer Submit. Ingen "Ready."/"Done." (issue #77).
    # Telefonen (issue #508): beskeden ombrydes paa to linjer i stedet for
    # at blive skaaret af - den siger, hvad der blokerer Submit.
    info = text_ctrl("txtFlInfo",
                     "varFlInfo",
                     size=12, color=C_INVALID_FG, height=lay.mobile_or(36, 18),
                     wrap=lay.mobile_or("true", "false"),
                     visible="!IsBlank(varFlInfo)")
    return card("conFlRowsCard", [head_row, more, table, info, verify_button()], gap=10)

# ---------------------------------------------------------------------------
# Klassefanerne (functional-location.html:77-81, FL28 og FL60)
# ---------------------------------------------------------------------------
# CLASSES ER ROWS' FAELLES KOLONNER + EDIT (issue #468): #, Functional
# Location, Description, StrIndicator, Class, Room, Sort field, ABC
# indicator og ATEX med Rows' bredder (V_SPEC) og mellemrum (VGAP), saa de
# staar lige under Rows' kolonner. Her er de kun til visning - de rettes i
# Rows eller sidepanelet. Edit staar lige efter ATEX. Room, Sort field, ABC
# indicator og ATEX kom med i issue #467.
C_SHARED = 3 + len(V_SHARED)
C_ROW_VALS = ("Room", "Sort", "Abc", "Atex")
assert [n for n, *_ in V_SPEC[:C_SHARED]] == ["No", "Fl", "Desc", "Kks", "Cls", *C_ROW_VALS]
# CLASSES FYLDER OGSAA KORTET, OG ACTIONS STAAR UNDER ROWS' ACTIONS (issue
# #490). Edit er nu en blyant i en Actions-kolonne med Rows' Actions-bredde
# (ACT_W). Mellem ATEX og Actions staar en tom kolonne (Gap) paa Rows'
# Class data..Status (C_MID_W) - saa de to tabeller er lige brede, og
# blyanten staar lige under Rows' Copy. Er kortet for smalt til hele Rows,
# krymper Gap foerst, saa Classes kun scroller, naar det er noedvendigt.
C_MID = [w for n, _l, w in V_FIXED if n in ("ClsData", "Mfr", "War", "Status")]
C_MID_W = sum(C_MID) + VGAP * (len(C_MID) - 1)
C_ACT = ("Open", "Actions", ACT_W, None)
C_BASE_W = spec_width(V_SPEC[:C_SHARED] + [C_ACT])
C_GAP_W = f"Min({C_MID_W}, Max(0, ({ROWS_W}) - {C_BASE_W} - {VGAP}))"
C_SPEC = V_SPEC[:C_SHARED] + [("Gap", "", C_GAP_W, None), C_ACT]
C_W = spec_width(C_SPEC)
C_GAL_W = f"({C_W}) + {SCROLLBAR_W} + {GALLERY_RESERVE}"

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
# Telefonen (issue #508): fanerne er 42 px hoeje (galleriet 48 med
# TemplatePadding 3), og Classes' raekker er kort paa tre linjer:
#   #3 . FL                                   [Edit]
#   Description
#   CLASS . Str. X . Room . Sort . ABC . ATEX
TAB_H_M = 42
C_ROW_H_M = 76
C_ROWS_MAX = 50
CLASSES_OPEN = "varFlClassesOpen"
# CLASSES ER KLAPPET SAMMEN SOM STANDARD - PAA ALLE SKAERMBREDDER (issue
# #533). Rows er arbejdsfladen; Classes er en anden visning af de SAMME
# raekker (V.BUCKETS), og med op til 100 raekker fyldte den meget. Lukket
# viser overskriften en opsummering, regnet af raekkerne:
#   Classes  . 100 Functional Locations . 8 classes
# Functional Locations: raekker, der ikke er tomme (EMPTY_ROW - den tomme
# raekke nederst taeller ikke). Classes: de klasser, Classes-listen viser
# (V.BUCKETS - samme som fanerne). Tilstanden (CLASSES_OPEN) saettes kun af
# chevronen: rettelser, faner, gem og indsend roerer den ikke. Den
# nulstilles (lukket), naar en anden anmodning aabnes (RESET_FX, S.load_fx).
CLASSES_FLS = f"CountRows(Filter(colFlRows, !({EMPTY_ROW})))"
CLASSES_N = f"CountRows(Distinct({V.BUCKETS}, AssignedClass))"
CLASSES_SUMMARY = ("IfError(" + dt.plural(CLASSES_FLS, "Functional Location") + ' & "  \u00b7  " & '
                   + dt.plural(CLASSES_N, "class", "classes") + ', "")')


def build_classes():
    """Uden klassificerede raekker er kortet KUN titlen og een linje - ingen
    tom fanebjaelke, overskrift eller tom raekke (issue #77)."""
    tab = button("btnFlTab", "ThisItem.Label", "Set(varFlTab, ThisItem.Key)", width=130,
                 height=lay.mobile_or(TAB_H_M, 34))
    sel = "varFlTab = ThisItem.Key"
    # Det faelles segment-udtryk (build_helpers.seg_style, issue #526).
    seg_style(tab, sel, icon=False, standalone=True)
    # FL65: klassens hjaelpetekst (resolveClassHelpText :2353-2357).
    tab.props["Tooltip"] = ('With({ hp: LookUp(colFlClassHelp, Key = ThisItem.Key).Help }, '
                            'If(IsBlank(hp), "", ThisItem.Key & ": " & hp))')
    tabs = Ctrl("galFlTabs", "Gallery", variant="Horizontal", props={
        "AccessibleLabel": '"Class tabs"',
        "BorderStyle": "BorderStyle.None",
        "Fill": C_CARD_BG,
        "FillPortions": "0",
        "Height": lay.mobile_or(TAB_H_M + 6, 40),
        "Items": "colFlTabs",
        "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None",
        "Selectable": "false",
        # Kun naar fanerne ikke kan staa paa een linje.
        # Paa telefonen swipes fanerne - ingen scrollbar under dem.
        "ShowScrollbar": lay.mobile_or("false", f"CountRows(colFlTabs) * {TAB_W} > {SHELL_W} - 36"),
        "TabIndex": "0",
        "TemplatePadding": "3",
        "TemplateSize": str(TAB_W - 6),
        "Visible": HAS_CLASSES,
        "Width": "Parent.Width",
        "WrapCount": "1",
    }, children=[tab], h=lay.mobile_or(TAB_H_M + 6, 40), vis=HAS_CLASSES)

    # Issue #533: i View er blyanten et View-ikon (CLS_VIEW_ICON).
    note_txt = lay.mobile_or(
        f'If({CLS_LOCKED}, "The view icon opens the class data of the row.", '
        '"The pencil opens the class data of the row.")',
        f'If({CLS_LOCKED}, "Compact view - the view icon opens the class data of the row.", '
        '"Compact view - the Edit pencil opens the class data of the row.")')
    note = text_ctrl("txtFlClassNote", note_txt, accessible=note_txt,
                     size=12, color=C_MUTED, height=18, wrap="false", visible=HAS_CLASSES)

    head = table_head("conFlClsHead", C_SPEC, gap=VGAP, width=C_GAL_W)
    head.props["Visible"] = HAS_CLASSES
    head.vis = HAS_CLASSES

    # Alle vaerdier er kun til visning her (issue #468) - de rettes i Rows
    # eller i sidepanelet (Edit). Samme tekststil som Rows' visningsceller.
    no = text_ctrl("txtFlCNo", "Text(ThisItem.Pos)", size=13, color=C_MUTED, height=20,
                   wrap="false")
    fl = text_ctrl("txtFlCFl", 'If(IsBlank(ThisItem.FL), "-", ThisItem.FL)', size=13,
                   height=20, wrap="false", accessible='"Functional Location: " & Self.Text')
    desc = text_ctrl("txtFlCDesc", 'If(IsBlank(ThisItem.Description), "-", ThisItem.Description)',
                     size=13, height=20, wrap="false", accessible='"Description: " & Self.Text')
    strc = text_ctrl("txtFlCStr", 'If(IsBlank(ThisItem.KksType), "-", ThisItem.KksType)',
                     size=13, height=20, wrap="false")
    clsc = text_ctrl("txtFlCCls", 'If(IsBlank(ThisItem.AssignedClass), "-", ThisItem.AssignedClass)',
                     size=13, weight="Semibold", height=20, wrap="false")
    # Raekkens Room, Sort field, ABC indicator og ATEX (issue #467). Samme
    # felter som Rows' celler (ROW_VALS, txtFlRowAbc, chkFlRowAtex).
    ro_vals = []
    for n, f in (("Room", "ROOM"), ("Sort", "SORT FIELD"), ("Abc", "ABC INDIC.")):
        ro_vals.append(text_ctrl(f"txtFlC{n}", f'With({{ v: {_val(f)} }}, If(IsBlank(v), "-", v))',
                                 size=13, weight="Semibold" if n == "Abc" else None,
                                 height=20, wrap="false"))
    ro_vals.append(text_ctrl("txtFlCAtex", f'If(Upper(Trim({_val("ATEX")})) = "X", "Yes", "-")',
                             size=13, height=20, wrap="false",
                             accessible='"ATEX: " & If(Self.Text = "Yes", "yes", "no")'))
    # Edit aabner raekkens sidepanel med klassens felter - samme panel som
    # Class data i Rows (issue #346). Hver post her ER een raekke
    # (V.BUCKETS), saa ThisItem.RowGuid er raekken. Info-kolonnen er vaek
    # (issue #468: Classes' eneste egen kolonne er Edit); raekkens foerste
    # besked staar i Edit's tooltip og paa Status-knappen i Rows.
    info_msg = "Coalesce(ThisItem.FirstIssue, ThisItem.FirstWarning, \"\")"
    # Blyanten (issue #490): samme ikonknap som Rows' Copy og Delete -
    # ACT_BTN bred, IconOnly, klikflade H.hit - i sin egen gruppe, saa den
    # ikke straekkes til kolonnens bredde.
    #
    # BLYANTEN KUN NAAR DER KAN RETTES (issue #533). I View (eller naar
    # anmodningen er indsendt - CLS_LOCKED, samme regel som sidepanelets
    # felter) aabnede blyanten et skrivebeskyttet panel og lovede noget,
    # der ikke var der. Nu er knappen et View-ikon med tooltippet "View
    # class data"; den aabner det SAMME panel (kun til at laese) og skifter
    # ikke tilstand - sidehovedets Edit er stadig eneste vej til Edit mode.
    # Issue #551: ikon og verbum fra de faelles hjaelpere (icons.edit_or_view,
    # action_tips.verb) - samme regel som Materials/Equipment/MP's raekker.
    verb = tips.verb(CLS_LOCKED)
    open_ = button("btnFlCOpen", f'{verb}',
                   open_row_panel_fx("ThisItem.RowGuid", f'"{PANEL_CLS_JUMP}"'), width=ACT_BTN,
                   height=30,
                   icon=icons.edit_or_view(CLS_LOCKED),
                   accessible=f'{verb} & " class data of " & ThisItem.FL',
                   tooltip=(f'With({{ m: {info_msg} }}, {verb} & " class data of " & ThisItem.FL & '
                            'If(IsBlank(m), "", " - " & m))'))
    open_.props["Layout"] = "ButtonLayout.IconOnly"
    ensure_hit(open_, square=False)
    c_act = group("conFlCAct", [open_], direction="Horizontal", gap=VGAP,
                  height=lay.HIT, align_items="Center")
    # Den tomme kolonne mellem ATEX og Actions (C_GAP_W).
    gap = group("conFlCGap", [], direction="Horizontal", height=20)
    cells = _cells(C_SPEC, [no, fl, desc, strc, clsc] + ro_vals + [gap, c_act])
    # Telefonen: kortet paa tre linjer (TAB_H_M ovenfor). Nummeret staar
    # foran FL, og klasse, StrIndicator, Room, Sort, ABC og ATEX i een linje
    # (txtFlCMetaM). Blyanten er 44 px til hoejre.
    for c in [no, strc, clsc] + ro_vals:
        mobile.hide_on_mobile(c)
    text_w = f"({M_TW}) - {ACT_BTN + M_GAP}"
    fl.props["Text"] = lay.mobile_or(
        '"#" & ThisItem.Pos & "  \u00b7  " & If(IsBlank(ThisItem.FL), "-", ThisItem.FL)',
        fl.props["Text"])
    mobile.gallery_place(fl, x=0, y=8, w=text_w, h=22)
    mobile.gallery_place(desc, x=0, y=30, w=text_w, h=20)
    mobile.gallery_place(open_, x=f"({M_TW}) - {ACT_BTN}", y=(C_ROW_H_M - M_LINE) // 2,
                         w=ACT_BTN, h=M_LINE)
    meta = text_ctrl(
        "txtFlCMetaM",
        f'With({{ c: ThisItem.AssignedClass, k: ThisItem.KksType, r: {_val("ROOM")}, '
        f'so: {_val("SORT FIELD")}, a: {_val("ABC INDIC.")}, x: {_val("ATEX")} }}, '
        'Coalesce(c, "-") & If(IsBlank(k), "", "  \u00b7  Str. " & k) & '
        'If(IsBlank(r), "", "  \u00b7  Room " & r) & If(IsBlank(so), "", "  \u00b7  Sort " & so) & '
        'If(IsBlank(a), "", "  \u00b7  ABC " & a) & If(Upper(Trim(x)) = "X", "  \u00b7  ATEX", ""))',
        size=12, color=C_MUTED, height=18, wrap="false", visible=lay.MOBILE)
    meta.props["X"] = "0"
    meta.props["Y"] = "50"
    meta.props["Width"] = f"Max(0, {text_w})"
    # HELE RAEKKEN ER KLIKBAR (issue #573) - hubbens og Issue Boards
    # moenster (build_helpers.row_hit): et klik, tryk eller Enter paa
    # raekken aabner det SAMME Class data-panel som blyanten/View-ikonet, i
    # den aktuelle View/Edit-tilstand. Ikonet ligger oven paa laget og goer
    # kun sit eget. Panelets raekke er markeret (TemplateFill nedenfor).
    hit = row_hit_under_actions(
        "btnFlCRowHit", open_row_panel_fx("ThisItem.RowGuid", f'"{PANEL_CLS_JUMP}"'),
        f'{verb} & " class data of " & ThisItem.FL', cells)
    # Samme raekkehoejde og mellemrum som Rows (issue #468).
    gal = table_gallery("galFlClassRows", '"Rows in the selected class"', VIEW_POS, VIEW_N,
                        cells, "conFlCRow", visible=HAS_CLASSES, gap=VGAP,
                        width=lay.mobile_or(M_CARD_W, C_GAL_W),
                        row_h=V_ROW_H, tpl_h=ROW_TOP_F, extra=[meta, hit])
    # Den aabne raekke staar i trykkets tone - som Materials/Equipment/MP.
    gal.props["TemplateFill"] = (
        f"If(IfError(varFlPanelOpen, false) && ThisItem.RowGuid = varFlDetailRow, "
        f"{C_ROW_PRESSED}, {C_TRANSPARENT})")
    gal.props["TemplateSize"] = lay.mobile_or(C_ROW_H_M, gal.props["TemplateSize"])
    c_mob_h = f"Min({VIEW_N}, {C_ROWS_MAX}) * {C_ROW_H_M}"
    gal.props["Height"] = lay.mobile_or(c_mob_h, gal.props["Height"])
    gal.h = gal.props["Height"]
    gal.props["ShowScrollbar"] = lay.mobile_or(f"{VIEW_N} > {C_ROWS_MAX}", gal.props["ShowScrollbar"])
    # Vandret scroll, naar tabellen er bredere end kortet - som Rows'
    # conFlTable (issue #356).
    c_wide = f"({ROWS_W}) < ({C_W})"
    mobile.hide_on_mobile(head)
    rule = mobile.hide_on_mobile(divider("conFlClsRule", HAS_CLASSES, width=C_GAL_W))
    table = group("conFlClsTable", [head, rule, gal],
                  direction="Vertical", gap=10, overflow_x="Scroll", align_items="Start",
                  visible=HAS_CLASSES)
    table.props["Height"] = lay.mobile_or(
        c_mob_h, f"{table.props['Height']} + If({c_wide}, {SCROLLBAR_W}, 0)")
    table.h = table.props["Height"]
    empty = text_ctrl("txtFlNoClassRows",
                      '"No classified rows yet - a row appears here once its Functional Location is valid."',
                      size=13, color=C_MUTED, height=20, wrap="false",
                      visible=f"!({HAS_CLASSES})")
    # Classes er klappet sammen som standard paa alle skaermbredder (issue
    # #533, CLASSES_OPEN ovenfor) - med den chevron, telefonen allerede
    # brugte (mobile.collapsible). Titlen staar i chevronlinjen. Chevronen
    # staar fast yderst til hoejre, og hele linjen klapper ud og sammen
    # (issue #548, mobile.fold_head).
    #
    # OVERSKRIFTEN STAAR ALTID OEVERST (issue #559). Udfoldet stod titel og
    # chevron nederst - under fanerne og tabellen. Nu har kortet praecis TO
    # boern i fast raekkefoelge: overskriften (conFlClassesFoldHead) og
    # kroppen (conFlClassesBody, en lodret container med faner, note, tabel
    # og "No classified rows yet ..."). Kroppen er kun synlig, mens Classes
    # er aaben, og hverken tabellen eller den tomme tekst kan komme foran
    # overskriften - de ligger alle inde i kroppen, under den.
    body = group("conFlClassesBody", [tabs, note, table, empty], direction="Vertical", gap=10)
    # Hoejden: enten faner + note + tabel, eller den ene tomme linje - aldrig
    # begge (stack_height regner med, at det foerste barn altid er synligt).
    from gen_screen import stack_height
    body.props["Height"] = (f"If({HAS_CLASSES}, {stack_height([tabs, note, table], 10)}, "
                            f"{empty.h})")
    body.h = body.props["Height"]
    fold = mobile.collapsible(
        "FlClasses", "Classes", [body], CLASSES_OPEN,
        summary=CLASSES_SUMMARY, size=lay.SIZE_CARD_TITLE, everywhere=True)
    assert [c.name for c in fold] == ["conFlClassesFoldHead", "conFlClassesBody"]
    # Fra Tablet staar opsummeringen lige efter titlen ("Classes . 100 ...");
    # paa telefonen som foer til hoejre for den.
    summary = mobile.find(fold[0], "txtFlClassesFoldSummary")
    assert summary is not None
    summary.props["Text"] = lay.mobile_or(CLASSES_SUMMARY, '"\u00b7  " & ' + CLASSES_SUMMARY)
    summary.props["Align"] = lay.mobile_or("Align.Right", "Align.Left")
    # Opsummeringen staar ved titlen baade lukket og aaben (issue #559) -
    # chevronen er stadig yderst til hoejre (SpaceBetween, issue #548).
    summary.props.pop("Visible", None)
    summary.vis = None
    return card("conFlClassesCard", fold, gap=10)


# ---------------------------------------------------------------------------
# Felterne bag raekkens knapper (issue #184, #232, #278, #346)
#
# Class data, Manufacturer og Warranty i Rows og Edit i Classes aabner
# ALLE raekkens sidepanel (build_row_panel) med knappens felter oeverst
# (PANEL_FOCUS). Der er ingen egne popupper laengere - Class data-popuppen
# er fjernet (issue #346).
# Hvilke felter der er hvor, er Section i colFlColumns (harnessens
# buildPlan), og editoren er Kind (generate_app_onstart.editor_kind).
# Klassen bestemmes af KKS-koden (FL16-FL23) - ingen overstyring.
# ---------------------------------------------------------------------------
# Klassens felter (Class data-knappens udfyldt-tilstand) og den laaste
# anmodning.
CLS_TEST = 'Section in ["Class", "TRM"]'
CLS_LOCKED = 'varFlViewOnly || varFlStatus = "Indsendt"'
# Classes' View-ikon (issue #533): et ikon, appen allerede bruger paa
# ModernButton - "DocumentText" (Long text: laes teksten). Oejet (icons.EYE)
# findes kun som SVG i View mode-pillen, ikke som ModernButton-ikon.
# Issue #551: det er nu det faelles icons.FLUENT["view"].
CLS_VIEW_ICON = icons.FLUENT["view"]


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

# Datofelternes format (issue #356): Warranty Start/End GEMMES som tekst
# DD.MM.YYYY (FL34, fl_validation.date_bad), og datovaelgeren viser dem i
# samme form - ikke appens faelles dd-mm-yyyy (layout_tokens.DATE_FMT).
FL_DATE_FMT = "dd.mm.yyyy"


def date_of_text(v):
    """Den gemte tekst DD.MM.YYYY som dato - tom eller ugyldig: ingen dato
    (feltets besked siger saa "Use DD.MM.YYYY.")."""
    bad = V.date_bad("wv").replace(chr(10), " ")
    return (f"With({{ wv: Trim({v}) }}, If(IsBlank(wv) || {bad}, Blank(), "
            f"Date(Value(Right(wv, 4)), Value(Mid(wv, 4, 2)), Value(Left(wv, 2)))))")


def text_of_date(d):
    """Datoen som tekst DD.MM.YYYY - bygget af tallene, saa sprog og
    landeformat aldrig aendrer den gemte vaerdi. Ingen dato: tom."""
    return (f'If(IsBlank({d}), "", Text(Day({d}), "00") & "." & '
            f'Text(Month({d}), "00") & "." & Text(Year({d}), "0000"))')


# En kort hjaelp under feltet, naar det ikke har en besked. KKS type og
# Assigned class har ingen (issue #308) - de regnes stadig af KKS-koden.
FIELD_HELP = ('Switch(ThisItem.Field, '
              '"ABC INDIC.", "Set automatically from the TRM fields.", '
              '"TRM ASSIGNMENT", "Set automatically from the TRM fields.", '
              '"WARRANTY START", "Format DD.MM.YYYY", '
              '"WARRANTY END", "Format DD.MM.YYYY", '
              '"")')


def _set_detail(value):
    """Fold-ud-sektionens felter skriver direkte i raekkens data."""
    return set_val_fx("varFlDetailRow", "ThisItem.Field", value)


def _live(ctrl):
    """Panelets felter: vaerdi og besked laeses direkte (PANEL_VALUE,
    PANEL_ISSUE) i stedet for fra samlingens kopi (issue #278).

    ItemDisplayText springes over: dens ThisItem er dropdownens EGEN
    listepost, og egenskaben maa kun bruge den (ingen LookUp, samlinger
    eller variabler) - ellers afviser compile den (issue #300)."""
    for k, v in list(ctrl.props.items()):
        if isinstance(v, str) and not k.startswith("On") and k != "ItemDisplayText":
            ctrl.props[k] = (v.replace("ThisItem.Value", f"({PANEL_VALUE})")
                             .replace("ThisItem.Issue", f"({PANEL_ISSUE})"))
    for c in ctrl.children:
        _live(c)


def field_grid(tag, section_test, label, source="colFlDet", set_fx=_set_detail, cols=None,
               items=None, live=False):
    """Et gitter af felter fra source (colFlDet eller popuppens kopi). Hvert
    felt: etiket, editor (efter Kind) og en linje med beskeden - eller en
    kort hjaelp. live: sidepanelet - vaerdi og besked laeses direkte."""
    cols = cols or FORM_COLS
    items = items or f"Filter({source}, {section_test})"
    n = f"CountRows({items})"
    w = "Parent.Width"
    lbl = text_ctrl(f"txtFl{tag}Lbl",
                    'ThisItem.Column & If(ThisItem.Field = "DESCRIPTION", " *", "")',
                    size=12, color=C_MUTED, weight="Semibold", height=18, wrap="false")
    txt = text_input(f"inpFl{tag}Val", "ThisItem.Value", width=w, display_mode=DM_EDIT,
                     label="ThisItem.Column",
                     onchange=set_fx("Self.Text"))
    txt.props["MaxLength"] = "If(ThisItem.MaxLen > 0, ThisItem.MaxLen, 4000)"
    txt.props["BorderColor"] = _field_border("!IsBlank(ThisItem.Issue)", "!IsBlank(ThisItem.Value)")
    txt.vis = 'ThisItem.Kind = "text"'
    # Datofelterne (Warranty Start/End): appens datovaelger (issue #356).
    # Vaerdien gemmes stadig som tekst DD.MM.YYYY i colFlVals - samme felt,
    # samme validering (FL34) - kun editoren er en kalender.
    dte = date_picker(f"dteFl{tag}Val", date_of_text("ThisItem.Value"), width=w,
                      display_mode=DM_EDIT, label="ThisItem.Column",
                      onchange=set_fx(text_of_date("Self.SelectedDate")),
                      fmt=FL_DATE_FMT)
    dte.props["BorderColor"] = _field_border("!IsBlank(ThisItem.Issue)", "!IsBlank(ThisItem.Value)")
    dte.vis = 'ThisItem.Kind = "date"'
    dd = themed_dropdown(f"drpFl{tag}Val", DD_ITEMS,
                         f"LookUp({DD_ITEMS}, Upper(Value) = Upper(ThisItem.Value)).Value",
                         width=w, display_mode=DM_EDIT, label="ThisItem.Column")
    dd.props["OnChange"] = set_fx("Coalesce(Self.Selected.Value, \"\")")
    dd.props["BorderColor"] = _field_border("!IsBlank(ThisItem.Issue)", "!IsBlank(ThisItem.Value)")
    dd.vis = 'ThisItem.Kind = "list"'
    # X-felterne (Atex, TRM assignment): afkrydsning,
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
    # Telefonen (issue #508): felterne er 44 px hoeje (touch), og flisen har
    # ingen luft til hoejre - der er kun een kolonne (PANEL_COLS).
    for c in (txt, dte, dd, chk, ro):
        c.props["Height"] = lay.mobile_or(mobile.TOUCH, c.props["Height"])
        c.h = c.props["Height"]
    # Bredden paa telefonen: panelets formular (lay.PANEL_INNER_W) minus de
    # 8 px, et galleri uden scrollbar holder fri paa mobil - ikke den
    # usikre kaedes GALLERY_RESERVE (40 px tabt i hver linje).
    for c in (lbl, txt, dte, dd, chk, ro, issue):
        mobile.gallery_place(c, w=f"App.Width - {2 * lay.MOBILE_PAD_X} - {SCROLLBAR_W} - 8")
    tile = group(f"conFl{tag}Tile", [lbl, txt, dte, dd, chk, ro, issue], direction="Vertical", gap=2,
                 width="Parent.TemplateWidth", height="Parent.TemplateHeight",
                 pad=(0, TILE_GAP, 10, 0))
    mobile_pad(tile, right=0)
    if live:
        _live(tile)
    tile_h = lay.mobile_or(TILE_H + mobile.TOUCH - 36, TILE_H)
    gal_h = f"RoundUp({n} / ({cols}), 0) * ({tile_h})"
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
        "TemplateSize": tile_h,
        "Visible": vis,
        "Width": "Parent.Width",
        "WrapCount": cols,
    }, children=[tile], h=gal_h, vis=vis)
    return gal


# ---------------------------------------------------------------------------
# New request (FL70). Save draft, Submit og New request staar i bjaelken.
# ---------------------------------------------------------------------------
# "Tom skaerm": de samlinger, der hoerer til EEN anmodning. Bruges af "New
# request" og af BIO SAP's klargoering (assemble_screen.reset_part, R2-003),
# saa der kun er een liste.
RESET_FX = """Clear(colFlRows);
Clear(colFlDeleted);
Clear(colFlCopies);
Clear(colFlVals);
Clear(colFlIssues);
Clear(colFlIssuesRaw);
Clear(colFlTabs);
Clear(colFlDet);
Clear(colFlPanelSnap);
Clear(colFlPanelSnapVals);
// Issue #533: en anden anmodning aabnes med Classes lukket og uden
// "Unsaved changes".
Set(varFlClassesOpen, false);
Set(varFlDirty, false)"""

NEW_FX = RESET_FX + """;
Set(varFlAct, "");
Set(varFlRequestGuid, "");
Set(varFlRequestNo, "");
Set(varFlStatus, "");
Set(varFlViewOnly, false);
Set(varFlCanEdit, false);
Set(varFlTab, "ALL");
Set(varFlDetailRow, "");
Set(varFlPanelOpen, false);
Set(varFlPanelJump, "");
Set(varFlSubmitAsk, false);
Set(varFlStale, false);
Set(varFlNextRowNo, 1);
""" + add_row_fx() + """;
Set(varFlInfo, "");
Select(btnFlVerify)"""


def build_submit_confirm():
    """Bekraeftelsen foer Submit og ventespinneren (issue #54).
    [sloer, popup, spinner] - SIDST i skaermens boern."""
    return confirm_modal(
        "Fl", "varFlConfirmSubmit", "Submit request?",
        # Issue #533: Submit gemmer og indsender i een handling (S.submit_fx) -
        # Save draft foerst er ikke noedvendigt.
        '"The request is saved and submitted in one step. A JSON snapshot is frozen and the rows are locked."',
        "Submit", SUBMIT_FX, "btnFlSubmitConfirm", msg_height=60) + delete_modal(
        "Fl", "varFlRequestGuid", cfg.L_INDEX, cfg.DOMAIN) + [
        # Mens der gemmes: Save draft/Submit viser det selv (issue #420) -
        # et gennemsigtigt lag, intet sloer og ingen bjaelke.
        *act_layers("Fl", ACT)]


# ---------------------------------------------------------------------------
# PASTE ROWS FROM EXCEL (UX-review L3)
#
# To kolonner fra Excel - funktionsplads og beskrivelse, adskilt af
# tabulator - bliver hver sin raekke i tabellen. Raekkerne er kun lokale,
# til Save draft, og valideringen koerer bagefter, saa hver raekke viser
# sine fejl som en raekke, der er tastet. Tomme, ugemte raekker fjernes
# foerst, saa den tomme startraekke ikke staar tilbage.
# ---------------------------------------------------------------------------
PASTE_OPEN = 'Set(varFlPasteText, "");\nReset(inpFlPaste);\nSet(varFlPasteOpen, true)'
PASTE_LINES = ('Filter(Split(Substitute(Coalesce(varFlPasteText, ""), Char(13), ""), Char(10)), '
               '!IsBlank(Trim(Value)) && Upper(Trim(First(Split(Value, Char(9))).Value)) '
               '<> "FUNCTIONAL LOCATION")')


def _paste_add_fx():
    cell = 'IfError(Index(Split(Index(lines, Value).Value, Char(9)), {i}).Value, "")'
    return (
        f"With(\n    {{ lines: {PASTE_LINES} }},\n"
        # Raekkeloftet (R2-043): de tomme, ugemte raekker fjernes alligevel
        # og taeller ikke med. Over loftet bliver popuppen staaende.
        "If(\n"
        f"    CountRows(Filter(colFlRows, !(SpId = 0 && IsBlank(FL) && IsBlank(Description)))) + CountRows(lines) > {MAX_ROWS},\n"
        f'    Notify("{MAX_ROWS_MSG}", NotificationType.Error),\n'
        "    RemoveIf(colFlRows, SpId = 0 && IsBlank(FL) && IsBlank(Description));\n"
        # Een Collect med hele tabellen, ikke en pr. linje (regel 15, issue #342).
        "    Collect(\n"
        "        colFlRows,\n"
        "        ForAll(Sequence(CountRows(lines)), { RowGuid: Text(GUID()), RowNo: varFlNextRowNo + Value - 1, SpId: 0, "
        f"FL: {norm_fl(cell.format(i=1))}, Description: Upper(Trim({cell.format(i=2)})), "
        'KksType: "", AssignedClass: "", Status: "draft", FirstIssue: "", FirstWarning: "", '
        'IssueCount: 0, WarningCount: 0, Pos: 0, FlBad: false, DescBad: false, Hint: "" })\n'
        "    );\n"
        "    Set(varFlNextRowNo, varFlNextRowNo + CountRows(lines));\n"
        '    Notify(Text(CountRows(lines)) & " rows added. Check the messages on each row.", '
        "NotificationType.Success);\n"
        '    Set(varFlPasteOpen, false);\n    Set(varFlPasteText, "");\n'
        f"    {MARK_DIRTY};\n"
        "    " + REVERIFY.replace("\n", "\n    ") + "\n"
        ")\n)")


def build_paste():
    """Popuppen "Paste rows" - [sloer, popup]."""
    from build_helpers import popup_head, tap_backdrop, popup_body_max, capped_body, mobile_footer
    vis = "IfError(varFlPasteOpen, false)"
    close = "Set(varFlPasteOpen, false)"
    backdrop = tap_backdrop("conFlPasteBackdrop", vis, close)
    title = text_ctrl("txtFlPasteTitle", '"Paste rows"', size=lay.SIZE_CARD_TITLE,
                      weight="Semibold", height=26, wrap="false")
    head = popup_head("conFlPasteHead", title, "btnFlPasteClose", close)
    # Telefonen (issue #508): kortere hjaelp og et lavere felt, saa Add rows
    # kan ses over tastaturet; popuppen staar oeverst i (naesten) fuld bredde.
    help_txt = lay.mobile_or('"Paste two Excel columns: functional location and description."',
                             '"Copy two columns in Excel and paste them here, one row per line: '
                             'the functional location and the description."')
    help_ = text_ctrl("txtFlPasteHelp", help_txt, size=13, color=C_MUTED, height=40, wrap="true",
                      accessible=help_txt)
    inp = text_input("inpFlPaste", 'Coalesce(varFlPasteText, "")', height=lay.mobile_or(120, 160),
                     ttype="Multiline",
                     placeholder='"Paste from Excel"', label='"Rows to paste"',
                     onchange="Set(varFlPasteText, Self.Text)")
    n = f"CountRows({PASTE_LINES})"
    add = button("btnFlPasteAdd", f'If({n} = 0, "Add rows", "Add " & Text({n}) & " rows")',
                 _paste_add_fx(), primary=True, icon="Add",
                 width=fit_button_width('"Add 00 rows"') + ICON_W, height=36,
                 display_mode=f"If({n} = 0, DisplayMode.Disabled, DisplayMode.Edit)")
    footer = group("conFlPasteFooter", [add], direction="Horizontal", gap=8,
                   height=36, justify="End", align_items="Center")
    mobile_footer(footer)
    body = capped_body("conFlPasteBody", [help_, inp], f"{popup_body_max([head.h, 0])} - ({footer.h})")
    modal = group("conFlPasteModal", [head, body, footer], direction="Vertical",
                  gap=12, fill=C_MODAL_BG, border_color=C_PRIMARY_SOFT, radius=lay.RADIUS_MODAL,
                  pad=(18, 18, 18, 18), width="Min(560, App.Width - 24)",
                  drop_shadow="ExtraBold", visible=vis)
    modal.props["X"] = "(App.Width - Self.Width) / 2"
    modal.props["Y"] = "Max(12, (App.Height - Self.Height) / 3)"
    mobile.mobile_popup(modal, top=True)
    return [backdrop, modal]
