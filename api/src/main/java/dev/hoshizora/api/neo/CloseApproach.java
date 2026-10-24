package dev.hoshizora.api.neo;

import dev.hoshizora.api.i18n.Term;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.Instant;
import java.time.LocalDateTime;
import org.jspecify.annotations.Nullable;

@Schema(description = "A close approach of an asteroid or comet to Earth within 0.05 au, from JPL SBDB.")
public record CloseApproach(
        @Schema(description = "JPL primary designation.", example = "2026 TS")
        String designation,

        @Nullable String fullname,

        @Schema(description = "The body approached. Currently always Earth.")
        Term body,

        @Schema(
                description = "Time of closest approach in TDB (Barycentric Dynamical Time), as JPL gives it. It has"
                        + " no UTC offset because TDB is not a civil time zone.",
                type = "string",
                format = "tdb-date-time",
                pattern = "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}$",
                example = "2026-10-18T06:16:00")
        LocalDateTime approachTdb,

        @Schema(description = "The same instant in UTC, using IERS leap seconds. Absent before 1972.") @Nullable
        Instant approachUtc,

        @Nullable TimeUncertainty timeUncertainty,

        @Schema(description = "Nominal approach distance in astronomical units.")
        double distAu,

        double distKm,

        @Schema(description = "Distance in Earth–Moon distances (1 LD = 384,400 km).")
        double distLd,

        @Schema(description = "Minimum possible distance at 3 sigma.") @Nullable
        Double distMinKm,

        @Schema(description = "Maximum possible distance at 3 sigma.") @Nullable
        Double distMaxKm,

        @Schema(description = "Velocity relative to Earth at closest approach.") @Nullable
        Double vRelKms,

        @Schema(description = "Velocity relative to a massless Earth, as if no gravity bent the path.") @Nullable
        Double vInfKms,

        @Schema(description = "Absolute magnitude H: lower means larger.") @Nullable
        Double hMag,

        Size size,

        @Schema(description = "Whether the object is on the active Sentry impact-monitoring list.")
        boolean sentry) {

    @Schema(description = "3-sigma uncertainty in the approach time.")
    public record TimeUncertainty(
            double minutes,

            @Schema(description = "True when JPL states only an upper bound, e.g. under one minute.")
            boolean lessThan) {}

    @Schema(
            name = "SmallBodySize",
            description = "Measured diameter where known, otherwise a range estimated from H for an assumed"
                    + " geometric albedo between 0.05 (dark) and 0.25 (bright).")
    public record Size(
            @Nullable Double measuredKm,
            @Nullable Double measuredSigmaKm,

            @Schema(description = "Diameter if the surface is bright (albedo 0.25).") @Nullable
            Double estimatedMinKm,

            @Schema(description = "Diameter if the surface is dark (albedo 0.05).") @Nullable
            Double estimatedMaxKm,

            double assumedAlbedoMin,
            double assumedAlbedoMax) {}
}
