package dev.hoshizora.api.agencies;

import io.swagger.v3.oas.annotations.media.Schema;
import java.time.Instant;
import org.jspecify.annotations.Nullable;

@Schema(description = "Launches an organization provided as launch service provider.")
public record LaunchStats(
        @Schema(description = "Launches that left the pad, including those still in flight.")
        long attempts,

        long successes,
        long failures,
        long partialFailures,

        @Schema(description = "Launches announced but not yet flown.")
        long scheduled,

        @Schema(description = "Successes over completed attempts, from 0 to 1. Partial failures count as failures.")
        @Nullable
        Double successRate,

        @Nullable Instant firstLaunchAt,
        @Nullable Instant lastLaunchAt) {

    static LaunchStats of(AgencyRow.Totals totals) {
        var completed = totals.successes() + totals.failures() + totals.partialFailures();
        return new LaunchStats(
                totals.attempts(),
                totals.successes(),
                totals.failures(),
                totals.partialFailures(),
                totals.scheduled(),
                completed == 0 ? null : (double) totals.successes() / completed,
                totals.firstLaunchAt(),
                totals.lastLaunchAt());
    }
}
