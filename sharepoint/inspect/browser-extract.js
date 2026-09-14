/* ---------------------------------------------------------------------------
 * Udtraek af SharePoint-listestrukturen UDEN PowerShell og UDEN app-registrering.
 *
 * HVORFOR
 * -------
 * PnP.PowerShell 2.x har ikke laengere en faelles app-registrering, saa
 * Connect-PnPOnline kraever et ClientId fra en Entra-app i jeres egen tenant.
 * Kan du ikke faa en, kan scriptet ikke koere.
 *
 * Det her bruger i stedet SharePoints egen REST API gennem DIN allerede
 * indloggede browsersession. Der er ingen app, intet token og ingen ekstra
 * rettigheder - du kan praecis det, du kan i forvejen som bruger.
 *
 * SAADAN
 * ------
 *  1. Aabn SharePoint-sitet i Edge eller Chrome, og log ind som normalt.
 *     Du skal staa PAA sitet, fx .../sites/SAPMasterdata - ikke paa en
 *     underside i en anden site collection.
 *  2. Tryk F12 -> fanen "Console".
 *  3. Er der en advarsel om at indsaette kode, saa skriv "allow pasting"
 *     og tryk Enter foerst.
 *  4. Indsaet HELE denne fil og tryk Enter.
 *  5. Vent. Der skrives fremdrift undervejs. Til sidst hentes filen
 *     sharepoint-schema.json.
 *  6. Laeg filen i sharepoint/inspect/out/ i repoet, commit og push.
 *
 * Vil du ikke have rigtige data med, saa saet SAMPLE_ROWS = 0 nedenfor.
 * ------------------------------------------------------------------------- */

(async () => {
  const SAMPLE_ROWS = 8;   // 0 = kun struktur, ingen data

  // Kun de egenskaber der siger noget om datamodellen. Uden filteret bliver
  // filen flere MB af ligegyldige SharePoint-internals.
  const FIELD_PROPS = [
    "InternalName", "Title", "TypeAsString", "Required", "Indexed",
    "ReadOnlyField", "Hidden", "Description", "Choices", "MaxLength",
    "LookupList", "LookupField", "AllowMultipleValues", "Formula",
    "DefaultValue", "EnforceUniqueValues"
  ];

  // Systemkolonner. De fylder alt og siger intet.
  const SKIP = new Set([
    "ContentType","Attachments","Edit","LinkTitleNoMenu","LinkTitle","DocIcon",
    "_UIVersionString","_ComplianceFlags","_ComplianceTag","_ComplianceTagWrittenTime",
    "_ComplianceTagUserId","_IsRecord","AppAuthor","AppEditor","FolderChildCount",
    "ItemChildCount","_CommentCount","_CommentFlags","ComplianceAssetId","InstanceID",
    "Order","GUID","WorkflowVersion","WorkflowInstanceID","FileLeafRef","FileDirRef",
    "FSObjType","SortBehavior","PermMask","UniqueId","ProgId","ScopeId","MetaInfo",
    "owshiddenversion","_Level","_HasCopyDestinations","_CopySource","_ModerationStatus",
    "_ModerationComments","_UIVersion","Created_x0020_Date","Last_x0020_Modified",
    "SyncClientId","CheckedOutTitle","CheckedOutUserId","IsCheckedoutToLocal",
    "ParentVersionString","ParentLeafName","ParentUniqueId","BSN","AccessPolicy",
    "_ListSchemaVersion","_Dirty","_Parsable","_StubFile","_VirusStatus","NoExecute",
    "_EditMenuTableStart","_EditMenuTableStart2","_EditMenuTableEnd","ServerUrl",
    "EncodedAbsUrl","BaseName","FileSizeDisplay","OriginatorId","HashCode","_activity",
    "_ColorTag","_SourceUrl","_SharedFileIndex","SelectFilename","TemplateUrl",
    "xd_ProgID","xd_Signature","_CheckinComment","CheckoutUser","VirusStatus",
    "_ShortcutUrl","_ShortcutSiteId","_ShortcutWebId","_ShortcutUniqueId","TriggerFlowInfo"
  ]);

  const web = (typeof _spPageContextInfo !== "undefined" && _spPageContextInfo.webAbsoluteUrl)
    ? _spPageContextInfo.webAbsoluteUrl
    : location.origin + (location.pathname.match(/^(\/sites\/[^/]+|\/teams\/[^/]+)/) || ["", ""])[1];

  console.log("%cUdtraekker fra " + web, "font-weight:bold");

  async function api(path) {
    const r = await fetch(web + "/_api/" + path, {
      credentials: "include",
      headers: { "Accept": "application/json;odata=nometadata" }
    });
    if (!r.ok) throw new Error("HTTP " + r.status + " " + r.statusText + "  (" + path + ")");
    return r.json();
  }

  // Listetitler kan indeholde apostroffer. I OData fordobles de.
  const byTitle = t => "web/lists/getbytitle('" + encodeURIComponent(t.replace(/'/g, "''")) + "')";

  const failed = [];
  const out = {
    site: web,
    exportedOn: new Date().toISOString().slice(0, 16).replace("T", " "),
    includesData: SAMPLE_ROWS > 0,
    lists: [],
    failedLists: failed
  };

  let all;
  try {
    all = (await api("web/lists?$select=Title,ItemCount,Hidden,BaseTemplate"))
      .value.filter(l => !l.Hidden && l.BaseTemplate === 100)
      .sort((a, b) => a.Title.localeCompare(b.Title));
  } catch (e) {
    console.error("Kunne ikke hente listerne:", e.message);
    console.error("Staar du paa det rigtige site? web = " + web);
    return;
  }

  console.log(all.length + " lister");

  for (const l of all) {
    try {
      const fieldsRaw = (await api(byTitle(l.Title) + "/fields")).value;
      const fields = fieldsRaw
        .filter(f => !SKIP.has(f.InternalName))
        .filter(f => !f.Hidden || f.InternalName === "Title")
        .map(f => {
          const o = {};
          for (const k of FIELD_PROPS) {
            const v = f[k];
            if (v === null || v === undefined || v === "" || v === false) continue;
            if (Array.isArray(v) && v.length === 0) continue;
            o[k] = v;
          }
          return o;
        });

      const entry = { title: l.Title, itemCount: l.ItemCount, fields: fields };

      if (SAMPLE_ROWS > 0 && l.ItemCount > 0) {
        const names = fields.map(f => f.InternalName);
        const rows = (await api(byTitle(l.Title) + "/items?$top=" + SAMPLE_ROWS)).value;
        entry.sample = rows.map(r => {
          const o = {};
          for (const n of names) if (n in r) o[n] = r[n];
          return o;
        });
      }

      out.lists.push(entry);
      console.log("  " + l.Title.padEnd(34) + String(l.ItemCount).padStart(8) + " raekker, "
                  + fields.length + " kolonner");
    } catch (e) {
      failed.push({ list: l.Title, error: e.message });
      console.warn("  FEJLEDE: " + l.Title + " - " + e.message);
    }
  }

  if (failed.length) {
    console.warn("%c" + failed.length + " liste(r) FEJLEDE og mangler i udtraekket. "
      + "Commit det ikke som fuldstaendigt.", "color:red;font-weight:bold");
  }

  const blob = new Blob([JSON.stringify(out, null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "sharepoint-schema.json";
  document.body.appendChild(a);
  a.click();
  a.remove();

  console.log("%cFaerdig. " + out.lists.length + " lister hentet - se sharepoint-schema.json "
    + "i din Downloads-mappe.", "color:green;font-weight:bold");
})();
