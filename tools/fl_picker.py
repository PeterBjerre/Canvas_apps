# -*- coding: utf-8 -*-
"""
Functional Location-vaelgeren - EEN ModernCombobox til soegning OG valg.

Den samme kontrol i VH-plan, Equipments og Materials (issue #63, #68).
Flow-kontrakten staar stadig i build_flsearch.py; her staar kun,
hvordan brugeren soeger og vaelger.

    [ SSV13 HFC|                    v ][ Search ]
    [ SSV13 HFC|                    v ][   ◌    ]   mens flowet koerer

HVAD BRUGEREN GOER (issue #72)
------------------------------
1. Skriver mindst MIN_SEARCH_LEN tegn i comboboksen. Foer det er Search
   deaktiveret. Listen er TOM - der staar hverken hjaelpetekst, en
   pladsholder eller en kunstig "tryk Enter"-raekke i den. Comboboksen
   har intet at aabne, foer flowet har svaret.
2. Trykker Search. Flowet kaldes EEN gang, og svaret fylder
   resultatsamlingen, som comboboksen viser.
3. Det FOERSTE resultat vaelges automatisk og staar i feltet i stedet for
   pladsholderen (pick_var + Reset: DefaultSelectedItems laeses igen).
4. Brugeren kan skrive videre for at snaevre ind - comboboksens EGEN
   lokale filtrering, intet nyt kald - og vaelge en anden raekke.

Valget bliver staaende, naar brugeren klikker et andet sted. Det ryddes
kun af en ny soegning, en lokal nulstilling (reset_fx) eller et nyt valg.

Beskeder ("6 Functional Locations found for ...", "Searching ...", ingen
traef, fejl) staar UNDER feltet (msg_var) - aldrig i listen.

HVORFOR ENTER IKKE LAENGERE SOEGER
----------------------------------
ModernCombobox har ingen Enter-haendelse, kun OnChange, naar en raekke
VAELGES. Den eneste vej til "Enter soeger" var en kunstig raekke i listen
- og det er netop den, issue #72 fjerner: listen maa kun indeholde rigtige
Functional Locations. Search-knappen er vejen.

SOEGETEKSTEN GEMMES, MENS DER SKRIVES
-------------------------------------
Search-knappen laeser SearchText. Trykker man paa knappen, mister
comboboksen fokus, og en Fluent-combobox kan rydde sin tekst i samme
oejeblik - saa ville knappen blive deaktiveret midt i klikket. En timer
laegger derfor teksten i query_var, saa laenge der staar noget.

KNAPPEN MENS FLOWET KOERER
--------------------------
Knappen staar STILLE: samme bredde, hoejde og plads i alle tilstande. Mens
flowet koerer, er den deaktiveret og uden tekst, og EEN ModernSpinner
drejer i en fast plads lige til hoejre for den. Pladsen er der altid, saa
intet i raekken flytter sig, naar spinneren kommer og gaar. Ingen prikker,
ingen fuldskaerms-spinner, ingen spinner inde i knappen.

RAEKKEN KLIPPER IKKE
--------------------
Raekken har 2 px luft over og under (ROW_PAD). Uden den var raekken
PRAECIS lige saa hoej som knappen, og knappens fokusring og trykkede
tilstand blev klippet af containerens LayoutOverflow.Hide - knappen saa ud
til at vokse og blive skaaret af forneden, naar den blev aktiv.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gen_screen import Ctrl
from build_helpers import (button, group, grow, border_rule, input_theme,
                           fit_button_width)
import build_flsearch as fl

PLACEHOLDER = f'"At least {fl.MIN_SEARCH_LEN} characters, e.g. SSV13 HFC"'
SEARCH_W = fit_button_width('"Search"')
HEIGHT = 36
# Luft over og under raekken, saa knappens fokusring ikke klippes.
ROW_PAD = 2
# Spinnerens faste plads til hoejre for knappen.
SPIN = 20


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


def reset_fx(*, combo, results, msg_var, query_var, last_var, pick_var=None,
             extra=None):
    """Nulstil EEN vaelger - og kun den (issue #72).

    Soegetekst, valgt resultat, resultaterne og beskeden ryddes, og
    comboboksen faar sin pladsholder tilbage. Alle navne er vaelgerens
    egne, saa en Reset i een formular aldrig roerer en anden formulars
    comboboks. extra: vaelgerens egne afhaengigheder (fx Object List)."""
    parts = [f'Set({query_var}, "")', f'Set({last_var}, "")',
             f'Set({msg_var}, "")', f"Clear({results})"]
    if pick_var:
        parts.append(f'Set({pick_var}, "")')
    if extra:
        parts.append(extra)
    parts.append(f"Reset({combo})")
    return "; ".join(parts)


def fl_picker(prefix, *, combo, results, raw_var, msg_var, busy_var, query_var,
              last_var, pick_var, default_items, display_mode, on_select=None,
              on_clear=None, required_formula="false", width="Parent.Width",
              label="Functional location"):
    """Raekken [combobox][Search][spinner] og dens timer - som EEN container.

    prefix     navnepraefikset (Vhp, Dom) - knap, spinner og timer faar det
    combo      comboboksens navn
    results    samlingen, flowets svar lander i - og det ENESTE, listen viser
    pick_var   det valgte resultats kode. Soegningen saetter den til det
               foerste resultat; default_items skal laese den
    default_items  DefaultSelectedItems - det gemte valg som tabel
    on_select  hvad et valg goer ud over at saette pick_var
    on_clear   ryd det gemte valg - koeres, naar en ny soegning starter
    """
    query = f"Coalesce({combo}.SearchText, {query_var})"
    search = fl.search_action(
        combo, results, msg_var, raw_var=raw_var, busy_var=busy_var,
        query_expr=query, last_var=last_var,
        # Det gamle valg er vaek, i samme oejeblik en ny soegning starter -
        # ogsaa hvis den ikke finder noget.
        on_start=f'Set({pick_var}, ""); Reset({combo})' + (f"; {on_clear}" if on_clear else ""),
        on_found=(f"Set({pick_var}, First({results}).Code);\n"
                  f"                    Reset({combo})"))

    select = f'Set({pick_var}, Coalesce(Self.Selected.Code, ""))'
    if on_select:
        select += f";\n{on_select}"

    # Farver, udseende og laast-tilstand er DE SAMME som alle andre felters
    # (build_helpers.input_theme, issue #78). Comboboksen var Outline -
    # "transparent background" - og deaktiveret tegnede Fluent den sort med
    # graa tekst i moerk tilstand.
    cmb = Ctrl(combo, "ModernCombobox", props=input_theme({
        "AccessibleLabel": (f'"{label} - type at least {fl.MIN_SEARCH_LEN} '
                            f'characters, then Search"'),
        "BorderColor": border_rule("IsBlank(Self.Selected.Code)", required_formula),
        "BorderStyle": "BorderStyle.Solid",
        "BorderThickness": "1",
        "DefaultSelectedItems": default_items,
        "DelayOutput": "false",
        "Height": str(HEIGHT),
        "InputTextPlaceholder": PLACEHOLDER,
        "IsSearchable": "true",
        "ItemDisplayText": "ThisItem.Display",
        # KUN rigtige resultater - ingen soegeraekke, ingen hjaelpetekst.
        "Items": results,
        "LayoutMinWidth": "0",
        "OnChange": select,
        # Samme hjoerner som alle andre felter (text_input, dropdown ...).
        "RadiusBottomLeft": "10", "RadiusBottomRight": "10",
        "RadiusTopLeft": "10", "RadiusTopRight": "10",
        "SelectMultiple": "false",
        "ValidationState": (f"If({required_formula} && IsBlank(Self.Selected.Code), "
                            "ValidationState.Error, ValidationState.None)"),
        "Width": "0",
    }, display_mode), h=HEIGHT)
    grow(cmb)

    too_short = f"Len(Trim({query})) < {fl.MIN_SEARCH_LEN}"
    btn = button(f"btn{prefix}FlSearch", f'If({busy_var}, "", "Search")', search,
                 width=SEARCH_W, height=HEIGHT,
                 display_mode=(f"If({busy_var} || {too_short}, DisplayMode.Disabled, "
                               f"{display_mode})"),
                 accessible=f'If({busy_var}, "Searching functional locations", '
                            '"Search functional location")')
    btn.props["LayoutMinWidth"] = str(SEARCH_W)

    # Spinnerens plads staar der altid; kun spinneren kommer og gaar.
    spin = Ctrl(f"spn{prefix}FlSearch", "ModernSpinner", props={
        "AccessibleLabel": '"Searching functional locations"',
        "Height": str(SPIN),
        "Label": '""',
        "Visible": busy_var,
        "Width": str(SPIN),
    }, h=SPIN, vis=busy_var)
    slot = group(f"con{prefix}FlSearchBusy", [spin], direction="Horizontal",
                 gap=0, height=HEIGHT, width=SPIN, align_items="Center",
                 justify="Center")
    slot.props["LayoutMinWidth"] = str(SPIN)

    row = group(f"con{prefix}FlInput", [cmb, btn, slot], direction="Horizontal",
                gap=8, height=HEIGHT + 2 * ROW_PAD, pad=(ROW_PAD, 0, ROW_PAD, 0),
                align_items="Center", width=width)
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
