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
                        C_TRANSPARENT, SHELL_W, C_WARN_FG, C_WARN_BG, C_ROW_HOVER, C_WHITE)
import layout_tokens as lay
from build_helpers import (_sum_expr, row_rule, row_hit, text_input, text_ctrl, group, button, card, flow_row, top_bar,
                           fit_button_width, ICON_W, grow, themed_dropdown, icon_on_mobile,
                           confirm_modal)
from hub_config import LIST, COL_NO, DOMAINS, STATUS, STATUS_ICON, APP_TARGET
from design_tokens import theme_query, ref_hex, ref as _t
from icons import MIRROR_X
import approval_flow
from layout_tokens import (if_below, below, at_least, SCROLLBAR_W, GALLERY_RESERVE, PAGE_PAD_R,
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
EDIT_ACTION = None


def use_actions(new_action, open_action, edit_action):
    """Den samlede app (BIO SAP App): "New" og "Open" navigerer til
    skaerme. new_action(domaene) -> formel; open_action (View) og
    edit_action (Edit) -> formler."""
    global NEW_ACTION, OPEN_ACTION, EDIT_ACTION
    if (not callable(new_action) or not isinstance(open_action, str)
            or not isinstance(edit_action, str)):
        raise SystemExit("build_hub.use_actions: new_action skal vaere en funktion, "
                         "open_action og edit_action formler.")
    NEW_ACTION, OPEN_ACTION, EDIT_ACTION = new_action, open_action, edit_action

# "New request"-menuen i bjaelken. Blank ved start = lukket.
MENU_OPEN = "IfError(varMdNewMenu, false)"
MENU_CLOSE = "Set(varMdNewMenu, false)"


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
#   HVIS    "My requests" (varMdView)   mine / hele afdelingen
#   HVILKE  Open / Closed / All       varMdStatusMode
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
# If OMKRING ENKLE FILTRE - IKKE ET FLADT FILTER (issue #84)
#
# I fase 1 stod her eet fladt Filter:
#     Filter(liste, varMdView <> "mine" || RequesterEmail = varMdMe,
#                   varMdStatusMode = "all" || IsOpen = (varMdStatusMode = "open"))
# Ved foerste deploy af den samlede app svarede SharePoint:
#     [MD_RequestIndex] The query is not valid.
# og alle tal stod paa 0. Den sandsynlige aarsag er IsOpen = (udtryk): en
# Ja/Nej-kolonne sammenlignet med et UDTRYK i stedet for true/false.
#
# Formen nedenfor er den, der var deployet og virkede: If vaelger mellem
# filtre, hvor hver betingelse er EEN kolonne mod en variabel eller en
# konstant (RequesterEmail = varMdMe, IsOpen = true). Domaene- og
# soegefiltret ovenpaa (ITEMS) er uaendret - det var ogsaa deployet.
#
# Stadig kun indekserede felter: RequesterEmail (tekst) og IsOpen (ja/nej).
# ET Filter MED ALLE BETINGELSER - IKKE Filter INDE I Filter (issue #84)
#
# "Mine" stod som Filter(Filter(liste, RequesterEmail = varMdMe), IsOpen =
# true). Med de rigtige data i listen (alle Peters raekker har
# RequesterEmail = pkbje@orsted.com og IsOpen = ja) kom der EEN raekke
# tilbage - en afvist. Alle-grenen, som er eet Filter, var rigtig. Hver
# gren er nu eet Filter, hvor betingelserne staar side om side.
def _scope(mine, status):
    cond = []
    if mine:
        cond.append("RequesterEmail = varMdMe")
    if status is not None:
        cond.append(f"IsOpen = {status}")
    return f"Filter('{LIST}', {', '.join(cond)})" if cond else f"'{LIST}'"


def _by_status(mine, indent=4):
    pad = " " * indent
    return ("If(\n"
            f"{pad}    varMdStatusMode = \"open\", {_scope(mine, 'true')},\n"
            f"{pad}    varMdStatusMode = \"done\", {_scope(mine, 'false')},\n"
            f"{pad}    {_scope(mine, None)}\n"
            f"{pad})")


SCOPE = (
    "If(\n"
    "        varMdView = \"mine\",\n"
    f"        {_by_status(True, 8)},\n"
    f"        {_by_status(False, 8)}\n"
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
SCOPE_REFRESH = (
    f"ClearCollect(colMdScope, ForAll({SCOPE} As R, {{ Domain: R.Domain.Value, "
    "Mine: R.AssignedToEmail = varMdMe, "
    "Stuck: R.IsOpen && R.LastActionOn < DateAdd(Now(), -5, TimeUnit.Days), "
    'Ret: R.Status.Value = "AfventerInfo" && R.RequesterEmail = varMdMe }))')
SCOPE_FULL = f"CountRows(colMdScope) >= {ROW_LIMIT}"

# SKAERMENS OnVisible - IKKE AFHAENGIG AF App.OnStart
#
# App.OnStart koerer SAMTIDIG med foerste skaerms OnVisible (non-blocking
# OnStart). Taellingen ovenfor stod alene i OnVisible og laeste varMdView og
# varMdMe, som OnStart saetter. Kom OnVisible foerst, var varMdView tom, og
# fliserne talte HELE afdelingen under overskriften "my requests" - til man
# trykkede paa en knap. Skaermen saetter derfor selv det, den taeller med,
# hvis det ikke er sat endnu.
HUB_ON_VISIBLE = (
    "Set(varMdMe, Lower(User().Email));\n"
    "If(IsBlank(varMdView), Set(varMdView, \"mine\"));\n"
    "If(IsBlank(varMdStatusMode), Set(varMdStatusMode, \"open\"));\n"
    "If(IsBlank(varMdFlag), Set(varMdFlag, \"\"));\n"
    "Concurrent(\n    " + SCOPE_REFRESH + ",\n    " + approval_flow.LOG_REFRESH + "\n)"
)


def scope_count(pred=None):
    """Antal i colMdScope (evt. afgraenset) som tekst - med "+" ved loftet."""
    n = f"CountRows(Filter(colMdScope, {pred}))" if pred else "CountRows(colMdScope)"
    return f'Text({n}) & If({SCOPE_FULL}, "+", "")'


# Flisernes undertekst: hvad tallet taeller.
SCOPE_WORDS = ('Switch(varMdStatusMode, "open", "Filter", "done", "Closed", "All") & '
               'If(varMdView = "mine", " - my requests", " - whole department")')

# De seneste lukkede indmeldinger i det valgte omfang - til Closed-preview'et.
CLOSED_LATEST = (
    "FirstN(\n"
    "    SortByColumns(\n"
    "        If(\n"
    "            varMdView = \"mine\",\n"
    f"            Filter('{LIST}', RequesterEmail = varMdMe, IsOpen = false),\n"
    f"            Filter('{LIST}', IsOpen = false)\n"
    "        ),\n"
    "        \"LastActionOn\", SortOrder.Descending\n"
    "    ),\n"
    "    5\n"
    ")"
)
PEEK_OPEN = "IfError(varMdClosedPeek, false)"

# Tabellens kolonner. EEN kilde til bredderne, saa overskriften og raekken
# ikke kan komme til at staa forskudt. Resten af bredden ligger i REQUEST,
# som regnes af de faste.
# Air sits after each left-aligned value, so a wide column widens the gap to its right neighbour.
DOM_TEXT = 156
REQ_AIR = 28
COLS = [("DOMAIN", 192), ("REQUEST", 0), ("PLANT", 64), ("REQUESTER", 84), ("APPROVAL", 270),
        ("STATUS", 130), ("UPDATED", 84), ("ACTIONS", 120)]
CW = dict(COLS)
TL_W = 28
GAP = 12
ROW_PAD = 12
FIXED = sum(w for _, w in COLS) + REQ_AIR + GAP * (len(COLS) - 1) + 2 * ROW_PAD
# Bruges BAADE i listehovedet og i galleriets raekke. REGNET AF DEN BREDDE,
# LISTEN HAR - ikke af Parent.Width, som er raekkens Width-EGENSKAB og
# hverken traekker kortets padding, galleriets TemplatePadding eller dets
# scrollbar fra.
AVAIL = f"({SHELL_W} - 36 - 4 - {SCROLLBAR_W} - {GALLERY_RESERVE})"
MAIN_CAP = 720
MAIN_W = f"Min({MAIN_CAP}, Max(0, {AVAIL} - {FIXED}))"
SLACK = f"Max(0, {AVAIL} - {FIXED} - {MAIN_CAP})"
CWF = {k: v for k, v in COLS if k != "REQUEST"}
CWF["REQUEST"] = f"({MAIN_W} + {REQ_AIR} + {SLACK})"

ROW_H = 52
GAL_ROWS = 14
ROW_H_C = 112
GAL_ROWS_C = 7
ROW_H_M = 62
GAL_ROWS_M = 8
STRIP_Y_C = 70
WHEN_FX = ("With(\n    { d: DateDiff(ThisItem.LastActionOn, Now(), TimeUnit.Days) },\n"
           "    If(d <= 0, \"Today\", If(d = 1, \"Yesterday\", Text(d) & \" days ago\"))\n)")

_AGE = "DateDiff(ThisItem.LastActionOn, Now(), TimeUnit.Days)"
STUCK = f"ThisItem.IsOpen && {_AGE} > 5"
STUCK_TXT = f'"Stuck " & Text({_AGE}) & " d"'
WHEN_SHORT = f'With({{ d: {_AGE} }}, If(d <= 0, "Today", Text(d) & " d ago"))'
INITIALS = 'Upper(First(Split(Coalesce(ThisItem.RequesterEmail, "?@"), "@")).Value)'

ICON_CHEVRON = "M9 6l6 6-6 6"
ICON_CLOCK = "M12 3a9 9 0 1 0 0 18a9 9 0 0 0 0-18zM12 7v5l3 2"

NO_W = 120

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
    seg = _view_switch(mobile=True)
    for s in seg:
        s.props["Visible"] = s.vis
    new = button("btnMdNewRequest", '"New request"', f"Set(varMdNewMenu, !{MENU_OPEN})",
                 width=fit_button_width('"New request"') + ICON_W, height=38,
                 icon="Add")
    for b_, lit in ((new, '"New request"'),):
        narrow_w = round((fit_button_width(lit, size=12, min_w=0) - 32) * 1.12) + ICON_W + 24
        b_.props["Width"] = f"If({below('Tablet')}, {narrow_w}, {b_.props['Width']})"
        b_.props["Size"] = f"If({below('Tablet')}, 12, {lay.SIZE_INPUT})"
    bar = top_bar("Md", '"Masterdatahub"',
                  '"SAP requests - " & If(varMdView = "mine", varMdMe, "whole department")',
                  seg + [new], icon="hub")
    return bar


def _view_switch(mobile=False):
    """My requests | Department as two outline buttons in the row, styled like Open/Closed/All.
    Mobile: My | All (first row under the top bar)."""
    btns = []
    size = 12 if mobile else lay.SIZE_INPUT
    for name, key, wide, short in (
            ("btnMdViewMine", "mine", "My requests", "My"),
            ("btnMdViewAll", "queue", "Department", "All")):
        label = short if mobile else wide
        w = fit_button_width(f'"{label}"', size=size, min_w=0) + 20
        b = button(name + ("M" if mobile else ""), f'"{label}"',
                   f'Set(varMdView, "{key}"); Set(varMdDomain, "");\n' + SCOPE_REFRESH,
                   width=w, height=36, accessible=f'"{wide}"')
        _selected_style(b, f'varMdView = "{key}"', idle_color=C_MUTED)
        b.props["Size"] = str(size)
        b.props["LayoutMinWidth"] = b.props["Width"]
        b.vis = below("Tablet") if mobile else at_least("Tablet")
        btns.append(b)
    return btns

MENU_W = 290
MENU_ITEM_H = 40


def _menu_item_svg(d, ready):
    fg = _hx("text-primary") if ready else _hx("text-muted")
    body = _dglyph(d, _hx(d["token"]) if ready else _hx("text-muted"), x=14, y=9,
                   size=22)
    body += (f"<text x='48' y='{MENU_ITEM_H // 2 + 5}' {SVG_FONT} font-size='14' "
             f"font-weight='600' fill='{fg}'>\" & \"{d['name']}\" & \"</text>")
    if not ready:
        body += (f"<text x='{MENU_W - 16 - 14}' y='{MENU_ITEM_H // 2 + 4}' text-anchor='end' "
                 f"{SVG_FONT} font-size='11' fill='{_hx('text-muted')}'>\" & \"Coming soon\" & \"</text>")
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
                 fill=C_MODAL_BG, border_color=C_CARD_BORDER, radius=lay.RADIUS_MODAL, pad=8,
                 drop_shadow="Bold", visible=MENU_OPEN, align_items="Start")
    menu.props["X"] = f"App.Width - Self.Width - {PAGE_PAD_R + SCROLLBAR_W}"
    # Lige under bjaelken: dens padding + titel og undertitel (30 + 2 + 20).
    menu.props["Y"] = if_below("Tablet", str(HEADER_PAD_T + 36 + 6), str(HEADER_PAD_T + 52 + 6))
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
TILE_GAP_X = TILE_GAP
TILE_PAD_T = 4
TILE_PAD_B = 8
# Fliserne gaar hele vejen ud til listens kanter (ingen sidepolstring).
TILES_CW = f"({SHELL_W})"
TILE_W = if_below("Desktop", f"({TILES_CW} - {2 * TILE_GAP}) / 3",
                  f"({TILES_CW} - {4 * TILE_GAP}) / 5")
TILE_LINES = if_below("Desktop", "2", "1")
# Mere kvadratiske fliser: ikon og navn oeverst, tallet stort under.
TILE_H = 148
TILE_H_M = 100
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
    words = d["name"].split(" ", 1)
    name_lines = "".join(
        f"<text x='8' y='{60 + 14 * i}' {SVG_FONT} font-size='11' font-weight='600' "
        f"fill='{_hx('text-primary')}'>{wd}</text>" for i, wd in enumerate(words))
    sub_y = 60 + 14 * len(words) + 4
    compact = ('"' + f"<svg xmlns='http://www.w3.org/2000/svg' width='{w}' height='{TILE_H_M}' "
               f"viewBox='0 0 {w} {TILE_H_M}'>"
               f"<rect width='{w}' height='{STRIPE_H}' fill='{c}'/>"
               f"<circle cx='24' cy='28' r='14' fill='{c}' fill-opacity='0.12'/>"
               + _dglyph(d, c, x=15, y=19, size=18) +
               f"<text x='{w}' dx='-8' y='38' text-anchor='end' {SVG_FONT} font-size='22' "
               f"font-weight='600' fill='{_hx('text-primary')}'>\" & {count_expr} & \"</text>"
               + name_lines +
               f"<text x='8' y='{sub_y}' {SVG_FONT} font-size='10' "
               f"fill='{_hx('text-muted')}'>\" & \"filter\" & \"</text></svg>" + '"')
    full = ('"' + f"<svg xmlns='http://www.w3.org/2000/svg' width='{w}' height='{h}' "
            f"viewBox='0 0 {w} {h}'>"
            f"<rect width='{w}' height='{STRIPE_H}' fill='{c}'/>"
            f"<circle cx='38' cy='46' r='20' fill='{c}' fill-opacity='0.12'/>"
            + _dglyph(d, c, x=28, y=36, size=20) +
            f"<text x='70' y='51' {SVG_FONT} font-size='15' font-weight='600' "
            f"fill='{_hx('text-primary')}'>\" & \"{d['name']}\" & \"</text>"
            f"<text x='18' y='108' {SVG_FONT} font-size='34' font-weight='600' "
            f"fill='{_hx('text-primary')}'>\" & {count_expr} & \"</text>"
            f"<text x='18' y='130' {SVG_FONT} font-size='12' "
            f"fill='{_hx('text-muted')}'>\" & {SCOPE_WORDS} & \"</text></svg>" + '"')
    return f"If({below('Tablet')}, {compact}, {full})"


def build_tiles():
    """De fem domaenefliser. Hele flisen filtrerer listen; "New request" i
    bjaelken er vejen til en ny indmelding (issue #74 fjernede flisernes
    egne "+ New")."""
    tiles = []
    for d in DOMAINS:
        n = d["short"]
        sel = f'varMdDomain = "{d["key"]}"'
        # Tallet taelles paa PRAECIS det saet, listen viser - omfang og
        # Open/Closed/All - bare afgraenset til domaenet.
        count = scope_count(f'Domain = "{d["key"]}"')

        st = _tile_state(d, sel)
        face = _image(f"imgMdTile{n}", _svg_uri(_tile_face(d, count)), "Parent.Width",
                      if_below("Tablet", str(TILE_H_M), str(TILE_H)),
                      onselect=f'Set(varMdDomain, If({sel}, "", "{d["key"]}"))',
                      # Uden tallet: det ville vaere endnu en forespoergsel.
                      label=f'If({sel}, "Show all domains", "Show only {d["name"].lower()}")',
                      hover=st["hover"])
        face.props["FocusedBorderColor"] = d["color"]

        tile = group(
            f"conMdTile{n}", [face], direction="Vertical", gap=0,
            fill=st["fill"], radius=lay.RADIUS_CARD, width=TILE_W,
            border_color=st["border"], border_thickness=st["thickness"])
        tile.props["DropShadow"] = st["shadow"]
        tiles.append(tile)

    tile_h = tiles[0].h
    return group("conMdTiles", tiles, direction="Horizontal", gap=TILE_GAP_X, wrap="true",
                 justify="Center",
                 pad=(TILE_PAD_T, 0, TILE_PAD_B, 0),
                 # SAMME braekpunkt som TILE_W. Var de uenige, ville beholderen
                 # have hoejde til een raekke fliser, mens fliserne selv stod i
                 # tre - og de to nederste raekker blev klippet af.
                 height=(f"{TILE_PAD_T} + {TILE_LINES} * ({tile_h}) + "
                         f"({TILE_LINES} - 1) * ({TILE_GAP_X}) + {TILE_PAD_B}"))


# ---------------------------------------------------------------------------
# Filtre
# ---------------------------------------------------------------------------
def _chip(name, label, value, icon):
    b = button(name, f'"{label}"', f'Set(varMdStatusMode, "{value}");\n' + SCOPE_REFRESH,
               width=fit_button_width(f'"{label}"') + ICON_W, height=36, icon=icon)
    return _selected_style(b, f'varMdStatusMode = "{value}"', idle_color=C_MUTED)


SEARCH_W = 280
SEARCH_MIN_W = 140


def _flag_pill(name, flag, label, field, icon):
    n = f"Text(CountRows(Filter(colMdScope, {field})))"
    b = button(name, f'"{label} (" & {n} & ")"',
               f'Set(varMdFlag, If(varMdFlag = "{flag}", "", "{flag}"));\n'
               'If(varMdFlag <> "", Set(varMdStatusMode, "open"));\n' + SCOPE_REFRESH,
               width=fit_button_width(f'"{label} (99)"') + ICON_W, height=36, icon=icon)
    return _selected_style(b, f'varMdFlag = "{flag}"', idle_color=C_MUTED)


def build_banner():
    """Returned requests of mine: counted in colMdScope, no extra query."""
    n = "CountRows(Filter(colMdScope, Ret))"
    msg = grow(text_ctrl("txtMdRetMsg",
                         f'Text({n}) & If({n} = 1, " request was", " requests were") & '
                         '" returned to you for changes"',
                         size=13, color=C_WARN_FG, weight="Semibold", height=22, wrap="false"))
    btn = button("btnMdRetShow", 'If(varMdFlag = "ret", "Show all", "Show them")',
                 'Set(varMdFlag, If(varMdFlag = "ret", "", "ret"));\n'
                 'If(varMdFlag <> "", Set(varMdStatusMode, "open"));\n' + SCOPE_REFRESH,
                 width=fit_button_width('"Show them"') + 8, height=32)
    return group("conMdRetBanner", [msg, btn], direction="Horizontal", gap=12, height=44,
                 align_items="Center", fill=C_WARN_BG, radius=lay.RADIUS_INPUT,
                 pad=(6, 12, 6, 16), visible=f"{n} > 0")


def build_filters():
    """Vaerktoejslinjen (issue #74):

        [Search number, text or plant...][Open][Closed][i][All]      42 requests

    Soegefeltet er saa bredt som det, man soeger efter (et nummer, et
    vaerk, et par ord) - ikke resten af linjen. Taelleren staar til hoejre
    og tager resten, saa den flugter med listens hoejre kant. My requests
    staar i bjaelken: det er et omfang, ikke et statusfilter."""
    # Det SAMME felt som alle andre (build_helpers.text_input -> input_theme,
    # issue #78) - ikke et haandbygget med sine egne farver.
    search = text_input("inpMdFind", '""', placeholder='"Search number, text or plant..."',
                        width=str(SEARCH_W), ttype="Search",
                        label='"Search number, text or plant"')
    shown = scope_count('varMdDomain = "" || Domain = varMdDomain')
    count = text_ctrl("txtMdTotal", f'{shown} & " requests"',
                      size=12, color=C_MUTED, height=36, align="Right", width=110, wrap="false")
    closed = _chip("btnMdFltDone", "Closed", "done", "CheckmarkCircle")
    # Statisk: tooltip'en hentede de seneste lukkede (en forespoergsel) ved
    # hver visning af skaermen. Info-knappen ved siden af viser dem.
    closed.props["Tooltip"] = '"Show closed requests - the (i) button lists the latest"'
    chips = [_chip("btnMdFltOpen", "Open", "open", "MailInbox"), closed, _peek_button(),
             _chip("btnMdFltAll", "All", "all", "TextBulletListLtr"),
             _flag_pill("btnMdFltMe", "me", "Waiting for me", "Mine", "Person"),
             _flag_pill("btnMdFltStuck", "stuck", "Stuck > 5 d", "Stuck", "Clock")]
    # Soegefelt og knapper staar til venstre; tallet tager resten af linjen.
    # Enten een linje, eller et felt pr. linje - se build_helpers.flow_row.
    # Under Tablet erstattes knapperne af EN dropdown (+ info-knappen).
    for c in chips + [count]:
        c.vis = at_least("Tablet")
    mobile = _mobile_filter()
    spacer = group("conMdFltGap", [], direction="Horizontal", height=0)
    spacer.vis = at_least("Tablet")
    search.props["Width"] = str(SEARCH_MIN_W)
    row = flow_row("conMdFltRow", [search] + chips + [spacer] + _view_switch() + [count], SHELL_W,
                   gap=10, flex=spacer, flex_min=0)
    # The search field gives way before the row stacks: it takes what the other
    # controls leave, between SEARCH_MIN_W and SEARCH_W.
    others = [str(c.props["Width"]) for c in row.children if c is not search and c is not spacer]
    rest = _sum_expr(others + ["0"], 10)
    search.props["Width"] = f"Max({SEARCH_MIN_W}, Min({SEARCH_W}, {SHELL_W} - ({rest})))"
    return group("conMdFlt", [row, mobile], direction="Vertical", gap=8)


_MOBILE_FILTERS = ("Open", "Closed", "All", "Waiting for me", "Stuck > 5 d")


def _mobile_filter():
    """Telefon: een dropdown med de samme valg som knapperne + info-knappen."""
    items = "Table(" + ", ".join(f'{{ Value: "{v}" }}' for v in _MOBILE_FILTERS) + ")"
    cur = ('Switch(varMdFlag, "me", "Waiting for me", "stuck", "Stuck > 5 d", '
           'Switch(varMdStatusMode, "done", "Closed", "all", "All", "Open"))')
    on_change = ('With({ v: Self.Selected.Value },\n'
                 '    Set(varMdFlag, Switch(v, "Waiting for me", "me", "Stuck > 5 d", "stuck", ""));\n'
                 '    Set(varMdStatusMode, Switch(v, "Closed", "done", "All", "all", "open"))\n'
                 ');\n' + SCOPE_REFRESH)
    dd = themed_dropdown("ddMdFltMobile", items, cur, width="Parent.Width",
                         label='"Filter requests"', onchange=on_change)
    dd = grow(dd, 80)
    peek = _peek_button("btnMdFltPeekM")
    row = group("conMdFltMobile", [dd, peek], direction="Horizontal", gap=8, height=36,
                width=f"({SHELL_W})", align_items="Center", visible=below("Tablet"))
    return row


# ---------------------------------------------------------------------------
# Closed-preview (issue #74) - KUN ved Closed
# ---------------------------------------------------------------------------
# To veje til det samme: hover over Closed viser de seneste lukkede som
# tooltip, og info-knappen ved siden af aabner en lille popover, hvor hver
# raekke kan aabnes. Knappen er vejen paa touch og med tastatur - en
# tooltip kan hverken naas med en finger eller klikkes i.
PEEK_W = 360
PEEK_ROW_H = 48


def _peek_button(name="btnMdFltPeek"):
    b = button(name, '""', f"Set(varMdClosedPeek, !{PEEK_OPEN})",
               width=36, height=36, icon="Info",
               accessible='"Show the latest closed requests"')
    b.props["Layout"] = "ButtonLayout.IconOnly"
    b.props["Tooltip"] = '"Latest closed requests"'
    return _selected_style(b, PEEK_OPEN, idle_color=C_MUTED)


def build_closed_peek():
    """Popoveren: [sloer, kort]. Staar paa skaermen efter rammen, som
    "New request"-menuen - se assemble_hub."""
    close = "Set(varMdClosedPeek, false)"
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
                    'If(varMdView = "mine", "My requests", "Whole department")',
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
                  width=PEEK_W, fill=C_MODAL_BG, border_color=C_CARD_BORDER, radius=lay.RADIUS_MODAL,
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
    '        varMdDomain = "" || Domain.Value = varMdDomain,\n'
    '        varMdFlag <> "me" || AssignedToEmail = varMdMe,\n'
    '        varMdFlag <> "stuck" || (IsOpen = true && LastActionOn < DateAdd(Now(), -5, TimeUnit.Days)),\n'
    '        varMdFlag <> "ret" || (Status.Value = "AfventerInfo" && RequesterEmail = varMdMe),\n'
    '        IsBlank(Trim(inpMdFind.Text)) ||\n'
    f"            StartsWith({COL_NO}, Trim(inpMdFind.Text)) ||\n"
    "            StartsWith(ShortText, Trim(inpMdFind.Text)) ||\n"
    "            StartsWith(Plant, Trim(inpMdFind.Text))\n"
    "    ),\n"
    '    "LastActionOn", SortOrder.Descending\n'
    ")"
)


def _open_action(mode="view"):
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
    return (EDIT_ACTION if mode == "edit" else OPEN_ACTION) or (
        f"With(\n    {{ u: {url} }},\n"
        "    If(\n"
        "        IsBlank(ThisItem.RequestGuid),\n"
        '        Notify("This request has no ID.", NotificationType.Error),\n'
        "        !IsBlank(u),\n"
        f'        Launch(u & "?reqid=" & ThisItem.RequestGuid & "&mode={mode}" & {THEME_Q_AMP}, {{ }}, {APP_TARGET}),\n'
        "        !IsBlank(ThisItem.AppUrl),\n"
        "        Launch(\n"
        '            If(Find("reqid=", ThisItem.AppUrl) > 0, ThisItem.AppUrl,\n'
        '                ThisItem.AppUrl & If(Find("?", ThisItem.AppUrl) > 0, "&", "?") &\n'
        '                    "reqid=" & ThisItem.RequestGuid) &\n'
        f'                "&mode={mode}" & {THEME_Q_AMP},\n'
        f"            {{ }}, {APP_TARGET}\n"
        "        ),\n"
        '        Notify("This request has no app URL.", NotificationType.Error)\n'
        "    )\n"
        ")")


def build_list():
    head = group("conMdListHead",
                 [text_ctrl(f"txtMdH{i}", f'"{t}"', size=lay.SIZE_MICRO, weight="Semibold", color=C_MUTED,
                            height=20, wrap="false",
                            width=CWF[k])
                  for i, (t, _w) in enumerate(COLS) for k in [t]],
                 direction="Horizontal", gap=GAP, height=20, align_items="Center",
                 pad=(0, ROW_PAD, 0, ROW_PAD), visible=at_least("Wide"))

    # DOMAIN: ikonet i domaenets farve og navnet.
    dom_icon = _image("imgMdRowDomain",
                      _svg_uri(_domain_switch(
                          lambda d: _icon_svg(d["icon"], _hx(d["token"]),
                                              mirror=d.get("mirror", False)), '""')),
                      24, 24)
    dom_name = text_ctrl("txtMdRowDomain",
                         _domain_switch(lambda d: f'"{d["name"]}"', '"?"'),
                         size=13, height=20, width=DOM_TEXT - 24 - 12, wrap="false")
    dom = group("conMdRowDom", [dom_icon, dom_name], direction="Horizontal", gap=12,
                width=CWF["DOMAIN"], align_items="Center")

    # DEN TOMME MIDTE (issue #74). Raekken viste kun nummer og kort tekst,
    # og resten af den bredeste kolonne stod tom. Nu staar det, indekset
    # ALLEREDE har, ud for nummeret: hvem der har oprettet den, hvor mange
    # linjer, SAP-nummeret, naar det findes, og hvem der sidst roerte den.
    # Ingen nye kald - det er kolonner i MD_RequestIndex, som galleriet
    # alligevel henter.
    no = text_ctrl("txtMdRowNo", f'ThisItem.{COL_NO} & " -"', size=13, weight="Semibold",
                   height=20, width=NO_W, wrap="false",
                   accessible=f"ThisItem.{COL_NO}")
    txt = text_ctrl("txtMdRowText", "ThisItem.ShortText", size=13, color=C_MUTED, height=20,
                    width=f"{MAIN_W} - {NO_W} - 8", wrap="false")
    main = group("conMdRowMain", [no, txt], direction="Horizontal", gap=8, width=CWF["REQUEST"],
                 height=20, align_items="Center")
    req = text_ctrl("txtMdRowReq", INITIALS, size=13, height=20, width=CWF["REQUESTER"], wrap="false",
                    accessible='"Requested by " & Coalesce(ThisItem.RequesterName, ThisItem.RequesterEmail)')

    plant = text_ctrl("txtMdRowPlant", "ThisItem.Plant", size=13, height=20,
                      width=CWF["PLANT"], wrap="false")

    approval = _image("imgMdRowApproval", _svg_uri(approval_flow.row_svg()), CW["APPROVAL"], 30,
                      label='"Approval progress"')

    st_icon = _image("imgMdRowStatus", _svg_uri(
        "Switch(\n    ThisItem.Status.Value,\n    " +
        ",\n    ".join(f'"{k}", {_icon_svg(path, _hx(tok))}'
                       for k, (path, tok) in STATUS_ICON.items()) +
        f',\n    {_icon_svg(STATUS_ICON["Kladde"][0], _hx("state-neutral-fg"))}\n)'),
        22, 22)
    st_lbl = text_ctrl("txtMdRowStatus", _switch(1, '"Unknown"', quote=True), size=13,
                       height=20, width=f"{CWF['STATUS']} - 22 - 10", wrap="false")
    st_top = group("conMdRowStatTop", [st_icon, st_lbl], direction="Horizontal", gap=10,
                   width=CWF["STATUS"], height=22, align_items="Center")
    stuck = text_ctrl("txtMdRowStuck", STUCK_TXT, size=12, color=C_WARN_FG, weight="Semibold",
                      height=16, width=CWF["STATUS"], wrap="false", visible=STUCK,
                      extra={"PaddingLeft": "32"})
    stat = group("conMdRowStat", [st_top, stuck], direction="Vertical", gap=0,
                 width=CWF["STATUS"], align_items="Stretch")

    when = text_ctrl("txtMdRowWhen", WHEN_SHORT, size=12, height=20, width=CWF["UPDATED"],
                     wrap="false", color=C_MUTED)

    act = _open_action()
    edit_btn, del_btn = _owner_buttons(_open_action("edit"), "")
    actions = [edit_btn, del_btn]

    row = group("conMdRow", [dom, main, plant, req, approval, stat, when],
                direction="Horizontal", gap=GAP, height="Parent.TemplateHeight - 1",
                align_items="Center", width="Parent.TemplateWidth", fill=C_CARD_BG,
                pad=(0, ROW_PAD, 0, ROW_PAD), visible=at_least("Wide"))

    # STREGEN MELLEM RAEKKERNE ER SIN EGEN FIGUR (issue #70)
    #
    # Den var galleriets FYLD, der saas i den 1 px, raekken var lavere end
    # skabelonen. Men fyldet ses ogsaa alle andre steder, galleriet ikke
    # har en raekke: under de sidste raekker naar filteret giver faa, og
    # ved siden af scrollbaren - et graat felt i en anden farve end
    # tabellen. Nu er galleriet i kortets farve, og stregen er en figur
    # nederst i hver raekke.
    rule = row_rule("rctMdRowRule", ROW_H)
    rule.props["Y"] = "Parent.TemplateHeight - 1"
    # HELE RAEKKEN ER KLIKBAR (issue #79) - samme handling som Open.
    hit = row_hit("btnMdRowHit", act,
                  f'"Open " & ThisItem.{COL_NO} & " - " & ThisItem.ShortText',
                  "Parent.TemplateWidth", "Parent.TemplateHeight - 1")
    strip_x = (f"{ROW_PAD} + {CWF['DOMAIN']} + {GAP} + {CWF['REQUEST']} + {GAP} + {CWF['PLANT']} + {GAP} + "
               f"{CWF['REQUESTER']} + {GAP}")
    tl_x = (f"{strip_x} + {CW['APPROVAL']} + {GAP} + {CWF['STATUS']} + {GAP} + {CWF['UPDATED']} + {GAP}")
    timeline = _image("imgMdRowTimeline", _svg_uri(_icon_svg(ICON_CLOCK, _hx("text-muted"))), TL_W,
                      TL_W, onselect=approval_flow.timeline_fx(),
                      label=f'"Activity for " & ThisItem.{COL_NO}', hover=C_ROW_HOVER)
    timeline.props["X"] = if_below("Wide", f"Parent.Width - {SCROLLBAR_W} - {ROW_PAD} - {TL_W}", tl_x)
    timeline.props["Y"] = if_below("Wide", "8", f"(Parent.TemplateHeight - 1 - {TL_W}) / 2")
    for i, b in enumerate(actions):
        b.props["X"] = f"{tl_x} + {TL_W} + 12 + {i * 40}"
        b.props["Y"] = "(Parent.TemplateHeight - 1 - 30) / 2"
        b.props["Visible"] = f"{at_least('Wide')} && ({b.props['Visible']})"
    strip = approval_flow.strip_hits(
        CW["APPROVAL"], strip_x,
        compact={"x": str(ROW_PAD), "y": str(STRIP_Y_C - 5), "zone": "(Parent.TemplateWidth - 24) / 4"})
    compact_row, compact_strip = _compact_row(act)
    c_edit, c_del = _owner_buttons(_open_action("edit"), "C")
    c_actions = [c_edit, c_del]
    for i, b in enumerate(c_actions):
        b.props["X"] = f"Parent.Width - {SCROLLBAR_W} - {ROW_PAD} - {TL_W} - 8 - 80 + {i * 40}"
        b.props["Y"] = "6"
        b.props["Visible"] = f"{at_least('Desktop')} && {below('Wide')} && ({b.props['Visible']})"
    for b in (*actions, *c_actions):
        b.props["HoverFill"] = C_ROW_HOVER
        b.props["PressedFill"] = C_ROW_HOVER
    c_base = f"Parent.Width - {SCROLLBAR_W} - {ROW_PAD} - {TL_W} - 8 - 80"
    zone_w = 80 + 8 + TL_W + 8
    zone = _image("imgMdRowActionsZone", '""', zone_w, 34, onselect="false", hover=C_CARD_BG)
    zone.props["Fill"] = C_CARD_BG
    zone.props["X"] = if_below("Wide", f"{c_base} - 4", f"{tl_x} - 4")
    zone.props["Y"] = if_below("Wide", "4", "(Parent.TemplateHeight - 1 - 34) / 2")
    zone.props["Width"] = if_below("Wide", str(zone_w), str(TL_W + 12 + 72 + 8))
    zone.props["Visible"] = at_least("Desktop")
    gal = Ctrl("galMdRequests", "Gallery", variant="Vertical", props={
        "AccessibleLabel": '"Requests"',
        "BorderStyle": "BorderStyle.None", "Fill": C_CARD_BG, "FillPortions": "0",
        "Height": if_below("Tablet", str(GAL_ROWS_M * ROW_H_M),
                           if_below("Wide", str(GAL_ROWS_C * ROW_H_C), str(GAL_ROWS * ROW_H))),
        "Items": ITEMS, "LayoutMinWidth": "0", "LoadingSpinner": "LoadingSpinner.Controls",
        "Selectable": "false", "ShowScrollbar": "true", "TabIndex": "0",
        "TemplatePadding": "0",
        "TemplateSize": if_below("Tablet", str(ROW_H_M),
                                 if_below("Wide", str(ROW_H_C), str(ROW_H))),
        "Width": "Parent.Width",
        "WrapCount": "1",
    }, children=[row, compact_row, compact_strip, rule, hit, *strip, zone, timeline, *actions, *c_actions], h=GAL_ROWS * ROW_H)

    empty = text_ctrl("txtMdEmpty", '"No requests match the filters."', size=13,
                      color=C_MUTED, height=24, wrap="true",
                      # GALLERIETS egne raekker - ikke en ny forespoergsel.
                      # En hoejde maa ikke kunne fejle paa netvaerket.
                      visible="IsEmpty(galMdRequests.AllItems)")

    # Streg mellem overskriften og den foerste raekke.
    head_rule = group("conMdListRule", [], direction="Horizontal", height=1,
                      fill=C_DIVIDER, visible=at_least("Wide"))

    parts = [_active_filter(), head, head_rule, gal, empty]
    gal.h = GAL_ROWS_C * ROW_H_C
    h_compact = card("conMdListCard", parts, gap=8).props["Height"]
    gal.h = GAL_ROWS_M * ROW_H_M
    h_mobile = card("conMdListCard", parts, gap=8).props["Height"]
    gal.h = GAL_ROWS * ROW_H
    out = card("conMdListCard", parts, gap=8)
    out.props["Height"] = if_below("Tablet", h_mobile, if_below("Wide", h_compact, out.props["Height"]))
    return out

def _owner_buttons(act, suffix):
    """Edit and Delete: shown and enabled for the creator's own requests."""
    own = 'Lower(Coalesce(ThisItem.RequesterEmail, "")) = varMdMe'
    edit = _image("btnMdRowEdit" + suffix,
                  _svg_uri(_icon_svg("M4 20h4L19 9l-4-4L4 16v4z M13.5 6.5l4 4", _hx("text-muted"))),
                  TL_W, TL_W, onselect=act, label=f'"Edit " & ThisItem.{COL_NO}', hover=C_ROW_HOVER)
    dele = _image("btnMdRowDelete" + suffix,
                  _svg_uri(_icon_svg("M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3", _hx("state-error-fg"))),
                  TL_W, TL_W, onselect="Set(varMdDelItem, ThisItem);\nSet(varMdDeleteOpen, true)",
                  label=f'"Delete " & ThisItem.{COL_NO}', hover=C_ROW_HOVER)
    for b in (edit, dele):
        b.props["Visible"] = own
    return edit, dele


def build_delete_modal():
    fx = (f"IfError(\n    Remove('{LIST}', LookUp('{LIST}', ID = varMdDelItem.ID));\n"
          '    Notify("Request deleted.", NotificationType.Success);\n    true,\n'
          '    Notify("The request could not be deleted.", NotificationType.Error);\n    false\n);\n'
          + SCOPE_REFRESH)
    return confirm_modal("MdDel", "varMdDeleteOpen", "Delete request",
                         f'"Delete " & varMdDelItem.{COL_NO} & "? This cannot be undone."',
                         "Delete", fx, "btnMdDelConfirm", icon="Delete")


def _compact_row(act):
    """Card row below Desktop: the essentials; the approval strip and the row itself open the details."""
    dom_icon = _image("imgMdRowDomainC",
                      _svg_uri(_domain_switch(
                          lambda d: _icon_svg(d["icon"], _hx(d["token"]),
                                              mirror=d.get("mirror", False)), '""')), 20, 20)
    no = grow(text_ctrl("txtMdRowNoC", f"ThisItem.{COL_NO}", size=14, weight="Semibold",
                        height=22, wrap="false"))
    st_icon = _image("imgMdRowStatusC", _svg_uri(
        "Switch(\n    ThisItem.Status.Value,\n    " +
        ",\n    ".join(f'"{k}", {_icon_svg(path, _hx(tok))}'
                       for k, (path, tok) in STATUS_ICON.items()) +
        f',\n    {_icon_svg(STATUS_ICON["Kladde"][0], _hx("state-neutral-fg"))}\n)'), 18, 18)
    st_lbl = text_ctrl("txtMdRowStatusC", _switch(1, '"Unknown"', quote=True), size=12,
                       height=20, width=96, wrap="false")
    line1 = group("conMdRowLineC1", [dom_icon, no, st_icon, st_lbl], direction="Horizontal", gap=8,
                  height=22, align_items="Center",
                  pad=(0, if_below("Tablet", str(TL_W + 6), str(TL_W + 6 + 144)), 0, 0))
    st_lbl.vis = at_least("Tablet")
    line2 = text_ctrl("txtMdRowTextC",
                      f'If({below("Tablet")}, ' + _domain_switch(lambda d: f'"{d["name"]}"', '"?"') +
                      ' & "  \u00b7  " & ThisItem.ShortText, ThisItem.ShortText)',
                      size=13, height=18, wrap="false")
    line3 = text_ctrl("txtMdRowMetaC",
                      _domain_switch(lambda d: f'"{d["name"]}"', '"?"') +
                      f' & "  \u00b7  " & {INITIALS} & "  \u00b7  Plant " & ThisItem.Plant & "  \u00b7  " & {WHEN_FX} & '
                      f'If({STUCK}, "  \u00b7  " & {STUCK_TXT}, "")',
                      size=12, color=C_MUTED, height=18, wrap="false", visible=at_least("Tablet"))
    row = group("conMdRowC", [line1, line2, line3], direction="Vertical", gap=2,
                height="Parent.TemplateHeight - 1", align_items="Stretch",
                width=f"Parent.Width - {SCROLLBAR_W}", fill=C_CARD_BG, pad=(8, ROW_PAD, 0, ROW_PAD),
                visible=below("Wide"))
    strip = _image("imgMdRowApprovalC", _svg_uri(approval_flow.row_svg()), 0, 30,
                   label='"Approval progress"')
    strip.props["Width"] = "Parent.TemplateWidth - 24"
    strip.props["X"] = str(ROW_PAD)
    strip.props["Y"] = str(STRIP_Y_C)
    strip.props["ImagePosition"] = "ImagePosition.Stretch"
    strip.props["Visible"] = f"{below('Wide')} && {at_least('Tablet')}"
    strip.vis = strip.props["Visible"]
    return row, strip


def _active_filter():
    """Det aktive domaenefilter over tabellen (issue #70) - i domaenets
    farve, saa man kan se, HVORFOR listen er kortere, og fjerne filteret
    uden at finde flisen igen. Tabellen selv forbliver neutral: farven
    staar kun her, paa flisens kant og i ikonerne."""
    on = 'varMdDomain <> ""'
    color = _domain_switch_on("varMdDomain", lambda d: d["color"], C_PRIMARY)
    name = _domain_switch_on("varMdDomain", lambda d: f'"{d["name"]}"', '""')
    longest = max((d["name"] for d in DOMAINS), key=len)
    chip = button("btnMdActiveDomain", f'"Filter: " & {name}',
                  'Set(varMdDomain, "")', height=30,
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
