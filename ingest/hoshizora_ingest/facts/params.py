from collections.abc import Mapping
from datetime import UTC, date, datetime
from decimal import Decimal

from hoshizora_ingest.facts.humanize import humanize
from hoshizora_ingest.facts.spec import Param, TemplateError
from hoshizora_ingest.jsontypes import JsonValue

type Row = Mapping[str, object]


def column(row: Row, name: str) -> object:
    if name not in row:
        message = f"query returns no column {name}"
        raise TemplateError(message)
    value = row[name]
    if value is None:
        message = f"column {name} is null"
        raise TemplateError(message)
    return value


def number(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float | Decimal):
        message = f"{value!r} is not a number"
        raise TemplateError(message)
    return float(value)


def moment(value: object) -> datetime:
    if isinstance(value, datetime):
        return value.astimezone(UTC)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=UTC)
    message = f"{value!r} is not a date"
    raise TemplateError(message)


def rounded(value: float, param: Param) -> float | int:
    if param.significant is not None:
        return float(f"{value:.{param.significant}g}")
    decimals = param.decimals or 0
    if param.type == "percent":
        return round(value, decimals + 2)
    return round(value) if decimals == 0 else round(value, decimals)


def localized(row: Row, source: str) -> dict[str, JsonValue]:
    english = str(column(row, f"{source}_en"))
    japanese = row.get(f"{source}_ja")
    return {"en": english, "ja": str(japanese)} if japanese else {"en": english}


def param_value(param: Param, row: Row) -> JsonValue:
    if param.type == "name":
        return localized(row, param.source)
    value = column(row, param.source)
    match param.type:
        case "text":
            return str(value)
        case "year":
            return str(int(number(value)))
        case "date":
            return moment(value).date().isoformat()
        case "integer":
            amount = number(value)
            return round(humanize(param.humanize, amount) if param.humanize else amount)
        case "number" | "percent":
            amount = number(value)
            return rounded(humanize(param.humanize, amount) if param.humanize else amount, param)
