# -*- coding: utf-8 -*-
"""
LAYOUTTOKENS - den eneste kilde til, hvornaar layoutet skifter.

HVORFOR DEN HER FIL FINDES
--------------------------
Braekpunkterne stod ni steder i fire filer, maalt mod tre forskellige
baser (App.Width, SHELL_W = App.Width - 64, HERO_CW = App.Width - 96).
Omregnet til App.Width laa de saadan her:

     704   SHELL_W < 640          to kolonner -> en
     718   HERO_CW < 622          procesindikatoren ombryder
     740   (SHELL_W - 36) < 640   felterne -> en kolonne
     900   App.Width < 900        topbjaelken ombryder
     996   HERO_CW < 900          heroen stables
    1000   App.Width < 1000       item-skinnen stables
    1004   SHELL_W < 940          fem fliser -> to
    1024   App.Width < 1024       FillPortions slaas fra
    1600   App.Width < 1600       listen ved siden af formularen

FIRE braekpunkter inden for 28 pixels. Traekker en bruger vinduet fra 990
til 1030, sker der fire ting paa fire forskellige tidspunkter - og det
ligner ikke et layout, der skifter tilstand, men et der saetter sig.
Ingen af de fire tal var valgt i forhold til de tre andre; de var valgt
hver for sig, i hver sin maaned.

DE TO SLAGS GRAENSER
--------------------
Det var ikke bare et talproblem. De ni graenser er TO forskellige
spoergsmaal, som var skrevet ens:

1. VIEWPORT-TIER - "hvor stor er skaermen?"
   Fem fliser eller to. Hero ved siden af eller ovenpaa. Det er en
   beslutning om enhedsklasse, og den skal traeffes det SAMME sted for
   hele appen. De hoerer til her, i BREAKPOINTS.

2. CONTAINER-GRAENSE - "er der plads til indholdet i DENNE kasse?"
   Et kort paa 600 px skal stable sine to kolonner, uanset om vinduet er
   1920 bredt. Det er ikke en enhedsklasse; det er aritmetik paa
   indholdet. De skal blive ved at vaere lokale - men de skal REGNES ud
   af det, de beskytter, ikke skrives som et tal.

   Forskellen er ikke akademisk: topbjaelken havde 900 skrevet i sig,
   mens hoejresiden fyldte 440. Da hoejresiden blev 542 bred, fulgte de
   900 ikke med, og bjaelken ville have ombrudt paa enhver skaermbredde.
   En graense, der regnes ud af sit indhold, kan ikke komme ud af trit
   med det.

HVORDAN
-------
Viewport-tieren staar som TO navngivne formler i App.Formulas:

    LayoutContext = "Mobile" | "Tablet" | "Desktop" | "Wide"
    LayoutRank    = 1 | 2 | 3 | 4

LayoutContext er den, man kan laese i Studio. LayoutRank er den, man kan
sammenligne med: "det her eller bredere" bliver LayoutRank >= 3 i stedet
for en kaede af eller'er over strenge.

Builderne skriver aldrig et tal. De skriver below("Desktop") eller
at_least("Wide"), og faar det rigtige udtryk.
"""

# ---------------------------------------------------------------------------
# Viewport-tiers
#
# Tallet er den mindste App.Width, tieren gaelder fra.
#
# HVOR TALLENE KOMMER FRA
# -----------------------
#  720  Telefon vs. tablet. Samme tal som i oplaegget fra konferencen, og
#       det falder midt i den klynge (704-740), apperne selv havde.
# 1024  Tablet vs. desktop. Stod allerede i build_helpers.py, er den
#       klassiske tablet-landskabsbredde, og den ligger oeverst i den
#       anden klynge (996-1024). Klyngen bliver dermed til EET tal.
# 1600  Desktop vs. bredt. Den er ikke pyntetal: Equipment-listen har syv
#       kolonner og knap 540 px faste bredder, saa den kan foerst staa ved
#       siden af formularen her. Se build_domain.HALF_W.
#
# Ingen tier flytter sig mere end 28 px i forhold til i dag.
# ---------------------------------------------------------------------------
BREAKPOINTS = [
    ("Mobile",  0),
    ("Tablet",  720),
    ("Desktop", 1024),
    ("Wide",    1600),
]

CONTEXT = "LayoutContext"
RANK = "LayoutRank"

_NAMES = [n for n, _ in BREAKPOINTS]
_RANK = {n: i + 1 for i, (n, _) in enumerate(BREAKPOINTS)}
_MIN = dict(BREAKPOINTS)


def _check(name):
    if name not in _RANK:
        raise KeyError("Ukendt layout-tier: %r\nKendte: %s"
                       % (name, ", ".join(_NAMES)))
    return name


def min_width(name):
    """Den mindste App.Width, tieren gaelder fra. Bruges af check_layout til
    at proeve netop de bredder, hvor noget skifter."""
    return _MIN[_check(name)]


def test_widths():
    """De skaermbredder, layout-tjekket skal proeve.

    HVER GRAENSE OG DEN PIXEL LIGE UNDER DEN. Braekpunkter er praecis dér,
    layoutfejl bor - en container, der er hoej nok paa 1024 og 12 px for
    lav paa 1023, ses ikke af en haandplukket liste, der springer fra 900
    til 1024.

    Plus et par almindelige skaermbredder, saa listen ogsaa daekker det,
    brugerne faktisk sidder med."""
    out = set([420, 1366, 1920])
    for _, w in BREAKPOINTS:
        if w:
            out.add(w - 1)
            out.add(w)
    return sorted(out)


def tier_for(width):
    """Hvilken tier en given App.Width lander i. Python-siden af
    LayoutContext - check_layout bruger den til at indsaette den rigtige
    vaerdi, foer den regner paa et hoejdeudtryk."""
    name = _NAMES[0]
    for n, w in BREAKPOINTS:
        if width >= w:
            name = n
    return name


def rank_for(width):
    return _RANK[tier_for(width)]



# ---------------------------------------------------------------------------
# RAMMEN - den plads, indholdet FAKTISK har
#
# Alle fire skaerme har samme ramme (build_helpers.app_frame):
#
#     con<X>Root     lodret, Parent.Width x Parent.Height, scroller IKKE
#       con<X>Header   fast hoejde - bjaelken. Scroller aldrig vaek, og
#                      dens hoejde afhaenger kun af App.Width.
#       con<X>Body     FillPortions = 1, LayoutOverflowY = Scroll. Kortene
#                      staar direkte i den. INGEN hoejde summeres.
#
# SHELL_W er den bredde, alle builderne regner med. Den SKAL vaere en
# NEDRE graense for det, platformen giver - aldrig et gaet paa det praecise
# tal. Er den bare een pixel for stor, bliver en raekke, der er regnet til
# at fylde SHELL_W, for bred, dens sidste barn ombryder til en linje, som
# hoejden ikke har plads til, og barnet klippes vaek. Det var praecis
# bjaelkerne og knapperne, der forsvandt.
#
# Og det var "hit and miss", fordi scrollbaren er det: paa Windows tager
# den ~17 px af bredden, paa en Mac ligger den oven paa indholdet og koster
# ingenting. Den samme skaerm var hel paa een maskine og klippet paa den
# anden.
#
# Derfor regnes scrollbaren ALTID med, og der laegges FIT_SLACK oveni:
#
#     body:    PAGE_PAD_L + PAGE_PAD_R + SCROLLBAR_W + FIT_SLACK = SHELL_INSET
#     header:  PAGE_PAD_L + (PAGE_PAD_R + SCROLLBAR_W) + FIT_SLACK = SHELL_INSET
#
# Headeren scroller ikke, men faar scrollbarens bredde som hoejre-padding,
# saa dens hoejre kant flugter med kortenes, og SHELL_W er sand begge
# steder. Den faktiske bredde er altsaa ALTID >= SHELL_W + FIT_SLACK.
# layout-tjekket (regel 4c og 23) efterregner det.
# ---------------------------------------------------------------------------
PAGE_PAD_L = 24
PAGE_PAD_R = 16
# Bredere end de 17 px, Windows' klassiske scrollbar fylder i Edge og
# Chrome. Et par pixels for meget koster intet; een for lidt klipper.
SCROLLBAR_W = 18
# GALLERIETS RESERVE
#
# En gallerirakkes bredde bestemmer Studio SELV. Aflaest i egenskabs-
# panelet stod der foerst 320 (et fald-tilbage-tal) og siden Parent.Width -
# aldrig det udtryk, builderen skrev. Rakken er altsaa saa bred, som
# galleriet giver den, og vores tal er kun et BUDGET for cellerne.
#
# Er budgettet bare nogle faa pixels for stort, ligger den sidste celle
# uden for rakken - og siden rakken skjuler sit overloeb, forsvinder den i
# stedet for at blive tegnet udenfor. Det var knapperne i listen, anden
# gang.
#
# Budgettet skal derfor vaere en NEDRE graense med luft. 40 px er en
# kolonnebredde mindre til beskrivelsen og kan ikke vaeltes af en kant, en
# scrollbar der alligevel kom, eller en afrunding.
GALLERY_RESERVE = 40

# Luft, saa ingen raekke nogensinde er regnet til at passe PAA pixlen.
# Afrunding af broekdele og en kant paa 1 px maa ikke kunne vaelte den.
FIT_SLACK = 6
SHELL_INSET = PAGE_PAD_L + PAGE_PAD_R + SCROLLBAR_W + FIT_SLACK
SHELL_W = "(App.Width - %d)" % SHELL_INSET

# Top og bund. Bunden i kroppen er stor nok til, at det sidste kort ikke
# ligger klos op ad kanten, naar man har scrollet helt ned.
HEADER_PAD_T = 14
HEADER_PAD_B = 10
BODY_PAD_T = 16
BODY_PAD_B = 40

assert SHELL_INSET == 64, (
    "SHELL_INSET er %d. Tallet indgaar i alle breakpoint-beregninger i de "
    "fire apps og i docs/27 - flyt det kun med vilje." % SHELL_INSET)

# ---------------------------------------------------------------------------
# Udtryk, builderne skriver
# ---------------------------------------------------------------------------
def below(name):
    """Smallere end denne tier. below("Desktop") -> LayoutRank < 3."""
    return "%s < %d" % (RANK, _RANK[_check(name)])


def at_least(name):
    """Denne tier eller bredere."""
    return "%s >= %d" % (RANK, _RANK[_check(name)])


def tier_is(name):
    """Praecis denne tier. Laeses bedst i Studio, men kan sjaeldent bruges:
    de fleste beslutninger er "smallere end X", ikke "praecis X"."""
    return '%s = "%s"' % (CONTEXT, _check(name))


def if_below(name, narrow, wide):
    """If(smallere end tier, narrow, wide) - det moenster, naesten alle
    braekpunkter i repoet bruger."""
    return "If(%s, %s, %s)" % (below(name), narrow, wide)


# ---------------------------------------------------------------------------
# Container-graenser
#
# De hoerer IKKE til en enhedsklasse, men de hoerer til eet sted, saa de
# kan genkendes som det, de er.
# ---------------------------------------------------------------------------
# Den ene containergraense, der er faelles for alle fire apps: under den
# kan to kolonner ikke staa ved siden af hinanden og laeses. Den maales mod
# CONTAINERENS bredde, ikke mod skaermens - et 600 px kort skal stable sine
# felter, ogsaa i et 1920 px vindue.
TWO_COL_MIN = 640


def fits(container_w, needs, narrow, wide):
    """If(containeren er for smal til 'needs', narrow, wide).

    'needs' er den plads, indholdet FAKTISK fylder - udregnet, ikke
    skrevet. Det er hele pointen: topbjaelken havde 900 skrevet i sig,
    mens dens hoejreside fyldte 440. Da hoejresiden voksede til 542, fulgte
    de 900 ikke med.
    """
    return "If((%s) < %s, %s, %s)" % (container_w, needs, narrow, wide)


# ---------------------------------------------------------------------------
# Den navngivne formel
# ---------------------------------------------------------------------------
def _ladder(value_for):
    """If-kaeden, nedefra og op. Power Fx' If tager vilkaarligt mange
    betingelse/vaerdi-par, saa den kan skrives fladt."""
    parts = []
    for name, w in reversed(BREAKPOINTS):
        if w:
            parts.append("    App.Width >= %d, %s," % (w, value_for(name)))
    parts.append("    %s" % value_for(BREAKPOINTS[0][0]))
    return "If(\n" + "\n".join(parts) + "\n)"


def formula():
    """De to navngivne formler til App.Formulas.

    De staar sammen med C (designtokens) og udgoer tilsammen det, der
    afgoer, hvordan appen ser ud: farve og form, begge steder eet sted.
    """
    return (
        "// LAYOUTTOKENS. Genereret af tools/layout_tokens.py - ret ikke her.\n"
        "//\n"
        "// LayoutContext er den, man kan LAESE. LayoutRank er den, man kan\n"
        "// SAMMENLIGNE med: \"desktop eller bredere\" er LayoutRank >= 3.\n"
        "// Braekpunkterne staar eet sted for alle fire apps.\n"
        "%s = %s;\n\n"
        "%s = %s;" % (CONTEXT, _ladder(lambda n: '"%s"' % n),
                      RANK, _ladder(lambda n: str(_RANK[n])))
    )


if __name__ == "__main__":
    print(formula())
    print()
    print("test_widths():", test_widths())
    for w in test_widths():
        print("   %5d -> %-8s rank %d" % (w, tier_for(w), rank_for(w)))
