package dev.hoshizora.api.stats;

import dev.hoshizora.api.i18n.Lang;
import dev.hoshizora.api.i18n.Term;
import dev.hoshizora.api.i18n.Vocabulary;
import dev.hoshizora.api.web.InvalidParameterException;
import dev.hoshizora.api.web.Responses;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.stream.Collectors;
import org.jspecify.annotations.Nullable;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.util.UriComponentsBuilder;

@RestController
@RequestMapping("/api/v1/stats/exoplanets")
@Tag(name = "Statistics")
class ExoplanetStatsController {

    static final String SOURCE = "exoplanet-archive";

    private final ExoplanetStatsRepository repository;
    private final Vocabulary vocabulary;
    private final Responses responses;

    ExoplanetStatsController(ExoplanetStatsRepository repository, Vocabulary vocabulary, Responses responses) {
        this.repository = repository;
        this.vocabulary = vocabulary;
        this.responses = responses;
    }

    @GetMapping("/discoveries")
    @Operation(
            operationId = "getExoplanetDiscoveries",
            summary = "Exoplanet discoveries per year",
            description = "Confirmed exoplanets per discovery year, split by the method that found them, with the"
                    + " number found from space. Each year links to its planets.")
    ResponseEntity<ExoplanetDiscoveries> getExoplanetDiscoveries(
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
            Locale locale) {
        if (fromYear != null && toYear != null && fromYear > toYear) {
            throw new InvalidParameterException("from_year", "validation.range_order");
        }
        var lang = Lang.of(locale);
        var rows = repository.discoveries(fromYear, toYear);
        var methods = rows.stream()
                .collect(Collectors.groupingBy(
                        ExoplanetStatsRepository.DiscoveryRow::method,
                        LinkedHashMap::new,
                        Collectors.summingLong(ExoplanetStatsRepository.DiscoveryRow::planets)))
                .entrySet()
                .stream()
                .sorted(Map.Entry.<String, Long>comparingByValue(Comparator.reverseOrder())
                        .thenComparing(Map.Entry.comparingByKey()))
                .map(entry -> new ExoplanetDiscoveries.Method(method(entry.getKey(), lang), entry.getValue()))
                .toList();
        var years = rows.stream()
                .collect(Collectors.groupingBy(
                        ExoplanetStatsRepository.DiscoveryRow::year, LinkedHashMap::new, Collectors.toList()))
                .entrySet()
                .stream()
                .map(entry -> year(entry.getKey(), entry.getValue(), lang))
                .toList();
        return responses.ok(
                ExoplanetStatsRepository.DISCOVERIES_CACHE, new ExoplanetDiscoveries(SOURCE, methods, years));
    }

    @GetMapping("/size-orbit")
    @Operation(
            operationId = "getExoplanetSizeOrbit",
            summary = "Exoplanet sizes against orbital periods",
            description = "Transiting exoplanets counted on a logarithmic grid: 0.25 powers of ten of orbital period"
                    + " by 0.125 powers of ten of radius. Only transits measure the radius directly.")
    ResponseEntity<ExoplanetSizeOrbit> getExoplanetSizeOrbit() {
        var cells = repository.sizeOrbit().stream()
                .map(row -> new ExoplanetSizeOrbit.Cell(
                        edge(row.periodBin(), ExoplanetStatsRepository.PERIOD_STEP_DEX),
                        edge(row.periodBin() + 1, ExoplanetStatsRepository.PERIOD_STEP_DEX),
                        edge(row.radiusBin(), ExoplanetStatsRepository.RADIUS_STEP_DEX),
                        edge(row.radiusBin() + 1, ExoplanetStatsRepository.RADIUS_STEP_DEX),
                        row.planets()))
                .toList();
        var planets = cells.stream().mapToLong(ExoplanetSizeOrbit.Cell::planets).sum();
        return responses.ok(
                ExoplanetStatsRepository.SIZE_ORBIT_CACHE,
                new ExoplanetSizeOrbit(
                        SOURCE,
                        ExoplanetStatsRepository.PERIOD_STEP_DEX,
                        ExoplanetStatsRepository.RADIUS_STEP_DEX,
                        planets,
                        cells));
    }

    private ExoplanetDiscoveries.Year year(int year, List<ExoplanetStatsRepository.DiscoveryRow> rows, Lang lang) {
        return new ExoplanetDiscoveries.Year(
                year,
                rows.stream()
                        .mapToLong(ExoplanetStatsRepository.DiscoveryRow::planets)
                        .sum(),
                rows.stream()
                        .mapToLong(ExoplanetStatsRepository.DiscoveryRow::fromSpace)
                        .sum(),
                rows.stream()
                        .map(row -> new ExoplanetDiscoveries.MethodCount(
                                method(row.method(), lang).code(), row.planets()))
                        .toList(),
                UriComponentsBuilder.fromPath("/api/v1/exoplanets")
                        .queryParam("from_year", year)
                        .queryParam("to_year", year)
                        .build()
                        .toUriString());
    }

    private Term method(String method, Lang lang) {
        return Objects.requireNonNull(vocabulary.fromSource("discovery_method", method, lang));
    }

    private static double edge(int bin, double stepDex) {
        return Math.pow(10, bin * stepDex);
    }
}
