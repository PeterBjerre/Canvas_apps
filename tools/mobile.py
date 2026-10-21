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


def chevron_toggle(name, title, var, default_open=False, on_select_extra=None):
    """Chevronknappen: 44 x 44 (TOUCH), kun paa mobil. Ned = lukket, op =
    aaben. Skaermlaeseren faar "Expand <title>" / "Collapse <title>"."""
    from build_helpers import icon_button  # cirkulaer import undgaas
    st = state(var, default_open)
    fx = "Set(%s, !%s)" % (var, st)
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
                size=None):
    """En sektion, der kan klappes sammen PAA MOBIL. Returnerer en LISTE:

        [overskrift (kun mobil), *children]

    Listen saettes direkte ind, hvor children stod foer - der kommer ingen
    ny container om dem, saa tablet og desktop er uaendrede (overskriften
    er skjult dér, og boernene er synlige som foer).

    Paa mobil: overskriften er titlen, en kort opsummering (summary, en
    Power Fx-tekst, der vises, mens sektionen er lukket) og chevronen.
    Boernene vises kun, mens sektionen er aaben. var er en global variabel
    (Set); blank = default_open, saa der skal intet i OnStart."""
    from build_helpers import text_ctrl, group, grow, label_px
    from gen_screen import C_TITLE, C_MUTED
    size = size or lay.SIZE_INPUT
    t = text_ctrl("txt%sFoldTitle" % prefix, '"%s"' % title, size=size, weight="Semibold",
                  color=C_TITLE, height=lay.TOUCH_MIN - 20, wrap="false")
    t.props["Width"] = str(label_px(title, size) + 4)
    t.props["LayoutMinWidth"] = t.props["Width"]
    kids = [t]
    if summary:
        s = grow(text_ctrl("txt%sFoldSummary" % prefix, summary, size=lay.SIZE_SMALL,
                           color=C_MUTED, height=20, wrap="false", align="Right"))
        s.vis = "!%s" % state(var, default_open)
        s.props["Visible"] = s.vis
        kids.append(s)
    else:
        kids.append(grow(group("con%sFoldGap" % prefix, [], direction="Horizontal", height=0)))
    kids.append(chevron_toggle("btn%sFold" % prefix, title, var, default_open))
    head = group("con%sFold" % prefix, kids, direction="Horizontal", gap=8,
                 height=TOUCH, align_items="Center", visible=MOBILE)
    for c in children:
        _and_vis(c, shown(var, default_open))
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
