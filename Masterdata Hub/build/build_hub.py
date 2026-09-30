# -*- coding: utf-8 -*-
"""
Landingssiden for SAP masterdata-indmeldinger.

EEN DATAKILDE
-------------
Skaermen laeser kun MD_RequestIndex. Den maa ALDRIG laese de fem
domaenelister og flette dem i klienten - det er fem forbindelser og en
fletning, der ikke kan delegeres. Se docs/07-landingsside.md.

INGEN DATAHENTNING I App.OnStart
--------------------------------
OnStart betales af hver bruger hver gang. Galleriet binder direkte til et
filter, og flisernes tal taelles paa det samme, allerede afgraensede saet.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import (Ctrl, C_CARD_BG, C_CARD_BORDER, C_TITLE, C_MUTED,
                        C_PRIMARY, C_MUTED_BG, C_MODAL_BG, C_DIVIDER,
                        C_TRANSPARENT, SHELL_W)
from build_helpers import (row_rule, row_hit, text_input, text_ctrl, group, button, card, flow_row, top_bar,
                           fit_button_width, ICON_W)
from hub_config import LIST, COL_NO, DOMAINS, STATUS, STATUS_ICON, APP_TARGET
from design_tokens import theme_query, ref_hex, ref as _t
from icons import MIRROR_X
from layout_tokens import (if_below, SCROLLBAR_W, GALLERY_RESERVE, PAGE_PAD_R,
                           HEADER_PAD_T)

# Hubben aabner satellitterne. Temaet skal med i URL'en, fordi
# SaveData-lageret er isoleret pr. app-id: uden den ville en moerk hub
# aabne en lys Equipment-app, og brugeren ville se appen skifte farve som
# foelge af sit eget klik. Satellitten laeser Param("theme") i OnStart.
THEME_Q = theme_query("?")      # flisen sender ingen andre parametre
THEME_Q_AMP = theme_query("&")  # "Open" sender allerede ?reqid=

# DEN SAMLEDE APP (BIO SAP App/) genbruger hubben som sin startskaerm. Dér
# er domaenerne skaerme, ikke apps, saa "New" og "Open" er Navigate() i
# stedet for Launch(). Dens bygger saetter de to:
#
#   NEW_ACTION(d) -> OnSelect for flisens "New" og menupunktet under
#                    "New request", eller None, naar domaenet ikke har en
#                    skaerm ("Coming soon").
#   OPEN_ACTION   -> OnSelect for raekkens "Open".
#
# None (de fem enkelte apps) = Launch som hidtil.
NEW_ACTION = None
OPEN_ACTION = None

# "New request"-menuen i bjaelken. Blank ved start = lukket.
MENU_OPEN = "IfError(gblNewMenu, false)"
MENU_CLOSE = "Set(gblNewMenu, false)"


def _new_action(d):
    """(OnSelect, klar) for et domaenes "New". Samme regel til flisen og
    menuen, saa de ikke kan vaere uenige om, hvad der er "Coming soon"."""
    if NEW_ACTION is not None:
        act = NEW_ACTION(d)
        if act is not None:
            return act, True
        return 'Notify("This app has not been built yet.", NotificationType.Warning)', False
    if d["url"]:
        # Temaet sendes MED i URL'en. SaveData er isoleret pr. app-id,
        # saa uden det ville satellitten aabne i sit eget gamle tema.
        return f'Launch("{d["url"]}" & {THEME_Q}, {{ }}, {APP_TARGET})', True
    return 'Notify("This app has not been built yet.", NotificationType.Warning)', False


# ---------------------------------------------------------------------------
# SVG - ikonerne (issue: nyt design). Samme form som sidebaren
# (tools/side_nav.py): EET Image med en SVG, farverne er tokens, saa de
# skifter tema med alt andet. SVG'en bruger kun enkelte anfoerselstegn,
# saa den kan staa i en Power Fx-streng.
# ---------------------------------------------------------------------------
SVG_FONT = "font-family='Segoe UI, sans-serif'"


def _hx(token):
    return '" & %s & "' % ref_hex(token)


def _svg_uri(svg_expr):
    return f'"data:image/svg+xml;utf8," & EncodeUrl({svg_expr})'


def _glyph(path, color, x=0, y=0, size=24, width=1.8, mirror=False):
    """Et stregikon. mirror spejler det vandret (icons.MIRROR_X) - Measuring
    Points lineal, saa den peger samme vej som Equipments skruenoegle."""
    s = size / 24
    inner = f"<path d='{path}'/>"
    if mirror:
        inner = f"<g transform='{MIRROR_X}'>{inner}</g>"
    return (f"<g transform='translate({x:g} {y:g}) scale({s:g})' fill='none' "
            f"stroke='{color}' stroke-width='{width}' stroke-linecap='round' "
            f"stroke-linejoin='round'>{inner}</g>")


def _dglyph(d, color, **kw):
    """Domaenets ikon - spejlet, hvis domaenet siger det (hub_config)."""
    return _glyph(d["icon"], color, mirror=d.get("mirror", False), **kw)


def _icon_svg(path, color, size=24, mirror=False):
    return ('"' + f"<svg xmlns='http://www.w3.org/2000/svg' width='{size}' height='{size}' "
            f"viewBox='0 0 {size} {size}'>" + _glyph(path, color, size=size, mirror=mirror)
            + "</svg>" + '"')


def _image(name, image, width, height, onselect=None, label='""', hover=None):
    """Et billede. Uden onselect er det pynt: ingen tab stop, tom etiket."""
    props = {
        "AccessibleLabel": label,
        "BorderStyle": "BorderStyle.None",
        "BorderThickness": "0",
        "Fill": C_TRANSPARENT,
        "Height": str(height),
        "Image": image,
        "ImagePosition": "ImagePosition.Fit",
        "Width": str(width),
    }
    if onselect:
        props.update({
            "FocusedBorderColor": C_PRIMARY,
            "FocusedBorderThickness": "2",
            "HoverFill": hover or C_TRANSPARENT,
            "PressedFill": hover or C_TRANSPARENT,
            "OnSelect": onselect,
            "TabIndex": "0",
        })
    else:
        props.update({"OnSelect": "false", "TabIndex": "-1"})
    return Ctrl(name, "Image", props=props, h=height)


def _domain_switch(field, fallback):
    return ("Switch(\n    ThisItem.Domain.Value,\n    " +
            ",\n    ".join(f'"{d["key"]}", {field(d)}' for d in DOMAINS) +
            f",\n    {fallback}\n)")


# ---------------------------------------------------------------------------
# Afgraensningen - TO uafhaengige valg (issue #74):
#
#   HVIS    "My requests" (gblView)   mine / hele afdelingen
#   HVILKE  Open / Closed / All       gblStatusMode
#
# "My requests" er et OMFANG, ikke et statusfilter; de to kombineres. Foer
# var afdelingens visning det samme som "aabne", saa Closed og All viste
# intet, naar My requests var slaaet fra, og fliserne talte altid kun aabne.
#
# Hver gren er delegerbar for sig: RequesterEmail og IsOpen er indekserede
# felter, og en enkelt sammenligning paa hver er det, SharePoint kan. En
# raekke OR'ede statusvaerdier kunne den ikke - derfor IsOpen, som
# submit-flowet vedligeholder sammen med Status.
#
# SCOPE er BAADE listens, flisernes og taellerens grundlag, saa de tre
# aldrig kan vaere uenige om, hvad der er valgt.
# ---------------------------------------------------------------------------
# ET FLADT FILTER, IKKE If(...) OMKRING SEKS FILTRE
#
# Her stod If(gblView = "mine", If(gblStatusMode = ...)) med et Filter i
# hver gren. Om Power Apps delegerer det ydre Filter/SortByColumns GENNEM
# en If, var aldrig efterproevet (README bad selv om at tjekke det). Et
# enkelt Filter, hvor hver betingelse er "konstant ELLER delegerbar
# sammenligning", er samme moenster som soegningen nedenfor
# (IsBlank(...) || StartsWith(...)) - og det staar kun een gang i YAML'en.
#
# Stadig kun indekserede felter: RequesterEmail (tekst) og IsOpen (ja/nej).
SCOPE = (
    "Filter(\n"
    f"        '{LIST}',\n"
    '        gblView <> "mine" || RequesterEmail = gblMe,\n'
    '        gblStatusMode = "all" || IsOpen = (gblStatusMode = "open")\n'
    "    )"
)

# FLISERNES OG TAELLERENS TAL - EEN HENTNING, IKKE SEKS
#
# Her stod CountRows(Filter(SCOPE, Domain.Value = "X")) fem gange plus een
# for taelleren. CountRows mod en SharePoint-liste delegeres ikke: seks
# forespoergsler, og hvert tal stoppede ved data row limit - netop det,
# docs/07 regel 6 forbyder (REVIEW.md B1).
#
# Nu hentes omfanget EEN gang til colMdScope - kun domaenet - naar skaermen
# vises, og naar "My requests" eller Open/Closed/All skifter. Tallene
# taelles i samlingen. Rammer den loftet, staar der "500+".
ROW_LIMIT = 500   # appens Data row limit (Studio -> Settings)
SCOPE_REFRESH = f"ClearCollect(colMdScope, ForAll({SCOPE} As R, {{ Domain: R.Domain.Value }}))"
SCOPE_FULL = f"CountRows(colMdScope) >= {ROW_LIMIT}"


def scope_count(pred=None):
    """Antal i colMdScope (evt. afgraenset) som tekst - med "+" ved loftet."""
    n = f"CountRows(Filter(colMdScope, {pred}))" if pred else "CountRows(colMdScope)"
    return f'Text({n}) & If({SCOPE_FULL}, "+", "")'


# Flisernes undertekst: hvad tallet taeller.
SCOPE_WORDS = ('Switch(gblStatusMode, "open", "Open", "done", "Closed", "All") & '
               'If(gblView = "mine", " - my requests", " - whole department")')

# De seneste lukkede indmeldinger i det valgte omfang - til Closed-preview'et.
CLOSED_LATEST = (
    "FirstN(\n"
    "    SortByColumns(\n"
    f"        Filter('{LIST}', gblView <> \"mine\" || RequesterEmail = gblMe, IsOpen = false),\n"
    "        \"LastActionOn\", SortOrder.Descending\n"
    "    ),\n"
    "    5\n"
    ")"
)
PEEK_OPEN = "IfError(gblClosedPeek, false)"

# Tabellens kolonner. EEN kilde til bredderne, saa overskriften og raekken
# ikke kan komme til at staa forskudt. Resten af bredden ligger i REQUEST,
# som regnes af de faste.
COLS = [("DOMAIN", 190), ("REQUEST", 0), ("PLANT", 80), ("STATUS", 160),
        ("LAST", 110), ("ACTIONS", 104)]
GAP = 12
ROW_PAD = 12
FIXED = sum(w for _, w in COLS) + GAP * (len(COLS) - 1) + 2 * ROW_PAD
# Bruges BAADE i listehovedet og i galleriets raekke. REGNET AF DEN BREDDE,
# LISTEN HAR - ikke af Parent.Width, som er raekkens Width-EGENSKAB og
# hverken traekker kortets padding, galleriets TemplatePadding eller dets
# scrollbar fra.
MAIN_W = f"({SHELL_W} - 36 - 4 - {SCROLLBAR_W} - {GALLERY_RESERVE} - {FIXED})"

ROW_H = 52
GAL_ROWS = 9

ICON_CHEVRON = "M9 6l6 6-6 6"

# Det, raekken viser ud for nummeret - kun de dele, der er udfyldt.
NO_W = 120
ROW_META = (
    "Concat(\n"
    "    Filter(\n"
    "        Table(\n"
    '            { v: If(!IsBlank(ThisItem.RequesterName), "by " & ThisItem.RequesterName) },\n'
    "            { v: If(ThisItem.ItemCount > 0, Text(ThisItem.ItemCount) &\n"
    '                    If(ThisItem.ItemCount = 1, " item", " items")) },\n'
    '            { v: If(!IsBlank(ThisItem.SapObjectNo), "SAP " & ThisItem.SapObjectNo) },\n'
    '            { v: If(!IsBlank(ThisItem.LastActionBy), "last change by " & ThisItem.LastActionBy) }\n'
    "        ),\n"
    "        !IsBlank(v)\n"
    "    ),\n"
    "    v,\n"
    '    "  \u00b7  "\n'
    ")"
)

# Hvert statusikon skal have en status - og omvendt.
if set(STATUS_ICON) != {s[0] for s in STATUS}:
    raise SystemExit("hub_config: STATUS_ICON og STATUS har ikke de samme noegler: %s"
                     % sorted(set(STATUS_ICON) ^ {s[0] for s in STATUS}))


def _switch(field_index, fallback, quote=False):
    """Switch over statusvaerdien, bygget af ordforraadet i hub_config.

    quote=True naar feltet er TEKST. Farvefelterne er Power Fx-udtryk
    ("RGBA(...)") og skal staa uden anfoerselstegn, men etiketten er en
    streng - uden dem blev "In progress" til to identifiers."""
    parts = [f'"{s[0]}", ' + (f'"{s[field_index]}"' if quote else f'{s[field_index]}')
             for s in STATUS]
    return "Switch(\n    ThisItem.Status.Value,\n    " + ",\n    ".join(parts) + \
           f",\n    {fallback}\n)"


# ---------------------------------------------------------------------------
# Toplinje
# ---------------------------------------------------------------------------
def _selected_style(b, selected, color=C_PRIMARY, idle_color=C_TITLE):
    """Valgt = kanten (og teksten) i farven, 2 px. Ikke valgt = den
    almindelige graa kant. Samme regel som flisernes."""
    b.props["Appearance"] = "ButtonAppearance.Outline"
    b.props["BorderColor"] = f"If({selected}, {color}, {C_CARD_BORDER})"
    b.props["BorderThickness"] = f"If({selected}, 2, 1)"
    b.props["Color"] = f"If({selected}, {color}, {idle_color})"
    return b


def build_bar():
    """Toplinjen - build_helpers.top_bar(), den samme i alle apps.

    "My requests" er en kontakt: slaaet til viser listen og fliserne dine
    egne indmeldinger, slaaet fra afdelingens koe. "New request" aabner en
    menu med de fem domaener (build_new_menu)."""
    mine = button("btnMdViewMine", '"My requests"',
                  'Set(gblView, If(gblView = "mine", "queue", "mine")); Set(gblDomain, "");\n'
                  + SCOPE_REFRESH,
                  width=fit_button_width('"My requests"') + ICON_W, height=36, icon="Person",
                  accessible='If(gblView = "mine", "Showing my requests - show the queue", '
                             '"Showing the queue - show my requests")')
    _selected_style(mine, 'gblView = "mine"')
    new = button("btnMdNewRequest", '"New request"', f"Set(gblNewMenu, !{MENU_OPEN})",
                 primary=True, width=fit_button_width('"New request"') + ICON_W, height=36,
                 icon="Add")
    return top_bar("Md", '"Masterdatahub"',
                   '"SAP requests - " & If(gblView = "mine", gblMe, "whole department")',
                   [mine, new], icon="hub")


MENU_W = 290
MENU_ITEM_H = 40


def _menu_item_svg(d, ready):
    fg = _hx("text-primary") if ready else _hx("text-muted")
    body = _dglyph(d, _hx(d["token"]) if ready else _hx("text-muted"), x=14, y=9,
                   size=22)
    body += (f"<text x='48' y='{MENU_ITEM_H // 2 + 5}' {SVG_FONT} font-size='14' "
             f"font-weight='600' fill='{fg}'>{d['name']}</text>")
    if not ready:
        body += (f"<text x='{MENU_W - 16 - 14}' y='{MENU_ITEM_H // 2 + 4}' text-anchor='end' "
                 f"{SVG_FONT} font-size='11' fill='{_hx('text-muted')}'>Coming soon</text>")
    w = MENU_W - 16
    return ('"' + f"<svg xmlns='http://www.w3.org/2000/svg' width='{w}' "
            f"height='{MENU_ITEM_H}' viewBox='0 0 {w} {MENU_ITEM_H}'>" + body + "</svg>" + '"')


def build_new_menu():
    """"New request"-menuen: [sloer, menu]. Staar paa skaermen EFTER
    rammen, saa den ligger oven paa listen - se assemble_hub."""
    scrim = Ctrl("imgMdNewScrim", "Image", props={
        "AccessibleLabel": '"Close menu"',
        "BorderStyle": "BorderStyle.None",
        "BorderThickness": "0",
        "Fill": C_TRANSPARENT, "HoverFill": C_TRANSPARENT, "PressedFill": C_TRANSPARENT,
        "Height": "App.Height",
        "Image": '""',
        "OnSelect": MENU_CLOSE,
        "TabIndex": "-1",
        "Visible": MENU_OPEN,
        "Width": "App.Width",
        "X": "0",
        "Y": "0",
    }, h="App.Height", vis=MENU_OPEN)
    items = []
    for d in DOMAINS:
        act, ready = _new_action(d)
        items.append(_image(f"imgMdNew{d['short']}", _svg_uri(_menu_item_svg(d, ready)),
                            MENU_W - 16, MENU_ITEM_H, onselect=f"{MENU_CLOSE};\n{act}",
                            label=f'"New {d["name"].lower()} request"' if ready
                            else f'"{d["name"]} - coming soon"',
                            hover=C_MUTED_BG if ready else None))
    menu = group("conMdNewMenu", items, direction="Vertical", gap=2, width=MENU_W,
                 fill=C_MODAL_BG, border_color=C_CARD_BORDER, radius=12, pad=8,
                 drop_shadow="Bold", visible=MENU_OPEN, align_items="Start")
    menu.props["X"] = f"App.Width - Self.Width - {PAGE_PAD_R + SCROLLBAR_W}"
    # Lige under bjaelken: dens padding + titel og undertitel (30 + 2 + 20).
    menu.props["Y"] = str(HEADER_PAD_T + 52 + 6)
    return [scrim, menu]


# ---------------------------------------------------------------------------
# Domaenefliser - HELE flisen er filterknappen
# ---------------------------------------------------------------------------
# Fem fliser eller to. Det er en beslutning om, hvor stor skaermen er -
# altsaa et viewport-braekpunkt, ikke en udregning paa indholdet. Se
# tools/layout_tokens.py.
#
# Under "Tablet" (telefon) EEN pr. raekke.
#
# LUFT OM RAEKKEN (issue #70). Fliserne fyldte beholderen paa pixlen, og
# beholderen skjuler sit overloeb - saa en valgt flises 2 px kant og
# skygge blev klippet, og Functional Location (den foerste) saa ud til at
# vaere skaaret af i venstre side. Nu har raekken polstring:
#
#     TILE_GAP til venstre og hoejre - den samme afstand som MELLEM fliserne,
#              saa den foerste og den sidste har samme yderkant som resten
#     TILE_PAD_T / TILE_PAD_B foroven og forneden - plads til kant og skygge
#
# og TILE_W regnes af det, der er tilbage.
TILE_GAP = 12
TILE_PAD_T = 4
TILE_PAD_B = 8
TILES_CW = f"({SHELL_W} - {2 * TILE_GAP})"
TILE_W = if_below("Tablet", TILES_CW,
                  if_below("Desktop", f"({TILES_CW} - {TILE_GAP}) / 2",
                           f"({TILES_CW} - {4 * TILE_GAP}) / 5"))
TILE_LINES = if_below("Tablet", "5", if_below("Desktop", "3", "1"))
# Kompakt (issue #74): ikon og navn paa een linje, tallet under. Var 156
# px forside + 4 px streg + en knaprad paa 48 - nu er hele flisen 108.
TILE_H = 108
STRIPE_H = 4


def _tile_state(d, sel):
    """Flisens tilstande - de SAMME for alle fem, kun farven er domaenets.

        standard   kortets fyld, 1 px graa kant, ingen skygge
        hover      HELE flisen toner i domaenets bloede farve
        trykket    samme toning
        fokus      2 px kant i domaenets farve (tastatur)
        valgt      2 px kant i domaenets farve, bloed toning af hele
                   flisen og en let skygge - ikke en kraftig baggrund

    Hover daekker hele flisen, fordi hele flisen ER eet billede (issue
    #74): der er ingen knaprad under forsiden mere, som hover ikke naaede.

    Den bloede farve (domain-*-soft) er domaenet blandet 8 % (lys) / 16 %
    (moerk) ind i kortets baggrund, og design_tokens.CONTRAST kraever, at
    tekst og kant kan laeses paa den i begge temaer."""
    soft = _t(d["token"] + "-soft")
    return {
        "fill": f"If({sel}, {soft}, {C_CARD_BG})",
        "border": f"If({sel}, {d['color']}, {C_CARD_BORDER})",
        "thickness": f"If({sel}, 2, 1)",
        "shadow": f"If({sel}, DropShadow.Light, DropShadow.None)",
        "hover": soft,
    }


def _tile_face(d, count_expr):
    """HELE flisen som EEN SVG: stregen foroven i domaenets farve, ikonet i
    en tonet cirkel med navnet ved siden af, tallet og hvad det taeller.
    Bredden er billedets egen (Self.Width), saa intet skaleres.

    Et billede har OnSelect og HoverFill - det har en tekst ikke. Derfor er
    flisen et billede: saa er hele flisen filterknappen, og hele flisen
    reagerer paa musen."""
    c = _hx(d["token"])
    w = '" & Self.Width & "'
    h = TILE_H
    return ('"' + f"<svg xmlns='http://www.w3.org/2000/svg' width='{w}' height='{h}' "
            f"viewBox='0 0 {w} {h}'>"
            f"<rect width='{w}' height='{STRIPE_H}' fill='{c}'/>"
            f"<circle cx='34' cy='36' r='18' fill='{c}' fill-opacity='0.12'/>"
            + _dglyph(d, c, x=24, y=26, size=20) +
            f"<text x='62' y='41' {SVG_FONT} font-size='14' font-weight='600' "
            f"fill='{_hx('text-primary')}'>{d['name']}</text>"
            f"<text x='16' y='82' {SVG_FONT} font-size='26' font-weight='600' "
            f"fill='{_hx('text-primary')}'>\" & {count_expr} & \"</text>"
            f"<text x='16' y='98' {SVG_FONT} font-size='11' "
            f"fill='{_hx('text-muted')}'>\" & {SCOPE_WORDS} & \"</text></svg>" + '"')


def build_tiles():
    """De fem domaenefliser. Hele flisen filtrerer listen; "New request" i
    bjaelken er vejen til en ny indmelding (issue #74 fjernede flisernes
    egne "+ New")."""
    tiles = []
    for d in DOMAINS:
        n = d["short"]
        sel = f'gblDomain = "{d["key"]}"'
        # Tallet taelles paa PRAECIS det saet, listen viser - omfang og
        # Open/Closed/All - bare afgraenset til domaenet.
        count = scope_count(f'Domain = "{d["key"]}"')

        st = _tile_state(d, sel)
        face = _image(f"imgMdTile{n}", _svg_uri(_tile_face(d, count)), "Parent.Width",
                      TILE_H,
                      onselect=f'Set(gblDomain, If({sel}, "", "{d["key"]}"))',
                      # Uden tallet: det ville vaere endnu en forespoergsel.
                      label=f'If({sel}, "Show all domains", "Show only {d["name"].lower()}")',
                      hover=st["hover"])
        face.props["FocusedBorderColor"] = d["color"]

        tile = group(
            f"conMdTile{n}", [face], direction="Vertical", gap=0,
            fill=st["fill"], radius=12, width=TILE_W,
            border_color=st["border"], border_thickness=st["thickness"])
        tile.props["DropShadow"] = st["shadow"]
        tiles.append(tile)

    tile_h = tiles[0].h
    return group("conMdTiles", tiles, direction="Horizontal", gap=TILE_GAP, wrap="true",
                 pad=(TILE_PAD_T, TILE_GAP, TILE_PAD_B, TILE_GAP),
                 # SAMME braekpunkt som TILE_W. Var de uenige, ville beholderen
                 # have hoejde til een raekke fliser, mens fliserne selv stod i
                 # tre - og de to nederste raekker blev klippet af.
                 height=(f"{TILE_PAD_T} + {TILE_LINES} * ({tile_h}) + "
                         f"({TILE_LINES} - 1) * {TILE_GAP} + {TILE_PAD_B}"))


# ---------------------------------------------------------------------------
# Filtre
# ---------------------------------------------------------------------------
def _chip(name, label, value, icon):
    b = button(name, f'"{label}"', f'Set(gblStatusMode, "{value}");\n' + SCOPE_REFRESH,
               width=fit_button_width(f'"{label}"') + ICON_W, height=36, icon=icon)
    return _selected_style(b, f'gblStatusMode = "{value}"', idle_color=C_MUTED)


SEARCH_W = 280


def build_filters():
    """Vaerktoejslinjen (issue #74):

        [Search number, text or plant...][Open][Closed][i][All]      42 requests

    Soegefeltet er saa bredt som det, man soeger efter (et nummer, et
    vaerk, et par ord) - ikke resten af linjen. Taelleren staar til hoejre
    og tager resten, saa den flugter med listens hoejre kant. My requests
    staar i bjaelken: det er et omfang, ikke et statusfilter."""
    # Det SAMME felt som alle andre (build_helpers.text_input -> input_theme,
    # issue #78) - ikke et haandbygget med sine egne farver.
    search = text_input("txtMdSearch", '""', placeholder='"Search number, text or plant..."',
                        width=str(SEARCH_W), ttype="Search",
                        label='"Search number, text or plant"')
    shown = scope_count('gblDomain = "" || Domain = gblDomain')
    count = text_ctrl("txtMdCount", f'{shown} & " requests"',
                      size=12, color=C_MUTED, height=36, align="Right", width=110, wrap="false")
    closed = _chip("btnMdStDone", "Closed", "done", "CheckmarkCircle")
    # Statisk: tooltip'en hentede de seneste lukkede (en forespoergsel) ved
    # hver visning af skaermen. Info-knappen ved siden af viser dem.
    closed.props["Tooltip"] = '"Show closed requests - the (i) button lists the latest"'
    kids = [search, _chip("btnMdStOpen", "Open", "open", "MailInbox"),
            closed, _peek_button(),
            _chip("btnMdStAll", "All", "all", "TextBulletListLtr"), count]
    # Enten een linje, eller et felt pr. linje - se build_helpers.flow_row.
    return flow_row("conMdFilters", kids, SHELL_W, gap=10, flex=count, flex_min=110)


# ---------------------------------------------------------------------------
# Closed-preview (issue #74) - KUN ved Closed
# ---------------------------------------------------------------------------
# To veje til det samme: hover over Closed viser de seneste lukkede som
# tooltip, og info-knappen ved siden af aabner en lille popover, hvor hver
# raekke kan aabnes. Knappen er vejen paa touch og med tastatur - en
# tooltip kan hverken naas med en finger eller klikkes i.
PEEK_W = 360
PEEK_ROW_H = 48


def _peek_button():
    b = button("btnMdClosedPeek", '""', f"Set(gblClosedPeek, !{PEEK_OPEN})",
               width=36, height=36, icon="Info",
               accessible='"Show the latest closed requests"')
    b.props["Layout"] = "ButtonLayout.IconOnly"
    b.props["Tooltip"] = '"Latest closed requests"'
    return _selected_style(b, PEEK_OPEN, idle_color=C_MUTED)


def build_closed_peek():
    """Popoveren: [sloer, kort]. Staar paa skaermen efter rammen, som
    "New request"-menuen - se assemble_hub."""
    close = "Set(gblClosedPeek, false)"
    scrim = Ctrl("imgMdPeekScrim", "Image", props={
        "AccessibleLabel": '"Close preview"',
        "BorderStyle": "BorderStyle.None",
        "BorderThickness": "0",
        "Fill": C_TRANSPARENT, "HoverFill": C_TRANSPARENT, "PressedFill": C_TRANSPARENT,
        "Height": "App.Height",
        "Image": '""',
        "OnSelect": close,
        "TabIndex": "-1",
        "Visible": PEEK_OPEN,
        "Width": "App.Width",
        "X": "0",
        "Y": "0",
    }, h="App.Height", vis=PEEK_OPEN)
    title = text_ctrl("txtMdPeekTitle", '"Latest closed requests"', size=14,
                      weight="Semibold", height=22, wrap="false")
    sub = text_ctrl("txtMdPeekSub",
                    'If(gblView = "mine", "My requests", "Whole department")',
                    size=11, color=C_MUTED, height=18, wrap="false")

    icon = _image("imgMdPeekDomain",
                  _svg_uri(_domain_switch(
                      lambda d: _icon_svg(d["icon"], _hx(d["token"]),
                                          mirror=d.get("mirror", False)), '""')),
                  20, 20)
    icon.props["X"] = "8"
    icon.props["Y"] = str((PEEK_ROW_H - 20) // 2)
    line1 = text_ctrl("txtMdPeekNo",
                      f'ThisItem.{COL_NO} & "  -  " & ' +
                      _domain_switch(lambda d: f'"{d["name"]}"', '""'),
                      size=13, weight="Semibold", height=20, wrap="false")
    line2 = text_ctrl("txtMdPeekText", "ThisItem.ShortText", size=12, color=C_MUTED,
                      height=18, wrap="false")
    for i, t in enumerate((line1, line2)):
        t.props["X"] = "38"
        t.props["Y"] = str(5 + i * 20)
        t.props["Width"] = str(PEEK_W - 16 - 38 - 12)
    act = _open_action()
    # Hele raekken er klikbar - det faelles moenster (build_helpers.row_hit).
    hit = row_hit("btnMdPeekOpen", f"{close};\n{act}", f'"Open " & ThisItem.{COL_NO}',
                  PEEK_W - 16, PEEK_ROW_H, radius=8)
    gal = Ctrl("galMdPeek", "Gallery", variant="Vertical", props={
        "AccessibleLabel": '"Latest closed requests"',
        "BorderStyle": "BorderStyle.None", "Fill": C_TRANSPARENT, "FillPortions": "0",
        "Height": str(5 * PEEK_ROW_H),
        "Items": CLOSED_LATEST, "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.Controls",
        "Selectable": "false", "ShowScrollbar": "false", "TabIndex": "0",
        "TemplatePadding": "0", "TemplateSize": str(PEEK_ROW_H),
        "Width": str(PEEK_W - 16), "WrapCount": "1",
        # Start, ikke Stretch: saa er bredden praecis den skrevne, og
        # skabelonen regnes uden GALLERY_RESERVE (se VH-planens items).
        "AlignInContainer": "AlignInContainer.Start",
    }, children=[icon, line1, line2, hit], h=5 * PEEK_ROW_H)
    empty = text_ctrl("txtMdPeekEmpty", '"No closed requests yet."', size=12,
                      color=C_MUTED, height=20, wrap="false",
                      visible="IsEmpty(galMdPeek.AllItems)")
    card_ = group("conMdPeek", [title, sub, gal, empty], direction="Vertical", gap=6,
                  width=PEEK_W, fill=C_MODAL_BG, border_color=C_CARD_BORDER, radius=12,
                  pad=8, drop_shadow="Bold", visible=PEEK_OPEN, align_items="Stretch")
    card_.props["X"] = f"Max(8, App.Width - Self.Width - {PAGE_PAD_R + SCROLLBAR_W})"
    card_.props["Y"] = str(HEADER_PAD_T + 52 + 6)
    return [scrim, card_]


# ---------------------------------------------------------------------------
# Listen
# ---------------------------------------------------------------------------
ITEMS = (
    "SortByColumns(\n"
    "    Filter(\n"
    f"        {SCOPE},\n"
    '        gblDomain = "" || Domain.Value = gblDomain,\n'
    '        IsBlank(Trim(txtMdSearch.Text)) ||\n'
    f"            StartsWith({COL_NO}, Trim(txtMdSearch.Text)) ||\n"
    "            StartsWith(ShortText, Trim(txtMdSearch.Text)) ||\n"
    "            StartsWith(Plant, Trim(txtMdSearch.Text))\n"
    "    ),\n"
    '    "LastActionOn", SortOrder.Descending\n'
    ")"
)


def _open_action():
    """Open: domaenets EGEN play-URL (hub_config, fra canvas_apps.json) +
    ?reqid=.

    Her stod ThisItem.AppUrl & "&reqid=". To problemer: Equipment,
    Material og FL skriver allerede "?reqid=" i AppUrl, saa parameteren kom
    med to gange - og AppUrl er en tekstkolonne, som alle med Contribute
    kan rette, saa hubben launchede hvad som helst. Nu er URL'en hubbens
    egen, og raekkens AppUrl bruges kun, hvis domaenet er ukendt.
    Samme tjek som i BIO SAP: uden RequestGuid er der intet at aabne."""
    known = [(d["key"], d["url"]) for d in DOMAINS if d["url"]]
    url = ("Switch(\n"
           "        ThisItem.Domain.Value,\n"
           + "".join(f'        "{k}", "{u}",\n' for k, u in known) +
           '        ""\n'
           "    )")
    return OPEN_ACTION or (
        f"With(\n    {{ u: {url} }},\n"
        "    If(\n"
        "        IsBlank(ThisItem.RequestGuid),\n"
        '        Notify("This request has no ID.", NotificationType.Error),\n'
        "        !IsBlank(u),\n"
        f'        Launch(u & "?reqid=" & ThisItem.RequestGuid & {THEME_Q_AMP}, {{ }}, {APP_TARGET}),\n'
        "        !IsBlank(ThisItem.AppUrl),\n"
        "        Launch(\n"
        '            If(Find("reqid=", ThisItem.AppUrl) > 0, ThisItem.AppUrl,\n'
        '                ThisItem.AppUrl & If(Find("?", ThisItem.AppUrl) > 0, "&", "?") &\n'
        '                    "reqid=" & ThisItem.RequestGuid) &\n'
        f"                {THEME_Q_AMP},\n"
        f"            {{ }}, {APP_TARGET}\n"
        "        ),\n"
        '        Notify("This request has no app URL.", NotificationType.Error)\n'
        "    )\n"
        ")")


def build_list():
    head = group("conMdListHead",
                 [text_ctrl(f"txtMdH{i}", f'"{t}"', size=10, weight="Semibold", color=C_MUTED,
                            height=20, wrap="false",
                            width=(MAIN_W if w == 0 else w))
                  for i, (t, w) in enumerate(COLS)],
                 direction="Horizontal", gap=GAP, height=20, align_items="Center",
                 pad=(0, ROW_PAD, 0, ROW_PAD))

    # DOMAIN: ikonet i domaenets farve og navnet.
    dom_icon = _image("imgMdRowDomain",
                      _svg_uri(_domain_switch(
                          lambda d: _icon_svg(d["icon"], _hx(d["token"]),
                                              mirror=d.get("mirror", False)), '""')),
                      24, 24)
    dom_name = text_ctrl("txtMdRowDomain",
                         _domain_switch(lambda d: f'"{d["name"]}"', '"?"'),
                         size=13, height=20, width=COLS[0][1] - 24 - 12, wrap="false")
    dom = group("conMdRowDom", [dom_icon, dom_name], direction="Horizontal", gap=12,
                width=COLS[0][1], align_items="Center")

    # DEN TOMME MIDTE (issue #74). Raekken viste kun nummer og kort tekst,
    # og resten af den bredeste kolonne stod tom. Nu staar det, indekset
    # ALLEREDE har, ud for nummeret: hvem der har oprettet den, hvor mange
    # linjer, SAP-nummeret, naar det findes, og hvem der sidst roerte den.
    # Ingen nye kald - det er kolonner i MD_RequestIndex, som galleriet
    # alligevel henter.
    no = text_ctrl("txtMdRowNo", f"ThisItem.{COL_NO}", size=13, weight="Semibold",
                   height=20, width=NO_W, wrap="false")
    meta = text_ctrl("txtMdRowMeta", ROW_META, size=12, color=C_MUTED, height=20,
                     width=f"{MAIN_W} - {NO_W} - 8", wrap="false")
    top = group("conMdRowTop", [no, meta], direction="Horizontal", gap=8, width=MAIN_W,
                height=20, align_items="Center")
    txt = text_ctrl("txtMdRowText", "ThisItem.ShortText", size=12, color=C_MUTED, height=18,
                    wrap="false")
    main = group("conMdRowMain", [top, txt], direction="Vertical", gap=0, width=MAIN_W,
                 align_items="Stretch")

    plant = text_ctrl("txtMdRowPlant", "ThisItem.Plant", size=13, height=20,
                      width=COLS[2][1], wrap="false")

    st_icon = _image("imgMdRowStatus", _svg_uri(
        "Switch(\n    ThisItem.Status.Value,\n    " +
        ",\n    ".join(f'"{k}", {_icon_svg(path, _hx(tok))}'
                       for k, (path, tok) in STATUS_ICON.items()) +
        f',\n    {_icon_svg(STATUS_ICON["Kladde"][0], _hx("state-neutral-fg"))}\n)'),
        22, 22)
    st_lbl = text_ctrl("txtMdRowStatus", _switch(1, '"Unknown"', quote=True), size=13,
                       height=20, width=COLS[3][1] - 22 - 10, wrap="false")
    stat = group("conMdRowStat", [st_icon, st_lbl], direction="Horizontal", gap=10,
                 width=COLS[3][1], align_items="Center")

    when = text_ctrl("txtMdRowWhen",
                     'With(\n'
                     '    { d: DateDiff(ThisItem.LastActionOn, Now(), TimeUnit.Days) },\n'
                     '    If(d <= 0, "Today", If(d = 1, "Yesterday", Text(d) & " days ago"))\n'
                     ')',
                     size=12, color=C_MUTED, height=20, width=COLS[4][1], wrap="false")

    act = _open_action()
    open_btn = button("btnMdRowOpen", '"Open"', act, width=64, height=30,
                      accessible=f'"Open " & ThisItem.{COL_NO} & " in the domain app"')
    open_btn.props["Size"] = "13"
    chevron = _image("imgMdRowGo", _svg_uri(_icon_svg(ICON_CHEVRON, _hx("text-muted"))),
                     24, 24, onselect=act,
                     label=f'"Open " & ThisItem.{COL_NO}')
    # Open og pilen er TEGN paa, at raekken kan aabnes. Klikket er hele
    # raekkens (row_hit nedenfor). Pilen tages ud af tab-raekkefoelgen, saa
    # Tab ikke moeder den samme handling tre gange pr. raekke (issue #79).
    # Open-knappen kan ikke: ModernButton kender ikke TabIndex - compile
    # afviste den. Den bliver staaende som et ekstra tab-stop.
    chevron.props["TabIndex"] = "-1"
    actions = group("conMdRowActions", [open_btn, chevron], direction="Horizontal", gap=16,
                    width=COLS[5][1], align_items="Center")

    row = group("conMdRow", [dom, main, plant, stat, when, actions],
                direction="Horizontal", gap=GAP, height="Parent.TemplateHeight - 1",
                align_items="Center", width="Parent.TemplateWidth", fill=C_CARD_BG,
                pad=(0, ROW_PAD, 0, ROW_PAD))

    # STREGEN MELLEM RAEKKERNE ER SIN EGEN FIGUR (issue #70)
    #
    # Den var galleriets FYLD, der saas i den 1 px, raekken var lavere end
    # skabelonen. Men fyldet ses ogsaa alle andre steder, galleriet ikke
    # har en raekke: under de sidste raekker naar filteret giver faa, og
    # ved siden af scrollbaren - et graat felt i en anden farve end
    # tabellen. Nu er galleriet i kortets farve, og stregen er en figur
    # nederst i hver raekke.
    rule = row_rule("rctMdRowRule", ROW_H)
    # HELE RAEKKEN ER KLIKBAR (issue #79) - samme handling som Open.
    hit = row_hit("btnMdRowHit", act,
                  f'"Open " & ThisItem.{COL_NO} & " - " & ThisItem.ShortText',
                  "Parent.TemplateWidth", ROW_H - 1)
    gal = Ctrl("galMdRequests", "Gallery", variant="Vertical", props={
        "AccessibleLabel": '"Requests"',
        "BorderStyle": "BorderStyle.None", "Fill": C_CARD_BG, "FillPortions": "0",
        "Height": str(GAL_ROWS * ROW_H),
        "Items": ITEMS, "LayoutMinWidth": "0", "LoadingSpinner": "LoadingSpinner.Controls",
        "Selectable": "false", "ShowScrollbar": "true", "TabIndex": "0",
        "TemplatePadding": "0", "TemplateSize": str(ROW_H),
        "Width": "Parent.Width", "WrapCount": "1",
    }, children=[row, rule, hit], h=GAL_ROWS * ROW_H)

    empty = text_ctrl("txtMdEmpty", '"No requests match the filters."', size=13,
                      color=C_MUTED, height=24, wrap="true",
                      # GALLERIETS egne raekker - ikke en ny forespoergsel.
                      # En hoejde maa ikke kunne fejle paa netvaerket.
                      visible="IsEmpty(galMdRequests.AllItems)")

    # Streg mellem overskriften og den foerste raekke.
    head_rule = group("conMdListRule", [], direction="Horizontal", height=1,
                      fill=C_DIVIDER)

    return card("conMdListCard", [_active_filter(), head, head_rule, gal, empty], gap=8)


def _active_filter():
    """Det aktive domaenefilter over tabellen (issue #70) - i domaenets
    farve, saa man kan se, HVORFOR listen er kortere, og fjerne filteret
    uden at finde flisen igen. Tabellen selv forbliver neutral: farven
    staar kun her, paa flisens kant og i ikonerne."""
    on = 'gblDomain <> ""'
    color = _domain_switch_on("gblDomain", lambda d: d["color"], C_PRIMARY)
    name = _domain_switch_on("gblDomain", lambda d: f'"{d["name"]}"', '""')
    longest = max((d["name"] for d in DOMAINS), key=len)
    chip = button("btnMdActiveDomain", f'"Filter: " & {name}',
                  'Set(gblDomain, "")', height=30,
                  width=fit_button_width(f'"Filter: {longest}"') + ICON_W,
                  icon="Dismiss",
                  accessible=f'"Remove filter " & {name}')
    chip.props["Icon"] = '"Dismiss"'
    chip.props["Layout"] = "ButtonLayout.IconAfter"
    chip.props["Color"] = color
    chip.props["BorderColor"] = color
    chip.props["Size"] = "13"
    return group("conMdActiveFilter", [chip], direction="Horizontal", height=30,
                 align_items="Center", visible=on)


def _domain_switch_on(var, field, fallback):
    return ("Switch(\n    %s,\n    " % var +
            ",\n    ".join(f'"{d["key"]}", {field(d)}' for d in DOMAINS) +
            f",\n    {fallback}\n)")
