from collections.abc import Sequence
from datetime import datetime
from typing import Annotated, ClassVar, cast

from pydantic import BaseModel, BeforeValidator, ConfigDict


def assume_utc(value: object) -> object:
    if isinstance(value, str) and value and not value.endswith(("Z", "+00:00")):
        return f"{value.replace(' ', 'T')}+00:00"
    return value


UtcDatetime = Annotated[datetime, BeforeValidator(assume_utc)]


class SourceModel(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    unused: ClassVar[frozenset[str]] = frozenset()


def _nested(value: object, path: str) -> set[str]:
    if isinstance(value, BaseModel):
        return unexpected_fields(value, f"{path}.")
    if isinstance(value, (list, tuple)):
        found: set[str] = set()
        for item in cast("Sequence[object]", value):
            found |= _nested(item, f"{path}[]")
        return found
    return set()


def unexpected_fields(model: BaseModel, prefix: str = "") -> set[str]:
    declared_unused = getattr(type(model), "unused", frozenset[str]())
    found = {f"{prefix}{name}" for name in (model.model_extra or {}) if name not in declared_unused}
    for name in type(model).model_fields:
        found |= _nested(getattr(model, name), f"{prefix}{name}")
    return found
