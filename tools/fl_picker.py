# -*- coding: utf-8 -*-
"""
Functional Location-vaelgeren - EEN ModernCombobox til soegning OG valg.

Den samme kontrol i VH-plan, Equipments og Materials (issue #63, #68).
Flow-kontrakten staar stadig i build_flsearch.py; her staar kun,
hvordan brugeren soeger og vaelger.

    [ SSV13 HFC|                    v ][ Search ]
    [ SSV13 HFC|                    v ][   ◌    ]   mens flowet koerer

HVAD BRUGEREN GOER
------------------
1. Skriver mindst MIN_SEARCH_LEN tegn i comboboksen. Foer det er Search
   deaktiveret.
2. Trykker Search - eller Enter (se nedenfor). Flowet kaldes EEN gang, og
   svaret fylder resultatsamlingen, som comboboksen viser.
3. Skriver videre for at snaevre ind. Det er comboboksens EGEN lokale
   filtrering - intet nyt kald til flowet eller SAP.
4. Vaelger een raekke (SelectMultiple = false).

ENTER SOEGER - HVORDAN
----------------------
ModernCombobox har ingen OnSelect- eller Enter-haendelse, kun OnChange,
som kommer, naar en raekke VAELGES (Learn, "Combo box modern control":
OnChange "fires immediately on every selection or deselection"). Og Enter
i en combobox betyder netop: vaelg den fremhaevede raekke.

Derfor staar der en SOEGERAEKKE i listen, saa snart der er skrevet nok:

    SSV13 HFC10  -  press Enter to search SAP

Dens Display STARTER med soegeteksten, saa comboboksens eget filter altid
lader den staa. Enter vaelger den, og OnChange genkender den paa sin kode
(SEARCH_CODE) og koerer soegningen i stedet for at gemme et valg. Den
ligger OEVERST, naar teksten er en ny soegning - og NEDERST, naar
brugeren blot snaevrer det sidste svar ind (teksten starter med den
sidste soegning), saa Enter dér vaelger det foerste rigtige resultat.
Mens flowet koerer, er den vaek - saa to Enter ikke giver to kald.

Raekken kan ikke gemmes: dens kode er SEARCH_CODE, og OnChange nulstiller
comboboksen, naar den er valgt.

SOEGETEKSTEN GEMMES, MENS DER SKRIVES
-------------------------------------
Search-knappen laeser SearchText. Trykker man paa knappen, mister
comboboksen fokus, og en Fluent-combobox kan rydde sin tekst i samme
oejeblik - saa ville knappen blive deaktiveret midt i klikket. En timer
laegger derfor teksten i query_var, saa laenge der staar noget.

SPINNEREN I KNAPPEN
-------------------
Mens flowet koerer, er knappen skiftet ud med en boks af PRAECIS samme
stoerrelse og form med een centreret ModernSpinner. De to staar paa samme
plads i raekken, og kun den ene er synlig ad gangen - saa intet i raekken
flytter sig, og der er hverken prikker eller en fuldskaerms-spinner.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gen_screen import Ctrl, C_CARD_BORDER, C_DISABLED_BG, FONT
from build_helpers import (button, group, grow, border_rule, input_fill,
                           fit_button_width)
import build_flsearch as fl

# Soegeraekkens kode. Ingen rigtig Functional Location starter med "?".
SEARCH_CODE = "?search"
SEARCH_HINT = "  -  press Enter to search SAP"
PLACEHOLDER = f'"At least {fl.MIN_SEARCH_LEN} characters, e.g. SSV13 HFC"'
SEARCH_W = fit_button_width('"Search"')
HEIGHT = 36


def _timer(name, start, duration, on_end):
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


def items_fx(results, busy_var, last_var):
    """Comboboksens Items: resultaterne - plus soegeraekken, naar der er
    skrevet nok til en ny soegning.

    Ungroup, fordi Table() ikke blander en record og en tabel. Kolonnenavnet
    er et NAVN, ikke en streng (check_layout regel 31)."""
    return (
        "With(\n"
        "    { q: Trim(Self.SearchText) },\n"
        "    With(\n"
        "        {\n"
        f"            s: Table({{ Code: \"{SEARCH_CODE}\", Description: q,\n"
        f"                       Display: q & \"{SEARCH_HINT}\",\n"
        "                       Maintainable: true, Level: \"\" }),\n"
        f"            ask: Len(q) >= {fl.MIN_SEARCH_LEN} && !{busy_var} &&\n"
        f"                 Upper(q) <> Upper(Coalesce({last_var}, \"\")),\n"
        f"            narrow: CountRows({results}) > 0 && !IsBlank({last_var}) &&\n"
        f"                    StartsWith(Upper(q), Upper({last_var}))\n"
        "        },\n"
        "        If(\n"
        f"            !ask, {results},\n"
        f"            narrow, Ungroup(Table({{ Rows: {results} }}, {{ Rows: s }}), Rows),\n"
        f"            Ungroup(Table({{ Rows: s }}, {{ Rows: {results} }}), Rows)\n"
        "        )\n"
        "    )\n"
        ")"
    )


def fl_picker(prefix, *, combo, results, raw_var, msg_var, busy_var, query_var,
              last_var, default_items, display_mode, on_select=None, on_clear=None,
              required_formula="false", width="Parent.Width",
              label="Functional location"):
    """Raekken [combobox][Search] og dens timer - som EEN container.

    prefix     navnepraefikset (Vhp, Dom) - knap, boks og timer faar det
    combo      comboboksens navn
    results    samlingen, flowets svar lander i
    default_items  DefaultSelectedItems - det gemte valg som tabel
    on_select  hvad et valg goer (fx Set(var, Self.Selected.Code));
               Self.Selected er aldrig soegeraekken her. Udelades, naar
               appen laeser valget direkte af comboboksen (VH-plan)
    on_clear   ryd det gemte valg - koeres, naar en ny soegning starter
    """
    query = f"Coalesce({combo}.SearchText, {query_var})"

    def search(q_expr):
        return fl.search_action(combo, results, msg_var, raw_var=raw_var,
                                busy_var=busy_var, query_expr=q_expr,
                                last_var=last_var, on_start=on_clear)

    cmb = Ctrl(combo, "ModernCombobox", props={
        "AccessibleLabel": (f'"{label} - type at least {fl.MIN_SEARCH_LEN} '
                            f'characters, then Search or Enter"'),
        "Appearance": "Appearance.Outline",
        "BorderColor": border_rule(
            f'(IsBlank(Self.Selected.Code) || Self.Selected.Code = "{SEARCH_CODE}")',
            required_formula),
        "BorderStyle": "BorderStyle.Solid",
        "BorderThickness": "1",
        "DefaultSelectedItems": default_items,
        "DelayOutput": "false",
        "DisplayMode": display_mode,
        "Fill": input_fill(display_mode),
        "Font": FONT,
        "Height": str(HEIGHT),
        "InputTextPlaceholder": PLACEHOLDER,
        "IsSearchable": "true",
        "ItemDisplayText": "ThisItem.Display",
        "Items": items_fx(results, busy_var, last_var),
        "LayoutMinWidth": "0",
        "OnChange": (
            "If(\n"
            f"    Self.Selected.Code = \"{SEARCH_CODE}\",\n"
            f"    Set({query_var}, Self.Selected.Description);\n"
            f"    {search(query_var)};\n"
            f"    Reset({combo})"
            + (f",\n    {on_select}" if on_select else "") + "\n"
            ")"
        ),
        "SelectMultiple": "false",
        "Size": "14",
        "Width": "0",
    }, h=HEIGHT)
    grow(cmb)

    too_short = f"Len(Trim({query})) < {fl.MIN_SEARCH_LEN}"
    btn = button(f"btn{prefix}FlSearch", '"Search"', search(query),
                 width=SEARCH_W, height=HEIGHT,
                 display_mode=(f"If({too_short}, DisplayMode.Disabled, "
                               f"{display_mode})"),
                 accessible='"Search functional location"',
                 visible=f"!{busy_var}")
    btn.props["LayoutMinWidth"] = str(SEARCH_W)

    # Knappen, mens flowet koerer: samme stoerrelse og form, een spinner
    # midt i. AccessibleLabel paa spinneren - boksen er ikke interaktiv.
    spin = Ctrl(f"spn{prefix}FlSearch", "ModernSpinner", props={
        "AccessibleLabel": '"Searching functional locations"',
        "Height": "24",
        "Label": '""',
        "Width": "24",
    }, h=24)
    busy = group(f"con{prefix}FlSearchBusy", [spin], direction="Horizontal",
                 gap=0, height=HEIGHT, width=SEARCH_W, align_items="Center",
                 justify="Center", fill=C_DISABLED_BG, border_color=C_CARD_BORDER,
                 radius=10, visible=busy_var)
    busy.props["LayoutMinWidth"] = str(SEARCH_W)

    row = group(f"con{prefix}FlInput", [cmb, btn, busy], direction="Horizontal",
                gap=8, height=HEIGHT, align_items="Center", width=width)
    capture = _timer(
        f"tmr{prefix}FlCapture", f"!IsBlank({combo}.SearchText)", 300,
        f"If(!IsBlank({combo}.SearchText), Set({query_var}, {combo}.SearchText))")
    return group(f"con{prefix}FlWrap", [row, capture], direction="Vertical", gap=0,
                 width=width)


def known_fx(results, src, desc='""'):
    """Laeg et gemt valg i resultatsamlingen, hvis det ikke er der - saa
    comboboksen kan vise det, ogsaa uden at der er soegt paa det."""
    return (f"If(\n"
            f"    !IsBlank({src}) && IsBlank(LookUp({results}, Code = {src})),\n"
            f"    Collect({results}, {{ Code: {src}, Description: {desc}, "
            f"Display: {src} & If(IsBlank({desc}), \"\", \" - \" & {desc}),"
            f" Maintainable: true, Level: \"\" }})\n"
            f");")
