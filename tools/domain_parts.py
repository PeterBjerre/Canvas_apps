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
                        C_CARD_BORDER, C_TITLE, C_MUTED, C_MUTED_BG, C_REQUIRED,
                        C_PRIMARY, C_WHITE, C_TRANSPARENT,
                        C_NEUTRAL_BG, C_NEUTRAL_FG, C_INFO_FG, C_INFO_BG,
                        C_VALID_FG, C_VALID_BG, C_WARN_FG, C_WARN_BG,
                        C_MODAL_BG, C_PRIMARY_SOFT, C_OVERLAY)
from layout_tokens import fits
from build_helpers import (text_ctrl, group, button, text_input,
                           date_picker, fit_button_row, fit_button_width,
                           number_input, themed_dropdown, card, field_cell,
                           pin_widths, badge, top_bar, grow, flow_row,
                           border_rule, input_fill, label_px, text_px,
                           loading_overlay, with_busy, confirm_modal, ICON_SAVE,
                           ICON_SUBMIT, ICON_W)

# Mens en gemning koerer, staar ventespinneren oven paa skaermen (issue #54).
SAVING_VAR = "varDomSaving"
# Bekraeftelsen foer Submit.
CONFIRM_VAR = "varDomConfirmSubmit"
from layout_tokens import SCROLLBAR_W
import domain_config as cfg
import attflows

# Flowkontrakten staar i tools/attflows.py; ruden her er dens
# domaeneudgave - samme tre flows, egne samlingsnavne.
att = attflows.DomainPane()
import build_flsearch as fl
from fl_picker import fl_picker, known_fx as fl_known_fx

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
    # Temaskiftet og vejen til hubben staar i sidebaren (tools/side_nav.py).
    return top_bar("Dom", f'"{cfg.TITLE}"', f'"{cfg.SUBTITLE}"',
                   [count, no],
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
        # Classic/DropDown: Default er TEKSTEN, ikke en record - se
        # build_helpers.themed_dropdown for hvorfor den ikke er moderne.
        items = "[" + ", ".join(f'"{x}"' for x in choices) + "]"
        return themed_dropdown(name, items, v, display_mode=DM_ROW,
                               onchange=f"Set({v}, Self.Selected.Value)")
    if kind == "bool":
        # Ja/nej. Samme ModernCheckbox som dokumentlisten bruger - den er
        # bevist i dette miljoe. En app kan ogsaa vise feltet paa sin egen
        # maade (Materials: No BOM Item er en knap i formularens hoved).
        return Ctrl(name, "ModernCheckbox", props={
            "AccessibleLabel": f'"{name}"',
            "Default": v,
            "DisplayMode": DM_ROW,
            "Height": "36",
            "Label": '""',
            "OnCheck": f"Set({v}, true)",
            "OnUncheck": f"Set({v}, false)",
            "Width": "Parent.Width",
        }, h=36)
    c = text_input(name, v, max_length=255, display_mode=DM_ROW,
                   onchange=f"Set({v}, Self.Text)")
    return c


def _plant_dropdown():
    """Vaerkfeltet.

    TO fejl sad her, og de laa oven i hinanden:

    1. Default var "varDomFPlant" - en STRENG. En ModernDropdown vil have
       en RECORD fra sin egen Items-tabel, ikke vaerdien inde i den.
       Compile svarede: [Control 'drpDomPlant', Property 'Default']
       Expected a valid input matching Items.

    2. Der var slet ingen OnChange. Variablen blev altsaa aldrig sat, og
       da Gem kraever den udfyldt, kunne der ALDRIG gemmes - en fejl,
       compile ikke kan se, fordi formlen i sig selv er gyldig.

    Nu er den en Classic/DropDown (build_helpers.themed_dropdown), saa
    listen kan ses i moerk tilstand. Den vil have TEKSTEN som Default -
    fejl 1 ovenfor gaelder kun ModernDropdown."""
    return themed_dropdown("drpDomPlant", "colDomPlants", "varDomFPlant",
                           required_formula=REQUIRED, display_mode=DM_ROW,
                           onchange="Set(varDomFPlant, Self.Selected.Value)")


# FL-vaelgerens tilstand. Selve vaelgeren er tools/fl_picker.py - den
# samme i VH-plan, Equipments og Materials (issue #63).
FL_QUERY_VAR = "varDomFlQuery"
FL_BUSY_VAR = "varDomFlBusy"
FL_LAST_VAR = "varDomFlLast"
FL_COMBO = "cmbDomFl"


def build_fl_picker(cell_w, lock=None, required_formula="false"):
    """Functional Location i EEN combobox med Search - soegefelt OG
    valgliste (fl_picker.py). Der er ingen separat soegeboks og ingen
    separat dropdown.

    lock: et udtryk, der - naar det er sandt - deaktiverer vaelgeren
    (Materials' No BOM Item). required_formula: hvornaar kanten maa vaere
    roed."""
    dm = DM_ROW if lock is None else f"If({lock}, DisplayMode.Disabled, {DM_ROW})"
    v = _var(cfg.FL_FIELD)
    return fl_picker(
        "Dom", combo=FL_COMBO, results="colDomFl", raw_var=fl.DEFAULT_RAW,
        msg_var="varDomFlMsg", busy_var=FL_BUSY_VAR, query_var=FL_QUERY_VAR,
        last_var=FL_LAST_VAR, default_items=f"Filter(colDomFl, Code = {v})",
        on_select=f'Set({v}, Coalesce(Self.Selected.Code, ""))',
        on_clear=f'Set({v}, "")', display_mode=dm,
        required_formula=required_formula, width=cell_w)


def build_fl_msg():
    """Soegningens svar - under raekken, i fuld bredde, og kun naar der er
    noget at sige. I en fjerdedel af kortet ville det blive klippet."""
    return text_ctrl("txtDomFlMsg", "varDomFlMsg", size=12, color=C_MUTED,
                     height=18, wrap="false", visible="!IsBlank(varDomFlMsg)")


def _fl_known_fx(src):
    """Den gemte funktionsplads skal staa i comboboksen, naar en raekke
    hentes eller kopieres - ogsaa selv om der ikke er soegt paa den."""
    return fl_known_fx("colDomFl", src)


# ---------------------------------------------------------------------------
# Adfaerden
# ---------------------------------------------------------------------------
BLANK = {"num": "Blank()", "date": "Blank()", "bool": "false"}


def _blank(kind):
    return BLANK.get(kind, '""')


def _patch_value(col, kind):
    v = _var(col)
    if kind in ("text", "long", "choice"):
        return f"Trim(Coalesce({v}, \"\"))"
    if kind == "bool":
        return f"Coalesce({v}, false)"
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
        elif kind == "bool":
            v = f"Coalesce(R.{col}, false)"
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
    lines.append(f'Set({FL_QUERY_VAR}, "");')
    lines.append(f'Set({FL_LAST_VAR}, "");')
    lines.append(f'Reset({FL_COMBO});')
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
    if getattr(cfg, "FL_FIELD", None):
        lines.append(_fl_known_fx(f"ThisItem.{cfg.FL_FIELD}"))
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
    if getattr(cfg, "FL_FIELD", None):
        lines.append(_fl_known_fx(f"ThisItem.{cfg.FL_FIELD}"))
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


def save_row_fx(status="valid", required=()):
    """Gem raekken i SharePoint - som kladde eller som faerdig.

    required: appens EKSTRA krav til en faerdig raekke, som par af
    (betingelse der betyder "mangler", besked). Kladden tjekker dem ikke.
    Materials kraever funktionspladsen - undtagen paa en No BOM-raekke.

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
    # Hvert ekstra krav er sin egen gren i den samme If - og faar sin egen
    # besked, saa brugeren ser HVAD der mangler.
    extra = ""
    if status != "draft":
        for cond, text in required:
            extra += f'    {cond},\n    Notify("{text}", NotificationType.Warning),\n'

    return (
        # "Jeg har tjekket" - herfra maa kanterne vaere roede.
        f"Set({REQUIRED}, true);\n"
        "If(\n"
        f"    {guard},\n"
        f'    Notify("{msg}", NotificationType.Warning),\n'
        + extra +
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
        '    Set(varDomInfo, "Save failed: " & FirstError.Message);\n'
        '    Notify("Save failed: " & FirstError.Message, '
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
    actions = fit_button_row("conDomAttActions", [up, refresh, rem], DOCS_INNER_W)

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
# Raekkens knapper og deres bredder - som i den haandbyggede Materials-app,
# hvor knapperne virkede: 30 px hoeje, 13 pt. Her stod 26 px med 14 pt, og
# knapperne stod som tomme kanter i bunden af raekken - under den moderne
# knaps mindstehoejde. check_layout regel 25 kraever nu mindst 30.
ROW_BTN = {"btnDomRowOpen": 60, "btnDomRowDetails": 72, "btnDomRowDocs": 64,
           "btnDomRowCopy": 64, "btnDomRowDelete": 72}
ROW_BTN_H = 30
ROW_BTN_GAP = 4


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


def build_details(scope=None):
    """Alle raekkens felter, med frem og tilbage mellem raekkerne.

    scope: det filter, listen viser (standard: LIST_SCOPE), saa frem og
    tilbage foelger det, brugeren ser."""
    scope = LIST_SCOPE if scope is None else scope
    # Raekken, ruden viser. Den slaas op HVER gang - saa er den altid den,
    # der staar i samlingen, ogsaa efter en Gem.
    row = f"LookUp(colDomRows, RowId = varDomDetailsId)"
    # Positionen i den SORTEREDE og FILTREREDE liste, saa frem/tilbage
    # foelger det, brugeren faktisk ser. Power Fx har ingen IndexOf, men
    # i en faldende sortering er positionen antallet af raekker foran.
    order = f"Sort({scope}, RowId, SortOrder.Descending)"
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
        if kind == "bool":
            v = f'If({row}.{col}, "Yes", "No")'
        elif kind in ("num", "date"):
            v = f'If(IsBlank({row}.{col}), "-", Text({row}.{col}))'
        else:
            v = f'Coalesce({row}.{col}, "-")'
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
        # Derefter stod der Filter(Filter(liste, RequesterEmail = varDomMe)
        # As S, CountRows(Filter(raekker, RowId = S.ID)) > 0). Det inderste
        # filter blev delegeret, det yderste ikke - og compile gav fire
        # delegeringsadvarsler paa de to send-knapper (issue #37).
        #
        # Nu roeres listen slet ikke for at FINDE raekkerne: samlingen
        # kender deres ID (RowId), og en SharePoint-raekke kan patches med
        # { ID: n } som grundraekke. Aendringerne er ens for alle raekker,
        # saa det er stadig eet batchet Patch - to tabeller af samme laengde.
        "        Patch(\n"
        f"            {cfg.L_ROWS},\n"
        f"            ForAll({rows} As X, {{ ID: X.RowId }}),\n"
        f"            ForAll(\n"
        f"                {rows},\n"
        "                {\n"
        + "\n".join(row_patch) + "\n"
        "                }\n"
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


def build_submit_confirm():
    """Bekraeftelsen foer Submit og ventespinneren (issue #54).

    [sloer, popup, spinner] - skal staa SIDST i skaermens boern, saa de
    ligger oven paa alt andet."""
    return confirm_modal(
        "Dom", CONFIRM_VAR, "Submit request?",
        '"The valid rows are sent to the landing page as Submitted and locked."',
        "Submit", with_busy(SAVING_VAR, send_fx(True)), "btnDomSubmitConfirm") + [
        loading_overlay("imgDomSaving", SAVING_VAR)]


# ---------------------------------------------------------------------------
# Formularens byggeklodser (issue #67 / #68)
#
# Begge apps har nu HTML-projektets formular: ingen sektionsoverskrifter, et
# gitter med fire kolonner paa desktop, to paa tablet og een paa mobil,
# piller med vaerk og raekkestatus, og knapperne til hoejre. Selve
# kompositionen - hvilke felter, i hvilken raekkefoelge - er appens egen
# (material_parts.py / equipment_parts.py).
# ---------------------------------------------------------------------------
GRID_GAP = 20
# Mindste cellebredde for fire og for to kolonner. Graenserne regnes af
# dem - ikke skrevet af - saa en anden mindstebredde flytter dem selv.
CELL_MIN_4 = 200
CELL_MIN_2 = 220
NEED_4 = 4 * CELL_MIN_4 + 3 * GRID_GAP
NEED_2 = 2 * CELL_MIN_2 + GRID_GAP
GRID_COLS = 4

# Een celles bredde - maalt paa KORTETS bredde, ikke paa App.Width.
CELL_W = fits(FORM_W, NEED_4,
              fits(FORM_W, NEED_2, FORM_W, f"(({FORM_W}) - {GRID_GAP}) / 2"),
              f"(({FORM_W}) - {3 * GRID_GAP}) / 4")


def _line_h(hs):
    """Den hoejeste af cellerne paa en linje - tal, hvis de alle er tal."""
    if all(isinstance(h, (int, float)) for h in hs):
        return str(max(hs))
    return hs[0] if len(hs) == 1 else "Max(%s)" % ", ".join("(%s)" % h for h in hs)


def _chunk_h(heights, k):
    """Hoejden af en raekke, der ombryder til linjer a k celler."""
    lines = [heights[i:i + k] for i in range(0, len(heights), k)]
    return (" + ".join("(%s)" % _line_h(l) for l in lines)
            + " + %d" % (GRID_GAP * (len(lines) - 1)))


def grid_row(name, cells):
    """Op til fire celler (eller kolonner), der ombryder til to og een.

    Hoejden regnes for hver af de tre tilstande af cellernes egne hoejder
    - check_layout regel 4c spiller ombrydningen og efterproever den."""
    if len(cells) > GRID_COLS:
        raise SystemExit(f"domain_parts.grid_row: {name} har {len(cells)} celler - "
                         f"hoejst {GRID_COLS}")
    hs = [c.h for c in cells]
    h = fits(FORM_W, NEED_4,
             fits(FORM_W, NEED_2, _chunk_h(hs, 1), _chunk_h(hs, 2)),
             _chunk_h(hs, 4))
    return group(name, cells, direction="Horizontal", gap=GRID_GAP, height=h, wrap="true")


def grid_rows(prefix, cells):
    """Celler i RAEKKE-orden: fire pr. raekke, venstre mod hoejre."""
    return [grid_row(f"{prefix}{i // GRID_COLS}", cells[i:i + GRID_COLS])
            for i in range(0, len(cells), GRID_COLS)]


def grid_columns(name, columns, row_gap=14):
    """Celler i KOLONNE-orden: oppefra og ned i kolonne 1, saa kolonne 2 ...
    (eq.png). Paa en tablet staar kolonne 1 og 2 side om side over 3 og 4;
    paa en telefon under hinanden - stadig i kolonne-orden."""
    cols = [group(f"{name}Col{i + 1}", cells, direction="Vertical", gap=row_gap,
                  width=CELL_W, align_items="Stretch", align_in_container="Start")
            for i, cells in enumerate(columns)]
    return grid_row(name, cols)


def grid_cell(name, label, ctrl, required=False):
    return field_cell(name, label, ctrl, required=required, width=CELL_W,
                      fill_portions_formula="0")


def field_grid_cell(col):
    """Et felt fra SECTIONS som celle i gitteret."""
    for c, label, kind, choices in FIELDS:
        if c == col:
            return grid_cell(f"con{c}", label, _input_for(c, kind, choices))
    raise SystemExit(f"domain_parts: {col} er ikke et felt i SECTIONS")


def text_cell():
    """Raekkens tekst (Title) - kraevet, ogsaa paa en kladde."""
    return grid_cell("conDomText", cfg.TEXT_LABEL,
                     text_input("inpDomText", "varDomFText", max_length=40,
                                placeholder=cfg.TEXT_PLACEHOLDER,
                                required_formula=REQUIRED, display_mode=DM_ROW,
                                onchange="Set(varDomFText, Self.Text)"),
                     required=True)


def plant_cell():
    return grid_cell("conDomPlant", cfg.PLANT_LABEL, _plant_dropdown(), required=True)


def check_form_order(order, special, not_in_grid=()):
    """Et felt i SECTIONS, der ikke er i appens raekkefoelge, ville ellers
    bare mangle paa skaermen - uden at noget sagde det."""
    want = {c for c, _l, _k, _ch in FIELDS} - set(not_in_grid)
    have = set(order) - set(special)
    if want != have or len(order) != len(set(order)):
        raise SystemExit("Formularens raekkefoelge passer ikke til SECTIONS:\n"
                         f"  mangler: {sorted(want - have)}\n"
                         f"  ukendte: {sorted(have - want)}")


# ---------------------------------------------------------------------------
# Knapper: saa brede som deres tekst, og aldrig klippet
# ---------------------------------------------------------------------------
def fit(btn, icon=False, size=14):
    """Bredden af knappens tekst (+ ikon), laast som mindstebredde.

    fit_button_width kraever en litteral: en knap, hvis tekst skifter, skal
    have sin LAENGSTE tekst, naar den kaldes - og faa formlen bagefter."""
    w = fit_button_width(btn.props["Text"], size=size, min_w=0) + (ICON_W if icon else 0)
    btn.props["Width"] = str(w)
    btn.props["LayoutMinWidth"] = str(w)
    return btn


def pill(btn, on):
    """En knap, der er TIL eller FRA: udfyldt, naar den er til."""
    for k in ("TopLeft", "TopRight", "BottomLeft", "BottomRight"):
        btn.props["Radius" + k] = "16"
    btn.props["Appearance"] = (f"If({on}, ButtonAppearance.Primary, "
                               "ButtonAppearance.Outline)")
    btn.props["BasePaletteColor"] = C_PRIMARY
    btn.props["Color"] = f"If({on}, {C_WHITE}, {C_TITLE})"
    btn.props["BorderColor"] = f"If({on}, {C_PRIMARY}, {C_CARD_BORDER})"
    return btn


def meta_pill(name, text, width):
    return text_ctrl(name, text, size=12, color=C_MUTED, height=28, width=width,
                     wrap="false",
                     extra={"Fill": C_NEUTRAL_BG, "VerticalAlign": "VerticalAlign.Middle",
                            "PaddingLeft": "10", "PaddingRight": "10",
                            "RadiusBottomLeft": "8", "RadiusBottomRight": "8",
                            "RadiusTopLeft": "8", "RadiusTopRight": "8"})


# ---------------------------------------------------------------------------
# Dokumenterne fra formularen
# ---------------------------------------------------------------------------
def open_active_docs_fx():
    """Formularens Documents-knap: dokumentpopuppen for den AABNE raekke.

    Samme som raekkens Docs-knap (open_docs_fx), bare med den aktive raekke
    i stedet for ThisItem. Popuppen aabner kun her og paa Docs - aldrig af
    sig selv: varDomDocsId er Blank fra OnStart."""
    return (
        "Set(varDomDocsId, varDomActiveRowId);\n"
        "If(\n"
        f"    Coalesce({ACTIVE}.FileCount, 0) > 0 &&\n"
        "    CountRows(Filter(colDomAttachments, RowId = varDomActiveRowId)) = 0,\n"
        + att.refresh_fx(4) + "\n"
        ")"
    )


def docs_cell():
    """Documentation: hvor mange dokumenter raekken har, og en knap til
    den eksisterende dokumentpopup. Dokumenterne ligger i en mappe, der
    hedder raekkens noegle, saa knappen virker foerst efter Save."""
    info = grow(text_input(
        "txtDomDocsInfo",
        ('If(IsBlank(varDomActiveRowId), "Save the row first", '
         f'Text(Coalesce({ACTIVE}.FileCount, 0)) & " document(s)")'),
        display_mode="DisplayMode.View", label='"Documents on this row"'))
    text = '"Documents"'
    btn = button("btnDomDocs", text, open_active_docs_fx(),
                 width=fit_button_width(text), display_mode=DM_SEL,
                 accessible='"Open the documents for this row"')
    btn.props["LayoutMinWidth"] = btn.props["Width"]
    row = group("conDomDocsRow", [info, btn], direction="Horizontal", gap=8,
                height=36, align_items="Center", width=CELL_W)
    return grid_cell("conDomDocs", "Documentation", row)


# ---------------------------------------------------------------------------
# Formularens hoved og fod
# ---------------------------------------------------------------------------
def form_head(title_txt, right=()):
    """Titlen, "* Required" og evt. kontroller til hoejre (No BOM Item)."""
    title = text_ctrl("txtDomFormH", f'"{title_txt}"', size=17, weight="Semibold",
                      height=26, width=text_px(title_txt, 17), wrap="false")
    star = text_ctrl("txtDomFormReqStar", '"*"', size=12, color=C_REQUIRED,
                     weight="Semibold", height=18, width=8, wrap="false",
                     accessible='"Required"')
    legend = text_ctrl("txtDomFormReq", '"Required"', size=12, color=C_MUTED,
                       height=18, width=text_px("Required", 12, semibold=False),
                       wrap="false")
    left = group("conDomFormTitle", [title, star, legend], direction="Horizontal",
                 gap=4, height=26, align_items="Center")
    if not right:
        return left
    left_w = sum(int(c.props["Width"]) for c in (title, star, legend)) + 2 * 4
    return flow_row("conDomFormHead", [left] + list(right), FORM_W, gap=12,
                    flex=left, flex_min=left_w)


def form_footer(buttons):
    """Vaerk og raekkens tilstand som to piller til venstre, knapperne til
    hoejre - og appens besked under dem."""
    plant = meta_pill("txtDomFormPlant", '"Plant: " & Coalesce(varDomFPlant, "-")', 130)
    state = meta_pill(
        "txtDomFormState",
        ('If(\n'
         '    IsBlank(varDomActiveRowId),\n'
         '    "Row status: New row - not saved yet",\n'
         '    "Row status: " & Coalesce(' + ACTIVE + '.ItemKey, "row " & varDomActiveRowId) &\n'
         '        " (" & varDomRowStatus & ")"\n'
         ')'), 290)
    meta_w = 130 + 8 + 290
    meta = group("conDomFormMeta", [plant, state], direction="Horizontal", gap=8,
                 height=28, align_items="Center")
    actions = flow_row("conDomFormActions", [meta] + list(buttons), FORM_W, gap=8,
                       flex=meta, flex_min=meta_w)
    info = text_ctrl("txtDomFormInfo", "varDomInfo", size=12, color=C_MUTED,
                     height=18, wrap="false")
    return [actions, info]


def form_buttons(save_fx, save_text, new_text):
    """Delete row, Save draft, Save og New row/Reset form - i den orden,
    med den primaere knap naestsidst som i HTML-projektet.

    save_fx(status) er appens gem (save_row_fx med evt. egne krav)."""
    return [
        fit(button("btnDomDelete", '"Delete row"', delete_row_fx(),
                   danger=True, display_mode=DM_SEL)),
        fit(button("btnDomSaveDraft", '"Save draft"',
                   with_busy(SAVING_VAR, save_fx("draft")),
                   display_mode=DM_ROW, icon=ICON_SAVE), icon=True),
        fit(button("btnDomSave", f'"{save_text}"',
                   with_busy(SAVING_VAR, save_fx("valid")),
                   primary=True, display_mode=DM_ROW, icon=ICON_SAVE), icon=True),
        fit(button("btnDomNew", f'"{new_text}"', clear_form_fx())),
    ]


# ---------------------------------------------------------------------------
# De gemte raekker (issue #67 / #68)
#
# Hoved med soegning, status- og vaerksfilter, Compact/All columns, en
# tabel der scroller vandret, naar den er bredere end kortet, og indsend
# under den til hoejre. Kolonnerne er appens egne (SLOTS i
# material_parts.py / equipment_parts.py).
#
# EEN RAEKKE, FLERE PLADSER
# -------------------------
# Kolonnerne staar i forskellig raekkefoelge i de to visninger. En celle
# kan ikke flytte sig i et galleri, men dens INDHOLD kan: hver plads viser
# een kolonne i Compact og en (evt. anden) i All columns. Saa er der ingen
# celle to gange, og overskriften skifter paa samme maade.
#
# En plads er (Compact, All). Hver af de to er (overskrift, udtryk,
# mindstebredde) - eller None, naar pladsen er tom i den visning.
# ---------------------------------------------------------------------------
# Compact eller All columns. Sat i App.OnStart og ALDRIG af en genhentning,
# saa visningen bliver staaende, naar raekkerne hentes forfra.
ALL_COLS = "varDomAllCols"

# "All plants"/"All status" er LOKALE ord: de betyder "filtrer ikke" og
# staar ingen steder i SharePoint. De tre andre statusvaerdier ER lagrede
# vaerdier i colDomRows.Status og maa ikke oversaettes.
ALL_STATUS = "All status"
ALL_PLANTS = "All plants"
SEARCH = " || ".join(f"Trim(txtDomSearch.Text) in {c}" for c in cfg.SEARCH_FIELDS)
LIST_SCOPE = (
    "Filter(\n"
    "    colDomRows,\n"
    f"    (IsBlank(Trim(txtDomSearch.Text)) || {SEARCH}),\n"
    f'    (drpDomStatusFilter.Selected.Value = "{ALL_STATUS}" ||\n'
    "     Status = drpDomStatusFilter.Selected.Value),\n"
    f'    (drpDomPlantFilter.Selected.Value = "{ALL_PLANTS}" ||\n'
    "     Plant = drpDomPlantFilter.Selected.Value)\n"
    ")"
)
PLANT_ITEMS = (
    "Ungroup(\n"
    f'    Table({{ Rows: Table({{ Value: "{ALL_PLANTS}" }}) }},\n'
    "          { Rows: Sort(Distinct(Filter(colDomRows, !IsBlank(Plant)), Plant), Value) }),\n"
    "    Rows\n"
    ")"
)

T_GAP = 6
HEAD_SIZE = 11
CELL_PAD = 10
BADGE_W = 90

# Knapperne. Details og Docs staar i DETAILS-kolonnen i Compact; i All
# columns er der ingen DETAILS-kolonne, og saa er de de foerste af
# handlingerne - overskriften "ACTIONS" flytter hen over dem.
DETAIL_BTNS = [("btnDomRowDetails", '"Details"'), ("btnDomRowDocs", '"Docs"')]
ACTION_BTNS = [("btnDomRowOpen", '"Edit"'), ("btnDomRowCopy", '"Copy"'),
               ("btnDomRowDelete", '"Delete"')]


def _btns_w(btns):
    """Bredderne er ROW_BTN - afproevet i Studio med 13 pt, og de klipper
    ikke teksten. En knap uden en bredde dér stopper byggeriet."""
    for n, _t in btns:
        if n not in ROW_BTN:
            raise SystemExit(f"domain_parts: {n} har ingen bredde i ROW_BTN")
    return sum(ROW_BTN[n] for n, _t in btns) + ROW_BTN_GAP * (len(btns) - 1)


LIST_DETAILS_W = _btns_w(DETAIL_BTNS) + CELL_PAD
LIST_ACTIONS_W = _btns_w(ACTION_BTNS) + CELL_PAD
# Galleriets egne 2 x 2 px skabelonpolstring og dets lodrette scrollbar.
TABLE_AVAIL = f"(({FORM_W}) - 4 - {SCROLLBAR_W})"


def col_w(spec):
    """Saa bred, at overskriften aldrig klippes - og mindst spec's minimum.

    label_px er Segoe UI's egne tegnbredder (build_helpers). text_px er et
    skoen, der med vilje rammer for bredt; paa sytten overskrifter blev det
    til flere hundrede pixels, og Compact kunne ikke staa uden scroll paa en
    1366-skaerm. 4 px oven i er sikkerheden."""
    if spec is None:
        return 0
    header, _expr, min_w = spec
    return max(min_w, label_px(header, HEAD_SIZE) + 2 * CELL_PAD + 4)


def num_text(col):
    return f'If(IsBlank(ThisItem.{col}), "", Text(ThisItem.{col}))'


def date_text(col):
    return f'If(IsBlank(ThisItem.{col}), "", Text(ThisItem.{col}, "yyyy-mm-dd"))'


class ListLayout:
    """Bredderne for et saet pladser i de to visninger.

    All columns har faste bredder. Compact FYLDER listens bredde: hver
    tekstkolonne faar sin mindstebredde (mindst saa bred som overskriften)
    plus en lige del af det, der er tilovers. Er der intet tilovers (en
    tablet), er tabellen sine mindstebredder og scroller vandret."""

    def __init__(self, slots):
        self.slots = slots
        self.all_ws = [col_w(a) for _c, a in slots]
        self.all_w = (BADGE_W + sum(self.all_ws) + LIST_DETAILS_W + LIST_ACTIONS_W
                      + T_GAP * (len(slots) + 2))
        self.compact = [i for i, (c, _a) in enumerate(slots) if c is not None]
        fixed = BADGE_W + LIST_DETAILS_W + LIST_ACTIONS_W + T_GAP * (len(self.compact) + 2)
        self.compact_min = fixed + sum(col_w(slots[i][0]) for i in self.compact)
        self.spare = (f"Max(0, ({TABLE_AVAIL}) - {self.compact_min}) / "
                      f"{len(self.compact)}")
        self.table_w = (f"If({ALL_COLS}, {self.all_w}, "
                        f"Max({self.compact_min}, {TABLE_AVAIL}))")

    def width(self, i):
        c, a = self.slots[i]
        if c is None:
            return str(self.all_ws[i])
        cw = f"{col_w(c)} + {self.spare}"
        return cw if a is None else f"If({ALL_COLS}, {self.all_ws[i]}, {cw})"

    def visible(self, i):
        c, a = self.slots[i]
        if c is None:
            return ALL_COLS
        if a is None:
            return f"!{ALL_COLS}"
        return None

    def text(self, i, part):
        """part 0 = overskriften, 1 = udtrykket."""
        c, a = self.slots[i]
        pick = (lambda s: f'"{s[0]}"') if part == 0 else (lambda s: s[1])
        if c is None:
            return pick(a)
        if a is None:
            return pick(c)
        cv, av = pick(c), pick(a)
        return cv if cv == av else f"If({ALL_COLS}, {av}, {cv})"


def _pad(ctrl):
    ctrl.props["PaddingLeft"] = str(CELL_PAD)
    return ctrl


def _head_text(name, text, width, visible=None, accessible=None):
    return _pad(text_ctrl(name, text, size=HEAD_SIZE, color=C_MUTED, weight="Semibold",
                          height=18, width=width, wrap="false", visible=visible,
                          accessible=accessible))


def _status_badge():
    """Raekkens status som et maerke - VALID, DRAFT, SUBMITTED - i sin
    egen farve, saa listen kan skimmes."""
    s = "ThisItem.Status"
    fg = (f'Switch({s}, "valid", {C_VALID_FG}, "submitted", {C_INFO_FG}, '
          f'"draft", {C_WARN_FG}, {C_NEUTRAL_FG})')
    bg = (f'Switch({s}, "valid", {C_VALID_BG}, "submitted", {C_INFO_BG}, '
          f'"draft", {C_WARN_BG}, {C_NEUTRAL_BG})')
    b = text_ctrl("txtDomRowStatus", f"Upper({s})", size=11, color=fg,
                  weight="Semibold", height=22, width=BADGE_W - 2 * CELL_PAD,
                  wrap="false", accessible=f'"Status: " & {s}',
                  extra={"Fill": bg, "Align": "Align.Center",
                         "AlignInContainer": "AlignInContainer.Center",
                         "RadiusBottomLeft": "6", "RadiusBottomRight": "6",
                         "RadiusTopLeft": "6", "RadiusTopRight": "6"})
    return group("conDomRowStatus", [b], direction="Horizontal", gap=0,
                 height=22, width=BADGE_W, align_items="Center",
                 pad=(0, 0, 0, CELL_PAD))


def _row_buttons(name, btns, fxs, width, danger=()):
    out = []
    for (bn, text), fx in zip(btns, fxs):
        b = button(bn, text, fx, danger=bn in danger, width=ROW_BTN[bn],
                   height=ROW_BTN_H)
        b.props["Size"] = "13"
        out.append(b)
    return group(name, out, direction="Horizontal", gap=ROW_BTN_GAP, height=ROW_BTN_H,
                 width=width, align_items="Center", pad=(0, 0, 0, CELL_PAD))


def build_list(slots, badge_head, search_placeholder):
    """Kortet med de gemte raekker - og indsend under tabellen.

    slots: appens pladser (se ovenfor). badge_head: overskriften over
    statusmaerket ("STATUS" / "VALIDATION")."""
    lay_ = ListLayout(slots)

    # --- hovedet: titel, soegning og de to filtre ---------------------
    title = text_ctrl("txtDomRowsH", '"Saved Rows"', size=17, weight="Semibold",
                      height=26, wrap="false")
    search = text_input("txtDomSearch", '""', width="240",
                        placeholder=f'"{search_placeholder}"',
                        label='"Search the rows"')
    status = themed_dropdown(
        "drpDomStatusFilter", f'["{ALL_STATUS}", "draft", "valid", "submitted"]',
        f'"{ALL_STATUS}"', width="170", label='"Filter by status"')
    plant = themed_dropdown("drpDomPlantFilter", PLANT_ITEMS, f'"{ALL_PLANTS}"',
                            width="170", label='"Filter by plant"')
    head = flow_row("conDomRowsTop", [title, search, status, plant], FORM_W, gap=8,
                    flex=title, flex_min=text_px("Saved Rows", 17))

    # --- Compact / All columns --------------------------------------------
    compact = pill(fit(button("btnDomViewCompact", '"Compact"',
                              f"Set({ALL_COLS}, false)", height=32,
                              accessible='"Compact view"'), size=13),
                   f"!{ALL_COLS}")
    allc = pill(fit(button("btnDomViewAll", '"All columns"',
                           f"Set({ALL_COLS}, true)", height=32,
                           accessible='"All columns view"'), size=13),
                ALL_COLS)
    for b in (compact, allc):
        b.props["Size"] = "13"
    views = group("conDomViewSwitch", [compact, allc], direction="Horizontal", gap=8,
                  height=32, align_items="Center", justify="End")

    # --- tabellen -----------------------------------------------------------
    heads = [_head_text("txtDomHeadStatus", f'"{badge_head}"', BADGE_W)]
    cells = [_status_badge()]
    for i in range(len(slots)):
        heads.append(_head_text(f"txtDomHead{i}", lay_.text(i, 0), lay_.width(i),
                                visible=lay_.visible(i), accessible=lay_.text(i, 0)))
        cells.append(_pad(text_ctrl(f"txtDomCell{i}", lay_.text(i, 1), size=13,
                                    height=20, width=lay_.width(i), wrap="false",
                                    visible=lay_.visible(i))))
    heads.append(_head_text("txtDomHeadDetails",
                            f'If({ALL_COLS}, "ACTIONS", "DETAILS")', LIST_DETAILS_W))
    heads.append(_head_text("txtDomHeadActions", f'If({ALL_COLS}, "", "ACTIONS")',
                            LIST_ACTIONS_W, accessible='"Actions"'))
    cells.append(_row_buttons("conDomRowDetails", DETAIL_BTNS,
                              ['Set(varDomDetailsId, ThisItem.RowId)', open_docs_fx()],
                              LIST_DETAILS_W))
    cells.append(_row_buttons("conDomRowActions", ACTION_BTNS,
                              [load_row_fx(), copy_row_fx(), delete_this_row_fx()],
                              LIST_ACTIONS_W, danger=("btnDomRowDelete",)))

    table_w = lay_.table_w
    list_head = group("conDomListHead", heads, direction="Horizontal", gap=T_GAP,
                      height=34, width=table_w, align_items="Center", fill=C_MUTED_BG)
    row = group("conDomRow", cells, direction="Horizontal", gap=T_GAP,
                height="Parent.TemplateHeight - 2", align_items="Center",
                justify="Start", width="Parent.TemplateWidth")

    gal_h = f"Max(Min(CountRows({LIST_SCOPE}), {GAL_ROWS}), 1) * {ROW_H + 2}"
    gal = Ctrl("galDomRows", "Gallery", variant="Vertical", props={
        "AccessibleLabel": '"Saved rows"',
        "BorderStyle": "BorderStyle.None",
        "Fill": C_TRANSPARENT,
        "FillPortions": "0",
        "Height": gal_h,
        "Items": f"Sort({LIST_SCOPE}, RowId, SortOrder.Descending)",
        "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None",
        "OnSelect": load_row_fx(),
        "Selectable": "true",
        "ShowScrollbar": "true",
        "TabIndex": "0",
        "TemplatePadding": "2",
        "TemplateSize": str(ROW_H),
        "Width": f"({table_w}) + 4 + {SCROLLBAR_W}",
        "WrapCount": "1",
    }, children=[row], h=gal_h)

    # Vandret scroll, naar tabellen er bredere end kortet (All columns, og
    # Compact paa en tablet). Start, ikke Stretch - check_layout regel 14.
    # Den vandrette scrollbar tager hoejde, saa den laegges til, naar den
    # er der.
    wide = f"(({table_w}) + 4 + {SCROLLBAR_W}) > ({FORM_W})"
    table = group("conDomTableWrap", [list_head, gal], direction="Vertical", gap=0,
                  overflow_x="Scroll", width="Parent.Width", align_items="Start")
    table.props["Height"] = f"{table.props['Height']} + If({wide}, {SCROLLBAR_W}, 0)"
    table.h = table.props["Height"]

    empty = text_ctrl("txtDomNoRows", '"No saved rows yet."', size=13, color=C_MUTED,
                      height=22, wrap="false",
                      visible="IfError(CountRows(colDomRows) = 0, false)")

    return card("conDomRowsCard", [head, views, table, empty] + _submit_parts())


# ---------------------------------------------------------------------------
# Indsend - under tabellen, til hoejre. Selve indsendelsen er send_fx.
# ---------------------------------------------------------------------------
def _submit_parts():
    """Reload rows, Save as draft og Submit saved rows - med Submit yderst
    til hoejre - og hvor indmeldingen staar."""
    # "Hent forfra" stod BEGGE steder - her og paa dokumentruden - og
    # betoed to forskellige ting. Nu siger navnet hvad der hentes.
    reload_ = fit(button("btnDomReload", '"Reload rows"',
                         refresh_rows_fx() + ';\nSet(varDomInfo, "Reloaded.")'))
    draft = fit(button(
        "btnDomSendDraft", '"Save as draft"', with_busy(SAVING_VAR, send_fx(False)),
        icon=ICON_SAVE,
        display_mode=f'If(CountRows({SENDABLE}) = 0, DisplayMode.Disabled, DisplayMode.Edit)'),
        icon=True)
    # Submit spoerger foerst (build_submit_confirm); indsendelsen koerer i
    # popup'ens Submit.
    submit = fit(button(
        "btnDomSubmit", '"Submit saved rows"', f"Set({CONFIRM_VAR}, true)", primary=True,
        icon=ICON_SUBMIT,
        display_mode=f'If(CountRows({VALID}) = 0, DisplayMode.Disabled, DisplayMode.Edit)'),
        icon=True)
    state = text_ctrl(
        "txtDomSubmitState",
        ('If(\n'
         '    IsBlank(varDomRequestNo),\n'
         '    "The request has not been sent to the hub yet.",\n'
         '    "Request " & varDomRequestNo & " is on the landing page."\n'
         ')'),
        size=13, color=C_MUTED, height=20, wrap="false")
    row = flow_row("conDomSubmitRow", [state, reload_, draft, submit], FORM_W, gap=8,
                   flex=state, flex_min=0)
    note = text_ctrl(
        "txtDomSubmitNote",
        ('"Save as draft puts the request on the landing page with status Draft '
         '- it can still be edited. Submit locks the rows and sets the status '
         'to Submitted. Both write to the SAME row in the index."'),
        size=12, color=C_MUTED, height=18, wrap="false")
    return [row, note]
