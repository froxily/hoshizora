package dev.hoshizora.api.spaceweather;

import io.swagger.v3.oas.annotations.media.ArraySchema;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.Instant;
import java.util.List;
import org.jspecify.annotations.Nullable;

@Schema(
        description = "NOAA SWPC's OVATION aurora forecast: the latest probability of visible aurora on a 1° grid,"
                + " and one summary per forecast for the past 48 hours.")
public record Aurora(
        @Schema(description = "The latest forecast; absent until one has been ingested.") @Nullable
        Forecast latest,

        @Schema(description = "One summary per stored forecast in the 48 hours up to the latest, oldest first.")
        List<Summary> history) {

    @Schema(name = "AuroraForecast")
    public record Forecast(
            @Schema(description = "When the model ran on the latest solar wind.")
            Instant observedAt,

            @Schema(description = "The time the forecast is for, usually 30 to 90 minutes later.")
            Instant forecastAt,

            Hemisphere north,
            Hemisphere south,

            @ArraySchema(
                    arraySchema =
                            @Schema(
                                    description = "Cells at or above min_percent as [longitude 0–359 °E, latitude,"
                                            + " probability %]. Cells below it are omitted."),
                    schema = @Schema(implementation = Integer[].class))
            List<List<Integer>> cells) {}

    @Schema(name = "AuroraHemisphere")
    public record Hemisphere(
            @Schema(description = "Highest probability of visible aurora anywhere in the hemisphere, in percent.")
            int maxPercent,

            @Schema(description = "Latitude closest to the equator where the probability reaches 10 %.") @Nullable
            Integer boundaryLat) {}

    @Schema(name = "AuroraSummary")
    public record Summary(Instant observedAt, int northMaxPercent, int southMaxPercent) {}
}
