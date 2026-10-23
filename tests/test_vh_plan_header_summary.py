# -*- coding: utf-8 -*-
"""Det foldede Plan header viser alle otte vaerdier og ombrydes (issue #287)."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenVhPlan.pa.yaml")


def _block(y, name, n=6000):
    i = y.index(f"- {name}:")
    return y[i:i + n]


def _summary():
    y = open(SCREEN, encoding="utf-8").read()
    return y, _block(y, "txtVhpPlanFoldSummary")


def test_the_summary_names_all_eight_fields_in_field_order():
    _, s = _summary()
    text = s[s.index("Text:"):]
    labels = ['"Plan type "', '"Status "', '"Plant "', '"Plan text "',
              '"Sort field "', '"Cycle "', '"Unit "', '"First call "']
    pos = [text.index(lab) for lab in labels]
    assert pos == sorted(pos), pos
    for ctrl in ("drpVhpPlanType.Selected.Value", "drpVhpStatus.Selected.Value",
                 "drpVhpPlant.Selected.Value", "inpVhpPlanText.Text",
                 "drpVhpSortField.Selected.Value", "varVhpPlan.Cycle",
                 "drpVhpUnit.Selected.Value", "dteVhpFirstCall.SelectedDate"):
        assert ctrl in text, ctrl


def test_the_summary_wraps_and_its_height_follows_the_text():
    y, s = _summary()
    assert "Wrap: |-\n" in s and "=true" in s[s.index("Wrap:"):s.index("Wrap:") + 60]
    h = s[s.index("Height:"):s.index("Height:") + 900]
    assert "RoundUp(Len(Self.Text)" in h
    card = _block(y, "conVhpPlanCard", 20000)
    assert "Len(txtVhpPlanFoldSummary.Text)" in card


def _children(block):
    """Navnene paa de direkte boern i en container-blok."""
    lines = block[block.index("Children:"):].splitlines()[1:]
    ind = len(lines[0]) - len(lines[0].lstrip())
    out = []
    for ln in lines:
        if not ln.strip():
            continue
        cur = len(ln) - len(ln.lstrip())
        if cur < ind:
            break
        if cur == ind and ln.lstrip().startswith("- "):
            out.append(ln.strip()[2:].rstrip(":"))
    return out


def test_phone_summary_has_the_full_card_width():
    """Issue #548/#559: paa en telefon staar resumeet paa sin egen linje
    under overskriften i kortets fulde bredde, uden indrykning."""
    y = open(SCREEN, encoding="utf-8").read()
    s = _block(y, "txtVhpPlanFoldSummaryM")
    w = s[s.index(" Width:"):s.index(" Width:") + 600]
    assert "- 96 - 8)" not in w
    pad = s[s.index("PaddingLeft:"):s.index("PaddingLeft:") + 200]
    assert "=0\n" in pad


def _prop(block, prop):
    """Vaerdien af en egenskab i en kontrol-blok (foerste forekomst)."""
    i = block.index(f" {prop}: |-\n")
    return block[i:].splitlines()[1].strip()


def test_cost_badge_is_hidden_without_a_total():
    """Issue #421: Total cost stod som en tom kasse. Maerket er kun synligt,
    naar planen har en sum over 0 - nu i den ene overskrift (issue #548)."""
    y, _ = _summary()
    assert "- bdgVhpPlanFoldCost:" not in y
    badge = _block(y, "bdgVhpPlanHeadCost", 6000)
    assert "IfError(Sum(colVhpOperations, Cost) > 0, false)" in _prop(badge, "Visible")
