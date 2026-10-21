# -*- coding: utf-8 -*-
"""
Issue #507: den valgte vaerdi i den lukkede "Subject or request"-vaelger
staar i samme stoerrelse som soegefeltet i den udfoldede liste (og
formularens felter). Knappen er en ModernButton - Size er i pixels.
Listens valgmuligheder og etiketten er uaendrede.

    python3 -m pytest tests/test_feedback_subject_size_507.py
"""
from test_feedback_message_492 import _screens, _prefix, _props


def test_collapsed_value_matches_the_search_field():
    screens = _screens()
    assert len(screens) >= 8
    for name, doc in screens.items():
        p = _prefix(doc, name)
        btn = _props(doc, f"btn{p}FbSubject")
        find = _props(doc, f"inp{p}FbSubjectFind")
        assert btn["Size"].strip() == "If(LayoutRank < 2, 16, 14)", name
        assert btn["Size"].strip() == find["Size"].strip(), name
        assert btn["VerticalAlign"].strip() == "VerticalAlign.Middle", name
        # Valgmulighederne og etiketten er uaendrede.
        assert _props(doc, f"txt{p}FbSubjectRow")["Size"].strip() == "T.body", name
        assert _props(doc, f"txt{p}FbSubjectLabel")["Size"].strip() == "T.small", name
