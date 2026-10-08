# -*- coding: utf-8 -*-
"""
"Message us" popup - opened from the message icon in the sidebar (side_nav.py).

The user writes to the SAP maintenance mailbox. The mail is sent by the
flow BioSap-SendFeedbackMail from the service account SVC_BioSap (issue
#189) - the same Outlook connection reference (orsted_BioSapOutlookConn,
embedded) as the Issue Board and approval mails. The user's own Outlook is
never used: no mailto link, no connector of the user's. The flow writes the
signed-in user (from Power Apps' header) at the top of the mail and sets
Reply-To to them, so the team can answer the user directly.

Files chosen in the popup go with the mail as attachments (JSON with the
files as data URIs - the flow turns them back into binaries).

The user's initials and email are read from the signed-in account.

EMNE ELLER ANMODNING (issue #116)
---------------------------------
Feltet "Subject or request" er en knap, der folder en lille liste ud med
to grupper: "General" (faste emner) og "Your requests" (brugerens egne
anmodninger fra MD_RequestIndex, med domaenets ikon og farve). En
ModernCombobox kan hverken vise et ikon eller en gruppeoverskrift pr.
raekke, saa listen er et galleri.

Anmodningerne hentes EEN gang, naar popuppen aabnes (OPEN_FX): et
delegerbart filter paa RequesterEmail (indekseret), sorteret paa
LastActionOn (indekseret), de nyeste REQ_LIMIT. En slettet anmodning har
ingen indeksraekke (tools/request_delete.py), saa den kommer aldrig med.
Soegningen koerer lokalt paa den hentede liste og spoerger ikke SharePoint
for hvert tastetryk.

Valget gemmes som en record i gblFbSel (Kind, Code, Label, TypeName, Domain,
Title, Url) og bruges direkte i mailens emne og - som JSON (CONTEXT_FX) - i
flowets "Context"-input. Flowet bygger selv mailens emne-/anmodningsafsnit
og linket (AppUrl fra MD_RequestIndex) ud fra den (issue #194); beskeden
sendes uaendret som ren tekst og escapes i flowet.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import Ctrl, C_OVERLAY, C_MODAL_BG, C_PRIMARY_SOFT, C_MUTED, C_TITLE, child_name
from gen_screen import C_DISABLED_BG, C_DIVIDER, C_INPUT_BG, C_INPUT_FG, C_PRIMARY, C_TRANSPARENT, FONT
from design_tokens import ref as _t, ref_hex
from build_helpers import (group, text_ctrl, button, text_input,
                           fit_button_width, grow, row_hit, ICON_W)
import layout_tokens as lay
import request_index as ri
import icons
import doc_upload as du

OPEN = "gblFbOpen"
ME = "gblFbMe"
SEL = "gblFbSel"      # det valgte emne eller anmodning (record), Blank = intet valgt
PICK = "gblFbPick"    # listen er foldet ud
REQS = "colFbRequests"
MAILBOX = "sapvedligehold@orsted.com"
SEND_FLOW = "'BioSap-SendFeedbackMail'"
BUSY = "gblFbBusy"    # flowet koerer - Send er spaerret, saa intet sendes to gange
# Vedhaeftninger: faa og smaa nok til, at JSON-kaldet (base64) og mailen
# holder sig langt under Outlook-forbindelsens graenser.
MAX_FILES = 3
MAX_FILE_MB = 5
INITIALS = f'Upper(First(Split({ME}, "@")).Value)'

# Brugerens egne anmodninger - aktive og historiske, nyeste foerst.
REQ_LIMIT = 100

# Domaenet (valgvaerdien i MD_RequestIndex.Domain) -> (noegle i
# tools/icons.DOMAIN, engelsk navn). Ikon og farve er de faelles.
DOMAIN_INFO = {
    "FunctionalLocation": ("functionallocation", "Functional location"),
    "Equipment":          ("equipment",          "Equipment"),
    "MeasuringPoint":     ("measuringpoint",     "Measuring point"),
    "Material":           ("material",           "Material"),
    "MaintenancePlan":    ("vhplan",             "Maintenance plan"),
}
if set(DOMAIN_INFO) != set(ri.DOMAINS):
    raise SystemExit("feedback_popup.DOMAIN_INFO skal daekke request_index.DOMAINS")

# De faste emner. Popuppen er til spoergsmaal, ideer og fejl (se
# intro-teksten) - fire emner, der ikke overlapper.
GENERAL = ("Question", "Improvement idea", "Technical issue", "Other")

# Over saa mange anmodninger faar listen et soegefelt.
SEARCH_MIN = 6
ROW_H = 36
MAX_ROWS = 7


def _type_fx(domain_expr):
    return ("Switch(" + domain_expr + ", " +
            ", ".join(f'"{k}", "{v[1]}"' for k, v in DOMAIN_INFO.items()) +
            ', "Request")')


_COLLECT = (f"ClearCollect({REQS}, ForAll(FirstN(Sort(Filter('{ri.LIST}', RequesterEmail = {ME}), "
            f"LastActionOn, SortOrder.Descending), {REQ_LIMIT}) As R, "
            f'{{Code: R.{ri.COL_NO}, Title: Coalesce(R.ShortText, ""), Domain: R.Domain.Value, '
            f"TypeName: {_type_fx('R.Domain.Value')}, Url: Coalesce(R.AppUrl, \"\")}}))")

OPEN_FX = (f"Set({ME}, Lower(User().Email)); Set({PICK}, false); Set({BUSY}, false); "
           f"{_COLLECT}; Set({OPEN}, true)")

# Ingen tom "Request:"-linje mere (issue #116): en valgt anmodning saettes
# ind som en kontekstblok ved afsendelse (CONTEXT_FX).
TEMPLATE_FX = ('"Hello SAP Maintenance Team," & Char(10) & Char(10) & '
               'Char(10) & Char(10) & "Kind regards," & Char(10) & Char(10) & User().FullName & '
               'Char(10) & User().Email')

# Valget til flowets "Context"-input (issue #194): flowet viser et fast
# emne i overskriften og - kun for en anmodning - et afsnit med nummer,
# type, titel og link. Beskeden selv faar ingen kontekstblok mere. Et tomt
# valg giver null-felter, som flowet laeser som tomme.
CONTEXT_FX = (f'JSON({{Kind: {SEL}.Kind, Topic: {SEL}.Label, Code: {SEL}.Code, '
              f'Type: {SEL}.TypeName, Title: {SEL}.Title, Url: {SEL}.Url}}, JSONFormat.Compact)')

SUBJECT_FX = (f'"SAP maintenance - " & Switch({SEL}.Kind, '
              f'"R", {SEL}.TypeName & " request " & {SEL}.Code, '
              f'"G", {SEL}.Label, "question")')

# Typografien for en valgmulighed - i listen og i den lukkede vaelger.
ROW_TEXT_SIZE = lay.SIZE_BODY
ROW_TEXT_PX = 7     # gennemsnitlig tegnbredde i den stoerrelse (til _fit)
CHEVRON_DOWN = icons.CHEVRON_DOWN
CHEVRON_UP = icons.CHEVRON_UP


def _hx(token):
    return '" & %s & "' % ref_hex(token)


def _icon_fx(domain_expr):
    """Domaenets ikon i domaenets farve - de faelles ikoner (tools/icons.py)."""
    cases = ", ".join(
        f'"{k}", "' + icons.stroke_svg(key, _hx(icons.token(key)), size=20) + '"'
        for k, (key, _n) in DOMAIN_INFO.items())
    return f'"data:image/svg+xml;utf8," & EncodeUrl(Switch({domain_expr}, {cases}, ""))'


def _accent_fx(domain_expr):
    """Valgmarkeringen: domaenets farve for en anmodning, ellers primaer."""
    return ("Switch(" + domain_expr + ", " +
            ", ".join(f'"{k}", {_t(icons.token(v[0]))}' for k, v in DOMAIN_INFO.items()) +
            f", {C_PRIMARY})")


def _chevron_svg(path):
    """Pilen - den faelles tegning og streg (tools/icons.py, issue #139)."""
    return icons.svg(path, _hx('text-muted'), size=20)


def _fit(text, width, px=7.5):
    """Teksten afkortet med ... til bredden, saa intet klippes midt i et
    tegn. px er en gennemsnitlig tegnbredde for Segoe UI i den brugte
    stoerrelse."""
    return (f"With({{t: {text}, c: RoundDown(({width}) / {px}, 0)}}, "
            'If(Len(t) > c, Left(t, Max(1, c - 3)) & "...", t))')


def _rec(kind, label, code='""', typ='""', domain='""', title='""', url='""'):
    return (f'{{Kind: "{kind}", Code: {code}, Label: {label}, TypeName: {typ}, '
            f'Domain: {domain}, Title: {title}, Url: {url}}}')


def _field(name, label, ctrl, width=None):
    lab = text_ctrl(child_name("txt", name, "Label"), f'"{label}"', size=12, color=C_MUTED,
                    weight="Semibold", height=20, wrap="false")
    return group(name, [lab, ctrl], direction="Vertical", gap=6,
                 width=width if width is not None else "Parent.Width")


def _subject_picker(n):
    """Feltet "Subject or request": knappen og den udfoldede liste."""
    toggle = f"Set({PICK}, !{PICK})"
    has = f"!IsBlank({SEL}.Kind)"
    is_req = f'{SEL}.Kind = "R"'

    icon = Ctrl(n("img", "SubjectIcon"), "Image", props={
        "AccessibleLabel": '"Choose a subject or request"', "BorderStyle": "BorderStyle.None", "BorderThickness": "0",
        "Fill": C_TRANSPARENT, "Height": "20", "Image": _icon_fx(f"{SEL}.Domain"),
        "ImagePosition": "ImagePosition.Fit", "OnSelect": toggle, "TabIndex": "0",
        "Visible": is_req, "Width": "20",
    }, h=20, vis=is_req)
    label = f'If({has}, {SEL}.Label, "Pick a subject or request")'
    # Den valgte vaerdi har samme typografi som teksten i den udfoldede
    # liste (SubjectRow: SIZE_BODY, normal vaegt, samme tegnbredde i _fit) -
    # paa alle skaermbredder (issue #140). Knappen er ikke et tekstfelt, saa
    # iOS-zoom-reglen bag SIZE_INPUT_MOBILE gaelder ikke her.
    size = str(ROW_TEXT_SIZE)
    btn = Ctrl(n("btn", "Subject"), "Classic/Button", props={
        "Align": "Align.Left",
        "BorderColor": C_TRANSPARENT, "BorderStyle": "BorderStyle.None", "BorderThickness": "0",
        "Color": f"If({has}, {C_INPUT_FG}, {C_MUTED})",
        "Fill": C_TRANSPARENT,
        "FocusedBorderColor": C_PRIMARY, "FocusedBorderThickness": "2",
        "Font": FONT, "FontWeight": "FontWeight.Normal",
        "Height": "34",
        "HoverBorderColor": C_TRANSPARENT, "HoverColor": f"If({has}, {C_INPUT_FG}, {C_MUTED})",
        "HoverFill": C_TRANSPARENT,
        "OnSelect": toggle,
        "PaddingBottom": "0", "PaddingLeft": "0", "PaddingRight": "0", "PaddingTop": "0",
        "PressedBorderColor": C_TRANSPARENT, "PressedColor": f"If({has}, {C_INPUT_FG}, {C_MUTED})",
        "PressedFill": C_TRANSPARENT,
        "Size": size,
        "TabIndex": "0",
        "Text": _fit(label, "Self.Width", ROW_TEXT_PX),
        "VerticalAlign": "VerticalAlign.Middle",
    }, h=34)
    chevron = Ctrl(n("img", "SubjectChevron"), "Image", props={
        "AccessibleLabel": f'If({PICK}, "Collapse list", "Expand list")', "BorderStyle": "BorderStyle.None", "BorderThickness": "0",
        "Fill": C_TRANSPARENT, "Height": "20",
        "Image": (f'"data:image/svg+xml;utf8," & EncodeUrl(If({PICK}, '
                  f'"{_chevron_svg(CHEVRON_UP)}", "{_chevron_svg(CHEVRON_DOWN)}"))'),
        "ImagePosition": "ImagePosition.Fit", "OnSelect": toggle, "TabIndex": "0",
        "Width": "20",
    }, h=20)
    trigger = group(n("con", "Subject"), [icon, grow(btn), chevron], direction="Horizontal",
                    gap=8, height=36, align_items="Center", pad=(0, 10, 0, 12),
                    fill=C_INPUT_BG, border_color=f"If({PICK}, {C_PRIMARY}, {C_DIVIDER})",
                    radius=lay.RADIUS_INPUT)

    # Soegefeltet - kun naar der er nok anmodninger til, at det hjaelper.
    find_name = n("inp", "SubjectFind")
    find = text_input(find_name, '""', placeholder='"Search number, title or type"',
                      label='"Search your requests"')
    many = f"CountRows({REQS}) > {SEARCH_MIN}"
    find_wrap = group(n("con", "SubjectFind"), [find], direction="Vertical", gap=0,
                      pad=(0, 0, 6, 0), visible=many)

    q = f"Trim({find_name}.Text)"
    general = "Table(" + ", ".join(f'{{Label: "{g}"}}' for g in GENERAL) + ")"
    head_general = _rec("H", '"General"')
    head_requests = _rec("H", '"Your requests"')
    gen_row = _rec("G", "G.Label")
    req_row = _rec("R", 'R.Code & If(IsBlank(R.Title), "", " · " & R.Title)',
                   "R.Code", "R.TypeName", "R.Domain", "R.Title", "R.Url")
    empty_row = _rec("E", 'If(IsBlank(q), "You have no requests yet.", "No requests match your search.")')
    items = (
        f"With({{q: {q}}},\n"
        f"    With({{\n"
        f"        g: Filter({general}, IsBlank(q) || q in Label),\n"
        f"        r: Filter({REQS}, IsBlank(q) || q in Code || q in Title || q in TypeName)\n"
        "    },\n"
        "    Ungroup(Table(\n"
        f"        {{x: Filter(Table({head_general}), !IsEmpty(g))}},\n"
        f"        {{x: ForAll(g As G, {gen_row})}},\n"
        f"        {{x: Table({head_requests})}},\n"
        f"        {{x: ForAll(r As R, {req_row})}},\n"
        f"        {{x: Filter(Table({empty_row}), IsEmpty(r))}}\n"
        "    ), x)))"
    )

    kind = "ThisItem.Kind"
    pickable = f'{kind} = "G" || {kind} = "R"'
    selected = f"{has} && {kind} = {SEL}.Kind && ThisItem.Label = {SEL}.Label"
    head = text_ctrl(n("txt", "SubjectHead"), "ThisItem.Label", size=lay.SIZE_MICRO,
                     color=C_MUTED, weight="Semibold", height=18, wrap="false",
                     visible=f'{kind} = "H"',
                     width="Parent.TemplateWidth - 24", extra={"X": "12", "Y": str(ROW_H - 22)})
    accent = Ctrl(n("rct", "SubjectAccent"), "Rectangle", props={
        "AccessibleLabel": '"Selected"', "BorderStyle": "BorderStyle.None", "BorderThickness": "0",
        "Fill": _accent_fx("ThisItem.Domain"), "Height": "24", "OnSelect": "false",
        "TabIndex": "0", "Visible": selected, "Width": "3", "X": "0", "Y": str((ROW_H - 24) // 2),
    }, h=24, vis=selected)
    row_icon = Ctrl(n("img", "SubjectRowIcon"), "Image", props={
        "AccessibleLabel": 'Coalesce(ThisItem.TypeName, "Request")', "BorderStyle": "BorderStyle.None", "BorderThickness": "0",
        "Fill": C_TRANSPARENT, "Height": "20", "Image": _icon_fx("ThisItem.Domain"),
        "ImagePosition": "ImagePosition.Fit", "OnSelect": "false", "TabIndex": "0",
        "Visible": f'{kind} = "R"', "Width": "20", "X": "12", "Y": str((ROW_H - 20) // 2),
    }, h=20, vis=f'{kind} = "R"')
    text_x = f'If({kind} = "R", 40, 12)'
    text_w = f"Parent.TemplateWidth - {text_x} - 12"
    row_text = text_ctrl(n("txt", "SubjectRow"), _fit("ThisItem.Label", "Self.Width", ROW_TEXT_PX),
                         size=ROW_TEXT_SIZE, color=f'If({kind} = "E", {C_MUTED}, {C_TITLE})',
                         height=20, wrap="false", visible=f'{kind} <> "H"',
                         width=text_w, extra={"X": text_x, "Y": str((ROW_H - 20) // 2)})
    # weight er et udtryk, ikke et navn
    row_text.props["FontWeight"] = f"If({selected}, FontWeight.Semibold, FontWeight.Normal)"
    pick = (f"Set({SEL}, {{Kind: ThisItem.Kind, Code: ThisItem.Code, Label: ThisItem.Label, "
            "TypeName: ThisItem.TypeName, Domain: ThisItem.Domain, Title: ThisItem.Title, "
            "Url: ThisItem.Url}); "
            f"Set({PICK}, false)")
    hit_label = (f'If({kind} = "R", "Request " & ThisItem.Code & ", " & ThisItem.TypeName & '
                 '", " & ThisItem.Title, ThisItem.Label)')
    hit = row_hit(n("btn", "SubjectPick"), pick, hit_label, "Parent.TemplateWidth", ROW_H, radius=6)
    hit.props["Visible"] = pickable
    hit.vis = pickable

    gal_name = n("gal", "Subject")
    gal_h = f"Min({gal_name}.AllItemsCount, {MAX_ROWS}) * {ROW_H}"
    gal = Ctrl(gal_name, "Gallery", variant="Vertical", props={
        "AccessibleLabel": '"Subjects and your requests"',
        "BorderStyle": "BorderStyle.None", "Fill": C_TRANSPARENT, "FillPortions": "0",
        "Height": gal_h,
        "Items": items, "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None",
        "Selectable": "false", "ShowScrollbar": "true", "TabIndex": "0",
        "TemplatePadding": "0", "TemplateSize": str(ROW_H),
        "Width": "Parent.Width", "WrapCount": "1",
    }, children=[head, accent, row_icon, row_text, hit], h=gal_h)

    panel = group(n("con", "SubjectList"), [find_wrap, gal], direction="Vertical", gap=0,
                  pad=(6, 6, 6, 6), fill=C_MODAL_BG, border_color=C_DIVIDER,
                  radius=lay.RADIUS_INPUT, visible=PICK)

    lab = text_ctrl(n("txt", "SubjectLabel"), '"Subject or request (optional)"', size=12,
                    color=C_MUTED, weight="Semibold", height=20, wrap="false")
    cell = group(n("con", "SubjectCell"), [lab, trigger, panel], direction="Vertical", gap=6)
    return cell, find_name


def build(p):
    """[backdrop, popup] for one screen. p is the screen's name prefix."""
    vis = f"IfError({OPEN}, false)"
    n = lambda kind, base: f"{kind}{p}Fb{base}"

    about, find_name = _subject_picker(n)
    files = n("att", "Files")
    reset = (f"Set({SEL}, Blank()); Set({PICK}, false); Reset({find_name}); "
             f"Reset({n('inp', 'Message')}); Reset({files})")

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

    # Vedhaeftningsfeltet (issue #189) staar paa den gamle notes plads
    # (36): etiket 20 + 6, vaelgeren, 6 + loftteksten 18. Beskeden giver
    # forskellen fra sig, naar skaermen er lav.
    extra = f"({du.picker_height(files)} + 50 - 36)"
    msg_h = (f"If({lay.below('Tablet')}, 220, Max(160, Min(272, App.Height - 40 - 402 - {extra})))")
    inpMessage = text_input(n("inp", "Message"), TEMPLATE_FX, placeholder='"Write your message"',
                            max_length=1200, height=220, ttype="Multiline",
                            label='"Message"')
    inpMessage.props["Height"] = msg_h
    inpMessage.h = msg_h
    message = _field(n("con", "MessageCell"), "Message", inpMessage)
    # Mens listen er foldet ud, staar den paa beskedens plads - saa passer
    # popuppen stadig paa en telefon. Teksten i feltet bevares.
    message.props["Visible"] = f"!{PICK}"
    message.vis = f"!{PICK}"

    # Filerne gaar med mailen fra servicekontoen (issue #189) - den gamle
    # "Send via Outlook" (mailto) er vaek.
    picker = du.picker(files, '"Files to attach to the message"', MAX_FILES, MAX_FILE_MB,
                       display_mode=f"If({BUSY}, DisplayMode.Disabled, DisplayMode.Edit)")
    limits = du.limits_text(n("txt", "FileLimits"), MAX_FILES, MAX_FILE_MB)
    attach = _field(n("con", "FilesCell"), "Attachments (optional)",
                    group(n("con", "FilesBody"), [picker, limits], direction="Vertical", gap=6))
    attach.props["Visible"] = f"!{PICK}"
    attach.vis = f"!{PICK}"

    msg = f"{n('inp', 'Message')}.Text"
    # Flowet sender fra SVC_BioSap og svarer {sent, message}. En afvisning
    # (sent = "no") og en fejl i kaldet giver begge fejlbeskeden; popuppen
    # bliver staaende med teksten, saa intet gaar tabt.
    run = (f'{SEND_FLOW}.Run("{MAILBOX}", {SUBJECT_FX}, {msg}, '
           f"JSON({files}.Attachments, JSONFormat.IncludeBinaryData), {CONTEXT_FX})")
    send_app = (f"Set({BUSY}, true);\n"
                f"IfError(\n"
                f"    With({{ res: {run} }},\n"
                '        If(res.sent = "yes",\n'
                f"            Set({OPEN}, false); {reset}; "
                'Notify("Message sent.", NotificationType.Success),\n'
                '            Notify("The message could not be sent. " & res.message, NotificationType.Error))),\n'
                '    Notify("The message could not be sent.", NotificationType.Error));\n'
                f"Set({BUSY}, false)")
    blank = (f"If(IsBlank(Trim({msg})) || {BUSY}, "
             "DisplayMode.Disabled, DisplayMode.Edit)")
    btnSend = button(n("btn", "Send"), '"Send"', send_app, primary=True,
                     width=fit_button_width('"Send"') + ICON_W, height=36, icon="Send",
                     display_mode=blank)
    footer = group(n("con", "Footer"), [btnSend], direction="Horizontal", gap=8,
                   height=36, justify="End", align_items="Center")

    modal = group(n("con", "Modal"), [head, intro, who, about, message, attach, footer],
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
