# -*- coding: utf-8 -*-
"""
Skriver ../App.pa.yaml: navngivne formler + OnStart.

FOER (testdata)                     NU (rigtige lister)
------------------------------     ----------------------------------------
21 ClearCollect med haardkodede     12 navngivne formler mod SharePoint,
tabeller, ~460 linjer OnStart       evalueret dovent og cachet

OnStart indeholder herefter kun to ting: skemaet for de samlinger, appen
SKRIVER til, og de Set() der styrer skaermen. Ingen datahentning.

Se sp_config.py for hvorfor, og for hvilke lister og kolonner der bruges.
"""
import os
import sys
import sp_config as cfg
import build_load

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "tools"))
import design_tokens as tok
import layout_tokens as lay


def _fx_value(v):
    return str(v)


def working_collection_block():
    """Skema uden data.

    ClearCollect med een raekke og derefter Clear: det er den maade, en
    samling faar kendte kolonnetyper i Power Apps, uden at der ligger data.
    Uden det kender Power Fx ikke typerne, foer brugeren har tilfoejet noget,
    og formler mod tomme samlinger fejler i compile."""
    out = []
    for name, schema in cfg.WORKING_COLLECTIONS:
        fields = ", ".join(f"{k}: {_fx_value(v)}" for k, v in schema.items())
        out.append(f"ClearCollect({name}, {{ {fields} }});\nClear({name});")
    return "\n\n".join(out)


# ---------------------------------------------------------------------------
# Skaermens tilstand. INGEN demo-plan: appen aabner tom, og brugeren
# opretter eller indlaeser en plan.
# ---------------------------------------------------------------------------
VARS_BLOCK = """Set(
    varVhpPlan,
    {
        Plant: "",
        Status: "",
        PlanType: "SingleCycle",
        Strategy: "",
        PlanText: "",
        SortField: "",
        Cycle: 0,
        Unit: "",
        CallHorizon: "",
        SchedulingIndicator: "",
        FirstCallDay: Day(Today()),
        FirstCallMonth: Month(Today()),
        FirstCallYear: Year(Today()) + 1,
        StatutorySortField: ""
    }
);

Set(varVhpPlanCommitted, false);
Set(varVhpPlanLocked, false);
Set(varVhpPlanCreatedAt, Blank());
Set(varVhpPlanValidated, false);
Set(varVhpItemValidated, false);
// Appen aabner med EET item, der allerede er valgt. Item Editoren stod
// foer tom og skrivebeskyttet (DM_ITEM slaar fra paa tomt
// varVhpActiveItemId), saa det foerste man moedte var en raekke graa felter
// og en knap, man skulle finde foerst. Nummeret er 1, saa "Add item" (som
// taeller varVhpNextItemId een op foerst) fortsaetter ved 2.
Set(varVhpActiveItemId, 1);
Set(varVhpNextItemId, 1);
Set(varVhpRuntimeInfo, "");
Set(varVhpFlMeta, "");
Set(varVhpLastValidationErrors, "");
Set(varVhpExportJson, "");
Set(varVhpTasklistPickerOpen, false);

// Get-flowet svarer med en STRENG, der skal gennem ParseJSON.
Set(varVhpAttJson, "");

// Popup'en til lang tekst paa en operation. Operationen udpeges af
// BEGGE noegler - OperationNo er kun unikt inden for et item.
Set(varVhpLongTextOpen, false);
Set(varVhpLongTextItemId, 0);
Set(varVhpLongTextOpNo, "");
Set(varVhpLongTextDraft, "");

// Gemning i SharePoint. SpId > 0 betyder, at planen findes som raekke -
// saa opdateres den i stedet for at blive oprettet igen.
Set(varVhpPlanSpId, 0);
Set(varVhpPlanKey, "");
Set(varVhpRequestGuid, "");
Set(varVhpSaving, false);

// Hjaelpepanelerne. Slaaet fra som standard - teksten er der for den, der
// har brug for den, ikke for at fylde skaermen for alle andre.
Set(varVhpShowHints, false);

// Fanen i Tasklist-sektionen. Operations er den man er i oftest.
Set(varVhpOpsTab, "ops");
Set(varVhpHelpPlan, false);
Set(varVhpHelpItem, false);
Set(varVhpHelpOps, false);
Set(varVhpHelpPkg, false);"""


def check_plan_record():
    """varVhpPlan skal have de SAMME felter de to steder, den saettes.

    En record med andre felter er en anden type i Power Fx, og en Set med
    den type paa en eksisterende variabel afvises. De to steder staar langt
    fra hinanden - her i VARS_BLOCK og i build_load - saa det er en fejl,
    der ellers foerst ville vise sig, naar nogen aabnede et dyblink."""
    import re
    m = re.search(r"Set\(\s*varVhpPlan,\s*\{(.*?)\n    \}\s*\);", VARS_BLOCK, re.S)
    if not m:
        return ["kunne ikke finde Set(varVhpPlan, ...) i VARS_BLOCK"]
    here = {line.split(":")[0].strip()
            for line in m.group(1).splitlines() if ":" in line}
    there = {k for k, _ in build_load.PLAN_FIELDS}
    out = []
    if here - there:
        out.append(f"varVhpPlan: build_load mangler {sorted(here - there)}")
    if there - here:
        out.append(f"varVhpPlan: build_load saetter {sorted(there - here)}, "
                   f"som OnStart ikke opretter")
    return out


def build_onstart():
    # Indlaesningen staar TIL SIDST: den skriver i de samlinger, skemablokken
    # lige har ryddet, og laeser de variable, VARS_BLOCK saetter.
    problems = build_load.check_mappings() + check_plan_record()
    if problems:
        raise SystemExit("build_load passer ikke til OnStart:\n  "
                         + "\n  ".join(problems))
    prefs_name, prefs_schema = tok.prefs_schema()
    prefs = "ClearCollect(%s, { %s });\nClear(%s);" % (
        prefs_name,
        ", ".join("%s: %s" % kv for kv in prefs_schema.items()),
        prefs_name)
    blocks = [working_collection_block(), prefs, tok.onstart_block(),
              VARS_BLOCK.strip(), build_load.load_block()]
    s = "\n\n".join(b for b in blocks if b).rstrip()
    return s[:-1] if s.endswith(";") else s


def build_formulas():
    """App.Formulas. Hver formel afsluttes med semikolon - ogsaa den sidste."""
    out = [tok.formula(), "", lay.formula(), ""]
    for name, expr, why in cfg.named_formulas():
        if why:
            out.append(f"// {why}")
        out.append(f"{name} = {expr};")
        out.append("")
    return "\n".join(out).rstrip()


def _yaml_block(prop, text, first_line_eq=True):
    lines = [f"    {prop}: |"]
    done = not first_line_eq
    for line in text.split("\n"):
        if not line.strip():
            lines.append("")
        elif not done:
            lines.append("      =" + line)
            done = True
        else:
            lines.append("      " + line)
    return lines


def main():
    out = ["App:", "  Properties:"]
    out += _yaml_block("Formulas", build_formulas())
    out += _yaml_block("OnStart", build_onstart())
    out += ["    StartScreen: |-", "        =ScreenVhPlan",
            "    Theme: |-", "        =PowerAppsTheme"]
    content = "\n".join(out) + "\n"

    with open(os.path.join(OUT_DIR, "App.pa.yaml"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(content)

    n_fx = len(cfg.named_formulas())
    print(f"App.pa.yaml skrevet. {content.count(chr(10)) + 1} linjer, "
          f"{n_fx} navngivne formler, "
          f"{len(cfg.WORKING_COLLECTIONS)} arbejdssamlinger, 0 datahentninger i OnStart.")


if __name__ == "__main__":
    main()
