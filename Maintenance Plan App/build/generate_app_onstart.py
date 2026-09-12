# -*- coding: utf-8 -*-
import os
FILES_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(FILES_DIR, "..")

with open(os.path.join(FILES_DIR, "colOptions_renamed.txt"), encoding="utf-8") as f:
    OPTIONS_BLOCK = f.read()
with open(os.path.join(FILES_DIR, "colTasklists_renamed.txt"), encoding="utf-8") as f:
    TASKLISTS_BLOCK = f.read()

PLANT_CODES_BLOCK = """ClearCollect(
    colVhpPlantCodes,
    Table(
        { Value: "SSV" },
        { Value: "SKV" },
        { Value: "HEV" },
        { Value: "HCV" },
        { Value: "ASV" },
        { Value: "AVV" },
        { Value: "KYV" },
        { Value: "STV" },
        { Value: "SMV" }
    )
);"""

FL_BLOCK = """ClearCollect(
    colVhpFunctionalLocations,
    Table(
        { Code: "SSV10 KAB10AP001", Description: "Ball bearing house, pump area", Plant: "SSV" },
        { Code: "SKV21 HAD20AA001", Description: "Gasket area, feedwater system", Plant: "SKV" },
        { Code: "HEV31 LAB10AA010", Description: "Servo motor drive unit", Plant: "HEV" },
        { Code: "HCV12 CAB05AA002", Description: "Cooling water pump", Plant: "HCV" },
        { Code: "ASV20 FAB08AA003", Description: "Ash handling conveyor", Plant: "ASV" },
        { Code: "AVV15 KAB12AA004", Description: "Flue gas fan", Plant: "AVV" },
        { Code: "KYV18 PAB09AA005", Description: "Boiler feed pump", Plant: "KYV" },
        { Code: "SMV22 TAB07AA006", Description: "Turbine lube oil system", Plant: "SMV" }
    )
);"""

ITEMS_BLOCK = """ClearCollect(
    colVhpItems,
    Table(
        {
            ItemId: 1,
            ShortText: "SSV aarligt eftersyn - KAB10AP001",
            FunctionalLocation: "SSV10 KAB10AP001",
            FlDescription: "Ball bearing house, pump area",
            MainWorkCenter: "*PROD - Produktion",
            ActivityType: "ZPRE 101 Maintenance",
            ObjectList: "",
            Revision: "REV - Generelt revisionsmaerke",
            OrstedResponsible: "",
            Initials: "",
            LongText: "",
            TasklistKey: "SSV001-STD",
            TasklistName: "Standard task list - SSV001",
            Status: "valid"
        },
        {
            ItemId: 2,
            ShortText: "HEV smoering - LAB10AA010",
            FunctionalLocation: "HEV31 LAB10AA010",
            FlDescription: "Servo motor drive unit",
            MainWorkCenter: "*SERVE - Maintenance Execution",
            ActivityType: "ZPRE 160 Lubrication",
            ObjectList: "",
            Revision: "",
            OrstedResponsible: "",
            Initials: "",
            LongText: "",
            TasklistKey: "",
            TasklistName: "",
            Status: "draft"
        }
    )
);"""

OPERATIONS_BLOCK = """ClearCollect(
    colVhpOperations,
    Table(
        { ItemId: 1, OperationNo: "0010", OperationShortText: "Timer til tilrettelaeggelse", WorkHours: 1, DurationHours: 1, MainWorkCenter: "SSVAP", Vendor: "", LongText: "", PackagesKey: ";", Selected: false },
        { ItemId: 1, OperationNo: "0020", OperationShortText: "Supervisor timer", WorkHours: 2, DurationHours: 1, MainWorkCenter: "SSVSUP", Vendor: "", LongText: "", PackagesKey: ";", Selected: false },
        { ItemId: 1, OperationNo: "0030", OperationShortText: "Interne timer E-Service", WorkHours: 3, DurationHours: 2, MainWorkCenter: "SSVSERVE", Vendor: "", LongText: "", PackagesKey: ";", Selected: false },
        { ItemId: 1, OperationNo: "0040", OperationShortText: "Smoering af lejer", WorkHours: 1, DurationHours: 1, MainWorkCenter: "SSVSERVI", Vendor: "", LongText: "", PackagesKey: ";", Selected: false }
    )
);"""

# ---------------------------------------------------------------------------
# Strategiplaner
#
# Pakkerne er MASTERDATA og hoerer til strategien (SAP IP11). Brugeren
# opfinder dem ikke - appen viser dem. Hierarchy styrer hvilken pakke der
# kalder, naar flere forfalder samme dag: hoejere tal = mere omfattende.
#
# Samme data som sharepoint/seed/MD_StrategyPackage.csv, saa app og backend
# beskriver de samme strategier.
# ---------------------------------------------------------------------------
PLANTYPE_BLOCK = """ClearCollect(
    colVhpPlanTypeOptions,
    Table(
        { Key: "SingleCycle", Value: "Single cycle plan (IP41)" },
        { Key: "Strategy", Value: "Strategiplan (IP42)" }
    )
);"""

STRATEGIES_BLOCK = """ClearCollect(
    colVhpStrategies,
    Table(
        { Key: "Z-MONTH", Name: "Maanedsbaseret 1/3/6/12", SchedIndicator: "TIME" },
        { Key: "Z-YEAR", Name: "Aarsbaseret 1/2/5 aar", SchedIndicator: "TIME" },
        { Key: "Z-WEEK", Name: "Ugebaseret 1/4/13 uger", SchedIndicator: "TIME" },
        { Key: "Z-RUNH", Name: "Driftstimer 500/2000/8000", SchedIndicator: "PERFORMANCE" }
    )
);"""

PACKAGES_BLOCK = """ClearCollect(
    colVhpStrategyPackages,
    Table(
        { StrategyKey: "Z-MONTH", PackageNo: 1, ShortCode: "M1", CycleLength: 1, CycleUnit: "MON", Hierarchy: 1, PackageText: "Maanedligt tilsyn" },
        { StrategyKey: "Z-MONTH", PackageNo: 2, ShortCode: "M3", CycleLength: 3, CycleUnit: "MON", Hierarchy: 2, PackageText: "Kvartalsvis eftersyn" },
        { StrategyKey: "Z-MONTH", PackageNo: 3, ShortCode: "M6", CycleLength: 6, CycleUnit: "MON", Hierarchy: 3, PackageText: "Halvaarligt eftersyn" },
        { StrategyKey: "Z-MONTH", PackageNo: 4, ShortCode: "M12", CycleLength: 12, CycleUnit: "MON", Hierarchy: 4, PackageText: "Aarligt hovedeftersyn" },
        { StrategyKey: "Z-YEAR", PackageNo: 1, ShortCode: "Y1", CycleLength: 1, CycleUnit: "YR", Hierarchy: 1, PackageText: "Aarlig inspektion" },
        { StrategyKey: "Z-YEAR", PackageNo: 2, ShortCode: "Y2", CycleLength: 2, CycleUnit: "YR", Hierarchy: 2, PackageText: "2-aarig gennemgang" },
        { StrategyKey: "Z-YEAR", PackageNo: 3, ShortCode: "Y5", CycleLength: 5, CycleUnit: "YR", Hierarchy: 3, PackageText: "5-aarigt hovedeftersyn" },
        { StrategyKey: "Z-WEEK", PackageNo: 1, ShortCode: "W1", CycleLength: 1, CycleUnit: "WK", Hierarchy: 1, PackageText: "Ugentligt runderingstjek" },
        { StrategyKey: "Z-WEEK", PackageNo: 2, ShortCode: "W4", CycleLength: 4, CycleUnit: "WK", Hierarchy: 2, PackageText: "4-ugers eftersyn" },
        { StrategyKey: "Z-WEEK", PackageNo: 3, ShortCode: "W13", CycleLength: 13, CycleUnit: "WK", Hierarchy: 3, PackageText: "Kvartalseftersyn" },
        { StrategyKey: "Z-RUNH", PackageNo: 1, ShortCode: "H500", CycleLength: 500, CycleUnit: "H", Hierarchy: 1, PackageText: "500 driftstimer" },
        { StrategyKey: "Z-RUNH", PackageNo: 2, ShortCode: "H2000", CycleLength: 2000, CycleUnit: "H", Hierarchy: 2, PackageText: "2000 driftstimer" },
        { StrategyKey: "Z-RUNH", PackageNo: 3, ShortCode: "H8000", CycleLength: 8000, CycleUnit: "H", Hierarchy: 3, PackageText: "8000 driftstimer - hovedeftersyn" }
    )
);"""

PICKER_SEED_BLOCK = """ClearCollect(colVhpPickerSelected, { OperationNo: "" });
Clear(colVhpPickerSelected);"""

VARS_BLOCK = """Set(
    varVhpPlan,
    {
        Plant: "SSV",
        Status: "Ny",
        PlanType: "SingleCycle",
        Strategy: "",
        PlanText: "SSV Aarlig Rundering",
        SortField: "080 - Boiler Control Category A",
        Cycle: 12,
        Unit: "MON",
        CallHorizon: "55 Dage (1 YR)",
        SchedulingIndicator: "",
        FirstCallDay: 1,
        FirstCallMonth: 1,
        FirstCallYear: 2027,
        StatutorySortField: ""
    }
);
Set(varVhpPlanCommitted, true);
Set(varVhpPlanLocked, true);
Set(varVhpPlanCreatedAt, Now());
Set(varVhpPlanValidated, false);
Set(varVhpItemValidated, false);
Set(varVhpActiveItemId, 1);
Set(varVhpNextItemId, 3);
Set(varVhpRuntimeInfo, "Ready. Demo plan SSV Aarlig Rundering loaded with 2 items. Skift Plan Type til Strategiplan for at bruge pakker.");
Set(varVhpFlMeta, "");
Set(varVhpLastValidationErrors, "");
Set(varVhpExportJson, "");
Set(varVhpTasklistPickerOpen, false);"""

ALL_BLOCKS = [
    OPTIONS_BLOCK.strip(),
    PLANTYPE_BLOCK.strip(),
    STRATEGIES_BLOCK.strip(),
    PACKAGES_BLOCK.strip(),
    TASKLISTS_BLOCK.strip(),
    PLANT_CODES_BLOCK.strip(),
    FL_BLOCK.strip(),
    ITEMS_BLOCK.strip(),
    OPERATIONS_BLOCK.strip(),
    PICKER_SEED_BLOCK.strip(),
    VARS_BLOCK.strip(),
]

onstart_script = "\n\n".join(ALL_BLOCKS)
onstart_script = onstart_script.rstrip()
if onstart_script.endswith(";"):
    onstart_script = onstart_script[:-1]

app_yaml_lines = ["App:", "  Properties:", "    OnStart: |"]
script_lines = onstart_script.split("\n")
first_prefixed = False
for line in script_lines:
    if not first_prefixed and line.strip() != "":
        app_yaml_lines.append("      =" + line)
        first_prefixed = True
    else:
        app_yaml_lines.append(("      " + line) if line.strip() != "" else "")

app_yaml_lines.append("    StartScreen: |-")
app_yaml_lines.append("        =ScreenVhPlan")
app_yaml_lines.append("    Theme: |-")
app_yaml_lines.append("        =PowerAppsTheme")

content = "\n".join(app_yaml_lines) + "\n"

with open(os.path.join(OUT_DIR, "App.pa.yaml"), "w", encoding="utf-8", newline="\n") as f:
    f.write(content)

print("App.pa.yaml written. Lines:", content.count(chr(10)) + 1, "Chars:", len(content))
