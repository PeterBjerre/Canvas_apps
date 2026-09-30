# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import (Ctrl, C_CARD_BG, C_CARD_BORDER, C_MUTED, C_INFO_FG,
                        C_INFO_BG, C_VALID_FG, C_VALID_BG, C_INVALID_FG,
                        C_INVALID_BG, C_NEUTRAL_BG, C_INPUT_BG, SHELL_W,
                        EDITOR_W, RAIL_W, SPLIT_GAP, C_TRANSPARENT, C_MODAL_BG,
                        C_PRIMARY_SOFT)
from layout_tokens import if_below, at_least
from build_helpers import (checkbox_theme, row_hit, text_ctrl, group, button,
                           button_row, text_input, themed_dropdown, label_row,
                           field_cell, col_width, card, HINTS_ON, grow,
                           fit_button_width, column_grid, ICON_SAVE, ICON_W,
                           mark_done, bool_toggle)
from build_plan_header import section_header, help_panel
import build_help as bh
from fl_picker import fl_picker
import sp_config as cfg

DM_ITEM = "If(IsBlank(varVhpActiveItemId), DisplayMode.Disabled, DisplayMode.Edit)"
REQ_ITEM = "varVhpItemValidated"

# Items-skinnens og editorens indholdsbredde (kortbredde minus 18+18 polstring).
RAIL_CW = RAIL_W - 36
EDITOR_CW = f"({EDITOR_W} - 36)"

# To kolonner til felterne - Functional Location har sin egen raekke i
# editorens fulde bredde under dem (issue #72).
EDITOR_COLS = 2

# Gallerihoejde: een raekke pr. item. Mellemrummet paa 6 px ligger UNDER
# kortet i raekken (kortet er 88 hoejt), ikke i TemplatePadding - saa ville
# det ogsaa ligge til hoejre og venstre, og kortet flugtede ikke med
# knapperne over det.
ITEM_GAP = 6
ITEM_ROW_H = 88 + ITEM_GAP
ITEMS_GAL_H = f"Max(CountRows(colVhpItems), 1) * {ITEM_ROW_H}"

# Comboboksen (tools/fl_picker.py, issue #63) - soegefelt OG valgliste.
FL_COMBO = "cmbVhpItemFL"

# Den valgte FL-kode. Listen indeholder kun rigtige Functional Locations
# (issue #72), saa comboboksens valg ER koden.
FL_CODE = f"{FL_COMBO}.Selected.Code"

# Den FL der er valgt lige nu: comboboksens valg, med fald tilbage til det
# gemte paa itemet, saa objektlisten ogsaa filtrerer korrekt foer brugeren
# har roert comboboksen.
SEL_FL = (f"Coalesce({FL_CODE}, "
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

# Object List-knappens tooltip (issue #63): de valgte objekter, een pr.
# linje. Teksten under knappen er vaek - hover viser det samme, og
# knappens tal siger, hvor mange der er valgt.
OBJ_TOOLTIP = (
    "With(\n"
    f"    {{ n: CountRows({OBJ_CHOSEN}),\n"
    f"      fremmede: CountRows(Filter({OBJ_CHOSEN}, !StartsWith(Code, {SEL_FL}))) }},\n"
    "    If(\n"
    "        n = 0, \"No sub-objects selected.\",\n"
    "        \"Selected:\" & Char(10) &\n"
    f"            Concat(Sort({OBJ_CHOSEN}, Code), Code & \" - \" & Description, Char(10)) &\n"
    "            If(\n"
    "                fremmede > 0,\n"
    "                Char(10) & \"WARNING: \" & Text(fremmede) &\n"
    "                    \" of them are not under the selected functional location.\",\n"
    "                \"\"\n"
    "            )\n"
    "    )\n"
    ")"
)
# Er der noget at vise? Foerst en gyldig Functional Location (issue #72) -
# saa kandidater under den, eller et valg, der skal kunne fjernes igen.
OBJ_HAS_DATA = (f"!IsBlank({SEL_FL}) && "
                f"(CountRows({OBJ_CANDIDATES}) > 0 || CountRows({OBJ_CHOSEN}) > 0)")

# FL-vaelgerens tilstand - samme konstruktion som Equipments og Materials
# (tools/fl_picker.py). search_action saetter FL_BUSY_VAR false igen ad
# BEGGE veje ud - svar og fejl.
FL_BUSY_VAR = "varVhpFlBusy"
FL_QUERY_VAR = "varVhpFlQuery"
FL_LAST_VAR = "varVhpFlLast"
# Det valgte resultat. Soegningen saetter den til det FOERSTE svar (issue
# #72); comboboksens DefaultSelectedItems laeser den foer itemets gemte FL.
FL_PICK_VAR = "varVhpFlPick"

RESET_EDITOR_CONTROLS = (
    f"Set({FL_QUERY_VAR}, \"\"); Set({FL_LAST_VAR}, \"\"); Set({FL_PICK_VAR}, \"\"); "
    f"Reset({FL_COMBO}); "
    "Reset(inpVhpItemShortText); "
    "Reset(drpVhpItemMainWorkCenter); Reset(drpVhpItemActivityType); Reset(tglVhpItemRevision); "
    "Reset(inpVhpItemInitials); "
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
    ")"
)


def _copy_record(collection, alias, indent):
    """Record til Copy item: HVERT felt i samlingens skema kopieres fra
    alias, undtagen ItemId (den nye) og Selected (en markering er ikke en
    del af raekken).

    Her stod operationens felter skrevet af i haanden, og syv af dem
    manglede (Persons, ControlKey, Cost, UnitCost, Currency, CostElement,
    MaterialGroup) - de blev blanke paa kopien. Med skemaet som kilde kan
    et nyt felt ikke glemmes igen."""
    schema = dict(cfg.WORKING_COLLECTIONS)[collection]
    pad = " " * indent
    fields = []
    for k in schema:
        if k == "ItemId":
            fields.append("ItemId: varVhpNextItemId")
        elif k == "Selected":
            fields.append("Selected: false")
        else:
            fields.append(f"{k}: {alias}.{k}")
    return "{\n" + pad + "    " + (",\n" + pad + "    ").join(fields) + "\n" + pad + "}"


def build_items_rail():
    # Vaerket fra Plan Header staar ved titlen: det er den kontekst, alle
    # items arbejder i - arbejdscentre, tasklister og FL-soegningen er
    # filtreret paa det (issue #54).
    plant = text_ctrl("txtVhpItemsPlant", "\"Plant: \" & varVhpPlan.Plant", size=12,
                      color=C_MUTED, weight="Semibold", height=18, width=90, wrap="false",
                      visible="!IsBlank(varVhpPlan.Plant)")
    header = section_header("conVhpItemsHead", "Items", "Step 2", extra_left=[plant])

    btnAdd = button(
        "btnVhpAddItem", "\"Add item\"",
        (
            "If(\n"
            "    !varVhpPlanCommitted,\n"
            "    Notify(\"Save the plan before adding items.\", NotificationType.Warning),\n"
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
            "    Notify(\"Item \" & Text(varVhpNextItemId) & \" added.\", NotificationType.Success)\n"
            ")"
        ))

    btnCopy = button(
        "btnVhpCopyItem", "\"Copy item\"",
        (
            "If(\n"
            "    IsBlank(varVhpActiveItemId) || CountRows(Filter(colVhpItems, ItemId = varVhpActiveItemId)) = 0,\n"
            "    Notify(\"Select an item to copy first.\", NotificationType.Warning),\n"
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
            # Collect UDEN OM ForAll. ForAll returnerer en tabel, og Collect
            # tager den i eet kald; foer stod Collect INDE i loekken, altsaa
            # een mutation pr. operation (App checker: ForAllWithMutation).
            #
            # Og den var ikke kun langsom: kilden OG maalet er den SAMME
            # samling. Med Collect inde i loekken skriver den i det, den
            # laeser fra. Naar ForAll faerdiggoeres foerst, er tabellen
            # laest af den gamle samling, foer der skrives en eneste raekke.
            "        Collect(\n"
            "            colVhpOperations,\n"
            "            ForAll(\n"
            "                Filter(colVhpOperations, ItemId = varVhpActiveItemId) As SRC,\n"
            f"                {_copy_record('colVhpOperations', 'SRC', 16)}\n"
            "            )\n"
            "        );\n"
            # Materialerne foelger operationerne. LineId er unik pr. item,
            # saa kopien kan beholde den.
            "        Collect(\n"
            "            colVhpMaterials,\n"
            "            ForAll(\n"
            "                Filter(colVhpMaterials, ItemId = varVhpActiveItemId) As MSRC,\n"
            f"                {_copy_record('colVhpMaterials', 'MSRC', 16)}\n"
            "            )\n"
            "        );\n"
            "        Collect(\n"
            "            colVhpItemObjects,\n"
            "            ForAll(\n"
            "                Filter(colVhpItemObjects, ItemId = varVhpActiveItemId) As OBJ,\n"
            "                { ItemId: varVhpNextItemId, Code: OBJ.Code, Description: OBJ.Description }\n"
            "            )\n"
            "        );\n"
            "        Set(varVhpActiveItemId, varVhpNextItemId);\n"
            f"        {SEED_FL_PICKER};\n"
            f"        {RESET_EDITOR_CONTROLS};\n"
            "        Notify(\"Item copied. Functional Location cleared on the copied item.\", NotificationType.Success)\n"
            "    )\n"
            ")"
        ))

    # Knapperne deler bredden ligeligt, saa raekken aldrig ombryder. Delete
    # staar nu paa hvert kort (se nedenfor), ikke her.
    btnRow = button_row("conVhpItemButtonRow", [btnAdd, btnCopy], RAIL_CW)

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
    cardTextCol = grow(group("conVhpItemCardText", [cardTitle, cardFl, cardTasklist],
                             direction="Vertical", gap=2))
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
    # DELETE PAA KORTET (issue #54). Hed "Remove item" og stod i knaprakken
    # over listen, hvor den slettede det AKTIVE item - ikke noedvendigvis
    # det, man kiggede paa. Nu sletter den sit eget kort. Id'et laeses FOER
    # noget fjernes: raekken, ThisItem peger paa, forsvinder undervejs.
    #
    # Samme sletning som foer: operationer og objekter foelger med.
    DEL_W = fit_button_width("\"Delete\"", size=13, min_w=64)
    btnDelete = button(
        "btnVhpRemoveItem", "\"Delete\"",
        (
            "With(\n"
            "    { id: ThisItem.ItemId },\n"
            "    RemoveIf(colVhpOperations, ItemId = id);\n"
            "    RemoveIf(colVhpItemObjects, ItemId = id);\n"
            # Materialer og dokumentraekker foelger med. Stod de tilbage,
            # blev de gemt med tom ItemKey og laa usynlige i planen.
            "    RemoveIf(colVhpMaterials, ItemId = id);\n"
            "    RemoveIf(colVhpAttachments, ItemId = id);\n"
            "    RemoveIf(colVhpItems, ItemId = id);\n"
            "    If(\n"
            "        varVhpActiveItemId = id,\n"
            "        Set(varVhpActiveItemId, If(CountRows(colVhpItems) > 0, First(colVhpItems).ItemId, Blank()));\n"
            f"        {RESET_EDITOR_CONTROLS}\n"
            "    );\n"
            "    Notify(\"Item \" & Text(id) & \" deleted.\", NotificationType.Success)\n"
            ")"
        ), danger=True, width=DEL_W, height=30,
        accessible="\"Delete item \" & Text(ThisItem.ItemId)")
    btnDelete.props["Size"] = "13"
    btnDelete.props["_OnTop"] = "true"
    RIGHT_W = max(66, DEL_W)
    cardRight = group("conVhpItemCardRight", [cardStatus, btnDelete], direction="Vertical", gap=6,
                      align_items="End", width=RIGHT_W)

    # Det aktive item: kant i to px og info-farven - ikke kun en svag
    # forskel i fyldet (issue #54).
    ACTIVE = "ThisItem.ItemId = varVhpActiveItemId"
    itemCard = group(
        "conVhpItemCard", [cardTextCol, cardRight], direction="Horizontal", gap=10,
        height=f"Parent.TemplateHeight - {ITEM_GAP}",
        fill=f"If({ACTIVE}, {C_INFO_BG}, {C_CARD_BG})",
        border_color=f"If({ACTIVE}, {C_INFO_FG}, {C_CARD_BORDER})",
        border_thickness=f"If({ACTIVE}, 2, 1)", radius=10, pad=(10, 12, 10, 12),
        width="Parent.TemplateWidth", align_items="Center")

    # HELE KORTET ER KLIKBART (issue #54). En gennemsigtig knap over kortet
    # med Open-knappens OnSelect - navnet er Open-knappens, saa intet, der
    # pegede paa den, er brudt. Den ligger OVER teksterne og UNDER Delete
    # (_OnTop), saa et klik paa Delete aldrig ogsaa aabner kortet.
    #
    # Det er det faelles moenster for klikbare raekker (build_helpers.row_hit,
    # issue #79): tone ved hover og tryk, kant ved fokus - og her ogsaa en
    # kant ved hover, fordi kortene staar hver for sig.
    btnOpen = row_hit(
        "btnVhpItemOpen",
        ("Set(varVhpActiveItemId, ThisItem.ItemId);\n"
         "Set(varVhpItemValidated, false);\n"
         "Set(varVhpFlMeta, \"\");\n"
         f"{SEED_FL_PICKER};\n"
         f"{RESET_EDITOR_CONTROLS}"),
        "\"Open item \" & Text(ThisItem.ItemId) & \" \" & ThisItem.ShortText",
        "Parent.TemplateWidth", f"Parent.TemplateHeight - {ITEM_GAP}",
        radius=10, hover_border=True)

    gallery = Ctrl(
        "galVhpItemsRail", "Gallery", variant="Vertical",
        props={
            "AccessibleLabel": "\"VH-plan items\"",
            "BorderStyle": "BorderStyle.None",
            "Fill": C_TRANSPARENT,
            "FillPortions": "0",
            "Height": ITEMS_GAL_H,
            "Items": "Sort(colVhpItems, ItemId)",
            "LayoutMinWidth": "0",
            "LoadingSpinner": "LoadingSpinner.None",
            "Selectable": "false",
            "ShowScrollbar": "false",
            "TabIndex": "0",
            # Kortet skal flugte med knaprakken over det (issue #45): samme
            # bredde som kortets indhold, ingen TemplatePadding. Bredden er
            # skrevet ud - med Parent.Width regner gen_screen den som usikker
            # og traekker GALLERY_RESERVE (40 px) fra kortet i raekken.
            # Start, ikke Stretch: et straekt barn regnes ogsaa som usikkert,
            # uanset hvad der staar i Width.
            "AlignInContainer": "AlignInContainer.Start",
            "TemplatePadding": "0",
            "TemplateSize": str(ITEM_ROW_H),
            "Width": f"({if_below('Desktop', SHELL_W, str(RAIL_W))}) - 36",
            "WrapCount": "1",
        },
        children=[itemCard, btnOpen], h=ITEMS_GAL_H)

    emptyState = text_ctrl(
        "txtVhpItemsEmpty", "\"No items yet. Use Add item to create the first item for this plan.\"",
        size=13, color=C_MUTED, height=40, wrap="true",
        visible="IfError(CountRows(colVhpItems) = 0, true)")

    return card("conVhpItemsCard", [header, btnRow, gallery, emptyState], gap=12)


# Editorens to kolonner. Functional Location staar i sin egen raekke i
# editorens FULDE bredde (issue #72): soegningen skal have plads til koder
# som "SSV13 HFC10AJ010 - Ball bearing house ...".
EDITOR_COL_W = col_width(EDITOR_CW, EDITOR_COLS)
FL_W = EDITOR_CW


def build_item_editor():
    header = section_header("conVhpEditorHead", "Item Editor", "")
    helpPanel = help_panel("conVhpItemHelp", "item")

    # --- Functional Location: EEN combobox med Search (issue #63) ---------
    #
    # Soegefelt og valgliste er den samme ModernCombobox - den samme
    # vaelger som Equipments og Materials (tools/fl_picker.py). Search-
    # knappen eller Enter kalder flowet; det, brugeren derefter skriver,
    # filtrerer svaret lokalt uden nye kald.
    flLabelRow = label_row("conVhpItemFlLabel", "Functional Location", required=True)
    flHint = text_ctrl("txtVhpItemFlHint", bh.hint("FunctionalLocation"), size=12,
                       color=C_MUTED, height=32, wrap="true", visible=HINTS_ON)

    # raw_var foelger VH-plans egen navnekonvention. Den stod foer som en
    # konstant i appens EGEN kopi af build_flsearch.py - og det var netop
    # den ene linje, de tre kopier havde glidt fra hinanden paa.
    flPicker = fl_picker(
        "Vhp", combo=FL_COMBO, results="colVhpFlSearch", raw_var="varVhpFlRaw",
        msg_var="varVhpFlMeta", busy_var=FL_BUSY_VAR, query_var=FL_QUERY_VAR,
        last_var=FL_LAST_VAR, pick_var=FL_PICK_VAR,
        default_items=(f"Filter(colVhpFlSearch, Code = Coalesce({FL_PICK_VAR}, "
                       "LookUp(colVhpItems, ItemId = varVhpActiveItemId).FunctionalLocation))"),
        # En ny soegning goer det gamle objektvalg ugyldigt (issue #72):
        # objekterne hoerer til den soegning, de blev valgt i.
        on_clear=("RemoveIf(colVhpItemObjects, ItemId = varVhpActiveItemId); "
                  "Clear(colVhpObjDraft)"),
        display_mode=DM_ITEM, required_formula=REQ_ITEM, label="Functional location",
        width=FL_W)

    # Soegningens status UNDER feltet - som i Materials (issue #72): "6
    # Functional Locations found for SSV13 HFC10AJ010. Select one from the
    # list below.", soeger, ingen traef, fejl. Aldrig inde i listen.
    flMsg = text_ctrl("txtVhpFlMsg", "varVhpFlMeta", size=12, color=C_MUTED,
                      height=18, wrap="false", visible="!IsBlank(varVhpFlMeta)")

    # OBJECT LIST ER EN POPUP (issue #54). Knappen staar lige under
    # comboboksen og aabner popup'en med en KLADDE af det valgte. Lukkes
    # popup'en uden "Use selected", er intet aendret. Se
    # build_object_list_modal nedenfor.
    #
    # Issue #63: ingen hjaelpe- eller statustekst under knappen. Antallet
    # staar i knappen - "Object List (3)" - og de valgte vises ved hover
    # (Tooltip). Er der intet at vaelge og intet valgt, er den deaktiveret.
    # Bredden er regnet af den bredeste tekst, den kan faa.
    n_obj = f"CountRows({OBJ_CHOSEN})"
    btnObjList = button(
        "btnVhpObjList", f'"Object List (" & Text({n_obj}) & ")"',
        (
            "ClearCollect(\n"
            "    colVhpObjDraft,\n"
            f"    ForAll({OBJ_CHOSEN} As O, {{ Code: O.Code, Description: O.Description }})\n"
            ");\n"
            "Set(varVhpObjListOpen, true)"
        ), width=fit_button_width("\"Object List (000)\""), height=34,
        display_mode=(f"If(IsBlank(varVhpActiveItemId) || !({OBJ_HAS_DATA}), "
                      "DisplayMode.Disabled, DisplayMode.Edit)"),
        accessible=f'"Object List, " & Text({n_obj}) & " selected"')
    btnObjList.props["AlignInContainer"] = "AlignInContainer.Start"
    btnObjList.props["Tooltip"] = OBJ_TOOLTIP
    # Samme udfyldt-tilstand som Item Long Text (issue #73). Den foelger
    # antallet: ryddes valget - af Cancel, Reset eller en ny soegning - er
    # den groenne kant vaek med det samme.
    mark_done(btnObjList, f"{n_obj} > 0")

    flBlock = group("conVhpItemFlBlock",
                    [flLabelRow, flHint, flPicker, flMsg, btnObjList],
                    direction="Vertical", gap=6, width=FL_W, fill_portions=0,
                    align_in_container="Start")

    # Arbejdscentrene til det valgte vaerk (Plant i Plan Header). Upper paa
    # begge sider, saa "asv" og "ASV" er det samme vaerk. Er der ikke valgt
    # vaerk endnu, vises de alle - en tom dropdown uden forklaring er vaerre
    # end en lang.
    MWC_ITEMS = ("Sort(\n"
                 "    If(\n"
                 "        IsBlank(varVhpPlan.Plant),\n"
                 "        colVhpMainWorkCenters,\n"
                 "        Filter(colVhpMainWorkCenters, Upper(Plant) = Upper(varVhpPlan.Plant))\n"
                 "    ),\n"
                 "    Value\n"
                 ")")
    # Default slaar op i den FILTREREDE liste: et arbejdscenter fra et andet
    # vaerk vises som tomt i stedet for som et gyldigt valg.
    drpMwc = themed_dropdown("drpVhpItemMainWorkCenter", MWC_ITEMS,
                      f"LookUp({MWC_ITEMS}, Value = LookUp(colVhpItems, ItemId = varVhpActiveItemId).MainWorkCenter).Value",
                      required_formula=REQ_ITEM, display_mode=DM_ITEM)
    drpAct = themed_dropdown("drpVhpItemActivityType", "colVhpActivityTypeOptions",
                      "LookUp(colVhpActivityTypeOptions, Value = LookUp(colVhpItems, ItemId = varVhpActiveItemId).ActivityType).Value",
                      required_formula=REQ_ITEM, display_mode=DM_ITEM)
    txtShort = text_input("inpVhpItemShortText",
                          "LookUp(colVhpItems, ItemId = varVhpActiveItemId).ShortText", max_length=40,
                          required_formula=REQ_ITEM, display_mode=DM_ITEM)
    # REVISION ER EN TOGGLE (issue #54). SharePoint-kolonnen RevisionMark
    # har eet valg - "REV - General Revision Mark" - saa et felt med en
    # liste var et ja/nej i forklaedning. Taendt = det ene valg, slukket =
    # tomt; vaerdien, der gemmes, er den samme som foer.
    #
    # Classic/Toggle, fordi den moderne toggle ikke er brugt i dette miljoe;
    # den klassiske staar i den gamle VH-plan-app og kompilerer. Den har
    # ingen AccessibleLabel (samme fejl som Classic/Button, issue #57) -
    # Tooltip bruges i stedet.
    # Kompakt kontakt (issue #73) - build_helpers.bool_toggle, den samme
    # stil for alle ja/nej-felter. "Yes"/"No" og intet andet; hvad "Yes"
    # betyder, staar i tooltip'en og i feltets hjaelpetekst.
    tglRevision = bool_toggle(
        "tglVhpItemRevision",
        "!IsBlank(LookUp(colVhpItems, ItemId = varVhpActiveItemId).Revision)",
        display_mode=DM_ITEM,
        tooltip='"Revision: outage work (" & First(colVhpRevisionOptions).Value & ")"')
    # "Orsted Responsible" er fjernet (issue #54) - Initials er nok.
    # Kolonnen OrstedResponsible paa itemet bliver staaende: Save skriver
    # stadig indsenderen som ansvarlig i SharePoint (build_save.py), og en
    # gemt plan laeser den tilbage (build_load.py).
    txtInitials = text_input("inpVhpItemInitials",
                             "LookUp(colVhpItems, ItemId = varVhpActiveItemId).Initials", max_length=12,
                             display_mode=DM_ITEM)
    # LANG TEKST ER EN POPUP (issue #54) - som paa operationerne. Feltet
    # viser begyndelsen af teksten; skrivningen sker i popup'en
    # (build_modal.build_longtext_modal), der gemmer direkte paa itemet.
    LT = "LookUp(colVhpItems, ItemId = varVhpActiveItemId).LongText"
    LT_TIP = 400
    #
    # Issue #73: en KOMPAKT knap med et dokumentikon - ikke et felt i hele
    # kolonnens bredde. "Add long text" uden tekst, "Long text" med, og
    # saa den faelles udfyldt-tilstand (groen kant). Hover viser teksten;
    # er den lang, vises begyndelsen, og knappen aabner hele teksten.
    HAS_LT = f"!IsBlank(Trim(Coalesce({LT}, \"\")))"
    btnLongText = button(
        "btnVhpItemLongText",
        f'If({HAS_LT}, "Long text", "Add long text")',
        ("Set(varVhpLongTextTarget, \"item\");\n"
         "Set(varVhpLongTextItemId, varVhpActiveItemId);\n"
         f"Set(varVhpLongTextDraft, Coalesce({LT}, \"\"));\n"
         "Reset(inpVhpLongTextBox);\n"
         "Set(varVhpLongTextOpen, true)"),
        width=fit_button_width('"Add long text"') + ICON_W, height=36,
        display_mode=DM_ITEM, icon="TextDescription",
        accessible=(f'If({HAS_LT}, "Edit long text for item ", "Add long text for item ") '
                    "& Text(varVhpActiveItemId)"))
    btnLongText.props["AlignInContainer"] = "AlignInContainer.Start"
    btnLongText.props["Tooltip"] = (
        f"If({HAS_LT}, If(Len({LT}) > {LT_TIP}, Left({LT}, {LT_TIP}) & "
        "\"... (open to read all)\", " + LT + "), \"No long text yet\")")
    mark_done(btnLongText, HAS_LT)

    # KOLONNE-ORDEN (issue #54, #72): oppefra og ned i kolonne 1, saa
    # kolonne 2 - og Functional Location i fuld bredde under dem.
    #
    #     +------------------------------+------------------------------+
    #     | Item Short Text              | Revision                     |
    #     | Main Work Center             | Initials                     |
    #     | Activity Type                | Item Long Text               |
    #     +------------------------------+------------------------------+
    #     | Functional Location  [combobox ................][Search] o  |
    #     | 6 Functional Locations found for ...                        |
    #     | [Object List (3)]                                           |
    #     +-------------------------------------------------------------+
    CW = EDITOR_CW

    def cell(name, label, ctrl, hint, required=False):
        return field_cell(name, label, ctrl, required=required, width=EDITOR_COL_W,
                          container_w=CW, fill_portions_formula="0",
                          hint_text=bh.hint(hint))

    fieldsGrid = column_grid("conVhpItemFieldsGrid", [
        [cell("conVhpCellItemShortText", "Item Short Text", txtShort, "ItemShortText", True),
         cell("conVhpCellItemMwc", "Main Work Center", drpMwc, "MainWorkCenter", True),
         cell("conVhpCellItemAct", "Maintenance Activity Type", drpAct, "ActivityType", True)],
        [cell("conVhpCellItemRevision", "Revision", tglRevision, "Revision"),
         cell("conVhpCellItemInitials", "Initials", txtInitials, "Initials"),
         cell("conVhpCellItemLongText", "Item Long Text", btnLongText, "ItemLongText")],
    ], container_w=CW, row_gap=12)

    itemMeta = text_ctrl(
        "txtVhpItemMeta",
        "If(IsBlank(varVhpActiveItemId), \"No item selected.\", \"Item \" & Text(varVhpActiveItemId) & \" - status: \" & Upper(LookUp(colVhpItems, ItemId = varVhpActiveItemId).Status))",
        size=12, color=C_MUTED, height=18, wrap="true")
    # Hvert udfald siger det HOEJT. Knappen skrev foer kun i
    # varVhpRuntimeInfo, som stod i hero-kortet oeverst paa skaermen - var
    # man scrollet ned til Item Editoren, kan man ikke se den, og saa ser et
    # klik ud som om der ikke skete noget. Notify staar oven paa skaermen,
    # uanset hvor man er.
    #
    # Den tredje besked er en faelde, der ellers ikke kunne ses: rammer
    # UpdateIf ingen raekke, goer den ingenting og siger heller ingenting.
    btnSaveItem = button(
        "btnVhpSaveItem", "\"Save\"",
        (
            "If(\n"
            "    IsBlank(varVhpActiveItemId),\n"
            "    Notify(\"Select or add an item first.\", NotificationType.Warning),\n"
            "\n"
            "    Set(varVhpItemValidated, true);\n"
            "    If(\n"
            "        IsBlank(Trim(inpVhpItemShortText.Text)) || Len(Trim(inpVhpItemShortText.Text)) > 40 ||\n"
            "        IsBlank(drpVhpItemMainWorkCenter.Selected.Value) ||\n"
            "        IsBlank(drpVhpItemActivityType.Selected.Value) ||\n"
            f"        IsBlank({FL_CODE}),\n"
            "        UpdateIf(colVhpItems, ItemId = varVhpActiveItemId, { Status: \"invalid\" });\n"
            "        Notify(\"Item contains issues. Fix required fields (marked with *).\", NotificationType.Warning),\n"
            "\n"
            # colVhpItemObjects er allerede sandheden - Tilfoej/Fjern skriver
            # direkte i den. Der er ikke laengere en kontrol med en
            # konkurrerende liste, der skal kopieres herind ved Save.

            "        With(\n"
            f"            {{ code: {FL_CODE} }},\n"
            "            UpdateIf(\n"
            "                colVhpItems,\n"
            "                ItemId = varVhpActiveItemId,\n"
            "                {\n"
            "                    ShortText: Trim(inpVhpItemShortText.Text),\n"
            "                    FunctionalLocation: code,\n"
            f"                    FlDescription: {FL_COMBO}.Selected.Description,\n"
            "                    MainWorkCenter: drpVhpItemMainWorkCenter.Selected.Value,\n"
            "                    ActivityType: drpVhpItemActivityType.Selected.Value,\n"
            "                    ObjectList: Concat(Sort(Filter(colVhpItemObjects, ItemId = varVhpActiveItemId), Code), Code, \"; \"),\n"
            "                    Revision: If(tglVhpItemRevision.Value, First(colVhpRevisionOptions).Value, \"\"),\n"
            "                    Initials: Trim(inpVhpItemInitials.Text),\n"

            "                    Status: \"valid\"\n"
            "                }\n"
            "            )\n"
            "        );\n"
            "        If(\n"
            "            CountRows(Filter(colVhpItems, ItemId = varVhpActiveItemId)) = 0,\n"
            "            Notify(\n"
            "                \"Item \" & Text(varVhpActiveItemId) & \" is not in the list - nothing was saved.\",\n"
            "                NotificationType.Error\n"
            "            ),\n"
            "            Notify(\"Item saved: \" & Trim(inpVhpItemShortText.Text) & \".\", NotificationType.Success)\n"
            "        )\n"
            "    )\n"
            ")"
        ), primary=True, width=110, icon=ICON_SAVE,
        display_mode="If(IsBlank(varVhpActiveItemId), DisplayMode.Disabled, DisplayMode.Edit)")
    # RESET (issue #54): Item Editorens usavede aendringer tilbage til det,
    # der sidst blev gemt paa itemet - eller tomt, hvis itemet aldrig er
    # gemt. Felterne har itemets gemte vaerdi som Default, saa Reset() er
    # "senest gemt". Objektlisten skrives direkte i colVhpItemObjects og
    # hentes derfor tilbage fra itemets gemte ObjectList - beskrivelsen
    # bevares for de objekter, der allerede stod der. Andre items og andre
    # sektioner roeres ikke, og intet slettes i SharePoint.
    btnResetItem = button(
        "btnVhpResetItem", "\"Reset\"",
        (
            "With(\n"
            "    {\n"
            "        keep: ForAll(\n"
            "            Filter(\n"
            "                Split(LookUp(colVhpItems, ItemId = varVhpActiveItemId).ObjectList, \";\"),\n"
            "                !IsBlank(Trim(Value))\n"
            "            ) As S,\n"
            "            {\n"
            "                ItemId: varVhpActiveItemId,\n"
            "                Code: Trim(S.Value),\n"
            "                Description: Coalesce(\n"
            "                    LookUp(colVhpItemObjects, ItemId = varVhpActiveItemId && Code = Trim(S.Value)).Description,\n"
            "                    \"\"\n"
            "                )\n"
            "            }\n"
            "        )\n"
            "    },\n"
            "    RemoveIf(colVhpItemObjects, ItemId = varVhpActiveItemId);\n"
            "    Collect(colVhpItemObjects, keep)\n"
            ");\n"
            "Set(varVhpItemValidated, false);\n"
            "Set(varVhpFlMeta, \"\");\n"
            f"{SEED_FL_PICKER};\n"
            f"{RESET_EDITOR_CONTROLS}"
        ), width=fit_button_width("\"Reset\""), height=36,
        display_mode="If(IsBlank(varVhpActiveItemId), DisplayMode.Disabled, DisplayMode.Edit)")
    btnSaveItem.props["Width"] = str(fit_button_width("\"Save\"", min_w=96) + ICON_W)
    grow(itemMeta)
    footer = group("conVhpEditorFooter", [itemMeta, btnResetItem, btnSaveItem], direction="Horizontal",
                   gap=8, height=36, align_items="Center")

    return card("conVhpEditorCard",
                [header, helpPanel, fieldsGrid, flBlock, footer])


def build_object_list_modal():
    """Object List som popup (issue #54).

    Samme konstruktion som tasklist-pickeren (build_modal.py): en container
    oven paa skaermen med sloeret bagved, centreret, med titel, luk-knap og
    en liste, der selv scroller - siden bagved staar stille.

    Listen er den samme som foer - galleri med ModernCheckbox, filtreret paa
    den valgte Functional Location - men krydserne skrives i en KLADDE,
    colVhpObjDraft. Foerst "Use selected" skriver dem paa itemet. Close og
    X lukker uden at aendre noget."""
    title = text_ctrl("txtVhpObjListTitle", "\"Object List\"", size=17, weight="Semibold",
                      height=26, wrap="false")
    grow(title)
    btnX = button("btnVhpObjListClose", "\"Close\"",
                  "Set(varVhpObjListOpen, false); Clear(colVhpObjDraft)",
                  width=fit_button_width("\"Close\""), height=32,
                  accessible="\"Close object list without changes\"")
    headRow = group("conVhpObjListHeadRow", [title, btnX], direction="Horizontal", gap=12,
                    height=32, align_items="Center")

    under = text_ctrl(
        "txtVhpObjListFl",
        f"If(IsBlank({SEL_FL}), \"No functional location selected.\", "
        f"\"Sub-objects under \" & {SEL_FL} & \" - \" & Text(CountRows({OBJ_CANDIDATES})) & \" found.\")",
        size=12, color=C_MUTED, height=18, wrap="false")

    IN_DRAFT = "CountRows(Filter(colVhpObjDraft, Code = ThisItem.Code)) > 0"
    # EEN afkrydsning, EEN tekst pr. objekt (issue #72). Foer stod der en
    # afkrydsning paa 26 px OG en tekst ved siden af - afkrydsningens egen
    # etiket (platformens standard) blev tegnet oven i teksten, naar raekken
    # blev valgt. Nu ER teksten afkrydsningens etiket, og der er ikke noget
    # andet i raekken, der kan overlappe den.
    chkObj = Ctrl("chkVhpObjPick", "ModernCheckbox", props=checkbox_theme({
        "AccessibleLabel": "\"Select object \" & ThisItem.Code",
        "Default": IN_DRAFT,
        "Height": "24",
        "Label": "ThisItem.Code & If(IsBlank(ThisItem.Description), \"\", \" - \" & ThisItem.Description)",
        "OnCheck": ("If(\n"
                    f"    !({IN_DRAFT}),\n"
                    "    Collect(colVhpObjDraft, { Code: ThisItem.Code, Description: ThisItem.Description })\n"
                    ")"),
        "OnUncheck": "RemoveIf(colVhpObjDraft, Code = ThisItem.Code)",
        "Width": "0",
    }), h=24)
    grow(chkObj)
    objRowTpl = group("conVhpObjRow", [chkObj], direction="Horizontal",
                      gap=10, height="Parent.TemplateHeight - 2", pad=(0, 8, 0, 8),
                      fill=f"If({IN_DRAFT}, {C_INFO_BG}, {C_TRANSPARENT})",
                      align_items="Center", width="Parent.TemplateWidth")

    OBJ_ROWS = 9
    OBJ_ROW_H = 32
    galObj = Ctrl(
        "galVhpItemObjects", "Gallery", variant="Vertical",
        props={
            "AccessibleLabel": "\"Sub-objects\"",
            "BorderColor": C_CARD_BORDER,
            "BorderStyle": "BorderStyle.Solid",
            "BorderThickness": "1",
            "Fill": C_INPUT_BG,
            "FillPortions": "0",
            "Height": str(OBJ_ROWS * (OBJ_ROW_H + 2)),
            "Items": f"Sort({OBJ_CANDIDATES}, Code)",
            "LayoutMinWidth": "0",
            "LoadingSpinner": "LoadingSpinner.None",
            "Selectable": "false",
            "ShowScrollbar": "true",
            "TabIndex": "0",
            "TemplatePadding": "2",
            "TemplateSize": str(OBJ_ROW_H),
            "Width": "Parent.Width",
            "WrapCount": "1",
        },
        children=[objRowTpl], h=OBJ_ROWS * (OBJ_ROW_H + 2))

    objEmpty = text_ctrl(
        "txtVhpObjEmpty",
        (
            "If(\n"
            f"    IsBlank({SEL_FL}),\n"
            "    \"Choose a functional location first.\",\n"
            "    \"No results found. Search more broadly in the functional location field.\"\n"
            ")"
        ), size=12, color=C_MUTED, height=32, wrap="true",
        visible=f"IfError(CountRows({OBJ_CANDIDATES}) = 0, true)")

    info = text_ctrl("txtVhpObjListInfo",
                     "Text(CountRows(colVhpObjDraft)) & \" selected\"",
                     size=12, color=C_MUTED, height=18, wrap="false")
    grow(info)
    btnCancel = button("btnVhpObjListCancel", "\"Cancel\"",
                       "Set(varVhpObjListOpen, false); Clear(colVhpObjDraft)",
                       width=fit_button_width("\"Cancel\""), height=36)
    btnUse = button(
        "btnVhpObjListUse", "\"Use selected\"",
        (
            "RemoveIf(colVhpItemObjects, ItemId = varVhpActiveItemId);\n"
            "Collect(\n"
            "    colVhpItemObjects,\n"
            "    ForAll(colVhpObjDraft As D,\n"
            "        { ItemId: varVhpActiveItemId, Code: D.Code, Description: D.Description })\n"
            ");\n"
            "Clear(colVhpObjDraft);\n"
            "Set(varVhpObjListOpen, false)"
        ), primary=True, width=fit_button_width("\"Use selected\""), height=36)
    footer = group("conVhpObjListFooter", [info, btnCancel, btnUse], direction="Horizontal",
                   gap=8, height=36, align_items="Center")

    # Maks 640 bred og aldrig bredere end skaermen minus 20 px i hver side.
    modal = group(
        "conVhpObjListModal", [headRow, under, galObj, objEmpty, footer], direction="Vertical",
        gap=12, fill=C_MODAL_BG, border_color=C_PRIMARY_SOFT, radius=16,
        pad=(18, 18, 18, 18), width="Min(640, App.Width - 40)", drop_shadow="ExtraBold",
        visible="varVhpObjListOpen")
    modal.props["X"] = "(App.Width - Self.Width) / 2"
    modal.props["Y"] = "Max(20, (App.Height - Self.Height) / 3)"
    return modal


SECTION_SLACK = 2


def build_items_section():
    rail = build_items_rail()
    editor = build_item_editor()
    # Hoejden er de to korts BEREGNEDE hoejder - ikke .Height paa kontrollerne.
    # Det var netop den reference, der gav cirkelreferencen og kaskade-vaeksten.
    # De TRE udtryk herunder skal bruge det SAMME braekpunkt: hoejden,
    # skinnens bredde og EDITOR_W. Er de uenige, tror skinnen at den staar
    # under editoren, mens editoren tror den staar ved siden af - og
    # hoejden passer til ingen af delene. Derfor kommer de alle tre fra
    # tools/layout_tokens.py nu, hvor de foer havde 1000 skrevet i sig hver
    # for sig.
    side = at_least("Desktop")
    h = if_below("Desktop",
                 f"({rail.h}) + {SPLIT_GAP} + ({editor.h})",
                 f"Max(({rail.h}), ({editor.h}))")
    # INGEN WRAP (issue #78). I #73 blev raekken LayoutWrap + Align Start +
    # FillPortions paa editoren - og i Studio blev BEGGE kort ca. 100 px
    # hoeje og klippede deres indhold. Microsoft: "If the container's Wrap
    # property is enabled, the Align property setting is ignored on child
    # controls." Nu er det flow_row's konstruktion: ENTEN side om side
    # (Desktop og op) ELLER under hinanden - retningen skifter, linjeantallet
    # goer ikke. Side om side er det Microsofts eget eksempel: Align
    # Stretch, skinnen fast, editoren FillPortions 1, saa dens hoejre kant
    # flugter med kortene over og under (issue #73) uden en haandregnet
    # bredde. Under hinanden er begge Stretch i fuld bredde.
    rail.props["Width"] = if_below("Desktop", SHELL_W, str(RAIL_W))
    rail.props["FillPortions"] = "0"
    rail.props["LayoutMinWidth"] = f"If({side}, {RAIL_W}, 0)"
    editor.props["Width"] = EDITOR_W
    editor.props["FillPortions"] = f"If({side}, 1, 0)"
    editor.props["LayoutMinWidth"] = f"If({side}, {EDITOR_W}, 0)"
    # 2 px under kortene: kanten, hjoernerne og fokusringen nederst paa
    # Items og Item Editor maa ikke klippes af raekkens LayoutOverflow.Hide
    # (issue #73) - heller ikke naar Studio tegner et kort en pixel hoejere,
    # end hoejde-algebraen regnede med.
    split = group("conVhpItemsSplit", [rail, editor], direction="Horizontal", gap=SPLIT_GAP,
                  height=f"({h}) + {SECTION_SLACK}", pad=(0, 0, SECTION_SLACK, 0),
                  align_items="Stretch")
    split.props["LayoutDirection"] = (f"If({side}, LayoutDirection.Horizontal, "
                                      f"LayoutDirection.Vertical)")
    return split
