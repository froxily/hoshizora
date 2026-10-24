package dev.hoshizora.api.stats;

import io.swagger.v3.oas.annotations.media.Schema;
import java.util.List;

@Schema(
        description = "Transiting exoplanets counted on a logarithmic grid of orbital period and radius. Transits"
                + " measure a planet's radius directly; other methods mostly estimate it, so they are left out.")
public record ExoplanetSizeOrbit(
        @Schema(description = "Source slug, as in /api/v1/meta/sources.")
        String source,

        @Schema(description = "Width of a period cell in powers of ten.", example = "0.25")
        double periodStepDex,

        @Schema(description = "Height of a radius cell in powers of ten.", example = "0.125")
        double radiusStepDex,

        long planets,
        List<Cell> cells) {

    @Schema(name = "ExoplanetSizeOrbitCell")
    public record Cell(
            @Schema(description = "Shortest orbital period in the cell, days.")
            double periodMinDays,

            @Schema(description = "Longest orbital period in the cell, days (exclusive).")
            double periodMaxDays,

            @Schema(description = "Smallest radius in the cell, Earth radii.")
            double radiusMinEarth,

            @Schema(description = "Largest radius in the cell, Earth radii (exclusive).")
            double radiusMaxEarth,

            long planets) {}
}
