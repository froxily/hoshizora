import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import httpx

from hoshizora_ingest.config import DEFAULT_CONTACT, VERSION

CLDR_REF = "48.2.3"
CLDR_BASE = "https://raw.githubusercontent.com/unicode-org/cldr-json/{ref}/cldr-json"
OUTPUT = Path(__file__).with_name("countries.toml")
ISO_ALPHA2_LENGTH = 2
PSEUDO_REGIONS = frozenset({"EU", "QO"})

type Names = dict[str, str]


@dataclass(frozen=True)
class CountryName:
    code: str
    alpha3: str
    en: str
    ja: str


def is_country(code: str, alpha3: str | None) -> bool:
    return (
        len(code) == ISO_ALPHA2_LENGTH
        and code.isalpha()
        and code.isupper()
        and alpha3 is not None
        and code not in PSEUDO_REGIONS
    )


def countries(en: Names, ja: Names, alpha3: Names) -> list[CountryName]:
    return [
        CountryName(code, alpha3[code], en[code], ja[code])
        for code in sorted(en)
        if is_country(code, alpha3.get(code)) and code in ja
    ]


def toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def render(ref: str, rows: list[CountryName]) -> str:
    lines = [
        "[meta]",
        'source = "Unicode CLDR"',
        f"version = {toml_string(ref)}",
        f"url = {toml_string(CLDR_BASE.format(ref=ref))}",
    ]
    for row in rows:
        lines += [
            "",
            f"[countries.{row.code}]",
            f"alpha3 = {toml_string(row.alpha3)}",
            f"en = {toml_string(row.en)}",
            f"ja = {toml_string(row.ja)}",
        ]
    return "\n".join(lines) + "\n"


def territories(client: httpx.Client, ref: str, locale: str) -> Names:
    path = f"cldr-localenames-full/main/{locale}/territories.json"
    document = client.get(f"{CLDR_BASE.format(ref=ref)}/{path}").raise_for_status().json()
    return cast("Names", document["main"][locale]["localeDisplayNames"]["territories"])


def alpha3_codes(client: httpx.Client, ref: str) -> Names:
    path = "cldr-core/supplemental/codeMappings.json"
    document = client.get(f"{CLDR_BASE.format(ref=ref)}/{path}").raise_for_status().json()
    mappings = cast("dict[str, dict[str, str]]", document["supplemental"]["codeMappings"])
    return {code: mapping["_alpha3"] for code, mapping in mappings.items() if "_alpha3" in mapping}


def build(ref: str = CLDR_REF) -> str:
    headers = {"User-Agent": f"Hoshizora/{VERSION} ({DEFAULT_CONTACT})"}
    with httpx.Client(headers=headers, timeout=60) as client:
        rows = countries(
            territories(client, ref, "en"),
            territories(client, ref, "ja"),
            alpha3_codes(client, ref),
        )
    return render(ref, rows)


if __name__ == "__main__":
    OUTPUT.write_text(build(*sys.argv[1:]), encoding="utf-8", newline="\n")
