# -*- coding: utf-8 -*-
"""
Pakker testflowet til FL-API'et som en importpakke til Power Automate.

    python3 tools/build_fl_api_test.py

Kilden er flow/fl-api-test/definition.json. Resultatet er
flow/fl-api-test/FL-API-Test.zip, som importeres under
My flows -> Import -> Import Package (Legacy). Se docs/37-fl-api-test.md.

Flowet bruger kun HTTP-handlinger, saa pakken har ingen forbindelser.
Client secret og x-apikey er tomme variabler i flowet; de udfyldes i
Power Automate og maa aldrig staa her.

Pakken bygges deterministisk (faste GUID'er og tidsstempler), saa en
genbygning uden aendringer giver en identisk zip.
"""
import io
import json
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "flow", "fl-api-test", "definition.json")
OUT = os.path.join(ROOT, "flow", "fl-api-test", "FL-API-Test.zip")

DISPLAY_NAME = "BioSap-Test-FL-API (SAP Utility)"
FLOW_ID = "5e0c2f1a-6b3d-4c8e-9a71-0f4d2b6c8e13"
RES_ID = "8d4b7a29-3e61-4f0c-b5a2-1c9e7d3f6a40"
TELEMETRY_ID = "2a7f9c3e-5d18-4b6a-8e04-7c3b1f9d2e65"
CREATED = "2026-10-06T00:00:00.0000000Z"
ZIP_TIME = (2026, 10, 6, 0, 0, 0)


def files():
    with open(SRC, encoding="utf-8") as f:
        definition = json.load(f)
    flow_dir = "Microsoft.Flow/flows/" + FLOW_ID
    manifest = {
        "schema": "1.0",
        "details": {
            "displayName": DISPLAY_NAME,
            "description": "Tester SAP Utility test-endpointet "
                           "/functionallocations/{objektId}.",
            "createdTime": CREATED,
            "packageTelemetryId": TELEMETRY_ID,
            "creator": "Canvas_apps",
            "sourceEnvironment": "",
        },
        "resources": {
            RES_ID: {
                "id": "/providers/Microsoft.Flow/flows/" + FLOW_ID,
                "name": FLOW_ID,
                "type": "Microsoft.Flow/flows",
                "suggestedCreationType": "New",
                "creationType": "Existing, New, Update",
                "details": {"displayName": DISPLAY_NAME},
                "configurableBy": "User",
                "hierarchy": "Root",
                "dependsOn": [],
            }
        },
    }
    flow = {
        "name": FLOW_ID,
        "id": "/providers/Microsoft.Flow/flows/" + FLOW_ID,
        "type": "Microsoft.Flow/flows",
        "properties": {
            "apiId": "/providers/Microsoft.PowerApps/apis/shared_logicflows",
            "displayName": DISPLAY_NAME,
            "definition": definition,
            "connectionReferences": {},
            "flowFailureAlertSubscribed": False,
            "isManaged": False,
        },
    }
    return [
        ("manifest.json", manifest),
        ("Microsoft.Flow/flows/manifest.json",
         {"packageSchemaVersion": "1.0",
          "flowAssets": {"assetPaths": [FLOW_ID]}}),
        (flow_dir + "/definition.json", flow),
        (flow_dir + "/apisMap.json", {}),
        (flow_dir + "/connectionsMap.json", {}),
    ]


def build():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, obj in files():
            info = zipfile.ZipInfo(name, ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, json.dumps(obj, indent=2, ensure_ascii=False))
    return buf.getvalue()


def main():
    data = build()
    with open(OUT, "wb") as f:
        f.write(data)
    print("Skrev", os.path.relpath(OUT, ROOT), len(data), "bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
