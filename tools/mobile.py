# -*- coding: utf-8 -*-
"""
MOBILFUNDAMENTET (issue #508) - de faelles byggeklodser til telefonen.

"Mobil" er den eksisterende tier under Tablet: App.Width < 720, altsaa
LayoutRank = 1 (tools/layout_tokens.py, MOBILE). Alt her skriver sine
mobilvaerdier som If(LayoutRank < 2, <mobil>, <som foer>), saa tablet og
desktop er praecis, som de var. Brug lay.mobile_or() til enkeltvaerdier.

HVAD DER ALLEREDE ER FAELLES (og derfor ikke staar her)
------------------------------------------------------
  * rammen (build_helpers.app_frame): MOBILE_PAD_X i siderne, lavere header,
    MOBILE_GAP mellem kortene. SHELL_W regner med den paa mobil.
  * kortet (build_helpers.card): MOBILE_CARD_PAD i siderne.
  * sidepanelet (build_helpers.row_editor_panel): fuld skaerm under Desktop
    (PANEL_W_AT); paa mobil MOBILE_PAD_X i siderne og ingen ekstra polstring
    om formularen. Overskriften med Luk og pilene staar fast oeverst.
  * bundbjaelken (build_helpers.sticky_actions): under Desktop.
  * bekraeftelser (build_helpers.confirm_modal, text_modal): popup_w og
    mobile_footer - knapperne staar under hinanden i fuld bredde.
  * klikflader: H.hit er 44 under Desktop (build_helpers.ensure_hit).

HER
---
  collapsible()      en sektion, der kan klappes sammen paa mobil (chevron)
  chevron_toggle()   kun chevronknappen - til en eksisterende overskrift
  mobile_popup()     en popup i (naesten) fuld bredde paa mobil
  full_screen()      et sidepanel/overlag, der er hele skaermen paa mobil
  touch()            en knap, der er mindst TOUCH_MIN hoej paa mobil
  sheet_y()          Y for en popup paa mobil: oeverst med lidt luft
  find()             en kontrol i et byggetrae, ud fra navnet
  refit()            regn en containers hoejde om efter en mobilhoejde
  gallery_place()    X/Y/bredde/hoejde i en galleriraekke paa mobil (kort)
  hide_on_mobile()   skjul en kontrol paa mobil
  restack()          regn containernes hoejder om paa mobil (efter mobilhoejder)
  phone_stack()      en vandret raekke, der staar lodret paa mobil
  set_phone_h()      en anden hoejde paa mobil (Height + mh)
  split()/phone()/desk()  grenene af If(LayoutRank < 2, m, d)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import layout_tokens as lay  # noqa: E402
import icons as _icons  # noqa: E402
from design_tokens import ref_hex  # noqa: E402

MOBILE = lay.MOBILE
NOT_MOBILE = "!(%s)" % MOBILE
mobile_or = lay.mobile_or
popup_w = lay.popup_w
PAD_X = lay.MOBILE_PAD_X
GAP = lay.MOBILE_GAP
CARD_PAD = lay.MOBILE_CARD_PAD
TOUCH = lay.TOUCH_MIN
POP_MARGIN = lay.MOBILE_POP_MARGIN


def state(var, default_open=False):
    """Er sektionen aaben? Blank (aldrig sat) = default_open."""
    return "Coalesce(%s, %s)" % (var, "true" if default_open else "false")


def shown(var, default_open=False):
    """Synlig fra Tablet og op - og paa mobil, naar sektionen er aaben."""
    return "(%s || %s)" % (NOT_MOBILE, state(var, default_open))


def _and_vis(ctrl, cond):
    v = ctrl.props.get("Visible")
    ctrl.vis = cond if not v else "%s && (%s)" % (cond, v)
    return ctrl


def chevron_toggle(name, title, var, default_open=False, on_select_extra=None,
                   open_expr=None):
    """Chevronknappen: 44 x 44 (TOUCH), kun paa mobil. Ned = lukket, op =
    aaben. Skaermlaeseren faar "Expand <title>" / "Collapse <title>".
    open_expr: et eget udtryk for "aaben" (standard state(var, default_open))
    - fx naar standarden afhaenger af andet end en fast vaerdi. Et tryk
    saetter var til det modsatte af udtrykket."""
    from build_helpers import icon_button  # cirkulaer import undgaas
    st = open_expr or state(var, default_open)
    # !(...) om et eget udtryk: ! binder staerkere end && (test_not_precedence).
    fx = "Set(%s, !%s)" % (var, "(%s)" % st if open_expr else st)
    if on_select_extra:
        fx += ";\n" + on_select_extra
    btn = icon_button(name, "Expand %s" % title, fx, _icons.CHEVRON_DOWN)
    grey = '" & %s & "' % ref_hex("text-primary")
    up = _icons.svg(_icons.CHEVRON_UP, grey, size=20, box=TOUCH)
    down = _icons.svg(_icons.CHEVRON_DOWN, grey, size=20, box=TOUCH)
    btn.props["Image"] = ('"data:image/svg+xml;utf8," & EncodeUrl(If(%s, "%s", "%s"))'
                          % (st, up, down))
    lab = 'If(%s, "Collapse %s", "Expand %s")' % (st, title, title)
    btn.props["AccessibleLabel"] = lab
    btn.props["Tooltip"] = lab
    btn.props["LayoutMinWidth"] = btn.props["Width"]
    btn.props["AlignInContainer"] = "AlignInContainer.Center"
    _and_vis(btn, MOBILE)
    return btn


def collapsible(prefix, title, children, var, default_open=False, summary=None,
                size=None, open_expr=None):
    """En sektion, der kan klappes sammen PAA MOBIL. Returnerer en LISTE:

        [overskrift (kun mobil), *children]

    Listen saettes direkte ind, hvor children stod foer - der kommer ingen
    ny container om dem, saa tablet og desktop er uaendrede (overskriften
    er skjult dér, og boernene er synlige som foer).

    Paa mobil: overskriften er titlen, en kort opsummering (summary, en
    Power Fx-tekst, der vises, mens sektionen er lukket) og chevronen.
    Boernene vises kun, mens sektionen er aaben. var er en global variabel
    (Set); blank = default_open, saa der skal intet i OnStart. open_expr:
    se chevron_toggle (fase 3, FL-sidepanelets sektioner)."""
    from build_helpers import text_ctrl, group, grow, label_px
    from gen_screen import C_TITLE, C_MUTED
    size = size or lay.SIZE_INPUT
    t = text_ctrl("txt%sFoldTitle" % prefix, '"%s"' % title, size=size, weight="Semibold",
                  color=C_TITLE, height=lay.TOUCH_MIN - 20, wrap="false")
    t.props["Width"] = str(label_px(title, size) + 4)
    t.props["LayoutMinWidth"] = t.props["Width"]
    kids = [t]
    if summary:
        # To linjer (fase 6): ved 320 px er der ofte kun ca. 110 px til
        # opsummeringen ved siden af titlen og chevronen.
        s = grow(text_ctrl("txt%sFoldSummary" % prefix, summary, size=lay.SIZE_SMALL,
                           color=C_MUTED, height=20, wrap="false", align="Right"))
        # Overskriften ses kun paa mobil; grenene holder Tablet/Desktop ens.
        s.props["Height"] = mobile_or(TOUCH - 8, 20)
        s.h = s.props["Height"]
        s.props["Wrap"] = mobile_or("true", "false")
        s.vis = "!%s" % (open_expr or state(var, default_open))
        s.props["Visible"] = s.vis
        kids.append(s)
    else:
        kids.append(grow(group("con%sFoldGap" % prefix, [], direction="Horizontal", height=0)))
    kids.append(chevron_toggle("btn%sFold" % prefix, title, var, default_open,
                               open_expr=open_expr))
    head = group("con%sFold" % prefix, kids, direction="Horizontal", gap=8,
                 height=TOUCH, align_items="Center", visible=MOBILE)
    vis = ("(%s || %s)" % (NOT_MOBILE, open_expr)) if open_expr else shown(var, default_open)
    for c in children:
        _and_vis(c, vis)
    return [head, *children]


def mobile_popup(modal, max_w=None, margin=24, top=None):
    """En popup (en container med X/Y paa skaermen) i naesten fuld bredde paa
    mobil: App.Width - 2 x POP_MARGIN, centreret, og siderne polstret med
    CARD_PAD. max_w/margin: popuppens bredde fra Tablet og op - udelades de,
    beholdes dens nuvaerende Width. top: saa staar den oeverst paa mobil
    (sheet_y) i stedet for sin egen Y - til popupper med meget indhold."""
    from build_helpers import mobile_pad
    cur = modal.props.get("Width")
    desk = "Min(%s, App.Width - %s)" % (max_w, margin) if max_w is not None else cur
    modal.props["Width"] = mobile_or("App.Width - %d" % (2 * POP_MARGIN), desk)
    modal.props["X"] = "(App.Width - Self.Width) / 2"
    if top:
        modal.props["Y"] = sheet_y(modal.props.get("Y", "0"))
    mobile_pad(modal, x=CARD_PAD)
    return modal


def sheet_y(desk_y):
    """Y paa mobil: lige under kanten (POP_MARGIN), ellers desk_y."""
    return mobile_or(str(POP_MARGIN), desk_y)


def full_screen(panel, desk_x=None, desk_w=None, pad_x=PAD_X):
    """Et sidepanel/overlag, der er HELE skaermen paa mobil: X = 0, Y = 0,
    App.Width x App.Height, polstret med pad_x i siderne. Overskriften
    (med Luk/Tilbage) skal vaere panelets foerste barn og ligge uden for
    det, der scroller - som i row_editor_panel."""
    from build_helpers import mobile_pad
    panel.props["Width"] = mobile_or("App.Width", desk_w or panel.props.get("Width"))
    panel.props["X"] = mobile_or("0", desk_x or panel.props.get("X", "0"))
    panel.props["Y"] = mobile_or("0", panel.props.get("Y", "0"))
    mobile_pad(panel, x=pad_x)
    return panel


def find(node, name):
    """Kontrollen med navnet name i traeet under node (node selv med) -
    til at efterjustere en kontrol, en faelles bygger har lavet."""
    if node.name == name:
        return node
    for c in node.children or ():
        hit = find(c, name)
        if hit is not None:
            return hit
    return None


def refit(box):
    """Regn en containers hoejde om af boernene - efter at et barn har
    faaet en mobilhoejde, EFTER containeren blev bygget (group() regner
    hoejden ved bygningen). Kun containere uden fast hoejde."""
    from build_helpers import stack_height, row_height
    p = box.props
    gap = p.get("LayoutGap", "0")
    gap = int(gap) if str(gap).isdigit() else gap
    pt, pb = p.get("PaddingTop", "0"), p.get("PaddingBottom", "0")
    pt = int(pt) if str(pt).isdigit() else pt
    pb = int(pb) if str(pb).isdigit() else pb
    if "Vertical" in p.get("LayoutDirection", "Vertical"):
        h = stack_height(box.children, gap, pt, pb)
    else:
        h = row_height(box.children, pt, pb, rows=1, gap=gap)
    p["Height"] = str(h)
    box.h = h
    return box


def gallery_place(ctrl, x=None, y=None, w=None, h=None):
    """Placeringen af en kontrol i en galleriraekke PAA EN TELEFON (X, Y,
    bredde, hoejde i skabelonens koordinater). gen_screen._place laegger
    dem uden om den udregnede placering, naar raekken foldes ud - saa en
    tabelraekke kan vaere et kort paa to linjer paa en telefon, mens
    tablet og desktop er uaendrede. Kun i et galleri."""
    m = {}
    for k, v in (("X", x), ("Y", y), ("Width", w), ("Height", h)):
        if v is not None:
            m[k] = str(v)
    ctrl.props["_Mobile"] = m
    return ctrl


def hide_on_mobile(ctrl):
    """Skjult paa en telefon, ellers som foer."""
    v = ctrl.props.get("Visible")
    ctrl.vis = mobile_or("false", v or "true")
    return ctrl


def touch(btn):
    """En knap med tekst, der er mindst TOUCH hoej paa mobil (bredden roeres
    ikke). Ikonknapper bruger build_helpers.ensure_hit (H.hit)."""
    h = btn.props.get("Height", "36")
    try:
        if int(h) >= TOUCH:
            return btn
    except ValueError:
        pass
    btn.props["Height"] = mobile_or(TOUCH, h)
    btn.h = btn.props["Height"]
    return btn


# ---------------------------------------------------------------------------
# HOEJDER PAA EN TELEFON (fase 4: Materials, Equipment, Measuring Point)
#
# group() regner en containers hoejde af boernene, NAAR den bygges. Faar et
# barn bagefter en anden hoejde paa mobil (felterne 44 i stedet for 36, en
# sektion, der er klappet sammen), passer foraelderens hoejde ikke laengere.
# restack() regner hele traeet om nedefra - kun mobilgrenen:
#
#     Height = If(LayoutRank < 2, <mobilhoejden>, <som foer>)
#
# og kun dér, hvor de to er forskellige. Tablet og desktop er uroerte.
# Containere med en FAST hoejde (scroll, popupper, flow_row) springes over -
# de skal have deres mobilhoejde (mh) givet af den, der byggede dem.
# ---------------------------------------------------------------------------
def split(expr):
    """(mobil, ellers) for et udtryk af formen If(LayoutRank < 2, m, d) -
    ellers None. Kun et If, der er HELE udtrykket."""
    s = str(expr).strip()
    pre = "If(%s, " % MOBILE
    if not (s.startswith(pre) and s.endswith(")")):
        return None
    inner = s[len(pre):-1]
    depth, quote, parts, start = 0, False, [], 0
    for i, ch in enumerate(inner):
        if ch == '"':
            quote = not quote
        elif quote:
            continue
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
            if depth < 0:
                return None
        elif ch == "," and depth == 0:
            parts.append(inner[start:i].strip())
            start = i + 1
    parts.append(inner[start:].strip())
    return (parts[0], parts[1]) if len(parts) == 2 else None


def phone(expr):
    """Vaerdien paa en telefon: mobilgrenen, hvis udtrykket er en mobil-If."""
    sp = split(expr)
    return sp[0] if sp else expr


def desk(expr):
    """Vaerdien fra Tablet og op: ellers-grenen af en mobil-If."""
    sp = split(expr)
    return sp[1] if sp else expr


def _num(v):
    try:
        f = float(str(v))
    except ValueError:
        return v
    return int(f) if f.is_integer() else f


def phone_h(ctrl):
    """Kontrollens hoejde paa en telefon (mh, ellers h's mobilgren)."""
    if ctrl.mh is not None:
        return ctrl.mh
    return _num(phone(ctrl.h if ctrl.h is not None else ctrl.props.get("Height", 0)))


def set_phone_h(ctrl, h):
    """Giv ctrl en anden hoejde paa en telefon. Height bliver en mobil-If om
    den hoejde, den har fra Tablet og op; h (foraeldrenes algebra) roeres
    ikke, saa tablet og desktop regner som foer."""
    cur = ctrl.props.get("Height", ctrl.h)
    d = desk(cur)
    if str(_num(h)).replace(" ", "") == str(d).replace(" ", ""):
        ctrl.props["Height"] = str(d)
    else:
        ctrl.props["Height"] = mobile_or(h, d)
    ctrl.mh = _num(h)
    return ctrl


class _Proxy:
    """Et barn, som hoejde-algebraen ser det paa en telefon."""
    __slots__ = ("h", "vis")

    def __init__(self, h, vis):
        self.h, self.vis = h, vis


def restack(node):
    """Regn mobilhoejderne om i hele traeet under node (node selv med) og
    returner nodes hoejde paa en telefon. Se afsnittet ovenfor."""
    from gen_screen import stack_height, row_height
    kids = node.children or []
    hs = [restack(c) for c in kids]
    if node.control != "GroupContainer" or not kids or not node._auto:
        return phone_h(node)
    direction, built = node._auto
    if str(node.props.get("Height")) != str(built) and node.mh is None:
        # Nogen har givet containeren en anden hoejde efter group() - den
        # er ikke laengere boernenes, saa den roeres ikke.
        return phone_h(node)
    p = node.props
    pt, pb = _num(phone(p.get("PaddingTop", 0))), _num(phone(p.get("PaddingBottom", 0)))
    gap = _num(phone(p.get("LayoutGap", 0)))
    lay_dir = phone(p.get("LayoutDirection", "LayoutDirection.%s" % direction))
    if not all(isinstance(x, (int, float)) for x in (pt, pb, gap)):
        return phone_h(node)
    proxies = [_Proxy(h, c.vis) for c, h in zip(kids, hs)]
    wraps = str(phone(p.get("LayoutWrap", "false"))).lower() == "true"
    if "Vertical" in lay_dir or (wraps and direction == "Vertical"):
        # En raekke, der ombryder paa mobil, og som er markeret lodret
        # (_auto), har boern i hele bredden: een pr. linje.
        h = stack_height(proxies, gap, pt, pb)
    elif wraps:
        return phone_h(node)   # ombrydning: kan ikke regnes her
    else:
        h = row_height(proxies, pt, pb)
    if str(_num(h)).replace(" ", "") != str(_num(desk(p["Height"]))).replace(" ", ""):
        set_phone_h(node, h)
    return _num(h)


def phone_stack(box, gap=None):
    """En vandret (evt. ombrydende) container, der staar LODRET paa en
    telefon - eet barn pr. linje. restack regner dens hoejde paa mobil.
    gap: mellemrummet paa mobil (standard: det samme som ellers)."""
    p = box.props
    p["LayoutDirection"] = mobile_or("LayoutDirection.Vertical",
                                     desk(p.get("LayoutDirection", "LayoutDirection.Horizontal")))
    if "LayoutWrap" in p:
        p["LayoutWrap"] = mobile_or("false", desk(p["LayoutWrap"]))
    if gap is not None:
        p["LayoutGap"] = mobile_or(gap, desk(p.get("LayoutGap", "0")))
    p["LayoutAlignItems"] = mobile_or("LayoutAlignItems.Stretch",
                                      desk(p.get("LayoutAlignItems", "LayoutAlignItems.Start")))
    # Som om group() havde regnet hoejden: restack maa regne den om.
    box._auto = ("Vertical", p["Height"])
    return box


# ---------------------------------------------------------------------------
# LISTER UDEN EGEN SCROLL (fase 5: KKS Lookup og Issue Board)
#
# En lang liste paa en telefon er SIDENS scroll - galleriet er saa hoejt som
# de kort, det viser, og har ingen scrollbar. Saa ingen indlejret scroll. For
# ikke at tegne tusind kort paa een gang viser galleriet de foerste
# show_count() raekker (FirstN i Items paa mobil), og knappen "Show more"
# under listen viser SHOW_STEP til. Fra Tablet og op er listen som foer.
# ---------------------------------------------------------------------------
SHOW_STEP = 50


def show_count(var, step=SHOW_STEP):
    """Antallet af raekker, listen viser paa en telefon (blank = step)."""
    return "Coalesce(%s, %d)" % (var, step)


def show_more(name, var, total, step=SHOW_STEP, label="items"):
    """Knappen under en liste paa en telefon: "Show 50 more (120 left)".
    Kun paa mobil og kun, naar der er flere raekker end vist. total: Power
    Fx for det samlede antal (samme raekker, som listen viser)."""
    from build_helpers import button
    n = show_count(var, step)
    left = "(%s - %s)" % (total, n)
    vis = "%s && %s > %s" % (MOBILE, total, n)
    btn = button(name, '"Show " & Min(%d, %s) & " more (" & %s & " left)"' % (step, left, left),
                 "Set(%s, %s + %d)" % (var, n, step), width=200, height=TOUCH,
                 icon="ChevronDown", visible=vis,
                 accessible='"Show " & Min(%d, %s) & " more %s, " & %s & " not shown yet"'
                            % (step, left, label, left))
    btn.props["AlignInContainer"] = "AlignInContainer.Stretch"
    btn.props["LayoutMinWidth"] = "0"
    return btn
