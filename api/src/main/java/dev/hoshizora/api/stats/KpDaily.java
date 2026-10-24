package dev.hoshizora.api.stats;

import dev.hoshizora.api.i18n.Term;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDate;
import java.util.List;

@Schema(description = "Planetary Kp per UTC day.")
public record KpDaily(String source, LocalDate from, LocalDate to, List<Day> items) {

    @Schema(name = "KpDay")
    public record Day(
            LocalDate day,
            double kpMax,
            double kpMean,

            @Schema(description = "3-hour intervals seen that day, at most 8.")
            int intervals,

            @Schema(description = "NOAA storm level of the day's maximum.")
            Term gScale,

            String recordsUrl) {}
}
