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
        toggle = _image(n("NavToggle"), _item_svg(w, ICON_COLLAPSE, "Collapse", False),
                        w, ITEM_H, CLOSE, '"Collapse menu"')
    else:
        toggle = _image(n("NavToggle"), _item_svg(w, ICON_EXPAND, None, False),
                        w, ITEM_H, f"Set({OPEN}, true)", '"Expand menu"',
                        tooltip='"Expand menu"')
    items = []
    for key, label, icon in ITEMS:
        if not env.app_id(key):
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
                visible=OPEN if is_open else None)
    col.props["X"] = "-1"
    col.props["Y"] = "-1"
    return col


def side_nav(prefix, current, help_on=None, help_action=None):
    """Sidebaren. Returnerer (skinne, overlag) - de staar to steder i
    skaermens Children:

        [root, skinne, sloer og popupper ..., *overlag]

    skinne:  den lukkede udgave (NAV_W). Lige efter rammen, saa popupper
             og deres sloer ligger oven paa den som paa alt andet.
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
    return rail, [scrim, panel]
