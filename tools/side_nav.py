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
    |  >>  |              |  <<   Collapse         |
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
    en knap (">>" / "<<  Collapse"), der aabner og lukker.
  * Et klik uden for den aabne sidebar lukker den (et gennemsigtigt
    sloer bag den), saa den ikke skal lukkes med knappen.
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
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import Ctrl, C_SURFACE, C_DIVIDER, C_MUTED_BG, C_PRIMARY
from design_tokens import ref_hex, theme_query, TRANSPARENT
from build_helpers import group, theme_button, help_toggle, THEME_TOGGLE_H
import layout_tokens as lay
import env_config as env

# Aaben eller lukket. Blank ved start = lukket. Den gemmes ikke: en
# sidebar, der stod aaben fra sidst, ville ligge oven paa formularen.
OPEN = "gblNavOpen"
TOGGLE = f"Set({OPEN}, !{OPEN})"
CLOSE = f"Set({OPEN}, false)"

ITEM_H = 40
BRAND_H = 44

# (noegle i canvas_apps.json, tekst, ikon). Raekkefoelgen og ikonerne er
# NAV_ITEMS i html/shell.js; teksterne er appsenes egne navne.
ITEMS = [
    ("hub", "Masterdata Hub",
     "M3 10.5 12 3l9 7.5M5.5 9.5V20h13V9.5"),
    ("functionallocation", "Functional Location",
     "M12 21s7-5.2 7-11a7 7 0 1 0-14 0c0 5.8 7 11 7 11Z "
     "M12 12.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Z"),
    ("vhplan", "VH-plan",
     "M4 6.5h16M4 12h16M4 17.5h10 M17.5 16.5l1.6 1.6 3-3.2"),
    ("material", "Materials",
     "M12 3 21 8v8l-9 5-9-5V8l9-5Z M3 8l9 5 9-5 M12 13v8"),
    ("equipment", "Equipments",
     "M7 7h10v10H7z M4.5 10.5h2.5M4.5 13.5h2.5M17 10.5h2.5M17 13.5h2.5"
     "M10.5 4.5V7M13.5 4.5V7M10.5 17v2.5M13.5 17v2.5"),
]

ICON_EXPAND = "M6 6l6 6-6 6 M12 6l6 6-6 6"
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


def _width():
    return f"If({OPEN}, {lay.NAV_W_OPEN}, {lay.NAV_W})"


def _image(name, img, height, onselect, label, tooltip=None, hover=True):
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
        "Image": img,
        "ImagePosition": "ImagePosition.Fit",
        "OnSelect": onselect,
        "PressedFill": C_MUTED_BG if hover else t,
        "TabIndex": "0",
        "Width": _width(),
    }
    if tooltip:
        props["Tooltip"] = tooltip
    return Ctrl(name, "Image", props=props, h=height)


def _data_uri(open_svg, closed_svg):
    return (f'"data:image/svg+xml;utf8," & EncodeUrl(If({OPEN},\n'
            f'    {open_svg},\n    {closed_svg}\n))')


def _launch(key):
    url = env.play_url(key)
    return f'{CLOSE}; Launch("{url}" & {theme_query("?")}, {{ }}, LaunchTarget.Replace)'


def side_nav(prefix, current, help_on=None, help_action=None):
    """Sidebaren og sloeret bag den - i den raekkefoelge, de skal staa i
    skaermens Children, LIGE EFTER rammen (build_helpers.app_frame):

        [root, *side_nav(...), popupper ...]

    Popupperne og deres sloer staar efter, saa de ligger oven paa
    sidebaren, ligesom de ligger oven paa resten.

    current:     noeglen i canvas_apps.json for den app, man staar i.
    help_on:     Power Fx-udtryk, sandt naar hjaelpen vises. Kun apps med
                 hjaelp (VH-plan) giver det - de andre faar ingen kontakt.
    help_action: OnSelect, der vender hjaelpen.
    """
    p = prefix
    keys = [k for k, _, _ in ITEMS]
    if current not in keys:
        raise ValueError("side_nav: ukendt app '%s'. Kendte: %s" % (current, ", ".join(keys)))

    W_OPEN, W = lay.NAV_W_OPEN, lay.NAV_W
    hub = current == "hub"
    brand = _image(f"img{p}NavBrand",
                   _data_uri(_brand_svg(W_OPEN, True), _brand_svg(W, False)),
                   BRAND_H, CLOSE if hub else _launch("hub"),
                   '"BIO SAP - Masterdata Hub"', hover=False)
    toggle = _image(f"img{p}NavToggle",
                    _data_uri(_item_svg(W_OPEN, ICON_COLLAPSE, "Collapse", False),
                              _item_svg(W, ICON_EXPAND, None, False)),
                    ITEM_H, TOGGLE,
                    f'If({OPEN}, "Collapse menu", "Expand menu")',
                    tooltip=f'If({OPEN}, "", "Expand menu")')
    items = []
    for key, label, icon in ITEMS:
        if not env.app_id(key):
            continue
        cur = key == current
        items.append(_image(
            f"img{p}Nav{key[0].upper()}{key[1:]}",
            _data_uri(_item_svg(W_OPEN, icon, label, cur), _item_svg(W, icon, None, cur)),
            ITEM_H, CLOSE if cur else _launch(key),
            f'"{label}' + (' (current app)"' if cur else '"'),
            tooltip=f'If({OPEN}, "", "{label}")', hover=not cur))
    top = group(f"con{p}NavTop", [brand, toggle] + items, gap=2, width=_width(),
                align_items="Start")

    compact = f"!{OPEN}"
    foot_kids = [group(f"con{p}NavRule", [], direction="Horizontal", height=1,
                       width=f"If({OPEN}, {W_OPEN - 20}, {W - 20})", fill=C_DIVIDER)]
    if help_on is not None:
        foot_kids.append(help_toggle(f"img{p}Help", help_on, help_action, compact=compact))
    foot_kids.append(theme_button(f"img{p}Theme", compact=compact))
    # Knopperne er THEME_TOGGLE_H brede, naar skinnen er lukket - venstre
    # polstring saa de staar midt i den.
    foot = group(f"con{p}NavFoot", foot_kids, gap=10, width=_width(), align_items="Start",
                 pad=(0, 0, 0, (W - THEME_TOGGLE_H) // 2))

    # Kanten til hoejre er containerens egen ramme. Den er skubbet 1 px ud
    # over skaermens top, venstre og bund, saa kun hoejrekanten ses - og
    # den falder paa den sidste pixel foer rammen (X = NAV_W).
    nav = group(f"con{p}Nav", [top, foot], gap=12, height="App.Height + 2",
                width=f"{_width()} + 1", fill=C_SURFACE, border_color=C_DIVIDER,
                border_thickness=1, pad=(13, 0, 15, 0), align_items="Start",
                justify="SpaceBetween")
    nav.props["X"] = "-1"
    nav.props["Y"] = "-1"
    nav.props["DropShadow"] = f"If({OPEN}, DropShadow.Bold, DropShadow.None)"

    # Klik uden for den aabne sidebar lukker den. Gennemsigtigt: HTML-
    # sidens aabne skinne daemper heller ikke indholdet, den har en skygge.
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
    return [scrim, nav]
