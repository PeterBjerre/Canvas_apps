# -*- coding: utf-8 -*-
"""
Materials: IMPORT INVOICE - en faktura bliver til kladderaekker i en NY
anmodning, og brugeren udfylder resten. Se docs/34-faktura-import.md.

KAEDEN
------
    appen                  flowet                         Office Script
    [Read invoice]  -->  BioSap-Material-ReadInvoice  -->  ReadInvoice.ts
    fil (base64)         Excel Online (Business):          PDF-tekst eller
                         Run script from SharePoint        OIOUBL/Peppol-XML
                         library - STANDARD, ikke premium  -> linjer som JSON
          <-- result: en JSON-STRENG (ParseJSON, som FL-soegningen)

    [Create request]  ->  MD_RequestIndex (Kladde) + MaterialItems (draft)
                          i EET Patch-kald hver - samme moenster som Indsend
                          -> evt. fakturaen som dokument paa hver raekke
                             (det eksisterende BioSap-TaskListAttachment)

Laesningen ligger i flowet; SKRIVNINGEN ligger her, i appen. Noeglerne
(MAT-000441), statusordene og indeksraekken er de samme, som Gem og Indsend
bruger (domain_parts, request_index) - et flow, der selv skrev raekkerne,
ville vaere en anden udgave af den samme logik.

HVORFOR KLADDER
---------------
En faktura siger intet om funktionsplads, lager eller sliddel. Raekkerne
oprettes derfor som draft (kraever kun beskrivelsen, se save_row_fx), og
brugeren gemmer hver af dem som faerdig, naar resten er udfyldt. Saa er
det de almindelige regler, der afgoer, om en raekke kan indsendes.

KONTRAKTEN
----------
CONTRACT_LINE og CONTRACT_RESULT er feltnavnene i scriptets svar - ordret
interfacenavnene i flow/invoice-import/ReadInvoice.ts. tools/invoice/
harness.mjs stopper byggeriet, hvis de to lister glider fra hinanden.
"""
import attflows
import domain_config as cfg
import domain_parts as dp
import layout_tokens as lay
import request_index as ri
from build_helpers import (text_ctrl, text_min_height, group, button, checkbox_theme,
                           grow, pin_widths, flow_row, with_busy)
from gen_screen import (Ctrl, C_CARD_BORDER, C_MUTED, C_MUTED_BG, C_MODAL_BG,
                        C_PRIMARY_SOFT, C_OVERLAY, C_TRANSPARENT, C_TITLE,
                        C_WARN_FG, C_INVALID_FG)
from layout_tokens import at_least, SCROLLBAR_W

# ---------------------------------------------------------------------------
# Flowet og svaret
# ---------------------------------------------------------------------------
# Flowets Power Fx-navn er dets visningsnavn - med bindestreger, derfor i
# lige anfoerselstegn (se tools/build_flsearch.py).
FLOW_NAME = "'BioSap-Material-ReadInvoice'"
# Outputtet i "Respond to a Power App or flow". Power Apps ser det med
# smaa bogstaver.
FLOW_OUTPUT = "result"

CONTRACT_LINE = (
    "lineNo", "description", "extraText", "supplierPartNo", "manufacturer",
    "manufacturerPartNo", "model", "gtin", "quantity", "unit", "unitPrice",
    "priceUnit", "discountPct", "amount", "isCharge", "check",
)
CONTRACT_RESULT = (
    "ok", "error", "version", "source", "format", "fileName", "supplierName",
    "supplierVatNo", "invoiceNo", "invoiceDate", "orderNo", "currency", "netTotal",
    "linesTotal", "plantHint", "pages", "lines", "warnings", "text",
)

# colDomInvLines: (samlingens felt, JSON-feltet, art). Samlingen er det,
# popuppen viser og brugeren vaelger i.
LINE_FIELDS = [
    ("LineNo", "lineNo", "num"),
    ("Description", "description", "text"),
    ("ExtraText", "extraText", "text"),
    ("SupplierPartNo", "supplierPartNo", "text"),
    ("Manufacturer", "manufacturer", "text"),
    ("ManufacturerPartNo", "manufacturerPartNo", "text"),
    ("Model", "model", "text"),
    ("Gtin", "gtin", "text"),
    ("Quantity", "quantity", "num"),
    ("Unit", "unit", "text"),
    ("UnitPrice", "unitPrice", "num"),
    ("PriceUnit", "priceUnit", "num"),
    ("DiscountPct", "discountPct", "num"),
    ("Amount", "amount", "num"),
    ("IsCharge", "isCharge", "bool"),
    ("Check", "check", "text"),
]
# Fakturahovedet i varDomInvHead: (feltet, JSON-feltet).
HEAD_FIELDS = [
    ("Format", "format"),
    ("Supplier", "supplierName"),
    ("VatNo", "supplierVatNo"),
    ("InvoiceNo", "invoiceNo"),
    ("InvoiceDate", "invoiceDate"),
    ("OrderNo", "orderNo"),
    ("Currency", "currency"),
    ("Plant", "plantHint"),
]


def _check_contract():
    used = {j for _c, j, _k in LINE_FIELDS}
    unknown = used - set(CONTRACT_LINE)
    unknown |= {j for _c, j in HEAD_FIELDS} - set(CONTRACT_RESULT)
    if unknown:
        raise SystemExit("invoice_parts: %s er ikke felter i scriptets svar (CONTRACT_*)"
                         % sorted(unknown))


_check_contract()

# ---------------------------------------------------------------------------
# Fra fakturalinje (L) og -hoved (H) til MaterialItems
# ---------------------------------------------------------------------------
# Langteksten fortaeller, hvor raekken kommer fra - og bevarer det, der
# ikke har en kolonne: antal, rabat, valuta, beloeb og hele teksten.
LONG_TEXT = (
    '"Imported from invoice " & H.InvoiceNo & '
    'If(!IsBlank(H.InvoiceDate), " of " & H.InvoiceDate) & '
    'If(!IsBlank(H.Supplier), " from " & H.Supplier) & '
    'If(!IsBlank(H.OrderNo), ", order " & H.OrderNo) & "." & Char(10) & '
    '"Invoice line " & L.LineNo & ": " & '
    'If(IsBlank(L.Quantity), "", Text(L.Quantity) & " " & L.Unit & " x ") & '
    'If(IsBlank(L.UnitPrice), "", Text(L.UnitPrice, "0.00##") & " " & H.Currency) & '
    'If(!IsBlank(L.PriceUnit), " per " & Text(L.PriceUnit)) & '
    'If(!IsBlank(L.DiscountPct), ", discount " & Text(L.DiscountPct) & " %") & '
    'If(IsBlank(L.Amount), "", " = " & Text(L.Amount, "0.00") & " " & H.Currency) & "." & '
    'If(!IsBlank(L.Gtin), Char(10) & "GTIN: " & L.Gtin) & '
    'If(Len(L.Description) > 40, Char(10) & L.Description) & '
    'If(!IsBlank(L.ExtraText), Char(10) & L.ExtraText)'
)

# Hvad hver kolonne faar fra fakturaen. Resten af SECTIONS staar i
# USER_FILLS: det kan en faktura ikke vide. Et nyt felt i SECTIONS, der
# ikke staar nogen af stederne, stopper byggeriet - saa er der taget
# stilling til det.
FROM_INVOICE = {
    "Manufacturer": "L.Manufacturer",
    "ModelNumber": "L.Model",
    "ManufacturerPartNo": "L.ManufacturerPartNo",
    "Supplier": "H.Supplier",
    "SupplierPartNo": "L.SupplierPartNo",
    "Price": "L.UnitPrice",
    "PriceUnit": 'If(IsBlank(L.PriceUnit), "", Text(L.PriceUnit))',
    "StockUnit": "L.Unit",
    "LongText": LONG_TEXT,
}
USER_FILLS = {"FunctionalLocation", "NoBomItem", "DeliveringTime", "RecommendedStock",
              "StrategicPart", "WearPart"}


def _row_fields():
    have = {c for c, _l, _k, _ch in dp.FIELDS}
    missing = have - set(FROM_INVOICE) - USER_FILLS
    unknown = (set(FROM_INVOICE) | USER_FILLS) - have
    if missing or unknown:
        raise SystemExit("invoice_parts: felterne passer ikke til SECTIONS.\n"
                         f"  hverken i FROM_INVOICE eller USER_FILLS: {sorted(missing)}\n"
                         f"  ukendte: {sorted(unknown)}")
    out = []
    for col, _lab, kind, _ch in dp.FIELDS:
        if col in FROM_INVOICE:
            v = FROM_INVOICE[col]
            if kind in ("text", "choice"):
                v = f"Left({v}, 255)"
            out.append(f"{col}: {v}")
        else:
            out.append(f"{col}: {dp._blank(kind)}")
    return out


# ---------------------------------------------------------------------------
# Tilstanden (App.OnStart - kun skemaer og startvaerdier, ingen hentning)
# ---------------------------------------------------------------------------
_EMPTY = {"num": "0", "text": '""', "bool": "false"}


def collections():
    lines = {"Selected": "false"}
    for col, _j, kind in LINE_FIELDS:
        lines[col] = _EMPTY[kind]
    return [
        # Fakturaens linjer, som popuppen viser dem. Selected = med i den
        # nye anmodning.
        ("colDomInvLines", lines),
        # Hvad upload-flowet svarede pr. ny raekke.
        ("colDomInvUp", {"RowId": "0", "Ok": "false"}),
    ]


HEAD_EMPTY = ("{ Ok: false, Error: \"\", Warnings: \"\", FileName: \"\", "
              + ", ".join(f'{c}: ""' for c, _j in HEAD_FIELDS) + " }")

STATE = (
    "// Fakturaimporten (Material App/build/invoice_parts.py): popuppen, om\n"
    "// fakturaen er laest, og dens hoved.\n"
    "Set(varDomInvOpen, false);\n"
    "Set(varDomInvRead, false);\n"
    "// Fakturaen som dokument paa hver ny raekke (kan slaas fra i popuppen).\n"
    "Set(varDomInvAttach, true);\n"
    'Set(varDomInvJson, "");\n'
    f"Set(varDomInvHead, {HEAD_EMPTY})"
)

# ---------------------------------------------------------------------------
# Adfaerden
# ---------------------------------------------------------------------------
PICKER = "attDomInvPicker"
FILE = f"First({PICKER}.Attachments)"
LINES = "colDomInvLines"
SELECTED = f"Filter({LINES}, Selected)"


def _parse_line(alias):
    out = []
    for col, j, kind in LINE_FIELDS:
        v = f"{alias}.Value.{j}"
        if kind == "num":
            out.append(f"{col}: Value({v})")
        elif kind == "bool":
            out.append(f"{col}: Coalesce(Boolean({v}), false)")
        else:
            out.append(f'{col}: Coalesce(Text({v}), "")')
    return out


def read_fx():
    """Send filen gennem flowet og laeg svaret i popuppen.

    Svaret er en JSON-STRENG. Coalesce(..., "{}"): svarer flowet ingenting,
    skal resten stadig koere og sige det - ikke stoppe uden en lyd.

    En linje, der ligner fragt, et gebyr eller en kreditering, er med i
    listen, men ikke valgt (isCharge)."""
    head = ",\n".join(
        "                    " + f'{c}: Coalesce(Text(r.{j}), "")' for c, j in HEAD_FIELDS)
    line = ",\n".join("                        " + x for x in _parse_line("L"))
    return (
        "If(\n"
        f"    CountRows({PICKER}.Attachments) = 0,\n"
        '    Notify("Choose the invoice file first - a PDF or an XML file.", NotificationType.Warning),\n'
        "\n"
        "    IfError(\n"
        "        Set(\n"
        "            varDomInvJson,\n"
        f"            {FLOW_NAME}.Run(\n"
        f"                {FILE}.Name,\n"
        f"                {{ file: {{ contentBytes: {FILE}.Value, name: {FILE}.Name }} }}\n"
        f"            ).{FLOW_OUTPUT}\n"
        "        );\n"
        "        With(\n"
        '            { r: ParseJSON(Coalesce(varDomInvJson, "{}")) },\n'
        "            Set(\n"
        "                varDomInvHead,\n"
        "                {\n"
        "                    Ok: Coalesce(Boolean(r.ok), false),\n"
        '                    Error: Coalesce(Text(r.error), ""),\n'
        '                    Warnings: Concat(Table(r.warnings) As W, Text(W.Value), " "),\n'
        f"                    FileName: {FILE}.Name,\n"
        + head + "\n"
        "                }\n"
        "            );\n"
        "            ClearCollect(\n"
        f"                {LINES},\n"
        "                ForAll(\n"
        "                    Table(r.lines) As L,\n"
        "                    {\n"
        "                        Selected: !Coalesce(Boolean(L.Value.isCharge), false),\n"
        + line + "\n"
        "                    }\n"
        "                )\n"
        "            )\n"
        "        );\n"
        f"        Set(varDomInvRead, varDomInvHead.Ok && CountRows({LINES}) > 0),\n"
        "\n"
        "        Set(\n"
        "            varDomInvHead,\n"
        '            Patch(varDomInvHead, { Ok: false, Error: "The invoice could not be read: " & FirstError.Message })\n'
        "        );\n"
        f"        Clear({LINES});\n"
        "        Set(varDomInvRead, false)\n"
        "    )\n"
        ")"
    )


def again_fx():
    """En anden fil: tilbage til foerste trin."""
    return (f"Clear({LINES});\n"
            "Set(varDomInvRead, false);\n"
            f"Set(varDomInvHead, {HEAD_EMPTY});\n"
            f"Reset({PICKER})")


def create_fx():
    """Opret anmodningen og raekkerne - og laeg evt. fakturaen paa dem.

    EN NY ANMODNING
    ---------------
    Ny RequestGuid, og indeksraekken skrives som Kladde med det samme -
    praecis som "Save as draft" goer, med samme felter (request_index.py).
    Nummeret er indeksraekkens eget ID (MAT-000123), som ved Indsend.

    RAEKKERNE I EET KALD
    --------------------
    Patch med en tabel af Defaults() opretter dem alle og giver dem
    tilbage med ID - saa kan noeglen (MAT-000441) skrives i eet kald mere.
    Samme greb som Indsend; intet Patch inde i et ForAll.

    DOKUMENTET
    ----------
    Fakturaen laegges i hver ny raekkes mappe med det flow, dokumentruden
    bruger. Flowet koeres een gang pr. raekke - derfor kan det slaas fra."""
    rec = ri.record(
        cfg.DOMAIN, cfg.APP_KEY, ri.DRAFT,
        request_no="Coalesce(varDomRequestNo, varDomRequestGuid)",
        guid="varDomRequestGuid", me="varDomMe",
        short_text=f'"{cfg.TITLE}: " & CountRows(sel) & " row(s) from invoice " & H.InvoiceNo',
        plant="plant", item_count="CountRows(sel)", indent=20)
    fields = ",\n".join("                            " + f for f in [
        f"{cfg.C_TEXT}: Left(Coalesce(L.Description, L.SupplierPartNo, \"Invoice line \" & L.LineNo), 40)",
        "Plant: plant",
        *_row_fields(),
        'RowStatus: { Value: "draft" }',
        "RequestNo: varDomRequestNo",
        "RequestGuid: varDomRequestGuid",
        "RequesterEmail: varDomMe",
        "RequesterName: User().FullName",
    ])
    key = f'"{cfg.PREFIX}-" & Text(C.ID, "000000")'
    upload = (
        f"{attflows.FLOW_UPLOAD}.Run(\n"
        f"                                    {key},\n"
        f"                                    {{ file: {{ contentBytes: {FILE}.Value, name: {FILE}.Name }} }}\n"
        "                                ).flowrunsuccess"
    )
    return (
        "With(\n"
        "    {\n"
        f"        sel: {SELECTED},\n"
        "        H: varDomInvHead,\n"
        # Vaerket fra leveringsadressen - kun hvis det er et af listens.
        "        plant: If(\n"
        "            IsBlank(LookUp(colDomPlants, Value = varDomInvHead.Plant)),\n"
        '            "",\n'
        "            varDomInvHead.Plant\n"
        "        )\n"
        "    },\n"
        "    If(\n"
        "        CountRows(sel) = 0,\n"
        '        Notify("Select at least one invoice line.", NotificationType.Warning),\n'
        "\n"
        "        IfError(\n"
        "            Set(varDomRequestGuid, Text(GUID()));\n"
        '            Set(varDomRequestNo, "");\n'
        "            Set(\n"
        "                varDomIdx,\n"
        f"                Patch({cfg.L_INDEX}, Defaults({cfg.L_INDEX}), {rec})\n"
        "            );\n"
        f'            Set(varDomRequestNo, {ri.number_expr(cfg.PREFIX, "varDomIdx.ID")});\n'
        f"            Patch({cfg.L_INDEX}, varDomIdx, {{ {ri.COL_NO}: varDomRequestNo }});\n"
        "\n"
        "            Set(\n"
        "                varDomInvNew,\n"
        "                Patch(\n"
        f"                    {cfg.L_ROWS},\n"
        f"                    ForAll(sel, Defaults({cfg.L_ROWS})),\n"
        "                    ForAll(\n"
        "                        sel As L,\n"
        "                        {\n"
        + fields + "\n"
        "                        }\n"
        "                    )\n"
        "                )\n"
        "            );\n"
        "            Patch(\n"
        f"                {cfg.L_ROWS},\n"
        "                ForAll(varDomInvNew As C, { ID: C.ID }),\n"
        "                ForAll(\n"
        "                    varDomInvNew As C,\n"
        "                    {\n"
        "                        RowId: C.ID,\n"
        f"                        ItemKey: {key},\n"
        f'                        AttachmentFolder: "{attflows.LIBRARY}/" & {key}\n'
        "                    }\n"
        "                )\n"
        "            );\n"
        "\n"
        "            If(\n"
        f"                varDomInvAttach && CountRows({PICKER}.Attachments) > 0,\n"
        "                ClearCollect(\n"
        "                    colDomInvUp,\n"
        "                    ForAll(\n"
        "                        varDomInvNew As C,\n"
        "                        {\n"
        "                            RowId: C.ID,\n"
        "                            Ok: IfError(\n"
        "                                Lower(Text(" + upload + ")) = \"true\",\n"
        "                                false\n"
        "                            )\n"
        "                        }\n"
        "                    )\n"
        "                );\n"
        "                Patch(\n"
        f"                    {cfg.L_ROWS},\n"
        "                    ForAll(Filter(colDomInvUp, Ok) As U, { ID: U.RowId }),\n"
        "                    ForAll(Filter(colDomInvUp, Ok), { FileCount: 1 })\n"
        "                ),\n"
        "                Clear(colDomInvUp)\n"
        "            );\n"
        "\n"
        + dp.refresh_rows_fx(12) + ";\n"
        "\n"
        "            Set(\n"
        "                varDomInfo,\n"
        '                "Request " & varDomRequestNo & ": " & CountRows(varDomInvNew) &\n'
        '                " draft row(s) from invoice " & H.InvoiceNo &\n'
        '                ". Open each row, fill in what is missing and save it." &\n'
        "                If(\n"
        "                    CountRows(Filter(colDomInvUp, !Ok)) > 0,\n"
        '                    " The invoice could not be attached to " &\n'
        '                    CountRows(Filter(colDomInvUp, !Ok)) & " row(s)."\n'
        "                )\n"
        "            );\n"
        "            Notify(varDomInfo, NotificationType.Success);\n"
        f"            Clear({LINES});\n"
        "            Set(varDomInvRead, false);\n"
        f"            Set(varDomInvHead, {HEAD_EMPTY});\n"
        f"            Reset({PICKER});\n"
        "            Set(varDomInvOpen, false),\n"
        "\n"
        '            Set(varDomInfo, "Import failed: " & FirstError.Message);\n'
        '            Notify("Import failed: " & FirstError.Message, NotificationType.Error)\n'
        "        )\n"
        "    )\n"
        ")"
    )


# ---------------------------------------------------------------------------
# Knappen i formularens hoved
# ---------------------------------------------------------------------------
def import_button():
    b = button("btnDomInvOpen", '"Import invoice"', "Set(varDomInvOpen, true)", height=32,
               accessible='"Import an invoice: its lines become draft rows in a new request"',
               tooltip='"Read a supplier invoice (PDF or XML) into a new request"')
    b.props["Size"] = "13"
    return dp.fit(b, size=13)


# ---------------------------------------------------------------------------
# Popuppen
# ---------------------------------------------------------------------------
INV_W = "Min(920, App.Width - 32)"
INV_INNER_W = f"(({INV_W}) - 36)"
# Tabellens bredde: popuppens indre bredde minus galleriets polstring og
# scrollbar - saa overskriften og raekken har samme bredde (regel 29).
TABLE_W = f"({INV_INNER_W} - 4 - {SCROLLBAR_W})"
ROW_H = 32
GAL_ROWS = 7

READ = "varDomInvRead"
NOT_READ = f"!{READ}"
# Paa en telefon er der kun plads til beskrivelse, antal og beloeb.
WIDE = at_least("Tablet")

# (navn, overskrift, udtryk, bredde, hoejrestillet, kun paa bred skaerm)
COLUMNS = [
    ("No", "ITEM NO.", "ThisItem.SupplierPartNo", 110, False, True),
    ("Desc", "DESCRIPTION",
     'ThisItem.Description & If(ThisItem.IsCharge, "  (fee / charge)", "")', None, False, False),
    ("Qty", "QTY", 'If(IsBlank(ThisItem.Quantity), "-", Text(ThisItem.Quantity))', 64, True, False),
    ("Unit", "UNIT", "ThisItem.Unit", 56, False, True),
    ("Price", "PRICE", 'If(IsBlank(ThisItem.UnitPrice), "-", Text(ThisItem.UnitPrice, "#,##0.00##"))',
     90, True, True),
    ("Amount", "AMOUNT", 'If(IsBlank(ThisItem.Amount), "-", Text(ThisItem.Amount, "#,##0.00"))',
     96, True, False),
]
CHK_W = 30


def _cell(name, text, width, right, wide, size, head=False):
    c = text_ctrl(name, text, size=size, height=text_min_height(size),
                  color=C_MUTED if head else C_TITLE, weight="Semibold" if head else None,
                  wrap="false", align="Right" if right else None,
                  width=width if width is not None else 0,
                  visible=WIDE if wide else None)
    if width is None:
        grow(c, 80)
    return c


def _table():
    heads = [text_ctrl("txtDomInvHeadSel", '""', size=lay.SIZE_MICRO, height=18, width=CHK_W,
                       wrap="false", accessible='"Selected"')]
    cells = [Ctrl("chkDomInvSel", "ModernCheckbox", props=checkbox_theme({
        "AccessibleLabel": '"Include line " & ThisItem.LineNo',
        "Default": "ThisItem.Selected",
        "Height": "24",
        "Label": '""',
        "OnCheck": f"Patch({LINES}, ThisItem, {{ Selected: true }})",
        "OnUncheck": f"Patch({LINES}, ThisItem, {{ Selected: false }})",
        "Width": str(CHK_W),
    }), h=24)]
    for key, label, expr, width, right, wide in COLUMNS:
        heads.append(_cell(f"txtDomInvHead{key}", f'"{label}"', width, right, wide,
                           lay.SIZE_MICRO, head=True))
        c = _cell(f"txtDomInvCell{key}", expr, width, right, wide, 13)
        if key == "Amount":
            # Antal x pris passer ikke med beloebet - brugeren skal kigge.
            c.props["Color"] = f'If(ThisItem.Check = "mismatch", {C_WARN_FG}, {C_TITLE})'
        cells.append(c)
    head = group("conDomInvListHead", pin_widths(heads), direction="Horizontal", gap=8,
                 height=28, width=TABLE_W, align_items="Center", fill=C_MUTED_BG,
                 pad=(0, 0, 0, 0))
    row = group("conDomInvRow", pin_widths(cells), direction="Horizontal", gap=8,
                height="Parent.TemplateHeight - 2", align_items="Center",
                width="Parent.TemplateWidth")
    gal_h = f"Min(Max(CountRows({LINES}), 1), {GAL_ROWS}) * {ROW_H + 2}"
    gal = Ctrl("galDomInvLines", "Gallery", variant="Vertical", props={
        "AccessibleLabel": '"Invoice lines"',
        "BorderStyle": "BorderStyle.None",
        "Fill": C_TRANSPARENT,
        "FillPortions": "0",
        "Height": gal_h,
        "Items": f"Sort({LINES}, LineNo)",
        "LayoutMinWidth": "0",
        "LoadingSpinner": "LoadingSpinner.None",
        "Selectable": "false",
        "ShowScrollbar": "true",
        "TabIndex": "0",
        "TemplatePadding": "2",
        "TemplateSize": str(ROW_H),
        "Width": f"({TABLE_W}) + 4 + {SCROLLBAR_W}",
        "WrapCount": "1",
    }, children=[row], h=gal_h)
    return [head, gal]


def _summary_text():
    return (
        'varDomInvHead.Format & " invoice " & varDomInvHead.InvoiceNo &\n'
        'If(!IsBlank(varDomInvHead.InvoiceDate), " of " & varDomInvHead.InvoiceDate) &\n'
        '" from " & Coalesce(varDomInvHead.Supplier, "an unknown supplier") &\n'
        'If(!IsBlank(varDomInvHead.OrderNo), " - order " & varDomInvHead.OrderNo) &\n'
        'If(!IsBlank(varDomInvHead.Currency), " - " & varDomInvHead.Currency) &\n'
        'If(!IsBlank(varDomInvHead.Plant), " - plant " & varDomInvHead.Plant & " (from the delivery address)")'
    )


MSG = ('If(!varDomInvHead.Ok && !IsBlank(varDomInvHead.Error), varDomInvHead.Error, '
       'varDomInvHead.Warnings)')


def build_popups():
    """[sloer, popup] - staar efter dokumentpopuppen i skaermens boern.

    TO TRIN, EEN POPUP
    ------------------
    Foer laesningen: forklaring, filvaelger og Read invoice. Bagefter:
    fakturaens hoved, linjerne med et flueben hver og Create request. Saa
    er popuppen aldrig hoejere, end en baerbar kan vise - begge trin paa
    een gang ville vaere over 700 px."""
    vis = "IfError(varDomInvOpen, false)"
    backdrop = Ctrl("conDomInvBackdrop", "GroupContainer", variant="AutoLayout", props={
        "BorderStyle": "BorderStyle.None",
        "DropShadow": "DropShadow.None",
        "Fill": C_OVERLAY,
        "Height": "App.Height",
        "LayoutDirection": "LayoutDirection.Vertical",
        "LayoutOverflowX": "LayoutOverflow.Hide",
        "LayoutOverflowY": "LayoutOverflow.Hide",
        "Visible": vis,
        "Width": "App.Width",
        "X": "0",
        "Y": "0",
    }, children=[], vis=vis)

    title = grow(text_ctrl("txtDomInvH", '"Import invoice"', size=lay.SIZE_CARD_TITLE,
                           weight="Semibold", height=text_min_height(lay.SIZE_CARD_TITLE),
                           wrap="false"))
    close = button("btnDomInvClose", '"Close"', "Set(varDomInvOpen, false)", width=84, height=32)
    head = group("conDomInvHead", [title, close], direction="Horizontal", gap=12,
                 align_items="Center")

    # --- trin 1: filen --------------------------------------------------
    intro = text_ctrl(
        "txtDomInvIntro",
        '"Read a supplier invoice - a PDF with text, or an OIOUBL/Peppol XML file. Its lines become '
        'draft rows in a new request; you fill in what the invoice does not say."',
        size=13, color=C_MUTED, height=40, wrap="true", visible=NOT_READ)
    picker = Ctrl(PICKER, "Attachments@2.3.0", props={
        "AccessibleLabel": '"Choose the invoice file"',
        "BorderColor": C_CARD_BORDER,
        "BorderThickness": "1",
        "Height": "80",
        "MaxAttachments": "1",
        # Excel-connectoren tager hoejst 5 MB pr. kald, og filen sendes som
        # base64 (+33 %). En faktura er sjaeldent over et par hundrede kB.
        "MaxAttachmentSize": "3",
        "NoAttachmentsText": '"Drop the invoice here (PDF or XML), or browse"',
        "PaddingBottom": "5", "PaddingLeft": "5",
        "PaddingRight": "5", "PaddingTop": "5",
        "Visible": NOT_READ,
        "Width": "Parent.Width",
    }, h=80, vis=NOT_READ)
    read = dp.fit(button("btnDomInvRead", '"Read invoice"',
                         with_busy(dp.SAVING_VAR, read_fx()), primary=True,
                         display_mode=f"If(CountRows({PICKER}.Attachments) = 0, "
                                      "DisplayMode.Disabled, DisplayMode.Edit)",
                         tooltip='"Send the invoice through the invoice reader"'))
    read_row = group("conDomInvReadRow", [read], direction="Horizontal", gap=8, height=36,
                     align_items="Center", visible=NOT_READ)

    msg = text_ctrl("txtDomInvMsg", MSG, size=12,
                    color=f"If(varDomInvHead.Ok, {C_WARN_FG}, {C_INVALID_FG})",
                    height=54, wrap="true", visible=f"!IsBlank({MSG})")

    # --- trin 2: linjerne ------------------------------------------------
    summary = text_ctrl("txtDomInvSummary", _summary_text(), size=13, weight="Semibold",
                        height=40, wrap="true", visible=READ)
    table = _table()
    table_box = group("conDomInvTable", table, direction="Vertical", gap=0,
                      align_items="Start", visible=READ)
    attach = Ctrl("chkDomInvAttach", "ModernCheckbox", props=checkbox_theme({
        "AccessibleLabel": '"Attach the invoice to each new row"',
        "Default": "varDomInvAttach",
        "Height": "28",
        "Label": '"Attach the invoice to each new row as a document (one upload per row)"',
        "OnCheck": "Set(varDomInvAttach, true)",
        "OnUncheck": "Set(varDomInvAttach, false)",
        "Visible": READ,
        "Width": "Parent.Width",
    }), h=28, vis=READ)

    count = text_ctrl("txtDomInvCount",
                      f'CountRows({SELECTED}) & " of " & CountRows({LINES}) & " lines selected"',
                      size=13, color=C_MUTED, height=20, wrap="false")
    all_ = dp.fit(button("btnDomInvAll", '"Select all"',
                         f"UpdateIf({LINES}, true, {{ Selected: true }})", height=32))
    none = dp.fit(button("btnDomInvNone", '"Select none"',
                         f"UpdateIf({LINES}, true, {{ Selected: false }})", height=32))
    again = dp.fit(button("btnDomInvAgain", '"Other file"', again_fx(), height=32,
                          tooltip='"Start again with another invoice file"'))
    create = dp.fit(button("btnDomInvCreate", '"Create request"',
                           with_busy(dp.SAVING_VAR, create_fx()), primary=True, height=32,
                           display_mode=f"If(CountRows({SELECTED}) = 0, DisplayMode.Disabled, "
                                        "DisplayMode.Edit)",
                           tooltip='"Create a new request with the selected lines as draft rows"'))
    for b in (all_, none, again, create):
        b.props["Size"] = "13"
    footer = flow_row("conDomInvFooter", [count, all_, none, again, create], INV_INNER_W,
                      gap=8, flex=count, flex_min=0, visible=READ)

    modal = group("conDomInvModal",
                  [head, intro, picker, read_row, msg, summary, table_box, attach, footer],
                  direction="Vertical", gap=12, fill=C_MODAL_BG, border_color=C_PRIMARY_SOFT,
                  radius=lay.RADIUS_MODAL, pad=(18, 18, 18, 18), width=INV_W,
                  drop_shadow="ExtraBold", visible=vis)
    modal.props["X"] = dp.MODAL_X
    modal.props["Y"] = dp.MODAL_Y
    return [backdrop, modal]
