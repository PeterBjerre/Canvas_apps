# -*- coding: utf-8 -*-
"""
R2-086: SapOrders fejlmail har ét link, og det er en URL (ikke kørsels-id'et).
SapReceipts mail ved en fejlet kvittering viser aarsagen: kvitteringens
state/planId/sapSystem/orderGuid/lastError og planens status - ogsaa naar
flowet stoppede, foer de blev laest (saa er felterne tomme).

    python3 -m pytest tests/test_sap_error_mails.py
"""
import flowkit as fk
import wdl_eval

SYS = "BioSap-SapSystem (orsted_BioSapSapSystem)"


def test_sap_order_error_mail_links_to_the_run():
    body = fk.params(fk.find("BioSap-VhPlan-SapOrder", "Send_error_notification"))[
        "emailMessage/Body"]
    assert "href=\"@{workflow()" not in body
    assert body.count("FlowRunHistoryLink") == 1
    init = fk.find("BioSap-VhPlan-SapOrder", "Initialize_FlowRunHistoryLink")
    assert "https://make.powerautomate.com/" in init["inputs"]["variables"][0]["value"]


def _render(receipt, plan):
    body = fk.params(fk.find("BioSap-VhPlan-SapReceipt",
                             "Send_error_notification_on_receipt_failure"))["emailMessage/Body"]
    # wdl_eval kender ikke actions()/variables(); samme vaerdier som outputs.
    body = (body.replace("actions('Receipt')?['outputs']", "outputs('Receipt')")
                .replace("actions('Get_plan')?['outputs']?['body']", "outputs('Get_plan')")
                .replace("variables('FlowRunHistoryLink')", "outputs('Link')")
                .replace("items('Each_receipt')?['{FilenameWithExtension}']", "outputs('File')"))
    acts = {"Receipt": {"type": "Compose", "inputs": receipt},
            "Get_plan": {"type": "Compose", "inputs": plan},
            "Link": {"type": "Compose", "inputs": "<a>run</a>"},
            "File": {"type": "Compose", "inputs": "r<1>.json"},
            "Body": {"type": "Compose", "inputs": body}}
    return wdl_eval.run(acts, list(acts), {}, {}, parameters={SYS: "GP1"}).outputs["Body"]


def test_receipt_failure_mail_shows_the_reason():
    html = _render({"state": "Created", "planId": 7, "sapSystem": "GQ1", "orderGuid": "g-1",
                    "lastError": "Plan <locked>"},
                   {"SapOrderGuid": "g-2", "Status": {"Value": "Ready for creation in SAP"}})
    for text in ("Created", ">7<", "GQ1", ">GP1<", "g-1", "g-2", "Ready for creation in SAP",
                 "Plan &lt;locked&gt;", "r&lt;1&gt;.json", "<a>run</a>"):
        assert text in html, text


def test_receipt_failure_mail_renders_without_receipt():
    html = _render(None, None)
    assert "r&lt;1&gt;.json" in html and "<a>run</a>" in html
