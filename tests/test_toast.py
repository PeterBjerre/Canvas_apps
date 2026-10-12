# -*- coding: utf-8 -*-
"""Beskederne nederst til hoejre (tools/toast.py, UX-review 2026-10 B1)."""
import os
import re

import pytest

import toast

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "BIO SAP App")


def test_a_statement_in_a_chain_becomes_a_set():
    out = toast.rewrite('Notify("Saved.", NotificationType.Success);\nSet(x, 1)')
    assert out == ('Set(gblToast, { Text: "Saved.", Kind: "Success", At: Now() });\n'
                   "Set(x, 1)")


def test_the_last_value_of_an_argument_keeps_its_type():
    out = toast.rewrite('If(c, Notify("A", NotificationType.Warning), x)')
    assert out == ('If(c, Set(gblToast, { Text: "A", Kind: "Warning", At: Now() }); true, x)')
    out = toast.rewrite('IfError(Patch(l, r); true, Notify("B: " & FirstError.Message, '
                        'NotificationType.Error))')
    assert out.endswith('Kind: "Error", At: Now() }); true)')


def test_a_notify_without_a_type_is_information():
    assert 'Kind: "Information"' in toast.rewrite('Notify("Hi")')


def test_text_inside_a_string_is_not_touched():
    s = '"Notify(this)" & x'
    assert toast.rewrite(s) == s


def test_an_unknown_type_stops_the_build():
    with pytest.raises(SystemExit):
        toast.rewrite('Notify("x", t)')


def test_every_screen_has_the_toast_and_no_notify():
    for f in sorted(os.listdir(APP)):
        if not f.startswith("Screen") or not f.endswith(".pa.yaml"):
            continue
        t = open(os.path.join(APP, f), encoding="utf-8").read()
        assert not re.search(r"\bNotify\s*\(", t), f
        assert re.search(r"- con\w+Toast:", t), f
        assert re.search(r"- tmr\w+Toast:", t), f


def test_errors_stay_until_closed():
    t = open(os.path.join(APP, "ScreenMdHub.pa.yaml"), encoding="utf-8").read()
    i = t.index("tmrMdToast:")
    block = t[i:i + 1500]
    assert 'IfError(gblToast.Kind, "") = "Error"' in block
    assert "DateDiff(gblToast.At, Now(), TimeUnit.Milliseconds) >= %d" % toast.TOAST_MS in block


def test_app_onstart_declares_the_toast():
    t = open(os.path.join(APP, "App.pa.yaml"), encoding="utf-8").read()
    assert "Set(gblToast, " + toast.EMPTY + ")" in t
    assert "Notify(" not in t
