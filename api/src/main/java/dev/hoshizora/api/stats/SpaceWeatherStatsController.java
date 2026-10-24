package dev.hoshizora.api.stats;

import dev.hoshizora.api.i18n.Lang;
import dev.hoshizora.api.i18n.Vocabulary;
import dev.hoshizora.api.web.Ranges;
import dev.hoshizora.api.web.Responses;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import java.time.Clock;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.Locale;
import org.jspecify.annotations.Nullable;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.util.UriComponentsBuilder;

@RestController
@RequestMapping("/api/v1/stats/space-weather")
@Tag(name = "Statistics")
class SpaceWeatherStatsController {

    private static final String SOURCE = "swpc";

    private final SpaceWeatherStatsRepository repository;
    private final Vocabulary vocabulary;
    private final Responses responses;
    private final Clock clock;

    SpaceWeatherStatsController(
            SpaceWeatherStatsRepository repository, Vocabulary vocabulary, Responses responses, Clock clock) {
        this.repository = repository;
        this.vocabulary = vocabulary;
        this.responses = responses;
        this.clock = clock;
    }

    @GetMapping("/flares")
    @Operation(
            operationId = "getFlaresMonthly",
            summary = "Solar flares per month",
            description = "Classified X-ray flares per UTC month by class letter, with the strongest of each month."
                    + " Defaults to the past twelve months. History grows with every ingestion, since SWPC publishes"
                    + " only the latest week.")
    ResponseEntity<FlaresMonthly> getFlaresMonthly(
            @Parameter(description = "Only months starting on or after this date (YYYY-MM-DD).")
                    @RequestParam(name = "from", required = false)
                    @Nullable
                    LocalDate from,
            @Parameter(description = "Only months starting before this date (YYYY-MM-DD).")
                    @RequestParam(name = "to", required = false)
                    @Nullable
                    LocalDate to) {
        var thisMonth = today().withDayOfMonth(1);
        var dates =
                Ranges.dates(from, to, new Ranges.Dates(thisMonth.minusMonths(11), thisMonth.plusMonths(1)), 11_000);
        var items = repository.flares(dates).stream()
                .map(month -> new FlaresMonthly.Month(
                        month.month(),
                        month.total(),
                        month.byClass(),
                        month.maxPeakFluxWm2(),
                        month.strongestClass(),
                        recordsUrl(
                                "/api/v1/space-weather/flares?min_class=A",
                                month.month(),
                                month.month().plusMonths(1))))
                .toList();
        return responses.ok(
                SpaceWeatherStatsRepository.FLARES_CACHE, new FlaresMonthly(SOURCE, dates.from(), dates.to(), items));
    }

    @GetMapping("/kp")
    @Operation(
            operationId = "getKpDaily",
            summary = "Kp per day",
            description = "Daily maximum and mean planetary Kp with the NOAA storm level of the maximum. Defaults to"
                    + " the past 30 days.")
    ResponseEntity<KpDaily> getKpDaily(
            @Parameter(description = "First UTC day, inclusive (YYYY-MM-DD).")
                    @RequestParam(name = "from", required = false)
                    @Nullable
                    LocalDate from,
            @Parameter(description = "Last UTC day, exclusive (YYYY-MM-DD).")
                    @RequestParam(name = "to", required = false)
                    @Nullable
                    LocalDate to,
            Locale locale) {
        var lang = Lang.of(locale);
        var tomorrow = today().plusDays(1);
        var dates = Ranges.dates(from, to, new Ranges.Dates(tomorrow.minusDays(30), tomorrow), 3_660);
        var items = repository.kp(dates).stream()
                .map(day -> new KpDaily.Day(
                        day.day(),
                        day.kpMax(),
                        day.kpMean(),
                        day.intervals(),
                        vocabulary.term("g_scale", "g" + day.gScale(), lang),
                        recordsUrl(
                                "/api/v1/space-weather/kp", day.day(), day.day().plusDays(1))))
                .toList();
        return responses.ok(SpaceWeatherStatsRepository.KP_CACHE, new KpDaily(SOURCE, dates.from(), dates.to(), items));
    }

    private LocalDate today() {
        return LocalDate.ofInstant(clock.instant(), ZoneOffset.UTC);
    }

    private static String recordsUrl(String path, LocalDate from, LocalDate to) {
        return UriComponentsBuilder.fromUriString(path)
                .queryParam("from", from.atStartOfDay().toInstant(ZoneOffset.UTC))
                .queryParam("to", to.atStartOfDay().toInstant(ZoneOffset.UTC))
                .build()
                .toUriString();
    }
}
