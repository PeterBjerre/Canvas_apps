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
    row = _block(y, "conVhpPlanFoldRow", 1200)
    assert "Len(txtVhpPlanFoldSummary.Text)" in row
    assert "LayoutDirection.Vertical" in row


def test_show_stays_in_the_folded_header():
    y, _ = _summary()
    show = _block(y, "btnVhpPlanShow", 3000)
    assert '"Show the plan header fields"' in show
    assert "Set(varVhpPlanShow, !IfError(varVhpPlanShow, false))" in show


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


def test_show_sits_right_of_the_summary_not_in_the_title_row():
    """Issue #292: Show (med chevron) staar hoejrestillet i samme raekke som
    resumeet, lodret centreret - titelraekken er ikon, titel og planens
    samlede omkostning (Peter 2026-10-19)."""
    y, _ = _summary()
    top = _block(y, "conVhpPlanFoldTop", 20000)
    assert _children(top) == ["icoVhpPlanFoldStatus", "txtVhpPlanFoldTitle", "bdgVhpPlanFoldCost"]
    body = _block(y, "conVhpPlanFoldBody", 40000)
    assert _children(body) == ["txtVhpPlanFoldSummary", "btnVhpPlanShow"]
    head = body[:body.index("Children:")]
    assert "LayoutDirection.Horizontal" in head
    assert "LayoutAlignItems.Center" in head
    assert "LayoutJustifyContent.SpaceBetween" in head
    row = _block(y, "conVhpPlanFoldRow", 40000)
    assert _children(row) == ["conVhpPlanFoldTop", "conVhpPlanFoldBody"]
    show = _block(y, "btnVhpPlanShow", 3000)
    assert "AlignInContainer.Center" in show


def test_summary_width_and_height_leave_room_for_show():
    """Resumeet er kortets bredde minus Show (96) og gap (8), og hoejden
    regnes af den smallere bredde. Raekken er mindst knappens hoejde - ingen
    ekstra raekke. Paa en telefon falder indrykningen bort."""
    y, s = _summary()
    w = s[s.index(" Width:"):s.index(" Width:") + 600]
    assert "- 96 - 8)" in w
    h = s[s.index("Height:"):s.index("Height:") + 900]
    assert "- 96 - 8) - If(LayoutRank < 2, 0, 30))" in h
    pad = s[s.index("PaddingLeft:"):s.index("PaddingLeft:") + 160]
    assert "If(LayoutRank < 2, 0, 30)" in pad
    body = _block(y, "conVhpPlanFoldBody", 2000)
    bh = body[body.index("Height:"):body.index("Height:") + 1200]
    # Issue #508: Show er 44 hoej paa en telefon, 36 som foer ellers.
    assert "(If(LayoutRank < 2, 44, 36)))" in bh and "Len(txtVhpPlanFoldSummary.Text)" in bh


def _prop(block, prop):
    """Vaerdien af en egenskab i en kontrol-blok (foerste forekomst)."""
    i = block.index(f" {prop}: |-\n")
    return block[i:].splitlines()[1].strip()


def test_fold_cost_badge_is_hidden_without_a_total():
    """Issue #421: Total cost i det foldede planhoved stod som en tom kasse
    over Show. Maerket (bdgVhpPlanFoldCost, PR #424) er nu kun synligt, naar
    planen har en sum over 0, og titlen regner kun med maerkets bredde, naar
    det ses."""
    y, _ = _summary()
    badge = _block(y, "bdgVhpPlanFoldCost", 6000)
    assert _prop(badge, "Visible") == "=IfError(Sum(colVhpOperations, Cost) > 0, false)"
    title = _block(y, "txtVhpPlanFoldTitle", 3000)
    assert "If(IfError(Sum(colVhpOperations, Cost) > 0, false), (" in _prop(title, "Width")
    # Show bliver i resumeets raekke, hoejrestillet - uberoert af maerket.
    body = _block(y, "conVhpPlanFoldBody", 40000)
    assert _children(body) == ["txtVhpPlanFoldSummary", "btnVhpPlanShow"]
    assert "LayoutJustifyContent.SpaceBetween" in body[:body.index("Children:")]
