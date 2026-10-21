# -*- coding: utf-8 -*-
"""
Sidepanelets Objects-fane - den samme i Materials og Equipment (issue #485).

HVAD FANEN ER
-------------
Funktionspladserne, raekken er knyttet til - i SAP de funktionspladser,
hvis styklister (BOM) materialet eller udstyret skal paa. De gemmes paa
raekken som objektlisten (tools/object_list.py):

    ObjectList      koderne, sorteret og adskilt af "; "
    ObjectListJson  kode + beskrivelse
    FunctionalLocation  den FOERSTE kode (soegning, liste og SAP-flowene
                        laeser stadig kolonnen)

    Objects
    Search with at least N characters, pick a result and press Add ...
    [ SSV13 HFC|                      v ][ Search ]
    Functional locations (2)                              [ Add ]
    SSV13 HFC10AJ010   Pump 1                           [ Remove ]
    SSV13 HFC10AJ020   Pump 2                           [ Remove ]

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
  - Add og Remove retter kun samlingen. Den bliver staaende, naar brugeren
    skifter fane - fanen henter IKKE raekken igen
  - Save skriver den paa raekken sammen med resten (extra_patch), og den
    staar i admin-loggens diff og i Reset's "ugemte aendringer" (extra_diff)
  - i visning (anmodningen kan kun ses, eller raekken er indsendt) kan
    fanen aabnes, men soegning og Add er skjult og Remove er slaaet fra

Modulet kender hverken materialer eller udstyr: appen giver mindstelaengden
for soegningen, det, der skal ske efter en aendring (Equipment holder sit
FL-felt i takt), og sine egne linjer under listen.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import domain_parts as dp
import object_list as ol
import build_flsearch as fl
from fl_picker import fl_picker
from gen_screen import C_MUTED
from build_helpers import text_ctrl, capped_body
from layout_tokens import if_below

# Formularens objektliste og det valgte soegeresultat.
OBJECTS = "colDomObjects"
PICK = "varDomObjPick"
# Antallet foer Add - saa "efter en aendring" kun koerer, naar der kom en til.
COUNT_BEFORE = "varDomObjN"
FL_MSG = "varDomFlMsg"
SCHEMA = ol.schema()
STATE = f'Set({PICK}, "")'

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
    return f'{ol.clear_fx(OBJECTS)};\nSet({PICK}, "")'


def open_tab_fx():
    """Objects-fanen aabnes: kun soegningen starter forfra. Listen hentes
    IKKE igen - saa et valg, der ikke er gemt endnu, bliver staaende."""
    return f'Set({PICK}, "");\n{dp.fl_reset_fx_dom()}'


def open_row_fx(tab_var):
    """Raekkens Objects-ikon: hent raekken og aabn den paa Objects."""
    return (dp.load_row_fx() + f';\nSet({tab_var}, "Objects");\n' + open_tab_fx())


def extra_patch(fl_col=True):
    """Kolonnerne, Save skriver. fl_col=False, naar FL-kolonnen allerede er
    et felt i formularen (Equipment holder feltet i takt med listen)."""
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


def add_fx(after=""):
    """Add: laeg det VALGTE resultat i listen. Dubletter og et tomt valg
    afvises af ol.add_fx. Intet skrives til SharePoint - det goer Save."""
    desc = f'Coalesce(LookUp(colDomFl, Code = {PICK}).Description, "")'
    fx = ol.add_fx(OBJECTS, PICK, desc, FL_MSG)
    if after:
        fx = (f"Set({COUNT_BEFORE}, {ol.count_fx(OBJECTS)});\n" + fx
              + f";\nIf(\n    {ol.count_fx(OBJECTS)} > {COUNT_BEFORE},\n"
              + "\n".join("    " + l for l in after.split("\n")) + "\n)")
    return fx


def tab_body(height, min_len=None, after="", extra=()):
    """Objects-fanens krop: hjaelpelinjen, FL-soegningen, svaret og listen.

    min_len: mindste antal tegn for soegning og Add (Materials: 16).
    after: Power Fx efter Add og Remove. extra: appens linjer under listen."""
    n_min = min_len or fl.MIN_SEARCH_LEN
    ready = f'Len(Trim(Coalesce({PICK}, ""))) >= {n_min}'
    hint = text_ctrl(
        "txtDomObjHint",
        f'If({EDIT}, "Search with at least {n_min} characters, pick a result and '
        'press Add. The functional locations are saved with the row when you choose Save.", '
        '"Read only - the row or the request cannot be changed.")',
        size=12, color=C_MUTED, height=if_below("Tablet", "54", "36"), wrap="true")
    # Soegningen er FL-vaelgerens egen (tools/fl_picker.py) - den samme som
    # i resten af appen.
    picker = fl_picker(
        "Dom", combo=dp.FL_COMBO, results="colDomFl", raw_var="varDomFlRaw",
        msg_var=FL_MSG, busy_var=dp.FL_BUSY_VAR, query_var=dp.FL_QUERY_VAR,
        last_var=dp.FL_LAST_VAR, pick_var=PICK,
        default_items=f"Filter(colDomFl, Code = {PICK})",
        display_mode="DisplayMode.Edit", min_len=n_min,
        width="Parent.Width", stack_search=True)
    picker.vis = EDIT
    msg = dp.build_fl_msg()
    add = ol.add_button(
        "Dom", add_fx(after),
        display_mode=f"If({EDIT} && {ready}, DisplayMode.Edit, DisplayMode.Disabled)")
    add.vis = EDIT
    pnl = ol.panel(
        "Dom", OBJECTS, width="Parent.Width", msg_var=FL_MSG, add=add,
        display_mode=DM_EDIT, label="Functional locations", extra=extra,
        hint='"No functional locations on this row yet."',
        on_remove=after or None)
    body = capped_body("conDomObjTabBody", [hint, picker, msg, pnl], height)
    body.props["Height"] = height
    body.h = height
    return body
