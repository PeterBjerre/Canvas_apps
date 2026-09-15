# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import (Ctrl, C_CARD_BG, C_CARD_BORDER, C_TITLE, C_MUTED, C_REQUIRED, C_PRIMARY, C_WHITE,
                        C_INFO_FG, C_INFO_BG, C_VALID_FG, C_VALID_BG, C_INVALID_FG, C_INVALID_BG,
                        C_NEUTRAL_FG, C_NEUTRAL_BG, FONT, SHELL_W, EDITOR_W, RAIL_W, SPLIT_GAP)
from build_helpers import (text_ctrl, group, button, button_row, text_input, number_input, dropdown,
                           label_row, field_cell, row_n, col_width, badge, card, combobox, poll_timer,
                           TWO_COL_MIN)
from build_plan_header import section_header
from build_flsearch import timer_poll_action, MIN_SEARCH_LEN

DM_ITEM = "If(IsBlank(varVhpActiveItemId), DisplayMode.Disabled, DisplayMode.Edit)"
REQ_ITEM = "varVhpItemValidated"

# Items-skinnens og editorens indholdsbredde (kortbredde minus 18+18 polstring).
RAIL_CW = RAIL_W - 36
EDITOR_CW = f"({EDITOR_W} - 36)"

# Tre kolonner i stedet for to for indtastningsfelterne i Item Editor.
EDITOR_COLS = 3

# Gallerihoejde: TemplateSize + TemplatePadding pr. raekke. Den oprindelige
# formel regnede kun med TemplateSize og klippede derfor den sidste raekke.
ITEM_ROW_H = 88 + 6
ITEMS_GAL_H = f"Max(CountRows(colVhpItems), 1) * {ITEM_ROW_H}"

# Den FL der er valgt lige nu: comboboksens valg, med fald tilbage til det
# gemte paa itemet, saa objektlisten ogsaa filtrerer korrekt foer brugeren
# har roert comboboksen.
SEL_FL = ("Coalesce(cmbVhpItemFL.Selected.Code, "
          "LookUp(colVhpItems, ItemId = varVhpActiveItemId).FunctionalLocation)")

# Kandidater til objektlisten: alt under den valgte FL, minus den selv.
#
# De kommer fra colVhpFlSearch - altsaa SAMME resultat som FL-soegningen
# hentede. Objektlisten kalder aldrig selv flowet: soeger man fx "SSV13 HFC10",
# returnerer flowet baade SSV13 HFC10 og alt under den, saa de underliggende
# FL ligger allerede i samlingen. Det giver eet flow-kald pr. soegning i
# stedet for to, og listen kan ikke komme ud af trit med FL-feltet.
OBJ_CANDIDATES = (f"Filter(colVhpFlSearch, StartsWith(Code, {SEL_FL}) && Code <> {SEL_FL})")

# DefaultSelectedItems skal komme fra SAMME tabel som Items, ellers matcher
# Power Apps ikke raekkerne, og de gemte valg ville ikke staa markeret.
OBJ_DEFAULT_ITEMS = (
    f"Filter(\n"
    f"    {OBJ_CANDIDATES} As C,\n"
    f"    CountRows(Filter(colVhpItemObjects, ItemId = varVhpActiveItemId && Code = C.Code)) > 0\n"
    f")"
)
FL_DEFAULT_ITEMS = (
    "Filter(\n"
    "    colVhpFlSearch As F,\n"
    "    F.Code = LookUp(colVhpItems, ItemId = varVhpActiveItemId).FunctionalLocation\n"
    ")"
)

RESET_EDITOR_CONTROLS = (
    "Reset(cmbVhpItemFL); Reset(cmbVhpItemObjects); Reset(txtVhpItemShortText); "
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
                            "Hvert item har eget FL, tasklist-binding og operationer.", "Step 2")

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
                            "Fulde itemfelter med reference-opslag af Functional Location.", "")

    # --- Functional Location: soeg OG vaelg i EET felt ----------------------
    # Classic/ComboBox har indbygget soegefelt, saa brugeren skriver og
    # vaelger i den samme kontrol. Ingen soegeknap, ingen separat dropdown.
    flLabelRow = label_row("conVhpItemFlLabel", "Functional Location", required=True)

    cmbFl = combobox(
        "cmbVhpItemFL", "colVhpFlSearch",
        display_field="Display",
        default_items=FL_DEFAULT_ITEMS,
        placeholder=("\"Skriv mindst %d tegn, fx SSV13 HFC - og vaelg i listen\"" % MIN_SEARCH_LEN),
        required_formula=REQ_ITEM, display_mode=DM_ITEM)

    # Timeren driver KUN FL-soegningen. Objektlisten kalder ikke flowet - den
    # filtrerer bare i det resultat, denne soegning allerede har hentet.
    fl_poll = timer_poll_action("cmbVhpItemFL.SearchText", "colVhpFlSearch",
                                "varVhpFlLastSearch", "varVhpFlMeta")
    tmrFl = poll_timer("tmrVhpFlSearch", fl_poll)

    flDescription = text_ctrl(
        "txtVhpItemFlDescription",
        (
            "If(\n"
            "    IsBlank(cmbVhpItemFL.Selected.Code), \"Ingen Functional Location valgt endnu.\",\n"
            "    \"Valgt: \" & cmbVhpItemFL.Selected.Code & \" - \" &\n"
            "    cmbVhpItemFL.Selected.Description &\n"
            "    If(\n"
            "        cmbVhpItemFL.Selected.Maintainable, \"\",\n"
            "        \"   |   ADVARSEL: markeret som ikke vedligeholdbar i SAP.\"\n"
            "    )\n"
            ")"
        ),
        size=12, height=18, wrap="true",
        color=("If(!IsBlank(cmbVhpItemFL.Selected.Code) && "
               f"!cmbVhpItemFL.Selected.Maintainable, {C_INVALID_FG}, {C_MUTED})"))
    flMeta = text_ctrl("txtVhpItemFlMeta", "varVhpFlMeta", size=12, color=C_MUTED, height=18, wrap="true")
    # FL-blokken staar nu som en normal gitter-celle (samme bredde som de
    # andre indtastningsfelter) i stedet for i fuld bredde.
    flBlock = group("conVhpItemFlBlock", [flLabelRow, cmbFl, flDescription, flMeta, tmrFl],
                    direction="Vertical", gap=6, width="Parent.Width",
                    # FillPortions = 0. Blokken laa foer i en VANDRET
                    # gitterraekke, hvor den fordelte bredde. I den lodrette
                    # hoejrekolonne fordeler den HOEJDE, og med 1 voksede
                    # blokken til hele kolonnens hoejde - langt ud over sine
                    # 114 px indhold.
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

    # --- Objektliste: soeg OG vaelg flere i EET felt ------------------------
    # Samme princip som FL-feltet, bare multi-select: Classic/ComboBox med
    # SelectMultiple. Der er hverken hente-knap, ryd-knap eller et galleri
    # ved siden af - comboboksen har selv soegefelt, tags og et kryds til at
    # rydde med.
    #
    # Items filtreres i colVhpFlSearch, altsaa resultatet af FL-soegningen.
    # Objektlisten kalder aldrig flowet selv.
    objLabelRow = label_row("conVhpItemObjLabel", "Object List")

    cmbObj = combobox(
        "cmbVhpItemObjects", f"Sort({OBJ_CANDIDATES}, Code)",
        display_field="Display", multi=True,
        default_items=OBJ_DEFAULT_ITEMS,
        placeholder="\"Vaelg et eller flere underliggende objekter\"",
        display_mode=DM_ITEM)

    objMeta = text_ctrl(
        "txtVhpItemObjMeta",
        (
            "If(\n"
            f"    IsBlank({SEL_FL}), \"Vaelg foerst en Functional Location ovenfor.\",\n"
            f"    \"Filtreret til FL der starter med \" & {SEL_FL} & \". \" &\n"
            "    Text(CountRows(cmbVhpItemObjects.SelectedItems)) & \" valgt af \" &\n"
            f"    Text(CountRows({OBJ_CANDIDATES})) & \" mulige.\"\n"
            ")"
        ), size=12, color=C_MUTED, height=18, wrap="true")

    objEmpty = text_ctrl(
        "txtVhpObjEmpty",
        (
            "If(\n"
            f"    IsBlank({SEL_FL}), \"Vaelg en Functional Location for at se underliggende objekter.\",\n"
            "    \"Der er ingen underliggende Functional Locations i soegeresultatet. \" &\n"
            "    \"Soeg bredere i Functional Location-feltet, fx paa faerre tegn.\"\n"
            ")"
        ), size=12, color=C_MUTED, height=20, wrap="true",
        visible=f"IfError(CountRows({OBJ_CANDIDATES}) = 0, true)")

    # Objektliste-blokken staar nu som en normal gitter-celle (samme bredde
    # som de andre indtastningsfelter) i stedet for i fuld bredde.
    objBlock = group("conVhpItemObjBlock", [objLabelRow, cmbObj, objMeta, objEmpty],
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
    RIGHT_W = f"(({CW} - {2 * GAP}) / 3)"
    LEFT_W = f"({CW} - {GAP} - {RIGHT_W})"
    # Under braekpunktet stables alt, og saa fylder begge sider det hele.
    RIGHT = f"If({CW} < {TWO_COL_MIN}, {CW}, {RIGHT_W})"
    LEFT = f"If({CW} < {TWO_COL_MIN}, {CW}, {LEFT_W})"

    leftRows = [
        row_n("conVhpItemRow1", [
            field_cell("conVhpCellItemShortText", "Item Short Text", txtShort, required=True,
                       container_w=LEFT_W, cols=2),
            field_cell("conVhpCellItemMwc", "Main Work Center", drpMwc, required=True,
                       container_w=LEFT_W, cols=2),
        ], container_w=LEFT_W),
        row_n("conVhpItemRow2", [
            field_cell("conVhpCellItemAct", "Maintenance Activity Type", drpAct, required=True,
                       container_w=LEFT_W, cols=2),
            field_cell("conVhpCellItemRevision", "Revision", drpRevision,
                       container_w=LEFT_W, cols=2),
        ], container_w=LEFT_W),
        row_n("conVhpItemRow3", [
            field_cell("conVhpCellItemOrstedResp", "Orsted Responsible", txtOrstedResp,
                       container_w=LEFT_W, cols=2),
            field_cell("conVhpCellItemInitials", "Initials", txtInitials,
                       container_w=LEFT_W, cols=2),
        ], container_w=LEFT_W),
    ]
    leftCol = group("conVhpItemLeftCol", leftRows, direction="Vertical", gap=16, width=LEFT)
    # justify=Start: naar raekken er hoejere end hoejrekolonnens indhold
    # (venstre side har tre raekker), skal de to blokke blive staaende
    # OEVERST i stedet for at blive fordelt ud over hele hoejden.
    rightCol = group("conVhpItemRightCol", [flBlock, objBlock], direction="Vertical",
                     gap=16, width=RIGHT, justify="Start")

    mainRow = row_n("conVhpItemMainRow", [leftCol, rightCol], container_w=CW)

    fieldsGrid = group("conVhpItemFieldsGrid", [mainRow], direction="Vertical", gap=16)

    txtLongText = text_input("txtVhpItemLongText",
                             "LookUp(colVhpItems, ItemId = varVhpActiveItemId).LongText", height=80,
                             display_mode=DM_ITEM, ttype="Multiline")
    longTextCell = field_cell("conVhpCellItemLongText", "Item Long Text", txtLongText,
                              width="Parent.Width", container_w=CW, fill_portions_formula="0")

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
            "        IsBlank(cmbVhpItemFL.Selected.Code),\n"
            "        UpdateIf(colVhpItems, ItemId = varVhpActiveItemId, { Status: \"invalid\" });\n"
            "        Set(varVhpRuntimeInfo, \"Item contains issues. Fix required fields (marked with *).\"),\n"
            "\n"
            # Comboboksens valg er sandheden, mens der redigeres. colVhpItemObjects
            # er den PERSISTENTE kopi: den overlever, at Items-filteret aendrer sig,
            # og det er den, Copy item og Remove item arbejder paa.
            "        RemoveIf(colVhpItemObjects, ItemId = varVhpActiveItemId);\n"
            "        ForAll(\n"
            "            cmbVhpItemObjects.SelectedItems As S,\n"
            "            Collect(\n"
            "                colVhpItemObjects,\n"
            "                { ItemId: varVhpActiveItemId, Code: S.Code, Description: S.Description }\n"
            "            )\n"
            "        );\n"
            "        With(\n"
            "            { code: cmbVhpItemFL.Selected.Code },\n"
            "            UpdateIf(\n"
            "                colVhpItems,\n"
            "                ItemId = varVhpActiveItemId,\n"
            "                {\n"
            "                    ShortText: Trim(txtVhpItemShortText.Text),\n"
            "                    FunctionalLocation: code,\n"
            "                    FlDescription: cmbVhpItemFL.Selected.Description,\n"
            "                    MainWorkCenter: drpVhpItemMainWorkCenter.Selected.Value,\n"
            "                    ActivityType: drpVhpItemActivityType.Selected.Value,\n"
            "                    ObjectList: Concat(Sort(cmbVhpItemObjects.SelectedItems, Code), Code, \"; \"),\n"
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
                [header, fieldsGrid, longTextCell, footer])


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
