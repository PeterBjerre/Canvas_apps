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
from design_tokens import DARK_VAR, toggle_action
import layout_tokens as lay
from layout_tokens import below, fits, if_below, TWO_COL_MIN
from gen_screen import (
    Ctrl, render, render_screen, stack_height, row_height,
    C_APP_BG, C_CARD_BG, C_CARD_BORDER, C_TITLE, C_MUTED, C_REQUIRED,
    C_PRIMARY, C_PRIMARY2, C_WHITE, C_TRANSPARENT, C_INPUT_BG, C_DISABLED_BG,
    C_DIVIDER, C_VALID_FG, C_VALID_BG, C_INVALID_FG, C_INVALID_BG,
    C_BORDER_OK, C_BORDER_ERROR,
    C_INFO_FG, C_INFO_BG, C_NEUTRAL_FG, C_NEUTRAL_BG, FONT,
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


def text_ctrl(name, text, size=14, color=C_TITLE, weight=None, wrap="false",
              align=None, height=20, width=None, fill=C_TRANSPARENT,
              accessible=None, visible=None, layout_min_width=None, extra=None):
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
    if overflow_y is not None:
        props["LayoutOverflowY"] = f"LayoutOverflow.{overflow_y}"
    if overflow_x is not None:
        props["LayoutOverflowX"] = f"LayoutOverflow.{overflow_x}"
    if visible is not None:
        props["Visible"] = visible
    if align_in_container is not None:
        props["AlignInContainer"] = f"AlignInContainer.{align_in_container}"
    props = {k: v for k, v in props.items() if v is not None}
    return Ctrl(name, "GroupContainer", variant="AutoLayout", props=props, children=children,
                h=height, vis=visible)


def button(name, text, onselect, primary=False, danger=False, width=140, height=36,
           display_mode=None, base_color=None, layout_min_width=None, visible=None,
           accessible=None):
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
    return Ctrl(name, "ModernButton", props=props, h=height, vis=visible)


def theme_button(name="btnThemeToggle", light_label='"Dark"',
                 dark_label='"Light"', width=92, height=34):
    """Knappen der skifter mellem lyst og moerkt tema.

    SAMME KONSTRUKTION I ALLE FIRE APPS. Det er hele pointen: en knap, der
    ser forskellig ud fra app til app, er praecis den slags drift, der har
    gjort de fire apps forskellige indtil nu.

    TEKSTEN SIGER HVAD DER SKER, IKKE HVAD DER ER
    ---------------------------------------------
    Staar appen lyst, staar der "Dark" paa knappen. Det er den samme
    konvention som i Windows og i browsere - en knap er en handling, ikke
    en tilstandsvisning. AccessibleLabel siger det udfoerligt, fordi et
    enkelt ord uden knappens udseende ikke er nok for en skaermlaeser.

    HVORFOR SEKUNDAER
    -----------------
    Den skal kunne findes og ellers vaere i fred. En primaerfarvet knap
    ville traekke oejet til sig hver gang skaermen tegnes, og temaskift er
    noget man goer een gang.

    Handlingen staar i tools/design_tokens.py - baade Set() og SaveData,
    saa valget ogsaa er der i morgen."""
    lbl = f"If({DARK_VAR}, {dark_label}, {light_label})"
    acc = (f'If({DARK_VAR}, "Switch to light theme", "Switch to dark theme")')
    return button(name, lbl, toggle_action(), width=width, height=height,
                  accessible=acc)


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


def flow_row(name, children, container_w, gap=8, narrow_cols=1, flex=None,
             flex_min=0, align_items="Center", **group_kw):
    """En vandret raekke, der ENTEN staar paa een linje ELLER som et gitter.
    Aldrig noget midt imellem.

    HVORFOR IKKE BARE LayoutWrap
    ----------------------------
    LayoutWrap lader platformen bestemme, hvor mange linjer det bliver - og
    det tal afhaenger af den bredde, containeren FAKTISK faar. Hoejden er
    derimod regnet her i Python. De to maa aldrig vaere uenige, men de
    kunne: en raekke regnet til at fylde SHELL_W paa pixlen, i en container
    der var scrollbarens 17 px smallere, ombroed til to linjer med hoejde
    til een. Sidste barn blev klippet vaek. Det var de forsvundne knapper.

    wrap_row_height(), som stod her foer, regnede med hoejst TO linjer. Paa
    en smal skaerm blev det tre, fire eller fem.

    HER ER DER KUN TO TILSTANDE, OG BEGGE ER REGNET UD
    ------------------------------------------------
      passer   ->  alle boern paa een linje med deres egne bredder.
                   Hoejde = det hoejeste barn.
      passer   ->  boernene faar bredden (Parent.Width - gaps) / narrow_cols
      ikke         MINUS 1 px, saa praecis narrow_cols staar paa hver linje.
                   Antallet af linjer er ceil(n / narrow_cols) - et tal, ikke
                   et gaet. Hoejde = summen af linjerne.

    Om den passer, afgoeres af boernenes EGNE bredder mod container_w, saa
    graensen flytter sig selv, naar nogen tilfoejer en knap.

    flex = et af boernene, der tager RESTEN af linjen (typisk titlen). Det
    taelles med flex_min px i graensen.

    Boernenes Width overskrives. Et barn, der selv er en flow_row, skal
    derfor bygges med container_w=flow_child_w(...) for den her raekke -
    se top_bar().
    """
    n = len(children)
    vis_any = any(c.vis for c in children)
    if vis_any and narrow_cols != 1:
        raise SystemExit("flow_row %s: skjulte boern kan kun staa i een "
                         "kolonne, naar raekken stables" % name)
    wide = [None if c is flex else str(c.props["Width"]) for c in children]
    fixed = [w for w in wide if w is not None]
    ok = flow_ok(children, container_w, gap, flex, flex_min)
    narrow_w = "(Parent.Width - %d) / %d - 1" % (gap * (narrow_cols - 1), narrow_cols)
    for c, w in zip(children, wide):
        if w is None:
            # Resten af den FAKTISKE linje - Parent.Width, ikke container_w.
            # Graensen ovenfor er afgjort med den forsigtige bredde; naar den
            # er sand, er der mindst saa meget plads, og titlen maa gerne
            # tage det hele, saa knapperne staar helt ude til hoejre.
            w = "Parent.Width - (%s) - %d" % (_sum_expr(fixed, 0), gap * len(fixed) + 1)
        c.props["Width"] = "If(%s, %s, %s)" % (ok, w, narrow_w)
        c.props["LayoutMinWidth"] = "0"

    hs = [0 if c.h is None else c.h for c in children]
    one = _max_expr(hs)
    if narrow_cols == 1:
        parts = []
        for i, c in enumerate(children):
            g = 0 if i == 0 else gap
            h = hs[i]
            if c.vis:
                parts.append("If(%s, %d + (%s), 0)" % (c.vis, g, h))
            else:
                parts.append("%d + (%s)" % (g, h) if g else "(%s)" % h)
        stacked = " + ".join(parts)
    else:
        lines = [hs[i:i + narrow_cols] for i in range(0, n, narrow_cols)]
        stacked = _sum_expr([_max_expr(l) for l in lines], gap)
    height = "If(%s, %s, %s)" % (ok, one, stacked)
    return group(name, children, direction="Horizontal", gap=gap, wrap="true",
                 align_items=align_items, height=height, **group_kw)


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


def flow_child_w(row_ok, wide_w, container_w):
    """Den bredde, et barn af en flow_row regner med: sin egen, naar
    raekken staar paa een linje, og hele containerens, naar den stables.
    Bruges, naar barnet SELV er en flow_row (knapperne i top_bar)."""
    return "If(%s, %s, %s)" % (row_ok, wide_w, container_w)


def top_bar(prefix, title, subtitle, actions, container_w, gap=20,
            action_gap=10, min_title=240, title_size=22):
    """Bjaelken oeverst - den SAMME konstruktion i alle fire apps.

    Venstre: titel og undertitel, som tager resten af linjen.
    Hoejre:  handlingerne, hver med sin faste bredde.

    Der er ingen haandskrevet tabel over knapbredderne, og ingen vagt der
    skal holde den i trit: graensen regnes af de kontroller, der faktisk
    staar i raekken. Tilfoejes en knap, flytter graensen sig selv.

    Staar den i rammens header (app_frame), scroller den aldrig vaek, og
    dens hoejde afhaenger kun af App.Width - aldrig af data.

    Smal skaerm: titlen over knapperne, og knapperne to og to.
    """
    t = text_ctrl("txt%sTitle" % prefix, title, size=title_size, weight="Semibold",
                  height=30, wrap="false")
    sub = text_ctrl("txt%sSub" % prefix, subtitle, size=13, color=C_MUTED,
                    height=20, wrap="false")
    left = group("con%sBarLeft" % prefix, [t, sub], direction="Vertical", gap=2,
                 width="0")
    # +2: knapperne staar i deres EGEN wrap-raekke, og den er praecis saa
    # bred som dem. Uden luft kunne en afrunding paa en broekdel af en
    # pixel sende den sidste knap ned paa en linje, der ikke er der.
    act_w = (sum(int(str(a.props["Width"])) for a in actions)
             + action_gap * (len(actions) - 1) + 2)
    # Graensen for hele bjaelken skal kendes, FOER hoejresiden bygges:
    # hoejresidens egen container er "min bredde, hvis bjaelken passer,
    # ellers hele linjen". flow_ok() er den samme funktion, flow_row selv
    # bruger, saa de to kan ikke regne forskelligt.
    right = group("con%sBarRight" % prefix, [], width=str(act_w))
    bar_ok = flow_ok([left, right], container_w, gap, flex=left, flex_min=min_title)
    right_cw = flow_child_w(bar_ok, str(act_w), container_w)
    right = flow_row("con%sBarRight" % prefix, actions, right_cw, gap=action_gap,
                     narrow_cols=2)
    right.props["Width"] = str(act_w)
    return flow_row("con%sBar" % prefix, [left, right], container_w, gap=gap,
                    flex=left, flex_min=min_title)


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
    return group("con%sRoot" % prefix, [head, main], direction="Vertical", gap=0,
                 height="Parent.Height", width="Parent.Width", fill=C_APP_BG)


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


def label_row(name, label_text, required=False, width="Parent.Width"):
    kids = [text_ctrl(f"{name}Lbl", f"\"{label_text}\"", size=13, weight="Semibold", height=20, wrap="false")]
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
    kids = [label_row(name, label_text, required=required), input_ctrl]
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

    w = width or col_width(container_w, cols, gap)
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


def card(name, children, gap=14, visible=None):
    """Sektionskort i appens standardstil. Padding taelles automatisk med i
    hoejden - det var den fejl der gjorde hvert eneste kort 36 px for lavt."""
    return group(name, children, direction="Vertical", gap=gap,
                 fill=C_CARD_BG, border_color=C_CARD_BORDER, radius=14,
                 pad=(18, 18, 18, 18), visible=visible)
