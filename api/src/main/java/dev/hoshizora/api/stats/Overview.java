package dev.hoshizora.api.stats;

import dev.hoshizora.api.launches.LaunchSummary;
import dev.hoshizora.api.neo.CloseApproach;
import dev.hoshizora.api.spaceweather.Kp;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.Instant;
import java.util.List;
import org.jspecify.annotations.Nullable;

@Schema(
        description = "The home ticker: the next launch, this year's launches, current Kp, this week's closest"
                + " approach and objects in Earth orbit.")
public record Overview(
        @Schema(description = "Start of the current UTC hour; everything is computed as of this instant.")
        Instant asOf,

        @Nullable LaunchSummary nextLaunch,
        LaunchYear launchesThisYear,
        Kp.@Nullable Reading kp,

        @Schema(description = "The closest approach in the seven days from as_of.") @Nullable
        CloseApproach closestApproachThisWeek,

        OrbitCount objectsInEarthOrbit,

        @Schema(description = "Source slugs behind these numbers.")
        List<String> sources) {

    @Schema(
            name = "OverviewLaunchYear",
            description = "Launch attempts so far this UTC year against the same span of last year.")
    public record LaunchYear(int year, long attempts, long samePeriodLastYear, String recordsUrl) {}

    @Schema(name = "OverviewOrbitCount")
    public record OrbitCount(long total, long payloads, String recordsUrl) {}
}
