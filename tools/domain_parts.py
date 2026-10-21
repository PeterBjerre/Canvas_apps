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

from gen_screen import (Ctrl, SHELL_W, C_WARN_FG, C_CARD_BORDER, C_TITLE, C_MUTED,
                        C_MUTED_BG, C_REQUIRED, C_PRIMARY, C_WHITE,
                        C_TRANSPARENT, C_ROW_PRESSED, C_NEUTRAL_BG,
                        C_MODAL_BG, C_PRIMARY_SOFT,
                        C_INVALID_FG)
import layout_tokens as lay
from layout_tokens import fits, if_below, below, at_least
from build_helpers import (row_rule, panel_save_fx, ensure_hit, close_x, popup_head, validation_summary, tap_backdrop, text_ctrl, text_min_height, group, button, text_input,
                           checkbox_theme, date_picker,
                           fit_button_width, number_field, num_value, themed_dropdown,
                           card, field_cell, pin_widths, top_bar, grow, flow_ok,
                           flow_row, label_px, text_px,
                           act_fx, act_mark, act_button, act_status, act_layers, icon_only_when,
                           confirm_modal, edit_button, delete_button, delete_modal, ICON_SAVE, ICON_SUBMIT,
                           ICON_W, icon_on_mobile, new_request_label, segmented, empty_state, breadcrumb,
                           request_actions, row_list, reset_click_fx, reset_confirm)

# Knappernes ventetilstand (issue #420, build_helpers.act_fx): handlingens
# noegle ("save", "submit", "duplicate", "delete", "add"), mens den koerer,
# og "<noegle>:ok"/":failed" bagefter. Foer var det varDomSaving og et graat
# sloer med en bjaelke midt paa skaermen.
ACT_VAR = "varDomAct"
# Sidepanelets gem-tilstand: "saving", "failed" eller tom (issue #402,
# build_helpers.panel_save_status).
PANEL_SAVE_VAR = "varDomPanelSave"

# Appens "Data row limit" (Studio -> Settings). Standard er 500. Rammer
# raekkespejlet det, mangler de aeldste raekker - txtDomRowsCap under
# tabellen og en advarsel ved Save/Submit siger det (R2-041).
# Haeves graensen i Studio (maks 2000), skal tallet her foelge med.
ROW_LIMIT = 500
ROWS_CAPPED = f"CountRows(colDomRows) >= {ROW_LIMIT}"
ROWS_CAP_MSG = (f"Only the newest {ROW_LIMIT} rows are shown - "
                "older rows are not included when you submit.")
# Bekraeftelsen foer Submit.
CONFIRM_VAR = "varDomConfirmSubmit"
# Listen over kladde-raekker efter Submit (UX-review M4, validation_summary).
FIX_VAR = "varDomFixOn"
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
import display_text as dt
import action_tips as tips
import status_chip as sc
import icons
import design_tokens as tok

# Ejeren maa rette og genindsende en anmodning, der er sendt retur (R2-014).
RESUBMIT = cfg.DOMAIN in perm.RESUBMIT_DOMAINS

# Vedhaeftningskontrakten staar i tools/attflows.py; ruden her er dens
# domaeneudgave - filerne er vedhaeftninger paa raekken i cfg.L_ROWS
# (issue #300).
att = attflows.DomainPane()
# Har appen dokumenter? Measuring Point har ikke (Peter, issue #300).
DOCS = bool(getattr(cfg, "DOCS_ENABLED", True))
from fl_picker import fl_picker, known_fx as fl_known_fx, reset_fx as fl_reset_fx

# Raekkens felter i een flad liste - raekkefoelgen er sektionernes.
FIELDS = [f for _sec, fields in cfg.SECTIONS for f in fields]
# BETINGEDE FELTER (opt-in, issue #210)
# -------------------------------------
# cfg.WHEN = { kolonne: Power Fx-udtryk }. Et felt med et udtryk vises kun,
# naar udtrykket er sandt, og dets vaerdi RYDDES ved gem, saa en aendret
# type ikke efterlader gamle vaerdier i raekken.
#
# Equipment har ingen WHEN, og dens skaerms YAML er derfor ordret den samme
# som foer - det er hele pointen med at det er opt-in. Materials bruger den
# til lagerfelterne og det erstattede materiale (issue #228).
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
# Felter, der er en CHOICE-kolonne i SharePoint (opt-in, issue #210).
# Appen holder teksten ("Yes", "Counter") i formularen og i colDomRows,
# men skriver { Value: ... } og laeser .Value. Equipment og Materials har
# tekstkolonner, saetter den ikke og genereres uaendret.
SP_CHOICE = set(getattr(cfg, "SP_CHOICE", ()))
_unknown = sorted(c for c in SP_CHOICE
                  if c not in {f for f, _l, k, _ch in FIELDS if k == "choice"})
if _unknown:
    raise SystemExit("domain_config.SP_CHOICE naevner felter, der ikke er et "
                     "'choice'-felt i SECTIONS: %s" % ", ".join(_unknown))
# SAP-FELTLAENGDER (R2-038). Beskrivelsen er SAP's korttekst (40 tegn) i
# alle domaener; cfg.MAX_LEN giver tekstfelter med en kortere SAP-laengde
# end listens 255 (opt-in - felter uden laengde genereres uaendret).
# MaxLength stopper kun tastaturet: Gem og Paste rows tjekker laengden
# ogsaa, saa en indsat, kopieret eller gammel vaerdi ikke gaar igennem.
TEXT_MAX = 40

# DECIMALTAL HAR FAST KULTUR (R2-075). "dec"-felter tastes som tekst og
# parses og vises i en-US - som resten af appens tal (layout_tokens.
# num_text). Foer fulgte de brugerens sprog, og "1.000" betoed tusind for
# een bruger og een for en anden. Feltet siger det i pladsholderen, og et
# komma stoppes ved gem, saa "1,5" ikke stiltiende bliver 15.
DEC_LANG = "en-US"
DEC_FMT = "0.###"
DEC_PLACEHOLDER = '"Use . as decimal separator"'


def dec_value(v):
    """Tekstens tal i appens faste kultur (R2-075)."""
    return f'Value(Trim({v}), "{DEC_LANG}")'
MAX_LEN = dict(getattr(cfg, "MAX_LEN", {}))
_unknown = sorted(c for c in MAX_LEN
                  if c not in {f for f, _l, k, _ch in FIELDS if k == "text"})
if _unknown:
    raise SystemExit("domain_config.MAX_LEN naevner felter, der ikke er et "
                     "'text'-felt i SECTIONS: %s" % ", ".join(_unknown))
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

ROW_H = 56
GAL_ROWS = 8

# ---------------------------------------------------------------------------
# APPENS EGNE KROGE (issue #204)
#
# Delene herunder er FAELLES. Skal den ene app noget mere - Materials'
# Object List, dens standardvaerdi i et felt, dens grupperede detaljer -
# hoerer koden i appens egen mappe, men de faelles dele skal kunne KALDE
# den. Derfor den her ene, navngivne kontrakt i stedet for en voksende
# raekke af undtagelser med appnavne i.
#
# Appens *_parts kalder configure() ved IMPORT (ikke i en build-funktion):
# delene kaldes af tools/domain_app.build_screen, og den ser kun modulet.
#
# Hver krog er domaeneneutral - der staar intet om materialer her:
#
#   field_defaults  {kolonne: udtryk} - vaerdien et felt faar, naar
#                   formularen ryddes (Materials: StorageBin = "X")
#   clear_extra     Power Fx efter clear_form_fx
#   load_extra      Power Fx efter load_row_fx (brug ThisItem.<kolonne>;
#                   detaljeruden erstatter "ThisItem." med sit opslag)
#   copy_extra      Power Fx efter copy_row_fx (efter at kopien er hentet
#                   ind i formularen, issue #485)
#   extra_patch     [(kolonne, udtryk)] - skrives med i save_row_fx ud
#                   over felterne i SECTIONS
#   extra_diff      [(etiket, gammelt udtryk paa o, nyt udtryk)] - appens
#                   egne vaerdier, der ikke er et felt (objektlisten, issue
#                   #485). Med i admin-loggens diff og i "er der ugemte
#                   aendringer?" paa en hentet raekke
#   patch_override  {kolonne: udtryk} - et felt fra SECTIONS, der gemmes
#                   som noget andet end sin egen variabel (Materials
#                   gemmer FL-kolonnen som den FOERSTE kode i objektlisten)
#   details_groups  [(overskrift, [kolonner])] - grupperet detaljerude.
#                   None = den flade liste som hidtil
#   details_hide    kolonner, detaljeruden ikke viser
#   details_open    Power Fx naar detaljeruden aabnes paa en raekke
#   details_nav     Power Fx ved Previous/Next i detaljeruden
#   details_rows    funktion(row) -> kontroller, der laegges i
#                   detaljeruden efter felterne
#   submit_guard    (foer, spaerret, besked) - Power Fx, der koeres naar
#                   Submit trykkes, et udtryk der betyder "kan ikke
#                   indsendes" og beskeden. Er det spaerret, aabner
#                   bekraeftelsen slet ikke (Materials: en strategisk
#                   raekke uden system eller uden systemansvarlig)
#   after_submit    Power Fx efter en LYKKET indsendelse, mens
#                   varDomRequestGuid stadig staar (Materials: start
#                   systemgodkendelsen)
#   row_actions     Saved Rows' knapper (issue #228). None = de faelles
#                   (Docs, Copy | Details, Edit, Delete). Ellers en liste
#                   af RowAction i den raekkefoelge, de skal staa - een
#                   ACTIONS-kolonne, og to linjer i mobilkortet
# ---------------------------------------------------------------------------
HOOKS = {
    "field_defaults": {},
    "clear_extra": "",
    "load_extra": "",
    "copy_extra": "",
    "extra_patch": (),
    "extra_diff": (),
    "patch_override": {},
    "details_groups": None,
    "details_hide": (),
    "details_open": "",
    "details_nav": "",
    "details_rows": None,
    "submit_guard": None,
    "after_submit": "",
    "row_actions": None,
}


def configure(**kw):
    """Appens kroge. Et ukendt navn er en tastefejl og stopper byggeriet."""
    unknown = set(kw) - set(HOOKS)
    if unknown:
        raise SystemExit("domain_parts.configure: ukendt krog %s" % sorted(unknown))
    HOOKS.update(kw)

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
PANEL_FORM_W = f"{lay.PANEL_W_AT} - 2 * 20 - 2 * 20 - {SCROLLBAR_W}"

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


def docs_cleanup_fx():
    """Glem dokumentrudens raekke, naar sidepanelet lukkes, eller der
    skiftes raekke (issue #393). Uden den blev varDomDocsId staaende efter
    Materials Documents-fane, og alt, der hang paa den (sloeret), blev
    staaende med. Ikke midt i en gemning - den skal have sin raekke.
    Tom uden sidepanel eller dokumenter: dér lukker popuppen sig selv."""
    if not (DOCS and getattr(cfg, "ROW_PANEL_ENABLED", False)):
        return ""
    return f"If(!{att.busy}, {DOCS_CLOSE.replace(chr(10), ' ')})"
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
def submit_press_fx():
    """Submit-knappen. Uden en vagt aabner den bare bekraeftelsen.

    MED en vagt (HOOKS["submit_guard"]) koeres appens eget tjek FOERST, og
    er indmeldingen spaerret, aabner bekraeftelsen slet ikke - brugeren
    faar beskeden om, hvad der mangler. Vagten staar her og ikke i
    send_fx, fordi den skal kunne stoppe POPUPPEN, ikke bare gemningen."""
    # Er der kladder, viser listen "Rows to fix" dem (UX-review M4) - de
    # gyldige kan stadig sendes, saa bekraeftelsen aabner som foer.
    open_confirm = (f"Set({FIX_VAR}, CountRows({DRAFTS}) > 0);\n"
                    f"Set({CONFIRM_VAR}, true)")
    if getattr(cfg, "ROW_PANEL_ENABLED", False):
        open_confirm = f"Set({CONFIRM_VAR}, true)"
    open_confirm = (f"If(\n    {PLANT_MIX},\n"
                    f"    Notify({PLANT_MIX_MSG}, NotificationType.Warning),\n"
                    "    " + open_confirm.replace("\n", "\n    ") + "\n)")
    if not HOOKS["submit_guard"]:
        return open_confirm
    before, blocked, message = HOOKS["submit_guard"]
    # En vagt uden noget, der skal koeres foerst (Materials uden
    # godkendelse, issue #228), er bare If'en.
    return ((f"{before};\n" if before else "") +
            "If(\n"
            f"    {blocked},\n"
            f"    Notify({message}, NotificationType.Warning),\n"
            f"    {open_confirm}\n"
            ")")


# EET VAERK PR. ANMODNING (R2-074, Peters beslutning). SAP-opretteren koerer
# pr. vaerk, og MD_RequestIndex.Plant og hubbens vaerkfilter har eet vaerk.
# Submit stoppes derfor, naar de faerdige raekker har mere end eet vaerk -
# baade foer bekraeftelsen (submit_press_fx) og i selve send_fx.
PLANT_MIX = 'CountRows(Distinct(Filter(colDomRows, Status = "valid"), Plant)) > 1'
PLANT_MIX_MSG = ('"A request can only cover one plant. The rows have plants " & '
                 'Concat(Distinct(Filter(colDomRows, Status = "valid"), Plant), Value, ", ") & '
                 '" - split them into one request per plant."')


# En ny anmodnings "session": raekker uden GUID, oprettet fra nu af, hoerer til
# den. 2 min. margen mod forskel mellem enhedens ur og SharePoints.
SESSION_FX = "Set(varDomSessionStart, DateAdd(Now(), -2, TimeUnit.Minutes))"
DUP_VIS = '!IsBlank(varDomRequestGuid)'


def duplicate_fx():
    """DUPLICATE (UX-review L2): kopier anmodningens raekker til en NY
    kladde, som brugeren ejer.

    Kopierne hentes fra LISTEN (Filter paa RequestGuid er delegerbar), ikke
    fra colDomRows, hvor valg og tal er laest om til tekst. Hver kopi faar
    sin egen ItemKey og mappe, som en ny raekke ved Gem - dokumenter,
    SAP-svar og godkendelser foelger ikke med. En indsendt raekke bliver
    "valid" igen; kopien er en ny anmodning uden GUID, som Save draft
    giver nummer."""
    cols = [cfg.C_TEXT, "Plant"] + [c for c, _l, _k, _ch in FIELDS]
    cols += [c for c, _e in HOOKS["extra_patch"]] + list(EXTRA_PATCH)
    seen, copy = set(), []
    for c in cols:
        if c not in seen:
            seen.add(c)
            copy.append(f"                    {c}: R.{c},")
    key = ri.row_key(cfg.PREFIX, "n.ID")
    return (
        "If(\n"
        "    IsBlank(varDomRequestGuid),\n"
        '    Notify("Save the request before you duplicate it.", NotificationType.Warning),\n'
        "    IfError(\n"
        # Kilden SKAL vaere en kopi: Power Fx afviser Patch mod den liste,
        # ForAll loeber over ("cannot operate on the same data source that
        # is used in ForAll", issue #265). Filter er delegerbar, og
        # samlingen beholder listens typer (valg er stadig poster).
        "        " + SESSION_FX + ";\n"
        f"        ClearCollect(colDomDupSrc, Filter({cfg.L_ROWS}, RequestGuid = varDomRequestGuid));\n"
        # Een Patch med tabeller opretter alle kopierne, en til giver dem
        # RowId, ItemKey og mappe ud fra de nye ID'er - ingen skrivning
        # inde i ForAll (regel 15, issue #342).
        "        With(\n"
        "            { created: Patch(\n"
        f"                {cfg.L_ROWS},\n"
        f"                ForAll(colDomDupSrc, Defaults({cfg.L_ROWS})),\n"
        "                ForAll(colDomDupSrc As R, {\n"
        + "\n".join(copy) + "\n"
        '                    RowStatus: { Value: If(R.RowStatus.Value = "submitted", "valid", Coalesce(R.RowStatus.Value, "valid")) },\n'
        '                    RequestGuid: "", RequestNo: "",\n'
        "                    RequesterEmail: varDomMe, RequesterName: User().FullName\n"
        "                })\n"
        "            ) },\n"
        "            Patch(\n"
        f"                {cfg.L_ROWS},\n"
        "                ForAll(created As n, { ID: n.ID }),\n"
        f"                ForAll(created As n, {{ RowId: n.ID, ItemKey: {key},\n"
        f'                    AttachmentFolder: "{attflows.LIBRARY}/" & {key} }})\n'
        "            )\n"
        "        );\n"
        '        Set(varDomRequestGuid, "");\n'
        '        Set(varDomRequestNo, "");\n'
        "        Set(varDomIdx, Blank());\n"
        "        Set(varDomViewOnly, false);\n"
        "        Set(varDomCanEdit, false);\n"
        + _indent(clear_form_fx(), 8) + ";\n"
        + refresh_rows_fx(8) + ";\n"
        f"        {act_mark(ACT_VAR, 'duplicate')};\n"
        '        Notify("Duplicated as a new draft request. Choose Save draft to keep it.", NotificationType.Success),\n'
        f"        {act_mark(ACT_VAR, 'duplicate', False)};\n"
        '        Notify("Could not duplicate the request: " & FirstError.Message, NotificationType.Error)\n'
        "    )\n"
        ")")


BAR_ACTIONS = []
# Hjulet og beskeden i bundbjaelken under Desktop (issue #420).
ACT_FOOT = []


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

    no_rows = f"CountRows({SENDABLE}) = 0"
    save = sized(button(
        "btnDomSendDraft", '"Save draft"', act_fx(ACT_VAR, "save", send_fx(False)),
        icon=ICON_SAVE,
        display_mode=f'If(varDomViewOnly || {no_rows}, DisplayMode.Disabled, DisplayMode.Edit)',
        # Hvorfor er den graa? (UX-review, Materials): "Add a row first".
        tooltip=(f'If(varDomViewOnly, "View mode - choose Edit to change the request", '
                 f'{no_rows}, "Add a row first", '
                 '"Put the request on the landing page as Draft - rows stay editable")')),
        True)
    submit = sized(button(
        "btnDomSubmit", '"Submit"', submit_press_fx(), primary=True,
        icon=ICON_SUBMIT,
        display_mode=f'If(varDomViewOnly || CountRows({VALID}) = 0, DisplayMode.Disabled, DisplayMode.Edit)',
        tooltip=(f'If(varDomViewOnly, "View mode - choose Edit to change the request", '
                 f'{no_rows}, "Add a row first", '
                 f'CountRows({VALID}) = 0, "Complete the required fields on a row first", '
                 f'CountRows({DRAFTS}) > 0, Text(CountRows({DRAFTS})) & " draft rows stay as drafts - '
                 'only the valid rows are submitted (asks first)", '
                 '"Submit the valid rows - they are locked afterwards (asks first)")')),
        bool(ICON_SUBMIT))
    # "New request" - den faelles tekst (build_helpers.new_request_label).
    new = new_request_label(button(
        "btnDomNewRequest", '"New request"',
        f'Set({ACT_VAR}, "");\n' + 'Set(varDomRequestGuid, "");\nSet(varDomRequestNo, "");\nSet(varDomViewOnly, false);\nSet(varDomCanEdit, false);\n' + SESSION_FX + ";\n" + refresh_rows_fx() + ";\n" + clear_form_fx(),
        tooltip='"Start a new request - your saved rows stay in SharePoint"'))
    # Edit og Delete er VH-planens (issue #94): de faelles knapper i
    # build_helpers, samme synlighed, placering og ikon-kun under Tablet.
    # varDomCanEdit er sat af tools/permissions.may_change ved aabningen.
    edit = edit_button("btnDomEditRequest", "varDomViewOnly", "varDomCanEdit",
                       "Set(varDomViewOnly, false)", what=WHAT,
                       tooltip=f'"Edit this {WHAT}"')
    # SAMME RAEKKEFOELGE SOM ALLE ANDRE DOMAENER (UX-review T1):
    # [New request] | [Edit] [Save draft] [Submit (N to fix)] [Delete].
    # Taelleren er raekkerne, der stadig er kladder - de sendes ikke med.
    dup = button("btnDomDuplicate", '"Duplicate"', act_fx(ACT_VAR, "duplicate", duplicate_fx()),
                 icon="Copy", visible=DUP_VIS,
                 tooltip='"Copy all rows to a new draft request - documents are not copied"')
    sized(dup, True)
    dup.props["Width"] = f"If({below('Tablet')}, 40, {dup.props['Width']})"
    dup.props["Layout"] = f"If({below('Tablet')}, ButtonLayout.IconOnly, ButtonLayout.IconBefore)"
    # "Saved"/"Save failed" lige foran Save draft (issue #420) - fra
    # Desktop; under Desktop staar de i bundbjaelken (ACT_FOOT). Mens der
    # gemmes, siger knappen det selv - intet hjul ved siden af (#441).
    # Kun Duplicate er sit ikon alene paa en telefon: dér staar hjulet i
    # bundbjaelken, mens den koerer.
    status = act_status("DomAct", ACT_VAR, ("save", "submit", "duplicate"),
                        visible=at_least("Desktop"))
    ACT_FOOT[:] = act_status("DomFootAct", ACT_VAR, ("save", "submit", "duplicate"),
                             spin={"duplicate": icon_only_when(dup)})
    actions = request_actions("Dom", new, save, submit, fix_expr=f"CountRows({DRAFTS})",
                              extra=[edit, dup, *status])
    # Bundbjaelken under Desktop (UX-review M8) kopierer disse to.
    BAR_ACTIONS[:] = [save, submit]
    narrow = below("Tablet")
    save.props["Width"] = f"If({narrow}, 40, {save.props['Width']})"
    save.props["Layout"] = f"If({narrow}, ButtonLayout.IconOnly, ButtonLayout.IconBefore)"
    # Submit ogsaa kun sit ikon paa en telefon, saa "New request" kan staa
    # med hele sin tekst (issue #243). Tooltip og navn er uaendrede.
    if ICON_SUBMIT:
        submit.props["Width"] = f"If({narrow}, 40, {submit.props['Width']})"
        submit.props["Layout"] = f"If({narrow}, ButtonLayout.IconOnly, ButtonLayout.IconBefore)"
    # "Saving..." / "Submitting..." / "Duplicating..." paa knapperne (#420).
    act_button(save, ACT_VAR, "save")
    act_button(submit, ACT_VAR, "submit")
    act_button(dup, ACT_VAR, "duplicate")
    return top_bar("Dom", f'"{cfg.TITLE}"', f'"{cfg.SUBTITLE}"',
                   actions + [delete_button("Dom", "varDomViewOnly", "varDomRequestGuid", WHAT)],
                   icon=cfg.APP_KEY, mode_var="varDomViewOnly", num_var="varDomRequestNo",
                   crumb=breadcrumb("Dom", cfg.APP_KEY, "varDomRequestNo"))


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


def _input_for(col, kind, choices, required_formula="false"):
    # Praefikset foelger kontroltypen (REVIEW.md A4): inp = tekst,
    # num = tal, dte = dato.
    # Tal er tekstfelter uden spin-pile (UX-review T10) - derfor ogsaa inp.
    name = {"date": "dteDom", "bool": "chkDom"}.get(kind, "inpDom") + col
    v = _var(col)
    if kind == "num":
        return number_field(name, v, display_mode=DM_ROW, required_formula=required_formula,
                            onchange=f"Set({v}, {num_value()})")
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
                          placeholder=DEC_PLACEHOLDER,
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
    if kind == "choice" and set(choices or ()) == set(YES_NO):
        return yes_no(col)
    if kind == "choice":
        # themed_dropdown tager TEKSTEN og slaar selv recorden op til
        # ModernDropdown.Default.
        items = "[" + ", ".join(f'"{x}"' for x in choices) + "]"
        return themed_dropdown(name, items, v, display_mode=DM_ROW,
                               required_formula=required_formula,
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
    c = text_input(name, v, max_length=MAX_LEN.get(col, 255), display_mode=DM_ROW,
                   required_formula=required_formula,
                   onchange=f"Set({v}, Self.Text)")
    return c


# JA/NEJ ER ET SEGMENT OVERALT (UX-review T6). Materials havde Stock item
# som segment, Strategic part som dropdown og Wear part som tekstfelt;
# Measuring Points' "Does it exist in SAP?" var en dropdown. Et valgfelt
# med netop Yes og No bliver nu altid segmentet [ No | Yes ]. Den LAGREDE
# vaerdi er uaendret: teksten "Yes" eller "No".
YES_NO = ("No", "Yes")


def yes_no(col, tip=None, extra_fx=None):
    """[ No | Yes ] for et tekst-/valgfelt, der gemmer "No"/"Yes"."""
    v = _var(col)
    label = next(l for c, l, _k, _ch in FIELDS if c == col)
    opts = []
    for val in YES_NO:
        fx = f'Set({v}, "{val}")' + (f";\n{extra_fx(val)}" if extra_fx else "")
        opts.append((val, val, f'Coalesce({v}, "") = "{val}"', fx, tip))
    return segmented(f"conDom{col}Seg", opts, display_mode=DM_ROW, label=label)


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
                           onchange="Set(varDomFPlant, Self.Selected.Value);\n"
                                    + tok.prefs_save({"prefDomNewPlant": "Self.Selected.Value"}))


# FL-vaelgerens tilstand. Selve vaelgeren er tools/fl_picker.py - den
# samme i VH-plan, Equipments og Materials (issue #63).
FL_QUERY_VAR = "varDomFlQuery"
FL_BUSY_VAR = "varDomFlBusy"
FL_LAST_VAR = "varDomFlLast"
FL_COMBO = "cmbDomFl"


def build_fl_picker(cell_w, lock=None, required_formula="false", min_len=None):
    """Functional Location i EEN combobox med Search - soegefelt OG
    valgliste (fl_picker.py). Der er ingen separat soegeboks og ingen
    separat dropdown.

    lock: et udtryk, der - naar det er sandt - deaktiverer vaelgeren
    (Materials' No BOM Item). required_formula: hvornaar kanten maa vaere
    roed. min_len: mindste antal tegn foer der kan soeges (Materials
    kraever 16 - se build_flsearch.MIN_SEARCH_LEN for standarden).

    lock gaar til fl_picker selv (issue #101): foer blev den lagt ind i
    DisplayMode her, og input_theme gjorde Disabled til View - feltet saa
    ud som et almindeligt, tomt felt. Nu er det Disabled og graat."""
    v = _var(cfg.FL_FIELD)
    return fl_picker(
        "Dom", combo=FL_COMBO, results="colDomFl", raw_var="varDomFlRaw",
        msg_var="varDomFlMsg", busy_var=FL_BUSY_VAR, query_var=FL_QUERY_VAR,
        last_var=FL_LAST_VAR, pick_var=v,
        default_items=f"Filter(colDomFl, Code = {v})",
        display_mode=DM_ROW, lock=lock, min_len=min_len,
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


def _patch_blank(col, kind):
    """Den tomme vaerdi, der GEMMES. En valgkolonne tager ikke "" - den
    ryddes med Blank() (SP_CHOICE)."""
    return "Blank()" if col in SP_CHOICE else _blank(kind)


def _patch_value(col, kind):
    v = _var(col)
    if col in SP_CHOICE:
        return (f'If(IsBlank(Trim(Coalesce({v}, ""))), Blank(), '
                f'{{ Value: Trim({v}) }})')
    if kind in ("text", "long", "choice"):
        return f"Trim(Coalesce({v}, \"\"))"
    if kind == "bool":
        return f"Coalesce({v}, false)"
    if kind == "dec":
        # Tekstfeltets indhold ind i en Number-kolonne. Tom tekst skal
        # vaere Blank() og ikke 0: 0 er en maaling, tom er "ikke udfyldt".
        return (f'If(IsBlank(Trim(Coalesce({v}, ""))), Blank(), '
                f'IfError({dec_value(v)}, Blank()))')
    return v


def refresh_rows_fx(indent=0):
    """Spejlet af listen. Samlingen er ALDRIG sandheden - den hentes
    forfra efter hver skrivning, saa det, skaermen viser, er det, der staar
    i SharePoint.

    Brugerens egne raekker - eller, naar en admin har aabnet en andens
    anmodning, DEN anmodnings raekker (AS_ADMIN). To hele ClearCollect i
    en If, saa hvert filter delegeres for sig."""
    pad = " " * indent
    # Kun DENNE anmodnings raekker: de med anmodningens GUID, og de nye
    # raekker uden GUID, der er oprettet siden skaermen blev klargjort
    # (varDomSessionStart). Tidligere indsendte/gemte anmodninger staar ikke
    # i listen, naar man kommer ind direkte eller starter en ny - kun
    # hubbens Open henter en eksisterende (varDomRequestGuid).
    # IsBlank(RequestGuid) og en OR paa tvaers af kolonner kan SharePoint
    # ikke delegere. Uden GUID er en raekke oprettet siden session-start
    # allerede denne sessions (efter Save/Submit nulstilles baade GUID og
    # session-start), saa blank-testen er overfloedig og udelades.
    mine_guid = _collect_rows(
        f"Filter({cfg.L_ROWS}, RequesterEmail = varDomMe, RequestGuid = varDomRequestGuid)")
    mine_new = _collect_rows(
        f"Filter({cfg.L_ROWS}, RequesterEmail = varDomMe, Created >= varDomSessionStart)")
    theirs = _collect_rows(f"Filter({cfg.L_ROWS}, RequestGuid = varDomRequestGuid)")
    ind = lambda t: "\n".join("    " + l for l in t.split("\n"))
    mine = f"If(\n    !IsBlank(varDomRequestGuid),\n{ind(mine_guid)},\n{ind(mine_new)}\n)"
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
        if col in SP_CHOICE:
            v = f'Coalesce(R.{col}.Value, "")'
        elif kind in ("text", "long", "choice"):
            v = f'Coalesce(R.{col}, "")'
        elif kind == "dec":
            # Tallet som TEKST, saa formularens tekstfelt kan vise det
            # praecis som det staar - og tom betyder tom (issue #210).
            v = f'If(IsBlank(R.{col}), "", Text(R.{col}, "{DEC_FMT}", "{DEC_LANG}"))'
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
        + perm.may_change("varDomIdx.RequesterEmail", "varDomIdx.Status.Value", "varDomMe", resubmit=RESUBMIT) + ");\n"
        "        Set(varDomViewOnly, !(Lower(Coalesce(Param(\"mode\"), \"\")) = \"edit\" && varDomCanEdit))\n"
        "    )\n"
        ")"
    )


def clear_form_fx():
    lines = ['Set(varDomActiveRowId, Blank());',
             'Set(varDomRowStatus, "valid");',
             f'Set({REQUIRED}, false);',
             'Set(varDomFText, "");',
             # Det sidst valgte vaerk paa en ny raekke (UX-review L2).
             f'Set(varDomFPlant, {tok.pref_get("prefDomNewPlant")});']
    if getattr(cfg, "ROW_PANEL_ENABLED", False):
        lines.append('Set(varDomEditorOpen, false);')
        # Panelets gem-tilstand hoerer til den raekke, der var aaben (#402).
        lines.append(f'Set({PANEL_SAVE_VAR}, "");')
    if getattr(cfg, "ROW_EDITOR_TAB_VAR", None):
        lines.append(f'Set({cfg.ROW_EDITOR_TAB_VAR}, "Details");')
    if docs_cleanup_fx():
        lines.append(docs_cleanup_fx() + ";")
    for col, _lab, kind, _ch in FIELDS:
        # Appens standardvaerdi, hvor der er en (HOOKS["field_defaults"]).
        lines.append(f"Set({_var(col)}, {HOOKS['field_defaults'].get(col, _blank(kind))});")
    lines.append(fl_reset_fx_dom() + ";")
    if HOOKS["clear_extra"]:
        lines.append(HOOKS["clear_extra"] + ";")
    lines.append('Set(varDomInfo, "")')
    return "\n".join(lines)


def new_row_fx():
    return clear_form_fx() + ";\nSet(varDomEditorOpen, true)"


def form_dirty_fx(extra_new=()):
    """Er der ugemte aendringer i formularen? (issue #228, #403)

    En NY raekke: noget er udfyldt ud over standardvaerdierne (extra_new:
    appens egne betingelser, fx Materials' objekter paa en kopi). En
    HENTET raekke: formularen er ikke den samme som den GEMTE raekke i
    colDomRows - samme sammenligning, som admin-loggen bruger
    (admin_log.diff)."""
    # Vaerket: en ny raekke faar det sidst valgte (clear_form_fx), saa det
    # er kun en aendring, naar det er et andet.
    new = ['!IsBlank(Trim(Coalesce(varDomFText, "")))',
           f'Coalesce(varDomFPlant, "") <> {tok.pref_get("prefDomNewPlant")}',
           *extra_new]
    defaults = HOOKS["field_defaults"]
    for col, _l, kind, _ch in FIELDS:
        v = _var(col)
        if col in defaults:
            new.append(f'Coalesce({v}, "") <> {defaults[col]}')
        elif kind == "bool":
            new.append(f"Coalesce({v}, false)")
        elif kind in ("num", "date"):
            new.append(f"!IsBlank({v})")
        else:
            new.append(f'!IsBlank(Trim(Coalesce({v}, "")))')
    changed = (f"!IsBlank(With({{ o: {ACTIVE} }},\n"
               + _indent(alog.diff(_diff_pairs()), 4) + "\n))")
    return ("If(\n    IsBlank(varDomActiveRowId),\n    "
            + " ||\n    ".join(new) + ",\n    " + changed + "\n)")


def reset_form_fx():
    """Sidepanelets Reset (issue #403, #405, #450): KUN de ugemte aendringer
    kasseres. En gemt raekke faar sine SENESTE gemte vaerdier igen - den
    samme indlaesning som Previous/Next (load_row_fx mod colDomRows, som
    Save opdaterer), saa variabler, FL-vaelgeren og appens egne kroge
    (load_extra, details_open) nulstilles ens. En ny, ugemt raekke ryddes
    til standardvaerdierne. Panelet bliver aabent.

    Brugeren bliver paa den fane, hun stod paa (issue #450): indlaesningen
    saetter fanen til Details, saa den saettes tilbage bagefter, og
    Documents/Objects hentes igen for raekken, som fanerne selv goer.

    Koeres fra Reset-bekraeftelsen (build_reset_confirm) - eller direkte
    fra knappen, naar der intet er at kassere (reset_click_fx)."""
    load = load_row_fx().replace("ThisItem.", ACTIVE + ".")
    body = (f"If(\n    IsBlank({ACTIVE}),\n{_indent(new_row_fx(), 4)},\n"
            f"{_indent(load, 4)}\n)")
    tab = getattr(cfg, "ROW_EDITOR_TAB_VAR", None)
    if not tab:
        return body
    lines = [body, f"Set({tab}, keepTab)"]
    if DOCS:
        lines.append(f'If(\n    keepTab = "Documents" && !IsBlank(varDomActiveRowId) && !{att.busy},\n'
                     f"{_indent(open_active_docs_fx(), 4)}\n)")
    if TAB_REOPEN.get("Objects"):
        lines.append(f'If(\n    keepTab = "Objects",\n{_indent(TAB_REOPEN["Objects"], 4)}\n)')
    return (f"With(\n    {{ keepTab: Coalesce({tab}, \"Details\") }},\n"
            + _indent(";\n".join(lines), 4) + "\n)")


# Det, en fane goer, naar den aabnes (editor_tabs) - Reset koerer det igen
# for fanen, brugeren stod paa (issue #450).
TAB_REOPEN = {}
# Reset spoerger foerst, naar der er noget at kassere (issue #450).
RESET_ASK = "varDomResetAsk"
# Appens egne "ny raekke er aendret"-betingelser (reset_button(extra_new)).
RESET_EXTRA = [()]


def reset_mode(extra_new=()):
    """Reset er slaaet fra i visning, og naar formularen allerede er den
    gemte raekke (issue #403)."""
    dirty = form_dirty_fx(extra_new).replace("\n", " ")
    return (f"If(IfError(varDomViewOnly, false) || !({dirty}), "
            "DisplayMode.Disabled, DisplayMode.Edit)")


def reset_button(extra_new=()):
    """Reset i sidepanelets bundbjaelke (tools/domain_app._row_editor).
    Spoerger foerst, naar der er ugemte aendringer (issue #450)."""
    RESET_EXTRA[0] = tuple(extra_new)
    return button("btnDomNew", '"Reset"',
                  reset_click_fx(RESET_ASK, form_dirty_fx(extra_new), reset_form_fx()),
                  display_mode=reset_mode(extra_new),
                  tooltip='"Undo the unsaved changes to this row"')


def build_reset_confirm():
    """Reset-bekraeftelsen (issue #450) - [sloer, popup], som sletningens.
    Kun med sidepanel: dér staar Reset."""
    if not getattr(cfg, "ROW_PANEL_ENABLED", False):
        return []
    return reset_confirm("DomReset", RESET_ASK, reset_form_fx(),
                         form_dirty_fx(RESET_EXTRA[0]), "this row",
                         guard="IfError(varDomEditorOpen, false) && !IfError(varDomViewOnly, false)")


def copy_row_fx():
    """Copy: opret en NY raekke ud fra den valgte (issue #485).

    Foer lagde Copy raekkens vaerdier i formularen med blankt raekke-id, og
    sidepanelet aabnede med den valgte raekkes oplysninger. Det lignede, at
    man rettede i originalen, og der kom foerst en ny raekke, naar der blev
    trykket Save.

    Nu oprettes kopien MED DET SAMME som sin egen raekke i listen - som en
    KLADDE (Draft), saa den ikke er klar til indsendelse, foer brugeren har
    set den igennem. Bagefter hentes den ind i sidepanelet i Edit-tilstand.
    Originalen roeres ikke.

    Kopien laeses fra LISTEN (LookUp paa ID), ikke fra colDomRows, hvor
    valg og tal er laest om til tekst - samme greb som Duplicate.

    Det, der IKKE foelger med, er raekkens unikke og genererede vaerdier:
    ID, RowId, ItemKey og dokumentmappen (de dannes af kopiens eget ID),
    status (kopien er en kladde), dokumenterne (FileCount), SAP-numre og
    -svar (READ_FIELDS skrives aldrig) og cfg.COPY_SKIP (Measuring Points
    eksisterende maalepunktsnummer - to raekker kan ikke vaere samme
    punkt, issue #210). Kopien hoerer til den aabne anmodning, som en ny
    raekke ved Save (R2-002).

    Funktionspladserne (objektlisten) foelger med - det er samme sted med
    et andet materiale eller udstyr."""
    skip = set(getattr(cfg, "COPY_SKIP", ()))
    kinds = {c: k for c, _l, k, _ch in FIELDS}
    cols = [cfg.C_TEXT, "Plant"] + [c for c, _l, _k, _ch in FIELDS]
    cols += [c for c, _e in HOOKS["extra_patch"]] + list(EXTRA_PATCH)
    seen, rec = set(), []
    for c in cols:
        if c in seen:
            continue
        seen.add(c)
        v = _patch_blank(c, kinds.get(c, "text")) if c in skip else f"src.{c}"
        rec.append(f"                    {c}: {v},")
    key = ri.row_key(cfg.PREFIX, "varDomSpRow.ID")
    copied = "LookUp(colDomRows, RowId = varDomSpRow.ID)"
    load = load_row_fx().replace("ThisItem.", copied + ".")
    if HOOKS["copy_extra"]:
        load += ";\n" + HOOKS["copy_extra"].replace("ThisItem.", copied + ".")
    log = alog.write("varDomRequestGuid", "varDomRequestNo", alog.EDIT,
                     '"New row " & varDomSpRow.ItemKey & " (copy of " & srcKey & ")"', 12)
    return (
        "With(\n"
        "    { srcId: ThisItem.RowId, srcKey: ThisItem.ItemKey },\n"
        "    If(\n"
        # Rettigheden staar ogsaa i selve handlingen, ikke kun i UI'et.
        f"        {AS_ADMIN} && !{perm.IS_ADMIN},\n"
        f"        {DENIED_OTHER},\n"
        "        IfError(\n"
        "            With(\n"
        f"                {{ src: LookUp({cfg.L_ROWS}, ID = srcId) }},\n"
        "                Set(\n"
        "                    varDomSpRow,\n"
        f"                    Patch({cfg.L_ROWS}, Defaults({cfg.L_ROWS}), {{\n"
        + "\n".join("    " + l for l in rec) + "\n"
        '                        RowStatus: { Value: "draft" },\n'
        '                        RequestGuid: Coalesce(varDomRequestGuid, ""),\n'
        '                        RequestNo: Coalesce(varDomRequestNo, ""),\n'
        # En admin i en andens anmodning kopierer i EJERENS navn.
        f"                        RequesterEmail: If({AS_ADMIN}, Lower(varDomIdx.RequesterEmail), varDomMe),\n"
        f"                        RequesterName: If({AS_ADMIN}, varDomIdx.RequesterName, User().FullName)\n"
        "                    })\n"
        "                )\n"
        "            );\n"
        # Noeglen dannes af kopiens EGET ID - som en ny raekke ved Save.
        "            Set(\n"
        "                varDomSpRow,\n"
        f"                Patch({cfg.L_ROWS}, varDomSpRow, {{\n"
        "                    RowId: varDomSpRow.ID,\n"
        f"                    ItemKey: {key},\n"
        f'                    AttachmentFolder: "{attflows.LIBRARY}/" & {key}\n'
        "                })\n"
        "            );\n"
        f"            If(\n                {AS_ADMIN},\n{log}\n            );\n"
        + refresh_rows_fx(12) + ";\n"
        # Kopien aabnes i sidepanelet - i Edit, da den er en kladde.
        + _indent(load, 12) + ";\n"
        '            Set(varDomInfo, "Copied " & srcKey & " to the new draft row " & '
        'varDomSpRow.ItemKey & ". Documents were not copied.");\n'
        '            Notify("Copied " & srcKey & " to the new draft row " & varDomSpRow.ItemKey & '
        '". Documents were not copied.", NotificationType.Success),\n'
        '            Notify("Could not copy the row: " & FirstError.Message, NotificationType.Error)\n'
        "        )\n"
        "    )\n"
        ")"
    )


def delete_this_row_fx():
    """Listens slet-ikon: slet DEN raekke, ikonet sidder paa - bag en
    bekraeftelse (build_delete_confirm). Det er den eneste vej til at slette
    en raekke; formularens "Delete row" er fjernet (issue #94)."""
    return f"Set({DELETE_ID}, ThisItem.RowId);\nSet({DELETE_VAR}, true)"


def build_row_menu():
    """More-menu til de domaener, der bruger request-panelet."""
    actions = HOOKS["row_actions"] or ()
    has_more = any(action.name == "btnDomRowMore" for action in actions)
    if not getattr(cfg, "ROW_PANEL_ENABLED", False) or not has_more:
        return []
    row = "LookUp(colDomRows, RowId = varDomMoreRowId)"
    close = "Set(varDomMoreRowId, Blank())"
    backdrop = tap_backdrop("imgDomRowMenuBackdrop", "!IsBlank(varDomMoreRowId)", close)
    copy_fx = copy_row_fx().replace("ThisItem.", row + ".") + ";\n" + close
    copy = button("btnDomMoreCopy", '"Copy row"', copy_fx,
                  width=fit_button_width('"Copy row"'), height=36,
                  display_mode="If(varDomViewOnly, DisplayMode.Disabled, DisplayMode.Edit)")
    delete_fx = f"Set({DELETE_ID}, varDomMoreRowId);\nSet({DELETE_VAR}, true);\n{close}"
    delete = button("btnDomMoreDelete", '"Delete row"', delete_fx, danger=True,
                    width=fit_button_width('"Delete row"'), height=36,
                    display_mode=(f"If(varDomViewOnly || {row}.Status = \"submitted\", "
                                  "DisplayMode.Disabled, DisplayMode.Edit)"))
    menu = group("conDomRowMoreMenu", [copy, delete], direction="Vertical", gap=8,
                 width=220, fill=C_MODAL_BG, border_color=C_CARD_BORDER,
                 radius=lay.RADIUS_CARD, pad=(12, 12, 12, 12),
                 visible="!IsBlank(varDomMoreRowId)", drop_shadow="Bold")
    menu.props["X"] = "App.Width - Self.Width - 16"
    menu.props["Y"] = "96"
    return [backdrop, menu]

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
    if getattr(cfg, "ROW_PANEL_ENABLED", False):
        lines.append('Set(varDomEditorOpen, true);')
        lines.append(f'Set({PANEL_SAVE_VAR}, "");')
    if getattr(cfg, "ROW_EDITOR_TAB_VAR", None):
        lines.append(f'Set({cfg.ROW_EDITOR_TAB_VAR}, "Details");')
    # En anden raekke: den forrige raekkes dokumenter lukkes (issue #393).
    if docs_cleanup_fx():
        lines.append(docs_cleanup_fx() + ";")
    for col, _lab, _kind, _ch in FIELDS:
        lines.append(f"Set({_var(col)}, ThisItem.{col});")
    if getattr(cfg, "FL_FIELD", None):
        lines.append(_fl_known_fx(f"ThisItem.{cfg.FL_FIELD}"))
    if HOOKS["load_extra"]:
        lines.append(HOOKS["load_extra"] + ";")
    if getattr(cfg, "ROW_PANEL_ENABLED", False) and HOOKS["details_open"]:
        lines.append(HOOKS["details_open"] + ";")
    lines[-1] = lines[-1].rstrip(";")
    return "\n".join(lines)


def open_docs_fx():
    """Raekkens Docs-knap: peg popuppen paa DENNE raekke og hent raekken
    fra listen (LookUp paa ID), saa kontrollen viser dens vedhaeftninger."""
    return "Set(varDomDocsId, ThisItem.RowId);\n" + att.load_fx("ThisItem.RowId")


def build_backdrop():
    """Sloeret bag popupperne. EEN kontrol til begge - to ville lagre oven
    paa hinanden og goere baggrunden dobbelt saa moerk."""
    if getattr(cfg, "ROW_PANEL_ENABLED", False):
        # Sidepanelet har ingen detaljepopup: kun dokumentpopuppen er tilbage.
        return tap_backdrop("conDomBackdrop", "!IsBlank(varDomDocsId)",
                            f"If(!{att.busy}, {DOCS_CLOSE})")
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
    # Appens egne vaerdier, der ikke er et felt (issue #485).
    pairs += list(HOOKS["extra_diff"])
    return pairs


def save_row_fx(status="valid", required=(), always=()):
    """Gem raekken i SharePoint - som kladde eller som faerdig.

    required: appens EKSTRA krav til en faerdig raekke, som par af
    (betingelse der betyder "mangler", besked). Kladden tjekker dem ikke.
    Materials kraever funktionspladsen - undtagen paa en No BOM-raekke.

    En KLADDE kraever kun beskrivelsen. Listens Title er obligatorisk, saa
    helt tom kan raekken ikke vaere, men alt andet maa mangle - det er
    hele pointen med en kladde.

    En FAERDIG raekke kraever ogsaa vaerket, og det er den status, Indsend
    tager med.

    always: krav, der gaelder BAADE kladde og faerdig raekke (opt-in,
    issue #228) - en vaerdi, der er forkert, ikke bare mangler (Materials:
    min stock > max stock). Samme form som required.

    status="auto" (UX-review 2026-10, F2/T2): EEN knap, "Add row" /
    "Update row". Raekken gemmes som FAERDIG, naar alle krav er opfyldt, og
    ellers som KLADDE - kun beskrivelsen er et krav for at gemme. Foer var
    der to knapper (Save row draft og Save row), og brugeren skulle selv
    vide, hvilken status raekken skulle have. Beskeden siger, hvad der blev
    gemt, og hvad der mangler for at raekken kan indsendes.
    """
    if status == "auto":
        return _save_row_auto(required, always)
    patch = [
        f"            {cfg.C_TEXT}: Trim(varDomFText),",
        "            Plant: varDomFPlant,",
    ]
    for col, _lab, kind, _ch in FIELDS:
        v = HOOKS["patch_override"].get(col) or _patch_value(col, kind)
        if col in WHEN:
            # ET SKJULT FELT GEMMES TOMT (issue #210)
            #
            # Skifter brugeren type, skal den gamle types vaerdier ikke
            # blive staaende paa raekken - saa ville SAP-ordren og
            # detaljerne vise et felt, formularen ikke laengere viser.
            v = f"If({WHEN[col]}, {v}, {_patch_blank(col, kind)})"
        patch.append(f"            {col}: {v},")
    # Appens egne kolonner, der ikke er et felt i formularen (Materials'
    # Object List) - HOOKS["extra_patch"].
    for col, expr in HOOKS["extra_patch"]:
        patch.append(f"            {col}: {expr},")
    # Felter, appen afleder af andre (cfg.EXTRA_PATCH, issue #210).
    for col, fx in EXTRA_PATCH.items():
        patch.append(f"            {col}: {fx},")
    patch += [
        '            RowStatus: { Value: "%s" },' % status,
        # En admin i en andens anmodning gemmer raekken i EJERENS navn.
        f"            RequesterEmail: If({AS_ADMIN}, Lower(varDomIdx.RequesterEmail), varDomMe),",
        f"            RequesterName: If({AS_ADMIN}, varDomIdx.RequesterName, User().FullName)",
    ]
    key = ri.row_key(cfg.PREFIX, "varDomSpRow.ID")

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
    for cond, text in length_rules() + list(always):
        extra += f'    {cond},\n    Notify("{text}", NotificationType.Warning),\n'
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
        # En NY raekke i en aaben anmodning skal hoere til DEN anmodning -
        # ogsaa ejerens, ikke kun en admins. Ellers forsvinder den fra
        # listen ved naeste refresh_rows_fx og bliver foraeldreloes (R2-002).
        # Kun raekker uden GUID, saa en raekke aldrig flyttes fra en anden
        # anmodning.
        "    If(\n"
        "        !IsBlank(varDomRequestGuid) && IsBlank(Coalesce(varDomSpRow.RequestGuid, \"\")),\n"
        "        Set(\n"
        "            varDomSpRow,\n"
        f"            Patch({cfg.L_ROWS}, varDomSpRow, {{ RequestGuid: varDomRequestGuid, RequestNo: Coalesce(varDomRequestNo, \"\") }})\n"
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
          "NotificationType.Success)"
          + (";\n    Set(varDomEditorOpen, false)"
              if getattr(cfg, "ROW_PANEL_ENABLED", False) else "")
          + ",\n"
        "\n"
        '    Set(varDomInfo, "Save failed: " & FirstError.Message);\n'
        + (f'    Set({PANEL_SAVE_VAR}, "failed");\n'
           if getattr(cfg, "ROW_PANEL_ENABLED", False) else "") +
        '    Notify("Save failed: " & FirstError.Message, '
        "NotificationType.Error)\n"
        "    )\n"
        ")"
    )


def length_rules():
    """For lange tekster (R2-038) - gaelder baade kladde og faerdig raekke,
    i samme form som save_row_fx's always."""
    rules = [(f'Len(Trim(Coalesce(varDomFText, ""))) > {TEXT_MAX}',
              f"{cfg.TEXT_LABEL} can have at most {TEXT_MAX} characters.")]
    for col, label, _k, _ch in FIELDS:
        if col in MAX_LEN:
            rules.append((f'Len(Trim(Coalesce({_var(col)}, ""))) > {MAX_LEN[col]}',
                          f"{label} can have at most {MAX_LEN[col]} characters."))
    # Decimaltal: komma er ikke decimaltegn i en-US (R2-075).
    for col, label, kind, _ch in FIELDS:
        if kind == "dec":
            rules.append((f'"," in Coalesce({_var(col)}, "")',
                          f"{label}: use . as decimal separator."))
    return rules


def row_complete_fx(required=()):
    """Sand, naar raekken opfylder kravene til en FAERDIG raekke: tekst,
    vaerk og appens egne krav (de samme som save_row_fx("valid"))."""
    conds = ['!IsBlank(Trim(Coalesce(varDomFText, "")))', "!IsBlank(varDomFPlant)"]
    conds += [f"!({c})" for c, _t in required]
    return "(" + " && ".join(conds) + ")"


def _save_row_auto(required, always):
    """Gem raekken som faerdig eller som kladde - afgjort af kravene."""
    complete = row_complete_fx(required)
    valid = save_row_fx("valid", required=(), always=always)
    draft = save_row_fx("draft", required=(), always=always)
    # Beskeden: gemt som kladde, og hvad der mangler for at blive faerdig.
    missing = ['If(IsBlank(varDomFPlant), "' + PLANT_LABEL_MISSING + '", "")']
    for c, text in required:
        missing.append(f'If({c}, "{text} ", "")')
    hint = " & ".join(missing)
    msg = '"Saved as draft row " & ' + ACTIVE + '.ItemKey & " - " & Trim(' + hint + ')'
    for a, b in (('Set(varDomInfo, "Draft saved as " & ' + ACTIVE + '.ItemKey);',
                  f'Set(varDomInfo, {msg});'),
                 ('Notify("Draft saved as " & ' + ACTIVE + '.ItemKey, NotificationType.Success)',
                  f'Notify({msg}, NotificationType.Warning)')):
        if a not in draft:
            raise SystemExit("domain_parts._save_row_auto: kladdens besked er aendret")
        draft = draft.replace(a, b)
    return ("// Add row / Update row (UX-review F2): faerdig, naar kravene er opfyldt,\n"
            "// ellers kladde. Kun beskrivelsen kraeves for at gemme.\n"
            f"If(\n    {complete},\n" + _indent(valid, 4) + ",\n" + _indent(draft, 4) + "\n)")


PLANT_LABEL_MISSING = "%s is required to submit the row." % cfg.PLANT_LABEL


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
        f"            {act_mark(ACT_VAR, 'delete', False)};\n"
        '            Notify("Delete failed: " & FirstError.Message, NotificationType.Error);\n'
        "            false\n"
        "        ),\n"
        + ("" if getattr(cfg, "ROW_PANEL_ENABLED", False) else
           f"        If(varDomDetailsId = {DELETE_ID}, Set(varDomDetailsId, Blank()));\n") +
        (f"        If(varDomDocsId = {DELETE_ID}, {DOCS_CLOSE.replace(chr(10), ' ')});\n"
         if DOCS else "") +
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
        f"        {act_mark(ACT_VAR, 'delete')};\n"
        '        Set(varDomInfo, "Row deleted.");\n'
        '        Notify("Row deleted.", NotificationType.Success)\n'
        "    )\n"
        ");\n"
        f"Set({DELETE_ID}, Blank())"
    )


def build_delete_confirm():
    """Bekraeftelsen foer sletning - [sloer, popup], som Submit's."""
    return confirm_modal(
        "DomDel", DELETE_VAR, "Delete row?",
        f'"Row " & LookUp(colDomRows, RowId = {DELETE_ID}).ItemKey & ' +
        ('" is deleted in SharePoint, together with its attached documents."' if DOCS
         else '" is deleted in SharePoint."'),
        "Delete", delete_confirmed_fx(),
        "btnDomDeleteConfirm", icon="Delete", act=(ACT_VAR, "delete"))

# ---------------------------------------------------------------------------
# Dokumentruden
#
# Den erstatter DocumentType og DocumentLink. De to felter var et link,
# brugeren selv skulle skaffe; her ligger filen som vedhaeftning paa
# raekken i SharePoint (issue #300), og appen kender den.
#
# Ruden hoerer til den VALGTE, GEMTE raekke - ikke til formularen.
# ---------------------------------------------------------------------------
def build_attachments():
    """Dokumentpopuppen (issue #134, #300): den moderne Attachments-
    kontrol bundet til raekkens vedhaeftninger og een "Save documents".
    Kontrollen viser, aabner og fjerner selv de gemte filer.
    Opbygningen er den faelles i tools/doc_upload.py."""
    edit = DOCS_EDIT
    pick = du.picker(att.picker, '"Documents on the selected row"', 10, 10, att.items,
                     display_mode=du.picker_mode(att, edit))
    # 10 MB: SharePoint-vedhaeftninger fra Power Apps. En datablad eller
    # en manual er langt under.
    limits = du.limits_text("txtDomAttLimits", 10, 10, visible=edit)
    save = du.save_button("btnDomAttUpload", att, visible=edit)
    actions = group("conDomAttActions", [save], direction="Horizontal", gap=8,
                    height=36, justify="End", align_items="Center", visible=edit)
    ro = du.readonly_note("txtDomAttReadOnly", f"!IsBlank(varDomDocsId) && !{edit}")

    title = grow(text_ctrl(
        "txtDomAttH",
        '"Documents · " & Coalesce(LookUp(colDomRows, RowId = varDomDocsId).ItemKey, "")',
        size=lay.SIZE_CARD_TITLE, weight="Semibold", height=text_min_height(lay.SIZE_CARD_TITLE), wrap="false"))
    # X oeverst til hoejre (issue #343) - ikke midt i en gemning.
    head = popup_head("conDomAttHead", title, "btnDomAttClose", DOCS_CLOSE,
                      mode=f"If({att.busy}, DisplayMode.Disabled, DisplayMode.Edit)")
    # Popuppen: 18 + 18 luft, hovedet og afstanden - resten er indholdet.
    body = du.capped_body("conDomAttBody",
                          [pick, limits, actions, ro],
                          f"App.Height - 40 - 36 - {head.h} - 14")
    # Kontrollen fylder den plads, popuppen har tilbage (issue #344).
    du.fit_picker(pick, body.children, 12)
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
# 128 + 2 x 14: kortets to knaplinjer er H.hit hoeje (44 under Desktop),
# saa Delete-ikonet har sin klikflade (UX-review F6, regel 40).
ROW_H_C = 156
GAL_ROWS_C = 5
ROW_BTN_H = 30
ROW_LINE_H = lay.HIT     # linjen, knapperne staar i - ikonknappen er H.hit
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


# ---------------------------------------------------------------------------
# Detaljeruden GRUPPERET (issue #204)
#
# Nitten felter paa en flad liste er en liste, man skimmer uden at laese.
# Med grupper - identifikation, objekter, leverandoer, lager,
# klassifikation, yderligere oplysninger, rekvirent - kan man finde det,
# man leder efter.
#
# EET GALLERI, IKKE EN KONTROL PR. LINJE. Fyrre linjer som fyrre
# containere er fyrre kontroller, der skal tegnes og regnes med - og en
# lodret container, der er hoejere end popuppen maa vaere, melder overloeb
# (check_layout regel 2), ogsaa naar den scroller. Galleriet har EEN
# skabelon og en fast hoejde.
#
# Grupperne staar i appens egen fil (HOOKS["details_groups"]); den er kun
# tilgaengelig for de apps, der har sat den - de andre faar den flade
# liste som hidtil.
# ---------------------------------------------------------------------------
DET_ROW_H = 26
DET_MAX_ROWS = 18


def _detail_value(col, row):
    """(etiket, udtryk) for en kolonne i detaljeruden."""
    special = {
        "TEXT": (cfg.TEXT_LABEL, f'Coalesce({row}.{cfg.C_TEXT}, "-")'),
        "PLANT": (cfg.PLANT_LABEL, f'Coalesce({row}.Plant, "-")'),
        "STATUS": ("Status", f'Coalesce({row}.Status, "-")'),
        "DOCS": ("Documents", f'Text(Coalesce({row}.FileCount, 0))'),
        "KEY": ("Row key", f'Coalesce({row}.ItemKey, "-")'),
        "REQUESTNO": ("Request no.", f'Coalesce({row}.RequestNo, "-")'),
    }
    if col in special:
        return special[col]
    for c, label, kind, _ch in ROW_FIELDS:
        if c != col:
            continue
        if kind == "bool":
            return label, f'If({row}.{col}, "Yes", "No")'
        if kind == "dec":
            return label, f'If(IsBlank({row}.{col}), "-", {row}.{col})'
        if kind == "date":
            return label, f'If(IsBlank({row}.{col}), "-", Text({row}.{col}, "{lay.DATE_FMT}"))'
        if kind == "num":
            return label, f'If(IsBlank({row}.{col}), "-", {lay.num_text(row + "." + col)})'
        return label, f'Coalesce({row}.{col}, "-")'
    raise SystemExit(f"domain_parts: {col} kan ikke vises i detaljeruden")


def _details_items(row):
    """Galleriets raekker: en overskrift (K = "H") pr. gruppe og en linje
    (K = "D") pr. felt. Appen kan give (etiket, udtryk) direkte, hvor
    vaerdien ikke blot er kolonnen - {row} er raekken."""
    recs = []
    for title, cols in HOOKS["details_groups"]:
        recs.append('{ K: "H", L: "%s", V: "" }' % title)
        for col in cols:
            if isinstance(col, tuple):
                label, expr = col[0], col[1].replace("{row}", row)
            else:
                label, expr = _detail_value(col, row)
            recs.append('{ K: "D", L: "%s", V: %s }' % (label, expr))
    body = ",\n            ".join(recs)
    return len(recs), "Table(\n            %s\n        )" % body


def _details_gallery(row):
    n, items = _details_items(row)
    head = text_ctrl("txtDomDetGrp", "Upper(ThisItem.L)", size=11, color=C_MUTED,
                     weight="Semibold", height=20, wrap="false",
                     visible='ThisItem.K = "H"')
    head.props["X"] = "0"
    head.props["Y"] = "6"
    head.props["Width"] = "Parent.TemplateWidth"
    lbl = text_ctrl("txtDomDetL", "ThisItem.L", size=12, color=C_MUTED,
                    weight="Semibold", height=20, width=DETAIL_LBL_W, wrap="false",
                    visible='ThisItem.K = "D"')
    lbl.props["X"] = "0"
    lbl.props["Y"] = "3"
    val = text_ctrl("txtDomDetV", "ThisItem.V", size=13, height=20, wrap="false",
                    visible='ThisItem.K = "D"')
    val.props["X"] = str(DETAIL_LBL_W + 12)
    val.props["Y"] = "3"
    val.props["Width"] = f"Parent.TemplateWidth - {DETAIL_LBL_W + 12}"
    h = f"Min({n * DET_ROW_H}, App.Height - 260)"
    gal = Ctrl("galDomDetails", "Gallery", variant="Vertical", props={
        "AccessibleLabel": '"All fields on this row"',
        "BorderStyle": "BorderStyle.None",
        "Fill": C_TRANSPARENT,
        "FillPortions": "0",
        "Height": h,
        "Items": items,
        "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None",
        "Selectable": "false",
        "ShowScrollbar": "true",
        "TabIndex": "0",
        "TemplatePadding": "0",
        "TemplateSize": str(DET_ROW_H),
        "Width": "Parent.Width",
        "WrapCount": "1",
    }, children=[head, lbl, val], h=h)
    return gal


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
    row = "LookUp(colDomRows, RowId = varDomDetailsId)"
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

    # Skifter ruden raekke, skal appens egne felter i den foelge med
    # (HOOKS["details_nav"], fx Materials' felt til materialenummeret).
    nav = (";\n" + HOOKS["details_nav"]) if HOOKS["details_nav"] else ""
    prev = button("btnDomDetPrev", '"Previous"',
                  f'Set(varDomDetailsId, Index({order}, Max(1, {pos} - 1)).RowId)' + nav,
                  width=96, height=30,
                  display_mode=f"If({pos} <= 1, DisplayMode.Disabled, DisplayMode.Edit)")
    nxt = button("btnDomDetNext", '"Next"',
                 f'Set(varDomDetailsId, '
                 f'Index({order}, Min(CountRows({order}), {pos} + 1)).RowId)' + nav,
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
    # X oeverst til hoejre, som i de andre popupper (issue #343).
    close = close_x("btnDomDetClose", "Set(varDomDetailsId, Blank())")
    # Knapperne DIREKTE i hovedet, ikke i en indlejret gruppe: i Studio
    # stod de i en indlejret gruppe ved siden af en fleksibel venstreside
    # en linje for lavt, skaaret over af kanten. Samme som topbjaelken.
    head = group("conDomDetHead", [head_left] + pin_widths([prev, nxt, edit]) + [close],
                 direction="Horizontal", gap=8, align_items="Center")

    # Alle felter - ogsaa de tomme. En tom linje er et svar: feltet ER
    # ikke udfyldt. Skjules den, kan man ikke se forskel paa "tomt" og
    # "findes ikke".
    if HOOKS["details_groups"]:
        kids = [_details_gallery(row)]
        if HOOKS["details_rows"]:
            kids += HOOKS["details_rows"](row)
        kids += list(extra(row) if callable(extra) else extra)
        box = group("conDomDetRows", kids, direction="Vertical", gap=10)
        modal = group("conDomDetailsModal", [head, box], direction="Vertical",
                      gap=12, fill=C_MODAL_BG, border_color=C_PRIMARY_SOFT,
                      radius=lay.RADIUS_MODAL, pad=(lay.CARD_PAD,) * 4,
                      width=DETAILS_W, drop_shadow="ExtraBold",
                      visible="!IsBlank(varDomDetailsId)")
        modal.props["X"] = MODAL_X
        modal.props["Y"] = MODAL_Y
        return modal
    rows = [_detail_row(0, cfg.TEXT_LABEL, f'Coalesce({row}.{cfg.C_TEXT}, "-")'),
            _detail_row(1, "Plant", f'Coalesce({row}.Plant, "-")'),
            _detail_row(2, "Status", f'Coalesce({row}.Status, "-")'),
            _detail_row(3, "Documents", f'Text(Coalesce({row}.FileCount, 0))')]
    for n, (col, label, kind, _ch) in enumerate(ROW_FIELDS, start=len(rows)):
        if kind == "bool":
            v = f'If({row}.{col}, "Yes", "No")'
        elif kind == "dec":
            v = f'If(IsBlank({row}.{col}), "-", {row}.{col})'
        elif kind == "date":
            v = f'If(IsBlank({row}.{col}), "-", Text({row}.{col}, "{lay.DATE_FMT}"))'
        elif kind == "num":
            v = f'If(IsBlank({row}.{col}), "-", {lay.num_text(row + "." + col)})'
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
# Raekker, der er gemt som kladde: de mangler noget for at kunne indsendes.
DRAFTS = 'Filter(colDomRows, Status = "draft")'


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
    # Knappens noegle (issue #420) - udfaldet skrives i grenene herunder.
    key = "submit" if submit else "save"
    action = "Submit" if submit else "Save"
    # Efter Submit er anmodningen afleveret. Stod GUID og nummer tilbage,
    # patchede naeste "Save as draft" i samme session den INDSENDTE
    # indeksraekke tilbage til Kladde. Naeste batch er en ny anmodning.
    after = (';\n        Set(varDomRequestGuid, "");\n'
             '        Set(varDomRequestNo, "");\n        ' + SESSION_FX) if submit else ""
    # Indeksraekken er den samme i alle apps - tools/request_index.py.
    index_rec = ri.record(
        cfg.DOMAIN, cfg.APP_KEY, status,
        request_no="Coalesce(varDomRequestNo, varDomRequestGuid)",
        guid="varDomRequestGuid", me="varDomMe",
        # Ejeren bevares - ogsaa naar en admin gemmer en andens anmodning.
        owner='Coalesce(varDomIdx.RequesterEmail, varDomMe)',
        owner_name="Coalesce(varDomIdx.RequesterName, User().FullName)",
        current="varDomIdx",
        short_text=ri.rows_text(cfg.TITLE, f"CountRows({rows})"),
        # Den AELDSTE raekkes vaerk (laveste ID), saa vaerdien ikke skifter,
        # naar en raekke tilfoejes (R2-074). Ved Submit er der kun eet.
        plant=f"First(Sort({rows}, RowId)).Plant", item_count=f"CountRows({rows})")
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
    # Appens eget efterspil - koeres FOER GUID og nummer ryddes (after
    # ovenfor), saa det stadig ved, hvilken indmelding der blev sendt.
    submit_extra = ""
    if submit and HOOKS["after_submit"]:
        submit_extra = ";\n" + _indent(HOOKS["after_submit"], 8)

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

    # KLADDERAEKKER FOELGER ANMODNINGEN (R2-002, valg a)
    #
    # Ved Submit faar kladderaekkerne anmodningens GUID og nummer, men ingen
    # statusaendring. Ellers stod de uden GUID og forsvandt fra appen, saa
    # snart GUID og session-start blev nulstillet. Nu ses de igen, naar
    # anmodningen aabnes, og kan indsendes, hvis den sendes retur.
    drafts_follow = ""
    if submit:
        drafts_follow = (
            "        If(\n"
            f"            CountRows({DRAFTS}) > 0,\n"
            "            Patch(\n"
            f"                {cfg.L_ROWS},\n"
            f"                ForAll({DRAFTS} As X, {{ ID: X.RowId }}),\n"
            f"                ForAll({DRAFTS}, {{ RequestNo: varDomRequestNo, RequestGuid: varDomRequestGuid }})\n"
            "            )\n"
            "        );\n")

    plant_guard = ""
    if submit:
        plant_guard = (f"    {PLANT_MIX},\n"
                       f"    Notify({PLANT_MIX_MSG}, NotificationType.Warning),\n")
    return (
        "If(\n"
        f"    CountRows({rows}) = 0,\n"
        f'    Notify("{empty}", NotificationType.Warning),\n'
        + plant_guard +
        "\n"
        # Raekkeloftet (R2-041): advar, men stop ikke.
        f'    If({ROWS_CAPPED}, Notify("{ROWS_CAP_MSG}", NotificationType.Warning));\n'
        "\n"
        # Indeksraekken slaas op FRISK, foer der skrives: den er grundraekken
        # i Patch (samme ene opslag som foer) og afgoer, om brugeren maa.
        "    Set(\n"
        "        varDomIdx,\n"
        f"        If(!IsBlank(varDomRequestGuid), LookUp({cfg.L_INDEX}, RequestGuid = varDomRequestGuid))\n"
        "    );\n"
        "    If(\n"
        "        !IsBlank(varDomIdx) &&\n"
        "        !" + perm.may_change("varDomIdx.RequesterEmail", "varDomIdx.Status.Value", "varDomMe", resubmit=RESUBMIT) + ",\n"
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
        + drafts_follow +
        "\n"
        + refresh_rows_fx(8) + ";\n"
        + admin_submit_log +
        "\n"
        f"        {act_mark(ACT_VAR, key)};\n"
        f'        Set(varDomInfo, "{label}: " & varDomRequestNo);\n'
        f"        {(msg.submitted if submit else msg.saved)('varDomRequestNo')}"
        + submit_extra + after + ',\n'
        "\n"
        f"        {act_mark(ACT_VAR, key, False)};\n"
        f'        Set(varDomInfo, "{action} failed: " & FirstError.Message);\n'
        f"        {msg.failed(action)}\n"
        "    )\n"
        "    )\n"
        ")"
    )


def build_submit_confirm():
    """Bekraeftelsen foer Submit og ventespinneren (issue #54).

    [sloer, popup, sloer, spinner] - skal staa SIDST i skaermens boern, saa de
    ligger oven paa alt andet."""
    return confirm_modal(
        "Dom", CONFIRM_VAR, "Submit request?",
        '"The valid rows are sent to the landing page as Submitted and locked."',
        "Submit", act_fx(ACT_VAR, "submit", send_fx(True)), "btnDomSubmitConfirm") + delete_modal(
        "Dom", "varDomRequestGuid", cfg.L_INDEX, cfg.DOMAIN, WHAT) + [
        # Mens en handling koerer: knappen viser det selv (issue #420) - et
        # gennemsigtigt lag oeverst, intet sloer og ingen bjaelke.
        *act_layers("Dom", ACT_VAR)]


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
PANEL_NEED_2 = 360
PANEL_NEED_3 = 3 * 140 + 2 * GRID_GAP
GRID_COLS = 4

# Een celles bredde - maalt paa KORTETS bredde, ikke paa App.Width.
CELL_W = fits(FORM_W, NEED_4,
              fits(FORM_W, NEED_2, FORM_W, f"(({FORM_W}) - {GRID_GAP}) / 2"),
              f"(({FORM_W}) - {3 * GRID_GAP}) / 4")
PANEL_CELL_W = fits(PANEL_FORM_W, PANEL_NEED_2, PANEL_FORM_W,
                    fits(PANEL_FORM_W, PANEL_NEED_3,
                         f"(({PANEL_FORM_W}) - {GRID_GAP}) / 2",
                         f"(({PANEL_FORM_W}) - {2 * GRID_GAP}) / 3"))


# Felter, der fylder hele panelets bredde (mockuppen: FL og Description).
PANEL_FULL_KEYS = {"FL", "TEXT", "DOCS"}
PANEL_FULL_NAMES = {"conDomFl", "conDomText", "conDomDocs"}


def panel_cell_w(key, cell_width):
    """Cellebredden for et felt i panelet: hele bredden for FL/TEXT/DOCS."""
    return PANEL_FORM_W if key in PANEL_FULL_KEYS and cell_width == PANEL_CELL_W else cell_width


def panel_fit_w(cell_width, need):
    """En celle i panelet, der mindst er need px bred - dog aldrig bredere
    end panelets formular (issue #477). Til en celle, der staar ALENE paa
    sin linje i panelet, saa den udnytter pladsen i stedet for at klippe
    sit indhold af ved en tredjedel af bredden."""
    return f"Min({PANEL_FORM_W}, Max({cell_width}, {need}))"


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


def grid_row(name, cells, container_w=None, columns=None, cell_width=None):
    """Op til fire celler (eller kolonner), der ombryder til to og een.

    Hoejden regnes for hver af de tre tilstande af cellernes egne hoejder
    - check_layout regel 4c spiller ombrydningen og efterproever den."""
    if len(cells) > GRID_COLS:
        raise SystemExit(f"domain_parts.grid_row: {name} har {len(cells)} celler - "
                         f"hoejst {GRID_COLS}")
    hs = [c.h for c in cells]
    calc_w = FORM_W if container_w is None else container_w
    if columns is None:
        h = fits(calc_w, NEED_4,
                 fits(calc_w, NEED_2, _chunk_h(hs, 1), _chunk_h(hs, 2)),
                 _chunk_h(hs, 4))
    elif columns == 2:
        # Panelets gitter: to kolonner, tre naar panelet er bredt nok, een
        # naar det er smalt. Felter, der fylder hele bredden, deler gitteret.
        runs, cur = [], []
        for cell in cells:
            if cell.name in PANEL_FULL_NAMES:
                if cur:
                    runs.append(cur)
                    cur = []
                runs.append([cell])
                continue
            cur.append(cell)
            if len(cur) == 3:
                runs.append(cur)
                cur = []
        if cur:
            runs.append(cur)
        groups = []
        for index, run in enumerate(runs):
            run_heights = [cell.h for cell in run]
            run_height = (run_heights[0] if len(run) == 1 else
                          fits(calc_w, PANEL_NEED_2, _chunk_h(run_heights, 1),
                               fits(calc_w, PANEL_NEED_3, _chunk_h(run_heights, 2),
                                    _chunk_h(run_heights, 3))))
            groups.append(group(f"{name}Pair{index}", run,
                                direction="Horizontal", gap=GRID_GAP,
                                height=run_height, width=container_w or "Parent.Width",
                                wrap="true"))
        return group(name, groups, direction="Vertical", gap=GRID_GAP,
                     width=container_w or "Parent.Width", wrap="false")
    else:
        if columns < 1 or columns > GRID_COLS:
            raise ValueError("grid_row columns must be between 1 and 4")
        h = _chunk_h(hs, columns)
    if cell_width is not None:
        for cell in cells:
            cell.props["Width"] = str(cell_width)
            cell.props["LayoutMinWidth"] = "0"
    direction = "Vertical" if columns == 1 else "Horizontal"
    return group(name, cells, direction=direction, gap=GRID_GAP, height=h,
                 width="Parent.Width" if container_w is None else container_w,
                 wrap="true" if direction == "Horizontal" else "false")


def grid_rows(prefix, cells, container_w=None, columns=None, cell_width=None):
    """Celler i RAEKKE-orden: fire pr. raekke, venstre mod hoejre."""
    return [grid_row(f"{prefix}{i // GRID_COLS}", cells[i:i + GRID_COLS],
                     container_w=container_w, columns=columns, cell_width=cell_width)
            for i in range(0, len(cells), GRID_COLS)]


def grid_columns(name, columns, row_gap=14):
    """Celler i KOLONNE-orden: oppefra og ned i kolonne 1, saa kolonne 2 ...
    (eq.png). Paa en tablet staar kolonne 1 og 2 side om side over 3 og 4;
    paa en telefon under hinanden - stadig i kolonne-orden."""
    cols = [group(f"{name}Col{i + 1}", cells, direction="Vertical", gap=row_gap,
                  width=CELL_W, align_items="Stretch", align_in_container="Start")
            for i, cells in enumerate(columns)]
    return grid_row(name, cols)


def grid_cell(name, label, ctrl, required=False, width=CELL_W):
    return field_cell(name, label, ctrl, required=required, width=width,
                      fill_portions_formula="0")


def field_grid_cell(col, required=False, visible=None, width=CELL_W):
    """Et felt fra SECTIONS som celle i gitteret.

    required: stjernen ved etiketten - true, eller et UDTRYK, naar kravet
    afhaenger af noget andet (Materials: min/max kraeves kun for en
    lagervare). visible: et udtryk, feltet kun vises under. Et skjult felt
    koster ingen plads - gitterets hoejde regnes af de synlige boern.

    Staar feltet i cfg.WHEN (issue #210), faar cellen ogsaa betingelsen
    som Visible - sammen med visible, hvis begge er givet."""
    for c, label, kind, choices in FIELDS:
        if c == col:
            req_fx = (f"({REQUIRED} && ({required}))" if isinstance(required, str)
                      else (REQUIRED if required else "false"))
            cell = grid_cell(f"conDom{c}", label,
                             _input_for(c, kind, choices, required_formula=req_fx),
                             required=bool(required), width=width)
            if isinstance(required, str):
                # Stjernen kun, naar kravet gaelder. En stjerne ved et felt,
                # der ikke kraeves lige nu, ville lyve.
                star = cell.children[0].children[-1]
                star.vis = required
            conds = [x for x in (WHEN.get(c), visible) if x]
            if len(conds) == 1:
                cell.vis = conds[0]
            elif conds:
                cell.vis = " && ".join(f"({x})" for x in conds)
            return cell
    raise SystemExit(f"domain_parts: {col} er ikke et felt i SECTIONS")


def text_cell(width=CELL_W):
    """Raekkens tekst (Title) - kraevet, ogsaa paa en kladde."""
    return grid_cell("conDomText", cfg.TEXT_LABEL,
                     text_input("inpDomText", "varDomFText", max_length=TEXT_MAX,
                                placeholder=cfg.TEXT_PLACEHOLDER,
                                required_formula=REQUIRED, display_mode=DM_ROW,
                                onchange="Set(varDomFText, Self.Text)"),
                     required=True, width=width)


def plant_cell(width=CELL_W):
    return grid_cell("conDomPlant", cfg.PLANT_LABEL, _plant_dropdown(), required=True,
                     width=width)


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
    return "Set(varDomDocsId, varDomActiveRowId);\n" + att.load_fx("varDomActiveRowId")


def docs_cell(width=CELL_W):
    """Documentation: hvor mange dokumenter raekken har, og en knap til
    den eksisterende dokumentpopup. Dokumenterne er vedhaeftninger paa
    raekken i SharePoint, saa knappen virker foerst efter Save."""
    info = grow(text_input(
        "inpDomDocsInfo",
        ('If(IsBlank(varDomActiveRowId), "Add the row first", '
         + dt.plural(f"Coalesce({ACTIVE}.FileCount, 0)", "document") + ")"),
        display_mode="DisplayMode.View", label='"Documents on this row"'))
    text = '"Documents"'
    btn = button("btnDomDocs", text, open_active_docs_fx(),
                 width=fit_button_width(text), display_mode=DM_SEL,
                 accessible='"Open the documents for this row"')
    btn.props["LayoutMinWidth"] = btn.props["Width"]
    row = group("conDomDocsRow", [info, btn], direction="Horizontal", gap=8,
                height=36, align_items="Center", width=width)
    return grid_cell("conDomDocs", "Documentation", row, width=width)


def docs_count_cell(width=CELL_W):
    """Documentation i sidepanelets Documents-fane (issue #430): kun
    antallet. Fanen ER dokumenterne - knappen til popuppen hoerer til
    formularen uden faner (docs_cell)."""
    info = text_input(
        "inpDomDocsInfo",
        ('If(IsBlank(varDomActiveRowId), "Add the row first", '
         + dt.plural(f"Coalesce({ACTIVE}.FileCount, 0)", "document") + ")"),
        display_mode="DisplayMode.View", label='"Documents on this row"')
    info.props["Width"] = str(width)
    return grid_cell("conDomDocs", "Documentation", info, width=width)


# ---------------------------------------------------------------------------
# Sidepanelets faner: Details, Objects, Documents (Materials, issue #430)
# ---------------------------------------------------------------------------
# Hoejden paa en fanes fyldte krop (objektlisten, dokumentkontrollen):
# vinduet minus panelets hoved, fanerne og bundbjaelken.
EDITOR_TAB_BODY_H = "App.Height - 250"


def docs_tab_body(height=EDITOR_TAB_BODY_H):
    """Dokumentpopuppens krop (build_attachments) til Documents-fanen -
    samme ModernAttachments-kontrol, Save documents og read-only-note."""
    body = build_attachments().children[1]
    body.props["Height"] = height
    return body


def editor_tabs(form, extras=(), objects=None, documents=(), open_objects=""):
    """Sidepanelets indhold med faner - det faelles moenster for Materials
    og Equipment (issue #430). Fanen huskes i cfg.ROW_EDITOR_TAB_VAR, som
    load_row_fx/clear_form_fx/copy_row_fx saetter til "Details".

    form: appens formular (build_form(panel=True)); dens knapraekke
    (naestsidste barn) udelades - knapperne staar i panelets faste bund.
    extras: appens linjer under felterne. objects/documents: fanernes
    kontroller; objects=None: ingen Objects-fane (Equipment, issue #485 -
    udstyret har een funktionsplads, i formularen). open_objects: det, Objects-fanen goer ud over at vise sig
    (Materials fylder objektlisten fra raekken). Documents-fanen peger
    dokumentkontrollen paa den aabne raekke (open_active_docs_fx).

    Fanerne er altid til at trykke paa - ogsaa i visning. Felterne paa
    dem foelger selv DM_ROW og DOCS_EDIT, saa de er skrivebeskyttede dér."""
    tab = cfg.ROW_EDITOR_TAB_VAR
    TAB_REOPEN["Objects"] = open_objects if objects is not None else ""
    objects_fx = f'Set({tab}, "Objects")' + (f";\n{open_objects}" if open_objects else "")
    tabs = [("Details", "Details", f'{tab} = "Details"', f'Set({tab}, "Details")', None)]
    if objects is not None:
        tabs.append(("Objects", "Objects", f'{tab} = "Objects"', objects_fx, None))
    tabs.append(("Documents", "Documents", f'{tab} = "Documents"',
                 f'Set({tab}, "Documents");\n{open_active_docs_fx()}', None))
    selector = segmented("conDomEditorTabs", tabs, label="Row details", fit=True)
    details = group("conDomEditorDetails",
                    list(form.children[:-2]) + list(extras) + [form.children[-1]],
                    direction="Vertical", gap=12, visible=f'{tab} = "Details"')
    documents = group("conDomEditorDocuments", list(documents), direction="Vertical", gap=12,
                      visible=f'{tab} = "Documents"')
    if objects is None:
        return [selector, details, documents]
    objects = group("conDomEditorObjects", list(objects), direction="Vertical", gap=12,
                    visible=f'{tab} = "Objects"')
    return [selector, details, objects, documents]


# ---------------------------------------------------------------------------
# Formularens hoved og fod
# ---------------------------------------------------------------------------
# SEKTIONER (UX-review 2026-10, M2): formularen er grupper med en
# overskrift - Identification, Location, Manufacturer ... - i stedet for
# fire anonyme raekker felter. Overskriften er en tynd streg og et ord;
# den foerste har ingen streg (hovedet staar lige over den).
SECTION_TITLE_H = 20


def form_section(key, title, visible=None, first=False):
    """Sektionens overskrift: [streg] Titel. key: navnets hale (conDomSec<key>)."""
    t = text_ctrl(f"txtDomSec{key}", f'Upper("{title}")', size=lay.SIZE_MICRO,
                  weight="Semibold", color=C_MUTED, height=SECTION_TITLE_H, wrap="false")
    return group(f"conDomSec{key}", [t], direction="Vertical", gap=0,
                 visible=visible, pad=(0 if first else 8, 0, 0, 0))


def sectioned(sections):
    """[(key, titel, synlighed, [kontroller...]), ...] -> een liste: hver
    sektions overskrift efterfulgt af dens raekker. En sektion uden synlige
    raekker skjules med sin synlighed (fx Stock kun for en lagervare)."""
    out = []
    for i, (key, title, vis, ctrls) in enumerate(sections):
        out.append(form_section(key, title, visible=vis, first=(i == 0)))
        out.extend(ctrls)
    return out


def required_parts():
    """Stjernen og ordet "Required" - forklaringen paa felternes stjerner.
    Sekundaer: 12 px, ordet i den daempede farve; kun stjernen har
    feltstjernernes roede farve, saa de to kan kobles sammen."""
    star = text_ctrl("txtDomFormReqStar", '"*"', size=12, color=C_REQUIRED,
                     weight="Semibold", height=18, width=8, wrap="false",
                     accessible='"Required"')
    legend = text_ctrl("txtDomFormReq", '"Required"', size=12, color=C_MUTED,
                       height=18, width=text_px("Required", 12, semibold=False),
                       wrap="false")
    return star, legend


def required_legend():
    """"* Required" til sidepanelets overskrift (issue #431): oeverst til
    hoejre, foran pileknapperne, i stedet for en egen raekke oeverst i
    formularen, der skubbede den foerste sektion (fx IDENTIFICATION) ned.
    Bredden er fast (tekstens), saa det er titlen, der giver sig."""
    star, legend = required_parts()
    w = int(star.props["Width"]) + 4 + int(legend.props["Width"])
    return group("conDomFormReqLegend", [star, legend], direction="Horizontal", gap=4,
                 height=18, width=w, align_items="Center")


def form_head(title_txt, right=()):
    """Titlen, "* Required" og evt. kontroller til hoejre (No BOM Item).
    Kun uden sidepanel - med panelet staar "* Required" i panelets
    overskrift (required_legend)."""
    title = None if title_txt is None else text_ctrl(
        "txtDomFormH", f'"{title_txt}"', size=lay.SIZE_CARD_TITLE, weight="Semibold",
        height=text_min_height(lay.SIZE_CARD_TITLE),
        width=text_px(title_txt, lay.SIZE_CARD_TITLE), wrap="false")
    star, legend = required_parts()
    parts = [c for c in (title, star, legend) if c is not None]
    left = group("conDomFormTitle", parts, direction="Horizontal",
                 gap=4, height=26, align_items="Center")
    if not right:
        return left
    left_w = sum(int(c.props["Width"]) for c in parts) + (len(parts) - 1) * 4
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


# Add row-formlen - saettes af form_buttons, saa listens tomme tilstand kan
# bruge den samme (build_list kaldes efter build_form).
ADD_ROW_FX = [None]
# Det samme gem med panelets egen tilstand - sidepanelets Save (issue #402).
PANEL_SAVE_FX = [None]


def form_buttons(save_fx, save_text, new_text, new_fx=None, new_tooltip=None,
                 new_icon="Add"):
    """Save draft, Save og New row/Reset form - i den orden, med den
    primaere knap naestsidst som i HTML-projektet.

    "Delete row" stod foerst. Den er fjernet (issue #94): en gemt raekke
    slettes med ikonet paa sin egen raekke i Rows, som i VH-planens
    operationstabel. form_footer regner bredden af de knapper, der er, saa
    pladsen forsvinder med knappen.

    save_fx(status) er appens gem (save_row_fx med evt. egne krav).
    new_fx / new_tooltip / new_icon: appens egen tredje knap (opt-in,
    issue #228 - Materials' Reset spoerger foerst, naar der er noget at
    miste). Standard er den faelles "ryd formularen"."""
    # EEN gem-knap (UX-review F2/T2): "Save" - for en ny raekke og for en
    # hentet. Den gemmer som faerdig eller som kladde efter
    # kravene (save_row_fx("auto")). "Save row draft" er vaek. save_text
    # bruges ikke laengere - teksten er den samme i alle domaener.
    ADD_ROW_FX[0] = act_fx(ACT_VAR, "save", save_fx("auto"))
    PANEL_SAVE_FX[0] = panel_save_fx(PANEL_SAVE_VAR, save_fx("auto"))
    add = icon_on_mobile(fit(button(
        "btnDomSave", '"Update row"', ADD_ROW_FX[0],
        primary=True, display_mode=DM_ROW, icon=ICON_SAVE,
        tooltip=('If(IsBlank(varDomActiveRowId), "Add the row to the request - it is '
                 'saved as a draft until the required fields are filled in", '
                 '"Save the changes to this row")')), icon=True))
    add.props["Text"] = '"Save"'
    add.props["Icon"] = 'If(IsBlank(varDomActiveRowId), "Add", "Save")'
    add.props["AccessibleLabel"] = "Self.Text"
    return [
        add,
        icon_on_mobile(fit(button("btnDomNew", f'"{new_text}"', new_fx or clear_form_fx(),
                                  icon=new_icon,
        tooltip=new_tooltip or '"Clear the form and start a new row"'), icon=True)),
    ]


# ---------------------------------------------------------------------------
# De gemte raekker (issue #67 / #68, aendret i #204)
#
# Hoved med soegning, status- og vaerksfilter, en tabel der scroller
# vandret, naar den er bredere end kortet, og indsend under den.
# Kolonnerne er appens egne (SLOTS i material_parts.py /
# equipment_parts.py).
#
# EEN VISNING, IKKE TO (issue #204)
# ---------------------------------
# Her stod Compact/All columns: hver plads viste een kolonne i Compact og
# en anden i All columns, og en pille skiftede imellem dem. Det var to
# sandheder om samme tabel - overskrifter, bredder og indhold skiftede
# under haanden - og "alle kolonner" var alligevel for bredt til at laese
# paa en skaerm. Nu er der EET fast saet kolonner, og resten af raekkens
# felter ses i Details, hvor de staar i grupper.
#
# En plads er (overskrift, udtryk, mindstebredde).
# ---------------------------------------------------------------------------

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
    # Et gemt filter, der ikke laengere findes (et vaerk uden raekker),
    # giver et tomt valg - og et tomt valg filtrerer ikke (F8).
    f'    (IsBlank(drpDomStatusFilter.Selected.Value) || drpDomStatusFilter.Selected.Value = "{ALL_STATUS}" ||\n'
    "     Status = Lower(drpDomStatusFilter.Selected.Value)),\n"
    f'    (IsBlank(drpDomPlantFilter.Selected.Value) || drpDomPlantFilter.Selected.Value = "{ALL_PLANTS}" ||\n'
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
# Statuschippen (tools/status_chip.py) + cellens venstre luft.
BADGE_W = sc.table_width(sc.ROW) + CELL_PAD

# Knapperne. Raekkens handlinger er Details -> Edit -> Delete, i den
# raekkefoelge og yderst til hoejre (issue #101). Docs og Copy staar i
# MORE-kolonnen foran dem i Compact; i All columns er der ingen
# MORE-overskrift, og saa er de de foerste af handlingerne - overskriften
# "ACTIONS" flytter hen over dem.
MORE_BTNS = [("btnDomRowDocs", '"Docs"'), ("btnDomRowCopy", '"Copy"')]
ACTION_BTNS = [("btnDomRowDetails", '"Details"'), ("btnDomRowOpen", '"Edit"'),
               ("btnDomRowDelete", '"Delete row"')]
# Details aabner den eksisterende skrivebeskyttede popup (build_details).
def details_fx():
    """Raekkens Details-knap. HOOKS["details_open"] er appens egne felter i
    ruden (Materials' materialenummer)."""
    if getattr(cfg, "ROW_PANEL_ENABLED", False):
        # Details aabner sidepanelet (ingen separat popup): samme som Edit.
        return load_row_fx()
    fx = "Set(varDomDetailsId, ThisItem.RowId)"
    if HOOKS["details_open"]:
        fx += ";\n" + HOOKS["details_open"]
    return fx

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


# ---------------------------------------------------------------------------
# APPENS EGNE RAEKKEKNAPPER (opt-in, issue #228)
#
# HOOKS["row_actions"] er en liste af RowAction. Saa staar ALLE knapper i
# een ACTIONS-kolonne i den givne raekkefoelge (der er ingen MORE-kolonne),
# og i mobilkortet paa to linjer efter line. Uden krogen er listen den
# faelles - Equipment og Measuring Point genereres uaendret.
# ---------------------------------------------------------------------------
class RowAction:
    """En knap paa en gemt raekke.

    name     knappens navn (mobilkortets faar "C" bagpaa)
    text     Power Fx-teksten - maa vaere et udtryk ("Docs (2)")
    fx       OnSelect (ThisItem er raekken)
    width    fast bredde - tekstens LAENGSTE form skal kunne staa i den
    mode     DisplayMode-udtryk eller None (altid aktiv)
    danger   destruktiv knap (roed kant)
    icon     Fluent-ikon; icon_only goer knappen til kun ikonet
    label    AccessibleLabel/Tooltip; standard er teksten + raekkens noegle
    tip      Tooltip, naar det skal vaere kortere end label (issue #515:
             tooltippet gentager ikke raekkens noegle - tools/action_tips.py)
    line     1 eller 2 - linjen i mobilkortet"""

    def __init__(self, name, text, fx, width, mode=None, danger=False, icon=None,
                 icon_only=False, label=None, line=1, tip=None):
        self.name, self.text, self.fx, self.width = name, text, fx, width
        self.mode, self.danger, self.icon, self.icon_only = mode, danger, icon, icon_only
        self.label, self.line, self.tip = label, line, tip


def _actions_w(acts):
    return sum(a.width for a in acts) + ROW_BTN_GAP * (len(acts) - 1) + CELL_PAD


def _action_button(a, suffix=""):
    who = a.label or f'{a.text} & " " & ThisItem.ItemKey'
    b = button(a.name + suffix, a.text, a.fx, danger=a.danger, width=a.width,
               height=ROW_BTN_H, display_mode=a.mode, accessible=who, tooltip=a.tip or who)
    b.props["Size"] = "13"
    if a.icon:
        b.props["Icon"] = f'"{a.icon}"'
        b.props["Layout"] = ("ButtonLayout.IconOnly" if a.icon_only
                             else "ButtonLayout.IconBefore")
        if a.icon_only:
            ensure_hit(b)
    return b


# ---------------------------------------------------------------------------
# DE FAELLES RAEKKEIKONER (issue #485)
#
# Materials, Equipment og Measuring Point har de SAMME handlinger paa en
# gemt raekke, i den samme raekkefoelge, som ikoner af samme stoerrelse:
#
#     Edit (blyant)  Documents (papirclips)  Objects (link)  Copy  Delete
#
# Documents og Objects kun, hvor appen har dem: Objects kun i Materials
# (Equipment og Measuring Point sidder paa EEN funktionsplads, der vaelges
# i formularen), og Measuring Point har ingen dokumenter. Der er ingen Details-knap -
# Edit aabner sidepanelet, ogsaa paa en raekke, der kun kan ses (felterne
# er saa skrivebeskyttede) - og ingen More-menu: alle handlinger staar
# direkte i kolonnen. Hvert ikon har et tooltip, der siger handlingen og
# antallet (issue #515, tools/action_tips.py); AccessibleLabel er det samme
# med raekkens noegle bagefter.
#
# Papirclipsen er Issue Boards (ib_parts._attach_btn). Ikonerne er
# Fluent-navne paa den moderne knap (tools/icons.FLUENT).
# ---------------------------------------------------------------------------
ROW_ICON_W = lay.HIT_TOUCH
# Kan raekken kun ses? Samme regel som DM_ROW_EDIT/DM_ROW_DEL.
ROW_LOCKED = '(varDomViewOnly || ThisItem.Status = "submitted")'


def standard_row_actions(docs_fx=None, docs_n=None, objects_fx=None, objects_n=None):
    """Raekkens ikoner i den faelles raekkefoelge. docs_fx/objects_fx:
    OnSelect for Documents/Objects (None = appen har ikke handlingen);
    docs_n/objects_n: antallet, der staar i tooltippet - raekkens egne
    kolonner, det samme tal som sidepanelets fane viser."""
    key = "ThisItem.ItemKey"

    def act(name, text, fx, tip, **kw):
        return RowAction(name, text, fx, ROW_ICON_W, icon_only=True, tip=tip,
                         label=tips.label(tip, key), **kw)

    acts = [act("btnDomRowOpen", '"Edit"', load_row_fx(), tips.edit_row(ROW_LOCKED),
                icon=icons.FLUENT["edit"])]
    if docs_fx:
        acts.append(act("btnDomRowDocs", '"Documents"', docs_fx,
                        tips.documents(docs_n or "0", ROW_LOCKED),
                        icon=icons.FLUENT["attach"]))
    if objects_fx:
        acts.append(act("btnDomRowObjects", '"Objects"', objects_fx,
                        tips.functional_locations(objects_n or "0"),
                        icon=icons.FLUENT["objects"]))
    acts.append(act("btnDomRowCopy", '"Copy"', copy_row_fx(), tips.COPY_ROW,
                    mode=ROW_MODES["btnDomRowCopy"], icon=icons.FLUENT["copy"], line=2))
    acts.append(act("btnDomRowDelete", '"Delete row"', delete_this_row_fx(), tips.DELETE_ROW,
                    mode=DM_ROW_DEL, danger=True, icon=icons.FLUENT["delete"], line=2))
    return acts


# Galleriets egne 2 x 2 px skabelonpolstring og dets lodrette scrollbar.
TABLE_AVAIL = f"(({FORM_W}) - 4 - {SCROLLBAR_W})"


def col_w(spec):
    """Saa bred, at overskriften aldrig klippes - og mindst spec's minimum.

    label_px er Segoe UI's egne tegnbredder (build_helpers). text_px er et
    skoen, der med vilje rammer for bredt; paa sytten overskrifter blev det
    til flere hundrede pixels, og Compact kunne ikke staa uden scroll paa en
    1366-skaerm. 4 px oven i er sikkerheden."""
    header, _expr, min_w = spec
    return max(min_w, label_px(header, HEAD_SIZE) + 2 * CELL_PAD + 4)


def num_text(col):
    return lay.num_text(f"ThisItem.{col}")


def date_text(col):
    return f'If(IsBlank(ThisItem.{col}), "", Text(ThisItem.{col}, "{lay.DATE_FMT}"))'


class ListLayout:
    """Bredderne for tabellens kolonner.

    Tabellen FYLDER listens bredde: hver kolonne faar sin mindstebredde
    (mindst saa bred som overskriften) plus en lige del af det, der er
    tilovers. Er der intet tilovers (en tablet), er tabellen sine
    mindstebredder og scroller vandret."""

    def __init__(self, slots, actions=True):
        self.slots = list(slots)
        acts = HOOKS["row_actions"]
        if not actions:
            fixed = BADGE_W + T_GAP * (len(self.slots) + 1)
        elif acts:
            # Een ACTIONS-kolonne og ingen MORE (issue #228).
            fixed = BADGE_W + _actions_w(acts) + T_GAP * (len(self.slots) + 1)
        else:
            fixed = BADGE_W + LIST_MORE_W + LIST_ACTIONS_W + T_GAP * (len(self.slots) + 2)
        self.min_w = fixed + sum(col_w(c) for c in self.slots)
        self.spare = f"Max(0, ({TABLE_AVAIL}) - {self.min_w}) / {len(self.slots)}"
        self.table_w = f"Max({self.min_w}, {TABLE_AVAIL})"

    def width(self, i):
        return f"{col_w(self.slots[i])} + {self.spare}"

    def text(self, i, part):
        """part 0 = overskriften, 1 = udtrykket."""
        spec = self.slots[i]
        return f'"{spec[0]}"' if part == 0 else spec[1]


def _pad(ctrl):
    ctrl.props["PaddingLeft"] = str(CELL_PAD)
    return ctrl


def _head_text(name, text, width, visible=None, accessible=None):
    return _pad(text_ctrl(name, text, size=HEAD_SIZE, color=C_MUTED, weight="Semibold",
                          height=18, width=width, wrap="false", visible=visible,
                          accessible=accessible))


def _status_badge():
    """Raekkens status som den faelles statuschip (tools/status_chip.py,
    UX-review T4): ikon + "Draft"/"Valid"/"Submitted" i sentence case. Her
    stod VERSALER i et tekstmaerke, der ikke lignede hubbens status."""
    chip = sc.status_chip("imgDomRowStatus", "ThisItem.Status", sc.ROW)
    return group("conDomRowStatus", [chip], direction="Horizontal", gap=0,
                 height=sc.H, width=BADGE_W, align_items="Center",
                 pad=(0, 0, 0, CELL_PAD))


def _icon_only(b, bn):
    """Er knappen i ROW_ICON, er den kun sit ikon - paa desktop og mobil."""
    if bn in ROW_ICON:
        b.props["Icon"] = f'"{ROW_ICON[bn]}"'
        b.props["Layout"] = "ButtonLayout.IconOnly"
        ensure_hit(b)
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
    return group(name, out, direction="Horizontal", gap=ROW_BTN_GAP, height=ROW_LINE_H,
                 width=width, align_items="Center", pad=(0, 0, 0, CELL_PAD))


def _compact_row(lay_, load_fx, copy_fx, delete_fx):
    """Card row below Desktop: key + status on top, the next values under it, the actions
    on two short lines. Replaces the wide table, which would scroll sideways on a phone."""
    cs = list(lay_.slots)
    key = text_ctrl("txtDomRowKeyC", cs[0][1], size=14, weight="Semibold", height=22, wrap="false")
    key = grow(key)
    badge = sc.status_chip("imgDomRowStatusC", "ThisItem.Status", sc.ROW)
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
        return group(name, out, direction="Horizontal", gap=ROW_BTN_GAP, height=ROW_LINE_H,
                     align_items="Center")

    acts = HOOKS["row_actions"]
    if acts:
        def act_line(name, n):
            return group(name, [_action_button(a, "C") for a in acts if a.line == n],
                         direction="Horizontal", gap=ROW_BTN_GAP, height=ROW_LINE_H,
                         align_items="Center")
        line3 = act_line("conDomRowLineC3", 1)
        line4 = act_line("conDomRowLineC4", 2)
    else:
        line3 = btns("conDomRowLineC3", ACTION_BTNS, [details_fx(), load_fx, delete_fx],
                     danger=("btnDomRowDelete",), modes=ROW_MODES)
        line4 = btns("conDomRowLineC4", MORE_BTNS, [open_docs_fx(), copy_fx],
                     modes=ROW_MODES)
    return group("conDomRowC", [line1, line2, line3, line4], direction="Vertical", gap=4,
                 height="Parent.TemplateHeight - 2", align_items="Stretch",
                 width="Parent.TemplateWidth", pad=(8, CELL_PAD, 0, CELL_PAD),
                 visible=below("Desktop"))


def build_list(slots, badge_head, search_placeholder):
    """Kortet med de gemte raekker - og indsend under tabellen.

    slots: appens pladser (se ovenfor). badge_head: overskriften over
    statusmaerket ("STATUS" / "VALIDATION")."""
    lay_ = ListLayout(slots)

    # --- hovedet: titel, soegning og de to filtre ---------------------
    # Soegning og filtre huskes i SaveData-lageret (UX-review F8). Feltet
    # hedder prefDom* her og prefEq*/prefMat*/prefMp* i BIO SAP.
    search = text_input("inpDomSearch", tok.pref_get("prefDomSearch"), width="240",
                        placeholder=f'"{search_placeholder}"',
                        label='"Search the rows"',
                        onchange=tok.prefs_save({"prefDomSearch": "Self.Text"}))
    status = themed_dropdown(
        "drpDomStatusFilter", f'["{ALL_STATUS}", "Draft", "Valid", "Submitted"]',
        tok.pref_get("prefDomStatus", f'"{ALL_STATUS}"'), width="170",
        label='"Filter by status"',
        onchange=tok.prefs_save({"prefDomStatus": "Self.Selected.Value"}))
    plant = themed_dropdown("drpDomPlantFilter", PLANT_ITEMS,
                            tok.pref_get("prefDomPlant", f'"{ALL_PLANTS}"'),
                            width="170", label='"Filter by plant"',
                            onchange=tok.prefs_save({"prefDomPlant": "Self.Selected.Value"}))
    row_add = []
    panel_on = bool(getattr(cfg, "ROW_PANEL_ENABLED", False))
    if panel_on:
        copy_active = copy_row_fx().replace("ThisItem.", ACTIVE + ".")
        row_add.append(button(
            "btnDomToolbarCopy", '"Copy row"', copy_active, icon="Copy",
            width=fit_button_width('"Copy row"') + ICON_W, height=36,
            tooltip='"Copy the open row to a new draft row"',
            display_mode=("If(varDomViewOnly || IsBlank(varDomActiveRowId), "
                          "DisplayMode.Disabled, DisplayMode.Edit)"),
            visible="!varDomViewOnly"))
        row_add.append(button("btnDomPasteRows", '"Paste rows"', paste_open_fx(),
                              icon=icons.FLUENT["paste"],
                              width=fit_button_width('"Paste rows"') + ICON_W, height=36,
                              tooltip='"Paste rows copied from Excel - they are added as drafts"',
                              visible="!varDomViewOnly"))
        # Issue #310: uden raekker staar Add row kun i den tomme tilstand
        # (btnDomRowsEmptyAdd, samme betingelse IsEmpty(colDomRows)) - ikke
        # ogsaa her. Paste rows bliver staaende.
        row_add.append(button("btnDomNewRow", '"Add row"', new_row_fx(), primary=True,
                              width=fit_button_width('"Add row"'), height=36,
                              visible="!varDomViewOnly && !IsEmpty(colDomRows)"))
    # Soegning og filtre staar til venstre, Add row/Copy til hoejre: en tom,
    # fleksibel gruppe tager resten af linjen og skubber knapperne ud.
    if row_add:
        gap_ = grow(group("conDomRowsTopGap", [], direction="Horizontal", height=0))
        kids = [search, status, plant, gap_] + row_add
        gap_.vis = flow_ok(kids, FORM_W, gap=8, flex=gap_, flex_min=0)
        gap_.props["Visible"] = gap_.vis
        head = flow_row("conDomRowsTop", kids, FORM_W, gap=8, flex=gap_, flex_min=0)
    else:
        gap_ = grow(group("conDomRowsTopGap", [], direction="Horizontal", height=0))
        kids = [search, status, plant, gap_]
        gap_.vis = flow_ok(kids, FORM_W, gap=8, flex=gap_, flex_min=0)
        gap_.props["Visible"] = gap_.vis
        head = flow_row("conDomRowsTop", kids, FORM_W, gap=8, flex=gap_, flex_min=0)
    head.props["PaddingTop"] = "6"
    head.props["PaddingBottom"] = "6"
    head.props["Height"] = f"({head.props['Height']}) + 12"
    head.h = head.props["Height"]

    # --- tabellen -----------------------------------------------------------
    heads = [_head_text("txtDomHeadStatus", f'"{badge_head}"', BADGE_W)]
    cells = [_status_badge()]
    for i in range(len(slots)):
        heads.append(_head_text(f"txtDomHead{i}", lay_.text(i, 0), lay_.width(i),
                                accessible=lay_.text(i, 0)))
        cells.append(_pad(text_ctrl(f"txtDomCell{i}", lay_.text(i, 1), size=13,
                                    height=20, width=lay_.width(i), wrap="false")))
    acts = HOOKS["row_actions"]
    if acts:
        # Appens egne knapper i een kolonne (issue #228).
        aw = _actions_w(acts)
        heads.append(_head_text("txtDomHeadActions", '"ACTIONS"', aw,
                                accessible='"Actions"'))
        cells.append(group("conDomRowActions", [_action_button(a) for a in acts],
                           direction="Horizontal", gap=ROW_BTN_GAP, height=ROW_LINE_H,
                           width=aw, align_items="Center", pad=(0, 0, 0, CELL_PAD)))
    else:
        heads.append(_head_text("txtDomHeadMore", '"MORE"', LIST_MORE_W))
        heads.append(_head_text("txtDomHeadActions", '"ACTIONS"',
                                LIST_ACTIONS_W, accessible='"Actions"'))
        cells.append(_row_buttons("conDomRowMore", MORE_BTNS,
                                  [open_docs_fx(), copy_row_fx()],
                                  LIST_MORE_W, modes=ROW_MODES))
        cells.append(_row_buttons("conDomRowActions", ACTION_BTNS,
                                  [details_fx(), load_row_fx(), delete_this_row_fx()],
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
             + if_below("Desktop", str(GAL_ROWS_C), str(GAL_ROWS)) + "), 1) * "
             + if_below("Desktop", str(ROW_H_C + 2), str(ROW_H + 2)))
    rule = row_rule("rctDomRowRule", if_below("Desktop", str(ROW_H_C), str(ROW_H)))
    gal = row_list("Dom", f"Sort({LIST_SCOPE}, RowId, SortOrder.Descending)",
                   [row, row_c, rule], gal_h, if_below("Desktop", str(ROW_H_C), str(ROW_H)),
                   onselect=load_row_fx(), width=f"({table_w}) + 4 + {SCROLLBAR_W}",
                   accessible="Saved rows")
    if panel_on:
        gal.props["TemplateFill"] = (
            f"If(ThisItem.RowId = varDomActiveRowId && IfError(varDomEditorOpen, false), "
            f"{C_ROW_PRESSED}, {C_TRANSPARENT})")

    # Vandret scroll, naar tabellen er bredere end kortet (All columns, og
    # Compact paa en tablet). Start, ikke Stretch - check_layout regel 14.
    # Den vandrette scrollbar tager hoejde, saa den laegges til, naar den
    # er der.
    wide = f"(({table_w}) + 4 + {SCROLLBAR_W}) > ({FORM_W})"
    table = group("conDomTableWrap", [list_head, gal], direction="Vertical", gap=0,
                  overflow_x="Scroll", width="Parent.Width", align_items="Start")
    table.props["Height"] = f"{table.props['Height']} + If({wide}, {SCROLLBAR_W}, 0)"
    table.h = table.props["Height"]

    # TOM LISTE (UX-review F4/T9): "No rows yet" med Add row - samme gem som
    # formularens knap. Measuring Points viste kun overskrifterne.
    empty = empty_state(
        "conDomRowsEmpty",
        'If(IsEmpty(colDomRows), "No rows yet - fill in the details and choose Add row.", '
        '"No rows match the search and filters.")',
        "Add row", new_row_fx() if getattr(cfg, "ROW_PANEL_ENABLED", False)
        else ADD_ROW_FX[0] or "false", icon_key=cfg.APP_KEY,
        button_name="btnDomRowsEmptyAdd", action_icon="Add",
        action_visible="IsEmpty(colDomRows) && !varDomViewOnly",
        visible=f"IsEmpty({LIST_SCOPE})")
    table.vis = f"!IsEmpty({LIST_SCOPE})"
    table.props["Visible"] = table.vis

    # HVAD MANGLER (UX-review M4): efter Submit staar kladde-raekkerne her
    # med "Open row" - den samme handling som raekkens Edit. Listen gaar
    # selv vaek, naar der ikke er flere kladder.
    fix = validation_summary(
        "Dom", f"Sort({DRAFTS}, RowId, SortOrder.Descending)",
        f'ThisItem.ItemKey & If(IsBlank(ThisItem.{cfg.C_TEXT}), "", "  \u00b7  " & ThisItem.{cfg.C_TEXT})',
        "Open row" if not panel_on else "Go to field", load_row_fx(),
        # Lige efter Submit (GUID ryddet, samlingen har indsendte raekker)
        # ligger kladderne paa den indsendte anmodning (R2-002, valg a).
        f'If(IsBlank(varDomRequestGuid) && CountRows(Filter(colDomRows, Status = "submitted")) > 0, '
        f'{dt.plural(f"CountRows({DRAFTS})", "draft row")} & " stayed on the request - '
        'complete and submit them if the request is returned", '
        + ((f'{dt.plural(f"CountRows({DRAFTS})", "draft row")} & '
            f'If(CountRows({DRAFTS}) = 1, " - complete it to submit it too", '
            '" - complete them to submit them too")') if not panel_on else '"Still missing"')
        + ')',
        (f"IfError({FIX_VAR}, false) && CountRows({DRAFTS}) > 0 && !varDomViewOnly"
         if not panel_on else f"CountRows({DRAFTS}) > 0 && !varDomViewOnly"),
        f"Set({FIX_VAR}, false)", closable=not panel_on)
    parts = [head, table, empty] + _submit_parts()
    parts.insert(1 if not panel_on else 3, fix)
    # Raekkeloftet (R2-041): under tabellen, kun naar det er ramt.
    cap = text_ctrl("txtDomRowsCap", f'"{ROWS_CAP_MSG}"', size=13, color=C_WARN_FG,
                    height=if_below("Tablet", 40, 20), wrap="true", visible=ROWS_CAPPED)
    parts.insert(parts.index(table) + 1, cap)
    return card("conDomRowsCard", parts)


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


# ---------------------------------------------------------------------------
# PASTE ROWS FROM EXCEL (UX-review L3)
#
# Brugeren kopierer celler i Excel og indsaetter dem: en raekke pr. linje,
# kolonnerne adskilt af tabulator i raekkefoelgen PASTE_COLS. "Preview"
# laeser teksten ind i colDomPaste og siger pr. linje, om den kan tilfoejes;
# "Add" skriver de gode linjer som KLADDE-raekker, som brugeren derefter
# aabner og fuldfoerer i panelet. En overskriftslinje (beskrivelsens navn i
# foerste celle) springes over. Kun tekst- og valgfelter kan indsaettes -
# tal, datoer og ja/nej udfyldes i panelet.
# ---------------------------------------------------------------------------
PASTE_VAR = "varDomPasteOpen"
PASTE_TEXT = "varDomPasteText"


def paste_cols():
    """[(kolonne, etiket)] i den raekkefoelge, cellerne skal staa i."""
    cols = [(cfg.C_TEXT, cfg.TEXT_LABEL), ("Plant", cfg.PLANT_LABEL)]
    for col, label, kind, _ch in FIELDS:
        if kind in ("text", "long", "choice") and col not in ("Plant", cfg.C_TEXT):
            cols.append((col, label))
    return cols


def paste_schema():
    s = {"Line": "0", "Ok": "false", "Note": '""'}
    for col, _l in paste_cols():
        s[col] = '""'
    return ("colDomPaste", s)


def _paste_preview_fx():
    cols = paste_cols()
    # For lange celler (R2-038): linjen er roed, med en note, og taeller
    # ikke med i "Add N rows".
    too_long = []
    for i, (c, l) in enumerate(cols):
        n = TEXT_MAX if c == cfg.C_TEXT else MAX_LEN.get(c)
        if n and c != "Plant":
            too_long.append((f'Len(IfError(Trim(Index(c, {i + 1}).Value), "")) > {n}',
                             f"{l} longer than {n} characters"))
    cells = ",\n".join(
        f"                    {c}: IfError(Trim(Index(c, {i + 1}).Value), \"\")"
        for i, (c, _l) in enumerate(cols) if c != "Plant")
    return (
        "ClearCollect(\n"
        "    colDomPaste,\n"
        "    ForAll(\n"
        f"        Filter(Split(Substitute(Coalesce({PASTE_TEXT}, \"\"), Char(13), \"\"), Char(10)),\n"
        f"               !IsBlank(Trim(Value)) && Upper(Trim(First(Split(Value, Char(9))).Value)) <> \"{cfg.TEXT_LABEL.upper()}\") As L,\n"
        "        With(\n"
        "            { c: Split(L.Value, Char(9)) },\n"
        "            With(\n"
        "                {\n"
        f"                    p: IfError(Trim(Index(c, 2).Value), \"\")\n"
        "                },\n"
        "                With(\n"
        "                    { plant: If(IsBlank(p), \"\", LookUp(colDomPlants, Upper(Value) = Upper(p)).Value) },\n"
        "                    {\n"
        "                        Line: 0,\n"
        "                        Plant: Coalesce(plant, p),\n"
        + cells.replace("                    ", "                        ") + ",\n"
        "                        Ok: !IsBlank(IfError(Trim(Index(c, 1).Value), \"\")) && (IsBlank(p) || !IsBlank(plant))"
        + "".join(f" && !({t})" for t, _n in too_long) + ",\n"
        "                        Note: If(\n"
        "                            IsBlank(IfError(Trim(Index(c, 1).Value), \"\")), \"" + cfg.TEXT_LABEL + " is missing\",\n"
        "                            !IsBlank(p) && IsBlank(plant), \"Unknown plant \" & p,\n"
        + "".join(f"                            {t}, \"{n}\",\n" for t, n in too_long) +
        "                            \"Ready\"\n"
        "                        )\n"
        "                    }\n"
        "                )\n"
        "            )\n"
        "        )\n"
        "    )\n"
        ")"
    )


def _paste_add_fx():
    copy = []
    for col, _l in paste_cols():
        if col == "Plant":
            copy.append("                    Plant: P.Plant,")
        elif col in SP_CHOICE:
            copy.append(f"                    {col}: If(IsBlank(P.{col}), Blank(), {{ Value: P.{col} }}),")
        else:
            copy.append(f"                    {col}: P.{col},")
    key = ri.row_key(cfg.PREFIX, "n.ID")
    return (
        "IfError(\n"
        # Samlet skrivning, som ved Duplicate (regel 15, issue #342).
        "    With(\n"
        "        { created: Patch(\n"
        f"            {cfg.L_ROWS},\n"
        f"            ForAll(Filter(colDomPaste, Ok), Defaults({cfg.L_ROWS})),\n"
        "            ForAll(Filter(colDomPaste, Ok) As P, {\n"
        + "\n".join(copy) + "\n"
        '                    RowStatus: { Value: "draft" },\n'
        # Ogsaa ejerens raekker hoerer til den aabne anmodning (R2-002).
        '                    RequestGuid: Coalesce(varDomRequestGuid, ""),\n'
        '                    RequestNo: Coalesce(varDomRequestNo, ""),\n'
        f"                    RequesterEmail: If({AS_ADMIN}, Lower(varDomIdx.RequesterEmail), varDomMe),\n"
        f"                    RequesterName: If({AS_ADMIN}, varDomIdx.RequesterName, User().FullName)\n"
        "            })\n"
        "        ) },\n"
        "        Patch(\n"
        f"            {cfg.L_ROWS},\n"
        "            ForAll(created As n, { ID: n.ID }),\n"
        f"            ForAll(created As n, {{ RowId: n.ID, ItemKey: {key},\n"
        f'                AttachmentFolder: "{attflows.LIBRARY}/" & {key} }})\n'
        "        )\n"
        "    );\n"
        + refresh_rows_fx(4) + ";\n"
        '    Notify(Text(CountRows(Filter(colDomPaste, Ok))) & " rows added as drafts. Open each row to complete it.", '
        "NotificationType.Success);\n"
        f"    {act_mark(ACT_VAR, 'add')};\n"
        f"    Set({PASTE_VAR}, false);\n"
        f'    Set({PASTE_TEXT}, "");\n'
        "    Clear(colDomPaste),\n"
        f"    {act_mark(ACT_VAR, 'add', False)};\n"
        '    Notify("Could not add the rows: " & FirstError.Message, NotificationType.Error)\n'
        ")")


def paste_open_fx():
    return f'Set({PASTE_TEXT}, "");\nClear(colDomPaste);\nReset(inpDomPaste);\nSet({PASTE_VAR}, true)'


def build_paste():
    """Popuppen "Paste rows" - [sloer, popup]."""
    from build_helpers import popup_head, popup_body_max
    vis = f"IfError({PASTE_VAR}, false)"
    close = (f"Set({PASTE_VAR}, false);\n"
             f'If(IfError({ACT_VAR} = "add:failed", false), Set({ACT_VAR}, ""))')
    backdrop = tap_backdrop("conDomPasteBackdrop", vis, close)
    title = text_ctrl("txtDomPasteTitle", '"Paste rows"', size=lay.SIZE_CARD_TITLE,
                      weight="Semibold", height=26, wrap="false")
    head = popup_head("conDomPasteHead", title, "btnDomPasteClose", close)
    # Kolonnenavnene som hver sin tekst - de er etiketter, ikke en saetning.
    names = "Concat([" + ", ".join(f'"{l}"' for _c, l in paste_cols()) + '], Value, ", ")'
    help_ = text_ctrl("txtDomPasteHelp",
                      '"Copy the cells in Excel and paste them here, one row per line. '
                      'The rows are added as drafts. Columns in this order: " & ' + names,
                      size=13, color=C_MUTED, height=if_below("Tablet", 132, 80), wrap="true")
    inp = text_input("inpDomPaste", f"Coalesce({PASTE_TEXT}, \"\")", height=140, ttype="Multiline",
                     placeholder='"Paste from Excel"', label='"Rows to paste"',
                     onchange=f"Set({PASTE_TEXT}, Self.Text)")
    preview = button("btnDomPastePreview", '"Preview"', _paste_preview_fx(),
                     width=fit_button_width('"Preview"'), height=36,
                     display_mode=f'If(IsBlank(Trim(Coalesce({PASTE_TEXT}, ""))), '
                                  "DisplayMode.Disabled, DisplayMode.Edit)")
    line = text_ctrl(
        "txtDomPasteLine",
        f'ThisItem.{cfg.C_TEXT} & If(IsBlank(ThisItem.Plant), "", "  ·  " & ThisItem.Plant) '
        '& "  —  " & ThisItem.Note',
        size=13, height=24, wrap="false",
        extra={"Color": f"If(ThisItem.Ok, {C_TITLE}, {C_INVALID_FG})",
               "Width": "Parent.TemplateWidth"})
    # Fra Desktop faar listen sin egen rulning efter seks linjer; under
    # Desktop vokser den, og popuppens indhold scroller i stedet.
    gal_h = f"If({at_least('Desktop')}, Min(CountRows(colDomPaste), 6), CountRows(colDomPaste)) * 26"
    gal = Ctrl("galDomPaste", "Gallery", variant="Vertical", props={
        "AccessibleLabel": '"Preview of the pasted rows"',
        "BorderStyle": "BorderStyle.None", "Fill": C_TRANSPARENT, "FillPortions": "0",
        "Height": gal_h, "Items": "colDomPaste", "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None", "Selectable": "false",
        "ShowScrollbar": at_least("Desktop"), "TabIndex": "0", "TemplatePadding": "0",
        "TemplateSize": "26", "Width": "Parent.Width",
    }, children=[line], h=gal_h, vis="!IsEmpty(colDomPaste)")
    ok_n = "CountRows(Filter(colDomPaste, Ok))"
    add_txt = f'If({ok_n} = 0, "Add rows", "Add " & Text({ok_n}) & " rows")'
    add = button("btnDomPasteAdd", add_txt, act_fx(ACT_VAR, "add", _paste_add_fx()), primary=True,
                 icon="Add", width=fit_button_width('"Add 00 rows"') + ICON_W, height=36,
                 display_mode=f"If({ok_n} = 0, DisplayMode.Disabled, DisplayMode.Edit)")
    # "Adding..." i knappen (eet ventetegn, issue #441); popuppen lukker,
    # naar raekkerne er tilfoejet - ellers staar "Add failed" her (#420).
    act_button(add, ACT_VAR, "add")
    status = act_status("DomPasteAct", ACT_VAR, ("add",))
    footer = group("conDomPasteFooter", [preview, *status, add], direction="Horizontal", gap=8,
                   height=36, justify="End", align_items="Center")
    body = du.capped_body("conDomPasteBody", [help_, inp, gal],
                          popup_body_max([head.h, footer.h]))
    modal = group("conDomPasteModal", [head, body, footer], direction="Vertical",
                  gap=12, fill=C_MODAL_BG, border_color=C_PRIMARY_SOFT, radius=lay.RADIUS_MODAL,
                  pad=(18, 18, 18, 18), width="Min(640, App.Width - 24)",
                  drop_shadow="ExtraBold", visible=vis)
    modal.props["X"] = "(App.Width - Self.Width) / 2"
    modal.props["Y"] = "Max(12, (App.Height - Self.Height) / 3)"
    return [backdrop, modal]
