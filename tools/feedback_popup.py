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
No connector is involved.

No attachments (issue #215): the popup has no file picker. The flow keeps
its Attachments input (text_3) so the app's .Run call keeps its five
arguments; the app always sends "[]" there, and the flow sends no files.

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
from gen_screen import C_DISABLED_BG, C_DIVIDER, C_INPUT_BG, C_INPUT_FG, C_PRIMARY, C_TRANSPARENT
from design_tokens import ref as _t, ref_hex
from build_helpers import (group, text_ctrl, button, text_input,
                           fit_button_width, grow, row_hit, ICON_W, ensure_hit,
                           flat_button, popup_head)
import layout_tokens as lay
import request_index as ri
import icons
import mobile
from build_helpers import mobile_footer, mobile_pad

OPEN = "gblFbOpen"
ME = "gblFbMe"
SEL = "gblFbSel"      # det valgte emne eller anmodning (record), Blank = intet valgt
PICK = "gblFbPick"    # listen er foldet ud
REQS = "colFbRequests"
# R2-052: FLOWET er kilden til postkassen (miljoevariablen
# BioSap-MasterDataEmail i BioSap-SendFeedbackMail). Literalen her bruges kun
# til teksten i popuppen, mailto-udkastet ("Send via Outlook") og flowets
# visningsinput "To" - flowet sender ikke til den.
MAILBOX = "sapvedligehold@orsted.com"
SEND_FLOW = "'BioSap-SendFeedbackMail'"
BUSY = "gblFbBusy"    # flowet koerer - Send er spaerret, saa intet sendes to gange
# Flowets Attachments-input (text_3) beholdes (issue #215), saa .Run har
# samme antal argumenter som flowet i solutionen. Appen sender altid en
# tom liste; flowet laeser den som ingen filer.
NO_FILES = '"[]"'
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
# TELEFONEN (issue #508, fase 6): listens raekker er TOUCH hoeje paa mobil,
# saa en tommelfinger rammer det rigtige emne. Tablet og desktop: ROW_H.
ROW_H_M = lay.TOUCH_MIN
ROW_H_FX = lay.mobile_or(ROW_H_M, ROW_H)


def _row_y(desk_y, mob_y):
    """Y i en listeraekke: mob_y paa mobil (raekken er ROW_H_M), ellers desk_y."""
    return lay.mobile_or(mob_y, desk_y)


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

# Beskedfeltet starter tomt (issue #492): ingen faerdig hilsen og
# signatur mere, kun pladsholderen. Flowet skriver selv afsenderen oeverst
# i mailen, og Outlook saetter brugerens egen signatur paa.
MESSAGE_DEFAULT = '""'
MESSAGE_PLACEHOLDER = '"Describe your question, idea or issue..."'

# KANTER, DER IKKE KLIPPES (issue #492). En container tegner sin kant paa
# sin yderkant, og foraelderen skjuler sit overloeb (LayoutOverflow.Hide,
# build_helpers.group) - samme aarsag som SPLIT_PAD i submission_notes.py.
# Vaelgerens knap og den udfoldede liste stod helt ude ved kanten af
# cellen/omraadet uden luft, saa venstre kant og bundkanten blev skaaret
# af. EDGE er luften paa alle fire sider af de to kanter.
EDGE = 2

# Det faste i popuppen PAA EN TELEFON (issue #508, fase 6): sloerets luft
# 2 x 8, polstringen 36, overskrift 44, intro 40, Email 62, emnecellen
# 20 + 6 + 44 (H.control) + EDGE, beskedens etiket 26, foden 44 + 8 + 44
# (knapperne under hinanden) og fem mellemrum af 12. EDGE laegges til i
# build(), som paa de andre skaermbredder.
PHONE_FIXED = 2 * 8 + 36 + 44 + 40 + 62 + (20 + 6 + 44) + 26 + (44 + 8 + 44) + 5 * 12

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
# 14 px, 16 px under Tablet - samme udtryk som input_theme og dermed som
# soegefeltet i den udfoldede liste. Knappen var en Classic/Button, hvis
# Size er i PUNKTER, og stoerrelsen blev derfor regnet om (1 pt = 4/3 px).
# Siden issue #307 er den en ModernButton, hvis Size er i PIXELS - omregningen
# gav 10,5/12 px, mindre end resten af formularen (issue #507).
SUBJECT_SIZE = lay.if_below("Tablet", str(lay.SIZE_INPUT_MOBILE), str(lay.SIZE_INPUT))
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
        # Pynt: knappen ved siden af er klikfladen (regel 40).
        "ImagePosition": "ImagePosition.Fit", "OnSelect": "false", "TabIndex": "0",
        "Visible": is_req, "Width": "20",
    }, h=20, vis=is_req)
    label = f'If({has}, {SEL}.Label, "Pick a subject or request")'
    # Pladsholderen og den valgte vaerdi har de andre felters typografi
    # (issue #205, se SUBJECT_SIZE): normal vaegt, een linje, ... til sidst.
    size = SUBJECT_SIZE
    # ModernButton med Padding* = 0 og ingen kant (issue #307): teksten
    # flugter med listen under (#140). Feltets flade og kant er beholderens
    # (conXxFbSubject); knappen er gennemsigtig (ButtonAppearance.Transparent).
    # Hover/tryk/fokus er Fluent-temaets - se docs/38.
    btn = flat_button(
        n("btn", "Subject"), _fit(label, "Self.Width", SUBJECT_PX), toggle,
        accessible=label, height=34, size=size,
        color=f"If({has}, {C_INPUT_FG}, {C_MUTED})")
    # Paa mobil fylder knappen feltets hoejde (H.control = 44): hele feltet
    # er klikfladen (issue #508, fase 6).
    mobile.touch(btn)
    chevron = Ctrl(n("img", "SubjectChevron"), "Image", props={
        "AccessibleLabel": f'If({PICK}, "Collapse list", "Expand list")',
        # Tooltip som etiketten (issue #515).
        "Tooltip": f'If({PICK}, "Collapse list", "Expand list")',
        "BorderStyle": "BorderStyle.None", "BorderThickness": "0",
        "Fill": C_TRANSPARENT, "Height": "20",
        "Image": (f'"data:image/svg+xml;utf8," & EncodeUrl(If({PICK}, '
                  f'"{_chevron_svg(CHEVRON_UP)}", "{_chevron_svg(CHEVRON_DOWN)}"))'),
        "ImagePosition": "ImagePosition.Fit", "OnSelect": toggle, "TabIndex": "0",
        "Width": "20",
    }, h=20)
    # Pilen er ogsaa en klikflade - mindst H.hit (regel 40), og feltet er
    # derfor H.control hoejt (44 paa touch).
    ensure_hit(chevron)
    trigger = group(n("con", "Subject"), [icon, grow(btn), chevron], direction="Horizontal",
                    gap=8, height=lay.CONTROL, align_items="Center", pad=(0, 4, 0, 12),
                    fill=C_INPUT_BG, border_color=f"If({PICK}, {C_PRIMARY}, {C_DIVIDER})",
                    radius=lay.RADIUS_INPUT)

    # Soegefeltet - kun naar der er nok anmodninger til, at det hjaelper.
    find_name = n("inp", "SubjectFind")
    find = text_input(find_name, '""', placeholder='"Search number, title or type"',
                      label='"Search your requests"')
    mobile.touch(find)
    many = f"CountRows({REQS}) > {SEARCH_MIN}"
    # Soegefeltets kant faar ogsaa luft til siderne og foroven (issue #492).
    find_wrap = group(n("con", "SubjectFind"), [find], direction="Vertical", gap=0,
                      pad=(EDGE, EDGE, 6, EDGE), visible=many)

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
                     width="Parent.TemplateWidth - 24",
                     extra={"X": "12", "Y": _row_y(ROW_H - 22, ROW_H_M - 22)})
    accent = Ctrl(n("rct", "SubjectAccent"), "Rectangle", props={
        "AccessibleLabel": '"Selected"', "BorderStyle": "BorderStyle.None", "BorderThickness": "0",
        "Fill": _accent_fx("ThisItem.Domain"), "Height": "24", "OnSelect": "false",
        "TabIndex": "0", "Visible": selected, "Width": "3", "X": "0",
        "Y": _row_y((ROW_H - 24) // 2, (ROW_H_M - 24) // 2),
    }, h=24, vis=selected)
    row_icon = Ctrl(n("img", "SubjectRowIcon"), "Image", props={
        "AccessibleLabel": 'Coalesce(ThisItem.TypeName, "Request")', "BorderStyle": "BorderStyle.None", "BorderThickness": "0",
        "Fill": C_TRANSPARENT, "Height": "20", "Image": _icon_fx("ThisItem.Domain"),
        "ImagePosition": "ImagePosition.Fit", "OnSelect": "false", "TabIndex": "0",
        "Visible": f'{kind} = "R"', "Width": "20", "X": "12",
        "Y": _row_y((ROW_H - 20) // 2, (ROW_H_M - 20) // 2),
    }, h=20, vis=f'{kind} = "R"')
    text_x = f'If({kind} = "R", 40, 12)'
    text_w = f"Parent.TemplateWidth - {text_x} - 12"
    row_text = text_ctrl(n("txt", "SubjectRow"), _fit("ThisItem.Label", "Self.Width", ROW_TEXT_PX),
                         size=ROW_TEXT_SIZE, color=f'If({kind} = "E", {C_MUTED}, {C_TITLE})',
                         height=20, wrap="false", visible=f'{kind} <> "H"',
                         width=text_w, extra={"X": text_x, "Y": _row_y((ROW_H - 20) // 2, (ROW_H_M - 20) // 2)})
    # weight er et udtryk, ikke et navn
    row_text.props["FontWeight"] = f"If({selected}, FontWeight.Semibold, FontWeight.Normal)"
    pick = (f"Set({SEL}, {{Kind: ThisItem.Kind, Code: ThisItem.Code, Label: ThisItem.Label, "
            "TypeName: ThisItem.TypeName, Domain: ThisItem.Domain, Title: ThisItem.Title, "
            "Url: ThisItem.Url}); "
            f"Set({PICK}, false)")
    hit_label = (f'If({kind} = "R", "Request " & ThisItem.Code & ", " & ThisItem.TypeName & '
                 '", " & ThisItem.Title, ThisItem.Label)')
    hit = row_hit(n("btn", "SubjectPick"), pick, hit_label, "Parent.TemplateWidth", ROW_H, radius=6)
    mobile.touch(hit)
    hit.props["Visible"] = pickable
    hit.vis = pickable

    gal_name = n("gal", "Subject")
    # Listen holder sig inden for den plads, der er under knappen, og
    # scroller resten (issue #205).
    gal_h = (f"Min(Min({gal_name}.AllItemsCount, {MAX_ROWS}) * {ROW_H_FX}, "
             f"{avail} - 12 - If({many}, {find_wrap.h}, 0))")
    gal = Ctrl(gal_name, "Gallery", variant="Vertical", props={
        "AccessibleLabel": '"Subjects and your requests"',
        "BorderStyle": "BorderStyle.None", "Fill": C_TRANSPARENT, "FillPortions": "0",
        "Height": gal_h,
        "Items": items, "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None",
        "Selectable": "false", "ShowScrollbar": "true", "TabIndex": "0",
        "TemplatePadding": "0", "TemplateSize": ROW_H_FX,
        "Width": "Parent.Width", "WrapCount": "1",
    }, children=[head, accent, row_icon, row_text, hit], h=gal_h)

    lst = group(n("con", "SubjectList"), [find_wrap, gal], direction="Vertical", gap=0,
                pad=(6, 6, 6, 6), fill=C_MODAL_BG, border_color=C_DIVIDER,
                radius=lay.RADIUS_INPUT)
    # Listen ligger i en gennemsigtig ramme med EDGE luft paa alle sider
    # (issue #492), saa dens kant og runde hjoerner ikke klippes af
    # omraadet, og den flugter med knappens kant.
    panel = group(n("con", "SubjectLayer"), [lst], direction="Vertical", gap=0,
                  pad=(EDGE, EDGE, EDGE, EDGE), visible=PICK)

    lab = text_ctrl(n("txt", "SubjectLabel"), '"Subject or request (optional)"', size=12,
                    color=C_MUTED, weight="Semibold", height=20, wrap="false")
    # Knappens kant faar EDGE luft til venstre, hoejre og forneden (issue
    # #492); foroven er der etikettens mellemrum. Etiketten flugter stadig
    # med "Message" under den.
    frame = group(n("con", "SubjectFrame"), [trigger], direction="Vertical", gap=0,
                  pad=(0, EDGE, EDGE, EDGE))
    cell = group(n("con", "SubjectCell"), [lab, frame], direction="Vertical", gap=6)
    return cell, panel, find_name


# Listens ramme starter lige under cellen: knappen slutter EDGE over
# cellens bund, og listen EDGE inde i rammen - 2 * EDGE = 4 px luft.
# Cellens hoejde (etiket 20 + 6 + knap H.control + EDGE) foelger H.control,
# 44 paa touch. Foer stod her et fast 66, saa listen daekkede knappens
# bundkant paa tablet og mobil (issue #492).
def _list_y(cell):
    return cell.h


def _no_flex(ctrl, x, y):
    """Et barn af en ManualLayout-container: X og Y i stedet for
    AutoLayout-egenskaberne."""
    for k in ("FillPortions", "LayoutMinWidth", "AlignInContainer"):
        ctrl.props.pop(k, None)
    ctrl.props["X"] = str(x)
    ctrl.props["Y"] = str(y)
    ctrl.props["Width"] = "Parent.Width"
    return ctrl


def build(p):
    """[backdrop] for one screen. p is the screen's name prefix."""
    vis = f"IfError({OPEN}, false)"
    n = lambda kind, base: f"{kind}{p}Fb{base}"

    # Beskedens hoejde: det faste i popuppen og resten til beskeden. Det
    # faste er 366 + EDGE: polstring 36, overskrift 44 (titel og X), intro 40,
    # Initials/Email 62, emnecellen 62 + EDGE (issue #492), beskedens etiket
    # 26, footer 36 og seks mellemrum af 12. Vedhaeftningsraekken (36 + 12) er vaek (issue #215), saa
    # beskeden faar den plads. Den afhaenger IKKE af, om listen er foldet
    # ud (issue #205), saa popuppen staar stille.
    # TELEFONEN (issue #508, fase 6): popuppen skal kunne staa paa skaermen
    # uden at sloeret scroller - ellers scroller baade siden og emnelisten.
    # Det faste paa mobil er PHONE_FIXED (se nedenfor); beskeden faar resten,
    # mindst 100 og hoejst de 220, den havde.
    msg_h = (f"If({lay.below('Tablet')}, Max(100, Min(220, App.Height - {PHONE_FIXED + EDGE})), "
             f"Max(160, Min(272, App.Height - 40 - {366 + EDGE})))")
    # Listens hoejde under vaelgerens knap: mellemrummet, beskedens etiket
    # og beskeden minus 4 px luft over listen. Rammens EDGE i bunden
    # opvejes af cellens EDGE under knappen, saa rammen slutter praecis ved
    # formularens bund.
    avail = f"({msg_h}) + {12 + 26 - 4}"
    about, panel, find_name = _subject_picker(n, avail)
    reset = (f"Set({SEL}, Blank()); Set({PICK}, false); Reset({find_name}); "
             f"Reset({n('inp', 'Message')})")

    title = text_ctrl(n("txt", "Title"), '"Message SAP maintenance"', size=lay.SIZE_CARD_TITLE,
                      weight="Semibold", height=26, wrap="false")
    # X oeverst til hoejre (issue #343) - lukker og nulstiller som foer.
    head = popup_head(n("con", "Head"), title, n("btn", "Close"), f"Set({OPEN}, false); {reset}")

    # Paa mobil en kortere tekst, der kan staa paa to linjer ved 320 px.
    intro = text_ctrl(n("txt", "Intro"),
                      lay.mobile_or(f'"Questions, ideas or issues? Sent to {MAILBOX}."',
                                    f'"Questions, ideas or something not working? Your message goes to {MAILBOX}."'),
                      size=13, color=C_MUTED, height=40, wrap="true")
    # Skaermlaeseren laeser den samme tekst som foer fra Tablet og op.
    intro.props["AccessibleLabel"] = intro.props["Text"]

    locked = {"PaddingLeft": "12", "VerticalAlign": "VerticalAlign.Middle",
              "BorderStyle": "BorderStyle.Solid", "BorderThickness": "1",
              "BorderColor": C_DIVIDER}
    inpInitials = text_ctrl(n("txt", "Initials"), INITIALS, size=14, color=C_MUTED, height=36,
                            fill=C_DISABLED_BG, accessible='"Your initials (locked)"', extra=locked)
    inpEmail = text_ctrl(n("txt", "Email"), ME, size=14, color=C_MUTED, height=36,
                         fill=C_DISABLED_BG, accessible='"Your email (locked)"', extra=locked)
    # Initialerne er laest af mailadressen - paa mobil staar kun Email, saa
    # den har hele bredden (issue #508, fase 6).
    initials = mobile.hide_on_mobile(_field(n("con", "InitialsCell"), "Initials", inpInitials,
                                            width="110"))
    who = group(n("con", "Who"), [
        initials,
        grow(_field(n("con", "EmailCell"), "Email", inpEmail), min_w=0),
    ], direction="Horizontal", gap=12, height=62, align_items="Start")

    inpMessage = text_input(n("inp", "Message"), MESSAGE_DEFAULT, placeholder=MESSAGE_PLACEHOLDER,
                            max_length=1200, height=220, ttype="Multiline",
                            label='"Message"')
    inpMessage.props["Height"] = msg_h
    inpMessage.h = msg_h
    message = _field(n("con", "MessageCell"), "Message", inpMessage)

    # Formularen under "Subject or request" og listen OVEN PAA den
    # (issue #205): en ManualLayout-container, hvor listen ligger sidst
    # (= oeverst). Formularen beholder sin hoejde og sine vaerdier, naar
    # listen foldes ud; listen er kun saa hoej, som der er plads til
    # (avail), og scroller resten.
    form = group(n("con", "Form"), [about, message], direction="Vertical", gap=12)
    _no_flex(form, 0, 0)
    _no_flex(panel, 0, _list_y(about))
    area = Ctrl(n("con", "Area"), "GroupContainer", variant="ManualLayout", props={
        "BorderStyle": "BorderStyle.None", "DropShadow": "DropShadow.None",
        "FillPortions": "0", "Height": str(form.h), "LayoutMinWidth": "0",
        "Width": "Parent.Width",
    }, children=[form, panel], h=form.h)

    msg = f"{n('inp', 'Message')}.Text"
    # Flowet sender fra SVC_BioSap og svarer {sent, message}. En afvisning
    # (sent = "no") og en fejl i kaldet giver begge fejlbeskeden; popuppen
    # bliver staaende med teksten, saa intet gaar tabt.
    run = (f'{SEND_FLOW}.Run("{MAILBOX}", {SUBJECT_FX}, {msg}, '
           f"{NO_FILES}, {CONTEXT_FX})")
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
    # brugerens egen Outlook med emne, anmodning og besked. Outlook saetter
    # brugerens egen signatur paa. Feltet har ingen faerdig hilsen mere
    # (issue #492), saa beskeden sendes, som brugeren skrev den.
    send_out = (f'Launch("mailto:{MAILBOX}?subject=" & EncodeUrl({SUBJECT_FX}) & '
                f'"&body=" & EncodeUrl({OUTLOOK_CONTEXT_FX} & {msg}));\n'
                f"Set({OPEN}, false);\n{reset};\n"
                'Notify("The mail is ready in Outlook. Press Send there.", NotificationType.Information)')
    btnOutlook = button(n("btn", "SendOutlook"), '"Send via Outlook"', send_out,
                        width=fit_button_width('"Send via Outlook"'), height=36,
                        display_mode=blank,
                        tooltip='"Open the message as a draft in your own Outlook"')
    footer = group(n("con", "Footer"), [btnOutlook, btnSend], direction="Horizontal", gap=8,
                   height=36, justify="End", align_items="Center")
    # Paa mobil staar knapperne under hinanden i fuld bredde, 44 hoeje,
    # Send nederst - som alle andre popupper (build_helpers.mobile_footer).
    mobile_footer(footer)

    modal = group(n("con", "Modal"), [head, intro, who, area, footer],
                  direction="Vertical", gap=12, fill=C_MODAL_BG, border_color=C_PRIMARY_SOFT,
                  radius=lay.RADIUS_MODAL, pad=(18, 18, 18, 18),
                  width=lay.popup_w(560, 40), drop_shadow="ExtraBold",
                  align_in_container="Center")
    mobile_pad(modal, x=mobile.CARD_PAD)
    backdrop = group(n("con", "Backdrop"), [modal], direction="Vertical", gap=0,
                     height="App.Height", width="App.Width", fill=C_OVERLAY, visible=vis,
                     justify="Start", align_items="Center", pad=(20, 0, 20, 0),
                     overflow_y="Scroll")
    # Paa mobil lige under kanten (sheet_y), saa beskeden faar pladsen.
    mobile_pad(backdrop, top=mobile.POP_MARGIN, bottom=mobile.POP_MARGIN)
    backdrop.props["X"] = "0"
    backdrop.props["Y"] = "0"
    return [backdrop]
