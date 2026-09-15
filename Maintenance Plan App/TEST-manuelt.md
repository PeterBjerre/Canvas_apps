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

**Object List** — samme princip, uden multi-select:

4. Med en FL valgt: åbn Object List-dropdownen.
   → Den skal vise de underliggende FL'er. Teksten under siger hvor mange.
5. Vælg en, klik **Tilføj**.
   → Linjen under skal vise `1 valgt: <kode>`.
6. Tilføj en mere, og klik så **Fjern** på en af dem.
   → Tallet og listen skal følge med.
7. Klik **Tilføj** på den samme to gange.
   → Anden gang skal der stå at den allerede er på listen — ingen dublet.

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

## Ryd op bagefter

Slet de rækker, testen oprettede, i alle fire lister — ellers ligger der en
testplan i systemet. Rækkefølgen: `TaskListMain`, `MaintenanceItems`,
`MaintenancePlans`, `MD_RequestIndex`.

---

## Hvis noget fejler

Noter **hvilket punkt**, hvad du gjorde, og hvad der stod — ordret hvis der
kom en fejlbesked. Det er nok til at finde fejlen i koden.
