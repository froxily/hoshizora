package dev.hoshizora.api.stats;

import dev.hoshizora.api.i18n.Term;
import dev.hoshizora.api.launches.LaunchSummary;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.Instant;
import java.util.List;
import org.jspecify.annotations.Nullable;

@Schema(description = "Identified first stages ranked by flights, most flown first.")
public record LaunchBoosters(
        @Schema(description = "Source slug, as in /api/v1/meta/sources.")
        String source,

        List<Item> items) {

    @Schema(name = "LaunchBooster")
    public record Item(
            @Schema(description = "Launch Library 2 launcher id.")
            int id,

            @Schema(description = "The serial painted on the stage.", example = "B1067")
            String serialNumber,

            @Schema(description = "active, retired, expended, lost, destroyed, scrapped or converted.") @Nullable
            Term status,

            LaunchSummary.@Nullable Vehicle vehicle,

            @Schema(description = "Rank by flights; stages with the same number of flights share a rank.")
            long rank,

            long flights,
            @Nullable Long landingAttempts,
            @Nullable Long landings,
            @Nullable Instant firstFlightAt,
            @Nullable Instant lastFlightAt,

            @Schema(description = "The shortest time between two flights of this stage, in days.") @Nullable
            Double fastestTurnaroundDays) {}
}
