(function () {
  window.BOOK2_FAQ_DATA = {
    analysis: {
      totalRows: 15651,
      dateMin: "2018-01-30",
      dateMax: "2026-07-03",
      note: "Bygget på fuldt udtræk af Query1 (alle rækker).",
    },
    items: [
      {
        id: "faq-001",
        category: "Kom godt i gang",
        question: "Hvilke oplysninger skal altid med i en indberetning?",
        answer:
          "Start med en kort problemformulering, så modtageren forstår hvad der er galt uden at læse hele tråden.\nAngiv derefter objektet præcist (FL, udstyr, plan eller ordre) og hvilket resultat du ønsker.\nSlut med tidsbehov, driftsmæssig konsekvens og hvem der kan godkende den faglige løsning.",
        roles: ["Maintenance Planner", "Maintenance Scheduler", "Support"],
        transactions: ["IL03", "IE03", "IP03", "IW33"],
      },
      {
        id: "faq-002",
        category: "Kom godt i gang",
        question: "Hvordan skriver jeg en emnelinje, så sagen behandles hurtigere?",
        answer:
          "Brug formatet handling + objekt + problemtype, fx 'Rettelse af VH-plan kaldfrekvens'.\nUndgå interne forkortelser som kun få personer forstår, medmindre de er standard i teamet.\nHold samme emnelinje i hele tråden, så historik og ansvar ikke splittes over flere sager.",
        roles: ["Maintenance Scheduler", "Senior Maintenance Engineer"],
      },
      {
        id: "faq-003",
        category: "Kom godt i gang",
        question: "Hvordan undgår jeg dubletter af samme sag?",
        answer:
          "Svar altid i den eksisterende tråd, også når du tilføjer nye bilag eller ekstra afklaring.\nHvis en ny tråd oprettes ved en fejl, så link tydeligt til hovedtråden i første svar.\nAftal i teamet hvem der ejer tråden, så opdateringer går samme vej hver gang.",
        roles: ["Support", "Maintenance Supervisor"],
      },
      {
        id: "faq-004",
        category: "Kom godt i gang",
        question: "Skal jeg validere data i SAP før jeg indberetter?",
        answer:
          "Ja, kontroller altid nuværende status før du beder om ændring, så sagen ikke bygger på antagelser.\nNotér kort hvad du har tjekket og hvad du så i systemet, fx status eller relationer.\nDet reducerer afklaringsrunder markant og gør implementering hurtigere.",
        roles: ["Maintenance Planner", "Senior Operations Engineer"],
        transactions: ["IL03", "IE03", "IP03", "IW33"],
      },
      {
        id: "faq-005",
        category: "Kom godt i gang",
        question: "Hvornår er en indberetning klar til behandling uden ekstra spørgsmål?",
        answer:
          "Når scope, ønsket ændring og teknisk begrundelse er skrevet så konkret, at en anden kan udføre ændringen direkte.\nNår ejerskab og godkender er tydelige, så support ikke skal bruge tid på at finde beslutningstager.\nNår konsekvens ved ikke at ændre noget er beskrevet i én tydelig sætning.",
        roles: ["Maintenance Supervisor", "Senior Project Manager"],
      },
      {
        id: "faq-006",
        category: "VH-plan",
        question: "Hvordan opretter jeg en ny vedligeholdelsesplan korrekt?",
        answer:
          "Definér først planens formål og hvilken vedligeholdelsesstrategi der skal understøttes.\nOpret derefter plan med korrekt cyklus, startdato, objekt og tydelige item-tekster.\nKontrollér til sidst at planen kan kalde i den ønskede rytme uden manuelle undtagelser.",
        roles: ["Maintenance Planner", "Senior Maintenance Scheduling Engineer"],
        transactions: ["IP41"],
      },
      {
        id: "faq-007",
        category: "VH-plan",
        question: "Hvordan retter jeg en eksisterende vedligeholdelsesplan?",
        answer:
          "Ret kun de felter der er nødvendige, og undgå brede ændringer uden faglig afklaring.\nSkriv i indberetningen præcis hvilke felter der ændres og hvad den nye værdi skal være.\nBekræft efterfølgende at ændringen ikke påvirker andre planer eller kald utilsigtet.",
        roles: ["Maintenance Scheduler", "Maintenance Engineer"],
        transactions: ["IP42", "IP43"],
      },
      {
        id: "faq-008",
        category: "VH-plan",
        question: "Hvad skal jeg beskrive, når jeg ændrer frekvens eller cyklus?",
        answer:
          "Angiv nuværende frekvens og ønsket frekvens med tydelig dato for ikrafttrædelse.\nBeskriv hvorfor ændringen er nødvendig ud fra drift, sikkerhed eller compliance.\nTilføj hvad der skal ske med eksisterende kommende kald, så planlægning ikke bliver tvetydig.",
        roles: ["Maintenance Scheduler", "Senior Process Specialist"],
        transactions: ["IP42", "IP10"],
      },
      {
        id: "faq-009",
        category: "VH-plan",
        question: "Hvornår opretter jeg ny plan i stedet for at rette den gamle?",
        answer:
          "Opret ny plan når omfang, strategi, ansvar eller objektliste ændres væsentligt.\nRet eksisterende plan ved mindre tekst- eller parameterjusteringer uden nyt forretningsscope.\nHvis du er i tvivl, så dokumentér begge muligheder og bed om hurtig faglig beslutning.",
        roles: ["Maintenance Planner", "Maintenance Supervisor"],
        transactions: ["IP41", "IP42"],
      },
      {
        id: "faq-010",
        category: "VH-plan",
        question: "Hvordan undgår jeg gentagne rettelser på samme plan?",
        answer:
          "Saml alle ændringspunkter i én samlet liste før første implementering.\nLad faglig ejer gennemgå listen og godkende prioritering inden ændring udføres.\nKør en afsluttende validering i visning, så nye afvigelser ikke opstår efter lukning.",
        roles: ["Maintenance Planner", "Senior Maintenance Engineer"],
        transactions: ["IP43"],
      },
      {
        id: "faq-011",
        category: "Kald og item",
        question: "Hvordan retter jeg maintenance items på en plan?",
        answer:
          "Beskriv item for item hvad der skal ændres og hvorfor, i stedet for samlet fritekst.\nSørg for at tekst, interval og arbejdsindhold peger på samme operationelle udførelse.\nAfslut med at kontrollere om ændringen påvirker eksisterende kald og opfølgningsordre.",
        roles: ["Maintenance Preparation Engineer", "Maintenance Scheduler"],
        transactions: ["IP42", "IP43"],
      },
      {
        id: "faq-012",
        category: "Kald og item",
        question: "Hvordan indberetter jeg fejl i genererede kald?",
        answer:
          "Angiv hvilket kald der er forkert, hvad du forventede, og hvilken plan/item der ligger bag.\nVedhæft gerne kort eksempel med datoer, så afvigelsen er hurtig at reproducere.\nHvis fejl kun ses i bestemte anlæg, så nævn præcist hvilke anlæg der er påvirket.",
        roles: ["Maintenance Scheduler", "Maintenance Planner"],
        transactions: ["IP10", "IP24"],
      },
      {
        id: "faq-013",
        category: "Kald og item",
        question: "Hvordan skriver jeg brugbare item-tekster til udførende hold?",
        answer:
          "Start med handlingen i imperativ form, fx 'Kontrollér', 'Udskift' eller 'Rens'.\nBeskriv derefter acceptance-kriterie, så udførende ved hvornår opgaven er færdig.\nUndgå uklare formuleringer som kræver lokal tolkning fra skift til skift.",
        roles: ["Maintenance Preparation Engineer", "Maintenance Technician"],
      },
      {
        id: "faq-014",
        category: "Kald og item",
        question: "Hvordan dokumenterer jeg ændring i item-prioritet?",
        answer:
          "Angiv gammel prioritet, ny prioritet og tydelig risikobegrundelse for ændringen.\nForklar hvilken effekt ændringen får på planlægning og udførelsesrækkefølge.\nSørg for at ændringen er fagligt godkendt før implementering i produktionsnær plan.",
        roles: ["Maintenance Supervisor", "Senior Operations Engineer"],
      },
      {
        id: "faq-015",
        category: "Kald og item",
        question: "Hvordan sikrer jeg at planændringer slår igennem på fremtidige kald?",
        answer:
          "Efter ændring skal du kontrollere kommende kald og sammenligne med den nye planopsætning.\nHvis gamle kald ligger forkert, skal der besluttes om de skal korrigeres manuelt.\nNotér resultatet i tråden, så alle ved om ændringen er verificeret end-to-end.",
        roles: ["Maintenance Scheduler", "Maintenance Engineer"],
        transactions: ["IP10", "IP24", "IW38"],
      },
      {
        id: "faq-016",
        category: "Ordre",
        question: "Hvordan opretter jeg en ordre til vedligeholdelsesopgave?",
        answer:
          "Vælg korrekt ordretype og tilknyt det rigtige objekt fra start.\nSkriv en operationel beskrivelse, så planlægning, udførelse og afslutning er entydig.\nKontrollér basisdata før frigivelse, så ordren kan bruges uden efterfølgende nødrettelser.",
        roles: ["Maintenance Planner", "Maintenance Supervisor"],
        transactions: ["IW31"],
      },
      {
        id: "faq-017",
        category: "Ordre",
        question: "Hvordan retter jeg en eksisterende ordre korrekt?",
        answer:
          "Ret kun de nødvendige felter og dokumentér årsagen direkte i indberetningen.\nHvis ordren allerede er i udførelse, afklar ændringen med udførende ansvarlig først.\nKontrollér at statusforløb stadig understøtter korrekt afslutning og rapportering.",
        roles: ["Maintenance Scheduler", "Maintenance Supervisor"],
        transactions: ["IW32", "IW33"],
      },
      {
        id: "faq-018",
        category: "Ordre",
        question: "Hvordan finder jeg åbne ordrer til opfølgning?",
        answer:
          "Brug ordreliste med faste filtre for anlæg, status og periode.\nGem en variant, så teamet bruger samme udsnit og samme prioriteringslogik.\nAfstem ugentligt listen med ansvarlige for at undgå gamle hængeordrer.",
        roles: ["Maintenance Planner", "Maintenance Scheduler"],
        transactions: ["IW38"],
      },
      {
        id: "faq-019",
        category: "Ordre",
        question: "Hvordan ser jeg historik på en ordre før en rettelse?",
        answer:
          "Kontrollér statusforløb, operationer og tidligere ændringer før du skriver indberetning.\nIdentificér om problemet skyldes stamdata, planlogik eller ren udførelsesafvigelse.\nBeskriv denne konklusion kort i sagen, så næste led kan handle hurtigere.",
        roles: ["Senior Maintenance Engineer", "Maintenance Planner"],
        transactions: ["IW33"],
      },
      {
        id: "faq-020",
        category: "Ordre",
        question: "Hvad gør jeg når tidsregistrering ikke kan bogføres som forventet?",
        answer:
          "Angiv operation, medarbejderrolle og præcis fejlmeddelelse fra systemet.\nNotér om fejlen gælder én ordre eller et generelt mønster på flere ordrer.\nVed generelt mønster bør rettigheder og work center-opsætning kontrolleres først.",
        roles: ["Maintenance Scheduler", "Senior System Manager"],
        transactions: ["IW41", "IW42", "IW32"],
      },
      {
        id: "faq-021",
        category: "FL og KKS",
        question: "Hvordan opretter jeg en ny Functional Location?",
        answer:
          "Sikre først at navngivning følger gældende KKS- og strukturprincipper.\nUdfyld beskrivelse, organisatorisk placering og relevante klassedata med det samme.\nBekræft til sidst at FL kan anvendes i de processer den er oprettet til.",
        roles: ["Maintenance Preparation Engineer", "Senior Master Data Specialist"],
        transactions: ["IL01", "IL03"],
      },
      {
        id: "faq-022",
        category: "FL og KKS",
        question: "Hvordan retter jeg data på en eksisterende FL?",
        answer:
          "Beskriv præcist hvilke felter der er forkerte, og hvilke værdier der ønskes.\nVed strukturændringer skal konsekvens for udstyr, planer og rapportering beskrives.\nUndgå blandede ændringer i samme sag hvis de kræver forskellige godkendelser.",
        roles: ["Senior Master Data Specialist", "Maintenance Planner"],
        transactions: ["IL02", "IL03"],
      },
      {
        id: "faq-023",
        category: "FL og KKS",
        question: "Hvordan opretter eller retter jeg udstyr med korrekt FL-relation?",
        answer:
          "Kontrollér først at mål-FL er korrekt og aktiv før udstyr oprettes eller flyttes.\nOpdatér udstyrsstamdata konsekvent, især relationer der bruges i planlægning.\nValider efterfølgende i visning at udstyr og FL hænger sammen som forventet.",
        roles: ["Maintenance Preparation Engineer", "Maintenance Technician"],
        transactions: ["IE01", "IE02", "IE03"],
      },
      {
        id: "faq-024",
        category: "FL og KKS",
        question: "Hvad skal jeg inkludere ved KKS-relaterede rettelser?",
        answer:
          "Medsend nuværende notation, ønsket notation og teknisk begrundelse for skiftet.\nBeskriv også hvilken klasse/funktion der understøttes af ændringen.\nHvis notation påvirker dokumentation, skal berørte dokumenter nævnes eksplicit.",
        roles: ["Senior Technical Documentation Coordinator", "Senior Process Specialist"],
      },
      {
        id: "faq-025",
        category: "FL og KKS",
        question: "Hvordan undgår jeg klassifikationsfejl i FL-indberetning?",
        answer:
          "Indsend FL, beskrivelse, str-indikator og forventet klasse i samme indberetning.\nHvis én af disse mangler, opstår der ofte ekstra afklaring og forsinkelse.\nBrug samme terminologi som i eksisterende klassefaner for at sikre konsistent udfald.",
        roles: ["Senior Master Data Specialist", "Maintenance Preparation Engineer"],
      },
      {
        id: "faq-026",
        category: "Materialer",
        question: "Hvordan tjekker jeg om et materiale allerede findes?",
        answer:
          "Søg først eksisterende materiale og verificér data i visning før ny oprettelse.\nVurdér om eksisterende materiale kan bruges med korrekt enhed og specifikation.\nDokumentér i indberetningen hvad der allerede er tjekket for at undgå dobbeltarbejde.",
        roles: ["Senior Master Data Specialist", "Maintenance Planner"],
        transactions: ["MM03"],
      },
      {
        id: "faq-027",
        category: "Materialer",
        question: "Hvordan indberetter jeg manglende materialer til planlagt aktivitet?",
        answer:
          "Angiv hvilken aktivitet der blokeres, og hvornår materialet senest skal være tilgængeligt.\nBeskriv teknisk specifikation, så anskaffelse ikke bliver forkert første gang.\nVed kritisk driftspåvirkning bør du markere hast og foreslå midlertidig løsning.",
        roles: ["Maintenance Planner", "Maintenance Supervisor"],
      },
      {
        id: "faq-028",
        category: "Materialer",
        question: "Hvordan kontrollerer jeg materialekobling i BOM før indberetning?",
        answer:
          "Gennemgå eksisterende BOM-linjer og identificér præcis hvilken position der er forkert.\nAngiv både nuværende og ønsket struktur i samme sag, så ændringen er reproducerbar.\nVed flere objekter bør du vedhæfte en kort matrix med objekt og ønsket BOM-ændring.",
        roles: ["Maintenance Preparation Engineer", "Maintenance Planner"],
        transactions: ["CS03"],
      },
      {
        id: "faq-029",
        category: "Adgang og roller",
        question: "Hvilke oplysninger skal med, når jeg beder om SAP-adgang eller roller?",
        answer:
          "Beskriv arbejdsopgaven, hvilke handlinger brugeren skal kunne udføre og hvilket scope der gælder.\nSkeln mellem visning, ændring og godkendelse, så rollen kan gives med mindst nødvendige rettigheder.\nVed ny medarbejder bør du også angive startdato og nærmeste leder for hurtig behandling.",
        roles: ["Senior System Manager", "Maintenance Supervisor", "Support"],
      },
      {
        id: "faq-030",
        category: "Kvalitet i indberetning",
        question: "Hvordan laver jeg en strømlinet indberetning, der kan løses i første omgang?",
        answer:
          "Brug denne struktur: problem, objekt, ønsket ændring, gyldighedsdato og konsekvens ved ikke at ændre.\nTilføj rolleinformation om hvem der bestiller, hvem der udfører, og hvem der godkender.\nVed SAP-rettelser: skriv hvilke transaktioner du allerede har brugt til at validere nuværende data.",
        roles: ["Maintenance Scheduler", "Maintenance Planner", "Maintenance Supervisor"],
      },
    ],
  };
})();
