# -*- coding: utf-8 -*-
"""
Kontroltrae-DSL og serialisering til .pa.yaml (Power Apps canvas).

Filen er ordret ens i alle apps i repoet. Retter du her, skal du kopiere
den til de oevrige build-mapper - se .github/skills/canvas-build/SKILL.md.

HOEJDEMODELLEN
--------------
Canvas-containere kan ikke "hugge" deres indhold - en container faar kun den
hoejde, dens Height-formel siger. Den oprindelige kode loeste det ved at lade
hver container summere sine BOERNS .Height:

    conVhpShell.Height = 40 + conVhpHero.Height + 20 + conVhpPlanCard.Height + ...

Det er en cirkelreference. I en AutoLayout-container er det FORAELDREN, der
saetter boernenes stoerrelse (LayoutAlignItems er Stretch som standard, og paa
en container med LayoutWrap = true fjerner platformen LayoutAlignItems helt,
saa Stretch ikke kan slaas fra). Naar forelderen saa laeser barnets .Height,
laeser den sin egen udregning tilbage. Resultatet er enten en formelfejl, der
falder tilbage til IfError-konstanten, eller den kaskade-vaekst hvor
containerne bliver stoerre for hver genberegning.

Loesningen her: ingen Height-formel refererer nogensinde en anden kontrol.
Hoejder beregnes i Python ud fra konstanter, App.Width og CountRows(), og
stack_height()/row_height() taeller selv padding og gaps med, saa de ikke kan
glemmes et enkelt sted.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def _out_dir():
    """App-mappen, skaermen skal skrives i.

    DEN MAA IKKE REGNES UD AF __file__. Her stod "HERE/..", og da filen
    flyttede fra hver app's build-mappe til tools/, blev HERE/.. til
    REPO-RODEN. Alle fire skaerme blev skrevet dér, app-mapperne beholdt
    deres gamle udgaver - og layout-tjekket sagde "OK", fordi det laeste de
    gamle filer. Groent byggeri, ingen aendring, ingen fejlmeddelelse.

    Den rigtige kilde er INDGANGEN: assemble_screen.py ligger altid i
    app'ens egen build-mappe. sys.argv[0] er den fil, der koeres.
    """
    entry = os.path.abspath(sys.argv[0]) if sys.argv and sys.argv[0] else ""
    build = os.path.dirname(entry) if entry else os.getcwd()
    app = os.path.abspath(os.path.join(build, ".."))
    # Et app-mappe HAR en build-mappe. Uden det tjek ville en forkert sti
    # bare skrive filen et tilfaeldigt sted - praecis som den gjorde.
    if not os.path.isdir(os.path.join(app, "build")):
        raise SystemExit(
            "gen_screen: kan ikke finde app-mappen.\n"
            "  indgang: %s\n  udledt:  %s\n"
            "Koer builderen fra app'ens build-mappe:\n"
            "    cd \"<App>/build\" && python3 assemble_screen.py\n"
            "eller brug: python3 tools/build_all.py" % (entry or "(ingen)", app))
    return app


OUT_DIR = _out_dir()

# Designtokens ligger EET sted for hele repoet - ikke i en kopi pr.
# build-mappe som denne fil selv. Farven er det eneste, de fire apps skal
# vaere enige om ned til vaerdien, og en kopi ville netop kunne glide.
#
# tools/ er udenfor app-mappen, og det er med vilje ufarligt her:
# canvas_mcp.stage() kopierer KUN *.pa.yaml over til serveren, saa hverken
# build/ eller tools/ naar nogensinde ud i Studio.
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from design_tokens import ref as _t, TRANSPARENT
from layout_tokens import (below, if_below, SHELL_W, SCROLLBAR_W,
                           GALLERY_RESERVE)

# ---------------------------------------------------------------------------
# Farver
#
# Ingen vaerdi staar her. Hvert navn peger paa en DESIGNTOKEN, og tokenens
# vaerdi staar i tools/design_tokens.py - eet sted for alle fire apps.
#
# Det, en builder skriver i en skaerm, er derfor ikke "RGBA(250, 251, 253, 1)"
# men "C.'bg-card'". C er en navngiven formel i App.Formulas, der vaelger
# mellem det lyse og det moerke saet. Derfor skifter hele appen tema uden at
# en eneste kontrol ved, at moerk tilstand findes.
#
# Navnene nedenfor er de GAMLE C_*-navne. De staar i knap 500 kald ude i
# builderne, og at doebe dem om ville vaere en anden aendring end den her.
# ---------------------------------------------------------------------------
C_APP_BG = _t("bg-app")
C_CARD_BG = _t("bg-card")
C_SURFACE = _t("bg-surface")
C_MUTED_BG = _t("bg-muted")
C_CARD_BORDER = _t("border-default")
C_TITLE = _t("text-primary")
C_MUTED = _t("text-muted")
C_REQUIRED = _t("state-error-fg")
C_PRIMARY = _t("color-brand-primary")
C_PRIMARY2 = _t("color-brand-primary-hover")
C_PRIMARY_SOFT = _t("color-brand-primary-soft")
C_WHITE = _t("text-on-primary")
# Tekst paa en DOMAENEFARVE. I lys tilstand er den den samme hvide som
# C_WHITE; i moerk er domaenefarverne lyse, og hvid tekst paa dem gav
# 1,67-2,72:1. Derfor et eget navn - se CONTRAST i design_tokens.py.
C_ON_DOMAIN = _t("text-on-domain")
C_INPUT_BG = _t("input-bg")
C_DISABLED_BG = _t("input-bg-disabled")
C_DIVIDER = _t("border-subtle")
C_MODAL_BG = _t("bg-modal")
C_OVERLAY = _t("overlay")

# Gennemsigtig er IKKE en token: den er den samme i begge temaer, og der
# er ingen beslutning at traeffe om den.
C_TRANSPARENT = TRANSPARENT

# KANT vs. TEKST. C_VALID_FG/C_INVALID_FG er TEKSTfarver (4,5:1).
# C_BORDER_OK/C_BORDER_ERROR er de samme to tilstande som en 1 px KANT
# (3,0:1) - ens i lys tilstand, daempet i moerk. Se BALANCED i
# tools/design_tokens.py for hvorfor de ikke kan vaere eet navn.
C_BORDER_OK = _t("border-ok")
C_BORDER_ERROR = _t("border-error")
C_VALID_FG = _t("state-ok-fg")
C_VALID_BG = _t("state-ok-bg")
C_INVALID_FG = _t("state-error-fg")
C_INVALID_BG = _t("state-error-bg")
C_WARN_FG = _t("state-warn-fg")
C_WARN_BG = _t("state-warn-bg")
C_INFO_FG = _t("state-info-fg")
C_INFO_BG = _t("state-info-bg")
C_NEUTRAL_FG = _t("state-neutral-fg")
C_NEUTRAL_BG = _t("state-neutral-bg")

FONT = "Font.'Segoe UI'"

# Bredden af skaermens indholdsomraade. Den staar i tools/layout_tokens.py
# sammen med rammen, den er regnet af - padding, scrollbar og luft. Alle
# responsive udregninger gaar gennem den, og den er en NEDRE graense for
# det, platformen giver: se RAMMEN i layout_tokens.py for hvorfor det ikke
# maa vaere et gaet paa det praecise tal.

# Bredden af items-skinnen naar de to kort staar side om side.
RAIL_W = 360
SPLIT_GAP = 20
# Bredden af Item Editor-kortet, udtrykt uden at referere nogen kontrol.
#
# Her stod "App.Width < 1000". Det var eet af FIRE braekpunkter mellem 996
# og 1024, spredt over fire filer - heroen stablede ved 996, det her ved
# 1000, hubbens fliser ved 1004 og FillPortions ved 1024. Alle fire stod
# for det samme skift, og ingen af dem var valgt i forhold til de tre
# andre. Nu er de eet tal. Se tools/layout_tokens.py.
EDITOR_W = if_below("Desktop", SHELL_W, f"{SHELL_W} - {RAIL_W} - {SPLIT_GAP}")


# ---------------------------------------------------------------------------
# Tiny control-tree DSL
# ---------------------------------------------------------------------------
class Ctrl:
    # h   = kontrollens hoejde som tal eller Power Fx-udtryk. Forelderen
    #       bruger den til at regne sin egen hoejde ud - den laeses ALDRIG
    #       som .Height i en formel.
    # vis = Visible-udtryk, hvis kontrollen kan vaere skjult. Forelderen
    #       taeller den saa kun med, naar den er synlig.
    __slots__ = ("name", "control", "variant", "props", "children", "h", "_vis",
                 "_tpl_w", "_tpl_h", "_tpl_unc", "_grow")

    def __init__(self, name, control, variant=None, props=None, children=None, h=None, vis=None):
        self.name = name
        self.control = control
        self.variant = variant
        self.props = props or {}
        self.children = children or []
        self.h = h
        self._tpl_w = self._tpl_h = None
        self._tpl_unc = False
        self._grow = None      # mindstebredde, naar barnet tager resten
        self._vis = None
        if vis is not None:
            self.vis = vis

    # vis skrives IGENNEM til Visible-egenskaben.
    #
    # Foer var vis kun hoejde-algebraens felt, saa "ctrl.vis = udtryk" efter
    # konstruktionen fik forelderen til at regne rigtigt, men skrev ingen
    # Visible i YAML'en - kontrollen blev bare ved med at vaere synlig. Det
    # ramte handlingsknapperne i pakkematricen, og fejlen var usynlig i
    # builderen. Nu kan de to ikke komme ud af trit.
    @property
    def vis(self):
        return self._vis

    @vis.setter
    def vis(self, expr):
        self._vis = expr
        if expr is None:
            self.props.pop("Visible", None)
        else:
            self.props["Visible"] = expr


# ---------------------------------------------------------------------------
# Hoejde-algebra
# ---------------------------------------------------------------------------
def _is_num(v):
    return isinstance(v, (int, float))


def stack_height(children, gap, pad_t=0, pad_b=0):
    """Hoejden af en lodret AutoLayout-container.

    Taeller padding og gaps med, saa de ikke kan glemmes. Boern med en
    vis-betingelse bidrager kun naar de er synlige - AutoLayout udelader
    skjulte boern fra baade stakken og gaps.

    Foerste barn skal altid vaere synligt (i praksis altid en sektions-
    overskrift), saa gap-regnskabet gaar op.
    """
    const = pad_t + pad_b
    parts = []
    for i, c in enumerate(children):
        h = 0 if c.h is None else c.h
        g = 0 if i == 0 else gap
        if c.vis:
            parts.append(f"If({c.vis}, {g} + ({h}), 0)")
        elif _is_num(h):
            const += h + g
        else:
            parts.append(f"({h})" if g == 0 else f"{g} + ({h})")
    expr = str(int(const)) if float(const).is_integer() else str(const)
    for p in parts:
        expr += " + " + p
    return expr


def row_height(children, pad_t=0, pad_b=0, rows=1, gap=0):
    """Hoejden af en vandret AutoLayout-container: det hoejeste barn.

    rows > 1 bruges naar raekken ombryder (LayoutWrap) og skal have plads
    til flere linjer.
    """
    hs = [(0 if c.h is None else c.h) for c in children] or [0]
    if all(_is_num(h) for h in hs):
        base = max(hs)
        return int(pad_t + pad_b + base * rows + gap * (rows - 1))
    terms = ", ".join(f"({h})" for h in hs)
    base = f"Max({terms})" if len(hs) > 1 else terms
    return f"{pad_t + pad_b} + ({base}) * {rows} + {gap * (rows - 1)}"


def render(node, item_indent):
    pad = " " * item_indent
    lines = [f"{pad}- {node.name}:"]
    body_indent = item_indent + 4
    bpad = " " * body_indent
    lines.append(f"{bpad}Control: {node.control}")
    if node.variant:
        lines.append(f"{bpad}Variant: {node.variant}")
    if node.props:
        lines.append(f"{bpad}Properties:")
        prop_indent = body_indent + 2
        ppad = " " * prop_indent
        content_indent = prop_indent + 4
        cpad = " " * content_indent
        for key in sorted(node.props.keys()):
            val = node.props[key]
            if val is None:
                continue
            val = str(val)
            lines.append(f"{ppad}{key}: |-")
            first = True
            for raw_line in val.split("\n"):
                if first:
                    lines.append(f"{cpad}={raw_line}")
                    first = False
                else:
                    lines.append(f"{cpad}{raw_line}")
    if node.children:
        lines.append(f"{bpad}Children:")
        child_indent = body_indent + 2
        for child in node.children:
            lines.extend(render(child, child_indent))
    return lines


# ---------------------------------------------------------------------------
# Galleriernes skabeloner: bredde og hoejde skrives ud, ikke laest
# ---------------------------------------------------------------------------
# Parent.TemplateWidth gav 320 i Studio - containerens standardbredde, ikke
# galleriets. Listens raekke var derfor 320 px bred, beskrivelsen alene
# 460, og alt efter den (status, filer, knapperne) laa uden for raekken.
#
# Her regnes hver containers bredde ud fra RAMMEN og ned - padding og
# scrollbar trukket fra, Stretch respekteret - og skabelonens bredde og
# hoejde skrives som et udtryk. Kan en bredde ikke regnes ud, stopper
# byggeriet: saa er det ikke et gaet, der ender i Studio.
def _p(ctrl, key, default="0"):
    return str(ctrl.props.get(key, default)).strip()


def _num_or(expr, default=0):
    try:
        return float(expr)
    except ValueError:
        return None


def _inner(ctrl, cw):
    """Pladsen inden i en container med bredden cw."""
    pads = [_p(ctrl, "PaddingLeft"), _p(ctrl, "PaddingRight")]
    extra = SCROLLBAR_W if "Scroll" in _p(ctrl, "LayoutOverflowY", "") else 0
    terms = [x for x in pads if x not in ("0", "")]
    out = f"({cw})"
    for t in terms:
        out += f" - {t}"
    if extra:
        out += f" - {extra}"
    return out


def _stretches(parent, child):
    if parent is None or parent.control != "GroupContainer":
        return False
    d = _p(parent, "LayoutDirection", "")
    a = _p(parent, "LayoutAlignItems", "")
    own = _p(child, "AlignInContainer", "")
    return (d == "LayoutDirection.Vertical" and a == "LayoutAlignItems.Stretch"
            and not any(x in own for x in (".Start", ".Center", ".End")))


def resolve_templates(nodes, parent=None, parent_inner=None, uncertain=False):
    """uncertain: kommer bredden fra en Parent.Width-kaede?

    Saa er vores tal en NEDRE graense - ikke den bredde, platformen giver.
    Det er fint for en almindelig container, der bare bliver lidt smallere
    end noedvendigt. Men et GALLERIS skabelon faar sin bredde af Studio,
    og cellerne i rakken maales mod VORES tal. Er det for stort, ligger den
    sidste celle uden for rakken. Derfor traekkes GALLERY_RESERVE fra, naar
    kaeden er usikker."""
    for c in nodes:
        w = _p(c, "Width", "")
        unc = uncertain
        if parent is not None and parent.control == "Gallery":
            cw = parent._tpl_w
            unc = parent._tpl_unc
        elif _stretches(parent, c):
            cw = parent_inner
            unc = True                 # foraelderen straekker: vi gaetter
        elif w and "Parent." not in w:
            cw = w
            unc = False                # et tal, vi selv har skrevet
        elif w in ("Parent.Width", "App.Width") and parent is None:
            cw = "App.Width"
        elif w == "Parent.Width":
            cw = parent_inner          # nedre graense: pladsen, ikke egenskaben
            unc = True
        else:
            cw = None
        if parent is not None and parent.control == "Gallery":
            for key, val in (("Width", parent._tpl_w), ("Height", parent._tpl_h)):
                cur = _p(c, key, "")
                if "Parent.Template" in cur:
                    if val is None:
                        raise SystemExit(
                            f"gen_screen: {c.name}.{key} bruger Parent.Template*, men "
                            f"galleriet {parent.name}s {key.lower()} kan ikke regnes ud")
                    new = cur.replace(f"Parent.Template{key}", f"({val})")
                    c.props[key] = new
                    if key == "Height":
                        c.h = new
            cw = parent._tpl_w
        if c.control == "Gallery":
            pad = _p(c, "TemplatePadding", "0")
            size = _p(c, "TemplateSize", "0")
            sb = SCROLLBAR_W if _p(c, "ShowScrollbar", "false") == "true" else 0
            if c.variant == "Horizontal":
                c._tpl_w = size
                c._tpl_h = f"({_p(c, 'Height')}) - 2 * {pad}"
                c._tpl_unc = False
            else:
                res = GALLERY_RESERVE if unc else 0
                c._tpl_w = (None if cw is None
                            else f"({cw}) - 2 * {pad} - {sb}"
                                 + (f" - {res}" if res else ""))
                c._tpl_h = size
                c._tpl_unc = unc
            inner = cw
        else:
            inner = None if cw is None else _inner(c, cw)
        if c.children and inner is not None and c.control == "GroupContainer" \
                and "Horizontal" in _p(c, "LayoutDirection", ""):
            _resolve_grow(c, inner)
        if c.children:
            resolve_templates(c.children, c, inner, unc)


def _resolve_grow(row, inner):
    """Det barn, der skal tage RESTEN af en vandret raekke, faar en
    UDREGNET bredde - ikke FillPortions.

    FillPortions var den fleksible del i topbjaelken og i detaljepopuppens
    hoved. Begge steder stod knapperne ved siden af den og blev i Studio
    tegnet en linje for lavt - skaaret over af beholderens kant. Listens
    raekker har kun faste, udregnede bredder, og dér stod knapperne
    rigtigt. Derfor regnes resten ud her: pladsen inden i raekken (en nedre
    graense - padding og scrollbar er trukket fra) minus de andre boern og
    mellemrummene, minus 2 px luft."""
    kids = row.children
    growers = [k for k in kids if k._grow is not None]
    if not growers:
        return
    if len(growers) > 1:
        raise SystemExit(f"gen_screen: {row.name} har mere end eet barn, der "
                         f"skal tage resten ({', '.join(k.name for k in growers)})")
    g = growers[0]
    gap = _p(row, "LayoutGap", "0")
    terms = []
    for k in kids:
        if k is g:
            continue
        w = _p(k, "Width", "")
        if not w or "Parent." in w:
            raise SystemExit(f"gen_screen: {row.name}: {k.name} har ingen fast "
                             f"bredde ({w or 'ingen'}) - saa kan resten ikke regnes ud")
        t = f"({w}) + {gap}"
        terms.append(f"If({k.vis}, {t}, 0)" if k.vis else t)
    rest = f"({inner})" + "".join(f" - ({t})" for t in terms) + " - 2"
    g.props["Width"] = f"Max({g._grow}, {rest})"
    g.props["FillPortions"] = "0"
    g.props["LayoutMinWidth"] = str(g._grow)


# ---------------------------------------------------------------------------
# Galleriernes skabeloner: INGEN containere - alt placeres med X og Y
# ---------------------------------------------------------------------------
# Et galleris oeverste barn faar sin bredde af Studio, ikke af os (docs/30,
# regel J). Den blev aflaest som 320, som Parent.Width - og efter et deploy
# med --clean igen som 320. Stod raekkens celler i en container, blev alt
# efter de foerste 320 px skjult. Det skete tre gange i Equipment, og hver
# rettelse gjorde bare budgettet mindre.
#
# Derfor foldes hver container i et galleri UD, naar skaermen skrives:
# boernene placeres med X, Y og Width regnet af containerens egen retning,
# gap, padding og justering - den samme opstilling, autolayout ville have
# lavet. En container med Fill eller kant bliver til et Rectangle under
# boernene, med containerens navn. Builderne skriver stadig containere;
# de bliver bare aldrig til containere i et galleri.
#
# check_layout regel 26c stopper byggeriet, hvis en container alligevel
# staar i et galleri.
def _hv(ctrl):
    h = _p(ctrl, "Height", "")
    return h if h else str(ctrl.h if ctrl.h is not None else 0)


def _and(*exprs):
    parts = [e for e in exprs if e]
    if not parts:
        return None
    if len(parts) == 1:
        return parts[0]
    return " && ".join(f"({e})" for e in parts)


_LAYOUT_ONLY = ("AlignInContainer", "LayoutMinWidth", "LayoutMaxWidth",
                "FillPortions", "LayoutMinHeight", "LayoutMaxHeight")


def _background(c, x, y, w, h, vis):
    fill = c.props.get("Fill")
    border = c.props.get("BorderColor")
    if not fill and not border:
        return None
    props = {"X": x, "Y": y, "Width": w, "Height": h,
             "Fill": fill or TRANSPARENT,
             "BorderColor": border or TRANSPARENT,
             "BorderThickness": c.props.get("BorderThickness", "0"),
             "BorderStyle": ("BorderStyle.Solid" if border else "BorderStyle.None"),
             # Ren pynt (issue #45). En figur i et galleri faar
             # OnSelect = Select(Parent) af Studio og er dermed "interaktiv"
             # for tilgaengelighedstjekket: det meldte conVhpItemCard for
             # manglende AccessibleLabel og manglende tab stop. Uden OnSelect,
             # med TabIndex -1 og en tom etiket er den et billede, som
             # skaermlaeseren springer over - teksten staar i boernene.
             "OnSelect": "false",
             "TabIndex": "-1",
             "AccessibleLabel": "\"\""}
    if vis:
        props["Visible"] = vis
    return Ctrl(c.name, "Rectangle", props=props, h=h)


def _place(c, x, y, w, h, vis, out):
    """Placer c i boksen (x, y, w, h). w/h er None, naar c har sin egen."""
    own_vis = c.props.get("Visible")
    vis_all = _and(vis, own_vis)
    if c.control != "GroupContainer":
        c.props["X"] = x
        c.props["Y"] = y
        if w is not None:
            c.props["Width"] = w
        if h is not None:
            c.props["Height"] = h
            c.h = h
        if "Parent." in _p(c, "Width", ""):
            raise SystemExit(f"gen_screen: {c.name}.Width = {_p(c, 'Width')} i et "
                             f"galleri - bredden kan ikke placeres")
        for k in _LAYOUT_ONLY:
            c.props.pop(k, None)
        if vis_all:
            c.props["Visible"] = vis_all
        out.append(c)
        return
    if "true" in _p(c, "LayoutWrap", "false"):
        raise SystemExit(f"gen_screen: {c.name} ombryder i et galleri - kan ikke foldes ud")
    cw = w if w is not None else _p(c, "Width", "")
    ch = h if h is not None else _hv(c)
    if not cw or "Parent." in cw:
        raise SystemExit(f"gen_screen: {c.name} i et galleri har ingen bredde, "
                         f"der kan regnes ud ({cw or 'ingen'})")
    bg = _background(c, x, y, cw, ch, vis_all)
    if bg is not None:
        out.append(bg)
    pt, pr, pb, pl = (_p(c, "Padding" + k) for k in ("Top", "Right", "Bottom", "Left"))
    gap = _p(c, "LayoutGap", "0")
    iw = f"({cw}) - {pl} - {pr}"
    ih = f"({ch}) - {pt} - {pb}"
    align = _p(c, "LayoutAlignItems", "LayoutAlignItems.Stretch").split(".")[-1]
    justify = _p(c, "LayoutJustifyContent", "LayoutJustifyContent.Start").split(".")[-1]
    horiz = "Horizontal" in _p(c, "LayoutDirection", "")
    kids = c.children

    def span(k):
        return _p(k, "Width", "") if horiz else _hv(k)

    def step(k, g):
        t = f"({span(k)}) + {g}"
        v = k.props.get("Visible")
        return f"If({v}, {t}, 0)" if v else t

    if justify not in ("Start", "Center"):
        raise SystemExit(f"gen_screen: {c.name}: LayoutJustifyContent.{justify} "
                         f"i et galleri er ikke understoettet")
    offset = "0"
    if justify == "Center":
        total = " + ".join(step(k, gap) for k in kids) or "0"
        offset = f"((({iw if horiz else ih}) - ({total} - {gap})) / 2)"
    acc = []
    for k in kids:
        a = _p(k, "AlignInContainer", "")
        a = a.split(".")[-1] if a and "SetByContainer" not in a else align
        along = " + ".join([offset] + acc)
        kw = kh = None
        if horiz:
            kx = f"{x} + {pl} + {along}"
            if a == "Stretch":
                ky, kh = f"{y} + {pt}", ih
            elif a == "Center":
                ky = f"{y} + {pt} + (({ih}) - ({_hv(k)})) / 2"
            elif a == "End":
                ky = f"{y} + {pt} + ({ih}) - ({_hv(k)})"
            else:
                ky = f"{y} + {pt}"
        else:
            ky = f"{y} + {pt} + {along}"
            kwid = _p(k, "Width", "")
            if a == "Stretch" or "Parent." in kwid or not kwid:
                kx, kw = f"{x} + {pl}", iw
            elif a == "Center":
                kx = f"{x} + {pl} + (({iw}) - ({kwid})) / 2"
            elif a == "End":
                kx = f"{x} + {pl} + ({iw}) - ({kwid})"
            else:
                kx = f"{x} + {pl}"
        if horiz and "Parent." in _p(k, "Width", ""):
            raise SystemExit(f"gen_screen: {k.name}.Width = {_p(k, 'Width')} i en "
                             f"vandret raekke i et galleri")
        acc.append(step(k, gap))
        _place(k, kx, ky, kw, kh, vis_all, out)


def _gallery_checks(gal, siblings, row, leaves):
    """De to maalinger, check_layout lavede paa raekkecontaineren (regel 26
    og 29). Efter udfoldningen er der ingen raekke at maale paa, saa de
    laves HER, hvor raekken stadig kendes - med check_layout's egen
    evaluate(), saa tallene regnes paa samme maade som foer.

    26: hver synlig celle slutter inden for skabelonens bredde.
    29: en tabeloverskrift (soeskende med "Head" i navnet, kun ModernText,
        lige saa mange boern som raekken) har de samme bredder som raekken."""
    # tools/check_layout.py ved STIEN: hver build-mappe har en shim med
    # samme navn, og den staar foerst paa sys.path.
    import importlib.util
    import layout_tokens as lay
    spec = importlib.util.spec_from_file_location(
        "_tools_check_layout", os.path.join(HERE, "check_layout.py"))
    cl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cl)
    evaluate, WIDTHS = cl.evaluate, cl.WIDTHS
    problems = []
    widths = [w for w in WIDTHS if w >= lay.min_width("Tablet")]
    for w in widths:
        budget = evaluate(str(gal._tpl_w), w, 3, 4, 4) if gal._tpl_w else None
        if budget is None:
            break
        for k in leaves:
            vis = evaluate(k.props.get("Visible"), w, 3, 4, 4) if k.props.get("Visible") else True
            if vis is False:
                continue
            x = evaluate(_p(k, "X"), w, 3, 4, 4)
            kw = evaluate(_p(k, "Width", ""), w, 3, 4, 4)
            if x is None or kw is None:
                continue
            if x + kw > budget + 0.5:
                problems.append(f"[26] {gal.name}: {k.name} slutter ved {x + kw:.0f} px "
                                f"i en skabelon paa {budget:.0f} px (App.Width={w})")
                break
    if row is not None:
        for sib in siblings:
            hk = sib.children
            if ("Head" not in sib.name or sib.control != "GroupContainer" or not hk
                    or len(hk) != len(row.children)
                    or any(x.control != "ModernText" for x in hk)):
                continue
            for w in widths:
                for hc, rc in zip(hk, row.children):
                    hw = evaluate(_p(hc, "Width", ""), w, 3, 4, 4)
                    rw = evaluate(_p(rc, "Width", ""), w, 3, 4, 4)
                    if hw is not None and rw is not None and abs(hw - rw) >= 0.51:
                        problems.append(f"[29] {sib.name} og {row.name} flugter ikke ved "
                                        f"App.Width={w}: {hc.name} er {hw:.0f} px, "
                                        f"{rc.name} er {rw:.0f} px")
                        break
            break
    return problems


def flatten_galleries(nodes, problems=None):
    top = problems is None
    problems = [] if top else problems
    for c in nodes:
        if c.control == "Gallery":
            out, row = [], None
            for k in c.children:
                if k.control == "GroupContainer":
                    row = row or k
                    w = c._tpl_w if c._tpl_w is not None else _p(k, "Width", "")
                    _place(k, "0", "0", w, _hv(k), None, out)
                else:
                    out.append(k)
            problems += _gallery_checks(c, nodes, row, out)
            c.children = out
        if c.children:
            flatten_galleries(c.children, problems)
    if top and problems:
        raise SystemExit("gen_screen: gallerierne passer ikke:\n  " + "\n  ".join(problems))


def render_screen(screen_name, screen_props, children):
    resolve_templates(children)
    flatten_galleries(children)
    lines = ["Screens:", f"  {screen_name}:", "    Properties:"]
    ppad = " " * 6
    cpad = " " * 10
    for key in sorted(screen_props.keys()):
        val = str(screen_props[key])
        lines.append(f"{ppad}{key}: |-")
        first = True
        for raw_line in val.split("\n"):
            if first:
                lines.append(f"{cpad}={raw_line}")
                first = False
            else:
                lines.append(f"{cpad}{raw_line}")
    lines.append("    Children:")
    for child in children:
        lines.extend(render(child, 6))
    return "\n".join(lines) + "\n"


# Denne fil er et bibliotek. Den kan koeres, men goer ingenting - og det
# kostede en hel verifikationsrunde, hvor "python3 gen_screen.py" saa ud
# til at bygge skaermen igen uden at roere den. Nu siger den fra.
if __name__ == "__main__":
    import sys
    sys.exit("gen_screen.py er et bibliotek og bygger ingenting.\n"
             "Byg skaermen med: python3 assemble_screen.py\n"
             "Eller hele kaeden med: python3 tools/build_all.py")
