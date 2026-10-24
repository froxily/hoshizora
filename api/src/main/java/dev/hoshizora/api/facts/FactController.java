package dev.hoshizora.api.facts;

import dev.hoshizora.api.common.Lineage;
import dev.hoshizora.api.i18n.Lang;
import dev.hoshizora.api.i18n.Vocabulary;
import dev.hoshizora.api.web.NotFoundException;
import dev.hoshizora.api.web.Responses;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import java.time.Clock;
import java.util.Locale;
import java.util.Optional;
import org.jspecify.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.util.UriComponentsBuilder;

@RestController
@RequestMapping("/api/v1/facts")
@Tag(name = "Facts", description = "Data-driven fun facts in English and Japanese, each traced to its records.")
class FactController {

    private static final Logger LOG = LoggerFactory.getLogger(FactController.class);

    private final FactRepository repository;
    private final FactRenderer renderer;
    private final Vocabulary vocabulary;
    private final Lineage lineage;
    private final Responses responses;
    private final Clock clock;

    FactController(
            FactRepository repository,
            FactRenderer renderer,
            Vocabulary vocabulary,
            Lineage lineage,
            Responses responses,
            Clock clock) {
        this.repository = repository;
        this.renderer = renderer;
        this.vocabulary = vocabulary;
        this.lineage = lineage;
        this.responses = responses;
        this.clock = clock;
    }

    @GetMapping
    @Operation(
            operationId = "listFacts",
            summary = "List top facts",
            description = "The highest-scoring facts that are still current, rendered in the requested language."
                    + " Facts below their template's minimum score never show. Without module or entity filters"
                    + " the list mixes modules: every module's best fact first, then every module's second best,"
                    + " and so on, each round best first.")
    ResponseEntity<Facts> listFacts(
            @Parameter(description = "Only facts for this page, e.g. home, launches, near-earth, sun or agencies.")
                    @RequestParam(name = "module", required = false)
                    @Pattern(regexp = "[a-z-]{1,32}")
                    @Nullable
                    String module,
            @Parameter(description = "Only facts about this kind of record, e.g. organization.")
                    @RequestParam(name = "entity_type", required = false)
                    @Size(min = 1, max = 64)
                    @Nullable
                    String entityType,
            @Parameter(description = "Only facts about this record, together with entity_type.")
                    @RequestParam(name = "entity_key", required = false)
                    @Size(min = 1, max = 128)
                    @Nullable
                    String entityKey,
            @Parameter(description = "How many facts, at most 20.")
                    @RequestParam(name = "limit", defaultValue = "3")
                    @Min(1)
                    @Max(20)
                    int limit,
            Locale locale) {
        var lang = Lang.of(locale);
        var now = clock.instant();
        var query = new FactRepository.Query(module, entityType, entityKey);
        var current =
                repository.list(query).stream().filter(row -> row.validAt(now)).toList();
        var ordered = query.pageAgnostic() ? FactMix.acrossModules(current) : current;
        var items = ordered.stream()
                .flatMap(row -> view(row, lang).stream())
                .limit(limit)
                .toList();
        return responses.ok(FactRepository.LIST_CACHE, new Facts(items));
    }

    @GetMapping("/{id}")
    @Operation(
            operationId = "getFact",
            summary = "Get a fact",
            description = "One fact with the records behind it and the source responses that produced those records.")
    ResponseEntity<FactDetail> getFact(
            @Parameter(description = "Fact id.") @PathVariable("id") @Min(1) long id, Locale locale) {
        var lang = Lang.of(locale);
        var row = repository
                .detail(id)
                .filter(fact -> fact.validAt(clock.instant()))
                .orElseThrow(() -> new NotFoundException("fact", Long.toString(id)));
        var fact = view(row, lang).orElseThrow(() -> new NotFoundException("fact", Long.toString(id)));
        var sources = row.sourceRefs().stream()
                .filter(ref -> ref.entity().startsWith("core."))
                .flatMap(ref -> lineage.of(ref.entity(), ref.key()).stream())
                .distinct()
                .toList();
        return responses.ok(FactRepository.DETAIL_CACHE, new FactDetail(fact, sources));
    }

    private Optional<Fact> view(FactRow row, Lang lang) {
        var text = row.text().in(lang);
        try {
            return Optional.of(new Fact(
                    row.id(),
                    row.templateKey(),
                    row.module(),
                    renderer.render(text.value(), row.params(), lang),
                    text.lang(),
                    row.params(),
                    row.score(),
                    vocabulary.term("fact_kind", row.kind(), lang),
                    row.citationUrl(),
                    row.entityType() == null || row.entityKey() == null
                            ? null
                            : new Fact.Entity(row.entityType(), row.entityKey()),
                    row.sourceRefs().stream()
                            .map(ref -> new Fact.Reference(ref.entity(), ref.key(), recordsUrl(ref)))
                            .toList(),
                    row.generatedAt(),
                    row.validUntil()));
        } catch (FactRenderer.FactRenderingException e) {
            LOG.warn("Skipping fact {} ({}): {}", row.id(), row.templateKey(), e.getMessage());
            return Optional.empty();
        }
    }

    static @Nullable String recordsUrl(FactRow.SourceRef ref) {
        var parts = ref.key().split("\\|");
        return switch (ref.entity()) {
            case "core.launch" -> path("/api/v1/launches/{key}", ref.key());
            case "core.impact_risk" -> path("/api/v1/impact-risks/{key}", ref.key());
            case "mart.organization_launch_summary" -> path("/api/v1/agencies/{key}", ref.key());
            case "core.space_weather_event" ->
                ref.key().startsWith("xray_flare|") ? "/api/v1/space-weather/flares" : null;
            case "mart.kp_daily" -> "/api/v1/space-weather/kp";
            case "mart.solar_wind_hourly" -> "/api/v1/space-weather/solar-wind";
            case "mart.launch_pad_activity" -> "/api/v1/stats/launches/pads";
            case "core.launcher", "core.landing" -> "/api/v1/stats/launches/boosters";
            case "core.exoplanet" -> path("/api/v1/exoplanets/{key}", ref.key());
            case "mart.exoplanet_discoveries_yearly" ->
                UriComponentsBuilder.fromPath("/api/v1/stats/exoplanets/discoveries")
                        .queryParam("from_year", parts[0])
                        .queryParam("to_year", parts[0])
                        .encode()
                        .build()
                        .toUriString();
            case "mart.objects_in_orbit_by_owner", "mart.objects_in_orbit_by_country" ->
                "/api/v1/stats/orbits/countries";
            case "core.close_approach", "core.small_body" ->
                UriComponentsBuilder.fromPath("/api/v1/close-approaches")
                        .queryParam("designation", parts[0])
                        .encode()
                        .build()
                        .toUriString();
            case "mart.launch_cadence_yearly" -> yearly("/api/v1/stats/launches/cadence", parts);
            case "mart.reusability_yearly" -> yearly("/api/v1/stats/launches/reusability", parts);
            default -> null;
        };
    }

    private static @Nullable String yearly(String path, String[] parts) {
        return parts.length == 3
                ? UriComponentsBuilder.fromPath(path)
                        .queryParam("group_by", parts[0])
                        .queryParam("key", parts[1])
                        .queryParam("from_year", parts[2])
                        .queryParam("to_year", parts[2])
                        .encode()
                        .build()
                        .toUriString()
                : null;
    }

    private static String path(String template, String key) {
        return UriComponentsBuilder.fromPath(template)
                .buildAndExpand(key)
                .encode()
                .toUriString();
    }
}
