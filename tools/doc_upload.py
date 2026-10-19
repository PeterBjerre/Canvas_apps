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
Den MODERNE Attachments-kontrol (ModernAttachments@1.3.0, preview),
bygget eet sted (issue #161). Issue #134 indfoerte den, men Studio
kendte den ikke dengang - "Unknown control type 'ModernAttachments'"
(issue #165) - og vi gik tilbage til den klassiske. Fra authoring-
version 3.26101.10 kender Peters Studio den, og Studio skriver @1.3.0.

Den moderne virker uden formular (MS Learn) og har selv filvaelgeren,
drag-and-drop paa web, flere filer, filtype-ikoner og fejl ved for store
filer. Paa mobil bruges enhedens filvaelger - derfor staar der ingen
instruktion om at traekke filer i vores egen tekst: kun loftet.

KONTRAKTEN (issue #300)
-----------------------
Kontrollen er bundet til en LISTERAEKKES vedhaeftninger:
Items = <raekke>.Attachments (tools/attflows.Pane.items). Den viser selv
de gemte filer, aabner/henter dem ved tryk og markerer en fjernet fil
til fjernelse, til der gemmes. Gem-knappen (save_button) Patch'er
raekkens Attachments med kontrollens Attachments-output i eet kald -
uden flows (Peter, 2026-10-17). Derfor er der intet galleri over gemte
filer, ingen Open/Remove pr. raekke og ingen Refresh mere.

Foer stod kontrollen med Items = Blank() og sendte hver fil gennem et
flow til biblioteket TaskListDocuments. Uden Items havde Attachments-
outputtet intet skema, og F.Name/F.Value kompilerede ikke (issue #300).

I View-tilstand (laast anmodning) viser kontrollen kun filerne til
download.
"""
from gen_screen import Ctrl, C_MUTED, C_WARN_FG, stack_height
import layout_tokens as lay
from build_helpers import text_ctrl, button, fit_button_width, ICON_W
# capped_body genudsendes: domain_parts, material_parts og VH-planens
# build_tasklist kalder du.capped_body. __all__ fortaeller pyflakes (som
# ikke kender "# noqa"), at importen er bevidst.
from build_helpers import capped_body
__all__ = ["capped_body"]

# Versionen er den, Studio selv skriver (Peter, issue #161). Regel 16b
# afviser den klassiske kontrol og enhver anden version.
CONTROL = "ModernAttachments@1.3.0"

# Dropfladen uden filer, og hvad hver fil laegger til (issue #344).
# 112 var for lidt: tom-tilstanden fik sin egen lodrette scrollbar, selv
# med masser af plads i popuppen. Hoejden foelger nu filerne helt ud og
# kappes foerst af den plads, foraelderen har (fit_picker) - kontrollen
# scroller kun, naar filerne reelt ikke kan vaere der.
PICKER_H = 160
PICKER_FILE_H = 44


def picker_rows(ref, items):
    """Raekker, kontrollen viser. AttachmentsCount taeller ikke filer, der
    er markeret til fjernelse - de staar der stadig, til der gemmes. Derfor
    det stoerste af det og de gemte filer (Items)."""
    return f"Max({ref}.AttachmentsCount, CountRows({items}))"


def picker_height(ref, items):
    """Den naturlige hoejde som udtryk - ref er "Self" i kontrollen og
    navnet i foraelderens regnestykke. Intet loft her: det saetter
    fit_picker ud fra den plads, der er."""
    return f"{PICKER_H} + {picker_rows(ref, items)} * {PICKER_FILE_H}"


def fit_picker(pick, siblings, gap):
    """Kontrollen fylder op til den plads, foraelderen har tilbage
    (issue #344): Parent.Height minus de andre synlige boern og deres
    mellemrum - aldrig mindre end tom-tilstanden, aldrig mere end
    indholdet. siblings er ALLE boern i den lodrette container, inkl.
    kontrollen selv, og gap containerens mellemrum. Foraelderens egen
    hoejde regnes af den naturlige hoejde (pick.h), saa der er ingen
    cirkel. Kontrollen staar i regnestykket som en tom plads (h 0), saa
    dens mellemrum taeller med, men den ikke naevner sig selv."""
    gap_only = Ctrl(pick.name, pick.control, h=0)
    reserve = stack_height([gap_only if c is pick else c for c in siblings], gap)
    pick.props["Height"] = (f"Min({pick.props['Height']}, "
                            f"Max({PICKER_H}, Parent.Height - ({reserve})))")
    return pick


def picker(name, label, max_files, max_mb, items, display_mode=None, visible=None):
    """Den moderne Attachments-kontrol - kun egenskaber, MS Learn
    dokumenterer for typen: Items, MaxAttachments, MaxAttachmentSize,
    AccessibleLabel, DisplayMode og OnError. Den klassiskes kant,
    polstring og NoAttachmentsText findes ikke her (regel 10).

    items er raekkens vedhaeftninger (attflows.Pane.items) - ALDRIG
    Blank(): saa har Attachments-outputtet intet skema (issue #300)."""
    props = {
        "AccessibleLabel": label,
        "Height": picker_height("Self", items),
        # De gemte filer paa listeraekken (issue #300).
        "Items": items,
        "MaxAttachments": str(max_files),
        "MaxAttachmentSize": str(max_mb),
        # Koerer kun, naar en fil ikke kan TILFOEJES (for stor, for mange).
        # Fejl ved gem melder gem-knappen (tools/attflows.save_fx).
        "OnError": (f'Notify("This file could not be added. A row can have up to {max_files} '
                    f'files of up to {max_mb} MB each.", NotificationType.Error)'),
        "Width": "Parent.Width",
    }
    if display_mode:
        props["DisplayMode"] = display_mode
    if visible is not None:
        props["Visible"] = visible
    return Ctrl(name, CONTROL, props=props, h=picker_height(name, items), vis=visible)


def picker_mode(pane, can_edit):
    """View, naar der ikke maa rettes (filerne kan stadig hentes);
    Disabled, mens der gemmes, eller raekken ikke er gemt endnu."""
    return (f"If(!({can_edit}), DisplayMode.View, {pane.busy} || IsBlank({pane.row_var}), "
            "DisplayMode.Disabled, DisplayMode.Edit)")


def limits_text(name, max_files, max_mb, extra="", visible=None):
    """Loftet - og ikke en instruktion mere. Kontrollen siger selv, hvordan
    man vaelger filer, og hvad der kan lade sig goere paa enheden."""
    return text_ctrl(name, f'"Up to {max_files} files, {max_mb} MB each.{extra}"',
                     size=lay.SIZE_SMALL, color=C_MUTED, height=34 if extra else 18,
                     wrap="true", visible=visible)


SAVE_TEXT = '"Save documents"'
# Mens der gemmes, siger knappen det selv (issue #441) - samme moenster
# som appens andre knapper (build_helpers.act_button). Foer stod en linje
# "Saving documents... please wait." under knappen OGSAA.
SAVING_TEXT = '"Saving..."'


def save_button(name, pane, onselect=None, base_mode="DisplayMode.Edit", visible=None):
    """Den ene gem-handling: Patch af raekkens Attachments
    (attflows.save_fx). Spaerret, mens kontrollen laeser filerne ind
    (IsUploading), og mens der gemmes - saa et dobbelt-tryk ikke gemmer
    to gange. Er raekken ikke gemt, siger knappen det (not_saved).

    Mens der gemmes, siger knappen "Saving..." - gemmets ENESTE
    ventetegn (issue #441). "Save documents" er den laengste tekst, saa
    bredden staar fast."""
    assert fit_button_width(SAVING_TEXT) <= fit_button_width(SAVE_TEXT)
    b = button(name, f"If({pane.busy}, {SAVING_TEXT}, {SAVE_TEXT})",
               onselect or pane.save_fx(), primary=True,
               width=fit_button_width(SAVE_TEXT) + ICON_W, height=36, icon="Save",
               accessible=f'If({pane.busy}, {SAVING_TEXT}, "Save the documents on this row")',
               visible=visible,
               display_mode=(f"If({pane.busy} || {pane.picker}.IsUploading, "
                             f"DisplayMode.Disabled, {base_mode})"))
    b.props["LayoutMinWidth"] = b.props["Width"]
    return b


def not_saved_text(name, pane, visible=None):
    """Raekken findes ikke i SharePoint endnu - sig hvorfor kontrollen
    er spaerret."""
    vis = f"IsBlank({pane.row_var})" if visible is None else f"({visible}) && IsBlank({pane.row_var})"
    return text_ctrl(name, f'"{pane.not_saved}"', size=lay.SIZE_SMALL, color=C_WARN_FG,
                     height=34, wrap="true", visible=vis)


def readonly_note(name, visible):
    """I View-tilstand og paa en laast anmodning: sig det i ord, i stedet
    for at lade de manglende knapper tale for sig selv."""
    return text_ctrl(name, '"Read only. You can open the documents, but not add or remove them."',
                     size=lay.SIZE_SMALL, color=C_MUTED, height=18, wrap="true", visible=visible)
