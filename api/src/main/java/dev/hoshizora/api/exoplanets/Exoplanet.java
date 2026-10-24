package dev.hoshizora.api.exoplanets;

import dev.hoshizora.api.i18n.Term;
import io.swagger.v3.oas.annotations.media.Schema;
import org.jspecify.annotations.Nullable;

@Schema(
        description = "A confirmed exoplanet with the NASA Exoplanet Archive's best value for each parameter, which"
                + " may come from different publications.")
public record Exoplanet(
        @Schema(description = "Planet name as most commonly used in the literature.", example = "Proxima Cen b")
        String name,

        @Schema(description = "Host star name.", example = "Proxima Cen")
        String hostName,

        Discovery discovery,

        @Schema(description = "Orbital period in days.") @Nullable
        Double orbitalPeriodDays,

        @Schema(description = "Semi-major axis in astronomical units.") @Nullable
        Double semiMajorAxisAu,

        @Schema(description = "Radius in Earth radii. Measured for transiting planets, mostly estimated otherwise.")
        @Nullable
        Double radiusEarth,

        @Schema(description = "Best available mass in Earth masses; M sin i for most radial-velocity planets.")
        @Nullable
        Double massEarth,

        @Nullable Double eccentricity,

        @Schema(description = "Modeled equilibrium temperature in kelvin.") @Nullable
        Double equilibriumTempK,

        @Schema(description = "Starlight received, relative to what Earth gets from the Sun.") @Nullable
        Double insolationEarth,

        Star star,

        @Schema(description = "Distance to the planetary system in parsecs.") @Nullable
        Double distancePc,

        @Schema(description = "Distance in light-years (1 pc = 3.26156 ly).") @Nullable
        Double distanceLy,

        @Schema(description = "The planet's confirmation has been questioned in the literature.")
        boolean controversial) {

    @Schema(name = "ExoplanetDiscovery")
    public record Discovery(
            @Nullable Integer year,

            @Schema(description = "Discovery method, e.g. transit or radial_velocity.")
            Term method,

            @Schema(
                    description =
                            "Facility behind the discovery observations, e.g. Transiting Exoplanet Survey Satellite (TESS).")
            @Nullable
            String facility,

            @Schema(description = "ground, space or multiple locales.") @Nullable
            String locale) {}

    @Schema(name = "ExoplanetStar", description = "The host star and its system.")
    public record Star(
            @Schema(description = "Effective temperature in kelvin.") @Nullable
            Double tempK,

            @Schema(description = "Radius in solar radii.") @Nullable
            Double radiusSun,

            @Schema(description = "Mass in solar masses.") @Nullable
            Double massSun,

            @Schema(description = "Stars in the system.") @Nullable
            Integer starCount,

            @Schema(description = "Confirmed planets in the system.") @Nullable
            Integer planetCount) {}
}
