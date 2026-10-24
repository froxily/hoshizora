package dev.hoshizora.api.stats;

import dev.hoshizora.api.common.Refs;
import dev.hoshizora.api.i18n.Bilingual;
import dev.hoshizora.api.i18n.Lang;
import dev.hoshizora.api.i18n.Vocabulary;
import dev.hoshizora.api.launches.LaunchSummary;
import dev.hoshizora.api.web.InvalidParameterException;
import dev.hoshizora.api.web.Responses;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import java.util.Locale;
import org.jspecify.annotations.Nullable;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/stats/launches")
@Tag(name = "Statistics", description = "Aggregates from the analytics marts, each linking to the records behind it.")
class LaunchStatsController {

    static final String SOURCE = "launch-library";

    private final LaunchStatsRepository repository;
    private final Vocabulary vocabulary;
    private final Refs refs;
    private final Responses responses;

    LaunchStatsController(LaunchStatsRepository repository, Vocabulary vocabulary, Refs refs, Responses responses) {
        this.repository = repository;
        this.vocabulary = vocabulary;
        this.refs = refs;
        this.responses = responses;
    }

    @GetMapping("/cadence")
    @Operation(
            operationId = "getLaunchCadence",
            summary = "Launches per year",
            description = "Launch attempts and outcomes per UTC year, grouped by national program, provider, vehicle"
                    + " family or launch-site country, busiest groups first. Each count links to its launches.")
    ResponseEntity<LaunchCadence> getLaunchCadence(
            @Parameter(description = "How to group launches.")
                    @RequestParam(name = "group_by", defaultValue = "program")
                    LaunchGrouping groupBy,
            @Parameter(description = "Only this group, e.g. japan for group_by=program.")
                    @RequestParam(name = "key", required = false)
                    @Size(min = 1, max = 64)
                    @Nullable
                    String key,
            @Parameter(description = "First year, inclusive.")
                    @RequestParam(name = "from_year", required = false)
                    @Min(1957)
                    @Max(2100)
                    @Nullable
                    Integer fromYear,
            @Parameter(description = "Last year, inclusive.")
                    @RequestParam(name = "to_year", required = false)
                    @Min(1957)
                    @Max(2100)
                    @Nullable
                    Integer toYear,
            @Parameter(description = "How many groups, at most 100.")
                    @RequestParam(name = "limit", defaultValue = "10")
                    @Min(1)
                    @Max(100)
                    int limit,
            Locale locale) {
        if (fromYear != null && toYear != null && fromYear > toYear) {
            throw new InvalidParameterException("from_year", "validation.range_order");
        }
        var lang = Lang.of(locale);
        var series =
                repository.cadence(new LaunchStatsRepository.GroupQuery(groupBy, key, fromYear, toYear, limit)).stream()
                        .map(row -> new LaunchCadence.Series(
                                group(groupBy, row.group(), lang),
                                row.totalAttempts(),
                                RecordsUrls.launches(groupBy, row.group().key(), null),
                                row.years().stream()
                                        .map(year -> new LaunchCadence.Year(
                                                year.year(),
                                                year.attempts(),
                                                year.successes(),
                                                year.failures(),
                                                year.partialFailures(),
                                                year.scheduled(),
                                                RecordsUrls.launches(
                                                        groupBy, row.group().key(), year.year())))
                                        .toList()))
                        .toList();
        return responses.ok(LaunchStatsRepository.CADENCE_CACHE, new LaunchCadence(SOURCE, groupBy, series));
    }

    @GetMapping("/success")
    @Operation(
            operationId = "getLaunchSuccess",
            summary = "Launch success rates",
            description = "Each group's success rate over its whole history and over its latest 20 completed"
                    + " attempts, its current and longest runs of successes, and the record at the end of each year.")
    ResponseEntity<LaunchSuccess> getLaunchSuccess(
            @Parameter(description = "How to group launches.")
                    @RequestParam(name = "group_by", defaultValue = "program")
                    LaunchGrouping groupBy,
            @Parameter(description = "Only this group, e.g. spacex for group_by=provider.")
                    @RequestParam(name = "key", required = false)
                    @Size(min = 1, max = 64)
                    @Nullable
                    String key,
            @Parameter(description = "How many groups, most attempts first, at most 100.")
                    @RequestParam(name = "limit", defaultValue = "10")
                    @Min(1)
                    @Max(100)
                    int limit,
            Locale locale) {
        var lang = Lang.of(locale);
        var groups = repository.success(new LaunchStatsRepository.GroupQuery(groupBy, key, null, null, limit)).stream()
                .map(row -> new LaunchSuccess.Group(
                        group(groupBy, row.group(), lang),
                        row.attempts(),
                        row.successes(),
                        rate(row.successes(), row.attempts()),
                        row.recentAttempts(),
                        row.recentSuccesses(),
                        rate(row.recentSuccesses(), row.recentAttempts()),
                        row.currentStreak(),
                        row.longestStreak(),
                        RecordsUrls.launches(groupBy, row.group().key(), null),
                        row.years().stream()
                                .map(year -> new LaunchSuccess.Year(
                                        year.year(),
                                        year.attemptsToDate(),
                                        year.successesToDate(),
                                        rate(year.successesToDate(), year.attemptsToDate()),
                                        rate(year.recentSuccesses(), year.recentAttempts())))
                                .toList()))
                .toList();
        return responses.ok(LaunchStatsRepository.SUCCESS_CACHE, new LaunchSuccess(SOURCE, groupBy, groups));
    }

    @GetMapping("/pads")
    @Operation(
            operationId = "getBusiestPads",
            summary = "Busiest launch pads",
            description = "Launch pads ranked by launch attempts, with outcomes, first and latest launch and their"
                    + " busiest year.")
    ResponseEntity<LaunchPads> getBusiestPads(
            @Parameter(description = "Only pads in this ISO 3166-1 alpha-2 country, e.g. JP.")
                    @RequestParam(name = "country", required = false)
                    @Pattern(regexp = "[A-Za-z]{2}")
                    @Nullable
                    String country,
            @Parameter(description = "How many pads, at most 100.")
                    @RequestParam(name = "limit", defaultValue = "10")
                    @Min(1)
                    @Max(100)
                    int limit,
            Locale locale) {
        var lang = Lang.of(locale);
        var items = repository.pads(country, limit).stream()
                .map(row -> new LaunchPads.Item(
                        new LaunchSummary.Pad(
                                row.padId(),
                                row.name(),
                                Lang.EN,
                                row.location(),
                                refs.country(row.countryCode(), row.countryEn(), row.countryJa(), lang),
                                row.latitude(),
                                row.longitude()),
                        row.attempts(),
                        row.successes(),
                        row.failures(),
                        row.scheduled(),
                        row.firstLaunchAt(),
                        row.lastLaunchAt(),
                        row.busiestYear(),
                        row.busiestYearAttempts(),
                        RecordsUrls.launchesFromPad(row.padId())))
                .toList();
        return responses.ok(LaunchStatsRepository.PADS_CACHE, new LaunchPads(SOURCE, items));
    }

    @GetMapping("/reusability")
    @Operation(
            operationId = "getLaunchReusability",
            summary = "First-stage reuse and landings per year",
            description = "For each group and UTC year: launches with a recorded first stage, how many flew a stage"
                    + " that had flown before, stage flights and reflights, and landing attempts and successes."
                    + " Launch Library 2 landings carry no launch link, so each is matched to the launch at its"
                    + " stage's previous flight plus the reported turnaround.")
    ResponseEntity<LaunchReusability> getLaunchReusability(
            @Parameter(description = "How to group launches.") @RequestParam(name = "group_by", defaultValue = "all")
                    LaunchGrouping groupBy,
            @Parameter(description = "Only this group, e.g. spacex for group_by=provider.")
                    @RequestParam(name = "key", required = false)
                    @Size(min = 1, max = 64)
                    @Nullable
                    String key,
            @Parameter(description = "First year, inclusive.")
                    @RequestParam(name = "from_year", required = false)
                    @Min(1957)
                    @Max(2100)
                    @Nullable
                    Integer fromYear,
            @Parameter(description = "Last year, inclusive.")
                    @RequestParam(name = "to_year", required = false)
                    @Min(1957)
                    @Max(2100)
                    @Nullable
                    Integer toYear,
            @Parameter(description = "How many groups, at most 100.")
                    @RequestParam(name = "limit", defaultValue = "10")
                    @Min(1)
                    @Max(100)
                    int limit,
            Locale locale) {
        if (fromYear != null && toYear != null && fromYear > toYear) {
            throw new InvalidParameterException("from_year", "validation.range_order");
        }
        var lang = Lang.of(locale);
        var query = new LaunchStatsRepository.GroupQuery(groupBy, key, fromYear, toYear, limit);
        var series = repository.reusability(query).stream()
                .map(row -> new LaunchReusability.Series(
                        group(groupBy, row.group(), lang),
                        row.totalStageFlights(),
                        RecordsUrls.launches(groupBy, row.group().key(), null),
                        row.years().stream()
                                .map(year -> new LaunchReusability.Year(
                                        year.year(),
                                        year.launches(),
                                        year.launchesReflown(),
                                        rate(year.launchesReflown(), year.launches()),
                                        year.stageFlights(),
                                        year.stageReflights(),
                                        year.landingAttempts(),
                                        year.landings(),
                                        rate(year.landings(), year.landingAttempts()),
                                        RecordsUrls.launches(
                                                groupBy, row.group().key(), year.year())))
                                .toList()))
                .toList();
        return responses.ok(LaunchStatsRepository.REUSABILITY_CACHE, new LaunchReusability(SOURCE, groupBy, series));
    }

    @GetMapping("/boosters")
    @Operation(
            operationId = "getLaunchBoosters",
            summary = "Most flown first stages",
            description = "Identified first stages ranked by flights, with their vehicle, landings, first and latest"
                    + " flight and fastest turnaround. Placeholder stages with no published serial are left out.")
    ResponseEntity<LaunchBoosters> getLaunchBoosters(
            @Parameter(description = "Only stages whose latest launch this provider flew, e.g. spacex.")
                    @RequestParam(name = "provider", required = false)
                    @Size(min = 1, max = 64)
                    @Nullable
                    String provider,
            @Parameter(description = "true for stages still in service, false for the rest.")
                    @RequestParam(name = "active", required = false)
                    @Nullable
                    Boolean active,
            @Parameter(description = "How many stages, at most 100.")
                    @RequestParam(name = "limit", defaultValue = "10")
                    @Min(1)
                    @Max(100)
                    int limit,
            Locale locale) {
        var lang = Lang.of(locale);
        var items = repository.boosters(new LaunchStatsRepository.BoosterQuery(provider, active, limit)).stream()
                .map(row -> new LaunchBoosters.Item(
                        row.launcherId(),
                        row.serialNumber(),
                        vocabulary.fromSource("stage_status", row.status(), lang),
                        vehicle(row, lang),
                        row.rank(),
                        row.flights(),
                        row.attemptedLandings(),
                        row.successfulLandings(),
                        row.firstLaunchAt(),
                        row.lastLaunchAt(),
                        row.fastestTurnaroundDays()))
                .toList();
        return responses.ok(LaunchStatsRepository.BOOSTERS_CACHE, new LaunchBoosters(SOURCE, items));
    }

    private static LaunchSummary.@Nullable Vehicle vehicle(LaunchStatsRepository.BoosterRow row, Lang lang) {
        if (row.vehicleId() == null || row.vehicleName() == null) {
            return null;
        }
        var name = new Bilingual(row.vehicleName(), row.vehicleNameJa()).in(lang);
        return new LaunchSummary.Vehicle(row.vehicleId(), name.value(), name.lang(), row.vehicleFamily(), null);
    }

    private LaunchGroup group(LaunchGrouping kind, LaunchStatsRepository.Named group, Lang lang) {
        if (kind == LaunchGrouping.ALL) {
            return new LaunchGroup(kind, group.key(), vocabulary.message("launch_group.all", lang), lang);
        }
        var name = new Bilingual(group.nameEn() == null ? group.key() : group.nameEn(), group.nameJa()).in(lang);
        return new LaunchGroup(kind, group.key(), name.value(), name.lang());
    }

    static @Nullable Double rate(long part, long whole) {
        return whole == 0 ? null : (double) part / whole;
    }
}
