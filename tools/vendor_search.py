# -*- coding: utf-8 -*-
"""
Leverandoersoegning via Power Automate - til PM02-operationerne i VH-planen.

Samme soegning og samme vaelger som Functional Location paa items
(tools/fl_picker.py, tools/build_flsearch.py): skriv i comboboksen, tryk
Search (eller Enter), og flowets svar fylder listen. Det, man derefter
skriver, filtrerer svaret lokalt uden nye kald.

FLOW-KONTRAKTEN (laest direkte i solution-eksporten,
solution/BIOSAP/src/Workflows/BioSap-Integration-VendorsAll-*.json)
---------------------------------------------------------------------
Flowet hedder BioSap-Integration-VendorsAll. Udloeseren er PowerApp V2
med EET tekst-input ("VendorFilterPar"). Flowet koerer en DAX-forespoergsel
mod Power BI-datasaettet Vendors:

    SEARCH("<tekst>", 'Vendors'[Vendor Search], 1, 0) >= 1

altsaa en delstreng-soegning uden hensyn til store og smaa bogstaver, hvor
spaerrede leverandoerer (Block Purchasing) og slettede (Centr. Del. Flag)
er sorteret fra. Hoejst 100 leverandoerer kommer tilbage (TOPN 100).

"Respond to a Power App or flow" har to tekst-outputs:

    vendoroutput           JSON-STRENG med raekkerne (firstTableRows)
    vendoroutputcompleted  den faste tekst "VendorOutputCompleted"

Raekkerne har kolonnerne fra SUMMARIZECOLUMNS:

    [ { "Vendors[Vendor Search]": "101985 - PERSOLIT ENTREPRENOERFIRMA A/S",
        "[SumVendor_Number]": 101985,
        "[IsGrandTotalRowTotal]": false }, ... ]

ROLLUPADDISSUBTOTAL giver ogsaa en total-raekke UDEN Vendor Search - den
sorteres fra her. Vi laeser kun Vendor Search: det er praecis den tekst,
TaskListMain.Vendor (Text) i forvejen gemmer ("101985 - PERSOLIT ..."), og
SAP-opretteren tager leverandoernummeret som de foranstillede cifre
(excel/opretter/VhpMap.bas, VendorNo). Den gamle Maintenance Plan-app
brugte samme felt (colVendorSearchData). Antagelse: navnet paa
JSON-noeglen er "Vendors[Vendor Search]" som i den gamle app - det er
ikke set i et koerende svar herfra.

FORUDSAETNING: flowet skal vaere tilfoejet BIO SAP-appen som datakilde i
Studio (og gemt), foer YAML'en deployes. Ellers fejler compile paa et
ukendt navn.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_flsearch as fl

FLOW_NAME = "'BioSap-Integration-VendorsAll'"
FLOW_OUTPUT = "vendoroutput"
JSON_SEARCH_FIELD = "'Vendors[Vendor Search]'"

# Flowet soeger paa en delstreng, saa tre tegn er nok til et nummer eller
# et navn - og svaret er alligevel hoejst 100 raekker.
MIN_SEARCH_LEN = 3

PLACEHOLDER = f'"At least {MIN_SEARCH_LEN} characters - vendor number or name"'


def collect_results(target_collection, *, raw_var):
    """Flowets raekker i samme skema som FL-vaelgerens samling (Code,
    Description, Display, Maintainable, Level), saa fl_picker kan vise
    dem uaendret. Code er Vendor Search - den tekst, der gemmes."""
    return (
        f"ClearCollect(\n"
        f"    {target_collection},\n"
        f"    Filter(\n"
        f"        ForAll(\n"
        f"            Table(ParseJSON({raw_var}.{FLOW_OUTPUT})) As R,\n"
        f"            With(\n"
        f"                {{ s: Trim(Text(R.Value.{JSON_SEARCH_FIELD})) }},\n"
        f"                {{ Code: s, Description: s, Display: s, Maintainable: true, Level: \"\" }}\n"
        f"            )\n"
        f"        ),\n"
        f"        !IsBlank(Code)\n"
        f"    )\n"
        f")"
    )


def search_action(query_ctrl, target_collection, msg_var, *, raw_var, **kw):
    """build_flsearch.search_action med leverandoerflowet bag.

    Et anfoerselstegn i soegeteksten ville bryde DAX-strengen i flowet, saa
    det fjernes, foer teksten sendes."""
    kw.setdefault("label", "vendors")
    return fl.search_action(
        query_ctrl, target_collection, msg_var, raw_var=raw_var,
        flow_name=FLOW_NAME, flow_output=FLOW_OUTPUT,
        collect_fx=collect_results, run_arg='Substitute(q, Char(34), "")', **kw)
