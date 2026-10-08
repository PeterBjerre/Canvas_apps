# -*- coding: utf-8 -*-
"""
Trinstriben i en anmodningsapp (tools/stepper.py, issue #204).

Striben er EET SVG-billede med to udgaver - den brede med navne og den
smalle med "2 of 3". Testene laeser Power Fx'en, for den kan ikke koeres
her, og de ting, der gaar i stykker, er netop dem, formlen siger: at det
rigtige trin er det aktuelle, at et trin, der ikke gaelder, hedder "Not
required", og at striben ikke er bundet til et domaene.

    python3 -m pytest tests/test_stepper.py
"""
import os
import sys

from conftest import ROOT, TOOLS

sys.path.insert(0, TOOLS)
import stepper as st

STEPS = [('"One"', 'varA'), ('"Two"', 'varB'), ('"Three"', 'varC')]


def test_the_strip_is_one_control():
    ctrl = st.strip("Dom", STEPS)
    assert ctrl.name == "imgDomSteps"
    # Et klassisk Image skal have et TabIndex (check_layout).
    assert ctrl.props["TabIndex"] == "0"
    assert ctrl.props["AccessibleLabel"]


def test_the_hint_line_sits_under_the_strip():
    box = st.strip("Dom", STEPS, hint='"missing something"')
    assert box.name == "conDomSteps"
    assert [c.name for c in box.children] == ["imgDomSteps", "txtDomStepsHint"]


def test_a_step_that_does_not_apply_says_not_required():
    fx = st.strip("Dom", STEPS).props["Image"]
    # Hvert trin har sin egen - baade i den brede og i den smalle udgave.
    assert fx.count('"Not required"') >= len(STEPS)
    for i, (label, _v) in enumerate(STEPS):
        assert 's%d = "Skipped", "Not required", %s' % (i + 1, label) in fx


def test_the_narrow_screen_gets_the_step_number():
    fx = st.strip("Dom", STEPS).props["Image"]
    assert '" of 3 - "' in fx
    # Det foerste trin, der er i gang - ellers det foerste, der ikke er
    # naaet; "2 of 3" skal passe med knuderne.
    pos = fx.index('" of 3 - "')
    head = fx[:pos]
    assert head.rindex('s1 = "Current", 1') < head.rindex('s2 = "Current", 2')
    assert 's1 = "Pending", 1' in head


def test_each_step_gets_its_own_binding():
    fx = st.strip("Dom", STEPS).props["Image"]
    # Tilstandene bindes EEN gang i et With - ikke een gang pr. brug.
    assert fx.startswith("With(")
    for i, (_lab, var) in enumerate(STEPS):
        assert "s%d: %s" % (i + 1, var) in fx
        assert fx.count("%s" % var) == 1


def test_the_module_is_domain_neutral():
    # Ingen samling, variabel eller liste fra et bestemt domaene - navnene
    # og tilstandene kommer fra kalderen (Measuring Point kan bruge den
    # uaendret). Kommentarerne maa gerne naevne, hvem der bruger den.
    src = open(os.path.join(TOOLS, "stepper.py"), encoding="utf-8").read()
    code = "\n".join(l for l in src.split("\n") if not l.lstrip().startswith("#"))
    for word in ("colDom", "varDom", "colMat", "varMat", "MaterialItems",
                 "EquipmentItems"):
        assert word not in code, word


def test_two_steps_draw_one_line_and_four_draw_three():
    for n in (2, 3, 4):
        steps = [('"S%d"' % i, "v%d" % i) for i in range(n)]
        fx = st.strip("Dom", steps).props["Image"]
        assert fx.count("<line") == n - 1, n
        assert fx.count("<circle") == n, n
