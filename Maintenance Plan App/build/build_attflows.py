# -*- coding: utf-8 -*-
"""
VH-plans dokumentrude. KUN det, der er anderledes end de andre appers.

Vedhaeftningskontrakten - Items, hentning paa ID, gem med Patch og luk -
staar i tools/attflows.py og staar der KUN eet sted (issue #300).

Her staar de navne, ruden hedder i denne app, og listen: filerne er
SharePoint-vedhaeftninger paa OPERATIONENS raekke i TaskListMain. En
operation skal derfor vaere gemt (have et SpId), foer der kan vedhaeftes.

Filerne skal senere videre til blob storage/SAP DMS via et API -
SharePoint er kun mellemlager (Peter, issue #300).
"""
import attflows
import sp_config as cfg

# Den operation, popuppen er aabnet for: itemets operation med nummeret.
ACTIVE_OP = ("LookUp(colVhpOperations, ItemId = varVhpActiveItemId && "
             "OperationNo = varVhpAttOpNo)")


class VhPlanPane(attflows.Pane):
    """Ruden haenger paa den aktive operation (varVhpAttOpNo)."""

    picker = "attVhpAttPicker"
    row_var = "varVhpAttRow"
    busy_var = "varVhpAttBusy"
    not_saved = ("Save the plan first - documents are attached to the saved "
                 "operation.")

    @property
    def data_source(self):
        return cfg.L_TASKS

    def open_fx(self, op_no):
        """Docs-knappen: aabn popuppen for operationen og hent dens raekke
        i TaskListMain (LookUp paa SpId). En ny operation har SpId 0 -
        saa er raekken Blank, og ruden siger, at planen skal gemmes."""
        return (f"Set(varVhpAttOpNo, {op_no});\n"
                + self.load_fx(f"{ACTIVE_OP}.SpId"))


PANE = VhPlanPane()
