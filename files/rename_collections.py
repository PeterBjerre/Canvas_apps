# -*- coding: utf-8 -*-
"""Rename collections in previously generated option/tasklist Power Fx snippets to the
colVhp* naming convention used by the generated screen, then assemble full App.pa.yaml
OnStart script (collections + seed data + starting variables)."""
import re

FILES_DIR = r"c:\Users\PKBJE\.copilot\session-state\e93d42be-2820-4dcf-8776-8328cfe9a7c9\files"
OUT_DIR = r"c:\Users\PKBJE\OneDrive - Ørsted\Documents - Sapvedligehold\SAP\SAP Site\html\powerapp-vhplan"

RENAME_MAP = {
    "colPlanStatusOptions": "colVhpPlanStatusOptions",
    "colYesNoOptions": "colVhpYesNoOptions",
    "colUnitOptions": "colVhpUnitOptions",
    "colOrderTypeOptions": "colVhpOrderTypeOptions",
    "colMainWorkCenterTasklistOptions": "colVhpMainWorkCenterTasklistOptions",
    "colMainWorkCenterItemOptions": "colVhpMainWorkCenterItemOptions",
    "colSortFieldOptions": "colVhpSortFieldOptions",
    "colPriorityOptions": "colVhpPriorityOptions",
    "colRevisionOptions": "colVhpRevisionOptions",
    "colActivityTypeOptions": "colVhpActivityTypeOptions",
    "colCtrlOptions": "colVhpCtrlOptions",
    "colCallHorizonOptions": "colVhpCallHorizonOptions",
    "colDocSystemOptions": "colVhpDocSystemOptions",
    "colTasklists": "colVhpTasklists",
}


def rename_collections(text):
    # Order matters: rename longer/more specific names first to avoid partial overlaps
    for old in sorted(RENAME_MAP.keys(), key=len, reverse=True):
        new = RENAME_MAP[old]
        text = re.sub(r"\b" + re.escape(old) + r"\b", new, text)
    return text


with open(FILES_DIR + r"\colOptions.txt", encoding="utf-8") as f:
    options_src = f.read()
with open(FILES_DIR + r"\colTasklists.txt", encoding="utf-8") as f:
    tasklists_src = f.read()

options_src = rename_collections(options_src)
tasklists_src = rename_collections(tasklists_src)

with open(FILES_DIR + r"\colOptions_renamed.txt", "w", encoding="utf-8") as f:
    f.write(options_src)
with open(FILES_DIR + r"\colTasklists_renamed.txt", "w", encoding="utf-8") as f:
    f.write(tasklists_src)

print("Renamed OK. options chars:", len(options_src), "tasklists chars:", len(tasklists_src))
