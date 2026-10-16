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
    h = s[s.index("Height:"):s.index("Height:") + 300]
    assert "RoundUp(Len(Self.Text)" in h
    row = _block(y, "conVhpPlanFoldRow", 1200)
    assert "Len(txtVhpPlanFoldSummary.Text)" in row
    assert "LayoutDirection.Vertical" in row


def test_show_stays_in_the_folded_header():
    y, _ = _summary()
    top = _block(y, "conVhpPlanFoldTop", 20000)
    assert "- btnVhpPlanShow:" in top
    show = _block(y, "btnVhpPlanShow", 3000)
    assert '"Show the plan header fields"' in show
    assert "Set(varVhpPlanShow, !IfError(varVhpPlanShow, false))" in show
