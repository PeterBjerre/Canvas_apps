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


# ===========================================================================
# IKONSYSTEMET (issue #139)
# ===========================================================================
# EEN familie, EEN metode. Alle ikoner i BIO SAP er enten
#
#   1. Fluent-ikoner paa ModernButton (Icon = "Save", "Delete", ...). Det er
#      Power Apps' egne moderne ikoner - ingen klassiske Icon.*-kontroller
#      findes i appen, og build_all afviser ingen af dem i dag, fordi der
#      ingen er. Navnene staar i FLUENT herunder, saa samme handling altid
#      faar samme ikon.
#   2. Stregikoner som SVG i en Image-kontrol - der, hvor en moderne knap
#      ikke kan tegne det, vi skal bruge (domaenefarver, sidebarens
#      markering, statusikoner, godkendelsesforloebet). De er tegnet i
#      SAMME stil som Fluent "Regular": 24 x 24-gitter, runde ender og
#      hjoerner, ingen fyld, hjoernerunding 2 paa rektangler.
#
# STREGTYKKELSE OG OPTISK STOERRELSE
#   Stregen er i gitterenheder, saa et ikon, der tegnes mindre, ville faa
#   en tyndere streg paa skaermen. stroke(px) holder den TEGNEDE streg paa
#   ca. 1,5 px uanset stoerrelse (mellem 1,5 og 2,0 enheder):
#       16-18 px -> 2.0    20 px -> 1.8    22 px -> 1.65    24+ px -> 1.5
#   Alle tegnefunktioner herunder bruger den, naar intet andet er givet.
#
# OUTLINE OG FYLD
#   Outline er standard. Fyld bruges KUN til at baere en tilstand:
#     * den valgte side i sidebaren: kraftigere streg (SELECTED_BOOST) paa en
#       tonet flade med accentstregen - ikke et andet ikon;
#     * knuder i godkendelsesforloebet: en fyldt cirkel i tilstandens farve
#       med et hvidt symbol (afsluttet/aktiv) - en hul cirkel er "afventer";
#     * statusikonet "In progress": en halvt fyldt cirkel (STATUS_PROGRESS).
#
# FARVE OG TILSTAND
#   Farven er altid en token (design_tokens). Handlingsikoner er neutrale
#   (text-muted), destruktive handlinger er state-error-fg, domaeneikoner
#   har domaenets farve, statusikoner tilstandens farve. Deaktiveret:
#   samme ikon i text-muted med DISABLED_OPACITY - falmet, aldrig en anden
#   form, og uden ramme. Farven staar aldrig alene: hver status har sin
#   egen FORM (se STATUS_*), og hver tilstand i forloebet sit eget symbol
#   (WORKFLOW).
#
# HANDLING ELLER STATUS
#   Et handlingsikon er klikbart: TabIndex 0, AccessibleLabel, Tooltip,
#   fokusramme, hover- og tryk-flade med runde hjoerner (HIT_RADIUS) og
#   luft rundt om symbolet (svg(..., box=)). Et statusikon er pynt ved
#   siden af sin tekst: TabIndex -1, tom etiket, ingen hover, ingen luft.
# ===========================================================================

# Fluent-navnene paa ModernButton. Samme handling = samme navn overalt.
FLUENT = {
    "save": "Save",
    "submit": "Send",       # indsend en anmodning = send en besked
    "send": "Send",
    "edit": "Edit",
    "delete": "Delete",
    "add": "Add",
    "dismiss": "Dismiss",
    "info": "Info",
    "upload": "ArrowUpload",
    "long_text": "DocumentText",
    "note": "Note",
    "expand": "ChevronDown",
    "collapse": "ChevronUp",
}

# Stregen ved en given tegnet stoerrelse - se ovenfor.
def stroke(px):
    return round(min(2.0, max(1.5, 36.0 / float(px))) * 20) / 20


# Den valgte side i sidebaren: kraftigere streg.
SELECTED_BOOST = 0.4
# Et deaktiveret ikon: falmet, samme form.
DISABLED_OPACITY = 0.45
# Hover- og fokusfladen paa et klikbart ikon (Image.Radius*).
HIT_RADIUS = 6

# --- handlinger og navigation -------------------------------------------
CHEVRON_RIGHT = "M9 6l6 6-6 6"
CHEVRON_DOWN = "M6 9l6 6 6-6"
CHEVRON_UP = "M6 15l6-6 6 6"
EXPAND = "M6 6l6 6-6 6 M12 6l6 6-6 6"
COLLAPSE = "M18 6l-6 6 6 6 M12 6l-6 6 6 6"
MENU = "M4 7h16M4 12h16M4 17h16"
# Besked til SAP-vedligehold: en taleboble (samme betydning som foer, nu
# med de samme runde hjoerner som resten).
MESSAGE = ("M5 4.5h14a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H10l-4.5 3.5v-3.5H5a2 2 0 0 1-2-2v-9"
           "a2 2 0 0 1 2-2Z")
EDIT = ("M4 20h4.5L19.3 9.2a2 2 0 0 0 0-2.8l-1.7-1.7a2 2 0 0 0-2.8 0L4 15.5V20Z "
        "M13.5 6l4.5 4.5")
DELETE = ("M4 6.5h16 M9.5 6.5v-2a1 1 0 0 1 1-1h3a1 1 0 0 1 1 1v2 "
          "M6 6.5l.9 12.6a2 2 0 0 0 2 1.9h6.2a2 2 0 0 0 2-1.9L18 6.5 M10 10.5v6M14 10.5v6")
# Aktivitet (tidslinjen): et ur med en pil mod uret - "historik". Ikke
# statusens ur: In progress er sin egen form (STATUS_PROGRESS).
HISTORY = ("M3.5 12a8.5 8.5 0 1 0 8.5-8.5a9.2 9.2 0 0 0-6.4 2.6L3.5 8 "
           "M3.5 3.5V8H8 M12 7.5V12l3 2")
# Noter: en notesblok med foldet hjoerne - samme som Fluent "Note" paa
# VH-planens knap. Ikke Drafts dokument.
NOTE = ("M5 3.5h14a1.5 1.5 0 0 1 1.5 1.5v9.5l-6 6H5A1.5 1.5 0 0 1 3.5 19V5A1.5 1.5 0 0 1 5 3.5Z "
        "M14.5 20.5V16a1.5 1.5 0 0 1 1.5-1.5h4.5 M7.5 8.5h9M7.5 12h5")
PERSON = "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z M4.5 20.5a7.5 7.5 0 0 1 15 0"
LIST = "M9 6h11M9 12h11M9 18h11 M4.5 6h.01M4.5 12h.01M4.5 18h.01"
# View mode: et oeje. Edit mode: blyanten (EDIT).
EYE = ("M2.5 12s3.5-6.5 9.5-6.5 9.5 6.5 9.5 6.5-3.5 6.5-9.5 6.5S2.5 12 2.5 12Z "
       "M12 14.8a2.8 2.8 0 1 0 0-5.6 2.8 2.8 0 0 0 0 5.6Z")

# --- status paa en anmodning (MD_RequestIndex.Status) --------------------
# Hver status sin egen FORM - farven alene maa ikke baere den (issue #74,
# #139). Cirklen er "en sag i et flow"; dokument og skjold falder udenfor:
# Draft er endnu ikke i flowet, Created in SAP er lukket og faerdig.
_RING = "M12 21.5a9.5 9.5 0 1 0 0-19 9.5 9.5 0 0 0 0 19Z"
STATUS_DRAFT = ("M14 2.5H7a2 2 0 0 0-2 2v15a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7.5L14 2.5Z "
                "M14 2.5v5h5 M9 13h6M9 17h6")
STATUS_SUBMITTED = "M21.5 3 2.5 10.5l7 3 3 7L21.5 3Z M9.5 13.5 21.5 3"
# In progress: en halvt fyldt cirkel - "paabegyndt". (streg, fyld)
STATUS_PROGRESS = (_RING, "M12 6.5a5.5 5.5 0 0 1 0 11Z")
STATUS_AWAITING = _RING + " M12 7.5v5.5M12 16.5v.01"
STATUS_READY = _RING + " M8 12.2l2.8 2.8L16 9.5"
STATUS_CREATED = ("M12 21.5s7.5-3.2 7.5-9.5V5.2L12 2.5 4.5 5.2V12c0 6.3 7.5 9.5 7.5 9.5Z "
                  "M8.8 11.8l2.3 2.3 4.3-4.6")
STATUS_REJECTED = _RING + " M9 9l6 6M15 9l-6 6"
STATUS_CANCELLED = _RING + " M5.3 5.3l13.4 13.4"

# --- godkendelsesforloebet -----------------------------------------------
# Symbolet INDE I en fyldt knude (hvid streg paa tilstandens farve). Samme
# tilstand = samme symbol i listens stribe og i popuppens tidslinje.
WORKFLOW = {
    "Approved":    "M7 12.5l3.2 3.2L17 9",
    "Done":        "M7 12.5l3.2 3.2L17 9",
    "Skipped":     "M8 12h8",
    "In progress": "M12 7a5 5 0 1 1-5 5",      # en trekvart ring: i gang
    "Returned":    "M10 8l-4 4 4 4M6 12h8a4 4 0 0 1 4 4",
    "Rejected":    "M8.5 8.5l7 7M15.5 8.5l-7 7",
    "Cancelled":   "M7.5 16.5l9-9",
    "Admin":       "M7.5 16.5h2.2l6.8-6.8-2.2-2.2-6.8 6.8v2.2Z",
    "Note":        "M8 9h8M8 12.5h8M8 16h5",
    "Pending":     "M7.5 12h.01M12 12h.01M16.5 12h.01",
}
WORKFLOW_DEFAULT = "M12 12v.01"


def _parts(d):
    """(streg, fyld) - en sti kan have en fyldt del (STATUS_PROGRESS)."""
    return d if isinstance(d, tuple) else (d, None)


def glyph(d, color, size=24, x=0, y=0, width=None, mirror=False, opacity=None):
    """Et stregikon som <g>, size px stort med oeverste venstre hjoerne i x, y.
    d er en sti fra denne fil (eller (streg, fyld)). width = stregen i
    gitterenheder; uden den stroke(size). color er et hex-udtryk, som det
    staar i en Power Fx-streng."""
    s = size / 24
    w = stroke(size) if width is None else width
    line, solid = _parts(d)
    inner = f"<path d='{line}'/>"
    if solid:
        inner += f"<path d='{solid}' fill='{color}' stroke='none'/>"
    if mirror:
        inner = f"<g transform='{MIRROR_X}'>{inner}</g>"
    op = f" opacity='{opacity:g}'" if opacity is not None else ""
    return (f"<g transform='translate({x:g} {y:g}) scale({s:g})' fill='none' "
            f"stroke='{color}' stroke-width='{w:g}' stroke-linecap='round' "
            f"stroke-linejoin='round'{op}>{inner}</g>")


def svg(d, color, size=24, box=None, width=None, mirror=False, opacity=None):
    """Et helt <svg> med ikonet. box > size giver luft rundt om symbolet -
    til et klikbart ikon, hvis hover-flade er box px stor. Uden box fylder
    symbolet hele billedet (statusikoner, pynt)."""
    b = box or size
    off = (b - size) / 2
    return (f"<svg xmlns='http://www.w3.org/2000/svg' width='{b:g}' height='{b:g}' "
            f"viewBox='0 0 {b:g} {b:g}'>"
            + glyph(d, color, size=size, x=off, y=off, width=width, mirror=mirror,
                    opacity=opacity)
            + "</svg>")


def hit_radius(props):
    """Runde hjoerner paa et klikbart ikons hover-, tryk- og fokusflade."""
    for k in ("RadiusTopLeft", "RadiusTopRight", "RadiusBottomLeft", "RadiusBottomRight"):
        props[k] = str(HIT_RADIUS)
    return props


def path(key):
    return DOMAIN[key][0]


def token(key):
    return DOMAIN[key][1]


def mirrored(key):
    return DOMAIN[key][2]


def stroke_svg(key, color, size=24, stroke=None, hx=None):
    """Domaeneikonet som en hel <svg>-streng i size x size. color er et
    hex-udtryk, som det staar inde i en Power Fx-streng. hx(token) bruges
    af hub-ikonet. stroke: uden den stroke(size) - se IKONSYSTEMET."""
    w = globals()["stroke"](size) if stroke is None else stroke
    t = f" transform='{MIRROR_X}'" if mirrored(key) else ""
    shape = hub_paths(hx) if key == "hub" and hx else f"<path d='{path(key)}'/>"
    return (f"<svg xmlns='http://www.w3.org/2000/svg' width='{size}' height='{size}' "
            f"viewBox='0 0 24 24'><g fill='none' stroke='{color}' "
            f"stroke-width='{w:g}' stroke-linecap='round' stroke-linejoin='round'{t}>"
            f"{shape}</g></svg>")
