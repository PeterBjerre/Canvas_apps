# -*- coding: utf-8 -*-
"""
KKS-opslagets skaerm: delene, formlerne og hentningen.

    [Function key][Aggregate key][Component key]   [Search Functional Locations]
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
from gen_screen import (Ctrl, C_CARD_BG, C_DIVIDER, C_INFO_BG,
                        C_INFO_FG, C_INVALID_FG, C_MUTED, C_MUTED_BG, C_PRIMARY,
                        C_PRIMARY_SOFT, C_MODAL_BG, C_TRANSPARENT, C_WHITE)
from build_helpers import (fluent, fluent_icon, button, card, concurrent, fit_button_width, flow_row, group, grow,
                           loading_overlay, row_hit, row_rule, text_ctrl,
                           text_modal, top_bar, app_frame, text_input,
                           ensure_hit, hit_size)
from fl_picker import HEIGHT as SEARCH_H, ROW_PAD as SEARCH_PAD
import layout_tokens as lay
from layout_tokens import SHELL_W, SCROLLBAR_W, GALLERY_RESERVE
import mobile
from gen_screen import SCROLLBAR_NOT_MOBILE, MOBILE_GALLERY_RESERVE

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
# Kopier-ikonet yderst til hoejre i raekken (UX-review, KKS) - beskrivelsen
# giver plads til det.
COPY_W = 32
# Kopier-knappen er H.hit bred (44 under Desktop - UX-review F6, regel 40).
DESC_W = (f"({TABLE_W} - {2 * ROW_PAD} - {CODE_W} - {ROW_GAP} - "
          f"Max({COPY_W}, {lay.HIT}) - {ROW_GAP})")
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


# --- Telefonen: raekkerne som kort (issue #508) -----------------------------
#
#   ABA ................................. [kopier]
#   Beskrivelsen i hele kortets bredde, ombrudt
#   -------------------------------------------------
#
# Under Tablet stod koden i en 72 px kolonne og beskrivelsen klemt ved siden
# af (ca. 110 px ved 320). Nu staar koden og kopier-knappen paa linjen
# foroven, og beskrivelsen faar hele bredden under. Samme kontroller, samme
# navne og samme klik - kun placeringen er en anden (mobile.gallery_place).
# Galleriet har ingen egen scroll paa en telefon: det er saa hoejt som de
# viste kort (siden scroller), og "Show more" viser flere (mobile.show_more).
M_TW = f"({SHELL_W} - {MOBILE_GALLERY_RESERVE})"   # skabelonen paa en telefon
M_PAD = 12
M_TOP = 40           # kodelinjen: kopier-knappen (44) med lidt luft under
M_DESC_W = f"({M_TW} - {2 * M_PAD})"
M_CHARS = f"Max(14, RoundDown({M_DESC_W} / 7.5, 0))"
SHOW_VAR = "varKksShowN"
SHOW_N = mobile.show_count(SHOW_VAR)


def desc_h_m(ref):
    return f"Max(1, RoundUp(Len({ref}) / {M_CHARS}, 0)) * {LINE_H} + 1"


def row_h_m(ref):
    return f"{M_TOP} + {desc_h_m(ref)} + 10"


def row_h(ref):
    return f"{desc_h(ref)} + 22"


# ---------------------------------------------------------------------------
# Tilstand
# ---------------------------------------------------------------------------
CLEAR_LEVELS = 'Set(varKksL1, "ALL");\nSet(varKksL2, "");\nSet(varKksL3, "")'
# Soegeteksten er feltets egen tekst (KksQuery) - at rydde den er at
# nulstille feltet. Ingen variabel at holde i trit (issue #478).
CLEAR_QUERY = 'Reset(inpKksFind)'
# Mindste soegetekst: eet tegn filtrerer allerede (issue #478).
SEARCH_MIN = 1

# FL-soegningens popup (issue #295) - dens EGNE variabler, saa aabning og
# lukning aldrig roerer KKS-filtrene, den valgte kode eller resultaterne.
FL_OPEN = "varKksFlOn"
FL_INIT = (
    'Set(varKksFlOn, false);\n'
    'Set(varKksFlBusy, false);\n'
    'Set(varKksFlQuery, "");\n'
    'Set(varKksFlLast, "");\n'
    'Set(varKksFlMsg, "");\n'
    'Set(varKksFlPick, "")'
)

# Foerste besoeg: tilstanden saettes, hvis den ikke findes. Staar i
# skaermens OnVisible og ikke i App.OnStart, saa den ogsaa gaelder i BIO
# SAP, hvor App.OnStart ikke kender domaenerne.
INIT_STATE = (
    "If(\n"
    "    IsBlank(varKksKey),\n"
    '    Set(varKksKey, "function");\n'
    "    " + CLEAR_LEVELS.replace("\n", "\n    ") + ";\n"
    '    Set(varKksDetailCode, "");\n'
    '    Set(varKksDetailText, "");\n'
    '    Set(varKksDetailOn, false);\n'
    '    Set(varKksPick, 0);\n'
    "    " + FL_INIT.replace("\n", "\n    ") + "\n"
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
# FL-soegningens resultat - samme skema som colDomFl (tools/build_flsearch.py).
FL = {"Code": '""', "Description": '""', "Display": '""', "Maintainable": "false",
      "Level": '""'}


def collections():
    out = [("colKksFunction", ROW), ("colKksAggregate", ROW), ("colKksComponent", ROW),
           ("colKksAggregateRaw", RAW), ("colKksComponentRaw", RAW), ("colKksFnAll", FN),
           ("colKksFl", FL)]
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


# Noegletypens navn (Function/Aggregate/Component) foerst i overskriften (UX-review).
KEY_SW = ("Switch(varKksKey, " + ", ".join('"%s", "%s"' % (k, t) for k, t, _s in cfg.KEYS)
          + ', "")')

FORMULAS = f'''// KKS-opslaget (KKS App/build/kks_parts.py). Samlingerne hentes i
// skaermens OnVisible; alt herunder regnes i hukommelsen.
// varKksLoaded staar med for at tvinge en genberegning, naar noeglerne er hentet.
colKksScope = With({{ready: varKksLoaded}}, Switch(varKksKey, "aggregate", colKksAggregate, "component", colKksComponent, colKksFunction));
KksHasL3 = varKksKey = "function";
colKksBase = If(varKksL1 = "ALL", colKksScope, Filter(colKksScope, L1 = varKksL1));
// Soegningen (issue #478): feltets tekst, mens man skriver - ingen timer og
// ingen variabel imellem. Lower paa begge sider: uafhaengig af store og
// smaa bogstaver, ogsaa Æ/æ, Ø/ø og Å/å. Kode OG beskrivelse; det valgte
// noegleomraade og bogstav (colKksBase) gaelder stadig.
KksQuery = With({{ _t: Trim(inpKksFind.Text) }}, If(Len(_t) >= {SEARCH_MIN}, _t, ""));
colKksBaseQ = If(IsBlank(KksQuery), colKksBase, With({{ _q: Lower(KksQuery) }}, Filter(colKksBase, _q in Lower(Code) || _q in Lower(Description))));
// Bogstaverne (issue #164): kun de bogstaver, der har mindst een gruppe
// (niveau 2) i den valgte noegletype - regnet af samme betingelse som
// colKksL2Keys, i hukommelsen, pr. type. Et bogstav uden grupper (fx
// funktionsnoeglen D, der ikke bruges, eller komponentnoeglen -A) vises
// ikke; raekken findes stadig i ALL og i soegningen.
colKksL1Keys = Sort(Distinct(Filter(colKksScope, L1 <> "HOME" && Len(P2) = 2 && StartsWith(P2, L1)), L1), Value);
colKksL2Keys = Sort(Distinct(Filter(colKksBaseQ, varKksL1 <> "ALL" && Len(P2) = 2 && StartsWith(P2, varKksL1)), P2), Value);
colKksL2Rows = If(IsBlank(varKksL2), colKksBaseQ, Filter(colKksBaseQ, P2 = varKksL2));
colKksL3Keys = Sort(Distinct(Filter(colKksL2Rows, KksHasL3 && !IsBlank(varKksL2) && Len(P3) = 3 && StartsWith(P3, varKksL2)), P3), Value);
colKksL3Rows = If(!KksHasL3 || IsBlank(varKksL3), colKksL2Rows, Filter(colKksL2Rows, P3 = varKksL3));
colKksResults = If(varKksL1 = "ALL" && IsBlank(KksQuery) && KksHasL3, Filter(colKksScope, L1 = "HOME"), colKksL3Rows);
KksNote2 = If(varKksL1 = "ALL", "", CountRows(colKksL2Keys) = 0, If(IsBlank(KksQuery), "No groups under this letter.", "No groups match the search."), "");
KksNote3 = If(!KksHasL3, "", varKksL1 = "ALL", "", IsBlank(varKksL2), "", CountRows(colKksL3Keys) = 0, If(IsBlank(KksQuery), "No subgroups under this group.", "No subgroups match the search."), "");
KksHeadL1 = If(varKksL1 = "ALL", "", Coalesce(LookUp(colKksScope, L1 = "HOME" && Upper(Code) = varKksL1, Description), LookUp(colKksBase, Upper(Code) = varKksL1, Description), LookUp(colKksBase, Len(P2) = 2 && Upper(Code) = P2 && StartsWith(P2, varKksL1), Description), ""));
KksHeadL2 = If(IsBlank(varKksL2), "", Coalesce(LookUp(colKksScope, Upper(Code) = varKksL2, Description), ""));
KksHeadL3 = If(IsBlank(varKksL3), "", Coalesce(LookUp(colKksScope, Upper(Code) = varKksL3, Description), ""));
KksTitle = {KEY_SW} & " / " & If(varKksL1 = "ALL", "All groups", varKksL1 & If(IsBlank(varKksL2) && IsBlank(varKksL3) && !IsBlank(KksHeadL1), " - " & {_cap("KksHeadL1")}, "") & If(IsBlank(varKksL2), "", " / " & varKksL2 & If(IsBlank(varKksL3) && !IsBlank(KksHeadL2), " - " & {_cap("KksHeadL2")}, "")) & If(IsBlank(varKksL3), "", " / " & varKksL3 & If(!IsBlank(KksHeadL3), " - " & {_cap("KksHeadL3")}, ""))) & If(IsBlank(KksQuery), "", " - search results") & " \u00b7 " & Text(CountRows(colKksResults)) & If(CountRows(colKksResults) = 1, " code", " codes");'''



# ---------------------------------------------------------------------------
# Delene
# ---------------------------------------------------------------------------
def _phone_h(c, h):
    """En anden hoejde paa en telefon (issue #508) - FOER foraelderen bygges,
    saa dens hoejde regner med den. Tablet og desktop er uaendrede."""
    c.props["Height"] = lay.mobile_or(h, c.props["Height"])
    c.h = c.props["Height"]
    return c


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


# Sideoverskriften - den SAMME som paa de andre sider (issue #164):
# build_helpers.top_bar med domaeneikonet fra sidebaren (tools/icons.py,
# noeglen "kks") i rammen build_helpers.app_frame. Foer stod skaermen i sin
# egen ramme uden overskrift. Titel og undertitel staar i kks_config.
def build_header():
    return top_bar(P, f'"{cfg.TITLE}"', f'"{cfg.SUBTITLE}"', [], icon=cfg.APP_KEY)


def frame(header, body):
    """Rammen er app_frame som paa de andre sider: overskriften staar fast,
    kroppen scroller.

    Under Tablet viser top_bar hverken ikon, titel eller undertitel - dem
    viser mobilens topbjaelke (tools/side_nav.py) - og KKS-siden har ingen
    handlingsknapper i bjaelken. Headeren ville da vaere et tomt baand, saa
    den er skjult paa mobil, og kroppen faar hoejden. Hoejden afhaenger
    stadig kun af skaermbredden (check_layout regel 23b)."""
    root = app_frame(P, header, body)
    head, main = root.children
    wide = lay.at_least("Tablet")
    head.h = f"If({wide}, {head.h}, 0)"
    head.props["Height"] = head.h
    head.vis = wide
    for c in head.children:
        c.vis = wide
    main.props["Height"] = f"Parent.Height - ({head.h})"
    return root


# DEN OEVERSTE RAEKKE (issue #345)
#
#   bred:   [Function][Aggregate][Component]  ........  [Search Functional Locations]
#   smal:   [Function ][Aggregate][Component]
#           [      Search Functional Locations       ]
#
# HVORFOR KNAPPERNE VAR VAEK
# --------------------------
# Issue #295 lagde fanerne i deres egen flow_row (conKksKeys) INDE i en
# anden flow_row (conKksTopRow) - to lag containere, der begge skiftede
# retning og justering med en formel, og knapperne med AlignInContainer.
# Center i det inderste. Det er praecis den konstruktion, der gjorde
# Issue Boards vaerktoejslinje (issue #229 -> #244) og topbjaelken til
# tomme flader i den udgivne app: Studio tegner de indlejrede knapper
# forskudt nedad, og LayoutOverflow.Hide skjuler dem. Hoejderne gik op -
# conKksKeys var 32 px og knapperne 32 px - saa check_layout var groen.
# Det var den eneste flow_row i en flow_row i hele BIO SAP. Det kom ud
# sammen med de moderne kontroller (#324-#332), men har intet med dem at
# goere: knapperne har vaeret ModernButton hele tiden.
#
# NU: knapperne staar DIREKTE i een fast, vandret raekke direkte i kortet -
# som foer #295, og som hubbens filterlinje og listernes vaerktoejslinjer
# (conDomRowsTop). Ingen indlejret container med knapper i, ingen retning
# som formel. Er der plads (TOP_WIDE), skubber en tom, udregnet mellemrums-
# gruppe (build_helpers.grow) FL-knappen ud til hoejre. Er der ikke plads
# (telefon og smal tablet), staar FL-knappen i fuld bredde direkte i kortet
# under raekken - som en anden kontrol, fordi en kontrol ikke kan flytte
# mellem to containere. Begge knapper goer det samme.
TOP_GAP = 8


def _key_tabs():
    tabs = []
    for key, text, _sub in cfg.KEYS:
        # Soegeteksten bliver staaende: den gaelder i det nye noegleomraade
        # (issue #478). Bogstav og grupper nulstilles som foer.
        b = button(f"btnKksKey{key.title()}", f'"{text}"',
                   f'Set(varKksKey, "{key}");\n{CLEAR_LEVELS}',
                   width=TAB_W, height=32,
                   accessible=f'"Show {text.lower()}s"')
        b.props["Size"] = f"If({lay.below('Tablet')}, {lay.SIZE_MICRO}, {lay.SIZE_SMALL})"
        b.props["Width"] = (f"If({lay.below('Tablet')}, ({CARD_W} - {TOP_GAP * (len(cfg.KEYS) - 1)})"
                            f" / {len(cfg.KEYS)}, {TAB_W})")
        # Fast i raekken - den skifter aldrig retning.
        b.props["LayoutMinWidth"] = b.props["Width"]
        _phone_h(b, mobile.TOUCH)      # touch paa en telefon (issue #508)
        tabs.append(_selected(b, f'varKksKey = "{key}"', radius=14))
    return tabs


FL_BTN_TEXT = '"Search Functional Locations"'
FL_BTN_W = fit_button_width(FL_BTN_TEXT, size=lay.SIZE_SMALL) + 24     # + Search-ikonet

# FL-knappen staar til hoejre for fanerne, naar de tre faner, knappen og
# mellemrummene kan staa paa een linje i kortet. Kun fra Tablet: under
# Tablet er fanerne en tredjedel af kortet hver og fylder hele linjen.
# (Bredden staar foerst: check_layouts regnemaskine kan ikke laese "&& (".)
TOP_NEED = len(cfg.KEYS) * TAB_W + TOP_GAP * len(cfg.KEYS) + FL_BTN_W
TOP_WIDE = f"({CARD_W}) >= {TOP_NEED} && {lay.at_least('Tablet')}"
TOP_NARROW = f"({CARD_W}) < {TOP_NEED} || {lay.below('Tablet')}"


def _fl_button(name, visible, width):
    """Knappen, der aabner FL-soegningen (issue #295). Den roerer intet af
    KKS-opslagets tilstand."""
    b = button(name, FL_BTN_TEXT, f"Set({FL_OPEN}, true)",
               width=width, height=32, icon="Search",
               accessible='"Search Functional Locations in SAP"', visible=visible,
               tooltip='"Search Functional Locations in SAP"',
               display_mode="DisplayMode.Edit")
    b.props["Size"] = str(lay.SIZE_SMALL)
    # Issue #478: hover-, tryk- og fokus-tilstandene regner Fluent ud af
    # BasePaletteColor - som fanerne ved siden af (_selected). Uden den
    # stod knappen ens i alle tilstande og saa ud, som om den ikke kunne
    # klikkes.
    b.props["BasePaletteColor"] = C_PRIMARY
    return _soft(b)


def _top_row():
    """Function / Aggregate / Component og - naar der er plads - FL-soegningen
    yderst til hoejre. Se forklaringen over TOP_GAP."""
    tabs = _key_tabs()
    gap = grow(group("conKksTopGap", [], direction="Horizontal", height=0))
    gap.props["Visible"] = TOP_WIDE
    gap.vis = TOP_WIDE
    fl = _fl_button("btnKksFlOpen", TOP_WIDE, FL_BTN_W)
    fl.props["LayoutMinWidth"] = str(FL_BTN_W)
    row = group("conKksTopRow", tabs + [gap, fl], direction="Horizontal", gap=TOP_GAP,
                height=lay.mobile_or(mobile.TOUCH, 32), align_items="Center")
    return row


def _fl_button_narrow():
    """FL-knappen under fanerne, naar den ikke kan staa paa deres linje.
    Direkte i kortet (lodret, Stretch): fuld bredde."""
    return _phone_h(_fl_button("btnKksFlOpenNarrow", TOP_NARROW, FL_BTN_W), mobile.TOUCH)


SEARCH_ROW_W = f"If({lay.below('Tablet')}, {CARD_W}, Min({CARD_W}, 420))"
# Soegningen (UX-review, KKS): et tekstfelt med soegeikon og et kryds, der
# rydder det. Search og Reset er vaek; et klik paa en raekke gaar stadig til
# dens plads (ROW_SELECT).
#
# ISSUE #478 - SOEGNINGEN FILTREREDE IKKE
# --------------------------------------
# Foer gik teksten gennem en timer (tmrKksFindApply) til varKksQuery, og
# feltets Default var varKksQuery:
#   * Timeren havde Repeat = false og intet Reset - den eneste i appen, der
#     startes af en Start-formel uden at blive nulstillet (act_timer har
#     Reset netop derfor). En timer, der er loebet til ende, staar ved sin
#     Duration; Start kan skifte, uden at den koerer igen, og saa naaede
#     teksten aldrig formlerne.
#   * Default = varKksQuery gav en sloejfe: naar timeren skrev variablen,
#     nulstillede feltet sig til den trimmede tekst og aad et mellemrum, man
#     lige havde skrevet.
# Nu er der hverken timer eller variabel: den navngivne formel KksQuery
# laeser feltets tekst direkte, og TriggerOutput.Delayed er den indbyggede
# korte pause efter sidste tastetryk - som Issue Boards soegefelt
# (inpIbSearch). Default er tom, saa Reset(inpKksFind) rydder feltet.
SEARCH_ICON = 20


def _search_row():
    # Lupen er Fluents "Search" (issue #306) - pynt ved feltet, ingen klik.
    ico = fluent_icon("icoKksFindIcon", fluent("search"), C_MUTED, '"Search"',
                      size=SEARCH_ICON)
    ico.props["AlignInContainer"] = "AlignInContainer.Center"
    ico.props["LayoutMinWidth"] = str(SEARCH_ICON)
    inp = text_input("inpKksFind", '""', placeholder='"Search code or description"',
                     height=SEARCH_H, label='"Search KKS codes and descriptions"')
    inp.props["TriggerOutput"] = "TriggerOutput.Delayed"
    _phone_h(inp, mobile.TOUCH)
    grow(inp)
    # Krydset rydder kun teksten - noegleomraadet og bogstavet bliver staaende.
    clear = button("btnKksFindClear", '""', CLEAR_QUERY, width=SEARCH_H, height=SEARCH_H,
                   icon="Dismiss", accessible='"Clear the search"',
                   tooltip='"Clear the search"', visible="!IsBlank(inpKksFind.Text)")
    clear.props["Layout"] = "ButtonLayout.IconOnly"
    clear.props["BorderColor"] = C_TRANSPARENT
    clear.props["LayoutMinWidth"] = str(SEARCH_H)
    ensure_hit(clear)                  # H.hit (UX-review F6, regel 40)
    row = group("conKksFindRow", [inp, clear, ico], direction="Horizontal", gap=8,
                height=f"{hit_size(SEARCH_H)} + {2 * SEARCH_PAD}", pad=(SEARCH_PAD, 0, SEARCH_PAD, 0),
                align_items="Center", width=SEARCH_ROW_W)
    return group("conKksFindWrap", [row], direction="Vertical", gap=0,
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
        # IfError: Index paa en tom tabel giver en fejl-banner ("cannot be
        # called with an empty table"), naar noeglerne genberegnes, mens
        # galleriet endnu viser de gamle raekker. Saa vises knappen tom.
        text = (f'If({shown}, If({idx} = 1, "ALL", '
                f'IfError(Index({keys}, {idx} - 1).Value, "")), "")')
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
    btn = button(f"btnKksSel{n}", text, f"Set(varKksPick, {n})", width="Parent.Width",
                 height=lay.mobile_or(mobile.TOUCH, 40),
                 accessible=f'"Choose {label.lower()}"', icon="ChevronDown",
                 display_mode=f"If({enabled}, DisplayMode.Edit, DisplayMode.Disabled)")
    btn.props["Layout"] = "ButtonLayout.IconAfter"
    btn.props["AlignInContainer"] = "AlignInContainer.Stretch"
    btn.props["LayoutMinWidth"] = "0"
    return btn


# Paa en telefon er vaelgeren et ark i (naesten) hele skaermen
# (mobile.mobile_popup, issue #508): bredden er lay.popup_w, og siderne er
# polstret med MOBILE_CARD_PAD.
PICK_W = lay.mobile_or(f"(App.Width - {2 * lay.MOBILE_POP_MARGIN + 2 * lay.MOBILE_CARD_PAD})",
                       "(Min(460, App.Width - 24) - 36)")
PICK_DESC_W = f"({PICK_W} - {2 * ROW_PAD} - {CODE_W} - {ROW_GAP} - {SCROLLBAR_W} - {GALLERY_RESERVE})"
PICK_SELECTED = ('Switch(varKksPick, 1, varKksL1, 2, Coalesce(varKksL2, "ALL"), '
                 'Coalesce(varKksL3, "ALL"))')
PICK_OPEN = f"IfError(varKksPick, 0) > 0 && {lay.below('Tablet')}"


def _pick_items():
    def one(keys):
        count = f"(CountRows({keys}) + 1)"
        return (f'ForAll(Sequence({count}), With({{k: If(Value = 1, "ALL", '
                f'IfError(Index({keys}, Value - 1).Value, ""))}}, {{Value: k, Desc: If(k = "ALL", '
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
    from build_helpers import tap_backdrop, popup_head
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
    # Telefonen: listen fylder arket ned til bunden (hovedet 44, mellemrummet
    # 12, arkets polstring 2 x 18 og margen 2 x 8) - den er arkets eneste
    # scroll, og siden bag er laast af sloeret.
    gal_h = lay.mobile_or(f"Max(160, App.Height - {2 * lay.MOBILE_POP_MARGIN + 36 + 44 + 12})",
                          "Max(160, Min(App.Height - 220, 480))")
    gal = Ctrl("galKksPick", "Gallery", variant="VariableHeight", props={
        "AccessibleLabel": '"Choices"',
        "BorderStyle": "BorderStyle.None", "Fill": C_CARD_BG, "FillPortions": "0",
        "Height": gal_h, "Items": _pick_items(), "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None", "Selectable": "false",
        "ShowScrollbar": "true", "TabIndex": "0", "TemplatePadding": "0",
        "TemplateSize": "42", "Width": "Parent.Width",
    }, children=[row, rule, hit], h=gal_h)
    # Close oeverst til hoejre, ingen bund (issue #237).
    head = popup_head("conKksPickHead", title, "btnKksPickClose", "Set(varKksPick, 0)")
    modal = group("conKksPickModal", [head, gal], direction="Vertical", gap=12,
                  fill=C_MODAL_BG, border_color=C_PRIMARY_SOFT, radius=lay.RADIUS_MODAL,
                  pad=(18, 18, 18, 18), width="Min(460, App.Width - 24)",
                  drop_shadow="ExtraBold", visible=vis)
    modal.props["X"] = "(App.Width - Self.Width) / 2"
    modal.props["Y"] = "Max(12, (App.Height - Self.Height) / 3)"
    mobile.mobile_popup(modal, 460, 24, top=True)
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
               note="KksNote2", visible=f'{wide} && varKksL1 <> "ALL"')
    l3 = _lane(3, "SUBGROUP", "colKksL3Keys",
               'If(Self.Text = "ALL", IsBlank(varKksL3), varKksL3 = Self.Text)',
               'Set(varKksL3, If(Self.Text = "ALL", "", Self.Text))', 56,
               note="KksNote3", visible=f"KksHasL3 && {wide} && !IsBlank(varKksL2)")
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
    return card("conKksBrowseCard", [_top_row(), _fl_button_narrow(), l1, l2, l3, m1, m2, m3, _search_row()], gap=12)


# Et klik paa en raekke gaar til dens plads i hierarkiet og rydder
# soegningen - som den oprindelige apps galKksRowsB.OnSelect. Er raekkens
# bogstav ikke i colKksL1Keys (ingen grupper, issue #164), gaar klikket til
# ALL, og en kode, der ikke begynder med bogstavet (noterne "*" og "**"),
# vaelger ingen gruppe - saa staar der aldrig et valg, der ikke er en knap.
ROW_SELECT = f'''With(
    {{c: Upper(ThisItem.Code), s: ThisItem.L1}},
    With(
        {{isTop: Len(c) = 1 && !IsBlank(LookUp(colKksL1Keys, Value = c))}},
        With(
            {{l1: If(isTop, c, With({{t: If(s = "HOME", Left(c, 1), s)}}, If(!IsBlank(LookUp(colKksL1Keys, Value = t)), t, "ALL")))}},
            Set(varKksL1, l1);
            Set(varKksL2, If(l1 = "ALL" || isTop || Len(c) < 2 || !StartsWith(c, l1), "", Left(c, 2)));
            Set(varKksL3, If(l1 = "ALL" || isTop || !KksHasL3 || Len(c) < 3 || !StartsWith(c, l1), "", Left(c, 3)));
            {CLEAR_QUERY.replace(chr(10), chr(10) + "            ")}
        )
    )
)'''

UP = None


def _crumbs():
    crumbs = []
    # (navn, tekst, handling, synlig, bredde, "her er du", etiket)
    spec = [
        ("All", '"All groups"', CLEAR_LEVELS, 'varKksL1 <> "ALL"', 84, 'varKksL1 = "ALL"',
         '"All groups"'),
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
        _phone_h(b, mobile.TOUCH)
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
    # Kortene paa en telefon har ingen kolonner - overskriften er vaek.
    mobile.hide_on_mobile(head)

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
    # KOPIER KODEN (UX-review, KKS): brugeren skrev den af. Copy() laegger
    # den i udklipsholderen, og beskeden siger "Copied" (tools/toast.py).
    copy = button("btnKksRowCopy", '""',
                  'Copy(ThisItem.Code);\nNotify("Copied " & ThisItem.Code & " to the clipboard.", '
                  'NotificationType.Success)',
                  width=COPY_W, height=COPY_W, icon="Copy",
                  accessible='"Copy " & ThisItem.Code', tooltip='"Copy " & ThisItem.Code')
    copy.props["Layout"] = "ButtonLayout.IconOnly"
    copy.props["BorderColor"] = C_TRANSPARENT
    ensure_hit(copy)
    copy.props["X"] = f"Parent.TemplateWidth - {ROW_PAD} - Self.Width"
    copy.props["Y"] = "0"
    copy.props["_OnTop"] = "true"
    # Telefonen (issue #508): kortet - se M_TW.
    rh_m = row_h_m("ThisItem.Description")
    mobile.gallery_place(row, w=M_TW, h=rh_m)
    mobile.gallery_place(code, x=M_PAD, y=12, w=f"{M_TW} - {2 * M_PAD} - {lay.HIT_TOUCH} - 8",
                         h=20)
    mobile.gallery_place(desc, x=M_PAD, y=M_TOP, w=M_DESC_W, h=desc_h_m("ThisItem.Description"))
    mobile.gallery_place(rule, y=f"({rh_m}) - 1", w=M_TW)
    mobile.gallery_place(hit, w=M_TW, h=f"({rh_m}) - 1")
    copy.props["X"] = lay.mobile_or(f"{M_TW} - 4 - Self.Width", copy.props["X"])
    n = "CountRows(colKksResults)"
    shown = f"FirstN(colKksResults, {SHOW_N})"
    gal_h = lay.mobile_or(f"If({n} = 0, 0, Sum({shown}, {row_h_m('ThisRecord.Description')}))",
                          f"If({n} = 0, 0, {TABLE_MAX_H})")
    gal = Ctrl("galKksRows", "Gallery", variant="VariableHeight", props={
        "AccessibleLabel": '"KKS codes. Select a row to go to its place."',
        "BorderStyle": "BorderStyle.None", "Fill": C_CARD_BG, "FillPortions": "0",
        "Height": gal_h, "Items": lay.mobile_or(shown, "colKksResults"), "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None", "Selectable": "false",
        "ShowScrollbar": SCROLLBAR_NOT_MOBILE, "TabIndex": "0", "TemplatePadding": "0",
        "TemplateSize": "42", "Width": "Parent.Width",
    }, children=[row, rule, hit, copy], h=gal_h, vis="CountRows(colKksResults) > 0")
    more = mobile.show_more("btnKksShowMore", SHOW_VAR, n, label="codes")

    empty = text_ctrl(
        "txtKksEmpty",
        'If(IsEmpty(colKksScope), If(IfError(varKksTried, false), "The KKS lists could not be loaded. '
        f'Check access to {cfg.L_FUNCTION} and {cfg.L_FLKEY}.", "Loading KKS keys..."), '
        '"No codes match.")',
        size=lay.SIZE_BODY, weight="Semibold", height=40, wrap="true",
        color=f"If(IsEmpty(colKksScope) && IfError(varKksTried, false), {C_INVALID_FG}, {C_MUTED})",
        visible="CountRows(colKksResults) = 0")
    res = card("conKksResultsCard", [_crumbs(), path, head, gal, more, empty], gap=8)
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
    """[sloer, hjul] (build_helpers.loading_overlay)."""
    return loading_overlay("imgKksLoading", "varKksLoading", "Loading KKS keys, please wait")


# ---------------------------------------------------------------------------
# FL-soegningen (issue #295)
# ---------------------------------------------------------------------------
# DEN SAMME live-soegning som i VH-plan, Equipments og Materials:
# tools/fl_picker.py (comboboks + Search + spinner, minimumslaengde og
# beskeder) og flowet i tools/build_flsearch.py. Intet er skrevet om - kun
# navnene er KKS-opslagets egne (Kks-praefikset), saa en soegning her aldrig
# roerer en anden skaerms vaelger. KKS-filtrene, den valgte kode og
# resultaterne staar uroert, naar popuppen aabnes og lukkes.
FL_W = "Min(560, App.Width - 24)"
# Paa en telefon er popuppen naesten hele bredden (mobile.mobile_popup,
# issue #508) - indholdet regner af den samme bredde.
FL_IN_W = lay.mobile_or(f"(App.Width - {2 * lay.MOBILE_POP_MARGIN + 2 * lay.MOBILE_CARD_PAD})",
                        f"({FL_W} - 36)")
FL_PICK = "varKksFlPick"
FL_SEL = f"LookUp(colKksFl, Code = {FL_PICK})"


def build_fl_search():
    """[sloer, popup]. Ligger efter sidebarens panel og de andre popups i
    skaermens boern - altsaa oven paa dem; kun ventespinneren ligger hoejere."""
    from build_helpers import tap_backdrop, popup_head
    from fl_picker import fl_picker
    from gen_screen import stack_height
    vis = f"IfError({FL_OPEN}, false)"
    close = f"Set({FL_OPEN}, false)"
    backdrop = tap_backdrop("conKksFlBackdrop", vis, close)
    title = text_ctrl("txtKksFlTitle", '"Search Functional Locations"',
                      size=lay.SIZE_CARD_TITLE, weight="Semibold", height=26, wrap="false")
    head = popup_head("conKksFlHead", title, "btnKksFlClose", close,
                      accessible='"Close the Functional Location search"')
    intro = text_ctrl("txtKksFlIntro",
                      '"Live search in SAP, independent of the KKS selection."',
                      size=lay.SIZE_SMALL, color=C_MUTED, height=36, wrap="true")
    picker = fl_picker(
        "Kks", combo="cmbKksFl", results="colKksFl", raw_var="varKksFlRaw",
        msg_var="varKksFlMsg", busy_var="varKksFlBusy", query_var="varKksFlQuery",
        last_var="varKksFlLast", pick_var=FL_PICK,
        default_items=f"Filter(colKksFl, Code = {FL_PICK})",
        display_mode="DisplayMode.Edit", width=FL_IN_W, stack_search=True)
    # Beskeden under feltet - som i domaeneapperne, men ombrudt: popuppen er
    # smal paa en telefon.
    per_line = f"Max(20, RoundDown({FL_IN_W} / 7, 0))"
    msg_h = f"Max(1, RoundUp(Len(varKksFlMsg) / {per_line}, 0)) * 18"
    msg = text_ctrl("txtKksFlMsg", "varKksFlMsg", size=12, color=C_MUTED,
                    height=msg_h, wrap="true", visible="!IsBlank(varKksFlMsg)")
    # ALLE RESULTATER, hver med sin kopier-knap (issue #514). Foer stod kun
    # det valgte (foerste) resultat under feltet, selv om beskeden sagde
    # "6 Functional Locations found". Listen viser hele colKksFl - samme
    # samling, som beskeden taeller, saa raekkerne og tallet altid er enige.
    # Det valgte i comboboksen er fremhaevet. colKksFl er en lokal samling
    # (flowets svar, ParseJSON + ForAll uden FirstN), saa Sum/CountRows er
    # ikke delegeringsfoelsomme.
    copy_w = hit_size(COPY_W)
    text_w = (f"({FL_IN_W} - 2 * {ROW_PAD} - {copy_w} - {ROW_GAP} - "
              f"{SCROLLBAR_W} - {GALLERY_RESERVE})")
    chars = f"Max(14, RoundDown({text_w} / 7.5, 0))"

    def _desc(ref):
        return (f'{ref}.Description & If(!IsBlank({ref}.Code) && !{ref}.Maintainable, '
                f'"   (not maintainable)", "")')

    def _desc_h(ref):
        return f"Max(1, RoundUp(Len({_desc(ref)}) / {chars}, 0)) * {LINE_H} + 1"

    def _row_h(ref):
        return f"Max({copy_w}, 22 + {_desc_h(ref)}) + 12"

    rh = _row_h("ThisItem")
    code = text_ctrl("txtKksFlRowCode", "ThisItem.Code", size=lay.SIZE_BODY, weight="Semibold",
                     height=20, width=text_w)
    desc = text_ctrl("txtKksFlRowDesc", _desc("ThisItem"), size=lay.SIZE_BODY, wrap="true",
                     height=_desc_h("ThisItem"), width=text_w)
    cell = group("conKksFlRowText", [code, desc], direction="Vertical", gap=2, width=text_w)
    row = group("conKksFlRow", [cell], direction="Horizontal", gap=ROW_GAP, height=rh,
                width="Parent.TemplateWidth", align_items="Start",
                fill=f"If(ThisItem.Code = {FL_PICK}, {C_PRIMARY_SOFT}, {C_CARD_BG})",
                pad=(6, ROW_PAD, 6, ROW_PAD))
    rule = row_rule("rctKksFlRowRule", 0)
    rule.props["Y"] = f"({rh}) - 1"
    copy = button("btnKksFlCopy", '""',
                  'Copy(ThisItem.Code);\nNotify("Copied " & ThisItem.Code & " to the clipboard.", '
                  'NotificationType.Success)',
                  width=COPY_W, height=COPY_W, icon="Copy",
                  accessible='"Copy " & ThisItem.Code', tooltip='"Copy " & ThisItem.Code')
    copy.props["Layout"] = "ButtonLayout.IconOnly"
    copy.props["BorderColor"] = C_TRANSPARENT
    ensure_hit(copy)
    copy.props["X"] = f"Parent.TemplateWidth - {ROW_PAD} - Self.Width"
    copy.props["Y"] = "6"
    copy.props["_OnTop"] = "true"
    # Hoejden: hele listen, saa laenge den kan staa i popuppen; foerst naar
    # den IKKE kan, faar den sin rest af skaermen og scroller (issue #514).
    # Resten er skaermen minus popuppens margen (12 + 12), dens polstring
    # (18 + 18), de andre boern og deres mellemrum.
    full_h = f"Sum(colKksFl, {_row_h('ThisRecord')})"
    above = stack_height([head, intro, picker, msg], 12, 18, 18)
    room = f"Max(120, App.Height - 24 - ({above}) - 12)"
    vis_list = "CountRows(colKksFl) > 0"
    gal_h = f"If({vis_list}, Min({full_h}, {room}), 0)"
    gal = Ctrl("galKksFlRows", "Gallery", variant="VariableHeight", props={
        "AccessibleLabel": '"Functional Locations found"',
        "BorderStyle": "BorderStyle.None", "Fill": C_CARD_BG, "FillPortions": "0",
        "Height": gal_h, "Items": "colKksFl", "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None", "Selectable": "false",
        "ShowScrollbar": f"{full_h} > {room}", "TabIndex": "0", "TemplatePadding": "0",
        "TemplateSize": "42", "Width": "Parent.Width",
    }, children=[row, rule, copy], h=gal_h, vis=vis_list)
    modal = group("conKksFlModal", [head, intro, picker, msg, gal], direction="Vertical",
                  gap=12, fill=C_MODAL_BG, border_color=C_PRIMARY_SOFT,
                  radius=lay.RADIUS_MODAL, pad=(18, 18, 18, 18), width=FL_W,
                  drop_shadow="ExtraBold", visible=vis)
    modal.props["X"] = "(App.Width - Self.Width) / 2"
    modal.props["Y"] = "Max(12, (App.Height - Self.Height) / 4)"
    mobile.mobile_popup(modal, top=True)
    return [backdrop, modal]
