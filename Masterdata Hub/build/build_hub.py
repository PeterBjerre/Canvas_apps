# -*- coding: utf-8 -*-
"""
Landingssiden for SAP masterdata-indmeldinger.

EEN DATAKILDE
-------------
Skaermen laeser kun MD_RequestIndex. Den maa ALDRIG laese de fem
domaenelister og flette dem i klienten - det er fem forbindelser og en
fletning, der ikke kan delegeres. Se docs/07-landingsside.md.

INGEN DATAHENTNING I App.OnStart
--------------------------------
OnStart betales af hver bruger hver gang. Galleriet binder direkte til et
filter, og flisernes tal taelles paa det samme, allerede afgraensede saet.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import (Ctrl, C_CARD_BG, C_CARD_BORDER, C_TITLE, C_MUTED, C_PRIMARY, C_WHITE,
                        C_INFO_FG, C_INFO_BG, C_NEUTRAL_BG, C_DIVIDER, C_TRANSPARENT,
                        C_APP_BG, FONT, SHELL_W)
from build_helpers import text_ctrl, group, button, card, theme_button
from hub_config import LIST, COL_NO, DOMAINS, STATUS, APP_TARGET
from design_tokens import theme_query
from layout_tokens import if_below

# Hubben aabner satellitterne. Temaet skal med i URL'en, fordi
# SaveData-lageret er isoleret pr. app-id: uden den ville en moerk hub
# aabne en lys Equipment-app, og brugeren ville se appen skifte farve som
# foelge af sit eget klik. Satellitten laeser Param("theme") i OnStart.
THEME_Q = theme_query("?")      # flisen sender ingen andre parametre
THEME_Q_AMP = theme_query("&")  # "Open" sender allerede ?reqid=

# ---------------------------------------------------------------------------
# Afgraensningen. Begge grene er delegerbare hver for sig:
#   Mine  - afgraenset af brugeren, altid en haandterbar maengde
#   Koeen - afgraenset af IsOpen, et indekseret boolsk felt
# IsOpen vedligeholdes af submit-flowet sammen med Status. Et enkelt boolsk
# felt er delegerbart; en raekke OR'ede statusvaerdier er det ikke.
# ---------------------------------------------------------------------------
SCOPE = (
    "If(\n"
    "    gblView = \"mine\",\n"
    f"    Filter('{LIST}', RequesterEmail = gblMe),\n"
    f"    Filter('{LIST}', IsOpen = true)\n"
    ")"
)

# Tabellens kolonner. EEN kilde til bredderne, saa overskriften og raekken
# ikke kan komme til at staa forskudt.
# DOMAIN er bredere end den danske DOMAENE, fordi etiketterne er det:
# "Functional location" fylder mere end "Funktionsplads". Resten af
# bredden ligger i INDMELDING/REQUEST, som regnes af de faste.
COLS = [("DOMAIN", 124), ("REQUEST", 0), ("PLANT", 62), ("STATUS", 176),
        ("LAST", 92), ("", 76)]
GAP = 10
FIXED = sum(w for _, w in COLS) + GAP * (len(COLS) - 1)
# Bruges BAADE i listehovedet og i galleriets raekke. Ingen af de to
# steder er forelderen selve galleriet - kun et galleris DIREKTE barn
# kender Parent.TemplateWidth, og raekkens indhold ligger et niveau
# dybere. Begge foraeldre er lige saa brede som skabelonen, saa
# Parent.Width giver det samme tal og virker begge steder.
MAIN_W = f"Parent.Width - {FIXED}"

ROW_H = 46
GAL_ROWS = 9


def _switch(field_index, fallback, quote=False):
    """Switch over statusvaerdien, bygget af ordforraadet i hub_config.

    quote=True naar feltet er TEKST. Farvefelterne er Power Fx-udtryk
    ("RGBA(...)") og skal staa uden anfoerselstegn, men etiketten er en
    streng - uden dem blev "In progress" til to identifiers, og Switch'en
    kunne ikke oversaettes. Den fejl kunne ikke ses i appen, fordi hubben
    endnu ikke er oprettet i Studio."""
    parts = [f'"{s[0]}", ' + (f'"{s[field_index]}"' if quote else f'{s[field_index]}')
             for s in STATUS]
    return "Switch(\n    ThisItem.Status.Value,\n    " + ",\n    ".join(parts) + \
           f",\n    {fallback}\n)"


# ---------------------------------------------------------------------------
# Toplinje
# ---------------------------------------------------------------------------
def _seg(name, label, value):
    b = button(name, f'"{label}"',
               f'Set(gblView, "{value}"); Set(gblDomain, "")', width=168, height=34)
    b.props["Appearance"] = f'If(gblView = "{value}", ButtonAppearance.Primary, ButtonAppearance.Secondary)'
    b.props["BasePaletteColor"] = C_PRIMARY
    b.props["Color"] = f'If(gblView = "{value}", {C_WHITE}, {C_TITLE})'
    b.props["BorderColor"] = C_CARD_BORDER
    b.props["BorderThickness"] = "1"
    return b


def build_bar():
    brand = text_ctrl("txtMdBrand", '"Masterdata"', size=22, weight="Semibold", height=30,
                      width=150, wrap="false")
    sub = text_ctrl("txtMdSub", '"SAP requests"', size=13, color=C_MUTED, height=30,
                    width=140, wrap="false")
    left = group("conMdBrand", [brand, sub], direction="Horizontal", gap=10, height=34,
                 align_items="Center", width=300)

    seg = group("conMdSeg", [_seg("btnMdViewMine", "My requests", "mine"),
                             _seg("btnMdViewQueue", "Queue", "queue")],
                direction="Horizontal", gap=0, height=34, align_items="Center", width=336)

    who = text_ctrl("txtMdWho",
                    'If(gblView = "mine", gblMe, "Queue - whole department")',
                    size=12, color=C_MUTED, height=34, align="Right", wrap="false",
                    width=f"Max(160, {SHELL_W} - 300 - 336 - 24)")

    # Temaknappen staar YDERST TIL HOEJRE og med engelsk tekst som resten
    # af hubben. Den er den samme kontrol som i de tre satellitter - se
    # build_helpers.theme_button.
    theme = theme_button("btnMdTheme", light_label='"Dark"', dark_label='"Light"')

    # who-feltet skal give plads til knappen, ellers skubber den linjen om.
    who.props["Width"] = f"Max(120, {SHELL_W} - 300 - 336 - 92 - 36)"

    return group("conMdBar", [left, seg, who, theme], direction="Horizontal", gap=12,
                 height=34, align_items="Center", wrap="true")


# ---------------------------------------------------------------------------
# Domaenefliser
# ---------------------------------------------------------------------------
# Fem fliser eller to. Det er en beslutning om, hvor stor skaermen er -
# altsaa et viewport-braekpunkt, ikke en udregning paa indholdet. Stod foer
# som SHELL_W < 940, hvilket er App.Width < 1004: et af fire naesten ens
# tal. Se tools/layout_tokens.py.
TILE_W = if_below("Desktop", f"({SHELL_W} - 10) / 2", f"({SHELL_W} - 40) / 5")


def build_tiles():
    tiles = []
    for d in DOMAINS:
        n = d["short"]
        stripe = group(f"conMdStripe{n}", [], height=4, width=34, fill=d["color"],
                       direction="Horizontal")
        name = text_ctrl(f"txtMdTileName{n}", f'"{d["name"]}"', size=14, weight="Semibold",
                         height=20, wrap="false")

        # Tallet taelles paa det samme afgraensede saet som galleriet bruger -
        # ikke som et selvstaendigt opslag mod hele listen.
        count = text_ctrl(
            f"txtMdTileCount{n}",
            f'Text(CountRows(Filter({SCOPE}, Domain.Value = "{d["key"]}", IsOpen = true)))',
            size=26, weight="Semibold", height=32, wrap="false")
        lbl = text_ctrl(f"txtMdTileLbl{n}",
                        'If(gblView = "mine", "open with me", "open in the queue")',
                        size=11, color=C_MUTED, height=16, wrap="false")

        bw = f"(({TILE_W}) - 24 - 6) / 2"
        bFilter = button(f"btnMdTileFilter{n}",
                         f'If(gblDomain = "{d["key"]}", "Show all", "Filter")',
                         f'Set(gblDomain, If(gblDomain = "{d["key"]}", "", "{d["key"]}"))',
                         width=bw, height=28)
        if d["url"]:
            # Temaet sendes MED i URL'en. SaveData er isoleret pr. app-id,
            # saa uden det ville satellitten aabne i sit eget gamle tema -
            # og brugeren ville se appen skifte farve, fordi han klikkede.
            new_action = (f'Launch("{d["url"]}" & {THEME_Q}, {{ }}, {APP_TARGET})')
        else:
            new_action = ('Notify("This app has not been built yet.", NotificationType.Warning)')
        bNew = button(f"btnMdTileNew{n}",
                      '"New request"' if d["url"] else '"Coming soon"',
                      new_action, primary=bool(d["url"]), width=bw, height=28,
                      display_mode="DisplayMode.Edit" if d["url"] else "DisplayMode.Disabled")
        btns = group(f"conMdTileBtns{n}", [bFilter, bNew], direction="Horizontal", gap=6,
                     height=28, align_items="Center")

        tiles.append(group(
            f"conMdTile{n}", [stripe, name, count, lbl, btns], direction="Vertical", gap=6,
            fill=C_CARD_BG, radius=10, pad=(12, 12, 12, 12), width=TILE_W,
            border_color=f'If(gblDomain = "{d["key"]}", {d["color"]}, {C_CARD_BORDER})',
            border_thickness=1))

    tile_h = tiles[0].h
    return group("conMdTiles", tiles, direction="Horizontal", gap=10, wrap="true",
                 # SAMME braekpunkt som TILE_W. Var de uenige, ville beholderen
                  # have hoejde til een raekke fliser, mens fliserne selv stod i
                  # tre - og de to nederste raekker blev klippet af.
                  height=if_below("Desktop", f"3 * ({tile_h}) + 20", tile_h))


# ---------------------------------------------------------------------------
# Filtre
# ---------------------------------------------------------------------------
def _chip(name, label, value):
    b = button(name, f'"{label}"', f'Set(gblStatusMode, "{value}")', width=104, height=32)
    b.props["Appearance"] = f'If(gblStatusMode = "{value}", ButtonAppearance.Primary, ButtonAppearance.Secondary)'
    b.props["BasePaletteColor"] = C_INFO_FG
    b.props["Color"] = f'If(gblStatusMode = "{value}", {C_WHITE}, {C_MUTED})'
    b.props["BorderColor"] = C_CARD_BORDER
    b.props["BorderThickness"] = "1"
    return b


def build_filters():
    search = Ctrl("txtMdSearch", "ModernTextInput", props={
        "AccessibleLabel": '"Search number, text or plant"',
        "BorderColor": C_CARD_BORDER, "BorderStyle": "BorderStyle.Solid", "BorderThickness": "1",
        "Color": C_TITLE, "Default": '""', "Fill": C_WHITE, "Font": FONT, "Height": "32",
        "LayoutMinWidth": "0", "Placeholder": '"Search number, text or plant"',
        "RadiusBottomLeft": "8", "RadiusBottomRight": "8", "RadiusTopLeft": "8", "RadiusTopRight": "8",
        "Size": "13", "Type": "TextInputType.Search",
        "Width": f"Max(180, {SHELL_W} - 3 * 104 - 200 - 5 * 8)",
    }, h=32)
    count = text_ctrl("txtMdCount",
                      f'Text(CountRows({SCOPE})) & " requests in this view"',
                      size=12, color=C_MUTED, height=32, align="Right", width=200, wrap="false")
    return group("conMdFilters",
                 [search, _chip("btnMdStOpen", "Open", "open"),
                  _chip("btnMdStDone", "Closed", "done"),
                  _chip("btnMdStAll", "All", "all"), count],
                 direction="Horizontal", gap=8, height=32, align_items="Center", wrap="true")


# ---------------------------------------------------------------------------
# Listen
# ---------------------------------------------------------------------------
ITEMS = (
    "SortByColumns(\n"
    "    Filter(\n"
    f"        {SCOPE},\n"
    '        gblDomain = "" || Domain.Value = gblDomain,\n'
    '        gblStatusMode = "all" || (gblStatusMode = "open" && IsOpen) ||\n'
    '            (gblStatusMode = "done" && !IsOpen),\n'
    '        IsBlank(Trim(txtMdSearch.Text)) ||\n'
    f"            StartsWith({COL_NO}, Trim(txtMdSearch.Text)) ||\n"
    "            StartsWith(ShortText, Trim(txtMdSearch.Text)) ||\n"
    "            StartsWith(Plant, Trim(txtMdSearch.Text))\n"
    "    ),\n"
    '    "LastActionOn", SortOrder.Descending\n'
    ")"
)


def build_list():
    head = group("conMdListHead",
                 [text_ctrl(f"txtMdH{i}", f'"{t}"', size=10, weight="Semibold", color=C_MUTED,
                            height=20, wrap="false",
                            width=(MAIN_W if w == 0 else w))
                  for i, (t, w) in enumerate(COLS)],
                 direction="Horizontal", gap=GAP, height=20, align_items="Center")

    badge = text_ctrl("txtMdRowDomain",
                      "Switch(\n    ThisItem.Domain.Value,\n    " +
                      ",\n    ".join(f'"{d["key"]}", "{d["name"]}"' for d in DOMAINS) +
                      ',\n    "?"\n)',
                      size=10, weight="Semibold", height=20, width=COLS[0][1], wrap="false",
                      align="Center",
                      extra={"Color": C_WHITE,
                             "Fill": "Switch(\n    ThisItem.Domain.Value,\n    " +
                                     ",\n    ".join(f'"{d["key"]}", {d["color"]}' for d in DOMAINS) +
                                     f',\n    {C_MUTED}\n)',
                             "AlignInContainer": "AlignInContainer.Center",
                             "PaddingLeft": "6", "PaddingRight": "6",
                             "RadiusBottomLeft": "4", "RadiusBottomRight": "4",
                             "RadiusTopLeft": "4", "RadiusTopRight": "4"})

    no = text_ctrl("txtMdRowNo", f"ThisItem.{COL_NO}", size=11, color=C_MUTED, height=16, wrap="false")
    txt = text_ctrl("txtMdRowText", "ThisItem.ShortText", size=13, height=18, wrap="false")
    main = group("conMdRowMain", [no, txt], direction="Vertical", gap=2, width=MAIN_W,
                 align_items="Stretch")

    plant = text_ctrl("txtMdRowPlant", "ThisItem.Plant", size=12, color=C_MUTED, height=36,
                      width=COLS[2][1], wrap="false")

    pill = text_ctrl("txtMdRowStatus", _switch(1, '"Unknown"', quote=True), size=11, weight="Semibold",
                     height=18, width=120, wrap="false", align="Center",
                     extra={"Color": _switch(3, C_MUTED), "Fill": _switch(4, C_NEUTRAL_BG),
                            "PaddingLeft": "8", "PaddingRight": "8",
                            "RadiusBottomLeft": "9", "RadiusBottomRight": "9",
                            "RadiusTopLeft": "9", "RadiusTopRight": "9"})
    steps = group("conMdRowSteps",
                  [group(f"conMdStep{i}", [], height=4, width=20, direction="Horizontal",
                         fill=f"If(ThisItem.StatusStep >= {i}, {_switch(3, C_MUTED)}, {C_DIVIDER})")
                   for i in range(1, 6)],
                  direction="Horizontal", gap=3, height=4, width=112)
    stat = group("conMdRowStat", [pill, steps], direction="Vertical", gap=5, width=COLS[3][1],
                 align_items="Start")

    when = text_ctrl("txtMdRowWhen",
                     'With(\n'
                     '    { d: DateDiff(ThisItem.LastActionOn, Now(), TimeUnit.Days) },\n'
                     '    If(d <= 0, "Today", If(d = 1, "Yesterday", Text(d) & " days ago"))\n'
                     ')',
                     size=11, color=C_MUTED, height=36, width=COLS[4][1], align="Right",
                     wrap="false")

    open_btn = button("btnMdRowOpen", '"Open"',
                      ("If(\n"
                       "    IsBlank(ThisItem.AppUrl),\n"
                       '    Notify("This request has no app URL.", NotificationType.Error),\n'
                       "    Launch(\n"
                       '        ThisItem.AppUrl & If(Find("?", ThisItem.AppUrl) > 0, "&", "?") &\n'
                       f'            "reqid=" & ThisItem.RequestGuid & {THEME_Q_AMP},\n'
                       "        { },\n"
                       f"        {APP_TARGET}\n"
                       "    )\n"
                       ")"),
                      width=COLS[5][1], height=28,
                      accessible=f'"Open " & ThisItem.{COL_NO} & " in the domain app"')

    row = group("conMdRow", [badge, main, plant, stat, when, open_btn],
                direction="Horizontal", gap=GAP, height="Parent.TemplateHeight - 2",
                align_items="Center", width="Parent.TemplateWidth", fill=C_CARD_BG)

    gal = Ctrl("galMdRequests", "Gallery", variant="Vertical", props={
        "AccessibleLabel": '"Requests"',
        "BorderStyle": "BorderStyle.None", "Fill": C_CARD_BORDER, "FillPortions": "0",
        "Height": str(GAL_ROWS * (ROW_H + 2)),
        "Items": ITEMS, "LayoutMinWidth": "0", "LoadingSpinner": "LoadingSpinner.Controls",
        "Selectable": "false", "ShowScrollbar": "true", "TabIndex": "0",
        "TemplatePadding": "2", "TemplateSize": str(ROW_H),
        "Width": "Parent.Width", "WrapCount": "1",
    }, children=[row], h=GAL_ROWS * (ROW_H + 2))

    empty = text_ctrl("txtMdEmpty", '"No requests match the filters."', size=13,
                      color=C_MUTED, height=24, wrap="true",
                      visible=f"IfError(IsEmpty({ITEMS}), false)")

    return card("conMdListCard", [head, gal, empty], gap=8)
