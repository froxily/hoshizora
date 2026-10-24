package dev.hoshizora.api.spaceweather;

import dev.hoshizora.api.i18n.Term;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.Instant;
import java.util.List;

@Schema(description = "The planetary Kp index per 3-hour interval.")
public record Kp(Instant from, Instant to, List<Reading> items) {

    @Schema(name = "KpReading", description = "Kp for the 3-hour interval starting at observed_at.")
    public record Reading(
            Instant observedAt,

            @Schema(description = "Planetary Kp from 0 to 9 in thirds, e.g. 4.67 for 5-.")
            double kp,

            @Schema(description = "NOAA geomagnetic storm level, g0 to g5.")
            Term gScale) {}
}
