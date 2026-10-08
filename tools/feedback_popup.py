# -*- coding: utf-8 -*-
"""
"Message us" popup - opened from the message icon in the sidebar (side_nav.py).

The user writes to the SAP maintenance mailbox. Send (the primary button)
runs the flow BioSap-SendFeedbackMail from the service account SVC_BioSap
(issue #189) - the same Outlook connection reference
(orsted_BioSapOutlookConn, embedded) as the Issue Board and approval mails.
The flow writes the signed-in user at the top of the mail and sets Reply-To
to them, so the team can answer the user directly.

"Send via Outlook" (issue #205) is the old mailto draft from before #189:
subject, the chosen request and the message open in the user's own Outlook.
No connector is involved. A mailto link cannot carry files, so the button
is disabled while files are attached, and the popup says why.

Files go with Send as attachments (JSON with the files as data URIs - the
flow turns them back into binaries). They are chosen in a separate
"Attach files" popup (issue #205); the paperclip button shows how many.

TEGN (issue #205): afsendernavnet kom fra Power Apps' header
x-ms-user-name, og en HTTP-header baerer ikke ae/oe/aa - de blev til "?".
Navnet sendes nu med i Context-JSON'en (User().FullName, UTF-8 i
kaldets krop), og flowet bruger det foer headeren.

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
ATT = "gblFbAtt"      # vedhaeftningspopuppen er aaben (issue #205)
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
           f"Set({ATT}, false); {_COLLECT}; Set({OPEN}, true)")

# Ingen tom "Request:"-linje mere (issue #116): en valgt anmodning saettes
# ind som en kontekstblok ved afsendelse (CONTEXT_FX).
TEMPLATE_FX = ('"Hello SAP Maintenance Team," & Char(10) & Char(10) & '
               'Char(10) & Char(10) & "Kind regards," & Char(10) & Char(10) & User().FullName & '
               'Char(10) & User().Email')

# Valget til flowets "Context"-input (issue #194): flowet viser et fast
# emne i overskriften og - kun for en anmodning - et afsnit med nummer,
# type, titel og link. Beskeden selv faar ingen kontekstblok mere. Et tomt
# valg giver null-felter, som flowet laeser som tomme.
# Name er brugerens navn (issue #205): i kaldets krop er det UTF-8, mens
# headeren x-ms-user-name gav "?" for ae, oe og aa.
CONTEXT_FX = (f'JSON({{Kind: {SEL}.Kind, Topic: {SEL}.Label, Code: {SEL}.Code, '
              f'Type: {SEL}.TypeName, Title: {SEL}.Title, Url: {SEL}.Url, '
              'Name: User().FullName}, JSONFormat.Compact)')

# "Send via Outlook" (issue #205): den gamle kontekstblok fra foer #189 -
# en mailto-krop er ren tekst, saa anmodningen staar som linjer foer
# beskeden. Linket kommer med, naar anmodningen har et.
OUTLOOK_CONTEXT_FX = (f'If({SEL}.Kind = "R", "Request: " & {SEL}.Code & Char(10) & '
                      f'"Type: " & {SEL}.TypeName & Char(10) & "Title: " & {SEL}.Title & Char(10) & '
                      f'If(IsBlank({SEL}.Url), "", "Link: " & {SEL}.Url & Char(10)) & Char(10), "")')

SUBJECT_FX = (f'"SAP maintenance - " & Switch({SEL}.Kind, '
              f'"R", {SEL}.TypeName & " request " & {SEL}.Code, '
              f'"G", {SEL}.Label, "question")')

# Typografien for en valgmulighed i den udfoldede liste (uaendret).
ROW_TEXT_SIZE = lay.SIZE_BODY
ROW_TEXT_PX = 7     # gennemsnitlig tegnbredde i den stoerrelse (til _fit)

# Den LUKKEDE vaelger (issue #205) har formularfelternes typografi:
# 14 px, 16 px under Tablet (input_theme). Knappen er en Classic/Button, og
# en klassisk kontrols Size er i PUNKTER, mens de moderne felters er i
# pixels - SIZE_BODY (13) blev derfor ca. 17 px, stoerre end felterne
# omkring den. 1 pt = 4/3 px.
def _pt(px):
    v = px * 0.75
    return str(int(v)) if v == int(v) else str(v)


SUBJECT_SIZE = lay.if_below("Tablet", _pt(lay.SIZE_INPUT_MOBILE), _pt(lay.SIZE_INPUT))
SUBJECT_PX = lay.if_below("Tablet", "8.2", "7.2")   # tegnbredde i den stoerrelse (til _fit)
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


def _subject_picker(n, avail):
    """Feltet "Subject or request": (cellen med knappen, den udfoldede
    liste, soegefeltets navn). avail er den hoejde, listen maa fylde under
    knappen - den ligger OVEN PAA formularen (issue #205), ikke i den."""
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
    # Pladsholderen og den valgte vaerdi har de andre felters typografi
    # (issue #205, se SUBJECT_SIZE): normal vaegt, een linje, ... til sidst.
    size = SUBJECT_SIZE
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
        "Text": _fit(label, "Self.Width", SUBJECT_PX),
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
    # Listen holder sig inden for den plads, der er under knappen, og
    # scroller resten (issue #205).
    gal_h = (f"Min(Min({gal_name}.AllItemsCount, {MAX_ROWS}) * {ROW_H}, "
             f"{avail} - 12 - If({many}, 42, 0))")
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
    cell = group(n("con", "SubjectCell"), [lab, trigger], direction="Vertical", gap=6)
    return cell, panel, find_name


# Raekken med vedhaeftningsknappen (issue #205) og hoejden af det, der staar
# under knappen "Subject or request": cellen er etiket 20 + 6 + knap 36.
SUBJECT_CELL_H = 62
ATTACH_ROW_H = 36
# Listen ligger 4 px under knappen.
LIST_Y = SUBJECT_CELL_H + 4


def _no_flex(ctrl, x, y):
    """Et barn af en ManualLayout-container: X og Y i stedet for
    AutoLayout-egenskaberne."""
    for k in ("FillPortions", "LayoutMinWidth", "AlignInContainer"):
        ctrl.props.pop(k, None)
    ctrl.props["X"] = str(x)
    ctrl.props["Y"] = str(y)
    ctrl.props["Width"] = "Parent.Width"
    return ctrl


def _attach_popup(n, files, close_fx):
    """Vedhaeftningspopuppen (issue #205): den faelles klassiske filvaelger
    (doc_upload) med loftet. Den skjules med Visible og fjernes aldrig, saa
    de valgte filer bliver i kontrollen, naar popuppen lukkes og aabnes
    igen. Close er eneste lukkehandling og nulstiller intet."""
    vis = f"IfError({OPEN} && {ATT}, false)"
    title = grow(text_ctrl(n("txt", "AttTitle"), '"Attach files"', size=lay.SIZE_CARD_TITLE,
                           weight="Semibold", height=26, wrap="false"))
    close = button(n("btn", "AttClose"), '"Close"', close_fx, width=90, height=32)
    head = group(n("con", "AttHead"), [title, close], direction="Horizontal", gap=12,
                 height=32, align_items="Center")
    intro = text_ctrl(n("txt", "AttIntro"),
                      '"The files go with the message when you press Send."',
                      size=13, color=C_MUTED, height=40, wrap="true")
    picker = du.picker(files, '"Files to attach to the message"', MAX_FILES, MAX_FILE_MB,
                       display_mode=f"If({BUSY}, DisplayMode.Disabled, DisplayMode.Edit)")
    limits = du.limits_text(n("txt", "FileLimits"), MAX_FILES, MAX_FILE_MB)
    modal = group(n("con", "AttModal"), [head, intro, picker, limits],
                  direction="Vertical", gap=12, fill=C_MODAL_BG, border_color=C_PRIMARY_SOFT,
                  radius=lay.RADIUS_MODAL, pad=(18, 18, 18, 18),
                  width="Min(480, App.Width - 40)", drop_shadow="ExtraBold",
                  align_in_container="Center")
    backdrop = group(n("con", "AttBackdrop"), [modal], direction="Vertical", gap=0,
                     height="App.Height", width="App.Width", fill=C_OVERLAY, visible=vis,
                     justify="Start", align_items="Center", pad=(20, 0, 20, 0),
                     overflow_y="Scroll")
    backdrop.props["X"] = "0"
    backdrop.props["Y"] = "0"
    return backdrop


def build(p):
    """[backdrop, attachments backdrop] for one screen. p is the screen's
    name prefix."""
    vis = f"IfError({OPEN}, false)"
    n = lambda kind, base: f"{kind}{p}Fb{base}"

    # Beskedens hoejde: det faste i popuppen (402 - samme regnestykke som
    # foer #189, hvor vedhaeftningsraekken staar paa notens plads) og
    # resten til beskeden. Den afhaenger IKKE af, om listen er foldet ud
    # (issue #205), saa popuppen staar stille.
    msg_h = f"If({lay.below('Tablet')}, 220, Max(160, Min(272, App.Height - 40 - 402)))"
    # Pladsen under vaelgerens knap: resten af cellen, beskeden og
    # vedhaeftningsraekken.
    avail = f"({msg_h}) + {12 + 26 + 12 + ATTACH_ROW_H - 4}"
    about, panel, find_name = _subject_picker(n, avail)
    files = n("att", "Files")
    n_files = f"CountRows({files}.Attachments)"
    reset = (f"Set({SEL}, Blank()); Set({PICK}, false); Set({ATT}, false); Reset({find_name}); "
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

    inpMessage = text_input(n("inp", "Message"), TEMPLATE_FX, placeholder='"Write your message"',
                            max_length=1200, height=220, ttype="Multiline",
                            label='"Message"')
    inpMessage.props["Height"] = msg_h
    inpMessage.h = msg_h
    message = _field(n("con", "MessageCell"), "Message", inpMessage)

    # Papirclipsen (issue #205): aabner vedhaeftningspopuppen og viser,
    # hvor mange filer der er valgt. Det store upload-felt er vaek fra
    # formularen.
    attach_text = f'If({n_files} = 0, "Attach files", "Attach files (" & {n_files} & ")")'
    attach_w = fit_button_width('"Attach files (3)"') + ICON_W
    btnAttach = button(n("btn", "Attach"), attach_text, f"Set({PICK}, false); Set({ATT}, true)",
                       width=attach_w, height=ATTACH_ROW_H, icon=icons.FLUENT["attach"],
                       accessible=(f'If({n_files} = 0, "Attach files", '
                                   f'"Attach files, " & {n_files} & " attached")'),
                       display_mode=f"If({BUSY}, DisplayMode.Disabled, DisplayMode.Edit)")
    btnAttach.props["LayoutMinWidth"] = str(attach_w)
    # mailto kan ikke baere filer - det siges, i stedet for at de forsvinder.
    outlook_note = text_ctrl(n("txt", "OutlookNote"), '"Send via Outlook can\'t include files."',
                             size=lay.SIZE_SMALL, color=C_MUTED, height=ATTACH_ROW_H, wrap="true",
                             visible=f"{n_files} > 0",
                             extra={"VerticalAlign": "VerticalAlign.Middle"})
    attach_row = group(n("con", "AttachRow"), [btnAttach, grow(outlook_note)],
                       direction="Horizontal", gap=12, height=ATTACH_ROW_H, align_items="Center")

    # Formularen under "Subject or request" og listen OVEN PAA den
    # (issue #205): en ManualLayout-container, hvor listen ligger sidst
    # (= oeverst). Formularen beholder sin hoejde og sine vaerdier, naar
    # listen foldes ud; listen er kun saa hoej, som der er plads til
    # (avail), og scroller resten.
    form = group(n("con", "Form"), [about, message, attach_row], direction="Vertical", gap=12)
    _no_flex(form, 0, 0)
    _no_flex(panel, 0, LIST_Y)
    area = Ctrl(n("con", "Area"), "GroupContainer", variant="ManualLayout", props={
        "BorderStyle": "BorderStyle.None", "DropShadow": "DropShadow.None",
        "FillPortions": "0", "Height": str(form.h), "LayoutMinWidth": "0",
        "Width": "Parent.Width",
    }, children=[form, panel], h=form.h)

    msg = f"{n('inp', 'Message')}.Text"
    # Flowet sender fra SVC_BioSap og svarer {sent, message}. En afvisning
    # (sent = "no") og en fejl i kaldet giver begge fejlbeskeden; popuppen
    # bliver staaende med teksten, saa intet gaar tabt.
    # Kun Name og Value: kontrollens Attachments-tabel har ogsaa en skjult
    # kolonne af typen Control, som JSON ikke kan serialisere (compile-fejl
    # "nested property ... of type 'Control'" ved deploy).
    files_json = (f"JSON(ForAll({files}.Attachments, {{Name: ThisRecord.Name, Value: ThisRecord.Value}}), "
                  "JSONFormat.IncludeBinaryData)")
    run = (f'{SEND_FLOW}.Run("{MAILBOX}", {SUBJECT_FX}, {msg}, '
           f"{files_json}, {CONTEXT_FX})")
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
    # "Send via Outlook" (issue #205) - adfaerden fra foer #189: et udkast i
    # brugerens egen Outlook med emne, anmodning og besked. Hilsenen
    # skaeres fra, for Outlook saetter brugerens egen signatur paa.
    # Spaerret, mens der er valgt filer: et mailto-link kan ikke baere dem.
    top = f'Left({msg}, Find("Kind regards,", {msg} & "Kind regards,") - 1)'
    send_out = (f'Launch("mailto:{MAILBOX}?subject=" & EncodeUrl({SUBJECT_FX}) & '
                f'"&body=" & EncodeUrl({OUTLOOK_CONTEXT_FX} & {top}));\n'
                f"Set({OPEN}, false);\n{reset};\n"
                'Notify("The mail is ready in Outlook. Press Send there.", NotificationType.Information)')
    btnOutlook = button(n("btn", "SendOutlook"), '"Send via Outlook"', send_out,
                        width=fit_button_width('"Send via Outlook"'), height=36,
                        display_mode=(f"If(IsBlank(Trim({msg})) || {BUSY} || {n_files} > 0, "
                                      "DisplayMode.Disabled, DisplayMode.Edit)"),
                        tooltip=(f'If({n_files} > 0, "Outlook can\'t take the attached files. '
                                 'Use Send, or remove the files.", '
                                 '"Open the message as a draft in your own Outlook")'))
    footer = group(n("con", "Footer"), [btnOutlook, btnSend], direction="Horizontal", gap=8,
                   height=36, justify="End", align_items="Center")

    modal = group(n("con", "Modal"), [head, intro, who, area, footer],
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
    # Vedhaeftningspopuppen ligger efter (= oven paa) Message us.
    return [backdrop, _attach_popup(n, files, f"Set({ATT}, false)")]
