package dev.hoshizora.api.neo;

import dev.hoshizora.api.i18n.Lang;
import dev.hoshizora.api.web.Page;
import dev.hoshizora.api.web.PageQuery;
import dev.hoshizora.api.web.Ranges;
import dev.hoshizora.api.web.Responses;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Size;
import java.time.LocalDate;
import java.util.Locale;
import org.jspecify.annotations.Nullable;
import org.springdoc.core.annotations.ParameterObject;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/close-approaches")
@Tag(name = "Near-Earth", description = "Asteroid and comet close approaches and Sentry impact monitoring, from JPL.")
class CloseApproachController {

    private final CloseApproachRepository repository;
    private final CloseApproachViews views;
    private final Responses responses;

    CloseApproachController(CloseApproachRepository repository, CloseApproachViews views, Responses responses) {
        this.repository = repository;
        this.views = views;
        this.responses = responses;
    }

    @GetMapping
    @Operation(
            operationId = "listCloseApproaches",
            summary = "List close approaches",
            description = "Approaches within 0.05 au of Earth from 1900 to 2200, past and predicted, with distances"
                    + " in km and Earth–Moon distances, UTC times, and a size range estimated from absolute"
                    + " magnitude where no measured diameter exists.")
    ResponseEntity<Page<CloseApproach>> listCloseApproaches(
            @Parameter(description = "Only approaches on or after this TDB calendar date (YYYY-MM-DD).")
                    @RequestParam(name = "from", required = false)
                    @Nullable
                    LocalDate from,
            @Parameter(description = "Only approaches before this TDB calendar date (YYYY-MM-DD).")
                    @RequestParam(name = "to", required = false)
                    @Nullable
                    LocalDate to,
            @Parameter(description = "Only approaches at most this many Earth–Moon distances away.")
                    @RequestParam(name = "max_dist_ld", required = false)
                    @DecimalMin(value = "0", inclusive = false)
                    @DecimalMax("20")
                    @Nullable
                    Double maxDistLd,
            @Parameter(description = "Only objects with absolute magnitude H at most this, i.e. larger objects.")
                    @RequestParam(name = "max_h", required = false)
                    @DecimalMin("0")
                    @DecimalMax("40")
                    @Nullable
                    Double maxH,
            @Parameter(description = "Only this object, by JPL designation, e.g. 99942 or 2026 TS.")
                    @RequestParam(name = "designation", required = false)
                    @Size(min = 1, max = 64)
                    @Nullable
                    String designation,
            @Parameter(description = "true for objects on the active Sentry impact-risk list only.")
                    @RequestParam(name = "sentry", required = false)
                    @Nullable
                    Boolean sentry,
            @Parameter(description = "date for soonest first, -date for latest first, distance for closest first.")
                    @RequestParam(name = "sort", defaultValue = "date")
                    CloseApproachSort sort,
            @ParameterObject @Valid PageQuery paging,
            Locale locale) {
        Ranges.ordered(from, to);
        var lang = Lang.of(locale);
        var filter = new CloseApproachFilter(from, to, maxDistLd, maxH, designation, sentry, sort);
        return responses.ok(
                CloseApproachRepository.CACHE, repository.list(filter, paging).map(row -> views.view(row, lang)));
    }
}
