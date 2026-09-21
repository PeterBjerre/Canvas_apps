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
                        C_VALID_FG, C_VALID_BG)
from design_tokens import theme_query
from layout_tokens import below, if_below, fits
from build_helpers import (text_ctrl, group, button, button_row, text_input, theme_button,
                           number_input, dropdown, card, field_cell, row_n,
                           label_row, pin_widths, badge)
import domain_config as cfg
import attflows as att
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

# Listen og dokumenterne staar side om side over braekpunktet og under
# hinanden derunder. 20 er mellemrummet mellem dem.
# 1600, ikke 1400. Listen har syv kolonner og knap 540 pixels i faste
# bredder; under det bliver beskrivelseskolonnen smallere end sit eget
# gulv, og raekken flyder ud over ruden i stedet for at dele sig.
HALF_W = if_below("Wide", SHELL_W, f"({SHELL_W} - 20) / 2")
PANE_W = f"({HALF_W} - 36)"

# Indsendte raekker kan ikke redigeres - saa ejer SAP-processen dem.
DM_ROW = ('If(varDomRowStatus = "submitted", DisplayMode.View, DisplayMode.Edit)')

# ---------------------------------------------------------------------------
# Topbjaelkens regnestykke. Se build_bar() for hvorfor det er regnet ud.
# ---------------------------------------------------------------------------
BAR_GAP = 10
BAR_SLACK = 20                       # luft i HOEJRESIDEN, taelles kun EEN gang:
                                     # den er en del af BAR_RIGHT_W, og venstresiden
                                     # traekker derfor kun BAR_RIGHT_W + BAR_GAP fra.
                                     # Blev den talt med begge steder, fik titlen 220
                                     # px ved braekpunktet, hvor der staar 240.
BAR_MIN_TITLE = 240                  # under det er titlen ikke laeselig
BAR_RIGHT = [("txtDomCount", 110), ("txtDomReqNo", 150),
             ("btnDomTheme", 92), ("btnDomBack", 140)]
BAR_RIGHT_W = (sum(w for _, w in BAR_RIGHT)
               + BAR_GAP * (len(BAR_RIGHT) - 1) + BAR_SLACK)
# Braekpunktet: er der plads til BAADE hoejresiden og en laeselig titel?
# Det er en CONTAINER-graense og ikke en enhedsklasse - en bjaelke med een
# knap mere skal ombryde tidligere, uanset hvad slags enhed det er.
BAR_MIN_W = BAR_RIGHT_W + BAR_GAP + BAR_MIN_TITLE
DM_SEL = ('If(IsBlank(varDomActiveRowId), DisplayMode.Disabled, DisplayMode.Edit)')


# ---------------------------------------------------------------------------
# Den flade top
# ---------------------------------------------------------------------------
def build_bar():
    """Toplinjen.

    BREDDERNE MAA IKKE KUNNE BLIVE NEGATIVE
    ---------------------------------------
    Her stod venstre side som "Parent.Width - 520" og hoejre som faste 500.
    Paa et smalt vindue blev venstre side negativ, og hoejre side - med
    nummeret, status og knappen tilbage til hubben - blev klippet vaek.
    Knapperne var der; de kunne bare ikke ses.

    Nu bryder linjen om i stedet: under braekpunktet staar de to grupper
    under hinanden, og wrap_rows=2 faar hoejden til at taelle begge rader
    med."""
    title = text_ctrl("txtDomTitle", f'"{cfg.TITLE}"', size=22, weight="Semibold",
                      height=30, wrap="false")
    sub = text_ctrl("txtDomSub", f'"{cfg.SUBTITLE}"', size=13, color=C_MUTED,
                    height=20, wrap="false")
    # BREDDERNE ER REGNET UD, IKKE SKREVET AF
    #
    # Her stod tre tal, der skulle passe sammen, og som intet knyttede
    # sammen: hoejresiden var 440, venstresiden reserverede 500, og
    # braekpunktet var 900. Da temaknappen gjorde hoejresiden 102 px
    # bredere, fulgte de to andre ikke med - og bjaelken ville have
    # ombrudt paa enhver skaermbredde.
    #
    # Nu kommer alle tre af BAR_RIGHT. Tilfoejes en knap, flytter
    # braekpunktet sig med.
    left = group("conDomBarLeft", [title, sub], direction="Vertical", gap=2,
                 width=fits(SHELL_W, BAR_MIN_W, SHELL_W,
                            f"{SHELL_W} - {BAR_RIGHT_W + BAR_GAP}"))

    count = badge("txtDomCount", '"Raekker: " & CountRows(colDomRows)', width=110)
    no = text_ctrl("txtDomReqNo",
                   'If(IsBlank(varDomRequestNo), "Ikke indsendt", varDomRequestNo)',
                   size=15, weight="Semibold", height=24, width=150, wrap="false")
    # Temaet med TILBAGE til hubben. Uden det skiftede hubben farve,
    # fordi brugeren gik retur - lageret er isoleret pr. app-id.
    back = button("btnDomBack", '"Til hubben"',
                  f'Launch("{cfg.HUB_URL}" & {theme_query("?")}, {{ }}, '
                  f'LaunchTarget.Replace)',
                  width=140)
    theme = theme_button("btnDomTheme")
    row = pin_widths([count, no, theme, back])
    got = [(c.name, int(c.props["Width"])) for c in row]
    if got != BAR_RIGHT:
        raise SystemExit("BAR_RIGHT passer ikke paa bjaelkens hoejreside:\n"
                         "  BAR_RIGHT: %s\n  raekken:   %s" % (BAR_RIGHT, got))
    right = group("conDomBarRight", row,
                  direction="Horizontal", gap=BAR_GAP, align_items="Center",
                  justify="End", width=str(BAR_RIGHT_W))
    return group("conDomBar", [left, right], direction="Horizontal", gap=20,
                 align_items="Center", wrap="true", wrap_rows=2)


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
                 required_formula="true", display_mode=DM_ROW)
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
                   placeholder=f'"Mindst {fl.MIN_SEARCH_LEN} tegn - fx SSV10 KAB10"',
                   width="Parent.Width", display_mode=DM_ROW)
    btn = button("btnDomFlSearch", '"Soeg"',
                 fl.search_action("txtDomFlQuery", "colDomFl",
                                  "varDomFlLast", "varDomFlMsg"),
                 width=90, display_mode=DM_ROW)
    row = group("conDomFlSearchRow", pin_widths([q, btn]),
                direction="Horizontal", gap=8, height=36, align_items="Center")

    drop = dropdown("drpDomFl", "colDomFl",
                    f"LookUp(colDomFl, Code = {_var(cfg.FL_FIELD)})",
                    item_display="ThisItem.Display", value_field="Code",
                    display_mode=DM_ROW)
    drop.props["OnChange"] = f"Set({_var(cfg.FL_FIELD)}, Self.Selected.Code)"

    chosen = text_ctrl(
        "txtDomFlChosen",
        f'If(IsBlank({_var(cfg.FL_FIELD)}), "Ingen valgt", "Valgt: " & {_var(cfg.FL_FIELD)})',
        size=12, color=C_MUTED, height=18, wrap="false")
    msg = text_ctrl("txtDomFlMsg", "varDomFlMsg", size=12, color=C_MUTED,
                    height=18, wrap="false")

    return group("conDomFlBlock",
                 [label_row("conDomFlLbl", "Functional location"),
                  row, drop, chosen, msg],
                 direction="Vertical", gap=6, width="Parent.Width")


def build_form():
    head = group("conDomFormHead", [
        text_ctrl("txtDomFormH", '"Raekke"', size=16, weight="Semibold",
                  height=22, wrap="false"),
        text_ctrl("txtDomFormState",
                  ('If(\n'
                   '    IsBlank(varDomActiveRowId),\n'
                   '    "Ny raekke - ikke gemt endnu",\n'
                   '    "Redigerer " & Coalesce(' + ACTIVE + '.ItemKey, "raekke " & varDomActiveRowId) &\n'
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
                              required_formula="true", display_mode=DM_ROW,
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
    # mangle. "Gem" kraever ogsaa vaerket, og det er DEN status, Indsend
    # tager med.
    draft = button("btnDomSaveDraft", '"Gem kladde"', save_row_fx("draft"),
                   width=150, display_mode=DM_ROW)
    save = button("btnDomSave", '"Gem"', save_row_fx("valid"), primary=True,
                  width=130, display_mode=DM_ROW)
    new = button("btnDomNew", '"Ny raekke"', clear_form_fx(), width=130)
    delete = button("btnDomDelete", '"Slet raekke"', delete_row_fx(),
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
             'Set(varDomFText, "");',
             'Set(varDomFPlant, "");']
    for col, _lab, kind, _ch in FIELDS:
        lines.append(f"Set({_var(col)}, {_blank(kind)});")
    lines.append('Set(varDomFlMsg, "");')
    lines.append('Reset(txtDomFlQuery);')
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
        msg = "%s skal udfyldes - ogsaa paa en kladde." % cfg.TEXT_LABEL
        done = "Kladde gemt som "
    else:
        guard = ('IsBlank(Trim(Coalesce(varDomFText, ""))) || '
                 "IsBlank(varDomFPlant)")
        msg = "%s og %s skal udfyldes." % (cfg.TEXT_LABEL, cfg.PLANT_LABEL)
        done = "Gemt som "

    return (
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
        f"                AttachmentFolder: \"{att.LIBRARY}/\" & {key}\n"
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
    refresh = button("btnDomAttRefresh", '"Hent dokumenter"',
                     att.refresh_button_fx(), display_mode=DM_SEL)
    rem = button("btnDomAttRemove", '"Fjern dokument"', att.delete_fx(),
                 danger=True, display_mode=DM_SEL)
    actions = button_row("conDomAttActions", [up, refresh, rem], PANE_W)

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
    # NY fane her, og kun her. Navigation mellem apps bruger Replace, saa
    # der ikke bliver en fane pr. klik - men et dokument er ikke en app.
    # Replace ville smide appen vaek, og en halvudfyldt formular med den.
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
# Beskrivelseskolonnen tager RESTEN af bredden - men hoejst 460.
#
# Uden loftet aad den alt: paa en bred skaerm blev den over tusind pixels,
# de oevrige kolonner blev skubbet helt ud til hoejre kant, og imellem dem
# laa en tom flade paa halvdelen af vinduet. En tabel skal vaere saa bred
# som sit indhold, ikke som sin beholder.
MAIN_W = f"Max(Min(Parent.Width - {FIXED}, 460), 150)"

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
    # Samme regel som paa vaerkfeltet: Default er en RECORD fra Items.
    filt = '["alle", "draft", "valid", "submitted"]'
    status = dropdown("drpDomStatusFilter", filt,
                      f'LookUp({filt}, Value = "alle")', width="160")
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
                           width=cfg.LIST_COLS[-2][1], wrap="false"))
    # En knap, ikke kun et klik paa raekken. Galleriets OnSelect virker
    # ogsaa, men den er usynlig - der er intet, der siger at raekken KAN
    # aabnes, og saa er det de faerreste der proever.
    cells.append(button("btnDomRowOpen", '"Aabn"', load_row_fx(),
                        width=cfg.LIST_COLS[-1][1], height=28))

    # align_items="Start" og ikke Stretch: raekken skal vaere saa bred som
    # sine celler, ikke som skabelonen - ellers straekkes den sidste celle
    # ud over den tomme flade til hoejre.
    row = group("conDomRow", pin_widths(cells), direction="Horizontal", gap=GAP,
                height="Parent.TemplateHeight - 2", align_items="Center",
                justify="Start", width="Parent.TemplateWidth")

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
    Ellers ville "Send som kladde" og derefter "Indsend" give TO raekker
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
    label = "Indsendt" if submit else "Gemt som kladde"
    empty = ("Der er ingen faerdige raekker at indsende."
             if submit else "Der er ingen raekker at gemme.")

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
        '& " raekke(r)",\n'
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
        "        Patch(\n"
        f"            {cfg.L_ROWS},\n"
        "            ForAll(\n"
        f"                {rows} As R,\n"
        f"                LookUp({cfg.L_ROWS}, ID = R.RowId)\n"
        "            ),\n"
        "            ForAll(\n"
        f"                {rows} As R,\n"
        "                {\n"
        + "\n".join(row_patch) + "\n"
        "                }\n"
        "            )\n"
        "        );\n"
        "\n"
        + refresh_rows_fx(8) + ";\n"
        "\n"
        f'        Set(varDomInfo, "{label}: " & varDomRequestNo);\n'
        f'        Notify("{label} som " & varDomRequestNo & " - se den paa '
        'landingssiden.", NotificationType.Success),\n'
        "\n"
        '        Set(varDomInfo, "Det fejlede: " & FirstError.Message);\n'
        '        Notify("Det fejlede: " & FirstError.Message, '
        "NotificationType.Error)\n"
        "    )\n"
        ")"
    )


def build_submit():
    draft = button(
        "btnDomSendDraft", '"Gem som kladde"', send_fx(False), width=180,
        display_mode=f'If(CountRows({SENDABLE}) = 0, DisplayMode.Disabled, DisplayMode.Edit)')
    submit = button(
        "btnDomSubmit", '"Indsend"', send_fx(True), primary=True, width=150,
        display_mode=f'If(CountRows({VALID}) = 0, DisplayMode.Disabled, DisplayMode.Edit)')
    # "Hent forfra" stod BEGGE steder - her og paa dokumentruden - og
    # betoed to forskellige ting. Nu siger navnet hvad der hentes.
    reload_ = button("btnDomReload", '"Hent raekker forfra"',
                     refresh_rows_fx() + ';\nSet(varDomInfo, "Hentet forfra.")',
                     width=150)
    note = text_ctrl(
        "txtDomSubmitNote",
        ('"Send som kladde laegger indmeldingen paa landingssiden med status '
         'Kladde - den kan stadig rettes. Indsend laaser raekkerne og saetter '
         'status til Indsendt. Begge skriver i den SAMME raekke i indekset."'),
        size=12, color=C_MUTED, height=18, wrap="false")
    state = text_ctrl(
        "txtDomSubmitState",
        ('If(\n'
         '    IsBlank(varDomRequestNo),\n'
         '    "Indmeldingen er ikke sendt til hubben endnu.",\n'
         '    "Indmelding " & varDomRequestNo & " ligger paa landingssiden."\n'
         ')'),
        size=13, height=20, wrap="false")
    return card("conDomSubmitCard",
                [state,
                 button_row("conDomSubmitRow", [draft, submit, reload_], SHELL_W),
                 note])
