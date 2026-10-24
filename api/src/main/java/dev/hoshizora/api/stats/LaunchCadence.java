package dev.hoshizora.api.stats;

import io.swagger.v3.oas.annotations.media.Schema;
import java.util.List;

@Schema(description = "Launches per UTC year for each group, busiest groups first.")
public record LaunchCadence(
        @Schema(description = "Source slug, as in /api/v1/meta/sources.")
        String source,

        LaunchGrouping groupBy,
        List<Series> groups) {

    @Schema(name = "LaunchCadenceSeries", description = "One group's launches by year.")
    public record Series(
            LaunchGroup group,

            @Schema(description = "Attempts across the years returned.")
            long totalAttempts,

            @Schema(description = "The launches behind these numbers.")
            String recordsUrl,

            List<Year> years) {}

    @Schema(name = "LaunchCadenceYear")
    public record Year(
            int year,

            @Schema(description = "Launches that left the pad, including those in flight.")
            long attempts,

            long successes,
            long failures,
            long partialFailures,

            @Schema(description = "Launches planned for the year and not yet flown.")
            long scheduled,

            String recordsUrl) {}
}
