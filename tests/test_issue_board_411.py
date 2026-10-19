"""Issue #411: kommentarfeltet i Activity med et kompakt send-ikon inden i
feltet, samme bredde som resten af fanen og mindre luft."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for d in ("tools", os.path.join("Issue Board", "build")):
    p = os.path.join(ROOT, d)
    if p not in sys.path:
        sys.path.insert(0, p)


def _walk(ctrls):
    for c in ctrls:
        yield c
        yield from _walk(c.children or [])


def _ctrls():
    import ib_parts as P
    return P, {c.name: c for c in _walk(P.build_detail())}


def test_field_and_send_icon_share_one_container():
    P, c = _ctrls()
    box = c["conIbCommentBox"]
    assert box.variant == "ManualLayout"
    assert [k.name for k in box.children] == ["inpIbComment", "btnIbPost", "spnIbPosting"]
    # Ingen egne bredder: alt foelger Activity-fanens bredde.
    assert box.props["Width"] == "Parent.Width"
    assert c["inpIbComment"].props["Width"] == "Parent.Width"
    assert c["conIbComposer"].props["Width"] == "Parent.Width"
    # Ikonet nederst til hoejre, og teksten kan ikke loebe ind under det.
    post = c["btnIbPost"]
    assert post.props["Layout"] == "ButtonLayout.IconOnly"
    assert post.props["Icon"] == '"Send"'
    assert post.props["X"].startswith("Parent.Width - Self.Width")
    assert post.props["Y"].startswith("Parent.Height - Self.Height")
    assert c["inpIbComment"].props["PaddingRight"] == f"{post.props['Width']} + {2 * P.SEND_INSET}"
    # Teksten i feltet flugter med teksten i kommentarerne.
    assert c["inpIbComment"].props["PaddingLeft"] == str(P.ACT_ROW_PAD)


def test_composer_order_and_spacing():
    P, c = _ctrls()
    comp = c["conIbComposer"]
    assert [k.name for k in comp.children] == ["conIbCommentBox", "chkIbInternal", "txtIbCommentHint"]
    assert comp.props["LayoutGap"] == "4"
    assert c["conIbDetActivity"].props["LayoutGap"] == "8"
    # Feltet forsvinder ikke mere, mens der sendes.
    assert comp.props["Visible"] == "IbCanComment"
    assert "conIbPosting" not in c and "txtIbPostingNote" not in c


def test_send_icon_state_follows_the_post():
    P, c = _ctrls()
    post, spin = c["btnIbPost"], c["spnIbPosting"]
    assert post.props["DisplayMode"] == ("If(IsBlank(Trim(inpIbComment.Text)) || varIbPosting, "
                                         "DisplayMode.Disabled, DisplayMode.Edit)")
    assert post.props["OnSelect"] == P.POST
    # Hjulet i ikonets sted, kun mens kaldet koerer for denne sag.
    assert spin.props["Visible"] == P.POSTING_HERE
    assert post.props["Visible"] == f"!({P.POSTING_HERE})"
    assert spin.props["X"] == post.props["X"] and spin.props["Y"] == post.props["Y"]
    # Feltet er laast, mens der sendes; teksten bevares ved fejl.
    assert P.POSTING_HERE in c["inpIbComment"].props["DisplayMode"]
    assert P.POST_FAILED_HERE in c["inpIbComment"].props["Default"]
    assert c["btnIbPostRetry"].props["OnSelect"] == P.POST
