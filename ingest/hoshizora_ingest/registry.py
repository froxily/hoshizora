from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from hoshizora_ingest.config import Settings
from hoshizora_ingest.sources.base import Source, SourceInfo
from hoshizora_ingest.sources.celestrak.adapter import INFO as CELESTRAK
from hoshizora_ingest.sources.celestrak.adapter import CelestrakSource
from hoshizora_ingest.sources.exoplanets.adapter import INFO as EXOPLANET_ARCHIVE
from hoshizora_ingest.sources.exoplanets.adapter import ExoplanetArchiveSource
from hoshizora_ingest.sources.jpl.adapter import INFO as JPL
from hoshizora_ingest.sources.jpl.adapter import JplSource
from hoshizora_ingest.sources.launch_library.adapter import INFO as LAUNCH_LIBRARY
from hoshizora_ingest.sources.launch_library.adapter import (
    PRODUCTION_BASE_URL,
    LaunchLibrarySource,
)
from hoshizora_ingest.sources.reference.adapter import INFO as REFERENCE
from hoshizora_ingest.sources.reference.adapter import ReferenceSource
from hoshizora_ingest.sources.swpc.adapter import INFO as SWPC
from hoshizora_ingest.sources.swpc.adapter import SwpcSource


@dataclass(frozen=True)
class SourceEntry:
    info: SourceInfo
    build: Callable[[Settings], Source[Any, Any]]


type Registry = Mapping[str, SourceEntry]


def registry_of(*entries: SourceEntry) -> Registry:
    return MappingProxyType({entry.info.slug: entry for entry in entries})


SOURCES: Registry = registry_of(
    SourceEntry(REFERENCE, lambda _settings: ReferenceSource()),
    SourceEntry(LAUNCH_LIBRARY, lambda settings: LaunchLibrarySource(settings.ll2_base_url)),
    SourceEntry(CELESTRAK, lambda _settings: CelestrakSource()),
    SourceEntry(JPL, lambda _settings: JplSource()),
    SourceEntry(SWPC, lambda _settings: SwpcSource()),
    SourceEntry(EXOPLANET_ARCHIVE, lambda _settings: ExoplanetArchiveSource()),
)

LAUNCH_LIBRARY_PRODUCTION = SourceEntry(
    LAUNCH_LIBRARY, lambda _settings: LaunchLibrarySource(PRODUCTION_BASE_URL)
)
