package dev.hoshizora.api.stats;

import dev.hoshizora.api.i18n.Lang;
import dev.hoshizora.api.i18n.Vocabulary;
import dev.hoshizora.api.launches.LaunchViews;
import dev.hoshizora.api.neo.CloseApproachViews;
import dev.hoshizora.api.spaceweather.Kp;
import dev.hoshizora.api.web.Responses;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import java.time.Clock;
import java.time.ZoneOffset;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.Locale;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.util.UriComponentsBuilder;

@RestController
@RequestMapping("/api/v1/stats")
@Tag(name = "Statistics")
class OverviewController {

    private final OverviewRepository repository;
    private final LaunchViews launches;
    private final CloseApproachViews approaches;
    private final Vocabulary vocabulary;
    private final Responses responses;
    private final Clock clock;

    OverviewController(
            OverviewRepository repository,
            LaunchViews launches,
            CloseApproachViews approaches,
            Vocabulary vocabulary,
            Responses responses,
            Clock clock) {
        this.repository = repository;
        this.launches = launches;
        this.approaches = approaches;
        this.vocabulary = vocabulary;
        this.responses = responses;
        this.clock = clock;
    }

    @GetMapping("/overview")
    @Operation(
            operationId = "getOverview",
            summary = "Home overview",
            description = "The numbers for the home ticker, as of the start of the current UTC hour: the next"
                    + " scheduled launch, launch attempts this year against the same span of last year, the latest"
                    + " Kp, the closest asteroid approach in the coming week, and objects in Earth orbit.")
    ResponseEntity<Overview> getOverview(Locale locale) {
        var lang = Lang.of(locale);
        var asOf = clock.instant().truncatedTo(ChronoUnit.HOURS);
        var snapshot = repository.snapshot(asOf);
        var year = asOf.atZone(ZoneOffset.UTC).getYear();
        var yearLaunches = UriComponentsBuilder.fromPath("/api/v1/launches")
                .queryParam(
                        "from",
                        asOf.atZone(ZoneOffset.UTC)
                                .withDayOfYear(1)
                                .truncatedTo(ChronoUnit.DAYS)
                                .toInstant())
                .queryParam("to", asOf)
                .build()
                .toUriString();
        return responses.ok(
                OverviewRepository.CACHE,
                new Overview(
                        asOf,
                        snapshot.nextLaunch() == null ? null : launches.summary(snapshot.nextLaunch(), lang),
                        new Overview.LaunchYear(
                                year, snapshot.launchesThisYear(), snapshot.launchesSamePeriodLastYear(), yearLaunches),
                        snapshot.kpObservedAt() == null
                                ? null
                                : new Kp.Reading(
                                        snapshot.kpObservedAt(),
                                        snapshot.kp(),
                                        vocabulary.term("g_scale", "g" + snapshot.gScale(), lang)),
                        snapshot.closestApproach() == null ? null : approaches.view(snapshot.closestApproach(), lang),
                        new Overview.OrbitCount(
                                snapshot.objectsInEarthOrbit(),
                                snapshot.payloadsInEarthOrbit(),
                                "/api/v1/stats/orbits/countries"),
                        List.of("launch-library", "swpc", "jpl", "celestrak")));
    }
}
