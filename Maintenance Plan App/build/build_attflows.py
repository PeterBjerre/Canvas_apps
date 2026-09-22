# -*- coding: utf-8 -*-
"""
VH-plans dokumentrude. KUN det, der er anderledes end de andre appers.

Flowkontrakten - de tre flownavne, biblioteket, stikonstruktionen og de
fire knapformler - staar i tools/attflows.py og staar der KUN eet sted.
Den her fil stod foer som en naesten-kopi af den: de samme fjorten navne,
de samme tre flowkald, men ikke ordret ens, saa ingen vagt kunne se det.
Rettes et flow i Azure, skulle begge filer med - og den glemte app ville
foerst fejle, naar en bruger trykkede paa knappen.

Tilbage her er de seks navne, ruden hedder i denne app, og den ene
metode, der faktisk goer noget andet: refresh_fx().
"""
import attflows


class VhPlanPane(attflows.Pane):
    """Ruden haenger paa det aktive item, ikke paa en raekke i en liste."""

    picker = "attVhpAttPicker"
    folder = 'LookUp(colVhpSavedItems, LocalId = varVhpActiveItemId).ItemKey'
    key_pred = "ItemId = varVhpActiveItemId"
    collection = "colVhpAttachments"
    up_collection = "colVhpAttUp"
    not_saved = ("Save the plan before attaching documents - the folder is "
                 "named after the item.")
    empty_pre = "No documents in "
    empty_post = " yet."

    def refresh_fx(self, indent=0):
        """Hent mappens indhold og laeg det i colVhpAttachments.

        HVORFOR DEN IKKE ER DEN SAMME SOM DOMAENEAPPERNES:
        Operationskoblingen (OperationsKey) findes kun i appen, ikke i
        biblioteket. Den reddes derfor over i colVhpAttKeep FOER raekkerne
        skiftes ud, og saettes tilbage paa de filer, der stadig er der.
        Domaeneapperne har ingen kobling at redde - de skriver til
        gengaeld filantallet tilbage i listen. To forretningsforskelle,
        der skal blive ved at vaere synlige hver for sig."""
        pad = " " * indent
        return "\n".join(pad + l for l in (
            "ClearCollect(",
            "    colVhpAttKeep,",
            "    ForAll(",
            f"        {self.scope} As A,",
            "        { FileName: A.FileName, OperationsKey: A.OperationsKey }",
            "    )",
            ");",
            "Set(",
            "    varVhpAttJson,",
            f"    {attflows.FLOW_LIST}.Run({self.folder_path}).files",
            ");",
            "ClearCollect(",
            "    colVhpAttFiles,",
            "    ForAll(",
            "        ParseJSON(Coalesce(varVhpAttJson, \"[]\")),",
            "        {",
            "            Name: Text(ThisRecord.Name),",
            "            Link: Text(ThisRecord.Link),",
            "            Identifier: Text(ThisRecord.Identifier)",
            "        }",
            "    )",
            ");",
            f"RemoveIf({self.collection}, {self.key_pred});",
            "Collect(",
            f"    {self.collection},",
            "    ForAll(",
            "        colVhpAttFiles As F,",
            "        {",
            "            ItemId: varVhpActiveItemId,",
            "            FileName: F.Name,",
            "            FileUrl: F.Link,",
            "            Identifier: F.Identifier,",
            "            FileSize: 0,",
            "            OperationsKey: Coalesce(",
            "                LookUp(colVhpAttKeep, FileName = F.Name).OperationsKey,",
            "                \";\"",
            "            ),",
            "            Status: \"Uploaded\",",
            "            Selected: false",
            "        }",
            "    )",
            ");",
            "Clear(colVhpAttKeep)",
        ))


PANE = VhPlanPane()
