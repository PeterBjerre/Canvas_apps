# -*- coding: utf-8 -*-
"""
DEN FAELLES DOKUMENTUPLOAD (issue #134) - een oplevelse i hele appen.

HVAD DER STOD FOER
------------------
Fem klassiske Attachments-kontroller (Attachments@2.3.0) - to dokument-
popupper (Equipment/Material og VH-planens operationer) og to felter i
Issue Board - hver med sin egen hoejde, sin egen tekst ("Drag documents
here, or browse", "Drop documents here, or browse") og sit eget loft
(10 MB her, 50 MB der). Listen over gemte filer havde en afkrydsning pr.
raekke og en faelles "Remove document"-knap, og VH-planen havde ingen
Open-knap.

HVAD DER STAAR NU
-----------------
Den KLASSISKE Attachments-kontrol (Attachments@2.3.0), bygget eet sted.
Issue #134 brugte den moderne (ModernAttachments), men den kender
Studio ikke i dette miljoe: "Unknown control type 'ModernAttachments'"
(issue #165). Den moderne virker desuden kun inde i en formular (MS
Learn), og vores upload sker gennem et flow uden formular. Den klassiske
kompilerede og virkede foer #134, saa den er tilbage - med #134's faelles
tekst, hoejde, Upload-knap, status og liste.

Kontrollen holder de VALGTE filer, ikke de
gemte. De gemte ligger i dokumentbiblioteket (tools/attflows.py) og ikke
i en listes Attachments-kolonne, og en samling kan kontrollen ikke vise
som gemte filer. Listen under kontrollen er derfor stadig et galleri -
nu med filtype, navn, Open og Remove pr. raekke.

Flowkontrakten er uaendret: kontrollens Attachments-tabel har Name og
Value ligesom den klassiske, og det er de to, flowet faar.
"""
from gen_screen import (Ctrl, C_MUTED, C_MUTED_BG, C_INVALID_FG, C_VALID_FG, C_CARD_BORDER,
                        C_INFO_BG)
import layout_tokens as lay
from build_helpers import text_ctrl, button, group, grow, fit_button_width, ICON_W

CONTROL = "Attachments@2.3.0"

# Dropfladen uden filer, og hvad hver valgt fil laegger til. Hoejden
# foelger indholdet; over fire filer scroller kontrollen selv.
PICKER_H = 112
PICKER_FILE_H = 36
PICKER_MAX_FILES_SHOWN = 4

# Raekkerne i listen over gemte filer.
ROW_H = 40
BADGE_W = 44
REMOVE_W = 40


def picker_height(ref):
    """Hoejden som udtryk - ref er "Self" i kontrollen og navnet i
    foraelderens regnestykke."""
    return (f"If(CountRows({ref}.Attachments) = 0, {PICKER_H}, {PICKER_H} + "
            f"Min(CountRows({ref}.Attachments), {PICKER_MAX_FILES_SHOWN}) * {PICKER_FILE_H})")


def picker(name, label, max_files, max_mb, display_mode=None, visible=None):
    """Den klassiske Attachments-kontrol - kun egenskaber, typen kender
    (de samme som foer #134, som kompilerede)."""
    props = {
        "AccessibleLabel": label,
        "BorderColor": C_CARD_BORDER,
        "BorderThickness": "1",
        "Height": picker_height("Self"),
        "MaxAttachmentSize": str(max_mb),
        "MaxAttachments": str(max_files),
        "NoAttachmentsText": '"Select files to upload"',
        "PaddingBottom": "5",
        "PaddingLeft": "5",
        "PaddingRight": "5",
        "PaddingTop": "5",
        "Width": "Parent.Width",
    }
    if display_mode:
        props["DisplayMode"] = display_mode
    if visible is not None:
        props["Visible"] = visible
    return Ctrl(name, CONTROL, props=props, h=picker_height(name), vis=visible)


def limits_text(name, max_files, max_mb, extra="", visible=None):
    """Loftet - og ikke en instruktion mere. Kontrollen siger selv, hvordan
    man vaelger filer, og hvad der kan lade sig goere paa enheden."""
    return text_ctrl(name, f'"Up to {max_files} files at a time, {max_mb} MB each.{extra}"',
                     size=lay.SIZE_SMALL, color=C_MUTED, height=34 if extra else 18,
                     wrap="true", visible=visible)


def upload_button(name, picker_name, onselect, busy, base_mode="DisplayMode.Edit",
                  visible=None):
    """Den ene upload-handling. Spaerret, mens intet er valgt, og mens et
    flow koerer - saa et dobbelt-tryk ikke sender filerne to gange."""
    text = '"Upload"'
    b = button(name, text, onselect, primary=True,
               width=fit_button_width(text) + ICON_W, height=36, icon="ArrowUpload",
               accessible='"Upload the chosen files"', visible=visible,
               display_mode=(f"If({busy} || CountRows({picker_name}.Attachments) = 0, "
                             f"DisplayMode.Disabled, {base_mode})"))
    b.props["LayoutMinWidth"] = b.props["Width"]
    return b


def status_text(name, pane, visible=None):
    """Hvad der sker, og hvad der skete - i ord (tools/attflows.Pane)."""
    vis = pane.status_visible() if visible is None else f"({visible}) && {pane.status_visible()}"
    return text_ctrl(name, pane.status_fx(), size=lay.SIZE_SMALL,
                     color=pane.status_color_fx(C_VALID_FG, C_INVALID_FG, C_MUTED),
                     height=34, wrap="true", visible=vis,
                     accessible=pane.status_fx())


def type_badge(name, file_expr):
    """Filtypen som et lille maerke: PDF, DOCX, XLSX. Navnet efter det
    sidste punktum - uden punktum staar der FILE."""
    ext = (f'If(IsBlank(Find(".", {file_expr})), "FILE", '
           f'Upper(Left(Last(Split({file_expr}, ".")).Value, 4)))')
    t = text_ctrl(name, ext, size=lay.SIZE_MICRO, weight="Semibold", color=C_MUTED,
                  height=24, width=BADGE_W, align="Center",
                  extra={"Fill": C_MUTED_BG, "VerticalAlign": "VerticalAlign.Middle",
                         **lay.radius(6)})
    t.props["LayoutMinWidth"] = str(BADGE_W)
    return t


def open_button(name, url_expr, file_expr):
    """Open - i en NY fane: et dokument er ikke en app, og Replace ville
    smide appen og en halvudfyldt formular vaek. Browseren aabner eller
    henter filen efter typen."""
    text = '"Open"'
    w = fit_button_width(text, min_w=64)
    b = button(name, text, f"Launch({url_expr}, {{ }}, LaunchTarget.New)", width=w, height=32,
               accessible=f'"Open or download " & {file_expr}',
               display_mode=f'If(IsBlank({url_expr}), DisplayMode.Disabled, DisplayMode.Edit)')
    b.props["LayoutMinWidth"] = str(w)
    return b


def remove_button(name, pane, file_expr, can_edit):
    """Remove pr. dokument - kun mens der maa redigeres. Det sletter ikke
    endnu: det beder om en bekraeftelse (remove_confirm)."""
    b = button(name, '"Remove"', f"Set({pane.remove_var}, {file_expr})", danger=True,
               width=REMOVE_W, height=32, icon="Delete", visible=can_edit,
               accessible=f'"Remove " & {file_expr}', tooltip=f'"Remove " & {file_expr}',
               display_mode=f"If({pane.busy}, DisplayMode.Disabled, DisplayMode.Edit)")
    b.props["Layout"] = "ButtonLayout.IconOnly"
    b.props["LayoutMinWidth"] = str(REMOVE_W)
    return b


def remove_confirm(prefix, pane):
    """Bekraeftelsen inde i popuppen: "Remove x.pdf from SharePoint?" med
    Cancel og Remove. Filen slettes i biblioteket - det kan ikke fortrydes,
    og derfor spoerger vi en gang."""
    vis = f"!IsBlank({pane.remove_var})"
    msg = text_ctrl(f"txt{prefix}RemoveAsk",
                    f'"Remove " & {pane.remove_var} & " from SharePoint? This cannot be undone."',
                    size=lay.SIZE_BODY, height=36, wrap="true")
    cancel = button(f"btn{prefix}RemoveCancel", '"Cancel"', f"Set({pane.remove_var}, Blank())",
                    width=fit_button_width('"Cancel"'), height=32)
    ok = button(f"btn{prefix}RemoveConfirm", '"Remove"', pane.remove_fx(), danger=True,
                width=fit_button_width('"Remove"'), height=32,
                accessible=f'"Remove " & {pane.remove_var}',
                display_mode=f"If({pane.busy}, DisplayMode.Disabled, DisplayMode.Edit)")
    for b in (cancel, ok):
        b.props["LayoutMinWidth"] = b.props["Width"]
    btns = group(f"con{prefix}RemoveBtns", [cancel, ok], direction="Horizontal", gap=8,
                 height=32, justify="End", align_items="Center")
    return group(f"con{prefix}Remove", [msg, btns], direction="Vertical", gap=8,
                 fill=C_INFO_BG, border_color=C_CARD_BORDER, radius=lay.RADIUS_INPUT,
                 pad=(10, 12, 10, 12), visible=vis)


def capped_body(name, kids, max_h, gap=12):
    """Popuppens indhold: saa hoejt som indholdet, men aldrig hoejere end
    max_h. Foerst naar indholdet ikke kan vaere der, scroller det - og
    titlen og Close staar uden for, saa de bliver staaende."""
    body = group(name, kids, direction="Vertical", gap=gap, overflow_y="Scroll")
    body.props["Height"] = f"Min({body.h}, {max_h})"
    body.h = body.props["Height"]
    return body


def readonly_note(name, visible):
    """I View-tilstand og paa en laast anmodning: sig det i ord, i stedet
    for at lade de manglende knapper tale for sig selv."""
    return text_ctrl(name, '"Read only. You can open the documents, but not add or remove them."',
                     size=lay.SIZE_SMALL, color=C_MUTED, height=18, wrap="true", visible=visible)
