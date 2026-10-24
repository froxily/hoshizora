package dev.hoshizora.api.spaceweather;

import dev.hoshizora.api.i18n.Lang;
import dev.hoshizora.api.i18n.Vocabulary;
import dev.hoshizora.api.web.Page;
import dev.hoshizora.api.web.PageQuery;
import dev.hoshizora.api.web.Ranges;
import dev.hoshizora.api.web.Responses;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.Locale;
import org.jspecify.annotations.Nullable;
import org.springdoc.core.annotations.ParameterObject;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/space-weather")
@Tag(
        name = "Space weather",
        description = "Geomagnetic activity, solar flares, solar wind and the aurora forecast, from NOAA SWPC.")
class SpaceWeatherController {

    private static final Duration WEEK = Duration.ofDays(7);
    private static final Duration DAY = Duration.ofDays(1);

    private final SpaceWeatherRepository repository;
    private final AuroraRepository aurora;
    private final Vocabulary vocabulary;
    private final Responses responses;
    private final Clock clock;

    SpaceWeatherController(
            SpaceWeatherRepository repository,
            AuroraRepository aurora,
            Vocabulary vocabulary,
            Responses responses,
            Clock clock) {
        this.repository = repository;
        this.aurora = aurora;
        this.vocabulary = vocabulary;
        this.responses = responses;
        this.clock = clock;
    }

    @GetMapping("/now")
    @Operation(
            operationId = "getSpaceWeatherNow",
            summary = "Get current space weather",
            description = "The latest planetary Kp with its NOAA storm level, the latest solar wind minute, and the"
                    + " strongest classified flare of the past 24 hours, as of the next full hour.")
    ResponseEntity<SpaceWeatherNow> getSpaceWeatherNow(Locale locale) {
        var lang = Lang.of(locale);
        var asOf = clock.instant().truncatedTo(ChronoUnit.HOURS).plus(Duration.ofHours(1));
        var row = repository.now(asOf);
        return responses.ok(
                SpaceWeatherRepository.NOW_CACHE,
                new SpaceWeatherNow(
                        asOf,
                        row.kp() == null ? null : kp(row.kp(), lang),
                        row.wind(),
                        row.flare() == null ? null : flare(row.flare(), lang),
                        row.flaresLastDay()));
    }

    @GetMapping("/kp")
    @Operation(
            operationId = "listKp",
            summary = "List planetary Kp",
            description = "Planetary Kp per 3-hour interval with the NOAA geomagnetic storm level. Defaults to the"
                    + " past seven days; a range spans at most 366 days.")
    ResponseEntity<Kp> listKp(
            @Parameter(description = "Start of the range (ISO-8601, UTC). Defaults to seven days before to.")
                    @RequestParam(name = "from", required = false)
                    @Nullable
                    Instant from,
            @Parameter(description = "End of the range, exclusive (ISO-8601, UTC). Defaults to the next full hour.")
                    @RequestParam(name = "to", required = false)
                    @Nullable
                    Instant to,
            Locale locale) {
        var lang = Lang.of(locale);
        var window = Ranges.window(from, to, clock.instant(), WEEK, Duration.ofDays(366));
        var items = repository.kp(window).stream().map(row -> kp(row, lang)).toList();
        return responses.ok(SpaceWeatherRepository.KP_CACHE, new Kp(window.from(), window.to(), items));
    }

    @GetMapping("/flares")
    @Operation(
            operationId = "listFlares",
            summary = "List solar flares",
            description = "GOES X-ray flares with their class, peak flux and NOAA radio blackout level, newest or"
                    + " strongest first.")
    ResponseEntity<Page<Flare>> listFlares(
            @Parameter(description = "Only flares peaking at or after this instant (ISO-8601, UTC).")
                    @RequestParam(name = "from", required = false)
                    @Nullable
                    Instant from,
            @Parameter(description = "Only flares peaking before this instant (ISO-8601, UTC).")
                    @RequestParam(name = "to", required = false)
                    @Nullable
                    Instant to,
            @Parameter(description = "Only flares of at least this class: A, B, C, M or X.")
                    @RequestParam(name = "min_class", required = false)
                    @Nullable
                    FlareClass minClass,
            @Parameter(description = "-time for newest first, -flux for strongest first.")
                    @RequestParam(name = "sort", defaultValue = "-time")
                    FlareSort sort,
            @ParameterObject @Valid PageQuery paging,
            Locale locale) {
        Ranges.ordered(from, to);
        var lang = Lang.of(locale);
        var filter = new SpaceWeatherRepository.FlareFilter(from, to, minClass, sort);
        return responses.ok(
                SpaceWeatherRepository.FLARES_CACHE,
                repository.flares(filter, paging).map(row -> flare(row, lang)));
    }

    @GetMapping("/solar-wind")
    @Operation(
            operationId = "listSolarWind",
            summary = "List solar wind",
            description = "Solar wind at L1 from the spacecraft SWPC marks active: one point per minute (default one"
                    + " day, at most three) or hourly means (default seven days, at most 92).")
    ResponseEntity<SolarWind> listSolarWind(
            @Parameter(description = "Start of the range (ISO-8601, UTC).")
                    @RequestParam(name = "from", required = false)
                    @Nullable
                    Instant from,
            @Parameter(description = "End of the range, exclusive (ISO-8601, UTC). Defaults to the next full hour.")
                    @RequestParam(name = "to", required = false)
                    @Nullable
                    Instant to,
            @Parameter(description = "minute or hour.") @RequestParam(name = "resolution", defaultValue = "minute")
                    SolarWindResolution resolution) {
        var hourly = resolution == SolarWindResolution.HOUR;
        var window = Ranges.window(
                from, to, clock.instant(), hourly ? WEEK : DAY, hourly ? Duration.ofDays(92) : Duration.ofDays(3));
        return responses.ok(
                SpaceWeatherRepository.SOLAR_WIND_CACHE,
                new SolarWind(window.from(), window.to(), resolution, repository.solarWind(window, resolution)));
    }

    @GetMapping("/aurora")
    @Operation(
            operationId = "getAurora",
            summary = "Get the aurora forecast",
            description = "The latest OVATION forecast of the probability of visible aurora on a 1° grid, with each"
                    + " hemisphere's peak and its 10 % boundary, plus one summary per forecast for the past 48 hours.")
    ResponseEntity<Aurora> getAurora(
            @Parameter(description = "Only cells at or above this probability, in percent.")
                    @RequestParam(name = "min_percent", defaultValue = "1")
                    @Min(1)
                    @Max(100)
                    int minPercent) {
        return responses.ok(AuroraRepository.CACHE, aurora.aurora(minPercent));
    }

    private Kp.Reading kp(SpaceWeatherRows.KpRow row, Lang lang) {
        return new Kp.Reading(row.observedAt(), row.kp(), vocabulary.term("g_scale", "g" + row.gScale(), lang));
    }

    private Flare flare(SpaceWeatherRows.FlareRow row, Lang lang) {
        return new Flare(
                row.id(),
                row.beginAt(),
                row.peakAt(),
                row.endAt(),
                row.xrayClass(),
                row.xrayClass() == null ? null : row.xrayClass().substring(0, 1),
                row.peakFluxWm2(),
                row.rScale() == null ? null : vocabulary.term("r_scale", "r" + row.rScale(), lang),
                row.endAt() == null,
                row.satellite());
    }
}
