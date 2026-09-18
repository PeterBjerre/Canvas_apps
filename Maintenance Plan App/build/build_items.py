# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import (Ctrl, C_CARD_BG, C_CARD_BORDER, C_TITLE, C_MUTED, C_REQUIRED, C_PRIMARY, C_WHITE,
                        C_INFO_FG, C_INFO_BG, C_VALID_FG, C_VALID_BG, C_INVALID_FG, C_INVALID_BG,
                        C_NEUTRAL_FG, C_NEUTRAL_BG, C_INPUT_BG, FONT, SHELL_W, EDITOR_W, RAIL_W,
                        SPLIT_GAP)
from build_helpers import (text_ctrl, group, button, button_row, text_input, number_input, dropdown,
                           label_row, field_cell, row_n, col_width, badge, card, combobox, poll_timer,
                           TWO_COL_MIN, HINTS_ON)
from build_plan_header import section_header, help_panel
import build_help as bh
from build_flsearch import search_action, MIN_SEARCH_LEN

DM_ITEM = "If(IsBlank(varVhpActiveItemId), DisplayMode.Disabled, DisplayMode.Edit)"
REQ_ITEM = "varVhpItemValidated"

# Items-skinnens og editorens indholdsbredde (kortbredde minus 18+18 polstring).
RAIL_CW = RAIL_W - 36
EDITOR_CW = f"({EDITOR_W} - 36)"

# Tre kolonner i stedet for to for indtastningsfelterne i Item Editor.
EDITOR_COLS = 3

# Bredden paa Soeg-knappen i FL-blokken.
FL_BTN_W = 84

# Gallerihoejde: TemplateSize + TemplatePadding pr. raekke. Den oprindelige
# formel regnede kun med TemplateSize og klippede derfor den sidste raekke.
ITEM_ROW_H = 88 + 6
ITEMS_GAL_H = f"Max(CountRows(colVhpItems), 1) * {ITEM_ROW_H}"

# Den FL der er valgt lige nu: dropdownens valg, med fald tilbage til det
# gemte paa itemet, saa objektlisten ogsaa filtrerer korrekt foer brugeren
# har roert dropdownen.
SEL_FL = ("Coalesce(drpVhpItemFL.Selected.Code, "
          "LookUp(colVhpItems, ItemId = varVhpActiveItemId).FunctionalLocation)")

# Kandidater til objektlisten: alt under den valgte FL, minus den selv.
#
# De kommer fra colVhpFlSearch - altsaa SAMME resultat som FL-soegningen
# hentede. Objektlisten kalder aldrig selv flowet: soeger man fx "SSV13 HFC10",
# returnerer flowet baade SSV13 HFC10 og alt under den, saa de underliggende
# FL ligger allerede i samlingen.
#
# !IsBlank(SEL_FL) foerst er ikke pynt. StartsWith(Code, "") er SAND for alt,
# saa uden den betingelse ville objektlisten vise HELE soegeresultatet - 819
# raekker - saa laenge der ikke var valgt en Functional Location. Altsaa det
# stik modsatte af at vaere filtreret af FL-feltet.
OBJ_CANDIDATES = (
    f"Filter(\n"
    f"    colVhpFlSearch,\n"
    f"    !IsBlank({SEL_FL}) && StartsWith(Code, {SEL_FL}) && Code <> {SEL_FL}\n"
    f")"
)

# De objekter, der er valgt paa det aktive item. colVhpItemObjects ER
# sandheden nu - der er ingen multi-select-kontrol, der kan holde en
# konkurrerende liste.
OBJ_CHOSEN = "Filter(colVhpItemObjects, ItemId = varVhpActiveItemId)"

FL_DEFAULT = ("LookUp(colVhpFlSearch, "
              "Code = LookUp(colVhpItems, ItemId = varVhpActiveItemId).FunctionalLocation)")

RESET_EDITOR_CONTROLS = (
    "Reset(drpVhpItemFL); Reset(txtVhpFlQuery); "
    "Reset(txtVhpItemShortText); "
    "Reset(drpVhpItemMainWorkCenter); Reset(drpVhpItemActivityType); Reset(drpVhpItemRevision); "
    "Reset(txtVhpItemOrstedResponsible); Reset(txtVhpItemInitials); Reset(txtVhpItemLongText); "
    "Reset(drpVhpItemTasklist)"
)

# Naar et andet item aabnes, skal comboboksen kunne vise itemets gemte FL.
# Soegesamlingen er tom paa det tidspunkt, saa den seedes med den ene vaerdi.
# Display skal med, fordi det er det felt comboboksen soeger og viser paa.
SEED_FL_PICKER = (
    "Clear(colVhpFlSearch);\n"
    "With(\n"
    "    { it: LookUp(colVhpItems, ItemId = varVhpActiveItemId) },\n"
    "    If(\n"
    "        !IsBlank(it.FunctionalLocation),\n"
    "        Collect(\n"
    "            colVhpFlSearch,\n"
    "            { Code: it.FunctionalLocation, Description: it.FlDescription,\n"
    "              Display: it.FunctionalLocation & \" - \" & it.FlDescription,\n"
    "              Maintainable: true, Level: \"\" }\n"
    "        )\n"
    "    )\n"
    ");\n"
    "Set(varVhpFlLastSearch, \"\")"
)


def build_items_rail():
    header = section_header("conVhpItemsHead", "Items",
                            "Each item has its own functional location, task list and operations.", "Step 2")

    btnAdd = button(
        "btnVhpAddItem", "\"Add item\"",
        (
            "If(\n"
            "    !varVhpPlanCommitted,\n"
            "    Set(varVhpRuntimeInfo, \"Save the plan before adding items.\"),\n"
            "\n"
            "    Set(varVhpNextItemId, varVhpNextItemId + 1);\n"
            "    Collect(\n"
            "        colVhpItems,\n"
            "        {\n"
            "            ItemId: varVhpNextItemId, ShortText: \"\", FunctionalLocation: \"\", FlDescription: \"\",\n"
            "            MainWorkCenter: \"\", ActivityType: \"\", ObjectList: \"\", Revision: \"\",\n"
            "            OrstedResponsible: \"\", Initials: \"\", LongText: \"\", TasklistKey: \"\", TasklistName: \"\",\n"
            "            Status: \"draft\"\n"
            "        }\n"
            "    );\n"
            "    Set(varVhpActiveItemId, varVhpNextItemId);\n"
            "    Set(varVhpItemValidated, false);\n"
            "    Set(varVhpFlMeta, \"\");\n"
            f"    {SEED_FL_PICKER};\n"
            f"    {RESET_EDITOR_CONTROLS};\n"
            "    Set(varVhpRuntimeInfo, \"Item \" & Text(varVhpNextItemId) & \" added.\")\n"
            ")"
        ))

    btnCopy = button(
        "btnVhpCopyItem", "\"Copy item\"",
        (
            "If(\n"
            "    IsBlank(varVhpActiveItemId) || CountRows(Filter(colVhpItems, ItemId = varVhpActiveItemId)) = 0,\n"
            "    Set(varVhpRuntimeInfo, \"Select an item to copy first.\"),\n"
            "\n"
            "    With(\n"
            "        { src: LookUp(colVhpItems, ItemId = varVhpActiveItemId) },\n"
            "        Set(varVhpNextItemId, varVhpNextItemId + 1);\n"
            "        Collect(\n"
            "            colVhpItems,\n"
            "            {\n"
            "                ItemId: varVhpNextItemId, ShortText: src.ShortText, FunctionalLocation: \"\",\n"
            "                FlDescription: \"\", MainWorkCenter: src.MainWorkCenter, ActivityType: src.ActivityType,\n"
            "                ObjectList: src.ObjectList, Revision: src.Revision,\n"
            "                OrstedResponsible: src.OrstedResponsible, Initials: src.Initials, LongText: src.LongText,\n"
            "                TasklistKey: src.TasklistKey, TasklistName: src.TasklistName, Status: \"draft\"\n"
            "            }\n"
            "        );\n"
            "        ForAll(\n"
            "            Filter(colVhpOperations, ItemId = varVhpActiveItemId),\n"
            "            Collect(\n"
            "                colVhpOperations,\n"
            "                {\n"
            "                    ItemId: varVhpNextItemId, OperationNo: OperationNo,\n"
            "                    OperationShortText: OperationShortText, WorkHours: WorkHours,\n"
            "                    DurationHours: DurationHours, MainWorkCenter: MainWorkCenter, Vendor: Vendor,\n"
            "                    LongText: LongText, PackagesKey: PackagesKey, Selected: false\n"
            "                }\n"
            "            )\n"
            "        );\n"
            "        ForAll(\n"
            "            Filter(colVhpItemObjects, ItemId = varVhpActiveItemId) As OBJ,\n"
            "            Collect(\n"
            "                colVhpItemObjects,\n"
            "                { ItemId: varVhpNextItemId, Code: OBJ.Code, Description: OBJ.Description }\n"
            "            )\n"
            "        );\n"
            "        Set(varVhpActiveItemId, varVhpNextItemId);\n"
            f"        {SEED_FL_PICKER};\n"
            f"        {RESET_EDITOR_CONTROLS};\n"
            "        Set(varVhpRuntimeInfo, \"Item copied. Functional Location cleared on the copied item.\")\n"
            "    )\n"
            ")"
        ))

    btnRemove = button(
        "btnVhpRemoveItem", "\"Remove item\"",
        (
            "If(\n"
            "    IsBlank(varVhpActiveItemId),\n"
            "    Set(varVhpRuntimeInfo, \"Select an item to remove first.\"),\n"
            "\n"
            "    RemoveIf(colVhpOperations, ItemId = varVhpActiveItemId);\n"
            "    RemoveIf(colVhpItemObjects, ItemId = varVhpActiveItemId);\n"
            "    RemoveIf(colVhpItems, ItemId = varVhpActiveItemId);\n"
            "    Set(varVhpActiveItemId, If(CountRows(colVhpItems) > 0, First(colVhpItems).ItemId, Blank()));\n"
            f"    {RESET_EDITOR_CONTROLS};\n"
            "    Set(varVhpRuntimeInfo, \"Item removed.\")\n"
            ")"
        ), danger=True)

    # Knapperne deler bredden ligeligt, saa raekken aldrig ombryder.
    btnRow = button_row("conVhpItemButtonRow", [btnAdd, btnCopy, btnRemove], RAIL_CW)

    # --- item card template -------------------------------------------------
    cardTitle = text_ctrl(
        "txtVhpItemCardTitle",
        "If(IsBlank(ThisItem.ShortText), \"Item \" & Text(ThisItem.ItemId), ThisItem.ShortText)",
        size=14, weight="Semibold", height=20, wrap="false")
    cardFl = text_ctrl(
        "txtVhpItemCardFl",
        "\"FL: \" & If(IsBlank(ThisItem.FunctionalLocation), \"No FL\", ThisItem.FunctionalLocation)",
        size=12, color=C_MUTED, height=18, wrap="false")
    cardTasklist = text_ctrl(
        "txtVhpItemCardTasklist",
        "If(IsBlank(ThisItem.TasklistName), \"No tasklist\", ThisItem.TasklistName) & \" | Ops: \" & Text(CountRows(Filter(colVhpOperations, ItemId = ThisItem.ItemId)))",
        size=12, color=C_MUTED, height=18, wrap="false")
    cardTextCol = group("conVhpItemCardText", [cardTitle, cardFl, cardTasklist], direction="Vertical", gap=2,
                        fill_portions=1, width="Parent.Width - 70 - 10")
    cardStatus = text_ctrl(
        "txtVhpItemCardStatus", "Upper(ThisItem.Status)", size=11, weight="Semibold", height=22, width=66,
        wrap="false",
        extra={
            "Align": "Align.Center", "AlignInContainer": "AlignInContainer.Center",
            "Color": f"Switch(ThisItem.Status, \"valid\", {C_VALID_FG}, \"invalid\", {C_INVALID_FG}, {C_MUTED})",
            "Fill": f"Switch(ThisItem.Status, \"valid\", {C_VALID_BG}, \"invalid\", {C_INVALID_BG}, {C_NEUTRAL_BG})",
            "PaddingLeft": "6", "PaddingRight": "6",
            "RadiusBottomLeft": "10", "RadiusBottomRight": "10", "RadiusTopLeft": "10", "RadiusTopRight": "10",
        })
    btnOpen = button(
        "btnVhpItemOpen", "\"Open\"",
        (
            "Set(varVhpActiveItemId, ThisItem.ItemId);\n"
            "Set(varVhpItemValidated, false);\n"
            "Set(varVhpFlMeta, \"\");\n"
            f"{SEED_FL_PICKER};\n"
            f"{RESET_EDITOR_CONTROLS}"
        ), width=70, height=30)
    cardRight = group("conVhpItemCardRight", [cardStatus, btnOpen], direction="Vertical", gap=6,
                      align_items="End", width=70)

    itemCard = group(
        "conVhpItemCard", [cardTextCol, cardRight], direction="Horizontal", gap=10,
        height="Parent.TemplateHeight - 2",
        fill=f"If(ThisItem.ItemId = varVhpActiveItemId, {C_INFO_BG}, {C_CARD_BG})",
        border_color=f"If(ThisItem.ItemId = varVhpActiveItemId, {C_INFO_FG}, {C_CARD_BORDER})",
        border_thickness=1, radius=10, pad=(10, 12, 10, 12), width="Parent.TemplateWidth",
        align_items="Center")

    gallery = Ctrl(
        "galVhpItemsRail", "Gallery", variant="Vertical",
        props={
            "AccessibleLabel": "\"VH-plan items\"",
            "BorderStyle": "BorderStyle.None",
            "Fill": "RGBA(0, 0, 0, 0)",
            "FillPortions": "0",
            "Height": ITEMS_GAL_H,
            "Items": "Sort(colVhpItems, ItemId)",
            "LayoutMinWidth": "0",
            "LoadingSpinner": "LoadingSpinner.None",
            "Selectable": "false",
            "ShowScrollbar": "false",
            "TabIndex": "0",
            "TemplatePadding": "6",
            "TemplateSize": "88",
            "Width": "Parent.Width",
            "WrapCount": "1",
        },
        children=[itemCard], h=ITEMS_GAL_H)

    emptyState = text_ctrl(
        "txtVhpItemsEmpty", "\"No items yet. Use Add item to create the first item for this plan.\"",
        size=13, color=C_MUTED, height=40, wrap="true",
        visible="IfError(CountRows(colVhpItems) = 0, true)")

    return card("conVhpItemsCard", [header, btnRow, gallery, emptyState], gap=12)


def build_item_editor():
    header = section_header("conVhpEditorHead", "Item Editor",
                            "Full item fields with functional location lookup.", "",
                            help_section="item")
    helpPanel = help_panel("conVhpItemHelp", "item")

    # --- Functional Location: soegefelt, soegeknap, dropdown ---------------
    #
    # Ingen combobox. Den forrige udgave lod en Timer polle
    # Classic/ComboBox.SearchText og lod comboboksen selv filtrere. Flowet
    # returnerede 819 raekker, beskeden sagde det - og dropdownen var TOM.
    # Comboboksens indbyggede filtrering viste ingen af de raekker, den
    # havde faaet.
    #
    # Her er der ingen skjult filtrering tilbage: dropdownen viser praecis
    # det, samlingen indeholder. Og felterne ser ud som alle de andre.
    flLabelRow = label_row("conVhpItemFlLabel", "Functional Location", required=True)
    flHint = text_ctrl("txtVhpItemFlHint", bh.hint("FunctionalLocation"), size=12,
                       color=C_MUTED, height=32, wrap="true", visible=HINTS_ON)

    txtFlQuery = text_input(
        "txtVhpFlQuery", "\"\"",
        placeholder=("\"At least %d characters, e.g. SSV13 HFC\"" % MIN_SEARCH_LEN),
        display_mode=DM_ITEM, width=f"Parent.Width - {FL_BTN_W} - 8")
    btnFlSearch = button(
        "btnVhpFlSearch", "\"Soeg\"",
        search_action("txtVhpFlQuery", "colVhpFlSearch",
                      "varVhpFlLastSearch", "varVhpFlMeta"),
        primary=True, width=FL_BTN_W, height=36, display_mode=DM_ITEM)
    flSearchRow = group("conVhpItemFlSearchRow", [txtFlQuery, btnFlSearch],
                        direction="Horizontal", gap=8, height=36,
                        align_items="Center", width="Parent.Width")

    drpFl = dropdown(
        "drpVhpItemFL", "Sort(colVhpFlSearch, Code)", FL_DEFAULT,
        item_display="ThisItem.Display",
        required_formula=REQ_ITEM, display_mode=DM_ITEM, value_field="Code")

    flDescription = text_ctrl(
        "txtVhpItemFlDescription",
        (
            "If(\n"
            "    IsBlank(drpVhpItemFL.Selected.Code), \"Ingen Functional Location valgt endnu.\",\n"
            "    \"Valgt: \" & drpVhpItemFL.Selected.Code & \" - \" &\n"
            "    drpVhpItemFL.Selected.Description &\n"
            "    If(\n"
            "        drpVhpItemFL.Selected.Maintainable, \"\",\n"
            "        \"   |   ADVARSEL: markeret som ikke vedligeholdbar i SAP.\"\n"
            "    )\n"
            ")"
        ),
        size=12, height=18, wrap="true",
        color=("If(!IsBlank(drpVhpItemFL.Selected.Code) && "
               f"!drpVhpItemFL.Selected.Maintainable, {C_INVALID_FG}, {C_MUTED})"))
    flMeta = text_ctrl("txtVhpItemFlMeta", "varVhpFlMeta", size=12, color=C_MUTED,
                       height=32, wrap="true")

    flBlock = group("conVhpItemFlBlock",
                    [flLabelRow, flHint, flSearchRow, drpFl, flDescription, flMeta],
                    direction="Vertical", gap=6, width="Parent.Width",
                    # FillPortions = 0: i en LODRET container fordeler den
                    # hoejde, og blokken ville vokse ud over sit indhold.
                    fill_portions=0, align_in_container="Start")

    # 53 arbejdscentre for hele afdelingen, men kun en haandfuld hoerer til
    # det valgte vaerk. Er der ikke valgt vaerk endnu, vises de alle - en tom
    # dropdown uden forklaring er vaerre end en lang.
    MWC_ITEMS = ("Sort(\n"
                 "    If(\n"
                 "        IsBlank(varVhpPlan.Plant),\n"
                 "        colVhpMainWorkCenters,\n"
                 "        Filter(colVhpMainWorkCenters, Plant = varVhpPlan.Plant)\n"
                 "    ),\n"
                 "    Value\n"
                 ")")
    drpMwc = dropdown("drpVhpItemMainWorkCenter", MWC_ITEMS,
                      "LookUp(colVhpMainWorkCenters, Value = LookUp(colVhpItems, ItemId = varVhpActiveItemId).MainWorkCenter)",
                      required_formula=REQ_ITEM, display_mode=DM_ITEM)
    drpAct = dropdown("drpVhpItemActivityType", "colVhpActivityTypeOptions",
                      "LookUp(colVhpActivityTypeOptions, Value = LookUp(colVhpItems, ItemId = varVhpActiveItemId).ActivityType)",
                      required_formula=REQ_ITEM, display_mode=DM_ITEM)
    txtShort = text_input("txtVhpItemShortText",
                          "LookUp(colVhpItems, ItemId = varVhpActiveItemId).ShortText", max_length=40,
                          required_formula=REQ_ITEM, display_mode=DM_ITEM)
    drpRevision = dropdown("drpVhpItemRevision", "colVhpRevisionOptions",
                           "LookUp(colVhpRevisionOptions, Value = LookUp(colVhpItems, ItemId = varVhpActiveItemId).Revision)",
                           display_mode=DM_ITEM)
    txtOrstedResp = text_input("txtVhpItemOrstedResponsible",
                               # Standard udfyldt med den bruger, der har appen aaben, men brugeren kan
                               # frit rette det. Coalesce falder kun tilbage til User().FullName, naar
                               # itemets gemte vaerdi er tom (fx et nyt item).
                               f"Coalesce(LookUp(colVhpItems, ItemId = varVhpActiveItemId).OrstedResponsible, User().FullName)",
                               display_mode=DM_ITEM)
    txtInitials = text_input("txtVhpItemInitials",
                             "LookUp(colVhpItems, ItemId = varVhpActiveItemId).Initials", max_length=12,
                             display_mode=DM_ITEM)

    # --- Objektliste: multi-select med afkrydsning -------------------------
    #
    # HVORFOR IKKE EN COMBOBOX MED SelectMultiple
    # Det var den oprindelige loesning, og det var ogsaa en combobox, der
    # svigtede paa FL-feltet: flowet gav 819 raekker, beskeden sagde det, og
    # dropdownen var tom. Aarsagen blev aldrig isoleret. At saette den samme
    # kontroltype tilbage her ville vaere at gaette paa, at fejlen ikke
    # rammer igen.
    #
    # Et galleri med ModernCheckbox er derimod EN KONSTRUKTION, DER ALLEREDE
    # VIRKER i denne app - tasklist-pickeren og pakkematricen bruger den. Der
    # er ingen skjult filtrering: galleriet viser praecis de raekker, Items
    # giver det, og hvert kryds skriver direkte i colVhpItemObjects.
    #
    # Til gengaeld kan man saette flere krydser i traek uden en knap imellem,
    # hvilket var hele pointen.
    objLabelRow = label_row("conVhpItemObjLabel", "Object List")
    objHint = text_ctrl("txtVhpItemObjHint", bh.hint("ObjectList"), size=12,
                        color=C_MUTED, height=32, wrap="true", visible=HINTS_ON)

    chkObj = Ctrl("chkVhpObjPick", "ModernCheckbox", props={
        "AccessibleLabel": "\"Select object\"",
        "Default": f"CountRows(Filter({OBJ_CHOSEN}, Code = ThisItem.Code)) > 0",
        "DisplayMode": DM_ITEM,
        "Height": "24",
        "OnCheck": ("Collect(\n"
                    "    colVhpItemObjects,\n"
                    "    { ItemId: varVhpActiveItemId, Code: ThisItem.Code,\n"
                    "      Description: ThisItem.Description }\n"
                    ")"),
        "OnUncheck": ("RemoveIf(\n"
                      "    colVhpItemObjects,\n"
                      "    ItemId = varVhpActiveItemId && Code = ThisItem.Code\n"
                      ")"),
        "Width": "26",
    }, h=24)
    # Parent her er raekkebeholderen, ikke galleriet - kun et galleris
    # DIREKTE barn kender Parent.TemplateWidth. Beholderen er selv saa bred
    # som skabelonen, saa Parent.Width giver det samme tal.
    txtObjRow = text_ctrl("txtVhpObjRowText", "ThisItem.Display", size=13, height=24,
                          width="Parent.Width - 26 - 10 - 4", wrap="false")
    objRowTpl = group("conVhpObjRow", [chkObj, txtObjRow], direction="Horizontal",
                      gap=10, height="Parent.TemplateHeight - 2",
                      align_items="Center", width="Parent.TemplateWidth")

    OBJ_ROWS = 6
    OBJ_ROW_H = 30
    galObj = Ctrl(
        "galVhpItemObjects", "Gallery", variant="Vertical",
        props={
            "AccessibleLabel": "\"Underliggende objekter\"",
            "BorderColor": C_CARD_BORDER,
            "BorderStyle": "BorderStyle.Solid",
            "BorderThickness": "1",
            "Fill": C_INPUT_BG,
            "FillPortions": "0",
            "Height": str(OBJ_ROWS * (OBJ_ROW_H + 2)),
            "Items": f"Sort({OBJ_CANDIDATES}, Code)",
            "LayoutMinWidth": "0",
            "LoadingSpinner": "LoadingSpinner.None",
            # Gallery understoetter ikke Radius* - kun rammen kan saettes.
            # Feltet faar derfor skarpe hjoerner, hvor dropdownen ved siden
            # af har bloede. Se check 10 i check_layout.py.
            "Selectable": "false",
            "ShowScrollbar": "true",
            "TabIndex": "0",
            "TemplatePadding": "2",
            "TemplateSize": str(OBJ_ROW_H),
            "Width": "Parent.Width",
            "WrapCount": "1",
        },
        children=[objRowTpl], h=OBJ_ROWS * (OBJ_ROW_H + 2))

    # Uden valgt FL er listen tom. Saa skal der staa hvorfor, i stedet for et
    # tomt felt der ligner en fejl.
    objEmpty = text_ctrl(
        "txtVhpObjEmpty",
        (
            "If(\n"
            f"    IsBlank({SEL_FL}),\n"
            "    \"Choose a functional location above first.\",\n"
            "    \"There are no sub-objects in the search result. \" &\n"
            "        \"Search more broadly in the functional location field.\"\n"
            ")"
        ), size=12, color=C_MUTED, height=32, wrap="true",
        visible=f"IfError(CountRows({OBJ_CANDIDATES}) = 0, true)")

    objChosen = text_ctrl(
        "txtVhpItemObjChosen",
        (
            "With(\n"
            f"    {{ n: CountRows({OBJ_CHOSEN}) }},\n"
            "    If(\n"
            "        n = 0, \"Ingen underliggende objekter valgt.\",\n"
            "        Text(n) & \" valgt: \" &\n"
            f"            Concat(Sort({OBJ_CHOSEN}, Code), Code, \", \") &\n"
            "            With(\n"
            f"                {{ fremmede: CountRows(Filter({OBJ_CHOSEN}, !StartsWith(Code, {SEL_FL}))) }},\n"
            "                If(\n"
            "                    fremmede > 0,\n"
            "                    \"   |   ADVARSEL: \" & Text(fremmede) &\n"
            "                        \" of them are not under the selected functional location.\",\n"
            "                    \"\"\n"
            "                )\n"
            "            )\n"
            "    )\n"
            ")"
        ), size=12, height=32, wrap="true",
        color=(f"If(\n"
               f"    CountRows(Filter({OBJ_CHOSEN}, !StartsWith(Code, {SEL_FL}))) > 0, {C_INVALID_FG},\n"
               f"    CountRows({OBJ_CHOSEN}) = 0, {C_MUTED},\n"
               f"    {C_TITLE}\n"
               f")"))

    objMeta = text_ctrl(
        "txtVhpItemObjMeta",
        (
            "If(\n"
            f"    IsBlank({SEL_FL}), \"\",\n"
            f"    Text(CountRows({OBJ_CANDIDATES})) & \" mulige under \" & {SEL_FL} & \".\"\n"
            ")"
        ), size=12, color=C_MUTED, height=18, wrap="true")

    objBlock = group("conVhpItemObjBlock",
                     [objLabelRow, objHint, galObj, objEmpty, objChosen, objMeta],
                     direction="Vertical", gap=6, width="Parent.Width",
                     fill_portions=0, align_in_container="Start")

    # Functional Location og Object List staar OVEN PAA HINANDEN i hoejre
    # kolonne. De to hoerer sammen - objektlisten kan foerst bruges, naar en
    # FL er valgt, og filtreres paa den - saa de skal ogsaa staa sammen.
    #
    # De oevrige felter staar i to kolonner til venstre. Layoutet er derfor
    # een vandret raekke med to celler, ikke tre raekker med tre celler:
    #
    #     +---------------------+---------------------+----------------+
    #     | Item Short Text     | Main Work Center    | Functional     |
    #     | Activity Type       | Revision            | Location       |
    #     | Orsted Responsible  | Initials            |                |
    #     |                     |                     | Object List    |
    #     +---------------------+---------------------+----------------+
    #            venstre: 2 kolonner                    hoejre: 1
    CW = EDITOR_CW
    GAP = 20
    # SLACK: uden den summer de to kolonner plus mellemrummet til PRAECIS
    # CW. Raekken har LayoutWrap = true (den skal stable under braekpunktet),
    # og ved et eksakt sammenfald er det en afrunding eller en kantlinje,
    # der afgoer, om hoejre kolonne bliver staaende eller falder ned under.
    # Den faldt ned. To pixels er nok til at gaa fri.
    SLACK = 2
    AVAIL = f"({CW} - {SLACK})"
    RIGHT_W = f"(({AVAIL} - {2 * GAP}) / 3)"
    LEFT_W = f"({AVAIL} - {GAP} - {RIGHT_W})"
    # Under braekpunktet stables alt, og saa fylder begge sider det hele.
    RIGHT = f"If({CW} < {TWO_COL_MIN}, {CW}, {RIGHT_W})"
    LEFT = f"If({CW} < {TWO_COL_MIN}, {CW}, {LEFT_W})"

    leftRows = [
        row_n("conVhpItemRow1", [
            field_cell("conVhpCellItemShortText", "Item Short Text", txtShort, required=True,
                       container_w=LEFT_W, cols=2, hint_text=bh.hint("ItemShortText")),
            field_cell("conVhpCellItemMwc", "Main Work Center", drpMwc, required=True,
                       container_w=LEFT_W, cols=2, hint_text=bh.hint("MainWorkCenter")),
        ], container_w=LEFT_W),
        row_n("conVhpItemRow2", [
            field_cell("conVhpCellItemAct", "Maintenance Activity Type", drpAct, required=True,
                       container_w=LEFT_W, cols=2, hint_text=bh.hint("ActivityType")),
            field_cell("conVhpCellItemRevision", "Revision", drpRevision,
                       container_w=LEFT_W, cols=2, hint_text=bh.hint("Revision")),
        ], container_w=LEFT_W),
        row_n("conVhpItemRow3", [
            field_cell("conVhpCellItemOrstedResp", "Orsted Responsible", txtOrstedResp,
                       container_w=LEFT_W, cols=2, hint_text=bh.hint("OrstedResponsible")),
            field_cell("conVhpCellItemInitials", "Initials", txtInitials,
                       container_w=LEFT_W, cols=2, hint_text=bh.hint("Initials")),
        ], container_w=LEFT_W),
    ]
    # Lang tekst laa foer UNDER hele gitteret i fuld bredde. Den hoerer til
    # itemets egne oplysninger, saa den staar nu nederst i venstre kolonne -
    # over begge kolonner dernede, og dermed til venstre for objektlisten,
    # der bliver staaende i hoejre kolonne.
    #
    # cols=1: cellen deler ikke raekken med nogen, den fylder kolonnen.
    txtLongText = text_input("txtVhpItemLongText",
                             "LookUp(colVhpItems, ItemId = varVhpActiveItemId).LongText", height=80,
                             display_mode=DM_ITEM, ttype="Multiline")
    longTextCell = field_cell("conVhpCellItemLongText", "Item Long Text", txtLongText,
                              container_w=LEFT_W, cols=1, fill_portions_formula="0",
                              hint_text=bh.hint("ItemLongText"))

    leftCol = group("conVhpItemLeftCol", leftRows + [longTextCell], direction="Vertical",
                    gap=16, width=LEFT)
    # justify=Start: naar raekken er hoejere end hoejrekolonnens indhold
    # (venstre side har tre raekker), skal de to blokke blive staaende
    # OEVERST i stedet for at blive fordelt ud over hele hoejden.
    rightCol = group("conVhpItemRightCol", [flBlock, objBlock], direction="Vertical",
                     gap=16, width=RIGHT, justify="Start")

    mainRow = row_n("conVhpItemMainRow", [leftCol, rightCol], container_w=CW)

    fieldsGrid = group("conVhpItemFieldsGrid", [mainRow], direction="Vertical", gap=16)

    itemMeta = text_ctrl(
        "txtVhpItemMeta",
        "If(IsBlank(varVhpActiveItemId), \"No item selected.\", \"Item \" & Text(varVhpActiveItemId) & \" - status: \" & Upper(LookUp(colVhpItems, ItemId = varVhpActiveItemId).Status))",
        size=12, color=C_MUTED, height=18, wrap="true")
    btnSaveItem = button(
        "btnVhpSaveItem", "\"Save\"",
        (
            "If(\n"
            "    IsBlank(varVhpActiveItemId),\n"
            "    Set(varVhpRuntimeInfo, \"Select or add an item first.\"),\n"
            "\n"
            "    Set(varVhpItemValidated, true);\n"
            "    If(\n"
            "        IsBlank(Trim(txtVhpItemShortText.Text)) || Len(Trim(txtVhpItemShortText.Text)) > 40 ||\n"
            "        IsBlank(drpVhpItemMainWorkCenter.Selected.Value) ||\n"
            "        IsBlank(drpVhpItemActivityType.Selected.Value) ||\n"
            "        IsBlank(drpVhpItemFL.Selected.Code),\n"
            "        UpdateIf(colVhpItems, ItemId = varVhpActiveItemId, { Status: \"invalid\" });\n"
            "        Set(varVhpRuntimeInfo, \"Item contains issues. Fix required fields (marked with *).\"),\n"
            "\n"
            # colVhpItemObjects er allerede sandheden - Tilfoej/Fjern skriver
            # direkte i den. Der er ikke laengere en kontrol med en
            # konkurrerende liste, der skal kopieres herind ved Save.

            "        With(\n"
            "            { code: drpVhpItemFL.Selected.Code },\n"
            "            UpdateIf(\n"
            "                colVhpItems,\n"
            "                ItemId = varVhpActiveItemId,\n"
            "                {\n"
            "                    ShortText: Trim(txtVhpItemShortText.Text),\n"
            "                    FunctionalLocation: code,\n"
            "                    FlDescription: drpVhpItemFL.Selected.Description,\n"
            "                    MainWorkCenter: drpVhpItemMainWorkCenter.Selected.Value,\n"
            "                    ActivityType: drpVhpItemActivityType.Selected.Value,\n"
            "                    ObjectList: Concat(Sort(Filter(colVhpItemObjects, ItemId = varVhpActiveItemId), Code), Code, \"; \"),\n"
            "                    Revision: drpVhpItemRevision.Selected.Value,\n"
            "                    OrstedResponsible: Trim(txtVhpItemOrstedResponsible.Text),\n"
            "                    Initials: Trim(txtVhpItemInitials.Text),\n"
            "                    LongText: Trim(txtVhpItemLongText.Text),\n"
            "                    Status: \"valid\"\n"
            "                }\n"
            "            )\n"
            "        );\n"
            "        Set(varVhpRuntimeInfo, \"Item saved: \" & Trim(txtVhpItemShortText.Text) & \".\")\n"
            "    )\n"
            ")"
        ), primary=True, width=110,
        display_mode="If(IsBlank(varVhpActiveItemId), DisplayMode.Disabled, DisplayMode.Edit)")
    footer = group("conVhpEditorFooter", [itemMeta, btnSaveItem], direction="Horizontal", gap=16, height=36,
                   align_items="Center")

    return card("conVhpEditorCard",
                [header, helpPanel, fieldsGrid, footer])


def build_items_section():
    rail = build_items_rail()
    editor = build_item_editor()
    # Hoejden er de to korts BEREGNEDE hoejder - ikke .Height paa kontrollerne.
    # Det var netop den reference, der gav cirkelreferencen og kaskade-vaeksten.
    h = (f"If(App.Width < 1000, ({rail.h}) + {SPLIT_GAP} + ({editor.h}), "
         f"Max(({rail.h}), ({editor.h})))")
    rail.props["Width"] = f"If(App.Width < 1000, Parent.Width, {RAIL_W})"
    editor.props["Width"] = EDITOR_W
    return group("conVhpItemsSplit", [rail, editor], direction="Horizontal", gap=SPLIT_GAP,
                 height=h, wrap="true")
