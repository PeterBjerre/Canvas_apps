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
import sp_config as cfg

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


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


def static_block():
    out = []
    for name, rows, why in cfg.STATIC_TABLES:
        recs = ",\n        ".join(
            "{ " + ", ".join(f'{k}: "{v}"' for k, v in r.items()) + " }" for r in rows)
        out.append(f"// {why}\nClearCollect(\n    {name},\n    Table(\n        {recs}\n    )\n);")
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
Set(varVhpActiveItemId, 0);
Set(varVhpNextItemId, 1);
Set(varVhpRuntimeInfo, "");
Set(varVhpFlMeta, "");
Set(varVhpFlLastSearch, "");
Set(varVhpLastValidationErrors, "");
Set(varVhpExportJson, "");
Set(varVhpTasklistPickerOpen, false);

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


def build_onstart():
    blocks = [working_collection_block(), static_block(), VARS_BLOCK.strip()]
    s = "\n\n".join(b for b in blocks if b).rstrip()
    return s[:-1] if s.endswith(";") else s


def build_formulas():
    """App.Formulas. Hver formel afsluttes med semikolon - ogsaa den sidste."""
    out = []
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
