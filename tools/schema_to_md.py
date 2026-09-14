# -*- coding: utf-8 -*-
"""
Laver schema.md ud af et listeudtraek - uanset hvilken vej det kom ind.

    python3 tools/schema_to_md.py sharepoint/inspect/out/sharepoint-schema.json

De to udtraeksveje giver samme indhold med forskellige feltnavne:

    Export-ListSchema.ps1   PnP, kraever en Entra app-registrering
    browser-extract.js      REST gennem browsersessionen, kraever ingenting

Denne fil kender begge former og skriver den samme markdown, saa resten af
arbejdet ikke behoever vide hvilken der blev brugt.
"""
import json, os, sys

# browser-navn -> faelles navn. PnP bruger allerede de faelles navne.
ALIAS = {
    "InternalName": "internalName", "Title": "displayName", "TypeAsString": "type",
    "Required": "required", "Indexed": "indexed", "ReadOnlyField": "readOnly",
    "Description": "description", "Choices": "choices", "LookupList": "lookupList",
    "LookupField": "lookupField", "AllowMultipleValues": "allowMultiple",
    "Formula": "formula", "MaxLength": "maxLength", "DefaultValue": "defaultValue",
    "EnforceUniqueValues": "unique",
}


def norm(field):
    out = {}
    for k, v in field.items():
        out[ALIAS.get(k, k)] = v
    # Browserens Choices kan komme som {"results": [...]}
    ch = out.get("choices")
    if isinstance(ch, dict) and "results" in ch:
        out["choices"] = ch["results"]
    return out


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    src = sys.argv[1]
    data = json.load(open(src, encoding="utf-8-sig"))
    lists = data.get("lists", [])
    failed = data.get("failedLists") or []

    L = []
    a = L.append
    a("# SharePoint-lister bag VH-plan appen")
    a("")
    a(f"Udtrukket {data.get('exportedOn','?')} fra {data.get('site','?')}.")
    a(f"Data med: {'ja' if data.get('includesData') else 'nej, kun struktur'}.")
    a("")

    if failed:
        a(f"> **{len(failed)} liste(r) fejlede og mangler i udtraekket:**")
        for f in failed:
            a(f"> - `{f.get('list')}`: {f.get('error')}")
        a("")

    a("| Liste | Raekker | Kolonner |")
    a("|---|---:|---:|")
    for l in lists:
        a(f"| `{l['title']}` | {l.get('itemCount', '?')} | {len(l.get('fields', []))} |")

    for l in lists:
        a("")
        a(f"## `{l['title']}`  -  {l.get('itemCount','?')} raekker")
        a("")
        a("| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |")
        a("|---|---|---|:-:|:-:|---|")
        for raw in l.get("fields", []):
            f = norm(raw)
            notes = []
            if f.get("choices"):
                notes.append("valg: " + ", ".join(str(c) for c in f["choices"][:12]))
            if f.get("lookupList"):
                notes.append(f"opslag -> {f['lookupList']} ({f.get('lookupField','')})")
            if f.get("formula"):
                notes.append(f"beregnet: `{f['formula']}`")
            if f.get("allowMultiple"):
                notes.append("flere vaerdier")
            if f.get("unique"):
                notes.append("unik")
            if f.get("readOnly"):
                notes.append("skrivebeskyttet")
            internal = f.get("internalName", "?")
            display = f.get("displayName", internal)
            # Power Fx binder paa visningsnavnet - fremhaev hvor de er forskellige.
            shown = f"**{display}**" if display != internal else display
            a(f"| `{internal}` | {shown} | {f.get('type','?')} | "
              f"{'x' if f.get('required') else ''} | {'x' if f.get('indexed') else ''} | "
              f"{'; '.join(notes)} |")

        sample = l.get("sample")
        if sample:
            a("")
            a(f"<details><summary>{len(sample)} proeveraekker</summary>")
            a("")
            a("```json")
            a(json.dumps(sample, indent=2, ensure_ascii=False))
            a("```")
            a("</details>")

    out = os.path.join(os.path.dirname(os.path.abspath(src)), "schema.md")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L) + "\n")
    print(f"Skrev {out} - {len(lists)} lister, "
          f"{sum(len(l.get('fields', [])) for l in lists)} kolonner i alt")
    if failed:
        print(f"ADVARSEL: {len(failed)} liste(r) mangler i udtraekket.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
