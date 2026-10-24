package dev.hoshizora.api.stats;

import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDate;
import java.util.List;
import org.jspecify.annotations.Nullable;

@Schema(description = "Close approaches within 0.05 au of Earth per TDB calendar month, past and predicted.")
public record CloseApproachMonthly(String source, LocalDate from, LocalDate to, List<Month> items) {

    @Schema(name = "CloseApproachMonth")
    public record Month(
            @Schema(description = "First day of the month.") LocalDate month,
            long approaches,

            @Schema(description = "Approaches closer than the Moon (1 LD = 384,400 km).")
            long withinLunarDistance,

            double closestDistLd,
            String closestDesignation,

            @Schema(description = "Lowest absolute magnitude H that month: the likely largest object.") @Nullable
            Double minAbsoluteMagnitude,

            @Nullable String largestDesignation,

            @Schema(description = "True when the whole month lies in the future, so every approach is predicted.")
            boolean predicted,

            String recordsUrl) {}
}
