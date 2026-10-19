# -*- coding: utf-8 -*-
"""
Application -> ikon og farve (issue #415). EEN tabel for hele loesningen.

Issue Boards sager har en Application (IB_Tickets.Application, en tekst
fra IB_AppSections.Application - seedet fra
sharepoint/seed/IB_AppSections.csv). Hver Application faar her sin noegle
i tools/icons.DOMAIN, saa ikonet og farven er DE SAMME som i sidebaren,
hubbens fliser og hubbens anmodningsliste. De tre Applications uden en
app (Navigation and shared layout, General, Other) har deres egne ikoner
og farver i samme tabel (icons.NAVIGATION/GENERAL/OTHER, tokens app-*).

Vil en skaerm vise en Application med ikon, slaar den op her - ingen
skaerm har sin egen tabel. tests/test_app_icons.py holder tabellen i trit
med seed-filen (IconRef/DomainColor).

TEGNINGEN
---------
Samme stil som hubbens anmodningsliste (build_hub._tile_icon_svg):
ikonet i domaenets farve paa en tonet firkant (12 % af farven) med runde
hjoerner - her i raekkens kompakte stoerrelse, TILE px med et GLYPH px
symbol. Masterdata Hubs hus tegnes i sine fire domaenefarver som i
sidebaren (icons.hub_paths).

URI'erne regnes EEN gang i en navngiven formel (formula()) - som hubbens
MdIcons (R2-081) - og raekken slaar op med Application (uri()).
"""
import icons
from design_tokens import ref_hex

# Vaerdien i IB_Tickets.Application -> noeglen i icons.DOMAIN.
# Vaerdierne er IB_AppSections.csv's - staves praecis som dér.
APPLICATIONS = {
    "Masterdata Hub":               "hub",
    "Functional Location":          "functionallocation",
    "Maintenance Plan":             "vhplan",
    "Materials":                    "material",
    "Equipments":                   "equipment",
    "Measuring Point":              "measuringpoint",
    "KKS lookup":                   "kks",
    "Issue Board":                  "issueboard",
    "Navigation and shared layout": "navigation",
    "General":                      "general",
    "Other":                        "other",
}
# En Application, tabellen ikke kender (en ny raekke i IB_AppSections):
# prikkerne for Other, indtil den faar sin egen linje her.
FALLBACK = "Other"

for _a, _k in APPLICATIONS.items():
    if _k not in icons.DOMAIN:
        raise SystemExit("app_icons: %r peger paa en ukendt ikonnoegle %r" % (_a, _k))

# Raekkens kompakte ikon: TILE px firkant med et GLYPH px symbol.
TILE = 20
GLYPH = 14
RADIUS = 5
TINT = 0.12


def key(app):
    """Ikonnoeglen for en Application (FALLBACK, hvis den er ukendt)."""
    return APPLICATIONS.get(app, APPLICATIONS[FALLBACK])


def _hx(token):
    return '" & %s & "' % ref_hex(token)


def tile_svg(icon_key, size=TILE, glyph=GLYPH):
    """Ikonet i en tonet firkant som <svg>-streng til en Power Fx-streng
    (farverne er token-udtryk, saa de foelger temaet)."""
    c = _hx(icons.token(icon_key))
    pad = (size - glyph) / 2
    shape = (icons.hub_paths(_hx) if icon_key == "hub"
             else f"<path d='{icons.path(icon_key)}'/>")
    if icons.mirrored(icon_key):
        shape = f"<g transform='{icons.MIRROR_X}'>{shape}</g>"
    return (f"<svg xmlns='http://www.w3.org/2000/svg' width='{size}' height='{size}' "
            f"viewBox='0 0 {size} {size}'><rect width='{size}' height='{size}' "
            f"rx='{RADIUS}' fill='{c}' fill-opacity='{TINT:g}'/>"
            f"<g transform='translate({pad:g} {pad:g}) scale({glyph / 24:g})' fill='none' "
            f"stroke='{c}' stroke-width='{icons.stroke(glyph):g}' stroke-linecap='round' "
            f"stroke-linejoin='round'>{shape}</g></svg>")


def formula(name):
    """Den navngivne formel: Table({ Application, Uri }) - een raekke pr.
    Application, URI'en faerdigkodet."""
    rows = ",\n".join(
        f'    {{ Application: "{a}", Uri: "data:image/svg+xml;utf8," & '
        f'EncodeUrl("{tile_svg(k)}") }}'
        for a, k in APPLICATIONS.items())
    return (f"// Application -> ikon (tools/app_icons.py, issue #415) - ret ikke her.\n"
            f"{name} = Table(\n{rows}\n);")


def uri(name, app_expr):
    """Ikonets URI for app_expr (et Power Fx-tekstudtryk); en ukendt
    Application faar FALLBACK's."""
    return (f"Coalesce(LookUp({name}, Application = {app_expr}).Uri, "
            f'LookUp({name}, Application = "{FALLBACK}").Uri)')
