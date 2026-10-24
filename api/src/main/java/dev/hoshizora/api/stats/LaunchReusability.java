package dev.hoshizora.api.stats;

import io.swagger.v3.oas.annotations.media.Schema;
import java.util.List;
import org.jspecify.annotations.Nullable;

@Schema(
        description = "First-stage reuse and landings per UTC year for each group, most stage flights first. Only"
                + " launches with a recorded first stage that have flown count.")
public record LaunchReusability(
        @Schema(description = "Source slug, as in /api/v1/meta/sources.")
        String source,

        LaunchGrouping groupBy,
        List<Series> groups) {

    @Schema(name = "LaunchReusabilitySeries", description = "One group's stage reuse and landings by year.")
    public record Series(
            LaunchGroup group,

            @Schema(description = "Stage flights across the years returned.")
            long totalStageFlights,

            @Schema(description = "The launches behind these numbers.")
            String recordsUrl,

            List<Year> years) {}

    @Schema(name = "LaunchReusabilityYear")
    public record Year(
            int year,

            @Schema(description = "Launches with at least one recorded first stage.")
            long launches,

            @Schema(description = "Of those, launches flying at least one stage that had flown before.")
            long launchesReflown,

            @Schema(description = "launches_reflown / launches.") @Nullable
            Double reflownShare,

            @Schema(description = "First stages flown, counting each Falcon Heavy side booster.")
            long stageFlights,

            @Schema(description = "Stage flights on a stage that had flown before.")
            long stageReflights,

            @Schema(description = "Landing attempts with a known outcome.")
            long landingAttempts,

            @Schema(description = "Successful landings.") long landings,

            @Schema(description = "landings / landing_attempts.") @Nullable
            Double landingSuccessRate,

            String recordsUrl) {}
}
