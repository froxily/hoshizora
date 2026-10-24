package dev.hoshizora.api.stats;

import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDate;
import java.util.List;
import org.jspecify.annotations.Nullable;

@Schema(description = "Classified GOES X-ray flares per UTC month by class letter.")
public record FlaresMonthly(String source, LocalDate from, LocalDate to, List<Month> items) {

    @Schema(name = "FlareMonth")
    public record Month(
            @Schema(description = "First day of the month.") LocalDate month,
            long total,

            @Schema(description = "Flares per class letter; each letter is ten times stronger than the one before.")
            ClassCounts byClass,

            @Nullable Double maxPeakFluxWm2,
            @Schema(example = "M6.4") @Nullable String strongestClass,
            String recordsUrl) {}

    @Schema(name = "FlareClassCounts")
    public record ClassCounts(long a, long b, long c, long m, long x) {}
}
