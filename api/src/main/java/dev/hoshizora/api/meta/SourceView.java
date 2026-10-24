package dev.hoshizora.api.meta;

import dev.hoshizora.api.i18n.Term;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.Instant;
import org.jspecify.annotations.Nullable;

@Schema(description = "A data source with its credit, license, update cadence, freshness and data-quality status.")
public record SourceView(
        @Schema(description = "Stable source identifier.", example = "swpc")
        String slug,

        String name,
        @Schema(description = "What the source provides.") String description,

        @Schema(description = "Credit text to show wherever this source's data appears.")
        String credit,

        @Schema(description = "The source's license or usage terms, summarized.")
        String license,

        @Nullable String licenseUrl,
        String homepageUrl,

        @Schema(description = "How often Hoshizora refreshes the source.")
        String cadence,

        @Schema(description = "Planned refresh interval; null when the source changes only on demand.") @Nullable
        Long updateIntervalSeconds,

        Status status,
        Quality quality) {

    @Schema(name = "SourceStatus", description = "The latest ingestion run and fetch for this source.")
    public record Status(
            @Schema(description = "Status of the most recent ingestion run.") @Nullable
            Term lastRun,

            @Nullable Instant lastRunStartedAt,
            @Nullable Instant lastRunFinishedAt,
            @Nullable Instant lastSucceededAt,

            @Schema(description = "The most recent request to the source, including 304 Not Modified.") @Nullable
            Instant lastFetchedAt,

            @Schema(description = "fresh, stale (no fetch within twice the interval), unknown or on_demand.")
            Term freshness) {}

    @Schema(name = "SourceQuality", description = "Open data-quality problems attributed to this source.")
    public record Quality(
            @Schema(description = "Problems that fail the strict data-quality check.")
            long blocking,

            @Schema(description = "Gaps such as names without a Japanese translation.")
            long warnings,

            @Schema(description = "ok, warning or blocking.")
            Term level) {}
}
