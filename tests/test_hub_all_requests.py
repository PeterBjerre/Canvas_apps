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


def test_tab_says_all_requests_and_keeps_the_queue_logic():
    """Issue #303: My requests | All requests er faner (ModernTabList), men
    vaerdien bag "All requests" er stadig varMdView = "queue"."""
    b = _block("tabMdFltView")
    assert "Control: ModernTabList@1.0.0" in b
    items = _prop(b, "Items")
    assert '"All requests"' in items and '"My requests"' in items
    assert '"All")' in items or '"All",' in items      # kort trin paa smal tablet
    on = b[b.index("OnChange:"):]
    assert '"All requests", "queue"' in on and '"My requests", "mine"' in on
    assert "Set(varMdView, k)" in on and 'Set(varMdDomain, "")' in on
    assert _prop(b, "Default").startswith('Switch(varMdView, "mine", ')


def test_all_requests_tab_list_shrinks_with_the_filter_row():
    w = _prop(_block("tabMdFltView"), "Width")
    widths = [int(n) for n in re.findall(r"PanelInset\)\) >= \d+, (\d+)", w)]
    widths.append(int(re.search(r", (\d+)\)$", w).group(1)))
    # fuld > kompakt > kort.
    assert widths[0] > widths[1] > widths[2]


def test_mobile_keeps_my_and_all():
    b = _block("tabMdViewM")
    assert "Control: ModernTabList@1.0.0" in b
    assert _prop(b, "Items") == '["My", "All"]'
