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
from gen_screen import (Ctrl, C_CARD_BG, C_CARD_BORDER, C_TITLE, C_MUTED, C_PRIMARY,
                        C_MUTED_BG, C_MODAL_BG, C_DIVIDER, C_TRANSPARENT, FONT, SHELL_W)
from build_helpers import (text_ctrl, group, button, card, flow_row, top_bar,
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
# Afgraensningen. Begge grene er delegerbare hver for sig:
#   Mine  - afgraenset af brugeren, altid en haandterbar maengde
#   Koeen - afgraenset af IsOpen, et indekseret boolsk felt
# IsOpen vedligeholdes af submit-flowet sammen med Status. Et enkelt boolsk
# felt er delegerbart; en raekke OR'ede statusvaerdier er det ikke.
# ---------------------------------------------------------------------------
SCOPE = (
    "If(\n"
    "    gblView = \"mine\",\n"
    f"    Filter('{LIST}', RequesterEmail = gblMe),\n"
    f"    Filter('{LIST}', IsOpen = true)\n"
    ")"
)

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
                  'Set(gblView, If(gblView = "mine", "queue", "mine")); Set(gblDomain, "")',
                  width=fit_button_width('"My requests"') + ICON_W, height=36, icon="Person",
                  accessible='If(gblView = "mine", "Showing my requests - show the queue", '
                             '"Showing the queue - show my requests")')
    _selected_style(mine, 'gblView = "mine"')
    new = button("btnMdNewRequest", '"New request"', f"Set(gblNewMenu, !{MENU_OPEN})",
                 primary=True, width=fit_button_width('"New request"') + ICON_W, height=36,
                 icon="Add")
    return top_bar("Md", '"Masterdatahub"',
                   '"SAP requests - " & If(gblView = "mine", gblMe, "queue, whole department")',
                   [mine, new])


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
TILE_FACE_H = 156


def _tile_state(d, sel):
    """Flisens tilstande - de SAMME for alle fem, kun farven er domaenets.

        standard   kortets fyld, 1 px graa kant, ingen skygge
        hover      forsiden toner svagt i domaenets bloede farve
        trykket    samme toning
        fokus      2 px kant i domaenets farve om forsiden (tastatur)
        valgt      2 px kant i domaenets farve, bloed toning af hele
                   flisen og en let skygge - ikke en kraftig baggrund

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
    """Flisens forside som EEN SVG: ikonet i en tonet cirkel, navnet,
    tallet og teksten under. Bredden er billedets egen (Self.Width), saa
    indholdet staar til venstre og intet skaleres.

    Et billede har OnSelect - det har en tekst ikke. Derfor er forsiden et
    billede: saa er hele flisen (paa naer "New") filterknappen."""
    c = _hx(d["token"])
    w = '" & Self.Width & "'
    h = TILE_FACE_H
    return ('"' + f"<svg xmlns='http://www.w3.org/2000/svg' width='{w}' height='{h}' "
            f"viewBox='0 0 {w} {h}'>"
            f"<circle cx='40' cy='40' r='24' fill='{c}' fill-opacity='0.12'/>"
            + _dglyph(d, c, x=28, y=28) +
            f"<text x='16' y='92' {SVG_FONT} font-size='15' font-weight='600' "
            f"fill='{_hx('text-primary')}'>{d['name']}</text>"
            f"<text x='16' y='126' {SVG_FONT} font-size='28' font-weight='600' "
            f"fill='{_hx('text-primary')}'>\" & {count_expr} & \"</text>"
            f"<text x='16' y='146' {SVG_FONT} font-size='12' "
            f"fill='{_hx('text-muted')}'>\" & "
            'If(gblView = "mine", "open with me", "open in the queue")'
            " & \"</text></svg>" + '"')


def build_tiles():
    tiles = []
    for d in DOMAINS:
        n = d["short"]
        sel = f'gblDomain = "{d["key"]}"'
        # Tallet taelles paa det samme afgraensede saet som galleriet bruger -
        # ikke som et selvstaendigt opslag mod hele listen.
        count = f'Text(CountRows(Filter({SCOPE}, Domain.Value = "{d["key"]}", IsOpen = true)))'

        st = _tile_state(d, sel)
        stripe = group(f"conMdStripe{n}", [], height=4, fill=d["color"],
                       direction="Horizontal")
        face = _image(f"imgMdTile{n}", _svg_uri(_tile_face(d, count)), "Parent.Width",
                      TILE_FACE_H,
                      onselect=f'Set(gblDomain, If({sel}, "", "{d["key"]}"))',
                      # Uden tallet: det ville vaere endnu en forespoergsel.
                      label=f'If({sel}, "Show all domains", "Show only {d["name"].lower()}")',
                      hover=st["hover"])
        face.props["FocusedBorderColor"] = d["color"]

        act, ready = _new_action(d)
        label = '"New"' if ready else '"Coming soon"'
        bNew = button(f"btnMdTileNew{n}", label, act,
                      width=fit_button_width(label) + (ICON_W if ready else 0), height=32,
                      icon="Add" if ready else None,
                      accessible=f'"New {d["name"].lower()} request"' if ready else label,
                      display_mode="DisplayMode.Edit" if ready else "DisplayMode.Disabled")
        if ready:
            # Knappen i domaenets farve - tekst, ikon og kant.
            bNew.props["Color"] = d["color"]
            bNew.props["BorderColor"] = d["color"]
        btns = group(f"conMdTileBtns{n}", [bNew], direction="Horizontal", gap=6,
                     pad=(0, 16, 16, 16), align_items="Center")

        # Stregen foroven har domaenets farve hele tiden; kant, toning og
        # skygge kun naar flisen filtrerer listen (_tile_state).
        tile = group(
            f"conMdTile{n}", [stripe, face, btns], direction="Vertical", gap=0,
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
    b = button(name, f'"{label}"', f'Set(gblStatusMode, "{value}")',
               width=fit_button_width(f'"{label}"') + ICON_W, height=36, icon=icon)
    return _selected_style(b, f'gblStatusMode = "{value}"', idle_color=C_MUTED)


def build_filters():
    search = Ctrl("txtMdSearch", "ModernTextInput", props={
        "AccessibleLabel": '"Search number, text or plant"',
        "BorderColor": C_CARD_BORDER, "BorderStyle": "BorderStyle.Solid", "BorderThickness": "1",
        "Color": C_TITLE, "Default": '""', "Fill": C_CARD_BG, "Font": FONT, "Height": "36",
        "LayoutMinWidth": "0", "Placeholder": '"Search number, text or plant..."',
        "RadiusBottomLeft": "10", "RadiusBottomRight": "10",
        "RadiusTopLeft": "10", "RadiusTopRight": "10",
        "Size": "13", "Type": "TextInputType.Search",
        "Width": "0",   # flow_row: resten af linjen, mindst 180
    }, h=36)
    count = text_ctrl("txtMdCount", f'Text(CountRows({SCOPE})) & " requests"',
                      size=12, color=C_MUTED, height=36, align="Right", width=110, wrap="false")
    kids = [search, _chip("btnMdStOpen", "Open", "open", "MailInbox"),
            _chip("btnMdStDone", "Closed", "done", "CheckmarkCircle"),
            _chip("btnMdStAll", "All", "all", "TextBulletListLtr"), count]
    # Enten een linje, eller et felt pr. linje - se build_helpers.flow_row.
    return flow_row("conMdFilters", kids, SHELL_W, gap=10, flex=search, flex_min=180)


# ---------------------------------------------------------------------------
# Listen
# ---------------------------------------------------------------------------
ITEMS = (
    "SortByColumns(\n"
    "    Filter(\n"
    f"        {SCOPE},\n"
    '        gblDomain = "" || Domain.Value = gblDomain,\n'
    '        gblStatusMode = "all" || (gblStatusMode = "open" && IsOpen) ||\n'
    '            (gblStatusMode = "done" && !IsOpen),\n'
    '        IsBlank(Trim(txtMdSearch.Text)) ||\n'
    f"            StartsWith({COL_NO}, Trim(txtMdSearch.Text)) ||\n"
    "            StartsWith(ShortText, Trim(txtMdSearch.Text)) ||\n"
    "            StartsWith(Plant, Trim(txtMdSearch.Text))\n"
    "    ),\n"
    '    "LastActionOn", SortOrder.Descending\n'
    ")"
)


def _open_action():
    return OPEN_ACTION or (
        "If(\n"
        "    IsBlank(ThisItem.AppUrl),\n"
        '    Notify("This request has no app URL.", NotificationType.Error),\n'
        "    Launch(\n"
        '        ThisItem.AppUrl & If(Find("?", ThisItem.AppUrl) > 0, "&", "?") &\n'
        f'            "reqid=" & ThisItem.RequestGuid & {THEME_Q_AMP},\n'
        "        { },\n"
        f"        {APP_TARGET}\n"
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

    no = text_ctrl("txtMdRowNo", f"ThisItem.{COL_NO}", size=13, height=20, wrap="false")
    txt = text_ctrl("txtMdRowText", "ThisItem.ShortText", size=12, color=C_MUTED, height=18,
                    wrap="false")
    main = group("conMdRowMain", [no, txt], direction="Vertical", gap=0, width=MAIN_W,
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
    rule = Ctrl("rctMdRowRule", "Rectangle", props={
        "AccessibleLabel": '""', "BorderStyle": "BorderStyle.None",
        "BorderThickness": "0", "Fill": C_DIVIDER, "Height": "1",
        "OnSelect": "false", "TabIndex": "-1",
        "Width": "Parent.TemplateWidth", "X": "0", "Y": str(ROW_H - 1),
    }, h=1)
    gal = Ctrl("galMdRequests", "Gallery", variant="Vertical", props={
        "AccessibleLabel": '"Requests"',
        "BorderStyle": "BorderStyle.None", "Fill": C_CARD_BG, "FillPortions": "0",
        "Height": str(GAL_ROWS * ROW_H),
        "Items": ITEMS, "LayoutMinWidth": "0", "LoadingSpinner": "LoadingSpinner.Controls",
        "Selectable": "false", "ShowScrollbar": "true", "TabIndex": "0",
        "TemplatePadding": "0", "TemplateSize": str(ROW_H),
        "Width": "Parent.Width", "WrapCount": "1",
    }, children=[row, rule], h=GAL_ROWS * ROW_H)

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
