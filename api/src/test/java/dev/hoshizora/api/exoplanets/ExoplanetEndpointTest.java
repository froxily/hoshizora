package dev.hoshizora.api.exoplanets;

import static dev.hoshizora.api.support.OpenApiContract.assertConforms;
import static org.assertj.core.api.Assertions.assertThat;

import dev.hoshizora.api.support.ApiTest;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.test.web.servlet.assertj.MockMvcTester;
import org.springframework.test.web.servlet.assertj.MvcTestResult;

@ApiTest
class ExoplanetEndpointTest {

    private static final String PLANETS = "/api/v1/exoplanets";
    private static final String STATS = "/api/v1/stats/exoplanets";

    private final MockMvcTester mvc;

    @Autowired
    ExoplanetEndpointTest(MockMvcTester mvc) {
        this.mvc = mvc;
    }

    @Test
    void listsNearestFirstWithoutQuestionedPlanets() {
        var result = get(PLANETS);

        assertThat(result).hasStatusOk();
        assertConforms(result);
        var json = assertThat(result).bodyJson();
        json.extractingPath("$.total_items").isEqualTo(4);
        json.extractingPath("$.items[*].name")
                .asArray()
                .containsExactly("Proxima Cen b", "TRAPPIST-1 e", "HAT-P-47 b", "OGLE-2016-BLG-1227L b");
        json.extractingPath("$.items[0].distance_ly").isEqualTo(4.2439092564);
        json.extractingPath("$.items[0].discovery.method.code").isEqualTo("radial_velocity");
    }

    @Test
    void filtersByMethodYearDistanceAndConfirmation() {
        assertThat(get(PLANETS + "?include_controversial=true"))
                .bodyJson()
                .extractingPath("$.total_items")
                .isEqualTo(6);
        assertThat(get(PLANETS + "?method=transit"))
                .bodyJson()
                .extractingPath("$.items[*].name")
                .asArray()
                .containsExactly("TRAPPIST-1 e", "HAT-P-47 b");
        assertThat(get(PLANETS + "?from_year=2016&to_year=2017"))
                .bodyJson()
                .extractingPath("$.total_items")
                .isEqualTo(2);
        assertThat(get(PLANETS + "?max_distance_ly=50"))
                .bodyJson()
                .extractingPath("$.items[*].name")
                .asArray()
                .containsExactly("Proxima Cen b", "TRAPPIST-1 e");
        assertThat(get(PLANETS + "?sort=-discovery_year&size=1"))
                .bodyJson()
                .extractingPath("$.items[0].name")
                .isEqualTo("HAT-P-47 b");
    }

    @Test
    void namesMethodsInJapanese() {
        assertThat(get(PLANETS + "?method=microlensing", "ja"))
                .bodyJson()
                .extractingPath("$.items[0].discovery.method.name")
                .isEqualTo("重力マイクロレンズ法");
    }

    @Test
    void showsOnePlanetWithItsLineage() {
        var result = get(PLANETS + "/Proxima Cen b");

        assertThat(result).hasStatusOk();
        assertConforms(result);
        var json = assertThat(result).bodyJson();
        json.extractingPath("$.planet.star.planet_count").isEqualTo(2);
        json.extractingPath("$.lineage[0].source").isEqualTo("exoplanet-archive");
        assertThat(get(PLANETS + "/Kepler-452 b"))
                .bodyJson()
                .extractingPath("$.planet.controversial")
                .isEqualTo(true);
        assertThat(get(PLANETS + "/Planet Nine")).hasStatus(HttpStatus.NOT_FOUND);
    }

    @Test
    void countsDiscoveriesPerYearAndMethod() {
        var result = get(STATS + "/discoveries");

        assertThat(result).hasStatusOk();
        assertConforms(result);
        var json = assertThat(result).bodyJson();
        json.extractingPath("$.methods[*].method.code")
                .asArray()
                .containsExactly("transit", "radial_velocity", "microlensing");
        json.extractingPath("$.methods[0].planets").isEqualTo(3);
        json.extractingPath("$.years[*].year").asArray().containsExactly(2013, 2015, 2016, 2017, 2020, 2026);
        json.extractingPath("$.years[1].from_space").isEqualTo(1);
        json.extractingPath("$.years[1].records_url").isEqualTo(PLANETS + "?from_year=2015&to_year=2015");
        assertThat(get(STATS + "/discoveries?from_year=2017&to_year=2020"))
                .bodyJson()
                .extractingPath("$.years")
                .asArray()
                .hasSize(2);
    }

    @Test
    void binsTransitingPlanetsBySizeAndOrbit() {
        var result = get(STATS + "/size-orbit");

        assertThat(result).hasStatusOk();
        assertConforms(result);
        var json = assertThat(result).bodyJson();
        json.extractingPath("$.planets").isEqualTo(3);
        json.extractingPath("$.cells").asArray().hasSize(3);
        json.extractingPath("$.cells[1].period_min_days").isEqualTo(5.623413251903491);
        json.extractingPath("$.cells[1].radius_max_earth").isEqualTo(1.0);
    }

    @Test
    void rejectsInvalidParameters() {
        assertThat(get(PLANETS + "?method=Transit!")).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(get(PLANETS + "?sort=mass")).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(get(PLANETS + "?max_distance_ly=0")).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(get(STATS + "/discoveries?from_year=2020&to_year=2010")).hasStatus(HttpStatus.BAD_REQUEST);
    }

    @Test
    void answersConditionalRequestsWithNotModified() {
        var first = get(STATS + "/size-orbit");

        var again = mvc.get()
                .uri(STATS + "/size-orbit")
                .header(HttpHeaders.IF_NONE_MATCH, first.getResponse().getHeader(HttpHeaders.ETAG))
                .exchange();

        assertThat(again).hasStatus(HttpStatus.NOT_MODIFIED);
    }

    private MvcTestResult get(String uri) {
        return mvc.get().uri(uri).exchange();
    }

    private MvcTestResult get(String uri, String language) {
        return mvc.get().uri(uri).header(HttpHeaders.ACCEPT_LANGUAGE, language).exchange();
    }
}
