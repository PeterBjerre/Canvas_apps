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
                        C_PRIMARY, C_TRANSPARENT, C_MODAL_BG, C_PRIMARY_SOFT,
                        C_BORDER_OK, C_BORDER_ERROR, C_INVALID_FG, C_WARN_FG, C_VALID_FG,
                        C_CARD_BG, C_DIVIDER)
from design_tokens import ref_hex
import layout_tokens as lay
from progress_overlay import progress_overlay
from layout_tokens import SCROLLBAR_W, GALLERY_RESERVE, at_least, below
import icons
from build_helpers import (C_INPUT_BORDER, ensure_hit, checkbox_theme, new_request_label, request_actions, breadcrumb, text_ctrl, group, button, text_input, themed_dropdown, card, date_picker,
                           pin_widths, top_bar, grow, fit_button_width, row_rule, mark_done,
                           with_busy, confirm_modal, delete_button, delete_modal, ICON_SAVE, ICON_SUBMIT,
                           ICON_W, text_px, stable_scrim, icon_button, icon_heading, editor_footer,
                           panel_save_fx, panel_save_mode, panel_save_status, panel_save_space,
                           panel_save_block)

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


def add_row_fx():
    """FL63: en ny, tom raekke. Alle felter staar i raekken eller bag
    dens popup-knapper - der er intet at folde ud (issue #232)."""
    return ("Collect(colFlRows, { RowGuid: Text(GUID()), RowNo: varFlNextRowNo, SpId: 0, "
            "FL: \"\", Description: \"\", KksType: \"\", AssignedClass: \"\", Status: \"draft\", "
            "FirstIssue: \"\", FirstWarning: \"\", IssueCount: 0, WarningCount: 0, "
            "Pos: 0, FlBad: false, DescBad: false, Hint: \"\" });\n"
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


# FL62: validering er AUTOMATISK (issue #77) - der er ingen Verify-knap.
# Formlen staar KUN i den skjulte btnFlVerify (build_rows), og hver
# aendring - ny raekke, rettet felt, slettet raekke, indlaest anmodning -
# kalder den. Den er lokal Power Fx mod de navngivne formler (nf*), saa
# den koster ingen kald til SharePoint eller flows.
REVERIFY = "Set(varFlStale, true);\nSelect(btnFlVerify)"


def delete_row_fx(guid):
    """Raekken guid fjernes lokalt; Save draft sletter den i SharePoint
    (colFlDeleted, fl_save trin 3). Den sidste raekke afloeses af en tom."""
    return f"""Collect(colFlDeleted, {{ RowGuid: {guid} }});
Remove(colFlRows, LookUp(colFlRows, RowGuid = {guid}));
RemoveIf(colFlVals, RowGuid = {guid});
RemoveIf(colFlIssues, RowGuid = {guid});
If(CountRows(colFlRows) = 0, {add_row_fx()});
{REVERIFY}"""


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
    """Under Desktop er bjaelkens knapper kun deres ikon, saa alle tre kan
    staa ved siden af titlen - ingen af dem skjules (issue #392)."""
    w = btn.props["Width"]
    btn.props["Width"] = f"If({NARROW}, 40, {w})"
    btn.props["Layout"] = f"If({NARROW}, ButtonLayout.IconOnly, ButtonLayout.IconBefore)"
    return btn


# Save draft - og panelets Save, som er det samme gem (issue #308).
SAVE_DM = (f'If(varFlViewOnly || varFlStatus = "Indsendt" || CountRows({S.LIVE}) = 0, '
           f'DisplayMode.Disabled, DisplayMode.Edit)')

def build_bar():
    """Save draft, Submit og New request staar dér, hvor Verify og Export
    JSON stod (issue #77). Valideringen koerer af sig selv (REVERIFY), og
    eksporten er vaek - snapshottet fryses stadig ved Submit (payload_fx).
    Tallene er renderMetrics (FL66)."""
    save = _fit(button("btnFlSaveDraft", '"Save draft"', with_busy("varFlSaving", S.save_fx()),
                       icon=ICON_SAVE, display_mode=SAVE_DM), icon=True)
    save.props["Tooltip"] = ('"Puts the request on the landing page as Draft - '
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
    # SAMME RAEKKEFOELGE SOM ALLE DOMAENER (UX-review T1):
    # [New request] | [Edit] [Save draft] [Submit (N to fix)] [Delete].
    # Taelleren er raekkerne med fejl (renderMetrics, S.ERRS).
    actions = request_actions("Fl", new, save, submit, fix_expr=S.ERRS, extra=[edit])
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
    # Temaskiftet og vejen til hubben staar i sidebaren (tools/side_nav.py).
    bar = top_bar("Fl", f'"{cfg.TITLE}"', SUBTITLE,
                  actions + [delete_button("Fl", "varFlViewOnly", "varFlRequestGuid")],
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


class Cols:
    """Kolonnebredderne for Classes-tabellen - de SAMME udtryk i
    overskriften og i raekken, saa de altid flugter (check_layout regel 29).

    #, Functional Location og Description er RAEKKERNES (issue #356):
    bredde, mellemrum og synlighed kommer fra V_SPEC, saa de samme felter
    staar lige under hinanden i Rows og Classes. Resten foelger efter:
      - de to midterste kolonner skjules, naar Info ikke kan faa 160 px ved
        siden af dem;
      - Info faar resten, mindst VAL_MIN;
      - er tabellen bredere end kortet (smal skaerm), scroller den vandret
        i kortet - som Rows. Intet klippes eller laegges oven i hinanden."""

    def __init__(self, mid, act_w, lead, gap):
        self.mid = mid                      # [(navn, overskrift, bredde)]
        self.lead = lead                    # Rows' #, FL og Description
        self.gap = gap
        self.act = str(act_w)
        mid_sum = sum(w + gap for _n, _l, w in mid)
        # #, FL, Description og mellemrummene efter dem; Info-Open-mellemrum
        # og Open. Det, der er tilbage, deles af midten og Info.
        before = " + ".join(f"If({vis}, {w} + {gap}, 0)" if vis is not None
                            else f"({w}) + {gap}" for _n, _l, w, vis in lead)
        after = f"{gap} + {act_w}"
        free = f"({ROWS_W}) - ({before}) - ({after})"
        self.show_mid = f"({free}) >= {mid_sum} + 160"
        self.rest = f"Max({VAL_MIN}, ({free}) - If({self.show_mid}, {mid_sum}, 0))"
        # Tabellens bredde: kortets, eller mere, naar # + FL + Description
        # + Info-minimum + Open ikke kan staa i det (vandret scroll).
        self.width = f"Max({ROWS_W}, ({before}) + {VAL_MIN} + {after})"

    def spec(self, rest_name, rest_label, act_name, act_label):
        """(navn, overskrift, bredde, synlig) i raekkefoelge."""
        return (list(self.lead)
                + [(n, l, w, self.show_mid) for n, l, w in self.mid]
                + [(rest_name, rest_label, self.rest, None),
                   (act_name, act_label, self.act, None)])


def table_head(name, spec, gap=GAP, width="Parent.Width"):
    """Kolonneoverskrifterne og stregen under dem (Masterdata Hub's
    moenster, issue #70)."""
    head = group(name,
                 pin_widths([text_ctrl(f"txt{name[3:]}{n}", f'"{lbl}"', size=11, color=C_MUTED,
                                       weight="Semibold", height=18, width=w, wrap="false",
                                       visible=vis)
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
V_BASE_MAX = 1258
# (navn, overskrift, bredde) efter Description. Delete er et ikon.
# Class Data staar lige efter Assigned Class (issue #242).
V_FIXED = ([("Kks", "KKS type", 64), ("Cls", "Assigned class", 96),
            ("ClsData", "Class data", _pop_w("Class data"))]
           # Reglernes etiket ("Sort Field") i appens sentence case (F1).
           + [(n, _NO_CLASS[f]["Column"][:1] + _NO_CLASS[f]["Column"][1:].lower(), w)
              for n, f, w in ROW_VALS]
           + [("Abc", "ABC indicator", 88), ("Atex", "ATEX", 40),
              ("Mfr", "Manufacturer", MFR_WAR_W),
              ("War", "Warranty", MFR_WAR_W),
              ("Status", "Status", 80),
              # "Actions" er 47 px i 11 px - knappen er et ikon.
              ("Act", "Actions", 48)])
# Description faar det, der er tilbage af V_BASE_MAX - men aldrig mindre end
# sin overskrift plus feltets padding.
DESC_MIN = (V_BASE_MAX - FL_MIN - sum(w for _n, _l, w in V_FIXED)
            - VGAP * (len(V_FIXED) + 1))
assert DESC_MIN >= text_px("Description", 11) + 24, DESC_MIN
V_SHOW_NO = at_least("Tablet")
# Raekkens mindste bredde: # (fra Tablet), FL, Description, resten og
# mellemrummene. Er kortet smallere, scroller TABELLEN vandret i kortet
# (som Equipment/Materials' raekker) - intet skjules, klippes eller
# laegges oven i hinanden.
V_BASE = FL_MIN + DESC_MIN + sum(w for _n, _l, w in V_FIXED) + VGAP * (len(V_FIXED) + 1)
V_MIN = f"(If({V_SHOW_NO}, {28 + VGAP}, 0) + {V_BASE})"
V_SPARE = f"Max(0, ({ROWS_W}) - {V_MIN})"
V_W = f"Max({ROWS_W}, {V_MIN})"
# DEN EKSTRA PLADS DELES AF ALLE KOLONNER, DER KAN BRUGE DEN (issue #242).
# Foer fik Functional Location og Description hver halvdelen - paa en
# 1920 px skaerm 421 og 381 px, med et stort tomt felt. Nu faar de hver
# V_PAIR_SHARE af den (omtrent halvdelen af den gamle bredde), og resten
# deles ligeligt af kolonnerne i V_GROW. ATEX (afkrydsning) og Actions
# (ikon) har fast bredde. Andelene summer til 1, saa raekken er stadig
# praecis V_W bred, og overskrift og raekke bruger de samme bredder.
V_PAIR_SHARE = "1 / 10"
V_DESC_SHARE = "3 / 20"
V_GROW = ("Kks", "Cls", "Room", "Sort", "Abc")
V_GROW_SHARE = f"3 / {4 * len(V_GROW)}"
assert set(V_GROW) <= {n for n, _l, _w in V_FIXED}


def _v_w(n, w):
    return f"{w} + ({V_SPARE}) * {V_GROW_SHARE}" if n in V_GROW else w


V_SPEC = ([("No", "#", 28, V_SHOW_NO),
           ("Fl", "Functional Location", f"{FL_MIN} + ({V_SPARE}) * {V_PAIR_SHARE}", None),
           ("Desc", "Description", f"{DESC_MIN} + ({V_SPARE}) * {V_DESC_SHARE}", None)]
          + [(n, l, _v_w(n, w), None) for n, l, w in V_FIXED])
V_GAL_W = f"({V_W}) + {SCROLLBAR_W} + {GALLERY_RESERVE}"
V_WIDE = f"({ROWS_W}) < {V_MIN}"

ROW_TOP = 40
# Delete er en ikonknap med klikfladen H.hit (UX-review F6, regel 40):
# under Desktop er cellelinjen 44 hoej, og resten af raekken rykker
# TOUCH_EXTRA (0 fra Desktop, 4 under) ned.
ROW_TOP_F = f"Max({ROW_TOP}, {lay.HIT})"
TOUCH_EXTRA = f"({ROW_TOP_F} - {ROW_TOP})"
V_ROW_H = f"{ROW_H} + {TOUCH_EXTRA}"

ERRS = 'CountRows(Filter(colFlRows, Status = "invalid"))'

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


def verify_button():
    """HELE valideringen - skjult. Alle aendringer kalder den med
    Select(btnFlVerify) (REVERIFY, docs/31 PX7). Select virker paa en
    skjult knap; den skal bare staa paa samme skaerm."""
    b = button("btnFlVerify", '"Verify"',
               V.verify_fx(PANEL_REFRESH, after=S.submit_after_verify()),
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
    desc = text_input("inpFlRowDesc", "ThisItem.Description", max_length=40, width="140",
                      display_mode=DM_EDIT, label='"Description"',
                      onchange=set_row_fx("ThisItem.RowGuid", "Description", "Trim(Self.Text)"))
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
    cls_data = _pop_button(
        "btnFlRowClassData", "Class data", open_row_panel_fx("ThisItem.RowGuid", f'"{PANEL_CLS_JUMP}"'),
        f"{has_cls} && " + has_vals(
            "ThisItem.RowGuid",
            f"Filter(colFlColumns, Cls = ThisItem.AssignedClass && {CLS_TEST}).Field"),
        '"Class data of row " & ThisItem.Pos',
        (f'If({has_cls}, "Edit the class characteristics and TRM fields of this row", '
         '"Valid FL first - the class is determined by the KKS code of a valid Functional Location.")'),
        f"If({has_cls}, DisplayMode.Edit, DisplayMode.Disabled)")
    pops = [cls_data]
    for name, kind, fields, tip in (
            ("btnFlRowMfr", "Manufacturer", MFR_FIELDS,
             "Manufacturer, Model Number, Manufacturer Part Number and Manufacturer Serial Number"),
            ("btnFlRowWar", "Warranty", WAR_FIELDS, "Warranty Start and Warranty End")):
        has = has_vals("ThisItem.RowGuid", _fields(fields))
        # Som Long Text: laast og tom = deaktiveret; ellers kan den aabnes
        # (i View kun til at laese).
        pops.append(_pop_button(
            name, kind, open_row_panel_fx("ThisItem.RowGuid", f'"{PANEL_JUMP[kind]}"'), has,
            f'"{kind} of row " & ThisItem.Pos', f'"{tip}"',
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
                    accessible='"Delete row " & ThisItem.Pos', tooltip='"Delete row " & ThisItem.Pos')
    delete.props["Layout"] = "ButtonLayout.IconOnly"
    ensure_hit(delete, square=False)
    # Samme raekkefoelge som V_FIXED: Class data lige efter Assigned Class.
    return _cells(V_SPEC, [no, fl, desc, kks, cls, pops[0]] + vals + [abc, atex]
                  + pops[1:] + [status, delete])


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
    """Assigned class: raekkens klasse, kun til visning."""
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
#   Reset   raekken tilbage til aftrykket - spoerger foerst, hvis der er
#           aendret noget (Materials' "Discard unsaved changes?").
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
{REVERIFY}"""
PANEL_LOCKED = 'varFlViewOnly || varFlStatus = "Indsendt"'
PANEL_DM = f"If({PANEL_LOCKED}, DisplayMode.Disabled, DisplayMode.Edit)"


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
            "Set(varFlPanelOpen, true)")


def _panel_grid(key, label, cols):
    items = f'Sort(Filter(colFlDet, Pane = "{key}"), PaneOrd)'
    return field_grid(f"Panel{key}", f'Pane = "{key}"', label, cols=cols, items=items, live=True)


def _panel_section(key, title):
    fields = [_panel_grid(key, f'"{title}"', PANEL_COLS)]
    sub = cfg.PANEL_SUB.get(key)
    if sub:
        # KKS type og Assigned class paa een linje (issue #308).
        fields.append(_panel_grid(sub, f'"{title} - KKS type and assigned class"', PANEL_SUB_COLS))
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
    return group(f"conFlPanel{key}", [heading] + fields, direction="Vertical",
                 gap=PANEL_HEAD_GAP, visible=vis)


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
PANEL_FORM_W = f"({lay.PANEL_W_AT}) - 2 * {PANEL_PAD} - 2 * {PANEL_PAD} - {SCROLLBAR_W}"
PANEL_COL_MIN = 200
# 3 kolonner naar de kan faa PANEL_COL_MIN hver, ellers 2, ellers 1.
PANEL_COLS = (f"If(({PANEL_FORM_W}) >= 3 * {PANEL_COL_MIN}, 3, "
              f"If(({PANEL_FORM_W}) >= 2 * {PANEL_COL_MIN}, 2, 1))")
# KKS type + Assigned class: side om side, og under hinanden (KKS type
# foerst), naar to kolonner ikke kan faa PANEL_COL_MIN hver.
PANEL_SUB_COLS = f"If(({PANEL_FORM_W}) >= 2 * {PANEL_COL_MIN}, 2, 1)"
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
    reset = button("btnFlEditorReset", '"Reset"', f"If({PANEL_DIRTY}, Set(varFlPanelResetAsk, true))",
                   width=fit_button_width('"Reset"'), height=lay.HIT_TOUCH, display_mode=PANEL_DM,
                   tooltip='"Undo the changes made to this row since it was opened"')
    cancel = button("btnFlEditorCancel", '"Cancel"',
                    f"If(\n    {PANEL_DIRTY},\n    {PANEL_RESTORE.replace(chr(10), chr(10) + '    ')}\n);\n"
                    f"{CLOSE_PANEL_FX}",
                    width=fit_button_width('"Cancel"'), height=lay.HIT_TOUCH)
    save = button("btnFlEditorSave", '"Save"', PANEL_SAVE_FX,
                  primary=True, width=PANEL_SAVE_W, height=lay.HIT_TOUCH,
                  display_mode=panel_save_mode(PANEL_SAVE, SAVE_DM), icon='"Save"',
                  tooltip='"Save the request with this row and close the panel"')
    save.props["AccessibleLabel"] = "Self.Text"
    return editor_footer("Fl", delete, reset, cancel, save)


def _panel_confirms():
    """Delete row og Reset spoerger foerst - som Materials."""
    pos = 'Text(LookUp(colFlRows, RowGuid = varFlDetailRow).Pos)'
    delete = confirm_modal(
        "FlRowDel", "varFlPanelDelAsk", "Delete row?",
        f'"Row " & {pos} & " is removed from the request. Save the request to delete it in SharePoint too."',
        "Delete", delete_row_fx("varFlDetailRow") + ";\n" + CLOSE_PANEL_FX,
        "btnFlRowDelConfirm", icon="Delete")
    reset = confirm_modal(
        "FlRowReset", "varFlPanelResetAsk", "Discard unsaved changes?",
        '"The row returns to how it was when you opened it. Other rows and the request are not changed."',
        "Reset", PANEL_RESTORE, "btnFlRowResetConfirm", icon=None, danger=True)
    return delete + reset


def build_rows():
    # "Rows" og hvor mange der er gyldige (UX-review F1/T7 og FL Spool):
    # kortet hed "Validation".
    title = text_ctrl("txtFlRowsH", '"Rows"', size=lay.SIZE_CARD_TITLE, weight="Semibold",
                      height=26, wrap="false", width=text_px("Rows", lay.SIZE_CARD_TITLE))
    count = grow(text_ctrl("txtFlRowsCount",
                           f'Text({S.READY}) & " of " & Text(CountRows(colFlRows)) & " valid"',
                           size=13, color=C_MUTED, height=20, wrap="false"))
    add = _fit(button("btnFlAddRow", '"Add row"', capped_add_row_fx(),
                      display_mode=DM_EDIT, icon="Add", primary=True), icon=True)
    paste = _fit(button("btnFlPasteRows", '"Paste rows"', PASTE_OPEN,
                        display_mode=DM_EDIT, icon=icons.FLUENT["paste"],
                        tooltip='"Paste functional locations and descriptions copied from Excel"'),
                 icon=True)
    head_row = group("conFlRowsTop", pin_widths([title, count, paste, add]), direction="Horizontal",
                     gap=12, align_items="Center")

    head = table_head("conFlRowsHead", V_SPEC, gap=VGAP, width=V_GAL_W)
    gal = table_gallery("galFlRows", '"Functional Location rows"',
                        "Sort(colFlRows, RowNo)", "CountRows(colFlRows)", row_cells(), "conFlRow",
                        row_h=V_ROW_H, gap=VGAP, width=V_GAL_W, tpl_h=ROW_TOP_F)
    # Vandret scroll, naar tabellen er bredere end kortet (Equipment/
    # Materials' moenster, domain_parts). Start, ikke Stretch - check_layout
    # regel 14. Den vandrette scrollbar tager hoejde, saa den laegges til.
    table = group("conFlTable", [head, divider("conFlRowsRule", width=V_GAL_W), gal],
                  direction="Vertical", gap=10, overflow_x="Scroll", align_items="Start")
    table.props["Height"] = f"{table.props['Height']} + If({V_WIDE}, {SCROLLBAR_W}, 0)"
    table.h = table.props["Height"]

    # Kun noget at sige, naar der ER noget: en fejl ved gem/indsend, eller
    # raekker, der blokerer Submit. Ingen "Ready."/"Done." (issue #77).
    info = text_ctrl("txtFlInfo",
                     "varFlInfo",
                     size=12, color=C_INVALID_FG, height=18, wrap="false",
                     visible="!IsBlank(varFlInfo)")
    return card("conFlRowsCard", [head_row, table, info, verify_button()], gap=10)

# ---------------------------------------------------------------------------
# Klassefanerne (functional-location.html:77-81, FL28 og FL60)
# ---------------------------------------------------------------------------
# #, Functional Location og Description bruger Rows' bredder (V_SPEC) og
# mellemrum (VGAP), saa kolonnerne flugter med Rows ovenover (issue #356).
CCOLS = Cols([("Str", "StrIndicator", 76), ("Cls", "Class", 96)], act_w=72,
             lead=V_SPEC[:3], gap=VGAP)
C_SPEC = CCOLS.spec("Info", "Info", "Open", "Edit")
C_GAL_W = f"({CCOLS.width}) + {SCROLLBAR_W} + {GALLERY_RESERVE}"

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
                     '"Compact view - Edit opens the class data of the row."',
                     size=12, color=C_MUTED, height=18, wrap="false", visible=HAS_CLASSES)

    head = table_head("conFlClsHead", C_SPEC, gap=VGAP, width=C_GAL_W)
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
    # Edit aabner raekkens sidepanel med klassens felter - samme panel som
    # Class data i Rows (issue #346). Hver post her ER een raekke
    # (V.BUCKETS), saa ThisItem.RowGuid er raekken.
    open_ = button("btnFlCOpen", '"Edit"',
                   open_row_panel_fx("ThisItem.RowGuid", f'"{PANEL_CLS_JUMP}"'), width=72, height=30,
                   accessible='"Edit class data of " & ThisItem.FL')
    cells = _cells(C_SPEC, [no, fl, desc, strc, clsc, info, open_])
    gal = table_gallery("galFlClassRows", '"Rows in the selected class"', VIEW_POS, VIEW_N,
                        cells, "conFlCRow", visible=HAS_CLASSES, gap=VGAP, width=C_GAL_W)
    # Vandret scroll, naar tabellen er bredere end kortet - som Rows'
    # conFlTable (issue #356).
    c_wide = f"({ROWS_W}) < ({CCOLS.width})"
    table = group("conFlClsTable", [head, divider("conFlClsRule", HAS_CLASSES, width=C_GAL_W), gal],
                  direction="Vertical", gap=10, overflow_x="Scroll", align_items="Start",
                  visible=HAS_CLASSES)
    table.props["Height"] = f"{table.props['Height']} + If({c_wide}, {SCROLLBAR_W}, 0)"
    table.h = table.props["Height"]
    empty = text_ctrl("txtFlNoClassRows",
                      '"No classified rows yet - a row appears here once its Functional Location is valid."',
                      size=13, color=C_MUTED, height=20, wrap="false",
                      visible=f"!({HAS_CLASSES})")
    return card("conFlClassesCard",
                [title, tabs, note, table, empty],
                gap=10)


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
    tile = group(f"conFl{tag}Tile", [lbl, txt, dte, dd, chk, ro, issue], direction="Vertical", gap=2,
                 width="Parent.TemplateWidth", height="Parent.TemplateHeight",
                 pad=(0, TILE_GAP, 10, 0))
    if live:
        _live(tile)
    gal_h = f"RoundUp({n} / ({cols}), 0) * {TILE_H}"
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
        "WrapCount": cols,
    }, children=[tile], h=gal_h, vis=vis)
    return gal



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
# "Tom skaerm": de samlinger, der hoerer til EEN anmodning. Bruges af "New
# request" og af BIO SAP's klargoering (assemble_screen.reset_part, R2-003),
# saa der kun er een liste.
RESET_FX = """Clear(colFlRows);
Clear(colFlDeleted);
Clear(colFlVals);
Clear(colFlIssues);
Clear(colFlIssuesRaw);
Clear(colFlTabs);
Clear(colFlDet);
Clear(colFlPanelSnap);
Clear(colFlPanelSnapVals)"""

NEW_FX = RESET_FX + """;
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
        '"A JSON snapshot is frozen and the rows are locked."',
        "Submit", with_busy("varFlSaving", S.submit_fx()), "btnFlSubmitConfirm") + delete_modal(
        "Fl", "varFlRequestGuid", cfg.L_INDEX, cfg.DOMAIN) + [
        *progress_overlay("imgFlSaving", "varFlSaving", "Saving, please wait")]


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
        f"FL: {norm_fl(cell.format(i=1))}, Description: Trim({cell.format(i=2)}), "
        'KksType: "", AssignedClass: "", Status: "draft", FirstIssue: "", FirstWarning: "", '
        'IssueCount: 0, WarningCount: 0, Pos: 0, FlBad: false, DescBad: false, Hint: "" })\n'
        "    );\n"
        "    Set(varFlNextRowNo, varFlNextRowNo + CountRows(lines));\n"
        '    Notify(Text(CountRows(lines)) & " rows added. Check the messages on each row.", '
        "NotificationType.Success);\n"
        '    Set(varFlPasteOpen, false);\n    Set(varFlPasteText, "");\n'
        "    " + REVERIFY.replace("\n", "\n    ") + "\n"
        ")\n)")


def build_paste():
    """Popuppen "Paste rows" - [sloer, popup]."""
    from build_helpers import popup_head, tap_backdrop, popup_body_max, capped_body
    vis = "IfError(varFlPasteOpen, false)"
    close = "Set(varFlPasteOpen, false)"
    backdrop = tap_backdrop("conFlPasteBackdrop", vis, close)
    title = text_ctrl("txtFlPasteTitle", '"Paste rows"', size=lay.SIZE_CARD_TITLE,
                      weight="Semibold", height=26, wrap="false")
    head = popup_head("conFlPasteHead", title, "btnFlPasteClose", close)
    help_ = text_ctrl("txtFlPasteHelp",
                      '"Copy two columns in Excel and paste them here, one row per line: '
                      'the functional location and the description."',
                      size=13, color=C_MUTED, height=lay.if_below("Tablet", 60, 40), wrap="true")
    inp = text_input("inpFlPaste", 'Coalesce(varFlPasteText, "")', height=160, ttype="Multiline",
                     placeholder='"Paste from Excel"', label='"Rows to paste"',
                     onchange="Set(varFlPasteText, Self.Text)")
    n = f"CountRows({PASTE_LINES})"
    add = button("btnFlPasteAdd", f'If({n} = 0, "Add rows", "Add " & Text({n}) & " rows")',
                 _paste_add_fx(), primary=True, icon="Add",
                 width=fit_button_width('"Add 00 rows"') + ICON_W, height=36,
                 display_mode=f"If({n} = 0, DisplayMode.Disabled, DisplayMode.Edit)")
    footer = group("conFlPasteFooter", [add], direction="Horizontal", gap=8,
                   height=36, justify="End", align_items="Center")
    body = capped_body("conFlPasteBody", [help_, inp], popup_body_max([head.h, footer.h]))
    modal = group("conFlPasteModal", [head, body, footer], direction="Vertical",
                  gap=12, fill=C_MODAL_BG, border_color=C_PRIMARY_SOFT, radius=lay.RADIUS_MODAL,
                  pad=(18, 18, 18, 18), width="Min(560, App.Width - 24)",
                  drop_shadow="ExtraBold", visible=vis)
    modal.props["X"] = "(App.Width - Self.Width) / 2"
    modal.props["Y"] = "Max(12, (App.Height - Self.Height) / 3)"
    return [backdrop, modal]
