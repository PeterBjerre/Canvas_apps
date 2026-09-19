# -*- coding: utf-8 -*-
"""
Skaermen til en domaeneapp - Equipment eller Materials.

Filen er ORDRET ens i de to build-mapper. Alt det, der skiller de to apps,
staar i domain_config.py; her staar kun formen, og den er den samme.

FORMEN
------
    Bar          hvem, hvilket nummer, hvilken status, tilbage til hubben
    Header       indmeldingens egne felter - kort tekst og vaerk
    Items        listen over poster, og hvad der kan goeres ved dem
    Detail       den aktive posts felter, bygget af SECTIONS
    Documents    dokumentruden, mod de samme tre flows som VH-plan
    Save         gem kladde, indsend

EN POST FOER ET DOKUMENT
------------------------
Dokumentmappen hedder postens noegle, og noeglen findes foerst, naar
indmeldingen er gemt. Derfor er dokumentruden ikke en fane ved siden af -
den staar under posten og siger selv fra, saa laenge noeglen mangler.

FELTERNE KOMMER FRA EEN LISTE
-----------------------------
SECTIONS i domain_config.py bestemmer BAADE kontrollen paa skaermen,
kolonnen i samlingen og formen i Patch. Det er den eneste maade at undgaa,
at de tre kommer til at sige noget forskelligt om det samme felt - og det
er praecis den fejl, der ellers opstaar, naar et felt tilfoejes et sted og
glemmes to andre.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from gen_screen import (Ctrl, SHELL_W, RAIL_W, SPLIT_GAP, EDITOR_W, FONT,
                        C_APP_BG, C_CARD_BG, C_CARD_BORDER, C_TITLE, C_MUTED,
                        C_PRIMARY, C_WHITE, C_TRANSPARENT, C_DIVIDER,
                        C_NEUTRAL_BG, C_INFO_FG, C_INFO_BG)
from build_helpers import (text_ctrl, group, button, button_row, text_input,
                           number_input, dropdown, card, field_cell, row_n,
                           label_row, pin_widths, badge)
import domain_config as cfg
import attflows as att

# Postens felter i een flad liste - rekkefoelgen er sektionernes.
FIELDS = [f for _sec, fields in cfg.SECTIONS for f in fields]

# Redigering er kun mulig, saa laenge indmeldingen er en kladde. Naar den
# er indsendt, ejer SAP-processen den.
DM = 'If(varDomStatus = "Kladde", DisplayMode.Edit, DisplayMode.View)'
DM_ITEM = ('If(varDomStatus = "Kladde" && !IsBlank(varDomActiveItemId), '
           'DisplayMode.Edit, DisplayMode.View)')

ACTIVE = "LookUp(colDomItems, LocalId = varDomActiveItemId)"
ROW_H = 44
GAL_ROWS = 8


# ---------------------------------------------------------------------------
# Den flade top
# ---------------------------------------------------------------------------
def build_bar():
    title = text_ctrl("txtDomTitle", f'"{cfg.TITLE}"', size=22, weight="Semibold",
                      height=30, wrap="false")
    sub = text_ctrl("txtDomSub", f'"{cfg.SUBTITLE}"', size=13, color=C_MUTED,
                    height=20, wrap="false")
    left = group("conDomBarLeft", [title, sub], direction="Vertical", gap=2,
                 width=f"Parent.Width - 520")

    no = text_ctrl("txtDomReqNo",
                   'If(IsBlank(varDomRequestNo), "Not saved yet", varDomRequestNo)',
                   size=15, weight="Semibold", height=24, width=160, wrap="false")
    # Statusteksten er den SharePoint-vaerdi, der faktisk staar i listen -
    # ikke en oversaettelse. Skulle den vises paa engelsk, skulle
    # ordforraadet staa eet sted, og det staar i hub_config.py, som denne
    # app ikke deler kode med.
    st = badge("txtDomStatus", 'Coalesce(varDomStatus, "Kladde")', width=140)
    back = button("btnDomBack", '"Back to hub"',
                  "Back(ScreenTransition.Fade)", width=130)
    right = group("conDomBarRight", pin_widths([no, st, back]),
                  direction="Horizontal", gap=12, align_items="Center",
                  width="500")
    return group("conDomBar", [left, right], direction="Horizontal", gap=20,
                 align_items="Center")


# ---------------------------------------------------------------------------
# Indmeldingens egne felter
# ---------------------------------------------------------------------------
def build_header():
    short = field_cell(
        "conDomShort", "Short text",
        text_input("txtDomShort", "varDomShortText", max_length=60,
                   required_formula="true", display_mode=DM,
                   onchange="Set(varDomShortText, Self.Text)"),
        required=True, container_w=SHELL_W, cols=3)
    plant = field_cell(
        "conDomPlant", "Plant",
        dropdown("drpDomPlant", "colDomPlants", "varDomPlant",
                 display_mode=DM),
        required=True, container_w=SHELL_W, cols=3)
    who = field_cell(
        "conDomWho", "Requester",
        text_input("txtDomWho", "varDomMe", display_mode="DisplayMode.View"),
        container_w=SHELL_W, cols=3)
    return card("conDomHeaderCard",
                [text_ctrl("txtDomHeaderH", '"Request"', size=16,
                           weight="Semibold", height=22, wrap="false"),
                 row_n("conDomHeaderRow", [short, plant, who],
                       container_w=SHELL_W)])


# ---------------------------------------------------------------------------
# Listen over poster
# ---------------------------------------------------------------------------
GAP = 10
FIXED = sum(w for _n, w in cfg.LIST_COLS) + GAP * (len(cfg.LIST_COLS) - 1)
MAIN_W = f"Parent.Width - {FIXED}"


def _head_cell(i, label, width):
    w = MAIN_W if width == 0 else width
    return text_ctrl(f"txtDomHead{i}", f'"{label}"', size=11, color=C_MUTED,
                     weight="Semibold", height=18, width=w, wrap="false")


def build_items():
    head = group("conDomListHead",
                 pin_widths([_head_cell(i, n, w)
                             for i, (n, w) in enumerate(cfg.LIST_COLS)]),
                 direction="Horizontal", gap=GAP, height=18,
                 align_items="Center")

    # Raekken. Foerste celle er postens tekst, de naeste er LIST_FIELDS, og
    # den sidste er antallet af dokumenter - taelt paa appens egen samling,
    # ikke mod biblioteket. Et opslag pr. raekke ville vaere eet kald pr.
    # post hver gang listen tegnes.
    cells = [text_ctrl("txtDomRowText",
                       'If(IsBlank(Trim(ThisItem.ItemText)), "(no text yet)", ThisItem.ItemText)',
                       size=14, height=20, width=MAIN_W, wrap="false")]
    for i, col in enumerate(cfg.LIST_FIELDS):
        w = cfg.LIST_COLS[i + 1][1]
        cells.append(text_ctrl(f"txtDomRow{i}", f"ThisItem.{col}", size=13,
                               color=C_MUTED, height=20, width=w, wrap="false"))
    cells.append(text_ctrl(
        "txtDomRowFiles",
        "Text(CountRows(Filter(colDomAttachments, LocalId = ThisItem.LocalId)))",
        size=13, color=C_MUTED, height=20,
        width=cfg.LIST_COLS[-1][1], wrap="false"))

    row = group("conDomRow", pin_widths(cells), direction="Horizontal", gap=GAP,
                height="Parent.TemplateHeight - 2", align_items="Center",
                width="Parent.TemplateWidth")

    gal_h = f"Max(Min(CountRows(colDomItems), {GAL_ROWS}), 1) * {ROW_H + 2}"
    gal = Ctrl("galDomItems", "Gallery", variant="Vertical", props={
        "AccessibleLabel": '"Items in this request"',
        "BorderStyle": "BorderStyle.None",
        "Fill": C_TRANSPARENT,
        "FillPortions": "0",
        "Height": gal_h,
        "Items": "Sort(colDomItems, LocalId)",
        "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None",
        "OnSelect": "Set(varDomActiveItemId, ThisItem.LocalId)",
        "Selectable": "true",
        "ShowScrollbar": "true",
        "TabIndex": "0",
        "TemplatePadding": "2",
        "TemplateSize": str(ROW_H),
        "Width": "Parent.Width",
        "WrapCount": "1",
    }, children=[row], h=gal_h)

    empty = text_ctrl("txtDomNoItems",
                      '"No items yet. Add the first one."',
                      size=13, color=C_MUTED, height=22, wrap="false",
                      visible="IfError(CountRows(colDomItems) = 0, false)")

    add = button("btnDomAdd", '"Add item"', add_item_fx(), primary=True,
                 display_mode=DM)
    rem = button("btnDomRemove", '"Remove item"', remove_item_fx(), danger=True,
                 display_mode=DM_ITEM)
    actions = button_row("conDomItemActions", [add, rem], SHELL_W)

    return card("conDomItemsCard",
                [text_ctrl("txtDomItemsH", '"Items"', size=16, weight="Semibold",
                           height=22, wrap="false"),
                 actions, head, gal, empty])


def add_item_fx():
    """Ny post. Alle felter skrives med, saa samlingens skema er komplet fra
    foerste raekke - en kolonne, der foerst dukker op paa raekke to, findes
    ikke for Power Fx."""
    blanks = ['            LocalId: varDomNextLocalId,',
              '            SpId: 0,',
              '            ItemKey: "",',
              '            ItemText: "",']
    for col, _lab, kind, _w, _ch in FIELDS:
        v = {"num": "0", "bool": "false"}.get(kind, '""')
        blanks.append(f'            {col}: {v},')
    blanks[-1] = blanks[-1].rstrip(",")
    return ("Set(varDomNextLocalId, Coalesce(Max(colDomItems, LocalId), 0) + 1);\n"
            "Collect(\n"
            "    colDomItems,\n"
            "    {\n"
            + "\n".join(blanks) + "\n"
            "    }\n"
            ");\n"
            "Set(varDomActiveItemId, varDomNextLocalId)")


def remove_item_fx():
    """Fjern posten - ogsaa i SharePoint, hvis den naaede derhen.

    Dokumenterne i biblioteket bliver staaende. De slettes eet for eet i
    dokumentruden, og det er med vilje: en post, der fjernes ved et uheld,
    maa ikke tage bilagene med sig."""
    return (
        "If(\n"
        "    IsBlank(varDomActiveItemId),\n"
        "    Notify(\"Select an item first.\", NotificationType.Warning),\n"
        "\n"
        "    With(\n"
        f"        {{ sp: {ACTIVE}.SpId }},\n"
        "        If(\n"
        "            sp > 0,\n"
        f"            Remove({cfg.L_ITEM}, LookUp({cfg.L_ITEM}, ID = sp))\n"
        "        )\n"
        "    );\n"
        "    RemoveIf(colDomItems, LocalId = varDomActiveItemId);\n"
        "    RemoveIf(colDomAttachments, LocalId = varDomActiveItemId);\n"
        "    Set(varDomActiveItemId, Blank())\n"
        ")"
    )


# ---------------------------------------------------------------------------
# Den aktive posts felter
#
# Kontrollen vaelges af feltets ART, og OnChange skriver TILBAGE i
# samlingen med det samme. Der er ingen "anvend"-knap: valget ER
# handlingen, og en knap til at bekraefte noget, brugeren lige har
# besluttet, er et klik for meget.
# ---------------------------------------------------------------------------
def _update(col, value):
    return ("UpdateIf(\n"
            "    colDomItems,\n"
            "    LocalId = varDomActiveItemId,\n"
            f"    {{ {col}: {value} }}\n"
            ")")


def _input_for(col, kind, choices):
    name = "inp" + col
    default = f"{ACTIVE}.{col}"
    if kind == "num":
        c = number_input(name, default, display_mode=DM_ITEM)
        c.props["OnChange"] = _update(col, "Self.Value")
        return c
    if kind == "bool":
        return Ctrl(name, "ModernCheckbox", props={
            "AccessibleLabel": f'"{col}"',
            "Default": default,
            "DisplayMode": DM_ITEM,
            "Height": "32",
            "Label": '""',
            "OnCheck": _update(col, "true"),
            "OnUncheck": _update(col, "false"),
            "Width": "Parent.Width",
        }, h=32)
    if kind == "choice":
        items = "[" + ", ".join(f'"{v}"' for v in choices) + "]"
        c = dropdown(name, items, default, display_mode=DM_ITEM)
        c.props["OnChange"] = _update(col, "Self.Selected.Value")
        return c
    if kind == "date":
        # Der er ingen datovaelger i repoets kontrolsaet - ingen af de to
        # eksisterende apps bruger en, saa den er ikke bevist her. Feltet
        # er derfor tekst i appen og bliver til en dato ved Patch.
        # ValidationState siger fra med det samme, hvis teksten ikke kan
        # laeses som en dato - ellers ville fejlen foerst vise sig ved Gem,
        # som en tom dato uden forklaring.
        c = text_input(name, default, placeholder='"yyyy-mm-dd"',
                       display_mode=DM_ITEM)
        c.props["OnChange"] = _update(col, "Self.Text")
        c.props["ValidationState"] = (
            "If(\n"
            "    !IsBlank(Trim(Self.Text)) && IsError(DateValue(Self.Text)),\n"
            "    ValidationState.Error,\n"
            "    ValidationState.None\n"
            ")")
        return c
    c = text_input(name, default, display_mode=DM_ITEM)
    c.props["OnChange"] = _update(col, "Self.Text")
    return c


COLS_PER_ROW = 3


def build_detail():
    kids = [text_ctrl("txtDomDetailH", '"Item details"', size=16,
                      weight="Semibold", height=22, wrap="false")]

    # Postens tekst staar for sig. Den er listens Title, den er
    # obligatorisk, og den er det eneste felt, der ogsaa staar i
    # oversigten - derfor over de andre og i fuld bredde.
    kids.append(field_cell(
        "conDomItemText", cfg.ITEM_TEXT_LABEL,
        text_input("inpDomItemText", f"{ACTIVE}.ItemText", max_length=40,
                   placeholder=cfg.ITEM_TEXT_PLACEHOLDER,
                   required_formula="true", display_mode=DM_ITEM,
                   onchange=_update("ItemText", "Self.Text")),
        required=True, container_w=EDITOR_W, cols=1,
        fill_portions_formula="0"))

    for s_i, (section, fields) in enumerate(cfg.SECTIONS):
        kids.append(text_ctrl(f"txtDomSec{s_i}", f'"{section}"', size=13,
                              weight="Semibold", color=C_MUTED, height=20,
                              wrap="false"))
        chunk = []
        for f_i, (col, label, kind, _w, choices) in enumerate(fields):
            chunk.append(field_cell(
                f"con{col}", label, _input_for(col, kind, choices),
                container_w=EDITOR_W, cols=COLS_PER_ROW))
            if len(chunk) == COLS_PER_ROW:
                kids.append(row_n(f"conDomRow{s_i}_{f_i}", chunk,
                                  container_w=EDITOR_W))
                chunk = []
        if chunk:
            kids.append(row_n(f"conDomRow{s_i}_end", chunk,
                              container_w=EDITOR_W))

    empty = text_ctrl("txtDomNoActive",
                      '"Select an item in the list to edit it."',
                      size=13, color=C_MUTED, height=22, wrap="false",
                      visible="IsBlank(varDomActiveItemId)")
    return card("conDomDetailCard", [empty] + kids)


# ---------------------------------------------------------------------------
# Dokumentruden
# ---------------------------------------------------------------------------
def build_attachments():
    picker = Ctrl(att.PICKER, "Attachments@2.3.0", props={
        "AccessibleLabel": '"Choose documents"',
        "BorderColor": C_CARD_BORDER,
        "BorderThickness": "1",
        "DisplayMode": DM_ITEM,
        "Height": "120",
        "MaxAttachments": "10",
        "MaxAttachmentSize": "50",
        "NoAttachmentsText": '"Drop documents here, or browse"',
        "PaddingBottom": "5", "PaddingLeft": "5",
        "PaddingRight": "5", "PaddingTop": "5",
        "Width": "Parent.Width",
    }, h=120)

    up = button("btnDomAttUpload", '"Upload to SharePoint"', att.upload_fx(),
                primary=True, display_mode=DM_ITEM)
    refresh = button("btnDomAttRefresh", '"Refresh from SharePoint"',
                     att.refresh_button_fx(), display_mode=DM_ITEM)
    rem = button("btnDomAttRemove", '"Remove document"', att.delete_fx(),
                 danger=True, display_mode=DM_ITEM)
    actions = button_row("conDomAttActions", [up, refresh, rem], EDITOR_W)

    chk = Ctrl("chkDomAttSel", "ModernCheckbox", props={
        "AccessibleLabel": '"Select document"',
        "Default": "ThisItem.Selected",
        "Height": "24",
        "Label": '""',
        "OnCheck": "Patch(colDomAttachments, ThisItem, { Selected: true })",
        "OnUncheck": "Patch(colDomAttachments, ThisItem, { Selected: false })",
        "Width": "30",
    }, h=24)
    name = text_ctrl("txtDomAttName", "ThisItem.FileName", size=13, height=28,
                     width=360, wrap="false")
    link = text_ctrl("txtDomAttLink", "ThisItem.FileUrl", size=12, color=C_MUTED,
                     height=28, width=420, wrap="false")
    row = group("conDomAttRow", pin_widths([chk, name, link]),
                direction="Horizontal", gap=10,
                height="Parent.TemplateHeight - 2", align_items="Center",
                width="Parent.TemplateWidth")

    # Filnavnet er raekkens noegle - der er INGEN LineId paa dokumenterne.
    # VH-plan-appen sorterede paa en LineId, der ikke fandtes; Items gik i
    # fejl, og galleriet stod tomt, mens filerne laa i biblioteket. Den
    # fejl gentages ikke her.
    gal_h = f"Max(CountRows({att.ACTIVE}), 1) * 34"
    gal = Ctrl("galDomAttachments", "Gallery", variant="Vertical", props={
        "AccessibleLabel": '"Documents on this item"',
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
                [text_ctrl("txtDomAttH", '"Documents"', size=16,
                           weight="Semibold", height=22, wrap="false"),
                 picker, actions, gal, empty])


# ---------------------------------------------------------------------------
# Gem
#
# Nummeret kommer fra SharePoint, ikke fra appen. Raekken oprettes foerst,
# og dens ID bliver til EQ-000912. Det kraever ingen taeller, intet flow og
# ingen aftale mellem to apps om hvem der uddeler numre - og to brugere,
# der gemmer samtidig, kan ikke faa det samme nummer.
#
# Postens noegle er <indmelding>-<linje>: EQ-000912-001. Den er ogsaa
# mappenavnet i dokumentbiblioteket, og derfor skal den vaere unik paa
# tvaers af domaener - det er den, fordi praefikset er det.
# ---------------------------------------------------------------------------
KEY_EXPR = 'varDomRequestNo & "-" & Text(I.LocalId, "000")'

REQUIRED_CHOICES = [col for col, _l, kind, _w, ch in FIELDS
                    if kind == "choice" and col in ("ChangeType",
                                                    "EquipmentCategory",
                                                    "MaterialType",
                                                    "IndustrySector")]


def _patch_value(col, kind):
    """Vaerdien som SharePoint vil have den.

    En valgkolonne vil have { Value: ... } - men ikke en tom af slagsen:
    en valgkolonne uden vaerdi er Blank(), ikke { Value: "" }. Datoer er
    tekst i appen og bliver til datoer her; kan teksten ikke laeses, bliver
    feltet tomt i stedet for at vaelte hele Patch."""
    if kind == "choice":
        return (f"If(IsBlank(I.{col}), Blank(), {{ Value: I.{col} }})")
    if kind == "date":
        return (f"If(IsBlank(Trim(I.{col})), Blank(), "
                f"IfError(DateValue(I.{col}), Blank()))")
    return f"I.{col}"


def _item_patch():
    lines = [
        f"                        {cfg.C_ITEM_TEXT}: I.ItemText,",
        f"                        {cfg.C_REQ_NO}: varDomRequestNo,",
        "                        RequestId: varDomReqId,",
        "                        LineId: I.LocalId,",
        "                        ItemKey: key,",
        f'                        AttachmentFolder: "{att.LIBRARY}/" & key,',
        "                        FileCount: CountRows(",
        "                            Filter(colDomAttachments, LocalId = I.LocalId)",
        "                        ),",
    ]
    for col, _lab, kind, _w, _ch in FIELDS:
        lines.append(f"                        {col}: {_patch_value(col, kind)},")
    lines[-1] = lines[-1].rstrip(",")
    return "\n".join(lines)


def save_fx(submit=False):
    status = "Indsendt" if submit else "Kladde"
    step = 2 if submit else 1
    guard = ['IsBlank(Trim(varDomShortText))', 'IsBlank(varDomPlant)']
    if submit:
        guard.append("CountRows(colDomItems) = 0")
        for col in REQUIRED_CHOICES:
            guard.append(f"CountRows(Filter(colDomItems, IsBlank({col}))) > 0")
        guard.append("CountRows(Filter(colDomItems, IsBlank(Trim(ItemText)))) > 0")
    msg = ("Short text, plant, at least one item, and every item's required "
           "fields must be filled in before submitting."
           if submit else "Short text and plant are required.")

    head_common = (
        "            Plant: varDomPlant,\n"
        "            ShortText: varDomShortText,\n"
        "            ItemCount: CountRows(colDomItems),\n"
        f'            Status: {{ Value: "{status}" }},\n'
        f"            StatusStep: {step},\n"
        "            IsOpen: true,\n"
        "            LastActionOn: Now(),\n"
        "            LastActionBy: varDomMe")
    submitted = ",\n            SubmittedOn: Now()" if submit else ""

    idx = (
        "                    Domain: { Value: \"" + cfg.DOMAIN + "\" },\n"
        f'                    Status: {{ Value: "{status}" }},\n'
        f"                    StatusStep: {step},\n"
        "                    IsOpen: true,\n"
        "                    RequesterEmail: varDomMe,\n"
        "                    RequesterName: User().FullName,\n"
        "                    ShortText: varDomShortText,\n"
        "                    Plant: varDomPlant,\n"
        "                    ItemCount: CountRows(colDomItems),\n"
        "                    RequestGuid: varDomGuid,\n"
        "                    SourceItemId: varDomReqId,\n"
        "                    AppUrl: If(\n"
        "                        IsBlank(varDomPlayUrl),\n"
        '                        "",\n'
        '                        varDomPlayUrl & "?reqid=" & varDomGuid\n'
        "                    ),\n"
        "                    LastActionOn: Now(),\n"
        "                    LastActionBy: varDomMe")

    return (
        "If(\n"
        f"    {' || '.join(guard)},\n"
        f'    Notify("{msg}", NotificationType.Warning),\n'
        "\n"
        "    // 1. Indmeldingen - foerste gang oprettes raekken, og dens\n"
        "    //    ID bliver til nummeret\n"
        "    If(\n"
        "        varDomReqId = 0,\n"
        "        Set(\n"
        "            varDomHdr,\n"
        "            Patch(\n"
        f"                {cfg.L_REQ},\n"
        f"                Defaults({cfg.L_REQ}),\n"
        "                {\n"
        "                    RequestGuid: varDomGuid,\n"
        "                    RequesterEmail: varDomMe,\n"
        "                    RequesterName: User().FullName,\n"
        + head_common.replace("            ", "                    ") + submitted.replace("            ", "                    ") + "\n"
        "                }\n"
        "            )\n"
        "        );\n"
        "        Set(varDomReqId, varDomHdr.ID);\n"
        f'        Set(varDomRequestNo, "{cfg.PREFIX}-" & Text(varDomHdr.ID, "000000"));\n'
        f"        Patch({cfg.L_REQ}, varDomHdr, {{ {cfg.C_REQ_NO}: varDomRequestNo }}),\n"
        "\n"
        "        Patch(\n"
        f"            {cfg.L_REQ},\n"
        f"            LookUp({cfg.L_REQ}, ID = varDomReqId),\n"
        "            {\n"
        + head_common + submitted + "\n"
        "            }\n"
        "        )\n"
        "    );\n"
        "\n"
        "    // 2. Posterne. SpId og ItemKey skrives tilbage i samlingen,\n"
        "    //    saa naeste gem opdaterer i stedet for at oprette igen -\n"
        "    //    og saa dokumentruden ved, hvad mappen hedder.\n"
        "    Clear(colDomSaved);\n"
        "    ForAll(\n"
        "        colDomItems As I,\n"
        "        With(\n"
        f"            {{ key: {KEY_EXPR} }},\n"
        "            Collect(\n"
        "                colDomSaved,\n"
        "                {\n"
        "                    LocalId: I.LocalId,\n"
        "                    ItemKey: key,\n"
        "                    SpId: Patch(\n"
        f"                        {cfg.L_ITEM},\n"
        "                        If(\n"
        "                            I.SpId > 0,\n"
        f"                            LookUp({cfg.L_ITEM}, ID = I.SpId),\n"
        f"                            Defaults({cfg.L_ITEM})\n"
        "                        ),\n"
        "                        {\n"
        + _item_patch() + "\n"
        "                        }\n"
        "                    ).ID\n"
        "                }\n"
        "            )\n"
        "        )\n"
        "    );\n"
        "    ForAll(\n"
        "        colDomSaved As S,\n"
        "        UpdateIf(\n"
        "            colDomItems,\n"
        "            LocalId = S.LocalId,\n"
        "            { SpId: S.SpId, ItemKey: S.ItemKey }\n"
        "        )\n"
        "    );\n"
        "\n"
        "    // 3. Raekken i det faelles indeks. Den er landingssidens ENESTE\n"
        "    //    kilde - uden den findes indmeldingen ikke for hubben.\n"
        "    With(\n"
        f"        {{ idx: LookUp({cfg.L_INDEX}, RequestGuid = varDomGuid) }},\n"
        "        Patch(\n"
        f"            {cfg.L_INDEX},\n"
        f"            If(IsBlank(idx), Defaults({cfg.L_INDEX}), idx),\n"
        "            {\n"
        f"                {cfg.C_REQ_NO}: varDomRequestNo,\n"
        + idx.replace("                    ", "                ") + "\n"
        "            }\n"
        "        )\n"
        "    );\n"
        "\n"
        f'    Set(varDomStatus, "{status}");\n'
        f'    Notify("{"Submitted as " if submit else "Saved as "}" & varDomRequestNo, '
        "NotificationType.Success)\n"
        ")"
    )


def build_savebar():
    save = button("btnDomSave", '"Save draft"', save_fx(False), width=150,
                  display_mode=DM)
    submit = button("btnDomSubmit", '"Submit"', save_fx(True), primary=True,
                    width=150, display_mode=DM)
    note = text_ctrl("txtDomSaveNote",
                     '"The request number is assigned by SharePoint on the '
                     'first save. Documents can be attached once an item has '
                     'a key."',
                     size=12, color=C_MUTED, height=18, wrap="false")
    return card("conDomSaveCard",
                [button_row("conDomSaveRow", [save, submit], SHELL_W), note])
