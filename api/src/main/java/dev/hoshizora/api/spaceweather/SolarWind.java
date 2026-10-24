package dev.hoshizora.api.spaceweather;

import io.swagger.v3.oas.annotations.media.Schema;
import java.time.Instant;
import java.util.List;
import org.jspecify.annotations.Nullable;

@Schema(description = "Real-time solar wind at the Sun–Earth L1 point, by minute or averaged by hour.")
public record SolarWind(Instant from, Instant to, SolarWindResolution resolution, List<Point> items) {

    @Schema(name = "SolarWindPoint", description = "One minute, or the mean over one UTC hour.")
    public record Point(
            Instant observedAt,
            @Schema(description = "Bulk speed.") @Nullable Double speedKms,

            @Schema(description = "Proton density.") @Nullable
            Double densityCm3,

            @Nullable Double temperatureK,

            @Schema(description = "Total magnetic field strength.") @Nullable
            Double btNt,

            @Schema(description = "North-south field component (GSM); sustained negative values drive storms.")
            @Nullable
            Double bzGsmNt,

            @Schema(description = "Hourly only: the fastest minute.") @Nullable
            Double speedKmsMax,

            @Schema(description = "Hourly only: the most southward minute.") @Nullable
            Double bzGsmNtMin,

            @Schema(description = "Hourly only: minutes averaged.") @Nullable
            Integer samples) {}
}
