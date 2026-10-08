# -*- coding: utf-8 -*-
"""
OBJEKTLISTEN paa en raekke - flere funktionspladser, een raekke.

Hvad den er
-----------
En raekke i en indmelding kan hoere til mere end een funktionsplads. VH-plan
har det samme begreb paa sine items (MaintenanceItems.ObjectList: koderne
adskilt af "; "), og delene her skriver PRAECIS det samme format, saa de to
lister kan laeses ens.

EEN RAEKKE, UANSET ANTAL OBJEKTER
---------------------------------
Objekterne er en EGENSKAB ved raekken - de skaber ingen nye raekker. Derfor
gemmes de paa raekken selv:

    ObjectList      koderne, sorteret og adskilt af "; "
    ObjectListJson  [{code, desc}] - saa BESKRIVELSERNE kan gendannes, naar
                    raekken aabnes, kopieres eller rettes igen
    <FL-kolonnen>   den FOERSTE kode. Soegning, indeks og alt, der laeser
                    feltet i dag, virker derfor uaendret

FORMULARENS LISTE ER EN SAMLING, IKKE EN NOEGLE PR. RAEKKE
----------------------------------------------------------
Samlingen holder objekterne for den raekke, formularen staar paa - uden
raekke-id. Et id ville ikke findes paa en NY raekke (det uddeles af
SharePoint ved Gem), og saa skulle objekterne noegles om bagefter. I stedet
fyldes samlingen, naar en raekke hentes eller kopieres, og ryddes, naar
formularen ryddes - som felterne ved siden af.

Modulet er DOMAENENEUTRALT: det kender hverken materialer, udstyr eller
maalesteder. Kalderen giver samlingens navn, kolonnenavnene og praefikset
til kontrollerne (issue #204; Measuring Point kan genbruge det uaendret).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gen_screen import (Ctrl, C_MUTED, C_TRANSPARENT, C_CARD_BORDER, C_TITLE)
import layout_tokens as lay
from build_helpers import (group, text_ctrl, button, grow, fit_button_width,
                           text_px, label_px)

# Adskilleren i ObjectList - den samme som MaintenanceItems bruger.
SEP = "; "
ROW_H = 32
MAX_ROWS = 5
REMOVE_W = 76
# Koden er saa bred som den laengste, der findes ("SSV13 HFC10AJ010" og
# lidt luft); beskrivelsen tager resten af raekken.
CODE_W = 170


def schema():
    """Samlingens skema til App.OnStart."""
    return {"Code": '""', "Description": '""'}


# ---------------------------------------------------------------------------
# Power Fx: tilfoej, fjern, gem, gendan
# ---------------------------------------------------------------------------
def count_fx(coll):
    return f"CountRows({coll})"


def sorted_fx(coll):
    return f"Sort({coll}, Code)"


def codes_fx(coll):
    """ObjectList: koderne sorteret og adskilt af "; "."""
    return f'Concat({sorted_fx(coll)}, Code, "{SEP}")'


def json_fx(coll):
    """ObjectListJson: [{code, desc}] - beskrivelserne, saa de kan gendannes."""
    return (f"JSON(ForAll({sorted_fx(coll)} As O, "
            "{ code: O.Code, desc: O.Description }), JSONFormat.Compact)")


def first_fx(coll):
    """Den foerste kode - den, FL-kolonnen paa raekken faar."""
    return f'Coalesce(First({sorted_fx(coll)}).Code, "")'


def add_fx(coll, code, desc, msg_var, *, max_rows=None):
    """Laeg det valgte resultat i listen.

    En kode, der allerede staar der, giver en besked og ingen dublet -
    sammenligningen er paa Upper(Trim(kode)), saa store og smaa bogstaver
    er den samme kode."""
    guard = (f'IsBlank(Trim(Coalesce({code}, "")))',
             '"Search for a functional location and select one first."')
    dup = (f'CountRows(Filter({coll}, Upper(Trim(Code)) = Upper(Trim({code})))) > 0',
           '"Already in the object list."')
    lines = (
        "If(\n"
        f"    {guard[0]},\n"
        f"    Set({msg_var}, {guard[1]}),\n"
        "\n"
        f"    {dup[0]},\n"
        f"    Set({msg_var}, {dup[1]}),\n"
        "\n"
        f"    Collect({coll}, {{ Code: Trim({code}), Description: Coalesce({desc}, \"\") }});\n"
        f'    Set({msg_var}, "Added " & Trim({code}) & " - " & Text({count_fx(coll)}) & '
        '" in the object list.")\n'
        ")"
    )
    if max_rows:
        lines = (
            "If(\n"
            f"    {count_fx(coll)} >= {max_rows},\n"
            f'    Set({msg_var}, "The object list is full ({max_rows} functional locations).")'
            ",\n"
            + "\n".join("    " + l for l in lines.split("\n")) + "\n"
            ")"
        )
    return lines


def remove_fx(coll, msg_var, code="ThisItem.Code"):
    return (f"RemoveIf({coll}, Code = {code});\n"
            f'Set({msg_var}, "Removed " & {code} & ".")')


def clear_fx(coll):
    return f"Clear({coll})"


def restore_fx(coll, *, json_src, list_src, fl_src):
    """Fyld samlingen fra raekken, som den er gemt.

    Tre veje, i den raekkefoelge: JSON'en (kode OG beskrivelse), den
    "; "-adskilte liste (kun koder - en raekke gemt foer JSON'en fandtes),
    og endelig FL-kolonnen alene (en raekke fra foer objektlisten)."""
    return (
        f"{clear_fx(coll)};\n"
        "If(\n"
        f'    !IsBlank(Trim(Coalesce({json_src}, ""))),\n'
        f"    Collect(\n        {coll},\n"
        f"        ForAll(Table(ParseJSON({json_src})) As R,\n"
        '            { Code: Text(R.Value.code), Description: Text(R.Value.desc) })\n'
        "    ),\n"
        "\n"
        f'    !IsBlank(Trim(Coalesce({list_src}, ""))),\n'
        f"    Collect(\n        {coll},\n"
        f'        ForAll(Filter(Split({list_src}, "{SEP.strip()}"), !IsBlank(Trim(Value))) As S,\n'
        '            { Code: Trim(S.Value), Description: "" })\n'
        "    ),\n"
        "\n"
        f'    !IsBlank(Trim(Coalesce({fl_src}, ""))),\n'
        f'    Collect({coll}, {{ Code: Trim({fl_src}), Description: "" }})\n'
        ")"
    )


def summary_fx(list_col, first_col, *, empty='"-"'):
    """Listens celle: den foerste kode og "+n" for resten - "SSV13
    HFC10AJ010 +2". Regnet af den GEMTE tekst, saa den virker for enhver
    raekke i tabellen."""
    n = (f'CountRows(Filter(Split(Coalesce({list_col}, ""), "{SEP.strip()}"), '
         "!IsBlank(Trim(Value))))")
    return (f'With(\n    {{ n: {n} }},\n'
            f'    If(\n        n = 0, Coalesce({first_col}, {empty}),\n'
            f'        Coalesce({first_col}, {empty}) & If(n > 1, " +" & Text(n - 1), "")\n'
            "    )\n)")


# ---------------------------------------------------------------------------
# Kontrollerne: listen med kode, beskrivelse og Remove
# ---------------------------------------------------------------------------
def panel(prefix, coll, *, width, display_mode, msg_var, add=None,
          label="Object list",
          hint='"Search for a functional location and press Add."'):
    """Objektlisten som den ses i formularen: en overskrift med antallet,
    en raekke pr. objekt (kode, beskrivelse, Remove) og en linje, naar den
    er tom.

    EET GALLERI, ikke en kontrol pr. objekt: antallet er brugerens, og en
    formular kan ikke have et ukendt antal kontroller."""
    title = text_ctrl(f"txt{prefix}ObjHead",
                      f'"{label} (" & Text({count_fx(coll)}) & ")"',
                      size=13, weight="Semibold", height=20, wrap="false",
                      width=label_px(label + " (00)", 13) + 4)
    # ADD STAAR HER, IKKE VED SEARCH
    #
    # Knappen hoerer til listen, den skriver i - og i FL-cellen, der er en
    # fjerdedel af kortet bred, var der ikke plads til baade comboboks,
    # Search og Add paa samme linje (check_layout regel 4d). Her er der
    # hele kortets bredde.
    kids = [grow(title)] + ([add] if add else [])
    head = group(f"con{prefix}ObjHead", kids, direction="Horizontal", gap=8,
                 height=36, align_items="Center")
    empty = text_ctrl(f"txt{prefix}ObjEmpty", hint, size=12, color=C_MUTED,
                      height=18, wrap="false",
                      visible=f"{count_fx(coll)} = 0")
    code = text_ctrl(f"txt{prefix}ObjCode", "ThisItem.Code", size=13,
                     weight="Semibold", height=20, wrap="false",
                     width=CODE_W)
    desc = grow(text_ctrl(f"txt{prefix}ObjDesc",
                          'Coalesce(ThisItem.Description, "")', size=12,
                          color=C_MUTED, height=20, wrap="false"))
    rem = button(f"btn{prefix}ObjRemove", '"Remove"', remove_fx(coll, msg_var),
                 width=REMOVE_W, height=ROW_H - 2, display_mode=display_mode,
                 accessible='"Remove " & ThisItem.Code',
                 tooltip='"Remove " & ThisItem.Code')
    rem.props["Size"] = "12"
    rem.props["LayoutMinWidth"] = str(REMOVE_W)
    row = group(f"con{prefix}ObjRow", [code, desc, rem], direction="Horizontal",
                gap=8, height=ROW_H - 2, align_items="Center",
                width="Parent.TemplateWidth")
    gal_h = f"Max(Min({count_fx(coll)}, {MAX_ROWS}), 1) * {ROW_H}"
    gal = Ctrl(f"gal{prefix}Objects", "Gallery", variant="Vertical", props={
        "AccessibleLabel": '"Functional locations on this row"',
        "BorderStyle": "BorderStyle.None",
        "Fill": C_TRANSPARENT,
        "FillPortions": "0",
        "Height": gal_h,
        "Items": sorted_fx(coll),
        "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None",
        "Selectable": "false",
        "ShowScrollbar": "true",
        "TabIndex": "0",
        "TemplatePadding": "1",
        "TemplateSize": str(ROW_H),
        "Width": "Parent.Width",
        "WrapCount": "1",
        "Visible": f"{count_fx(coll)} > 0",
    }, children=[row], h=gal_h, vis=f"{count_fx(coll)} > 0")
    box = group(f"con{prefix}Objects", [head, empty, gal], direction="Vertical",
                gap=4, width=width, align_items="Stretch")
    return box


def add_button(prefix, fx, *, display_mode, height=36):
    """Add - knappen ved siden af Search. Den laegger DET VALGTE resultat i
    listen; selve soegningen er FL-vaelgerens egen (tools/fl_picker.py)."""
    b = button(f"btn{prefix}ObjAdd", '"Add"', fx,
               width=fit_button_width('"Add"'), height=height,
               display_mode=display_mode,
               accessible='"Add the selected functional location to the object list"',
               tooltip='"Add the selected functional location to the object list"')
    b.props["LayoutMinWidth"] = b.props["Width"]
    return b
