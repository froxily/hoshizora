package dev.hoshizora.api.neo;

import dev.hoshizora.api.i18n.Term;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.Instant;
import java.time.LocalDate;
import org.jspecify.annotations.Nullable;

@Schema(description = "An object on JPL's Sentry impact-monitoring list, with its cumulative impact risk.")
public record ImpactRisk(
        @Schema(example = "29075") String designation,
        @Nullable String fullname,

        @Schema(description = "Cumulative probability of any listed potential impact, from 0 to 1.") @Nullable
        Double impactProbability,

        @Schema(
                description = "Cumulative Palermo scale: below -2 means no concern; 0 means as risky as the"
                        + " background until the impact date.")
        @Nullable
        Double palermoCumulative,

        @Nullable Double palermoMax,

        @Schema(description = "Highest Torino scale value, 0 to 10.") @Nullable
        Integer torinoMax,

        @Schema(
                description = "Torino category: no_hazard, normal, meriting_attention, threatening or"
                        + " certain_collision.")
        @Nullable
        Term torino,

        @Schema(description = "How many potential impacts Sentry lists.") @Nullable
        Integer potentialImpacts,

        @Nullable Integer impactYearFirst,
        @Nullable Integer impactYearLast,
        @Nullable LocalDate lastObserved,

        @Schema(description = "Sentry's own diameter estimate, weighted by impact probability.") @Nullable
        Double sentryDiameterKm,

        @Nullable Double hMag,

        @Schema(description = "Velocity relative to a massless Earth.") @Nullable
        Double vInfKms,

        CloseApproach.Size size,

        @Schema(description = "When Sentry removed the object from its list; absent while it is monitored.") @Nullable
        Instant removedAt) {}
