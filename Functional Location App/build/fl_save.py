# -*- coding: utf-8 -*-
"""
GEM, INDSEND, EKSPORT OG DYBLINK - efter powerfx/04-submit-patch.fx.

SharePoint har ingen transaktioner. Hvert gem er derfor GENOPTAGELIGT i
stedet for atomart:

  1. Hovedet foerst - raekkerne skal bruge dets ID. Status roeres ikke.
  2. Raekkerne findes i listen paa RowGuid (klientnoeglen). En raekke, der
     blev oprettet foer en fejl, findes derfor igen og oprettes ikke to
     gange. Nye og eksisterende skrives hver i EEN Patch med to tabeller -
     ingen Patch inde i en ForAll (check_layout regel 15). De eksisterende
     peges ud med { ID: ... } - listens primaernoegle - og ikke med et
     LookUp pr. raekke: det kan ikke delegeres (regel 30), og SharePoint
     ville saa kun lede i de foerste 500-2000 raekker.
  3. Raekker, der ikke laengere er i appen (slettet eller tomme), fjernes -
     ogsaa dem en tidligere, afbrudt gemning efterlod.
  4. Indeksraekken i MD_RequestIndex, fundet paa RequestGuid.
  5. Status SIDST. Fejler noget undervejs, staar anmodningen stadig som
     Kladde og kan gemmes igen.

Indsend er det samme gem efterfulgt af det frosne JSON-snapshot
(schema/functional-location-request.schema.json) og status Indsendt. Det
kan kun ske, naar Verify er koert efter sidste aendring, og ingen raekke
har en fejl (docs/31 FL68).
"""
import fl_config as cfg
from fl_validation import BUCKETS

LIVE = 'Filter(colFlRows, Status <> "draft")'
ERRS = 'CountRows(Filter(colFlRows, Status = "invalid"))'
READY = 'CountRows(Filter(colFlRows, Status = "valid" || Status = "warning"))'
WARNS = 'CountRows(Filter(colFlRows, Status = "warning"))'

# FL68: Submit kun med en frisk, fejlfri Verify og mindst een klar raekke.
SUBMIT_OK = (f'!varFlStale && {ERRS} = 0 && {READY} > 0 && '
             f'varFlStatus <> "Indsendt"')
SUBMIT_DM = f"If({SUBMIT_OK}, DisplayMode.Edit, DisplayMode.Disabled)"
SUBMIT_WHY = (f'If(varFlStatus = "Indsendt", "Request " & varFlRequestNo & " is submitted and locked.",\n'
              f'   varFlStale, "Press Verify before you submit - something changed since the last check.",\n'
              f'   {ERRS} > 0, "Submit is blocked: " & {ERRS} & " row(s) have errors.",\n'
              f'   {READY} = 0, "There are no rows ready for SAP.",\n'
              f'   "Ready to submit " & {READY} & " row(s).")')


def _spool(field):
    return f'Coalesce(LookUp(colFlVals, RowGuid = R.RowGuid && Field = "{field}").Value, "")'


def _row_record():
    return f"""{{
                RowGuid: R.RowGuid,
                RequestGuid: varFlRequestGuid,
                RequestId: varFlReq.ID,
                RowNo: R.RowNo,
                FunctionalLocation: R.FL,
                Description: R.Description,
                KksType: R.KksType,
                AssignedClass: R.AssignedClass,
                RowStatus: {{ Value: R.Status }},
                FirstIssue: Left(Coalesce(R.FirstIssue, R.FirstWarning, ""), 255),
                IssueCount: R.IssueCount,
                TrmAssignment: {_spool("TRM ASSIGNMENT")},
                AbcIndic: {_spool("ABC INDIC.")},
                SafetyCriticalEquipment: {_spool("SAFETY CRITICAL EQUIPMENT")},
                RequesterEmail: varFlMe,
                SpoolValuesJson: JSON(
                    ForAll(Sort(Filter(colFlVals, RowGuid = R.RowGuid), Field) As V,
                           {{ field: V.Field, value: V.Value }}),
                    JSONFormat.Compact
                )
            }}"""


def _index_patch(status, step):
    return f"""Set(
        varFlIdx,
        Patch(
            {cfg.L_INDEX},
            Coalesce(
                LookUp({cfg.L_INDEX}, RequestGuid = varFlRequestGuid),
                Defaults({cfg.L_INDEX})
            ),
            {{
                RequestNo: varFlRequestNo,
                Domain: {{ Value: "{cfg.DOMAIN}" }},
                Status: {{ Value: "{status}" }},
                StatusStep: {step},
                IsOpen: true,
                RequesterEmail: varFlMe,
                RequesterName: User().FullName,
                ShortText: "{cfg.TITLE}: " & CountRows({LIVE}) & " row(s)",
                Plant: Coalesce(Left(First(Sort({LIVE}, RowNo)).FL, 3), ""),
                ItemCount: CountRows({LIVE}),
                RequestGuid: varFlRequestGuid,
                SourceItemId: varFlReq.ID,
                AppUrl: "{cfg.PLAY_URL}?reqid=" & varFlRequestGuid,
                LastActionOn: Now(),
                LastActionBy: varFlMe
            }}
        )
    )"""


def save_fx(status="Kladde", step=1):
    """Gem - trin 1-5 ovenfor. status er det, hovedet og indekset faar til
    SIDST. Indsend kalder den med Kladde og saetter Indsendt bagefter,
    naar snapshottet er skrevet."""
    L = cfg.L_ITEMS
    new_rows = f'Filter(colFlRows, Status <> "draft" && !(RowGuid in colFlSp.RowGuid))'
    old_rows = f'Filter(colFlRows, Status <> "draft" && RowGuid in colFlSp.RowGuid)'
    gone = f'Filter(colFlSp, !(RowGuid in {LIVE}.RowGuid))'
    return f"""Clear(colFlSaveErrors);
If(IsBlank(varFlRequestGuid), Set(varFlRequestGuid, Text(GUID())));

// 1. Hovedet. RequestNo er obligatorisk (Title) - GUID'en staar der, til
//    nummeret kan dannes af listens eget ID.
IfError(
    Set(
        varFlReq,
        Patch(
            {cfg.L_REQ},
            Coalesce(
                LookUp({cfg.L_REQ}, RequestGuid = varFlRequestGuid),
                Defaults({cfg.L_REQ})
            ),
            {{
                RequestNo: Coalesce(varFlRequestNo, varFlRequestGuid),
                RequestGuid: varFlRequestGuid,
                RequesterEmail: varFlMe,
                RequesterName: User().FullName
            }}
        )
    ),
    Collect(colFlSaveErrors, {{ Where: "Header", Msg: FirstError.Message }})
);
If(
    IsBlank(varFlRequestNo) && !IsBlank(varFlReq.ID),
    Set(varFlRequestNo, "{cfg.PREFIX}-" & Text(varFlReq.ID, "000000"));
    IfError(
        Patch({cfg.L_REQ}, varFlReq, {{ RequestNo: varFlRequestNo }}),
        Collect(colFlSaveErrors, {{ Where: "Request number", Msg: FirstError.Message }})
    )
);

If(
    CountRows(colFlSaveErrors) = 0,

    // 2. Hvilke raekker findes allerede? Paa RowGuid - klientnoeglen.
    ClearCollect(
        colFlSp,
        ForAll(Filter({L}, RequestGuid = varFlRequestGuid) As I, {{ RowGuid: I.RowGuid, ID: I.ID }})
    );
    IfError(
        Patch({L}, ForAll({new_rows}, Defaults({L})),
              ForAll({new_rows} As R, {_row_record()})),
        Collect(colFlSaveErrors, {{ Where: "New rows", Msg: FirstError.Message }})
    );
    IfError(
        Patch({L}, ForAll({old_rows} As R, {{ ID: LookUp(colFlSp, RowGuid = R.RowGuid).ID }}),
              ForAll({old_rows} As R, {_row_record()})),
        Collect(colFlSaveErrors, {{ Where: "Rows", Msg: FirstError.Message }})
    );

    // 3. Raekker, der ikke laengere er i appen.
    IfError(
        Remove({L}, ForAll({gone} As D, {{ ID: D.ID }})),
        Collect(colFlSaveErrors, {{ Where: "Deleted rows", Msg: FirstError.Message }})
    );

    // 4. Landingssiden.
    IfError(
    {_index_patch(status, step)},
        Collect(colFlSaveErrors, {{ Where: "Landing page", Msg: FirstError.Message }})
    );

    // 5. Status SIDST - og kun naar alt andet lykkedes.
    If(
        CountRows(colFlSaveErrors) = 0,
        IfError(
            Patch(
                {cfg.L_REQ}, varFlReq,
                {{
                    Status: {{ Value: "{status}" }},
                    RowCount: CountRows({LIVE}),
                    ReadyCount: {READY},
                    IssueCount: {ERRS},
                    WarningCount: {WARNS},
                    IndexItemId: varFlIdx.ID
                }}
            ),
            Collect(colFlSaveErrors, {{ Where: "Status", Msg: FirstError.Message }})
        )
    )
);

// Een samlet tilbagemelding - aldrig een Notify pr. raekke.
If(
    CountRows(colFlSaveErrors) = 0,
    Set(varFlStatus, "{status}");
    Set(varFlInfo, "Saved as " & varFlRequestNo & ".");
    Notify("Saved as " & varFlRequestNo & " - see it on the landing page.", NotificationType.Success),
    Set(varFlInfo, "Saving failed (" & First(colFlSaveErrors).Where & "): " & First(colFlSaveErrors).Msg);
    Notify(CountRows(colFlSaveErrors) & " step(s) failed. What was saved is kept - try again.", NotificationType.Error)
)"""


def payload_fx():
    """Snapshottet. Formen er HTML-sidens Export JSON (generatedAt, source,
    rows, classBuckets, ruleMeta - app-functional-location.js:2254-2276)
    plus anmodningens egne felter. Kontrakt:
    schema/functional-location-request.schema.json."""
    return f"""JSON(
    {{
        schemaVersion: "1.0",
        requestGuid: varFlRequestGuid,
        requestNo: varFlRequestNo,
        submittedBy: varFlMe,
        submittedOn: Text(Now(), DateTimeFormat.UTC),
        generatedAt: Text(Now(), DateTimeFormat.UTC),
        source: "functional-location-canvas-app",
        rows: ForAll(
            Sort({LIVE}, RowNo) As R,
            {{
                rowNo: R.RowNo,
                functionalLocation: R.FL,
                description: R.Description,
                kksType: R.KksType,
                assignedClass: R.AssignedClass,
                status: R.Status,
                blockingIssues: ForAll(Sort(Filter(colFlIssues, RowGuid = R.RowGuid && Sev = "Error"), Ord) As M, {{ message: M.Msg }}),
                warnings: ForAll(Sort(Filter(colFlIssues, RowGuid = R.RowGuid && Sev = "Warning"), Ord) As M, {{ message: M.Msg }}),
                spoolValues: ForAll(Sort(Filter(colFlVals, RowGuid = R.RowGuid), Field) As V, {{ field: V.Field, value: V.Value }})
            }}
        ),
        classBuckets: ForAll(
            Filter(colFlTabs, Key <> "ALL") As K,
            {{
                className: K.Key,
                functionalLocations: ForAll(Sort(Filter({BUCKETS}, AssignedClass = K.Key), FL) As B, {{ functionalLocation: B.FL }})
            }}
        ),
        ruleMeta: {{
            componentCount: CountRows(nfFlComponent),
            aggregateCount: CountRows(nfFlAggregate),
            functionKeyCount: nfFlFunctionKeyCount,
            ruleSource: "html/app-functional-location.js + html/fl-rule-engine.js"
        }}
    }},
    JSONFormat.Compact
)"""


def submit_fx():
    """Indsend: gem, snapshot, status Indsendt - i den raekkefoelge."""
    return f"""If(
    !({SUBMIT_OK}),
    Notify({SUBMIT_WHY}, NotificationType.Warning),

    {save_fx().replace(chr(10), chr(10) + "    ")};

    If(
        CountRows(colFlSaveErrors) = 0,
        Set(varFlPayload, {payload_fx().replace(chr(10), chr(10) + "        ")});
        // PayloadJson er en Note-kolonne - samme loft som i 04-submit-patch.fx.
        If(
            Len(varFlPayload) > 60000,
            Notify("The request is too large to submit in one piece. Split it into more requests.", NotificationType.Error),
            IfError(
                Patch({cfg.L_REQ}, varFlReq,
                      {{ Status: {{ Value: "Indsendt" }}, PayloadJson: varFlPayload, SubmittedOn: Now() }});
                Patch({cfg.L_INDEX}, varFlIdx, {{ Status: {{ Value: "Indsendt" }}, StatusStep: 2, LastActionOn: Now() }});
                Set(varFlStatus, "Indsendt");
                Set(varFlInfo, "Submitted as " & varFlRequestNo & ".");
                Notify("Submitted as " & varFlRequestNo & ".", NotificationType.Success),
                Set(varFlInfo, "Submit failed: " & FirstError.Message);
                Notify("Submit failed: " & FirstError.Message, NotificationType.Error)
            )
        )
    )
)"""


def export_fx():
    """FL64: Export JSON. En canvas app kan ikke hente en genereret fil ned,
    saa JSON'en vises i en popup, hvor den kan kopieres (docs/31 PX10)."""
    return (f"Set(varFlExportJson, {payload_fx()});\n"
            "Set(varFlExportOpen, true);\n"
            'Set(varFlInfo, "Exported JSON.")')


def load_fx():
    """Dyblinket fra hubben (?reqid=). Kun den anmodning hentes - og kun
    naar appen er aabnet med et reqid. Alle andre betaler ingenting."""
    L = cfg.L_ITEMS
    return f"""Set(varFlRequestGuid, Param("reqid"));
Set(varFlReq, LookUp({cfg.L_REQ}, RequestGuid = varFlRequestGuid));
Set(varFlRequestNo, Coalesce(varFlReq.RequestNo, ""));
Set(varFlStatus, Coalesce(varFlReq.Status.Value, "Kladde"));
ClearCollect(
    colFlLoad,
    ForAll(
        Filter({L}, RequestGuid = varFlRequestGuid) As I,
        {{
            RowGuid: I.RowGuid, RowNo: I.RowNo, SpId: I.ID,
            FL: I.FunctionalLocation, Description: I.Description,
            KksType: I.KksType, AssignedClass: I.AssignedClass,
            Status: I.RowStatus.Value, FirstIssue: I.FirstIssue,
            IssueCount: I.IssueCount, Json: Coalesce(I.SpoolValuesJson, "[]")
        }}
    )
);
ClearCollect(
    colFlRows,
    ForAll(
        Sort(colFlLoad, RowNo) As I,
        {{
            RowGuid: I.RowGuid, RowNo: I.RowNo, SpId: I.SpId, FL: I.FL,
            Description: I.Description, KksType: I.KksType,
            AssignedClass: I.AssignedClass, Status: I.Status,
            FirstIssue: I.FirstIssue, FirstWarning: "",
            IssueCount: I.IssueCount, WarningCount: 0
        }}
    )
);
ClearCollect(
    colFlVals,
    Ungroup(
        ForAll(
            colFlLoad As I,
            {{
                Vals: ForAll(
                    Table(ParseJSON(I.Json)) As J,
                    {{ RowGuid: I.RowGuid, Field: Text(J.Value.field), Value: Text(J.Value.value) }}
                )
            }}
        ),
        "Vals"
    )
);
Set(varFlNextRowNo, Max(colFlRows, RowNo) + 1);
// Beskederne gemmes ikke - de regnes. Verify skal koeres, foer der kan
// indsendes (FL68).
Set(varFlStale, true);
Set(varFlInfo, "Loaded " & varFlRequestNo & " - press Verify to check the rows again.")"""
