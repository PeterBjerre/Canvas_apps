# -*- coding: utf-8 -*-
"""
Ikoner, der skal vaere ENS overalt i Power Apps-loesningen.

Stierne er SVG-path-data i en 24 x 24 viewBox, tegnet som streg (fill
none, round caps/joins). Stregtykkelse og farve bestemmer den, der tegner:
sidebaren (tools/side_nav.py), hubbens fliser og raekker (Masterdata
Hub/build/build_hub.py) og sideoverskrifterne (build_helpers.page_icon).

EET IKON PR. DOMAENE (issue #74)
--------------------------------
Sidebaren og hubben havde hver sit saet: VH-plan var en tjekliste i
sidebaren og en kalender paa flisen, Materials en terning og en stak
lag, Equipments en chip og en skruenoegle. Nu staar de her, i DOMAIN, og
alle tre steder slaar op i den samme tabel. Et nyt ikon er een linje.

FUNCTIONAL LOCATION (issue #70, #74)
------------------------------------
Et kraftvaerk: jordlinje, fabrikshal med savtakket tag, skorsten og roeg.
Lokationsnaalen rundt om (issue #70) er fjernet igen - i 18 px aad naalen
vaerket, og ikonet laeste som "et sted", ikke som "et anlaeg".
"""

FUNCTIONAL_LOCATION = (
    # jorden
    "M2.5 20.5h19 "
    # hallen med savtakket tag, der fortsaetter op i skorstenen
    "M4 20.5v-8l4 2.5v-2.5l4 2.5v-2.5l4 2.5V5h3v15.5 "
    # vinduer
    "M7 17.5h2M11 17.5h2 "
    # roegen
    "M16.4 3c.7-.9 1.8-.9 2.5 0"
)

EQUIPMENT = (
    "M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 "
    "7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76Z"
)

MEASURING_POINT = (
    "M21.3 15.3a2.4 2.4 0 0 1 0 3.4l-2.6 2.6a2.4 2.4 0 0 1-3.4 0L2.7 8.7a2.41 2.41 "
    "0 0 1 0-3.4l2.6-2.6a2.41 2.41 0 0 1 3.4 0Z "
    "M14.5 12.5l2-2 M11.5 9.5l2-2 M8.5 6.5l2-2 M17.5 15.5l2-2"
)

MATERIAL = "M12 3 2.5 8l9.5 5 9.5-5L12 3Z M2.5 12.5 12 17.5l9.5-5 M2.5 17 12 22l9.5-5"

MAINTENANCE_PLAN = (
    "M5 4.5h14a2 2 0 0 1 2 2V19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6.5a2 2 0 0 1 2-2Z "
    "M8 2.5v4M16 2.5v4M3 10h18"
)

HUB_SATELLITES = (
    (5, 5, "domain-fl"),
    (19, 5, "domain-vhp"),
    (5, 19, "domain-mat"),
    (19, 19, "domain-eq"),
)
HUB = "M7 7l2.6 2.6M17 7l-2.6 2.6M7 17l2.6-2.6M17 17l-2.6-2.6"


def hub_paths(hx):
    """Et midterpunkt med fire satellitter, hver i sin domaenefarve. hx(token) giver farven, som den staar i en streng."""
    sats = "".join(f"<circle cx='{x}' cy='{y}' r='3' fill='{hx(t)}' stroke='none'/>"
                   for x, y, t in HUB_SATELLITES)
    return (f"<path d='{HUB}' stroke='{hx('text-muted')}' stroke-width='1.6'/>"
            f"<circle cx='12' cy='12' r='3.6' fill='{hx('text-muted')}' stroke='none'/>" + sats)

# KKS-opslaget: tre linjer tekst og et forstoerrelsesglas - en
# kodevejledning, man soeger i. Ikke et domaene med anmodninger, saa det
# deler farve med hubben.
KKS = "M3 6h11M3 11h7M3 16h5M15.5 11.5a3.5 3.5 0 1 1 0 7a3.5 3.5 0 1 1 0-7ZM18.1 18.1 21 21"

# Issue Board (issue #114): en billet med perforering - en sag, man har
# meldt og foelger. Heller ikke et domaene, saa samme farve som hubben.
ISSUE_BOARD = ("M4 6h16a1 1 0 0 1 1 1v3a2 2 0 0 0 0 4v3a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-3"
               "a2 2 0 0 0 0-4V7a1 1 0 0 1 1-1Z M15 6.5v2M15 11v2M15 15.5v2")

# Et ikon, der skal spejles vandret, tegnes med denne transform om
# stien (viewBox 24). Bruges af Measuring Points lineal, saa den peger
# samme vej som Equipments skruenoegle (issue #70).
MIRROR_X = "matrix(-1 0 0 1 24 0)"

# noegle (canvas_apps.json) -> (sti, farvetoken, spejlet)
DOMAIN = {
    "hub":                (HUB,                 "text-muted",         False),
    "functionallocation": (FUNCTIONAL_LOCATION, "domain-fl",           False),
    "equipment":          (EQUIPMENT,           "domain-eq",           False),
    "measuringpoint":     (MEASURING_POINT,     "domain-mp",           True),
    "material":           (MATERIAL,            "domain-mat",          False),
    "vhplan":             (MAINTENANCE_PLAN,    "domain-vhp",          False),
    "kks":                (KKS,                 "text-muted",         False),
    "issueboard":         (ISSUE_BOARD,         "text-muted",         False),
}


def path(key):
    return DOMAIN[key][0]


def token(key):
    return DOMAIN[key][1]


def mirrored(key):
    return DOMAIN[key][2]


def stroke_svg(key, color, size=24, stroke=1.8, hx=None):
    """Ikonet som en hel <svg>-streng i size x size. color er et hex-udtryk,
    som det staar inde i en Power Fx-streng. hx(token) bruges af hub-ikonet."""
    t = f" transform='{MIRROR_X}'" if mirrored(key) else ""
    shape = hub_paths(hx) if key == "hub" and hx else f"<path d='{path(key)}'/>"
    return (f"<svg xmlns='http://www.w3.org/2000/svg' width='{size}' height='{size}' "
            f"viewBox='0 0 24 24'><g fill='none' stroke='{color}' "
            f"stroke-width='{stroke}' stroke-linecap='round' stroke-linejoin='round'{t}>"
            f"{shape}</g></svg>")
