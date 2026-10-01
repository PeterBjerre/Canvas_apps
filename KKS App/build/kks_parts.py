# -*- coding: utf-8 -*-
"""
KKS-opslagets skaerm: delene, formlerne og hentningen.

    [Function key][Aggregate key][Component key]
    [Search code or description....] [Reset]
    LETTER    ALL A B C ...              <- colKksL1Items
    GROUP     ALL AB AC ...              <- colKksL2Items (eller en note)
    SUBGROUP  ALL ABA ABB ...            <- colKksL3Items (kun funktionsnoegle)

    [Back] [All] [> A] [> AB] [> ABA]                         42 rows
    A / AB - Groups ...
    CODE   DESCRIPTION
    ABA    ...                           <- et klik gaar til raekkens plads

FRA DEN OPRINDELIGE APP
-----------------------
Navigationen og filtrene er powerapp-kks' (den haandbyggede app), formel for
formel: de samme tre niveauer, den samme soegning og det samme klik paa en
raekke. Det, der er lavet om:

  * Data kommer fra SharePoint (kks_config.py) i stedet for Table(...)-
    literaler, og hentes EEN gang - foerste gang skaermen vises.
  * Knapgitrene er eet galleri med WrapCount pr. niveau og EEN knap -
    ikke 25 knapper pr. raekke, hver med sin egen Index()-formel.
  * Rammen, bjaelken, farverne og breakpoints er repoets (app_frame,
    top_bar, design_tokens, layout_tokens) - ingen RGBA og ingen App.Width
    sammenlignet med et tal.
  * Ingen hoejde laeser en anden kontrols .Height (check_layout regel 1).
  * Teksterne er engelske som i resten af BIO SAP. Vejledningens egne
    beskrivelser er data og staar paa dansk, som i kilden.
"""
from gen_screen import (Ctrl, C_CARD_BG, C_CARD_BORDER, C_DIVIDER, C_INVALID_FG, C_MUTED,
                        C_PRIMARY, C_TITLE)
from build_helpers import (button, card, concurrent, fit_button_width, flow_row, group,
                           loading_overlay, row_hit, row_rule, text_ctrl, text_input,
                           top_bar, ICON_W)
import layout_tokens as lay
from layout_tokens import SHELL_W, SCROLLBAR_W, GALLERY_RESERVE

import kks_config as cfg

P = "Kks"

# ---------------------------------------------------------------------------
# Bredder
# ---------------------------------------------------------------------------
# Indholdet i et kort: SHELL_W minus kortets 2 x 18 px polstring.
CARD_W = f"({SHELL_W} - 2 * {lay.CARD_PAD})"

# Knapgitrene: en knap pr. celle, saa mange celler pr. raekke der er plads
# til. Cellerne er mindst CHIP_PITCH brede (knap + luft).
CHIP_W = 56
CHIP_H = 32
CHIP_ROW = 40
CHIP_PITCH = CHIP_W + 8
CHIPS_PER_ROW = f"Max(1, RoundDown({CARD_W} / {CHIP_PITCH}, 0))"

# Tabellen. Raekkens celler maales mod galleriets skabelon, som er kortets
# indhold minus scrollbaren og GALLERY_RESERVE (gen_screen.resolve_templates).
# Overskriften bruger de SAMME bredder (check_layout regel 29).
TABLE_W = f"({CARD_W} - {SCROLLBAR_W} - {GALLERY_RESERVE})"
ROW_PAD = 12
ROW_GAP = 12
CODE_W = 96
DESC_W = f"({TABLE_W} - {2 * ROW_PAD} - {CODE_W} - {ROW_GAP})"
# Beskrivelserne ombrydes. Hoejden regnes af laengden: tegn pr. linje ved
# 13 pt (mange er VERSALER, derfor et bredt skoen - hellere en linje luft
# end en klippet linje), 19 px pr. linje.
LINE_H = 19
CHARS_PER_LINE = f"Max(14, RoundDown({DESC_W} / 7.5, 0))"
TABLE_MAX_H = 560


def desc_h(ref):
    return f"Max(1, RoundUp(Len({ref}) / {CHARS_PER_LINE}, 0)) * {LINE_H} + 1"


def row_h(ref):
    return f"{desc_h(ref)} + 22"


# ---------------------------------------------------------------------------
# Tilstand
# ---------------------------------------------------------------------------
CLEAR_LEVELS = 'Set(varKksL1, "ALL");\nSet(varKksL2, "");\nSet(varKksL3, "")'
CLEAR_QUERY = 'Set(varKksQuery, "");\nReset(inpKksSearch)'

# Foerste besoeg: tilstanden saettes, hvis den ikke findes. Staar i
# skaermens OnVisible og ikke i App.OnStart, saa den ogsaa gaelder i BIO
# SAP, hvor App.OnStart ikke kender domaenerne.
INIT_STATE = (
    "If(\n"
    "    IsBlank(varKksKey),\n"
    '    Set(varKksKey, "function");\n'
    "    " + CLEAR_LEVELS.replace("\n", "\n    ") + ";\n"
    '    Set(varKksQuery, "")\n'
    ")"
)


def load_fx():
    """Hent de tre noegleomraader - EEN gang pr. session.

    Alle hentninger staar i een Concurrent: funktionsnoeglerne i bidder
    efter SortNo (kks_config.CHUNK), aggregat og komponent fra MD_FLKey.
    Hver filtrering sammenligner med en KONSTANT, saa SharePoint udfoerer
    den (check_layout regel 30). Bagefter samles bidderne og formes til
    det skema, formlerne bruger: L1, Code, Description, P2, P3.

    Fejler hentningen, er varKksLoaded stadig falsk, og naeste besoeg
    proever igen. Skaermen siger imens, at listerne ikke kunne hentes."""
    n = cfg.chunk_count()
    fetch = []
    for i in range(n):
        lo, hi = i * cfg.CHUNK + 1, (i + 1) * cfg.CHUNK
        cond = (f"SortNo >= {lo} && SortNo <= {hi}" if i < n - 1
                else f"SortNo >= {lo}")
        fetch.append(
            f"ClearCollect(colKksFn{i + 1}, ForAll(Filter({cfg.L_FUNCTION}, {cond}) As r,\n"
            "        { Ord: r.SortNo, Section: r.Section, Code: r.Code, "
            "Description: r.Description }))")
    for key, key_type in cfg.FLKEY_TYPES.items():
        fetch.append(
            f"ClearCollect(colKks{key.title()}Raw, ForAll(Filter({cfg.L_FLKEY}, "
            f'KeyType = "{key_type}") As r,\n'
            "        { Code: r.KeyValue, Description: r.Description }))")
    parts = ", ".join(f"colKksFn{i + 1}" for i in range(n))

    def from_flkey(key, l1):
        return (
            f"ClearCollect(\n    colKks{key.title()},\n"
            f"    SortByColumns(\n"
            f"        ForAll(Filter(colKks{key.title()}Raw, !IsBlank(Description)) As r,\n"
            f"            {{ L1: {l1}, Code: r.Code, Description: r.Description, "
            f'P2: r.Code, P3: "" }}),\n'
            '        "L1", SortOrder.Ascending, "Code", SortOrder.Ascending\n'
            "    )\n)")

    body = ";\n".join([
        "Set(varKksLoading, true)",
        concurrent(*fetch),
        f"ClearCollect(colKksFnAll, {parts})",
        # P2/P3 er de foerste to og tre tegn af koden - undtagen i HOME,
        # de 25 overordnede bogstaver. Efterproevet mod den oprindelige
        # apps tabel: alle 2.913 raekker giver det samme.
        "ClearCollect(\n    colKksFunction,\n"
        "    ForAll(Sort(colKksFnAll, Ord) As r,\n"
        "        { L1: r.Section, Code: r.Code, Description: r.Description,\n"
        '          P2: If(r.Section = "HOME" || Len(r.Code) < 2, "", Left(r.Code, 2)),\n'
        '          P3: If(r.Section = "HOME" || Len(r.Code) < 3, "", Left(r.Code, 3)) })\n'
        ")",
        from_flkey("aggregate", "Left(r.Code, 1)"),
        # Komponentnoeglerne "-A" ... "-Z" hoerer under bogstavet efter
        # stregen, som i HTML-sidens sektioner.
        from_flkey("component",
                   'If(StartsWith(r.Code, "-"), Mid(r.Code, 2, 1), Left(r.Code, 1))'),
        "Set(varKksLoaded, !IsEmpty(colKksFunction))",
        "Set(varKksLoading, false)",
    ])
    return ("// Noeglerne hentes EEN gang - se KKS App/build/kks_parts.py, load_fx().\n"
            "If(\n    !varKksLoaded,\n    " + body.replace("\n", "\n    ") + "\n)")


def on_visible():
    return INIT_STATE + ";\n" + load_fx()


# Skemaerne for samlingerne. If(false, ...): kun skemaet - App.OnStart
# koerer samtidig med OnVisible og maa ikke toemme det, den henter
# (check_layout regel 34).
ROW = {"L1": '""', "Code": '""', "Description": '""', "P2": '""', "P3": '""'}
RAW = {"Code": '""', "Description": '""'}
FN = {"Ord": "0", "Section": '""', "Code": '""', "Description": '""'}


def collections():
    out = [("colKksFunction", ROW), ("colKksAggregate", ROW), ("colKksComponent", ROW),
           ("colKksAggregateRaw", RAW), ("colKksComponentRaw", RAW), ("colKksFnAll", FN)]
    out += [(f"colKksFn{i + 1}", FN) for i in range(cfg.chunk_count())]
    return out


# ---------------------------------------------------------------------------
# Navngivne formler - navigationen og filtrene
# ---------------------------------------------------------------------------
# Ordret den oprindelige apps (powerapp-kks App.Formulas), med samlinger i
# stedet for literaler og engelske tekster. "ALL" er en VAERDI (en knap i
# gitteret og varKksL1's startvaerdi), ikke en tekst at oversaette.
def _cap(expr):
    """'ABC...' -> 'Abc...' - overskrifternes form i stien."""
    return f"Upper(Left(Lower({expr}), 1)) & Mid(Lower({expr}), 2)"


FORMULAS = f'''// KKS-opslaget (KKS App/build/kks_parts.py). Samlingerne hentes i
// skaermens OnVisible; alt herunder regnes i hukommelsen.
colKksScope = Switch(varKksKey, "aggregate", colKksAggregate, "component", colKksComponent, colKksFunction);
KksHasL3 = varKksKey = "function";
colKksBase = If(varKksL1 = "ALL", colKksScope, Filter(colKksScope, L1 = varKksL1));
colKksBaseQ = If(IsBlank(varKksQuery), colKksBase, Filter(colKksBase, varKksQuery in Code || varKksQuery in Description));
// Bogstaverne: funktionsnoeglens er HOME-sektionens 25 koder, de to andres
// de bogstaver, der har raekker.
colKksL1Keys = If(KksHasL3, Sort(Distinct(Filter(colKksScope, L1 = "HOME"), Code), Value), Sort(Distinct(colKksScope, L1), Value));
colKksL1Items = Ungroup(Table({{T: Table({{Value: "ALL"}})}}, {{T: colKksL1Keys}}), T);
colKksL2Keys = Sort(Distinct(Filter(colKksBaseQ, varKksL1 <> "ALL" && Len(P2) = 2 && StartsWith(P2, varKksL1)), P2), Value);
colKksL2Items = Ungroup(Table({{T: Table({{Value: "ALL"}})}}, {{T: colKksL2Keys}}), T);
colKksL2Rows = If(IsBlank(varKksL2), colKksBaseQ, Filter(colKksBaseQ, P2 = varKksL2));
colKksL3Keys = Sort(Distinct(Filter(colKksL2Rows, KksHasL3 && !IsBlank(varKksL2) && Len(P3) = 3 && StartsWith(P3, varKksL2)), P3), Value);
colKksL3Items = Ungroup(Table({{T: Table({{Value: "ALL"}})}}, {{T: colKksL3Keys}}), T);
colKksL3Rows = If(!KksHasL3 || IsBlank(varKksL3), colKksL2Rows, Filter(colKksL2Rows, P3 = varKksL3));
colKksResults = If(varKksL1 = "ALL" && IsBlank(varKksQuery) && KksHasL3, Filter(colKksScope, L1 = "HOME"), colKksL3Rows);
KksNote2 = If(varKksL1 = "ALL", "Pick a letter to see its groups.", CountRows(colKksL2Keys) = 0, If(IsBlank(varKksQuery), "No groups under this letter.", "No groups match the search."), "");
KksNote3 = If(!KksHasL3, "", varKksL1 = "ALL", "Pick a letter to see its subgroups.", IsBlank(varKksL2), "Pick a group to see its subgroups.", CountRows(colKksL3Keys) = 0, If(IsBlank(varKksQuery), "No subgroups under this group.", "No subgroups match the search."), "");
KksHeadL1 = If(varKksL1 = "ALL", "", Coalesce(LookUp(colKksScope, L1 = "HOME" && Upper(Code) = varKksL1, Description), LookUp(colKksBase, Upper(Code) = varKksL1, Description), LookUp(colKksBase, Len(P2) = 2 && Upper(Code) = P2 && StartsWith(P2, varKksL1), Description), ""));
KksHeadL2 = If(IsBlank(varKksL2), "", Coalesce(LookUp(colKksScope, Upper(Code) = varKksL2, Description), ""));
KksHeadL3 = If(IsBlank(varKksL3), "", Coalesce(LookUp(colKksScope, Upper(Code) = varKksL3, Description), ""));
KksTitle = If(varKksL1 = "ALL", "All sections" & If(IsBlank(varKksQuery), "", " - search results"), varKksL1 & If(IsBlank(varKksL2) && IsBlank(varKksL3) && !IsBlank(KksHeadL1), " - " & {_cap("KksHeadL1")}, "") & If(IsBlank(varKksL2), "", " / " & varKksL2 & If(IsBlank(varKksL3) && !IsBlank(KksHeadL2), " - " & {_cap("KksHeadL2")}, "")) & If(IsBlank(varKksL3), "", " / " & varKksL3 & If(!IsBlank(KksHeadL3), " - " & {_cap("KksHeadL3")}, "")) & If(IsBlank(varKksQuery), "", " - search results"));'''


# ---------------------------------------------------------------------------
# Delene
# ---------------------------------------------------------------------------
def _selected(b, selected):
    """Valgt = kant og tekst i primaerfarven, 2 px - hubbens regel for
    filterknapper (build_hub._selected_style)."""
    b.props["Appearance"] = "ButtonAppearance.Outline"
    b.props["BorderColor"] = f"If({selected}, {C_PRIMARY}, {C_CARD_BORDER})"
    b.props["BorderThickness"] = f"If({selected}, 2, 1)"
    b.props["Color"] = f"If({selected}, {C_PRIMARY}, {C_TITLE})"
    return b


def build_bar():
    sub = "Switch(\n    varKksKey,\n    " + ",\n    ".join(
        f'"{k}", "{s}"' for k, _t, s in cfg.KEYS[1:]) + f',\n    "{cfg.KEYS[0][2]}"\n)'
    return top_bar(P, f'"{cfg.TITLE}"', sub, [], icon=cfg.APP_KEY)


def _key_tabs():
    tabs = []
    for key, text, _sub in cfg.KEYS:
        b = button(f"btnKksKey{key.title()}", f'"{text}"',
                   f'Set(varKksKey, "{key}");\n{CLEAR_LEVELS};\n{CLEAR_QUERY}',
                   width=fit_button_width(f'"{text}"'), height=36,
                   accessible=f'"Show {text.lower()}s"')
        tabs.append(_selected(b, f'varKksKey = "{key}"'))
    return flow_row("conKksKeys", tabs, CARD_W, gap=8)


def _search_row():
    search = text_input("inpKksSearch", '""', placeholder='"Search code or description"',
                        width="340", ttype="Search",
                        onchange="Set(varKksQuery, Trim(Self.Text))",
                        label='"Search KKS codes and descriptions"')
    # Soegningen koerer, naar brugeren holder en pause - ikke pr. tastetryk
    # over 2.913 raekker.
    search.props["TriggerOutput"] = "TriggerOutput.Delayed"
    reset = button("btnKksReset", '"Reset"', f"{CLEAR_LEVELS};\n{CLEAR_QUERY}",
                   width=fit_button_width('"Reset"') + ICON_W, height=36, icon="ArrowReset",
                   accessible='"Reset letter, group and search"',
                   display_mode='If(varKksL1 = "ALL" && IsBlank(varKksQuery) && '
                                'IsBlank(inpKksSearch.Text), DisplayMode.Disabled, '
                                'DisplayMode.Edit)')
    return flow_row("conKksSearchRow", [search, reset], CARD_W, gap=10)


def _lane(n, label, items, selected, onselect, note=None, visible=None):
    """Et niveau: overskrift, og enten et gitter af knapper eller en note.

    Gitteret er EET galleri med WrapCount = saa mange knapper, der er plads
    til, og EEN knap i skabelonen. Hoejden er antallet af raekker gange
    raekkehoejden - regnet af det samme tal, saa de ikke kan uenes."""
    lbl = text_ctrl(f"txtKksLane{n}", f'"{label}"', size=lay.SIZE_MICRO, weight="Semibold",
                    color=C_MUTED, height=18)
    chip = button(f"btnKksL{n}Chip", "ThisItem.Value", onselect, width=CHIP_W, height=CHIP_H,
                  accessible=f'"{label.title()} " & ThisItem.Value')
    _selected(chip, selected)
    chip.props["X"] = "0"
    chip.props["Y"] = str((CHIP_ROW - CHIP_H) // 2)
    for k in ("AlignInContainer", "LayoutMinWidth"):
        chip.props.pop(k, None)
    rows = f"RoundUp(CountRows({items}) / {CHIPS_PER_ROW}, 0)"
    gal_vis = f'{note} = ""' if note else None
    gal = Ctrl(f"galKksL{n}", "Gallery", variant="Vertical", props={
        "AccessibleLabel": f'"{label.title()}"',
        "BorderStyle": "BorderStyle.None", "Fill": C_CARD_BG, "FillPortions": "0",
        "Height": f"{rows} * {CHIP_ROW}", "Items": items, "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None", "Selectable": "false",
        "ShowScrollbar": "false", "TabIndex": "0", "TemplatePadding": "0",
        "TemplateSize": str(CHIP_ROW), "Width": "Parent.Width",
        "WrapCount": CHIPS_PER_ROW,
    }, children=[chip], h=f"{rows} * {CHIP_ROW}", vis=gal_vis)
    kids = [lbl]
    if note:
        kids.append(text_ctrl(f"txtKksNote{n}", note, size=lay.SIZE_SMALL, color=C_MUTED,
                              height=20, visible=f'{note} <> ""'))
    kids.append(gal)
    return group(f"conKksLane{n}", kids, gap=6, visible=visible)


def build_browse():
    l1 = _lane(1, "LETTER", "colKksL1Items", "varKksL1 = ThisItem.Value",
               f"Set(varKksL1, ThisItem.Value);\nSet(varKksL2, \"\");\nSet(varKksL3, \"\")")
    l2 = _lane(2, "GROUP", "colKksL2Items",
               'If(ThisItem.Value = "ALL", IsBlank(varKksL2), varKksL2 = ThisItem.Value)',
               'Set(varKksL2, If(ThisItem.Value = "ALL", "", ThisItem.Value));\n'
               'Set(varKksL3, "")',
               note="KksNote2")
    l3 = _lane(3, "SUBGROUP", "colKksL3Items",
               'If(ThisItem.Value = "ALL", IsBlank(varKksL3), varKksL3 = ThisItem.Value)',
               'Set(varKksL3, If(ThisItem.Value = "ALL", "", ThisItem.Value))',
               note="KksNote3", visible="KksHasL3")
    return card("conKksBrowseCard", [_key_tabs(), _search_row(), l1, l2, l3], gap=12)


# Et klik paa en raekke gaar til dens plads i hierarkiet og rydder
# soegningen - ordret den oprindelige apps galKksRowsB.OnSelect.
ROW_SELECT = f'''With(
    {{c: Upper(ThisItem.Code), s: ThisItem.L1}},
    With(
        {{isTop: Len(c) = 1 && !IsBlank(LookUp(colKksL1Keys, Value = c))}},
        With(
            {{l1: If(isTop, c, If(s = "HOME", If(!IsBlank(LookUp(colKksL1Keys, Value = Left(c, 1))), Left(c, 1), "ALL"), s))}},
            Set(varKksL1, l1);
            Set(varKksL2, If(l1 = "ALL" || isTop || Len(c) < 2, "", Left(c, 2)));
            Set(varKksL3, If(l1 = "ALL" || isTop || !KksHasL3 || Len(c) < 3, "", Left(c, 3)));
            {CLEAR_QUERY.replace(chr(10), chr(10) + "            ")}
        )
    )
)'''

UP = '''If(
    !IsBlank(varKksL3), Set(varKksL3, ""),
    !IsBlank(varKksL2), Set(varKksL2, ""),
    Set(varKksL1, "ALL")
)'''


def _crumbs():
    up = button("btnKksUp", '"Back"', UP, width=fit_button_width('"Back"') + ICON_W, height=32,
                icon="ArrowLeft", accessible='"Up one level"',
                display_mode='If(varKksL1 = "ALL", DisplayMode.Disabled, DisplayMode.Edit)')
    crumbs = [up]
    # (navn, tekst, handling, synlig, bredde, "her er du", etiket)
    spec = [
        ("All", '"All"', CLEAR_LEVELS, None, 56, 'varKksL1 = "ALL"', '"All sections"'),
        ("L1", '"› " & varKksL1', 'Set(varKksL2, "");\nSet(varKksL3, "")',
         'varKksL1 <> "ALL"', 56, "IsBlank(varKksL2)", '"Letter " & varKksL1'),
        ("L2", '"› " & varKksL2', 'Set(varKksL3, "")', "!IsBlank(varKksL2)", 64,
         "IsBlank(varKksL3)", '"Group " & varKksL2'),
        ("L3", '"› " & varKksL3', "false", "!IsBlank(varKksL3)", 72, "true",
         '"Subgroup " & varKksL3'),
    ]
    for name, text, act, vis, w, here, label in spec:
        b = button(f"btnKksCrumb{name}", text, act, width=w, height=32, visible=vis,
                   accessible=label)
        b.props["Size"] = str(lay.SIZE_BODY)
        crumbs.append(_selected(b, here))
    count = text_ctrl("txtKksCount",
                      'CountRows(colKksResults) & If(CountRows(colKksResults) = 1, " row", " rows")',
                      size=lay.SIZE_SMALL, color=C_MUTED, height=32, align="Right", width=90)
    return flow_row("conKksCrumbs", crumbs + [count], CARD_W, gap=6, flex=count, flex_min=90)


def build_results():
    path_h = (f"Max(20, RoundUp(Len(KksTitle) / Max(24, RoundDown({CARD_W} / 7.5, 0)), 0) "
              f"* {LINE_H + 1})")
    path = text_ctrl("txtKksPath", "KksTitle", size=lay.SIZE_BODY, color=C_PRIMARY,
                     weight="Semibold", wrap="true", height=path_h)

    def head_cell(name, text, w):
        return text_ctrl(name, f'"{text}"', size=lay.SIZE_MICRO, weight="Semibold",
                         color=C_MUTED, height=20, width=w)

    head = group("conKksTableHead", [head_cell("txtKksHeadCode", "CODE", CODE_W),
                                     head_cell("txtKksHeadDesc", "DESCRIPTION", DESC_W)],
                 direction="Horizontal", gap=ROW_GAP, height=20, align_items="Center",
                 pad=(0, ROW_PAD, 0, ROW_PAD))
    head_rule = group("conKksTableRule", [], direction="Horizontal", height=1, fill=C_DIVIDER)

    rh = row_h("ThisItem.Description")
    code = text_ctrl("txtKksRowCode", "ThisItem.Code", size=lay.SIZE_BODY, weight="Semibold",
                     height=20, width=CODE_W)
    desc = text_ctrl("txtKksRowDesc", "ThisItem.Description", size=lay.SIZE_BODY,
                     wrap="true", height=desc_h("ThisItem.Description"), width=DESC_W)
    row = group("conKksRow", [code, desc], direction="Horizontal", gap=ROW_GAP, height=rh,
                width="Parent.TemplateWidth", align_items="Start", fill=C_CARD_BG,
                pad=(11, ROW_PAD, 11, ROW_PAD))
    rule = row_rule("rctKksRowRule", 0)
    rule.props["Y"] = f"({rh}) - 1"
    hit = row_hit("btnKksRowHit", ROW_SELECT,
                  '"Go to " & ThisItem.Code & " - " & ThisItem.Description',
                  "Parent.TemplateWidth", f"({rh}) - 1")
    gal_h = (f"If(CountRows(colKksResults) = 0, 0, "
             f"Min({TABLE_MAX_H}, Sum(colKksResults, {row_h('Description')}) + 2))")
    gal = Ctrl("galKksRows", "Gallery", variant="VariableHeight", props={
        "AccessibleLabel": '"KKS codes. Select a row to go to its place."',
        "BorderStyle": "BorderStyle.None", "Fill": C_CARD_BG, "FillPortions": "0",
        "Height": gal_h, "Items": "colKksResults", "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None", "Selectable": "false",
        "ShowScrollbar": "true", "TabIndex": "0", "TemplatePadding": "0",
        "TemplateSize": "42", "Width": "Parent.Width", "WrapCount": "1",
    }, children=[row, rule, hit], h=gal_h, vis="CountRows(colKksResults) > 0")

    empty = text_ctrl(
        "txtKksEmpty",
        'If(IsEmpty(colKksScope), "The KKS lists could not be loaded. Check access to '
        f'{cfg.L_FUNCTION} and {cfg.L_FLKEY}.", "No codes match.")',
        size=lay.SIZE_BODY, weight="Semibold", height=40, wrap="true",
        color=f"If(IsEmpty(colKksScope), {C_INVALID_FG}, {C_MUTED})",
        visible="CountRows(colKksResults) = 0")
    return card("conKksResultsCard", [_crumbs(), path, head, head_rule, gal, empty], gap=8)


def build_loading():
    return loading_overlay("imgKksLoading", "varKksLoading", "Loading KKS keys, please wait")
