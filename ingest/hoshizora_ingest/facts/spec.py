import re
from collections.abc import Iterable
from datetime import timedelta
from pathlib import Path
from typing import Annotated, Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from hoshizora_ingest.facts.humanize import Unit

TEMPLATES_DIR = Path(__file__).resolve().parents[3] / "facts" / "templates"

type Module = Literal[
    "launches", "near-earth", "space-weather", "orbits", "agencies", "sources", "exoplanets"
]
type ParamType = Literal["text", "name", "year", "date", "integer", "number", "percent"]
type Style = Literal["", "number", "number,integer", "number,percent", "number,compact", "date"]

KEY = r"^(launches|near-earth|space-weather|orbits|agencies|sources|exoplanets)\.[a-z][a-z0-9_]*$"
PLACEHOLDER = re.compile(
    r"\{\s*([a-z][a-z0-9_]*)\s*(?:,\s*(number|date)\s*(?:,\s*(integer|percent|compact)\s*)?)?}"
)
FORBIDDEN_SCHEMAS = re.compile(
    r"\b(raw|facts|public|pg_catalog|information_schema)\s*\.", re.IGNORECASE
)
ALLOWED_SCHEMAS = re.compile(r"\b(core|mart)\s*\.", re.IGNORECASE)
STYLES: dict[ParamType, frozenset[str]] = {
    "text": frozenset({""}),
    "name": frozenset({""}),
    "year": frozenset({""}),
    "date": frozenset({"date"}),
    "integer": frozenset({"", "number", "number,integer", "number,compact"}),
    "number": frozenset({"", "number", "number,compact"}),
    "percent": frozenset({"number,percent"}),
}


class TemplateError(ValueError):
    pass


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Param(Strict):
    type: ParamType
    source: Annotated[str, Field(alias="from", pattern=r"^[a-z][a-z0-9_]*$")]
    decimals: Annotated[int | None, Field(ge=0, le=6)] = None
    significant: Annotated[int | None, Field(ge=1, le=6)] = None
    humanize: Unit | None = None

    @model_validator(mode="after")
    def rounding_fits_type(self) -> Self:
        numeric = self.type in {"number", "percent"}
        if (self.decimals is not None or self.significant is not None) and not numeric:
            message = f"{self.type} params take no rounding"
            raise ValueError(message)
        if numeric and (self.decimals is None) == (self.significant is None):
            message = f"{self.type} params need exactly one of decimals or significant"
            raise ValueError(message)
        if self.humanize is not None and self.type not in {"number", "integer"}:
            message = "only number and integer params can be humanized"
            raise ValueError(message)
        return self


class Scoring(Strict):
    base: Annotated[float, Field(ge=0, le=1)] = 0.5
    half_life_days: Annotated[float | None, Field(gt=0)] = None


class Text(Strict):
    en: str
    ja: str


class Example(Strict):
    params: dict[str, object]
    en: str
    ja: str


class Template(Strict):
    key: Annotated[str, Field(pattern=KEY)]
    module: Module
    query: str
    params: dict[str, Param]
    text: Text
    min_score: Annotated[float, Field(ge=0, le=1)]
    valid_for: timedelta
    scoring: Scoring = Scoring()
    requires: tuple[str, ...] = ()
    examples: Annotated[tuple[Example, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if not self.key.startswith(f"{self.module}."):
            message = f"key {self.key} must start with its module {self.module}"
            raise ValueError(message)
        check_query(self.query)
        en, ja = placeholders(self.text.en), placeholders(self.text.ja)
        en_names, ja_names = {name for name, _ in en}, {name for name, _ in ja}
        if en_names != ja_names:
            message = f"en and ja placeholders differ: {sorted(en_names ^ ja_names)}"
            raise ValueError(message)
        if en_names != set(self.params):
            message = f"placeholders {sorted(en_names)} must match params {sorted(self.params)}"
            raise ValueError(message)
        for name, style in en | ja:
            param_type = self.params[name].type
            if style not in STYLES[param_type]:
                message = f"{{{name}}} is a {param_type} param and can't use style '{style}'"
                raise ValueError(message)
        for example in self.examples:
            if set(example.params) != set(self.params):
                message = f"example params must be exactly {sorted(self.params)}"
                raise ValueError(message)
        return self


class TemplateFile(Strict):
    templates: tuple[Template, ...]


def placeholders(text: str) -> set[tuple[str, str]]:
    found = {
        (match[1], ",".join(part for part in (match[2], match[3]) if part))
        for match in PLACEHOLDER.finditer(text)
    }
    if "{" in PLACEHOLDER.sub("", text) or "}" in PLACEHOLDER.sub("", text):
        message = f"text has a brace the renderer can't format: {text}"
        raise ValueError(message)
    return found


def check_query(query: str) -> None:
    statement = query.strip()
    if not re.match(r"^(select|with)\b", statement, re.IGNORECASE) or ";" in statement:
        message = "query must be one SELECT or WITH statement"
        raise ValueError(message)
    if FORBIDDEN_SCHEMAS.search(statement) or not ALLOWED_SCHEMAS.search(statement):
        message = "query must read core and mart only"
        raise ValueError(message)


def parse_templates(name: str, text: str) -> tuple[Template, ...]:
    try:
        return TemplateFile.model_validate({"templates": yaml.safe_load(text)}).templates
    except ValidationError as invalid:
        message = f"{name}: {invalid}"
        raise TemplateError(message) from invalid


def unique(templates: Iterable[Template]) -> tuple[Template, ...]:
    seen: dict[str, Template] = {}
    for template in templates:
        if template.key in seen:
            message = f"duplicate template key {template.key}"
            raise TemplateError(message)
        seen[template.key] = template
    return tuple(seen.values())


def load_templates(directory: Path = TEMPLATES_DIR) -> tuple[Template, ...]:
    files = sorted(directory.glob("*.yaml"))
    return unique(
        template
        for path in files
        for template in parse_templates(path.name, path.read_text(encoding="utf-8"))
    )
