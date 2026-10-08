# -*- coding: utf-8 -*-
"""
Message us (issue #189): mailen sendes af flowet BioSap-SendFeedbackMail fra
servicekontoen SVC_BioSap - samme Outlook-connection reference
(orsted_BioSapOutlookConn, embedded) som Issue Board og godkendelsesmailene.
Aldrig fra brugerens egen Outlook (invoker eller mailto).

    python3 -m pytest tests/test_feedback_mail.py
"""
import glob
import json
import os
import re

from conftest import ROOT
import feedback_popup as fb

SRC = os.path.join(ROOT, "solution", "BIOSAP", "src")
FLOWS = os.path.join(SRC, "Workflows")
SVC_OUTLOOK = "orsted_BioSapOutlookConn"


def _flow():
    path, = glob.glob(os.path.join(FLOWS, "BioSap-SendFeedbackMail-*.json"))
    return json.load(open(path, encoding="utf-8-sig"))


def _actions(actions):
    for name, a in actions.items():
        yield name, a
        if "actions" in a:
            yield from _actions(a["actions"])
        if "else" in a:
            yield from _actions(a["else"]["actions"])


def _solution_refs():
    xml = open(os.path.join(SRC, "Other", "Customizations.xml"), encoding="utf-8-sig").read()
    return set(re.findall(r'connectionreferencelogicalname="([^"]+)"', xml))


def test_flow_sends_from_the_service_account():
    refs = _flow()["properties"]["connectionReferences"]
    assert refs == {"shared_office365": {
        "runtimeSource": "embedded",
        "connection": {"connectionReferenceLogicalName": SVC_OUTLOOK},
        "api": {"name": "shared_office365"},
    }}
    # Samme reference som Issue Board-flowet bruger til sine mails.
    ib, = glob.glob(os.path.join(FLOWS, "BioSap-IssueBoard-Submit-*.json"))
    ib_refs = json.load(open(ib, encoding="utf-8-sig"))["properties"]["connectionReferences"]
    assert ib_refs["shared_office365"] == refs["shared_office365"]


def test_every_flow_reference_is_in_the_solution():
    known = _solution_refs()
    for path in glob.glob(os.path.join(FLOWS, "*.json")):
        refs = json.load(open(path, encoding="utf-8-sig"))["properties"]["connectionReferences"]
        for key, r in refs.items():
            name = r["connection"]["connectionReferenceLogicalName"]
            assert name in known, (os.path.basename(path), key, name)


def test_solution_has_no_missing_dependency_on_the_flow():
    xml = open(os.path.join(SRC, "Other", "Solution.xml"), encoding="utf-8-sig").read()
    assert "orsted_sharedoffice365_0add9" not in xml
    assert "b30c1c37-6dbe-f111-aaaf-70a8a5824645" in xml   # flowet er stadig i solutionen


def test_mail_names_the_user_and_only_goes_to_the_mailbox():
    actions = dict(_actions(_flow()["properties"]["definition"]["actions"]))
    assert actions["Mailbox"]["inputs"] == fb.MAILBOX
    assert "x-ms-user-email" in actions["Caller"]["inputs"]
    send = actions["Send_an_email_(V2)"]["inputs"]
    assert send["host"]["connectionName"] == "shared_office365"
    p = send["parameters"]
    assert p["emailMessage/To"] == "@outputs('Mailbox')"
    assert p["emailMessage/ReplyTo"] == "@outputs('Caller')"
    assert "outputs('Caller')" in p["emailMessage/Body"]
    assert p["emailMessage/Attachments"] == "@body('Files')"
    # Ingen afsenderadresse - servicekontoens forbindelse er afsenderen.
    assert "emailMessage/From" not in p


def test_app_calls_the_flow_with_its_trigger_inputs():
    path, = glob.glob(os.path.join(FLOWS, "BioSap-SendFeedbackMail-*.json.data.xml"))
    assert 'Name="BioSap-SendFeedbackMail"' in open(path, encoding="utf-8-sig").read()
    assert fb.SEND_FLOW == "'BioSap-SendFeedbackMail'"
    schema = _flow()["properties"]["definition"]["triggers"]["manual"]["inputs"]["schema"]
    assert schema["required"] == ["text", "text_1", "text_2", "text_3"]


def test_popup_never_opens_outlook():
    src = open(fb.__file__, encoding="utf-8").read()
    code = src.split('"""', 2)[2]
    assert "Launch(" not in code and "mailto:" not in code
    yaml = "".join(open(p, encoding="utf-8").read()
                   for p in glob.glob(os.path.join(ROOT, "BIO SAP App", "Screen*.pa.yaml")))
    assert "mailto:" not in yaml
    assert yaml.count("'BioSap-SendFeedbackMail'.Run(") == 7
