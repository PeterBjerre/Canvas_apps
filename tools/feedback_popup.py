# -*- coding: utf-8 -*-
"""
"Message us" popup - opened from the message icon in the sidebar (side_nav.py).

The user writes to the SAP maintenance mailbox. The mail is composed from the
user's own Outlook through a mailto link, so no connector is needed and the
message is sent as the user. A mailto link cannot carry file attachments;
the popup says so and the user adds them in Outlook.

The user's initials and email are read from the signed-in account. The
request the question is about is picked from the user's own requests in
MD_RequestIndex and written into the subject and the body.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import Ctrl, C_OVERLAY, C_MODAL_BG, C_PRIMARY_SOFT, C_MUTED, C_TITLE, child_name
from gen_screen import C_DISABLED_BG, C_DIVIDER
from build_helpers import (group, text_ctrl, button, text_input, input_theme,
                           fit_button_width, grow, ICON_W)
import layout_tokens as lay
import request_index as ri

OPEN = "gblFbOpen"
ME = "gblFbMe"
MAILBOX = "sapvedligehold@orsted.com"
SEND_FLOW = "'BioSap-SendFeedbackMail'"
OPEN_FX = (f"Set({ME}, Lower(User().Email)); Set({OPEN}, true)")
INITIALS = f'Upper(First(Split({ME}, "@")).Value)'

TEMPLATE_FX = ('"Hello SAP Maintenance Team," & Char(10) & Char(10) & "Request:" & Char(10) & '
               'Char(10) & Char(10) & "Kind regards," & Char(10) & Char(10) & User().FullName & '
               'Char(10) & User().Email')

REQUESTS = (f"FirstN(Sort(Filter('{ri.LIST}', RequesterEmail = {ME}), "
            "LastActionOn, SortOrder.Descending), 50)")


def _field(name, label, ctrl, width=None):
    lab = text_ctrl(child_name("txt", name, "Label"), f'"{label}"', size=12, color=C_MUTED,
                    weight="Semibold", height=20, wrap="false")
    return group(name, [lab, ctrl], direction="Vertical", gap=6,
                 width=width if width is not None else "Parent.Width")


def build(p):
    """[backdrop, popup] for one screen. p is the screen's name prefix."""
    vis = f"IfError({OPEN}, false)"
    n = lambda kind, base: f"{kind}{p}Fb{base}"
    cmbName = n("cmb", "Request")
    reset = f"Reset({cmbName}); Reset({n('inp', 'Message')})"

    title = grow(text_ctrl(n("txt", "Title"), '"Message SAP maintenance"', size=lay.SIZE_CARD_TITLE,
                           weight="Semibold", height=26, wrap="false"))
    btnClose = button(n("btn", "Close"), '"Close"', f"Set({OPEN}, false); {reset}", width=90, height=32)
    head = group(n("con", "Head"), [title, btnClose], direction="Horizontal", gap=12,
                 height=32, align_items="Center")

    intro = text_ctrl(n("txt", "Intro"),
                      f'"Questions, ideas or something not working? Your message goes to {MAILBOX}."',
                      size=13, color=C_MUTED, height=40, wrap="true")

    locked = {"PaddingLeft": "12", "VerticalAlign": "VerticalAlign.Middle",
              "BorderStyle": "BorderStyle.Solid", "BorderThickness": "1",
              "BorderColor": C_DIVIDER}
    inpInitials = text_ctrl(n("txt", "Initials"), INITIALS, size=14, color=C_MUTED, height=36,
                            fill=C_DISABLED_BG, accessible='"Your initials (locked)"', extra=locked)
    inpEmail = text_ctrl(n("txt", "Email"), ME, size=14, color=C_MUTED, height=36,
                         fill=C_DISABLED_BG, accessible='"Your email (locked)"', extra=locked)
    who = group(n("con", "Who"), [
        _field(n("con", "InitialsCell"), "Initials", inpInitials, width="110"),
        grow(_field(n("con", "EmailCell"), "Email", inpEmail), min_w=0),
    ], direction="Horizontal", gap=12, height=62, align_items="Start")

    typed = f"Trim({cmbName}.SearchText)"
    items = (f'Ungroup(Table({{r: Filter(Table({{Code: "", Display: {typed}}}), !IsBlank(Display))}}, '
             f'{{r: ForAll({REQUESTS} As R, {{Code: R.{ri.COL_NO}, '
             f'Display: R.{ri.COL_NO} & " - " & R.ShortText}})}}), r)')
    cmbRequest = Ctrl(cmbName, "ModernCombobox", props=input_theme({
        "AccessibleLabel": '"Request the message is about, or type your own subject"',
        "BorderStyle": "BorderStyle.Solid",
        "BorderThickness": "1",
        "Height": "36",
        "InputTextPlaceholder": '"Pick a request or type a subject"',
        "IsSearchable": "true",
        "ItemDisplayText": "ThisItem.Display",
        "Items": items,
        "LayoutMinWidth": "0",
        "SelectMultiple": "false",
        "Width": "Parent.Width",
        **lay.radius(lay.RADIUS_INPUT),
    }, None), h=36)
    about = _field(n("con", "RequestCell"), "About a request (optional)", cmbRequest)

    msg_h = f"If({lay.below('Tablet')}, 220, Max(220, Min(272, App.Height - 40 - 402)))"
    inpMessage = text_input(n("inp", "Message"), TEMPLATE_FX, placeholder='"Write your message"',
                            max_length=1200, height=220, ttype="Multiline",
                            label='"Message"')
    inpMessage.props["Height"] = msg_h
    inpMessage.h = msg_h
    message = _field(n("con", "MessageCell"), "Message", inpMessage)

    note = text_ctrl(n("txt", "Note"),
                     '"Send delivers the message from the app. Send via Outlook opens a draft where you can add attachments."',
                     size=12, color=C_MUTED, height=36, wrap="true")

    sel = f"{cmbName}.Selected"
    subject = (f'"SAP maintenance - " & If(IsBlank({sel}.Display), "question", '
               f'If(IsBlank({sel}.Code), {sel}.Display, "request " & {sel}.Code))')
    msg = f"{n('inp', 'Message')}.Text"
    top = f'Left({msg}, Find("Kind regards,", {msg} & "Kind regards,") - 1)'
    send_out = (f'Launch("mailto:{MAILBOX}?subject=" & EncodeUrl({subject}) & '
                f'"&body=" & EncodeUrl({top}));\n'
                f"Set({OPEN}, false);\n{reset};\n"
                'Notify("The mail is ready in Outlook. Press Send there.", NotificationType.Information)')
    send_app = (f'IfError({SEND_FLOW}.Run("{MAILBOX}", {subject}, '
                f'Substitute({msg}, Char(10), "<br>")), '
                'Notify("The message could not be sent.", NotificationType.Error), '
                f'Set({OPEN}, false); {reset}; '
                'Notify("Message sent.", NotificationType.Success))')
    blank = (f"If(IsBlank(Trim({msg})), "
             "DisplayMode.Disabled, DisplayMode.Edit)")
    btnOutlook = button(n("btn", "SendOutlook"), '"Send via Outlook"', send_out,
                        width=fit_button_width('"Send via Outlook"'), height=36, display_mode=blank)
    btnSend = button(n("btn", "Send"), '"Send"', send_app, primary=True,
                     width=fit_button_width('"Send"') + ICON_W, height=36, icon="Send",
                     display_mode=blank)
    footer = group(n("con", "Footer"), [btnOutlook, btnSend], direction="Horizontal", gap=8,
                   height=36, justify="End", align_items="Center")

    modal = group(n("con", "Modal"), [head, intro, who, about, message, note, footer],
                  direction="Vertical", gap=12, fill=C_MODAL_BG, border_color=C_PRIMARY_SOFT,
                  radius=lay.RADIUS_MODAL, pad=(18, 18, 18, 18),
                  width="Min(560, App.Width - 40)", drop_shadow="ExtraBold",
                  align_in_container="Center")
    backdrop = group(n("con", "Backdrop"), [modal], direction="Vertical", gap=0,
                     height="App.Height", width="App.Width", fill=C_OVERLAY, visible=vis,
                     justify="Start", align_items="Center", pad=(20, 0, 20, 0),
                     overflow_y="Scroll")
    backdrop.props["X"] = "0"
    backdrop.props["Y"] = "0"
    return [backdrop]
