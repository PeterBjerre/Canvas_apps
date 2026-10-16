"""Teams-ikoner til BIO SAP, afledt af BIO SAP App/app-icon.png (issue #275).

Hvorfor: app-icon.png er en lyseblaa, AFRUNDET flise (#DEF0FC) med en 1 px
lys kant og gennemsigtige hjoerner. Power Apps viser den paa en hvid
baggrund, saa den ser rigtig ud dér. Teams kraever derimod, at farveikonet
er et skarpt kvadrat paa en "solid or fully transparent square background",
og Teams afrunder selv hjoernerne. Alt gennemsigtigt i ikonet fyldes med
appens baggrundsfarve (accentColor i Teams-pakken; i Power Apps er det
"Background fill", som staar til standard-blaa RGBA(0,176,240,1) i de
andre apps). Derfor faar ikonet en blaa kant/blaa hjoerner i Teams.

Scriptet laver to filer i "BIO SAP App/teams-icon/":

  * color.png   192x192, helt uigennemsigtigt kvadrat i flisens farve
                #DEF0FC med det samme symbol og de samme farver. Ingen
                afrundede hjoerner, ingen kant og ingen gennemsigtighed,
                saa der er intet, Teams kan fylde med blaa.
  * outline.png 32x32, hvidt symbol paa gennemsigtig baggrund uden ekstra
                luft (Teams' krav til outline-ikonet i app-baren).

app-icon.png roeres ikke (den bruges ogsaa som logo i sidebaren via
tools/side_nav.py). Koer igen, hvis app-icon.png aendres:

    python3 tools/teams_icons.py

Kraever Pillow (pip install pillow).
"""
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "BIO SAP App", "app-icon.png")
OUT_DIR = os.path.join(ROOT, "BIO SAP App", "teams-icon")
COLOR_FILE = os.path.join(OUT_DIR, "color.png")
OUTLINE_FILE = os.path.join(OUT_DIR, "outline.png")

# Flisens farve i app-icon.png. Bruges ogsaa som anbefalet "Background
# fill"/accentColor (se docs/42-teams-app-ikon.md). Det er app-ikonets egen
# farve, ikke en temafarve, saa den hoerer ikke i design_tokens.py.
TILE = (222, 240, 252)
COLOR_PX = 192
OUTLINE_PX = 32
# Kun pixels med mindst denne afstand (stoerste kanal) fra flisefarven
# hoerer til symbolet. Flisens lyse kant ligger under 25.
SYMBOL_DIFF = 40
# Fuld daekning i outline-ikonet ved denne afstand (symbolets graa streg
# ligger ca. 130 fra flisen; de farvede prikker endnu laengere).
OUTLINE_FULL = 120


def _diff(p):
    return max(abs(p[0] - TILE[0]), abs(p[1] - TILE[1]), abs(p[2] - TILE[2]))


def symbol_bbox(src):
    """Kasse om symbolet (pixels tydeligt forskellige fra flisen)."""
    w, h = src.size
    xs, ys = [], []
    for y in range(h):
        for x in range(w):
            p = src.getpixel((x, y))
            if p[3] == 255 and _diff(p) >= SYMBOL_DIFF:
                xs.append(x)
                ys.append(y)
    if not xs:
        raise SystemExit("Fandt intet symbol i " + SRC)
    return min(xs), min(ys), max(xs) + 1, max(ys) + 1


def _inside(src, box):
    """Symbolets kasse ligger helt inde i flisen (uigennemsigtig)."""
    l, t, r, b = box
    return all(src.getpixel((x, y))[3] == 255
               for x in range(l, r) for y in range(t, b))


def make_color(src):
    """Kvadrat i flisefarven med symbolet kopieret pixel for pixel.

    Symbolets kantudglatning er allerede blandet mod flisefarven, saa et
    udsnit omkring symbolet passer praecis ind paa en ensfarvet flade.
    Hjoernerne og den lyse kant kommer ikke med."""
    l, t, r, b = symbol_bbox(src)
    pad = 4
    box = (max(l - pad, 0), max(t - pad, 0),
           min(r + pad, src.width), min(b + pad, src.height))
    if not _inside(src, box):
        raise SystemExit("Symbolet naar ud til flisens kant i " + SRC)
    big = Image.new("RGB", src.size, TILE)
    big.paste(src.crop(box).convert("RGB"), box[:2])
    return big.resize((COLOR_PX, COLOR_PX), Image.LANCZOS)


def make_outline(src):
    """Hvidt symbol paa gennemsigtig baggrund, beskaaret til symbolet."""
    l, t, r, b = symbol_bbox(src)
    alpha = Image.new("L", src.size, 0)
    for y in range(t, b):
        for x in range(l, r):
            p = src.getpixel((x, y))
            a = min(255, round(255 * _diff(p) / OUTLINE_FULL))
            alpha.putpixel((x, y), a)
    alpha = alpha.crop((l, t, r, b))
    side = max(alpha.size)
    sq = Image.new("L", (side, side), 0)
    sq.paste(alpha, ((side - alpha.width) // 2, (side - alpha.height) // 2))
    sq = sq.resize((OUTLINE_PX, OUTLINE_PX), Image.LANCZOS)
    out = Image.new("RGBA", (OUTLINE_PX, OUTLINE_PX), (255, 255, 255, 0))
    out.putalpha(sq)
    return out


def render():
    src = Image.open(SRC).convert("RGBA")
    return make_color(src), make_outline(src)


def main():
    color, outline = render()
    os.makedirs(OUT_DIR, exist_ok=True)
    color.save(COLOR_FILE, optimize=True)
    outline.save(OUTLINE_FILE, optimize=True)
    for f in (COLOR_FILE, OUTLINE_FILE):
        print("skrev", os.path.relpath(f, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
