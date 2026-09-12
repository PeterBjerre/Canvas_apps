import json, re

src = r"c:\Users\PKBJE\OneDrive - Ørsted\Documents - Sapvedligehold\SAP\SAP Site\html\js\data\vh-tasklist-data.js"
with open(src, encoding="utf-8-sig") as f:
    raw = f.read()

raw = re.sub(r'^window\.VH_TASKLIST_DATA\s*=\s*', '', raw.strip())
raw = re.sub(r';\s*$', '', raw)
data = json.loads(raw)

def esc(s):
    if s is None:
        return ""
    s = str(s)
    s = s.replace('"', '""')
    return s

def numlit(s):
    # numeric literal for workHours/durationHours; fallback to 0
    if s is None or str(s).strip() == "":
        return "0"
    try:
        f = float(s)
        if f == int(f):
            return str(int(f))
        return str(f)
    except ValueError:
        return "0"

lines = []
lines.append("ClearCollect(")
lines.append("    colTasklists,")
lines.append("    Table(")

plant_entries = []
MAX_OPS_PER_TASKLIST = 6
for plant_code, plant_obj in data["plants"].items():
    for tl in plant_obj["tasklists"]:
        if tl["key"].endswith("-CUSTOM"):
            continue  # skip empty custom tasklists to reduce OnStart formula size
        ops = tl.get("operations", [])[:MAX_OPS_PER_TASKLIST]
        op_records = []
        for op in ops:
            rec = (
                '{ OperationNo: "' + esc(op.get("operationNo")) + '", '
                'OperationShortText: "' + esc(op.get("operationShortText")) + '", '
                'WorkHours: ' + numlit(op.get("workHours")) + ', '
                'DurationHours: ' + numlit(op.get("durationHours")) + ', '
                'MainWorkCenter: "' + esc(op.get("mainWorkCenter")) + '", '
                'Vendor: "' + esc(op.get("vendor")) + '", '
                'LongText: "' + esc(op.get("longText")) + '", '
                'ControlKey: "' + esc(op.get("controlKey")) + '", '
                'OpPlant: "' + esc(op.get("plant")) + '" }'
            )
            op_records.append(rec)
        ops_table = "Table(\n            " + ",\n            ".join(op_records) + "\n        )" if op_records else "Table()"
        entry = (
            "        {\n"
            '            Plant: "' + esc(plant_code) + '",\n'
            '            Key: "' + esc(tl["key"]) + '",\n'
            '            Name: "' + esc(tl["name"]) + '",\n'
            '            Description: "' + esc(tl.get("description")) + '",\n'
            "            Operations: " + ops_table + "\n"
            "        }"
        )
        plant_entries.append(entry)

lines.append(",\n".join(plant_entries))
lines.append("    )")
lines.append(");")

out = "\n".join(lines)
outpath = r"c:\Users\PKBJE\.copilot\session-state\e93d42be-2820-4dcf-8776-8328cfe9a7c9\files\colTasklists.txt"
with open(outpath, "w", encoding="utf-8") as f:
    f.write(out)

print("Total tasklists:", len(plant_entries))
print("Output length chars:", len(out))
print("Output lines:", out.count(chr(10)) + 1)
