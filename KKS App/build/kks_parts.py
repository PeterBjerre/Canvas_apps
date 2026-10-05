# -*- coding: utf-8 -*-
"""
KKS-opslagets skaerm: delene, formlerne og hentningen.

    [Function key][Aggregate key][Component key]
    [Search code or description....] [Reset]
    LETTER    ALL A B C ...              <- colKksL1Keys
    GROUP     ALL AB AC ...              <- colKksL2Keys (eller en note)
    SUBGROUP  ALL ABA ABB ...            <- colKksL3Keys (kun funktionsnoegle)

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
from gen_screen import (Ctrl, C_APP_BG, C_CARD_BG, C_DISABLED_BG, C_DIVIDER, C_INFO_BG,
                        C_INFO_FG, C_INVALID_FG, C_MUTED, C_MUTED_BG, C_PRIMARY,
                        C_PRIMARY_SOFT, C_MODAL_BG, C_TRANSPARENT, C_WHITE)
from build_helpers import (border_rule, button, card, concurrent, fit_button_width, flow_row, group, grow,
                           input_theme, loading_overlay, row_hit, row_rule, text_ctrl,
                           text_modal, themed_dropdown)
from fl_picker import BUSY_W, SEARCH_W, busy_box, HEIGHT as SEARCH_H, ROW_PAD as SEARCH_PAD, _timer
import layout_tokens as lay
from layout_tokens import SHELL_W, SCROLLBAR_W, GALLERY_RESERVE

import kks_config as cfg

P = "Kks"

# ---------------------------------------------------------------------------
# Bredder
# ---------------------------------------------------------------------------
# Indholdet i et kort: SHELL_W minus kortets 2 x 18 px polstring.
CARD_W = f"({SHELL_W} - 2 * {lay.CARD_PAD})"
# Results: no card on a phone, so the content is as wide as the page.
RES_W = f"If({lay.below('Tablet')}, {SHELL_W}, {CARD_W})"

# Knapgitrene: et galleri af RAEKKER, hver med LANE_SLOTS knapper ved siden af
# hinanden (X = k * pitch). WrapCount duer ikke: Power Apps begraenser det
# til 10, og knapperne fik da en bred celle hver og det oevrige blev klippet.
# Knapperne er smalle som i den oprindelige app: 50 px (bogstav) eller 56 px
# (gruppe), med 8 px imellem.
LANE_SLOTS = 26      # flest elementer i et niveau: ALL + 25 (se kks_config)
CHIP_H = 32
CHIP_ROW = 40
CHIP_RADIUS = 12
TAB_W = 116
NOTE_H = 28
# Hvert niveau staar i sin egen kasse: polstring paa hver side.
LANE_PAD = 10
# Galleriets skabelon er smallere end kassen: gen_screen.resolve_templates
# trækker GALLERY_RESERVE fra, og kassens kant og polstring ligger oven i
# (regel 26 maaler cellerne mod det tal).
LANE_W = f"({CARD_W} - {2 * LANE_PAD} - 34)"
CHIP_GAP = 8


def per_row(chip_w):
    """Knapper pr. raekke - regnet af kasserne, ikke af en kontrols bredde."""
    return f"Max(1, RoundDown(({LANE_W} + {CHIP_GAP}) / {chip_w + CHIP_GAP}, 0))"


def per_row_probe(chip_w):
    """Det samme tal som per_row, skrevet kun med If og Max, saa
    check_layout kan regne paa det (det kender ikke RoundDown). Bruges kun
    af gen_screens regel 26 og skrives aldrig ud i appen."""
    pitch = chip_w + CHIP_GAP
    terms = " + ".join(f"If({LANE_W} + {CHIP_GAP} >= {j * pitch}, 1, 0)"
                       for j in range(1, LANE_SLOTS + 1))
    return f"Max(1, {terms})"

# Tabellen. Raekkens celler maales mod galleriets skabelon, som er kortets
# indhold minus scrollbaren og GALLERY_RESERVE (gen_screen.resolve_templates).
# Overskriften bruger de SAMME bredder (check_layout regel 29).
TABLE_W = (f"({RES_W} - {SCROLLBAR_W} - If({lay.below('Tablet')}, 0, {GALLERY_RESERVE}))")
ROW_PAD = 8
ROW_GAP = 8
CODE_W = 72
DESC_W = f"({TABLE_W} - {2 * ROW_PAD} - {CODE_W} - {ROW_GAP})"
# Beskrivelserne ombrydes. Hoejden regnes af laengden: tegn pr. linje ved
# 13 pt (mange er VERSALER, derfor et bredt skoen - hellere en linje luft
# end en klippet linje), 19 px pr. linje.
LINE_H = 19
CHARS_PER_LINE = f"Max(14, RoundDown({DESC_W} / 7.5, 0))"
MOBILE_LINES = 3
LONG_DESC = f"Len(ThisItem.Description) > {MOBILE_LINES} * {CHARS_PER_LINE}"
TABLE_MAX_H = f"If({lay.below('Tablet')}, 1120, Max(560, App.Height - 600))"


def desc_h(ref):
    return f"Max(1, RoundUp(Len({ref}) / {CHARS_PER_LINE}, 0)) * {LINE_H} + 1"


def row_h(ref):
    return f"{desc_h(ref)} + 22"


# ---------------------------------------------------------------------------
# Tilstand
# ---------------------------------------------------------------------------
CLEAR_LEVELS = 'Set(varKksL1, "ALL");\nSet(varKksL2, "");\nSet(varKksL3, "")'
CLEAR_QUERY = ('Set(varKksQuery, "");\nSet(varKksTyped, "");\n'
               'Set(varKksBusy, false);\nReset(cmbKksFind)')

# Foerste besoeg: tilstanden saettes, hvis den ikke findes. Staar i
# skaermens OnVisible og ikke i App.OnStart, saa den ogsaa gaelder i BIO
# SAP, hvor App.OnStart ikke kender domaenerne.
INIT_STATE = (
    "If(\n"
    "    IsBlank(varKksKey),\n"
    '    Set(varKksKey, "function");\n'
    "    " + CLEAR_LEVELS.replace("\n", "\n    ") + ";\n"
    '    Set(varKksQuery, "");\n'
    '    Set(varKksTyped, "");\n'
    '    Set(varKksPending, "");\n'
    '    Set(varKksDetailCode, "");\n'
    '    Set(varKksDetailText, "");\n'
    '    Set(varKksDetailOn, false);\n'
    '    Set(varKksPick, 0);\n'
    "    Set(varKksBusy, false)\n"
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
        "Set(varKksTried, true)",
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
// varKksLoaded staar med for at tvinge en genberegning, naar noeglerne er hentet.
colKksScope = With({{ready: varKksLoaded}}, Switch(varKksKey, "aggregate", colKksAggregate, "component", colKksComponent, colKksFunction));
KksHasL3 = varKksKey = "function";
colKksBase = If(varKksL1 = "ALL", colKksScope, Filter(colKksScope, L1 = varKksL1));
colKksBaseQ = If(IsBlank(varKksQuery), colKksBase, Filter(colKksBase, varKksQuery in Code || varKksQuery in Description));
// Bogstaverne: funktionsnoeglens er HOME-sektionens 25 koder, de to andres
// de bogstaver, der har raekker.
colKksL1Keys = If(KksHasL3, Sort(Distinct(Filter(colKksScope, L1 = "HOME"), Code), Value), Sort(Distinct(colKksScope, L1), Value));
colKksL2Keys = Sort(Distinct(Filter(colKksBaseQ, varKksL1 <> "ALL" && Len(P2) = 2 && StartsWith(P2, varKksL1)), P2), Value);
colKksL2Rows = If(IsBlank(varKksL2), colKksBaseQ, Filter(colKksBaseQ, P2 = varKksL2));
colKksL3Keys = Sort(Distinct(Filter(colKksL2Rows, KksHasL3 && !IsBlank(varKksL2) && Len(P3) = 3 && StartsWith(P3, varKksL2)), P3), Value);
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
def _selected(b, selected, radius=CHIP_RADIUS):
    """Piller: valgt = fyldt i primaerfarven med hvid tekst, ikke valgt =
    lyseblaa kant og moerkeblaa tekst (originalens (173,208,238) og
    (10,75,125), som tokens)."""
    b.props.update(lay.radius(radius))
    b.props["Appearance"] = (f"If({selected}, ButtonAppearance.Primary, "
                            f"ButtonAppearance.Outline)")
    b.props["BasePaletteColor"] = C_PRIMARY
    b.props["BorderColor"] = f"If({selected}, {C_PRIMARY}, {C_PRIMARY_SOFT})"
    b.props["BorderThickness"] = "1"
    b.props["Color"] = f"If({selected}, {C_WHITE}, {C_INFO_FG})"
    return b


def _soft(b):
    """En almindelig knap i kortets lyseblaa udtryk."""
    b.props["BorderColor"] = C_PRIMARY_SOFT
    b.props["Color"] = C_INFO_FG
    return b


def _link(b, here):
    """Stien foroven resultaterne: tekst i primaerfarven uden kant."""
    b.props["Appearance"] = "ButtonAppearance.Transparent"
    b.props["BorderColor"] = C_TRANSPARENT
    b.props["BorderThickness"] = "0"
    b.props["Color"] = C_PRIMARY
    b.props["FontWeight"] = f"If({here}, FontWeight.Semibold, FontWeight.Normal)"
    return b


def build_bar():
    sub = "Switch(\n    varKksKey,\n    " + ",\n    ".join(
        f'"{k}", "{s}"' for k, _t, s in cfg.KEYS[1:]) + f',\n    "{cfg.KEYS[0][2]}"\n)'
    title = text_ctrl("txtKksTitle", f'"{cfg.TITLE}"', size=28, weight="Semibold", height=40)
    subtitle = text_ctrl("txtKksSub", sub, size=lay.SIZE_INPUT, color=C_MUTED, height=24)
    return group("conKksTitleBlock", [title, subtitle], direction="Vertical", gap=6,
                 fill=C_TRANSPARENT)


def build_header():
    """Titlen i et kort oeverst - ikke en bjaelke med streg under."""
    return card("conKksHeaderCard", [build_bar()], gap=0, pad_y=16)


def frame(header, body):
    """Siden uden titelkort: sidebjaelken har titlen. Samme
    mal som build_helpers.app_frame, saa check_layout regel 23 holder."""
    main = group("conKksBody", body, direction="Vertical", gap=16,
                 height="Parent.Height", fill_portions=1,
                 overflow_y="Scroll", fill=C_APP_BG,
                 pad=(lay.HEADER_PAD_T, lay.PAGE_PAD_R, lay.BODY_PAD_B, lay.PAGE_PAD_L))
    root = group("conKksRoot", [main], direction="Vertical", gap=0,
                 height=lay.ROOT_H, width=lay.ROOT_W, fill=C_APP_BG)
    root.props["X"] = lay.ROOT_X
    root.props["Y"] = lay.ROOT_Y
    return root


def _key_tabs():
    tabs = []
    for key, text, _sub in cfg.KEYS:
        b = button(f"btnKksKey{key.title()}", f'"{text}"',
                   f'Set(varKksKey, "{key}");\n{CLEAR_LEVELS};\n{CLEAR_QUERY}',
                   width=TAB_W, height=32,
                   accessible=f'"Show {text.lower()}s"')
        b.props["Size"] = f"If({lay.below('Tablet')}, {lay.SIZE_MICRO}, {lay.SIZE_SMALL})"
        b.props["Width"] = f"If({lay.below('Tablet')}, ({CARD_W} - 16) / 3, {TAB_W})"
        b.props["LayoutMinWidth"] = b.props["Width"]
        tabs.append(_selected(b, f'varKksKey = "{key}"', radius=14))
    return flow_row("conKksKeys", tabs, CARD_W, gap=8)


SEARCH_CODE = "?search"
SEARCH_MIN = 2
SEARCH_ROW_W = f"If({lay.below('Tablet')}, {CARD_W}, Max(460, {CARD_W} / 3))"
RESET_FX = ('Set(varKksKey, "function");\n' + CLEAR_LEVELS + ";\n" + CLEAR_QUERY
            + ';\nSet(varKksPending, "");\nSet(varKksDetailOn, false)')
NOTHING_TO_RESET = ('varKksKey = "function" && varKksL1 = "ALL" && IsBlank(varKksL2) && '
                    'IsBlank(varKksL3) && IsBlank(varKksQuery) && IsBlank(varKksTyped) && '
                    'IsBlank(cmbKksFind.SearchText)')


def _suggest_items():
    """Comboboksens Items: de raekker, der matcher det skrevne (hoejst 50),
    plus en soegeraekke foerst, naar teksten er en ny soegning - Enter
    vaelger den, og ModernCombobox har ingen anden Enter-haendelse. Samme
    moenster som FL-vaelgeren (tools/fl_picker.py), men paa de lokale
    samlinger: intet flowkald."""
    s = (f'{{ L1: "", Code: "{SEARCH_CODE}", Description: q, P2: "", P3: "", '
         f'Display: q & "  -  press Enter to search" }}')
    return (
        "With(\n"
        "    { q: Trim(Self.SearchText) },\n"
        "    With(\n"
        "        {\n"
        f"            hits: FirstN(AddColumns(Filter(colKksScope, Len(q) >= {SEARCH_MIN} && "
        "(q in Code || q in Description)), Display, Code & \" - \" & Description), 50),\n"
        f"            s: {s}\n"
        "        },\n"
        "        If(\n"
        f"            Len(q) < {SEARCH_MIN} || varKksBusy || Upper(q) = Upper(Coalesce(varKksQuery, \"\")),\n"
        "            hits,\n"
        "            ForAll(Sequence(CountRows(hits) + 1),\n"
        "                If(Value = 1, s, Last(FirstN(hits, Value - 1))))\n"
        "        )\n"
        "    )\n"
        ")"
    )


def _search_row():
    query = "Coalesce(cmbKksFind.SearchText, varKksTyped)"
    run = f"Set(varKksPending, Trim({query}));\nSet(varKksBusy, true)"
    pick = ROW_SELECT.replace("ThisItem.", "Self.Selected.")
    on_change = (
        "If(\n"
        f'    Self.Selected.Code = "{SEARCH_CODE}",\n'
        "    Set(varKksPending, Self.Selected.Description);\n"
        "    Set(varKksBusy, true);\n"
        "    Reset(cmbKksFind),\n"
        "    !IsBlank(Self.Selected.Code),\n"
        f"    {pick.replace(chr(10), chr(10) + '    ')}\n"
        ")"
    )
    cmb = Ctrl("cmbKksFind", "ModernCombobox", props=input_theme({
        "AccessibleLabel": '"Search KKS codes and descriptions - type, then Search or Enter"',
        "BorderColor": border_rule("IsBlank(Self.SearchText)", "false"),
        "BorderStyle": "BorderStyle.Solid",
        "BorderThickness": "1",
        "DelayOutput": "false",
        "Height": str(SEARCH_H),
        "InputTextPlaceholder": '"Search code or description"',
        "IsSearchable": "true",
        "ItemDisplayText": "ThisItem.Display",
        "Items": _suggest_items(),
        "LayoutMinWidth": "0",
        "OnChange": on_change,
        **lay.radius(lay.RADIUS_INPUT),
        "SelectMultiple": "false",
        "Width": "0",
    }, None), h=SEARCH_H)
    grow(cmb)

    btn = button("btnKksFind", '"Search"', run, width=SEARCH_W, height=SEARCH_H,
                 accessible='"Search KKS codes"', visible="!varKksBusy")
    btn.props["LayoutMinWidth"] = str(SEARCH_W)
    btn.props["Size"] = str(lay.SIZE_SMALL)
    reset_w = fit_button_width('"Reset"')
    reset = button("btnKksReset", '"Reset"', RESET_FX, width=reset_w, height=SEARCH_H,
                   accessible='"Reset the KKS lookup"',
                   display_mode=f'If({NOTHING_TO_RESET}, DisplayMode.Disabled, DisplayMode.Edit)')
    reset.props["LayoutMinWidth"] = str(reset_w)
    reset.props["Size"] = str(lay.SIZE_SMALL)
    btns = group("conKksFindBtns", [btn, reset], direction="Horizontal", gap=8,
                 height=SEARCH_H, width=str(SEARCH_W + 8 + reset_w), align_items="Center",
                 visible="!varKksBusy")
    btns.props["LayoutMinWidth"] = str(SEARCH_W + 8 + reset_w)
    busy = busy_box("imgKksFindBusy", "varKksBusy")
    stk = lay.below("Tablet")
    for c in (btns, busy):
        c.props["AlignInContainer"] = f"If({stk}, AlignInContainer.End, AlignInContainer.Center)"

    row = group("conKksFindRow", [cmb, btns, busy], direction="Horizontal", gap=8,
                height=SEARCH_H + 2 * SEARCH_PAD, pad=(SEARCH_PAD, 0, SEARCH_PAD, 0),
                align_items="Center", width=SEARCH_ROW_W)
    row.props["LayoutDirection"] = (f"If({stk}, LayoutDirection.Vertical, "
                                    "LayoutDirection.Horizontal)")
    row.props["LayoutAlignItems"] = (f"If({stk}, LayoutAlignItems.Stretch, "
                                     "LayoutAlignItems.Center)")
    row.props["Height"] = (f"If({stk}, {2 * SEARCH_H + 8 + 2 * SEARCH_PAD}, "
                           f"{SEARCH_H + 2 * SEARCH_PAD})")
    row.h = row.props["Height"]
    # Soegeteksten gemmes, mens der skrives: trykker man paa Search, mister
    # comboboksen fokus og kan rydde sin tekst (se fl_picker).
    capture = _timer("tmrKksFindCapture", "!IsBlank(cmbKksFind.SearchText)", 300,
                     "If(!IsBlank(cmbKksFind.SearchText), "
                     "Set(varKksTyped, cmbKksFind.SearchText))")
    # Spinneren faar tid til at blive tegnet, foer filtreringen over alle
    # raekker bliver regnet.
    apply = _timer("tmrKksFindApply", "varKksBusy", 300,
                   "Set(varKksQuery, varKksPending);\nSet(varKksBusy, false)")
    apply.props["Repeat"] = "false"
    return group("conKksFindWrap", [row, capture, apply], direction="Vertical", gap=0,
                 width=SEARCH_ROW_W, align_in_container="Start")


def _lane(n, label, keys, selected, onselect, chip_w, note=None, visible=None):
    """Et niveau i sin egen kasse: enten et gitter af piller eller en note.

    Element 1 er altid ALL, element 2.. er noeglerne. ALL skrives IKKE ind i
    en tabel med Ungroup: Ungroup(Table({T: ..}, {T: ..}), T) gav kun et
    element pr. post (ALL og den foerste noegle) i Power Apps.
    Kassen har ingen overskrift: billedet viser ingen, og knapperne har en
    AccessibleLabel med niveauets navn."""
    per = per_row(chip_w)
    count = f"(CountRows({keys}) + 1)"
    slots = []
    for k in range(1, LANE_SLOTS + 1):
        # Galleriets Items er raekkenumrene 1..n; knap k i raekke r viser
        # element (r - 1) * pr. raekke + k, eller intet, hvis der ikke er
        # plads eller flere elementer.
        idx = f"((ThisItem.Value - 1) * {per} + {k})"
        shown = f"{k} <= {per} && {idx} <= {count}"
        text = (f'If({shown}, If({idx} = 1, "ALL", '
                f'Last(FirstN({keys}, {idx} - 1)).Value), "")')
        chip = button(f"btnKksL{n}_{k:02d}", text, onselect, width=chip_w, height=CHIP_H,
                      accessible=f'"{label.title()} " & Self.Text', visible=shown)
        _selected(chip, selected)
        chip.props["X"] = str((k - 1) * (chip_w + CHIP_GAP))
        chip.props["Y"] = str((CHIP_ROW - CHIP_H) // 2)
        # Regel 26 kan ikke se, at knap k er skjult, naar der ikke er plads.
        chip.props["_FitGuard"] = f"{k} <= {per_row_probe(chip_w)}"
        for key in ("AlignInContainer", "LayoutMinWidth"):
            chip.props.pop(key, None)
        slots.append(chip)
    rows = f"RoundUp({count} / {per}, 0)"
    gal_vis = f'{note} = ""' if note else None
    gal = Ctrl(f"galKksL{n}", "Gallery", variant="Vertical", props={
        "AccessibleLabel": f'"{label.title()}"',
        "BorderStyle": "BorderStyle.None", "Fill": C_TRANSPARENT, "FillPortions": "0",
        "Height": f"{rows} * {CHIP_ROW}", "Items": f"Sequence({rows})", "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None", "Selectable": "false",
        "ShowScrollbar": "false", "TabIndex": "0", "TemplatePadding": "0",
        "TemplateSize": str(CHIP_ROW), "Width": "Parent.Width",
    }, children=slots, h=f"{rows} * {CHIP_ROW}", vis=gal_vis)
    kids = []
    if note:
        kids.append(text_ctrl(f"txtKksNote{n}", note, size=lay.SIZE_SMALL, color=C_MUTED,
                              weight="Semibold", height=NOTE_H, visible=f'{note} <> ""',
                              extra={"Fill": C_INFO_BG, "PaddingLeft": "12",
                                     "PaddingTop": "5", **lay.radius(10)}))
    kids.append(gal)
    # gap=0: et skjult foerste barn skal ikke give det andet et mellemrum.
    return group(f"conKksLane{n}", kids, gap=0, fill=C_CARD_BG, border_color=C_PRIMARY_SOFT,
                 radius=14, pad=(LANE_PAD - 4, LANE_PAD, LANE_PAD - 4, LANE_PAD),
                 visible=visible)


def _level_menu(n, label, keys, selected, visible, enabled):
    """Mobilens udgave af et niveau: en vaelger-knap, der aabner en liste."""
    desc = (f'Coalesce(LookUp(colKksScope, L1 = "HOME" && Upper(Code) = {selected}, Description), '
            f'LookUp(colKksScope, Upper(Code) = {selected}, Description), "")')
    cut = f"Max(6, RoundDown((App.Width - 130) / 10.5, 0) - Len({selected}) - 3)"
    text = (f'Coalesce(If({selected} = "", Blank(), {selected}), "ALL") & '
            f'If(IsBlank({selected}) || {selected} = "ALL" || IsBlank({desc}), "", " \u00b7 " & '
            f'If(Len({desc}) > {cut}, Left({desc}, {cut} - 1) & "...", {desc}))')
    btn = button(f"btnKksSel{n}", text, f"Set(varKksPick, {n})", width="Parent.Width", height=40,
                 accessible=f'"Choose {label.lower()}"', icon="ChevronDown",
                 display_mode=f"If({enabled}, DisplayMode.Edit, DisplayMode.Disabled)")
    btn.props["Layout"] = "ButtonLayout.IconAfter"
    btn.props["AlignInContainer"] = "AlignInContainer.Stretch"
    btn.props["LayoutMinWidth"] = "0"
    return btn


PICK_W = "(Min(460, App.Width - 24) - 36)"
PICK_DESC_W = f"({PICK_W} - {2 * ROW_PAD} - {CODE_W} - {ROW_GAP} - {SCROLLBAR_W} - {GALLERY_RESERVE})"
PICK_SELECTED = ('Switch(varKksPick, 1, varKksL1, 2, Coalesce(varKksL2, "ALL"), '
                 'Coalesce(varKksL3, "ALL"))')
PICK_OPEN = f"IfError(varKksPick, 0) > 0 && {lay.below('Tablet')}"


def _pick_items():
    def one(keys):
        count = f"(CountRows({keys}) + 1)"
        return (f'ForAll(Sequence({count}), With({{k: If(Value = 1, "ALL", '
                f'Last(FirstN({keys}, Value - 1)).Value)}}, {{Value: k, Desc: If(k = "ALL", '
                f'"Show all", Coalesce(LookUp(colKksScope, L1 = "HOME" && Upper(Code) = k, Description), '
                f'LookUp(colKksScope, Upper(Code) = k, Description), ""))}}))')
    return (f"Switch(varKksPick, 1, {one('colKksL1Keys')}, 2, {one('colKksL2Keys')}, "
            f"{one('colKksL3Keys')})")


PICK_SELECT = (
    'If(\n    varKksPick = 1,\n    Set(varKksL1, ThisItem.Value);\n    Set(varKksL2, "");\n'
    '    Set(varKksL3, ""),\n    varKksPick = 2,\n'
    '    Set(varKksL2, If(ThisItem.Value = "ALL", "", ThisItem.Value));\n    Set(varKksL3, ""),\n'
    '    Set(varKksL3, If(ThisItem.Value = "ALL", "", ThisItem.Value))\n);\nSet(varKksPick, 0)')


def build_picker():
    """Mobilens vaelgerliste - [sloer, popup]. Kode + beskrivelse, der ombrydes."""
    from build_helpers import tap_backdrop
    vis = PICK_OPEN
    backdrop = tap_backdrop("conKksPickBackdrop", vis, "Set(varKksPick, 0)")
    title = text_ctrl("txtKksPickTitle",
                      'Switch(varKksPick, 1, "Letter", 2, "Group", "Subgroup")',
                      size=lay.SIZE_CARD_TITLE, weight="Semibold", height=26, wrap="false")
    chars = f"Max(8, RoundDown({PICK_DESC_W} / 7.5, 0))"
    rh = f"Max(1, RoundUp(Len(ThisItem.Desc) / {chars}, 0)) * {LINE_H} + 22"
    code = text_ctrl("txtKksPickCode", "ThisItem.Value", size=lay.SIZE_BODY, weight="Semibold",
                     height=20, width=CODE_W)
    desc = text_ctrl("txtKksPickDesc", "ThisItem.Desc", size=lay.SIZE_BODY, wrap="true",
                     height=f"Max(1, RoundUp(Len(ThisItem.Desc) / {chars}, 0)) * {LINE_H} + 1",
                     width=PICK_DESC_W)
    row = group("conKksPickRow", [code, desc], direction="Horizontal", gap=ROW_GAP, height=rh,
                width="Parent.TemplateWidth", align_items="Start",
                fill=f"If(ThisItem.Value = {PICK_SELECTED}, {C_PRIMARY_SOFT}, {C_CARD_BG})",
                pad=(11, ROW_PAD, 11, ROW_PAD))
    rule = row_rule("rctKksPickRule", 0)
    rule.props["Y"] = f"({rh}) - 1"
    hit = row_hit("btnKksPickHit", PICK_SELECT,
                  '"Choose " & ThisItem.Value & " " & ThisItem.Desc',
                  "Parent.TemplateWidth", f"({rh}) - 1")
    gal_h = "Max(160, Min(App.Height - 220, 480))"
    gal = Ctrl("galKksPick", "Gallery", variant="VariableHeight", props={
        "AccessibleLabel": '"Choices"',
        "BorderStyle": "BorderStyle.None", "Fill": C_CARD_BG, "FillPortions": "0",
        "Height": gal_h, "Items": _pick_items(), "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None", "Selectable": "false",
        "ShowScrollbar": "true", "TabIndex": "0", "TemplatePadding": "0",
        "TemplateSize": "42", "Width": "Parent.Width",
    }, children=[row, rule, hit], h=gal_h)
    close = button("btnKksPickClose", '"Close"', "Set(varKksPick, 0)",
                   width=fit_button_width('"Close"'), height=36)
    footer = group("conKksPickFooter", [close], direction="Horizontal", gap=8,
                   height=36, justify="End", align_items="Center")
    modal = group("conKksPickModal", [title, gal, footer], direction="Vertical", gap=12,
                  fill=C_MODAL_BG, border_color=C_PRIMARY_SOFT, radius=lay.RADIUS_MODAL,
                  pad=(18, 18, 18, 18), width="Min(460, App.Width - 24)",
                  drop_shadow="ExtraBold", visible=vis)
    modal.props["X"] = "(App.Width - Self.Width) / 2"
    modal.props["Y"] = "Max(12, (App.Height - Self.Height) / 3)"
    return [backdrop, modal]


def build_browse():
    from layout_tokens import below, at_least
    wide = at_least("Tablet")
    l1 = _lane(1, "LETTER", "colKksL1Keys", "varKksL1 = Self.Text",
               'Set(varKksL1, Self.Text);\nSet(varKksL2, "");\nSet(varKksL3, "")', 50,
               visible=wide)
    l2 = _lane(2, "GROUP", "colKksL2Keys",
               'If(Self.Text = "ALL", IsBlank(varKksL2), varKksL2 = Self.Text)',
               'Set(varKksL2, If(Self.Text = "ALL", "", Self.Text));\n'
               'Set(varKksL3, "")', 56,
               note="KksNote2", visible=wide)
    l3 = _lane(3, "SUBGROUP", "colKksL3Keys",
               'If(Self.Text = "ALL", IsBlank(varKksL3), varKksL3 = Self.Text)',
               'Set(varKksL3, If(Self.Text = "ALL", "", Self.Text))', 56,
               note="KksNote3", visible=f"KksHasL3 && {wide}")
    m1 = _level_menu(1, "Letter", "colKksL1Keys", "varKksL1", None, "true")
    m2 = _level_menu(2, "Group", "colKksL2Keys", "varKksL2", None,
                     'varKksL1 <> "ALL" && CountRows(colKksL2Keys) > 0')
    m3 = _level_menu(3, "Subgroup", "colKksL3Keys", "varKksL3", None,
                     '!IsBlank(varKksL2) && CountRows(colKksL3Keys) > 0')
    m3.props["Visible"] = f"KksHasL3 && {below('Tablet')}"
    m3.vis = m3.props["Visible"]
    for m in (m1, m2):
        m.props["Visible"] = below("Tablet")
        m.vis = m.props["Visible"]
    return card("conKksBrowseCard", [_key_tabs(), l1, l2, l3, m1, m2, m3, _search_row()], gap=12)


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

UP = None


def _crumbs():
    crumbs = []
    # (navn, tekst, handling, synlig, bredde, "her er du", etiket)
    spec = [
        ("All", '"All"', CLEAR_LEVELS, None, 44, 'varKksL1 = "ALL"', '"All sections"'),
        ("L1", '"› " & varKksL1', 'Set(varKksL2, "");\nSet(varKksL3, "")',
         'varKksL1 <> "ALL"', 48, "IsBlank(varKksL2)", '"Letter " & varKksL1'),
        ("L2", '"› " & varKksL2', 'Set(varKksL3, "")', "!IsBlank(varKksL2)", 56,
         "IsBlank(varKksL3)", '"Group " & varKksL2'),
        ("L3", '"› " & varKksL3', "false", "!IsBlank(varKksL3)", 72, "true",
         '"Subgroup " & varKksL3'),
    ]
    for name, text, act, vis, w, here, label in spec:
        b = button(f"btnKksCrumb{name}", text, act, width=w, height=32, visible=vis,
                   accessible=label)
        b.props["Size"] = str(lay.SIZE_SMALL)
        crumbs.append(_link(b, here))
    return flow_row("conKksCrumbs", crumbs, RES_W, gap=2)


def build_results():
    path_h = (f"Max(20, RoundUp(Len(KksTitle) / Max(24, RoundDown({RES_W} / 7.5, 0)), 0) "
              f"* {LINE_H + 1})")
    path = text_ctrl("txtKksPath", "KksTitle", size=lay.SIZE_BODY, color=C_PRIMARY,
                     wrap="true", height=path_h)

    def head_cell(name, text, w):
        return text_ctrl(name, f'"{text}"', size=lay.SIZE_MICRO, weight="Semibold",
                         color=C_MUTED, height=20, width=w)

    head = group("conKksTableHead", [head_cell("txtKksHeadCode", "CODE", CODE_W),
                                     head_cell("txtKksHeadDesc", "DESCRIPTION", DESC_W)],
                 direction="Horizontal", gap=ROW_GAP, height=34, align_items="Center",
                 fill=C_MUTED_BG, border_color=C_DIVIDER, radius=10,
                 pad=(0, ROW_PAD, 0, ROW_PAD))

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
    info = button("btnKksRowMore", '"More"',
                  'Set(varKksDetailCode, ThisItem.Code);\nSet(varKksDetailText, ThisItem.Description);\n'
                  'Set(varKksDetailOn, true)',
                  width=30, height=30, icon="Info", accessible='"Show the full description"',
                  visible=f"{lay.below('Tablet')} && {LONG_DESC}")
    info.props["Layout"] = "ButtonLayout.IconOnly"
    info.props["X"] = f"Parent.TemplateWidth - {ROW_PAD} - 30"
    info.props["Y"] = f"({rh}) - 33"
    info.props["LayoutMinWidth"] = "30"
    gal_h = f"If(CountRows(colKksResults) = 0, 0, {TABLE_MAX_H})"
    gal = Ctrl("galKksRows", "Gallery", variant="VariableHeight", props={
        "AccessibleLabel": '"KKS codes. Select a row to go to its place."',
        "BorderStyle": "BorderStyle.None", "Fill": C_CARD_BG, "FillPortions": "0",
        "Height": gal_h, "Items": "colKksResults", "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None", "Selectable": "false",
        "ShowScrollbar": "true", "TabIndex": "0", "TemplatePadding": "0",
        "TemplateSize": "42", "Width": "Parent.Width",
    }, children=[row, rule, hit], h=gal_h, vis="CountRows(colKksResults) > 0")

    empty = text_ctrl(
        "txtKksEmpty",
        'If(IsEmpty(colKksScope), If(IfError(varKksTried, false), "The KKS lists could not be loaded. '
        f'Check access to {cfg.L_FUNCTION} and {cfg.L_FLKEY}.", "Loading KKS keys..."), '
        '"No codes match.")',
        size=lay.SIZE_BODY, weight="Semibold", height=40, wrap="true",
        color=f"If(IsEmpty(colKksScope) && IfError(varKksTried, false), {C_INVALID_FG}, {C_MUTED})",
        visible="CountRows(colKksResults) = 0")
    res = card("conKksResultsCard", [_crumbs(), path, head, gal, empty], gap=8)
    narrow = lay.below("Tablet")
    res.props["Fill"] = f"If({narrow}, {C_TRANSPARENT}, {C_CARD_BG})"
    res.props["BorderThickness"] = f"If({narrow}, 0, 1)"
    res.props["PaddingLeft"] = f"If({narrow}, 0, {lay.CARD_PAD})"
    res.props["PaddingRight"] = f"If({narrow}, 0, {lay.CARD_PAD})"
    for side in ("TopLeft", "TopRight", "BottomLeft", "BottomRight"):
        res.props[f"Radius{side}"] = f"If({narrow}, 0, {lay.RADIUS_CARD})"
    return res


def build_detail():
    per_line = "Max(20, RoundDown((Min(460, App.Width - 24) - 36) / 7.5, 0))"
    return text_modal("KksDetail", "varKksDetailOn", "varKksDetailCode", "varKksDetailText",
                      f"Max(20, RoundUp(Len(varKksDetailText) / {per_line}, 0) * {LINE_H})")


def build_loading():
    return loading_overlay("imgKksLoading", "varKksLoading", "Loading KKS keys, please wait")
