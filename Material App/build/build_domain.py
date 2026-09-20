# -*- coding: utf-8 -*-
"""
Skaermen til en domaeneapp - Equipment eller Materials.

Filen er ORDRET ens i de to build-mapper. Alt det, der skiller de to apps,
staar i domain_config.py; her staar kun formen, og den er den samme.

FORMEN
------
    Bar        hvem, hvilket nummer, hvor mange raekker, tilbage til hubben
    Form       raekkens felter, bygget af SECTIONS
    Documents  dokumentruden for den valgte raekke
    Rows       de gemte raekker, med soegning og filtre
    Submit     send de gyldige raekker, og skriv een raekke i indekset

RAEKKEN ER I SHAREPOINT, IKKE I HUKOMMELSEN
-------------------------------------------
Den haandbyggede app samlede alt i colEquipmentRows og havde ikke eet
Patch mod en datakilde. Lukkede brugeren appen, var raekkerne vaek.

Her skriver "Gem raekke" direkte i listen, og samlingen er kun et spejl,
der hentes forfra bagefter. RowId ER raekkens ID i SharePoint - ikke en
taeller, appen selv skruer op. To brugere, der gemmer samtidig, kan
dermed ikke faa det samme nummer.

Og noeglen - EQ-000912 - er lavet af det samme ID. Den er mappenavnet i
dokumentbiblioteket, og derfor kan der foerst laegges dokumenter op, NAAR
raekken er gemt. Det er ogsaa grunden til, at Gem skriver med det samme i
stedet for foerst ved Indsend.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from gen_screen import (Ctrl, SHELL_W, RAIL_W, SPLIT_GAP, EDITOR_W, FONT,
                        C_APP_BG, C_CARD_BG, C_CARD_BORDER, C_TITLE, C_MUTED,
                        C_PRIMARY, C_WHITE, C_TRANSPARENT, C_DIVIDER,
                        C_NEUTRAL_BG, C_INFO_FG, C_INFO_BG,
                        C_VALID_FG, C_VALID_BG)
from build_helpers import (text_ctrl, group, button, button_row, text_input,
                           number_input, dropdown, card, field_cell, row_n,
                           label_row, pin_widths, badge)
import domain_config as cfg
import attflows as att

# Raekkens felter i een flad liste - raekkefoelgen er sektionernes.
FIELDS = [f for _sec, fields in cfg.SECTIONS for f in fields]

ROW_H = 44
GAL_ROWS = 8

# Den aktive raekke i samlingen. Blank betyder "ny raekke".
ACTIVE = "LookUp(colDomRows, RowId = varDomActiveRowId)"

# Indsendte raekker kan ikke redigeres - saa ejer SAP-processen dem.
DM_ROW = ('If(varDomRowStatus = "submitted", DisplayMode.View, DisplayMode.Edit)')
DM_SEL = ('If(IsBlank(varDomActiveRowId), DisplayMode.Disabled, DisplayMode.Edit)')


# ---------------------------------------------------------------------------
# Den flade top
# ---------------------------------------------------------------------------
def build_bar():
    title = text_ctrl("txtDomTitle", f'"{cfg.TITLE}"', size=22, weight="Semibold",
                      height=30, wrap="false")
    sub = text_ctrl("txtDomSub", f'"{cfg.SUBTITLE}"', size=13, color=C_MUTED,
                    height=20, wrap="false")
    left = group("conDomBarLeft", [title, sub], direction="Vertical", gap=2,
                 width="Parent.Width - 520")

    count = badge("txtDomCount",
                  '"Raekker: " & CountRows(colDomRows)', width=120)
    no = text_ctrl("txtDomReqNo",
                   'If(IsBlank(varDomRequestNo), "Ikke indsendt", varDomRequestNo)',
                   size=15, weight="Semibold", height=24, width=160, wrap="false")
    back = button("btnDomBack", '"Tilbage til hubben"',
                  "Back(ScreenTransition.Fade)", width=180)
    right = group("conDomBarRight", pin_widths([count, no, back]),
                  direction="Horizontal", gap=12, align_items="Center",
                  width="500")
    return group("conDomBar", [left, right], direction="Horizontal", gap=20,
                 align_items="Center")


# ---------------------------------------------------------------------------
# Formularen
#
# Felterne staar i variabler, ikke i kontrollerne. Det er ikke pynt: naar
# brugeren vaelger en gemt raekke, skal formularen fyldes ud - og et
# Default, der peger paa en kontrols egen Text, kan ikke saettes udefra.
# Med en variabel bagved er "vaelg raekke" bare femten Set().
# ---------------------------------------------------------------------------
def _var(col):
    return "varDomF" + col


def _input_for(col, kind, choices):
    name = "inp" + col
    v = _var(col)
    if kind == "num":
        c = number_input(name, v, display_mode=DM_ROW)
        c.props["OnChange"] = f"Set({v}, Self.Value)"
        return c
    if kind == "date":
        # Rigtig datovaelger. Den haandbyggede app gemte
        # Text(..., "dd/mm/yyyy") - en streng, der ikke kan sorteres, ikke
        # filtreres paa interval, og betyder noget forskelligt alt efter
        # hvilket landeformat der laeser den. Kolonnen er DateTime, og her
        # sendes datoen som en dato.
        # DefaultDate saetter datoen. SelectedDate LAESER den og kan ikke
        # skrives - her stod "SelectedDate: v", og compile svarede
        # "Unknown property 'SelectedDate' for control type
        # 'ModernDatePicker'". Formen nedenfor er kopieret fra den
        # haandbyggede app, hvor datovaelgerne virker.
        return Ctrl(name, "ModernDatePicker", props={
            "AccessibleLabel": f'"{col}"',
            "Appearance": "Appearance.Outline",
            "BorderColor": C_CARD_BORDER,
            "BorderStyle": "BorderStyle.Solid",
            "BorderThickness": "1",
            "DefaultDate": v,
            "DisplayMode": DM_ROW,
            "Font": FONT,
            "Format": "DatePickerFormat.Short",
            "Height": "36",
            "LayoutMinWidth": "0",
            "OnChange": f"Set({v}, Self.SelectedDate)",
            "Placeholder": '"dd/mm/yyyy"',
            "RadiusBottomLeft": "10", "RadiusBottomRight": "10",
            "RadiusTopLeft": "10", "RadiusTopRight": "10",
            "Size": "14",
            "Width": "Parent.Width",
        }, h=36)
    if kind == "long":
        # ttype="Multiline" -> Type: TextInputType.Multiline. Det er den
        # form, VH-plan-appens langtekstboks bruger, og dermed den eneste
        # der er bevist i dette miljoe. "Mode: TextMode.MultiLine" stod her
        # foerst; den findes ikke paa ModernTextInput, og check_layout
        # kender ikke kontrollens egenskaber godt nok til at sige fra.
        return text_input(name, v, height=140, display_mode=DM_ROW,
                          ttype="Multiline",
                          onchange=f"Set({v}, Self.Text)")
    if kind == "choice":
        items = "[" + ", ".join(f'"{x}"' for x in choices) + "]"
        c = dropdown(name, items, v, display_mode=DM_ROW)
        c.props["OnChange"] = f"Set({v}, Self.Selected.Value)"
        return c
    c = text_input(name, v, max_length=255, display_mode=DM_ROW,
                   onchange=f"Set({v}, Self.Text)")
    return c


COLS_PER_ROW = 3


def build_form():
    head = group("conDomFormHead", [
        text_ctrl("txtDomFormH", '"Raekke"', size=16, weight="Semibold",
                  height=22, wrap="false"),
        text_ctrl("txtDomFormState",
                  ('If(\n'
                   '    IsBlank(varDomActiveRowId),\n'
                   '    "Ny raekke - ikke gemt endnu",\n'
                   '    "Redigerer " & Coalesce(' + ACTIVE + '.ItemKey, "raekke " & varDomActiveRowId)\n'
                   ')'),
                  size=13, color=C_MUTED, height=20, wrap="false"),
    ], direction="Vertical", gap=2)

    # Teksten og vaerket staar oeverst: den ene er listens Title og
    # obligatorisk, den anden afgoer hvilket vaerk raekken hoerer til.
    top = row_n("conDomTopRow", [
        field_cell("conDomText", cfg.TEXT_LABEL,
                   text_input("inpDomText", "varDomFText", max_length=40,
                              placeholder=cfg.TEXT_PLACEHOLDER,
                              required_formula="true", display_mode=DM_ROW,
                              onchange="Set(varDomFText, Self.Text)"),
                   required=True, container_w=EDITOR_W, cols=2),
        field_cell("conDomPlant", cfg.PLANT_LABEL,
                   dropdown("drpDomPlant", "colDomPlants", "varDomFPlant",
                            required_formula="true", display_mode=DM_ROW),
                   required=True, container_w=EDITOR_W, cols=2),
    ], container_w=EDITOR_W)

    kids = [head, top]
    for s_i, (section, fields) in enumerate(cfg.SECTIONS):
        kids.append(text_ctrl(f"txtDomSec{s_i}", f'"{section}"', size=13,
                              weight="Semibold", color=C_MUTED, height=20,
                              wrap="false"))
        chunk = []
        for f_i, (col, label, kind, choices) in enumerate(fields):
            # Langtekst faar hele bredden - den er hoejere end de andre.
            wide = kind == "long"
            cell = field_cell(f"con{col}", label, _input_for(col, kind, choices),
                              container_w=EDITOR_W,
                              cols=1 if wide else COLS_PER_ROW,
                              fill_portions_formula="0" if wide else None)
            if wide:
                if chunk:
                    kids.append(row_n(f"conDomRow{s_i}_{f_i}", chunk,
                                      container_w=EDITOR_W))
                    chunk = []
                kids.append(cell)
                continue
            chunk.append(cell)
            if len(chunk) == COLS_PER_ROW:
                kids.append(row_n(f"conDomRow{s_i}_{f_i}", chunk,
                                  container_w=EDITOR_W))
                chunk = []
        if chunk:
            kids.append(row_n(f"conDomRow{s_i}_end", chunk, container_w=EDITOR_W))

    save = button("btnDomSave", '"Gem raekke"', save_row_fx(), primary=True,
                  width=150, display_mode=DM_ROW)
    new = button("btnDomNew", '"Ny raekke"', clear_form_fx(), width=130)
    delete = button("btnDomDelete", '"Slet raekke"', delete_row_fx(),
                    danger=True, width=150, display_mode=DM_SEL)
    kids.append(button_row("conDomFormActions", [save, new, delete], EDITOR_W))
    kids.append(text_ctrl("txtDomFormInfo", "varDomInfo", size=12,
                          color=C_MUTED, height=18, wrap="false"))
    return card("conDomFormCard", kids)


# ---------------------------------------------------------------------------
# Adfaerden
# ---------------------------------------------------------------------------
BLANK = {"num": "Blank()", "date": "Blank()"}


def _blank(kind):
    return BLANK.get(kind, '""')


def _patch_value(col, kind):
    v = _var(col)
    if kind in ("text", "long", "choice"):
        return f"Trim(Coalesce({v}, \"\"))"
    return v


def refresh_rows_fx(indent=0):
    """Spejlet af listen. Samlingen er ALDRIG sandheden - den hentes
    forfra efter hver skrivning, saa det, skaermen viser, er det, der staar
    i SharePoint."""
    pad = " " * indent
    lines = [
        "ClearCollect(",
        "    colDomRows,",
        "    ForAll(",
        f"        Filter({cfg.L_ROWS}, RequesterEmail = varDomMe) As R,",
        "        {",
        "            RowId: R.ID,",
        "            ItemKey: Coalesce(R.ItemKey, \"\"),",
        "            RequestNo: Coalesce(R.RequestNo, \"\"),",
        "            Status: Coalesce(R.RowStatus.Value, \"valid\"),",
        "            FileCount: Coalesce(R.FileCount, 0),",
        f"            {cfg.C_TEXT}: Coalesce(R.{cfg.C_TEXT}, \"\"),",
        "            Plant: Coalesce(R.Plant, \"\"),",
    ]
    for col, _lab, kind, _ch in FIELDS:
        if kind in ("text", "long", "choice"):
            v = f'Coalesce(R.{col}, "")'
        elif kind == "num":
            v = f"R.{col}"
        else:
            v = f"R.{col}"
        lines.append(f"            {col}: {v},")
    lines[-1] = lines[-1].rstrip(",")
    lines += ["        }", "    )", ")"]
    return "\n".join(pad + l for l in lines)


def clear_form_fx():
    lines = ['Set(varDomActiveRowId, Blank());',
             'Set(varDomRowStatus, "valid");',
             'Set(varDomFText, "");',
             'Set(varDomFPlant, "");']
    for col, _lab, kind, _ch in FIELDS:
        lines.append(f"Set({_var(col)}, {_blank(kind)});")
    lines.append('Set(varDomInfo, "Ny raekke - udfyld og gem.")')
    return "\n".join(lines)


def load_row_fx():
    """Vaelg en gemt raekke. Dokumenterne hentes kun, hvis raekken HAR
    nogen og de ikke allerede er hentet - ellers ville hvert klik i
    listen koste et flow-kald."""
    lines = ['Set(varDomActiveRowId, ThisItem.RowId);',
             'Set(varDomRowStatus, ThisItem.Status);',
             f'Set(varDomFText, ThisItem.{cfg.C_TEXT});',
             'Set(varDomFPlant, ThisItem.Plant);']
    for col, _lab, _kind, _ch in FIELDS:
        lines.append(f"Set({_var(col)}, ThisItem.{col});")
    lines.append(
        "If(\n"
        "    ThisItem.FileCount > 0 &&\n"
        "    CountRows(Filter(colDomAttachments, RowId = ThisItem.RowId)) = 0,\n"
        + att.refresh_fx(4) + "\n"
        ")")
    return "\n".join(lines)


def save_row_fx():
    patch = [
        f"            {cfg.C_TEXT}: Trim(varDomFText),",
        "            Plant: varDomFPlant,",
    ]
    for col, _lab, kind, _ch in FIELDS:
        patch.append(f"            {col}: {_patch_value(col, kind)},")
    patch += [
        '            RowStatus: { Value: "valid" },',
        "            RequesterEmail: varDomMe,",
        "            RequesterName: User().FullName",
    ]
    key = f'"{cfg.PREFIX}-" & Text(varDomSpRow.ID, "000000")'
    return (
        "If(\n"
        "    IsBlank(Trim(Coalesce(varDomFText, \"\"))) || IsBlank(varDomFPlant),\n"
        '    Set(varDomInfo, "' + cfg.TEXT_LABEL + ' og ' + cfg.PLANT_LABEL
        + ' skal udfyldes."),\n'
        "\n"
        "    Set(\n"
        "        varDomSpRow,\n"
        "        Patch(\n"
        f"            {cfg.L_ROWS},\n"
        "            If(\n"
        "                IsBlank(varDomActiveRowId),\n"
        f"                Defaults({cfg.L_ROWS}),\n"
        f"                LookUp({cfg.L_ROWS}, ID = varDomActiveRowId)\n"
        "            ),\n"
        "            {\n"
        + "\n".join(patch) + "\n"
        "            }\n"
        "        )\n"
        "    );\n"
        "\n"
        "    // Noeglen er lavet af raekkens eget ID og kan derfor foerst\n"
        "    // dannes, naar raekken findes. Derfor to skrivninger paa en ny\n"
        "    // raekke og een paa en gammel.\n"
        "    If(\n"
        "        IsBlank(varDomSpRow.ItemKey),\n"
        "        Patch(\n"
        f"            {cfg.L_ROWS},\n"
        "            varDomSpRow,\n"
        "            {\n"
        "                RowId: varDomSpRow.ID,\n"
        f"                ItemKey: {key},\n"
        f"                AttachmentFolder: \"{att.LIBRARY}/\" & {key}\n"
        "            }\n"
        "        )\n"
        "    );\n"
        "    Set(varDomActiveRowId, varDomSpRow.ID);\n"
        '    Set(varDomRowStatus, "valid");\n'
        "\n"
        + refresh_rows_fx(4) + ";\n"
        "\n"
        '    Set(varDomInfo, "Gemt som " & ' + ACTIVE + '.ItemKey)\n'
        ")"
    )


def delete_row_fx():
    """Slet raekken - ogsaa i SharePoint.

    Dokumenterne i biblioteket bliver staaende. Det er med vilje: en
    raekke, der fjernes ved et uheld, maa ikke tage bilagene med sig."""
    return (
        "If(\n"
        "    IsBlank(varDomActiveRowId),\n"
        '    Set(varDomInfo, "Vaelg en raekke i listen foerst."),\n'
        "\n"
        f"    Remove({cfg.L_ROWS}, LookUp({cfg.L_ROWS}, ID = varDomActiveRowId));\n"
        "    RemoveIf(colDomAttachments, RowId = varDomActiveRowId);\n"
        "\n"
        + refresh_rows_fx(4) + ";\n"
        "\n"
        + clear_form_fx().replace("\n", "\n    ").replace(
            'Set(varDomInfo, "Ny raekke - udfyld og gem.")',
            'Set(varDomInfo, "Raekken er slettet. Dokumenterne ligger stadig i biblioteket.")')
        + "\n"
        ")"
    )


# ---------------------------------------------------------------------------
# Dokumentruden
#
# Den erstatter DocumentType og DocumentLink. De to felter var et link,
# brugeren selv skulle skaffe; her ligger filen i biblioteket, og appen
# kender den.
#
# Ruden hoerer til den VALGTE, GEMTE raekke - ikke til formularen. Mappen
# hedder raekkens ItemKey, og den findes foerst efter Gem.
# ---------------------------------------------------------------------------
def build_attachments():
    picker = Ctrl(att.PICKER, "Attachments@2.3.0", props={
        "AccessibleLabel": '"Vaelg dokumenter"',
        "BorderColor": C_CARD_BORDER,
        "BorderThickness": "1",
        "DisplayMode": DM_SEL,
        "Height": "110",
        "MaxAttachments": "10",
        # 10 MB, ikke 50. App checker advarer ved store filer, og den har
        # ret i mere end den siger: Attachments-kontrollen holder filen i
        # hukommelsen som base64, og flowet sender den videre i samme form.
        # En datablad eller en manual er langt under; 50 MB var et tal, der
        # stod der, fordi det var stort nok - ikke fordi nogen havde valgt det.
        "MaxAttachmentSize": "10",
        "NoAttachmentsText": '"Traek dokumenter hertil, eller gennemse"',
        "PaddingBottom": "5", "PaddingLeft": "5",
        "PaddingRight": "5", "PaddingTop": "5",
        "Width": "Parent.Width",
    }, h=110)

    up = button("btnDomAttUpload", '"Laeg op i SharePoint"', att.upload_fx(),
                primary=True, display_mode=DM_SEL)
    refresh = button("btnDomAttRefresh", '"Hent forfra"',
                     att.refresh_button_fx(), display_mode=DM_SEL)
    rem = button("btnDomAttRemove", '"Fjern dokument"', att.delete_fx(),
                 danger=True, display_mode=DM_SEL)
    actions = button_row("conDomAttActions", [up, refresh, rem], EDITOR_W)

    chk = Ctrl("chkDomAttSel", "ModernCheckbox", props={
        "AccessibleLabel": '"Vaelg dokument"',
        "Default": "ThisItem.Selected",
        "Height": "24",
        "Label": '""',
        "OnCheck": "Patch(colDomAttachments, ThisItem, { Selected: true })",
        "OnUncheck": "Patch(colDomAttachments, ThisItem, { Selected: false })",
        "Width": "30",
    }, h=24)
    name = text_ctrl("txtDomAttName", "ThisItem.FileName", size=13, height=28,
                     width=340, wrap="false")
    link = button("btnDomAttOpen", '"Aabn"',
                  "Launch(ThisItem.FileUrl, { }, LaunchTarget.New)",
                  width=80, height=28)
    row = group("conDomAttRow", pin_widths([chk, name, link]),
                direction="Horizontal", gap=10,
                height="Parent.TemplateHeight - 2", align_items="Center",
                width="Parent.TemplateWidth")

    # Filnavnet er raekkens noegle - der er INGEN LineId paa dokumenterne.
    # VH-plan-appen sorterede paa en LineId, der ikke fandtes; Items gik i
    # fejl, galleriet stod tomt, og filerne laa i biblioteket hele tiden.
    gal_h = f"Max(CountRows({att.ACTIVE}), 1) * 34"
    gal = Ctrl("galDomAttachments", "Gallery", variant="Vertical", props={
        "AccessibleLabel": '"Dokumenter paa den valgte raekke"',
        "BorderStyle": "BorderStyle.None",
        "Fill": C_TRANSPARENT,
        "FillPortions": "0",
        "Height": gal_h,
        "Items": f"Sort({att.ACTIVE}, FileName)",
        "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None",
        "Selectable": "true",
        "ShowScrollbar": "true",
        "TabIndex": "0",
        "TemplatePadding": "2",
        "TemplateSize": "32",
        "Width": "Parent.Width",
        "WrapCount": "1",
    }, children=[row], h=gal_h)

    empty = text_ctrl("txtDomAttEmpty", att.empty_text_fx(), size=13,
                      color=C_MUTED, height=36, wrap="true",
                      visible=f"IfError(CountRows({att.ACTIVE}) = 0, false)")

    return card("conDomAttCard",
                [text_ctrl("txtDomAttH", '"Dokumenter"', size=16,
                           weight="Semibold", height=22, wrap="false"),
                 picker, actions, gal, empty])


# ---------------------------------------------------------------------------
# De gemte raekker
# ---------------------------------------------------------------------------
GAP = 10
FIXED = sum(w for _n, w in cfg.LIST_COLS) + GAP * (len(cfg.LIST_COLS) - 1)
MAIN_W = f"Parent.Width - {FIXED}"

SEARCH = " || ".join(
    f"Trim(txtDomSearch.Text) in {c}" for c in cfg.SEARCH_FIELDS)
SCOPE = (
    "Filter(\n"
    "    colDomRows,\n"
    f"    (IsBlank(Trim(txtDomSearch.Text)) || {SEARCH}),\n"
    "    (drpDomStatusFilter.Selected.Value = \"alle\" ||\n"
    "     Status = drpDomStatusFilter.Selected.Value)\n"
    ")"
)


def _head_cell(i, label, width):
    w = MAIN_W if width == 0 else width
    return text_ctrl(f"txtDomHead{i}", f'"{label}"', size=11, color=C_MUTED,
                     weight="Semibold", height=18, width=w, wrap="false")


def build_rows():
    search = text_input("txtDomSearch", '""',
                        placeholder='"Soeg i beskrivelse, funktionsplads, nummer"',
                        width="360")
    status = dropdown("drpDomStatusFilter", '["alle", "valid", "submitted"]',
                      '"alle"', width="160")
    toolbar = group("conDomToolbar", pin_widths([search, status]),
                    direction="Horizontal", gap=12, align_items="Center")

    head = group("conDomListHead",
                 pin_widths([_head_cell(i, n, w)
                             for i, (n, w) in enumerate(cfg.LIST_COLS)]),
                 direction="Horizontal", gap=GAP, height=18,
                 align_items="Center")

    cells = [text_ctrl("txtDomRowText",
                       f'If(IsBlank(Trim(ThisItem.{cfg.C_TEXT})), "(uden tekst)", ThisItem.{cfg.C_TEXT})',
                       size=14, height=20, width=MAIN_W, wrap="false")]
    for i, col in enumerate(cfg.LIST_FIELDS):
        cells.append(text_ctrl(f"txtDomRow{i}", f"ThisItem.{col}", size=13,
                               color=C_MUTED, height=20,
                               width=cfg.LIST_COLS[i + 1][1], wrap="false"))
    cells.append(badge("txtDomRowStatus", "ThisItem.Status",
                       width=cfg.LIST_COLS[-2][1]))
    cells.append(text_ctrl("txtDomRowFiles", "Text(ThisItem.FileCount)",
                           size=13, color=C_MUTED, height=20,
                           width=cfg.LIST_COLS[-1][1], wrap="false"))

    row = group("conDomRow", pin_widths(cells), direction="Horizontal", gap=GAP,
                height="Parent.TemplateHeight - 2", align_items="Center",
                width="Parent.TemplateWidth")

    gal_h = f"Max(Min(CountRows({SCOPE}), {GAL_ROWS}), 1) * {ROW_H + 2}"
    gal = Ctrl("galDomRows", "Gallery", variant="Vertical", props={
        "AccessibleLabel": '"Gemte raekker"',
        "BorderStyle": "BorderStyle.None",
        "Fill": C_TRANSPARENT,
        "FillPortions": "0",
        "Height": gal_h,
        "Items": f"Sort({SCOPE}, RowId, SortOrder.Descending)",
        "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None",
        "OnSelect": load_row_fx(),
        "Selectable": "true",
        "ShowScrollbar": "true",
        "TabIndex": "0",
        "TemplatePadding": "2",
        "TemplateSize": str(ROW_H),
        "Width": "Parent.Width",
        "WrapCount": "1",
    }, children=[row], h=gal_h)

    empty = text_ctrl("txtDomNoRows",
                      '"Ingen gemte raekker endnu."',
                      size=13, color=C_MUTED, height=22, wrap="false",
                      visible="IfError(CountRows(colDomRows) = 0, false)")

    return card("conDomRowsCard",
                [text_ctrl("txtDomRowsH", '"Gemte raekker"', size=16,
                           weight="Semibold", height=22, wrap="false"),
                 toolbar, head, gal, empty])


# ---------------------------------------------------------------------------
# Indsend
#
# Nummeret kommer fra indeksraekkens eget ID. Det kraever ingen taeller,
# intet flow og ingen aftale mellem apps om hvem der uddeler numre - og to
# brugere, der indsender samtidig, kan ikke faa det samme nummer.
# ---------------------------------------------------------------------------
VALID = 'Filter(colDomRows, Status = "valid")'


def submit_fx():
    return (
        "If(\n"
        f"    CountRows({VALID}) = 0,\n"
        '    Set(varDomInfo, "Der er ingen gyldige raekker at indsende."),\n'
        "\n"
        "    Set(varDomRequestGuid, GUID());\n"
        "    Set(\n"
        "        varDomIdx,\n"
        "        Patch(\n"
        f"            {cfg.L_INDEX},\n"
        f"            Defaults({cfg.L_INDEX}),\n"
        "            {\n"
        f'                Domain: {{ Value: "{cfg.DOMAIN}" }},\n'
        '                Status: { Value: "Indsendt" },\n'
        "                StatusStep: 2,\n"
        "                IsOpen: true,\n"
        "                RequesterEmail: varDomMe,\n"
        "                RequesterName: User().FullName,\n"
        f'                ShortText: "{cfg.TITLE}: " & CountRows({VALID}) & " raekke(r)",\n'
        f"                Plant: First({VALID}).Plant,\n"
        f"                ItemCount: CountRows({VALID}),\n"
        "                RequestGuid: varDomRequestGuid,\n"
        f'                AppUrl: "{cfg.PLAY_URL}?reqid=" & varDomRequestGuid,\n'
        "                LastActionOn: Now(),\n"
        "                LastActionBy: varDomMe\n"
        "            }\n"
        "        )\n"
        "    );\n"
        f'    Set(varDomRequestNo, "{cfg.PREFIX}-" & Text(varDomIdx.ID, "000000"));\n'
        f"    Patch({cfg.L_INDEX}, varDomIdx, {{ RequestNo: varDomRequestNo }});\n"
        "\n"
        # Patch(kilde, RAEKKER, AENDRINGER) - een skrivning, ikke een pr.
        # raekke. Her stod Patch inde i ForAll, og App checker melder det
        # som ForAllWithMutation: mod en datakilde er det eet netvaerkskald
        # pr. iteration. De to tabeller kommer fra samme filter i samme
        # raekkefoelge, saa de staar over for hinanden.
        "    Patch(\n"
        f"        {cfg.L_ROWS},\n"
        "        ForAll(\n"
        f"            {VALID} As R,\n"
        f"            LookUp({cfg.L_ROWS}, ID = R.RowId)\n"
        "        ),\n"
        "        ForAll(\n"
        f"            {VALID} As R,\n"
        "            {\n"
        "                RequestNo: varDomRequestNo,\n"
        "                RequestGuid: varDomRequestGuid,\n"
        '                RowStatus: { Value: "submitted" },\n'
        "                SubmittedOn: Now()\n"
        "            }\n"
        "        )\n"
        "    );\n"
        "\n"
        + refresh_rows_fx(4) + ";\n"
        "\n"
        '    Set(varDomRowStatus, "submitted");\n'
        '    Set(varDomInfo, "Indsendt som " & varDomRequestNo)\n'
        ")"
    )


def build_submit():
    submit = button("btnDomSubmit", '"Indsend"', submit_fx(), primary=True,
                    width=150,
                    display_mode=f'If(CountRows({VALID}) = 0, DisplayMode.Disabled, DisplayMode.Edit)')
    reload_ = button("btnDomReload", '"Hent forfra"',
                     refresh_rows_fx() + ';\nSet(varDomInfo, "Hentet forfra.")',
                     width=150)
    note = text_ctrl(
        "txtDomSubmitNote",
        ('"Indsend skriver een raekke i MD_RequestIndex, saa indmeldingen '
         'kan ses paa landingssiden. Kun raekker med status valid sendes."'),
        size=12, color=C_MUTED, height=18, wrap="false")
    return card("conDomSubmitCard",
                [button_row("conDomSubmitRow", [submit, reload_], SHELL_W), note])
