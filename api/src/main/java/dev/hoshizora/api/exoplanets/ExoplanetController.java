package dev.hoshizora.api.exoplanets;

import dev.hoshizora.api.i18n.Lang;
import dev.hoshizora.api.i18n.Term;
import dev.hoshizora.api.i18n.Vocabulary;
import dev.hoshizora.api.web.NotFoundException;
import dev.hoshizora.api.web.Page;
import dev.hoshizora.api.web.PageQuery;
import dev.hoshizora.api.web.Responses;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.Size;
import java.util.Locale;
import java.util.Objects;
import org.jspecify.annotations.Nullable;
import org.springdoc.core.annotations.ParameterObject;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/exoplanets")
@Tag(name = "Exoplanets", description = "Confirmed exoplanets from the NASA Exoplanet Archive.")
class ExoplanetController {

    static final double LIGHT_YEARS_PER_PARSEC = 3.26156;

    private final ExoplanetRepository repository;
    private final Vocabulary vocabulary;
    private final Responses responses;

    ExoplanetController(ExoplanetRepository repository, Vocabulary vocabulary, Responses responses) {
        this.repository = repository;
        this.vocabulary = vocabulary;
        this.responses = responses;
    }

    @GetMapping
    @Operation(
            operationId = "listExoplanets",
            summary = "List confirmed exoplanets",
            description = "Confirmed exoplanets from the archive's composite table, filtered by discovery method,"
                    + " year and distance. Planets whose confirmation has been questioned are hidden unless asked"
                    + " for.")
    ResponseEntity<Page<Exoplanet>> listExoplanets(
            @Parameter(description = "Discovery method code, e.g. transit, radial_velocity or microlensing.")
                    @RequestParam(name = "method", required = false)
                    @Pattern(regexp = "[a-z_]{1,40}")
                    @Nullable
                    String method,
            @Parameter(description = "First discovery year, inclusive.")
                    @RequestParam(name = "from_year", required = false)
                    @Min(1989)
                    @Max(2100)
                    @Nullable
                    Integer fromYear,
            @Parameter(description = "Last discovery year, inclusive.")
                    @RequestParam(name = "to_year", required = false)
                    @Min(1989)
                    @Max(2100)
                    @Nullable
                    Integer toYear,
            @Parameter(description = "Only systems at most this many light-years away.")
                    @RequestParam(name = "max_distance_ly", required = false)
                    @Positive
                    @Nullable
                    Double maxDistanceLy,
            @Parameter(description = "true to include planets whose confirmation has been questioned.")
                    @RequestParam(name = "include_controversial", defaultValue = "false")
                    boolean includeControversial,
            @Parameter(description = "distance (nearest first), -discovery_year, radius or name.")
                    @RequestParam(name = "sort", defaultValue = "distance")
                    ExoplanetSort sort,
            @ParameterObject @Valid PageQuery paging,
            Locale locale) {
        var lang = Lang.of(locale);
        var query = new ExoplanetRepository.Query(
                null, method, fromYear, toYear, maxDistanceLy, includeControversial, sort);
        return responses.ok(
                ExoplanetRepository.LIST_CACHE, repository.list(query, paging).map(row -> view(row, lang)));
    }

    @GetMapping("/{name}")
    @Operation(
            operationId = "getExoplanet",
            summary = "Get an exoplanet",
            description = "One confirmed exoplanet, including questioned ones, with the archive responses behind"
                    + " its record.")
    ResponseEntity<ExoplanetDetail> getExoplanet(
            @Parameter(description = "Planet name, e.g. Proxima Cen b.") @PathVariable("name") @Size(min = 1, max = 64)
                    String name,
            Locale locale) {
        var lang = Lang.of(locale);
        return repository
                .detail(name)
                .map(detail -> responses.ok(
                        ExoplanetRepository.DETAIL_CACHE,
                        new ExoplanetDetail(view(detail.planet(), lang), detail.lineage())))
                .orElseThrow(() -> new NotFoundException("exoplanet", name));
    }

    private Exoplanet view(ExoplanetRepository.Row row, Lang lang) {
        return new Exoplanet(
                row.name(),
                row.hostName(),
                new Exoplanet.Discovery(
                        row.discoveryYear(),
                        method(row.discoveryMethod(), lang),
                        row.discoveryFacility(),
                        row.discoveryLocale()),
                row.orbitalPeriodDays(),
                row.semiMajorAxisAu(),
                row.radiusEarth(),
                row.massEarth(),
                row.eccentricity(),
                row.equilibriumTempK(),
                row.insolationEarth(),
                new Exoplanet.Star(
                        row.starTempK(), row.starRadiusSun(), row.starMassSun(), row.starCount(), row.planetCount()),
                row.distancePc(),
                row.distancePc() == null ? null : row.distancePc() * LIGHT_YEARS_PER_PARSEC,
                row.controversial());
    }

    private Term method(String method, Lang lang) {
        return Objects.requireNonNull(vocabulary.fromSource("discovery_method", method, lang));
    }
}
