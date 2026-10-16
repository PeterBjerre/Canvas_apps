# -*- coding: utf-8 -*-
"""Issue #276: "Department" hedder "All requests" i hubbens skifter paa
desktop og tablet. Mobilen beholder "My" | "All", og logikken
(varMdView = "queue") er uaendret."""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCREEN = os.path.join(ROOT, "BIO SAP App", "ScreenMdHub.pa.yaml")


def _block(name, n=6000):
    y = open(SCREEN, encoding="utf-8").read()
    i = y.index(f"- {name}:")
    j = y.find("\n" + " " * (len(y[:i]) - len(y[:i].rstrip(" ")) ) + "- ", i + 1)
    return y[i:j if 0 < j < i + n else i + n]


def _prop(block, prop):
    m = re.search(rf"\n\s+{prop}: \|-\n\s+=(.*)", block)
    return m.group(1)


def test_department_is_gone_from_the_hub():
    y = open(SCREEN, encoding="utf-8").read()
    assert '"Department"' not in y
    assert '"Dept."' not in y


def test_segment_says_all_requests_and_keeps_the_queue_logic():
    b = _block("conMdFltViewDept")
    text = _prop(b, "Text")
    assert '"All requests"' in text
    assert '"All")' in text or '"All",' in text      # kort trin paa smal tablet
    assert 'varMdView = "queue"' in _prop(b, "Appearance")
    assert 'Set(varMdView, "queue")' in _prop(b, "OnSelect")
    assert '"View: All requests"' in _prop(b, "AccessibleLabel")
    # "My requests" er uaendret.
    assert '"My requests"' in _prop(_block("conMdFltViewMine"), "Text")


def test_all_requests_segment_is_at_least_as_wide_as_my_requests():
    def widths(name):
        return [int(n) for n in re.findall(r", (\d+)[,)]", _prop(_block(name), "Width"))]
    mine, alls = widths("conMdFltViewMine"), widths("conMdFltViewDept")
    # fuld og kompakt: "All requests" er en anelse bredere end "My requests".
    assert alls[0] >= mine[0] and alls[1] >= mine[1]


def test_mobile_keeps_my_and_all():
    assert _prop(_block("btnMdViewMineM"), "Text") == '"My"'
    assert _prop(_block("btnMdViewAllM"), "Text") == '"All"'
