# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import (Ctrl, C_CARD_BG, C_CARD_BORDER, C_MUTED, C_INFO_FG,
                        C_INFO_BG, C_VALID_FG, C_INVALID_FG,
                        C_INPUT_BG, SHELL_W,
                        C_TRANSPARENT, C_MODAL_BG,
                        C_PRIMARY_SOFT, C_PRIMARY, C_MUTED_BG, C_WARN_FG)
from design_tokens import ref_hex
import layout_tokens as lay
import icons
from layout_tokens import if_below, at_least, below, fits, TWO_COL_MIN
from build_helpers import (empty_state, checkbox_theme, row_hit, text_ctrl, group, button,
                           text_input, themed_dropdown, label_row,
                           field_cell, col_width, card, grow,
                           fit_button_width, column_grid, ICON_W,
                           mark_done, segmented, border_rule, row_n)
from build_plan_header import section_header, help_panel, section_footer, status_icon
from build_helpers import ensure_hit, popup_head, act_fx, act_mark, act_button
from gen_screen import lock_section
import build_help as bh
from fl_picker import fl_picker, result_count_fx
import build_flsearch as flsearch
import sp_config as cfg
from build_tasklist import AUTO_SELECT_TL
import build_status as st

from build_help import HINTS_ON

# Bredden af items-skinnen, naar de to kort staar side om side, og
# afstanden mellem dem. Stod i tools/gen_screen.py, men VH-planen er den
# eneste bruger (R2-093).
RAIL_W = 360
SPLIT_GAP = 20
# Bredden af Item Editor-kortet, udtrykt uden at referere nogen kontrol.
#
# Her stod "App.Width < 1000". Det var eet af FIRE braekpunkter mellem 996
# og 1024, spredt over fire filer - heroen stablede ved 996, det her ved
# 1000, hubbens fliser ved 1004 og FillPortions ved 1024. Alle fire stod
# for det samme skift, og ingen af dem var valgt i forhold til de tre
# andre. Nu er de eet tal. Se tools/layout_tokens.py.
EDITOR_W = if_below("Desktop", SHELL_W, f"{SHELL_W} - {RAIL_W} - {SPLIT_GAP}")

DM_ITEM = "If(varVhpViewOnly || IsBlank(varVhpActiveItemId), DisplayMode.Disabled, DisplayMode.Edit)"
VIEW_LOCK = "If(varVhpViewOnly, DisplayMode.Disabled, DisplayMode.Edit)"
REQ_ITEM = "varVhpItemValidated"
# Item-sektionen er gemt med Save og laast, til der trykkes Edit (#433).
ITEM_LOCKED = cfg.section_locked("Item")
# Skaermens handlingstilstand (build_hero.ACT) - Saving... i knappen.
ACT = "varVhpAct"

# Items-skinnens og editorens indholdsbredde (kortbredde minus 18+18 polstring).
RAIL_CW = RAIL_W - 36
EDITOR_CW = f"({EDITOR_W} - 36)"

# To kolonner til felterne - Functional Location har sin egen raekke i
# editorens fulde bredde under dem (issue #72).
EDITOR_COLS = 3

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
# De kommer fra colVhpFl - altsaa SAMME resultat som FL-soegningen
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
    f"    colVhpFl,\n"
    f"    !IsBlank({SEL_FL}) && StartsWith(Code, {SEL_FL}) && Code <> {SEL_FL}\n"
    f")"
)

# De objekter, der er valgt paa det aktive item. colVhpItemObjects ER
# sandheden nu - der er ingen multi-select-kontrol, der kan holde en
# konkurrerende liste.
OBJ_CHOSEN = "Filter(colVhpItemObjects, ItemId = varVhpActiveItemId)"

# KKS-BESKRIVELSEN TIL ET VALGT OBJEKT (issue #389).
#
# En gemt plan gemmer kun KKS-numrene (MaintenanceItems.ObjectList: "A; B"),
# og hentningen (build_load.py) giver derfor objekterne en tom Description.
# Beskrivelsen gemmes IKKE dobbelt - den slaas op i den samme kilde, som
# Object list viste den fra ved oprettelsen: FL-flowets svar. Foerst det
# aktuelle soegeresultat (colVhpFl), saa OBJ_DESC_CACHE, som Object list-
# knappen fylder fra flowet for en genaabnet plans objekter
# (FETCH_OBJ_DESC). Er beskrivelsen gemt i samlingen (oprettelse), vinder
# den. Alt er lokale samlinger - intet delegeringsspoergsmaal.
OBJ_DESC_CACHE = "colVhpObjDesc"
OBJ_DESC_RAW = "varVhpObjDescRaw"


def obj_desc_fx(code, stored):
    """Beskrivelsen til objektet code: den gemte, ellers KKS-kildens."""
    return (f"Coalesce({stored}, LookUp(colVhpFl, Code = {code}).Description, "
            f"LookUp({OBJ_DESC_CACHE}, Code = {code}).Description, \"\")")


def obj_label_fx(code, desc):
    """Samme visning som ved oprettelsen: "KKS - beskrivelse"."""
    return f'{code} & If(IsBlank({desc}), "", " - " & {desc})'


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
    f"            Concat(ForAll(Sort({OBJ_CHOSEN}, Code) As O,\n"
    f"                {{ t: {obj_label_fx('O.Code', obj_desc_fx('O.Code', 'O.Description'))} }}), t, Char(10)) &\n"
    "            If(\n"
    "                fremmede > 0,\n"
    "                Char(10) & \"WARNING: \" & Text(fremmede) &\n"
    "                    \" of them are not under the selected functional location.\",\n"
    "                \"\"\n"
    "            )\n"
    "    )\n"
    ")"
)
# Popup'ens raekker (issue #102): kandidaterne under FL'en PLUS de gemte
# valg, der ikke er blandt dem. En gemt plan seeder kun colVhpFl med selve
# FL'en (SEED_FL_PICKER), saa uden de gemte valg var listen tom, og de valgte
# objekter - som tooltip'en viser - kunne ikke ses i popup'en. Kilden er den
# samme som tooltip'ens (OBJ_CHOSEN, lokalt), saa der er intet ekstra kald.
# ForAll over Sequence i stedet for Ungroup (se tools/fl_picker.items_fx).
# I View (issue #406) er raekkerne kun de valgte objekter: der kan ikke
# vaelges nye, saa kandidaterne fra soegningen vises ikke.
OBJ_ROWS_FX = (
    "With(\n"
    f"    {{ c: ForAll(Filter({OBJ_CANDIDATES}, !varVhpViewOnly) As F, "
    "{ Code: F.Code, Description: F.Description }) },\n"
    "    With(\n"
    f"        {{ x: ForAll(Filter({OBJ_CHOSEN}, !(Code in c.Code)) As O,\n"
    f"                    {{ Code: O.Code, Description: {obj_desc_fx('O.Code', 'O.Description')} }}) }},\n"
    "        Sort(\n"
    "            ForAll(\n"
    "                Sequence(CountRows(c) + CountRows(x)),\n"
    "                If(Value <= CountRows(c), Index(c, Value), Index(x, Value - CountRows(c)))\n"
    "            ),\n"
    "            Code\n"
    "        )\n"
    "    )\n"
    ")"
)
# Er der noget at vise? Foerst en gyldig Functional Location (issue #72) -
# saa kandidater under den, eller et valg, der skal kunne fjernes igen.
OBJ_HAS_DATA = (f"!IsBlank({SEL_FL}) && "
                f"(CountRows({OBJ_CANDIDATES}) > 0 || CountRows({OBJ_CHOSEN}) > 0)")

# HENT DE MANGLENDE BESKRIVELSER (issue #389) - naar Object list aabnes paa
# et item, hvis valgte objekter ingen beskrivelse har (en genaabnet plan).
# Den laeser kladden, som knappen lige har fyldt med itemets valgte objekter
# (colVhpObjDraft) - det er dem, popup'en viser som valgt.
# EET kald til FL-flowet med itemets Functional Location - det samme kald,
# som Search laver ved oprettelsen, og som returnerer FL'en og alt under
# den. Svaret laegges i OBJ_DESC_CACHE, ikke i colVhpFl: comboboksen,
# kandidaterne og valget er uaendrede. colVhpItemObjects roeres heller
# ikke, saa planen bliver ikke "aendret" af at blive vist. Hver manglende
# kode faar en raekke (tom, hvis flowet ikke kender den), saa samme item
# ikke kalder flowet igen. Fejler kaldet, staar koderne alene som foer.
# IfError kraever, at vaerdien og fallback'en har samme type: Notify giver
# Boolean, saa kaeden ender med true og ikke med Collect's tabel (issue #400).
FETCH_OBJ_DESC = (
    "With(\n"
    f"    {{ fl: Upper(Trim({SEL_FL})),\n"
    f"      miss: Filter(colVhpObjDraft, IsBlank(Description) && !(Code in {OBJ_DESC_CACHE}.Code) &&\n"
    "                 !(Code in colVhpFl.Code)) },\n"
    "    If(\n"
    "        !IsBlank(fl) && CountRows(miss) > 0,\n"
    "        IfError(\n"
    f"            Set({OBJ_DESC_RAW}, {flsearch.FLOW_NAME}.Run(fl));\n"
    "            With(\n"
    "                { found: ForAll(\n"
    f"                    Table(ParseJSON(Coalesce({OBJ_DESC_RAW}.{flsearch.FLOW_OUTPUT}, \"[]\"))) As R,\n"
    f"                    {{ Code: Text(R.Value.{flsearch.JSON_CODE_FIELD}), "
    f"Description: Text(R.Value.{flsearch.JSON_DESC_FIELD}) }}) }},\n"
    "                Collect(\n"
    f"                    {OBJ_DESC_CACHE},\n"
    "                    ForAll(miss As O,\n"
    "                        { Code: O.Code, Description: Coalesce(LookUp(found, Code = O.Code).Description, \"\") })\n"
    "                )\n"
    "            );\n"
    "            true,\n"
    "            Notify(\"Could not load the object descriptions.\", NotificationType.Warning)\n"
    "        )\n"
    "    )\n"
    ")"
)

# FL-vaelgerens tilstand - samme konstruktion som Equipments og Materials
# (tools/fl_picker.py). search_action saetter FL_BUSY_VAR false igen ad
# BEGGE veje ud - svar og fejl.
FL_BUSY_VAR = "varVhpFlBusy"
FL_QUERY_VAR = "varVhpFlQuery"
FL_LAST_VAR = "varVhpFlLast"
# Det valgte resultat. Soegningen saetter den til det FOERSTE svar (issue
# #72); comboboksens DefaultSelectedItems laeser den foer itemets gemte FL.
FL_PICK_VAR = "varVhpFlPick"
# Mindste soegelaengde i Item Editor (issue #144): 8 tegn (trimmet), foer
# Search - og soegeraekken (Enter) - kan bruges. Kun her; Equipments,
# Materials og de andre FL-soegninger beholder build_flsearch.MIN_SEARCH_LEN.
FL_MIN_LEN = 8

# KUN FL FRA PLANENS VAERK. En FL-kode starter med vaerket (SSV13 HFC10
# hoerer til SSV), og System approval sender en plan retur, naar en FL
# hoerer til et andet vaerk end planens. Derfor soeges der kun, naar de
# foerste 3 tegn er planens Plant (store/smaa bogstaver er ligegyldige). Er
# der ikke valgt Plant endnu, kan der slet ikke soeges.
#
# Issue #453: vaerket er det, der STAAR i Plan Header (st.PLANT = VhpPlant) -
# ogsaa foer Save.
FL_PLANT_PREFIX = st.PLANT_PREFIX


def fl_wrong_plant(q):
    """Sand, naar soegeteksten q (trimmet) ikke maa soeges paa i denne plan."""
    return (f"(IsBlank({st.PLANT}) || "
            f"Upper(Left({q}, 3)) <> {FL_PLANT_PREFIX})")


# VAERKET STAAR ALLEREDE I SOEGNINGEN (issue #453). ModernCombobox har ingen
# standard-soegetekst, saa "SSV" kan ikke staa skrevet i feltet. I stedet
# udfylder appen praefikset: starter det skrevne med et tal ("13 HFC10"),
# soeges der paa vaerket foran ("SSV13 HFC10"). Pladsholderen siger det.
# Skriver brugeren selv hele koden ("SSV13 HFC10"), er intet aendret, og en
# kode fra et andet vaerk ("AVV13 ...") stoppes som foer (fl_wrong_plant).
def fl_with_prefix(q):
    """Soegeteksten q med vaerkets praefiks foran, naar q starter med et tal."""
    return (f"With({{ fq: Trim({q}) }}, "
            f"If(!IsBlank({FL_PLANT_PREFIX}) && IsMatch(Left(fq, 1), \"[0-9]\"), "
            f"{FL_PLANT_PREFIX} & fq, fq))")


FL_PLACEHOLDER = (f'If(IsBlank({st.PLANT}), "Choose a plant in the Plan header first", '
                  f'{FL_PLANT_PREFIX} & "... type the rest, e.g. 13 HFC10")')


FL_WRONG_PLANT_MSG = (
    "If(\n"
    f"    IsBlank({st.PLANT}),\n"
    "    \"Choose a plant in the Plan header before searching for a functional location.\",\n"
    f"    \"Only functional locations for plant \" & {FL_PLANT_PREFIX} &\n"
    f"        \" can be searched. The search must start with \" & {FL_PLANT_PREFIX} & \".\"\n"
    ")"
)

# REVISION OG NON FLOW USER STATUS ER SEGMENTEREDE VALG (issue #141).
# Knapper har ingen Value, saa valget staar i en KLADDE-variabel pr. felt:
# Blank = uroert, og saa gaelder itemets gemte vaerdi. Reset (nyt item,
# andet item, Reset-knappen) er derfor bare Set(..., Blank()) - der er
# intet at indlaese. Save og "usavede aendringer" laeser REV_ON og NF_VAL.
#
# Non Flow-kladden er en post { Value }, fordi IsBlank("") er sand: en
# tekst kunne ikke skelne "None valgt" fra "uroert". En gemt vaerdi, der
# hverken er tom eller ZBOW (historisk), staar derfor uroert, til brugeren
# selv vaelger None eller ZBOW.
ACTIVE_REV = "LookUp(colVhpItems, ItemId = varVhpActiveItemId).Revision"
ACTIVE_NF = "LookUp(colVhpItems, ItemId = varVhpActiveItemId).NonFlowUserStatus"
REV_ON = f"Coalesce(varVhpItemRevPick, !IsBlank({ACTIVE_REV}))"
NF_VAL = f'If(IsBlank(varVhpItemNfPick), {ACTIVE_NF} & "", varVhpItemNfPick.Value & "")'
# SAP-koden, der gemmes for ZBOW - samme vaerdi som valget i SharePoint-
# kolonnen MaintenanceItems.NonFlowUserStatus.
NF_ZBOW = '"ZBOW"'

# DET AKTIVE ITEM, SOM DET STOD, DA DET BLEV AABNET ELLER GEMT (issue #448).
# Item Editoren skriver sine felter i colVhpItems, naar de aendres
# (write_item), saa colVhpItems er ikke laengere "senest gemt". Reset
# laegger itemet tilbage til denne kopi. Den tages hver gang editoren
# nulstilles - nyt, kopieret, slettet eller aabnet item, Reset, ny plan -
# og naar itemet gemmes med Save. Indlaesningen tager den ogsaa
# (build_load).
ACTIVE_ROW = "LookUp(colVhpItems, ItemId = varVhpActiveItemId)"
ITEM_BASE = "varVhpItemBase"
SNAP_ITEM_BASE = f"Set({ITEM_BASE}, {ACTIVE_ROW})"
# Felterne, Item Editoren skriver - og Reset laegger tilbage.
EDITOR_COLUMNS = ("ShortText", "FunctionalLocation", "FlDescription", "MainWorkCenter",
                  "ActivityType", "Revision", "Initials", "NonFlowUserStatus")


def write_item(fields, cond="true"):
    """Skriv et felt fra Item Editoren paa det aktive item (issue #448).

    Felterne skriver deres vaerdi, naar de aendres eller forlades
    (OnChange), saa itemets kort ("N to fix"), trinene og Submit regnes af
    det, der STAAR i editoren - uden Save. Intet datakald: kun colVhpItems.

    cond er feltets egen vagt - samme moenster som tasklist-dropdownen
    (build_tasklist): et tomt valg skrives aldrig fra en dropdown (et
    vaerksskift eller en Reset kan give tomt Selected), og en vaerdi, der
    allerede staar paa itemet, skrives ikke igen."""
    return (f"If(!IsBlank(varVhpActiveItemId) && !varVhpViewOnly && ({cond}), "
            f"UpdateIf(colVhpItems, ItemId = varVhpActiveItemId, {fields}))")


def _differs(new, col):
    """new er forskellig fra det aktive items col (blank = tom tekst)."""
    return f"({new}) <> ({ACTIVE_ROW}.{col} & \"\")"


WRITE_SHORT = write_item("{ ShortText: Trim(inpVhpItemShortText.Text) }",
                         _differs("Trim(inpVhpItemShortText.Text)", "ShortText"))
WRITE_INITIALS = write_item("{ Initials: Upper(Trim(inpVhpItemInitials.Text)) }",
                            _differs("Upper(Trim(inpVhpItemInitials.Text))", "Initials"))


def write_choice(ctrl, col):
    """Dropdownens valg paa itemet - aldrig et tomt valg."""
    return write_item(f"{{ {col}: {ctrl}.Selected.Value }}",
                      f"!IsBlank({ctrl}.Selected.Value) && "
                      + _differs(f"{ctrl}.Selected.Value", col))


# Functional Location: brugerens valg i comboboksen og det automatiske valg
# af foerste soegeresultat (fl_picker on_found). Et tomt valg skrives ikke -
# comboboksen kan staa tom efter en Reset uden at itemet har mistet sin FL.
WRITE_FL_SELECT = write_item(
    f"{{ FunctionalLocation: {FL_COMBO}.Selected.Code, FlDescription: {FL_COMBO}.Selected.Description }}",
    f"!IsBlank({FL_COMBO}.Selected.Code) && " + _differs(f"{FL_COMBO}.Selected.Code", "FunctionalLocation"))
WRITE_FL_FOUND = write_item(
    f"{{ FunctionalLocation: {FL_PICK_VAR}, "
    f"FlDescription: LookUp(colVhpFl, Code = {FL_PICK_VAR}).Description }}",
    f"!IsBlank({FL_PICK_VAR}) && " + _differs(FL_PICK_VAR, "FunctionalLocation"))

# Det aktive items manglende felter som tekst ("Item short text, Initials")
# - tom, naar intet mangler. Samme liste som reglen (build_status).
ACTIVE_MISSING = (
    f"With({{ ar: {ACTIVE_ROW} }}, Concat(Filter(Table("
    + ", ".join(f'{{ n: "{n}", m: {c} }}' for n, c in st.item_required("ar."))
    + '), m), n, ", "))')

# Det aktive items felter fra et andet vaerk end Plan Headers Plant (issue
# #453) - "Main work center, Functional Location" - tom, naar alt passer.
# Samme betingelser som reglen (build_status.ITEM_PLANT_CONFLICTS).
ACTIVE_CONFLICTS = (
    f"With({{ ar: {ACTIVE_ROW} }}, Concat(Filter(Table("
    + ", ".join(f'{{ n: "{n}", m: {c} }}' for n, c in st.item_plant_conflicts("ar."))
    + '), m), n, ", "))')
ACTIVE_MWC_CONFLICT = dict(st.item_plant_conflicts(f"{ACTIVE_ROW}."))["Main work center"]

RESET_EDITOR_CONTROLS = (
    f"{SNAP_ITEM_BASE}; "
    f"Set({FL_QUERY_VAR}, \"\"); Set({FL_LAST_VAR}, \"\"); Set({FL_PICK_VAR}, \"\"); "
    f"Reset({FL_COMBO}); "
    "Reset(inpVhpItemShortText); "
    "Reset(drpVhpItemMainWorkCenter); Reset(drpVhpItemActivityType); Set(varVhpItemRevPick, Blank()); "
    "Reset(inpVhpItemInitials); Set(varVhpItemNfPick, Blank()); "
    # Issue #158: det aktive items foerste gyldige tasklist, hvis det er
    # gemt og ikke har et gyldigt valg (skift af item, aabnet kladde).
    f"{AUTO_SELECT_TL}; "
    "Reset(drpVhpItemTasklist)"
)

# Naar et andet item aabnes, skal comboboksen kunne vise itemets gemte FL.
# Soegesamlingen er tom paa det tidspunkt, saa den seedes med den ene vaerdi.
# Display skal med, fordi det er det felt comboboksen soeger og viser paa.
SEED_FL_PICKER = (
    "Clear(colVhpFl);\n"
    "With(\n"
    "    { it: LookUp(colVhpItems, ItemId = varVhpActiveItemId) },\n"
    "    If(\n"
    "        !IsBlank(it.FunctionalLocation),\n"
    "        Collect(\n"
    "            colVhpFl,\n"
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
        elif k == "SpId":
            # En kopi er en NY raekke - den maa ikke opdatere originalen.
            fields.append("SpId: 0")
        elif k == "ItemGuid":
            # En kopi er et nyt item med sin egen identitet (docs/32 §6).
            fields.append("ItemGuid: Text(GUID())")
        elif k == "FileCount":
            # Dokumenterne haenger paa originalens raekke - kopien har ingen.
            fields.append("FileCount: 0")
        elif k == "FileNames":
            fields.append('FileNames: ""')
        else:
            fields.append(f"{k}: {alias}.{k}")
    return "{\n" + pad + "    " + (",\n" + pad + "    ").join(fields) + "\n" + pad + "}"


# Kortets nummer i Items-listen (Sort(colVhpItems, ItemId)) - issue #230.
CARD_NO = "CountRows(Filter(colVhpItems, ItemId <= ThisItem.ItemId))"



def _delete_item_fx(item_id):
    """Sletningen af et item - editorens "Delete item"
    (UX-review M5). Id'et laeses FOER noget fjernes."""
    return (
            "With(\n"
            "    { id: " + item_id + ", no: CountRows(Filter(colVhpItems, ItemId <= " + item_id + ")) },\n"
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
            "    Notify(\"Item \" & Text(no) & \" deleted.\", NotificationType.Success)\n"
            ")"
    )


# ITEMETS BLOKERINGER (issue #448) - til kortet i Items-listen. Hver raekke
# er een ting, der holder Submit tilbage for itemet: de paakraevede felter
# (build_status.ITEM_REQUIRED - samme liste som reglen og trin 2), en
# tasklist (trin 3), mindst een operation (trin 4) og operationernes egne
# regler (kort tekst, PM02, pakke paa en strategiplan). Alt laeses af
# samlingerne - ingen datakald - og Item Editoren skriver sine felter i
# colVhpItems, naar de aendres (write_item), saa kortet foelger med uden Save.
_ROW = "ThisItem."
_OP_PROBLEM = (f"{st.OP_NO_TEXT} || ({st.OP_NO_MG}) || ({st.OP_NO_COST}) || "
               f"(pk && {st.OP_NO_PKG})")
# Issue #453: vaerdier fra et andet vaerk end Plan Headers Plant er ogsaa
# blokeringer - de markeres, de slettes ikke.
_BLOCKER_ROWS = [(n, c) for n, c in st.item_required(_ROW)] + [
    (f"{n} (other plant)", c) for n, c in st.item_plant_conflicts(_ROW)] + [
    ("Task list", f"IsBlank(Trim({_ROW}TasklistKey))"),
    ("Task list (other plant)", st.tasklist_plant_conflict(_ROW)),
    ("Operations", "IsEmpty(ops)"),
    ("Operation details", f"!IsEmpty(Filter(ops, {_OP_PROBLEM}))"),
]
ITEM_BLOCKERS = (
    "With(\n"
    "    {\n"
    f"        ops: Filter(colVhpOperations, ItemId = {_ROW}ItemId),\n"
    f"        pk: IfError({st.IS_STRAT_PLAN}, false) && {st.HAS_PKGS}\n"
    "    },\n"
    "    Filter(\n"
    "        Table(\n"
    + ",\n".join(f'            {{ n: "{n}", m: {c} }}' for n, c in _BLOCKER_ROWS) + "\n"
    "        ),\n"
    "        m\n"
    "    )\n"
    ")")
# Mangler kortets item et paakraevet felt? (de roede kanter i editoren)
ITEM_FIELDS_MISSING_ROW = "(" + " || ".join(c for _n, c in st.item_required(_ROW)) + ")"


def build_items_rail():
    # Vaerket fra Plan Header staar ved titlen: det er den kontekst, alle
    # items arbejder i - arbejdscentre, tasklister og FL-soegningen er
    # filtreret paa det (issue #54).
    header = None  # bygges efter knapperne (copy + Add item staar i kortets hoved)

    btnAdd = button(
        "btnVhpAddItem", "\"Add item\"",
        (
            "If(\n"
            "    !varVhpPlanCommitted,\n"
            "    Notify(\"Press Save in the plan header before adding items.\", NotificationType.Warning),\n"
            "    Set(varVhpNextItemId, varVhpNextItemId + 1);\n"
            "    Collect(\n"
            "        colVhpItems,\n"
            "        {\n"
            "            ItemId: varVhpNextItemId, ShortText: \"\", FunctionalLocation: \"\", FlDescription: \"\",\n"
            "            MainWorkCenter: \"\", ActivityType: \"\", ObjectList: \"\", Revision: \"\",\n"
            "            OrstedResponsible: \"\", Initials: Upper(First(Split(varVhpMe, \"@\")).Value), LongText: \"\", NonFlowUserStatus: \"\", TasklistKey: \"\", TasklistName: \"\",\n"
            "            Status: \"draft\", SpId: 0, ItemGuid: Text(GUID())\n"
            "        }\n"
            "    );\n"
            "    Set(varVhpActiveItemId, varVhpNextItemId);\n"
            "    Set(varVhpItemValidated, false);\n"
            "    Set(varVhpFlMsg, \"\");\n"
            f"    {SEED_FL_PICKER};\n"
            f"    {RESET_EDITOR_CONTROLS};\n"
            "    Notify(\"Item \" & Text(CountRows(colVhpItems)) & \" added.\", NotificationType.Success)\n"
            ")"
        ), primary=True, icon=icons.FLUENT["add"], display_mode=VIEW_LOCK,
                    visible="!varVhpViewOnly")


    btnCopy = button(
        "btnVhpCopyItem", "\"\"",
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
            "                NonFlowUserStatus: src.NonFlowUserStatus,\n"
            "                TasklistKey: src.TasklistKey, TasklistName: src.TasklistName, Status: \"draft\",\n"
            # En kopi er et NYT item: ny identitet, ikke kildens (docs/32 §6).
            "                SpId: 0, ItemGuid: Text(GUID())\n"
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
        ), display_mode=VIEW_LOCK, visible="!varVhpViewOnly")

    # KORTETS HOVED (mockup): Copy som ikonknap og "+ Add item" som blaa
    # primaerknap staar til hoejre i overskriften, efter trin-badget. Delete
    # staar paa hvert kort (se nedenfor).
    btnAdd.props["Width"] = str(fit_button_width('"Add item"', size=13, min_w=0) + ICON_W - 8)
    btnAdd.props["Size"] = "13"
    btnAdd.props["LayoutMinWidth"] = btnAdd.props["Width"]
    btnAdd.props["Height"] = "36"
    btnCopy.props.update({
        "Icon": f"\"{icons.FLUENT['copy']}\"",
        "Layout": "ButtonLayout.IconOnly",
        "AccessibleLabel": "\"Copy item\"",
        "Tooltip": "\"Copy item\"",
        "Width": "36", "Height": "36", "LayoutMinWidth": "36",
    })
    ensure_hit(btnCopy)
    btnCopy.props["LayoutMinWidth"] = btnCopy.props["Width"]
    header = section_header("conVhpItemsHead", "Items", "Step 2", extra_right=[btnCopy, btnAdd],
                            valid_fx=items_valid_fx())
    # Badget foer knapperne: [titel] [gap] [badge] [copy] [add]
    _kids = header.children
    _badge = _kids.pop()
    _kids.insert(len(_kids) - 2, _badge)

    # --- item card template -------------------------------------------------
    # Uden kort tekst hedder kortet sit NUMMER i listen (issue #230) - det
    # samme "Item <nr>", som valideringsbeskederne bruger (build_status.
    # item_ref). Foer stod ItemId, som efter indlaesning er SharePoint-ID'et
    # ("Item 199").
    cardTitle = text_ctrl(
        "txtVhpItemCardTitle",
        f"If(IsBlank(ThisItem.ShortText), \"Item \" & Text({CARD_NO}), ThisItem.ShortText)",
        size=14, weight="Bold", height=20, wrap="false")
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
    # STATUS (mockup): flueben/advarsel til venstre og "Valid" (groen) eller
    # "N to fix" (roed) til hoejre - ikke et uppercase-badge.
    #
    # ISSUE #448: N er itemets AEGTE blokeringer for Submit, regnet af de
    # aktuelle vaerdier (item_blockers). Foer talte kortet fire felter paa
    # den GEMTE raekke og kraevede Status "valid" - saa det stod "4 to fix",
    # mens felterne var udfyldt i editoren, og tasklist (uden for Strategy)
    # og operationer taltes slet ikke, selvom Submit kraever dem.
    FIX_N = f"CountRows({ITEM_BLOCKERS})"
    ITEM_OK = f"IsEmpty({ITEM_BLOCKERS})"
    cardIcon = status_icon("icoVhpItemCardStatus", ITEM_OK, size=20)
    cardIcon.props["AlignInContainer"] = "AlignInContainer.Center"
    cardStatus = text_ctrl(
        "txtVhpItemCardStatus",
        f"With({{ fixN: {FIX_N} }}, If(fixN = 0, \"Valid\", Text(fixN) & \" to fix\"))",
        size=12, weight="Semibold", height=22, width=84, wrap="false", align="Right",
        extra={
            "AlignInContainer": "AlignInContainer.End",
            "Color": f"If({ITEM_OK}, {C_VALID_FG}, {C_INVALID_FG})",
        })
    # DELETE PAA KORTET (issue #54). Hed "Remove item" og stod i knaprakken
    # over listen, hvor den slettede det AKTIVE item - ikke noedvendigvis
    # det, man kiggede paa. Nu sletter den sit eget kort. Id'et laeses FOER
    # noget fjernes: raekken, ThisItem peger paa, forsvinder undervejs.
    #
    # Samme sletning som foer: operationer og objekter foelger med.
    # Beskeden naevner itemets nummer i listen (issue #230), regnet FOER
    # sletningen - ikke ItemId, som er SharePoint-ID'et.
    DEL_W = fit_button_width("\"Delete\"", size=13, min_w=64)
    btnDelete = button(
        "btnVhpRemoveItem", "\"Delete\"",
        _delete_item_fx("ThisItem.ItemId"), danger=True, width=DEL_W, height=30, display_mode=VIEW_LOCK, visible="!varVhpViewOnly",
        accessible=f"\"Delete item \" & Text({CARD_NO})")
    btnDelete.props["Size"] = "13"
    btnDelete.props["_OnTop"] = "true"
    RIGHT_W = max(84, DEL_W)
    cardRight = group("conVhpItemCardRight", [cardStatus, btnDelete], direction="Vertical", gap=6,
                      align_items="End", width=RIGHT_W)

    # Det aktive item: kant i to px og info-farven - ikke kun en svag
    # forskel i fyldet (issue #54).
    ACTIVE = "ThisItem.ItemId = varVhpActiveItemId"
    itemCard = group(
        "conVhpItemCard", [cardIcon, cardTextCol, cardRight], direction="Horizontal", gap=10,
        height=f"Parent.TemplateHeight - {ITEM_GAP}",
        fill=f"If({ACTIVE}, {C_INFO_BG}, {C_CARD_BG})",
        border_color=f"If({ACTIVE}, {C_INFO_FG}, {C_CARD_BORDER})",
        border_thickness=f"If({ACTIVE}, 2, 1)", radius=10, pad=(10, 12, 10, 12),
        width="Parent.TemplateWidth", align_items="Center")

    # HELE KORTET ER KLIKBART (issue #54). En gennemsigtig knap over kortet
    # med Open-knappens OnSelect - navnet er Open-knappens, saa intet, der
    # pegede paa den, er brudt. Den ligger OVER teksterne.
    #
    # Det er det faelles moenster for klikbare raekker (build_helpers.row_hit,
    # issue #79): tone ved hover og tryk, kant ved fokus - og her ogsaa en
    # kant ved hover, fordi kortene staar hver for sig.
    btnOpen = row_hit(
        "btnVhpItemOpen",
        ("Set(varVhpActiveItemId, ThisItem.ItemId);\n"
         f"Set(varVhpItemValidated, {ITEM_FIELDS_MISSING_ROW});\n"
         "Set(varVhpFlMsg, \"\");\n"
         f"{SEED_FL_PICKER};\n"
         f"{RESET_EDITOR_CONTROLS}"),
        f"\"Open item \" & Text({CARD_NO}) & \" \" & ThisItem.ShortText",
        "Parent.TemplateWidth", f"Parent.TemplateHeight - {ITEM_GAP}",
        radius=10, hover_border=True)
    MISSING = f'Concat({ITEM_BLOCKERS}, n, ", ")'
    btnOpen.props["Tooltip"] = f'With({{ miss: {MISSING} }}, If(IsBlank(miss), "", "To fix: " & miss))'

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

    # Tom tilstand (UX-review F4): ikon og een saetning. Ingen egen knap -
    # Add item i kortets hoved er den eneste (issue #459: den stod to gange).
    emptyState = empty_state(
        "conVhpItemsEmpty", '"No items yet - choose Add item to create the first one."',
        icon_key="vhplan",
        visible="IfError(CountRows(colVhpItems) = 0, true)")

    return card("conVhpItemsCard", [header, gallery, emptyState], gap=12)


# Editorens to kolonner. Functional Location staar i sin egen raekke i
# editorens FULDE bredde (issue #72): soegningen skal have plads til koder
# som "SSV13 HFC10AJ010 - Ball bearing house ...".
EDITOR_COL_W = col_width(EDITOR_CW, EDITOR_COLS)
FL_W = fits(EDITOR_CW, TWO_COL_MIN, EDITOR_CW, f"(({EDITOR_CW} - 40) / 3) * 2 + 20")


def _obj_list_button(n_obj, n_found):
    """Object list-knappen som et billede med SAMME udseende som en outline-
    knap. Et billede, fordi dets Tooltip er browserens egen: den bryder
    linjerne (Char(10)) og ombryder lange tekster. ModernButtons Fluent-
    tooltip samlede alle de valgte objekter paa een linje.

    Udfyldt (mindst et objekt valgt): groen kant og tekst, som Item Long
    Text (issue #73) - tilstanden foelger antallet, saa den forsvinder, naar
    valget ryddes.

    Tallet i knappen (issue #454) er n_found: antal resultater i den
    aktuelle FL-soegning - samme samling og samme tal som beskeden under
    feltet ("6 Functional Locations found ..." -> "Object list (6)").
    Det nulstilles af fl_picker.result_count_fx, naar soegeteksten aendres,
    resultaterne ryddes, eller en ny soegning starter. De VALGTE objekter
    staar i tooltip'en og i den groenne tilstand (n_obj)."""
    w, h = fit_button_width('"Object list (000)"') + 28, 34
    done = f"({n_obj} > 0)"
    # I View (issue #406) kan knappen altid bruges paa et item: popup'en
    # viser itemets objekter skrivebeskyttet. Soegningen er laast i View,
    # saa kravet om data at vaelge imellem gaelder kun i Create og Edit.
    off = f"(IsBlank(varVhpActiveItemId) || (!varVhpViewOnly && !({OBJ_HAS_DATA})))"
    hx = ref_hex
    edge = f"If({done}, {hx('state-ok-fg')}, {hx('border-default')})"
    ink = f"If({off}, {hx('text-muted')}, {done}, {hx('state-ok-fg')}, {hx('text-primary')})"
    def _svg(w, x0, label):
        return (
            f'"<svg xmlns=\'http://www.w3.org/2000/svg\' width=\'{w}\' height=\'{h}\' '
            f'viewBox=\'0 0 {w} {h}\'><rect x=\'0.5\' y=\'0.5\' width=\'{w - 1}\' '
            f'height=\'{h - 1}\' rx=\'{lay.RADIUS_INPUT}\' fill=\'none\' stroke=\'" & {edge} & "\'/>'
            # Listeikonet er det faelles (tools/icons.LIST, issue #139) - samme
            # tegning og streg som Fluents TextBulletListLtr paa hubbens "All".
            + icons.glyph(icons.LIST, "#", size=16, x=x0 - 1, y=h // 2 - 8).replace(
                "'#'", "'\" & " + ink + " & \"'")
            + (f'<text x=\'{(w + 22) // 2}\' y=\'{h // 2 + 5}\' text-anchor=\'middle\' '
               f'font-family=\'Segoe UI, sans-serif\' font-size=\'14\' font-weight=\'600\' '
               f'fill=\'" & {ink} & "\'>" & {label} & "</text>' if label else '')
            + '</svg>"')
    svg = (f'If({below("Tablet")}, ' + _svg(40, 12, None) + ', '
           + _svg(w, 14, '"Object list (" & Text(' + n_found + ') & ")"') + ')')
    img = Ctrl("imgVhpObjList", "Image", props={
        "AccessibleLabel": (f'"Object list, " & Text({n_found}) & " found, " & '
                           f'Text({n_obj}) & " selected"'),
        "AlignInContainer": "AlignInContainer.Start",
        "BorderStyle": "BorderStyle.None",
        "BorderThickness": "0",
        "DisplayMode": f"If({off}, DisplayMode.Disabled, DisplayMode.Edit)",
        "Fill": C_TRANSPARENT,
        "FocusedBorderColor": C_PRIMARY,
        "FocusedBorderThickness": "2",
        "Height": str(h),
        "HoverFill": C_MUTED_BG,
        "Image": f'"data:image/svg+xml;utf8," & EncodeUrl({svg})',
        "ImagePosition": "ImagePosition.Fit",
        "OnSelect": (
            "ClearCollect(\n"
            "    colVhpObjDraft,\n"
            f"    ForAll({OBJ_CHOSEN} As O, {{ Code: O.Code, Description: O.Description }})\n"
            ");\n"
            "Set(varVhpObjListOpen, true);\n"
            # Popup'en aabner med det samme; beskrivelserne kommer, naar
            # flowet svarer (issue #389).
            + FETCH_OBJ_DESC
        ),
        "PressedFill": C_MUTED_BG,
        "TabIndex": "0",
        "Tooltip": OBJ_TOOLTIP,
        "Width": if_below("Tablet", "40", str(w)),
    }, h=h)
    return img


def items_valid_fx():
    """Trin 2 er "Valid" (issue #123): alle items har deres paakraevede
    felter, og ingen item-regel fejler (build_status.VhpItemsValid) - samme
    betingelse som progressbarens Item-trin. Issue #448: usavede
    aendringer i Item Editoren goer ikke trinnet ugyldigt; editoren skriver
    felterne paa itemet, naar de aendres (write_item)."""
    return "VhpItemsValid"


def build_item_editor():
    # TRIN-BADGE (issue #123): "Step 2", indtil trinnet er faerdigt og
    # gyldigt, saa "Valid" - som Plan Header og Tasklist and Operations.
    # Foer stod det valgte items egen status her (Draft/Valid/Invalid); den
    # staar stadig paa itemets kort i listen. Badgets advarsel vises, naar
    # det valgte item mangler et paakraevet felt, efter Save er forsoegt
    # eller itemet er aabnet med mangler (issue #448: af vaerdierne, ikke
    # af Status fra sidste Save).
    # HVILKET ITEM (UX-review M5, VH-plan-mockuppen): "Item 1 - Bearing
    # lubrication" ved titlen og "Delete item" i hovedet - den samme
    # sletning som kortets Delete, paa det aktive item.
    active = "LookUp(colVhpItems, ItemId = varVhpActiveItemId)"
    no = "CountRows(Filter(colVhpItems, ItemId <= varVhpActiveItemId))"
    which = text_ctrl("txtVhpEditorWhich",
                      f'If(IsBlank(varVhpActiveItemId), "", Text({no}) & '
                      f'If(IsBlank({active}.ShortText), "", "  \u00b7  " & {active}.ShortText))',
                      size=lay.SIZE_BODY, color=C_MUTED, height=20, width="260", wrap="false")
    del_txt = '"Delete item"'
    btnDelItem = button("btnVhpEditorDelete", del_txt, _delete_item_fx("varVhpActiveItemId"),
                        danger=True, width=fit_button_width(del_txt, size=13), height=30,
                        display_mode=VIEW_LOCK,
                        visible="(!IsBlank(varVhpActiveItemId) && !varVhpViewOnly)",
                        accessible=f'"Delete item " & Text({no})')
    btnDelItem.props["Size"] = "13"
    btnDelItem.props["LayoutMinWidth"] = btnDelItem.props["Width"]
    header = section_header("conVhpEditorHead", "Item", "Step 2", extra_left=[which],
                            extra_right=[btnDelItem],
                            valid_fx=items_valid_fx(),
                            attention_fx=f"({REQ_ITEM} && !IsBlank({ACTIVE_MISSING}))")
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
    n_obj = f"CountRows({OBJ_CHOSEN})"
    # Knappens tal: den aktuelle soegnings resultater (issue #454).
    n_found = result_count_fx(combo=FL_COMBO, results="colVhpFl",
                              busy_var=FL_BUSY_VAR, last_var=FL_LAST_VAR)
    btnObjList = _obj_list_button(n_obj, n_found)
    btnObjList.props["AlignInContainer"] = "AlignInContainer.Center"
    btnObjList.props["LayoutMinWidth"] = btnObjList.props["Width"]
    flPicker = fl_picker(
        "Vhp", combo=FL_COMBO, results="colVhpFl", raw_var="varVhpFlRaw",
        msg_var="varVhpFlMsg", busy_var=FL_BUSY_VAR, query_var=FL_QUERY_VAR,
        last_var=FL_LAST_VAR, pick_var=FL_PICK_VAR,
        default_items=(f"Filter(colVhpFl, Code = Coalesce({FL_PICK_VAR}, "
                       "LookUp(colVhpItems, ItemId = varVhpActiveItemId).FunctionalLocation))"),
        # En ny soegning goer det gamle objektvalg ugyldigt (issue #72):
        # objekterne hoerer til den soegning, de blev valgt i.
        on_clear=("RemoveIf(colVhpItemObjects, ItemId = varVhpActiveItemId); "
                  "Clear(colVhpObjDraft)"),
        on_select=WRITE_FL_SELECT, on_found=WRITE_FL_FOUND,
        display_mode=DM_ITEM, required_formula=REQ_ITEM, label="Functional location",
        width=FL_W, trail=[btnObjList], stack_search=True, col_w=EDITOR_COL_W,
        stack_cond=f"({below('Tablet')} || ({EDITOR_CW}) < {TWO_COL_MIN})",
        min_len=FL_MIN_LEN, block=(fl_wrong_plant, FL_WRONG_PLANT_MSG),
        query_map=fl_with_prefix, placeholder=FL_PLACEHOLDER)

    # For kort soegetekst (issue #144): en kort besked under feltet, saa
    # laenge der er skrevet noget, men faerre end FL_MIN_LEN tegn. Laeser
    # comboboksens SearchText direkte - ikke FL_QUERY_VAR, som timeren kun
    # opdaterer, naar der staar noget, og som derfor kan vaere foraeldet.
    # Issue #453: laengden og vaerket af det, der SOEGES paa - med vaerket
    # udfyldt foran (fl_with_prefix), som Search-knappen goer.
    fl_typed = f"Len(Trim({FL_COMBO}.SearchText))"
    fl_query = fl_with_prefix(f"{FL_COMBO}.SearchText")
    fl_query_len = f"Len({fl_query})"
    # Forkert vaerk: vises fra 3 tegn (der kan prefikset afgoeres) - eller med
    # det samme, hvis planen ikke har en Plant endnu.
    fl_wrong = (f"!{FL_BUSY_VAR} && {fl_typed} > 0 && "
                f"(IsBlank({st.PLANT}) || ({fl_query_len} >= 3 && "
                f"{fl_wrong_plant(fl_query)}))")
    # ITEMETS GEMTE FL HOERER TIL ET ANDET VAERK (issue #453) - fx efter et
    # skift af Plant. FL'en bliver staaende (markeret, ikke slettet), og
    # beskeden siger, hvad der skal goeres. Kun naar der ikke skrives.
    fl_conflict = (f"!{FL_BUSY_VAR} && {fl_typed} = 0 && "
                   + dict(st.item_plant_conflicts(f"{ACTIVE_ROW}."))["Functional Location"])
    flWrongPlant = text_ctrl(
        "txtVhpFlWrongPlant",
        (f"If(\n    {fl_typed} = 0,\n"
         f"    \"Functional location \" & {ACTIVE_ROW}.FunctionalLocation & "
         f"\" belongs to another plant. Search for one in \" & {FL_PLANT_PREFIX} & \".\",\n"
         f"    {FL_WRONG_PLANT_MSG}\n)"),
        size=12, color=C_WARN_FG, height=32, wrap="true",
        visible=f"({fl_wrong}) || ({fl_conflict})")
    flTooShort = text_ctrl(
        "txtVhpFlTooShort",
        f'"Enter at least {FL_MIN_LEN} characters to search."',
        size=12, color=C_WARN_FG, height=18, wrap="false",
        visible=(f"!{FL_BUSY_VAR} && {fl_typed} > 0 && {fl_query_len} < {FL_MIN_LEN} && "
                 f"!({fl_wrong})"))

    # Soegningens status UNDER feltet - som i Materials (issue #72): "6
    # Functional Locations found for SSV13 HFC10AJ010. Select one from the
    # list below.", soeger, ingen traef, fejl. Aldrig inde i listen.
    flMsg = text_ctrl("txtVhpFlMsg", "varVhpFlMsg", size=12, color=C_MUTED,
                      height=18, wrap="false", visible="!IsBlank(varVhpFlMsg)")

    # OBJECT LIST ER EN POPUP (issue #54). Knappen staar lige under
    # comboboksen og aabner popup'en med en KLADDE af det valgte. Lukkes
    # popup'en uden "Use selected", er intet aendret. Se
    # build_object_list_modal nedenfor.
    #
    # Issue #63: ingen hjaelpe- eller statustekst under knappen. Antallet
    # staar i knappen - "Object List (3)" - og de valgte vises ved hover
    # (Tooltip). Issue #454: tallet i knappen er nu soegningens antal
    # resultater - det samme som beskeden under feltet. Er der intet at
    # vaelge og intet valgt, er den deaktiveret.
    # Bredden er regnet af den bredeste tekst, den kan faa.
    flBlock = group("conVhpItemFlBlock",
                    [flLabelRow, flHint, flPicker, flWrongPlant, flTooShort, flMsg],
                    direction="Vertical", gap=6, width=FL_W, fill_portions=0,
                    align_in_container="Start")

    # Arbejdscentrene til det valgte vaerk (Plant i Plan Header). Upper paa
    # begge sider, saa "asv" og "ASV" er det samme vaerk. Er der ikke valgt
    # vaerk endnu, vises de alle - en tom dropdown uden forklaring er vaerre
    # end en lang. Issue #453: vaerket, som det STAAR i Plan Header (VhpPlant)
    # - ogsaa foer Save. colVhpMainWorkCenters er indlaest, saa filteret er
    # lokalt (ingen delegering).
    MWC_ITEMS = ("Sort(\n"
                 "    If(\n"
                 f"        IsBlank({st.PLANT}),\n"
                 "        colVhpMainWorkCenters,\n"
                 f"        Filter(colVhpMainWorkCenters, Upper(Plant) = Upper({st.PLANT}))\n"
                 "    ),\n"
                 "    Value\n"
                 ")")
    # Default slaar op i den FILTREREDE liste: et arbejdscenter fra et andet
    # vaerk vises som tomt i stedet for som et gyldigt valg.
    drpMwc = themed_dropdown("drpVhpItemMainWorkCenter", MWC_ITEMS,
                      f"LookUp({MWC_ITEMS}, Value = LookUp(colVhpItems, ItemId = varVhpActiveItemId).MainWorkCenter).Value",
                      # Arbejdscenter fra et andet vaerk (issue #453): feltet
                      # staar tomt og roedt med det samme - ikke foerst efter Save.
                      required_formula=f"({REQ_ITEM} || {ACTIVE_MWC_CONFLICT})",
                      display_mode=DM_ITEM)
    drpAct = themed_dropdown("drpVhpItemActivityType", "colVhpActivityTypeOptions",
                      "LookUp(colVhpActivityTypeOptions, Value = LookUp(colVhpItems, ItemId = varVhpActiveItemId).ActivityType).Value",
                      required_formula=REQ_ITEM, display_mode=DM_ITEM)
    # Hvert felt skriver sin vaerdi paa itemet, naar det aendres eller
    # forlades (issue #448, write_item) - saa "N to fix" og Submit foelger
    # med uden Save.
    drpMwc.props["OnChange"] = write_choice("drpVhpItemMainWorkCenter", "MainWorkCenter")
    drpAct.props["OnChange"] = write_choice("drpVhpItemActivityType", "ActivityType")
    txtShort = text_input("inpVhpItemShortText",
                          "LookUp(colVhpItems, ItemId = varVhpActiveItemId).ShortText", max_length=40,
                          required_formula=REQ_ITEM, display_mode=DM_ITEM, onchange=WRITE_SHORT)
    # REVISION (issue #54, #141). SharePoint-kolonnen RevisionMark har eet
    # valg - "REV - General Revision Mark" - saa feltet er et ja/nej: Yes =
    # det ene valg, No = tomt; vaerdien, der gemmes, er den samme som foer.
    # Issue #141: et segmenteret valg [ No | Yes ] i stedet for kontakten,
    # saa begge muligheder kan ses (build_helpers.segmented).
    REV_TIP = '"Revision: outage work (" & First(colVhpRevisionOptions).Value & ")"'
    segRevision = segmented("conVhpItemRevisionSeg", [
        ("No", "No", f"!{REV_ON}",
         "Set(varVhpItemRevPick, false);\n" + write_item('{ Revision: "" }'), REV_TIP),
        ("Yes", "Yes", REV_ON,
         "Set(varVhpItemRevPick, true);\n"
         + write_item("{ Revision: First(colVhpRevisionOptions).Value }"), REV_TIP),
    ], display_mode=DM_ITEM, label="Revision")
    # "Orsted Responsible" er fjernet (issue #54) - Initials er nok.
    # Kolonnen OrstedResponsible paa itemet bliver staaende: Save skriver
    # stadig indsenderen som ansvarlig i SharePoint (build_save.py), og en
    # gemt plan laeser den tilbage (build_load.py).
    txtInitials = text_input("inpVhpItemInitials",
                             "Upper(LookUp(colVhpItems, ItemId = varVhpActiveItemId).Initials)",
                             max_length=5, required_formula=REQ_ITEM, display_mode=DM_ITEM,
                             onchange=(WRITE_INITIALS + ";\n"
                                       "If(inpVhpItemInitials.Text <> Upper(Trim(inpVhpItemInitials.Text)), "
                                       "Reset(inpVhpItemInitials))"))
    txtInitials.props["BorderColor"] = border_rule("Len(Trim(Self.Text)) <> 5", REQ_ITEM)
    txtInitials.props["ValidationState"] = (f"If({REQ_ITEM} && Len(Trim(Self.Text)) <> 5, "
                                            "ValidationState.Error, ValidationState.None)")
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
        display_mode=f"If(IsBlank(varVhpActiveItemId) || (varVhpViewOnly && !({HAS_LT})), "
                     "DisplayMode.Disabled, DisplayMode.Edit)", icon="DocumentText",
        accessible=(f'If({HAS_LT}, "Edit long text for item ", "Add long text for item ") '
                    "& Text(varVhpActiveItemId)"))
    btnLongText.props["AlignInContainer"] = "AlignInContainer.Start"
    btnLongText.props["Tooltip"] = (
        f"If({HAS_LT}, If(Len({LT}) > {LT_TIP}, Left({LT}, {LT_TIP}) & "
        "\"... (open to read all)\", " + LT + "), \"No long text yet\")")
    mark_done(btnLongText, HAS_LT)

    # NON FLOW USER STATUS (issue #112, #141). Valgfri. Et segmenteret valg
    # [ None | ZBOW ]: None gemmer tom vaerdi (det, "(none)" gjorde), ZBOW
    # gemmer SAP-koden. Har itemet en ANDEN, historisk kode, er ingen af
    # dem valgt; koden vises under valget og gemmes uaendret, til brugeren
    # selv vaelger None eller ZBOW (NF_VAL).
    NF_DESC = ("Coalesce(LookUp(colVhpNonFlowStatusOptions, Value = " + NF_ZBOW + ").Display, "
               + NF_ZBOW + ")")
    segNonFlow = segmented("conVhpItemNonFlowSeg", [
        ("None", "None", f"Len({NF_VAL}) = 0",
         'Set(varVhpItemNfPick, { Value: "" });\n' + write_item('{ NonFlowUserStatus: "" }'),
         '"No non flow user status"'),
        ("Zbow", "ZBOW", f"{NF_VAL} = {NF_ZBOW}",
         "Set(varVhpItemNfPick, { Value: " + NF_ZBOW + " });\n"
         + write_item("{ NonFlowUserStatus: " + NF_ZBOW + " }"),
         NF_DESC),
    ], display_mode=DM_ITEM, label="Non-flow user status")
    NF_OTHER = f"(Len({NF_VAL}) > 0 && {NF_VAL} <> {NF_ZBOW})"
    nfOther = text_ctrl(
        "txtVhpItemNonFlowOther",
        ('"Saved status: " & Coalesce(LookUp(colVhpNonFlowStatusOptions, Value = '
         f'{NF_VAL}).Display, {NF_VAL}) & ". Kept until you choose None or ZBOW."'),
        size=12, color=C_MUTED, height=32, wrap="true", visible=NF_OTHER)
    nfBlock = group("conVhpItemNonFlowBlock", [segNonFlow, nfOther], direction="Vertical",
                    gap=4)

    # KOLONNE-ORDEN (issue #54, #72): oppefra og ned i kolonne 1, saa
    # kolonne 2 - og Functional Location i fuld bredde under dem.
    #
    #     +------------------------------+------------------------------+
    #     | Item Short Text              | Revision                     |
    #     | Main Work Center             | Initials                     |
    #     | Activity Type                | Item Long Text               |
    #     +------------------------------+------------------------------+
    #     | Functional Location  [combobox ][Search] | Non Flow User      |
    #     | 6 Functional Locations found for ...     | Status (#112)      |
    #     | [Object List (3)]                        |                    |
    #     +----------------------------------------+--------------------+
    #
    # Functional Location fylder to af de tre kolonner (FL_W); Non Flow User
    # Status staar i den tredje kolonnes ledige plads ved siden af. Under
    # braekpunktet stables de - Functional Location foerst.
    CW = EDITOR_CW

    def cell(name, label, ctrl, hint, required=False):
        return field_cell(name, label, ctrl, required=required, width=EDITOR_COL_W,
                          container_w=CW, fill_portions_formula="0",
                          hint_text=bh.hint(hint), hints_on=bh.HINTS_ON)

    fieldsGrid = column_grid("conVhpItemFieldsGrid", [
        [cell("conVhpCellItemShortText", "Item short text", txtShort, "ItemShortText", True),
         cell("conVhpCellItemMwc", "Main work center", drpMwc, "MainWorkCenter", True)],
        [cell("conVhpCellItemLongText", "Item long text", btnLongText, "ItemLongText"),
         cell("conVhpCellItemAct", "Maintenance activity type", drpAct, "ActivityType", True)],
        [cell("conVhpCellItemRevision", "Revision", segRevision, "Revision"),
         cell("conVhpCellItemInitials", "Initials", txtInitials, "Initials", True)],
    ], container_w=CW, row_gap=12)
    # Samme celle som de andre felter, i tredje kolonnes bredde.
    nfCell = cell("conVhpCellItemNonFlow", "Non-flow user status", nfBlock,
                  "NonFlowUserStatus")
    flRow = row_n("conVhpItemFlRow", [flBlock, nfCell], container_w=CW)

    # Hvert udfald siger det HOEJT. Knappen skrev foer kun i
    # varVhpRuntimeInfo, som stod i hero-kortet oeverst paa skaermen - var
    # man scrollet ned til Item Editoren, kan man ikke se den, og saa ser et
    # klik ud som om der ikke skete noget. Notify staar oven paa skaermen,
    # uanset hvor man er.
    #
    # Den tredje besked er en faelde, der ellers ikke kunne ses: rammer
    # UpdateIf ingen raekke, goer den ingenting og siger heller ingenting.
    #
    # SAVE/EDIT (issue #433), som Plan header: Save (foer Done) siger
    # "Saving..." mens den gemmer, og laaser sektionen, naar itemet er
    # gemt som valid - knappen hedder saa Edit, og Edit laaser op igen.
    # Fejler valideringen eller gemningen, er felterne stadig aabne.
    # Laasen er colVhpSectionLocks (pr. item); trinene laeser stadig
    # itemets Status, saa progressen er den samme som foer.
    save_fx = (
            "Set(varVhpItemValidated, true);\n"
            "    If(\n"
            "        IsBlank(Trim(inpVhpItemShortText.Text)) || Len(Trim(inpVhpItemShortText.Text)) > 40 ||\n"
            "        IsBlank(drpVhpItemMainWorkCenter.Selected.Value) ||\n"
            "        IsBlank(drpVhpItemActivityType.Selected.Value) ||\n"
            "        Len(Trim(inpVhpItemInitials.Text)) <> 5 ||\n"
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
            f"                    Revision: If({REV_ON}, First(colVhpRevisionOptions).Value, \"\"),\n"
            "                    Initials: Upper(Trim(inpVhpItemInitials.Text)),\n"
            f"                    NonFlowUserStatus: {NF_VAL},\n"

            "                    Status: \"valid\"\n"
            "                }\n"
            "            )\n"
            "        );\n"
            "        If(\n"
            "            CountRows(Filter(colVhpItems, ItemId = varVhpActiveItemId)) = 0,\n"
            f"            {act_mark(ACT, 'item', ok=False)};\n"
            "            Notify(\n"
            "                \"Item \" & Text(varVhpActiveItemId) & \" is not in the list - nothing was changed.\",\n"
            "                NotificationType.Error\n"
            "            ),\n"
            # Issue #158: itemet har nu en Functional Location - vaelg den
            # foerste tasklist, hvis det ikke allerede har et gyldigt valg.
            f"            {AUTO_SELECT_TL};\n"
            # Gemt: sektionen laases (issue #433). Ingen besked om Save
            # draft - Edit-knappen og de graa felter er svaret.
            "            Collect(colVhpSectionLocks, { ItemId: varVhpActiveItemId, Section: \"Item\" });\n"
            # Det gemte er nu det, Reset laegger tilbage (issue #448).
            f"            {SNAP_ITEM_BASE};\n"
            f"            {act_mark(ACT, 'item')}\n"
            "        )\n"
            "    )"
    )
    btnSaveItem = button(
        "btnVhpSaveItem", f'If({ITEM_LOCKED}, "Edit", "Save")',
        (
            "If(\n"
            "    IsBlank(varVhpActiveItemId),\n"
            "    Notify(\"Select or add an item first.\", NotificationType.Warning),\n"
            f"    {ITEM_LOCKED},\n"
            "    RemoveIf(colVhpSectionLocks, ItemId = varVhpActiveItemId && Section = \"Item\"),\n"
            "\n"
            + act_fx(ACT, "item", save_fx) + "\n"
            ")"
        ), primary=True, width=110, icon=f'If({ITEM_LOCKED}, "Edit", "Checkmark")',
        display_mode=DM_ITEM)
    btnSaveItem.props["AccessibleLabel"] = (f'If({ITEM_LOCKED}, "Edit item ", "Save item ") & '
                                            'Text(varVhpActiveItemId)')
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
            # Issue #448: felterne staar allerede paa itemet (write_item),
            # saa itemet laegges foerst tilbage til kopien fra, da det blev
            # aabnet eller gemt (varVhpItemBase).
            f"If(\n    !IsBlank(varVhpActiveItemId) && {ITEM_BASE}.ItemId = varVhpActiveItemId,\n"
            "    UpdateIf(\n        colVhpItems,\n        ItemId = varVhpActiveItemId,\n"
            "        { " + ", ".join(f"{c}: {ITEM_BASE}.{c}" for c in EDITOR_COLUMNS) + " }\n"
            "    )\n);\n"
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
            "Set(varVhpFlMsg, \"\");\n"
            f"{SEED_FL_PICKER};\n"
            f"{RESET_EDITOR_CONTROLS}"
        ), width=fit_button_width("\"Reset\""), height=36,
        display_mode=DM_ITEM)
    btnSaveItem.props["Width"] = str(ITEM_SAVE_W)
    act_button(btnSaveItem, ACT, "item", text="Saving...", grow=False)

    # ALTID FOLDET UD (issue #192): felterne, Functional Location og
    # hjaelpepanelet staar der altid. Foden siger, hvad der mangler, foer
    # itemet er gemt som gyldigt.
    # Issue #448: regnet af itemets aktuelle vaerdier - ikke af Status fra
    # sidste Save.
    attention = text_ctrl(
        "txtVhpItemAttention",
        f'With({{ miss: {ACTIVE_MISSING}, other: {ACTIVE_CONFLICTS} }}, '
        'If(!IsBlank(miss), "Fill in " & miss & ".", '
        # Issue #453: felter fra et andet vaerk staar her med det samme.
        f'!IsBlank(other), other & " does not belong to plant " & {st.PLANT} & " - choose one for that plant.", '
        '"Item is valid."))',
        size=12, height=36, wrap="true",
        visible="(!IsBlank(varVhpActiveItemId) && !varVhpViewOnly)",
        extra={"Color": (f'If(({REQ_ITEM} && !IsBlank({ACTIVE_MISSING})) || '
                          f'!IsBlank({ACTIVE_CONFLICTS}), {C_INVALID_FG}, {C_MUTED})'),
               "VerticalAlign": "VerticalAlign.Middle"})
    footerInfo = group("conVhpItemFooterInfo", [attention], direction="Vertical", gap=0,
                       justify="Center", visible=attention.vis)
    footer = section_footer("conVhpEditorFooter", footerInfo, [btnResetItem, btnSaveItem], EDITOR_CW)
    # GEMT = SKRIVEBESKYTTET (issue #433): felterne, Functional Location,
    # Object list og Reset laases, som i View mode, til der trykkes Edit.
    lock_section([fieldsGrid, flRow, footer], "varVhpViewOnly", ITEM_LOCKED,
                 keep={"btnVhpSaveItem"})

    # The card stretches to the height of the items list; SpaceBetween keeps
    # Reset and Save at the bottom edge when the editor card is taller.
    body = group("conVhpEditorBody", [header, helpPanel, fieldsGrid, flRow],
                 direction="Vertical", gap=14)
    editor = card("conVhpEditorCard", [body, footer])
    editor.props["LayoutJustifyContent"] = "LayoutJustifyContent.SpaceBetween"
    return editor


# Save-knappens bredde i Item Editoren.
# Bredt nok til "Saving..." (issue #433), saa foden staar stille.
ITEM_SAVE_W = fit_button_width("\"Saving...\"", min_w=96) + ICON_W


# Object list-popuppens bredde (maks 640, aldrig bredere end skaermen minus
# 20 px i hver side), dens polstring og pladsen inden i den. Listen tager
# hele den indre bredde (issue #385).
OBJ_MODAL_W = "Min(640, App.Width - 40)"
OBJ_MODAL_PAD = 18
OBJ_LIST_W = f"({OBJ_MODAL_W}) - {2 * OBJ_MODAL_PAD}"


def build_object_list_modal():
    """Object list som popup (issue #54).

    Samme konstruktion som tasklist-pickeren (build_modal.py): en container
    oven paa skaermen med sloeret bagved, centreret, med titel, luk-knap og
    en liste, der selv scroller - siden bagved staar stille.

    Listen er den samme som foer - galleri med ModernCheckbox, filtreret paa
    den valgte Functional Location - men krydserne skrives i en KLADDE,
    colVhpObjDraft. Foerst "Use selected" skriver dem paa itemet. Close
    (eneste luk, issue #237) lukker uden at aendre noget."""
    title = text_ctrl("txtVhpObjListTitle", "\"Object list\"", size=lay.SIZE_CARD_TITLE, weight="Semibold",
                      height=26, wrap="false")
    # X oeverst til hoejre (issue #343).
    headRow = popup_head("conVhpObjListHeadRow", title, "btnVhpObjListClose",
                         "Set(varVhpObjListOpen, false); Clear(colVhpObjDraft)",
                         accessible="\"Close object list without changes\"")

    # View (issue #406): popup'en viser kun itemets valgte objekter og
    # siger, at den er skrivebeskyttet.
    under = text_ctrl(
        "txtVhpObjListFl",
        f"If(IsBlank({SEL_FL}), \"No functional location selected.\", "
        f"varVhpViewOnly, \"Objects linked under \" & {SEL_FL} & \" - read-only.\", "
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
    chkObj.props["DisplayMode"] = "If(varVhpViewOnly, DisplayMode.View, DisplayMode.Edit)"
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
            "Height": f"Min({OBJ_ROWS * (OBJ_ROW_H + 2)}, Max(96, App.Height - 260))",
            "Items": OBJ_ROWS_FX,
            "LayoutMinWidth": "0",
            "LoadingSpinner": "LoadingSpinner.None",
            "Selectable": "false",
            "ShowScrollbar": "true",
            "TabIndex": "0",
            "TemplatePadding": "2",
            "TemplateSize": str(OBJ_ROW_H),
            # Issue #385: listens bredde er popuppens INDRE bredde - samme
            # udtryk som popuppens Width minus dens polstring - og ikke
            # Parent.Width. Med Parent.Width var bredden et gaet for
            # gen_screen, der derfor trak GALLERY_RESERVE (40 px) fra
            # raekken: den blaa baggrund stoppede 40 px foer listens kant,
            # og teksten blev klippet tilsvarende tidligt. Nu er listen,
            # raekken (Parent.TemplateWidth) og teksten (resten af raekken)
            # regnet af een og samme responsive bredde.
            "Width": OBJ_LIST_W,
            "AlignInContainer": "AlignInContainer.Start",
            "WrapCount": "1",
        },
        children=[objRowTpl], h=OBJ_ROWS * (OBJ_ROW_H + 2))

    objEmpty = text_ctrl(
        "txtVhpObjEmpty",
        (
            "If(\n"
            "    varVhpViewOnly,\n"
            "    \"No objects are linked to this item.\",\n"
            f"    IsBlank({SEL_FL}),\n"
            "    \"Choose a functional location first.\",\n"
            "    \"No results found. Search more broadly in the functional location field.\"\n"
            ")"
        ), size=12, color=C_MUTED, height=32, wrap="true",
        # Tom kun, naar der hverken er kandidater eller gemte valg (#102) -
        # i View kun, naar itemet ingen valgte objekter har (issue #406).
        visible=(f"IfError((varVhpViewOnly || CountRows({OBJ_CANDIDATES}) = 0) && "
                 f"CountRows({OBJ_CHOSEN}) = 0, true)"))

    info = text_ctrl("txtVhpObjListInfo",
                     "Text(CountRows(colVhpObjDraft)) & \" selected\"",
                     size=12, color=C_MUTED, height=18, wrap="false")
    grow(info)
    # Cancel er fjernet (issue #237): Close oeverst til hoejre er popuppens
    # eneste luk og kasserer kladden, som Cancel gjorde.
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
        ), primary=True, width=fit_button_width("\"Use selected\""), height=36,
        # Skjult i View (issue #406) - popup'en er kun til at se objekterne.
        display_mode=VIEW_LOCK, visible="!varVhpViewOnly")
    footer = group("conVhpObjListFooter", [info, btnUse], direction="Horizontal",
                   gap=8, height=36, align_items="Center")

    # Maks 640 bred og aldrig bredere end skaermen minus 20 px i hver side.
    modal = group(
        "conVhpObjListModal", [headRow, under, galObj, objEmpty, footer], direction="Vertical",
        gap=12, fill=C_MODAL_BG, border_color=C_PRIMARY_SOFT, radius=lay.RADIUS_MODAL,
        pad=(OBJ_MODAL_PAD,) * 4, width=OBJ_MODAL_W, drop_shadow="ExtraBold",
        visible="varVhpObjListOpen")
    modal.props["X"] = "(App.Width - Self.Width) / 2"
    modal.props["Y"] = "Max(20, (App.Height - Self.Height) / 3)"
    # Et gemt item (issue #433) viser sine objekter skrivebeskyttet, som i View.
    lock_section([modal], "varVhpViewOnly", ITEM_LOCKED)
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
