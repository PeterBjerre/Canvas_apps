# -*- coding: utf-8 -*-
"""
Issue #524: hierarkiets streger i SAP Objects-popuppen.

Planens streg skal vaere EEN sammenhaengende linje ned til alle dens items,
hvert item knaekker af fra den, en opgaveliste haenger kun paa sit eget
item, og ingen streg fortsaetter forbi det sidste barn.

Testen laeser stregernes X/Y/Height/Visible fra den genererede YAML,
regner dem ud for et antal raekkefoelger (med flagene Kids/More/Pass som
formlen i open_fx) og kontrollerer stregerne i absolutte koordinater.

    python3 -m pytest tests/test_sap_tree_524.py
"""
import os
import re
import sys

from conftest import ROOT

for p in (os.path.join(ROOT, "tools"), os.path.join(ROOT, "Masterdata Hub", "build")):
    if p not in sys.path:
        sys.path.insert(0, p)
import sap_objects as so  # noqa: E402
from test_hub_sap_objects import _block, _prop, _yaml  # noqa: E402

LINES = ("rctMdSapTreePass", "rctMdSapTreeV", "rctMdSapGuide")


def _flags(lvls):
    """Python-spejl af flagene i sap_objects._collect."""
    out = []
    for i, lvl in enumerate(lvls):
        rest = lvls[i + 1:]
        first = lambda cond: next((x for x in rest if cond(x)), -1)  # noqa: E731
        out.append({
            "Lvl": lvl,
            "Kids": (rest[0] if rest else -1) == lvl + 1,
            "More": first(lambda x: x <= lvl) == lvl,
            "Pass": lvl > 1 and first(lambda x: x <= lvl - 1) == lvl - 1,
        })
    return out


def If(c, a, b):  # noqa: N802 - Power Fx-navnet
    return a if c else b


def _ev(expr, row):
    py = expr.replace("&&", " and ")
    for k in ("Lvl", "Kids", "More", "Pass"):
        py = py.replace(f"ThisItem.{k}", repr(row[k]))
    return eval(py, {"If": If})


def _segments(lvls):
    """{x: [(y0, y1), ...]} for alle synlige lodrette streger."""
    pop = _block(_yaml(), "conMdSapBackdrop")
    props = {n: _block(pop, n) + "\n" for n in LINES}
    segs = {}
    for i, row in enumerate(_flags(lvls)):
        off = i * so.ROW_H
        for name, b in props.items():
            vis = _prop(b, "Visible")
            if vis is not None and not _ev(vis, row):
                continue
            x = _ev(_prop(b, "X"), row)
            y = _ev(_prop(b, "Y"), row)
            h = _ev(_prop(b, "Height"), row)
            segs.setdefault(x, []).append((off + y, off + y + h, name, i))
    return segs


def _covered(segs, y0, y1):
    """Daekker segmenterne [y0, y1] uden huller?"""
    y = y0
    for a, b, *_ in sorted(segs):
        if a <= y < b or a == y:
            y = max(y, b)
    return y >= y1


KNEE = so.BAR_Y + so.BAR_H // 2
BAR_BOTTOM = so.BAR_Y + so.BAR_H

CASES = [
    [0, 1, 2, 1, 2],          # issuet: to items med hver sin opgaveliste
    [0, 1, 2, 1, 2, 1, 2],    # tre items
    [0, 1, 1, 2, 1],          # items med og uden opgaveliste
    [0, 1, 2],                # eet item
    [0, 1],                   # eet item uden opgaveliste
    [0],                      # kun planen
    [0, 0, 0],                # flade domaener (Material, Equipment ...)
]


def _parent(lvls, i):
    return max(j for j in range(i) if lvls[j] == lvls[i] - 1)


def test_parent_line_is_continuous_to_every_child_and_stops_at_the_last():
    for lvls in CASES:
        segs = _segments(lvls)
        for p, plvl in enumerate(lvls):
            kids = [i for i in range(p + 1, len(lvls)) if lvls[i] == plvl + 1
                    and _parent(lvls, i) == p]
            x = plvl * so.INDENT + so.GUIDE
            at_x = segs.get(x, [])
            if not kids:
                continue
            start = p * so.ROW_H + BAR_BOTTOM
            last = kids[-1] * so.ROW_H + KNEE
            for k in kids:
                assert _covered(at_x, start, k * so.ROW_H + KNEE), (lvls, p, k)
            # Ingen hale: intet paa foraelderens x efter det sidste barns
            # knaek, foer et nyt objekt paa samme niveau begynder.
            nxt = next((j for j in range(p + 1, len(lvls)) if lvls[j] <= plvl), len(lvls))
            end = nxt * so.ROW_H
            tail = [s for s in at_x if s[1] > last and s[0] < end and s[3] > p]
            assert not tail, (lvls, p, tail)


def test_task_list_hangs_only_on_its_own_item():
    # Opgavelisten under item 1 maa ikke forbindes med item 2: dens knaek
    # sidder paa item 1's streg, og item 1's streg slutter dér.
    lvls = [0, 1, 2, 1, 2]
    segs = _segments(lvls)
    item_x = 1 * so.INDENT + so.GUIDE
    first_task_knee = 2 * so.ROW_H + KNEE
    assert not [s for s in segs.get(item_x, []) if s[0] < 3 * so.ROW_H and s[1] > first_task_knee]
    # Planens streg loeber igennem opgavelistens raekke (Pass).
    plan_x = so.GUIDE
    assert _covered(segs[plan_x], 2 * so.ROW_H, 3 * so.ROW_H)
    # ... men ikke under den sidste opgaveliste.
    assert not [s for s in segs[plan_x] if s[3] == 4]


def test_flags_are_computed_after_rows_without_numbers_drop_out():
    fx = so.open_fx()
    for line in ("Kids: Coalesce(First(rest).Lvl, -1) = cur.Lvl + 1",
                 "More: Coalesce(First(Filter(rest, Lvl <= cur.Lvl)).Lvl, -1) = cur.Lvl",
                 "Pass: cur.Lvl > 1 && Coalesce(First(Filter(rest, Lvl <= cur.Lvl - 1)).Lvl, -1)"
                 " = cur.Lvl - 1"):
        # Een gang pr. domaene - alle raekker har samme felter.
        assert fx.count(line) == len(so._domain_rows()), line
    plan = so._domain_rows()["MaintenancePlan"]
    assert plan.index("!IsBlank(No)") < plan.index("ClearCollect(")


def test_lines_follow_the_template_height():
    pop = _block(_yaml(), "conMdSapBackdrop")
    src = open(os.path.join(ROOT, "Masterdata Hub", "build", "sap_objects.py"),
               encoding="utf-8").read()
    assert src.count("Parent.TemplateHeight") >= 3
    # gen_screen skriver skabelonens hoejde ud som tal.
    assert re.search(rf"If\(ThisItem\.More, \({so.ROW_H}\), {KNEE}\)",
                     _prop(_block(pop, "rctMdSapTreeV") + "\n", "Height"))
