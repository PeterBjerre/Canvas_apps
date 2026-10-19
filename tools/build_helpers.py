# -*- coding: utf-8 -*-
"""
Genbrugelige kontrol-byggere. Styling er uaendret fra den oprindelige app
(samme farver, radier, skriftstoerrelser og polstring som powerapp-materialer).

Det eneste der er lavet om, er hoejdemodellen: group() regner selv sin hoejde
ud af boernenes hoejder plus gaps og padding, i stedet for at en formel i
YAML'en refererer andre kontrollers .Height. Se gen_screen.stack_height.
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from design_tokens import DARK_VAR, toggle_action, ref_hex as ref_hex_expr, TRANSPARENT
import layout_tokens as lay
from layout_tokens import at_least, below, fits, if_below, TWO_COL_MIN
from gen_screen import (Ctrl, child_name, stack_height, row_height, C_APP_BG, C_CARD_BG,
                        C_CARD_BORDER, C_INPUT_BORDER, C_TITLE, C_MUTED, C_REQUIRED, C_PRIMARY,
                        C_PRIMARY2, C_WHITE, C_TRANSPARENT, C_INPUT_BG, C_INPUT_FG,
                        C_DISABLED_BG, C_DIVIDER, C_VALID_FG, C_INVALID_FG,
                        C_VALID_BG, C_INVALID_BG,
                        C_BORDER_OK, C_BORDER_ERROR, C_PRIMARY_SOFT, C_OVERLAY,
                        C_MODAL_BG, C_ROW_HOVER, C_ROW_PRESSED, C_NEUTRAL_BG, C_MUTED_BG,
                        FONT, SHELL_W)

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


# Braekpunktet, hvor et to-kolonne-felt stables lodret, staar i
# tools/layout_tokens.py. Det er en CONTAINER-graense og ikke en
# enhedsklasse: et smalt kort stabler sine felter, ogsaa paa en bred
# skaerm.


# En tekstkontrol skal vaere mindst saa hoej som en linje af sin egen
# skrift. Er den ikke det, viser den moderne Text-kontrol sin EGEN
# scrollbar - det var den moerke streg midt i topbjaelken: titlen var 22 pt
# i 30 px. Samme forhold stod paa VH-planens sektionstitler (19 i 26) og
# hubbens tal (26 i 32). 1,5 x skriftstoerrelsen giver luft til Semibold.
TEXT_LINE = lay.TEXT_LINE


def text_min_height(size):
    return int(-(-size * TEXT_LINE // 1))


def text_ctrl(name, text, size=14, color=C_TITLE, weight=None, wrap="false",
              align=None, height=20, width=None, fill=C_TRANSPARENT,
              accessible=None, visible=None, layout_min_width=None, extra=None):
    if isinstance(height, (int, float)) and height < text_min_height(size):
        height = text_min_height(size)
    props = {
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
    # AccessibleLabel kun, naar den siger noget andet end teksten - eller
    # naar teksten er en fast streng. En skaermlaeser laeser en ModernText's
    # Text op i forvejen. Her stod ALTID "accessible or text", saa en tung
    # tekstformel (hubbens CountRows mod SharePoint, Switch/DateDiff pr.
    # galleriraekke) blev regnet ud to gange (REVIEW.md B2).
    # Men uden AccessibleLabel melder tilgaengelighedstjekket
    # AccessibleLabelNeeded for hver eneste tekst med en formel (issue #86).
    # Self.Text laeser den allerede beregnede vaerdi - formlen koerer ikke
    # igen.
    if accessible:
        props["AccessibleLabel"] = accessible
    elif re.fullmatch(r'"(?:[^"]|"")*"', text.strip()):
        props["AccessibleLabel"] = text
    else:
        props["AccessibleLabel"] = "Self.Text"
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
# er Fluent-ikonernes; ModernButton.Icon tager dem direkte. De staar i
# tools/icons.FLUENT (issue #139): Submit fik ingen ikon, mens Save draft
# ved siden af havde et, og Send (beskeder, Issue Board) havde papirflyveren.
# Nu er indsend = send overalt.
import icons as _icons
ICON_SAVE = _icons.FLUENT["save"]
ICON_SUBMIT = _icons.FLUENT["submit"]
# Ikon + mellemrum foran teksten - laegges til knappens tekstbredde.
ICON_W = 24


def button(name, text, onselect, primary=False, danger=False, width=140, height=36,
           display_mode=None, base_color=None, layout_min_width=None, visible=None,
           accessible=None, icon=None, tooltip=None):
    props = {
        "AccessibleLabel": accessible if accessible else text,
        "Align": "Align.Center",
        "AlignInContainer": "AlignInContainer.Center",
        "Font": FONT,
        "FontWeight": "FontWeight.Semibold",
        "Height": str(height),
        "Layout": "ButtonLayout.TextOnly",
        "OnSelect": onselect,
        **lay.radius(lay.RADIUS_INPUT),
        "Size": str(lay.SIZE_INPUT),
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
        # border-input (3:1 mod fladen), ikke border-default (1,2:1, naesten usynlig)
        props["BorderColor"] = C_INPUT_BORDER
        props["BorderThickness"] = "1"
        props["Color"] = C_TITLE
    if display_mode:
        props["DisplayMode"] = display_mode
    if layout_min_width is not None:
        props["LayoutMinWidth"] = str(layout_min_width)
    if visible is not None:
        props["Visible"] = visible
    if tooltip:
        props["Tooltip"] = tooltip
    # Ikon foran teksten. icon er et Fluent-ikonnavn ("Save") eller et
    # Power Fx-udtryk, der giver et.
    if icon:
        props["Icon"] = icon if icon.startswith(("If(", '"')) else f'"{icon}"'
        props["Layout"] = "ButtonLayout.IconBefore"
    return Ctrl(name, "ModernButton", props=props, h=height, vis=visible)


def flat_button(name, text, onselect, *, accessible, height, color, width=None,
                appearance="Transparent", base_color=None, align="Left", size=None,
                weight="Normal", padding=0, border=None, radius=0, tooltip=None,
                visible=None):
    """En ModernButton UDEN Fluent-knappens indre luft (issue #307).

    De sidste klassiske knapper, der ikke er raekkelag: feedback-vaelgerens
    felt (venstrestillet tekst, der flugter med listen under, #140) og
    "nogle valgt"-feltet i operationsvaelgeren (18 x 18 px). De brugte
    Classic/Button for Padding* og BorderStyle; den opdaterede moderne knap
    har begge (Microsoft Learn, "Button modern control in canvas apps").

    Kun Learns egenskaber. Hover-, tryk- og fokusfarverne er Fluent-temaets
    - knappen har intet HoverFill/PressedFill/FocusedBorder* og intet Fill
    (fyldet er Appearance + BasePaletteColor). border er (farve, tykkelse)
    eller None (ingen kant)."""
    pad = str(padding)
    props = {
        "AccessibleLabel": accessible,
        "Align": f"Align.{align}",
        "Appearance": f"ButtonAppearance.{appearance}",
        "BorderStyle": "BorderStyle.Solid" if border else "BorderStyle.None",
        "BorderThickness": str(border[1]) if border else "0",
        "Color": color,
        "Font": FONT,
        "FontWeight": f"FontWeight.{weight}",
        "Height": str(height),
        # Intet Layout: uden Icon er knappen ren tekst (Learn kender kun
        # IconBefore/IconAfter/IconOnly).
        "OnSelect": onselect,
        "PaddingBottom": pad, "PaddingLeft": pad, "PaddingRight": pad, "PaddingTop": pad,
        **lay.radius(radius),
        "Size": str(size if size is not None else lay.SIZE_INPUT),
        "Text": text,
        "VerticalAlign": "VerticalAlign.Middle",
    }
    if border:
        props["BorderColor"] = border[0]
    if base_color:
        props["BasePaletteColor"] = base_color
    if width is not None:
        props["Width"] = str(width)
    if tooltip:
        props["Tooltip"] = tooltip
    if visible is not None:
        props["Visible"] = visible
    return Ctrl(name, "ModernButton", props=props, h=height, vis=visible)


def icon_on_mobile(btn, w=40):
    """Under Tablet er knappen kun sit ikon (en kvadratisk flade); ellers uaendret."""
    narrow = lay.below("Tablet")
    btn.desk_w = btn.props["Width"]
    btn.icon_w = w
    btn.props["Width"] = f"If({narrow}, {w}, {btn.props['Width']})"
    btn.props["LayoutMinWidth"] = btn.props["Width"]
    btn.props["Layout"] = f"If({narrow}, ButtonLayout.IconOnly, ButtonLayout.IconBefore)"
    return btn


# "NEW REQUEST" - DEN SAMME KNAP OVERALT (issue #243)
#
# Hver knap, der starter en ny anmodning, hedder praecis "New Request" -
# uden plus-ikon og uden "+" i teksten, paa alle skaermbredder. Foer var den
# "New request" med et plus fra Tablet og op og "New" paa en telefon.
# Bredden er teksten + den faelles luft (fit_button_width), saa teksten
# staar midt i knappen. Paa en telefon er der ikke plads til 14 pt - der er
# teksten den samme i 12 pt med 12 px luft i hver side (text_px + 24, samme
# luft som hubbens smalle filterknapper). Submit er kun sit ikon dér.
NEW_REQUEST = '"New request"'
NEW_REQUEST_PHONE_SIZE = 12


def new_request_widths():
    """(bredde fra Tablet og op, bredde paa en telefon) for "New request"."""
    return (fit_button_width(NEW_REQUEST),
            text_px(NEW_REQUEST[1:-1], NEW_REQUEST_PHONE_SIZE) + 24)


def new_request_label(btn):
    """Goer btn til den faelles "New request"-knap (issue #243): praecis den
    tekst, intet ikon, centreret tekst og en bredde regnet af teksten.
    OnSelect, tooltip, synlighed og DisplayMode roeres ikke."""
    narrow = lay.below("Tablet")
    full_w, phone_w = new_request_widths()
    # En egen skaermlaesertekst (VH-planens "Start a new blank request")
    # bliver staaende; var den bare knappens tekst, foelger den med.
    if btn.props.get("AccessibleLabel") in (None, btn.props.get("Text")):
        btn.props["AccessibleLabel"] = NEW_REQUEST
    btn.props["Text"] = NEW_REQUEST
    btn.props.pop("Icon", None)
    btn.props["Layout"] = "ButtonLayout.TextOnly"
    btn.props["Align"] = "Align.Center"
    # Synlig kant (UX): den udfyldte knap stod uden omrids ved siden af de
    # andre knapper.
    btn.props["BorderColor"] = C_INPUT_BORDER
    btn.props["BorderThickness"] = "1"
    btn.props["Size"] = f"If({narrow}, {NEW_REQUEST_PHONE_SIZE}, {lay.SIZE_INPUT})"
    btn.props["Width"] = f"If({narrow}, {phone_w}, {full_w})"
    btn.props["LayoutMinWidth"] = btn.props["Width"]
    return btn


# ---------------------------------------------------------------------------
# HEADERENS HANDLINGER - SAMME RAEKKEFOELGE OG VAEGT OVERALT (UX-review T1)
#
#     [New request]  |  [Save draft] [Submit (2 to fix)]
#      diskret          outline       primaer (blaa)
#
# Foer stod Save draft, Submit og New request i een raekkefoelge i
# domaenerne og en anden i VH-planen ("New request, Create draft, Submit"),
# og Submit var aldrig den blaa knap - "Save row" nede i kortet var. Nu er
# Submit altid primaer, og taelleren siger, hvorfor den ikke kan sendes.
# ---------------------------------------------------------------------------
SUBMIT_FIX_LONGEST = '"Submit (99 to fix)"'


# ---------------------------------------------------------------------------
# KLIKFLADEN (UX-review F6/T10): en ikonknap og et klikbart ikon er mindst
# H.hit - 32 px fra Desktop og 44 px under (touch). Ikonet beholder sin
# stoerrelse; kun fladen vokser. check_layout regel 40 haandhaever det.
# ---------------------------------------------------------------------------
def hit_size(n):
    """Mindst n og mindst H.hit - som Power Fx."""
    return lay.HIT if n <= lay.HIT_DESKTOP else f"Max({n}, {lay.HIT})"


def ensure_hit(ctrl, square=True):
    """Goer ctrl's klikflade mindst H.hit. Et billede tegnes i sin egen
    stoerrelse midt i fladen (ImagePosition.Center), saa ikonet ikke
    skaleres. square=False roerer kun hoejden (en knap med tekst)."""
    def _num(v):
        try:
            return int(float(str(v)))
        except ValueError:
            return None
    h = _num(ctrl.props.get("Height"))
    if h is not None and h < lay.HIT_TOUCH:
        ctrl.props["Height"] = hit_size(h)
        ctrl.h = ctrl.props["Height"]
    if square:
        w = _num(ctrl.props.get("Width"))
        if w is not None and w < lay.HIT_TOUCH:
            ctrl.props["Width"] = hit_size(w)
            if "LayoutMinWidth" in ctrl.props:
                ctrl.props["LayoutMinWidth"] = ctrl.props["Width"]
    if ctrl.control == "Image":
        ctrl.props["ImagePosition"] = "ImagePosition.Center"
    return ctrl


def ghost(btn):
    """New request: samme synlige ramme som Save draft (outline, 1 px)."""
    btn.props["Appearance"] = "ButtonAppearance.Outline"
    btn.props["BorderColor"] = C_INPUT_BORDER
    btn.props["BorderThickness"] = "1"
    btn.props["Color"] = C_TITLE
    return btn


def submit_fix_text(fix_expr):
    """Submit-knappens tekst med taelleren: "Submit" / "Submit (2 to fix)"."""
    return (f'With({{ _f: {fix_expr} }}, "Submit" & '
            f'If(_f > 0, " (" & Text(_f) & " to fix)", ""))')


def with_fix_count(submit, fix_expr):
    """Goer submit til den faelles Submit med "N to fix" (T1/M4). Bredden
    er den laengste tekst, saa knappen ikke skifter stoerrelse."""
    submit.props["Text"] = submit_fix_text(fix_expr)
    submit.props["AccessibleLabel"] = "Self.Text"
    w = fit_button_width(SUBMIT_FIX_LONGEST) + (ICON_W if submit.props.get("Icon") else 0)
    submit.props["Width"] = str(w)
    submit.props["LayoutMinWidth"] = str(w)
    return submit


def action_sep(name, visible=None):
    """Den lodrette streg mellem New request og anmodningens handlinger."""
    sep = group(name, [], direction="Horizontal", height=24, width="1",
                fill=C_DIVIDER, layout_min_width=1, visible=visible)
    sep.props["AlignInContainer"] = "AlignInContainer.Center"
    return sep


def request_actions(prefix, new, save, submit, fix_expr=None, extra=()):
    """Headerens knapper i den faelles raekkefoelge:
    [new] | [extra...] [save] [submit]. new bliver diskret, submit primaer
    med taelleren. Returnerer listen til top_bar()."""
    ghost(new)
    submit.props.pop("Appearance", None)
    submit.props["BasePaletteColor"] = C_PRIMARY
    submit.props["Color"] = C_WHITE
    submit.props.pop("BorderColor", None)
    if fix_expr:
        with_fix_count(submit, fix_expr)
    sep = action_sep(f"con{prefix}HeadSep", visible=at_least("Tablet"))
    return [new, sep, *extra, save, submit]


def mark_done(btn, done_expr):
    """Den FAELLES "udfyldt"-tilstand for en outline-knap (issue #73).

    Item long text og Object list bruger den begge: naar der er noget,
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


# SEGMENTERET VALG (issue #141) - DEN ene stil for et valg mellem to (eller
# faa) muligheder, hvor begge skal kunne ses paa een gang. Hoejden er den,
# knapperne skal vaere (mindst 30, layout-regel 25) plus skinnens 2+2 px.
SEG_H = 34
SEG_PAD = 2
SEG_BTN_H = SEG_H - 2 * SEG_PAD
SEG_GAP = 2
SEG_SIZE = 13
# Alle segmenter er lige brede - bredden af den laengste tekst, appen
# bruger, plus fluebenet. Saa ser alle segmenterede felter ens ud.
SEG_TEXTS = ("None", "ZBOW", "No", "Yes")


def seg_button_width():
    return max(fit_button_width('"%s"' % t, size=SEG_SIZE, min_w=0) for t in SEG_TEXTS) + ICON_W


def segmented(name, options, display_mode=None, label=None, fit=False, compact=False):
    """Segmenteret kontrol: en pilleformet skinne med een knap pr. valg.

    options: liste af (suffix, tekst, on, onselect, tooltip) - tekst er en
    ren tekst ("Yes"), on et Power Fx-udtryk for "valgt", onselect det, et
    klik goer, og tooltip en Power Fx-tekst eller None.

    Det valgte segment er UDFYLDT (primaerfarven), har hvid, halvfed tekst,
    primaer kant OG et flueben foran teksten - saa det ikke kun er farven,
    der siger det. De andre er kant-loese outline-knapper med daempet tekst
    paa skinnens neutrale flade: synlige og klikbare, men uden samme vaegt.
    Hover, fokus og deaktiveret er ModernButtons egne, ens for alle
    segmenter. Knapperne er almindelige knapper, saa Tab/Enter/mellemrum
    virker, og hver har sin AccessibleLabel med "selected".

    fit=True: hvert segment er lige bredt som sin tekst (+ flueben) - til
    lange valg som "My requests" og "All requests"."""
    w_uni = seg_button_width()
    if compact:
        w_uni = max(fit_button_width('"%s"' % o[1], size=SEG_SIZE, min_w=0) for o in options) + ICON_W - 6
    kids = []
    widths = []
    for suffix, text, on, onselect, tooltip in options:
        w = (fit_button_width('"%s"' % text, size=SEG_SIZE, min_w=0) + ICON_W + 8) if fit else w_uni
        widths.append(w)
        acc = f'"{(label + ": ") if label else ""}{text}" & If({on}, ", selected", "")'
        b = button(f"{name}{suffix}", f'"{text}"', onselect, width=w, height=SEG_BTN_H,
                   display_mode=display_mode, accessible=acc, tooltip=tooltip)
        b.props["Appearance"] = f"If({on}, ButtonAppearance.Primary, ButtonAppearance.Outline)"
        b.props["BasePaletteColor"] = C_PRIMARY
        b.props["BorderColor"] = f"If({on}, {C_PRIMARY}, {C_TRANSPARENT})"
        b.props["BorderThickness"] = "1"
        b.props["Color"] = f"If({on}, {C_WHITE}, {C_MUTED})"
        b.props["FontWeight"] = f"If({on}, FontWeight.Semibold, FontWeight.Normal)"
        b.props["Icon"] = f'If({on}, "Checkmark", "")'
        b.props["Layout"] = f"If({on}, ButtonLayout.IconBefore, ButtonLayout.TextOnly)"
        b.props["Size"] = str(SEG_SIZE)
        b.props["LayoutMinWidth"] = str(w)
        b.props.update(lay.radius(SEG_BTN_H // 2))
        kids.append(b)
    gap = 0 if compact else SEG_GAP
    track_w = sum(widths) + (len(kids) - 1) * gap + 2 * SEG_PAD
    return group(name, kids, direction="Horizontal", gap=gap, width=track_w,
                 align_items="Center", fill=C_NEUTRAL_BG, border_color=C_CARD_BORDER,
                 radius=SEG_H // 2, pad=SEG_PAD, align_in_container="Start")


# FANER (issue #303, del af #161) - DEN moderne Tab list fra Microsoft
# Learn ("Tab List modern control in canvas apps"). Versionen er den, Learns
# YAML-eksempel skriver; check_layout regel 16t afviser enhver anden og
# enhver egenskab, Learn ikke dokumenterer for typen.
TABLIST_CONTROL = "ModernTabList@1.0.0"
# Hoejden er den samme som de linjer, fanerne staar i (36). Den indre luft
# er sat, saa teksten (20 px linje) og understregningen har plads - Fluents
# egen luft ville goere fanen hoejere end linjen.
TAB_H = 36
TAB_PAD_X = 10
TAB_PAD_Y = 4
TAB_SIZE = 13
# Fluents egen afstand mellem fanerne og om understregningen.
TAB_SLACK = 8


def tab_w(text, size=TAB_SIZE):
    """En fanes bredde: teksten (text_px er med vilje lidt for bred) + den
    indre luft i begge sider + Fluents egen afstand."""
    return text_px(text, size) + 2 * TAB_PAD_X + TAB_SLACK


def tabs_w(texts, size=TAB_SIZE):
    """Hele fanerækkens bredde."""
    return sum(tab_w(t, size) for t in texts)


def _fx_literals(fx):
    return re.findall(r'"([^"]*)"', fx)


def tab_list(name, var, tabs, *, label, width, tail="", size=TAB_SIZE, visible=None):
    """Een fanerække - ModernTabList - der laeser og saetter en VARIABEL.

    var:   variablen, fanerne afspejler (fx varIbScope). Den er stadig det,
           al filtrering laeser; fanerne er kun en ny maade at saette den.
    tabs:  liste af (noegle, tekst-udtryk) eller (noegle, tekst-udtryk,
           betingelse). noegle er variablens vaerdi ("mine"); tekst-udtryk
           er Power Fx, der giver fanens tekst - en litteral ('"My issues"')
           eller et If(), der vaelger en kort tekst paa en smal skaerm.
           betingelse (Power Fx) skjuler fanen, naar den er falsk (fx kun
           for admin).
    tail:  Power Fx, der koeres efter Set(var, ...) - fx hubbens
           genindlaesning og gem af filtrene.

    Items    fanernes tekster ([...], eller Filter([...], ...) med betingelser)
    Default  teksten for variablens vaerdi; ukendt eller tom -> foerste fane.
             Saa foelger fanerne med, naar variablen saettes andre steder
             (mobilens dropdown, hero-trinnet, OnStart).
    OnChange oversaetter den valgte tekst tilbage til noeglen - alle tekster,
             et tekst-udtryk kan give (lang og kort) - og saetter variablen
             KUN naar den faktisk skifter. En Default, der nulstiller fanen,
             goer derfor intet (ingen ekstra genindlaesning).

    Default er en POST ({Value: ...}) som Items' raekker - en ren tekst
    afviste compile ("Expected a value compatible with 'Items'", #331).
    Alignment og Appearance saettes IKKE: tenantens Tab list kender
    hverken TabListAlignment eller TabListAppearance.Underline (#331), saa
    Fluents standard tegner fanerne (streg under den valgte).
    Color er text-primary, saa teksten kan laeses
    i baade lys og moerk tilstand (appen saetter ikke Fluent-temaet, jf.
    regel 10c). Ingen TabIndex (Learn har ingen); fanerne er Fluents egne,
    saa Tab, piletaster og skaermlaeser virker."""
    texts, conds, mapping = [], [], []
    for t in tabs:
        key, fx = t[0], t[1]
        cond = t[2] if len(t) > 2 else None
        texts.append(fx)
        lits = _fx_literals(fx)
        assert lits, (name, fx)
        if cond:
            conds.append("(" + " && ".join(f'Value <> "{lit}"' for lit in lits) + f" || {cond})")
        mapping += [(lit, key) for lit in lits]
    items = "[" + ", ".join(texts) + "]"
    if conds:
        items = f"Filter({items}, " + " && ".join(conds) + ")"
    default = (f"Switch({var}, " + ", ".join(f'"{t[0]}", {t[1]}' for t in tabs)
               + f", {tabs[0][1]})")
    pick = ("Switch(Self.Selected.Value, "
            + ", ".join(f'"{lit}", "{key}"' for lit, key in mapping) + ', "")')
    on_change = (f"With({{ k: {pick} }},\n"
                 f"    If(!IsBlank(k) && k <> {var},\n"
                 f"        Set({var}, k)"
                 + (";\n        " + tail.replace("\n", "\n        ") if tail else "")
                 + "\n    )\n)")
    props = {
        "AccessibleLabel": f'"{label}"',
        "AlignInContainer": "AlignInContainer.Start",
        "Color": C_TITLE,
        "Default": "{Value: " + default + "}",
        "Font": FONT,
        "Height": str(TAB_H),
        "Items": items,
        "OnChange": on_change,
        "PaddingBottom": str(TAB_PAD_Y),
        "PaddingLeft": str(TAB_PAD_X),
        "PaddingRight": str(TAB_PAD_X),
        "PaddingTop": str(TAB_PAD_Y),
        "Size": str(size),
        "Width": str(width),
    }
    return Ctrl(name, TABLIST_CONTROL, props=props, h=TAB_H, vis=visible)


# Hjulet er den moderne Spinner-kontrol (issue #302, del af #161). Versionen
# er den, Microsoft Learns YAML-eksempel skriver; check_layout regel 16c
# afviser enhver anden - og ethvert animeret SVG-hjul i et Image.
SPINNER_CONTROL = "ModernSpinner@1.1.0"


def spinner(name, visible, accessible, *, width, height, label='""', below=False,
            size=None, weight=None):
    """Hjulet - EEN kontrol for hele repoet (issue #64, #302).

    Var et drejende SVG-billede (spinner_svg) i temaets farver. Nu den
    moderne Spinner fra Microsoft Learn. Kun dokumenterede egenskaber:

      BasePaletteColor  brandfarven (color-brand-primary) - den palet,
                        Fluent tegner hjulet med. Hjulets spor og praecise
                        nuance vaelger Fluent selv; dem kan vi ikke saette.
      Label/Color/Size  teksten ved hjulet i text-primary, som foer
      LabelPosition     SpinnerLabelPosition.Below, naar teksten skal staa
                        under hjulet (below=True); ellers Fluents standard
                        (After = til hoejre)

    Hjulets egen stoerrelse kan ikke saettes (Learn har ingen SpinnerSize);
    Width/Height er kontrollens plads, som foer billedets. Spinneren tager
    ikke input og har ingen TabIndex. Den forsinkede indtoning og
    prefers-reduced-motion fra SVG'en (issue #92) styrer Fluent nu selv."""
    props = {
        "AccessibleLabel": accessible,
        "BasePaletteColor": C_PRIMARY,
        "Color": C_TITLE,
        "Font": FONT,
        "Height": str(height),
        "Label": label,
        "Visible": visible,
        "Width": str(width),
    }
    if below:
        props["LabelPosition"] = "SpinnerLabelPosition.Below"
    if size:
        props["Size"] = str(size)
    if weight:
        props["FontWeight"] = f"FontWeight.{weight}"
    return Ctrl(name, SPINNER_CONTROL, props=props, h=height, vis=visible)


def error_svg(size=40, stroke=4):
    """Det stille modstykke til hjulet: en cirkel med et udraabstegn i
    fejlfarven, i hjulets plads - saa intet flytter sig, naar en
    indlaesning stopper med en fejl (issue #92). Et stillestaaende billede,
    ikke en spinner (regel 16c afviser kun animerede)."""
    hx = lambda n: '" & %s & "' % ref_hex_expr(n)
    c = size // 2
    r = c - stroke
    col = hx('state-error-fg')
    svg = ('"' + f"<svg xmlns='http://www.w3.org/2000/svg' width='{size}' height='{size}' "
           f"viewBox='0 0 {size} {size}'>"
           f"<circle cx='{c}' cy='{c}' r='{r}' fill='none' stroke-width='{stroke - 1}' "
           f"stroke='{col}'/>"
           f"<path d='M{c} {c - r // 2} V{c + 2}' stroke='{col}' stroke-width='{stroke}' "
           f"stroke-linecap='round'/>"
           f"<circle cx='{c}' cy='{c + r // 2 + 1}' r='{stroke // 2 + 1}' fill='{col}'/>"
           "</svg>" + '"')
    return f'"data:image/svg+xml;utf8," & EncodeUrl({svg})'


def stable_scrim(fill=C_OVERLAY):
    """Sloerets farve - ens i alle tilstande (issue #221).

    Et klassisk Image har sin egen HoverFill og PressedFill. Var de ikke
    sat, skiftede sloeret farve, naar musen gik fra popuppen ud paa sloeret
    (sloeret er "hovered" udenfor popuppen, ikke inde i den), og igen ved
    et tryk. Fokusrammen tegnede en kant rundt om hele skaermen, naar
    sloeret fik fokus ved et klik. Alle tre er nu den samme fyldfarve og
    en gennemsigtig fokusramme (App checker kraever tykkelse > 0), saa siden under er daempet ens, til popuppen lukker.

    Bruges af ALLE sloer med C_OVERLAY (tap_backdrop, loading_overlay,
    open_overlay). Popupper, hvis sloer er en container med popuppen
    indeni, har ingen hover-tilstand og er allerede stabile."""
    return {
        "Fill": fill,
        "FocusedBorderColor": C_TRANSPARENT,
        "FocusedBorderThickness": "2",
        "HoverFill": fill,
        "PressedFill": fill,
    }


def loading_overlay(name, busy_var, label="Saving, please wait", caption=None):
    """DEN ventespinner - ens i alle apps og alle skaerme (issue #54, #64).

    [sloer, hjul]: et sloer over hele skaermen i sloerets farve - saa ingen
    naar at trykke paa noget, mens der hentes eller gemmes - og den moderne
    Spinner (spinner, issue #302) midt paa. Begge synlige, saa laenge
    busy_var er sand. caption staar under hjulet.

    Sloeret er det samme Image som foer, nu uden billede (som
    open_overlay's sloer); hjulet hedder som sloeret med "spn" for "img".

    Bruges til BAADE gemning (appernes Save/Submit) og indlaesning (den
    samlede apps skaerme). Der var to kopier af den samme SVG - een her og
    een i BIO SAP App/build/build_screens.py - og skaermene fik oveni Power
    Apps' egen LoadingSpinner, saa der stod et hjul inden i hjulet. Nu er
    der een.

    Staar SIDST i skaermens boern: det, der staar senere, ligger oeverst."""
    vis = f"IfError({busy_var}, false)"
    scrim = Ctrl(name, "Image", props={
        "AccessibleLabel": f'"{label}"',
        "BorderStyle": "BorderStyle.None",
        "BorderThickness": "0",
        **stable_scrim(),
        "Height": "App.Height",
        "Image": '""',
        "TabIndex": "0",
        "Visible": vis,
        "Width": "App.Width",
        "X": "0",
        "Y": "0",
    }, h="App.Height", vis=vis)
    assert name.startswith("img"), name
    if caption:
        spin = spinner("spn" + name[3:], vis, f'"{label}"', width="Min(440, App.Width - 32)",
                       height=100, label=f'"{caption}"', below=True,
                       size=lay.SIZE_INPUT, weight="Semibold")
    else:
        spin = spinner("spn" + name[3:], vis, f'"{label}"', width=64, height=64)
    spin.props["X"] = "(App.Width - Self.Width) / 2"
    spin.props["Y"] = "(App.Height - Self.Height) / 2"
    return [scrim, spin]


def open_overlay(prefix, busy_var, failed_var, slow_var, *, title_fx, step_fx, hint_fx,
                 retry_fx, close_fx, label, slow_ms=6000, show_fx=None):
    """Indlaesningen af en anmodning - [sloer, kort, timer] (issue #92).

    Erstatter det store hjul med den faste billedtekst. Et lille, centreret
    kort paa sloeret:

        (hjul)                 eller (!) ved en fejl - samme plads
        Opening request        titlen
        Loading items ...      det trin, indlaesningen ER i lige nu
        Taking longer ...      kun naar det trin tager lang tid
        [Close] [Retry]        kun ved en fejl

    Hver linje har sin faste hoejde, og trinlinjen ombryder ikke - en ny
    tekst flytter derfor intet. Kun knapraekken kommer og gaar, og det er
    et skift af tilstand, ikke af tekst.

    INGEN PROCENT
    -------------
    Trinene er rigtige, men de varer vidt forskelligt, og et par af dem
    koster kun noget foerste gang i sessionen. En bjaelke, der hopper fra
    20 til 80 %, ville vaere en gaet fremdrift. Hjulet er ubestemt, og
    teksten siger, hvad der sker.

    TIMEREN ER KUN TIL "DET TAGER LANG TID"
    ---------------------------------------
    Den starter, naar busy_var bliver sand, og nulstilles, naar den bliver
    falsk. Naar den udloeber, saettes slow_var - og hint_fx viser en
    besked om det trin, der er i gang. Den skifter aldrig trinteksten.

    show_fx (issue #391): en betingelse, der ogsaa skal vaere sand, for at
    sloer og kort vises, mens der indlaeses. Uden den vises de hele tiden.
    En fejl viser altid kortet (Retry/Close)."""
    busy = f"IfError({busy_var}, false)"
    failed = f"IfError({failed_var}, false)"
    vis = f"{busy} || {failed}" if show_fx is None else f"({busy} && {show_fx}) || {failed}"
    scrim = Ctrl(f"img{prefix}Loading", "Image", props={
        "AccessibleLabel": f'"{label}"',
        "BorderStyle": "BorderStyle.None",
        "BorderThickness": "0",
        **stable_scrim(),
        "Height": "App.Height",
        "Image": '""',
        "TabIndex": "0",
        "Visible": vis,
        "Width": "App.Width",
        "X": "0",
        "Y": "0",
    }, h="App.Height", vis=vis)
    # Hjulet og fejlikonet har samme plads (40 x 40); kun een er synlig.
    spin = spinner(f"spn{prefix}LoadIcon", f"!{failed}", '"Loading"', width=40, height=40)
    spin.props["AlignInContainer"] = "AlignInContainer.Center"
    icon = Ctrl(f"img{prefix}LoadIcon", "Image", props={
        "AccessibleLabel": '"Error"',
        "AlignInContainer": "AlignInContainer.Center",
        "BorderStyle": "BorderStyle.None",
        "BorderThickness": "0",
        "Height": "40",
        "Image": error_svg(40, 4),
        "ImagePosition": "ImagePosition.Fit",
        "TabIndex": "0",
        "Visible": failed,
        "Width": "40",
    }, h=40, vis=failed)
    title = text_ctrl(f"txt{prefix}LoadTitle", title_fx, size=lay.SIZE_CARD_TITLE,
                      weight="Semibold", align="Center", height=26, wrap="false")
    step = text_ctrl(f"txt{prefix}LoadStep", step_fx, size=13, color=C_MUTED,
                     align="Center", height=20, wrap="false")
    hint = text_ctrl(f"txt{prefix}LoadHint", hint_fx, size=12, color=C_MUTED,
                     align="Center", height=34, wrap="true")
    close = button(f"btn{prefix}LoadClose", '"Close"', close_fx,
                   width=fit_button_width('"Close"'), height=36)
    retry = button(f"btn{prefix}LoadRetry", '"Retry"', retry_fx, primary=True,
                   width=fit_button_width('"Retry"'), height=36)
    actions = group(f"con{prefix}LoadActions", [close, retry], direction="Horizontal", gap=8,
                    height=36, justify="Center", align_items="Center", visible=failed)
    card = group(f"con{prefix}LoadCard", [spin, icon, title, step, hint, actions],
                 direction="Vertical", gap=6, fill=C_MODAL_BG, border_color=C_CARD_BORDER,
                 radius=lay.RADIUS_MODAL, pad=(22, 20, 18, 20),
                 width="Min(360, App.Width - 32)", drop_shadow="Bold", visible=vis)
    card.props["X"] = "(App.Width - Self.Width) / 2"
    card.props["Y"] = "(App.Height - Self.Height) / 2"
    timer = Ctrl(f"tmr{prefix}LoadSlow", "Timer", props={
        "AutoPause": "false",
        "AutoStart": "false",
        "Duration": str(slow_ms),
        "Height": "1",
        "OnTimerEnd": f"Set({slow_var}, true)",
        "Repeat": "false",
        "Reset": f"!{busy}",
        "Start": busy,
        "Visible": "false",
        "Width": "1",
    }, h=1, vis="false")
    return [scrim, card, timer]


def tap_backdrop(name, vis, close_fx, fill=C_OVERLAY):
    """Sloeret bag en popup. Paa mobil lukker et tryk udenfor popuppen den;
    sloeret daekker hele skaermen, saa siden under ikke kan trykkes paa. Er
    ventespinneren oppe, ligger den oven paa og tager trykket.

    TAB STOP DER, HVOR DEN LUKKER (issue #165). App checker kraever et tab
    stop paa ethvert Image (TabIndexShouldBeDefinedForInteractiveControl).
    Sloeret lukker kun under Tablet, saa det er et tab stop ("Close the
    dialog") netop dér - paa en bred skaerm ville Enter paa det intet goere.
    X oeverst i popuppen er den lukning, der virker overalt."""
    below = lay.below('Tablet')
    return Ctrl(name, "Image", props={
        "AccessibleLabel": '"Close the dialog"',
        "BorderStyle": "BorderStyle.None",
        "BorderThickness": "0",
        **stable_scrim(fill),
        "Height": "App.Height",
        "Image": '""',
        "OnSelect": f"If({below}, {close_fx})",
        "TabIndex": f"If({below}, 0, -1)",
        "Visible": vis,
        "Width": "App.Width",
        "X": "0",
        "Y": "0",
    }, h="App.Height", vis=vis)


def with_busy(busy_var, fx):
    """fx med ventespinneren taendt, mens den koerer."""
    return f"Set({busy_var}, true);\n{fx};\nSet({busy_var}, false)"


def confirm_modal(prefix, open_var, title, message, confirm_text, confirm_fx,
                  confirm_name, icon=ICON_SUBMIT, danger=None, act=None):
    """Bekraeftelsen foer Submit (issue #54) - [sloer, popup].

    Samme konstruktion som appernes andre popupper: en centreret container
    med sloer bag, titel med X, en linje tekst og handlingen. Submit-knappen
    aabner den (Set(open_var, true)); foerst "Submit" HER koerer
    indsendelsen. X lukker uden at goere noget (issue #343).

    danger: knappen sletter eller kasserer noget - roed kant og tekst i
    stedet for den blaa primaerknap (UX-review, screenshots 2026-10-13).
    Uden angivelse er en Delete-knap (icon="Delete") altid danger.

    act: (act_var, key) - handlingen koerer I popuppen (issue #420): den
    lukker ikke foerst, knappen siger fx "Deleting..." med hjulet ved
    siden af, og popuppen lukker, naar handlingen lykkes. Fejler den,
    bliver popuppen staaende med "Delete failed" ved knappen. confirm_fx
    skriver selv sit udfald (act_mark)."""
    if danger is None:
        danger = icon == "Delete"
    vis = f"IfError({open_var}, false)"
    close_fx = f"Set({open_var}, false)"
    run_fx = f"Set({open_var}, false);\n{confirm_fx}"
    if act:
        av, key = act
        # Lukket uden at lykkes: beskeden hoerer til denne popup.
        close_fx += f';\nIf(IfError({av} = "{key}:failed", false), Set({av}, ""))'
        run_fx = (act_fx(av, key, confirm_fx) + ";\n"
                  f'If(IfError({av} = "{key}:ok", false), Set({open_var}, false))')
    backdrop = tap_backdrop(f"con{prefix}ConfirmBackdrop", vis, close_fx)
    t = text_ctrl(f"txt{prefix}ConfirmTitle", f'"{title}"', size=lay.SIZE_CARD_TITLE, weight="Semibold",
                  height=26, wrap="false")
    # Nej'et er X oeverst til hoejre (issue #343), som i appens andre
    # popupper - det lukker uden at goere noget. Navnet er det gamle.
    head = popup_head(f"con{prefix}ConfirmHead", t, f"btn{prefix}ConfirmCancel", close_fx)
    msg = text_ctrl(f"txt{prefix}ConfirmText", message, size=13, color=C_MUTED,
                    height=40, wrap="true")
    ok = button(confirm_name, f'"{confirm_text}"',
                run_fx, primary=not danger, danger=danger,
                width=fit_button_width(f'"{confirm_text}"') + (ICON_W if icon else 0), height=36, icon=icon)
    status = []
    if act:
        act_button(ok, av, key)
        status = act_status(f"{prefix}ConfirmAct", av, (key,))
    footer = group(f"con{prefix}ConfirmFooter", [*status, ok], direction="Horizontal", gap=8,
                   height=36, justify="End", align_items="Center")
    modal = group(f"con{prefix}ConfirmModal", [head, msg, footer], direction="Vertical", gap=12,
                  fill=C_MODAL_BG, border_color=C_PRIMARY_SOFT, radius=lay.RADIUS_MODAL,
                  pad=(18, 18, 18, 18), width="Min(460, App.Width - 40)",
                  drop_shadow="ExtraBold", visible=vis)
    modal.props["X"] = "(App.Width - Self.Width) / 2"
    modal.props["Y"] = "Max(20, (App.Height - Self.Height) / 3)"
    return [backdrop, modal]


def close_x(name, close_fx, accessible=None, mode=None):
    """Popuppens luk: det samme X som sidepanelernes (btn...EditorClose,
    icon_button med icons.CLOSE) - stregikonet uden ramme, 44 x 44
    klikflade, samme hover og tryk (issue #343). Navnet er det gamle
    Close-knaps, saa intet andet skal rettes.

    accessible: skaermlaeserens tekst, naar "Close" ikke siger nok (fx
    "Close without applying"). Tooltip er altid "Close". mode: DisplayMode
    - X'et toner ud og kan ikke trykkes, mens popuppen er optaget."""
    close = icon_button(name, "Close", close_fx, _icons.CLOSE, mode)
    if accessible:
        close.props["AccessibleLabel"] = accessible
    close.props["AlignInContainer"] = "AlignInContainer.Start"
    close.props["LayoutMinWidth"] = close.props["Width"]
    return close


def popup_head(name, title, close_name, close_fx, accessible=None, mode=None, extra=(),
               gap=12):
    """Popuppens hoved: titlen til venstre og X oeverst til hoejre - samme
    X som sidepanelerne (issue #343; foer en Close-knap, issue #237).
    Hovedet er popuppens foerste barn og ligger uden for det, der scroller,
    saa X altid kan ses. Hoejden er X'ets klikflade (44), som
    sidepanelernes overskrift (icon_heading).

    extra: knapper mellem titlen og X (fx Previous/Next/Edit)."""
    grow(title)
    close = close_x(close_name, close_fx, accessible=accessible, mode=mode)
    return group(name, [title, *extra, close], direction="Horizontal", gap=gap,
                 height=lay.HIT_TOUCH, align_items="Center")


def capped_body(name, kids, max_h, gap=12):
    """Popuppens indhold: saa hoejt som indholdet, men aldrig hoejere end
    max_h. Foerst naar indholdet ikke kan vaere der, scroller det - og
    titlen og Close staar uden for, saa de bliver staaende."""
    body = group(name, kids, direction="Vertical", gap=gap, overflow_y="Scroll")
    body.props["Height"] = f"Min({body.h}, {max_h})"
    body.h = body.props["Height"]
    return body


def popup_body_max(fixed_h, margin=12, gap=12, pad=18):
    """Den hoejeste indholdsflade en popup kan have paa skaermen: skaermens
    hoejde minus luften over og under, polstringen og de faste dele (hoved,
    bund) med deres mellemrum. Tallet er til capped_body."""
    chrome = 2 * margin + 2 * pad + sum(fixed_h) + gap * len(fixed_h)
    return f"App.Height - {chrome}"


def text_modal(prefix, open_var, title_fx, body_fx, body_h):
    """Et laeseudsnit: titel med X oeverst til hoejre og broedtekst -
    [sloer, popup]. Ingen bund: Close sad der foer (issue #237)."""
    vis = f"IfError({open_var}, false)"
    backdrop = tap_backdrop(f"con{prefix}Backdrop", vis, f"Set({open_var}, false)")
    t = text_ctrl(f"txt{prefix}Title", title_fx, size=lay.SIZE_CARD_TITLE, weight="Semibold",
                  height=26, wrap="false")
    head = popup_head(f"con{prefix}Head", t, f"btn{prefix}Close", f"Set({open_var}, false)")
    body = text_ctrl(f"txt{prefix}Body", body_fx, size=13, height=body_h, wrap="true")
    modal = group(f"con{prefix}Modal", [head, body], direction="Vertical", gap=12,
                  fill=C_MODAL_BG, border_color=C_PRIMARY_SOFT, radius=lay.RADIUS_MODAL,
                  pad=(18, 18, 18, 18), width="Min(460, App.Width - 24)",
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
    img = Ctrl(name, "Image", props=props, h=THEME_TOGGLE_H)
    # Klikfladen (F6): knoppen i den lukkede skinne er 36 px - fladen 44
    # under Desktop. Pillen i panelet er bred nok i forvejen.
    return ensure_hit(img) if compact else img


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
    img = Ctrl(name, "Image", props=props, h=THEME_TOGGLE_H)
    return ensure_hit(img) if compact else img


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


def fit(ctrl, natural_w, reserve=None):
    """Kontrollen er saa bred som sit indhold (natural_w) - men aldrig
    bredere end pladsen inden i foraelderen minus reserve.

    Ligesom grow en MARKERING: gen_screen._resolve_fit regner bredden ud,
    naar skaermen skrives, ud fra foraelderens udregnede bredde - ikke
    Parent.Width (check_layout regel 24). Er der plads, staar hele teksten;
    kun naar foraelderen reelt er for smal, klipper den (issue #93)."""
    ctrl._fit = (natural_w, reserve)
    ctrl.props["Width"] = str(natural_w)
    ctrl.props["LayoutMinWidth"] = "0"
    return ctrl


def flow_row(name, children, container_w, gap=8, flex=None, flex_min=0,
             ok=None, **group_kw):
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

    ok kan gives udefra, naar raekken selv krymper sine boern, saa den
    altid passer (hubbens filterlinje, issue #91) - saa er graensen en
    tier og ikke en sum. gap maa da ogsaa vaere et udtryk.
    """
    if ok is None:
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
        gs = str(g) if isinstance(g, int) else "(%s)" % g
        if c.vis:
            parts.append("If(%s, %s + (%s), 0)" % (c.vis, gs, hs[i]))
        else:
            parts.append("%s + (%s)" % (gs, hs[i]) if g else "(%s)" % hs[i])
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


# Pynt- og statusikoner er den moderne Icon-kontrol (issue #306, del af
# #161). Versionen er den, Microsoft Learns YAML-eksempler skriver;
# check_layout regel 16i afviser enhver anden og ukendte egenskaber.
ICON_CONTROL = "ModernIcon@1.1.0"


def fluent(key):
    """Fluent-navnet (som Power Fx-tekst) for en noegle i icons.FLUENT.
    KeyError, hvis ikonet ikke har et sidestykke dér - et domaeneikon skal
    blive et Image (docs/38)."""
    return '"%s"' % _icons.FLUENT[key]


def fluent_icon(name, icon_fx, color, accessible, *, size=20, visible=None):
    """Et Fluent-ikon som pynt eller status - EEN kontrol for hele repoet.

    icon_fx: Power Fx-tekst med Fluent-navnet (fluent(...) eller en
    Switch/If af dem). color: tokenfarven (C...), som billedet havde.
    Ingen OnSelect: uden den er ikonet pynt, ikke en knap, og naas ikke med
    tastaturet (Learn). TabIndex findes ikke paa kontrollen. Stregtegning
    som foer = IconStyle.Outline. Width/Height som billedets."""
    assert name.startswith("ico"), name
    props = {
        "AccessibleLabel": accessible,
        "Height": str(size),
        "Icon": icon_fx,
        "IconColor": color,
        "IconStyle": "IconStyle.Outline",
        "Width": str(size),
    }
    if visible is not None:
        props["Visible"] = visible
    return Ctrl(name, ICON_CONTROL, props=props, h=size, vis=visible)


PAGE_ICON = 32


def page_icon(name, key, size=PAGE_ICON):
    """Domaenets ikon til sideoverskriften (issue #74) - det SAMME ikon som i
    sidebaren og paa hubbens flise (tools/icons.py), i domaenets farve, i
    en svagt tonet firkant.

    Etiketten er sidens navn (sidebarens tekst for noeglen): Studios App
    checker godtager ikke en tom etiket paa et billede (AccessibleLabelNeeded,
    issue #165), og det er netop det, ikonet viser."""
    import icons
    import env_config as env
    page = (env.APPS.get(key) or {}).get("nav_label") or key
    color = '" & %s & "' % ref_hex_expr(icons.token(key))
    inner = icons.stroke_svg(key, color, size=20,
                             hx=lambda tk: '" & %s & "' % ref_hex_expr(tk))
    pad = (size - 20) / 2
    svg = ("<svg xmlns='http://www.w3.org/2000/svg' width='%d' height='%d' "
           "viewBox='0 0 %d %d'><rect width='%d' height='%d' rx='8' fill='%s' "
           "fill-opacity='0.12'/><g transform='translate(%g %g)'>%s</g></svg>"
           % (size, size, size, size, size, size, color, pad, pad, inner))
    return Ctrl(name, "Image", props={
        "AccessibleLabel": f'"{page}"',
        "BorderStyle": "BorderStyle.None",
        "BorderThickness": "0",
        "Height": str(size),
        "Image": f'"data:image/svg+xml;utf8," & EncodeUrl("{svg}")',
        "ImagePosition": "ImagePosition.Fit",
        "OnSelect": "false",
        "TabIndex": "0",
        "Width": str(size),
    }, h=size)


# ---------------------------------------------------------------------------
# TOM TILSTAND - IKON, EEN SAETNING, EEN KNAP (UX-review F4/T9)
#
# "No requests match the filters." og en tom tabel med kun overskrifter
# fortalte, hvad der manglede, men ikke hvad man goer. Nu er det et fast
# moenster: et tonet ikon, een saetning og (hoejst) een knap.
# ---------------------------------------------------------------------------
EMPTY_ICON = 40
EMPTY_TEXT_H = 40


# ---------------------------------------------------------------------------
# HVAD MANGLER, OG HVOR (UX-review 2026-10, M4)
#
# Submit sagde "N to fix", men ikke HVILKE. validation_summary er een liste
# med en linje pr. ting, der mangler, og en knap, der gaar derhen ("Open
# row", "Go to items"). SetFocus kan ikke naa ind i en container (regel
# 10b), saa "derhen" er at aabne raekken/afsnittet - ikke et felt.
#
# Listen staar kun, naar brugeren har bedt om noget (Submit) og der faktisk
# mangler noget - aldrig mens der skrives (designsystemets regel).
# ---------------------------------------------------------------------------
FIX_ROW_H = 40
FIX_ROWS_MAX = 5


def validation_summary(prefix, items, label_expr, go_text, go_fx, title_fx, visible,
                       close_fx, closable=True):
    """Kortet med det, der mangler.

    items: Power Fx-tabel (een raekke pr. ting). label_expr: raekkens tekst
    (ThisItem...). go_text/go_fx: knappen pr. raekke. title_fx: overskrift
    (fx "2 rows to fix before you submit"). visible: hvornaar kortet staar.
    close_fx: Dismiss. Galleriet viser hoejst FIX_ROWS_MAX raekker og
    scroller derefter."""
    from gen_screen import C_WARN_BG, C_WARN_FG
    title = grow(text_ctrl(f"txt{prefix}FixTitle", title_fx, size=lay.SIZE_BODY,
                           weight="Semibold", color=C_WARN_FG, height=20, wrap="false"))
    close = button(f"btn{prefix}FixClose", '"Dismiss"', close_fx, icon="Dismiss",
                   width=40, height=32, accessible='"Hide the list of things to fix"',
                   tooltip='"Hide"')
    close.props["Layout"] = "ButtonLayout.IconOnly"
    close.props["BorderColor"] = C_TRANSPARENT
    close.props["LayoutMinWidth"] = "40"
    ensure_hit(close)
    head = group(f"con{prefix}FixHead", [title, close] if closable else [title],
                 direction="Horizontal", gap=8,
                 height=hit_size(32) if closable else 24, align_items="Center")
    go_w = fit_button_width(f'"{go_text}"', size=lay.SIZE_SMALL)
    go = button(f"btn{prefix}FixGo", f'"{go_text}"', go_fx, width=go_w, height=32,
                accessible=f'"{go_text}: " & {label_expr}')
    go.props["Size"] = str(lay.SIZE_SMALL)
    go.props["X"] = "Parent.TemplateWidth - Self.Width - 8"
    go.props["Y"] = f"({FIX_ROW_H} - Self.Height) / 2"
    go.props["_OnTop"] = "true"
    txt = text_ctrl(f"txt{prefix}FixItem", label_expr, size=lay.SIZE_BODY, height=20,
                    wrap="false", width=f"Parent.TemplateWidth - {go_w + 28}",
                    accessible=label_expr)
    txt.props["X"] = "8"
    txt.props["Y"] = f"{(FIX_ROW_H - 20) // 2}"
    gal_h = f"Min(CountRows({items}), {FIX_ROWS_MAX}) * {FIX_ROW_H}"
    gal = Ctrl(f"gal{prefix}Fix", "Gallery", variant="Vertical", props={
        "AccessibleLabel": title_fx,
        "BorderStyle": "BorderStyle.None",
        "Fill": C_TRANSPARENT,
        "FillPortions": "0",
        "Height": gal_h,
        "Items": items,
        "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None",
        "Selectable": "false",
        "ShowScrollbar": f"CountRows({items}) > {FIX_ROWS_MAX}",
        "TabIndex": "0",
        "TemplatePadding": "0",
        "TemplateSize": str(FIX_ROW_H),
        "Width": "Parent.Width",
        "WrapCount": "1",
    }, children=[txt, go], h=gal_h)
    return group(f"con{prefix}Fix", [head, gal], direction="Vertical", gap=4,
                 fill=C_WARN_BG, radius=lay.RADIUS_INPUT, pad=(8, 12, 8, 12),
                 visible=visible)


# ---------------------------------------------------------------------------
# PLADSHOLDER-RAEKKER MENS LISTEN HENTES (UX-review 2026-10, M7)
#
# Et hjul midt paa skaermen (loading_overlay) siger "vent", men ikke HVAD der
# kommer, og det daekker alt andet. En liste, der hentes, viser i stedet
# graa raekker i listens egen form: skaermen staar stille, og indholdet
# glider ind dér, hvor pladsholderne stod. Bjaelkerne er containere (ikke
# figurer), saa de hverken er tab-stop eller kraever en etiket (regel 37/38);
# skaermlaeseren faar een tekst: "Loading ...".
# ---------------------------------------------------------------------------
SKELETON_ROWS = 5
SKELETON_ROW_H = 44
SKELETON_SHORT_W = 160


def skeleton_rows(name, visible, rows=SKELETON_ROWS, row_h=SKELETON_ROW_H,
                  label="Loading, please wait", width="Parent.Width"):
    """rows graa raekker a row_h px: een lang og een kort bjaelke pr. raekke.
    name: con...; visible: Power Fx (fx varIbLoading)."""
    base = name[3:] if name.startswith("con") else name
    say = text_ctrl(f"txt{base}Say", f'"{label}"', size=lay.SIZE_SMALL, color=C_MUTED,
                    height=18, wrap="false")
    kids = [say]
    bar_h = 10
    gap = row_h - 2 * bar_h - 8
    for i in range(rows):
        long_ = group(f"con{base}Bar{i}A", [], direction="Horizontal", height=bar_h,
                      fill=C_MUTED_BG, radius=bar_h // 2)
        short = group(f"con{base}Bar{i}B", [], direction="Horizontal", height=bar_h,
                      width=str(SKELETON_SHORT_W), fill=C_MUTED_BG, radius=bar_h // 2)
        # Raekken straekker den lange bjaelke; den korte staar til venstre.
        short.props["AlignInContainer"] = "AlignInContainer.Start"
        kids.append(group(f"con{base}Row{i}", [long_, short], direction="Vertical",
                          gap=gap, align_items="Stretch", pad=(4, 0, 4, 0)))
    return group(name, kids, direction="Vertical", gap=0, width=width, visible=visible,
                 pad=(4, 0, 4, 0))


def empty_state(name, text, action_text=None, action_fx=None, icon_key=None,
                icon_path=None, visible=None, width=None, primary=True,
                button_name=None, action_icon=None, action_visible=None):
    """[ikon, tekst, knap] centreret i en lodret gruppe.

    name: gruppens navn (con...). icon_key: en noegle i tools/icons.DOMAIN
    (domaenets ikon i domaenets farve) - ellers icon_path i text-muted.
    text: Power Fx-tekst. action_text/action_fx: knappen (udelades uden)."""
    import icons
    if icon_key:
        tok = icons.token(icon_key)
        inner = icons.stroke_svg(icon_key, '" & %s & "' % ref_hex_expr(tok), size=20,
                                 hx=lambda t: '" & %s & "' % ref_hex_expr(t))
        color = '" & %s & "' % ref_hex_expr(tok)
    else:
        color = '" & %s & "' % ref_hex_expr("text-muted")
        inner = icons.glyph(icon_path or icons.LIST, color, size=20)
    pad = (EMPTY_ICON - 20) / 2
    svg = ("<svg xmlns='http://www.w3.org/2000/svg' width='%d' height='%d' "
           "viewBox='0 0 %d %d'><rect width='%d' height='%d' rx='10' fill='%s' "
           "fill-opacity='0.12'/><g transform='translate(%g %g)'>%s</g></svg>"
           % (EMPTY_ICON, EMPTY_ICON, EMPTY_ICON, EMPTY_ICON, EMPTY_ICON, EMPTY_ICON,
              color, pad, pad, inner))
    base = name[3:] if name.startswith("con") else name
    img = Ctrl(f"img{base}Icon", "Image", props={
        "AccessibleLabel": '"Empty list"',
        "AlignInContainer": "AlignInContainer.Center",
        "BorderStyle": "BorderStyle.None",
        "BorderThickness": "0",
        "Height": str(EMPTY_ICON),
        "Image": f'"data:image/svg+xml;utf8," & EncodeUrl("{svg}")',
        "ImagePosition": "ImagePosition.Fit",
        "OnSelect": "false",
        "TabIndex": "0",
        "Width": str(EMPTY_ICON),
    }, h=EMPTY_ICON)
    msg = text_ctrl(f"txt{base}Text", text, size=lay.SIZE_BODY, color=C_MUTED,
                    align="Center", height=EMPTY_TEXT_H, wrap="true",
                    extra={"VerticalAlign": "VerticalAlign.Middle"})
    # Teksten faar hele gruppens bredde (Stretch). Med gruppens Center fik
    # den sin egen smalle standardbredde, ombroed og blev klippet med en
    # rullepil (Measuring points, screenshots 2026-10-13).
    msg.props["AlignInContainer"] = "AlignInContainer.Stretch"
    kids = [img, msg]
    if action_text:
        w = fit_button_width(f'"{action_text}"') + (ICON_W if action_icon else 0)
        b = button(button_name or f"btn{base}Action", f'"{action_text}"', action_fx,
                   primary=primary, width=w, height=36, icon=action_icon,
                   visible=action_visible)
        b.props["LayoutMinWidth"] = str(w)
        kids.append(b)
    return group(name, kids, direction="Vertical", gap=8, align_items="Center",
                 pad=(12, 0, 12, 0), width=width, visible=visible)


DELETE_W = 40


def edit_button(name, view_var, can_var, onselect, what="request", tooltip=None):
    """Edit for the open request - VH-planens knap, nu faelles (issue #94).

    Vises kun i View mode og kun, naar brugeren maa aendre anmodningen
    (can_var er sat af tools/permissions.may_change ved indlaesningen:
    ejer i Kladde, admin i Kladde og AfventerInfo). Er anmodningen indsendt
    eller laast, er can_var falsk, og knappen staar der ikke. Under Tablet
    er den kun sit ikon, som Delete ved siden af."""
    b = button(name, '"Edit"', onselect, width=fit_button_width('"Edit"') + ICON_W, height=36,
               icon="Edit", visible=f"IfError({view_var} && {can_var}, false)",
               accessible=f'"Edit this {what}"', tooltip=tooltip)
    return icon_on_mobile(b)


def delete_button(prefix, view_var, guid_var, what="request"):
    """Icon-only Delete for the open request, shown in edit mode only."""
    b = button(f"btn{prefix}DeleteRequest", '"Delete"', f"Set(var{prefix}DeleteOpen, true)",
               width=fit_button_width('"Delete"') + ICON_W, height=36, icon="Delete", danger=True,
               visible=f"!IfError({view_var}, true) && !IsBlank({guid_var})",
               accessible=f'"Delete this {what}"', tooltip=f'"Delete this draft {what}"')
    return icon_on_mobile(b, DELETE_W)


def delete_modal(prefix, guid_var, index_list, domain, what="request"):
    """Delete request paa domaeneskaermen - tools/request_delete.py, den samme
    sletning som hubbens: kildedata foerst, indeksraekken sidst, og succes
    kun naar alt er slettet. Her stod Remove af indeksraekken alene.

    Efter sletningen glemmer skaermen anmodningen helt (want, opened og
    gbl<X>Stale), saa naeste besoeg starter en ny, tom anmodning og henter
    listen igen - ellers kunne et gem oprette indeksraekken paa ny."""
    import side_nav
    import request_delete as rd
    idx = f"var{prefix}DelIdx"
    success = (f'Set({guid_var}, "");\n'
               f"Set({rd.stale_var(prefix)}, true);\n"
               f"Set(gbl{prefix}Want, Blank());\n"
               f'Set(var{prefix}Opened, "");\n'
               'Notify("Request deleted.", NotificationType.Success);\n'
               f"{side_nav._launch('hub')}")
    fx = (f"Set({idx}, LookUp({index_list}, RequestGuid = {guid_var}));\n"
          "If(\n"
          f"    IsBlank({idx}),\n    {rd.GONE},\n"
          f"    !{rd.may_delete(idx, f'var{prefix}Me')},\n    {rd.DENIED},\n"
          + rd.delete_fx(prefix, [domain], success, f"var{prefix}Me", indent=4) + "\n)")
    return confirm_modal(f"{prefix}ReqDel", f"var{prefix}DeleteOpen", "Delete request",
                         f'"Delete this {what}? This cannot be undone."',
                         "Delete", fx, f"btn{prefix}ReqDelConfirm", icon="Delete")


def mode_badge(prefix, var):
    """Pille efter sidetitlen: View mode eller Edit mode (kun fra Tablet og op)."""
    view = f"IfError({var}, false)"
    fill = f'If({view}, {ref_hex_expr("state-info-bg")}, {ref_hex_expr("state-neutral-bg")})'
    fg = f'If({view}, {ref_hex_expr("state-info-fg")}, {ref_hex_expr("state-warn-fg")})'
    # Ikonet foran teksten (issue #139): et oeje i View, blyanten i Edit -
    # tilstanden kan ses paa formen, ikke kun paa farven. Prikken foer var
    # den samme i begge.
    import icons
    glyph = ('" & If(' + view + ', "' + icons.glyph(icons.EYE, "#", size=14, x=8, y=6).replace("'#'", "'\" & " + fg + " & \"'")
             + '", "' + icons.glyph(icons.EDIT, "#", size=14, x=8, y=6).replace("'#'", "'\" & " + fg + " & \"'")
             + '") & "')
    svg = ('"data:image/svg+xml;utf8," & EncodeUrl("<svg xmlns=\'http://www.w3.org/2000/svg\' width=\'104\' '
           'height=\'26\' viewBox=\'0 0 104 26\'><rect width=\'104\' height=\'26\' rx=\'13\' fill=\'" & ' + fill +
           ' & "\'/>' + glyph + '<text x=\'26\' y=\'17.5\' font-family=\'Segoe UI, sans-serif\' font-size=\'12\' '
           'font-weight=\'600\' fill=\'" & ' + fg + ' & "\'>" & If(' + view +
           ', "View mode", "Edit mode") & "</text></svg>")')
    img = Ctrl(f"img{prefix}Mode", "Image", props={
        "AccessibleLabel": f'If({view}, "View mode - fields are locked", "Edit mode")',
        "AlignInContainer": "AlignInContainer.Center",
        "BorderStyle": "BorderStyle.None", "BorderThickness": "0", "Height": "26",
        "Image": f'If(IfError({var.replace("ViewOnly", "BadgeOn")}, false), {svg}, "")', "ImagePosition": "ImagePosition.Fit", "LayoutMinWidth": "104",
        "OnSelect": "false", "TabIndex": "0", "Width": "104",
    }, h=26)
    return img


def number_badge(prefix, var, key):
    """Pill with the plan/request number (e.g. MP0142) in the page icon's colour; hidden until there is one.

    Var et 88 x 26 Image med en SVG-pille (tekst i ikonets farve paa en
    12 % tone af den). Nu en ModernBadge (#304) med samme maal og farver:
    teksten i farven, fyldet den samme farve med alfa 1F (= 12 %) - som
    8-cifret hex til ColorValue (Power Fx: "#rrggbbaa")."""
    import icons
    col = ref_hex_expr(icons.token(key))
    vis = f"!IsBlank({var})"
    b = modern_badge(f"bdg{prefix}Number", var, color=f"ColorValue({col})",
                     fill=f'ColorValue({col} & "1F")', width=88, height=26,
                     size=lay.SIZE_SMALL, accessible=f'"Number " & {var}', visible=vis,
                     extra={"AlignInContainer": "AlignInContainer.Start",
                            "LayoutMinWidth": "88"})
    return b


# ---------------------------------------------------------------------------
# BROEDKRUMMEN (UX-review F9)
#
#     Masterdata Hub / Equipments / EQ-000032
#
# Over titlen paa alle domaeneskaerme. Foerste led gaar tilbage til hubben
# - og hubbens filtre staar, som man forlod dem (de er variabler i samme
# session og gemt i SaveData, F8). Leddet er et Image med teksten tegnet i
# brandfarven: det har OnSelect, hover, fokus og TabIndex og er bevist i
# dette miljoe; en knap skal vaere mindst 30 px hoej (regel 25).
# ---------------------------------------------------------------------------
CRUMB_H = 18
CRUMB_SIZE = 12
HUB_LABEL = "Masterdata Hub"


def breadcrumb(prefix, app_key, id_expr=None):
    """[Masterdata Hub] / <skaermens navn>. id_expr bruges ikke laengere:
    nummeret staar i pillen ved titlen."""
    import side_nav
    import env_config as env
    page = (env.APPS.get(app_key) or {}).get("nav_label") or app_key
    w = label_px(HUB_LABEL, CRUMB_SIZE) + 4
    col = '" & %s & "' % ref_hex_expr("color-brand-primary")
    svg = ("<svg xmlns='http://www.w3.org/2000/svg' width='%d' height='%d' viewBox='0 0 %d %d'>"
           "<text x='0' y='13' font-family='Segoe UI, sans-serif' font-size='%d' "
           "font-weight='600' fill='%s'>%s</text></svg>"
           % (w, CRUMB_H, w, CRUMB_H, CRUMB_SIZE, col, HUB_LABEL))
    hub = Ctrl(f"img{prefix}CrumbHub", "Image", props={
        "AccessibleLabel": f'"Back to {HUB_LABEL}"',
        "AlignInContainer": "AlignInContainer.Center",
        "BorderStyle": "BorderStyle.None",
        "BorderThickness": "0",
        "Fill": C_TRANSPARENT,
        "FocusedBorderColor": C_PRIMARY,
        "FocusedBorderThickness": "2",
        "Height": str(CRUMB_H),
        "HoverFill": C_ROW_HOVER,
        "Image": f'"data:image/svg+xml;utf8," & EncodeUrl("{svg}")',
        "ImagePosition": "ImagePosition.Fit",
        "LayoutMinWidth": str(w),
        "OnSelect": side_nav._launch("hub"),
        "PressedFill": C_ROW_PRESSED,
        "TabIndex": "0",
        "Tooltip": f'"Back to {HUB_LABEL} - your filters are kept"',
        "Width": str(w),
    }, h=CRUMB_H)
    # Nummeret staar kun i pillen ved titlen - ikke ogsaa her.
    rest = f'"  /  {page}"'
    tail = grow(text_ctrl(f"txt{prefix}Crumb", rest, size=CRUMB_SIZE, color=C_MUTED,
                          height=CRUMB_H, wrap="false"))
    return group(f"con{prefix}Crumb", [hub, tail], direction="Horizontal", gap=0,
                 height=CRUMB_H, align_items="Center")


def top_bar(prefix, title, subtitle, actions, container_w=None, gap=10,
            narrow_hide=(), sub=None, icon=None, mode_var=None, num_var=None,
            crumb=None):
    """Bjaelken oeverst - den SAMME konstruktion i alle apps.

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
    t = text_ctrl("txt%sTitle" % prefix, title, size=lay.SIZE_PAGE_TITLE, weight="Semibold",
                  height=30, wrap="false")
    t.vis = at_least("Tablet")
    crumbs = []
    if crumb is not None:
        # Broedkrummen (F9) over titlen - kun fra Tablet, som titlen.
        crumb.vis = at_least("Tablet")
        crumb.props["Visible"] = crumb.vis
        crumbs = [crumb]
    if sub is None:
        sub = [text_ctrl("txt%sSub" % prefix, subtitle, size=13, color=C_MUTED,
                         height=20, wrap="false", visible=at_least("Tablet"))]
    extra = []
    first = t
    if num_var and icon:
        nb = number_badge(prefix, num_var, icon)
        nb.props["AlignInContainer"] = "AlignInContainer.Center"
        # TITLEN FAAR SIN FULDE BREDDE - OG KUN MINDRE, NAAR DER IKKE ER PLADS
        #
        # Her stod text_px(...) * 0.86 + 2 som FAST bredde paa baade titlen
        # og linjen. Skoennet ganget med 0.86 ramte under tekstens egen
        # bredde: "Equipment" fik 106 px, men er ca. 111 px i Segoe UI
        # Semibold 22 - og blev til "Equipme..." paa enhver skaerm, uanset
        # hvor meget plads bjaelken havde (issue #93). Nu maales titlen med
        # fontens egne tegnbredder (label_px, samme tabel som labels), og
        # bredden er et loft: Min(teksten, pladsen i linjen). Saa staar hele
        # titlen, naar der er plads, og kun naar bjaelken reelt er for smal,
        # klipper den med "...". Nummer-pillen (88 px + 6 px luft) tager
        # kun plads fra titlen, naar der ER et nummer.
        tw = label_px(title.strip()[1:-1], lay.SIZE_PAGE_TITLE) + 2
        fit(t, tw, reserve="If(IsBlank(%s), 0, 6 + 88)" % num_var)
        first = fit(group("con%sTitleLine" % prefix, [t, nb], direction="Horizontal", gap=6,
                          height=33, align_items="Center"), tw + 6 + 88)
        first.props["AlignInContainer"] = "AlignInContainer.Start"
        first.vis = at_least("Tablet")
        first.props["Visible"] = first.vis
    if mode_var:
        mb = mode_badge(prefix, mode_var)
        mb.props["AlignInContainer"] = "AlignInContainer.Start"
        mb.vis = at_least("Tablet")
        extra = [mb]
    left = grow(group("con%sBarLeft" % prefix, crumbs + [first] + list(sub) + extra,
                      direction="Vertical", gap=2))
    lead = []
    if icon:
        # icon: noeglen i tools/icons.DOMAIN - appens eget domaeneikon.
        ic = page_icon("img%sTitleIcon" % prefix, icon)
        ic.props["AlignInContainer"] = "AlignInContainer.Center"
        ic.props["LayoutMinWidth"] = str(PAGE_ICON)
        ic.vis = at_least("Tablet")
        lead = [ic]
    for a in actions:
        a.props["AlignInContainer"] = "AlignInContainer.Center"
        a.props["LayoutMinWidth"] = str(a.props["Width"])
        if a.name in narrow_hide:
            a.vis = at_least("Tablet")
    return group("con%sBar" % prefix, lead + [left] + list(actions), direction="Horizontal",
                 gap=gap, align_items="Center")


# FAST BUNDBJAELKE UNDER DESKTOP (UX-review 2026-10, M8)
#
# Paa en tablet og en telefon er headerens knapper smaa (kun ikoner) og
# langt fra tommelfingeren. Under Desktop staar anmodningens primaere
# handlinger - Save draft og Submit - i en fast bjaelke nederst paa
# skaermen, og de samme knapper i headeren skjules dér. Knapperne i
# bjaelken er KOPIER (samme OnSelect, DisplayMode, tekst og tooltip), saa
# reglen for, hvornaar de kan bruges, staar eet sted.
FOOT_H = lay.HIT_TOUCH + 16


def sticky_actions(prefix, buttons, status=()):
    """Bundbjaelken con<X>Foot med kopier af buttons (header-knapperne).
    Originalerne skjules under Desktop. Returnerer bjaelken til app_frame.

    status: knappernes hjul og besked (act_status, issue #420) - staar
    foran kopierne, som i headeren, og tager kun plads, mens de ses."""
    on = below("Desktop")
    copies = []
    for b in buttons:
        tail = b.name[3 + len(prefix):] if b.name.startswith("btn" + prefix) else b.name[3:]
        c = Ctrl(f"btn{prefix}Foot{tail}", b.control, variant=b.variant, props=dict(b.props),
                 h=lay.HIT_TOUCH)
        for k in ("Layout", "LayoutMinWidth", "AlignInContainer", "X", "Y"):
            c.props.pop(k, None)
        if c.props.get("Icon"):
            c.props["Layout"] = "ButtonLayout.IconBefore"
        c.props["Height"] = str(lay.HIT_TOUCH)
        c.props.pop("Visible", None)
        if b.props.get("Visible"):
            c.props["Visible"] = b.props["Visible"]
            c.vis = c.props["Visible"]
        copies.append(c)
        v = b.props.get("Visible")
        b.props["Visible"] = at_least("Desktop") if not v else f"{at_least('Desktop')} && ({v})"
        b.vis = b.props["Visible"]
    # SHELL_W: rammens indholdsbredde (aldrig Parent.Width, regel 24).
    inner_w = f"({SHELL_W})"
    row = button_row(f"con{prefix}FootRow", copies, inner_w, gap=8, height=lay.HIT_TOUCH,
                     lead=status)
    return group(f"con{prefix}Foot", [row], direction="Vertical", gap=0, height=FOOT_H,
                 fill=C_CARD_BG, pad=(8, lay.PAGE_PAD_R, 8, lay.PAGE_PAD_L), visible=on)


def app_frame(prefix, header, body, body_gap=16, body_pad_b=None, footer=None):
    """Rammen om hele skaermen - den SAMME i alle apps.

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
    foot_h = "" if footer is None else f" - If({footer.props['Visible']}, {FOOT_H}, 0)"
    main = group("con%sBody" % prefix, body, direction="Vertical", gap=body_gap,
                 height="Parent.Height - (%s)%s" % (head.h, foot_h), fill_portions=1,
                 overflow_y="Scroll", fill=C_APP_BG,
                 pad=(lay.BODY_PAD_T, lay.PAGE_PAD_R, pb, lay.PAGE_PAD_L))
    # Sidebaren (tools/side_nav.py) staar til venstre. Rammen starter
    # efter dens LUKKEDE bredde; aabnet ligger den oven paa rammen. Paa
    # mobil er skinnen skjult, og rammen starter under topbjaelken i stedet
    # (issue #65) - udtrykkene staar i tools/layout_tokens.py.
    root = group("con%sRoot" % prefix, [head, main] + ([footer] if footer is not None else []),
                 direction="Vertical", gap=0,
                 height=lay.ROOT_H, width=lay.ROOT_W, fill=C_APP_BG)
    root.props["X"] = lay.ROOT_X
    root.props["Y"] = lay.ROOT_Y
    return root


def row_list(prefix, items, row_controls, height, template_size, onselect="false",
             width="Parent.Width", visible=None, accessible="Request rows"):
    """Et vaelgbart galleri med en fast raekkeskaabelon.

    row_controls skal vaere galleriets direkte boern; containere i et
    galleri flades ikke ud her og afvises af layout-tjekket.
    """
    props = {
        "AccessibleLabel": f'"{accessible}"',
        "BorderStyle": "BorderStyle.None",
        "Fill": C_TRANSPARENT,
        "FillPortions": "0",
        "Height": str(height),
        "Items": items,
        "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None",
        "OnSelect": onselect,
        "Selectable": "true",
        "ShowScrollbar": "false",
        "TabIndex": "0",
        "TemplatePadding": "2",
        "TemplateSize": str(template_size),
        "Width": str(width),
        "WrapCount": "1",
    }
    if visible is not None:
        props["Visible"] = visible
    return Ctrl(f"gal{prefix}Rows", "Gallery", variant="Vertical", props=props,
                children=row_controls, h=height, vis=visible)


def icon_heading(name, title, buttons):
    """Panelets overskrift: titel til venstre, ikonknapperne til hoejre."""
    for b in buttons:
        b.props["AlignInContainer"] = "AlignInContainer.Start"
        b.props["LayoutMinWidth"] = b.props["Width"]
    return group(name, [title, *buttons], direction="Horizontal", gap=4,
                 height=lay.HIT_TOUCH, align_items="Center")


def icon_button(name, label, fx, path, mode=None):
    """Et stregikon som klikbar Image UDEN ramme. Svg'en er lige saa stor som
    klikfladen (ikonet tegnet midt i), saa intet bliver klippet."""
    grey = '" & %s & "' % ref_hex_expr("text-primary")
    box = lay.HIT_TOUCH
    svg = _icons.svg(path, grey, size=20, box=box)
    if mode is None:
        image = f'"data:image/svg+xml;utf8," & EncodeUrl("{svg}")'
        enabled = "true"
    else:
        faded = _icons.svg(path, grey, size=20, box=box, opacity=_icons.DISABLED_OPACITY)
        enabled = f"({mode}) <> DisplayMode.Disabled"
        image = (f'"data:image/svg+xml;utf8," & EncodeUrl(If({enabled}, '
                 f'"{svg}", "{faded}"))')
    props = {
        "AccessibleLabel": f'"{label}"',
        "BorderColor": C_TRANSPARENT,
        "BorderStyle": "BorderStyle.None",
        "BorderThickness": "0",
        "DisabledFill": C_TRANSPARENT,
        "Fill": C_TRANSPARENT,
        "Height": str(lay.HIT_TOUCH),
        "HoverFill": "If(%s, %s, %s)" % (enabled, C_ROW_HOVER, C_TRANSPARENT) if mode else C_ROW_HOVER,
        "Image": image,
        "ImagePosition": "ImagePosition.Center",
        "OnSelect": fx,
        "PressedFill": "If(%s, %s, %s)" % (enabled, C_ROW_PRESSED, C_TRANSPARENT) if mode else C_ROW_PRESSED,
        "TabIndex": "If(%s, 0, -1)" % enabled if mode else "0",
        "Tooltip": f'"{label}"',
        "Width": str(lay.HIT_TOUCH),
    }
    if mode:
        props["DisplayMode"] = mode
    _icons.hit_radius(props)
    c = Ctrl(name, "Image", props=props, h=lay.HIT_TOUCH)
    ensure_hit(c)
    return c


def click_outside_overlay(name, close_fx, visible, label="Close panel"):
    """Gennemsigtigt lag over hele skaermen: et klik UDEN FOR panelet kalder
    close_fx. Laeg det FOER (under) panelet i lagene, saa panelet fanger egne
    klik. Fra row_editor_panel gaar det samme lag med i listen. Bruges af
    sidepaneler uden egen backdrop. Returnerer een Ctrl (Image)."""
    return Ctrl(name, "Image", props={
        "AccessibleLabel": f'"{label}"',
        "BorderStyle": "BorderStyle.None",
        "BorderThickness": "0",
        **stable_scrim(C_TRANSPARENT),
        "Height": "App.Height",
        "Image": '""',
        "OnSelect": close_fx,
        "TabIndex": "0",
        "Visible": visible,
        "Width": "App.Width",
        "X": "0",
        "Y": "0",
    }, h="App.Height", vis=visible)


def editor_footer(prefix, delete, reset, cancel, save):
    """Sidepanelets bundbjaelke: Delete row og Reset til venstre, Cancel og
    Save til hoejre (Materials, issue #228 - FL bruger den samme, #308).

    Grupperne er Start-justeret og praecis knaphoeje - med Center tegnede
    Studio de indlejrede knapper forskudt nedad og klippede dem. Er panelet
    for smalt til begge par paa een linje (mobil), staar parrene under
    hinanden, og Cancel og Save staar stadig til hoejre. Knapperne har
    deres bredde paa forhaand (Width)."""
    gap = 8
    left_w = int(delete.props["Width"]) + gap + int(reset.props["Width"])
    right_w = int(cancel.props["Width"]) + gap + int(save.props["Width"])
    for b in (delete, reset, cancel, save):
        b.props["AlignInContainer"] = "AlignInContainer.Start"
        b.props["LayoutMinWidth"] = b.props["Width"]
    left = group(f"con{prefix}EditorDeleteAction", [delete, reset], direction="Horizontal",
                 gap=gap, height=lay.HIT_TOUCH, width=left_w, align_items="Start",
                 align_in_container="Start")
    right = group(f"con{prefix}EditorSaveActions", [cancel, save], direction="Horizontal",
                  gap=gap, height=lay.HIT_TOUCH, width=right_w, align_items="Start",
                  align_in_container="Start", justify="End")
    one_line = f"({lay.PANEL_W_AT}) - 2 * 20 >= {left_w + 16 + right_w}"
    footer = group(f"con{prefix}EditorFooter", [left, right], direction="Horizontal",
                   gap=gap, height=f"If({one_line}, {lay.HIT_TOUCH}, {2 * lay.HIT_TOUCH + gap})",
                   width="Parent.Width", justify="SpaceBetween", align_items="Start")
    right.props["AlignInContainer"] = (f"If({one_line}, AlignInContainer.Start, "
                                       "AlignInContainer.End)")
    footer.props["LayoutDirection"] = (f"If({one_line}, LayoutDirection.Horizontal, "
                                       "LayoutDirection.Vertical)")
    footer.props["LayoutAlignItems"] = (f"If({one_line}, LayoutAlignItems.Start, "
                                        "LayoutAlignItems.Stretch)")
    return footer


# ---------------------------------------------------------------------------
# Sidepanelets gem-tilstand (issue #402)
#
# Foer taendte panelets Save det samme sloer og den samme bjaelke midt paa
# SIDEN som Save draft og Submit (progress_overlay) - langt fra knappen og
# bag panelet. Nu vises tilstanden I panelet, lige over bundbjaelken:
#
#   "saving"  hjulet (ModernSpinner) med "Saving..." - Save er spaerret
#   "failed"  "Save failed. Your changes are kept." og Retry
#   ""        intet (panelet lukker, naar gemmet lykkes, og appens
#             "Saved ..."-besked siger det - som foer)
#
# Tilstanden er EEN tekstvariabel, sat foer og efter selve gemmet - ingen
# timer, ingen fast varighed. Imens ligger et GENNEMSIGTIGT lag over hele
# skaermen, saa intet kan trykkes to gange eller rettes midt i et gem (det
# graa sloer gjorde det foer), men der tegnes intet paa siden.
# ---------------------------------------------------------------------------
PANEL_SAVE_H = 32
PANEL_SAVING = '"saving"'
PANEL_FAILED = '"failed"'


def panel_save_fx(state_var, save_fx, after_fx=None):
    """Panelets gem: tilstanden "saving", gemmet, og saa tilstanden.

    after_fx: det, der afgoer udfaldet bagefter (FL: fejl i colFlSaveErrors).
    Uden after_fx saetter gemmet selv "failed" i sin fejlgren, og alt andet
    (lykkedes, eller stoppet af et manglende felt) bliver tomt igen."""
    end = after_fx or f'If({state_var} = {PANEL_SAVING}, Set({state_var}, ""))'
    return f"Set({state_var}, {PANEL_SAVING});\n{save_fx};\n{end}"


def panel_save_mode(state_var, display_mode):
    """Save og Retry er spaerret, mens der gemmes."""
    return (f"If(IfError({state_var} = {PANEL_SAVING}, false), DisplayMode.Disabled, "
            f"{display_mode or 'DisplayMode.Edit'})")


def panel_save_status(prefix, state_var, retry_fx, display_mode=None):
    """Linjen over panelets bundbjaelke: hjulet eller fejlen med Retry.
    Hoejre-justeret, saa den staar ved Save. Skjult, naar der intet er."""
    saving = f"IfError({state_var} = {PANEL_SAVING}, false)"
    failed = f"IfError({state_var} = {PANEL_FAILED}, false)"
    spin = spinner(f"spn{prefix}EditorSaving", saving, '"Saving"', width=120,
                   height=PANEL_SAVE_H, label='"Saving..."', size=13)
    text = text_ctrl(f"txt{prefix}EditorSaveFailed", '"Save failed. Your changes are kept."',
                     size=13, color=C_INVALID_FG, weight="Semibold", height=20, wrap="false",
                     align="Right", visible=failed)
    grow(text)
    retry = button(f"btn{prefix}EditorRetry", '"Retry"', retry_fx,
                   width=fit_button_width('"Retry"'), height=PANEL_SAVE_H,
                   display_mode=panel_save_mode(state_var, display_mode), visible=failed,
                   tooltip='"Try to save again"')
    vis = f"{saving} || {failed}"
    return group(f"con{prefix}EditorSaveStatus", [spin, text, retry], direction="Horizontal",
                 gap=8, height=PANEL_SAVE_H, justify="End", align_items="Center", visible=vis)


def panel_save_text(btn, state_var, text="Saving..."):
    """Panelets Save siger selv "Saving...", mens der gemmes - samme
    moenster som sidernes knapper (issue #420). Hjulet staar lige over
    knappen (panel_save_status), saa ikonet viger for teksten imens: saa
    kan "Saving..." staa i knappens egen bredde, og bundbjaelkens bredder
    (editor_footer regner med tal) staar fast."""
    saving = f"IfError({state_var} = {PANEL_SAVING}, false)"
    width = int(btn.props["Width"])
    assert fit_button_width(f'"{text}"') <= width, (btn.name, text)
    btn.props["Text"] = f'If({saving}, "{text}", {btn.props["Text"]})'
    acc = btn.props.get("AccessibleLabel")
    if acc and acc != "Self.Text":
        btn.props["AccessibleLabel"] = f'If({saving}, "{text}", {acc})'
    if btn.props.get("Icon"):
        btn.props["Layout"] = f'If({saving}, ButtonLayout.TextOnly, {btn.props["Layout"]})'
    return btn


def panel_save_space(status):
    """Det, scrollen skal give af, naar statuslinjen staar der (+ panelets gap)."""
    return f"If({status.props['Visible']}, {PANEL_SAVE_H + 12}, 0)"


def panel_save_block(prefix, state_var):
    """Det gennemsigtige lag, mens panelet gemmer - fanger tryk, viser intet."""
    vis = f"IfError({state_var} = {PANEL_SAVING}, false)"
    return Ctrl(f"img{prefix}EditorSaveBlock", "Image", props={
        "AccessibleLabel": '"Saving, please wait"',
        "BorderStyle": "BorderStyle.None",
        "BorderThickness": "0",
        **stable_scrim(C_TRANSPARENT),
        "Height": "App.Height",
        "Image": '""',
        "TabIndex": "0",
        "Visible": vis,
        "Width": "App.Width",
        "X": "0",
        "Y": "0",
    }, h="App.Height", vis=vis)


# ---------------------------------------------------------------------------
# Knappens egen ventetilstand (issue #420)
#
# Foer taendte Save draft, Submit, Duplicate, Delete, Add rows, Reopen,
# Archive og Save documents et graat sloer med en bjaelke midt paa SKAERMEN
# (progress_overlay) - langt fra knappen, der startede handlingen. Nu er
# tilstanden ved knappen selv, i det samme moenster som sidepanelernes gem
# (#402) og kommentarfeltet (#370):
#
#   koerer     knappen siger "Saving..." / "Submitting..." / "Deleting..."
#              og er spaerret; hjulet (ModernSpinner) staar lige ved siden af
#   lykkedes   "Saved" / "Submitted" ... i groent ved knappen i 4 sekunder
#   fejlede    "Save failed" ... i roedt ved knappen, til naeste handling.
#              Intet indtastet ryddes - handlingerne rydder kun ved succes.
#
# Tilstanden er EEN tekstvariabel pr. skaerm (var<X>Act): handlingens
# noegle ("save", "submit", ...) mens den koerer, og "<noegle>:ok" eller
# "<noegle>:failed" bagefter. Den saettes lige foer og lige efter selve
# handlingen - ingen timer afgoer, hvornaar den er faerdig. Kun den groenne
# besked forsvinder af sig selv (tmr<X>ActDone).
#
# Imens ligger et GENNEMSIGTIGT lag over hele skaermen (act_block), saa
# intet kan trykkes to gange eller rettes midt i en handling - det graa
# sloer gjorde det foer - men der tegnes intet paa siden.
# ---------------------------------------------------------------------------
# noegle -> (mens den koerer, lykkedes, fejlede)
ACT_TEXTS = {
    "save": ("Saving...", "Saved", "Save failed"),
    "submit": ("Submitting...", "Submitted", "Submit failed"),
    "delete": ("Deleting...", "Deleted", "Delete failed"),
    "duplicate": ("Duplicating...", "Duplicated", "Duplicate failed"),
    "add": ("Adding...", "Rows added", "Add failed"),
    "upload": ("Saving...", "Files saved", "Save failed"),
    "reopen": ("Reopening...", "Reopened", "Reopen failed"),
    "archive": ("Updating...", "Updated", "Update failed"),
}
ACT_SPIN = 24
ACT_NOTE_SIZE = 13
ACT_OK_MS = 4000


def act_running(act_var):
    """Sand, mens en handling paa skaermen koerer (ingen ":" endnu)."""
    return f'IfError(!IsBlank({act_var}) && !(":" in {act_var}), false)'


def act_is(act_var, key):
    return f'IfError({act_var} = "{key}", false)'


def act_mark(act_var, key, ok=True):
    """Handlingens eget udfald - skrives i dens succes- eller fejlgren."""
    return f'Set({act_var}, "{key}:{"ok" if ok else "failed"}")'


def act_fx(act_var, key, fx, busy_var=None, ok=None, key_fx=None, left=""):
    """Handlingen med knappens tilstand: noeglen, handlingen, udfaldet.

    ok:     et udtryk, der efter handlingen siger, om den lykkedes. Uden ok
            skriver handlingen selv sit udfald (act_mark); har den ikke
            gjort det, blev den stoppet foer noget blev skrevet (fx et
            manglende felt med sin egen besked) - saa er tilstanden tom
            igen, eller left ("failed"), naar intet stop er muligt.
    key_fx: noeglen som udtryk, naar den afgoeres, mens der trykkes
            (VH-planens Save draft er ogsaa Submit).
    busy_var: appens gamle boolean, som andre knappers DisplayMode laeser."""
    lines = [f"Set({act_var}, {key_fx or chr(34) + key + chr(34)})"]
    if busy_var:
        lines.append(f"Set({busy_var}, true)")
    lines.append(fx)
    if busy_var:
        lines.append(f"Set({busy_var}, false)")
    if ok is not None:
        lines.append(f'Set({act_var}, {act_var} & If({ok}, ":ok", ":failed"))')
    elif left:
        lines.append(f'If({act_running(act_var)}, Set({act_var}, {act_var} & ":{left}"))')
    else:
        lines.append(f'If({act_running(act_var)}, Set({act_var}, ""))')
    return ";\n".join(lines)


def act_button(btn, act_var, key, text=None, grow=True):
    """Knappen viser handlingens ventetekst og er spaerret, mens noget paa
    skaermen koerer. Den bliver bredere, mens teksten er laengere - men
    ikke der, hvor den kun er sit ikon. grow=False: bredden roeres ikke
    (kalderen ved, at ventteksten er kortere end knappens egen)."""
    busy = act_is(act_var, key)
    t = text or ACT_TEXTS[key][0]
    old = btn.props["Text"]
    btn.props["Text"] = f'If({busy}, "{t}", {old})'
    acc = btn.props.get("AccessibleLabel")
    if acc and acc != "Self.Text":
        btn.props["AccessibleLabel"] = f'If({busy}, "{t}", {acc})'
    dm = btn.props.get("DisplayMode") or "DisplayMode.Edit"
    btn.props["DisplayMode"] = f"If({act_running(act_var)}, DisplayMode.Disabled, {dm})"
    wide = act_width(key, bool(btn.props.get("Icon")), text)
    if not grow:
        return btn
    layout = btn.props.get("Layout", "")
    when = busy
    if layout.startswith("If(") and "IconOnly" in layout:
        # If(<smal>, ButtonLayout.IconOnly, ...): kun bredere, naar teksten ses.
        cond = layout[3:layout.index(", ButtonLayout.IconOnly")]
        when = f"{busy} && !({cond})"
    fit_ = getattr(btn, "_fit", None)
    if fit_ is not None:
        nat, reserve = fit_
        btn._fit = (f"If({when}, Max({wide}, {nat}), {nat})", reserve)
    w = btn.props["Width"]
    new_w = f"If({when}, Max({wide}, {w}), {w})"
    if btn.props.get("LayoutMinWidth") == w:
        btn.props["LayoutMinWidth"] = new_w
    btn.props["Width"] = new_w
    return btn


def act_width(key, icon=True, text=None):
    """Knappens bredde med ventteksten (og ikonet)."""
    return fit_button_width(f'"{text or ACT_TEXTS[key][0]}"') + (ICON_W if icon else 0)


def act_status(name, act_var, keys, visible=None, size=ACT_NOTE_SIZE):
    """[hjul, besked] - staar lige ved knapperne for keys.

    Hjulet ses, mens en af handlingerne koerer; beskeden bagefter. Begge
    har en fast bredde (beskedens efter teksten), saa en raekke kan regne
    resten ud (grow). visible: en ekstra betingelse (fx kun fra Desktop)."""
    def _w(text):
        return label_px(text, size) + 4
    ok = [(f"{k}:ok", ACT_TEXTS[k][1]) for k in keys]
    bad = [(f"{k}:failed", ACT_TEXTS[k][2]) for k in keys]
    running = "(" + " || ".join(act_is(act_var, k) for k in keys) + ")"
    lst = lambda pairs: "[" + ", ".join(f'"{s}"' for s, _t in pairs) + "]"
    shown = f"IfError({act_var} in {lst(ok + bad)}, false)"
    failed = f"IfError({act_var} in {lst(bad)}, false)"
    text = (f"Switch({act_var}, "
            + ", ".join(f'"{s}", "{t}"' for s, t in ok + bad) + ', "")')
    width = (f"Switch({act_var}, "
             + ", ".join(f'"{s}", {_w(t)}' for s, t in ok + bad) + ", 0)")
    spin_vis = running if visible is None else f"({visible}) && {running}"
    note_vis = shown if visible is None else f"({visible}) && {shown}"
    labels = ", ".join(f'"{k}", "{ACT_TEXTS[k][0][:-3]}, please wait"' for k in keys)
    spin = spinner(f"spn{name}", spin_vis, f'Switch({act_var}, {labels}, "Please wait")',
                   width=ACT_SPIN, height=ACT_SPIN)
    spin.props["LayoutMinWidth"] = str(ACT_SPIN)
    spin.props["AlignInContainer"] = "AlignInContainer.Center"
    note = text_ctrl(f"txt{name}Note", text, size=size, weight="Semibold", wrap="false",
                     color=f"If({failed}, {C_INVALID_FG}, {C_VALID_FG})", height=20,
                     width=width, visible=note_vis)
    note.props["LayoutMinWidth"] = width
    note.props["AlignInContainer"] = "AlignInContainer.Center"
    return [spin, note]


def act_block(prefix, act_var):
    """Det gennemsigtige lag, mens en handling koerer - fanger tryk, viser
    intet. Staar SIDST i skaermens boern, oven paa popupperne."""
    vis = act_running(act_var)
    return Ctrl(f"img{prefix}ActBlock", "Image", props={
        "AccessibleLabel": '"Please wait"',
        "BorderStyle": "BorderStyle.None",
        "BorderThickness": "0",
        **stable_scrim(C_TRANSPARENT),
        "Height": "App.Height",
        "Image": '""',
        "TabIndex": "0",
        "Visible": vis,
        "Width": "App.Width",
        "X": "0",
        "Y": "0",
    }, h="App.Height", vis=vis)


def act_timer(prefix, act_var):
    """Den groenne besked staar ACT_OK_MS og forsvinder saa. Den roede
    bliver staaende til naeste handling. Timeren afgoer ALDRIG, hvornaar en
    handling er faerdig - kun hvor laenge "Saved" ses."""
    done = f'IfError(EndsWith({act_var}, ":ok"), false)'
    return Ctrl(f"tmr{prefix}ActDone", "Timer", props={
        "AutoPause": "false",
        "AutoStart": "false",
        "Duration": str(ACT_OK_MS),
        "Height": "1",
        "OnTimerEnd": f'If({done}, Set({act_var}, ""))',
        "Repeat": "false",
        "Reset": f"!{done}",
        "Start": done,
        "Visible": "false",
        "Width": "1",
    }, h=1, vis="false")


def act_layers(prefix, act_var):
    """[timer, lag] - staar SIDST i skaermens boern."""
    return [act_timer(prefix, act_var), act_block(prefix, act_var)]


def row_editor_panel(prefix, position, sections, footer, previous_fx, next_fx,
                     close_fx, visible, width=None, previous_mode=None,
                     next_mode=None, side_by_side=False, multiple=None, status=None):
    """Et responsivt raekke-editorpanel; footer holdes uden for scrollomraadet.

    status: panelets gem-linje (panel_save_status, issue #402) - staar lige
    over bundbjaelken, og scrollen giver plads, kun mens den vises.

    side_by_side: fra PANEL_SIDE_MIN staar panelet ved siden af listen
    (PanelInset), og saa maa baggrunden ikke daekke listen."""
    vis = f"IfError({visible}, false)"
    # Staar listen ved siden af, maa baggrunden ikke fange klik og rul.
    scrim_vis = f"{vis} && {lay.INSET} = 0" if side_by_side else vis
    backdrop = Ctrl(f"img{prefix}EditorBackdrop", "Image", props={
        "AccessibleLabel": '"Close row editor"',
        "BorderStyle": "BorderStyle.None",
        "BorderThickness": "0",
        **stable_scrim(C_TRANSPARENT),
        "Height": "App.Height",
        "Image": '""',
        "OnSelect": close_fx,
        "TabIndex": "0",
        "Visible": scrim_vis,
        "Width": "App.Width",
        "X": "0",
        "Y": "0",
    }, h="App.Height", vis=scrim_vis)

    prev = icon_button(f"btn{prefix}EditorPrevious", "Previous row", previous_fx,
                    _icons.CHEVRON_LEFT, previous_mode)
    next_ = icon_button(f"btn{prefix}EditorNext", "Next row", next_fx,
                     _icons.CHEVRON_RIGHT, next_mode)
    close = icon_button(f"btn{prefix}EditorClose", "Close", close_fx, _icons.CLOSE)
    if multiple:
        prev.vis = multiple
        next_.vis = multiple
    title = text_ctrl(f"txt{prefix}EditorPosition", position, size=lay.SIZE_CARD_TITLE,
                      weight="Semibold", height=28, wrap="false")
    grow(title)
    # Knapperne staar direkte i overskriften (som Issue Boards panel): i en
    # egen indlejret container blev de klippet til en tynd stribe.
    heading = icon_heading(f"con{prefix}EditorHeading", title, [prev, next_, close])
    # Panelets pad (2 x 16), overskriften, to mellemrum og bundbjaelken
    # traekkes fra - formularen fylder resten, og bundbjaelken staar ved
    # panelets bund (her stod 88 px ekstra, som blev tom plads under den).
    scroll_h = f"App.Height - ({2 * 16 + lay.HIT_TOUCH + 2 * 12} + ({footer.h}))"
    if status is not None:
        scroll_h += f" - {panel_save_space(status)}"
    scroll = group(f"con{prefix}EditorSections", sections, direction="Vertical", gap=16,
                   height=scroll_h, overflow_y="Scroll",
                   pad=(16, 20, 16, 20))
    panel = group(f"con{prefix}EditorPanel",
                  [heading, scroll, *([status] if status is not None else []), footer],
                  direction="Vertical", gap=12, height="App.Height",
                  width=lay.PANEL_W_AT,
                  fill=C_CARD_BG, border_color=C_CARD_BORDER, pad=(16, 20, 16, 20),
                  visible=vis, drop_shadow="Bold")
    panel.props["X"] = f"If({at_least('Desktop')}, App.Width - Self.Width, 0)"
    panel.props["Y"] = "0"
    return [backdrop, panel]


def request_shell(prefix, header, breadcrumb, actions, rows, editor=None, footer=None,
                  body_gap=16):
    """Komponer header, anmodningsnavigation, raekkeliste og editor-overlay.

    DEN FAELLES SKAL (UX-review L1). Alle anmodningsskaerme - Equipments,
    Materials, Measuring points, Functional Location og Issue Board - bygger
    rammen her. rows er een del eller en liste af dele (FL har raekker,
    klasser og struktur under hinanden). Skaermen leverer kun sine dele;
    editor er panelet, som skaermen selv kan placere i lagene (det skal staa
    over sidebarens aabne panel paa FL og Issue Board), og saa gives det
    ikke her."""
    parts = list(rows) if isinstance(rows, (list, tuple)) else [rows]
    body = [item for item in (breadcrumb, actions, *parts) if item is not None]
    root = app_frame(prefix, header, body, body_gap=body_gap, footer=footer)
    return [root, *(editor or [])]


def button_row(name, buttons, container_w, gap=8, height=36, align_items="Center", lead=()):
    """Knapraekke der ALDRIG ombryder.

    Den oprindelige raekke havde faste knapbredder (104 + 104 + 112 + gaps =
    336 px) i et kort med 324 px indhold. Den ombroed derfor til to linjer,
    mens raekkens hoejde stod fast paa 36 - og den sidste knap blev klippet.
    Her deler knapperne bredden ligeligt, saa de altid passer.

    lead: kontroller med fast bredde foran knapperne (fx act_status). De
    tager kun plads, mens de ses - knapperne deler resten.
    """
    n = len(buttons)
    taken = "".join(f" - If({k.vis}, ({k.props['Width']}) + {gap}, 0)" if k.vis
                    else f" - ({k.props['Width']}) - {gap}" for k in lead)
    w = f"({container_w} - {gap * (n - 1)}{taken}) / {n}"
    for b in buttons:
        b.props["Width"] = w
        b.props["LayoutMinWidth"] = "0"
    return group(name, [*lead, *buttons], direction="Horizontal", gap=gap, height=height,
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

        ikke kraevet        ->  border-input
        kraevet + tom       ->  state-error-fg
        kraevet + udfyldt   ->  state-ok-fg

    border-input (UX-review F7), ikke border-default: et felt skal kunne
    ses som et felt (3,2:1). Et LAAST felt faar border-default - det
    saetter input_theme, saa en laast, udfyldt kraevet kant heller ikke er
    groen (VH-planens planhoved).
    """
    if required_formula == "false":
        return C_INPUT_BORDER
    return (f"If(\n"
            f"    {required_formula} && {empty_test},\n"
            f"    {C_BORDER_ERROR},\n"
            f"    If({empty_test}, {C_INPUT_BORDER}, {C_BORDER_OK})\n"
            f")")


def readonly_mode(display_mode):
    """Et felt, der ikke kan redigeres, er VIEW - aldrig Disabled (issue #78).

    De moderne inputfelter tegner DisplayMode.Disabled med Fluent-temaets
    egne "disabled"-farver og ignorerer baade Color og Fill. Appen saetter
    ikke Fluent-temaet (farverne er C), saa i moerk tilstand blev et laast
    felt graa tekst paa sort: Main work center, Control Key, Vendor, Cost,
    Material Group, Plan text, Scheduling Indicator, Statutory Sort field
    og FL-comboboksen - netop de felter, der kan vaere laaste.

    View er dokumenteret som skrivebeskyttet ("renders as read-only rather
    than looking disabled") og bruger vores egne farver. Feltets baggrund
    siger stadig, at det er laast (input_fill -> input-bg-disabled), og
    kontrasten mod den er efterproevet i design_tokens (CONTRAST).

    Knapper roeres ikke: en deaktiveret knap SKAL se deaktiveret ud."""
    if not display_mode:
        return None
    return (f"If(({display_mode}) = DisplayMode.Edit, DisplayMode.Edit, "
            f"DisplayMode.View)")


def input_theme(props, display_mode):
    """DEN ENE stil for alle moderne inputfelter (issue #78): tekstfelt,
    talfelt, datovaelger, dropdown og FL-comboboksen. Farverne kommer fra
    tokens i begge tilstande - intet overlades til Fluent-temaets standard.

    Redigerbart: Appearance.FilledDarker - den tegner vores Fill (Outline
    er "transparent background"). Laast: Outline og daempet tekst, se
    nedenfor.

    BasePaletteColor er brandfarven: den farver fokusringen, valgte
    raekker i listen og kalenderen i datovaelgeren."""
    props["BasePaletteColor"] = C_PRIMARY
    props["Fill"] = input_fill(display_mode)
    props["Font"] = FONT
    props["Size"] = if_below("Tablet", str(lay.SIZE_INPUT_MOBILE), str(lay.SIZE_INPUT))
    if not display_mode:
        props["Appearance"] = "Appearance.FilledDarker"
        props["Color"] = C_INPUT_FG
        return props
    # LAAST = OUTLINE (issue #78, anden runde). Aflaest i Studio i moerk
    # tilstand: i View tegnede ModernTextInput og ModernDropdown Fluents
    # LYSE skrivebeskyttede baggrund og ignorerede Fill - med vores lyse
    # tekst ovenpaa. Talfeltet fulgte Fill. Outline er dokumenteret som
    # "transparent background" for alle fem feltyper, saa et laast felt er
    # nu kortets egen flade med kant og daempet tekst - ens for alle typer
    # og i begge temaer. Det redigerbare felt er udfyldt; det laaste er det
    # ikke. Forskellen er synlig uden at vaere en farve, Fluent kan tage.
    editable = f"({display_mode}) = DisplayMode.Edit"
    # LAAST = VIEW-KANTEN (UX-review, VH-planens planhoved): border-default
    # og daempet tekst - aldrig groen eller roed om et felt, man ikke kan
    # aendre.
    if props.get("BorderColor"):
        props["BorderColor"] = f"If({editable}, {props['BorderColor']}, {C_CARD_BORDER})"
    props["Appearance"] = f"If({editable}, Appearance.FilledDarker, Appearance.Outline)"
    props["Color"] = f"If({editable}, {C_INPUT_FG}, {C_MUTED})"
    props["DisplayMode"] = readonly_mode(display_mode)
    return props


def checkbox_theme(props):
    """ModernCheckbox med vores farver: etiketten i tekstfarven og boksen i
    brandfarven. Uden dem var etiketten Fluent-temaets moerke tekst - paa
    moerk baggrund i moerk tilstand (issue #78). Laast = View, som felterne."""
    props["BasePaletteColor"] = C_PRIMARY
    props["Color"] = C_TITLE
    props["Font"] = FONT
    props.setdefault("Size", "13")
    if props.get("DisplayMode"):
        props["DisplayMode"] = readonly_mode(props["DisplayMode"])
    return props


def row_rule(name, template_size):
    """Stregen mellem to raekker i et galleri - SIN EGEN FIGUR nederst i
    raekken (issue #70, #77, #78).

    Flere tabeller lavede stregen med galleriets FYLD i kantfarven og 2 px
    TemplatePadding. Raekkerne havde intet eget fyld, saa hele tabellen -
    raekker, tom plads under dem og pladsen ved scrollbaren - stod i den
    graa kantfarve. Nu er galleriet i fladens farve (table_surface), og
    stregen er her."""
    return Ctrl(name, "Rectangle", props={
        "AccessibleLabel": '"Row divider"', "BorderStyle": "BorderStyle.None",
        "BorderThickness": "0", "Fill": C_DIVIDER, "Height": "1",
        "OnSelect": "false", "TabIndex": "0",
        "Width": "Parent.TemplateWidth", "X": "0",
        "Y": (str(template_size - 1) if isinstance(template_size, int)
              else f"{template_size} - 1"),
    }, h=1)


def row_hit(name, onselect, label, width, height, radius=0, hover_border=False):
    """HELE RAEKKEN ER KLIKBAR - det ene moenster for alle klikbare lister
    (issue #79): hubbens anmodninger, Closed-preview og VH-planens items.

    Et gennemsigtigt lag OVEN PAA raekkens celler, med raekkens handling.
    Det ligger oeverst, saa ingen tekst, ikon eller knap i raekken kan
    snuppe klikket - Open-knappen og pilen under det bliver staaende som
    synlige tegn paa, at raekken kan aabnes, men klikket er lagets, og det
    goer PRAECIS det samme (samme onselect).

    Tilstande - alle fra tokens, ens i lys og moerk tilstand:
      standard   intet
      hover      raekken tones (row-hover), som sidebarens punkter
      tryk       staerkere tone (row-pressed) - det, en touchskaerm viser
      fokus      2 px kant i primaerfarven (tastatur: Tab + Enter/mellemrum)
    En blød overgang mellem dem kan Power Apps ikke tegne paa en kontrol;
    tilstandene skifter med det samme.

    Classic/Button, ikke ModernButton: den moderne knap har intet Fill, og
    dens hover-flade er Fluent-temaets og ville daekke raekken. Den
    klassiske har INGEN AccessibleLabel (issue #57) - skaermlaeseren laeser
    Text, saa label staar i Text i en gennemsigtig farve: den hoeres, men
    ses ikke. Scrolling paa en touchskaerm udloeser ikke OnSelect; kun et
    tryk goer.

    Cellerne under laget, der selv kan aabnes, tages ud af tab-
    raekkefoelgen med TabIndex -1, hvor typen kender den (Image, klassiske
    kontroller) - ModernButton goer IKKE (check_layout regel 10).

    INGEN "OPEN ..."-BANNER (issue #219)
    ------------------------------------
    Den klassiske knap har AutoDisableOnSelect = true: mens OnSelect
    koerer, er knappen deaktiveret og tegnes med Disabled*-farverne. De
    stod paa Power Apps' standard (graa flade, graa tekst), saa den
    usynlige label ("Open MAT-2026-011 - ...") stod et oejeblik som et
    stort banner over hele raekken, foer spinneren kom. Nu er den
    deaktiverede tilstand den samme som tryk-tilstanden: teksten forbliver
    usynlig, raekken beholder trykkets tone og flytter sig ikke.
    AutoDisableOnSelect bliver staaende - den er det, der afviser et
    dobbeltklik, mens handlingen koerer."""
    t = C_TRANSPARENT
    edge = C_PRIMARY if hover_border else t
    props = {
        "BorderColor": t, "BorderStyle": "BorderStyle.Solid", "BorderThickness": "2",
        "Color": t,
        "DisabledBorderColor": edge, "DisabledColor": t, "DisabledFill": C_ROW_PRESSED,
        "Fill": t,
        "FocusedBorderColor": C_PRIMARY, "FocusedBorderThickness": "2",
        "Height": str(height),
        "HoverBorderColor": edge, "HoverColor": t, "HoverFill": C_ROW_HOVER,
        "OnSelect": onselect,
        "PressedBorderColor": edge, "PressedColor": t, "PressedFill": C_ROW_PRESSED,
        "RadiusBottomLeft": str(radius), "RadiusBottomRight": str(radius),
        "RadiusTopLeft": str(radius), "RadiusTopRight": str(radius),
        "TabIndex": "0",
        "Text": label,
        "Width": str(width), "X": "0", "Y": "0",
    }
    return Ctrl(name, "Classic/Button", props=props, h=height)


def table_surface(gal, rule_name, surface=C_CARD_BG):
    """Goer et galleri til en tabel med neutral flade og streger mellem
    raekkerne: fyldet er fladens, TemplatePadding 0, og stregen er en
    figur. TemplateSize vokser med den padding, der forsvinder, saa
    galleriets hoejde og antal synlige raekker er de samme som foer.
    Raekken (galleriets foerste barn) skal have hoejden
    Parent.TemplateHeight - 2 eller - 1; den bliver - 1."""
    pad = int(gal.props.get("TemplatePadding", "0"))
    ts = str(gal.props["TemplateSize"])
    # TemplateSize kan vaere en formel (fx H.hit + 6).
    size = int(ts) + pad if ts.isdigit() else (f"{ts} + {pad}" if pad else ts)
    gal.props["Fill"] = surface
    gal.props["TemplatePadding"] = "0"
    gal.props["TemplateSize"] = str(size)
    row = gal.children[0]
    row.props["Height"] = "Parent.TemplateHeight - 1"
    gal.children.append(row_rule(rule_name, size))
    return gal


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
        "Default": default,
        "Height": str(height),
        "LayoutMinWidth": "0",
        "Placeholder": placeholder,
        **lay.radius(lay.RADIUS_INPUT),
        "ValidationState": f"If({required_formula} && IsBlank(Trim(Self.Text)), ValidationState.Error, ValidationState.None)",
        "Width": width,
    }

    input_theme(props, display_mode)
    if max_length is not None:
        props["MaxLength"] = str(max_length)
    if ttype is not None:
        props["Type"] = f"TextInputType.{ttype}"
    if onchange is not None:
        props["OnChange"] = onchange
    return Ctrl(name, "ModernTextInput", props=props, h=height)


# TAL SOM TEKST, UDEN SPIN-PILE (UX-review 2026-10, T10)
#
# ModernNumberInput har spin-pile, som ikke kan skjules (der er ingen
# egenskab til det), og som paa en touch-skaerm aendrer tallet ved et uheld.
# Et tal er derfor et tekstfelt: Default er tallet som tekst, og vaerdien
# laeses med num_value() - heltal (som DecimalPrecision '0' foer), tom ved
# et tomt felt og ved tekst, der ikke er et tal. Enheden ("h", "days")
# staar efter feltet, naar feltet ikke staar i et galleri (regel 26c) -
# dér siger kolonneoverskriften enheden.
NUM_UNIT_GAP = 6


def num_value(ref="Self"):
    """Feltets vaerdi som heltal - Blank() ved tomt felt eller ikke-tal."""
    return (f"IfError(If(IsBlank(Trim({ref}.Text)), Blank(), "
            f"Round(Value(Trim({ref}.Text)), 0)), Blank())")


def number_field(name, default, required_formula="false", width="Parent.Width", height=36,
                 display_mode=None, label=None, onchange=None, unit=None, placeholder='""'):
    """Talfeltet: ModernTextInput (praefiks inp) med tallet som tekst.

    default: Power Fx-tallet (variablen/kolonnen). onchange: formlen, der
    laeser num_value(). unit: tekst efter feltet - saa returneres
    [felt, enhed] som en vandret gruppe con<Navn>Unit."""
    if not name.startswith("inp"):
        raise SystemExit(f"number_field: {name} skal hedde inp... (regel 33)")
    unit_w = text_px(unit, lay.SIZE_BODY, semibold=False) + 4 if unit else 0
    in_w = width if not unit else f"({width}) - {unit_w + NUM_UNIT_GAP}"
    c = text_input(name, f"If(IsBlank({default}), \"\", Text({default}))",
                   placeholder=placeholder, required_formula=required_formula,
                   width=in_w, height=height, display_mode=display_mode, onchange=onchange,
                   label=label)
    if not unit:
        return c
    u = text_ctrl(f"txt{name[3:]}Unit", f'"{unit}"', size=lay.SIZE_BODY, color=C_MUTED,
                  height=20, width=str(unit_w), wrap="false",
                  accessible=f'"Unit: {unit}"')
    return group(f"con{name[3:]}Unit", [c, u], direction="Horizontal", gap=NUM_UNIT_GAP,
                 height=height, width=width, align_items="Center")


def date_picker(name, default_date, required_formula="false",
                width="Parent.Width", height=36, display_mode=None,
                onchange=None, label=None, placeholder=None, fmt=None):
    """Datovaelger - med SAMME kant- og baggrundsregel som de andre felter.

    Den var bygget i haanden inde i domain_parts.py og havde en FAST graa
    kant og INGEN Fill. Den blev derfor aldrig roed, naar den manglede,
    aldrig groen naar den var udfyldt, og den saa redigerbar ud i
    visningstilstand - hvidt felt med kant, der ikke reagerer.

    DefaultDate SAETTER datoen. SelectedDate LAESER den og kan ikke
    skrives - "Unknown property 'SelectedDate' for control type
    'ModernDatePicker'". Det er derfor OnChange laeser Self.SelectedDate,
    mens DefaultDate faar variablen.

    fmt: et andet format end det faelles (layout_tokens.DATE_PICKER_FMT) -
    kun hvor den gemte tekst har sit eget format (FL's Warranty, DD.MM.YYYY,
    issue #356). Pladsholderen viser saa samme moenster."""
    fmt = fmt or lay.DATE_PICKER_FMT
    if placeholder is None:
        placeholder = f'"{lay.DATE_PICKER_PLACEHOLDER if fmt == lay.DATE_PICKER_FMT else fmt}"'
    props = {
        "AccessibleLabel": label if label else f'"{name}"',
        "BorderColor": border_rule("IsBlank(Self.SelectedDate)", required_formula),
        "BorderStyle": "BorderStyle.Solid",
        "BorderThickness": "1",
        "DefaultDate": default_date,
        # Faelles format for alle datovaelgere (issue #235)
        "Format": f'"{fmt}"',
        "Height": str(height),
        "LayoutMinWidth": "0",
        "Placeholder": placeholder,
        **lay.radius(lay.RADIUS_INPUT),
        "Width": width,
    }
    # Datovaelgeren havde hverken Color eller et tema - dens tekst var
    # Fluent-temaets moerke paa vores moerke felt (issue #78).
    input_theme(props, display_mode)
    if onchange is not None:
        props["OnChange"] = onchange
    return Ctrl(name, "ModernDatePicker", props=props, h=height)


def themed_dropdown(name, items, default_text, value_col="Value", required_formula="false",
                    width="Parent.Width", height=36, display_mode=None, label=None,
                    onchange=None, display_col=None):
    """Appernes ENESTE dropdown - en ModernDropdown med runde hjoerner.

    HVORFOR MODERN (2026-09-30)
    ---------------------------
    Classic/DropDown har ingen Radius-egenskaber, saa dropdowns var de
    eneste felter med firkantede hjoerner. ModernDropdown har dem.

    Dens liste er en Fluent-flyout med LYS baggrund i begge temaer - den
    kan ikke farves. Color farver derimod baade feltets tekst og listens,
    og derfor er feltteksten input-fg: en mellemgraa, der kan laeses paa
    det sorte felt og paa den hvide liste (design_tokens.py). Foer stod
    her Classic, fordi listen var ulaeselig med vores lyse tekst (e735d66).

    Kaldet er det samme som foer:
      default_text  TEKSTEN i den viste kolonne. Default bliver den RECORD
                    fra Items, hvis viste kolonne er lig med teksten.
                    'As _dd' holder kolonnenavnet fra at blive bundet i
                    default_text's egne LookUp'er.
      display_col   kolonnen, listen VISER (fx "Name"), naar den ikke er
                    value_col. value_col er den, der kraeves udfyldt.

    check_layout regel 16 afviser Classic/DropDown."""
    col = display_col or value_col
    props = {
        "AccessibleLabel": label if label else f"\"{name}\"",
        "BorderColor": border_rule(f"IsBlank(Self.Selected.{value_col})", required_formula),
        "BorderStyle": "BorderStyle.Solid",
        "BorderThickness": "1",
        "Default": f"LookUp({items} As _dd, _dd.{col} = ({default_text}))",
        "Height": str(height),
        "ItemDisplayText": f"ThisItem.{col}",
        "Items": items,
        "LayoutMinWidth": "0",
        **lay.radius(lay.RADIUS_INPUT),
        "ValidationState": (f"If({required_formula} && IsBlank(Self.Selected.{value_col}), "
                            "ValidationState.Error, ValidationState.None)"),
        "Width": width,
    }
    input_theme(props, display_mode)
    if onchange is not None:
        props["OnChange"] = onchange
    return Ctrl(name, "ModernDropdown", props=props, h=height)


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
        "Size": if_below("Tablet", str(lay.SIZE_INPUT_MOBILE), str(lay.SIZE_INPUT)),
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
        return text_ctrl(child_name("txt", name, "Lbl"), f"\"{label_text}\"", size=13, weight="Semibold",
                         height=20, width=width, wrap="false")
    lbl_w = label_px(label_text, 13)
    if cell_w is not None:
        lbl_w = "Min(%d, (%s) - 13)" % (lbl_w, cell_w)
    kids = [text_ctrl(child_name("txt", name, "Lbl"), f"\"{label_text}\"", size=13, weight="Semibold", height=20,
                      width=lbl_w if required else None, wrap="false")]
    if required:
        kids.append(text_ctrl(child_name("txt", name, "Star"), "\"*\"", size=13, color=C_REQUIRED, weight="Semibold",
                              height=20, width=10, wrap="false", accessible="\"Required\""))
    return group(f"{name}Row", kids, direction="Horizontal", gap=3, height=20, align_items="Center", width=width)


def col_width(container_w, cols, gap=20):
    """Bredden af eet ud af `cols` felter side om side i en container med
    bredden container_w. Under braekpunktet TWO_COL_MIN staar alle felter
    fuld bredde (raekken stables lodret af row_n / two_col_row)."""
    return fits(container_w, TWO_COL_MIN, container_w,
                f"({container_w} - {gap * (cols - 1)}) / {cols}")


def field_cell(name, label_text, input_ctrl, required=False, hint_text=None, width=None,
               container_w=SHELL_W, fill_portions_formula=None, cols=2, gap=20,
               hints_on=None):
    """Et felt med label over.

    fill_portions_formula=None betyder braekpunktet: feltet vokser kun,
    naar der er desktop-plads. Stod foer som "If(App.Width < 1024, 0, 1)"
    - et af fire naesten ens tal. Se tools/layout_tokens.py. Hoejden regnes af indholdet - den er ikke laengere
    et magisk tal, saa et hoejere input (fx multiline) giver automatisk en
    hoejere felt.

    cols er antallet af felter, der skal staa side om side i raekken (brug
    samme tal i row_n/two_col_row), saa bredden bliver ens for alle celler
    i raekken.

    hints_on er Visible-udtrykket for hint_text - appens EGEN til/fra-
    kontakt (VH-plan: build_help.HINTS_ON). Den skal gives sammen med
    hint_text: her stod VH-planens varVhpShowHints som fast vaerdi, saa et
    hint i en anden app tavst ville laese VH's variabel (C12, R2-093)."""
    # VH-planens feltforklaringer styres af EEN variabel, slaaet til og fra
    # i hero-kortet. Foer havde hvert felt sit eget i-ikon - 21 knapper for
    # at vise 21 linjer er en knap for meget pr. linje.
    #
    # Hoejdealgebraen taeller kun synlige boern med, saa linjerne koster
    # ingen plads, naar de er slaaet fra.
    w = width or col_width(container_w, cols, gap)
    kids = [label_row(name, label_text, required=required, cell_w=w), input_ctrl]
    if hint_text is not None:
        if hints_on is None:
            raise ValueError("field_cell(%s): hint_text kraever hints_on - appens egen "
                             "til/fra-kontakt for feltforklaringer." % name)
        kids.append(text_ctrl(child_name("txt", name, "Hint"), hint_text, size=12, color=C_MUTED,
                              height=32, wrap="true",
                              visible=hints_on))
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


# MAERKET (issue #304, del af #161). Status- og nummermaerker var en
# ModernText med fyld og runde hjoerner eller et Image med en SVG-pille. Nu
# den moderne Badge. Versionen er den, Microsoft Learns YAML-eksempel
# skriver ("Badge modern control in canvas apps"); check_layout regel 16e
# afviser enhver anden.
BADGE_CONTROL = "ModernBadge@1.0.0"


def modern_badge(name, content, *, color, fill, width, height=22, size=lay.SIZE_MICRO,
                 weight="Semibold", radius=None, pad=(0, 0), align="Center",
                 accessible=None, visible=None, extra=None):
    """Et maerke - EEN kontrol for alle status- og nummermaerker (#304).

    Farverne er vores egne tokens, ikke Fluents: Color og Fill saettes
    altid (Learn: "When blank, Intent and Appearance determine ..."), saa
    maerket har PRAECIS de farver, det havde som tekst/billede - ogsaa i
    moerk tilstand. Intent er Neutral, saa et maerke, der af en eller anden
    grund mister sit fyld, aldrig staar i Fluents groenne standard
    (Positive). Kun egenskaber fra Learn (regel 16e).

    pad: (venstre, hoejre) luft om teksten. radius: hjoernet; standard er
    en pille (halv hoejde). Maerket tager ikke input: intet OnSelect og
    ingen TabIndex (Learn: uden OnSelect er det display-only)."""
    r = height // 2 if radius is None else radius
    props = {
        "AccessibleLabel": accessible or content,
        "Align": f"Align.{align}",
        "Appearance": "BadgeAppearance.Filled",
        "BorderStyle": "BorderStyle.None",
        "BorderThickness": "0",
        "Color": color,
        "Content": content,
        "Fill": fill,
        "Font": FONT,
        "FontWeight": f"FontWeight.{weight}",
        "Height": str(height),
        "Intent": "BadgeIntent.Neutral",
        "PaddingBottom": "0", "PaddingLeft": str(pad[0]),
        "PaddingRight": str(pad[1]), "PaddingTop": "0",
        "Shape": "BadgeShape.Circular" if 2 * r >= height else "BadgeShape.Rounded",
        "Size": str(size),
        "VerticalAlign": "VerticalAlign.Middle",
        "Width": str(width),
        **lay.radius(r),
    }
    if visible is not None:
        props["Visible"] = visible
    if extra:
        props.update(extra)
    _badge_no_self(props)
    return Ctrl(name, BADGE_CONTROL, props=props, h=height, vis=visible)


# KORTET (Card, preview). Peter bad om det moderne Card til noegletallene paa
# VH-planens taskliste (Total cost og Duration, 2026-10-19). Versionen er
# den, Microsoft Learns YAML-eksempler skriver ("Card modern control").
# Kun egenskaber fra Learn: Title, Subtitle, Description, Image,
# HeaderImage, Fill, *Color og *Size. Image og HeaderImage er Blank(), saa
# kortet ikke viser et eksempelbillede.
CARD_CONTROL = "ModernCard@1.0.0"


def modern_card(name, title, subtitle, description, *, width, height, fill,
                title_color, subtitle_color, description_color, title_size=14,
                subtitle_size=12, description_size=12, visible=None):
    """Et kort med titel, undertitel og beskrivelse - kun visning."""
    props = {
        "Description": description,
        "DescriptionColor": description_color,
        "DescriptionSize": str(description_size),
        "Fill": fill,
        "HeaderImage": "Blank()",
        "Height": str(height),
        "Image": "Blank()",
        "Subtitle": subtitle,
        "SubtitleColor": subtitle_color,
        "SubtitleSize": str(subtitle_size),
        "Title": title,
        "TitleColor": title_color,
        "TitleSize": str(title_size),
        "Width": str(width),
    }
    if visible is not None:
        props["Visible"] = visible
    return Ctrl(name, CARD_CONTROL, props=props, h=height, vis=visible)


def _badge_no_self(props):
    """Self.Content kan ikke laeses i Studio ("'Content' isn't recognized",
    #331). Hvor en formel bruger den, staar maerkets egen tekst-formel i
    stedet (regel 16e afviser Self.Content)."""
    content = props["Content"]
    for key, fx in list(props.items()):
        if key != "Content" and "Self.Content" in fx:
            props[key] = fx.replace("Self.Content", f"({content})")


def badge(name, text, size=11, width=64):
    """Det graa trin-maerke ("Step N") - nu en ModernBadge (#304) med de
    samme farver, maal og hjoerner som teksten foer."""
    return modern_badge(name, text, color=C_MUTED, fill=C_NEUTRAL_BG, width=width, size=size,
                        radius=12, pad=(10, 10),
                        extra={"AlignInContainer": "AlignInContainer.Center"})


# SEKTIONSOVERSKRIFTEN (issue #228). Stod i VH-planens build_plan_header;
# den er flyttet hertil uaendret, saa Materials' formular kan faa samme
# overskrift som Item Editor uden at importere VH-planens moduler.
def step_badge(name, step_label, valid_fx, attention_fx=None):
    """Sektionens badge (issue #123): "Step N", indtil sektionen er
    faerdig OG opfylder valideringen - saa "Valid" i ok-farverne. Samme
    badge og samme farver paa alle tre sektioner.

    valid_fx er den eksisterende validering (build_status: VhpPlanValid,
    VhpItemsValid, VhpOpsValid), aldrig blot "gemt".
    attention_fx: hvornaar der i stedet skal staa "Invalid" (fx et item,
    der er gemt som ugyldigt)."""
    # UX-review (VH-plan): badget viser kun en TILSTAND - "Valid" eller
    # "Invalid". "Step 1/2/3" gentog headerens trin og forsvinder; uden en
    # tilstand er badget skjult.
    text = (f'If({valid_fx}, "Valid", ' + (f'{attention_fx}, "Invalid", ' if attention_fx else "")
            + '"")')
    b = badge(name, text, width=72)
    b.vis = f"({valid_fx})" + (f" || ({attention_fx})" if attention_fx else "")
    # Self.Content kan ikke laeses i Studio (#331); farverne vaelges ud fra
    # samme betingelser som teksten.
    att = f"{attention_fx}, " if attention_fx else ""
    b.props["Color"] = (f'If({valid_fx}, {C_VALID_FG}, '
                        + (f'{att}{C_INVALID_FG}, ' if attention_fx else "") + f'{C_MUTED})')
    b.props["Fill"] = (f'If({valid_fx}, {C_VALID_BG}, '
                       + (f'{att}{C_INVALID_BG}, ' if attention_fx else "") + f'{C_NEUTRAL_BG})')
    b.props["AccessibleLabel"] = (f'If({valid_fx}, "{step_label}: valid", '
                                  + (f'{att}"{step_label}: invalid", ' if attention_fx else "")
                                  + f'"{step_label}: not complete yet")')
    return b


def section_header(name, title, step_label, extra_right=(), extra_left=(), valid_fx=None,
                   attention_fx=None):
    """Sektionsoverskrift: titlen til venstre (evt. med noget lige efter
    den, fx "* Required"), og et trin-badge til hoejre.

    valid_fx (issue #123): badget skifter fra "Step N" til "Valid", naar
    sektionen opfylder valideringen (step_badge).

    Beskrivelsen under titlen er fjernet (issue #54). Den gentog blot det,
    sektionen viser, og kostede en linje paa hvert kort."""
    t = text_ctrl(child_name("txt", name, "Title"), f"\"{title}\"", size=lay.SIZE_CARD_TITLE, weight="Semibold",
                  height=text_min_height(lay.SIZE_CARD_TITLE),
                  width=text_px(title, lay.SIZE_CARD_TITLE), wrap="false")
    t.props["LayoutMinWidth"] = t.props["Width"]

    right = list(extra_right)
    if step_label and valid_fx:
        right.append(step_badge(child_name("bdg", name, "Badge"), step_label, valid_fx, attention_fx))
    elif step_label:
        right.append(badge(child_name("bdg", name, "Badge"), f"\"{step_label}\"", width=64))

    # FLAD RAEKKE (issue #54 - titlerne manglede i Studio). Titlen staar
    # DIREKTE i overskriftens raekke, ikke i en indlejret gruppe, og en tom
    # gruppe tager resten af bredden. Da titlen flyttede fra en lodret til
    # en vandret indlejret gruppe, lagde Studio den ikke rigtigt om - det er
    # netop den flytning mellem foraeldre, deploy advarer om. Uden en
    # indlejret titelgruppe er der intet at flytte forkert.
    gap = group(f"{name}Gap", [], direction="Horizontal", height=0)
    grow(gap)
    return group(f"{name}", [t] + list(extra_left) + [gap] + right, direction="Horizontal",
                 gap=12, align_items="Center")



def card(name, children, gap=14, visible=None, pad_y=18):
    """Sektionskort i appens standardstil. Padding taelles automatisk med i
    hoejden - det var den fejl der gjorde hvert eneste kort 36 px for lavt.

    pad_y er kun top og bund. Siderne er altid 18: indholdsbredden regnes
    overalt som SHELL_W - 36."""
    return group(name, children, direction="Vertical", gap=gap,
                 fill=C_CARD_BG, border_color=C_CARD_BORDER, radius=lay.RADIUS_CARD,
                 pad=(pad_y, 18, pad_y, 18), visible=visible)
