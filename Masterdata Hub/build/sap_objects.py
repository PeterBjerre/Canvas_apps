# -*- coding: utf-8 -*-
"""
SAP OBJECT - kolonnen i hubbens Closed-visning og popuppen bag den
(issue #471).

HVAD BRUGEREN SER
-----------------
Kolonnen SAP OBJECT (build_hub.SAP_COL) har et lille link-ikon, naar
anmodningen er oprettet i SAP. Et tryk aabner en skrivebeskyttet popup med
de SAP-objekter, anmodningen har oprettet: objekttypen, SAP-nummeret (som
tekst, der kan markeres og kopieres), et kopier-ikon lige efter nummeret
(ca. et mellemrums afstand, issue #504), en lodret skillestreg og en
beskrivelse. Yderst til hoejre staar een indrammet knap med SAP-maerket og
et "aaben eksternt"-ikon. Den er den ENE "Open in SAP"-handling (issue
#500/#504) og vises KUN, naar en hel, gyldig URL kan dannes. Efter en
kopiering skifter ikonet kort til et flueben, og "Copied" staar i raekken.

    SAP-nummer [kopier] | beskrivelse                 [SAP ->]

INGEN EKSTRA KALD VED START
---------------------------
Ikonet afgoeres af indeksraekken alene (MD_RequestIndex: SapObjectNo eller
Status = OprettetISAP), som galleriet allerede har. Domaenets raekker og
WebGUI-adressen hentes FOERST, naar popuppen aabnes - eet delegeret Filter
pr. liste paa de samme kolonner, som sletningen bruger
(tools/request_delete.py): RequestGuid, MaintenancePlanNo.Value og ID.

HVOR NUMRENE STAAR (sharepoint/inspect/out/schema.json)
------------------------------------------------------
  MaintenancePlan     MaintenancePlans.SAPNum (planen, ID = SourceItemId)
                      MaintenanceItems.SapItemNo, TaskListGroup,
                      TaskListGroupCounter (kvitteringsflowet,
                      flow/sap-ordre/kvittering-3/4)
  FunctionalLocation  FunctionalLocationItems.FunctionalLocation, naar
                      SapResult er Created (IL01) eller Updated (IL02)
  Material            MaterialItems.CreatedMaterialNo
  Equipment           EquipmentItems.EquipmentNumber
  MeasuringPoint      MeasuringPointItems.CreatedMeasuringPointNo

WEBGUI-ADRESSEN
---------------
Vaerten staar IKKE i repoet (det er offentligt). Den laeses fra
AppSettings: raekken med Option = SapWebGuiBaseUrl og miljoeets
Environment, kolonnen AppUrl (Provision-VHPlanApproval.ps1). Den kan
skrives som "https://<vaert>:<port>" eller med hele stien
".../webgui"; mangler "/webgui", saettes det paa. Er raekken tom eller
ikke https, vises numrene uden link-ikoner.

URL-MOENSTRENE er dem fra issuet/WebGUI (TX nedenfor). Numrene saettes ind
med EncodeUrl og kommer altid fra raekkens egne vaerdier.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import (Ctrl, C_OVERLAY, C_MODAL_BG, C_PRIMARY_SOFT, C_MUTED, C_TITLE,
                        C_TRANSPARENT, C_ROW_HOVER, C_ROW_PRESSED, C_PRIMARY, C_DIVIDER,
                        C_MUTED_BG, C_INPUT_BORDER, C_VALID_FG)
from build_helpers import (group, text_ctrl, grow, spinner, close_x, text_input, ensure_hit,
                           button)
from hub_config import DOMAINS
import layout_tokens as lay
import request_index as ri
import env_config as env
import approval_flow

OPEN = "IfError(varMdSapOpen, false)"
BUSY = "IfError(varMdSapBusy, false)"
CLOSE = "Set(varMdSapOpen, false)"
R = "varMdSapReq"
ROWS = "colMdSapRows"
BASE = "varMdSapBase"

# AppSettings (som VH-planens omkostningsgraense, R2-082).
SETTINGS = "AppSettings"
OPTION = "SapWebGuiBaseUrl"
SETTINGS_ENV = env.ENV_NAME.upper()

# Measuring Point-listen findes kun i appen, naar featuren er slaaet til.
MP_ON = env.feature_on("measuring_point")

# Ikonet i kolonnen: kun ud fra indeksraekken - intet opslag pr. raekke.
HAS_SAP = f'(!IsBlank(ThisItem.SapObjectNo) || ThisItem.Status.Value = "{ri.CREATED}")'
TIP = "View SAP objects"

# ---------------------------------------------------------------------------
# URL'erne. (transaktion, [felter], hale). Felterne faar raekkens vaerdier i
# raekkefoelge. Plan, item og opgaveliste er issuets moenstre; IL03 bruger
# feltet fra excel/opretter/VhpConfig.bas (IL03_FL), de tre sidste SAP's
# standardfelter paa visningsskaermene (ikke efterproevet mod Oersteds SAP).
# ---------------------------------------------------------------------------
TX = {
    "plan": ("IP03", ["RMIPM-WARPL"], ";&sap-language=EN"),
    "item": ("IP06", ["RMIPM-WAPOS"], "&sap-language=EN"),
    "tasklist": ("IA06", ["RC271-PLNNR", "RC271-PLNAL"], ";&sap-language=EN;DYNP_OKCODE=VOUE"),
    "fl": ("IL03", ["IFLO-TPLNR"], ";&sap-language=EN"),
    "equipment": ("IE03", ["RM63E-EQUNR"], ";&sap-language=EN"),
    "material": ("MM03", ["RMMG1-MATNR"], ";&sap-language=EN"),
    "mp": ("IK03", ["IMPT-POINT"], ";&sap-language=EN"),
}


def url_fx(kind, *values):
    """Power Fx: hele WebGUI-URL'en - eller "" naar adressen eller en af
    vaerdierne mangler. values er Power Fx-tekstudtryk."""
    tcode, fields, tail = TX[kind]
    if len(values) != len(fields):
        raise SystemExit(f"sap_objects.url_fx: {kind} skal have {len(fields)} vaerdier")
    parts = ";".join(f'{f}=" & EncodeUrl(Trim({v})) & "' for f, v in zip(fields, values))
    ok = " && ".join([f"!IsBlank({BASE})"] + [f"!IsBlank(Trim({v}))" for v in values])
    return f'If({ok}, {BASE} & "?~transaction=*{tcode}%20{parts}{tail}", "")'


# Adressen fra AppSettings, renset: uden "/" til sidst, "/webgui" paa,
# hvis den mangler, og "" hvis den ikke er https.
BASE_FX = (
    f'With({{ u: Trim(Coalesce(LookUp({SETTINGS}, Option.Value = "{OPTION}" && '
    f'Environment.Value = "{SETTINGS_ENV}").AppUrl, "")) }},\n'
    '    With({ t: If(EndsWith(u, "/"), Left(u, Len(u) - 1), u) },\n'
    '        If(\n'
    '            !StartsWith(Lower(t), "https://") || Len(t) <= 8, "",\n'
    '            EndsWith(Lower(t), "/webgui"), t,\n'
    '            t & "/webgui"\n'
    '        )\n'
    '    )\n'
    ')'
)


def _rec(lvl, kind, no, desc, url):
    return f"{{ Lvl: {lvl}, Kind: {kind}, No: {no}, Desc: {desc}, Url: {url} }}"


def _flat(src, key, sort, kind, no, desc, url_kind):
    """Een raekke pr. objekt i en domaeneliste (FL, Material, Equipment,
    MP). Filteret er delegeret (RequestGuid); raekker uden nummer faldt
    fra bagefter."""
    no_fx = f'Coalesce({no}, "")'
    return (f"Filter(\n        ForAll(\n            Sort(Filter({src}, {key} = varMdSapGuid), {sort}) As R,\n"
            f"            {_rec(0, kind, no_fx, desc, url_fx(url_kind, no_fx))}\n"
            "        ),\n        !IsBlank(No)\n    )")


def _plan_rows():
    """Planen oeverst, saa hvert item med sin opgaveliste under sig."""
    p = "varMdSapPlan"
    plan_no = f'Coalesce({p}.SAPNum, "")'
    plan = _rec(0, '"Maintenance plan"', plan_no, f'Coalesce({p}.Title, "")', url_fx("plan", plan_no))
    item_no = 'Coalesce(I.SapItemNo, "")'
    grp, cnt = 'Coalesce(I.TaskListGroup, "")', 'Coalesce(I.TaskListGroupCounter, "")'
    item = _rec(1, '"Maintenance item"', item_no, 'Coalesce(I.Title, "")', url_fx("item", item_no))
    task = _rec(2, '"Task list"', grp,
                f'If(IsBlank({cnt}), "", "Group counter " & {cnt})', url_fx("tasklist", grp, cnt))
    items = ("Ungroup(\n            ForAll(\n"
             "                Sort(Filter(MaintenanceItems, MaintenancePlanNo.Value = varMdSapKey), ID) As I,\n"
             f"                {{ r: Table(\n                    {item},\n                    {task}\n                ) }}\n"
             "            ),\n            r\n        )")
    return (f"Set({p}, LookUp(MaintenancePlans, ID = varMdSapSp));\n"
            f"ClearCollect(\n    {ROWS},\n    Filter(\n        Ungroup(\n            Table(\n"
            f"                {{ r: Table({plan}) }},\n"
            f"                {{ r: {items} }}\n"
            "            ),\n            r\n        ),\n        !IsBlank(No)\n    )\n)")


def _domain_rows():
    """{domaene: formel, der fylder colMdSapRows}."""
    out = {"MaintenancePlan": _plan_rows()}
    flat = {
        "FunctionalLocation": _flat(
            "FunctionalLocationItems", "RequestGuid", "RowNo",
            'If(R.SapResult = "Updated", "Functional location (updated)", "Functional location")',
            'If(R.SapResult = "Created" || R.SapResult = "Updated", R.FunctionalLocation, "")',
            'Coalesce(R.Description, "")', "fl"),
        "Material": _flat("MaterialItems", "RequestGuid", "RowId", '"Material"',
                          "R.CreatedMaterialNo", 'Coalesce(R.MaterialDescription, "")', "material"),
        "Equipment": _flat("EquipmentItems", "RequestGuid", "RowId", '"Equipment"',
                           "R.EquipmentNumber", 'Coalesce(R.Description, "")', "equipment"),
    }
    if MP_ON:
        flat["MeasuringPoint"] = _flat(
            "MeasuringPointItems", "RequestGuid", "RowId", '"Measuring point"',
            "R.CreatedMeasuringPointNo", 'Coalesce(R.Description, "")', "mp")
    for k, fx in flat.items():
        out[k] = f"ClearCollect(\n    {ROWS},\n    {fx}\n)"
    return out


def open_fx(rec="ThisItem"):
    """Ikonets OnSelect: popuppen aabnes, og FOERST nu hentes objekterne."""
    branches = ",\n".join(
        f'    "{d}",\n' + "\n".join("        " + l for l in fx.split("\n"))
        for d, fx in _domain_rows().items())
    return (f"Set({R}, {rec});\n"
            f"Set(varMdSapGuid, {rec}.RequestGuid);\n"
            f"Set(varMdSapKey, {rec}.{ri.COL_NO});\n"
            f"Set(varMdSapSp, {rec}.SourceItemId);\n"
            f"Clear({ROWS});\n"
            f'Set({COPIED_VAR}, "");\n'
            "Set(varMdSapBusy, true);\n"
            "Set(varMdSapOpen, true);\n"
            f"Set({BASE}, {BASE_FX});\n"
            f"Switch(\n    {rec}.Domain.Value,\n{branches}\n);\n"
            "Set(varMdSapBusy, false)")


# Hver anmodningstype sin forklaring under titlen - kolonnerne og
# hierarkiet er forskellige (issuet: "Design each popup according to the
# available object data").
HINT = {
    "MaintenancePlan": "The plan, its items and each item's task list (group and group counter).",
    "FunctionalLocation": "Functional locations created or updated in SAP.",
    "Material": "Material numbers created in SAP.",
    "Equipment": "Equipment numbers created in SAP.",
    "MeasuringPoint": "Measuring points created in SAP.",
}
HINT_FX = ("Switch(" + R + ".Domain.Value, " +
           ", ".join(f'"{k}", "{v}"' for k, v in HINT.items()) + ', "")')
EMPTY_TEXT = '"No SAP numbers have been recorded for this request yet."'
# Kort, lokal kvittering efter en kopiering (issue #504): raekkens noegle
# staar i COPIED_VAR, til timeren nulstiller den efter COPIED_MS. Noeglen
# er type + nummer + beskrivelse - to opgavelister kan have samme gruppe.
COPIED_VAR = "varMdSapCopied"
COPIED_MS = 2000
ROW_KEY = 'ThisItem.Kind & "|" & ThisItem.No & "|" & ThisItem.Desc'
COPIED = f'(IfError({COPIED_VAR}, "") = {ROW_KEY})'

# Maal (issue #488, mockuppen pictures/sap_popup.png). Hvert objekt er
# een galleriraekke: en graa sektionsbjaelke med objekttypen og under den
# raekken med nummeret. Bjaelke og raekke rykkes ind pr. niveau (plan 0,
# item 1, opgaveliste 2), og et lille "L" foran bjaelken viser, at den
# hoerer under raekken ovenover. Ikonerne til hoejre staar paa SAMME x i
# alle niveauer.
POP_MAX_W = 640
POP_PAD = 16
# Naesten fuld bredde paa en telefon (issue #508, layout_tokens.popup_w).
POP_W = lay.popup_w(POP_MAX_W, 24)
GW = f"({POP_W} - {2 * POP_PAD})"
MAX_ROWS = 5
INDENT = 28
BAR_Y = 6            # luft over bjaelken - ogsaa mellem to niveauer
BAR_H = 32
LINE_H = 48          # raekken med nummeret
ROW_H = BAR_Y + BAR_H + LINE_H
GUIDE = 12           # den lodrette streg foran nummeret, fra niveauets x
NO_X = 18            # nummerets felt, fra niveauets x
NO_H = 32
LINK = 32
# Open in SAP-knappen (issue #504, pictures/sap_popup_copy.png): SAP-maerket
# og et "aaben eksternt"-ikon i een indrammet knap.
SAP_LOGO_W = 78
# Kopier-ikonet lige ved nummeret - kun et almindeligt mellemrums afstand
# (issue #504; Segoe UI's mellemrum er ca. 0,27 em = 4 px ved 14 px).
# Nummerfeltet er saa bredt som teksten (skoen nedenfor), og kopier-
# knappen placeres, saa selve symbolet staar COPY_GAP efter tekstens
# slutning. Fluents tekstfelt har ca. 13 px fra kanten til teksten (1 kant
# + 10 + 2 polstring). Segoe UI's cifre er 0,566 em (tabelcifre); numre med
# bogstaver eller bindestreg skoennes rummeligere. Ikon-knappens symbol er
# 20 px og staar midt i knappen.
NO_PAD = 13
NO_CH_DIGITS = 0.57
NO_CH = 0.6
COPY_GAP = 4
COPY_ICON = 20
NO_SEP_GAP = 14      # kopier-symbolet -> skillestregen (uden for knappens touch-flade)
DESC_GAP = 14        # skillestregen -> beskrivelsen
SB = 12              # plads til galleriets scrollbar
EDGE = f"({GW} - {SB})"            # bjaelkernes hoejre kant
RIGHT = f"({EDGE} - 8)"            # SAP-knappens hoejre kant - alle niveauer

# Knapindholdet: SAP-fladen med "SAP" i hvidt og et "aaben eksternt"-ikon
# til hoejre. I appens brandfarve, saa den foelger temaet - farver staar
# kun i design_tokens.py. Ramme, flade og tilstande er Image-kontrollens
# egne (se build_popup), saa HELE knappen er een klikflade.
OPEN_LABEL = '"Open in SAP"'
COPY_LABEL = '"Copy SAP number"'
COPIED_LABEL = '"Copied"'
def _sap_logo_uri():
    fill = '" & ' + _ref("color-brand-primary") + ' & "'
    ink = '" & ' + _ref("text-on-primary") + ' & "'
    svg = (f"<svg xmlns='http://www.w3.org/2000/svg' width='{SAP_LOGO_W}' height='{LINK}' "
           f"viewBox='0 0 {SAP_LOGO_W} {LINK}'>"
           f"<path d='M10 6h40L30 26H10Z' fill='{fill}'/>"
           "<text x='12.5' y='20.5' font-family='Arial, Helvetica, sans-serif' font-size='13' "
           f"font-weight='700' font-style='italic' fill='{ink}'>SAP</text>"
           f"<path d='M60 10h-5v13h13v-5M62 9h7v7M69 9l-8 8' fill='none' stroke='{fill}' "
           "stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'/></svg>")
    return '"data:image/svg+xml;utf8," & EncodeUrl("' + svg + '")'


def _ref(token):
    from design_tokens import ref_hex
    return ref_hex(token)


def _line(name, x, y, w, h, visible=None, label="Divider"):
    """En tynd streg (hierarkiets "L", stregen foran nummeret, skillestreger).
    En Rectangle - en tom tekst kan ikke vaere lavere end een tekstlinje."""
    props = {
        "AccessibleLabel": f'"{label}"', "BorderStyle": "BorderStyle.None", "BorderThickness": "0",
        "Fill": C_DIVIDER, "Height": str(h), "OnSelect": "false", "TabIndex": "0",
        "Width": str(w), "X": str(x), "Y": str(y),
    }
    if visible is not None:
        props["Visible"] = visible
    return Ctrl(name, "Rectangle", props=props, h=h, vis=visible)


def build_popup():
    n = lambda kind, base: f"{kind}MdSap{base}"
    x0 = f"ThisItem.Lvl * {INDENT}"
    line_y = BAR_Y + BAR_H
    # Hierarkiet: et "L" fra forrige niveaus streg ind til bjaelken.
    up_x = f"(ThisItem.Lvl - 1) * {INDENT} + {GUIDE}"
    l_v = _line(n("rct", "TreeV"), up_x, 0, 1, BAR_Y + BAR_H // 2, visible="ThisItem.Lvl > 0",
                label="Hierarchy")
    l_h = _line(n("rct", "TreeH"), up_x, BAR_Y + BAR_H // 2, INDENT - GUIDE - 4,
                1, visible="ThisItem.Lvl > 0", label="Hierarchy")
    # Den graa sektionsbjaelke med objekttypen. Een tekst med fyld og runde
    # hjoerner - en container i et galleri flades ud og mister sin X.
    bar = text_ctrl(n("txt", "Kind"), "ThisItem.Kind", size=lay.SIZE_BODY, weight="Semibold",
                    color=C_TITLE, height=BAR_H, wrap="false", fill=C_MUTED_BG,
                    width=f"Max(0, {EDGE} - ({x0}))",
                    extra={"X": x0, "Y": str(BAR_Y), "PaddingLeft": "12", "PaddingRight": "12",
                           "VerticalAlign": "VerticalAlign.Middle",
                           "RadiusTopLeft": "6", "RadiusTopRight": "6",
                           "RadiusBottomLeft": "6", "RadiusBottomRight": "6"})
    # Den lodrette streg foran nummeret - under bjaelkens venstre kant.
    guide = _line(n("rct", "Guide"), f"{x0} + {GUIDE}", line_y + 8, 1, LINE_H - 16,
                  label="Hierarchy")
    # Nummeret: et skrivebeskyttet tekstfelt (View), saa det kan markeres
    # og kopieres - en ModernText kan ikke markeres. Uden ramme og fyld
    # (issue #488): det ser ud som almindelig tekst.
    no = text_input(n("inp", "No"), "ThisItem.No", height=NO_H, width="0",
                    display_mode="DisplayMode.View",
                    label='ThisItem.Kind & " SAP number " & ThisItem.No')
    # Feltet er saa bredt som teksten + polstring i begge sider. Skriften
    # er stoerre paa mobil (input_theme), saa bredden foelger feltets Size.
    # Rene cifre (de fleste SAP-numre) er smallere end bogstaver.
    ch = f'If(IsMatch(ThisItem.No, "[0-9]+"), {NO_CH_DIGITS}, {NO_CH})'
    text_w = f"Len(ThisItem.No) * {ch} * ({no.props['Size']})"
    no_w = f"Min(240, RoundUp(2 * {NO_PAD} + {text_w}, 0))"
    no.props["Width"] = no_w
    no.props.update({
        # input_theme giver allerede Outline i View (gennemsigtig flade);
        # her fjernes ogsaa kanten.
        "BorderColor": C_TRANSPARENT,
        "BorderStyle": "BorderStyle.None", "BorderThickness": "0", "Fill": C_TRANSPARENT,
        "Color": C_TITLE, "X": f"{x0} + {NO_X}", "Y": f"{line_y} + ({LINE_H} - {NO_H}) / 2",
    })
    # Kopier-ikonet hoerer til nummeret (issue #500/#504): symbolet staar
    # COPY_GAP efter tekstens slutning - knappens egen luft om symbolet
    # ((bredde - 20) / 2) traekkes fra, saa afstanden er den samme paa
    # desktop (32) og touch (44). Efter et tryk er ikonet kort et flueben,
    # og "Copied" staar i raekken (lokal kvittering i stedet for et banner).
    copy_label = f"If({COPIED}, {COPIED_LABEL}, {COPY_LABEL})"
    copy = button(n("btn", "Copy"), '""',
                  f"Copy(ThisItem.No);\nSet({COPIED_VAR}, {ROW_KEY})",
                  width=LINK, height=LINK, icon=f'If({COPIED}, "Checkmark", "Copy")',
                  accessible=copy_label, tooltip=copy_label)
    copy.props["Layout"] = "ButtonLayout.IconOnly"
    copy.props["BorderColor"] = C_TRANSPARENT
    copy.props["AlignInContainer"] = "AlignInContainer.Start"
    ensure_hit(copy)
    copy_w = copy.props["Width"]
    text_end = f"{x0} + {NO_X} + {NO_PAD} + Min(240 - {2 * NO_PAD}, {text_w})"
    copy_x = f"{text_end} + {COPY_GAP} - ({copy_w} - {COPY_ICON}) / 2"
    copy.props["X"] = copy_x
    copy.props["Y"] = f"{line_y} + ({LINE_H} - Self.Height) / 2"
    # Til hoejre: een indrammet knap (SAP-maerke + "aaben eksternt"-ikon)
    # er den ENE "Open in SAP"-handling (issue #500/#504), yderst til
    # hoejre paa samme x i alle niveauer. Knappens ramme skiller den fra
    # beskrivelsen - ingen skillestreg foran (issue #504). Kun naar en hel
    # URL kunne dannes (url_fx giver "" ellers). Hele knappen er een
    # Image, saa et tryk hvor som helst paa den aabner det samme link.
    # Hover, tryk og tastaturfokus ses som flade og kant.
    has_url = "!IsBlank(ThisItem.Url)"
    logo = Ctrl(n("img", "Logo"), "Image", props={
        "AccessibleLabel": OPEN_LABEL,
        "BorderColor": C_INPUT_BORDER, "BorderStyle": "BorderStyle.Solid", "BorderThickness": "1",
        "Fill": C_TRANSPARENT, "Height": str(LINK),
        "HoverBorderColor": C_PRIMARY, "HoverFill": C_ROW_HOVER,
        "PressedBorderColor": C_PRIMARY, "PressedFill": C_ROW_PRESSED,
        "Image": _sap_logo_uri(),
        "ImagePosition": "ImagePosition.Center",
        "OnSelect": "Launch(ThisItem.Url)", "TabIndex": "0",
        "FocusedBorderColor": C_PRIMARY, "FocusedBorderThickness": "2",
        "Tooltip": OPEN_LABEL, "Visible": has_url,
        "Width": str(SAP_LOGO_W), "X": f"{RIGHT} - {SAP_LOGO_W}",
        "Y": f"{line_y} + ({LINE_H} - {LINK}) / 2",
        "RadiusTopLeft": "6", "RadiusTopRight": "6", "RadiusBottomLeft": "6", "RadiusBottomRight": "6",
    }, h=LINK, vis=has_url)
    ensure_hit(logo, square=False)
    logo.props["Y"] = f"{line_y} + ({LINE_H} - Self.Height) / 2"
    logo_x = logo.props["X"]
    # Skillestregen mellem nummer/kopier-gruppen og beskrivelsen - den
    # eneste i raekken (issue #504). Den staar uden for kopier-knappens
    # touch-flade (symbol + 12 px luft).
    sep_x = f"{text_end} + {COPY_GAP + COPY_ICON + NO_SEP_GAP}"
    sep = _line(n("rct", "NoSep"), sep_x, line_y + 10, 1, LINE_H - 20)
    # Beskrivelsen efter skillestregen med tydelig luft (DESC_GAP).
    desc_x = f"{sep_x} + {1 + DESC_GAP}"
    desc_end = f"If({has_url}, {logo_x} - 12, {RIGHT})"
    desc_w = f"Max(0, {desc_end} - ({desc_x}))"
    desc = text_ctrl(n("txt", "Desc"), "ThisItem.Desc", size=lay.SIZE_BODY, color=C_TITLE,
                     height=LINE_H - 8, wrap="true", width=desc_w, visible=f"!{COPIED}",
                     extra={"X": desc_x, "Y": f"{line_y} + 4",
                            "VerticalAlign": "VerticalAlign.Middle"})
    # "Copied" staar kort paa beskrivelsens plads efter en kopiering.
    copied = text_ctrl(n("txt", "Copied"), COPIED_LABEL, size=lay.SIZE_BODY, weight="Semibold",
                       color=C_VALID_FG, height=LINE_H - 8, wrap="false", width=desc_w,
                       visible=COPIED,
                       extra={"X": desc_x, "Y": f"{line_y} + 4",
                              "VerticalAlign": "VerticalAlign.Middle"})
    rule = _line(n("rct", "Rule"), x0, ROW_H - 1, f"Max(0, {EDGE} - ({x0}))", 1)
    gh = f"Min(CountRows({ROWS}), {MAX_ROWS}) * {ROW_H}"
    gal = Ctrl(n("gal", "Rows"), "Gallery", variant="Vertical", props={
        "AccessibleLabel": '"SAP objects"',
        "AlignInContainer": "AlignInContainer.Start",
        "BorderStyle": "BorderStyle.None", "Fill": C_TRANSPARENT, "FillPortions": "0",
        "Height": gh, "Items": ROWS, "LayoutMinWidth": "0",
        "Selectable": "false", "ShowScrollbar": "true", "TabIndex": "0",
        "TemplatePadding": "0", "TemplateSize": str(ROW_H),
        "Visible": f"!{BUSY} && !IsEmpty({ROWS})",
        "Width": GW, "WrapCount": "1",
    }, children=[l_v, l_h, bar, guide, no, desc, copied, sep, copy, logo, rule],
       h=MAX_ROWS * ROW_H)

    title = text_ctrl(n("txt", "Title"), '"SAP objects"', size=lay.SIZE_CARD_TITLE, weight="Semibold",
                      height=26, wrap="false", width="120")
    title.props["LayoutMinWidth"] = "120"
    badge = approval_flow.number_badge(n("bdg", "No"), R)
    spacer = grow(text_ctrl(n("txt", "HeadGap"), '""', size=lay.SIZE_MICRO, height=20,
                            accessible='"Spacer"'))
    head = group(n("con", "Head"), [title, badge, spacer, close_x(n("btn", "Close"), CLOSE)],
                 direction="Horizontal", gap=10, height=lay.HIT_TOUCH, align_items="Center")
    domain = ("Switch(" + R + ".Domain.Value, " +
              ", ".join(f'"{d["key"]}", "{d["name"]}"' for d in DOMAINS) + ', "Request")')
    sub = text_ctrl(n("txt", "Sub"), f'{domain} & "  ·  " & {R}.ShortText',
                    size=lay.SIZE_SMALL, color=C_MUTED, height=20, wrap="false")
    hint = text_ctrl(n("txt", "Hint"), HINT_FX, size=lay.SIZE_SMALL, color=C_MUTED, height=34,
                     wrap="true")
    spin = spinner(n("spn", "Spinner"), BUSY, '"Loading SAP objects"', width=GW, height=80)
    empty = text_ctrl(n("txt", "Empty"), EMPTY_TEXT, size=lay.SIZE_BODY, color=C_MUTED, height=40,
                      wrap="true", visible=f"!{BUSY} && IsEmpty({ROWS})")
    # Mockuppens Close-knap nederst er udeladt: popupper lukkes kun med X'et
    # (tests/test_popup_close.py).
    modal = group(n("con", "Modal"), [head, sub, hint, spin, empty, gal], direction="Vertical",
                  gap=8,
                  fill=C_MODAL_BG, border_color=C_PRIMARY_SOFT, radius=lay.RADIUS_MODAL,
                  pad=(POP_PAD, POP_PAD, POP_PAD, POP_PAD), width=POP_W, drop_shadow="ExtraBold",
                  align_in_container="Center")
    modal.props["Height"] = (f"{2 * POP_PAD + lay.HIT_TOUCH + 20 + 34 + 3 * 8} + "
                             f"If({BUSY}, 80, If(IsEmpty({ROWS}), 40, {gh}))")
    backdrop = group(n("con", "Backdrop"), [modal], direction="Vertical", gap=0,
                     height="App.Height", width="App.Width", fill=C_OVERLAY, visible=OPEN,
                     justify="Start", align_items="Center", pad=(16, 0, 16, 0), overflow_y="Scroll")
    backdrop.props["X"] = "0"
    backdrop.props["Y"] = "0"
    # Nulstiller "Copied" efter COPIED_MS (samme moenster som act_timer).
    copied_off = f'IsBlank(IfError({COPIED_VAR}, ""))'
    timer = Ctrl(n("tmr", "Copied"), "Timer", props={
        "AutoPause": "false",
        "AutoStart": "false",
        "Duration": str(COPIED_MS),
        "Height": "1",
        "OnTimerEnd": f'Set({COPIED_VAR}, "")',
        "Repeat": "false",
        "Reset": copied_off,
        "Start": f"!{copied_off}",
        "Visible": "false",
        "Width": "1",
    }, h=1, vis="false")
    return [backdrop, timer]
