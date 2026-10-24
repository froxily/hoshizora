# ADR 0003: Canonical organizations, aliases and national programs

- Status: accepted
- Date: 2026-10-16

## Context

"Who launched this?" and "which country owns this?" have no clean answer in the sources:

- **A launch provider is not a space agency.** Chinese launches are attributed to CASC, a state-owned company, or to commercial firms, rarely to CNSA. Russian launches name Roscosmos, the armed forces or a manufacturer. Japanese launches are often operated by Mitsubishi Heavy Industries rather than JAXA.
- **Launch Library 2 types are coarse.** State corporations and armed forces are both "Government".
- **CelesTrak SATCAT owner codes are countries, joint ventures, international bodies or companies** (`US`, `CIS`, `CHBZ`, `ESA`, `IRID`), not agencies. Its published code list was also incomplete: four codes in the data (JOR, KWT, SVK, UGA) were not on it.
- The UI must say "Japan's launches" honestly and show official Japanese names, never machine transliterations.

## Decision

1. **One canonical `core.organization`, reached through namespaced aliases** (`core.organization_alias`: `ll2.agency/<id>`, `celestrak.owner/<code>`, `hoshizora/<slug>`).
   - LL2 agencies are the identity backbone and create organizations automatically.
   - Organizations known only to CelesTrak are curated.
2. **Source facts and curated facts live in separate columns, and generated columns decide which wins:**
   - `name_en = coalesce(curated_name_en, source_name)`.
   - `type = coalesce(type_override, mapped LL2 type)`.
   - Neither side can overwrite the other.
3. **Curation is data, keyed by external code** (`core.organization_curation`), loaded from version-controlled TOML through the `reference` source. It is applied idempotently after the reference load *and* after every LL2 agency load, so curation and source data can arrive in any order, including on replay. Curated facts are `slug`, `name_ja` plus its citation, `type_override`, countries and program membership.
4. **Every `name_ja` carries a citation** (`name_ja_source`, enforced by a CHECK constraint): Japanese Wikipedia or the organization's Japanese site. An organization without a verified name stays without one and is reported. Country names come from Unicode CLDR.
5. **Programs group organizations by nation** (`core.program`, `core.program_member`). For example, Japan = JAXA, ISAS, NASDA, MHI, IHI, Space One, Interstellar Technologies, and Russia and the Soviet Union = the Soviet program, Roscosmos, the space forces and the manufacturers. A query for a nation's launches joins the provider through programs instead of guessing from agency names.
6. **Owner codes resolve to countries and/or organizations** through `core.country_alias` (joint codes map to several countries; `CIS` maps to Russia as successor state) and `core.organization_alias`. Views `core.space_object_country` and `core.space_object_organization` expose the result.
7. **Fail loudly.**
   - Every code seen in the data is recorded in `core.observed_code`. The `mart.dq_*` views report codes missing from the vocabulary, vocabulary entries without a mapping, untyped organizations and missing `name_ja`.
   - `hoshizora dq --strict` exits non-zero on the blocking ones.
   - `docs/sources/organizations.md` is generated from the TOML and a test keeps it in sync.

## Consequences

- **The model already caught real problems:** the four undocumented CelesTrak owner codes, a CLDR filter that dropped Qatar, and LL2's placeholder "Unknown" agency, which is now an acknowledged unknown type.
- **A launch can be attributed three honest ways:** by provider organization, by mission partners (`core.mission_agency`, e.g. NASA on a SpaceX launch) and by national program.
- **Curation is ongoing work.** About 110 organizations are curated. Missing Japanese names for vehicles and missions are ranked by launch count in the DQ report, so the most visible ones get done first.
- **Parent relationships resolve by unique name**, because LL2 gives the parent's name rather than its id. Ambiguous names are left unlinked.
