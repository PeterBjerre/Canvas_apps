# KKS lookup

Opslag i KKS-vejledningen: **funktionsnøgle**, **aggregatnøgle** og
**komponentnøgle**. Vælg et bogstav, en gruppe og en undergruppe — eller
søg i kode og beskrivelse. Et klik på en række går til dens plads i
hierarkiet.

Skærmen er `ScreenKks` i [BIO SAP](../BIO%20SAP%20App/README.md) og har et
punkt i sidebaren. Den er **ikke** en enkeltapp og har aldrig været det:
`KKS App/*.pa.yaml` er mellemprodukter (se `.gitignore`), som BIO SAP bygges
af.

## Fra `powerapp-kks`

Den håndbyggede app `powerapp-kks/` er erstattet af byggerne her. Den lå i
repoet som to `.pa.yaml`-filer på i alt 675 KB:

| | `powerapp-kks` | Nu |
|---|---|---|
| Data | 3.071 rækker som `Table(...)` i `App.Formulas` (440 KB) | SharePoint — se nedenfor |
| Knapgitrene | 25-26 knapper pr. række, hver med sin egen `Index()`-formel | Ét galleri pr. niveau med `WrapCount` og én knap |
| Højder | `conKksHeaderB.Height + …` — kontrol-til-kontrol | Regnet i Python (`check_layout` regel 1) |
| Farver og breakpoints | `RGBA(...)`, `App.Width < 640` | Designtokens og `LayoutRank` — mørk tilstand virker |
| Ramme og navigation | Egen skal, ingen sidebar | `app_frame`, `top_bar` og sidebaren som de andre skærme |
| Tekster | Dansk | Engelsk som resten af BIO SAP. Vejledningens beskrivelser er data og står på dansk |

Navigationen og filtrene er de samme, formel for formel
(`kks_parts.FORMULAS`, `ROW_SELECT`, `UP`). Den eneste forskel i det viste:
aggregat- og komponentnøglerne står sorteret efter bogstav og kode, ikke i
PDF'ens rækkefølge.

## Data: to lister, den ene genbrugt

| Nøgleområde | Liste | Rækker vist |
|---|---|---|
| Funktionsnøgle | **`MD_KksFunctionKey`** (ny) | 2.913 |
| Aggregatnøgle | **`MD_FLKey`**, `KeyType = "Aggregate"`, med `Description` (genbrugt) | 98 af 146 |
| Komponentnøgle | **`MD_FLKey`**, `KeyType = "Component"`, med `Description` (genbrugt) | 60 af 139 |

**`MD_FLKey` genbruges**, fordi den i forvejen har præcis de rækker:
Functional Location-appens nøgleliste (docs/31) indeholder alle 98
aggregat- og 60 komponentnøgler fra vejledningen med ordret samme tekst.
Rækkerne uden tekst er klassebestemmelsens ekstra nøgler; dem viser
skærmen ikke.

**Funktionsnøglerne kan ikke genbruges** fra `MD_FLKey`. Dens 6.441
`Function`-rækker er de gyldige nøgler uden tekst; vejledningen er 2.913
rækker med tekst, dubletter, noter (`*`, `**`), O-grupper, der ikke er
nøgler, og 48 beskrivelser over 255 tegn. Derfor en ny liste.

`tools/gen_kks_seed.py --check` kører ved hver bygning og fejler, hvis
seedet ikke længere er `html/kks.generated.js` — eller hvis `MD_FLKey.csv`
ikke længere er vejledningens aggregat- og komponentrækker. Så var
genbruget forkert, og skærmen skal have sin egen liste til dem.

### Hentningen

Én gang pr. session, første gang skærmen vises (`kks_parts.load_fx`), i én
`Concurrent`:

- `MD_KksFunctionKey` i bidder på 500 efter `SortNo` (indekseret tal), så
  hver forespørgsel kan delegeres og holder sig under datagrænsen. Antallet
  af bidder regnes af seedet, plus én uden øvre grænse.
- `MD_FLKey` to gange: `KeyType = "Aggregate"` og `"Component"`.

Alt andet — bogstaver, grupper, søgning, stien — regnes i hukommelsen af
de navngivne formler. Fejler hentningen, siger skærmen det, og næste besøg
prøver igen.

## Opsætning

```powershell
# MD_FLKey (findes allerede, hvis Functional Location er sat op)
.\sharepoint\provision\Provision-FunctionalLocationLists.ps1 -SiteUrl $site -SeedMasterData
# MD_KksFunctionKey
.\sharepoint\provision\Provision-KksLists.ps1 -SiteUrl $site -SeedMasterData
```

Tilføj derefter `MD_KksFunctionKey` og `MD_FLKey` som datakilder i BIO SAP i
Studio, og deploy som sædvanlig.

Ændres `html/kks.generated.js`:

```bash
python3 tools/gen_kks_seed.py              # -> sharepoint/seed/MD_KksFunctionKey.csv
```

```powershell
.\sharepoint\provision\Provision-KksLists.ps1 -SiteUrl $site -Reseed
```

## Byg

```bash
python3 tools/build_all.py      # BIO SAP, med KKS-skærmen og alle tjek
```

Alene, fra `build/`:

```bash
python3 generate_app_onstart.py && python3 assemble_screen.py && python3 check_layout.py
```

| Fil | Ejer |
|---|---|
| `build/kks_config.py` | Listerne, de tre nøgleområder (knaptekst, undertitel) og bidstørrelsen |
| `build/kks_parts.py` | Skærmens dele, de navngivne formler og hentningen |
| `build/assemble_screen.py` | Samler skærmen → `../ScreenKks.pa.yaml` |
| `build/generate_app_onstart.py` | `App.Formulas` + `App.OnStart` → `../App.pa.yaml` |
| `tools/gen_kks_seed.py` | Seedet og tjekket af genbruget |
| `sharepoint/provision/Provision-KksLists.ps1` | `MD_KksFunctionKey` |

## Testplan (i Studio)

1. Sidebar → KKS lookup: ventespinneren, derefter *All sections* med de 25
   HOME-bogstaver. Monitor: syv kald til `MD_KksFunctionKey` og to til
   `MD_FLKey`, ingen delegeringsadvarsler.
2. Vælg `L` → `LA` → `LAD`: grupperne og undergrupperne følger, stien viser
   `L / LA / LAD - …`, og *Back* går ét niveau op ad gangen.
3. Søg `fødevand`: rækkerne fra alle sektioner; klik på en række, og
   bogstav, gruppe og undergruppe sættes, og søgningen ryddes.
4. *Aggregate key*: 98 rækker under *All*, bogstaverne A B C D G H U, ingen
   undergruppe-række. *Component key*: 60 rækker, `-A` står under `A`.
5. Gå til en anden skærm og tilbage: intet hentes igen, valget står.
6. Mørk tilstand og en smal skærm (mobil): knapgitrene ombryder, tabellens
   beskrivelser ombrydes uden at blive klippet.
