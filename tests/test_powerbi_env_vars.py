# -*- coding: utf-8 -*-
"""
R2-033: Power BI workspace og datasaet er miljoevariabler i
godkendelsesflowene - ikke flow-lokale parametre med DEV-GUID'er.

    python3 -m pytest tests/test_powerbi_env_vars.py
"""
import glob
import json
import os
import re

import pytest

import flowkit as fk

GUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
FLOWS = ["BioSap-VhPlan-SystemApproval", "BioSap-Material-SystemApproval",
         "BioSap-Material-ResolveApprovers", "BioSap-MeasuringPoint-Approval"]
EV = os.path.join(fk.FLOWS, "..", "environmentvariabledefinitions")


@pytest.mark.parametrize("name", FLOWS)
def test_power_bi_ids_are_environment_variables(name):
    params = fk.definition(name)["parameters"]
    for var, schema in (("BioSap-PowerBI-WorkspaceId", "orsted_BioSapPowerBIWorkspaceId"),
                        ("BioSap-PowerBI-DatasetId", "orsted_BioSapPowerBIDatasetId")):
        assert var not in params
        key = "%s (%s)" % (var, schema)
        assert params[key]["metadata"]["schemaName"] == schema
        assert "parameters('%s')" % key in json.dumps(fk.definition(name))
        assert os.path.isdir(os.path.join(EV, schema))


def test_no_local_parameter_carries_a_guid():
    for path in glob.glob(os.path.join(fk.FLOWS, "*.json")):
        params = json.load(open(path, encoding="utf-8-sig"))["properties"]["definition"]["parameters"]
        for k, v in params.items():
            if k.startswith("$") or v.get("metadata", {}).get("schemaName"):
                continue
            assert not GUID.match(str(v.get("defaultValue", ""))), \
                "%s: %s" % (os.path.basename(path), k)
