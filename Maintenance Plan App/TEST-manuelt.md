# Manuel test af VH-plan appen

Køres i browseren efter synk. Ingen Copilot-tokens bruges.

Der er **fem ting** at se efter. Tag dem i rækkefølge — de bygger på hinanden.

---

## 1. Layoutet (30 sekunder)

| Hvor | Hvad du skal se |
|---|---|
| **Item Editor** | Functional Location og Object List står **oven på hinanden i højre kolonne**. De øvrige felter i to kolonner til venstre |
| **Plan Header** | **First Call** dag, måned og år på **én række** i den sidste af de fire kolonner, med label `First Call (dd / mm / åååå)` |

Træk vinduet ned til ca. 900 px bredde. Intet må blive klippet.

---

## 2. Functional Location (2 minutter)

Feltet er bygget helt om. Der er **ingen combobox** længere — den viste ikke
de rækker, den fik. Nu er der et søgefelt, en **Søg**-knap og en almindelig
dropdown, præcis som de øvrige felter.

1. Vælg et item. Skriv `SSV13 HFC10` i Functional Location-feltet og klik
   **Søg**.
   → Beskeden skal sige hvor mange der blev fundet, **og for hvilken tekst**.
   → Dropdownen nedenunder skal nu indeholde dem. Åbn den og bekræft.
2. Vælg en i dropdownen.
   → Linjen under skal vise `Valgt: <kode> - <beskrivelse>`.
   → Er den ikke vedligeholdbar i SAP, skal der stå en rød advarsel.
3. Klik **Søg** med under 7 tegn i feltet.
   → Der skal komme en advarsel, og flowet må ikke kaldes.

**Object List** — multi-select med afkrydsning:

4. **Uden** en FL valgt: listen skal være tom, og der skal stå *"Vælg først
   en Functional Location ovenfor."*
   → Den må **ikke** vise hele søgeresultatet.
5. Med en FL valgt: listen skal vise de underliggende objekter, ét pr. linje
   med et afkrydsningsfelt. Teksten under siger hvor mange der er mulige.
6. **Sæt flere krydser i træk.** Linjen under skal tælle med hver gang —
   `1 valgt:`, `2 valgt:` osv. Der er ingen knap at trykke på.
7. Fjern et kryds igen → tallet og listen følger med.
8. Skift til et **andet item** og tilbage igen.
   → Krydserne skal stå som du efterlod dem. Hvert item har sin egen liste.
9. Med objekter valgt: gå tilbage og vælg en **anden** Functional Location.
   Linjen med de valgte skal blive **rød** og advare om, at nogle af dem
   ikke ligger under den nye FL. De ryddes **ikke** i stilhed.

## 3. Strategidelen (1 minut)

1. Skift **Plan Type** til `Strategiplan (IP42)`.
2. Åbn **Maintenance Strategy**. Der skal stå **53** strategier, og **52** af
   dem skal være mærket `(pakker mangler)`.
3. Vælg **101** (mærket). Pakkematricen skal være **væk**, og knapperne
   *Hierarki-udfyld* / *Alle pakker* / *Ryd pakker* skal være **skjulte** —
   ikke bare grå. I stedet står forklaringen om at strategien ikke har pakker.
4. Vælg **128**. Nu tegnes matricen med tre kolonner: `1Y`, `2Y`, `3Y`.
5. *Hierarki-udfyld* skal være **grå**, og under den skal stå en linje om at
   det ikke er afklaret, om strategien er hierarkisk. **Klik på den med
   musen** — der må ikke ske noget.
6. *Alle pakker* skal virke og sætte kryds i alle tre.

---

## 4. Gemningen — det nye (5 minutter)

**Før du begynder:** noter det sidste `PlanID` i `MaintenancePlans`, fx
`MP0068`. Det skal du bruge i trin 3 nedenfor.

Byg en lille plan:

1. Værk `SSV`, Plan Type `Single cycle`, udfyld Plan Text, Cycle, Unit,
   Call Horizon og First Call.
2. Tilføj **ét** item: FL, Item Short Text, Main Work Center.
3. Tilføj tasklist-operationer til item'et.
4. Klik **Gem kladde** nederst (Step 6).

Der skal komme en grøn besked med et `MP`-nummer.

### Tjek i SharePoint

| Liste | Hvad der skal stå |
|---|---|
| `MaintenancePlans` | Ny række. `PlanID` = **næste nummer i serien** (havde du `MP0068`, skal den nye være `MP0069`). `Status` = `Draft`. `PlantsInitial` = SSV. `CallHorizon` = et **tal**. `StrategyKey` tom |
| `MaintenanceItems` | Én række. `MaintenancePlanNo` peger på planen. `ItemID` fortsætter `MI`-serien. `OrstedResponsibleEmail` = din mail i småt. `Priority` = `Yellow (default)` |
| `TaskListMain` | Én række pr. operation. `OperationNo` = 10, 20, 30 … `TaskID` skal være **tom** |
| `MD_RequestIndex` | **Én** ny række. `RequestNo` = `MP`-nummeret, `Domain` = `MaintenancePlan`, `Status` = `Kladde`, `StatusStep` = 1, `IsOpen` = ja, `ItemCount` = 1 |

> **Er `PlanID` ikke det næste i serien**, så stop og sig til. Så er offsettet
> udledt forkert, og det skal rettes før der gemmes mere.

### Gem igen

5. Klik **Gem kladde** igen uden at ændre noget.
   → Der må **ikke** komme en ny plan eller en ny indeksrække. De
   eksisterende opdateres, og antallet af items og operationer er uændret.
6. Tilføj et item mere og gem igen.
   → Nu to items, og `ItemCount` i indeksrækken følger med.
7. Klik **Indsend**.
   → `MaintenancePlans.Status` bliver `In Progress`, og indeksrækken
   `Indsendt` / trin 2.

---

## 5. Landingssiden (30 sekunder)

Åbn **Masterdata Hub**. Indmeldingen skal stå under "Mine indmeldinger" med
rigtigt nummer, tekst, værk og status.

Klik **Åbn** på rækken → VH-plan appen åbnes i en ny fane.

---

## 6. Feltforklaringer og de nye regler (3 minutter)

### Hjælpepanelerne

Der skal være en **? Hjælp**-knap i overskriften på fire sektioner: Plan
Header, Item Editor, Tasklist and Operations, Strategy Packages.

1. Klik **? Hjælp** på Plan Header.
   → Et lyseblåt panel folder sig ud under overskriften. Knappen skifter til
   **Skjul hjælp** og bliver blå. Nederst i panelet står kilden.
2. Klik igen → panelet forsvinder, knappen bliver grå igen.
3. Gentag på de tre andre sektioner. De fire paneler er uafhængige — alle
   fire kan være åbne samtidig.

### Hints der ændrer sig

Hint-linjen under et felt skal **ændre tekst**, når forudsætningen ændrer
sig. Det er den vigtigste del af testen — en hint, der står stille, er en
statisk tekst, der er sluppet forbi.

| Gør dette | Hinten skal skifte til |
|---|---|
| Sæt Plan Type = `Strategy` | Strategy-hinten nævner pakkerne nedenfor |
| Skriv Plan Text uden værkskoden | PlanText-hinten siger, at teksten bør starte med værkskoden |
| Sæt et items Activity Type til `110` | Sort Field-hinten skifter til "Påkrævet: 1 item …" |
| Sæt samme items Main Work Center til noget uden `SUP` | MainWorkCenter-hinten peger på `*SUP` |
| Sæt Revision på et item | FirstCall-hinten siger 01/01 |
| Tilføj en operation uden Main Work Center | Linjen over operationstabellen nævner operation 0010 |
| Udfyld arbejdscentret, men lad short text stå tom | Samme linje skifter til "1 operation(er) mangler short text" |

### R1–R5 i valideringen

Alle fem skal dukke op i fejlpanelet øverst og blokere **Indsend**.

1. **R1** — Plan Text der ikke starter med værkskoden.
2. **R2** — et item med activity type `110`, og Sort Field tomt på planen.
3. **R3** — samme item med et Main Work Center uden `SUP`.
4. **R4** — et item med revisionsmærke, og First Call ≠ 01/01.
5. **R5** — Scheduling Period under 2 år.

Ret hver fejl → beskeden skal forsvinde igen, og Indsend skal blive aktiv,
når den sidste er væk.

---

## Ryd op bagefter

Slet de rækker, testen oprettede, i alle fire lister — ellers ligger der en
testplan i systemet. Rækkefølgen: `TaskListMain`, `MaintenanceItems`,
`MaintenancePlans`, `MD_RequestIndex`.

---

## Hvis noget fejler

Noter **hvilket punkt**, hvad du gjorde, og hvad der stod — ordret hvis der
kom en fejlbesked. Det er nok til at finde fejlen i koden.
