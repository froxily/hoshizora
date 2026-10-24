package dev.hoshizora.api.meta;

import dev.hoshizora.api.i18n.Lang;
import dev.hoshizora.api.i18n.Vocabulary;
import dev.hoshizora.api.web.Page;
import dev.hoshizora.api.web.PageQuery;
import dev.hoshizora.api.web.Responses;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.Locale;
import org.jspecify.annotations.Nullable;
import org.springdoc.core.annotations.ParameterObject;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/meta")
@Tag(name = "Meta", description = "Sources, credits and data freshness.")
class SourceController {

    private final SourceRepository repository;
    private final Vocabulary vocabulary;
    private final Responses responses;
    private final Clock clock;

    SourceController(SourceRepository repository, Vocabulary vocabulary, Responses responses, Clock clock) {
        this.repository = repository;
        this.vocabulary = vocabulary;
        this.responses = responses;
        this.clock = clock;
    }

    @GetMapping("/sources")
    @Operation(
            operationId = "listSources",
            summary = "List data sources",
            description = "Every source Hoshizora ingests, with its localized name, credit, license and cadence,"
                    + " the latest ingestion run and fetch, a freshness verdict, and open data-quality problems.")
    ResponseEntity<Page<SourceView>> listSources(@ParameterObject @Valid PageQuery paging, Locale locale) {
        var lang = Lang.of(locale);
        var now = clock.instant();
        return responses.ok(SourceRepository.CACHE, repository.list(paging).map(row -> view(row, lang, now)));
    }

    private SourceView view(SourceRow row, Lang lang, Instant now) {
        var status = new SourceView.Status(
                row.lastRunStatus() == null ? null : vocabulary.term("run_status", row.lastRunStatus(), lang),
                row.lastRunStartedAt(),
                row.lastRunFinishedAt(),
                row.lastSucceededAt(),
                row.lastFetchedAt(),
                vocabulary.term("freshness", freshness(row.updateIntervalSeconds(), row.lastFetchedAt(), now), lang));
        var level = row.blocking() > 0 ? "blocking" : row.warnings() > 0 ? "warning" : "ok";
        var quality = new SourceView.Quality(row.blocking(), row.warnings(), vocabulary.term("quality", level, lang));
        return new SourceView(
                row.slug(),
                row.name().in(lang).value(),
                row.description().in(lang).value(),
                row.credit().in(lang).value(),
                row.license().in(lang).value(),
                row.licenseUrl(),
                row.homepageUrl(),
                row.cadence().in(lang).value(),
                row.updateIntervalSeconds(),
                status,
                quality);
    }

    static String freshness(@Nullable Long intervalSeconds, @Nullable Instant lastFetchedAt, Instant now) {
        if (intervalSeconds == null) {
            return "on_demand";
        }
        if (lastFetchedAt == null) {
            return "unknown";
        }
        var allowed = Duration.ofSeconds(intervalSeconds).multipliedBy(2);
        return Duration.between(lastFetchedAt, now).compareTo(allowed) <= 0 ? "fresh" : "stale";
    }
}
