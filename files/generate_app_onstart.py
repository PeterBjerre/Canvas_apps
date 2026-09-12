# -*- coding: utf-8 -*-
FILES_DIR = r"c:\Users\PKBJE\.copilot\session-state\e93d42be-2820-4dcf-8776-8328cfe9a7c9\files"
OUT_DIR = r"C:\Temp\powerapp-vhplan"

with open(FILES_DIR + r"\colOptions_renamed.txt", encoding="utf-8") as f:
    OPTIONS_BLOCK = f.read()
with open(FILES_DIR + r"\colTasklists_renamed.txt", encoding="utf-8") as f:
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
        { ItemId: 1, OperationNo: "0010", OperationShortText: "Timer til tilrettelaeggelse", WorkHours: 1, DurationHours: 1, MainWorkCenter: "SSVAP", Vendor: "", LongText: "", Selected: false },
        { ItemId: 1, OperationNo: "0020", OperationShortText: "Supervisor timer", WorkHours: 2, DurationHours: 1, MainWorkCenter: "SSVSUP", Vendor: "", LongText: "", Selected: false },
        { ItemId: 1, OperationNo: "0030", OperationShortText: "Interne timer E-Service", WorkHours: 3, DurationHours: 2, MainWorkCenter: "SSVSERVE", Vendor: "", LongText: "", Selected: false },
        { ItemId: 1, OperationNo: "0040", OperationShortText: "Smoering af lejer", WorkHours: 1, DurationHours: 1, MainWorkCenter: "SSVSERVI", Vendor: "", LongText: "", Selected: false }
    )
);"""

PICKER_SEED_BLOCK = """ClearCollect(colVhpPickerSelected, { OperationNo: "" });
Clear(colVhpPickerSelected);"""

VARS_BLOCK = """Set(
    varVhpPlan,
    {
        Plant: "SSV",
        Status: "Ny",
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
Set(varVhpRuntimeInfo, "Ready. Demo plan SSV Aarlig Rundering loaded with 2 items.");
Set(varVhpFlMeta, "");
Set(varVhpLastValidationErrors, "");
Set(varVhpExportJson, "");
Set(varVhpTasklistPickerOpen, false);"""

ALL_BLOCKS = [
    OPTIONS_BLOCK.strip(),
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

with open(OUT_DIR + r"\App.pa.yaml", "w", encoding="utf-8", newline="\n") as f:
    f.write(content)

print("App.pa.yaml written. Lines:", content.count(chr(10)) + 1, "Chars:", len(content))
