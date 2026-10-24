package dev.hoshizora.api.stats;

import dev.hoshizora.api.launches.LaunchSummary;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.Instant;
import java.util.List;
import org.jspecify.annotations.Nullable;

@Schema(description = "The busiest launch pads by launch attempts.")
public record LaunchPads(String source, List<Item> items) {

    @Schema(name = "LaunchPadActivity")
    public record Item(
            LaunchSummary.Pad pad,
            long attempts,
            long successes,

            @Schema(description = "Failures and partial failures.")
            long failures,

            long scheduled,
            @Nullable Instant firstLaunchAt,
            @Nullable Instant lastLaunchAt,
            @Nullable Integer busiestYear,
            @Nullable Long busiestYearAttempts,
            String recordsUrl) {}
}
