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

from gen_screen import (Ctrl, SHELL_W, C_CARD_BORDER, C_TITLE, C_MUTED,
                        C_MUTED_BG, C_REQUIRED, C_PRIMARY, C_WHITE,
                        C_TRANSPARENT, C_NEUTRAL_BG, C_NEUTRAL_FG, C_INFO_FG,
                        C_INFO_BG, C_VALID_FG, C_VALID_BG, C_WARN_FG,
                        C_WARN_BG, C_MODAL_BG, C_PRIMARY_SOFT, C_OVERLAY)
import layout_tokens as lay
from layout_tokens import fits, if_below, below, at_least
from build_helpers import (tap_backdrop, text_ctrl, text_min_height, group, button, text_input,
                           checkbox_theme, date_picker, fit_button_row,
                           fit_button_width, number_input, themed_dropdown,
                           card, field_cell, pin_widths, badge, top_bar, grow,
                           flow_row, label_px, text_px, loading_overlay,
                           with_busy, confirm_modal, edit_button, delete_button, delete_modal, ICON_SAVE, ICON_SUBMIT,
                           ICON_W, icon_on_mobile, new_text_on_mobile)

# Mens en gemning koerer, staar ventespinneren oven paa skaermen (issue #54).
SAVING_VAR = "varDomSaving"

# Appens "Data row limit" (Studio -> Settings). Standard er 500. Rammer
# raekkespejlet det, mangler de aeldste raekker - taelleren siger det.
# Haeves graensen i Studio (maks 2000), skal tallet her foelge med.
ROW_LIMIT = 500
# Bekraeftelsen foer Submit.
CONFIRM_VAR = "varDomConfirmSubmit"
# Sletning sker bag en bekraeftelse: hvilken raekke, og om popuppen er aaben.
DELETE_ID = "varDomDeleteId"
DELETE_VAR = "varDomConfirmDelete"
from layout_tokens import SCROLLBAR_W
import domain_config as cfg
import attflows
import doc_upload as du
import messages as msg
import admin_log as alog
import permissions as perm
import request_index as ri

# Flowkontrakten staar i tools/attflows.py; ruden her er dens
# domaeneudgave - samme tre flows, egne samlingsnavne.
att = attflows.DomainPane()
from fl_picker import fl_picker, known_fx as fl_known_fx, reset_fx as fl_reset_fx

# Raekkens felter i een flad liste - raekkefoelgen er sektionernes.
FIELDS = [f for _sec, fields in cfg.SECTIONS for f in fields]
# BETINGEDE FELTER (opt-in, issue #210)
# -------------------------------------
# cfg.WHEN = { kolonne: Power Fx-udtryk }. Et felt med et udtryk vises kun,
# naar udtrykket er sandt, og dets vaerdi RYDDES ved gem, saa en aendret
# type ikke efterlader gamle vaerdier i raekken.
#
# Equipment og Materials har ingen WHEN, og deres skaermes YAML er derfor
# ordret den samme som foer - det er hele pointen med at det er opt-in.
WHEN = dict(getattr(cfg, "WHEN", {}))

# Felter, der skal skrives af appen i stedet for af brugeren (opt-in):
# { kolonne: Power Fx-udtryk }. Measuring Point bruger den til IsCounter og
# ApprovalRequired, der er AFLEDT af typen (issue #210 Q14/Q16). Kolonnerne
# staar i cfg.READ_FIELDS, saa de hentes og vises, men ikke tastes.
EXTRA_PATCH = dict(getattr(cfg, "EXTRA_PATCH", {}))

# Raekkens felter i SAMLINGEN: formularens plus dem, appen kun laeser
# (cfg.READ_FIELDS, fx Equipments SAP-udstyrsnummer - issue #94). De
# hentes og vises, men skrives aldrig af formularen.
ROW_FIELDS = FIELDS + list(getattr(cfg, "READ_FIELDS", []))

_COLS = {c for c, _l, _k, _ch in FIELDS}
_unknown = sorted(set(WHEN) - _COLS)
if _unknown:
    raise SystemExit("domain_config.WHEN naevner felter, der ikke staar i "
                     "SECTIONS: %s" % ", ".join(_unknown))
_READ_COLS = {c for c, _l, _k, _ch in getattr(cfg, "READ_FIELDS", [])}
_unknown = sorted(set(EXTRA_PATCH) - _READ_COLS)
if _unknown:
    raise SystemExit("domain_config.EXTRA_PATCH naevner felter, der ikke staar i "
                     "READ_FIELDS: %s" % ", ".join(_unknown))


def use(expected):
    """Stop, hvis modulet er bygget til en ANDEN apps domain_config.

    FIELDS, SEARCH, LIST_SCOPE og CELL_W regnes af cfg, naar modulet
    importeres. To apps i samme proces ville derfor tavst give den anden
    app den foerstes felter (REVIEW.md C2). Hver app bygges i sin egen
    proces (build_all, BIO SAP); tools/domain_app.py kalder use(cfg), saa
    en fremtidig indgang, der blander dem, stopper hoejlydt i stedet."""
    if expected is not cfg:
        raise SystemExit(
            "domain_parts er importeret til %s (%s), men kaldt med %s (%s).\n"
            "Byg hver domaeneapp i sin egen proces."
            % (cfg.APP_KEY, cfg.__file__, expected.APP_KEY, expected.__file__))

ROW_H = 44
GAL_ROWS = 8

# Arbejder brugeren som ADMIN i en andens anmodning? varDomIdx er den
# aabne anmodnings indeksraekke (open_request_fx / send_fx); uden GUID er
# der ingen aaben anmodning, og varDomIdx kan vaere en gammel vaerdi.
# Saa vises den anmodnings raekker i stedet for brugerens egne, og ejeren
# bevares paa alt, der gemmes (tools/permissions.py).
AS_ADMIN = ('(!IsBlank(varDomRequestGuid) && !IsBlank(varDomIdx) && '
            'varDomIdx.RequestGuid = varDomRequestGuid && '
            '!(' + perm.is_owner("varDomIdx.RequesterEmail", "varDomMe") + '))')

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
DM_ROW = ('If(varDomViewOnly || varDomRowStatus = "submitted", DisplayMode.View, DisplayMode.Edit)')

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
# Dokumentpopuppen haenger paa DEN raekke, den er aabnet for. Der maa
# laegges op og slettes, naar anmodningen kan redigeres - samme laas som
# DM_ROW (varDomViewOnly og en indsendt raekke, som SAP-processen ejer).
# Ellers kan dokumenterne kun aabnes (issue #134).
DOCS_EDIT = ('(!IsBlank(varDomDocsId) && !IfError(varDomViewOnly, false) && '
             'LookUp(colDomRows, RowId = varDomDocsId).Status <> "submitted")')
# Luk dokumentpopuppen: glem de valgte filer og omgangens svar.
DOCS_CLOSE = "Set(varDomDocsId, Blank());\n" + att.close_fx()
DM_SEL = ('If(IsBlank(varDomActiveRowId), DisplayMode.Disabled, DisplayMode.Edit)')
# Ordet for anmodningen i Edit/Delete: "equipment request" / "material request".
WHAT = f"{cfg.DOMAIN.lower()} request"
# Raekkens slet-ikon i listen (issue #94): kun mens anmodningen kan
# redigeres (varDomViewOnly er den eksisterende laas), og aldrig paa en
# indsendt raekke - den ejes af SAP-processen.
DM_ROW_DEL = ('If(varDomViewOnly || ThisItem.Status = "submitted", '
              "DisplayMode.Disabled, DisplayMode.Edit)")
# Raekkens Edit (issue #101): SAMME regel som slet-ikonet. Kan raekken
# ikke redigeres, er Details vejen til at se den.
DM_ROW_EDIT = DM_ROW_DEL


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
    # Same header actions as Functional Location: Save draft, Submit, New request.
    def sized(btn, icon):
        w = fit_button_width(btn.props["Text"]) + (ICON_W if icon else 0)
        btn.props["Width"] = str(w)
        btn.props["LayoutMinWidth"] = str(w)
        return btn

    save = sized(button(
        "btnDomSendDraft", '"Save draft"', with_busy(SAVING_VAR, send_fx(False)),
        icon=ICON_SAVE,
        display_mode=f'If(varDomViewOnly || CountRows({SENDABLE}) = 0, DisplayMode.Disabled, DisplayMode.Edit)',
        tooltip='"Put the request on the landing page as Draft - rows stay editable"'),
        True)
    submit = sized(button(
        "btnDomSubmit", '"Submit"', f"Set({CONFIRM_VAR}, true)", primary=True,
        icon=ICON_SUBMIT,
        display_mode=f'If(varDomViewOnly || CountRows({VALID}) = 0, DisplayMode.Disabled, DisplayMode.Edit)',
        tooltip='"Submit the valid rows - they are locked afterwards (asks first)"'),
        bool(ICON_SUBMIT))
    new = sized(button(
        "btnDomNewRequest", '"New request"',
        'Set(varDomRequestGuid, "");\nSet(varDomRequestNo, "");\nSet(varDomViewOnly, false);\nSet(varDomCanEdit, false);\n' + clear_form_fx(),
        icon="Add", tooltip='"Start a new request - your saved rows stay in SharePoint"'),
        True)
    # Edit og Delete er VH-planens (issue #94): de faelles knapper i
    # build_helpers, samme synlighed, placering og ikon-kun under Tablet.
    # varDomCanEdit er sat af tools/permissions.may_change ved aabningen.
    edit = edit_button("btnDomEditRequest", "varDomViewOnly", "varDomCanEdit",
                       "Set(varDomViewOnly, false)", what=WHAT,
                       tooltip=f'"Edit this {WHAT}"')
    narrow = below("Tablet")
    save.props["Width"] = f"If({narrow}, 40, {save.props['Width']})"
    save.props["Layout"] = f"If({narrow}, ButtonLayout.IconOnly, ButtonLayout.IconBefore)"
    new_text_on_mobile(new, new.props["Width"])
    return top_bar("Dom", f'"{cfg.TITLE}"', f'"{cfg.SUBTITLE}"',
                   [edit, delete_button("Dom", "varDomViewOnly", "varDomRequestGuid", WHAT), save, submit, new],
                   icon=cfg.APP_KEY, mode_var="varDomViewOnly", num_var="varDomRequestNo")


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
    # Praefikset foelger kontroltypen (REVIEW.md A4): inp = tekst,
    # num = tal, dte = dato.
    name = {"num": "numDom", "date": "dteDom"}.get(kind, "inpDom") + col
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
    if kind == "dec":
        # TAL MED DECIMALER, TASTET SOM TEKST (issue #210)
        #
        # ModernNumberInput har heltalspraecision (build_helpers.
        # number_input saetter Precision '0'), og en maaling kan have op
        # til tre decimaler. Feltet er derfor et tekstfelt, og _patch_value
        # sender Value(...) til Number-kolonnen. Variablen er TEKST, saa
        # "ikke udfyldt" kan skelnes fra 0.
        return text_input(name, v, max_length=20, display_mode=DM_ROW,
                          onchange=f"Set({v}, Self.Text)")
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
        # themed_dropdown tager TEKSTEN og slaar selv recorden op til
        # ModernDropdown.Default.
        items = "[" + ", ".join(f'"{x}"' for x in choices) + "]"
        return themed_dropdown(name, items, v, display_mode=DM_ROW,
                               onchange=f"Set({v}, Self.Selected.Value)")
    if kind == "bool":
        # Ja/nej. Samme ModernCheckbox som dokumentlisten bruger - den er
        # bevist i dette miljoe. En app kan ogsaa vise feltet paa sin egen
        # maade (Materials: No BOM Item er en knap i formularens hoved).
        return Ctrl(name, "ModernCheckbox", props=checkbox_theme({
            "AccessibleLabel": f'"{name}"',
            "Default": v,
            "DisplayMode": DM_ROW,
            "Height": "36",
            "Label": '""',
            "OnCheck": f"Set({v}, true)",
            "OnUncheck": f"Set({v}, false)",
            "Width": "Parent.Width",
        }), h=36)
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

    Nu bygges den af build_helpers.themed_dropdown, der tager TEKSTEN og
    selv slaar recorden op til Default - fejl 1 kan ikke opstaa igen."""
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
    roed.

    lock gaar til fl_picker selv (issue #101): foer blev den lagt ind i
    DisplayMode her, og input_theme gjorde Disabled til View - feltet saa
    ud som et almindeligt, tomt felt. Nu er det Disabled og graat."""
    v = _var(cfg.FL_FIELD)
    return fl_picker(
        "Dom", combo=FL_COMBO, results="colDomFl", raw_var="varDomFlRaw",
        msg_var="varDomFlMsg", busy_var=FL_BUSY_VAR, query_var=FL_QUERY_VAR,
        last_var=FL_LAST_VAR, pick_var=v,
        default_items=f"Filter(colDomFl, Code = {v})",
        display_mode=DM_ROW, lock=lock,
        required_formula=required_formula, width=cell_w, stack_search=True)


def fl_reset_fx_dom():
    """Nulstil formularens FL-vaelger - og kun den (issue #72). Selve
    feltvaerdien ryddes af clear_form_fx sammen med de andre felter."""
    return fl_reset_fx(combo=FL_COMBO, results="colDomFl", msg_var="varDomFlMsg",
                       query_var=FL_QUERY_VAR, last_var=FL_LAST_VAR)


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
    if kind == "dec":
        # Tekstfeltets indhold ind i en Number-kolonne. Tom tekst skal
        # vaere Blank() og ikke 0: 0 er en maaling, tom er "ikke udfyldt".
        return (f'If(IsBlank(Trim(Coalesce({v}, ""))), Blank(), '
                f'IfError(Value(Trim({v})), Blank()))')
    return v


def refresh_rows_fx(indent=0):
    """Spejlet af listen. Samlingen er ALDRIG sandheden - den hentes
    forfra efter hver skrivning, saa det, skaermen viser, er det, der staar
    i SharePoint.

    Brugerens egne raekker - eller, naar en admin har aabnet en andens
    anmodning, DEN anmodnings raekker (AS_ADMIN). To hele ClearCollect i
    en If, saa hvert filter delegeres for sig."""
    pad = " " * indent
    mine = _collect_rows(f"Filter({cfg.L_ROWS}, RequesterEmail = varDomMe)")
    theirs = _collect_rows(f"Filter({cfg.L_ROWS}, RequestGuid = varDomRequestGuid)")
    ind = lambda t: "\n".join("    " + l for l in t.split("\n"))
    body = f"If(\n    {AS_ADMIN},\n{ind(theirs)},\n{ind(mine)}\n)"
    return "\n".join(pad + l for l in body.split("\n"))


def _collect_rows(source):
    lines = [
        "ClearCollect(",
        "    colDomRows,",
        "    ForAll(",
        # Nyeste foerst: rammer listen appens data row limit, er det de
        # AELDSTE raekker, der ikke hentes - ikke tilfaeldige (REVIEW.md B4).
        f'        SortByColumns({source}, "Created", SortOrder.Descending) As R,',
        "        {",
        "            RowId: R.ID,",
        "            ItemKey: Coalesce(R.ItemKey, \"\"),",
        "            RequestNo: Coalesce(R.RequestNo, \"\"),",
        "            Status: Coalesce(R.RowStatus.Value, \"valid\"),",
        "            FileCount: Coalesce(R.FileCount, 0),",
        f"            {cfg.C_TEXT}: Coalesce(R.{cfg.C_TEXT}, \"\"),",
        "            Plant: Coalesce(R.Plant, \"\"),",
    ]
    for col, _lab, kind, _ch in ROW_FIELDS:
        if kind in ("text", "long", "choice"):
            v = f'Coalesce(R.{col}, "")'
        elif kind == "dec":
            # Tallet som TEKST, saa formularens tekstfelt kan vise det
            # praecis som det staar - og tom betyder tom (issue #210).
            v = f'If(IsBlank(R.{col}), "", Text(R.{col}))'
        elif kind == "bool":
            v = f"Coalesce(R.{col}, false)"
        elif kind == "num":
            v = f"R.{col}"
        else:
            v = f"R.{col}"
        lines.append(f"            {col}: {v},")
    lines[-1] = lines[-1].rstrip(",")
    lines += ["        }", "    )", ")"]
    return "\n".join(lines)



def open_request_fx():
    """Dyblinket fra hubben (?reqid=): fortsaet DEN anmodning.

    Her stod intet - Equipment og Material laeste aldrig Param("reqid").
    "Open" fra hubben aabnede derfor en ny session med tom GUID, og naeste
    kladde oprettede en NY indeksraekke, mens den gamle "Kladde" blev
    staaende for evigt (REVIEW.md D18).

    EN INDSENDT ANMODNING AABNES I VIEW MODE (issue #94)
    ----------------------------------------------------
    Her blev en indsendt anmodning smidt vaek: GUID og nummer blev
    nulstillet, og skaermen stod med en ny, tom anmodning i Edit mode.
    Nu er det VH-planens metode (Maintenance Plan App/build/build_load.py):
    anmodningen aabnes altid, varDomCanEdit afgoeres af
    tools/permissions.may_change (ejer i Kladde, admin i Kladde og
    AfventerInfo), og alt andet - indsendt eller laast - staar i View mode
    uden Edit og Delete. Gem og Submit er slaaet fra i View mode, saa en
    indsendt anmodning kan ikke skrives tilbage til Kladde (D19); en ny
    kladde startes med New request.

    Opslaget maaler mod varDomRequestGuid, der er sat lige foer - ikke mod
    Param(), som ikke er "ens for alle raekker" i delegeringens forstand."""
    return (
        "If(\n"
        '    !IsBlank(Param("reqid")) && varDomRequestGuid <> Param("reqid"),\n'
        '    Set(varDomRequestGuid, Param("reqid"));\n'
        f"    Set(varDomIdx, LookUp({cfg.L_INDEX}, RequestGuid = varDomRequestGuid));\n"
        "    If(\n"
        "        IsBlank(varDomIdx),\n"
        '        Notify("Could not find the request behind this link. Rows you save start a new request.",\n'
        "            NotificationType.Warning);\n"
        '        Set(varDomRequestGuid, ""); Set(varDomRequestNo, ""),\n'
        "        Set(varDomRequestNo, varDomIdx.RequestNo);\n"
        # Edit for the owner of a draft, and for an admin (tools/permissions.py);
        # everyone else stays in View.
        "        Set(varDomCanEdit, "
        + perm.may_change("varDomIdx.RequesterEmail", "varDomIdx.Status.Value", "varDomMe") + ");\n"
        "        Set(varDomViewOnly, !(Lower(Coalesce(Param(\"mode\"), \"\")) = \"edit\" && varDomCanEdit))\n"
        "    )\n"
        ")"
    )


def clear_form_fx():
    lines = ['Set(varDomActiveRowId, Blank());',
             'Set(varDomRowStatus, "valid");',
             f'Set({REQUIRED}, false);',
             'Set(varDomFText, "");',
             'Set(varDomFPlant, "");']
    for col, _lab, kind, _ch in FIELDS:
        lines.append(f"Set({_var(col)}, {_blank(kind)});")
    lines.append(fl_reset_fx_dom() + ";")
    lines.append('Set(varDomInfo, "")')
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
    # cfg.COPY_SKIP: felter, der IKKE maa foelge med i en kopi (opt-in).
    # Measuring Point bruger den til det eksisterende maalepunktsnummer -
    # to raekker kan ikke vaere det samme punkt (issue #210).
    skip = set(getattr(cfg, "COPY_SKIP", ()))
    for col, _lab, kind, _ch in FIELDS:
        if col in skip:
            lines.append(f"Set({_var(col)}, {_blank(kind)});")
            continue
        lines.append(f"Set({_var(col)}, ThisItem.{col});")
    # Dokumenterne foelger IKKE med. De ligger i en mappe, der hedder den
    # gamle raekkes noegle, og kopien har ingen noegle endnu.
    if getattr(cfg, "FL_FIELD", None):
        lines.append(_fl_known_fx(f"ThisItem.{cfg.FL_FIELD}"))
    lines.append('Set(varDomInfo, "Copied to a new row - not saved yet. '
                 'Documents were not copied.")')
    return "\n".join(lines)


def delete_this_row_fx():
    """Listens slet-ikon: slet DEN raekke, ikonet sidder paa - bag en
    bekraeftelse (build_delete_confirm). Det er den eneste vej til at slette
    en raekke; formularens "Delete row" er fjernet (issue #94)."""
    return f"Set({DELETE_ID}, ThisItem.RowId);\nSet({DELETE_VAR}, true)"

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
    vis = "!IsBlank(varDomDetailsId) || !IsBlank(varDomDocsId)"
    # Mens en upload koerer, lukker et tryk udenfor IKKE (issue #134).
    return tap_backdrop("conDomBackdrop", vis,
                        f"If(!{att.busy}, Set(varDomDetailsId, Blank()); {DOCS_CLOSE})")


DENIED_OTHER = ('Notify("You can only change your own requests.", '
                'NotificationType.Warning)')


def _indent(text, n):
    return "\n".join(" " * n + l for l in text.split("\n"))


def _diff_pairs():
    """(etiket, gammel vaerdi i raekken o, ny vaerdi i formularen)."""
    pairs = [(cfg.TEXT_LABEL, f"o.{cfg.C_TEXT}", "varDomFText"),
             (cfg.PLANT_LABEL, "o.Plant", "varDomFPlant")]
    for col, label, _kind, _ch in FIELDS:
        pairs.append((label, f"o.{col}", _var(col)))
    return pairs


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
        v = _patch_value(col, kind)
        if col in WHEN:
            # ET SKJULT FELT GEMMES TOMT (issue #210)
            #
            # Skifter brugeren type, skal den gamle types vaerdier ikke
            # blive staaende paa raekken - saa ville SAP-ordren og
            # detaljerne vise et felt, formularen ikke laengere viser.
            v = f"If({WHEN[col]}, {v}, {_blank(kind)})"
        patch.append(f"            {col}: {v},")
    for col, fx in EXTRA_PATCH.items():
        patch.append(f"            {col}: {fx},")
    patch += [
        '            RowStatus: { Value: "%s" },' % status,
        # En admin i en andens anmodning gemmer raekken i EJERENS navn.
        f"            RequesterEmail: If({AS_ADMIN}, Lower(varDomIdx.RequesterEmail), varDomMe),",
        f"            RequesterName: If({AS_ADMIN}, varDomIdx.RequesterName, User().FullName)",
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
    # Rettigheden staar ogsaa i selve handlingen, ikke kun i UI'et.
    extra = (f"    {AS_ADMIN} && !{perm.IS_ADMIN},\n"
             f"    {DENIED_OTHER},\n")
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
        # Admin i en andens anmodning: hvad aendres? Formularen mod raekken,
        # som den stod i listen - foer den hentes igen (tools/admin_log.py).
        "    Set(varDomAdmNew, IsBlank(varDomActiveRowId));\n"
        "    Set(\n"
        "        varDomAdmDiff,\n"
        f"        If({AS_ADMIN} && !varDomAdmNew, With({{ o: {ACTIVE} }},\n"
        + _indent(alog.diff(_diff_pairs(), 'o.ItemKey & " "'), 12) + "\n"
        '        ), "")\n'
        "    );\n"
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
        # Id'et STRAKS. Stod det foerst efter noegle-Patchen, og fejlede den,
        # var raekken oprettet, men formularen stadig "ny" - og naeste Gem
        # lavede en dublet med Defaults().
        "    Set(varDomActiveRowId, varDomSpRow.ID);\n"
        "\n"
        # En admins NYE raekke i en andens anmodning skal hoere til DEN
        # anmodning - ellers forsvinder den fra listen (refresh_rows_fx).
        "    If(\n"
        f"        {AS_ADMIN} && Coalesce(varDomSpRow.RequestGuid, \"\") <> varDomRequestGuid,\n"
        "        Set(\n"
        "            varDomSpRow,\n"
        f"            Patch({cfg.L_ROWS}, varDomSpRow, {{ RequestGuid: varDomRequestGuid, RequestNo: varDomRequestNo }})\n"
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
        f'    Set(varDomRowStatus, "{status}");\n'
        f"    If(\n        {AS_ADMIN} && (varDomAdmNew || !IsBlank(varDomAdmDiff)),\n"
        + alog.write("varDomRequestGuid", "varDomRequestNo", alog.EDIT,
                     f'If(varDomAdmNew, "New row " & Coalesce(varDomSpRow.ItemKey, {key}), varDomAdmDiff)', 8)
        + "\n    );\n"
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


def delete_confirmed_fx():
    """Sletningen selv - koeres af bekraeftelsens "Delete".

    Her stod to sletninger (listen og formularen) direkte paa knapperne:
    uden bekraeftelse, uden IfError - brugeren fik "Row deleted" ogsaa
    naar SharePoint afviste - og uden spaerre for en INDSENDT raekke, som
    SAP-processen ejer (DM_ROW). Nu er der een, og den tjekker alle tre.

    Dokumenterne i biblioteket bliver staaende. Det er med vilje: en
    raekke, der fjernes ved et uheld, maa ikke tage bilagene med sig."""
    row = f"LookUp(colDomRows, RowId = {DELETE_ID})"
    return (
        "If(\n"
        f"    IsBlank({DELETE_ID}) || IsBlank({row}),\n"
        '    Notify("Select a row in the list first.", NotificationType.Warning),\n'
        "\n"
        f'    {row}.Status = "submitted",\n'
        '    Notify("A submitted row cannot be deleted.", NotificationType.Warning),\n'
        "\n"
        "    If(\n"
        "        IfError(\n"
        f"            Remove({cfg.L_ROWS}, LookUp({cfg.L_ROWS}, ID = {DELETE_ID}));\n"
        "            true,\n"
        '            Notify("Delete failed: " & FirstError.Message, NotificationType.Error);\n'
        "            false\n"
        "        ),\n"
        f"        RemoveIf(colDomAttachments, RowId = {DELETE_ID});\n"
        f"        If(varDomDetailsId = {DELETE_ID}, Set(varDomDetailsId, Blank()));\n"
        f"        If(varDomDocsId = {DELETE_ID}, Set(varDomDocsId, Blank()));\n"
        # Var det den aabne raekke, skal formularen ogsaa ryddes - ellers
        # staar der felter fra noget, der ikke findes.
        f"        If(\n            {AS_ADMIN},\n"
        + alog.write("varDomRequestGuid", "varDomRequestNo", alog.DELETE,
                     f'"Row " & LookUp(colDomRows, RowId = {DELETE_ID}).ItemKey & " deleted"', 12)
        + "\n        );\n"
        f"        If(varDomActiveRowId = {DELETE_ID},\n"
        "            " + clear_form_fx().replace("\n", "\n            ") + "\n"
        "        );\n"
        + refresh_rows_fx(8) + ";\n"
        '        Set(varDomInfo, "Row deleted. The documents remain in the library.");\n'
        '        Notify("Row deleted. The documents remain in the library.", '
        "NotificationType.Success)\n"
        "    )\n"
        ");\n"
        f"Set({DELETE_ID}, Blank())"
    )


def build_delete_confirm():
    """Bekraeftelsen foer sletning - [sloer, popup], som Submit's."""
    return confirm_modal(
        "DomDel", DELETE_VAR, "Delete row?",
        f'"Row " & LookUp(colDomRows, RowId = {DELETE_ID}).ItemKey & '
        '" is deleted in SharePoint. The documents remain in the library."',
        "Delete", with_busy(SAVING_VAR, delete_confirmed_fx()),
        "btnDomDeleteConfirm", icon="Delete")

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
    """Dokumentpopuppen (issue #134): den moderne Attachments-kontrol,
    een Upload, og listen over gemte filer med filtype, Open og Remove.
    Opbygningen er den faelles i tools/doc_upload.py."""
    edit = DOCS_EDIT
    pick = du.picker(att.picker, '"Choose documents to upload"', 10, 10, visible=edit,
                     display_mode=f"If({att.busy}, DisplayMode.Disabled, DisplayMode.Edit)")
    # 10 MB, ikke 50. Kontrollen holder filen i hukommelsen som base64, og
    # flowet sender den videre i samme form. En datablad eller en manual er
    # langt under.
    limits = du.limits_text("txtDomAttLimits", 10, 10, visible=edit)
    up = du.upload_button("btnDomAttUpload", att.picker, att.upload_fx(), att.busy,
                          visible=edit)
    refresh = button("btnDomAttRefresh", '"Refresh"', att.refresh_button_fx(),
                     width=fit_button_width('"Refresh"'), height=36,
                     accessible='"Refresh the document list"',
                     display_mode=f"If(IsBlank(varDomDocsId) || {att.busy}, "
                                  "DisplayMode.Disabled, DisplayMode.Edit)")
    refresh.props["LayoutMinWidth"] = refresh.props["Width"]
    actions = group("conDomAttActions", [refresh, up], direction="Horizontal", gap=8,
                    height=36, justify="End", align_items="Center")
    status = du.status_text("txtDomAttStatus", att)
    confirm = du.remove_confirm("DomAtt", att)

    file = "ThisItem.FileName"
    badge_ = du.type_badge("txtDomAttType", file)
    name = grow(text_ctrl("txtDomAttName", file, size=13, height=28, wrap="false"))
    link = du.open_button("btnDomAttOpen", "ThisItem.FileUrl", file)
    rem = du.remove_button("btnDomAttRemove", att, file, edit)
    row = group("conDomAttRow", pin_widths([badge_, name, link, rem]),
                direction="Horizontal", gap=10,
                height="Parent.TemplateHeight - 2", align_items="Center",
                width="Parent.TemplateWidth")

    # Filnavnet er raekkens noegle - der er INGEN LineId paa dokumenterne.
    # Hele listen staar i galleriet; er der flere, end popuppen kan vise,
    # scroller popuppens indhold (du.capped_body) - ikke galleriet i den.
    gal_h = f"CountRows({att.scope}) * {du.ROW_H}"
    gal = Ctrl("galDomAttachments", "Gallery", variant="Vertical", props={
        "AccessibleLabel": '"Documents on the selected row"',
        "BorderStyle": "BorderStyle.None",
        "Fill": C_TRANSPARENT,
        "FillPortions": "0",
        "Height": gal_h,
        "Items": f"Sort({att.scope}, FileName)",
        "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None",
        "Selectable": "false",
        "ShowScrollbar": "false",
        "TabIndex": "0",
        "TemplatePadding": "2",
        "TemplateSize": str(du.ROW_H - 2),
        "Width": "Parent.Width",
        "WrapCount": "1",
    }, children=[row], h=gal_h)

    empty = text_ctrl("txtDomAttEmpty", att.empty_text_fx(), size=13,
                      color=C_MUTED, height=36, wrap="true",
                      visible=f"IfError(CountRows({att.scope}) = 0, false)")
    ro = du.readonly_note("txtDomAttReadOnly", f"!IsBlank(varDomDocsId) && !{edit}")

    title = grow(text_ctrl(
        "txtDomAttH",
        '"Documents · " & Coalesce(LookUp(colDomRows, RowId = varDomDocsId).ItemKey, "")',
        size=lay.SIZE_CARD_TITLE, weight="Semibold", height=text_min_height(lay.SIZE_CARD_TITLE), wrap="false"))
    close = button("btnDomAttClose", '"Close"', DOCS_CLOSE,
                   width=84, height=32,
                   display_mode=f"If({att.busy}, DisplayMode.Disabled, DisplayMode.Edit)")
    head = group("conDomAttHead", [title, close], direction="Horizontal",
                 gap=12, align_items="Center")
    # Popuppen: 18 + 18 luft, hovedet og afstanden - resten er indholdet.
    body = du.capped_body("conDomAttBody",
                          [pick, limits, actions, status, confirm, gal, empty, ro],
                          f"App.Height - 40 - 36 - {head.h} - 14")
    modal = group("conDomAttModal", [head, body],
                  direction="Vertical", gap=14,
                  fill=C_MODAL_BG, border_color=C_PRIMARY_SOFT, radius=lay.RADIUS_MODAL,
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
           "btnDomRowCopy": 64, "btnDomRowDelete": 40}
# Knapper, der KUN er deres ikon (issue #94) - som VH-planens
# btnVhpOpDelete. Teksten bliver staaende som tilgaengelig etiket.
ROW_ICON = {"btnDomRowDelete": "Delete"}
ROW_BTN.update({n + "C": w for n, w in list(ROW_BTN.items())})
ROW_H_C = 128
GAL_ROWS_C = 5
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


def build_details(scope=None, extra=()):
    """Alle raekkens felter, med frem og tilbage mellem raekkerne.

    scope: det filter, listen viser (standard: LIST_SCOPE), saa frem og
    tilbage foelger det, brugeren ser.
    extra: appens egne kontroller NEDERST i feltlisten (opt-in) - en
    funktion, der faar udtrykket for raekken, eller en liste. Measuring
    Point laegger Master Datas felt til maalepunktsnummeret dér
    (issue #210). Equipment og Materials giver ingen, og deres popup er
    uaendret."""
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
                    size=lay.SIZE_CARD_TITLE, weight="Semibold",
                    height=text_min_height(lay.SIZE_CARD_TITLE), wrap="false")
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
    # Samme regel som raekkens Edit (DM_ROW_EDIT, issue #101): popuppen er
    # en ren visning, naar raekken ikke kan redigeres.
    edit = button("btnDomDetEdit", '"Edit this row"',
                  load_row_fx().replace("ThisItem.", f"{row}.")
                  + ";\nSet(varDomDetailsId, Blank())",
                  primary=True, width=130, height=30,
                  display_mode=DM_ROW_EDIT.replace("ThisItem.", f"{row}."))
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
    for n, (col, label, kind, _ch) in enumerate(ROW_FIELDS, start=len(rows)):
        if kind == "bool":
            v = f'If({row}.{col}, "Yes", "No")'
        elif kind == "dec":
            v = f'If(IsBlank({row}.{col}), "-", {row}.{col})'
        elif kind in ("num", "date"):
            v = f'If(IsBlank({row}.{col}), "-", Text({row}.{col}))'
        else:
            v = f'Coalesce({row}.{col}, "-")'
        rows.append(_detail_row(n, label, v))
    # Anmodningen, raekken hoerer til - den sidste kolonne i colDomRows,
    # der ikke stod her (issue #101: "all available columns").
    rows.append(_detail_row(len(rows), "Request no.", f'Coalesce({row}.RequestNo, "-")'))
    rows += list(extra(row) if callable(extra) else extra)

    # FELTLISTEN SCROLLER, POPUPPEN GOER IKKE. Equipment har nitten felter;
    # hoejere end en baerbar skaerm. Hovedet med Luk staar fast.
    box = group("conDomDetRows", rows, direction="Vertical", gap=6)
    natural = box.props["Height"]
    box.props["Height"] = f"Min({natural}, App.Height - 200)"
    box.h = box.props["Height"]
    box.props["LayoutOverflowY"] = "LayoutOverflow.Scroll"
    modal = group("conDomDetailsModal", [head, box], direction="Vertical",
                  gap=12, fill=C_MODAL_BG, border_color=C_PRIMARY_SOFT,
                  radius=lay.RADIUS_MODAL, pad=(lay.CARD_PAD,) * 4, width=DETAILS_W,
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
    # ET DOMAENE UDEN GODKENDELSE KAN GAA DIREKTE VIDERE (opt-in)
    #
    # cfg.SUBMIT_STATUS er den status, indeksraekken faar ved Submit.
    # Measuring Point saetter den til KlarTilSAP: en anmodning uden
    # Counter-godkendelse og uden manglende taeller gaar direkte til Master
    # Data (issue #210 Q12). Equipment og Materials saetter den ikke og
    # indsender som hidtil.
    status = getattr(cfg, "SUBMIT_STATUS", ri.SUBMITTED) if submit else ri.DRAFT
    # Samme tekster som i VH-plan og FL: "Saved as X" / "Submitted as X".
    # Her stod "Saved as draft", og beskeden blev "Saved as draft as EQ-..".
    label = "Submitted" if submit else "Saved"
    action = "Submit" if submit else "Save"
    # Efter Submit er anmodningen afleveret. Stod GUID og nummer tilbage,
    # patchede naeste "Save as draft" i samme session den INDSENDTE
    # indeksraekke tilbage til Kladde. Naeste batch er en ny anmodning.
    after = (';\n        Set(varDomRequestGuid, "");\n'
             '        Set(varDomRequestNo, "")') if submit else ""
    # Indeksraekken er den samme i alle apps - tools/request_index.py.
    index_rec = ri.record(
        cfg.DOMAIN, cfg.APP_KEY, status,
        request_no="Coalesce(varDomRequestNo, varDomRequestGuid)",
        guid="varDomRequestGuid", me="varDomMe",
        # Ejeren bevares - ogsaa naar en admin gemmer en andens anmodning.
        owner='Coalesce(varDomIdx.RequesterEmail, varDomMe)',
        owner_name="Coalesce(varDomIdx.RequesterName, User().FullName)",
        current="varDomIdx",
        short_text=f'"{cfg.TITLE}: " & CountRows({rows}) & " row(s)"',
        plant=f"First({rows}).Plant", item_count=f"CountRows({rows})")
    # En admin, der indsender en andens anmodning, logges (tools/admin_log.py).
    admin_submit_log = ""
    if submit:
        admin_submit_log = (
            f"        If(\n            {AS_ADMIN},\n"
            + alog.write("varDomRequestGuid", "varDomRequestNo", alog.EDIT,
                         alog.submitted("varDomAdmFrom"), 12)
            + "\n        );\n")
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
        # Indeksraekken slaas op FRISK, foer der skrives: den er grundraekken
        # i Patch (samme ene opslag som foer) og afgoer, om brugeren maa.
        "    Set(\n"
        "        varDomIdx,\n"
        f"        If(!IsBlank(varDomRequestGuid), LookUp({cfg.L_INDEX}, RequestGuid = varDomRequestGuid))\n"
        "    );\n"
        "    If(\n"
        "        !IsBlank(varDomIdx) &&\n"
        "        !" + perm.may_change("varDomIdx.RequesterEmail", "varDomIdx.Status.Value", "varDomMe") + ",\n"
        '        Notify("This request can no longer be changed.", NotificationType.Warning),\n'
        "\n"
        "    IfError(\n"
        "        If(\n"
        "            IsBlank(varDomRequestGuid),\n"
        "            Set(varDomRequestGuid, Text(GUID()))\n"
        "        );\n"
        # Status foer - til admin-loggen ved Submit.
        "        Set(varDomAdmFrom, Coalesce(varDomIdx.Status.Value, \"\"));\n"
        "        Set(\n"
        "            varDomIdx,\n"
        "            Patch(\n"
        f"                {cfg.L_INDEX},\n"
        "                Coalesce(varDomIdx, Defaults(" + cfg.L_INDEX + ")),\n"
        f"                {index_rec}\n"
        "            )\n"
        "        );\n"
        "\n"
        "        // Foerste gang bliver indeksraekkens eget ID til nummeret\n"
        "        If(\n"
        "            IsBlank(varDomRequestNo),\n"
        f'            Set(varDomRequestNo, {ri.number_expr(cfg.PREFIX, "varDomIdx.ID")});\n'
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
        + admin_submit_log +
        "\n"
        f'        Set(varDomInfo, "{label}: " & varDomRequestNo);\n'
        f"        {(msg.submitted if submit else msg.saved)('varDomRequestNo')}"
        + after + ',\n'
        "\n"
        f'        Set(varDomInfo, "{action} failed: " & FirstError.Message);\n'
        f"        {msg.failed(action)}\n"
        "    )\n"
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
        "Submit", with_busy(SAVING_VAR, send_fx(True)), "btnDomSubmitConfirm") + delete_modal(
        "Dom", "varDomRequestGuid", cfg.L_INDEX, cfg.DOMAIN, WHAT) + [
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


def field_grid_cell(col, required=False):
    """Et felt fra SECTIONS som celle i gitteret.

    Staar feltet i cfg.WHEN, faar cellen betingelsen som Visible - og
    forelderens hoejde taeller den kun med, naar den vises
    (gen_screen.stack_height)."""
    for c, label, kind, choices in FIELDS:
        if c == col:
            cell = grid_cell(f"conDom{c}", label, _input_for(c, kind, choices),
                             required=required)
            if c in WHEN:
                cell.vis = WHEN[c]
            return cell
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
        "inpDomDocsInfo",
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
    title = text_ctrl("txtDomFormH", f'"{title_txt}"', size=lay.SIZE_CARD_TITLE, weight="Semibold",
                      height=text_min_height(lay.SIZE_CARD_TITLE),
                      width=text_px(title_txt, lay.SIZE_CARD_TITLE), wrap="false")
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
         ')'), f"Min(290, {FORM_W} - 138)")
    meta_w = 130 + 8 + 290
    meta = group("conDomFormMeta", [plant, state], direction="Horizontal", gap=8,
                 height=28, align_items="Center")
    buttons = list(buttons)
    desk = sum(int(b.desk_w) for b in buttons) + 8 * (len(buttons) - 1)
    icon = sum(b.icon_w for b in buttons) + 8 * (len(buttons) - 1)
    for b in buttons:
        b.props["LayoutMinWidth"] = b.props["Width"]
    btn_row = group("conDomFormButtons", buttons, direction="Horizontal", gap=8, height=36,
                    align_items="Center", width=if_below("Tablet", str(icon), str(desk)))
    btn_row.props["LayoutMinWidth"] = btn_row.props["Width"]
    btn_row.props["AlignInContainer"] = "AlignInContainer.Start"
    actions = flow_row("conDomFormActions", [meta, btn_row], FORM_W, gap=8,
                       flex=meta, flex_min=meta_w)
    info = text_ctrl("txtDomFormInfo", "varDomInfo", size=12, color=C_MUTED,
                     height=18, wrap="false", visible="!IsBlank(varDomInfo)")
    return [actions, info]


def form_buttons(save_fx, save_text, new_text):
    """Save draft, Save og New row/Reset form - i den orden, med den
    primaere knap naestsidst som i HTML-projektet.

    "Delete row" stod foerst. Den er fjernet (issue #94): en gemt raekke
    slettes med ikonet paa sin egen raekke i Saved Rows, som i VH-planens
    operationstabel. form_footer regner bredden af de knapper, der er, saa
    pladsen forsvinder med knappen.

    save_fx(status) er appens gem (save_row_fx med evt. egne krav)."""
    return [
        icon_on_mobile(fit(button("btnDomSaveDraft", '"Save row draft"',
                   with_busy(SAVING_VAR, save_fx("draft")),
                   display_mode=DM_ROW, icon=ICON_SAVE,
        tooltip='"Save the row as a draft - only the description is required"'), icon=True)),
        icon_on_mobile(fit(button("btnDomSave", f'"{save_text}"',
                   with_busy(SAVING_VAR, save_fx("valid")),
                   primary=True, display_mode=DM_ROW, icon=ICON_SAVE,
        tooltip='"Save the row as complete, ready to submit"'), icon=True)),
        icon_on_mobile(fit(button("btnDomNew", f'"{new_text}"', clear_form_fx(), icon="Add",
        tooltip='"Clear the form and start a new row"'), icon=True)),
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
SEARCH = " || ".join(f"Trim(inpDomSearch.Text) in {c}" for c in cfg.SEARCH_FIELDS)
LIST_SCOPE = (
    "Filter(\n"
    "    colDomRows,\n"
    f"    (IsBlank(Trim(inpDomSearch.Text)) || {SEARCH}),\n"
    f'    (drpDomStatusFilter.Selected.Value = "{ALL_STATUS}" ||\n'
    "     Status = Lower(drpDomStatusFilter.Selected.Value)),\n"
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

# Knapperne. Raekkens handlinger er Details -> Edit -> Delete, i den
# raekkefoelge og yderst til hoejre (issue #101). Docs og Copy staar i
# MORE-kolonnen foran dem i Compact; i All columns er der ingen
# MORE-overskrift, og saa er de de foerste af handlingerne - overskriften
# "ACTIONS" flytter hen over dem.
MORE_BTNS = [("btnDomRowDocs", '"Docs"'), ("btnDomRowCopy", '"Copy"')]
ACTION_BTNS = [("btnDomRowDetails", '"Details"'), ("btnDomRowOpen", '"Edit"'),
               ("btnDomRowDelete", '"Delete row"')]
# Details aabner den eksisterende skrivebeskyttede popup (build_details).
DETAILS_FX = "Set(varDomDetailsId, ThisItem.RowId)"
# Knapperne, der kan laases - ens i tabellen og i Compact-kortet.
ROW_MODES = {"btnDomRowDelete": DM_ROW_DEL, "btnDomRowOpen": DM_ROW_EDIT,
             "btnDomRowCopy": "If(varDomViewOnly, DisplayMode.Disabled, DisplayMode.Edit)"}


def _btns_w(btns):
    """Bredderne er ROW_BTN - afproevet i Studio med 13 pt, og de klipper
    ikke teksten. En knap uden en bredde dér stopper byggeriet."""
    for n, _t in btns:
        if n not in ROW_BTN:
            raise SystemExit(f"domain_parts: {n} har ingen bredde i ROW_BTN")
    return sum(ROW_BTN[n] for n, _t in btns) + ROW_BTN_GAP * (len(btns) - 1)


LIST_MORE_W = _btns_w(MORE_BTNS) + CELL_PAD
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
    return f'If(IsBlank(ThisItem.{col}), "", Text(ThisItem.{col}, "{lay.DATE_FMT}"))'


class ListLayout:
    """Bredderne for et saet pladser i de to visninger.

    All columns har faste bredder. Compact FYLDER listens bredde: hver
    tekstkolonne faar sin mindstebredde (mindst saa bred som overskriften)
    plus en lige del af det, der er tilovers. Er der intet tilovers (en
    tablet), er tabellen sine mindstebredder og scroller vandret."""

    def __init__(self, slots, fixed=False):
        self.slots = slots
        # FAST LAYOUT (opt-in, issue #210): een visning, ingen Compact/All.
        # Alle pladser er "Compact"-pladsen, de fylder listens bredde, og
        # der er ingen varDomAllCols at skifte med.
        self.fixed = fixed
        self.all_ws = [col_w(a) for _c, a in slots]
        self.all_w = (BADGE_W + sum(self.all_ws) + LIST_MORE_W + LIST_ACTIONS_W
                      + T_GAP * (len(slots) + 2))
        self.compact = [i for i, (c, _a) in enumerate(slots) if c is not None]
        # Det, der ikke kan vokse: maerket, de to knapkolonner og gaps.
        # (Hed "fixed" og skyggede parameteren af samme navn.)
        fixed_w = BADGE_W + LIST_MORE_W + LIST_ACTIONS_W + T_GAP * (len(self.compact) + 2)
        self.compact_min = fixed_w + sum(col_w(slots[i][0]) for i in self.compact)
        self.spare = (f"Max(0, ({TABLE_AVAIL}) - {self.compact_min}) / "
                      f"{len(self.compact)}")
        self.table_w = (f"Max({self.compact_min}, {TABLE_AVAIL})" if self.fixed else
                        f"If({ALL_COLS}, {self.all_w}, "
                        f"Max({self.compact_min}, {TABLE_AVAIL}))")

    def width(self, i):
        c, a = self.slots[i]
        if self.fixed:
            return f"{col_w(c)} + {self.spare}"
        if c is None:
            return str(self.all_ws[i])
        cw = f"{col_w(c)} + {self.spare}"
        return cw if a is None else f"If({ALL_COLS}, {self.all_ws[i]}, {cw})"

    def visible(self, i):
        c, a = self.slots[i]
        if self.fixed:
            return None
        if c is None:
            return ALL_COLS
        if a is None:
            return f"!{ALL_COLS}"
        return None

    def text(self, i, part):
        """part 0 = overskriften, 1 = udtrykket."""
        c, a = self.slots[i]
        pick = (lambda s: f'"{s[0]}"') if part == 0 else (lambda s: s[1])
        if self.fixed:
            return pick(c)
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


def _icon_only(b, bn):
    """Er knappen i ROW_ICON, er den kun sit ikon - paa desktop og mobil."""
    if bn in ROW_ICON:
        b.props["Icon"] = f'"{ROW_ICON[bn]}"'
        b.props["Layout"] = "ButtonLayout.IconOnly"
    return b


def _row_buttons(name, btns, fxs, width, danger=(), modes=None):
    out = []
    for (bn, text), fx in zip(btns, fxs):
        # Raekkens noegle i label og tooltip: otte "Delete" efter hinanden
        # siger intet til en skaermlaeser (REVIEW.md D29/A17).
        who = f'{text} & " " & ThisItem.ItemKey'
        b = button(bn, text, fx, danger=bn in danger, width=ROW_BTN[bn],
                   height=ROW_BTN_H, display_mode=(modes or {}).get(bn),
                   accessible=who, tooltip=who)
        b.props["Size"] = "13"
        out.append(_icon_only(b, bn))
    return group(name, out, direction="Horizontal", gap=ROW_BTN_GAP, height=ROW_BTN_H,
                 width=width, align_items="Center", pad=(0, 0, 0, CELL_PAD))


def _compact_row(lay_, load_fx, copy_fx, delete_fx):
    """Card row below Desktop: key + status on top, the next values under it, the actions
    on two short lines. Replaces the wide table, which would scroll sideways on a phone."""
    cs = [lay_.slots[i][0] for i in lay_.compact]
    s = "ThisItem.Status"
    fg = (f'Switch({s}, "valid", {C_VALID_FG}, "submitted", {C_INFO_FG}, '
          f'"draft", {C_WARN_FG}, {C_NEUTRAL_FG})')
    bg = (f'Switch({s}, "valid", {C_VALID_BG}, "submitted", {C_INFO_BG}, '
          f'"draft", {C_WARN_BG}, {C_NEUTRAL_BG})')
    key = text_ctrl("txtDomRowKeyC", cs[0][1], size=14, weight="Semibold", height=22, wrap="false")
    key = grow(key)
    badge = text_ctrl("txtDomRowStatusC", f"Upper({s})", size=11, color=fg, weight="Semibold",
                      height=22, width=BADGE_W - 2 * CELL_PAD, wrap="false",
                      accessible=f'"Status: " & {s}',
                      extra={"Fill": bg, "Align": "Align.Center",
                             "RadiusBottomLeft": "6", "RadiusBottomRight": "6",
                             "RadiusTopLeft": "6", "RadiusTopRight": "6"})
    line1 = group("conDomRowLineC1", [key, badge], direction="Horizontal", gap=8, height=22,
                  align_items="Center")
    rest = " & \"  \u00b7  \" & ".join(f"Text({c[1]})" for c in cs[1:4])
    line2 = text_ctrl("txtDomRowMetaC", rest or '""', size=12, color=C_MUTED, height=18,
                      wrap="false")

    def btns(name, names, fxs, **kw):
        out = []
        for (bn, text), fx in zip(names, fxs):
            who = f'{text} & " " & ThisItem.ItemKey'
            b = button(bn + "C", text, fx, danger=bn in kw.get("danger", ()),
                       width=ROW_BTN[bn], height=ROW_BTN_H,
                       display_mode=(kw.get("modes") or {}).get(bn), accessible=who, tooltip=who)
            b.props["Size"] = "13"
            out.append(_icon_only(b, bn))
        return group(name, out, direction="Horizontal", gap=ROW_BTN_GAP, height=ROW_BTN_H,
                     align_items="Center")

    line3 = btns("conDomRowLineC3", ACTION_BTNS, [DETAILS_FX, load_fx, delete_fx],
                 danger=("btnDomRowDelete",), modes=ROW_MODES)
    line4 = btns("conDomRowLineC4", MORE_BTNS, [open_docs_fx(), copy_fx],
                 modes=ROW_MODES)
    return group("conDomRowC", [line1, line2, line3, line4], direction="Vertical", gap=4,
                 height="Parent.TemplateHeight - 2", align_items="Stretch",
                 width="Parent.TemplateWidth", pad=(8, CELL_PAD, 0, CELL_PAD),
                 visible=below("Desktop"))


def build_list(slots, badge_head, search_placeholder, views=True, fixed=False):
    """Kortet med de gemte raekker - og indsend under tabellen.

    slots: appens pladser (se ovenfor). badge_head: overskriften over
    statusmaerket ("STATUS" / "VALIDATION").
    views: skal der vaere Compact/All columns? Measuring Point har EET
    fast layout (issue #210 Q13), og saa er der ingen knapper at skifte
    med - og ingen varDomAllCols.
    fixed: pladserne er faste; kun den foerste af hvert par bruges."""
    if fixed and views:
        raise SystemExit("domain_parts.build_list: fixed kraever views=False "
                         "- et fast layout har ingen Compact/All.")
    lay_ = ListLayout(slots, fixed=fixed)

    # --- hovedet: titel, soegning og de to filtre ---------------------
    title = text_ctrl("txtDomRowsH", '"Saved Rows"', size=lay.SIZE_CARD_TITLE, weight="Semibold",
                      height=text_min_height(lay.SIZE_CARD_TITLE), wrap="false")
    search = text_input("inpDomSearch", '""', width="240",
                        placeholder=f'"{search_placeholder}"',
                        label='"Search the rows"')
    status = themed_dropdown(
        "drpDomStatusFilter", f'["{ALL_STATUS}", "Draft", "Valid", "Submitted"]',
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
    view_switch = group("conDomViewSwitch", [compact, allc], direction="Horizontal",
                        gap=8, height=32, align_items="Center", justify="End")

    # --- tabellen -----------------------------------------------------------
    heads = [_head_text("txtDomHeadStatus", f'"{badge_head}"', BADGE_W)]
    cells = [_status_badge()]
    for i in range(len(slots)):
        heads.append(_head_text(f"txtDomHead{i}", lay_.text(i, 0), lay_.width(i),
                                visible=lay_.visible(i), accessible=lay_.text(i, 0)))
        cells.append(_pad(text_ctrl(f"txtDomCell{i}", lay_.text(i, 1), size=13,
                                    height=20, width=lay_.width(i), wrap="false",
                                    visible=lay_.visible(i))))
    heads.append(_head_text("txtDomHeadMore",
                            '"MORE"' if fixed else f'If({ALL_COLS}, "ACTIONS", "MORE")',
                            LIST_MORE_W))
    heads.append(_head_text("txtDomHeadActions",
                            '"ACTIONS"' if fixed else f'If({ALL_COLS}, "", "ACTIONS")',
                            LIST_ACTIONS_W, accessible='"Actions"'))
    cells.append(_row_buttons("conDomRowMore", MORE_BTNS,
                              [open_docs_fx(), copy_row_fx()],
                              LIST_MORE_W, modes=ROW_MODES))
    cells.append(_row_buttons("conDomRowActions", ACTION_BTNS,
                              [DETAILS_FX, load_row_fx(), delete_this_row_fx()],
                              LIST_ACTIONS_W, danger=("btnDomRowDelete",),
                              modes=ROW_MODES))

    table_w = if_below("Desktop", TABLE_AVAIL, lay_.table_w)
    list_head = group("conDomListHead", heads, direction="Horizontal", gap=T_GAP,
                      height=34, width=table_w, align_items="Center", fill=C_MUTED_BG,
                      visible=at_least("Desktop"))
    row = group("conDomRow", cells, direction="Horizontal", gap=T_GAP,
                height="Parent.TemplateHeight - 2", align_items="Center",
                justify="Start", width="Parent.TemplateWidth", visible=at_least("Desktop"))
    row_c = _compact_row(lay_, load_row_fx(), copy_row_fx(), delete_this_row_fx())

    gal_h = (f"Max(Min(CountRows({LIST_SCOPE}), "
             + if_below("Desktop", str(GAL_ROWS_C), str(GAL_ROWS)) + f"), 1) * "
             + if_below("Desktop", str(ROW_H_C + 2), str(ROW_H + 2)))
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
        "TemplateSize": if_below("Desktop", str(ROW_H_C), str(ROW_H)),
        "Width": f"({table_w}) + 4 + {SCROLLBAR_W}",
        "WrapCount": "1",
    }, children=[row, row_c], h=gal_h)

    # Vandret scroll, naar tabellen er bredere end kortet (All columns, og
    # Compact paa en tablet). Start, ikke Stretch - check_layout regel 14.
    # Den vandrette scrollbar tager hoejde, saa den laegges til, naar den
    # er der.
    wide = f"(({table_w}) + 4 + {SCROLLBAR_W}) > ({FORM_W})"
    table = group("conDomTableWrap", [list_head, gal], direction="Vertical", gap=0,
                  overflow_x="Scroll", width="Parent.Width", align_items="Start")
    table.props["Height"] = f"{table.props['Height']} + If({wide}, {SCROLLBAR_W}, 0)"
    table.h = table.props["Height"]

    empty = None

    body = [head, view_switch, table] if views else [head, table]
    return card("conDomRowsCard", body + _submit_parts())


# ---------------------------------------------------------------------------
# Indsend - under tabellen, til hoejre. Selve indsendelsen er send_fx.
# ---------------------------------------------------------------------------
def _submit_parts():
    """Hvor indmeldingen staar - under tabellen.

    "Reload rows" stod her (issue #101: fjernet). Listen hentes allerede
    forfra efter hver gem og sletning (refresh_rows_fx i save_row_fx og
    delete_confirmed_fx), saa knappen gav kun et ekstra kald. Teksten staar
    nu alene og er kun synlig, naar der er en anmodning - ellers tager den
    ingen plads (hoejden regnes af Visible)."""
    state = text_ctrl(
        "txtDomSubmitState",
        ('If(\n'
         '    IsBlank(varDomRequestNo),\n'
         '    "",\n'
         '    "Request " & varDomRequestNo & " is on the landing page."\n'
         ')'),
        size=13, color=C_MUTED, height=20, wrap="false", visible="!IsBlank(varDomRequestNo)")
    return [state]
