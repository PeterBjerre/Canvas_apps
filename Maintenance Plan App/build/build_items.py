# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import (Ctrl, C_CARD_BG, C_CARD_BORDER, C_TITLE, C_MUTED, C_REQUIRED, C_PRIMARY, C_WHITE,
                        C_INFO_FG, C_INFO_BG, C_VALID_FG, C_VALID_BG, C_INVALID_FG, C_INVALID_BG,
                        C_NEUTRAL_FG, C_NEUTRAL_BG, C_INPUT_BG, FONT, SHELL_W, EDITOR_W, RAIL_W,
                        SPLIT_GAP, C_TRANSPARENT, C_MODAL_BG, C_PRIMARY_SOFT)
from layout_tokens import if_below
from build_helpers import (text_ctrl, group, button, button_row, text_input, number_input, dropdown,
                           label_row, field_cell, row_n, col_width, badge, card, combobox, poll_timer,
                           TWO_COL_MIN, HINTS_ON, grow, fit_button_width, column_grid)
from build_plan_header import section_header, help_panel
import build_help as bh
from build_helpers import HINTS_ON as bh_hints
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

# Gallerihoejde: een raekke pr. item. Mellemrummet paa 6 px ligger UNDER
# kortet i raekken (kortet er 88 hoejt), ikke i TemplatePadding - saa ville
# det ogsaa ligge til hoejre og venstre, og kortet flugtede ikke med
# knapperne over det.
ITEM_GAP = 6
ITEM_ROW_H = 88 + ITEM_GAP
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

# Hvad der er valgt - under Object List-knappen, saa det kan ses uden at
# aabne popup'en.
OBJ_CHOSEN_TEXT = (
    "With(\n"
    f"    {{ n: CountRows({OBJ_CHOSEN}) }},\n"
    "    If(\n"
    "        n = 0, \"No sub-objects selected.\",\n"
    "        Text(n) & \" selected: \" &\n"
    f"            Concat(Sort({OBJ_CHOSEN}, Code), Code, \", \") &\n"
    "            With(\n"
    f"                {{ fremmede: CountRows(Filter({OBJ_CHOSEN}, !StartsWith(Code, {SEL_FL}))) }},\n"
    "                If(\n"
    "                    fremmede > 0,\n"
    "                    \"   |   WARNING: \" & Text(fremmede) &\n"
    "                        \" of them are not under the selected functional location.\",\n"
    "                    \"\"\n"
    "                )\n"
    "            )\n"
    "    )\n"
    ")"
)
OBJ_CHOSEN_COLOR = (f"If(\n"
                    f"    CountRows(Filter({OBJ_CHOSEN}, !StartsWith(Code, {SEL_FL}))) > 0, {C_INVALID_FG},\n"
                    f"    CountRows({OBJ_CHOSEN}) = 0, {C_MUTED},\n"
                    f"    {C_TITLE}\n"
                    f")")

# DROPDOWNEN EFTER EN SOEGNING (issue #54)
#
# Efter en soegning stod dropdownen tom, selv om der var 819 resultater:
# itemet havde ingen FL endnu, saa Default var blank, og den oeverste linje
# var tom. Nu staar der en pladsholder oeverst - "Select result (819)",
# "No results found" eller en opfordring til at soege.
#
# Pladsholderen er en RAEKKE i Items med tom Code. Den kan ikke gemmes som
# et valg: Save kraever !IsBlank(drpVhpItemFL.Selected.Code), og kanten
# bliver roed paa samme betingelse. Der vaelges aldrig et rigtigt resultat
# automatisk - brugeren aabner selv listen.
#
# Ungroup, fordi Table() ikke blander en record og en tabel. Kolonnenavnet
# er et NAVN, ikke en streng (check_layout regel 31).
FL_PLACEHOLDER = (
    "{ Code: \"\", Description: \"\", Maintainable: true, Level: \"\",\n"
    "  Display: If(\n"
    "      CountRows(colVhpFlSearch) > 0,\n"
    "      \"Select result (\" & Text(CountRows(colVhpFlSearch)) & \")\",\n"
    "      IsBlank(varVhpFlMeta), \"Search to list functional locations\",\n"
    "      \"No results found\"\n"
    "  ) }"
)
FL_ITEMS = ("Ungroup(\n"
            f"    Table({{ Rows: Table({FL_PLACEHOLDER}) }}, {{ Rows: Sort(colVhpFlSearch, Code) }}),\n"
            "    Rows\n"
            ")")
FL_DEFAULT = ("With(\n"
              f"    {{ hit: LookUp({FL_ITEMS}, !IsBlank(Code) && Code = "
              "LookUp(colVhpItems, ItemId = varVhpActiveItemId).FunctionalLocation) },\n"
              f"    If(IsBlank(hit), First({FL_ITEMS}), hit)\n"
              ")")

# FL-soegningens ventetilstand. Samme konstruktion som Equipment og
# Material (tools/domain_parts.py): knappen er deaktiveret, og "Search" er
# skiftet ud med prikker, der bevaeger sig. search_action saetter den
# false igen ad BEGGE veje ud - svar og fejl.
FL_BUSY_VAR = "varVhpFlBusy"
FL_DOTS_VAR = "varVhpFlDots"

RESET_EDITOR_CONTROLS = (
    "Reset(drpVhpItemFL); Reset(txtVhpFlQuery); "
    "Reset(txtVhpItemShortText); "
    "Reset(drpVhpItemMainWorkCenter); Reset(drpVhpItemActivityType); Reset(drpVhpItemRevision); "
    "Reset(txtVhpItemInitials); Reset(txtVhpItemLongText); "
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
            "                {\n"
            "                    ItemId: varVhpNextItemId, OperationNo: SRC.OperationNo,\n"
            "                    OperationShortText: SRC.OperationShortText, WorkHours: SRC.WorkHours,\n"
            "                    DurationHours: SRC.DurationHours, MainWorkCenter: SRC.MainWorkCenter,\n"
            "                    Vendor: SRC.Vendor,\n"
            "                    LongText: SRC.LongText, PackagesKey: SRC.PackagesKey, Selected: false\n"
            "                }\n"
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
            "        Set(varVhpRuntimeInfo, \"Item copied. Functional Location cleared on the copied item.\")\n"
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
            "    RemoveIf(colVhpItems, ItemId = id);\n"
            "    If(\n"
            "        varVhpActiveItemId = id,\n"
            "        Set(varVhpActiveItemId, If(CountRows(colVhpItems) > 0, First(colVhpItems).ItemId, Blank()));\n"
            f"        {RESET_EDITOR_CONTROLS}\n"
            "    );\n"
            "    Set(varVhpRuntimeInfo, \"Item \" & Text(id) & \" deleted.\")\n"
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
    # Classic/Button og ikke ModernButton: den moderne knap har intet Fill,
    # og dens hover-flade kommer fra Fluent-temaet og ville daekke teksten.
    # Den klassiske tegner PRAECIS det, den faar: intet fyld, og en kant i
    # primaerfarven, naar musen er over kortet eller det har fokus.
    #
    # Classic/Button har INGEN AccessibleLabel - compile afviste den (issue
    # #57). Skaermlaeseren laeser knappens Text, saa teksten STAAR der, men
    # i en gennemsigtig farve: den kan hoeres, ikke ses. Kortets egne
    # tekster ligger under og er det, man ser.
    btnOpen = Ctrl("btnVhpItemOpen", "Classic/Button", props={
        "BorderColor": C_TRANSPARENT,
        "BorderStyle": "BorderStyle.Solid",
        "BorderThickness": "2",
        "Color": C_TRANSPARENT,
        "Fill": C_TRANSPARENT,
        "FocusedBorderColor": C_PRIMARY,
        "FocusedBorderThickness": "2",
        "Height": f"Parent.TemplateHeight - {ITEM_GAP}",
        "HoverBorderColor": C_PRIMARY,
        "HoverColor": C_TRANSPARENT,
        "HoverFill": C_TRANSPARENT,
        "OnSelect": (
            "Set(varVhpActiveItemId, ThisItem.ItemId);\n"
            "Set(varVhpItemValidated, false);\n"
            "Set(varVhpFlMeta, \"\");\n"
            f"{SEED_FL_PICKER};\n"
            f"{RESET_EDITOR_CONTROLS}"
        ),
        "PressedBorderColor": C_PRIMARY,
        "PressedColor": C_TRANSPARENT,
        "PressedFill": C_TRANSPARENT,
        "RadiusBottomLeft": "10", "RadiusBottomRight": "10",
        "RadiusTopLeft": "10", "RadiusTopRight": "10",
        "TabIndex": "0",
        "Text": "\"Open item \" & Text(ThisItem.ItemId) & \" \" & ThisItem.ShortText",
        "Width": "Parent.TemplateWidth",
        "X": "0",
        "Y": "0",
    }, h=f"Parent.TemplateHeight - {ITEM_GAP}")

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


def _timer(name, start, duration, on_end):
    """Usynlig timer, der koerer, mens start er sand."""
    return Ctrl(name, "Timer", props={
        "AutoPause": "false",
        "AutoStart": "false",
        "Duration": str(duration),
        "Height": "1",
        "OnTimerEnd": on_end,
        "Repeat": "true",
        "Start": start,
        "Visible": "false",
        "Width": "1",
    }, h=1, vis="false")


# Editorens tre kolonner. Functional Location har sin egen kolonne, og
# feltets indhold er hoejst saa bredt - saa det er kompakt, og der er plads
# til Object List-knappen lige under dropdownen (issue #54).
EDITOR_COL_W = col_width(EDITOR_CW, EDITOR_COLS)
FL_W = f"Min({EDITOR_COL_W}, 360)"


def build_item_editor():
    header = section_header("conVhpEditorHead", "Item Editor", "")
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

    # Soegeteksten starter med vaerkets kode - FL-koderne begynder med den
    # (SSV13 HFC10 ...), saa brugeren skal kun skrive resten. Reset() ved
    # skift af item eller vaerk henter den igen (issue #54).
    txtFlQuery = text_input(
        "txtVhpFlQuery", "Coalesce(varVhpPlan.Plant, \"\")",
        placeholder=("\"At least %d characters, e.g. SSV13 HFC\"" % MIN_SEARCH_LEN),
        display_mode=DM_ITEM, label="\"Search functional location\"")
    grow(txtFlQuery)
    btnFlSearch = button(
        "btnVhpFlSearch",
        f"If({FL_BUSY_VAR}, Left(\"...\", 1 + {FL_DOTS_VAR}), \"Search\")",
        # raw_var foelger VH-plans egen navnekonvention. Den stod foer som
        # en konstant i appens EGEN kopi af build_flsearch.py - og det var
        # netop den ene linje, de tre kopier havde glidt fra hinanden paa.
        search_action("txtVhpFlQuery", "colVhpFlSearch", "varVhpFlMeta",
                      raw_var="varVhpFlRaw", busy_var=FL_BUSY_VAR),
        primary=True, width=FL_BTN_W, height=36,
        display_mode=f"If({FL_BUSY_VAR}, DisplayMode.Disabled, {DM_ITEM})",
        accessible="If(%s, \"Searching functional locations\", \"Search functional location\")"
                   % FL_BUSY_VAR)
    btnFlSearch.props["LayoutMinWidth"] = str(FL_BTN_W)
    flSearchRow = group("conVhpItemFlSearchRow", [txtFlQuery, btnFlSearch],
                        direction="Horizontal", gap=8, height=36,
                        align_items="Center", width="Parent.Width")
    flDots = _timer("tmrVhpFlDots", FL_BUSY_VAR, 400,
                    f"Set({FL_DOTS_VAR}, Mod({FL_DOTS_VAR} + 1, 3))")

    drpFl = dropdown(
        "drpVhpItemFL", FL_ITEMS, FL_DEFAULT,
        item_display="ThisItem.Display",
        required_formula=REQ_ITEM, display_mode=DM_ITEM, value_field="Code", label="\"Select functional location\"")

    # OBJECT LIST ER EN POPUP (issue #54). Knappen staar lige under
    # FL-dropdownen, er saa bred som sin tekst, og aabner popup'en med en
    # KLADDE af det valgte. Lukkes popup'en uden "Use selected", er intet
    # aendret. Se build_object_list_modal nedenfor.
    btnObjList = button(
        "btnVhpObjList", "\"Object List\"",
        (
            "ClearCollect(\n"
            "    colVhpObjDraft,\n"
            f"    ForAll({OBJ_CHOSEN} As O, {{ Code: O.Code, Description: O.Description }})\n"
            ");\n"
            "Set(varVhpObjListOpen, true)"
        ), width=fit_button_width("\"Object List\""), height=34, display_mode=DM_ITEM)
    btnObjList.props["AlignInContainer"] = "AlignInContainer.Start"

    flDescription = text_ctrl(
        "txtVhpItemFlDescription",
        (
            "If(\n"
            "    IsBlank(drpVhpItemFL.Selected.Code), \"No functional location selected yet.\",\n"
            "    \"Selected: \" & drpVhpItemFL.Selected.Code & \" - \" &\n"
            "    drpVhpItemFL.Selected.Description &\n"
            "    If(\n"
            "        drpVhpItemFL.Selected.Maintainable, \"\",\n"
            "        \"   |   WARNING: marked as not maintainable in SAP.\"\n"
            "    )\n"
            ")"
        ),
        size=12, height=18, wrap="true",
        color=("If(!IsBlank(drpVhpItemFL.Selected.Code) && "
               f"!drpVhpItemFL.Selected.Maintainable, {C_INVALID_FG}, {C_MUTED})"))
    flMeta = text_ctrl("txtVhpItemFlMeta", "varVhpFlMeta", size=12, color=C_MUTED,
                       height=32, wrap="true")
    objChosen = text_ctrl("txtVhpItemObjChosen", OBJ_CHOSEN_TEXT, size=12, height=32,
                          wrap="true", color=OBJ_CHOSEN_COLOR)

    flBlock = group("conVhpItemFlBlock",
                    [flLabelRow, flHint, flSearchRow, drpFl, btnObjList, objChosen,
                     flDescription, flMeta, flDots],
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
    drpMwc = dropdown("drpVhpItemMainWorkCenter", MWC_ITEMS,
                      f"LookUp({MWC_ITEMS}, Value = LookUp(colVhpItems, ItemId = varVhpActiveItemId).MainWorkCenter)",
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
    # "Orsted Responsible" er fjernet (issue #54) - Initials er nok.
    # Kolonnen OrstedResponsible paa itemet bliver staaende: Save skriver
    # stadig indsenderen som ansvarlig i SharePoint (build_save.py), og en
    # gemt plan laeser den tilbage (build_load.py).
    txtInitials = text_input("txtVhpItemInitials",
                             "LookUp(colVhpItems, ItemId = varVhpActiveItemId).Initials", max_length=12,
                             display_mode=DM_ITEM)
    # Lang tekst fylder EEN kolonne, ikke hele formularens bredde. Den er
    # flerlinjet og tre linjer hoej, saa der stadig er plads til en laengere
    # tekst.
    txtLongText = text_input("txtVhpItemLongText",
                             "LookUp(colVhpItems, ItemId = varVhpActiveItemId).LongText",
                             height=96, display_mode=DM_ITEM, ttype="Multiline")

    # KOLONNE-ORDEN (issue #54): oppefra og ned i kolonne 1, saa kolonne 2.
    #
    #     +---------------------+---------------------+----------------+
    #     | Item Short Text     | Revision            | Functional     |
    #     | Main Work Center    | Initials            | Location       |
    #     | Activity Type       | Item Long Text      | [Object List]  |
    #     +---------------------+---------------------+----------------+
    CW = EDITOR_CW

    def cell(name, label, ctrl, hint, required=False):
        return field_cell(name, label, ctrl, required=required, width=EDITOR_COL_W,
                          container_w=CW, fill_portions_formula="0",
                          hint_text=bh.hint(hint))

    fieldsGrid = column_grid("conVhpItemFieldsGrid", [
        [cell("conVhpCellItemShortText", "Item Short Text", txtShort, "ItemShortText", True),
         cell("conVhpCellItemMwc", "Main Work Center", drpMwc, "MainWorkCenter", True),
         cell("conVhpCellItemAct", "Maintenance Activity Type", drpAct, "ActivityType", True)],
        [cell("conVhpCellItemRevision", "Revision", drpRevision, "Revision"),
         cell("conVhpCellItemInitials", "Initials", txtInitials, "Initials"),
         cell("conVhpCellItemLongText", "Item Long Text", txtLongText, "ItemLongText")],
        [flBlock],
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
            "    Set(varVhpRuntimeInfo, \"Select or add an item first.\");\n"
            "    Notify(varVhpRuntimeInfo, NotificationType.Warning),\n"
            "\n"
            "    Set(varVhpItemValidated, true);\n"
            "    If(\n"
            "        IsBlank(Trim(txtVhpItemShortText.Text)) || Len(Trim(txtVhpItemShortText.Text)) > 40 ||\n"
            "        IsBlank(drpVhpItemMainWorkCenter.Selected.Value) ||\n"
            "        IsBlank(drpVhpItemActivityType.Selected.Value) ||\n"
            "        IsBlank(drpVhpItemFL.Selected.Code),\n"
            "        UpdateIf(colVhpItems, ItemId = varVhpActiveItemId, { Status: \"invalid\" });\n"
            "        Set(varVhpRuntimeInfo, \"Item contains issues. Fix required fields (marked with *).\");\n"
            "        Notify(varVhpRuntimeInfo, NotificationType.Warning),\n"
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
            "                    Initials: Trim(txtVhpItemInitials.Text),\n"
            "                    LongText: Trim(txtVhpItemLongText.Text),\n"
            "                    Status: \"valid\"\n"
            "                }\n"
            "            )\n"
            "        );\n"
            "        Set(\n"
            "            varVhpRuntimeInfo,\n"
            "            If(\n"
            "                CountRows(Filter(colVhpItems, ItemId = varVhpActiveItemId)) = 0,\n"
            "                \"Item \" & Text(varVhpActiveItemId) & \" is not in the list - nothing was saved.\",\n"
            "                \"Item saved: \" & Trim(txtVhpItemShortText.Text) & \".\"\n"
            "            )\n"
            "        );\n"
            "        Notify(\n"
            "            varVhpRuntimeInfo,\n"
            "            If(\n"
            "                CountRows(Filter(colVhpItems, ItemId = varVhpActiveItemId)) = 0,\n"
            "                NotificationType.Error,\n"
            "                NotificationType.Success\n"
            "            )\n"
            "        )\n"
            "    )\n"
            ")"
        ), primary=True, width=110,
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
    btnSaveItem.props["Width"] = str(fit_button_width("\"Save\"", min_w=96))
    grow(itemMeta)
    footer = group("conVhpEditorFooter", [itemMeta, btnResetItem, btnSaveItem], direction="Horizontal",
                   gap=8, height=36, align_items="Center")

    return card("conVhpEditorCard",
                [header, helpPanel, fieldsGrid, footer])


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
    chkObj = Ctrl("chkVhpObjPick", "ModernCheckbox", props={
        "AccessibleLabel": "\"Select object \" & ThisItem.Code",
        "Default": IN_DRAFT,
        "Height": "24",
        "OnCheck": ("If(\n"
                    f"    !({IN_DRAFT}),\n"
                    "    Collect(colVhpObjDraft, { Code: ThisItem.Code, Description: ThisItem.Description })\n"
                    ")"),
        "OnUncheck": "RemoveIf(colVhpObjDraft, Code = ThisItem.Code)",
        "Width": "26",
    }, h=24)
    txtObjRow = grow(text_ctrl("txtVhpObjRowText", "ThisItem.Display", size=13, height=24,
                               wrap="false"))
    # Den valgte raekke er markeret med info-farven - ikke kun krydset.
    objRowTpl = group("conVhpObjRow", [chkObj, txtObjRow], direction="Horizontal",
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
    h = if_below("Desktop",
                 f"({rail.h}) + {SPLIT_GAP} + ({editor.h})",
                 f"Max(({rail.h}), ({editor.h}))")
    # SHELL_W, ikke Parent.Width: Parent.Width er splittets Width-EGENSKAB,
    # som er hele kroppens - uden dens padding og scrollbar trukket fra.
    rail.props["Width"] = if_below("Desktop", SHELL_W, str(RAIL_W))
    editor.props["Width"] = EDITOR_W
    return group("conVhpItemsSplit", [rail, editor], direction="Horizontal", gap=SPLIT_GAP,
                 height=h, wrap="true")
