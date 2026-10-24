package dev.hoshizora.api.spaceweather;

import io.swagger.v3.oas.annotations.media.Schema;
import java.time.Instant;
import org.jspecify.annotations.Nullable;

@Schema(description = "Current space weather: the latest Kp, solar wind and the strongest flare of the past day.")
public record SpaceWeatherNow(
        @Schema(description = "Conditions are taken at or before this hour boundary.")
        Instant asOf,

        Kp.@Nullable Reading kp,
        SolarWind.@Nullable Point solarWind,

        @Schema(description = "The strongest classified flare in the 24 hours before as_of.") @Nullable
        Flare strongestFlareLastDay,

        @Schema(description = "Flares in the 24 hours before as_of.")
        long flaresLastDay) {}
