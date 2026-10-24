package dev.hoshizora.api.launches;

import dev.hoshizora.api.i18n.Lang;
import dev.hoshizora.api.web.NotFoundException;
import dev.hoshizora.api.web.Page;
import dev.hoshizora.api.web.PageQuery;
import dev.hoshizora.api.web.Ranges;
import dev.hoshizora.api.web.Responses;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import java.time.Instant;
import java.util.Locale;
import java.util.UUID;
import org.jspecify.annotations.Nullable;
import org.springdoc.core.annotations.ParameterObject;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/launches")
@Tag(name = "Launches", description = "Every orbital launch attempt and planned launch, from Launch Library 2.")
class LaunchController {

    private final LaunchRepository repository;
    private final LaunchViews views;
    private final Responses responses;

    LaunchController(LaunchRepository repository, LaunchViews views, Responses responses) {
        this.repository = repository;
        this.views = views;
        this.responses = responses;
    }

    @GetMapping
    @Operation(
            operationId = "listLaunches",
            summary = "List launches",
            description = "Launches filtered by time, outcome, provider, national program, vehicle family or launch"
                    + " site country. Entity names fall back to English where no Japanese name is curated yet.")
    ResponseEntity<Page<LaunchSummary>> listLaunches(
            @Parameter(description = "Only launches at or after this instant (ISO-8601, UTC).")
                    @RequestParam(name = "from", required = false)
                    @Nullable
                    Instant from,
            @Parameter(description = "Only launches before this instant (ISO-8601, UTC).")
                    @RequestParam(name = "to", required = false)
                    @Nullable
                    Instant to,
            @Parameter(description = "Only launches with this outcome.")
                    @RequestParam(name = "status", required = false)
                    @Nullable
                    LaunchOutcome status,
            @Parameter(description = "Provider key: a curated slug such as jaxa, or ll2-<agency id>.")
                    @RequestParam(name = "provider", required = false)
                    @Size(max = 64)
                    @Nullable
                    String provider,
            @Parameter(description = "National program slug, e.g. japan, usa, china, russia, europe or india.")
                    @RequestParam(name = "program", required = false)
                    @Size(max = 64)
                    @Nullable
                    String program,
            @Parameter(description = "Vehicle family, e.g. Falcon, Long March or Soyuz (case-insensitive).")
                    @RequestParam(name = "vehicle_family", required = false)
                    @Size(max = 64)
                    @Nullable
                    String vehicleFamily,
            @Parameter(description = "ISO 3166-1 alpha-2 country of the launch site, e.g. JP.")
                    @RequestParam(name = "site_country", required = false)
                    @Pattern(regexp = "[A-Za-z]{2}")
                    @Nullable
                    String siteCountry,
            @Parameter(description = "Launch Library 2 pad id, as in /api/v1/stats/launches/pads.")
                    @RequestParam(name = "pad", required = false)
                    @Min(1)
                    @Nullable
                    Integer pad,
            @Parameter(description = "net for oldest first, -net for newest first.")
                    @RequestParam(name = "sort", defaultValue = "-net")
                    LaunchSort sort,
            @ParameterObject @Valid PageQuery paging,
            Locale locale) {
        Ranges.ordered(from, to);
        var lang = Lang.of(locale);
        var filter = new LaunchFilter(from, to, status, provider, program, vehicleFamily, siteCountry, pad, sort);
        return responses.ok(
                LaunchRepository.LIST_CACHE, repository.list(filter, paging).map(row -> views.summary(row, lang)));
    }

    @GetMapping("/{id}")
    @Operation(
            operationId = "getLaunch",
            summary = "Get a launch",
            description = "One launch with its window, the provider's national programs, mission partners, the"
                    + " objects CelesTrak catalogued from it, and the source responses behind the record.")
    ResponseEntity<LaunchDetail> getLaunch(
            @Parameter(description = "Launch Library 2 launch id (UUID).") @PathVariable("id") UUID id, Locale locale) {
        var lang = Lang.of(locale);
        return repository
                .detail(id)
                .map(detail -> responses.ok(LaunchRepository.DETAIL_CACHE, views.detail(detail, lang)))
                .orElseThrow(() -> new NotFoundException("launch", id.toString()));
    }
}
