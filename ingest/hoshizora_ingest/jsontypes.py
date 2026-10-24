import hashlib
import json
from typing import cast

type JsonValue = bool | int | float | str | list[JsonValue] | dict[str, JsonValue] | None


def parse_json(content: bytes) -> JsonValue:
    return cast("JsonValue", json.loads(content))


def canonical_json(value: JsonValue) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def content_hash(value: JsonValue) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()
