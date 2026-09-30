# -*- coding: utf-8 -*-
"""
MD_RequestIndex - den faelles indeksliste bag landingssiden. EET sted.

HVORFOR DEN HER FIL FINDES
--------------------------
Indeksraekken blev skrevet tre steder - tools/domain_parts.py (Equipment og
Material), Functional Location App/build/fl_save.py og Maintenance Plan
App/build/build_save.py - med kopierede literaler for domaene, status, trin
og IsOpen. Kommentarerne sagde "SKAL vaere ordret den samme som i
hub_config.py", men intet tjekkede det, og felterne var ikke ens:
SourceItemId manglede i Equipment/Material, LastActionBy blev ikke altid
skrevet (REVIEW.md A13).

Nu kommer domaenenoeglerne, statusordforraadet og selve raekken herfra.
Hubben (hub_config.STATUS) laeser det samme ordforraad, og tests/ holder det
op mod valgene i sharepoint/provision/Provision-RequestIndex.ps1.
"""
import env_config as env

LIST = "MD_RequestIndex"

# Title er omdoebt til RequestNo (Provision-RequestIndex.ps1). Power Fx
# binder paa visningsnavnet.
COL_NO = "RequestNo"

# Valgvaerdierne i kolonnen Domain - ORDRET som i provisioneringen.
DOMAINS = ("FunctionalLocation", "Equipment", "MeasuringPoint", "Material",
           "MaintenancePlan")

# Statusordforraadet: (SharePoint-vaerdi, engelsk etiket, trin).
#
# FOERSTE felt skrives af domaeneapperne og laeses af flowene - det maa
# IKKE oversaettes. Trin 1-5 baeres som tal i indekset, saa hubben kan tegne
# forloebet; trin 0 = afsluttet uden oprettelse.
STATUS = (
    ("Kladde",          "Draft",          1),
    ("Indsendt",        "Submitted",      2),
    ("UnderBehandling", "In progress",    3),
    ("AfventerInfo",    "Awaiting info",  3),
    ("KlarTilSAP",      "Ready for SAP",  4),
    ("OprettetISAP",    "Created in SAP", 5),
    ("Afvist",          "Rejected",       0),
    ("Annulleret",      "Cancelled",      0),
)
_STEP = {k: step for k, _label, step in STATUS}

# De to, apperne selv skriver.
DRAFT = "Kladde"
SUBMITTED = "Indsendt"

# AppUrl PEGER PAA DEN SAMLEDE APP (2026-09-30)
#
# BIO SAP App er den app, der skal bruges; de fem enkeltapps udfases. En
# anmodning aabnes derfor i den samlede app, paa sin egen skaerm:
#
#     <BIO SAP play-URL>?domain=<appnoegle>&reqid=<RequestGuid>
#
# Det gaelder ogsaa en anmodning, der er gemt fra en af enkeltapperne,
# mens de stadig findes. BIO SAP App/build/combined.py laeser samme
# parameternavn.
COMBINED_APP = env.COMBINED
DOMAIN_PARAM = "domain"


def step(status):
    """Trinnet for en statusvaerdi. Et ukendt navn er en fejl ved bygning -
    ikke en raekke uden farve paa landingssiden."""
    if status not in _STEP:
        raise KeyError("Ukendt status '%s'. Kendte: %s" % (status, ", ".join(_STEP)))
    return _STEP[status]


def _check_domain(domain):
    if domain not in DOMAINS:
        raise KeyError("Ukendt domaene '%s'. Kendte: %s" % (domain, ", ".join(DOMAINS)))


def record(domain, app_key, status, *, request_no, guid, me, short_text,
           plant, item_count, source_id=None, indent=16):
    """Indeksraekken som Power Fx-record - de SAMME felter fra alle apps.

    Argumenterne er Power Fx-udtryk (fx "varDomRequestGuid"), undtagen
    domain, app_key og status, som er Python-tekst og efterproeves her.

    AppUrl er den SAMLEDE apps play-URL med ?domain=<app_key>&reqid= (se
    COMBINED_APP). Hubben bygger selv "Open" af domaenet
    (build_hub._open_action); AppUrl er reserven og linket til flows."""
    _check_domain(domain)
    if app_key not in env.screen_apps():
        raise KeyError("'%s' er ikke en domaeneskaerm i den samlede app. Kendte: %s"
                       % (app_key, ", ".join(env.screen_apps())))
    url = env.play_url(COMBINED_APP)
    if not url:
        raise SystemExit("'%s' har intet app_id i miljoeet '%s' (tools/canvas_apps.json)."
                         % (COMBINED_APP, env.ENV_NAME))
    fields = [
        f"{COL_NO}: {request_no}",
        f'Domain: {{ Value: "{domain}" }}',
        f'Status: {{ Value: "{status}" }}',
        f"StatusStep: {step(status)}",
        # Apperne skriver kun Kladde og Indsendt - begge er aabne. Flows,
        # der lukker en anmodning, saetter IsOpen selv.
        "IsOpen: true",
        f"RequestGuid: {guid}",
        f"RequesterEmail: {me}",
        "RequesterName: User().FullName",
        f"ShortText: {short_text}",
        f"Plant: {plant}",
        f"ItemCount: {item_count}",
    ]
    if source_id is not None:
        fields.append(f"SourceItemId: {source_id}")
    fields += [
        f'AppUrl: "{url}?{DOMAIN_PARAM}={app_key}&reqid=" & {guid}',
        "LastActionOn: Now()",
        f"LastActionBy: {me}",
    ]
    pad = " " * indent
    return "{\n" + ",\n".join(pad + "    " + f for f in fields) + "\n" + pad + "}"


def number_expr(prefix, id_expr):
    """Anmodningsnummeret: praefiks + listens ID med seks cifre (EQ-000912)."""
    return f'"{prefix}-" & Text({id_expr}, "000000")'
