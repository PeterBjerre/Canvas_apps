# App-ikonet i Teams (issue #275)

BIO SAP-ikonet ser rigtigt ud i Power Apps, men får blå fyld, når appen er
lagt i Teams. Her står årsagen, hvad der ligger i repoet, og hvad der skal
gøres i portalen. Ikonet og baggrundsfarven sættes i app-indstillingerne og
ikke i YAML. `python tools\canvas_mcp.py deploy` sender kun YAML, så en
deploy retter det ikke.

## Årsagen

`BIO SAP App/app-icon.png` er ikke et kvadrat. Det er en lyseblå flise
(`#DEF0FC`) med **afrundede hjørner**, en 1 px lys kant og **gennemsigtige
hjørner** udenom.

- **Power Apps** tegner ikonet oven på appens *Background fill*. I DEV er
  den hvid (`rgba(255, 255, 255, 1)` i den seneste eksport), så hjørnerne
  forsvinder mod den hvide side.
- **Teams** tegner farveikonet oven på pakkens `accentColor`, og alt
  gennemsigtigt i ikonet får den farve. Teams afrunder selv hjørnerne, og
  Microsofts krav er, at farveikonet er et kvadrat på 192×192 med symbolet
  på *"a solid or fully transparent square background"* og uden afrundede
  hjørner. Det krav opfylder vores ikon ikke.
- Power Apps' standard-*Background fill* er blå, `RGBA(0,176,240,1)`. Det
  står stadig i de seks andre apps i solutionen, og BIO SAP havde den selv
  indtil eksporten den 13-10-2026. Blev appen lagt i Teams før det, eller
  i et miljø hvor farven stadig er standard, har Teams-pakken en blå
  accentfarve. Den fylder hjørnerne og kanten om flisen.

Teams gemmer pakken og ikonet, da appen blev tilføjet. En ændring i Power
Apps slår derfor ikke igennem, før appen er fjernet og tilføjet igen.

> Vi har ikke kunnet se Teams-pakken, som Power Apps danner, og vi har ikke
> testet i Teams. At Power Apps bruger *Background fill* som `accentColor`,
> er derfor en antagelse. Den passer med Microsofts beskrivelse af
> `accentColor` og med det, Uffe ser.

## Det ligger i repoet

| Fil | Indhold |
| --- | --- |
| `BIO SAP App/app-icon.png` | Uændret. Bruges stadig som logo i sidebaren (`tools/side_nav.py`). |
| `BIO SAP App/teams-icon/color.png` | 192×192, helt uigennemsigtigt kvadrat i `#DEF0FC` med samme symbol og farver. Ingen runde hjørner, ingen kant og ingen gennemsigtighed. |
| `BIO SAP App/teams-icon/outline.png` | 32×32, hvidt symbol på gennemsigtig baggrund (ikonet i Teams' app-bar). |
| `tools/teams_icons.py` | Laver de to filer ud fra `app-icon.png`. Kør `python3 tools/teams_icons.py` igen, hvis ikonet ændres. Kræver Pillow. |

## Det skal gøres i Power Apps (den almindelige vej)

1. Åbn BIO SAP i Power Apps Studio → **Settings** → **General**.
2. **Icon**: upload `BIO SAP App/teams-icon/color.png`.
3. **Background fill**: sæt farven til `#DEF0FC`, altså
   `RGBA(222, 240, 252, 1)`. Den er samme farve som flisen, så hvis Teams
   alligevel viser baggrunden et sted, ser man ingen forskel.
4. **Save** og **Publish**.
5. I Teams: fjern den gamle BIO SAP-app (højreklik på ikonet i app-baren →
   *Uninstall*, eller *Apps* → *Manage your apps*), og frigør den, hvis den
   er fastgjort.
6. I Power Apps: **Apps** → **…** ved BIO SAP → **Add to Teams** → **Add to
   Teams** igen. Er appen lagt ud i organisationen via Teams Admin Center,
   skal pakken i stedet opdateres dér.
7. Tjek ikonet i Teams desktop, i Teams på web og i Teams på mobil, og i
   både lyst og mørkt tema.

Ikonet i Power Apps' app-liste bliver nu et kvadrat i stedet for en
afrundet flise på hvidt. Farverne og symbolet er de samme.

## Alternativ: ret Teams-pakken selv

Bruges, hvis Power Apps stadig laver en blå pakke, eller hvis appen er
lagt ud via Teams Admin Center.

1. Power Apps → **…** ved BIO SAP → **Add to Teams** → **Download app**.
2. Pak zip-filen ud. Den har `manifest.json`, `color.png` og `outline.png`.
3. Erstat de to PNG'er med filerne fra `BIO SAP App/teams-icon/`. Behold
   filnavnene.
4. Sæt `"accentColor": "#DEF0FC"` i `manifest.json`, og hæv `"version"`,
   så Teams ser pakken som ny.
5. Zip de tre filer igen. De skal ligge i roden af zip-filen, ikke i en
   mappe.
6. Upload i Teams (**Apps** → **Manage your apps** → **Upload an app**),
   eller opdatér appen i Teams Admin Center.

## Kilder

- Microsoft Learn: [Teams app icon for Teams Store and app bar](https://learn.microsoft.com/microsoftteams/platform/concepts/design/design-teams-app-icon-store-appbar)
  (192×192, kvadrat, ingen runde hjørner, Teams afrunder selv; outline
  32×32 hvid på gennemsigtig).
- Microsoft Learn: [Teams Store validation guidelines](https://learn.microsoft.com/microsoftteams/platform/concepts/deploy-and-publish/appsource/prepare/teams-store-validation-guidelines#app-package-and-teams-store-listing)
  (symbolet skal stå på en ensfarvet eller helt gennemsigtig kvadratisk
  baggrund).
- Microsoft Learn: [Embed a canvas app as personal app in Teams](https://learn.microsoft.com/power-apps/teams/embed-teams-app#add-to-teams)
  (Add to Teams og Download app).
- Teams-manifestets skema: `accentColor` er farven, Teams bruger sammen
  med farveikonet.
