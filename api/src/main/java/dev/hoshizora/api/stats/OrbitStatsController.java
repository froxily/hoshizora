package dev.hoshizora.api.stats;

import dev.hoshizora.api.common.CountryRef;
import dev.hoshizora.api.common.Refs;
import dev.hoshizora.api.i18n.Lang;
import dev.hoshizora.api.i18n.Vocabulary;
import dev.hoshizora.api.web.Responses;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import java.util.Locale;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/stats/orbits")
@Tag(name = "Statistics")
class OrbitStatsController {

    private final OrbitStatsRepository repository;
    private final Vocabulary vocabulary;
    private final Refs refs;
    private final Responses responses;

    OrbitStatsController(OrbitStatsRepository repository, Vocabulary vocabulary, Refs refs, Responses responses) {
        this.repository = repository;
        this.vocabulary = vocabulary;
        this.refs = refs;
        this.responses = responses;
    }

    @GetMapping("/countries")
    @Operation(
            operationId = "getObjectsInOrbit",
            summary = "Objects in orbit by country",
            description = "Catalogued payloads, rocket bodies and debris per owner country and per owning"
                    + " organization. SATCAT owner codes are countries or organizations, not agencies: a US object"
                    + " may be NASA's, the military's or a company's.")
    ResponseEntity<ObjectsInOrbit> getObjectsInOrbit(
            @Parameter(description = "earth_orbit (default), beyond_earth or decayed.")
                    @RequestParam(name = "orbit_state", defaultValue = "earth_orbit")
                    OrbitState orbitState,
            @Parameter(description = "How many countries and organizations, at most 300.")
                    @RequestParam(name = "limit", defaultValue = "20")
                    @Min(1)
                    @Max(300)
                    int limit,
            Locale locale) {
        var lang = Lang.of(locale);
        var snapshot = repository.snapshot(orbitState, limit);
        return responses.ok(
                OrbitStatsRepository.CACHE,
                new ObjectsInOrbit(
                        "celestrak",
                        vocabulary.term("orbit_state", orbitState.value(), lang),
                        snapshot.totals(),
                        snapshot.countries().stream()
                                .map(country -> new ObjectsInOrbit.CountryRow(
                                        new CountryRef(
                                                country.code(),
                                                country.name().in(lang).value()),
                                        country.counts(),
                                        country.shared()))
                                .toList(),
                        snapshot.owners().stream()
                                .map(owner -> new ObjectsInOrbit.OrganizationRow(
                                        owner.ownerCode(),
                                        owner.label(),
                                        Lang.EN,
                                        owner.organization() == null
                                                ? null
                                                : refs.organization(owner.organization(), lang),
                                        owner.counts()))
                                .toList()));
    }
}
