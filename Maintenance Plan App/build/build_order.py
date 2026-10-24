# -*- coding: utf-8 -*-
"""
ITEM FRA EN SAP-ORDRE (Peter 2026-10-23/24, docs/45-woe-ordre-flow.md).

En knap i Items-kortets hoved aabner en popup med eet felt: ordrenummeret.
Fetch koerer flowet BioSap-Integration-WoeOrder, som svarer med alt om
ordren som een JSON-tekst (result). Appen laeser den ind og opretter et
NYT item med ordrens header og en operationslinje pr. operation - praecis
som Add item + Copy item goer det, saa alt kan rettes i editoren, foer der
gemmes. Ingen SharePoint-skrivning her: det er Save draft, der gemmer.

Feltmappingen staar i docs/45 ("Feltmapping: ordre -> VH-plan-appen"):

- header.shortDescription -> ShortText, headerText (ellers header.description)
  -> LongText, header.functionalLocation -> FunctionalLocation (ryddes som
  ved Copy, naar den ikke hoerer til planens vaerk), responsibleInitials ->
  Initials, foerste operations workCenter -> MainWorkCenter (kun hvis den
  findes i listen), status ZBOW -> NonFlowUserStatus, objects -> Object list.
- operations[].id -> OperationNo, description -> OperationShortText,
  actualHours -> Work (Peter: faktisk arbejde, ikke planlagt), workCenter,
  controlKey, vendorId/vendorName -> Vendor ("101985 - NAME"),
  operationTexts (paa objectId) -> LongText. Persons findes ikke i svaret
  (API-teamet spurgt); 1 indtil da, saa varigheden kan regnes.
- status, partner, activities, causes, feedback bruges ikke (Peter:
  skjules; de bliver i svaret til senere).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import C_MUTED, C_MODAL_BG, C_PRIMARY_SOFT
import layout_tokens as lay
from layout_tokens import at_least
from build_helpers import (popup_head, text_ctrl, group, button, text_input, grow,
                           mobile_pad, ensure_hit)
import icons
import mobile
import sp_config as cfg

# Flowet (solution/BIOSAP/src/Workflows/BioSap-Integration-WoeOrder-*.json).
# Navnet staar i lige anfoerselstegn, fordi det har bindestreger.
ORDER_FLOW = "'BioSap-Integration-WoeOrder'"
OPEN = "varVhpOrderOpen"
BUSY = "varVhpOrderBusy"
MSG = "varVhpOrderMsg"
RAW = "varVhpOrderRaw"
INPUT = "inpVhpOrderNo"
BTN_HEAD = "btnVhpFromOrder"
BTN_FETCH = "btnVhpOrderFetch"
MODAL = "conVhpOrderModal"
# Som de andre popupper paa telefonen (build_modal.POP_CW_M).
POP_CW_M = f"App.Width - {2 * lay.MOBILE_POP_MARGIN + 2 * lay.MOBILE_CARD_PAD}"

# Variablerne, som App.OnStart saetter (generate_app_onstart.py).
ONSTART = [
    "// Item fra SAP-ordre (build_order.py): popuppen, opslaget koerer, og dens besked.",
    f"Set({OPEN}, false);",
    f"Set({BUSY}, false);",
    f'Set({MSG}, "");',
]


def _record(collection, overrides, indent):
    """Een raekke til samlingen med HVERT felt i dens skema (som
    build_items._copy_record): et nyt felt kan ikke glemmes. overrides er
    de felter, ordren fylder; resten faar skemaets tomme vaerdi."""
    schema = dict(cfg.WORKING_COLLECTIONS)[collection]
    pad = " " * indent
    fields = [f"{k}: {overrides.get(k, v)}" for k, v in schema.items()]
    return "{\n" + pad + "    " + (",\n" + pad + "    ").join(fields) + "\n" + pad + "}"


# Ordrens objekter som rader { Code, Description }: udstyret, naar der er
# et, ellers den funktionelle lokation. Planens egen FL (headerens) staar
# ikke i Object list - den er itemets FL (build_items.build_object_list_modal).
_OBJ_ROWS = (
    "Filter(\n"
    "    ForAll(\n"
    "        objs As OB,\n"
    "        With(\n"
    "            { eq: Coalesce(Trim(Text(OB.Value.equipment)), \"\") },\n"
    "            {\n"
    "                Code: If(eq = \"\", Coalesce(Trim(Text(OB.Value.functionalLocation)), \"\"), eq),\n"
    "                Description: If(eq = \"\", Coalesce(Trim(Text(OB.Value.functionalLocationDescription)), \"\"),\n"
    "                                 Coalesce(Trim(Text(OB.Value.equipmentDescription)), \"\"))\n"
    "            }\n"
    "        )\n"
    "    ),\n"
    "    Code <> \"\" && Code <> fl\n"
    ")"
)


def fetch_fx():
    """Fetch order: koer flowet, laes result og opret item + operationer."""
    import build_items as bi
    item = _record("colVhpItems", {
        "ItemId": "varVhpNextItemId",
        "ShortText": "Left(Coalesce(Trim(Text(hdr.shortDescription)), \"\"), 40)",
        "FunctionalLocation": "If(keepFl, fl, \"\")",
        "FlDescription": "If(keepFl, Coalesce(Trim(Text(LookUp(objs, Trim(Text(ThisRecord.Value.functionalLocation)) = fl).Value.functionalLocationDescription)), \"\"), \"\")",
        "MainWorkCenter": "If(IsBlank(LookUp(colVhpMainWorkCenters, Value = wc).Value), \"\", wc)",
        "ObjectList": "If(keepFl, Concat(Sort(objRows, Code), Code, \"; \"), \"\")",
        "Initials": "Coalesce(Upper(Trim(Text(hdr.responsibleInitials))), Upper(First(Split(varVhpMe, \"@\")).Value))",
        "LongText": "Coalesce(Trim(Text(ht.text)), Trim(Text(hdr.description)), \"\")",
        "NonFlowUserStatus": "If(CountRows(Filter(sts, Text(ThisRecord.Value.id) = \"ZBOW\" && Boolean(ThisRecord.Value.active))) > 0, \"ZBOW\", \"\")",
        "Status": "\"draft\"",
        "ItemGuid": "Text(GUID())",
    }, 12)
    op = _record("colVhpOperations", {
        "ItemId": "varVhpNextItemId",
        "OperationNo": "Text(Value(O.Value.id), \"0000\")",
        "OperationShortText": "Coalesce(Trim(Text(O.Value.description)), \"\")",
        "WorkHours": "Coalesce(Value(O.Value.actualHours), 0)",
        "Persons": "1",
        # Een person (se ovenfor): varigheden er arbejdet (sp_config.duration_expr).
        "DurationHours": "Round(Coalesce(Value(O.Value.actualHours), 0), 2)",
        "MainWorkCenter": "Coalesce(Trim(Text(O.Value.workCenter)), \"\")",
        "ControlKey": "Coalesce(Trim(Text(O.Value.controlKey)), \"\")",
        "Vendor": ("If(Coalesce(Value(O.Value.vendorId), 0) > 0, "
                   "Text(Value(O.Value.vendorId)) & \" - \" & Coalesce(Trim(Text(O.Value.vendorName)), \"\"), \"\")"),
        # data er en tekst (ikke et objekt), naar OperationText ikke svarede 200 -
        # .text paa en tekst er en fejl i Power Fx, derfor IfError.
        "LongText": ("IfError(Coalesce(Trim(Text(LookUp(txts, Text(ThisRecord.Value.objectId) = Text(O.Value.objectId))"
                     ".Value.data.text)), \"\"), \"\")"),
    }, 16)
    return (
        "With(\n"
        f"    {{ o: Trim({INPUT}.Text) }},\n"
        "    If(\n"
        "        !varVhpPlanCommitted,\n"
        "        Notify(\"Press Save in the plan header before adding items.\", NotificationType.Warning),\n"
        "        IsBlank(o) || !IsNumeric(o),\n"
        f"        Set({MSG}, \"Type the SAP order number (digits only).\"),\n"
        f"        Set({BUSY}, true);\n"
        f"        Set({MSG}, \"\");\n"
        "        IfError(\n"
        f"            Set({RAW}, {ORDER_FLOW}.Run(o));\n"
        "            If(\n"
        f"                {RAW}.ok <> \"yes\",\n"
        f"                Set({MSG}, \"Order \" & o & \" could not be fetched: \" & Coalesce({RAW}.message, \"no answer\")),\n"
        "                With(\n"
        f"                    {{ r: ParseJSON({RAW}.result) }},\n"
        "                    With(\n"
        "                        {\n"
        # Sektioner, der ikke svarede 200, har et fejlobjekt eller en tekst i
        # data - ikke en liste/record. Table() af det ville fejle, og et felt
        # paa en tekst er en fejl, saa de bliver tomme tabeller/records.
        "                            hdr: If(Value(r.header.status) = 200, r.header.data, ParseJSON(\"{}\")),\n"
        "                            ht: If(Value(r.headerText.status) = 200, r.headerText.data, ParseJSON(\"{}\")),\n"        "                            ops: If(Value(r.operations.status) = 200, Table(r.operations.data), Table(ParseJSON(\"[]\"))),\n"
        "                            objs: If(Value(r.objects.status) = 200, Table(r.objects.data), Table(ParseJSON(\"[]\"))),\n"
        "                            sts: If(Value(r.status.status) = 200, Table(r.status.data), Table(ParseJSON(\"[]\"))),\n"
        "                            txts: Table(r.operationTexts)\n"
        "                        },\n"
        "                        With(\n"
        "                            { fl: Coalesce(Trim(Text(hdr.functionalLocation)), \"\") },\n"
        "                        With(\n"
        "                            {\n"
        f"                                keepFl: fl <> \"\" && !{bi.fl_wrong_plant('fl')},\n"
        "                                wc: Coalesce(Trim(Text(First(ops).Value.workCenter)), \"\"),\n"
        f"                                objRows: {_OBJ_ROWS.replace(chr(10), chr(10) + ' ' * 32)}\n"
        "                            },\n"
        "                            Set(varVhpNextItemId, varVhpNextItemId + 1);\n"
        "                            Collect(\n"
        "                                colVhpItems,\n"
        f"                                {item.replace(chr(10), chr(10) + ' ' * 20)}\n"
        "                            );\n"
        # Collect UDEN OM ForAll (App checker: ForAllWithMutation).
        "                            Collect(\n"
        "                                colVhpOperations,\n"
        "                                ForAll(\n"
        "                                    ops As O,\n"
        f"                                    {op.replace(chr(10), chr(10) + ' ' * 20)}\n"
        "                                )\n"
        "                            );\n"
        "                            Collect(\n"
        "                                colVhpItemObjects,\n"
        "                                ForAll(\n"
        "                                    Filter(objRows, keepFl) As X,\n"
        "                                    { ItemId: varVhpNextItemId, Code: X.Code, Description: X.Description }\n"
        "                                )\n"
        "                            );\n"
        "                            Set(varVhpActiveItemId, varVhpNextItemId);\n"
        "                            Set(varVhpItemValidated, false);\n"
        "                            Set(varVhpFlMsg, \"\");\n"
        f"                            {bi.SEED_FL_PICKER.replace(chr(10), ' ')};\n"
        f"                            {bi.RESET_EDITOR_CONTROLS};\n"
        f"                            Set({OPEN}, false);\n"
        "                            Notify(\n"
        "                                \"Item \" & Text(CountRows(colVhpItems)) & \" created from order \" & o & \" with \" & Text(CountRows(ops)) & \" operations.\" &\n"
        "                                    If(fl <> \"\" && !keepFl, \" Functional Location and objects cleared - they do not belong to plant \" & " + bi.FL_PLANT_PREFIX + " & \".\", \"\") &\n"
        "                                    If(Value(r.header.status) = 200, \"\", \" The order header answered \" & Text(Value(r.header.status)) & \".\"),\n"
        "                                NotificationType.Success\n"
        "                            )\n"
        "                        )\n"
        "                        )\n"
        "                    )\n"
        "                )\n"
        "            ),\n"
        f"            Set({MSG}, \"The order lookup failed. Try again.\")\n"
        "        );\n"
        f"        Set({BUSY}, false)\n"
        "    )\n"
        ")"
    )


OPEN_FX = (
    f"Set({MSG}, \"\"); Reset({INPUT}); Set({OPEN}, true)"
)
CLOSE_FX = f"If(!{BUSY}, Set({OPEN}, false))"


def order_button():
    """Ikonknappen i Items-kortets hoved, mellem Copy og Add item. Samme
    vilkaar som Add item (ikke i View). Under Tablet er der ikke plads
    (Add item er allerede kun sit plus der), saa den er skjult paa en
    telefon."""
    btn = button(BTN_HEAD, "\"\"", OPEN_FX,
                 display_mode="If(varVhpViewOnly, DisplayMode.Disabled, DisplayMode.Edit)",
                 visible=f"!varVhpViewOnly && {at_least('Tablet')}")
    btn.props.update({
        "Icon": f"\"{icons.FLUENT['search']}\"",
        "Layout": "ButtonLayout.IconOnly",
        "AccessibleLabel": "\"Item from SAP order\"",
        "Tooltip": "\"Create an item from a SAP order\"",
        "Width": "36", "Height": "36", "LayoutMinWidth": "36",
    })
    ensure_hit(btn)
    btn.props["LayoutMinWidth"] = btn.props["Width"]
    return btn


def build_order_modal():
    title = text_ctrl("txtVhpOrderTitle", "\"Item from SAP order\"",
                      size=lay.SIZE_CARD_TITLE, weight="Semibold", height=26, wrap="false")
    headRow = popup_head("conVhpOrderHeadRow", title, "btnVhpOrderClose", CLOSE_FX,
                         accessible="\"Close without creating an item\"")
    note = text_ctrl(
        "txtVhpOrderNote",
        "\"The order's header becomes a new item and its operations the task list. "
        "You can change everything before you save.\"",
        size=13, color=C_MUTED, height=40, wrap="true")

    # Telefonen (issue #508): feltet er 44 hoejt som de andre popup-felter.
    inp = text_input(INPUT, "\"\"", placeholder="\"SAP order number, e.g. 25711067\"",
                     max_length=12, width="Parent.Width", label="\"SAP order number\"",
                     height=lay.mobile_or(mobile.TOUCH, 36),
                     display_mode=f"If({BUSY}, DisplayMode.View, DisplayMode.Edit)")
    grow(inp)
    btnFetch = button(
        BTN_FETCH, f"If({BUSY}, \"Fetching...\", \"Fetch order\")", fetch_fx(),
        primary=True, width=lay.mobile_or(POP_CW_M, 150), height=lay.mobile_or(mobile.TOUCH, 36),
        icon=icons.FLUENT["search"],
        display_mode=f"If({BUSY} || varVhpViewOnly, DisplayMode.Disabled, DisplayMode.Edit)")
    # Telefonen: feltet over knappen; ellers paa een linje.
    row = group("conVhpOrderRow", [inp, btnFetch], direction="Horizontal", gap=10,
                height=lay.mobile_or(2 * mobile.TOUCH + 10, 36), align_items="Center")
    row.props["LayoutDirection"] = lay.mobile_or("LayoutDirection.Vertical", "LayoutDirection.Horizontal")
    inp.props["Width"] = lay.mobile_or(POP_CW_M, inp.props["Width"])

    msg = text_ctrl("txtVhpOrderMsg", MSG, size=13, color=C_MUTED, height=40, wrap="true")
    msg.vis = f"!IsBlank({MSG})"
    msg.props["Visible"] = msg.vis

    modal = group(
        MODAL, [headRow, note, row, msg], direction="Vertical", gap=12,
        fill=C_MODAL_BG, border_color=C_PRIMARY_SOFT, radius=lay.RADIUS_MODAL,
        pad=(18, 18, 18, 18), width=lay.popup_w(560, 40), drop_shadow="ExtraBold",
        visible=OPEN)
    mobile_pad(modal, x=mobile.CARD_PAD)
    modal.props["X"] = "(App.Width - Self.Width) / 2"
    modal.props["Y"] = mobile.sheet_y("Max(20, (App.Height - Self.Height) / 3)")
    return modal
