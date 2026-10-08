# -*- coding: utf-8 -*-
"""
Sletning af en anmodning - EET sted for hubben og de fire domaeneskaerme.

HVORFOR DEN HER FIL FINDES (2026-10-05)
---------------------------------------
"Delete" i hubben og "Delete request" paa domaeneskaermene fjernede KUN
indeksraekken i MD_RequestIndex. Selve anmodningen blev liggende i
domaenets lister, og den kom igen:

  - Equipments og Materials henter alle brugerens raekker, saa de slettede
    kladderaekker stod stadig i listen og kom med i naeste "Save as draft".
  - Var anmodningen aaben paa sin skaerm, opretttede naeste gem
    indeksraekken igen (Patch med Coalesce(LookUp(...), Defaults(...))).
  - IfError(Remove(...); Notify("Request deleted."); true, ...) viste
    succes, ogsaa naar Remove fejlede: en fejl stopper ikke en ;-kaede.

Nu slettes kilden foerst og indeksraekken SIDST. Efter hvert Remove ses
der i Errors(<liste>): hvert trin koeres kun, naar det foregaaende
lykkedes, og succes vises kun, naar alt er slettet. (IfError's serieform
kan ikke bruges: compile kraever, at Remove's tabel og Notify's sandhed
har samme type - check_layout regel 32.) Fejler et trin, staar anmodningen stadig paa hubben
og kan slettes igen - de trin, der allerede er koert, finder intet anden
gang.

Dokumenterne i biblioteket og MD_ApprovalLog roeres ikke: bilag skal ikke
forsvinde ved et uheld, og loggen er sporet.

Alle filtre er paa indekserede kolonner (sharepoint/inspect/out/schema.md):
RequestGuid i EquipmentItems, MaterialItems, FunctionalLocationItems og
FunctionalLocationRequests; PlanKey i MD_TasklistMaterial og
MD_TasklistAttachment; MaintenancePlanID / MaintenancePlanNo (opslag) i
TaskListMain og MaintenanceItems; ID i MaintenancePlans.
"""
import admin_log as alog
import permissions as perm
import request_index as ri
import display_text as dt

INDEX = ri.LIST

# Domaenet (valgvaerdien i MD_RequestIndex.Domain) -> skaermens praefiks i
# den samlede app (BIO SAP App/build/combined.py).
TAGS = {"FunctionalLocation": "Fl", "MaintenancePlan": "Vhp",
        "Equipment": "Eq", "Material": "Mat"}

def stale_var(tag):
    """Saettes af en sletning; domaeneskaermen ser efter den i OnVisible
    (BIO SAP App/build/build_screens.stale_check)."""
    return f"gbl{tag}Stale"


def _steps(domain, guid, sp, key):
    """[(liste, betingelse for at koere, Remove-udtryk)] for domaenets
    kildedata, boern foer foraeldre."""
    if domain == "Equipment":
        return [("EquipmentItems", None,
                 f"Remove(EquipmentItems, Filter(EquipmentItems, RequestGuid = {guid}))")]
    if domain == "Material":
        return [("MaterialItems", None,
                 f"Remove(MaterialItems, Filter(MaterialItems, RequestGuid = {guid}))")]
    if domain == "FunctionalLocation":
        return [
            ("FunctionalLocationItems", None,
             f"Remove(FunctionalLocationItems, Filter(FunctionalLocationItems, RequestGuid = {guid}))"),
            ("FunctionalLocationRequests", None,
             f"Remove(FunctionalLocationRequests, Filter(FunctionalLocationRequests, RequestGuid = {guid}))"),
        ]
    if domain == "MaintenancePlan":
        # Uden SourceItemId kender indeksraekken ikke planen (meget gamle
        # kladder). Saa slettes kun indeksraekken, som foer.
        k, p = f"!IsBlank({key})", f"!IsBlank({sp})"
        return [
            ("MD_TasklistMaterial", k,
             f"Remove(MD_TasklistMaterial, Filter(MD_TasklistMaterial, PlanKey = {key}))"),
            ("MD_TasklistAttachment", k,
             f"Remove(MD_TasklistAttachment, Filter(MD_TasklistAttachment, PlanKey = {key}))"),
            ("TaskListMain", p,
             f"Remove(TaskListMain, Filter(TaskListMain, MaintenancePlanID.Id = {sp}))"),
            ("MaintenanceItems", p,
             f"Remove(MaintenanceItems, Filter(MaintenanceItems, MaintenancePlanNo.Id = {sp}))"),
            # Note to self (issue #115). Listen viser kun de raekker, brugeren
            # maa se - en admin uden Override List Behaviors finder ingen.
            ("VHP_NoteToSelf", None,
             f"Remove(VHP_NoteToSelf, Filter(VHP_NoteToSelf, RequestGuid = {guid}))"),
            ("MaintenancePlans", p,
             f"Remove(MaintenancePlans, Filter(MaintenancePlans, ID = {sp}))"),
        ]
    raise KeyError("Ukendt domaene '%s'" % domain)


def _chain(steps, success):
    """Trin for trin: Remove; If(fejl, besked, naeste trin)."""
    out = success
    for lst, cond, rm in reversed(steps):
        failed = f"!IsEmpty(Errors({lst}))"
        msg = (f'Notify("The request could not be deleted: " & '
               f'First(Errors({lst})).Message, NotificationType.Error)')
        if cond:
            rm = f"If({cond}, {rm})"
            failed = f"{cond} && {failed}"
        inner = "\n".join("    " + l for l in out.split("\n"))
        out = f"{rm};\nIf(\n    {failed},\n    {msg},\n{inner}\n)"
    return out


def delete_fx(prefix, domains, success, me, indent=0):
    """Selve sletningen, naar var<prefix>DelIdx er den friske indeksraekke.

    prefix:  skaermens praefiks ("Md" i hubben, "Dom"/"Vhp"/"Fl" paa
             domaeneskaermene) - variablerne hoerer til skaermen.
    domains: de domaener, skaermen kan slette. Er der flere (hubben),
             vaelges kaeden med Switch paa raekkens Domain.
    success: det, der skal ske, naar ALT er slettet.
    me:      brugerens e-mail (var<X>Me). Sletter en admin en ANDENS
             anmodning, skrives det i MD_ApprovalLog (tools/admin_log.py).

    Vaerdierne laegges i variabler foerst: et filter, der sammenligner
    med en variabel, delegeres; et felt i en record goer ikke altid."""
    idx = f"var{prefix}DelIdx"
    guid, sp, key, dom = (f"var{prefix}DelGuid", f"var{prefix}DelSp",
                          f"var{prefix}DelKey", f"var{prefix}DelDomain")
    index = [(INDEX, None, f"Remove({INDEX}, Filter({INDEX}, RequestGuid = {guid}))")]
    log = (f"If(\n    {perm.as_admin(idx + '.RequesterEmail', me)},\n"
           + alog.write(guid, key, alog.DELETE,
                        f'"Request deleted (" & {dt.status(idx + ".Status.Value")} & ", owner " & '
                        f'{idx}.RequesterEmail & ")"', 4)
           + "\n);\n")
    success = log + success
    head = (f"Set({guid}, {idx}.RequestGuid);\n"
            f"Set({sp}, {idx}.SourceItemId);\n"
            f"Set({key}, {idx}.{ri.COL_NO});\n"
            f"Set({dom}, {idx}.Domain.Value);\n")
    if len(domains) == 1:
        body = head + _chain(_steps(domains[0], guid, sp, key) + index, success)
    else:
        branches = []
        for d in domains:
            ch = _chain(_steps(d, guid, sp, key) + index, success)
            branches.append(f'    "{d}",\n' + "\n".join("        " + l for l in ch.split("\n")))
        body = (head + f"Switch(\n    {dom},\n" + ",\n".join(branches) + ",\n"
                '    Notify("This kind of request cannot be deleted here.", NotificationType.Warning)\n)')
    pad = " " * indent
    return "\n".join(pad + l for l in body.split("\n"))


def may_delete(idx, me):
    """Maa brugeren slette raekken? Ejeren sin kladde; en admin alle
    anmodninger i Kladde og AfventerInfo (tools/permissions.py)."""
    return perm.may_change(f"{idx}.RequesterEmail", f"{idx}.Status.Value", me)


DENIED = ('If(' + perm.IS_ADMIN + ', '
          'Notify("Only drafts and requests awaiting info can be deleted.", NotificationType.Warning), '
          'Notify("Only drafts can be deleted.", NotificationType.Warning))')
GONE = 'Notify("This request no longer exists.", NotificationType.Warning)'
