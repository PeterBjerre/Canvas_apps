# -*- coding: utf-8 -*-
"""
R2-050 (flow-delen): NewPlanCreated fyrer ogsaa, naar InitialEmailSent er
tom (null), som de to soesterflows. Appen nulstiller flaget ved Submit, saa
en genindsendt plan faar en ny kvittering; flowet saetter det igen efter
mailen, saa der ikke kommer dubletter.

    python3 -m pytest tests/test_vh_submitted_mail_trigger.py
"""
import pytest

import flowkit as fk

NAME = "BioSap-EmailNotification-NewPlanCreated"


def _conditions():
    trig = fk.definition(NAME)["triggers"]["When_an_item_is_created_or_modified"]
    return [c["expression"] for c in trig["conditions"]]


@pytest.mark.parametrize("flag,fires", [(None, True), (False, True), (True, False)])
def test_trigger_accepts_empty_flag(flag, fires):
    plan = {"Status/Value": "In Progress", "InitialEmailSent": flag}
    assert all(fk.evaluate(e, plan) for e in _conditions()) is fires


def test_flag_is_set_only_after_the_mail():
    a = fk.find(NAME, "Send_an_HTTP_request_to_SharePoint")
    assert a["runAfter"] == {"Send_an_email_(V2)-EmailRequestor": ["Succeeded"]}
    assert '"InitialEmailSent": true' in fk.params(a)["parameters/body"]
