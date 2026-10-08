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
import wdl_eval

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
    assert schema["required"] == ["text", "text_1", "text_2", "text_3", "text_4"]
    assert schema["properties"]["text_4"]["title"] == "Context"
    # Beskeden gaar uaendret til flowet - anmodningen kommer i Context (#194).
    yaml = open(os.path.join(ROOT, "BIO SAP App", "ScreenKks.pa.yaml"), encoding="utf-8").read()
    assert ("%s, inpKksFbMessage.Text, JSON(ForAll(attKksFbFiles.Attachments, {Name: ThisRecord.Name, Value: ThisRecord.Value}), JSONFormat.IncludeBinaryData), %s)"
            % (fb.SUBJECT_FX, fb.CONTEXT_FX)) in yaml
    assert "Url: Coalesce(R.AppUrl" in yaml


def test_popup_never_opens_outlook():
    src = open(fb.__file__, encoding="utf-8").read()
    code = src.split('"""', 2)[2]
    assert "Launch(" not in code and "mailto:" not in code
    yaml = "".join(open(p, encoding="utf-8").read()
                   for p in glob.glob(os.path.join(ROOT, "BIO SAP App", "Screen*.pa.yaml")))
    assert "mailto:" not in yaml
    assert yaml.count("'BioSap-SendFeedbackMail'.Run(") == 7


# ---------------------------------------------------------------------------
# Mailens formatering (issue #194): flowets udtryk koeres paa eksempler med
# en lille WDL-fortolker (tests/wdl_eval.py), og den faerdige HTML efterses.
# ---------------------------------------------------------------------------
COMPOSE = ["Caller", "Caller_name", "Mailbox", "Message_html", "Context",
           "Request", "Heading", "Request_html", "Preheader"]
HEADERS = {"x-ms-user-email": "Jane.Doe@orsted.com", "x-ms-user-name": 'Jane "JD" <Doe> & Co'}
REQUEST = {"Kind": "R", "Topic": "EQ-000912 \u00b7 Pump", "Code": "EQ-000912", "Type": "Equipment",
           "Title": "Pump <P-01> & \"seal\"",
           "Url": "https://apps.powerapps.com/play/e/x/a/y?domain=equipment&reqid=abc"}


def _mail(message, context):
    actions = dict(_actions(_flow()["properties"]["definition"]["actions"]))
    body = {"text": fb.MAILBOX, "text_1": "SAP maintenance - x", "text_2": message,
            "text_3": "[]", "text_4": json.dumps(context) if context is not None else ""}
    ctx = wdl_eval.run(actions, COMPOSE, body, HEADERS)
    html = wdl_eval.value(actions["Send_an_email_(V2)"]["inputs"]["parameters"]["emailMessage/Body"], ctx)
    return html, ctx.outputs


def _well_formed(html):
    """Aabne og lukkede tabeller, raekker og celler gaar op."""
    for tag in ("table", "tr", "td", "a", "div", "span", "strong"):
        assert html.count("<" + tag + " ") + html.count("<" + tag + ">") == html.count("</" + tag + ">"), tag


def test_flow_order_runs_every_compose_before_the_mail():
    acts = _flow()["properties"]["definition"]["actions"]
    prev = None
    for name in COMPOSE + ["Files", "Check"]:
        if prev:
            assert acts[name]["runAfter"] == {prev: ["Succeeded"]}, name
        prev = name


def test_message_is_escaped_and_keeps_line_breaks():
    msg = "Hello team,\r\n\r\n<script>alert(1)</script> & \"quoted\" text\nLine 3\rLine 4"
    html, out = _mail(msg, {"Kind": "G", "Topic": "Question"})
    assert out["Message_html"] == ("Hello team,<br><br>&lt;script&gt;alert(1)&lt;/script&gt; &amp; "
                                   "&quot;quoted&quot; text<br>Line 3<br>Line 4")
    assert "<script>" not in html
    # Afsenderens navn escapes ogsaa, og Reply-To-adressen staar som link.
    assert "Jane &quot;JD&quot; &lt;Doe&gt; &amp; Co" in html
    assert 'href="mailto:jane.doe@orsted.com"' in html
    # Preheaderen er beskedens start paa een linje.
    assert out["Preheader"].startswith("Hello team,    &lt;script&gt;")
    assert "<br>" not in out["Preheader"]
    _well_formed(html)


def test_message_text_is_not_translated_or_rewritten():
    msg = "Hej, pumpen paa \u00e6\u00f8\u00e5-linjen virker ikke."
    html, out = _mail(msg, None)
    assert out["Message_html"] == msg
    assert msg in html


def test_general_subject_gives_heading_and_no_request_section():
    html, out = _mail("Hi", {"Kind": "G", "Topic": "Improvement idea", "Code": "", "Type": "",
                             "Title": "", "Url": ""})
    assert out["Heading"] == "Improvement idea"
    assert out["Request_html"] == ""
    assert "Open the request in the app" not in html and ">Request<" not in html
    _well_formed(html)


def test_no_subject_gives_a_plain_heading():
    for ctx in (None, {}, {"Kind": None, "Topic": None, "Code": None, "Type": None,
                           "Title": None, "Url": None}):
        html, out = _mail("Hi", ctx)
        assert out["Heading"] == "Message"
        assert out["Request_html"] == ""
        _well_formed(html)


def test_request_section_has_details_and_the_link():
    html, out = _mail("Hi", REQUEST)
    assert out["Heading"] == "Equipment request EQ-000912"
    sec = out["Request_html"]
    assert ">Request<" in sec and "EQ-000912" in sec and ">Equipment<" in sec
    assert "Pump &lt;P-01&gt; &amp; &quot;seal&quot;" in sec
    assert ('href="https://apps.powerapps.com/play/e/x/a/y?domain=equipment&amp;reqid=abc"' in sec)
    assert "Open the request in the app" in sec
    # Beskeden kommer foer anmodningen - den er mailens hovedsag.
    assert html.index(">Message<") < html.index(">Request<")
    _well_formed(html)


def test_request_link_only_when_it_is_https():
    for url in ("", "javascript:alert(1)", "http://example.com"):
        html, out = _mail("Hi", dict(REQUEST, Url=url))
        assert "EQ-000912" in out["Request_html"]
        assert "Open the request in the app" not in html
        assert "javascript:" not in html
        _well_formed(html)


def test_mail_reuses_the_plan_mail_styling():
    """Samme farver, typografi og opbygning som VH-planens mails
    (flow/email-plan-submitted.html): tabeller, inline styles, Outlook-sikkert."""
    html, _ = _mail("Hi", REQUEST)
    tpl = open(os.path.join(ROOT, "flow", "email-plan-submitted.html"), encoding="utf-8").read()
    for token in ("#eef2f6", "#12405f", "#8fc4e5", "#d7dee8", "#24313f", "#6b7b8c",
                  "#1a6ea8", "#8494a5", "#e4e9f0", "Segoe UI,Arial,Helvetica,sans-serif",
                  'role="presentation"', 'bgcolor="#1a6ea8"'):
        assert token in tpl and token in html, token
    # Fast bredde kun i Outlook paa Windows; ellers flydende til mobil.
    assert "<!--[if mso]>" in html and "max-width:640px" in html
    for bad in ("<style", "class=", "display:flex", "<h1", "<h2", "<p>"):
        assert bad not in html, bad
    assert "Reply to this email" in html


def test_no_json_over_a_raw_attachments_table():
    # Attachments-tabellen har en skjult kolonne af typen Control; JSON af
    # hele tabellen fejler i Studio-compile. Kun Name og Value maa sendes.
    for path in glob.glob(os.path.join(ROOT, "BIO SAP App", "*.pa.yaml")):
        text = open(path, encoding="utf-8").read()
        assert not re.search(r"JSON\(\w+\.Attachments\b", text), path
