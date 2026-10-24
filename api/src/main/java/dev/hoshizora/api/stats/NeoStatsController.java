package dev.hoshizora.api.stats;

import dev.hoshizora.api.web.Ranges;
import dev.hoshizora.api.web.Responses;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import java.time.Clock;
import java.time.LocalDate;
import java.time.ZoneOffset;
import org.jspecify.annotations.Nullable;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.util.UriComponentsBuilder;

@RestController
@RequestMapping("/api/v1/stats/close-approaches")
@Tag(name = "Statistics")
class NeoStatsController {

    static final String CACHE = "close-approach-monthly";

    private final CloseApproachMonthlyRepository repository;
    private final Responses responses;
    private final Clock clock;

    NeoStatsController(CloseApproachMonthlyRepository repository, Responses responses, Clock clock) {
        this.repository = repository;
        this.responses = responses;
        this.clock = clock;
    }

    @GetMapping("/monthly")
    @Operation(
            operationId = "getCloseApproachesMonthly",
            summary = "Close approaches per month",
            description = "Approaches per TDB calendar month with how many came closer than the Moon, the closest"
                    + " and the likely largest object. Defaults to ten years back and two years ahead.")
    ResponseEntity<CloseApproachMonthly> getCloseApproachesMonthly(
            @Parameter(description = "Only months starting on or after this date (YYYY-MM-DD).")
                    @RequestParam(name = "from", required = false)
                    @Nullable
                    LocalDate from,
            @Parameter(description = "Only months starting before this date (YYYY-MM-DD).")
                    @RequestParam(name = "to", required = false)
                    @Nullable
                    LocalDate to) {
        var today = LocalDate.ofInstant(clock.instant(), ZoneOffset.UTC);
        var fallback =
                new Ranges.Dates(LocalDate.of(today.getYear() - 10, 1, 1), LocalDate.of(today.getYear() + 3, 1, 1));
        var dates = Ranges.dates(from, to, fallback, 110_000);
        var items = repository.monthly(dates).stream()
                .map(row -> new CloseApproachMonthly.Month(
                        row.month(),
                        row.approaches(),
                        row.withinLunarDistance(),
                        row.closestDistLd(),
                        row.closestDesignation(),
                        row.minAbsoluteMagnitude(),
                        row.largestDesignation(),
                        row.month().isAfter(today),
                        UriComponentsBuilder.fromPath("/api/v1/close-approaches")
                                .queryParam("from", row.month())
                                .queryParam("to", row.month().plusMonths(1))
                                .queryParam("sort", "distance")
                                .build()
                                .toUriString()))
                .toList();
        return responses.ok(CACHE, new CloseApproachMonthly("jpl", dates.from(), dates.to(), items));
    }
}
