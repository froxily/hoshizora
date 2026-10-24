package dev.hoshizora.api.neo;

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
@RequestMapping("/api/v1/impact-risks")
@Tag(name = "Near-Earth")
class ImpactRiskController {

    private final ImpactRiskRepository repository;
    private final CloseApproachViews approaches;
    private final Vocabulary vocabulary;
    private final Responses responses;

    ImpactRiskController(
            ImpactRiskRepository repository,
            CloseApproachViews approaches,
            Vocabulary vocabulary,
            Responses responses) {
        this.repository = repository;
        this.approaches = approaches;
        this.vocabulary = vocabulary;
        this.responses = responses;
    }

    @GetMapping
    @Operation(
            operationId = "listImpactRisks",
            summary = "List Sentry impact risks",
            description = "Objects JPL Sentry monitors for possible future Earth impacts, highest cumulative Palermo"
                    + " scale first. Objects removed from Sentry after new observations are hidden unless asked for.")
    ResponseEntity<Page<ImpactRisk>> listImpactRisks(
            @Parameter(description = "Only objects with a cumulative Palermo scale at least this.")
                    @RequestParam(name = "min_palermo", required = false)
                    @Nullable
                    Double minPalermo,
            @Parameter(description = "Only objects with a maximum Torino scale at least this (0 to 10).")
                    @RequestParam(name = "min_torino", required = false)
                    @Min(0)
                    @Max(10)
                    @Nullable
                    Integer minTorino,
            @Parameter(description = "true to include objects Sentry has removed from its list.")
                    @RequestParam(name = "include_removed", defaultValue = "false")
                    boolean includeRemoved,
            @Parameter(description = "-palermo, -probability, -torino or designation.")
                    @RequestParam(name = "sort", defaultValue = "-palermo")
                    ImpactRiskSort sort,
            @ParameterObject @Valid PageQuery paging,
            Locale locale) {
        var lang = Lang.of(locale);
        var query = new ImpactRiskQuery(null, minPalermo, minTorino, includeRemoved, sort);
        return responses.ok(
                ImpactRiskRepository.LIST_CACHE, repository.list(query, paging).map(row -> view(row, lang)));
    }

    @GetMapping("/{designation}")
    @Operation(
            operationId = "getImpactRisk",
            summary = "Get a Sentry object",
            description = "One Sentry object, monitored or removed, with every close approach JPL lists for it"
                    + " and the source responses behind the record.")
    ResponseEntity<ImpactRiskDetail> getImpactRisk(
            @Parameter(description = "JPL designation, e.g. 29075 or 2010 RF12.")
                    @PathVariable("designation")
                    @Size(min = 1, max = 64)
                    String designation,
            Locale locale) {
        var lang = Lang.of(locale);
        return repository
                .detail(designation)
                .map(detail -> responses.ok(
                        ImpactRiskRepository.DETAIL_CACHE,
                        new ImpactRiskDetail(
                                view(detail.risk(), lang),
                                detail.approaches().stream()
                                        .map(row -> approaches.view(row, lang))
                                        .toList(),
                                detail.lineage())))
                .orElseThrow(() -> new NotFoundException("impact_risk", designation));
    }

    private ImpactRisk view(ImpactRiskRow row, Lang lang) {
        return new ImpactRisk(
                row.designation(),
                row.fullname(),
                row.impactProbability(),
                row.palermoCumulative(),
                row.palermoMax(),
                row.torinoMax(),
                torino(row.torinoMax(), lang),
                row.potentialImpacts(),
                row.impactYearFirst(),
                row.impactYearLast(),
                row.lastObserved(),
                row.diameterKm(),
                row.hMag(),
                row.vInfKms(),
                new CloseApproach.Size(
                        null,
                        null,
                        row.diameterMinKm(),
                        row.diameterMaxKm(),
                        CloseApproachViews.DARK_ALBEDO,
                        CloseApproachViews.BRIGHT_ALBEDO),
                row.removedAt());
    }

    private @Nullable Term torino(@Nullable Integer value, Lang lang) {
        if (value == null) {
            return null;
        }
        var category = value == 0
                ? "no_hazard"
                : value == 1
                        ? "normal"
                        : value <= 4 ? "meriting_attention" : value <= 7 ? "threatening" : "certain_collision";
        return vocabulary.term("torino", category, lang);
    }
}
