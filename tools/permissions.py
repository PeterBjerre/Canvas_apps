# -*- coding: utf-8 -*-
"""
Hvem maa aendre og slette en anmodning - EET sted for hubben og de fire
domaeneskaerme (2026-10-05).

ADMIN
-----
Admin-listen er den samme, de gamle apps brugte: UserAndGroups med
Title = "Admin" og Member = brugerens e-mail med smaa bogstaver
(sharepoint/inspect/out/schema.json: begge kolonner er Text, 7 raekker).
Opslaget er een delegerbar LookUp i en navngiven formel. Navngivne formler
evalueres dovent og huskes, saa listen laeses hoejst een gang pr. session,
og kun hvis en formel faktisk spoerger.

UserAndGroups skal tilfoejes som datakilde i Studio (BIO SAP App har den
ikke i dag).

REGLEN
------
  Ejer:   maa aendre og slette sin egen anmodning, mens den er en kladde.
  Admin:  maa aendre og slette ALLE anmodninger i Kladde og AfventerInfo,
          uanset hvem der ejer dem.
  VH-plan: ejeren maa ogsaa aendre (ikke slette) sin plan i AfventerInfo -
          den er sendt retur i godkendelsen og skal rettes og indsendes
          igen. Kun VH-planen har det forloeb i appen (docs/32 §3).

Reglen staar baade i UI'et (Visible/DisplayMode) og i selve handlingen
(gem, indsend, slet), som slaar raekken op igen foer den skriver. En
skjult knap er ikke en sikring.
"""
import request_index as ri
import env_config as env

ADMIN_LIST = "UserAndGroups"
ADMIN_GROUP = "Admin"
IS_ADMIN = "IsAdmin"
# Godkender (issue #115): brugeren staar som 1. eller 2. godkender i
# MD_Approver. Listen har initialer (PKBJE); flowene danner mailen som
# initialer + @ + BioSap-EmailDomain, saa initialerne er delen foer @.
APPROVER_LIST = "MD_Approver"
MY_UID = "MyUserId"
IS_APPROVER = "IsApprover"

OWNER_STATUSES = (ri.DRAFT,)
ADMIN_STATUSES = (ri.DRAFT, "AfventerInfo")
# Domaener, hvor ejeren retter og genindsender en anmodning, der er sendt
# retur (AfventerInfo). Domaenenoeglen fra request_index.DOMAINS.
# R2-014: ogsaa FL, og Material/Measuring Point, naar deres godkendelse er
# slaaet til - flowene og docs/36 beder rekvirenten rette og indsende igen.
# Uden godkendelse sendes de aldrig retur. Equipment har ingen retur.
RESUBMIT_DOMAINS = ("MaintenancePlan", "FunctionalLocation") + tuple(
    d for d, flag in (("Material", "material_approval"),
                      ("MeasuringPoint", "measuring_point_approval"))
    if env.feature_on(flag))
RESUBMIT_STATUSES = (ri.DRAFT, "AfventerInfo")


def formula():
    """Den navngivne formel til App.Formulas. Ordret ens i alle apps, saa
    BIO SAP App's sammenlaegning (generate_app.build_formulas) beholder een."""
    return (
        "// ADMIN. Genereret af tools/permissions.py - ret ikke her.\n"
        "// Een delegerbar LookUp i admin-listen, laest dovent og kun een gang.\n"
        f"{IS_ADMIN} = !IsBlank(LookUp({ADMIN_LIST}, Title = \"{ADMIN_GROUP}\" "
        "&& Member = Lower(User().Email)));"
    )


def approver_formula():
    """IsApprover og MyUserId til App.Formulas (issue #115). Samme regel
    som flowene: en godkender er en raekke i MD_Approver med brugerens
    initialer som Approver1 eller Approver2. Systemnummeret pr. item kommer
    fra Power BI og kendes ikke i appen, saa reglen er "godkender i
    processen", ikke "godkender af netop det item" - se
    tools/submission_notes.py. MyUserId er en navngiven formel, saa
    LookUp'en delegeres."""
    return (
        "// GODKENDER. Genereret af tools/permissions.py - ret ikke her.\n"
        f"{MY_UID} = Upper(First(Split(User().Email, \"@\")).Value);\n"
        f"{IS_APPROVER} = !IsBlank(LookUp({APPROVER_LIST}, Approver1 = {MY_UID} "
        f"|| Approver2 = {MY_UID}));"
    )


def _in(status, statuses):
    return "(" + " || ".join(f'{status} = "{s}"' for s in statuses) + ")"


def is_owner(email, me):
    """email: udtryk for anmodningens RequesterEmail. me: brugerens e-mail
    med smaa bogstaver (var<X>Me)."""
    return f'Lower(Coalesce({email}, "")) = {me}'


def may_change(email, status, me, resubmit=False):
    """Maa brugeren aendre/slette? status er et tekstudtryk (fx
    R.Status.Value). resubmit=True: domaenet er i RESUBMIT_DOMAINS, saa
    ejeren maa ogsaa aendre en anmodning, der er sendt retur. Sletning
    kalder altid uden (request_delete.may_delete)."""
    own = RESUBMIT_STATUSES if resubmit else OWNER_STATUSES
    return (f"(({is_owner(email, me)} && {_in(status, own)}) || "
            f"({IS_ADMIN} && {_in(status, ADMIN_STATUSES)}))")


def may_change_row(item, me):
    """may_change for en raekke i MD_RequestIndex, hvor domaenet staar paa
    raekken (hubben): ejerens AfventerInfo gaelder kun RESUBMIT_DOMAINS."""
    email, status = item + ".RequesterEmail", item + ".Status.Value"
    back = [s for s in RESUBMIT_STATUSES if s not in OWNER_STATUSES]
    return (f"({may_change(email, status, me)} || "
            f"({is_owner(email, me)} && {_in(status, back)} && "
            f"{_in(item + '.Domain.Value', RESUBMIT_DOMAINS)}))")


def as_admin(email, me):
    """Aendrer brugeren som admin - altsaa i en andens anmodning? Saa
    skal aendringen logges (opgave 4). En admin i sin egen anmodning er
    en almindelig aendring."""
    return f"({IS_ADMIN} && !({is_owner(email, me)}))"


def may_change_ui(item, me):
    """Hubbens Edit/Delete-knapper. En almindelig bruger ser dem som i dag
    (paa alle sine egne anmodninger - handlingen afgoer status); en admin
    ser dem ogsaa paa andres i Kladde og AfventerInfo."""
    return (f"{is_owner(item + '.RequesterEmail', me)} || "
            f"({IS_ADMIN} && {_in(item + '.Status.Value', ADMIN_STATUSES)})")
