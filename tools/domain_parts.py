# -*- coding: utf-8 -*-
"""
BYGGEKLODSER til en indmeldings-app. Delt af Equipments og Materials.

DE TO APPS ER IKKE LAENGERE DEN SAMME APP
-----------------------------------------
De var det. Filen her hed build_domain.py, de to build-mapper indeholdt
ordret de samme filer, og tools/build_all.py NAEGTEDE at bygge, hvis de
gled fra hinanden. Kun domain_config.py maatte vaere forskellig.

Det holdt, saa laenge de to kun havde forskellige FELTER. Det gaelder ikke
laengere: de skal kunne to forskellige ting.

Derfor er den her fil ikke "domaeneappen" mere - den er de DELE, en
indmeldings-app er bygget af, og hver app komponerer selv:

    tools/domain_parts.py           delene - bar, formular, dokumenter,
                                    raekketabel, indsend, og Power Fx'en
                                    bag gem/hent/slet
    <App>/build/domain_config.py    felterne og listen
    <App>/build/assemble_screen.py  KOMPOSITIONEN - appens egen
    <App>/build/generate_app_onstart.py  samlingsskemaet - appens eget

De to sidste MAA nu vaere forskellige. Der er ingen vagt, der kraever at
de er ens, og det er med vilje.

HVORDAN EN APP AFVIGER
----------------------
1. Komponer anderledes: lad appens assemble_screen.py kalde andre dele,
   i en anden raekkefoelge, eller udelade en.
2. Erstat en del: skriv funktionen i appens EGEN build-mappe og kald den
   i stedet. Delene herunder kalder ikke hinanden paa kryds - de
   returnerer kontroller, som assembleren saetter sammen.
3. Er en aendring rigtig for BEGGE apps, hoerer den her. Er den kun rigtig
   for den ene, hoerer den i appens egen mappe. Den skelnen er hele
   grunden til, at filen ligger i tools/ og ikke er kopieret.

Delene laeser appens domain_config via "import domain_config as cfg".
Det virker, fordi appens build-mappe staar FOERST paa sys.path - hver app
faar sin egen.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from gen_screen import (Ctrl, SHELL_W, FONT,
                        C_APP_BG, C_CARD_BG, C_CARD_BORDER, C_TITLE, C_MUTED,
                        C_PRIMARY, C_WHITE, C_TRANSPARENT, C_DIVIDER,
                        C_NEUTRAL_BG, C_INFO_FG, C_INFO_BG,
                        C_VALID_FG, C_VALID_BG,
                        C_MODAL_BG, C_PRIMARY_SOFT, C_OVERLAY)
from design_tokens import theme_query
from layout_tokens import below, if_below, fits
from build_helpers import (text_ctrl, group, button, button_row, text_input, theme_button,
                           date_picker,
                           number_input, dropdown, card, field_cell, row_n,
                           label_row, pin_widths, badge, top_bar, grow)
from layout_tokens import SCROLLBAR_W, GALLERY_RESERVE
import domain_config as cfg
import attflows

# Flowkontrakten staar i tools/attflows.py; ruden her er dens
# domaeneudgave - samme tre flows, egne samlingsnavne.
att = attflows.DomainPane()
import build_flsearch as fl

# Raekkens felter i een flad liste - raekkefoelgen er sektionernes.
FIELDS = [f for _sec, fields in cfg.SECTIONS for f in fields]

ROW_H = 44
GAL_ROWS = 8

# Den aktive raekke i samlingen. Blank betyder "ny raekke".
ACTIVE = "LookUp(colDomRows, RowId = varDomActiveRowId)"

# BREDDERNE SKAL PASSE TIL DET KORT, FELTERNE FAKTISK STAAR I
#
# Her stod EDITOR_W - og den er SHELL_W minus en skinne paa 380, fra
# dengang formularen havde dokumentruden ved siden af sig. Skinnen er
# vaek, kortet fylder hele bredden, og saa regnede hver eneste celle med
# 380 pixels, den ikke havde. Resultatet var fire kolonner, der laa
# spredt ud over raekken med huller imellem sig - en labelrad hoejere
# oppe end den foerste, og inputfelter, man ikke kunne finde.
#
# Kortets padding er 18 i hver side; det er de 36.
FORM_W = f"({SHELL_W} - 36)"

# DOKUMENTERNE OG DETALJERNE ER POPUPS
# ------------------------------------
# De stod som kort paa skaermen: listen i den ene halvdel, dokumentruden i
# den anden og detaljerne under listen. Listen har syv kolonner og fem
# knapper - i en halv skaerm var der ikke plads; dokumentruden hoerte til
# den raekke, der laa i FORMULAREN; og detaljekortet skubbede alt ned.
#
# Konstruktionen er VH-plan-appens (build_modal.py): samme fill, kant, X/Y
# og baggrundssloer. Bredden er hoejst 820/760 og ellers skaermen minus
# 32, saa en popup aldrig gaar ud over kanten.
DETAILS_W = "Min(820, App.Width - 32)"
DOCS_W = "Min(760, App.Width - 32)"
DOCS_INNER_W = f"({DOCS_W}) - 36"
MODAL_X = "(App.Width - Self.Width) / 2"
MODAL_Y = "Max(20, (App.Height - Self.Height) / 3)"

# Indsendte raekker kan ikke redigeres - saa ejer SAP-processen dem.
DM_ROW = ('If(varDomRowStatus = "submitted", DisplayMode.View, DisplayMode.Edit)')

# HVORNAAR BLIVER EN FELTKANT ROED?
#
# Her stod "true": kanten var roed fra det oejeblik feltet var tomt -
# altsaa fra appen aabnede, foer brugeren havde roert noget. VH-plan gjorde
# det modsatte og ventede til brugeren trykkede Validér.
#
# To apps i samme familie sagde dermed to forskellige ting med den samme
# farve. Og "roed fra foerste sekund" er den af de to, der skader: den
# laerer brugeren at se bort fra roedt, og saa er farven ingenting vaerd,
# naar den endelig betyder noget.
#
# varDomValidated saettes, naar brugeren TRYKKER Gem eller Indsend - det
# er appens "jeg har tjekket". Den nulstilles, naar formularen ryddes
# eller en anden raekke hentes, for saa er det en ny formular.
REQUIRED = "varDomValidated"

# Topbjaelken regnes af build_helpers.top_bar() - af de kontroller, der
# faktisk staar i den. Her stod foer en haandskrevet tabel (BAR_RIGHT), et
# gap, en slack, en mindste titelbredde og en vagt, der skulle holde dem i
# trit. Den holdt dem i trit med hinanden - men ikke med scrollbaren, og
# derfor forsvandt hoejresiden. Se RAMMEN i tools/layout_tokens.py.
# Dokumentpopuppens knapper haenger paa DEN raekke, popuppen er aabnet for.
DM_DOCS = ('If(IsBlank(varDomDocsId), DisplayMode.Disabled, DisplayMode.Edit)')
DM_SEL = ('If(IsBlank(varDomActiveRowId), DisplayMode.Disabled, DisplayMode.Edit)')


# ---------------------------------------------------------------------------
# Den flade top
# ---------------------------------------------------------------------------
def build_bar():
    """Toplinjen. Den staar i rammens header (build_helpers.app_frame), saa
    den scroller aldrig vaek, og dens hoejde afhaenger kun af App.Width.

    Alt om bredderne - hvornaar den stables, og hvor meget titlen faar -
    regnes af top_bar() ud af de fire kontroller herunder. Tidligere stod
    det som fem konstanter og en vagt; de passede sammen, men ikke med den
    bredde, platformen faktisk gav, naar der var en scrollbar."""
    count = badge("txtDomCount", '"Rows: " & CountRows(colDomRows)', width=110)
    no = text_ctrl("txtDomReqNo",
                   'If(IsBlank(varDomRequestNo), "Not submitted", varDomRequestNo)',
                   size=15, weight="Semibold", height=24, width=150, wrap="false")
    # Temaet med TILBAGE til hubben. Uden det skiftede hubben farve,
    # fordi brugeren gik retur - lageret er isoleret pr. app-id.
    back = button("btnDomBack", '"To the hub"',
                  f'Launch("{cfg.HUB_URL}" & {theme_query("?")}, {{ }}, '
                  f'LaunchTarget.Replace)',
                  width=140)
    theme = theme_button("btnDomTheme")
    return top_bar("Dom", f'"{cfg.TITLE}"', f'"{cfg.SUBTITLE}"',
                   [count, no, theme, back],
                   narrow_hide=("txtDomCount", "txtDomReqNo"))


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
        #
        # Selve kontrollen stod foer bygget i haanden HER, med en fast
        # graa kant og uden Fill - altsaa uden baade validerings- og
        # graatonefarven, alle andre felter har. Den ligger nu i
        # build_helpers sammen med de fire andre og deler deres regel.
        return date_picker(name, v, display_mode=DM_ROW,
                           onchange=f"Set({v}, Self.SelectedDate)")
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
        # Default er en RECORD fra Items - ikke vaerdien inde i den.
        items = "[" + ", ".join(f'"{x}"' for x in choices) + "]"
        c = dropdown(name, items, f"LookUp({items}, Value = {v})",
                     display_mode=DM_ROW)
        c.props["OnChange"] = f"Set({v}, Self.Selected.Value)"
        return c
    c = text_input(name, v, max_length=255, display_mode=DM_ROW,
                   onchange=f"Set({v}, Self.Text)")
    return c


COLS_PER_ROW = 4


def _plant_dropdown():
    """Vaerkfeltet.

    TO fejl sad her, og de laa oven i hinanden:

    1. Default var "varDomFPlant" - en STRENG. En ModernDropdown vil have
       en RECORD fra sin egen Items-tabel, ikke vaerdien inde i den.
       Compile svarede: [Control 'drpDomPlant', Property 'Default']
       Expected a valid input matching Items.

    2. Der var slet ingen OnChange. Variablen blev altsaa aldrig sat, og
       da Gem kraever den udfyldt, kunne der ALDRIG gemmes - en fejl,
       compile ikke kan se, fordi formlen i sig selv er gyldig."""
    c = dropdown("drpDomPlant", "colDomPlants",
                 "LookUp(colDomPlants, Value = varDomFPlant)",
                 required_formula=REQUIRED, display_mode=DM_ROW)
    c.props["OnChange"] = "Set(varDomFPlant, Self.Selected.Value)"
    return c


def build_fl_block():
    """Functional Location - soegefelt, soegeknap og dropdown.

    Praecis VH-plan-appens konstruktion, kopieret i build_flsearch.py.
    Der er INGEN skjult filtrering: et tekstfelt siger HVAD der soeges, en
    knap siger HVORNAAR, og dropdownen viser praecis det, samlingen
    indeholder. Den foerste udgave i VH-plan brugte en combobox med
    indbygget soegning - den fik 819 raekker og viste nul."""
    q = text_input("txtDomFlQuery", '""',
                   placeholder=f'"At least {fl.MIN_SEARCH_LEN} characters - e.g. SSV10 KAB10"',
                   display_mode=DM_ROW, label="\"Search functional location\"")
    grow(q)
    btn = button("btnDomFlSearch", '"Search"',
                 fl.search_action("txtDomFlQuery", "colDomFl", "varDomFlMsg"),
                 width=90, display_mode=DM_ROW)
    row = group("conDomFlSearchRow", pin_widths([q, btn]),
                direction="Horizontal", gap=8, height=36, align_items="Center")

    drop = dropdown("drpDomFl", "colDomFl",
                    f"LookUp(colDomFl, Code = {_var(cfg.FL_FIELD)})",
                    item_display="ThisItem.Display", value_field="Code",
                    display_mode=DM_ROW, label="\"Select functional location\"")
    drop.props["OnChange"] = f"Set({_var(cfg.FL_FIELD)}, Self.Selected.Code)"

    chosen = text_ctrl(
        "txtDomFlChosen",
        f'If(IsBlank({_var(cfg.FL_FIELD)}), "None selected", "Selected: " & {_var(cfg.FL_FIELD)})',
        size=12, color=C_MUTED, height=18, wrap="false")
    msg = text_ctrl("txtDomFlMsg", "varDomFlMsg", size=12, color=C_MUTED,
                    height=18, wrap="false")

    return group("conDomFlBlock",
                 [label_row("conDomFlLbl", "Functional location"),
                  row, drop, chosen, msg],
                 direction="Vertical", gap=6, width="Parent.Width")


def build_form():
    head = group("conDomFormHead", [
        text_ctrl("txtDomFormH", '"Row"', size=16, weight="Semibold",
                  height=22, wrap="false"),
        text_ctrl("txtDomFormState",
                  ('If(\n'
                   '    IsBlank(varDomActiveRowId),\n'
                   '    "New row - not saved yet",\n'
                   '    "Editing " & Coalesce(' + ACTIVE + '.ItemKey, "row " & varDomActiveRowId) &\n'
                   '        " (" & varDomRowStatus & ")"\n'
                   ')'),
                  size=13, color=C_MUTED, height=20, wrap="false"),
    ], direction="Vertical", gap=2)

    # FIRE KOLONNER I TOPSEKTIONEN
    #
    # Teksten og vaerket hoerer til foerste sektion - ikke til en raekke for
    # sig. Ved at laegge dem foerst i den, fyldes raekken op til fire med de
    # to foerste af sektionens egne felter, og toppen bliver saa taet som
    # resten af formularen.
    top_cells = [
        field_cell("conDomText", cfg.TEXT_LABEL,
                   text_input("inpDomText", "varDomFText", max_length=40,
                              placeholder=cfg.TEXT_PLACEHOLDER,
                              required_formula=REQUIRED, display_mode=DM_ROW,
                              onchange="Set(varDomFText, Self.Text)"),
                   required=True, container_w=FORM_W, cols=COLS_PER_ROW),
        field_cell("conDomPlant", cfg.PLANT_LABEL, _plant_dropdown(),
                   required=True, container_w=FORM_W, cols=COLS_PER_ROW),
    ]

    kids = [head]
    for s_i, (section, fields) in enumerate(cfg.SECTIONS):
        kids.append(text_ctrl(f"txtDomSec{s_i}", f'"{section}"', size=13,
                              weight="Semibold", color=C_MUTED, height=20,
                              wrap="false"))
        chunk = top_cells if s_i == 0 else []
        top_cells = []
        for f_i, (col, label, kind, choices) in enumerate(fields):
            # FL-feltet er ikke et tekstfelt - det er en soegning, og den
            # fylder sin egen raekke.
            if col == getattr(cfg, "FL_FIELD", None):
                if chunk:
                    kids.append(row_n(f"conDomRow{s_i}_{f_i}", chunk,
                                      container_w=FORM_W))
                    chunk = []
                kids.append(build_fl_block())
                continue
            wide = kind == "long"
            cell = field_cell(f"con{col}", label, _input_for(col, kind, choices),
                              container_w=FORM_W,
                              cols=1 if wide else COLS_PER_ROW,
                              fill_portions_formula="0" if wide else None)
            if wide:
                if chunk:
                    kids.append(row_n(f"conDomRow{s_i}_{f_i}", chunk,
                                      container_w=FORM_W))
                    chunk = []
                kids.append(cell)
                continue
            chunk.append(cell)
            if len(chunk) == COLS_PER_ROW:
                kids.append(row_n(f"conDomRow{s_i}_{f_i}", chunk,
                                  container_w=FORM_W))
                chunk = []
        if chunk:
            kids.append(row_n(f"conDomRow{s_i}_end", chunk, container_w=FORM_W))

    # KLADDE OG FAERDIG ER TO KNAPPER
    #
    # En kladde kraever kun beskrivelsen - listens Title er obligatorisk i
    # SharePoint, saa helt tom kan en raekke ikke vaere. Alt andet maa
    # mangle. "Save" kraever ogsaa vaerket, og det er DEN status, Indsend
    # tager med.
    draft = button("btnDomSaveDraft", '"Save draft"', save_row_fx("draft"),
                   width=150, display_mode=DM_ROW)
    save = button("btnDomSave", '"Save"', save_row_fx("valid"), primary=True,
                  width=130, display_mode=DM_ROW)
    new = button("btnDomNew", '"New row"', clear_form_fx(), width=130)
    delete = button("btnDomDelete", '"Delete row"', delete_row_fx(),
                    danger=True, width=150, display_mode=DM_SEL)
    kids.append(button_row("conDomFormActions",
                           [draft, save, new, delete], FORM_W))
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
             f'Set({REQUIRED}, false);',
             'Set(varDomFText, "");',
             'Set(varDomFPlant, "");']
    for col, _lab, kind, _ch in FIELDS:
        lines.append(f"Set({_var(col)}, {_blank(kind)});")
    lines.append('Set(varDomFlMsg, "");')
    lines.append('Reset(txtDomFlQuery);')
    lines.append('Set(varDomInfo, "New row - fill in and save.")')
    return "\n".join(lines)


def copy_row_fx():
    """Kopier raekken til en NY, ugemt raekke i formularen.

    Den haandskrevne app kopierede til en lokal samling, fordi raekkerne
    dér kun laa i appen. Her ER en raekke en SharePoint-raekke, saa en
    kopi, der blev skrevet med det samme, ville lave en halvfaerdig raekke
    i listen, hver gang nogen kom til at trykke.

    Kopien lander derfor i FORMULAREN med blankt raekke-id: brugeren ser
    den, kan rette i den, og den findes foerst, naar der trykkes Gem.

    Funktionspladsen kopieres MED - modsat VH-plans "Copy item", hvor den
    ryddes. Dér er pointen som regel det samme udstyr et andet sted; her
    er det samme sted med et andet materiale."""
    lines = ['Set(varDomActiveRowId, Blank());',
             'Set(varDomRowStatus, "draft");',
             f'Set({REQUIRED}, false);',
             f'Set(varDomFText, ThisItem.{cfg.C_TEXT});',
             'Set(varDomFPlant, ThisItem.Plant);']
    for col, _lab, _kind, _ch in FIELDS:
        lines.append(f"Set({_var(col)}, ThisItem.{col});")
    # Dokumenterne foelger IKKE med. De ligger i en mappe, der hedder den
    # gamle raekkes noegle, og kopien har ingen noegle endnu.
    lines.append('Set(varDomInfo, "Copied to a new row - not saved yet. '
                 'Documents were not copied.")')
    return "\n".join(lines)


def delete_this_row_fx():
    """Slet DEN raekke, knappen sidder paa - ikke den, der er aaben.

    btnDomDelete i formularen sletter varDomActiveRowId. Her er raekken
    ThisItem, og de to er ikke noedvendigvis den samme: man skal kunne
    slette en raekke i listen uden foerst at aabne den."""
    return (
        f"Remove({cfg.L_ROWS}, LookUp({cfg.L_ROWS}, ID = ThisItem.RowId));\n"
        "RemoveIf(colDomAttachments, RowId = ThisItem.RowId);\n"
        "If(varDomDetailsId = ThisItem.RowId, Set(varDomDetailsId, Blank()));\n"
        "If(varDomDocsId = ThisItem.RowId, Set(varDomDocsId, Blank()));\n"
        "\n"
        "// Var det den aabne raekke, skal formularen ogsaa ryddes - ellers\n"
        "// staar der felter fra noget, der ikke findes.\n"
        "If(\n"
        "    varDomActiveRowId = ThisItem.RowId,\n"
        "    " + clear_form_fx().replace("\n", "\n    ") + "\n"
        ");\n"
        "\n"
        + refresh_rows_fx() + ";\n"
        'Set(varDomInfo, "Row deleted. The documents remain in the library.")'
    )


def load_row_fx():
    """Vaelg en gemt raekke og laeg den i formularen.

    Dokumenterne hentes IKKE her: de ligger i en popup, der aabnes med sin
    egen knap (open_docs_fx), og det er den, der henter dem. Et klik i
    listen koster dermed ingen flow-kald."""
    lines = ['Set(varDomActiveRowId, ThisItem.RowId);',
             'Set(varDomRowStatus, ThisItem.Status);',
             f'Set({REQUIRED}, false);',
             f'Set(varDomFText, ThisItem.{cfg.C_TEXT});',
             'Set(varDomFPlant, ThisItem.Plant);']
    for col, _lab, _kind, _ch in FIELDS:
        lines.append(f"Set({_var(col)}, ThisItem.{col});")
    lines[-1] = lines[-1].rstrip(";")
    return "\n".join(lines)


def open_docs_fx():
    """Raekkens Docs-knap: peg popuppen paa DENNE raekke, og hent mappen,
    hvis raekken har filer, der ikke allerede er hentet.

    Raekkefoelgen er ikke tilfaeldig: att.refresh_fx() laeser varDomDocsId,
    saa den skal saettes foerst - ellers henter flowet forrige raekkes
    mappe."""
    return (
        "Set(varDomDocsId, ThisItem.RowId);\n"
        "If(\n"
        "    ThisItem.FileCount > 0 &&\n"
        "    CountRows(Filter(colDomAttachments, RowId = ThisItem.RowId)) = 0,\n"
        + att.refresh_fx(4) + "\n"
        ")"
    )


def build_backdrop():
    """Sloeret bag popupperne. EEN kontrol til begge - to ville lagre oven
    paa hinanden og goere baggrunden dobbelt saa moerk."""
    return Ctrl("conDomBackdrop", "GroupContainer", variant="AutoLayout",
                props={
                    "BorderStyle": "BorderStyle.None",
                    "DropShadow": "DropShadow.None",
                    "Fill": C_OVERLAY,
                    "Height": "App.Height",
                    "LayoutDirection": "LayoutDirection.Vertical",
                    "LayoutOverflowX": "LayoutOverflow.Hide",
                    "LayoutOverflowY": "LayoutOverflow.Hide",
                    "Visible": "!IsBlank(varDomDetailsId) || !IsBlank(varDomDocsId)",
                    "Width": "App.Width",
                    "X": "0",
                    "Y": "0",
                }, children=[], vis="!IsBlank(varDomDetailsId) || !IsBlank(varDomDocsId)")


def save_row_fx(status="valid"):
    """Gem raekken i SharePoint - som kladde eller som faerdig.

    En KLADDE kraever kun beskrivelsen. Listens Title er obligatorisk, saa
    helt tom kan raekken ikke vaere, men alt andet maa mangle - det er
    hele pointen med en kladde.

    En FAERDIG raekke kraever ogsaa vaerket, og det er den status, Indsend
    tager med.
    """
    patch = [
        f"            {cfg.C_TEXT}: Trim(varDomFText),",
        "            Plant: varDomFPlant,",
    ]
    for col, _lab, kind, _ch in FIELDS:
        patch.append(f"            {col}: {_patch_value(col, kind)},")
    patch += [
        '            RowStatus: { Value: "%s" },' % status,
        "            RequesterEmail: varDomMe,",
        "            RequesterName: User().FullName",
    ]
    key = f'"{cfg.PREFIX}-" & Text(varDomSpRow.ID, "000000")'

    if status == "draft":
        guard = 'IsBlank(Trim(Coalesce(varDomFText, "")))'
        msg = "%s is required - also on a draft." % cfg.TEXT_LABEL
        done = "Draft saved as "
    else:
        guard = ('IsBlank(Trim(Coalesce(varDomFText, ""))) || '
                 "IsBlank(varDomFPlant)")
        msg = "%s and %s are required." % (cfg.TEXT_LABEL, cfg.PLANT_LABEL)
        done = "Saved as "

    return (
        # "Jeg har tjekket" - herfra maa kanterne vaere roede.
        f"Set({REQUIRED}, true);\n"
        "If(\n"
        f"    {guard},\n"
        f'    Notify("{msg}", NotificationType.Warning),\n'
        "\n"
        "    IfError(\n"
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
        "    // raekke og een paa en gammel\n"
        "    If(\n"
        "        IsBlank(varDomSpRow.ItemKey),\n"
        "        Patch(\n"
        f"            {cfg.L_ROWS},\n"
        "            varDomSpRow,\n"
        "            {\n"
        "                RowId: varDomSpRow.ID,\n"
        f"                ItemKey: {key},\n"
        f"                AttachmentFolder: \"{attflows.LIBRARY}/\" & {key}\n"
        "            }\n"
        "        )\n"
        "    );\n"
        "    Set(varDomActiveRowId, varDomSpRow.ID);\n"
        f'    Set(varDomRowStatus, "{status}");\n'
        "\n"
        + refresh_rows_fx(4) + ";\n"
        "\n"
        f'    Set(varDomInfo, "{done}" & ' + ACTIVE + '.ItemKey);\n'
        f'    Notify("{done}" & ' + ACTIVE + '.ItemKey, '
        "NotificationType.Success),\n"
        "\n"
        '    Set(varDomInfo, "Gemning fejlede: " & FirstError.Message);\n'
        '    Notify("Gemning fejlede: " & FirstError.Message, '
        "NotificationType.Error)\n"
        "    )\n"
        ")"
    )


def delete_row_fx():
    """Slet raekken - ogsaa i SharePoint.

    Dokumenterne i biblioteket bliver staaende. Det er med vilje: en
    raekke, der fjernes ved et uheld, maa ikke tage bilagene med sig."""
    return (
        "If(\n"
        "    IsBlank(varDomActiveRowId),\n"
        '    Set(varDomInfo, "Select a row in the list first."),\n'
        "\n"
        f"    Remove({cfg.L_ROWS}, LookUp({cfg.L_ROWS}, ID = varDomActiveRowId));\n"
        "    RemoveIf(colDomAttachments, RowId = varDomActiveRowId);\n"
        "    If(varDomDetailsId = varDomActiveRowId, Set(varDomDetailsId, Blank()));\n"
        "    If(varDomDocsId = varDomActiveRowId, Set(varDomDocsId, Blank()));\n"
        "\n"
        + refresh_rows_fx(4) + ";\n"
        "\n"
        + clear_form_fx().replace("\n", "\n    ").replace(
            'Set(varDomInfo, "New row - fill in and save.")',
            'Set(varDomInfo, "Row deleted. The documents remain in the library.")')
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
    picker = Ctrl(att.picker, "Attachments@2.3.0", props={
        "AccessibleLabel": '"Select documents"',
        "BorderColor": C_CARD_BORDER,
        "BorderThickness": "1",
        "DisplayMode": DM_DOCS,
        "Height": "110",
        "MaxAttachments": "10",
        # 10 MB, ikke 50. App checker advarer ved store filer, og den har
        # ret i mere end den siger: Attachments-kontrollen holder filen i
        # hukommelsen som base64, og flowet sender den videre i samme form.
        # En datablad eller en manual er langt under; 50 MB var et tal, der
        # stod der, fordi det var stort nok - ikke fordi nogen havde valgt det.
        "MaxAttachmentSize": "10",
        "NoAttachmentsText": '"Drag documents here, or browse"',
        "PaddingBottom": "5", "PaddingLeft": "5",
        "PaddingRight": "5", "PaddingTop": "5",
        "Width": "Parent.Width",
    }, h=110)

    up = button("btnDomAttUpload", '"Upload to SharePoint"', att.upload_fx(),
                primary=True, display_mode=DM_DOCS)
    refresh = button("btnDomAttRefresh", '"Refresh documents"',
                     att.refresh_button_fx(), display_mode=DM_DOCS)
    rem = button("btnDomAttRemove", '"Remove document"', att.delete_fx(),
                 danger=True, display_mode=DM_DOCS)
    actions = button_row("conDomAttActions", [up, refresh, rem], DOCS_INNER_W)

    chk = Ctrl("chkDomAttSel", "ModernCheckbox", props={
        "AccessibleLabel": '"Select document"',
        "Default": "ThisItem.Selected",
        "Height": "24",
        "Label": '""',
        "OnCheck": "Patch(colDomAttachments, ThisItem, { Selected: true })",
        "OnUncheck": "Patch(colDomAttachments, ThisItem, { Selected: false })",
        "Width": "30",
    }, h=24)
    name = grow(text_ctrl("txtDomAttName", "ThisItem.FileName", size=13, height=28,
                          wrap="false"))
    # NY fane her, og kun her. Navigation mellem apps bruger Replace, saa
    # der ikke bliver en fane pr. klik - men et dokument er ikke en app.
    # Replace ville smide appen vaek, og en halvudfyldt formular med den.
    link = button("btnDomAttOpen", '"Open"',
                  "Launch(ThisItem.FileUrl, { }, LaunchTarget.New)",
                  width=80, height=30)
    row = group("conDomAttRow", pin_widths([chk, name, link]),
                direction="Horizontal", gap=10,
                height="Parent.TemplateHeight - 2", align_items="Center",
                width="Parent.TemplateWidth")

    # Filnavnet er raekkens noegle - der er INGEN LineId paa dokumenterne.
    # VH-plan-appen sorterede paa en LineId, der ikke fandtes; Items gik i
    # fejl, galleriet stod tomt, og filerne laa i biblioteket hele tiden.
    # Loft paa hoejden: som popup maa den ikke vokse ud over skaermen. Ti
    # raekker, derover scroller galleriet.
    gal_h = f"Min(Max(CountRows({att.scope}), 1) * 34, 340)"
    gal = Ctrl("galDomAttachments", "Gallery", variant="Vertical", props={
        "AccessibleLabel": '"Documents on the selected row"',
        "BorderStyle": "BorderStyle.None",
        "Fill": C_TRANSPARENT,
        "FillPortions": "0",
        "Height": gal_h,
        "Items": f"Sort({att.scope}, FileName)",
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
                      visible=f"IfError(CountRows({att.scope}) = 0, false)")

    title = grow(text_ctrl(
        "txtDomAttH",
        '"Documents - " & Coalesce(LookUp(colDomRows, RowId = varDomDocsId).ItemKey, "")',
        size=17, weight="Semibold", height=26, wrap="false"))
    close = button("btnDomAttClose", '"Close"', "Set(varDomDocsId, Blank())",
                   width=84, height=32)
    head = group("conDomAttHead", [title, close], direction="Horizontal",
                 gap=12, align_items="Center")
    modal = group("conDomAttModal", [head, picker, actions, gal, empty],
                  direction="Vertical", gap=14,
                  fill=C_MODAL_BG, border_color=C_PRIMARY_SOFT, radius=16,
                  pad=(18, 18, 18, 18), width=DOCS_W, drop_shadow="ExtraBold",
                  visible="!IsBlank(varDomDocsId)")
    modal.props["X"] = MODAL_X
    modal.props["Y"] = MODAL_Y
    return modal


# ---------------------------------------------------------------------------
# De gemte raekker
# ---------------------------------------------------------------------------
GAP = 10

# Raekkens fire knapper. Bredden paa handlingskolonnen REGNES af dem, saa
# en femte knap ikke kan goere tabellen bredere end kolonnen uden at
# nogen opdager det. build_rows() efterproever tabellen mod raekken.
# Bredder og hoejde som i den haandbyggede Materials-app, hvor knapperne
# virkede: 30 px hoeje, 13 pt. Her stod 26 px med 14 pt, og knapperne stod
# som tomme kanter i bunden af raekken - under den moderne knaps
# mindstehoejde. check_layout regel 25 kraever nu mindst 30.
ROW_BTN = {"btnDomRowOpen": 60, "btnDomRowDetails": 72, "btnDomRowDocs": 64,
           "btnDomRowCopy": 64, "btnDomRowDelete": 72}
ROW_BTN_H = 30
ROW_BTN_GAP = 4
ACTIONS_W = sum(ROW_BTN.values()) + ROW_BTN_GAP * (len(ROW_BTN) - 1)
# Paa en tablet er der ikke plads til fem knapper OG en laeselig
# beskrivelse. Docs og Copy er de to, man kan undvaere: dokumenterne staar
# ogsaa i detaljeruden, og en kopi kan laves fra den aabne raekke.
ROW_BTN_NARROW = ("btnDomRowDocs", "btnDomRowCopy")
ACTIONS_W_NARROW = (ACTIONS_W - sum(ROW_BTN[b] + ROW_BTN_GAP
                                    for b in ROW_BTN_NARROW))

# Sidste kolonne i LIST_COLS er handlingerne. Bredden staar som 0 i de to
# domain_config.py og regnes HER - ellers skulle det samme tal vedligeholdes
# to steder, og det ene ville blive glemt.
LIST_COLS = [(n, ACTIONS_W if i == len(cfg.LIST_COLS) - 1 else w)
             for i, (n, w) in enumerate(cfg.LIST_COLS)]
LAST_COL = len(LIST_COLS) - 1
FIXED = sum(w for _n, w in LIST_COLS) + GAP * (len(LIST_COLS) - 1)
# Beskrivelseskolonnen tager RESTEN af bredden - men hoejst 460.
#
# Uden loftet aad den alt: paa en bred skaerm blev den over tusind pixels,
# de oevrige kolonner blev skubbet helt ud til hoejre kant, og imellem dem
# laa en tom flade paa halvdelen af vinduet. En tabel skal vaere saa bred
# som sit indhold, ikke som sin beholder.
#
# REGNET AF DEN BREDDE, LISTEN HAR - ikke af Parent.Width.
#
# Her stod "Parent.Width - FIXED". Parent.Width er raekkens Width-EGENSKAB,
# og den trak hverken kortets padding, galleriets TemplatePadding eller dets
# scrollbar fra. Nu regnes den af HALF_W (som er regnet af SHELL_W):
#   kortets padding 2 x 18, TemplatePadding 2 x 2, scrollbar.
# Budgettet for raekkens celler - en NEDRE graense for den bredde,
# galleriet giver skabelonen. GALLERY_RESERVE er luften; se RAMMEN og
# GALLERY_RESERVE i tools/layout_tokens.py.
ROWS_W = f"({SHELL_W} - 36 - 4 - {SCROLLBAR_W} - {GALLERY_RESERVE})"
# De midterste kolonner (nummer, FL/leverandoer, vaerk) skjules, naar der
# ikke er plads til dem OG en laeselig beskrivelse. Ellers blev raekken
# bredere end listen, og knapperne i hoejre side var skubbet ud.
MID_COLS = LIST_COLS[1:1 + len(cfg.LIST_FIELDS)]
FIXED_SMALL = FIXED - sum(w + GAP for _n, w in MID_COLS)
SHOW_MID = f"({ROWS_W}) >= {FIXED} + 150"
# Paa en tablet skjules ogsaa FILES - Docs-knappen viser filerne alligevel.
FILES_COL = LIST_COLS[-2][1] + GAP
# Under den her graense: ingen FILES-kolonne og kun tre knapper.
FIXED_TINY = FIXED_SMALL - FILES_COL - (ACTIONS_W - ACTIONS_W_NARROW)
SHOW_FILES = f"({ROWS_W}) >= {FIXED_SMALL} + 150"
ACT_W = f"If({SHOW_FILES}, {ACTIONS_W}, {ACTIONS_W_NARROW})"
MAIN_W = (f"Max(Min(({ROWS_W}) - If({SHOW_MID}, {FIXED}, "
          f"If({SHOW_FILES}, {FIXED_SMALL}, {FIXED_TINY})), 460), 150)")

SEARCH = " || ".join(
    f"Trim(txtDomSearch.Text) in {c}" for c in cfg.SEARCH_FIELDS)
SCOPE = (
    "Filter(\n"
    "    colDomRows,\n"
    f"    (IsBlank(Trim(txtDomSearch.Text)) || {SEARCH}),\n"
    "    (drpDomStatusFilter.Selected.Value = \"all\" ||\n"
    "     Status = drpDomStatusFilter.Selected.Value)\n"
    ")"
)


def _head_cell(i, label, width):
    w = MAIN_W if width == 0 else (ACT_W if i == LAST_COL else width)
    return text_ctrl(f"txtDomHead{i}", f'"{label}"', size=11, color=C_MUTED,
                     weight="Semibold", height=18, width=w, wrap="false",
                     visible=(SHOW_MID if 1 <= i <= len(cfg.LIST_FIELDS)
                              else SHOW_FILES if i == len(LIST_COLS) - 2 else None))


# ---------------------------------------------------------------------------
# Detaljeruden
#
# Den haandskrevne app havde en modal med alle raekkens felter og
# frem/tilbage mellem raekkerne. Den kom ikke med i builderen (issue #15,
# #16).
#
# Her er den et KORT under listen og ikke en modal. Grunden er praktisk:
# modalen i den gamle app var en HtmlViewer med hele raekken skrevet ind i
# en stylestreng, og den kunne hverken efterregnes af layout-tjekket eller
# laeses af en skaermlaeser. Et kort med rigtige tekstkontroller kan begge
# dele.
# ---------------------------------------------------------------------------
DETAIL_LBL_W = 190
DETAIL_ROW_H = 20


def _detail_row(i, label, value):
    lbl = text_ctrl(f"txtDomDet{i}L", f'"{label}"', size=12, color=C_MUTED,
                    weight="Semibold", height=DETAIL_ROW_H, width=DETAIL_LBL_W,
                    wrap="false")
    val = grow(text_ctrl(f"txtDomDet{i}V", value, size=13, height=DETAIL_ROW_H,
                         wrap="false"))
    return group(f"conDomDet{i}", [lbl, val], direction="Horizontal", gap=12,
                 height=DETAIL_ROW_H, align_items="Center")


def build_details():
    """Alle raekkens felter, med frem og tilbage mellem raekkerne."""
    # Raekken, ruden viser. Den slaas op HVER gang - saa er den altid den,
    # der staar i samlingen, ogsaa efter en Gem.
    row = f"LookUp(colDomRows, RowId = varDomDetailsId)"
    # Positionen i den SORTEREDE og FILTREREDE liste, saa frem/tilbage
    # foelger det, brugeren faktisk ser. Power Fx har ingen IndexOf, men
    # i en faldende sortering er positionen antallet af raekker foran.
    order = f"Sort({SCOPE}, RowId, SortOrder.Descending)"
    pos = f"CountRows(Filter({order}, RowId > varDomDetailsId)) + 1"

    key = text_ctrl("txtDomDetKey",
                    f'Coalesce({row}.ItemKey, "Row " & Text(varDomDetailsId))',
                    size=16, weight="Semibold", height=22, wrap="false")
    where = text_ctrl("txtDomDetPos",
                      f'"{{}} of " & Text(CountRows({order}))'.replace(
                          "{}", '" & Text(%s) & "' % pos),
                      size=12, color=C_MUTED, height=18, wrap="false")
    head_left = grow(group("conDomDetHeadL", [key, where], direction="Vertical",
                           gap=2))

    prev = button("btnDomDetPrev", '"Previous"',
                  f'Set(varDomDetailsId, Index({order}, Max(1, {pos} - 1)).RowId)',
                  width=96, height=30,
                  display_mode=f"If({pos} <= 1, DisplayMode.Disabled, DisplayMode.Edit)")
    nxt = button("btnDomDetNext", '"Next"',
                 f'Set(varDomDetailsId, '
                 f'Index({order}, Min(CountRows({order}), {pos} + 1)).RowId)',
                 width=96, height=30,
                 display_mode=f"If({pos} >= CountRows({order}), "
                              f"DisplayMode.Disabled, DisplayMode.Edit)")
    # Aabner raekken i formularen OG lukker popuppen - formularen staar
    # bagved, saa man ellers ikke kunne se, at der skete noget.
    edit = button("btnDomDetEdit", '"Edit this row"',
                  load_row_fx().replace("ThisItem.", f"{row}.")
                  + ";\nSet(varDomDetailsId, Blank())",
                  primary=True, width=130, height=30)
    close = button("btnDomDetClose", '"Close"',
                   "Set(varDomDetailsId, Blank())", width=84, height=30)
    # Knapperne DIREKTE i hovedet, ikke i en indlejret gruppe: i Studio
    # stod de i en indlejret gruppe ved siden af en fleksibel venstreside
    # en linje for lavt, skaaret over af kanten. Samme som topbjaelken.
    head = group("conDomDetHead", [head_left] + pin_widths([prev, nxt, edit, close]),
                 direction="Horizontal", gap=8, align_items="Center")

    # Alle felter - ogsaa de tomme. En tom linje er et svar: feltet ER
    # ikke udfyldt. Skjules den, kan man ikke se forskel paa "tomt" og
    # "findes ikke".
    rows = [_detail_row(0, cfg.TEXT_LABEL, f'Coalesce({row}.{cfg.C_TEXT}, "-")'),
            _detail_row(1, "Plant", f'Coalesce({row}.Plant, "-")'),
            _detail_row(2, "Status", f'Coalesce({row}.Status, "-")'),
            _detail_row(3, "Documents", f'Text(Coalesce({row}.FileCount, 0))')]
    for n, (col, label, kind, _ch) in enumerate(FIELDS, start=len(rows)):
        v = (f'If(IsBlank({row}.{col}), "-", Text({row}.{col}))'
             if kind in ("num", "date") else f'Coalesce({row}.{col}, "-")')
        rows.append(_detail_row(n, label, v))

    # FELTLISTEN SCROLLER, POPUPPEN GOER IKKE. Equipment har nitten felter;
    # hoejere end en baerbar skaerm. Hovedet med Luk staar fast.
    box = group("conDomDetRows", rows, direction="Vertical", gap=6)
    natural = box.props["Height"]
    box.props["Height"] = f"Min({natural}, App.Height - 200)"
    box.h = box.props["Height"]
    box.props["LayoutOverflowY"] = "LayoutOverflow.Scroll"
    modal = group("conDomDetailsModal", [head, box], direction="Vertical",
                  gap=12, fill=C_MODAL_BG, border_color=C_PRIMARY_SOFT,
                  radius=16, pad=(18, 18, 18, 18), width=DETAILS_W,
                  drop_shadow="ExtraBold",
                  visible="!IsBlank(varDomDetailsId)")
    modal.props["X"] = MODAL_X
    modal.props["Y"] = MODAL_Y
    return modal


def build_rows():
    search = text_input("txtDomSearch", '""',
                        placeholder='"Search description, functional location, number"',
                        width="360", label="\"Search the rows\"")
    # Samme regel som paa vaerkfeltet: Default er en RECORD fra Items.
    # "all" er et LOKALT sentinel-ord: det betyder "filtrer ikke" og
    # staar ingen steder i SharePoint. De tre andre ER lagrede vaerdier i
    # colDomRows.Status og maa derfor ikke oversaettes - check_datasources
    # efterproever dem mod udtraekket.
    filt = '["all", "draft", "valid", "submitted"]'
    status = dropdown("drpDomStatusFilter", filt,
                      f'LookUp({filt}, Value = "all")', width="160", label="\"Filter by status\"")
    toolbar = group("conDomToolbar", pin_widths([search, status]),
                    direction="Horizontal", gap=12, align_items="Center")

    head = group("conDomListHead",
                 pin_widths([_head_cell(i, n, w)
                             for i, (n, w) in enumerate(LIST_COLS)]),
                 direction="Horizontal", gap=GAP, height=18,
                 align_items="Center")

    cells = [text_ctrl("txtDomRowText",
                       f'If(IsBlank(Trim(ThisItem.{cfg.C_TEXT})), "(no text)", ThisItem.{cfg.C_TEXT})',
                       size=14, height=20, width=MAIN_W, wrap="false")]
    for i, col in enumerate(cfg.LIST_FIELDS):
        cells.append(text_ctrl(f"txtDomRow{i}", f"ThisItem.{col}", size=13,
                               color=C_MUTED, height=20,
                               width=LIST_COLS[i + 1][1], wrap="false",
                               visible=SHOW_MID))
    # STATUS-kolonnen, ikke FILES: her stod LIST_COLS[-2] (40 px), saa hver
    # celle efter status stod 35 px forskudt i forhold til overskriften.
    cells.append(badge("txtDomRowStatus", "ThisItem.Status",
                       width=LIST_COLS[-3][1]))
    cells.append(text_ctrl("txtDomRowFiles", "Text(ThisItem.FileCount)",
                           size=13, color=C_MUTED, height=20,
                           width=LIST_COLS[-2][1], wrap="false",
                           visible=SHOW_FILES))
    # FIRE KNAPPER, IKKE EEN
    #
    # Den haandskrevne app havde btnMatRowEdit, btnMatRowCopy,
    # btnMatRowDelete og btnMatRowDetails paa hver raekke. Ved
    # konverteringen til builderen kom kun Edit med - se issue #15 og #16.
    #
    # Knapper og ikke kun et klik paa raekken: galleriets OnSelect virker
    # ogsaa, men den er usynlig, og saa er det de faerreste der proever.
    acts = [
        button("btnDomRowOpen", '"Edit"', load_row_fx(),
               width=ROW_BTN["btnDomRowOpen"], height=ROW_BTN_H),
        button("btnDomRowDetails", '"Details"',
               'Set(varDomDetailsId, ThisItem.RowId)',
               width=ROW_BTN["btnDomRowDetails"], height=ROW_BTN_H),
        # Dokumenterne paa DENNE raekke - uden at laese den ind i
        # formularen foerst.
        button("btnDomRowDocs", '"Docs"', open_docs_fx(),
               width=ROW_BTN["btnDomRowDocs"], height=ROW_BTN_H,
               visible=SHOW_FILES),
        button("btnDomRowCopy", '"Copy"', copy_row_fx(),
               width=ROW_BTN["btnDomRowCopy"], height=ROW_BTN_H,
               visible=SHOW_FILES),
        button("btnDomRowDelete", '"Delete"', delete_this_row_fx(),
               danger=True, width=ROW_BTN["btnDomRowDelete"], height=ROW_BTN_H),
    ]
    got = [(c.name, int(c.props["Width"])) for c in acts]
    want = list(ROW_BTN.items())
    if got != want:
        raise SystemExit("ROW_BTN passer ikke paa raekkens knapper:\n"
                         "  ROW_BTN: %s\n  raekken: %s" % (want, got))
    cells.append(group("conDomRowActions", acts, direction="Horizontal",
                       gap=ROW_BTN_GAP, height=ROW_BTN_H, align_items="Center",
                       width=ACT_W, align_in_container="Center"))
    for b in acts:
        b.props["Size"] = "13"

    # align_items="Start" og ikke Stretch: raekken skal vaere saa bred som
    # sine celler, ikke som skabelonen - ellers straekkes den sidste celle
    # ud over den tomme flade til hoejre.
    row = group("conDomRow", pin_widths(cells), direction="Horizontal", gap=GAP,
                height="Parent.TemplateHeight - 2", align_items="Center",
                justify="Start", width="Parent.TemplateWidth")

    gal_h = f"Max(Min(CountRows({SCOPE}), {GAL_ROWS}), 1) * {ROW_H + 2}"
    gal = Ctrl("galDomRows", "Gallery", variant="Vertical", props={
        "AccessibleLabel": '"Saved rows"',
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
                      '"No saved rows yet."',
                      size=13, color=C_MUTED, height=22, wrap="false",
                      visible="IfError(CountRows(colDomRows) = 0, false)")

    return card("conDomRowsCard",
                [text_ctrl("txtDomRowsH", '"Saved rows"', size=16,
                           weight="Semibold", height=22, wrap="false"),
                 toolbar, head, gal, empty])


# ---------------------------------------------------------------------------
# Indsend
#
# Nummeret kommer fra indeksraekkens eget ID. Det kraever ingen taeller,
# intet flow og ingen aftale mellem apps om hvem der uddeler numre - og to
# brugere, der indsender samtidig, kan ikke faa det samme nummer.
# ---------------------------------------------------------------------------
# Raekker der kan sendes med. En kladde tager ALT, der ikke allerede er
# afsendt - ogsaa de halvfaerdige; det er meningen med en kladde. Indsend
# tager kun dem, der er meldt faerdige.
SENDABLE = 'Filter(colDomRows, Status <> "submitted")'
VALID = 'Filter(colDomRows, Status = "valid")'


def send_fx(submit):
    """Skriv indmeldingen til MD_RequestIndex - som kladde eller indsendt.

    EEN INDEKSRAEKKE, IKKE EEN PR. TRYK
    -----------------------------------
    Raekken slaas op paa RequestGuid og oprettes kun, hvis den ikke findes.
    Ellers ville "Send som kladde" og derefter "Submit" give TO raekker
    paa landingssiden for den samme indmelding - og den foerste ville
    blive staaende som kladde for evigt. Det er samme konstruktion som
    VH-plan-appens gem.

    RequestNo skrives med i FOERSTE Patch. MD_RequestIndex's Title er
    obligatorisk, og RequestNo ER Title, omdoebt - en raekke uden den
    bliver afvist. Nummeret laves af raekkens eget ID og kan derfor foerst
    kendes bagefter; indtil da staar GUID'en der.
    """
    rows = VALID if submit else SENDABLE
    status = "Indsendt" if submit else "Kladde"
    step = 2 if submit else 1
    label = "Submitted" if submit else "Saved as draft"
    empty = ("There are no completed rows to submit."
             if submit else "There are no rows to save.")

    # Kun en indsendelse laaser raekkerne. En kladde skal stadig kunne
    # rettes - ellers er det ikke en kladde.
    row_patch = [
        "                    RequestNo: varDomRequestNo,",
        "                    RequestGuid: varDomRequestGuid,",
    ]
    if submit:
        row_patch += [
            '                    RowStatus: { Value: "submitted" },',
            "                    SubmittedOn: Now()",
        ]
    else:
        row_patch[-1] = row_patch[-1].rstrip(",")

    return (
        "If(\n"
        f"    CountRows({rows}) = 0,\n"
        f'    Notify("{empty}", NotificationType.Warning),\n'
        "\n"
        "    IfError(\n"
        "        If(\n"
        "            IsBlank(varDomRequestGuid),\n"
        "            Set(varDomRequestGuid, Text(GUID()))\n"
        "        );\n"
        "        Set(\n"
        "            varDomIdx,\n"
        "            Patch(\n"
        f"                {cfg.L_INDEX},\n"
        "                Coalesce(\n"
        f"                    LookUp({cfg.L_INDEX}, RequestGuid = varDomRequestGuid),\n"
        f"                    Defaults({cfg.L_INDEX})\n"
        "                ),\n"
        "                {\n"
        "                    RequestNo: Coalesce(varDomRequestNo, varDomRequestGuid),\n"
        f'                    Domain: {{ Value: "{cfg.DOMAIN}" }},\n'
        f'                    Status: {{ Value: "{status}" }},\n'
        f"                    StatusStep: {step},\n"
        "                    IsOpen: true,\n"
        "                    RequesterEmail: varDomMe,\n"
        "                    RequesterName: User().FullName,\n"
        f'                    ShortText: "{cfg.TITLE}: " & CountRows({rows}) '
        '& " row(s)",\n'
        f"                    Plant: First({rows}).Plant,\n"
        f"                    ItemCount: CountRows({rows}),\n"
        "                    RequestGuid: varDomRequestGuid,\n"
        f'                    AppUrl: "{cfg.PLAY_URL}?reqid=" & varDomRequestGuid,\n'
        "                    LastActionOn: Now(),\n"
        "                    LastActionBy: varDomMe\n"
        "                }\n"
        "            )\n"
        "        );\n"
        "\n"
        "        // Foerste gang bliver indeksraekkens eget ID til nummeret\n"
        "        If(\n"
        "            IsBlank(varDomRequestNo),\n"
        f'            Set(varDomRequestNo, "{cfg.PREFIX}-" & Text(varDomIdx.ID, "000000"));\n'
        f"            Patch({cfg.L_INDEX}, varDomIdx, {{ RequestNo: varDomRequestNo }})\n"
        "        );\n"
        "\n"
        # EET OPSLAG, IKKE EET PR. RAEKKE
        #
        # Her stod ForAll(raekker, LookUp(EquipmentItems, ID = R.RowId)) som
        # Patchens grundraekker. LookUp mod en liste kan ikke delegeres, naar
        # der sammenlignes med et scope-felt, saa hver eneste raekke hentede
        # op til 500 raekker hjem og ledte lokalt. Med mere end 500 raekker i
        # listen ville en raekke laengere nede slet ikke blive fundet - og
        # saa opretter Patch en NY raekke i stedet for at rette den gamle.
        #
        # Nu hentes brugerens egne raekker EEN gang (RequesterEmail =
        # varDomMe er delegerbart - samme filter som refresh_rows_fx), og
        # udvaelgelsen sker i hukommelsen. Aendringerne er ens for alle
        # raekker, saa de kan skrives i eet batchet Patch.
        "        With(\n"
        "            {\n"
        "                src:\n"
        "                    Filter(\n"
        f"                        Filter({cfg.L_ROWS}, RequesterEmail = varDomMe) As S,\n"
        f"                        CountRows(Filter({rows}, RowId = S.ID)) > 0\n"
        "                    )\n"
        "            },\n"
        "            Patch(\n"
        f"                {cfg.L_ROWS},\n"
        "                src,\n"
        "                ForAll(\n"
        "                    src,\n"
        "                    {\n"
        + "\n".join("    " + l for l in row_patch) + "\n"
        "                    }\n"
        "                )\n"
        "            )\n"
        "        );\n"
        "\n"
        + refresh_rows_fx(8) + ";\n"
        "\n"
        f'        Set(varDomInfo, "{label}: " & varDomRequestNo);\n'
        f'        Notify("{label} as " & varDomRequestNo & " - see it on the '
        'landing page.", NotificationType.Success),\n'
        "\n"
        '        Set(varDomInfo, "It failed: " & FirstError.Message);\n'
        '        Notify("It failed: " & FirstError.Message, '
        "NotificationType.Error)\n"
        "    )\n"
        ")"
    )


def build_submit():
    draft = button(
        "btnDomSendDraft", '"Save as draft"', send_fx(False), width=180,
        display_mode=f'If(CountRows({SENDABLE}) = 0, DisplayMode.Disabled, DisplayMode.Edit)')
    submit = button(
        "btnDomSubmit", '"Submit"', send_fx(True), primary=True, width=150,
        display_mode=f'If(CountRows({VALID}) = 0, DisplayMode.Disabled, DisplayMode.Edit)')
    # "Hent forfra" stod BEGGE steder - her og paa dokumentruden - og
    # betoed to forskellige ting. Nu siger navnet hvad der hentes.
    reload_ = button("btnDomReload", '"Reload rows"',
                     refresh_rows_fx() + ';\nSet(varDomInfo, "Reloaded.")',
                     width=150)
    note = text_ctrl(
        "txtDomSubmitNote",
        ('"Save as draft puts the request on the landing page with status Draft '
         '- it can still be edited. Submit locks the rows and sets the status '
         'to Submitted. Both write to the SAME row in the index."'),
        size=12, color=C_MUTED, height=18, wrap="false")
    state = text_ctrl(
        "txtDomSubmitState",
        ('If(\n'
         '    IsBlank(varDomRequestNo),\n'
         '    "The request has not been sent to the hub yet.",\n'
         '    "Request " & varDomRequestNo & " is on the landing page."\n'
         ')'),
        size=13, height=20, wrap="false")
    return card("conDomSubmitCard",
                [state,
                 button_row("conDomSubmitRow", [draft, submit, reload_], SHELL_W),
                 note])
