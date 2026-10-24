package dev.hoshizora.api.stats;

import io.swagger.v3.oas.annotations.media.Schema;
import java.util.List;
import org.jspecify.annotations.Nullable;

@Schema(description = "Success rates per group over its whole history and its latest 20 completed attempts.")
public record LaunchSuccess(String source, LaunchGrouping groupBy, List<Group> groups) {

    @Schema(name = "LaunchSuccessGroup", description = "One group's record. Partial failures count as failures.")
    public record Group(
            LaunchGroup group,

            @Schema(description = "Completed attempts with a known outcome.")
            long attempts,

            long successes,
            @Nullable Double successRate,

            @Schema(description = "Completed attempts in the latest window of up to 20.")
            int recentAttempts,

            int recentSuccesses,
            @Nullable Double recentSuccessRate,

            @Schema(description = "Consecutive successes since the latest failure.")
            int currentStreak,

            int longestStreak,
            String recordsUrl,

            @Schema(description = "The record as it stood at the end of each year with a completed attempt.")
            List<Year> years) {}

    @Schema(name = "LaunchSuccessYear")
    public record Year(
            int year,
            long attemptsToDate,
            long successesToDate,
            @Nullable Double successRateToDate,

            @Schema(description = "Success rate over the 20 attempts ending with that year's last.") @Nullable
            Double recentSuccessRate) {}
}
