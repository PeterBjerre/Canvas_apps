# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_screen import Ctrl, SHELL_W
from build_helpers import button, top_bar
from design_tokens import ref_hex

# Topbjaelken er ALT, der er tilbage af hero-kortet.
#
# Heroen var et kort oeverst i kroppen med beskrivelse, procestrin,
# statuslinje, "* Required" og "Show field help". Det er forenklet:
#
#   procestrin        -> trinindikatoren under titlen (stepper)
#   Show field help   -> EEN Help-kontakt i sidebaren. Den slaar baade
#   + de fire ? Help     feltforklaringerne og sektionernes hjaelpepaneler
#                        til og fra (varVhpShowHints).
#   * Required        -> Plan Header-kortet, ved siden af Step 1
#   beskrivelse       -> slettet
#   statuslinje       -> slettet (txtVhpRuntimeInfo)
#
# Validate staar i Dispatch and Control-kortet (trin 5), hvor rapporten
# staar - se build_tasklist.build_dispatch_section. Export JSON og "Send as
# email" er fjernet: planen sendes videre ved at gemme og indsende den.

# EEN hjaelpekontakt. Foer var der fem: "Show field help" i heroen og en
# "? Help" i hver af de fire sektioner. De slaar nu alle det samme til.
# Den staar i sidebarens fod ved temakontakten (tools/side_nav.py) - se
# assemble_screen.py.
HELP_ON = "IfError(varVhpShowHints, false)"
HELP_ACTION = f"Set(varVhpShowHints, !{HELP_ON})"


def validate_button():
    """Validering. Reglerne er de samme som i oplaegget (docs/01) - S1, S3,
    S4 og S5 gaelder kun strategiplaner."""
    return button(
        "btnVhpValidate", "\"Validate\"",
        (
            "Set(varVhpPlanValidated, true);\n"
            "Set(varVhpItemValidated, true);\n"
            "With(\n"
            "    { isStrat: varVhpPlan.PlanType = \"Strategy\" },\n"
            "    With(\n"
            "        {\n"
            "            itemErr:\n"
            "                Concat(\n"
            "                    Filter(\n"
            "                        colVhpItems,\n"
            "                        IsBlank(ShortText) || IsBlank(MainWorkCenter) || IsBlank(ActivityType) || IsBlank(FunctionalLocation)\n"
            "                    ),\n"
            "                    \"Item \" & Text(ItemId) & \" (\" & Coalesce(ShortText, \"no short text\") & \"): missing required fields.\",\n"
            "                    Char(10)\n"
            "                ),\n"
            "            s1:\n"
            "                If(isStrat && IsBlank(varVhpPlan.Strategy),\n"
            "                    \"S1: A strategy must be chosen on a strategy plan.\", \"\"),\n"
            "            s3:\n"
            "                If(isStrat,\n"
            "                    Concat(\n"
            "                        Filter(colVhpItems, IsBlank(TasklistKey)),\n"
            "                        \"S3: Item \" & Text(ItemId) & \" has no task list - the package allocation belongs to the task list.\",\n"
            "                        Char(10)\n"
            "                    ), \"\"),\n"
            "            s4:\n"
            "                If(isStrat,\n"
            "                    Concat(\n"
            "                        Filter(colVhpOperations, Len(Coalesce(PackagesKey, \";\")) <= 1),\n"
            "                        \"S4: Item \" & Text(ItemId) & \" operation \" & OperationNo &\n"
            "                        \" has no package and would never be carried out.\",\n"
            "                        Char(10)\n"
            "                    ), \"\"),\n"
            "            s5:\n"
            "                If(isStrat,\n"
            "                    Concat(\n"
            "                        Filter(\n"
            "                            colVhpStrategyPackages As P,\n"
            "                            P.StrategyKey = varVhpPlan.Strategy &&\n"
            "                            CountRows(Filter(colVhpOperations, \";\" & Text(P.PackageNo) & \";\" in Coalesce(PackagesKey, \";\"))) = 0\n"
            "                        ),\n"
            "                        \"S5: Package \" & ShortCode & \" (\" & Text(CycleLength) & \" \" & CycleUnit &\n"
            "                        \") has no operations - the plan would call an empty order.\",\n"
            "                        Char(10)\n"
            "                    ), \"\")\n"
            ",\n"
            # --- Regler fra BIO_SAP_Fields.xlsx og "Den gode VH-plan" -------
            # R1: overskriften skal starte med vaerkskoden, saa planen kan
            # findes naar man ikke kan soege paa vaerk eller funktionsplads.
            "            r1:\n"
            "                If(\n"
            "                    !IsBlank(varVhpPlan.Plant) && !IsBlank(varVhpPlan.PlanText) &&\n"
            "                        !StartsWith(Upper(varVhpPlan.PlanText), Upper(varVhpPlan.Plant)),\n"
            "                    \"R1: Plan Text should start with the plant code \" & varVhpPlan.Plant &\n"
            "                        \" - otherwise the plan cannot be found without searching by plant.\", \"\"),\n"
            # R2: sort field bruges kun ved lovpligtige eftersyn - men SKAL
            # udfyldes, saa snart et item er et.
            "            r2:\n"
            "                With(\n"
            "                    { n: CountRows(Filter(colVhpItems, StartsWith(ActivityType, \"110\") || StartsWith(ActivityType, \"115\"))) },\n"
            "                    If(\n"
            "                        n > 0 && IsBlank(varVhpPlan.SortField),\n"
            "                        \"R2: Sort Field is required: \" & Text(n) &\n"
            "                            \" item(s) have activity type 110 or 115.\", \"\")),\n"
            # R3 er FJERNET. Den blokerede indsendelse, hvis et item med
            # activity type 110/115 ikke havde *SUP som arbejdscenter.
            # Peter har bekraeftet, at det ikke er rigtigt: lovpligtige
            # eftersyn sendes ikke altid til *SUP. Reglen blokerede altsaa
            # folk paa noget, der ikke er en regel, og den slags er vaerre
            # end ingen validering - den laerer folk at ignorere panelet.
            # Nummereringen R1, R2, R4, R5 staar urOErt, saa den fejl der
            # var, kan genkendes i docs/14 og i TEST-manuelt.md.
            # R4: revisionsopgaver kaldes 1/1, ellers rammer de ikke revisionen.
            "            r4:\n"
            "                With(\n"
            "                    { n: CountRows(Filter(colVhpItems, !IsBlank(Revision))) },\n"
            "                    If(\n"
            "                        n > 0 && (varVhpPlan.FirstCallDay <> 1 || varVhpPlan.FirstCallMonth <> 1),\n"
            "                        \"R4: \" & Text(n) & \" item(s) are marked as outage work. \" &\n"
            "                            \"First call must be 01/01, otherwise the task misses the outage.\", \"\")),\n"
            # R5: under 2 aars scheduling period virker den oekonomiske
            # simulering i BI-rapporten ikke.
            "            r5:\n"
            "                With(\n"
            "                    { m: LookUp(colVhpCallHorizonOptions, Value = varVhpPlan.CallHorizon) },\n"
            "                    If(\n"
            "                        !IsBlank(varVhpPlan.CallHorizon) && m.SchedPeriod < 2,\n"
            "                        \"R5: Scheduling period must be at least 2 years because of \" &\n"
            "                            \"the cost simulation in the BI report.\", \"\"))\n"
            "        },\n"
            "        Set(\n"
            "            varVhpLastValidationErrors,\n"
            "            Concat(\n"
            "                Filter(\n"
            "                    Table(\n"
            "                        { t: itemErr }, { t: s1 }, { t: s3 }, { t: s4 }, { t: s5 },\n"
            "                        { t: r1 }, { t: r2 }, { t: r4 }, { t: r5 }\n"
            "                    ),\n"
            "                    !IsBlank(t)\n"
            "                ),\n"
            "                t, Char(10)\n"
            "            )\n"
            "        )\n"
            "    )\n"
            ");\n"
            "Set(\n"
            "    varVhpRuntimeInfo,\n"
            "    \"Validated: \" & Text(CountRows(colVhpItems)) & \" item(s), \" &\n"
            "    Text(CountRows(colVhpOperations)) & \" operation line(s), \" &\n"
            "    Text(CountRows(Filter(colVhpItems, Status = \"invalid\"))) & \" invalid item(s).\" &\n"
            "    If(IsBlank(varVhpLastValidationErrors), \" No validation issues.\", \" See validation report.\")\n"
            ")"
        ),
        primary=True, width=110, height=36)

# ---------------------------------------------------------------------------
# Trinindikatoren
# ---------------------------------------------------------------------------
# Seks trin - de samme som kortenes Step-maerker. Et trin er NAAET, naar
# betingelsen er sand, og FAERDIGT, naar det naeste er naaet (det sidste:
# naar planen er gemt). Betingelserne er procestrinenes fra foer.
STEPS = [
    ('"Plan"', "true"),
    ('"Item"', "varVhpPlanCommitted"),
    ('"Task list"', "varVhpPlanCommitted && CountRows(colVhpItems) > 0"),
    ('If(varVhpPlan.PlanType = "Strategy", "Packages", "Operations")',
     "varVhpPlanCommitted && !IsBlank(LookUp(colVhpItems, ItemId = varVhpActiveItemId, TasklistKey))"),
    ('"Dispatch"', "varVhpPlanCommitted && CountRows(colVhpOperations) > 0"),
    ('"Save"', "varVhpPlanCommitted && CountRows(colVhpOperations) > 0 && "
               "IfError(varVhpPlanValidated, false) && IsBlank(varVhpLastValidationErrors)"),
]
SAVED = "!IsBlank(varVhpPlanKey)"
STEP_W, STEP_H, R = 120, 60, 13


def _hx(name):
    """En farvetoken midt i en SVG-streng."""
    return '" & %s & "' % ref_hex(name)


def stepper():
    """Trinene som en raekke cirkler med en streg imellem:

        (v)-----(v)-----(3)-----(4)       faerdigt: groen med flueben
                         ^                 aktuelt:  ring om nummeret
                                           endnu ikke: graa

    EET Image med en SVG, af samme grund som sidebaren og temaknappen: den
    tegner praecis det, der staar, i temaets farver. Tilstanden regnes i
    Power Fx, saa billedet skifter, mens man arbejder."""
    n = len(STEPS)
    w = n * STEP_W
    cy = R + 4
    ok, grey = ref_hex("state-ok-fg"), ref_hex("text-muted")
    line, text = ref_hex("border-default"), ref_hex("text-primary")
    surface = _hx("bg-surface")
    font = "font-family='Segoe UI, sans-serif' text-anchor='middle'"
    reached = ["(%s)" % c for _l, c in STEPS]
    done = reached[1:] + ["(%s)" % SAVED]
    fx = ['"<svg xmlns=\'http://www.w3.org/2000/svg\' width=\'%d\' height=\'%d\' '
          'viewBox=\'0 0 %d %d\'>"' % (w, STEP_H, w, STEP_H)]
    for i in range(n - 1):
        x1 = STEP_W * i + STEP_W // 2 + R + 4
        x2 = STEP_W * (i + 1) + STEP_W // 2 - R - 4
        fx.append('"<line x1=\'%d\' y1=\'%d\' x2=\'%d\' y2=\'%d\' stroke-width=\'3\' '
                  'stroke=\'" & If(%s, %s, %s) & "\'/>"' % (x1, cy, x2, cy, done[i], ok, line))
    for i, (label, _c) in enumerate(STEPS):
        cx = STEP_W * i + STEP_W // 2
        okc = _hx("state-ok-fg")
        check = (f"<circle cx='{cx}' cy='{cy}' r='{R}' fill='{okc}'/>"
                 f"<path d='M{cx - 5} {cy} l3.5 3.5 l6.5 -7' fill='none' stroke='{surface}' "
                 f"stroke-width='2.4' stroke-linecap='round' stroke-linejoin='round'/>")
        current = (f"<circle cx='{cx}' cy='{cy}' r='{R + 3}' fill='none' stroke='{okc}' "
                   f"stroke-width='2'/>"
                   f"<circle cx='{cx}' cy='{cy}' r='{R - 1}' fill='{surface}' stroke='{okc}' "
                   f"stroke-width='2'/>"
                   f"<text x='{cx}' y='{cy + 5}' {font} font-size='13' font-weight='700' "
                   f"fill='{okc}'>{i + 1}</text>")
        later = (f"<circle cx='{cx}' cy='{cy}' r='{R}' fill='{_hx('text-muted')}'/>"
                 f"<text x='{cx}' y='{cy + 5}' {font} font-size='13' font-weight='700' "
                 f"fill='{surface}'>{i + 1}</text>")
        fx.append('If(%s, "%s", %s, "%s", "%s")' % (done[i], check, reached[i], current, later))
        fx.append('"<text x=\'%d\' y=\'%d\' %s font-size=\'12\' font-weight=\'600\' '
                  'fill=\'" & If(%s, %s, %s) & "\'>" & %s & "</text>"'
                  % (cx, STEP_H - 6, font, reached[i], text, grey, label))
    fx.append('"</svg>"')
    img = '"data:image/svg+xml;utf8," & EncodeUrl(\n    ' + " &\n    ".join(fx) + "\n)"
    return Ctrl("imgVhpSteps", "Image", props={
        "AccessibleLabel": '"Progress through the six steps of the maintenance plan"',
        "BorderStyle": "BorderStyle.None",
        "BorderThickness": "0",
        "Height": str(STEP_H),
        "Image": img,
        "ImagePosition": "ImagePosition.Fit",
        "TabIndex": "-1",
        "Width": f"Min({w}, {SHELL_W} - 2)",
    }, h=STEP_H)


def build_top_bar():
    """VH-planens topbjaelke - den samme som i de tre andre apps
    (build_helpers.top_bar), men med trinindikatoren under titlen og uden
    knapper: Validate staar i trin 5, og Help og tema i sidebaren."""
    return top_bar("Vhp", '"VH-plan"', None, [], sub=[stepper()])
