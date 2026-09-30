# -*- coding: utf-8 -*-
"""
Sidebaren - den SAMME i alle fem apps.

Forlaegget er HTML-sidens navigationsskinne (html/shell.js buildRail,
html/shell.css .kv-rail): logo oeverst, en ikonliste med de moduler, man
kan gaa til, og en fod med indstillinger. Lukket er den en smal skinne
med ikoner; aabnet viser den teksterne ved siden af.

    lukket (NAV_W)        aabnet (NAV_W_OPEN)
    +------+              +------------------------+
    | [BS] |              | [BS]  BIO SAP          |
    |  >>  |              |  <<                    |
    |  ^   |              |  ^    Masterdata Hub   |
    |  o   |              |  o    Functional ...   |
    | |=   |              | |=    VH-plan    <- markeret: den app, man er i
    |  ..  |              |  ..   ...              |
    |------|              |------------------------|
    |  ?   |              | ( HELP  (?) )          |   <- kun hvor appen har hjaelp
    |  o   |              | ( LIGHT (sol) )        |
    +------+              +------------------------+

HVAD DER ER TAGET MED FRA HTML-SIDEN
------------------------------------
  * Logo-maerket "BS" og ordmaerket "BIO SAP".
  * Ikonerne - de samme stier som NAV_ITEMS i shell.js.
  * Den aktive side: lys baggrund, accentfarve og den smalle accentstreg
    ude ved kanten (".kv-rail-item[aria-current=page]::before").
  * Aabnet ligger den OVEN PAA indholdet med en skygge - "Expands as an
    overlay so the workspace never reflows". Derfor regner SHELL_W kun
    med den lukkede bredde (tools/layout_tokens.py, NAV_W).
  * Foden med en streg over. HTML-siden har soegning og taethed dér; her
    staar Help- og temakontakten, som foer stod i topbjaelken.

HVAD DER ER ANDERLEDES
----------------------
  * HTML-skinnen aabner, naar musen er over den. En canvas app har ingen
    hover-haendelse, og paa en trykskaerm findes den slet ikke - derfor
    en knap (">>" / "<<"), der aabner og lukker. Kun dobbeltpilen - ordet
    "Collapse" er fjernet (issue #65); knappens AccessibleLabel og
    Tooltip siger det stadig.

MOBIL: EN TOPBJAELKE I STEDET FOR SKINNEN (issue #65)
-----------------------------------------------------
Under Tablet (layout_tokens.NAV_ON er falsk) er skinnen skjult, og en
topbjaelke i fuld bredde staar oeverst:

    +--------------------------------------------+
    | [=]  [BS] BIO SAP              VH-plan     |
    +--------------------------------------------+

Menuknappen (hamburger) aabner det SAMME panel som skinnens ">>" - alle
punkter med tekst, Help og temaet - som en skuffe fra venstre, med det
gennemsigtige sloer bag. Der er altsaa een navigation, een markering af
den aktive app og een Launch/Navigate pr. punkt; bjaelken er kun en
anden maade at aabne den paa. Rammen staar under bjaelken
(layout_tokens.ROOT_Y).
  * Et klik uden for den aabne sidebar lukker den (et gennemsigtigt
    sloer bag den), saa den ikke skal lukkes med knappen.
  * Lukket og aaben er TO containere med hver sin faste bredde: skinnen
    (con<X>Nav) og panelet (con<X>NavOpen, Visible = gblNavOpen). Se
    _column for hvorfor.
  * Kommandopaletten (Ctrl+K) og taethedsvalget er ikke med. De soeger i
    og aendrer HTML-sidens DOM; det har en canvas app ikke.

HVORFOR SVG-BILLEDER
--------------------
Hvert punkt er EET Image med en SVG, af samme grund som temaknappen
(build_helpers.theme_button): en moderne knap tegner Fluent-temaets form,
ikke vores, og kan hverken have et ikon efter eget valg eller accent-
stregen. Farverne er tokens (C.'hex-...'), saa den skifter tema med alt
andet.

NAVIGATION
----------
Launch(url, {}, LaunchTarget.Replace) med temaet i URL'en - samme regel
som "To the hub" havde (se SKILL.md, "Navigation mellem apps"). En app
uden app-id i tools/canvas_apps.json kommer ikke med.

I DEN SAMLEDE APP (BIO SAP App/) er modulerne skaerme, ikke apps. Dens
bygger saetter SCREENS, og saa bliver hvert punkt Navigate() til en
skaerm i stedet for Launch() af en anden app - ingen kold start, og det,
man var i gang med, ligger der stadig, naar man kommer tilbage. Uden
SCREENS (de fem enkelte apps) er intet aendret.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import Ctrl, C_SURFACE, C_DIVIDER, C_MUTED_BG, C_PRIMARY
from design_tokens import ref_hex, theme_query, TRANSPARENT
from gen_screen import C_TITLE
from build_helpers import group, theme_button, help_toggle, text_ctrl, grow, THEME_TOGGLE_H
import layout_tokens as lay
import env_config as env
import icons

# Aaben eller lukket. Blank ved start = lukket. Den gemmes ikke: en
# sidebar, der stod aaben fra sidst, ville ligge oven paa formularen.
OPEN = "gblNavOpen"
CLOSE = f"Set({OPEN}, false)"

ITEM_H = 40
BRAND_H = 44

# (noegle i canvas_apps.json, tekst, ikon). Raekkefoelgen og ikonerne er
# NAV_ITEMS i html/shell.js; teksterne er appsenes egne navne.
ITEMS = [
    ("hub", "Masterdata Hub",
     "M3 10.5 12 3l9 7.5M5.5 9.5V20h13V9.5"),
    ("functionallocation", "Functional Location", icons.FUNCTIONAL_LOCATION),
    ("vhplan", "VH-plan",
     "M4 6.5h16M4 12h16M4 17.5h10 M17.5 16.5l1.6 1.6 3-3.2"),
    ("material", "Materials",
     "M12 3 21 8v8l-9 5-9-5V8l9-5Z M3 8l9 5 9-5 M12 13v8"),
    ("equipment", "Equipments",
     "M7 7h10v10H7z M4.5 10.5h2.5M4.5 13.5h2.5M17 10.5h2.5M17 13.5h2.5"
     "M10.5 4.5V7M13.5 4.5V7M10.5 17v2.5M13.5 17v2.5"),
]

# DEN SAMLEDE APP: {noegle: skaermnavn}. None = de fem enkelte apps, hvor
# et punkt er Launch() af en anden app. Saettes af BIO SAP App/build.
SCREENS = None

ICON_EXPAND = "M6 6l6 6-6 6 M12 6l6 6-6 6"
ICON_MENU = "M4 7h16M4 12h16M4 17h16"
ICON_COLLAPSE = "M18 6l-6 6 6 6 M12 6l-6 6 6 6"

FONT = "font-family='Segoe UI, sans-serif'"


def _hx(name):
    return "\" & %s & \"" % ref_hex(name)


def _svg(w, h, body):
    return ('"' + f"<svg xmlns='http://www.w3.org/2000/svg' width='{w}' "
            f"height='{h}' viewBox='0 0 {w} {h}'>" + body + "</svg>" + '"')


def _icon(path, color):
    """Ikonet fra shell.js: viewBox 24, tegnet 18 px stort og centreret i
    den lukkede skinne."""
    s = 18 / 24
    x = (lay.NAV_W - 18) / 2
    y = (ITEM_H - 18) / 2
    return (f"<g transform='translate({x:g} {y:g}) scale({s:g})' fill='none' "
            f"stroke='{color}' stroke-width='1.6' stroke-linecap='round' "
            f"stroke-linejoin='round'><path d='{path}'/></g>")


def _item_svg(w, path, label, current):
    """Et punkt. current = den app, man staar i: baggrund, accentfarve og
    stregen ude ved kanten, som i shell.css."""
    fg = _hx("state-info-fg") if current else _hx("text-muted")
    body = ""
    if current:
        body += (f"<rect x='8' y='0' width='{w - 16}' height='{ITEM_H}' rx='8' "
                 f"fill='{_hx('state-info-bg')}'/>"
                 f"<rect x='0' y='{ITEM_H // 2 - 10}' width='3' height='20' rx='1.5' "
                 f"fill='{_hx('color-brand-primary')}'/>")
    body += _icon(path, fg)
    if label:
        body += (f"<text x='{lay.NAV_W}' y='{ITEM_H // 2 + 5}' {FONT} "
                 f"font-size='14' font-weight='600' fill='{fg}'>{label}</text>")
    return _svg(w, ITEM_H, body)


def _brand_svg(w, wordmark):
    m = 26
    x = (lay.NAV_W - m) // 2
    y = (BRAND_H - m) // 2
    body = (f"<rect x='{x}' y='{y}' width='{m}' height='{m}' rx='7' "
            f"fill='{_hx('color-brand-primary')}'/>"
            f"<text x='{x + m // 2}' y='{y + 17}' text-anchor='middle' "
            f"font-family='Consolas, monospace' font-size='11' font-weight='700' "
            f"fill='{_hx('text-on-primary')}'>BS</text>")
    if wordmark:
        body += (f"<text x='{lay.NAV_W}' y='{BRAND_H // 2 + 6}' {FONT} "
                 f"font-size='16' font-weight='600' "
                 f"fill='{_hx('text-primary')}'>BIO SAP</text>")
    return _svg(w, BRAND_H, body)


def _image(name, svg, width, height, onselect, label, tooltip=None, hover=True):
    t = TRANSPARENT
    props = {
        "AccessibleLabel": label,
        "BorderStyle": "BorderStyle.None",
        "BorderThickness": "0",
        "Fill": t,
        "FocusedBorderColor": C_PRIMARY,
        "FocusedBorderThickness": "2",
        "Height": str(height),
        "HoverFill": C_MUTED_BG if hover else t,
        "Image": f'"data:image/svg+xml;utf8," & EncodeUrl({svg})',
        "ImagePosition": "ImagePosition.Fit",
        "OnSelect": onselect,
        "PressedFill": C_MUTED_BG if hover else t,
        "TabIndex": "0",
        "Width": str(width),
    }
    if tooltip:
        props["Tooltip"] = tooltip
    return Ctrl(name, "Image", props=props, h=height)


def _launch(key):
    if SCREENS is not None:
        return f"{CLOSE}; Navigate({SCREENS[key]}, ScreenTransition.None)"
    url = env.play_url(key)
    return f'{CLOSE}; Launch("{url}" & {theme_query("?")}, {{ }}, LaunchTarget.Replace)'


def _column(p, suffix, w, current, is_open, help_on, help_action):
    """Een udgave af sidebaren: den lukkede skinne eller det aabne panel.

    ALLE BREDDER ER FASTE TAL. Den foerste udgave var EEN container med
    Width = If(gblNavOpen, 232, 56). I Studio blev den ved med at vaere
    57 px bred: billederne inden i skiftede til den aabne udgave, men
    containeren klippede dem ved kanten, og panelet saa ud til at folde
    sig ud BAG indholdet."""
    hub = current == "hub"
    n = lambda base: f"img{p}{base}{suffix}"
    brand = _image(n("NavBrand"), _brand_svg(w, is_open), w, BRAND_H,
                   CLOSE if hub else _launch("hub"),
                   '"BIO SAP - Masterdata Hub"', hover=False)
    if is_open:
        # Kun dobbeltpilen - ingen "Collapse"-tekst (issue #65). Billedet er
        # saa bredt som den lukkede skinne, saa pilen staar det samme sted
        # som ">>", og resten af raekken er ikke et klikfelt.
        toggle = _image(n("NavToggle"), _item_svg(lay.NAV_W, ICON_COLLAPSE, None, False),
                        lay.NAV_W, ITEM_H, CLOSE, '"Collapse menu"',
                        tooltip='"Collapse menu"')
    else:
        toggle = _image(n("NavToggle"), _item_svg(w, ICON_EXPAND, None, False),
                        w, ITEM_H, f"Set({OPEN}, true)", '"Expand menu"',
                        tooltip='"Expand menu"')
    items = []
    for key, label, icon in ITEMS:
        if (key not in SCREENS) if SCREENS is not None else not env.app_id(key):
            continue
        cur = key == current
        items.append(_image(
            n(f"Nav{key[0].upper()}{key[1:]}"),
            _item_svg(w, icon, label if is_open else None, cur), w, ITEM_H,
            CLOSE if cur else _launch(key),
            f'"{label}' + (' (current app)"' if cur else '"'),
            tooltip=None if is_open else f'"{label}"', hover=not cur))
    top = group(f"con{p}NavTop{suffix}", [brand, toggle] + items, gap=2, width=w,
                align_items="Start")

    foot_kids = [group(f"con{p}NavRule{suffix}", [], direction="Horizontal", height=1,
                       width=w - 20, fill=C_DIVIDER)]
    if help_on is not None:
        foot_kids.append(help_toggle(n("Help"), help_on, help_action,
                                     compact=not is_open))
    foot_kids.append(theme_button(n("Theme"), compact=not is_open))
    # Knopperne er THEME_TOGGLE_H brede i den lukkede skinne - venstre
    # polstring saa de staar midt i den. Pillerne i panelet flugter med dem.
    foot = group(f"con{p}NavFoot{suffix}", foot_kids, gap=10, width=w, align_items="Start",
                 pad=(0, 0, 0, (lay.NAV_W - THEME_TOGGLE_H) // 2))

    # Kanten til hoejre er containerens egen ramme, skubbet 1 px ud over
    # skaermens top, venstre og bund, saa kun hoejrekanten ses.
    col = group(f"con{p}Nav{suffix}", [top, foot], gap=12, height="App.Height + 2",
                width=w + 1, fill=C_SURFACE, border_color=C_DIVIDER,
                border_thickness=1, pad=(13, 0, 15, 0), align_items="Start",
                justify="SpaceBetween",
                drop_shadow="Bold" if is_open else "None",
                visible=OPEN if is_open else lay.NAV_ON)
    col.props["X"] = "-1"
    col.props["Y"] = "-1"
    return col


def _mobile_bar(p, current):
    """Topbjaelken paa mobil (issue #65) - kun synlig, naar skinnen ikke er.

    Menuknappen aabner det samme panel som skinnens ">>". Logoet goer det
    samme som i skinnen (til hubben), og appens navn staar til hoejre, saa
    man kan se, hvor man er, uden at aabne menuen."""
    label = dict((k, l) for k, l, _ in ITEMS)[current]
    hub = current == "hub"
    menu = _image(f"img{p}NavMenu", _svg(lay.NAV_W, ITEM_H, _icon(ICON_MENU, _hx("text-primary"))),
                  lay.NAV_W, ITEM_H, f"Set({OPEN}, true)", '"Open menu"',
                  tooltip='"Open menu"')
    brand_w = lay.NAV_W + 80
    brand = _image(f"img{p}NavBrandMobile", _brand_svg(brand_w, True), brand_w, BRAND_H,
                   CLOSE if hub else _launch("hub"), '"BIO SAP - Masterdata Hub"',
                   hover=False)
    title = grow(text_ctrl(f"txt{p}NavTitle", f'"{label}"', size=14, color=C_TITLE,
                           weight="Semibold", height=22, align="Right"))
    bar = group(f"con{p}MobileBar", [menu, brand, title], direction="Horizontal", gap=0,
                height=lay.MOBILE_BAR_H, width="App.Width", align_items="Center",
                fill=C_SURFACE, border_color=C_DIVIDER, border_thickness=1,
                pad=(0, 16, 0, 0), visible=f"!({lay.NAV_ON})")
    # Rammen er skubbet 1 px ud over skaermens top og sider, saa kun
    # bundkanten ses - som skinnens hoejrekant.
    bar.props["X"] = "-1"
    bar.props["Y"] = "-1"
    bar.props["Width"] = "App.Width + 2"
    return bar


def side_nav(prefix, current, help_on=None, help_action=None):
    """Sidebaren. Returnerer (navigation, overlag) - de staar to steder i
    skaermens Children:

        [root, *navigation, sloer og popupper ..., *overlag]

    navigation: den lukkede skinne (NAV_W, Tablet og op) og mobilens
             topbjaelke (under Tablet). Lige efter rammen, saa popupper og
             deres sloer ligger oven paa dem som paa alt andet.
    overlag: et gennemsigtigt sloer (klik = luk) og det aabne panel
             (NAV_W_OPEN, Visible = gblNavOpen). SIDST paa skaermen: i en
             .pa.yaml ligger det, der staar senere, oeverst - saa panelet
             ligger oven paa rammen OG oven paa popupperne.

    current:     noeglen i canvas_apps.json for den app, man staar i.
    help_on:     Power Fx-udtryk, sandt naar hjaelpen vises. Kun apps med
                 hjaelp (VH-plan) giver det - de andre faar ingen kontakt.
    help_action: OnSelect, der vender hjaelpen.
    """
    keys = [k for k, _, _ in ITEMS]
    if current not in keys:
        raise ValueError("side_nav: ukendt app '%s'. Kendte: %s" % (current, ", ".join(keys)))

    p = prefix
    rail = _column(p, "", lay.NAV_W, current, False, help_on, help_action)
    panel = _column(p, "Open", lay.NAV_W_OPEN, current, True, help_on, help_action)

    # Klik uden for det aabne panel lukker det. Gennemsigtigt: HTML-sidens
    # aabne skinne daemper heller ikke indholdet, den har en skygge.
    t = TRANSPARENT
    scrim = Ctrl(f"img{p}NavScrim", "Image", props={
        "AccessibleLabel": '"Close menu"',
        "BorderStyle": "BorderStyle.None",
        "BorderThickness": "0",
        "Fill": t, "HoverFill": t, "PressedFill": t,
        "Height": "App.Height",
        "Image": '""',
        "OnSelect": CLOSE,
        "TabIndex": "-1",
        "Visible": OPEN,
        "Width": "App.Width",
        "X": "0",
        "Y": "0",
    }, h="App.Height", vis=OPEN)
    return [rail, _mobile_bar(p, current)], [scrim, panel]
