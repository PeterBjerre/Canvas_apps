import json, re

src = r"c:\Users\PKBJE\OneDrive - Ørsted\Documents - Sapvedligehold\SAP\SAP Site\html\js\data\vh-plan-options.json"
with open(src, encoding="utf-8-sig") as f:
    data = json.load(f)

def esc(s):
    return str(s).replace('"', '""')

opts = data["options"]

def make_collection(colname, key, label_field="Value"):
    items = opts[key]
    recs = ['{ ' + label_field + ': "' + esc(v) + '" }' for v in items]
    return "ClearCollect(\n    " + colname + ",\n    Table(\n        " + ",\n        ".join(recs) + "\n    )\n);"

blocks = []
blocks.append(make_collection("colPlanStatusOptions", "Status"))
blocks.append(make_collection("colYesNoOptions", "Vælg"))
blocks.append(make_collection("colUnitOptions", "Unit"))
blocks.append(make_collection("colOrderTypeOptions", "Order Type"))
blocks.append(make_collection("colMainWorkCenterTasklistOptions", "Main work center - Taskliste"))
blocks.append(make_collection("colMainWorkCenterItemOptions", "Main Work Center - Item"))
blocks.append(make_collection("colSortFieldOptions", "Sort field"))
blocks.append(make_collection("colPriorityOptions", "Priority"))
blocks.append(make_collection("colRevisionOptions", "Revision"))
blocks.append(make_collection("colActivityTypeOptions", "Maintenance activity type"))
blocks.append(make_collection("colCtrlOptions", "Crtl"))
blocks.append(make_collection("colCallHorizonOptions", "Call Horizon"))
blocks.append(make_collection("colDocSystemOptions", "Dokument system"))

out = "\n\n".join(blocks)
outpath = r"c:\Users\PKBJE\.copilot\session-state\e93d42be-2820-4dcf-8776-8328cfe9a7c9\files\colOptions.txt"
with open(outpath, "w", encoding="utf-8") as f:
    f.write(out)
print("chars:", len(out))
print(out[:2000])
