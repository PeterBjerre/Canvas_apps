# -*- coding: utf-8 -*-
"""
Kontroltrae-DSL og serialisering til .pa.yaml (Power Apps canvas).

Filen er ordret ens i alle apps i repoet. Retter du her, skal du kopiere
den til de oevrige build-mapper - se .github/skills/canvas-build/SKILL.md.

HOEJDEMODELLEN
--------------
Canvas-containere kan ikke "hugge" deres indhold - en container faar kun den
hoejde, dens Height-formel siger. Den oprindelige kode loeste det ved at lade
hver container summere sine BOERNS .Height:

    conVhpShell.Height = 40 + conVhpHero.Height + 20 + conVhpPlanCard.Height + ...

Det er en cirkelreference. I en AutoLayout-container er det FORAELDREN, der
saetter boernenes stoerrelse (LayoutAlignItems er Stretch som standard, og paa
en container med LayoutWrap = true fjerner platformen LayoutAlignItems helt,
saa Stretch ikke kan slaas fra). Naar forelderen saa laeser barnets .Height,
laeser den sin egen udregning tilbage. Resultatet er enten en formelfejl, der
falder tilbage til IfError-konstanten, eller den kaskade-vaekst hvor
containerne bliver stoerre for hver genberegning.

Loesningen her: ingen Height-formel refererer nogensinde en anden kontrol.
Hoejder beregnes i Python ud fra konstanter, App.Width og CountRows(), og
stack_height()/row_height() taeller selv padding og gaps med, saa de ikke kan
glemmes et enkelt sted.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def _out_dir():
    """App-mappen, skaermen skal skrives i.

    DEN MAA IKKE REGNES UD AF __file__. Her stod "HERE/..", og da filen
    flyttede fra hver app's build-mappe til tools/, blev HERE/.. til
    REPO-RODEN. Alle fire skaerme blev skrevet dér, app-mapperne beholdt
    deres gamle udgaver - og layout-tjekket sagde "OK", fordi det laeste de
    gamle filer. Groent byggeri, ingen aendring, ingen fejlmeddelelse.

    Den rigtige kilde er INDGANGEN: assemble_screen.py ligger altid i
    app'ens egen build-mappe. sys.argv[0] er den fil, der koeres.
    """
    entry = os.path.abspath(sys.argv[0]) if sys.argv and sys.argv[0] else ""
    build = os.path.dirname(entry) if entry else os.getcwd()
    app = os.path.abspath(os.path.join(build, ".."))
    # Et app-mappe HAR en build-mappe. Uden det tjek ville en forkert sti
    # bare skrive filen et tilfaeldigt sted - praecis som den gjorde.
    if not os.path.isdir(os.path.join(app, "build")):
        raise SystemExit(
            "gen_screen: kan ikke finde app-mappen.\n"
            "  indgang: %s\n  udledt:  %s\n"
            "Koer builderen fra app'ens build-mappe:\n"
            "    cd \"<App>/build\" && python3 assemble_screen.py\n"
            "eller brug: python3 tools/build_all.py" % (entry or "(ingen)", app))
    return app


OUT_DIR = _out_dir()

# Designtokens ligger EET sted for hele repoet - ikke i en kopi pr.
# build-mappe som denne fil selv. Farven er det eneste, de fire apps skal
# vaere enige om ned til vaerdien, og en kopi ville netop kunne glide.
#
# tools/ er udenfor app-mappen, og det er med vilje ufarligt her:
# canvas_mcp.stage() kopierer KUN *.pa.yaml over til serveren, saa hverken
# build/ eller tools/ naar nogensinde ud i Studio.
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from design_tokens import ref as _t, TRANSPARENT
from layout_tokens import below, if_below, SHELL_W

# ---------------------------------------------------------------------------
# Farver
#
# Ingen vaerdi staar her. Hvert navn peger paa en DESIGNTOKEN, og tokenens
# vaerdi staar i tools/design_tokens.py - eet sted for alle fire apps.
#
# Det, en builder skriver i en skaerm, er derfor ikke "RGBA(250, 251, 253, 1)"
# men "C.'bg-card'". C er en navngiven formel i App.Formulas, der vaelger
# mellem det lyse og det moerke saet. Derfor skifter hele appen tema uden at
# en eneste kontrol ved, at moerk tilstand findes.
#
# Navnene nedenfor er de GAMLE C_*-navne. De staar i knap 500 kald ude i
# builderne, og at doebe dem om ville vaere en anden aendring end den her.
# ---------------------------------------------------------------------------
C_APP_BG = _t("bg-app")
C_CARD_BG = _t("bg-card")
C_SURFACE = _t("bg-surface")
C_MUTED_BG = _t("bg-muted")
C_CARD_BORDER = _t("border-default")
C_TITLE = _t("text-primary")
C_MUTED = _t("text-muted")
C_REQUIRED = _t("state-error-fg")
C_PRIMARY = _t("color-brand-primary")
C_PRIMARY2 = _t("color-brand-primary-hover")
C_PRIMARY_SOFT = _t("color-brand-primary-soft")
C_WHITE = _t("text-on-primary")
# Tekst paa en DOMAENEFARVE. I lys tilstand er den den samme hvide som
# C_WHITE; i moerk er domaenefarverne lyse, og hvid tekst paa dem gav
# 1,67-2,72:1. Derfor et eget navn - se CONTRAST i design_tokens.py.
C_ON_DOMAIN = _t("text-on-domain")
C_INPUT_BG = _t("input-bg")
C_DISABLED_BG = _t("input-bg-disabled")
C_DIVIDER = _t("border-subtle")
C_MODAL_BG = _t("bg-modal")
C_OVERLAY = _t("overlay")

# Gennemsigtig er IKKE en token: den er den samme i begge temaer, og der
# er ingen beslutning at traeffe om den.
C_TRANSPARENT = TRANSPARENT

# KANT vs. TEKST. C_VALID_FG/C_INVALID_FG er TEKSTfarver (4,5:1).
# C_BORDER_OK/C_BORDER_ERROR er de samme to tilstande som en 1 px KANT
# (3,0:1) - ens i lys tilstand, daempet i moerk. Se BALANCED i
# tools/design_tokens.py for hvorfor de ikke kan vaere eet navn.
C_BORDER_OK = _t("border-ok")
C_BORDER_ERROR = _t("border-error")
C_VALID_FG = _t("state-ok-fg")
C_VALID_BG = _t("state-ok-bg")
C_INVALID_FG = _t("state-error-fg")
C_INVALID_BG = _t("state-error-bg")
C_WARN_FG = _t("state-warn-fg")
C_WARN_BG = _t("state-warn-bg")
C_INFO_FG = _t("state-info-fg")
C_INFO_BG = _t("state-info-bg")
C_NEUTRAL_FG = _t("state-neutral-fg")
C_NEUTRAL_BG = _t("state-neutral-bg")

FONT = "Font.'Segoe UI'"

# Bredden af skaermens indholdsomraade. Den staar i tools/layout_tokens.py
# sammen med rammen, den er regnet af - padding, scrollbar og luft. Alle
# responsive udregninger gaar gennem den, og den er en NEDRE graense for
# det, platformen giver: se RAMMEN i layout_tokens.py for hvorfor det ikke
# maa vaere et gaet paa det praecise tal.

# Bredden af items-skinnen naar de to kort staar side om side.
RAIL_W = 360
SPLIT_GAP = 20
# Bredden af Item Editor-kortet, udtrykt uden at referere nogen kontrol.
#
# Her stod "App.Width < 1000". Det var eet af FIRE braekpunkter mellem 996
# og 1024, spredt over fire filer - heroen stablede ved 996, det her ved
# 1000, hubbens fliser ved 1004 og FillPortions ved 1024. Alle fire stod
# for det samme skift, og ingen af dem var valgt i forhold til de tre
# andre. Nu er de eet tal. Se tools/layout_tokens.py.
EDITOR_W = if_below("Desktop", SHELL_W, f"{SHELL_W} - {RAIL_W} - {SPLIT_GAP}")


# ---------------------------------------------------------------------------
# Tiny control-tree DSL
# ---------------------------------------------------------------------------
class Ctrl:
    # h   = kontrollens hoejde som tal eller Power Fx-udtryk. Forelderen
    #       bruger den til at regne sin egen hoejde ud - den laeses ALDRIG
    #       som .Height i en formel.
    # vis = Visible-udtryk, hvis kontrollen kan vaere skjult. Forelderen
    #       taeller den saa kun med, naar den er synlig.
    __slots__ = ("name", "control", "variant", "props", "children", "h", "_vis")

    def __init__(self, name, control, variant=None, props=None, children=None, h=None, vis=None):
        self.name = name
        self.control = control
        self.variant = variant
        self.props = props or {}
        self.children = children or []
        self.h = h
        self._vis = None
        if vis is not None:
            self.vis = vis

    # vis skrives IGENNEM til Visible-egenskaben.
    #
    # Foer var vis kun hoejde-algebraens felt, saa "ctrl.vis = udtryk" efter
    # konstruktionen fik forelderen til at regne rigtigt, men skrev ingen
    # Visible i YAML'en - kontrollen blev bare ved med at vaere synlig. Det
    # ramte handlingsknapperne i pakkematricen, og fejlen var usynlig i
    # builderen. Nu kan de to ikke komme ud af trit.
    @property
    def vis(self):
        return self._vis

    @vis.setter
    def vis(self, expr):
        self._vis = expr
        if expr is None:
            self.props.pop("Visible", None)
        else:
            self.props["Visible"] = expr


# ---------------------------------------------------------------------------
# Hoejde-algebra
# ---------------------------------------------------------------------------
def _is_num(v):
    return isinstance(v, (int, float))


def stack_height(children, gap, pad_t=0, pad_b=0):
    """Hoejden af en lodret AutoLayout-container.

    Taeller padding og gaps med, saa de ikke kan glemmes. Boern med en
    vis-betingelse bidrager kun naar de er synlige - AutoLayout udelader
    skjulte boern fra baade stakken og gaps.

    Foerste barn skal altid vaere synligt (i praksis altid en sektions-
    overskrift), saa gap-regnskabet gaar op.
    """
    const = pad_t + pad_b
    parts = []
    for i, c in enumerate(children):
        h = 0 if c.h is None else c.h
        g = 0 if i == 0 else gap
        if c.vis:
            parts.append(f"If({c.vis}, {g} + ({h}), 0)")
        elif _is_num(h):
            const += h + g
        else:
            parts.append(f"({h})" if g == 0 else f"{g} + ({h})")
    expr = str(int(const)) if float(const).is_integer() else str(const)
    for p in parts:
        expr += " + " + p
    return expr


def row_height(children, pad_t=0, pad_b=0, rows=1, gap=0):
    """Hoejden af en vandret AutoLayout-container: det hoejeste barn.

    rows > 1 bruges naar raekken ombryder (LayoutWrap) og skal have plads
    til flere linjer.
    """
    hs = [(0 if c.h is None else c.h) for c in children] or [0]
    if all(_is_num(h) for h in hs):
        base = max(hs)
        return int(pad_t + pad_b + base * rows + gap * (rows - 1))
    terms = ", ".join(f"({h})" for h in hs)
    base = f"Max({terms})" if len(hs) > 1 else terms
    return f"{pad_t + pad_b} + ({base}) * {rows} + {gap * (rows - 1)}"


def render(node, item_indent):
    pad = " " * item_indent
    lines = [f"{pad}- {node.name}:"]
    body_indent = item_indent + 4
    bpad = " " * body_indent
    lines.append(f"{bpad}Control: {node.control}")
    if node.variant:
        lines.append(f"{bpad}Variant: {node.variant}")
    if node.props:
        lines.append(f"{bpad}Properties:")
        prop_indent = body_indent + 2
        ppad = " " * prop_indent
        content_indent = prop_indent + 4
        cpad = " " * content_indent
        for key in sorted(node.props.keys()):
            val = node.props[key]
            if val is None:
                continue
            val = str(val)
            lines.append(f"{ppad}{key}: |-")
            first = True
            for raw_line in val.split("\n"):
                if first:
                    lines.append(f"{cpad}={raw_line}")
                    first = False
                else:
                    lines.append(f"{cpad}{raw_line}")
    if node.children:
        lines.append(f"{bpad}Children:")
        child_indent = body_indent + 2
        for child in node.children:
            lines.extend(render(child, child_indent))
    return lines


def render_screen(screen_name, screen_props, children):
    lines = ["Screens:", f"  {screen_name}:", "    Properties:"]
    ppad = " " * 6
    cpad = " " * 10
    for key in sorted(screen_props.keys()):
        val = str(screen_props[key])
        lines.append(f"{ppad}{key}: |-")
        first = True
        for raw_line in val.split("\n"):
            if first:
                lines.append(f"{cpad}={raw_line}")
                first = False
            else:
                lines.append(f"{cpad}{raw_line}")
    lines.append("    Children:")
    for child in children:
        lines.extend(render(child, 6))
    return "\n".join(lines) + "\n"


# Denne fil er et bibliotek. Den kan koeres, men goer ingenting - og det
# kostede en hel verifikationsrunde, hvor "python3 gen_screen.py" saa ud
# til at bygge skaermen igen uden at roere den. Nu siger den fra.
if __name__ == "__main__":
    import sys
    sys.exit("gen_screen.py er et bibliotek og bygger ingenting.\n"
             "Byg skaermen med: python3 assemble_screen.py\n"
             "Eller hele kaeden med: python3 tools/build_all.py")
