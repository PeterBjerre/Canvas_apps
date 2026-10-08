# -*- coding: utf-8 -*-
"""
Sidebaren - den SAMME i alle fem apps.

Forlaegget er HTML-sidens navigationsskinne (html/shell.js buildRail,
html/shell.css .kv-rail): logo oeverst, en ikonliste med de moduler, man
kan gaa til, og en fod med indstillinger. Lukket er den en smal skinne
med ikoner; aabnet viser den teksterne ved siden af.

    lukket (NAV_W)        aabnet (NAV_W_OPEN)
    +------+              +------------------------+
    | [ik] |              | [ik]  BIO SAP          |
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
  * Logoet og ordmaerket "BIO SAP". Logoet er appens ikon (app-icon.png,
    issue #203) i stedet for HTML-sidens "BS"-maerke.
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
from gen_screen import Ctrl, C_SURFACE, C_DIVIDER, C_MUTED_BG, C_PRIMARY, C_TITLE
from design_tokens import ref_hex, theme_query, TRANSPARENT, FLAG_SVG
from build_helpers import group, theme_button, help_toggle, text_ctrl, grow, THEME_TOGGLE_H, page_icon
import layout_tokens as lay
import env_config as env
import icons
import feedback_popup as feedback

ICON_MESSAGE = icons.MESSAGE
# Aaben eller lukket. Blank ved start = lukket. Den gemmes ikke: en
# sidebar, der stod aaben fra sidst, ville ligge oven paa formularen.
OPEN = "gblNavOpen"
CLOSE = f"Set({OPEN}, false)"

ITEM_H = 40
BRAND_H = 44

# (noegle i canvas_apps.json, tekst, ikon). Raekkefoelgen er NAV_ITEMS i
# html/shell.js; teksterne er appsenes egne navne. Ikonerne er de SAMME som
# paa hubbens fliser og i sideoverskrifterne - tools/icons.py (issue #74).
# Teksterne og raekkefoelgen staar i tools/canvas_apps.json (nav_label,
# nav_order) - app-listen er eet sted.
ITEMS = [(k, env.APPS[k]["nav_label"], icons.path(k)) for k in env.NAV_ORDER]

# DEN SAMLEDE APP: {noegle: skaermnavn}. None = de fem enkelte apps, hvor
# et punkt er Launch() af en anden app. Saettes med use_screens().
SCREENS = None
NAV_PRE = {}


def use_screens(screens):
    """Sidebaren navigerer mellem SKAERME i stedet for at starte apps -
    kun den samlede app (BIO SAP App). Hver noegle i ITEMS skal have en
    skaerm; et hul ville ellers blive en Launch() midt i den samlede app."""
    global SCREENS
    missing = [k for k, _l, _i in ITEMS if k not in screens]
    if missing:
        raise SystemExit("side_nav.use_screens: ingen skaerm til %s" % ", ".join(missing))
    SCREENS = dict(screens)

# Systemikonerne staar i tools/icons.py (issue #139) - samme betydning som
# foer: dobbeltpil ud/ind og hamburgermenuen.
ICON_EXPAND = icons.EXPAND
ICON_MENU = icons.MENU
ICON_COLLAPSE = icons.COLLAPSE
# Ikonernes tegnede stoerrelse i sidebaren.
ICON_PX = 18

FONT = "font-family='Segoe UI, sans-serif'"


def _hx(name):
    return "\" & %s & \"" % ref_hex(name)


def _svg(w, h, body):
    return ('"' + f"<svg xmlns='http://www.w3.org/2000/svg' width='{w}' "
            f"height='{h}' viewBox='0 0 {w} {h}'>" + body + "</svg>" + '"')


def _icon(path, color, current=False):
    """Ikonet fra shell.js: viewBox 24, tegnet 18 px stort og centreret i
    den lukkede skinne. Stregen er icons.stroke(18); den valgte side faar
    en kraftigere streg (icons.SELECTED_BOOST) - samme ikon, mere vaegt."""
    s = ICON_PX / 24
    x = (lay.NAV_W - ICON_PX) / 2
    y = (ITEM_H - ICON_PX) / 2
    w = icons.stroke(ICON_PX) + (icons.SELECTED_BOOST if current else 0)
    shape = (icons.hub_paths(_hx) if path == icons.HUB else f"<path d='{path}'/>")
    return (f"<g transform='translate({x:g} {y:g}) scale({s:g})' fill='none' "
            f"stroke='{color}' stroke-width='{w:g}' stroke-linecap='round' "
            f"stroke-linejoin='round'>{shape}</g>")


def _item_svg(w, path, label, current, icon_token=None):
    """Et punkt. current = den app, man staar i: baggrund, accentfarve og
    stregen ude ved kanten, som i shell.css. icon_token: ikonets egen
    farve (domaenefarven); uden den foelger ikonet teksten."""
    fg = _hx("state-info-fg") if current else _hx("text-muted")
    icon_fg = _hx(icon_token) if icon_token else fg
    body = ""
    if current:
        body += (f"<rect x='8' y='0' width='{w - 16}' height='{ITEM_H}' rx='8' "
                 f"fill='{_hx('state-info-bg')}'/>"
                 f"<rect x='0' y='{ITEM_H // 2 - 10}' width='3' height='20' rx='1.5' "
                 f"fill='{icon_fg}'/>")
    body += _icon(path, icon_fg, current)
    if label:
        # The label is a STANDALONE string in the expression, so the language
        # selector (tools/i18n.py) can translate it. Valgt: fed tekst;
        # ellers en tand stillere (issue #139).
        weight = 700 if current else 500
        body += (f"<text x='{lay.NAV_W}' y='{ITEM_H // 2 + 5}' {FONT} "
                 f"font-size='14' font-weight='{weight}' fill='{fg}'>"
                 f'" & "{label}" & "</text>')
    return _svg(w, ITEM_H, body)


# App-logoet (issue #203): appens eget ikon, BIO SAP App/app-icon.png -
# det samme billede, som er app-ikon i app-indstillingerne. Deployet sender
# kun YAML (ingen medier), saa PNG'en staar som data-URI i EEN navngiven
# formel i App.Formulas, laest direkte fra filen ved hvert byg - ingen
# kopi af billedet, og ikke en kopi pr. skaerm. Logoet tegnes som <image>
# i sidebarens SVG, saa ordmaerket og afstandene er de samme som foer.
LOGO = "AppLogo"
LOGO_FILE = ("BIO SAP App", "app-icon.png")
LOGO_PX = 26


def logo_formula():
    """AppLogo til App.Formulas: PNG'en som data-URI (base64)."""
    import base64
    path = os.path.join(env.ROOT, *LOGO_FILE)
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("ascii")
    return ("// APP-LOGO. Genereret af tools/side_nav.py af "
            + "/".join(LOGO_FILE) + " - ret ikke her.\n"
            + f'{LOGO} = "data:image/png;base64,{data}";')


def _brand_svg(w, wordmark):
    m = LOGO_PX
    x = (lay.NAV_W - m) // 2
    y = (BRAND_H - m) // 2
    body = (f"<image x='{x}' y='{y}' width='{m}' height='{m}' "
            f"preserveAspectRatio='xMidYMid meet' href='\" & {LOGO} & \"'/>")
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



# Cirkulaere flag: tegningerne staar i design_tokens.FLAG_SVG.
_FLAGS = FLAG_SVG


def _flag(code, x, y, d):
    """Flaget som en rund badge med fin kant, d px stor, placeret i x, y."""
    cid = "f" + code
    return (f"<svg x='{x}' y='{y}' width='{d}' height='{d}' viewBox='0 0 24 24'>"
            f"<defs><clipPath id='{cid}'><circle cx='12' cy='12' r='11.5'/></clipPath></defs>"
            f"<g clip-path='url(#{cid})'>{_FLAGS[code]}</g>"
            f"<circle cx='12' cy='12' r='11.5' fill='none' stroke='{_hx('border-default')}' "
            f"stroke-opacity='0.9' stroke-width='1'/></svg>")


def _svg_data(w, h, body):
    return (f"<svg xmlns='http://www.w3.org/2000/svg' width='{w}' height='{h}' "
            f"viewBox='0 0 {w} {h}'>{body}</svg>")


def _lang_picker(p, suffix, compact):
    """Static English flag (information only, no action)."""
    H = THEME_TOGGLE_H
    W = H if compact else 148
    if compact:
        body = _flag("en", (W - 24) // 2, (H - 24) // 2, 24)
    else:
        body = (_flag("en", 8, (H - 24) // 2, 24)
                + f"<text x='42' y='{H // 2 + 5}' {FONT} font-size='13' font-weight='600' "
                  f"fill='{_hx('text-primary')}'>English</text>")
    c = _image(f"img{p}NavLang{suffix}", '"' + _svg_data(W, H, body) + '"', W, H,
               "false", '"Language: English"', hover=False)
    c.props["TabIndex"] = "0"
    return c

def _message_button(p, suffix, compact):
    """Message icon above the language flag: opens the feedback popup."""
    H = THEME_TOGGLE_H
    W = H if compact else 148
    ox = (W - 18) / 2 if compact else 12
    oy = (H - 18) / 2
    # En handling, ikke en kontakt: ingen fast pille rundt om (issue #139).
    # Hover og fokus tegner en rund flade (Radius = H/2) - pillerne under
    # den (Help, tema) har pillen som fast form, fordi de viser en tilstand.
    body = icons.glyph(ICON_MESSAGE, _hx('text-primary'), size=ICON_PX, x=ox, y=oy)
    if not compact:
        body += (f"<text x='40' y='{H // 2 + 5}' {FONT} font-size='13' font-weight='600' "
                 f"fill='{_hx('text-primary')}'>" + '" & "Message us" & "</text>')
    img = _image(f"img{p}NavMessage{suffix}", '"' + _svg_data(W, H, body) + '"', W, H,
                 f"{CLOSE}; {feedback.OPEN_FX}", '"Message SAP maintenance"',
                 tooltip='"Message SAP maintenance"')
    for k in ("RadiusTopLeft", "RadiusTopRight", "RadiusBottomLeft", "RadiusBottomRight"):
        img.props[k] = str(H // 2)
    return img


def _launch(key, current=None):
    """NAV_PRE[key] er en formel foer Navigate - eller en funktion af den
    skaerm, man kommer FRA (issue #114: Issue Board vil vide, hvor man var,
    saa det kan foreslaa Application)."""
    if SCREENS is not None:
        pre = NAV_PRE.get(key)
        if callable(pre):
            pre = pre(current)
        return f"{CLOSE}; " + (pre + "; " if pre else "") + f"Navigate({SCREENS[key]}, ScreenTransition.None)"
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
        # Kun dobbeltpilen - ingen "Collapse"-tekst (issue #65). Pilen staar
        # det samme sted som ">>", men HELE raekken er klikfeltet (issue
        # #74): hover, fokus og tryk daekker den fulde bredde, som paa de
        # andre punkter i sidebaren.
        toggle = _image(n("NavToggle"), _item_svg(w, ICON_COLLAPSE, None, False),
                        w, ITEM_H, CLOSE, '"Collapse menu"',
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
        tok = icons.token(key)
        items.append(_image(
            n(f"Nav{key[0].upper()}{key[1:]}"),
            _item_svg(w, icon, label if is_open else None, cur, tok), w, ITEM_H,
            CLOSE if cur else _launch(key, current),
            f'"{label}' + (' (current app)"' if cur else '"'),
            tooltip=None if is_open else f'"{label}"', hover=not cur))
    top = group(f"con{p}NavTop{suffix}", [brand, toggle] + items, gap=2, width=w,
                align_items="Start")

    foot_kids = [group(f"con{p}NavRule{suffix}", [], direction="Horizontal", height=1,
                       width=w - 20, fill=C_DIVIDER)]
    if help_on is not None:
        foot_kids.append(help_toggle(n("Help"), help_on, help_action,
                                     compact=not is_open))
    foot_kids.append(_message_button(p, suffix, not is_open))
    foot_kids.append(_lang_picker(p, suffix, not is_open))
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
    # En app uden punkt i sidebaren (issue #210) staar ikke i ITEMS; dens
    # navn staar stadig i tools/canvas_apps.json, saa bjaelken kan sige,
    # hvor man er.
    label = (dict((k, l) for k, l, _ in ITEMS).get(current)
             or env.APPS[current].get("nav_label") or current)
    menu = _image(f"img{p}NavMenu", _svg(lay.NAV_W, ITEM_H, _icon(ICON_MENU, _hx("text-primary"))),
                  lay.NAV_W, ITEM_H, f"Set({OPEN}, true)", '"Open menu"',
                  tooltip='"Open menu"')
    title = grow(text_ctrl(f"txt{p}NavTitle", f'"{label}"', size=16, color=C_TITLE,
                           weight="Semibold", height=24, wrap="false"))
    pic = page_icon(f"img{p}NavPageIcon", current)
    pic.props["AlignInContainer"] = "AlignInContainer.Center"
    pic.props["LayoutMinWidth"] = str(pic.props["Width"])
    bar = group(f"con{p}MobileBar", [menu, pic, title], direction="Horizontal", gap=6,
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
    # EN APP UDEN PUNKT I SIDEBAREN (issue #210)
    #
    # Measuring Point bygges, foer den faar sit punkt: et punkt mere
    # aendrer sidebaren paa ALLE skaermene, og de delte dele laves om i
    # #204. Appen findes i tools/canvas_apps.json, men staar ikke i
    # nav_order - saa er sidebaren bare umarkeret, mens man er paa den
    # skaerm. Et navn, der slet ikke findes som app, er stadig en fejl:
    # det ville ellers tavst give en sidebar uden markering.
    if current not in keys and current not in env.APPS:
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
        "TabIndex": "0",
        "Visible": OPEN,
        "Width": "App.Width",
        "X": "0",
        "Y": "0",
    }, h="App.Height", vis=OPEN)
    return [rail, _mobile_bar(p, current)], [scrim, panel] + feedback.build(p)
