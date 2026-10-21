# -*- coding: utf-8 -*-
"""
Sidepanelets Objects-fane i Materials (issue #485). Equipment og Measuring
Point har ingen: de sidder paa EEN funktionsplads, der vaelges i formularen.

HVAD FANEN ER
-------------
Funktionspladserne, raekken er knyttet til - i SAP de funktionspladser,
hvis styklister (BOM) materialet skal paa. De gemmes paa
raekken som objektlisten (tools/object_list.py):

    ObjectList      koderne, sorteret og adskilt af "; "
    ObjectListJson  kode + beskrivelse
    FunctionalLocation  den FOERSTE kode (soegning, liste og SAP-flowene
                        laeser stadig kolonnen)

    Objects
    Search with at least N characters, then choose Object list ...
    [ SSV13 HFC|                 v ][ Search ][ Object list ]
    Functional locations (2)
    SSV13 HFC10AJ010   Pump 1                               [trash]
    SSV13 HFC10AJ020   Pump 2                               [trash]

OBJECT LIST-POPUPPEN (issue #513)
---------------------------------
Foer valgte man EEN funktionsplads i comboboksen og trykkede Add. Nu
aabner "Object list" en popup med soegningens resultater (og de allerede
valgte) med afkrydsning. Krydserne skrives i en KLADDE (colDomObjDraft),
der fyldes fra listen, hver gang popuppen aabnes - saa valget bevares.
Foerst "Apply selection" skriver kladden i formularens liste; Cancel og X
kasserer den. Dubletter kan ikke opstaa: kladden sammenligner paa
Upper(Trim(kode)).

FANEN ER EN DEL AF FORMULAREN
-----------------------------
Foer (Materials, issue #228) var listen en popup paa den GEMTE raekke, og
hver Add og Remove blev skrevet til SharePoint med det samme. En ny raekke
kunne derfor ikke faa funktionspladser, foer den var gemt - fanen stod som
"Read only" paa en ny raekke.

Nu er listen formularens egen samling (colDomObjects) - som felterne paa
Details-fanen:
  - den fyldes fra raekken, naar raekken hentes (Edit, Documents, Objects,
    Previous/Next, Reset) og ryddes, naar formularen ryddes (load_extra /
    clear_extra)
  - Object list og skraldespanden retter kun samlingen. Den bliver staaende, naar brugeren
    skifter fane - fanen henter IKKE raekken igen
  - Save skriver den paa raekken sammen med resten (extra_patch), og den
    staar i admin-loggens diff og i Reset's "ugemte aendringer" (extra_diff)
  - i visning (anmodningen kan kun ses, eller raekken er indsendt) kan
    fanen aabnes, men soegning og Object list er skjult og skraldespanden
    er slaaet fra

Modulet kender hverken materialer eller udstyr: appen giver mindstelaengden
for soegningen, det, der skal ske efter en aendring, og sine egne linjer
under listen.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import domain_parts as dp
import object_list as ol
import build_flsearch as fl
from fl_picker import fl_picker
from gen_screen import C_MUTED
from gen_screen import Ctrl, C_MODAL_BG, C_PRIMARY_SOFT, C_TRANSPARENT
from build_helpers import (text_ctrl, capped_body, button, group, grow, popup_head,
                           tap_backdrop, checkbox_theme, fit_button_width)
from layout_tokens import if_below
import layout_tokens as lay
import icons
import status_chip as chip

# Formularens objektliste og det valgte soegeresultat.
OBJECTS = "colDomObjects"
PICK = "varDomObjPick"
FL_MSG = "varDomFlMsg"
SCHEMA = ol.schema()
# Object list-popuppen (issue #513): aaben/lukket, kladden med krydserne og
# kandidaterne (soegningens resultater plus de allerede valgte).
LIST_OPEN = "varDomObjListOpen"
DRAFT = "colDomObjDraft"
CANDS = "colDomObjCands"
STATE = f'Set({PICK}, "");\nSet({LIST_OPEN}, false)'

# Kan raekken i formularen rettes? Samme regel som domain_parts.DM_ROW.
EDIT = '!(IfError(varDomViewOnly, false) || varDomRowStatus = "submitted")'
DM_EDIT = f"If({EDIT}, DisplayMode.Edit, DisplayMode.Disabled)"


def restore_fx(src="ThisItem"):
    """Fyld formularens liste fra raekken src, som den er gemt."""
    return ol.restore_fx(OBJECTS, json_src=f"{src}.ObjectListJson",
                         list_src=f"{src}.ObjectList",
                         fl_src=f"{src}.FunctionalLocation")


def load_extra(after=""):
    """load_row_fx' krog: listen fra raekken (ThisItem - domain_parts
    erstatter det med sit opslag), soegningen forfra."""
    fx = restore_fx() + f';\nSet({PICK}, "")'
    return fx + (f";\n{after}" if after else "")


def clear_extra():
    return f'{ol.clear_fx(OBJECTS)};\nSet({PICK}, "");\nSet({LIST_OPEN}, false)'


def open_tab_fx():
    """Objects-fanen aabnes: kun soegningen starter forfra. Listen hentes
    IKKE igen - saa et valg, der ikke er gemt endnu, bliver staaende."""
    return f'Set({PICK}, "");\n{dp.fl_reset_fx_dom()}'


def open_row_fx(tab_var):
    """Raekkens Objects-ikon: hent raekken og aabn den paa Objects."""
    return (dp.load_row_fx() + f';\nSet({tab_var}, "Objects");\n' + open_tab_fx())


def extra_patch(fl_col=True):
    """Kolonnerne, Save skriver. fl_col=False, naar FL-kolonnen allerede er
    et felt i formularen, som appen selv holder i takt med listen."""
    out = [("ObjectList", ol.codes_fx(OBJECTS)),
           ("ObjectListJson", ol.json_fx(OBJECTS))]
    if fl_col:
        out.insert(0, ("FunctionalLocation", ol.first_fx(OBJECTS)))
    return out


# Det, der stod paa raekken: listen, eller FL-kolonnen alene paa en gammel
# raekke (restore_fx fylder listen paa samme maade).
SAVED_CODES = ('If(IsBlank(Trim(Coalesce(o.ObjectList, ""))), '
               'Trim(Coalesce(o.FunctionalLocation, "")), o.ObjectList)')


def extra_diff():
    """Admin-loggens diff og Reset's "ugemte aendringer" (domain_parts
    HOOKS["extra_diff"])."""
    return [("Object list", SAVED_CODES, ol.codes_fx(OBJECTS))]


def _same(code):
    """Er raekken i kladden den samme kode? Store og smaa bogstaver og
    mellemrum foran og bagved er den samme kode (som ol.add_fx)."""
    return f"Upper(Trim(Code)) = Upper(Trim({code}))"


IN_DRAFT = f"CountRows(Filter({DRAFT}, {_same('ThisItem.Code')})) > 0"


def open_list_fx():
    """Object list aabnes: kladden er formularens liste, som den staar nu
    (saa valget bevares), og kandidaterne er soegningens resultater plus de
    valgte, der ikke er blandt dem - saa de ogsaa kan fravaelges her."""
    return (
        f"Clear({DRAFT});\n"
        f"Collect({DRAFT}, ForAll({OBJECTS} As O, {{ Code: O.Code, Description: O.Description }}));\n"
        f"Clear({CANDS});\n"
        f"Collect({CANDS}, ForAll(colDomFl As R,\n"
        '    { Code: Trim(R.Code), Description: Coalesce(R.Description, "") }));\n'
        f"Collect({CANDS}, ForAll(\n"
        f"    Filter({OBJECTS} As O, IsBlank(LookUp(colDomFl, {_same('O.Code')}).Code)) As S,\n"
        "    { Code: S.Code, Description: S.Description }));\n"
        f"Set({LIST_OPEN}, true)"
    )


def close_list_fx():
    """Cancel og X: luk og kasser kladden - listen er uaendret."""
    return f"Set({LIST_OPEN}, false);\nClear({DRAFT});\nClear({CANDS})"


def apply_fx(after=""):
    """Apply selection: kladden ER nu formularens liste. Intet skrives til
    SharePoint - det goer Save. after: appens eget (Materials slaar de
    systemansvarlige op), som efter skraldespanden."""
    fx = (f"Clear({OBJECTS});\n"
          f"Collect({OBJECTS}, ForAll({DRAFT} As D, {{ Code: D.Code, Description: D.Description }}));\n"
          f'Set({FL_MSG}, Text({ol.count_fx(OBJECTS)}) & If({ol.count_fx(OBJECTS)} = 1, '
          '" functional location", " functional locations") & " in the object list.");\n'
          + close_list_fx())
    return fx + (f";\n{after}" if after else "")


# Popuppens bredde, polstring og raekker.
LIST_W = "Min(640, App.Width - 40)"
LIST_PAD = 18
LIST_ROW_H = 40
LIST_CHK_W = 28
LIST_CODE_W = 170
LIST_STATUS = [
    ("selected", "Selected", icons.STATUS_READY, "ok"),
    ("available", "Available", icons.STATUS_ADD, "info"),
]


def object_list_button(after_open="", min_len=None):
    """Object list - lige efter Search i FL-soegningens raekke. Den kan
    trykkes, naar den aktuelle soegning har fundet noget, eller naar der
    allerede er valgt funktionspladser (de kan saa fravaelges)."""
    found = fl_found_fx()
    b = button("btnDomObjList", '"Object list"', open_list_fx(),
               width=fit_button_width('"Object list"'), height=36,
               display_mode=(f"If({EDIT} && ({found} > 0 || {ol.count_fx(OBJECTS)} > 0), "
                             "DisplayMode.Edit, DisplayMode.Disabled)"),
               accessible='"Object list - choose the functional locations for this row"',
               tooltip='"Choose functional locations from the search results"')
    b.props["LayoutMinWidth"] = b.props["Width"]
    return b


def fl_found_fx():
    from fl_picker import result_count_fx
    return result_count_fx(combo=dp.FL_COMBO, results="colDomFl",
                           busy_var=dp.FL_BUSY_VAR, last_var=dp.FL_LAST_VAR)


def build_popup(after=""):
    """Object list-popuppen - [sloer, popup]. Appen laegger den i sine
    egne popupper (material_parts.build_popups), saa den tegnes OVER
    sidepanelet."""
    vis = f"IfError({LIST_OPEN}, false)"
    back = tap_backdrop("conDomObjListBackdrop", vis, close_list_fx())
    title = text_ctrl("txtDomObjListTitle", '"Object list"', size=lay.SIZE_CARD_TITLE,
                      weight="Semibold", height=26, wrap="false")
    head = popup_head("conDomObjListHead", title, "btnDomObjListClose", close_list_fx(),
                      accessible='"Close the object list without changes"')
    under = text_ctrl(
        "txtDomObjListSub",
        f'If(IsBlank({dp.FL_LAST_VAR}), "Functional locations on this row.", '
        f'Text(CountRows(colDomFl)) & " found for " & {dp.FL_LAST_VAR} & '
        '". Tick the ones the material belongs to.")',
        size=12, color=C_MUTED, height=if_below("Tablet", "36", "18"), wrap="true")

    chk = Ctrl("chkDomObjPick", "ModernCheckbox", props=checkbox_theme({
        "AccessibleLabel": '"Select " & ThisItem.Code',
        "Default": IN_DRAFT,
        "Height": "24",
        "Label": '""',
        "OnCheck": (f"If(\n    !({IN_DRAFT}),\n"
                    f"    Collect({DRAFT}, {{ Code: ThisItem.Code, Description: ThisItem.Description }})\n)"),
        "OnUncheck": f"RemoveIf({DRAFT}, {_same('ThisItem.Code')})",
        "Width": str(LIST_CHK_W),
    }), h=24)
    code = text_ctrl("txtDomObjListCode", "ThisItem.Code", size=13, weight="Semibold",
                     height=20, wrap="false", width=LIST_CODE_W)
    desc = grow(text_ctrl("txtDomObjListDesc", 'Coalesce(ThisItem.Description, "")', size=12,
                          color=C_MUTED, height=20, wrap="false"))
    status = chip.status_chip("imgDomObjListStatus",
                              f'If({IN_DRAFT}, "selected", "available")', LIST_STATUS)
    row = group("conDomObjListRow", [chk, code, desc, status], direction="Horizontal",
                gap=10, height=LIST_ROW_H, pad=(0, 8, 0, 8), fill=C_TRANSPARENT,
                align_items="Center", width="Parent.TemplateWidth")
    n = f"CountRows({CANDS})"
    gal_h = f"Min(Max({n}, 1) * {LIST_ROW_H}, Max({LIST_ROW_H * 2}, App.Height - 300))"
    gal = Ctrl("galDomObjList", "Gallery", variant="Vertical", props={
        "AccessibleLabel": '"Functional locations to choose from"',
        "BorderStyle": "BorderStyle.None",
        "Fill": C_TRANSPARENT,
        "FillPortions": "0",
        "Height": gal_h,
        "Items": f"Sort({CANDS}, Code)",
        "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None",
        "Selectable": "false",
        "ShowScrollbar": "true",
        "TabIndex": "0",
        "TemplatePadding": "0",
        "TemplateSize": str(LIST_ROW_H),
        "Width": f"({LIST_W}) - {2 * LIST_PAD}",
        "WrapCount": "1",
        "Visible": f"{n} > 0",
    }, children=[row], h=gal_h, vis=f"{n} > 0")
    empty = text_ctrl("txtDomObjListEmpty",
                      '"Nothing to choose from yet. Search for a functional location first."',
                      size=12, color=C_MUTED, height=18, wrap="false", visible=f"{n} = 0")

    info = grow(text_ctrl("txtDomObjListInfo", f'Text(CountRows({DRAFT})) & " selected"',
                          size=13, color=C_MUTED, height=18, wrap="false"))
    cancel = button("btnDomObjListCancel", '"Cancel"', close_list_fx(),
                    width=fit_button_width('"Cancel"'), height=36,
                    accessible='"Cancel - close without changing the object list"')
    use = button("btnDomObjListApply", '"Apply selection"', apply_fx(after), primary=True,
                 width=fit_button_width('"Apply selection"'), height=36,
                 display_mode=DM_EDIT,
                 accessible='"Apply the selected functional locations to this row"',
                 tooltip='"Apply the selection to this row - it is saved when you save the row"')
    for b in (cancel, use):
        b.props["LayoutMinWidth"] = b.props["Width"]
    foot = group("conDomObjListFoot", [info, cancel, use], direction="Horizontal", gap=8,
                 height=36, align_items="Center")
    modal = group("conDomObjListModal", [head, under, gal, empty, foot],
                  direction="Vertical", gap=12, fill=C_MODAL_BG, border_color=C_PRIMARY_SOFT,
                  radius=lay.RADIUS_MODAL, pad=(LIST_PAD,) * 4, width=LIST_W,
                  drop_shadow="ExtraBold", visible=vis)
    modal.props["X"] = dp.MODAL_X
    modal.props["Y"] = dp.MODAL_Y
    return [back, modal]


def tab_body(height, min_len=None, after="", extra=()):
    """Objects-fanens krop: hjaelpelinjen, FL-soegningen med Object list,
    svaret og listen.

    min_len: mindste antal tegn for soegningen (Materials: 16).
    after: Power Fx efter Apply selection og skraldespanden. extra: appens
    linjer under listen."""
    n_min = min_len or fl.MIN_SEARCH_LEN
    hint = text_ctrl(
        "txtDomObjHint",
        f'If({EDIT}, "Search with at least {n_min} characters, then open the object list '
        'to tick the functional locations. They are saved with the row when you choose Save.", '
        '"Read only - the row or the request cannot be changed.")',
        size=12, color=C_MUTED, height=if_below("Tablet", "54", "36"), wrap="true")
    # Soegningen er FL-vaelgerens egen (tools/fl_picker.py) - den samme som
    # i resten af appen. Object list staar lige efter Search (issue #513).
    picker = fl_picker(
        "Dom", combo=dp.FL_COMBO, results="colDomFl", raw_var="varDomFlRaw",
        msg_var=FL_MSG, busy_var=dp.FL_BUSY_VAR, query_var=dp.FL_QUERY_VAR,
        last_var=dp.FL_LAST_VAR, pick_var=PICK,
        default_items=f"Filter(colDomFl, Code = {PICK})",
        display_mode="DisplayMode.Edit", min_len=n_min,
        width="Parent.Width", stack_search=True, trail=[object_list_button()])
    picker.vis = EDIT
    msg = dp.build_fl_msg()
    pnl = ol.panel(
        "Dom", OBJECTS, width="Parent.Width", msg_var=FL_MSG,
        display_mode=DM_EDIT, label="Functional locations", extra=extra,
        hint='"No functional locations on this row yet."',
        on_remove=after or None)
    body = capped_body("conDomObjTabBody", [hint, picker, msg, pnl], height)
    body.props["Height"] = height
    body.h = height
    return body
