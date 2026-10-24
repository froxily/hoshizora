package dev.hoshizora.api.spaceweather;

import dev.hoshizora.api.i18n.Term;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.Instant;
import org.jspecify.annotations.Nullable;

@Schema(description = "A solar X-ray flare seen by a GOES satellite in the 0.1–0.8 nm band.")
public record Flare(
        @Schema(description = "SWPC event id.") String id,
        @Nullable Instant beginAt,
        @Nullable Instant peakAt,
        @Nullable Instant endAt,

        @Schema(description = "GOES class such as M6.4; absent until SWPC classifies the flare.", example = "M6.4")
        @Nullable
        String xrayClass,

        @Schema(description = "A, B, C, M or X: each letter is ten times the one before.") @Nullable
        String classLetter,

        @Schema(description = "Peak X-ray flux in W/m².") @Nullable
        Double peakFluxWm2,

        @Schema(description = "NOAA radio blackout level, r0 to r5.") @Nullable
        Term rScale,

        @Schema(description = "True while the flare has no end time yet.")
        boolean inProgress,

        @Schema(description = "GOES satellite number.") @Nullable
        Integer satellite) {}
