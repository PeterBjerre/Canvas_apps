# Implementeringsplan

Rækkefølgen er valgt, så det, der er dyrest at lave om, ligger først.

## Fase 0 – afklaring (før build)

Besvar de seks åbne spørgsmål i `01-loesningsoplaeg.md` §10. Særligt disse to,
fordi de ændrer omfanget markant:

- **Oprettes arbejdsplaner gennem appen?** Nej ⇒ trin 5 og hele
  `VHP_TaskList`/`VHP_Operation`-delen udgår. Det halverer arbejdet.
- **Hierarki-semantik.** Afgør hvordan matricen skal udfyldes i praksis.

Lav samtidig en **papirgennemgang med to reelle strategiplaner**, I har
oprettet for nylig. Hvis datamodellen kan rumme dem felt for felt, holder den.

## Fase 1 – fundament

| # | Opgave | Leverance |
|---|---|---|
| 1.1 | Provisionér lister i DEV | `Provision-VHPlanLists.ps1` kørt |
| 1.2 | Indlæs masterdata | Strategier + pakker fra SAP (eller seed-CSV) |
| 1.3 | Indekser og tilladelser | Jf. `02-datamodel-sharepoint.md` §3 |
| 1.4 | Løsningsopsætning | Solution, connection references, DEV/TEST/PROD |

Sanity-tjek før 1.4: kan `Filter(MD_ValueHelp, Domain = "WORKCENTER")` køre
uden delegationsadvarsel? Kan den ikke det, er indekset ikke sat rigtigt, og
det bliver kun dyrere at opdage senere.

## Fase 2 – app, uden matrix

Genbrug den eksisterende single cycle-app som udgangspunkt, men flyt den over
på den nye datamodel. Trin 1–4, 6, 7 og gem/submit.

Slutmål for fasen: en single cycle-plan kan indmeldes end-to-end på den nye
model. **Den gamle app kan pensioneres her**, uafhængigt af om strategidelen
bliver færdig.

## Fase 3 – strategier og pakker

| # | Opgave |
|---|---|
| 3.1 | Trin 2: strategivalg, pakkeoverblik, default af parametre |
| 3.2 | `cmpPackageMatrix` – nested gallery, toggle, række/kolonne-handlinger |
| 3.3 | Hierarki-udfyld og kopiér-fra |
| 3.4 | Validering S1–S8 |
| 3.5 | `cmpCycleTimeline` – HTML-forhåndsvisning |

3.2 er den eneste opgave med reel teknisk risiko. Byg den som en isoleret
komponent med hårdkodede testdata **først**, og mål rendertiden med 40
operationer × 8 pakker, før den kobles på resten.

## Fase 4 – proces og udlevering

| # | Opgave |
|---|---|
| 4.1 | Submit-flow med serverside-validering (samme regler som 03-validering.fx) |
| 4.2 | Godkendelsesflow + `VHP_StatusLog` |
| 4.3 | PDF-resumé (mulighed A i `04-integration-sap.md`) |
| 4.4 | Tilbageskrivning af SAP-plannummer |

## Fase 5 – drift

| # | Opgave |
|---|---|
| 5.1 | Natligt masterdata-sync fra SAP |
| 5.2 | Oprydningsflow for forældreløse rækker |
| 5.3 | Arkivering af anmodninger > 12 mdr. |
| 5.4 | `VHP_ClientLog` + enkelt driftsdashboard |

## Fase 6 – valgfrit

- PCF-komponent til matricen, hvis > 50 operationer viser sig at være normen
- Direkte SAP-integration (mulighed B eller C)
- Multiple counter plans (IP43)

---

## De fem ting, der typisk går galt

1. **Pakkerne lægges på planen i stedet for på arbejdsplanens operationer.**
   Opdages først, når SAP-siden skal nøgle det, og kræver ommodellering.
   Se `01-loesningsoplaeg.md` §2.
2. **Junction-liste til matricen.** 200 skrivninger pr. submit, halve
   gemninger og en app, brugerne tror er gået ned. Brug `PackagesKey`.
3. **Lookup-kolonner til relationerne.** Fungerer fint med 50 testrækker og
   knækker med delegationsadvarsler ved 2.000.
4. **Validering kun i appen.** Listerne er tilgængelige uden om appen.
   Reglerne skal også findes i submit-flowet.
5. **Manuelt vedligeholdte strategier.** Afviger fra SAP, og så validerer
   appen mod fiktion.

## Hvad der kan skæres væk, hvis tiden er knap

I prioriteret rækkefølge — øverst skæres først:

- HTML-tidslinjen (fase 3.5). Pæn og pædagogisk, men ikke nødvendig for at
  indmelde korrekt.
- Kopiér-fra og hierarki-udfyld (3.3). Genveje, ikke funktionalitet.
- Objektliste pr. position (`VHP_ItemObject`). Kan starte med ét objekt
  pr. position.
- Admin-skærmen til masterdata. Rediger i SharePoint-listen indtil videre.

Det, der **ikke** kan skæres væk: validering S1–S6, serverside-validering
og `requestGuid`.
