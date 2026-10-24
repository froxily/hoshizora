package dev.hoshizora.api.stats;

import dev.hoshizora.api.i18n.Term;
import io.swagger.v3.oas.annotations.media.Schema;
import java.util.List;

@Schema(description = "Confirmed exoplanets per discovery year, split by discovery method.")
public record ExoplanetDiscoveries(
        @Schema(description = "Source slug, as in /api/v1/meta/sources.")
        String source,

        @Schema(description = "Every method in the years returned, most planets first.")
        List<Method> methods,

        List<Year> years) {

    @Schema(name = "ExoplanetDiscoveryMethod")
    public record Method(Term method, long planets) {}

    @Schema(name = "ExoplanetDiscoveryYear")
    public record Year(
            int year,
            long planets,

            @Schema(description = "Planets found with space telescopes.")
            long fromSpace,

            List<MethodCount> methods,

            @Schema(description = "The planets behind these numbers.")
            String recordsUrl) {}

    @Schema(name = "ExoplanetMethodCount")
    public record MethodCount(
            @Schema(description = "Method code, as in methods[].method.code.")
            String code,

            long planets) {}
}
