# -*- coding: utf-8 -*-
"""
BESKEDER (TOAST) - EET STED FOR HELE APPEN (UX-review 2026-10, B1).

HVORFOR DEN HER FIL FINDES
--------------------------
Power Apps' Notify() tegner sit banner OEVERST paa skaermen, oven paa
headeren. I VH-planen klippede "Added 6 operation line(s) from tasklist."
titlen, og banneret kan hverken flyttes eller farves. Det kan ikke rettes
i et kald: banneret er platformens.

Derfor viser appen sine beskeder selv, nederst til hoejre:

    gblToast = { Text, Kind, At }      EEN global variabel for hele appen

  - Kind er "Success", "Warning", "Information" eller "Error".
  - Success, Warning og Information forsvinder efter TOAST_MS (4 s).
  - Error bliver staaende, til brugeren lukker den med krydset.
  - Krydset kan altid lukke beskeden foer tid.

Variablen er global, saa en besked overlever en Navigate: "Request
deleted." sat paa domaeneskaermen vises paa hubben, man lander paa.

HVORDAN DEN NAAR UD I SKAERMENE
-------------------------------
Ingen builder skal skrive den. gen_screen.render_screen() kalder
rewrite() paa hver formel: hvert Notify(besked, NotificationType.X) bliver
til et Set(gblToast, ...). Builderne og tools/messages.py skriver stadig
Notify - det er den kendte form, og den kan laeses. Toast-kontrollerne
(controls()) laegges paa hver skaerm af BIO SAP's bygger
(BIO SAP App/build/build_screens.py).

check_layout regel 39 stopper byggeriet, hvis et Notify( slipper igennem.

TYPEN BEVARES
-------------
Notify() giver true. Staar kaldet SIDST i et argument (If(c, Notify(..)),
IfError(x, Notify(..))), faar omskrivningen '; true' bagpaa, saa grenens
type er den samme som foer (check_layout regel 32). Staar det midt i en
kaede (Notify(..); Set(..)), er der ingen type at bevare.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import fx  # noqa: E402

VAR = "gblToast"
TOAST_MS = 4000
TICK_MS = 500
KINDS = ("Success", "Warning", "Information", "Error")

# Skemaet, App.OnStart giver variablen, saa typen er kendt fra start.
EMPTY = '{ Text: "", Kind: "", At: Now() }'


def onstart():
    """Linjen til App.OnStart (BIO SAP App/build/generate_app.py)."""
    return ("// Beskeder nederst til hoejre (tools/toast.py). Tom tekst = skjult.\n"
            f"Set({VAR}, {EMPTY})")


def show_fx(text_expr, kind="Success"):
    """Vis en besked. text_expr er et Power Fx-udtryk."""
    if kind not in KINDS:
        raise ValueError("toast: ukendt kind %r" % kind)
    return f'Set({VAR}, {{ Text: {text_expr}, Kind: "{kind}", At: Now() }})'


CLEAR = f"Set({VAR}, {EMPTY})"
VISIBLE = f'!IsBlank(IfError({VAR}.Text, ""))'
IS_ERROR = f'IfError({VAR}.Kind, "") = "Error"'

_NOTIFY = re.compile(r"\bNotify\s*\(")
_KIND = re.compile(r"^NotificationType\.(\w+)$")


def _code_positions(text):
    """Positionerne, der er kode (ikke streng/kommentar)."""
    return {i for i, _c in fx.walk(text)}


def rewrite(text):
    """Hvert Notify(...) i en formel -> Set(gblToast, ...).

    Et Notify med en ukendt form (et udtryk som type) stopper byggeriet -
    hellere det end en besked, der forsvinder."""
    if "Notify" not in text:
        return text
    out = []
    pos = 0
    code = _code_positions(text)
    for m in _NOTIFY.finditer(text):
        if m.start() < pos or m.start() not in code:
            continue
        open_at = m.end() - 1
        close = fx.matching_paren(text, open_at)
        if close < 0:
            raise SystemExit("toast.rewrite: Notify( lukkes aldrig:\n" + text[m.start():m.start() + 120])
        args = fx.call_args(text, open_at)
        msg = args[0].strip()
        kind = "Information"
        if len(args) > 1:
            k = _KIND.match(args[1].strip())
            if not k:
                raise SystemExit("toast.rewrite: Notify med en type, der ikke er "
                                 "NotificationType.X: %s" % args[1].strip())
            kind = k.group(1)
        # Beskeden kan selv indeholde et Notify? Nej - men omskriv den alligevel.
        msg = rewrite(msg)
        new = show_fx(msg, kind)
        # Sidst i et argument? Saa skal typen (true) bevares.
        rest = text[close + 1:]
        nxt = rest.lstrip()[:1]
        if nxt in (",", ")") or nxt == "":
            new += "; true"
        out.append(text[pos:m.start()])
        out.append(new)
        pos = close + 1
    out.append(text[pos:])
    return "".join(out)


# ---------------------------------------------------------------------------
# Kontrollerne
# ---------------------------------------------------------------------------
TOAST_W = 420
TOAST_H = 64
EDGE = 24


def _icon_svg():
    import icons
    from design_tokens import ref_hex
    hx = lambda t: '" & %s & "' % ref_hex(t)
    info = icons._RING + " M12 11v5.5M12 7.5v.01"
    shapes = {
        "Success": (icons.STATUS_READY, "state-ok-fg"),
        "Warning": (icons.STATUS_AWAITING, "state-warn-fg"),
        "Error": (icons.STATUS_REJECTED, "state-error-fg"),
    }
    branches = []
    for kind, (path, tok) in shapes.items():
        branches.append(f'"{kind}", "' + icons.svg(path, hx(tok), size=20) + '"')
    default = '"' + icons.svg(info, hx("state-info-fg"), size=20) + '"'
    body = f"Switch(IfError({VAR}.Kind, \"\"), " + ", ".join(branches) + f", {default})"
    return f'"data:image/svg+xml;utf8," & EncodeUrl({body})'


def controls(tag):
    """[kort, timer] - laegges paa skaermen efter alt andet, saa kortet
    ligger oeverst (men under ventespinneren, som skaermen laegger sidst).

    tag er skaermens infiks (Md, Vhp, Eq ...), saa navnene er unikke i
    appen."""
    from gen_screen import (Ctrl, C_MODAL_BG, C_CARD_BORDER, C_TITLE, C_MUTED,
                            C_BORDER_ERROR, C_TRANSPARENT)
    from build_helpers import group, text_ctrl, button, grow
    vis = VISIBLE
    icon = Ctrl(f"img{tag}ToastIcon", "Image", props={
        "AccessibleLabel": f'IfError({VAR}.Kind, "Message")',
        "AlignInContainer": "AlignInContainer.Center",
        "BorderStyle": "BorderStyle.None",
        "BorderThickness": "0",
        "Height": "20",
        "Image": _icon_svg(),
        "ImagePosition": "ImagePosition.Fit",
        "OnSelect": "false",
        "TabIndex": "0",
        "Width": "20",
    }, h=20)
    icon.props["LayoutMinWidth"] = "20"
    text = grow(text_ctrl(f"txt{tag}ToastText", f'IfError({VAR}.Text, "")', size=13,
                          color=C_TITLE, height=40, wrap="true",
                          extra={"VerticalAlign": "VerticalAlign.Middle"}))
    close = button(f"btn{tag}ToastClose", '""', CLEAR, width=32, height=32,
                   icon="Dismiss", accessible='"Close the message"')
    close.props["Layout"] = "ButtonLayout.IconOnly"
    # Outline uden synlig kant - den knaptype, appen allerede bruger
    # (build_helpers.button); en ny Appearance er ikke afproevet i Studio.
    close.props["BorderColor"] = C_TRANSPARENT
    close.props["Color"] = C_MUTED
    close.props["Tooltip"] = '"Close"'
    close.props["LayoutMinWidth"] = "32"
    card = group(f"con{tag}Toast", [icon, text, close], direction="Horizontal", gap=10,
                 height=TOAST_H, align_items="Center", fill=C_MODAL_BG,
                 border_color=f"If({IS_ERROR}, {C_BORDER_ERROR}, {C_CARD_BORDER})",
                 radius=10, pad=(8, 8, 8, 14), drop_shadow="Bold",
                 width=f"Min({TOAST_W}, App.Width - 32)", visible=vis)
    card.props["X"] = f"Max(16, App.Width - Self.Width - {EDGE})"
    card.props["Y"] = f"App.Height - Self.Height - {EDGE}"
    # Timeren taeller kun, mens en besked, der skal forsvinde, er synlig.
    # Den laeser alderen af beskeden (At) - saa en ny besked midt i en
    # anden faar sine egne fire sekunder.
    timer = Ctrl(f"tmr{tag}Toast", "Timer", props={
        "AutoPause": "true",
        "AutoStart": "false",
        "Duration": str(TICK_MS),
        "Height": "1",
        "OnTimerEnd": (f"If(\n    {vis} && !({IS_ERROR}) &&\n"
                       f"    DateDiff({VAR}.At, Now(), TimeUnit.Milliseconds) >= {TOAST_MS},\n"
                       f"    {CLEAR}\n)"),
        "Repeat": "true",
        "Start": f"{vis} && !({IS_ERROR})",
        "Visible": "false",
        "Width": "1",
    }, h=1, vis="false")
    return [card, timer]
