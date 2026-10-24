package dev.hoshizora.api.meta;

import dev.hoshizora.api.i18n.Bilingual;
import java.time.Instant;
import org.jspecify.annotations.Nullable;

record SourceRow(
        String slug,
        Bilingual name,
        Bilingual description,
        Bilingual credit,
        Bilingual license,
        @Nullable String licenseUrl,
        String homepageUrl,
        Bilingual cadence,
        @Nullable Long updateIntervalSeconds,
        @Nullable String lastRunStatus,
        @Nullable Instant lastRunStartedAt,
        @Nullable Instant lastRunFinishedAt,
        @Nullable Instant lastSucceededAt,
        @Nullable Instant lastFetchedAt,
        long blocking,
        long warnings) {}
