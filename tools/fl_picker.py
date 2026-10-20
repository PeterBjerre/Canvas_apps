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
flowet koerer, er den skjult, og EEN ModernSpinner med "Searching..."
drejer i dens faste plads (issue #302). Pladsen er der altid, saa
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

from gen_screen import Ctrl, C_CARD_BORDER, C_DISABLED_BG, C_MUTED
import layout_tokens as lay
from build_helpers import (button, group, grow, border_rule, input_theme,
                           fit_button_width, spinner)
import build_flsearch as fl

PLACEHOLDER = f'"At least {fl.MIN_SEARCH_LEN} characters, e.g. SSV13 HFC"'
SEARCH_W = fit_button_width('"Search"', min_w=0) - 12
HEIGHT = 36
# Luft over og under raekken, saa knappens fokusring ikke klippes.
ROW_PAD = 2
# Plads til hjulet ved siden af "Searching..." (Spinnerens eget hjul).
SPIN = 20
# Knappen og den optagede knap har SAMME bredde, saa intet flytter sig.
BUSY_W = fit_button_width('"Searching..."') + SPIN + 8
# Search keeps the Searching... width, so nothing shifts when a search starts.
SEARCH_W = BUSY_W

# Soegeraekken i listen: Enter i en combobox vaelger den fremhaevede raekke, og
# ModernCombobox har ingen Enter-haendelse. Ingen rigtig Functional Location
# starter med "?".
SEARCH_CODE = "?search"
SEARCH_HINT = "  -  press Enter to search"


def items_fx(results, busy_var, last_var, min_len=None, block=None, query_map=None):
    """Comboboksens Items: resultaterne - plus en soegeraekke, naar der er
    skrevet nok til en ny soegning.

    Raekken ligger oeverst, naar teksten er en ny soegning, og nederst, naar
    brugeren blot snaevrer det sidste svar ind, saa Enter der vaelger det
    foerste rigtige resultat. Mens soegningen koerer, er den vaek.
    ForAll over Sequence i stedet for Ungroup: Ungroup(Table({..},{..}), ..)
    gav kun en raekke pr. post i Power Apps.
    block: se fl_picker - er den sand for teksten, vises soegeraekken ikke.
    query_map: se fl_picker - soegeraekken baerer den udfyldte tekst."""
    no_block = f" && !({block('q')})" if block else ""
    q0 = query_map("Self.SearchText") if query_map else "Trim(Self.SearchText)"
    return (
        "With(\n"
        f"    {{ q: {q0} }},\n"
        "    With(\n"
        "        {\n"
        f"            s: {{ Code: \"{SEARCH_CODE}\", Description: q,\n"
        f"                  Display: q & \"{SEARCH_HINT}\",\n"
        "                  Maintainable: true, Level: \"\" },\n"
        f"            n: CountRows({results}),\n"
        f"            ask: Len(q) >= {min_len or fl.MIN_SEARCH_LEN} && !{busy_var} &&\n"
        f"                 Upper(q) <> Upper(Coalesce({last_var}, \"\")){no_block} &&\n"
        # Teksten i feltet er et resultats Display - typisk det valgte, som
        # feltet viser (issue #455). Det er ikke en ny soegning. Ellers stod soegeraekken
        # oeverst, saa snart et gemt valg fik fokus, og Enter eller et
        # klik ud kunne vaelge den - en ny soegning paa "KODE - tekst",
        # der ryddede den gemte Functional Location og objekterne.
        f"                 IsBlank(LookUp({results}, Upper(Trim(Display)) = Upper(q)).Code),\n"
        f"            narrow: CountRows({results}) > 0 && !IsBlank({last_var}) &&\n"
        f"                    StartsWith(Upper(q), Upper({last_var}))\n"
        "        },\n"
        "        If(\n"
        f"            !ask, {results},\n"
        "            ForAll(\n"
        "                Sequence(n + 1),\n"
        f"                If(narrow, If(Value <= n, Index({results}, Value), s),\n"
        f"                    If(Value = 1, s, Index({results}, Value - 1)))\n"
        "            )\n"
        "        )\n"
        "    )\n"
        ")"
    )


def busy_box(name, visible, label="Searching..."):
    """Knappens afloeser mens soegningen koerer: den moderne Spinner med
    teksten til hoejre (issue #302), i knappens faste plads (BUSY_W x
    HEIGHT), saa intet i raekken flytter sig.

    Foer var det EET billede med en knapformet boks, et drejende SVG-hjul
    og teksten, fordi en tidlig ModernSpinner (20 x 20, uden tekst) i en
    container ikke blev tegnet i Studio. Nu er hjul og tekst EN kontrol med
    plads til begge; boksen er vaek - Spinneren har ingen fyld eller kant.
    Teksten staar stadig som en streng for sig selv, saa den kan
    oversaettes."""
    spin = spinner(name, visible, '"Searching"', width=BUSY_W, height=HEIGHT,
                   label=f'"{label}"', size=lay.SIZE_INPUT, weight="Semibold")
    spin.props["LayoutMinWidth"] = str(BUSY_W)
    return spin


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
    comboboks. extra: vaelgerens egne afhaengigheder (fx Object list)."""
    parts = [f'Set({query_var}, "")', f'Set({last_var}, "")',
             f'Set({msg_var}, "")', f"Clear({results})"]
    if pick_var:
        parts.append(f'Set({pick_var}, "")')
    if extra:
        parts.append(extra)
    parts.append(f"Reset({combo})")
    return "; ".join(parts)


def result_count_fx(*, combo, results, busy_var, last_var):
    """Antal resultater i den AKTUELLE soegning - til en valgfri knap ved
    soegningen, fx "Object list (6)" (issue #454).

    Tallet laeses af SAMME samling som beskeden under feltet
    ("6 Functional Locations found for ..." - build_flsearch.search_action
    taeller CountRows(results)), saa de to aldrig er uenige. Det er 0:
      - foer der er soegt, og naar vaelgeren er nulstillet eller ryddet
        (last_var er tom, samlingen er tom - reset_fx, x-knappen),
      - mens en ny soegning koerer (busy_var; samlingen er ogsaa ryddet),
      - naar soegeteksten er aendret, siden der sidst blev soegt.
    Tom SearchText (et valgt resultat i feltet) er ikke en aendring.
    Ingen ny variabel og intet kald - kun vaelgerens egen tilstand, saa
    ALLE FL-soegninger med en Object list-knap kan bruge den."""
    typed = f"Upper(Trim({combo}.SearchText))"
    return (f"If({busy_var} || IsBlank({last_var}) || "
            f"(!IsBlank({typed}) && {typed} <> Upper(Trim({last_var}))), "
            f"0, CountRows({results}))")


# Pladsholderen, mens vaelgeren er laast af lock (issue #101).
LOCKED_PLACEHOLDER = '"Not used - No BOM Item is on"'


def _lock_combo(cmb, lock):
    """Laast af lock = UTILGAENGELIG, ikke skrivebeskyttet (issue #101).

    input_theme goer et laast felt til View: "renders as read-only rather
    than looking disabled". Det er rigtigt for et felt, man ikke maa
    aendre - men No BOM Item betyder, at feltet slet ikke er i brug, og i
    View saa comboboksen ud som et almindeligt, tomt felt. Derfor
    Disabled, mens lock er sand: ingen fokus, ingen soegning, intet valg,
    og Fluent graaner selv pilen. Fyld, kant og tekst saettes eksplicit
    til de graa tokens (udfyldt, saa Fill tegnes), og kanten er aldrig
    roed. Slaas lock fra, gaelder feltets egne regler igen uaendret."""
    p = cmb.props
    dm = p.get("DisplayMode") or "DisplayMode.Edit"
    p["DisplayMode"] = f"If({lock}, DisplayMode.Disabled, {dm})"
    p["Appearance"] = f"If({lock}, Appearance.FilledDarker, {p['Appearance']})"
    p["Fill"] = f"If({lock}, {C_DISABLED_BG}, {p['Fill']})"
    p["Color"] = f"If({lock}, {C_MUTED}, {p['Color']})"
    p["BorderColor"] = f"If({lock}, {C_CARD_BORDER}, {p['BorderColor']})"
    p["InputTextPlaceholder"] = (f"If({lock}, {LOCKED_PLACEHOLDER}, "
                                 f"{p['InputTextPlaceholder']})")


def fl_picker(prefix, *, combo, results, raw_var, msg_var, busy_var, query_var,
              last_var, pick_var, default_items, display_mode, on_select=None,
              on_clear=None, required_formula="false", width="Parent.Width",
              label="Functional location", trail=(), stack_search=False, col_w=None, stack_cond=None,
              lock=None, min_len=None, kind="Fl", searcher=None, placeholder=None,
              search_accessible='"Search functional location"', block=None, on_found=None,
              query_map=None):
    """Raekken [combobox][Search][spinner] og dens timer - som EEN container.

    prefix     navnepraefikset (Vhp, Dom) - knap, spinner og timer faar det
    combo      comboboksens navn
    results    samlingen, flowets svar lander i - og det ENESTE, listen viser
    pick_var   det valgte resultats kode. Soegningen saetter den til det
               foerste resultat; default_items skal laese den
    default_items  DefaultSelectedItems - det gemte valg som tabel
    on_select  hvad et valg goer ud over at saette pick_var
    on_clear   ryd det gemte valg - koeres, naar en ny soegning starter
    on_found   hvad det automatiske valg af foerste resultat goer ud over at
               saette pick_var (koden staar i pick_var) - fx skrive koden paa
               raekken, saa den ikke kun staar i comboboksen (issue #448)
    lock       udtryk, der goer vaelgeren utilgaengelig, mens det er sandt
               (Materials' No BOM Item, issue #101) - se _lock_combo
    min_len    mindste antal tegn (trimmet) foer der kan soeges - baade med
               Search og med soegeraekken (Enter). Standard er
               build_flsearch.MIN_SEARCH_LEN; kun VH-planens Item Editor
               saetter sin egen (8, issue #144)
    kind       navnets midterled (btn<prefix><kind>Search ...). "Fl" for
               FL-vaelgerne; leverandoervaelgeren bruger "Ven"
    searcher   soegningen - samme signatur som build_flsearch.search_action.
               Standard er FL-flowet; tools/vendor_search.py giver sin egen
    placeholder  comboboksens pladsholder; standard er FL-eksemplet
    query_map  q -> udtryk: soegeteksten, som den soeges paa (fx med VH-
               planens vaerk foran, issue #453). Bruges af Search, Enter-
               raekken, block og laengdetjekket. Standard: teksten, som den er
    block      (cond, msg): cond(q) giver et udtryk, der er sandt, naar
               soegeteksten q (trimmet) IKKE maa soeges paa - fx en FL fra et
               andet vaerk end VH-planens. Search er da deaktiveret, Enter-
               raekken vises ikke, og en soegning, der alligevel startes,
               stoppes med Notify(msg). Beskeden under feltet er kalderens.
    """
    n_min = min_len or fl.MIN_SEARCH_LEN
    query = f"Coalesce({combo}.SearchText, {query_var})"
    enter_query = query_var
    if query_map:
        query = query_map(query)
        enter_query = query_map(query_var)
    searcher = searcher or fl.search_action
    search = searcher(
        combo, results, msg_var, raw_var=raw_var, busy_var=busy_var,
        query_expr=query, last_var=last_var, min_len=n_min,
        # Det gamle valg er vaek, i samme oejeblik en ny soegning starter -
        # ogsaa hvis den ikke finder noget.
        on_start=f'Set({pick_var}, ""); Reset({combo})' + (f"; {on_clear}" if on_clear else ""),
        on_found=(f"Set({pick_var}, First({results}).Code);\n"
                  f"                    Reset({combo})"
                  + (f";\n                    {on_found}" if on_found else "")))

    block_cond = None
    if block:
        block_cond, block_msg = block

        def guard(q_src, action):
            # Soegningen starter slet ikke - intet flowkald, intet ryddes.
            return (f"If(\n    {block_cond(f'Trim({q_src})')},\n"
                    f"    Notify({block_msg}, NotificationType.Warning),\n"
                    f"    {action}\n)")
        search = guard(query, search)

    select = f'Set({pick_var}, Coalesce(Self.Selected.Code, ""))'
    if on_select:
        select += f";\n{on_select}"
    # The clear (x) button: drop the old search, its list and the dependants.
    cleared = (f'Set({pick_var}, ""); Clear({results}); Set({last_var}, ""); '
               f'Set({query_var}, ""); Set({msg_var}, "")'
               + (f"; {on_clear}" if on_clear else ""))
    select = (f"If(\n    IsBlank(Self.Selected.Code) && !{busy_var},\n    {cleared},\n"
              f"    {select}\n)")
    # Enter vaelger soegeraekken; OnChange koerer da soegningen paa den tekst,
    # raekken bar, i stedet for at gemme et valg.
    search_enter = searcher(
        combo, results, msg_var, raw_var=raw_var, busy_var=busy_var,
        query_expr=enter_query, last_var=last_var, min_len=n_min,
        on_start=f'Set({pick_var}, ""); Reset({combo})' + (f"; {on_clear}" if on_clear else ""),
        on_found=(f"Set({pick_var}, First({results}).Code);\n"
                  f"                    Reset({combo})"
                  + (f";\n                    {on_found}" if on_found else "")))
    if block:
        search_enter = guard(enter_query, search_enter)
    on_change = (
        "If(\n"
        f"    Self.Selected.Code = \"{SEARCH_CODE}\",\n"
        f"    Set({query_var}, Self.Selected.Description);\n"
        f"    {search_enter};\n"
        f"    Reset({combo}),\n"
        f"    {select}\n"
        ")"
    )

    # Farver, udseende og laast-tilstand er DE SAMME som alle andre felters
    # (build_helpers.input_theme, issue #78). Comboboksen var Outline -
    # "transparent background" - og deaktiveret tegnede Fluent den sort med
    # graa tekst i moerk tilstand.
    cmb = Ctrl(combo, "ModernCombobox", props=input_theme({
        "AccessibleLabel": (f'"{label} - type at least {n_min} '
                            f'characters, then Search or Enter"'),
        "BorderColor": border_rule(
            f'(IsBlank(Self.Selected.Code) || Self.Selected.Code = "{SEARCH_CODE}")',
            required_formula),
        "BorderStyle": "BorderStyle.Solid",
        "BorderThickness": "1",
        "DefaultSelectedItems": default_items,
        "DelayOutput": "false",
        "Height": str(HEIGHT),
        "InputTextPlaceholder": placeholder or (
            PLACEHOLDER if n_min == fl.MIN_SEARCH_LEN
            else f'"At least {n_min} characters, e.g. SSV13 HFC10"'),
        "IsSearchable": "true",
        "ItemDisplayText": "ThisItem.Display",
        "Items": items_fx(results, busy_var, last_var, n_min, block_cond, query_map),
        "LayoutMinWidth": "0",
        "OnChange": on_change,
        # Samme hjoerner som alle andre felter (text_input, dropdown ...).
        **lay.radius(lay.RADIUS_INPUT),
        "SelectMultiple": "false",
        "ValidationState": (f"If({required_formula} && IsBlank(Self.Selected.Code), "
                            "ValidationState.Error, ValidationState.None)"),
        "Width": "0",
    }, display_mode), h=HEIGHT)
    if lock:
        _lock_combo(cmb, lock)
    grow(cmb)

    too_short = f"Len(Trim({query})) < {n_min}"
    if block:
        too_short = f"{too_short} || {block_cond(f'Trim({query})')}"
    if lock:
        too_short = f"{lock} || {too_short}"
    btn = button(f"btn{prefix}{kind}Search", '"Search"', search,
                 width=SEARCH_W, height=HEIGHT,
                 display_mode=(f"If({too_short}, DisplayMode.Disabled, "
                               f"{display_mode})"),
                 accessible=search_accessible,
                 visible=f"!{busy_var}")
    btn.props["LayoutMinWidth"] = str(SEARCH_W)
    stk = stack_cond or lay.below('Tablet')
    if stack_search:
        btn.props["AlignInContainer"] = f"If({stk}, AlignInContainer.Start, AlignInContainer.Center)"

    # Mens soegningen koerer, er knappen skiftet ud med en Spinner i samme
    # plads: hjulet og "Searching...". Kun een af dem er synlig, saa intet i
    # raekken flytter sig.
    busy = busy_box(f"spn{prefix}{kind}Busy", busy_var)

    row_kids = [cmb, btn, busy, *trail]
    if stack_search and trail:
        narrow = stk
        sum_w = " + ".join([str(SEARCH_W)] + [f"({t.props['Width']})" for t in trail]) \
            + f" + {8 * len(trail)}"
        actions = group(f"con{prefix}{kind}Actions", [btn, busy, *trail], direction="Horizontal",
                        gap=8, height=HEIGHT, align_items="Center", justify="Start",
                        width=f"If({narrow}, {width}, {sum_w})")
        actions.props["LayoutMinWidth"] = f"If({narrow}, 0, {sum_w})"
        actions.props["AlignInContainer"] = "AlignInContainer.Start"
        cmb.props["AlignInContainer"] = "AlignInContainer.Start"
        row_kids = [cmb, actions]

    row = group(f"con{prefix}{kind}Input", row_kids, direction="Horizontal",
                gap=8, height=HEIGHT + 2 * ROW_PAD, pad=(ROW_PAD, 0, ROW_PAD, 0),
                align_items="Center", width=width)
    if stack_search:
        row.props["LayoutDirection"] = (f"If({stk}, LayoutDirection.Vertical, "
                                        "LayoutDirection.Horizontal)")
        vgap = 8
        if col_w and trail:
            # Combobox fills column 1 only; the actions start at column 2.
            vgap = 20
            row.props["LayoutGap"] = "20"
            cmb._grow = None
            cmb.props["Width"] = f"If({stk}, {width}, {col_w})"
            cmb.props["LayoutMinWidth"] = cmb.props["Width"]
        row.props["Height"] = (f"If({stk}, {2 * HEIGHT + vgap + 2 * ROW_PAD}, "
                               f"{HEIGHT + 2 * ROW_PAD})")
        row.props["LayoutAlignItems"] = (f"If({stk}, LayoutAlignItems.Stretch, "
                                         "LayoutAlignItems.Center)")
        row.h = row.props["Height"]
    capture = _timer(
        f"tmr{prefix}{kind}Capture", f"!IsBlank({combo}.SearchText)", 300,
        f"If(!IsBlank({combo}.SearchText), Set({query_var}, {combo}.SearchText))")
    return group(f"con{prefix}{kind}Wrap", [row, capture], direction="Vertical", gap=0,
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
