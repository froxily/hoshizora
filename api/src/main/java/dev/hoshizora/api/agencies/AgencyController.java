package dev.hoshizora.api.agencies;

import dev.hoshizora.api.i18n.Lang;
import dev.hoshizora.api.web.NotFoundException;
import dev.hoshizora.api.web.Page;
import dev.hoshizora.api.web.PageQuery;
import dev.hoshizora.api.web.Responses;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import java.util.Locale;
import org.jspecify.annotations.Nullable;
import org.springdoc.core.annotations.ParameterObject;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/agencies")
@Tag(
        name = "Agencies",
        description = "Space agencies, launch companies, armed forces and international bodies, as one model.")
class AgencyController {

    private final AgencyRepository repository;
    private final AgencyViews views;
    private final Responses responses;

    AgencyController(AgencyRepository repository, AgencyViews views, Responses responses) {
        this.repository = repository;
        this.views = views;
        this.responses = responses;
    }

    @GetMapping
    @Operation(
            operationId = "listAgencies",
            summary = "List organizations",
            description = "Organizations from Launch Library 2 and the curated reference data, with their countries,"
                    + " national programs and launch totals as provider. A launch provider is not necessarily an"
                    + " agency: Chinese launches are mostly attributed to CASC, a state company.")
    ResponseEntity<Page<AgencySummary>> listAgencies(
            @Parameter(description = "Only organizations of this type.")
                    @RequestParam(name = "type", required = false)
                    @Nullable
                    OrganizationType type,
            @Parameter(description = "ISO 3166-1 alpha-2 country, e.g. JP.")
                    @RequestParam(name = "country", required = false)
                    @Pattern(regexp = "[A-Za-z]{2}")
                    @Nullable
                    String country,
            @Parameter(description = "National program slug, e.g. japan.")
                    @RequestParam(name = "program", required = false)
                    @Size(max = 64)
                    @Nullable
                    String program,
            @Parameter(description = "true for launch providers only, false for organizations that never launched.")
                    @RequestParam(name = "has_launches", required = false)
                    @Nullable
                    Boolean hasLaunches,
            @Parameter(description = "Text to find in the English or Japanese name or the abbreviation.")
                    @RequestParam(name = "q", required = false)
                    @Size(min = 1, max = 64)
                    @Nullable
                    String query,
            @Parameter(description = "-launches for most launches first, name for alphabetical.")
                    @RequestParam(name = "sort", defaultValue = "-launches")
                    AgencySort sort,
            @ParameterObject @Valid PageQuery paging,
            Locale locale) {
        var lang = Lang.of(locale);
        var filter = new AgencyFilter(type, country, program, hasLaunches, query, sort);
        return responses.ok(
                AgencyRepository.LIST_CACHE, repository.list(filter, paging).map(row -> views.summary(row, lang)));
    }

    @GetMapping("/{key}")
    @Operation(
            operationId = "getAgency",
            summary = "Get an organization",
            description = "One organization with its launch record and recent reliability, the vehicles it flew"
                    + " most, its latest and next launches, objects catalogued under its own owner codes, and the"
                    + " source responses behind the record. Accepts the curated slug or ll2-<agency id>.")
    ResponseEntity<AgencyDetail> getAgency(
            @Parameter(description = "Organization key, e.g. jaxa, nasa, spacex or ll2-154.")
                    @PathVariable("key")
                    @Pattern(regexp = "[a-z0-9-]{1,64}")
                    String key,
            Locale locale) {
        var lang = Lang.of(locale);
        return repository
                .detail(key)
                .map(detail -> responses.ok(AgencyRepository.DETAIL_CACHE, views.detail(detail, lang)))
                .orElseThrow(() -> new NotFoundException("agency", key));
    }
}
