# -*- coding: utf-8 -*-
"""
Genbrugelige kontrol-byggere. Styling er uaendret fra den oprindelige app
(samme farver, radier, skriftstoerrelser og polstring som powerapp-materialer).

Det eneste der er lavet om, er hoejdemodellen: group() regner selv sin hoejde
ud af boernenes hoejder plus gaps og padding, i stedet for at en formel i
YAML'en refererer andre kontrollers .Height. Se gen_screen.stack_height.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from design_tokens import DARK_VAR, toggle_action, ref_hex as ref_hex_expr, TRANSPARENT
import layout_tokens as lay
from layout_tokens import below, at_least, fits, if_below, TWO_COL_MIN
from gen_screen import (
    Ctrl, render, render_screen, stack_height, row_height,
    C_APP_BG, C_CARD_BG, C_CARD_BORDER, C_TITLE, C_MUTED, C_REQUIRED,
    C_PRIMARY, C_PRIMARY2, C_WHITE, C_TRANSPARENT, C_INPUT_BG, C_DISABLED_BG,
    C_DIVIDER, C_VALID_FG, C_VALID_BG, C_INVALID_FG, C_INVALID_BG,
    C_BORDER_OK, C_BORDER_ERROR, C_PRIMARY_SOFT, C_OVERLAY, C_MODAL_BG,
    C_INFO_FG, C_INFO_BG, C_NEUTRAL_FG, C_NEUTRAL_BG, C_WARN_FG, FONT,
    SHELL_W, EDITOR_W, RAIL_W, SPLIT_GAP, OUT_DIR,
)

def concurrent(*formulas, indent=0):
    """Concurrent() - naar der hentes FLERE UAFHAENGIGE ting paa een gang.

    Uden den venter appen paa SUMMEN af kaldene; med den venter den kun
    paa det laengste. Fem SharePoint-lister i kaede er fem rundture efter
    hinanden.

    NAAR DEN IKKE SKAL BRUGES
    -------------------------
    Concurrent hjaelper KUN formler med et connector- eller
    Dataverse-kald. Set() af en lokal variabel eller ClearCollect af en
    literal tabel bliver ikke hurtigere - de tager mikrosekunder, og at
    pakke dem ind goer kun formlen svaerere at laese.

    OG DEN ER FARLIG VED AFHAENGIGHEDER
    -----------------------------------
    Raekkefoelgen er IKKE givet. To formler inde i den samme Concurrent
    maa ikke afhaenge af hinanden - Power Apps afviser det, naar den kan
    se det, og naar den ikke kan, faar man en kapploebsfejl, der kun
    optraeder nogle gange.

    Det er til gengaeld sikkert at afhaenge af noget FOER den (det er
    faerdigt), og at afhaenge af den bagefter (den venter paa alle).
    """
    if len(formulas) < 2:
        raise ValueError(
            "Concurrent kraever mindst to formler. Med een er der "
            "ingenting at goere parallelt - skriv den bare.")
    pad = " " * (indent + 4)
    body = (",\n").join(pad + f.strip() for f in formulas)
    return "Concurrent(\n%s\n%s)" % (body, " " * indent)


# Alle feltforklaringer ser paa den samme variabel.
HINTS_ON = "IfError(varVhpShowHints, false)"

# Braekpunktet, hvor et to-kolonne-felt stables lodret, staar i
# tools/layout_tokens.py. Det er en CONTAINER-graense og ikke en
# enhedsklasse: et smalt kort stabler sine felter, ogsaa paa en bred
# skaerm.


# En tekstkontrol skal vaere mindst saa hoej som en linje af sin egen
# skrift. Er den ikke det, viser den moderne Text-kontrol sin EGEN
# scrollbar - det var den moerke streg midt i topbjaelken: titlen var 22 pt
# i 30 px. Samme forhold stod paa VH-planens sektionstitler (19 i 26) og
# hubbens tal (26 i 32). 1,5 x skriftstoerrelsen giver luft til Semibold.
TEXT_LINE = 1.5


def text_min_height(size):
    return int(-(-size * TEXT_LINE // 1))


def text_ctrl(name, text, size=14, color=C_TITLE, weight=None, wrap="false",
              align=None, height=20, width=None, fill=C_TRANSPARENT,
              accessible=None, visible=None, layout_min_width=None, extra=None):
    if isinstance(height, (int, float)) and height < text_min_height(size):
        height = text_min_height(size)
    props = {
        "AccessibleLabel": accessible if accessible else text,
        "BorderStyle": "BorderStyle.None",
        "BorderThickness": "0",
        "Color": color,
        "Fill": fill,
        "Font": FONT,
        "Height": str(height),
        "PaddingBottom": "0", "PaddingLeft": "0", "PaddingRight": "0", "PaddingTop": "0",
        "Size": str(size),
        "Text": text,
        "Wrap": wrap,
    }
    if weight:
        props["FontWeight"] = f"FontWeight.{weight}"
    if align:
        props["Align"] = f"Align.{align}"
    if width is not None:
        props["Width"] = str(width)
    if visible is not None:
        props["Visible"] = visible
    if layout_min_width is not None:
        props["LayoutMinWidth"] = str(layout_min_width)
    if extra:
        props.update(extra)
    return Ctrl(name, "ModernText", props=props, h=height, vis=visible)


def group(name, children, direction="Vertical", gap=8, height=None, width="Parent.Width",
          align_items="Stretch", fill=None, border_color=None, border_thickness=None,
          radius=None, pad=None, fill_portions=None, wrap=None, justify=None,
          overflow_y=None, overflow_x=None, visible=None, drop_shadow="None", align_in_container=None,
          layout_min_width=None, wrap_rows=1):
    """height=None betyder: regn hoejden ud af boernene (anbefalet).

    Angiv kun height eksplicit, naar containeren bevidst skal have en fast
    hoejde og selv klippe/scrolle sit indhold.
    """
    if pad is not None:
        if isinstance(pad, tuple):
            pt, pr, pb, pl = pad
        else:
            pt = pr = pb = pl = pad
    else:
        pt = pr = pb = pl = 0

    if height is None:
        if direction == "Vertical":
            height = stack_height(children, gap, pt, pb)
        else:
            height = row_height(children, pt, pb, rows=wrap_rows, gap=gap)

    props = {
        "BorderStyle": "BorderStyle.None" if not border_color else None,
        "BorderColor": border_color,
        "BorderThickness": str(border_thickness) if border_thickness is not None else ("1" if border_color else None),
        "DropShadow": f"DropShadow.{drop_shadow}",
        "LayoutAlignItems": f"LayoutAlignItems.{align_items}",
        "LayoutDirection": f"LayoutDirection.{direction}",
        "LayoutGap": str(gap),
        "LayoutMinWidth": str(layout_min_width) if layout_min_width is not None else "0",
        # Referenceappen (powerapp-materialer) saetter altid FillPortions
        # eksplicit paa GroupContainer/Gallery. 0 = voks ikke.
        "FillPortions": str(fill_portions) if fill_portions is not None else "0",
        "Height": str(height),
    }
    if fill is not None:
        props["Fill"] = fill
    if width is not None:
        props["Width"] = str(width)
    if radius is not None:
        props["RadiusBottomLeft"] = str(radius)
        props["RadiusBottomRight"] = str(radius)
        props["RadiusTopLeft"] = str(radius)
        props["RadiusTopRight"] = str(radius)
    if pad is not None:
        props["PaddingTop"] = str(pt)
        props["PaddingRight"] = str(pr)
        props["PaddingBottom"] = str(pb)
        props["PaddingLeft"] = str(pl)
    if wrap is not None:
        props["LayoutWrap"] = wrap
    if justify is not None:
        props["LayoutJustifyContent"] = f"LayoutJustifyContent.{justify}"
    # OVERLOEB SKJULES, MED MINDRE DET SKAL SCROLLE - skrevet ud, ikke
    # overladt til platformens standard. Et barn, der var bare et par
    # pixels for hoejt, gav en scrollbar midt i topbjaelken.
    props["LayoutOverflowY"] = f"LayoutOverflow.{overflow_y or 'Hide'}"
    props["LayoutOverflowX"] = f"LayoutOverflow.{overflow_x or 'Hide'}"
    if visible is not None:
        props["Visible"] = visible
    if align_in_container is not None:
        props["AlignInContainer"] = f"AlignInContainer.{align_in_container}"
    props = {k: v for k, v in props.items() if v is not None}
    return Ctrl(name, "GroupContainer", variant="AutoLayout", props=props, children=children,
                h=height, vis=visible)


# Ikonerne paa gem- og indsend-knapperne i hele BIO SAP (issue #54). Navnene
# er Fluent-ikonernes; ModernButton.Icon tager dem direkte.
ICON_SAVE = "Save"
ICON_SUBMIT = "Send"
# Ikon + mellemrum foran teksten - laegges til knappens tekstbredde.
ICON_W = 24


def button(name, text, onselect, primary=False, danger=False, width=140, height=36,
           display_mode=None, base_color=None, layout_min_width=None, visible=None,
           accessible=None, icon=None):
    props = {
        "AccessibleLabel": accessible if accessible else text,
        "Align": "Align.Center",
        "AlignInContainer": "AlignInContainer.Center",
        "Font": FONT,
        "FontWeight": "FontWeight.Semibold",
        "Height": str(height),
        "Layout": "ButtonLayout.TextOnly",
        "OnSelect": onselect,
        "RadiusBottomLeft": "10", "RadiusBottomRight": "10",
        "RadiusTopLeft": "10", "RadiusTopRight": "10",
        "Size": "14",
        "Text": text,
        "VerticalAlign": "VerticalAlign.Middle",
        "Width": str(width),
    }
    # OUTLINE, IKKE SECONDARY
    #
    # ButtonAppearance.Secondary er dokumenteret som "subtle FILLED style",
    # og den moderne Button har INGEN Fill-egenskab - fyldet kommer fra
    # Fluent-temaet, som appen ikke saetter. I moerk tilstand blev hver
    # sekundaer knap derfor en LYS pille paa moerk baggrund, med vores egen
    # naesten-hvide C_TITLE ovenpaa. Uleselig, og ingen token kunne rette
    # det, fordi farven ikke kom fra en token.
    #
    # Outline er dokumenteret som "outlined button with NO background
    # fill". Saa er der kun kant og tekst tilbage - og dem saetter vi selv.
    if danger:
        props["Appearance"] = "ButtonAppearance.Outline"
        props["BorderColor"] = C_BORDER_ERROR
        props["BorderThickness"] = "1"
        props["Color"] = C_INVALID_FG
    elif primary:
        props["BasePaletteColor"] = base_color or C_PRIMARY
        props["Color"] = C_WHITE
    else:
        props["Appearance"] = "ButtonAppearance.Outline"
        props["BorderColor"] = C_CARD_BORDER
        props["BorderThickness"] = "1"
        props["Color"] = C_TITLE
    if display_mode:
        props["DisplayMode"] = display_mode
    if layout_min_width is not None:
        props["LayoutMinWidth"] = str(layout_min_width)
    if visible is not None:
        props["Visible"] = visible
    # Ikon foran teksten. icon er et Fluent-ikonnavn ("Save") eller et
    # Power Fx-udtryk, der giver et.
    if icon:
        props["Icon"] = icon if icon.startswith(("If(", '"')) else f'"{icon}"'
        props["Layout"] = "ButtonLayout.IconBefore"
    return Ctrl(name, "ModernButton", props=props, h=height, vis=visible)


def mark_done(btn, done_expr):
    """Den FAELLES "udfyldt"-tilstand for en outline-knap (issue #73).

    Item Long Text og Object List bruger den begge: naar der er noget,
    faar knappen en groen kant og groen tekst. Kanten bliver 1 px bred i
    alle tilstande, saa knappen aldrig skifter stoerrelse - kun farven
    siger det. ModernButton har intet Fill, saa en tonet baggrund kan den
    ikke faa; kant og tekst er den tilgaengelige udgave.

    Tilstanden forsvinder i samme oejeblik, done_expr bliver falsk - der
    er ingen variabel, der kan glemme at blive nulstillet."""
    btn.props["BorderColor"] = f"If({done_expr}, {C_BORDER_OK}, {C_CARD_BORDER})"
    btn.props["BorderThickness"] = "1"
    btn.props["Color"] = f"If({done_expr}, {C_VALID_FG}, {C_TITLE})"
    return btn


TOGGLE_W = 96
TOGGLE_H = 32


def bool_toggle(name, default, display_mode=None, tooltip=None, true_text='"Yes"',
                false_text='"No"', on_change=None):
    """Kompakt ja/nej-kontakt - DEN ene stil for booleske felter (issue #73).

    Classic/Toggle, fordi den tegner sin skinne, sit greb og sine
    hover-flader med de farver, den faar (tokens) - og fordi den er
    bevist i dette miljoe. Grebet glider selv mellem slukket og taendt.

    Lille og tydelig: 96 x 32, teksten "Yes"/"No" ved siden af skinnen,
    ingen tom plads. Ingen AccessibleLabel - compile afviste den paa de
    klassiske kontroller (issue #57); Tooltip siger, hvad den er."""
    props = {
        "BorderColor": C_TRANSPARENT,
        "Color": C_TITLE,
        "Default": default,
        "DisabledBorderColor": C_TRANSPARENT,
        "FalseFill": C_NEUTRAL_BG,
        "FalseHoverFill": C_DIVIDER,
        "FalseText": false_text,
        "FocusedBorderColor": C_PRIMARY,
        "FocusedBorderThickness": "2",
        "Font": FONT,
        "HandleFill": C_WHITE,
        "Height": str(TOGGLE_H),
        "HoverBorderColor": C_TRANSPARENT,
        "PressedBorderColor": C_PRIMARY,
        "ShowLabel": "true",
        "Size": "13",
        "TrueFill": C_PRIMARY,
        "TrueHoverFill": C_PRIMARY2,
        "TrueText": true_text,
        "Width": str(TOGGLE_W),
    }
    if display_mode:
        props["DisplayMode"] = display_mode
    if tooltip:
        props["Tooltip"] = tooltip
    if on_change:
        props["OnChange"] = on_change
    t = Ctrl(name, "Classic/Toggle", props=props, h=TOGGLE_H)
    t.props["AlignInContainer"] = "AlignInContainer.Start"
    return t


def spinner_svg(size=64, stroke=6, delay=0.15):
    """Hjulet - EEN tegning for hele repoet (issue #64).

    Et drejende SVG-hjul i temaets farver: et spor i state-neutral-bg og en
    bue i brandfarven. Udtrykket er en Power Fx-streng, der giver en
    data-URI - klar til et Images Image-egenskab.

    delay: hjulet toner ind efter saa mange sekunder. En hentning, der er
    faerdig hurtigere, viser derfor ikke et hjul, der blinker forbi - kun
    sloeret, som alligevel skal spaerre skaermen."""
    hx = lambda n: '" & %s & "' % ref_hex_expr(n)
    c = size // 2
    r = c - stroke - 4
    svg = ('"' + f"<svg xmlns='http://www.w3.org/2000/svg' width='{size}' height='{size}' "
           f"viewBox='0 0 {size} {size}'>"
           f"<g opacity='0'>"
           f"<animate attributeName='opacity' from='0' to='1' begin='{delay}s' "
           f"dur='0.2s' fill='freeze'/>"
           f"<circle cx='{c}' cy='{c}' r='{r}' fill='none' stroke-width='{stroke}' "
           f"stroke='{hx('state-neutral-bg')}'/>"
           f"<path d='M{c} {c - r} a{r} {r} 0 0 1 {r} {r}' fill='none' "
           f"stroke-width='{stroke}' stroke-linecap='round' "
           f"stroke='{hx('color-brand-primary')}'>"
           f"<animateTransform attributeName='transform' type='rotate' "
           f"from='0 {c} {c}' to='360 {c} {c}' dur='0.9s' repeatCount='indefinite'/>"
           f"</path></g>"
           "</svg>" + '"')
    return f'"data:image/svg+xml;utf8," & EncodeUrl({svg})'


def loading_overlay(name, busy_var, label="Saving, please wait"):
    """DEN ventespinner - ens i alle apps og alle skaerme (issue #54, #64).

    Et drejende hjul (spinner_svg) midt paa skaermen, oven paa alt, i
    sloerets farve - saa ingen naar at trykke paa noget, mens der hentes
    eller gemmes. Synlig, saa laenge busy_var er sand.

    Bruges til BAADE gemning (appernes Save/Submit) og indlaesning (den
    samlede apps skaerme). Der var to kopier af den samme SVG - een her og
    een i BIO SAP App/build/build_screens.py - og skaermene fik oveni Power
    Apps' egen LoadingSpinner, saa der stod et hjul inden i hjulet. Nu er
    der een.

    Staar SIDST i skaermens boern: det, der staar senere, ligger oeverst."""
    vis = f"IfError({busy_var}, false)"
    return Ctrl(name, "Image", props={
        "AccessibleLabel": f'"{label}"',
        "BorderStyle": "BorderStyle.None",
        "BorderThickness": "0",
        "Fill": C_OVERLAY,
        "Height": "App.Height",
        "Image": spinner_svg(),
        "ImagePosition": "ImagePosition.Center",
        "TabIndex": "-1",
        "Visible": vis,
        "Width": "App.Width",
        "X": "0",
        "Y": "0",
    }, h="App.Height", vis=vis)


def with_busy(busy_var, fx):
    """fx med ventespinneren taendt, mens den koerer."""
    return f"Set({busy_var}, true);\n{fx};\nSet({busy_var}, false)"


def confirm_modal(prefix, open_var, title, message, confirm_text, confirm_fx,
                  confirm_name, icon=ICON_SUBMIT):
    """Bekraeftelsen foer Submit (issue #54) - [sloer, popup].

    Samme konstruktion som appernes andre popupper: en centreret container
    med sloer bag, titel, en linje tekst og to knapper. Submit-knappen
    aabner den (Set(open_var, true)); foerst "Submit" HER koerer
    indsendelsen. Cancel lukker uden at goere noget."""
    vis = f"IfError({open_var}, false)"
    backdrop = Ctrl(f"con{prefix}ConfirmBackdrop", "GroupContainer", variant="AutoLayout", props={
        "BorderStyle": "BorderStyle.None",
        "DropShadow": "DropShadow.None",
        "Fill": C_OVERLAY,
        "Height": "App.Height",
        "LayoutDirection": "LayoutDirection.Vertical",
        "Visible": vis,
        "Width": "App.Width",
        "X": "0",
        "Y": "0",
    }, children=[], vis=vis)
    t = text_ctrl(f"txt{prefix}ConfirmTitle", f'"{title}"', size=17, weight="Semibold",
                  height=26, wrap="false")
    msg = text_ctrl(f"txt{prefix}ConfirmText", message, size=13, color=C_MUTED,
                    height=40, wrap="true")
    cancel = button(f"btn{prefix}ConfirmCancel", '"Cancel"', f"Set({open_var}, false)",
                    width=fit_button_width('"Cancel"'), height=36)
    ok = button(confirm_name, f'"{confirm_text}"',
                f"Set({open_var}, false);\n{confirm_fx}", primary=True,
                width=fit_button_width(f'"{confirm_text}"') + ICON_W, height=36, icon=icon)
    footer = group(f"con{prefix}ConfirmFooter", [cancel, ok], direction="Horizontal", gap=8,
                   height=36, justify="End", align_items="Center")
    modal = group(f"con{prefix}ConfirmModal", [t, msg, footer], direction="Vertical", gap=12,
                  fill=C_MODAL_BG, border_color=C_PRIMARY_SOFT, radius=16,
                  pad=(18, 18, 18, 18), width="Min(460, App.Width - 40)",
                  drop_shadow="ExtraBold", visible=vis)
    modal.props["X"] = "(App.Width - Self.Width) / 2"
    modal.props["Y"] = "Max(20, (App.Height - Self.Height) / 3)"
    return [backdrop, modal]


# Temaskiftets maal. Eksporteret, saa en app, der regner sin bjaelke selv
# (VH-plan, build_hero.BW), laeser det samme tal som kontrollen har.
THEME_TOGGLE_W = 104
THEME_TOGGLE_H = 36


def _theme_svg(dark, compact=False):
    """Pillen som SVG - LIGHT/DARK og en rund knop med sol eller maane,
    som referencebilledet i issue #37.

    compact: kun knoppen i en rund ramme, uden tekst - til den lukkede
    sidebar (tools/side_nav.py), hvor pillen ikke kan staa.

    Farverne er tokens (C.'hex-...'), sat ind med &. SVG'en bruger kun
    enkelte anfoerselstegn, saa den kan staa i en Power Fx-streng."""
    import math
    hx = lambda n: "\" & %s & \"" % ref_hex_expr(n)
    H, R = THEME_TOGGLE_H, THEME_TOGGLE_H // 2
    W = H if compact else THEME_TOGGLE_W
    kx = R if (dark or compact) else W - R
    parts = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{W}' height='{H}' "
        f"viewBox='0 0 {W} {H}'>",
        f"<rect x='1' y='1' width='{W - 2}' height='{H - 2}' rx='{R - 1}' "
        f"fill='{hx('state-neutral-bg')}' stroke='{hx('border-default')}'/>",
        f"<circle cx='{kx}' cy='{R}' r='{R - 4}' "
        f"fill='{hx('text-primary') if dark else hx('bg-surface')}'/>",
    ]
    if dark:
        # Maane: en fuld cirkel minus en forskudt - tegnet som een sti.
        parts.append(
            f"<path d='M{kx + 3} {R - 7} A7 7 0 1 0 {kx + 7} {R + 3} "
            f"A5.5 5.5 0 1 1 {kx + 3} {R - 7} Z' fill='{hx('bg-app')}'/>")
        tx, anchor, label = W - 14, "end", "DARK"
    else:
        sun = hx('state-warn-fg')
        parts.append(f"<circle cx='{kx}' cy='{R}' r='4' fill='none' "
                     f"stroke='{sun}' stroke-width='1.8'/>")
        for i in range(8):
            a = i * math.pi / 4
            x1, y1 = kx + 6.5 * math.cos(a), R + 6.5 * math.sin(a)
            x2, y2 = kx + 9 * math.cos(a), R + 9 * math.sin(a)
            parts.append(f"<line x1='{x1:.1f}' y1='{y1:.1f}' x2='{x2:.1f}' "
                         f"y2='{y2:.1f}' stroke='{sun}' stroke-width='1.8' "
                         f"stroke-linecap='round'/>")
        tx, anchor, label = 14, "start", "LIGHT"
    if not compact:
        parts.append(f"<text x='{tx}' y='{R + 4}' text-anchor='{anchor}' "
                     f"font-family='Segoe UI, sans-serif' font-size='12' "
                     f"font-weight='700' letter-spacing='0.5' "
                     f"fill='{hx('text-primary')}'>"
                     f"{label}</text>")
    parts.append("</svg>")
    return '"' + "".join(parts) + '"'


def theme_button(name="imgThemeToggle", compact=False):
    """Skiftet mellem lyst og moerkt tema - ET billede, man trykker paa.

        ( LIGHT  (sol) )     lyst tema
        ( (maane)  DARK )    moerkt tema

    SAMME KONTROL I ALLE APPS. Det er hele pointen.

    HVORFOR ET SVG-BILLEDE (issue #37)
    ----------------------------------
    Tredje forsoeg. De to foerste byggede pillen af containere og moderne
    knapper, og begge gange bestemte Fluent-temaet noget, vi ikke kunne
    styre: foerst blev knoppen en moerk klat (BasePaletteColor giver en
    PALET, ikke en farve), saa blev den en hvid klat uden ikon, og et tryk
    naaede ikke knappen. En moderne knap har ingen Fill.

    En Image-kontrol med en SVG tegner PRAECIS det, der staar - pille,
    knop, ikon og tekst - og har OnSelect og TabIndex, saa den kan bruges
    med mus og tastatur. Det er den samme form, appsene i BIOSAP-
    solutionen bruger til deres logo (Image@2.2.3 med EncodeUrl af en
    SVG), altsaa bevist i dette miljoe. Farverne er tokens, saa den
    skifter med temaet som alt andet.

    HVORFOR IKKE EN PCF-KOMPONENT
    -----------------------------
    Den ville kraeve sin egen solution-import og at kodekomponenter er
    slaaet til i miljoeet - og deploy-vejen (canvas_mcp) synker kun
    .pa.yaml. Et billede kan det samme her uden noget af det.

    Handlingen staar i tools/design_tokens.py - baade Set() og SaveData,
    saa valget ogsaa er der i morgen.

    compact: True = kun knoppen (THEME_TOGGLE_H i kvadrat) - den lukkede
    sidebar i tools/side_nav.py. Bredden er et fast tal, ikke en formel."""
    img = (f'"data:image/svg+xml;utf8," & EncodeUrl(If({DARK_VAR},\n'
           f'    {_theme_svg(True)},\n    {_theme_svg(False)}\n))')
    width = str(THEME_TOGGLE_W)
    if compact:
        img = (f'"data:image/svg+xml;utf8," & EncodeUrl(If({DARK_VAR},\n'
               f'    {_theme_svg(True, True)},\n    {_theme_svg(False, True)}\n))')
        width = str(THEME_TOGGLE_H)
    t = TRANSPARENT
    props = {
        "AccessibleLabel": (f'If({DARK_VAR}, "Dark theme is on - switch to light theme", '
                            f'"Light theme is on - switch to dark theme")'),
        "BorderStyle": "BorderStyle.None",
        "BorderThickness": "0",
        "FocusedBorderThickness": "2",
        "FocusedBorderColor": C_PRIMARY,
        "Height": str(THEME_TOGGLE_H),
        "HoverFill": t, "PressedFill": t, "Fill": t,
        "Image": img,
        "ImagePosition": "ImagePosition.Fit",
        "OnSelect": toggle_action(),
        "TabIndex": "0",
        "Width": width,
    }
    return Ctrl(name, "Image", props=props, h=THEME_TOGGLE_H)


def _help_svg(on, compact=False):
    """Hjaelpe-pillen - samme form som temapillen (_theme_svg).

        ( (?)  HELP )     slukket: graa knop til venstre
        ( HELP  (?) )     taendt: blaa knop til hoejre, blaa pille

    Knoppen skifter side OG farve, saa tilstanden kan ses uden at laese
    teksten - som en almindelig kontakt.

    compact: kun knoppen i en rund ramme (den lukkede sidebar). Farven
    viser stadig tilstanden."""
    hx = lambda n: "\" & %s & \"" % ref_hex_expr(n)
    H, R = THEME_TOGGLE_H, THEME_TOGGLE_H // 2
    W = H if compact else THEME_TOGGLE_W
    kx = W - R if on else R
    pill = hx('state-info-bg') if on else hx('state-neutral-bg')
    edge = hx('state-info-fg') if on else hx('border-default')
    knob = hx('state-info-fg') if on else hx('bg-surface')
    glyph = hx('bg-surface') if on else hx('state-info-fg')
    tx, anchor = (14, "start") if on else (W - 14, "end")
    return ('"' +
            f"<svg xmlns='http://www.w3.org/2000/svg' width='{W}' height='{H}' "
            f"viewBox='0 0 {W} {H}'>"
            f"<rect x='1' y='1' width='{W - 2}' height='{H - 2}' rx='{R - 1}' "
            f"fill='{pill}' stroke='{edge}'/>"
            f"<circle cx='{kx}' cy='{R}' r='{R - 4}' fill='{knob}'/>"
            f"<text x='{kx}' y='{R + 5}' text-anchor='middle' "
            f"font-family='Segoe UI, sans-serif' font-size='15' font-weight='700' "
            f"fill='{glyph}'>?</text>"
            + ("" if compact else
               f"<text x='{tx}' y='{R + 4}' text-anchor='{anchor}' "
               f"font-family='Segoe UI, sans-serif' font-size='12' "
               f"font-weight='700' letter-spacing='0.5' "
               f"fill='{hx('text-primary')}'>HELP</text>")
            + "</svg>" + '"')


def help_toggle(name, on, action, compact=False):
    """Hjaelp til/fra - samme slags kontakt som temaknappen (theme_button).

    on:      Power Fx-udtryk, der er sandt, naar hjaelpen vises.
    action:  OnSelect, der vender den.
    compact: True = kun knoppen (den lukkede sidebar).

    Et Image med en SVG af de grunde, theme_button beskriver: en moderne
    knap tegner Fluent-temaets form, ikke vores."""
    img = (f'"data:image/svg+xml;utf8," & EncodeUrl(If({on},\n'
           f'    {_help_svg(True)},\n    {_help_svg(False)}\n))')
    width = str(THEME_TOGGLE_W)
    if compact:
        img = (f'"data:image/svg+xml;utf8," & EncodeUrl(If({on},\n'
               f'    {_help_svg(True, True)},\n    {_help_svg(False, True)}\n))')
        width = str(THEME_TOGGLE_H)
    t = TRANSPARENT
    props = {
        "AccessibleLabel": (f'If({on}, "Help is shown - hide help", '
                            f'"Help is hidden - show help")'),
        "BorderStyle": "BorderStyle.None",
        "BorderThickness": "0",
        "FocusedBorderThickness": "2",
        "FocusedBorderColor": C_PRIMARY,
        "Height": str(THEME_TOGGLE_H),
        "HoverFill": t, "PressedFill": t, "Fill": t,
        "Image": img,
        "ImagePosition": "ImagePosition.Fit",
        "OnSelect": action,
        "TabIndex": "0",
        "Width": width,
    }
    return Ctrl(name, "Image", props=props, h=THEME_TOGGLE_H)


def _fits_expr(container_w, needs):
    """Sand, naar 'needs' px kan staa paa EEN linje i container_w.

    container_w er altid regnet af SHELL_W, som er en NEDRE graense for
    den bredde, platformen giver (se RAMMEN i layout_tokens.py). Er den
    sand her, er der ogsaa plads i virkeligheden."""
    return "(%s) >= %s" % (container_w, needs)


def _sum_expr(terms, gap):
    terms = ["(%s)" % t for t in terms]
    expr = " + ".join(terms)
    if gap and len(terms) > 1:
        expr += " + %d" % (gap * (len(terms) - 1))
    return expr


def _max_expr(hs):
    if all(isinstance(h, (int, float)) for h in hs):
        return str(max(hs))
    return hs[0] if len(hs) == 1 else "Max(%s)" % ", ".join("(%s)" % h for h in hs)


def grow(ctrl, min_w=0):
    """Barnet tager RESTEN af en vandret raekke.

    Det er en MARKERING, ikke FillPortions. gen_screen.resolve_templates()
    regner bredden ud, naar skaermen skrives: pladsen inden i raekken minus
    de andre boern. Se _resolve_grow for hvorfor - kort sagt stod knapperne
    ved siden af en FillPortions-del en linje for lavt i Studio.

    Her stod foer "Parent.Width - <de andre>", og Parent.Width er
    FORAELDERENS WIDTH-EGENSKAB, ikke pladsen inden i den."""
    ctrl._grow = min_w
    ctrl.props["Width"] = str(min_w)
    ctrl.props["LayoutMinWidth"] = str(min_w)
    return ctrl


def flow_row(name, children, container_w, gap=8, flex=None, flex_min=0,
             **group_kw):
    """En raekke, der ENTEN staar vandret paa een linje ELLER lodret med
    eet barn pr. linje. Aldrig noget midt imellem - og ALDRIG LayoutWrap.

    HVORFOR IKKE LayoutWrap
    -----------------------
    Med wrap bestemmer platformen, hvor mange linjer det bliver, ud fra
    den bredde, containeren FAKTISK har. Hoejden er regnet her i Python.
    Er de to bare een pixel uenige, havner det sidste barn paa en linje,
    hoejden ikke har plads til - og det er klippet vaek. Det var de
    forsvundne knapper, to gange.

    HER SKIFTER RETNINGEN, IKKE LINJEANTALLET
    -----------------------------------------
      passer   ->  LayoutDirection.Horizontal. Hoejde = det hoejeste barn.
      passer   ->  LayoutDirection.Vertical med Stretch: hvert barn sin
      ikke         egen linje i fuld bredde. Hoejde = summen.

    Konstruktionen er den, den haandbyggede Materials-app brugte paa sine
    raekker, og dermed bevist i dette miljoe.

    DEN FLEKSIBLE DEL REGNES AF PLATFORMEN
    --------------------------------------
    flex = det barn, der tager resten af linjen (typisk titlen). Det faar
    FillPortions = 1 - saa er det Power Apps, der regner resten ud, af den
    bredde der faktisk er. Her stod "Parent.Width - 545", og Parent.Width er
    FORAELDERENS WIDTH-EGENSKAB, ikke pladsen inden i den: headerens 58 px
    padding var ikke trukket fra, raekken var 57 px for bred, og knapperne
    ombroed ned under bjaelkens kant.

    Graensen (passer/passer ikke) regnes af boernenes egne bredder mod
    container_w, som altid er regnet af SHELL_W - en NEDRE graense for den
    bredde, der er. Tilfoejes en knap, flytter graensen sig selv.
    """
    ok = flow_ok(children, container_w, gap, flex, flex_min)
    for c in children:
        if c is flex:
            grow(c, 0)
        else:
            # Laast i raekken, saa den fleksible del er den eneste, der kan
            # give efter. Lodret er Stretch - saa maa den gerne vaere smal.
            c.props["LayoutMinWidth"] = "If(%s, %s, 0)" % (ok, c.props["Width"])

    hs = [0 if c.h is None else c.h for c in children]
    one = _max_expr(hs)
    parts = []
    for i, c in enumerate(children):
        g = 0 if i == 0 else gap
        if c.vis:
            parts.append("If(%s, %d + (%s), 0)" % (c.vis, g, hs[i]))
        else:
            parts.append("%d + (%s)" % (g, hs[i]) if g else "(%s)" % hs[i])
    stacked = " + ".join(parts)
    row = group(name, children, direction="Horizontal", gap=gap,
                height="If(%s, %s, %s)" % (ok, one, stacked), **group_kw)
    row.props["LayoutDirection"] = ("If(%s, LayoutDirection.Horizontal, "
                                    "LayoutDirection.Vertical)" % ok)
    row.props["LayoutAlignItems"] = ("If(%s, LayoutAlignItems.Center, "
                                     "LayoutAlignItems.Stretch)" % ok)
    return row


def flow_ok(children, container_w, gap=8, flex=None, flex_min=0):
    """Graensen for en flow_row: kan boernene staa paa een linje?

    Skal kaldes FOER flow_row, hvis et barn selv er en flow_row og skal
    kende sin container (top_bar). flow_row bruger den samme funktion, saa
    de to ikke kan regne forskelligt.

    Uanset synlighed: et skjult barn taelles med. Det kan kun faa raekken
    til at stable lidt for tidligt - aldrig for sent."""
    terms = [str(c.props["Width"]) for c in children if c is not flex]
    if flex is not None:
        terms.append(str(flex_min))
    return _fits_expr(container_w, _sum_expr(terms, gap))


PAGE_ICON = 32


def page_icon(name, key, size=PAGE_ICON):
    """Domaenets ikon til sideoverskriften (issue #74) - det SAMME ikon som i
    sidebaren og paa hubbens flise (tools/icons.py), i domaenets farve, i
    en svagt tonet firkant. Pynt: ingen tab stop, tom etiket."""
    import icons
    color = '" & %s & "' % ref_hex_expr(icons.token(key))
    inner = icons.stroke_svg(key, color, size=20)
    pad = (size - 20) / 2
    svg = ("<svg xmlns='http://www.w3.org/2000/svg' width='%d' height='%d' "
           "viewBox='0 0 %d %d'><rect width='%d' height='%d' rx='8' fill='%s' "
           "fill-opacity='0.12'/><g transform='translate(%g %g)'>%s</g></svg>"
           % (size, size, size, size, size, size, color, pad, pad, inner))
    return Ctrl(name, "Image", props={
        "AccessibleLabel": '""',
        "BorderStyle": "BorderStyle.None",
        "BorderThickness": "0",
        "Height": str(size),
        "Image": f'"data:image/svg+xml;utf8," & EncodeUrl("{svg}")',
        "ImagePosition": "ImagePosition.Fit",
        "OnSelect": "false",
        "TabIndex": "-1",
        "Width": str(size),
    }, h=size)


def top_bar(prefix, title, subtitle, actions, container_w=None, gap=10,
            narrow_hide=(), sub=None, icon=None):
    """Bjaelken oeverst - den SAMME konstruktion i alle fire apps.

    EEN vandret raekke uden formler i retning eller justering: titlen og
    undertitlen tager resten (build_helpers.grow -> en udregnet bredde), og
    knapperne staar DIREKTE i raekken - ikke i en indlejret gruppe.

    Foerste udgave havde knapperne i en indlejret gruppe ved siden af en
    FillPortions-titel, og en retning, der skiftede efter bredden. I Studio
    stod knapperne en linje for lavt og blev skaaret over af headerens kant.
    Listens raekker - faste, udregnede bredder, ingen indlejring - stod
    rigtigt. Det er den konstruktion, bjaelken nu har.

    narrow_hide: knapper, der skjules under "Tablet", saa resten kan staa.
    sub: kontroller, der staar under titlen I STEDET for undertitlen
         (VH-planens procestrin). Deres hoejde goer bjaelken hoejere.
    """
    t = text_ctrl("txt%sTitle" % prefix, title, size=22, weight="Semibold",
                  height=30, wrap="false")
    if sub is None:
        sub = [text_ctrl("txt%sSub" % prefix, subtitle, size=13, color=C_MUTED,
                         height=20, wrap="false")]
    left = grow(group("con%sBarLeft" % prefix, [t] + list(sub), direction="Vertical", gap=2))
    lead = []
    if icon:
        # icon: noeglen i tools/icons.DOMAIN - appens eget domaeneikon.
        ic = page_icon("img%sTitleIcon" % prefix, icon)
        ic.props["AlignInContainer"] = "AlignInContainer.Center"
        ic.props["LayoutMinWidth"] = str(PAGE_ICON)
        lead = [ic]
    for a in actions:
        a.props["AlignInContainer"] = "AlignInContainer.Center"
        a.props["LayoutMinWidth"] = str(a.props["Width"])
        if a.name in narrow_hide:
            a.vis = at_least("Tablet")
    return group("con%sBar" % prefix, lead + [left] + list(actions), direction="Horizontal",
                 gap=gap, align_items="Center")


def app_frame(prefix, header, body, body_gap=16, body_pad_b=None):
    """Rammen om hele skaermen - den SAMME i alle fire apps.

        con<X>Root     lodret, hele skaermen, scroller IKKE
          con<X>Header   fast hoejde. Bjaelken staar her og kan ikke
                         scrolle vaek, klippes af et andet kort, eller
                         faa sin hoejde fra noget, der kan fejle.
          con<X>Body     FillPortions = 1, LayoutOverflowY = Scroll.
                         Kortene staar direkte i den.

    HVAD DER VAR GALT
    -----------------
    Foer stod alt i een skal, hvis Height var SUMMEN af hvert korts
    udregnede hoejde - hundredvis af tegn med CountRows, Filter mod
    SharePoint og IfError. Een forkert term et sted, og skallen blev for
    lav: det nederste - indsend-knapperne - blev klippet vaek. Fejlede
    formlen, blev hele skallen, bjaelken med, til ingenting.

    Nu er der ingen sum. En scrollende container skal ikke vaere hoej nok
    til sit indhold; den SCROLLER. Hvert kort regner stadig sin egen hoejde
    ud, men en fejl dér rammer kun det kort. Det er Microsofts eget
    moenster: header med fast hoejde, krop med Fill portions og
    Vertical overflow = Scroll.

    Bredderne er sat, saa SHELL_W er sand begge steder - se RAMMEN i
    tools/layout_tokens.py."""
    hdr_kids = [header, group("con%sHeaderRule" % prefix, [], direction="Horizontal",
                              height=1, fill=C_DIVIDER)]
    head = group("con%sHeader" % prefix, hdr_kids, direction="Vertical",
                 gap=lay.HEADER_PAD_B,
                 pad=(lay.HEADER_PAD_T, lay.PAGE_PAD_R + lay.SCROLLBAR_W, 0, lay.PAGE_PAD_L),
                 fill=C_APP_BG)
    pb = lay.BODY_PAD_B if body_pad_b is None else body_pad_b
    main = group("con%sBody" % prefix, body, direction="Vertical", gap=body_gap,
                 height="Parent.Height - (%s)" % head.h, fill_portions=1,
                 overflow_y="Scroll", fill=C_APP_BG,
                 pad=(lay.BODY_PAD_T, lay.PAGE_PAD_R, pb, lay.PAGE_PAD_L))
    # Sidebaren (tools/side_nav.py) staar til venstre. Rammen starter
    # efter dens LUKKEDE bredde; aabnet ligger den oven paa rammen. Paa
    # mobil er skinnen skjult, og rammen starter under topbjaelken i stedet
    # (issue #65) - udtrykkene staar i tools/layout_tokens.py.
    root = group("con%sRoot" % prefix, [head, main], direction="Vertical", gap=0,
                 height=lay.ROOT_H, width=lay.ROOT_W, fill=C_APP_BG)
    root.props["X"] = lay.ROOT_X
    root.props["Y"] = lay.ROOT_Y
    return root


def button_row(name, buttons, container_w, gap=8, height=36, align_items="Center"):
    """Knapraekke der ALDRIG ombryder.

    Den oprindelige raekke havde faste knapbredder (104 + 104 + 112 + gaps =
    336 px) i et kort med 324 px indhold. Den ombroed derfor til to linjer,
    mens raekkens hoejde stod fast paa 36 - og den sidste knap blev klippet.
    Her deler knapperne bredden ligeligt, saa de altid passer.
    """
    n = len(buttons)
    w = f"({container_w} - {gap * (n - 1)}) / {n}"
    for b in buttons:
        b.props["Width"] = w
        b.props["LayoutMinWidth"] = "0"
    return group(name, buttons, direction="Horizontal", gap=gap, height=height,
                 align_items=align_items)


def fit_button_row(name, buttons, container_w, gap=8):
    """Knapraekke, hvor hver knap er saa bred som sin tekst.

    button_row() deler hele bredden ligeligt, og paa en bred skaerm blev
    "Save" 300 px bred med fire bogstaver i. Her faar hver knap den bredde,
    dens tekst skal bruge, og de staar til venstre.

    Passer de ikke paa een linje, staar de under hinanden - det er
    flow_row(), og derfor ombryder raekken aldrig halvt."""
    for b in buttons:
        b.props["Width"] = str(fit_button_width(b.props["Text"]))
    return flow_row(name, buttons, container_w, gap=gap)


def border_rule(empty_test, required_formula="false"):
    """DEN ENE REGEL om, hvad en feltkant siger.

    Foer var der FIRE, og de sad i samme formular ved siden af hinanden:

      text_input uden required   ingen BorderColor overhovedet - altsaa
                                 platformens standard, som ingen havde valgt
      text_input med required    roed / graa / GROEN
      number_input, dropdown     roed / graa / GROEN, OGSAA naar feltet
                                 ikke var kraevet
      ModernDatePicker           fast graa. Aldrig roed, aldrig groen -
                                 og bygget i haanden uden for den her fil

    I Equipments formular stod fire felter side om side, hvor et tekstfelt
    aldrig skiftede farve, et talfelt blev groent naar man skrev i det, og
    en datovaelger var graa uanset hvad.

    HVORFOR KUN DE KRAEVEDE FELTER FAAR FARVE
    -----------------------------------------
    Argumentet stod allerede i text_input og var rigtigt: en groen kant om
    hvert eneste udfyldt felt goer farven meningsloes. Groen skal betyde
    "det her krav er opfyldt", ikke "du har tastet noget".

    Derfor ensrettes der PAA text_inputs regel - ikke paa de to andres.
    Et felt, der ikke er kraevet, faar en almindelig kant, og den saettes
    EKSPLICIT: gjorde den ikke det, arvede feltet platformens standard,
    som ingen i projektet har valgt.

        ikke kraevet        ->  border-default
        kraevet + tom       ->  state-error-fg
        kraevet + udfyldt   ->  state-ok-fg
    """
    if required_formula == "false":
        return C_CARD_BORDER
    return (f"If(\n"
            f"    {required_formula} && {empty_test},\n"
            f"    {C_BORDER_ERROR},\n"
            f"    If({empty_test}, {C_CARD_BORDER}, {C_BORDER_OK})\n"
            f")")


def input_fill(display_mode):
    """Graat = kan ikke redigeres.

    Det ENE spoergsmaal, der afgoer et inputfelts baggrund. Datovaelgeren
    havde ingen - den saa redigerbar ud i visningstilstand."""
    if not display_mode:
        return C_INPUT_BG
    return f"If({display_mode} = DisplayMode.Edit, {C_INPUT_BG}, {C_DISABLED_BG})"


def text_input(name, default, placeholder="\"\"", max_length=None, required_formula="false",
               width="Parent.Width", height=36, display_mode=None, ttype=None,
               onchange=None, label=None):
    props = {
        "AccessibleLabel": label if label else f"\"{name}\"",
        "BorderColor": border_rule("IsBlank(Trim(Self.Text))", required_formula),
        "BorderStyle": "BorderStyle.Solid",
        "BorderThickness": "1",
        "Color": C_TITLE,
        "Default": default,
        "Fill": input_fill(display_mode),
        "Font": FONT,
        "Height": str(height),
        "LayoutMinWidth": "0",
        "Placeholder": placeholder,
        "RadiusBottomLeft": "10", "RadiusBottomRight": "10",
        "RadiusTopLeft": "10", "RadiusTopRight": "10",
        "Size": "14",
        "ValidationState": f"If({required_formula} && IsBlank(Trim(Self.Text)), ValidationState.Error, ValidationState.None)",
        "Width": width,
    }

    if max_length is not None:
        props["MaxLength"] = str(max_length)
    if display_mode is not None:
        props["DisplayMode"] = display_mode
    if ttype is not None:
        props["Type"] = f"TextInputType.{ttype}"
    if onchange is not None:
        props["OnChange"] = onchange
    return Ctrl(name, "ModernTextInput", props=props, h=height)


def number_input(name, default, min_v=None, max_v=None, required_formula="false",
                 width="Parent.Width", height=36, display_mode=None, label=None):
    props = {
        "AccessibleLabel": label if label else f"\"{name}\"",
        "Appearance": "Appearance.Outline",
        "BorderColor": border_rule("IsBlank(Self.Value)", required_formula),
        "BorderStyle": "BorderStyle.Solid",
        "BorderThickness": "1",
        "Color": C_TITLE,
        "Default": default,
        "Fill": input_fill(display_mode),
        "Font": FONT,
        "Height": str(height),
        "LayoutMinWidth": "0",
        "Precision": "DecimalPrecision.'0'",
        "RadiusBottomLeft": "10", "RadiusBottomRight": "10",
        "RadiusTopLeft": "10", "RadiusTopRight": "10",
        "Size": "14",
        "ValidationState": f"If({required_formula} && IsBlank(Self.Value), ValidationState.Error, ValidationState.None)",
        "Width": width,
    }
    if min_v is not None:
        props["Min"] = str(min_v)
    if max_v is not None:
        props["Max"] = str(max_v)
    if display_mode is not None:
        props["DisplayMode"] = display_mode
    return Ctrl(name, "ModernNumberInput", props=props, h=height)


def date_picker(name, default_date, required_formula="false",
                width="Parent.Width", height=36, display_mode=None,
                onchange=None, label=None, placeholder='"dd/mm/yyyy"'):
    """Datovaelger - med SAMME kant- og baggrundsregel som de andre felter.

    Den var bygget i haanden inde i domain_parts.py og havde en FAST graa
    kant og INGEN Fill. Den blev derfor aldrig roed, naar den manglede,
    aldrig groen naar den var udfyldt, og den saa redigerbar ud i
    visningstilstand - hvidt felt med kant, der ikke reagerer.

    DefaultDate SAETTER datoen. SelectedDate LAESER den og kan ikke
    skrives - "Unknown property 'SelectedDate' for control type
    'ModernDatePicker'". Det er derfor OnChange laeser Self.SelectedDate,
    mens DefaultDate faar variablen."""
    props = {
        "AccessibleLabel": label if label else f'"{name}"',
        "Appearance": "Appearance.Outline",
        "BorderColor": border_rule("IsBlank(Self.SelectedDate)", required_formula),
        "BorderStyle": "BorderStyle.Solid",
        "BorderThickness": "1",
        "DefaultDate": default_date,
        "Fill": input_fill(display_mode),
        "Font": FONT,
        "Format": "DatePickerFormat.Short",
        "Height": str(height),
        "LayoutMinWidth": "0",
        "Placeholder": placeholder,
        "RadiusBottomLeft": "10", "RadiusBottomRight": "10",
        "RadiusTopLeft": "10", "RadiusTopRight": "10",
        "Size": "14",
        "Width": width,
    }
    if display_mode is not None:
        props["DisplayMode"] = display_mode
    if onchange is not None:
        props["OnChange"] = onchange
    return Ctrl(name, "ModernDatePicker", props=props, h=height)


def dropdown(name, items, default, item_display="ThisItem.Value", required_formula="false",
             width="Parent.Width", height=36, display_mode=None, value_field="Value", label=None):
    props = {
        "AccessibleLabel": label if label else f"\"{name}\"",
        "Appearance": "Appearance.Outline",
        "BorderColor": border_rule(f"IsBlank(Self.Selected.{value_field})",
                                   required_formula),
        "BorderStyle": "BorderStyle.Solid",
        "BorderThickness": "1",
        "Color": C_TITLE,
        "Default": default,
        "Fill": input_fill(display_mode),
        "Font": FONT,
        "Height": str(height),
        "ItemDisplayText": item_display,
        "Items": items,
        "LayoutMinWidth": "0",
        "RadiusBottomLeft": "10", "RadiusBottomRight": "10",
        "RadiusTopLeft": "10", "RadiusTopRight": "10",
        "Size": "14",
        "ValidationState": f"If({required_formula} && IsBlank(Self.Selected.{value_field}), ValidationState.Error, ValidationState.None)",
        "Width": width,
    }
    if display_mode is not None:
        props["DisplayMode"] = display_mode
    return Ctrl(name, "ModernDropdown", props=props, h=height)


def themed_dropdown(name, items, default_text, value_col="Value", required_formula="false",
                    width="Parent.Width", height=36, display_mode=None, label=None,
                    onchange=None):
    """Dropdown, hvis LISTE ogsaa foelger temaet.

    HVORFOR IKKE ModernDropdown
    ---------------------------
    Den moderne dropdown aabner sin liste som en Fluent-flyout, og den
    flyout farves af Fluent-temaet - ikke af kontrollens egne egenskaber.
    Appen saetter ikke Fluent-temaet (farverne er C, se design_tokens.py),
    saa listen var hvid/graa i moerk tilstand, med vores naesten-hvide
    tekst ovenpaa. Man kunne ikke laese, hvad man valgte imellem.

    Classic/DropDown tegner sin liste med Fill, Color, HoverFill og
    SelectionFill - og dem giver vi tokens. Saa skifter listen med temaet
    som alt andet.

    Default er TEKSTEN i value_col - ikke en record, som ModernDropdown
    ville have. Selected er stadig hele recorden, saa Self.Selected.Code
    virker som foer."""
    props = {
        "AccessibleLabel": label if label else f"\"{name}\"",
        "AllowEmptySelection": "true",
        "BorderColor": border_rule(f"IsBlank(Self.Selected.{value_col})", required_formula),
        "BorderStyle": "BorderStyle.Solid",
        "BorderThickness": "1",
        "ChevronBackground": input_fill(display_mode),
        "ChevronDisabledBackground": C_DISABLED_BG,
        "ChevronDisabledFill": C_MUTED,
        "ChevronFill": C_TITLE,
        "ChevronHoverBackground": C_PRIMARY_SOFT,
        "ChevronHoverFill": C_TITLE,
        "Color": C_TITLE,
        "Default": default_text,
        "DisabledColor": C_MUTED,
        "DisabledFill": C_DISABLED_BG,
        "Fill": input_fill(display_mode),
        "Font": FONT,
        "Height": str(height),
        "HoverColor": C_TITLE,
        "HoverFill": C_PRIMARY_SOFT,
        "Items": items,
        "Items.Value": value_col,
        "PaddingLeft": "12",
        "PressedColor": C_WHITE,
        "PressedFill": C_PRIMARY,
        "SelectionColor": C_WHITE,
        "SelectionFill": C_PRIMARY,
        "Size": "14",
        "Width": width,
    }
    if display_mode is not None:
        props["DisplayMode"] = display_mode
    if onchange is not None:
        props["OnChange"] = onchange
    return Ctrl(name, "Classic/DropDown", props=props, h=height)


def combobox(name, items, display_field="Display", multi=False, default_items=None,
             placeholder="\"Search\"", required_formula="false", width="Parent.Width",
             height=40, display_mode=None, onchange=None, label=None):
    """Soegefelt og valgliste i EEN kontrol.

    BRUGES IKKE LAENGERE. Staar her, fordi ideen er god - men i praksis
    viste Classic/ComboBox sig ikke at vise de raekker, den fik: flowet
    returnerede 819 Functional Locations, beskeden sagde det, og dropdownen
    var tom. Comboboksens indbyggede soegefiltrering er et lag, der ikke kan
    inspiceres udefra, og det lag var fejlen.

    FL-feltet er derfor bygget om til soegefelt + soegeknap + almindelig
    dropdown, hvor der ikke er noget skjult filter tilbage. Genindfoer den
    ikke uden at have bevist, at filtreringen virker mod rigtige data.


    Classic/ComboBox har indbygget soegefelt (IsSearchable), saa brugeren
    skriver og vaelger i det samme felt. Derfor er der hverken en separat
    soegeknap eller en separat dropdown ved siden af.

    Der bruges Classic/ComboBox og ikke ModernCombobox, fordi det er den
    variant der eksponerer SearchText som output-egenskab. Uden SearchText
    kan timeren ikke se, hvad brugeren har skrevet, og saa er hele
    soege-mens-du-skriver-moenstret ikke muligt.

    Valideringen maaler paa SelectedItems og ikke paa Selected, saa den
    ogsaa virker for multi-select."""
    sel_test = ("CountRows(Self.SelectedItems) = 0" if multi
                else f"IsBlank(Self.Selected.{display_field})")
    props = {
        "AccessibleLabel": label if label else f"\"{name}\"",
        "BorderColor": border_rule(sel_test, required_formula),
        "BorderStyle": "BorderStyle.Solid",
        "BorderThickness": "1",
        "ChevronBackground": C_PRIMARY,
        "ChevronFill": C_WHITE,
        "ChevronHoverBackground": C_PRIMARY2,
        "ChevronHoverFill": C_WHITE,
        "Color": C_TITLE,
        "DisplayFields": f"[\"{display_field}\"]",
        "Fill": C_INPUT_BG,
        "Font": FONT,
        "Height": str(height),
        "InputTextPlaceholder": placeholder,
        "IsSearchable": "true",
        "Items": items,
        "LayoutMinWidth": "0",
        "NoSelectionText": "\"\"",
        "SearchFields": f"[\"{display_field}\"]",
        "SelectMultiple": "true" if multi else "false",
        "SelectionColor": C_WHITE,
        "SelectionFill": C_PRIMARY,
        "Size": "14",
        "Width": width,
    }
    if default_items is not None:
        props["DefaultSelectedItems"] = default_items
    if display_mode is not None:
        props["DisplayMode"] = display_mode
    if onchange is not None:
        props["OnChange"] = onchange
    return Ctrl(name, "Classic/ComboBox", props=props, h=height)


def poll_timer(name, on_timer_end, duration=500):
    """Usynlig baggrunds-timer.

    Duration 500 ms er samme vaerdi som i referenceappen: hurtigt nok til at
    foeles som "mens du skriver", langsomt nok til at brugeren naar at skrive
    faerdig foer der kaldes. Selve spaerren mod gentagne kald ligger i
    formlen (se build_flsearch.timer_poll_action), ikke i intervallet.

    Visible = false er med vilje: en Timer med AutoStart = true koerer
    ogsaa naar den er skjult, og kontrollen har ingen visuel funktion."""
    return Ctrl(name, "Timer", props={
        "AutoPause": "false",
        "AutoStart": "true",
        "Duration": str(duration),
        "Height": "1",
        "OnTimerEnd": on_timer_end,
        "Repeat": "true",
        "Visible": "false",
        "Width": "1",
    }, h=1, vis="false")


def pin_widths(ctrls):
    """Laas cellebredderne i en tabelraekke, saa den ikke kan klemmes sammen.

    Alle inputs faar LayoutMinWidth = 0 - det er med vilje, for i de fleste
    raekker SKAL de kunne give efter. Men i en vandret container med faste
    bredder betyder det, at hvis raekken bare er nogle faa pixels smallere
    end sit indhold - en scrollbar i galleriet, TemplatePadding, en kant -
    saa krymper ALLE celler forholdsmaessigt.

    Konsekvensen ses ikke i den foerste kolonne, men vokser hen over raekken:
    tabellen glider til venstre i forhold til sin HTML-overskrift, indtil
    vaerdierne staar under den forkerte titel. Overskriften er en HtmlViewer
    med faste kolonner og kan ikke give efter, saa de to kan ikke undgaa at
    komme fra hinanden.

    Her laases hver celles mindstebredde til dens faktiske bredde. Saa kan
    raekken ikke krympe - den bliver klippet eller scroller i stedet, og
    kolonnerne bliver staaende under deres titler.
    """
    for c in ctrls:
        w = str(c.props.get("Width", "")).strip()
        if w.isdigit():
            c.props["LayoutMinWidth"] = w
    return ctrls


# ---------------------------------------------------------------------------
# Tekstbredde - regnet i Python, fordi Power Fx ikke kan maale en tekst
# ---------------------------------------------------------------------------
# Andel af skriftstoerrelsen, et tegn fylder i Segoe UI. Et skoen, ikke en
# maaling - og med vilje et skoen, der rammer lidt for BREDT: en label, der
# er fire pixels for bred, flytter stjernen fire pixels; en, der er fire
# pixels for smal, klipper det sidste bogstav af.
_EM = {"upper": 0.68, "lower": 0.56, "digit": 0.58, "space": 0.3, "narrow": 0.34}
_NARROW = set("ijlrtf.,:;!|'()[]-/")


def text_px(text, size=14, semibold=True):
    """Hvor bred en LITTERAL tekst er, i pixels (afrundet op).

    Bruges hvor en kontrol skal vaere saa bred som sin tekst og ikke
    bredere: labelen foran en paakraevet-stjerne, og knapper."""
    em = 0.0
    for ch in text:
        if ch == " ":
            em += _EM["space"]
        elif ch in _NARROW:
            em += _EM["narrow"]
        elif ch.isdigit():
            em += _EM["digit"]
        elif ch.isupper():
            em += _EM["upper"]
        else:
            em += _EM["lower"]
    w = em * size * (1.06 if semibold else 1.0) * 1.1
    return int(-(-w // 1))


# Segoe UI's egne tegnbredder (regular, i em), til labelen foran en stjerne.
#
# text_px() ovenfor er et skoen med vilje for bredt - fint til en knap, der
# alligevel har 16 px luft i hver side. Foran en paakraevet-stjerne blev det
# til "Plan Type        *": skoennet ramte 15 px for bredt, og stjernen stod
# langt fra sin tekst (issue #54). Tabellen her er fontens egne maal, saa
# afstanden bliver de 3 px, label_row beder om, plus en lille sikkerhed.
_SEGOE = {
    " ": .274, "a": .537, "b": .599, "c": .478, "d": .599, "e": .54, "f": .326,
    "g": .599, "h": .577, "i": .24, "j": .24, "k": .505, "l": .24, "m": .874,
    "n": .577, "o": .595, "p": .599, "q": .599, "r": .354, "s": .438, "t": .35,
    "u": .577, "v": .496, "w": .736, "x": .478, "y": .496, "z": .455,
    "A": .653, "B": .576, "C": .627, "D": .706, "E": .506, "F": .482, "G": .694,
    "H": .729, "I": .273, "J": .361, "K": .589, "L": .468, "M": .897, "N": .748,
    "O": .748, "P": .553, "Q": .748, "R": .599, "S": .527, "T": .523, "U": .692,
    "V": .637, "W": .948, "X": .608, "Y": .569, "Z": .566,
    "(": .3, ")": .3, "/": .38, "-": .38, ".": .24, ",": .24, ":": .24,
}
# Semibold er ca. 4 % bredere end regular; 3 % oven i er sikkerheden mod at
# klippe det sidste bogstav.
_SEGOE_SEMIBOLD = 1.04 * 1.03


def label_px(text, size=13):
    """Bredden af en Semibold-label foran en stjerne, i pixels (op)."""
    em = sum(_SEGOE.get(ch, .58 if ch.isdigit() else .6) for ch in text)
    return int(-(-(em * size * _SEGOE_SEMIBOLD) // 1))


def fit_button_width(text, size=14, min_w=72):
    """Knapbredden til en tekst: teksten + 2 x 16 px luft.

    text er Power Fx-litteralen ('"Save draft"'), som den staar i button().
    """
    lit = text.strip()
    if not (lit.startswith('"') and lit.endswith('"')):
        raise ValueError("fit_button_width kraever en tekstlitteral, fik %r" % text)
    return max(min_w, text_px(lit[1:-1], size) + 32)


def label_row(name, label_text, required=False, width="Parent.Width", cell_w=None):
    """Feltets overskrift - og stjernen LIGE efter den.

    Labelen fyldte foer hele cellens bredde, saa stjernen stod ude ved
    cellens hoejre kant, langt fra den tekst, den hoerer til. Nu er labelen
    saa bred som sin tekst (text_px), og stjernen staar 3 px efter.

    cell_w er cellens bredde, naar den kendes. Labelen maa aldrig blive
    bredere end cellen minus stjernen - saa klipper den hellere, end den
    skubber stjernen ud af raekken."""
    # KUN EN RAEKKE, NAAR DER ER EN STJERNE
    #
    # Uden stjerne var raekken en container med eet barn - en kontrol pr.
    # felt, der intet gjorde. Equipment-skaermen ramte App checkerens
    # graense (kompleksitet 302 af 300, issue #37), og det var de
    # kontroller, der kunne undvaeres uden at noget ser anderledes ud.
    if not required:
        return text_ctrl(f"{name}Lbl", f"\"{label_text}\"", size=13, weight="Semibold",
                         height=20, width=width, wrap="false")
    lbl_w = label_px(label_text, 13)
    if cell_w is not None:
        lbl_w = "Min(%d, (%s) - 13)" % (lbl_w, cell_w)
    kids = [text_ctrl(f"{name}Lbl", f"\"{label_text}\"", size=13, weight="Semibold", height=20,
                      width=lbl_w if required else None, wrap="false")]
    if required:
        kids.append(text_ctrl(f"{name}Star", "\"*\"", size=13, color=C_REQUIRED, weight="Semibold",
                              height=20, width=10, wrap="false", accessible="\"Required\""))
    return group(f"{name}Row", kids, direction="Horizontal", gap=3, height=20, align_items="Center", width=width)


def col_width(container_w, cols, gap=20):
    """Bredden af eet ud af `cols` felter side om side i en container med
    bredden container_w. Under braekpunktet TWO_COL_MIN staar alle felter
    fuld bredde (raekken stables lodret af row_n / two_col_row)."""
    return fits(container_w, TWO_COL_MIN, container_w,
                f"({container_w} - {gap * (cols - 1)}) / {cols}")


def field_cell(name, label_text, input_ctrl, required=False, hint_text=None, width=None,
               container_w=SHELL_W, fill_portions_formula=None, cols=2, gap=20):
    """Et felt med label over.

    fill_portions_formula=None betyder braekpunktet: feltet vokser kun,
    naar der er desktop-plads. Stod foer som "If(App.Width < 1024, 0, 1)"
    - et af fire naesten ens tal. Se tools/layout_tokens.py. Hoejden regnes af indholdet - den er ikke laengere
    et magisk tal, saa et hoejere input (fx multiline) giver automatisk en
    hoejere felt.

    cols er antallet af felter, der skal staa side om side i raekken (brug
    samme tal i row_n/two_col_row), saa bredden bliver ens for alle celler
    i raekken."""
    # Alle feltforklaringer styres af EEN variabel, varVhpShowHints, slaaet
    # til og fra i hero-kortet. Foer havde hvert felt sit eget i-ikon - 21
    # knapper for at vise 21 linjer er en knap for meget pr. linje.
    #
    # Hoejdealgebraen taeller kun synlige boern med, saa linjerne koster
    # ingen plads, naar de er slaaet fra.
    w = width or col_width(container_w, cols, gap)
    kids = [label_row(name, label_text, required=required, cell_w=w), input_ctrl]
    if hint_text is not None:
        kids.append(text_ctrl(f"{name}Hint", hint_text, size=12, color=C_MUTED,
                              height=32, wrap="true",
                              visible=HINTS_ON))
    # SKAERMLAESEREN SKAL HOERE ETIKETTEN, IKKE KONTROLNAVNET
    #
    # De fire inputbyggere saetter AccessibleLabel til kontrollens eget
    # navn, naar kalderen ikke giver andet. Det betoed, at en skaermlaeser
    # sagde "inp Manufacturer" i stedet for "Fabrikat" - 75 felter i tre
    # apps. Hubben gjorde det rigtigt, fordi den ikke har raa inputs.
    #
    # field_cell KENDER etiketten. Den retter derfor det, der stadig staar
    # som standarden - og kun det: har kalderen sat en rigtig etiket, er
    # den bevaret. Standarden kendes paa, at den er kontrollens eget navn.
    #
    # "Paakraevet" haenges paa, fordi stjernen ved siden af etiketten er
    # synlig og dermed ingenting for den, der lytter.
    default_label = '"%s"' % input_ctrl.name
    if str(input_ctrl.props.get("AccessibleLabel", "")).strip() == default_label:
        acc = label_text + (", required" if required else "")
        input_ctrl.props["AccessibleLabel"] = '"%s"' % acc.replace('"', '""')

    fp = (if_below("Desktop", "0", "1")
          if fill_portions_formula is None else fill_portions_formula)
    return group(name, kids, direction="Vertical", gap=6, width=w,
                 align_items="Stretch", fill_portions=fp,
                 align_in_container="Start")


def row_n(name, cells, container_w=SHELL_W, gap=20):
    """Vilkaarligt antal felter side om side - stablet lodret under
    braekpunktet.

    Generaliseret udgave af two_col_row: hoejden foelger cellernes
    faktiske hoejde, og braekpunktet maales paa containerens egen bredde i
    stedet for App.Width."""
    heights = [c.h for c in cells]
    if len(cells) == 1:
        tall = f"({heights[0]})"
        stacked = tall
    else:
        terms = ", ".join(f"({h})" for h in heights)
        tall = f"Max({terms})"
        stacked = " + ".join(f"({h})" for h in heights) + f" + {gap * (len(cells) - 1)}"
    h = fits(container_w, TWO_COL_MIN, stacked, tall)
    return group(name, cells, direction="Horizontal", gap=gap, height=h, wrap="true")


def column_grid(name, columns, container_w=SHELL_W, gap=20, row_gap=12):
    """Felter i KOLONNE-orden (issue #54): oppefra og ned i kolonne 1, saa
    kolonne 2, og saa videre - ikke raekke for raekke.

    columns er en liste af kolonner, hver en liste af celler bygget med
    field_cell(..., width=column_width(...), fill_portions_formula="0").
    Hver kolonne er en lodret gruppe; kolonnerne staar side om side i en
    row_n, der stabler dem under braekpunktet - og saa kommer de stadig i
    kolonne-orden, fordi det er kolonnerne, der stables, ikke raekkerne.

    Tab-raekkefoelgen foelger traeet, og traeet er nu kolonne-orden."""
    w = col_width(container_w, len(columns), gap)
    cols = [group(f"{name}Col{i + 1}", cells, direction="Vertical", gap=row_gap,
                  width=w, align_items="Stretch", align_in_container="Start")
            for i, cells in enumerate(columns)]
    return row_n(name, cols, container_w=container_w, gap=gap)


def two_col_row(name, cell_a, cell_b, container_w=SHELL_W):
    """To felter side om side - stablet under braekpunktet. Item Editor-kortet
    er ca. 380 px smallere end skaermen, saa App.Width som maalestok fik
    felterne til at staa side om side laenge efter at der reelt var plads."""
    return row_n(name, [cell_a, cell_b], container_w=container_w)


def badge(name, text, size=11, width=64):
    return text_ctrl(name, text, size=size, color=C_MUTED, weight="Semibold", height=22,
                     width=width, wrap="false",
                     extra={"Fill": C_NEUTRAL_BG, "Align": "Align.Center",
                            "AlignInContainer": "AlignInContainer.Center",
                            "PaddingLeft": "10", "PaddingRight": "10",
                            "RadiusBottomLeft": "12", "RadiusBottomRight": "12",
                            "RadiusTopLeft": "12", "RadiusTopRight": "12"})


def card(name, children, gap=14, visible=None, pad_y=18):
    """Sektionskort i appens standardstil. Padding taelles automatisk med i
    hoejden - det var den fejl der gjorde hvert eneste kort 36 px for lavt.

    pad_y er kun top og bund. Siderne er altid 18: indholdsbredden regnes
    overalt som SHELL_W - 36."""
    return group(name, children, direction="Vertical", gap=gap,
                 fill=C_CARD_BG, border_color=C_CARD_BORDER, radius=14,
                 pad=(pad_y, 18, pad_y, 18), visible=visible)
