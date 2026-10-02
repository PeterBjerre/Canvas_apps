# Fakturaimport — Office Scriptet

[`ReadInvoice.ts`](ReadInvoice.ts) er fakturalæseren bag **Materials → Import
invoice**. Den køres af flowet `BioSap-Material-ReadInvoice` med Excel Online
(Business) → *Run script from SharePoint library* — en standard-connector,
ingen premium.

- Opsætning, flowet trin for trin og brugerens gang:
  [`docs/34-faktura-import.md`](../../docs/34-faktura-import.md)
- Appens side (popuppen, kontrakten, oprettelsen af rækkerne):
  [`Material App/build/invoice_parts.py`](../../Material%20App/build/invoice_parts.py)
- Testfakturaerne og testen: [`tools/invoice/`](../../tools/invoice)

**Ret i filen her, ikke i Excel.** Kør `python3 tools/build_all.py` — den
kører scriptet på testfakturaerne — og indsæt derefter den nye udgave i
Excels kodeeditor. Filen er ren ASCII med vilje (de danske bogstaver står som
`\u`-koder), så den kan kopieres uden tegnsætsfejl.
