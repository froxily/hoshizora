from pathlib import Path

from hoshizora_ingest.sources.reference.adapter import load_documents
from hoshizora_ingest.sources.reference.models import (
    OrganizationEntry,
    OwnerEntry,
    ReferenceData,
)

DOCS_PATH = Path(__file__).resolve().parents[3] / "docs" / "sources" / "organizations.md"

INTRO = """\
# Organizations

Generated from `ingest/hoshizora_ingest/reference/*.toml` by `uv run hoshizora docs`.
Do not edit by hand: a test fails when this file and the TOML disagree.

## How the model works

- **Identity.** Every Launch Library 2 agency becomes one `core.organization`, reached through the
  alias `ll2.agency/<id>`. Organizations that only CelesTrak knows (for example ORBCOMM) are
  curated here and reached through `hoshizora/<slug>`.
- **Type.** LL2 agency types map as Government → agency, Commercial and Private → company,
  Multinational → international, Educational → academic. Curation overrides the facts the source
  gets wrong: state-owned corporations such as CASC are companies, armed forces are military.
  Unknown LL2 types leave the type empty and appear in the data-quality report.
- **Names.** `name_en` comes from LL2 unless curated. Every `name_ja` cites its source, the
  organization's Japanese site or Japanese Wikipedia; names without one are reported as missing,
  never machine-transliterated.
- **Programs.** A program groups the agencies, companies and armed forces of one nation, so the UI
  can honestly say "Japan's launches" even when the provider is Mitsubishi Heavy Industries.
- **CelesTrak owner codes** are countries, joint ventures or organizations, not agencies. A `US`
  object can belong to NASA, the military or a company, so owner codes resolve to countries unless
  the code itself names an organization. `CIS` resolves to Russia as the USSR's successor state.
- **Fail loudly.** Every code seen in the data is recorded; codes missing from this vocabulary, and
  vocabulary entries without a mapping, appear in `hoshizora dq` and fail `--strict`.
"""


type Cell = str | list[str] | None


def cell(value: Cell) -> str:
    match value:
        case None:
            return ""
        case str():
            return value.replace("|", "\\|")
        case list():
            return ", ".join(value)


def table(header: tuple[str, ...], rows: list[tuple[Cell, ...]]) -> str:
    lines = [
        "| " + " | ".join(header) + " |",
        "|" + "|".join("---" for _ in header) + "|",
    ]
    lines += ["| " + " | ".join(cell(value) for value in row) + " |" for row in rows]
    return "\n".join(lines)


def organization_key(entry: OrganizationEntry) -> str:
    return f"ll2.agency/{entry.ll2}" if entry.ll2 is not None else f"hoshizora/{entry.slug}"


def name_ja_link(entry: OrganizationEntry) -> str:
    if entry.name_ja is None or entry.name_ja_source is None:
        return ""
    return f"[{entry.name_ja}](<{entry.name_ja_source}>)"


def owner_target(owner: OwnerEntry) -> str:
    if owner.unknown:
        return "unknown"
    targets = [*owner.countries]
    if owner.organization is not None:
        targets.append(f"organization `{owner.organization}`")
    return ", ".join(targets)


def programs_section(data: ReferenceData) -> str:
    organizations = data.organizations.organization
    rows: list[tuple[Cell, ...]] = [
        (
            program.slug,
            program.name_en,
            program.name_ja,
            [organization_key(entry) for entry in organizations if program.slug in entry.programs],
        )
        for program in data.organizations.program
    ]
    return "## Programs\n\n" + table(("Slug", "English", "日本語", "Members"), rows)


def organizations_section(data: ReferenceData) -> str:
    rows: list[tuple[Cell, ...]] = [
        (
            organization_key(entry),
            entry.slug,
            entry.name_en,
            name_ja_link(entry),
            entry.type,
            list(entry.countries),
        )
        for entry in data.organizations.organization
    ]
    header = ("Key", "Slug", "English override", "日本語 (source)", "Type override", "Countries")
    return "## Curated organizations\n\n" + table(header, rows)


def owners_section(data: ReferenceData) -> str:
    meta = data.celestrak_owners.meta
    rows: list[tuple[Cell, ...]] = [
        (code, owner.label, owner_target(owner), owner.note)
        for code, owner in sorted(data.celestrak_owners.owners.items())
    ]
    source = f"Source: <{meta['url']}>, retrieved {meta['retrieved']}."
    table_text = table(("Code", "CelesTrak label", "Maps to", "Note"), rows)
    return f"## CelesTrak owner codes\n\n{source}\n\n{table_text}"


def codes_section(data: ReferenceData) -> str:
    rows: list[tuple[Cell, ...]] = [
        (code.namespace, code.code, code.label, code.kind) for code in data.organizations.code
    ]
    return "## Other codes\n\n" + table(("Namespace", "Code", "Label", "Kind"), rows)


def countries_section(data: ReferenceData) -> str:
    meta = data.countries.meta
    count = len(data.countries.countries)
    return (
        f"## Countries\n\n{count} countries and territories with English and Japanese names "
        f"from {meta['source']} {meta['version']} (<{meta['url']}>)."
    )


def render_organizations(data: ReferenceData) -> str:
    sections = [
        INTRO.rstrip("\n"),
        programs_section(data),
        organizations_section(data),
        owners_section(data),
        codes_section(data),
        countries_section(data),
    ]
    return "\n\n".join(sections) + "\n"


def current_document() -> str:
    return render_organizations(ReferenceData.model_validate(load_documents()))


def write_document(path: Path = DOCS_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(current_document(), encoding="utf-8", newline="\n")
    return path
