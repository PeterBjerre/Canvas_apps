# -*- coding: utf-8 -*-
"""
Issue #506: ingen unoedig indre scroll i Task list and operations.

Et lodret galleri med TemplatePadding p fylder n raekker
p + n x (TemplateSize + p). Var hoejden kun n x (TemplateSize + p), var
indholdet p px hoejere end galleriet, og musehjulet rullede galleriet et
lille hak i stedet for siden. Galleriernes hoejde skal derfor vaere mindst
deres indhold - og ikke mere end een raekke ekstra (de scroller aldrig).

    python3 -m pytest tests/test_issue_506_ops_scroll.py
"""
import os
import re

import pytest

from conftest import ROOT

VH = os.path.join(ROOT, "BIO SAP App", "ScreenVhPlan.pa.yaml")


def _props(text, ctrl):
    m = re.search(r"- %s:\n(.*?)(?=\n\s+- \w+:\n\s+Control:|\Z)" % re.escape(ctrl), text, re.S)
    assert m, ctrl + " mangler"
    out = {}
    for name in ("Height", "TemplatePadding", "TemplateSize"):
        p = re.search(r"\n\s+%s: \|-\n\s+=(.*)" % name, m.group(1))
        assert p, f"{ctrl}.{name} mangler"
        out[name] = p.group(1).strip()
    return out


def _height(expr, n):
    """Hoejden med n raekker: CountRows(...) erstattes af n."""
    e = re.sub(r"CountRows\((?:[^()]|\([^()]*\))*\)", str(n), expr)
    assert re.fullmatch(r"[\sMax()0-9,+*]*", e), e
    return eval(e, {"__builtins__": {}}, {"Max": max})


@pytest.mark.parametrize("ctrl,min_rows", [("galVhpOps", 1), ("galVhpOpsM", 1),
                                           ("galVhpPkgRows", 1)])
def test_gallery_height_fits_content_exactly(ctrl, min_rows):
    p = _props(open(VH, encoding="utf-8").read(), ctrl)
    pad, size = int(p["TemplatePadding"]), int(p["TemplateSize"])
    for n in range(min_rows, 30):
        content = pad + n * (size + pad)
        h = _height(p["Height"], n)
        assert h >= content, f"{ctrl}: {n} raekker = {content} px indhold, galleriet {h} px - scroller"
        assert h - content < size, f"{ctrl}: {h} px er mere end indholdet ({content})"
