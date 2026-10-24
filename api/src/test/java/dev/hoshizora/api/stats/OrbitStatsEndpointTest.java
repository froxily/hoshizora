package dev.hoshizora.api.stats;

import static dev.hoshizora.api.support.OpenApiContract.assertConforms;
import static org.assertj.core.api.Assertions.assertThat;

import com.jayway.jsonpath.JsonPath;
import dev.hoshizora.api.support.ApiTest;
import java.io.UnsupportedEncodingException;
import java.nio.charset.StandardCharsets;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.test.web.servlet.assertj.MockMvcTester;
import org.springframework.test.web.servlet.assertj.MvcTestResult;

@ApiTest
class OrbitStatsEndpointTest {

    private static final String COUNTRIES = "/api/v1/stats/orbits/countries";

    private final MockMvcTester mvc;

    @Autowired
    OrbitStatsEndpointTest(MockMvcTester mvc) {
        this.mvc = mvc;
    }

    @Test
    void countsObjectsInEarthOrbitByCountry() throws UnsupportedEncodingException {
        var result = get(COUNTRIES);

        assertThat(result).hasStatusOk();
        assertConforms(result);
        var body = body(result);
        List<Integer> totals = JsonPath.read(body, "$.countries[*].counts.total");
        assertThat(totals).isSortedAccordingTo((a, b) -> b - a);
        int total = JsonPath.read(body, "$.totals.total");
        int payloads = JsonPath.read(body, "$.totals.payloads");
        int rocketBodies = JsonPath.read(body, "$.totals.rocket_bodies");
        int debris = JsonPath.read(body, "$.totals.debris");
        int unknown = JsonPath.read(body, "$.totals.unknown");
        assertThat(total)
                .isEqualTo(payloads + rocketBodies + debris + unknown)
                .isGreaterThanOrEqualTo(totals.getFirst());
        assertThat(JsonPath.<List<String>>read(body, "$.countries[*].country.code"))
                .contains("JP", "US", "CN");
    }

    @Test
    void countsJointOwnersForEachCountryAndFlagsThem() throws UnsupportedEncodingException {
        var body = body(get(COUNTRIES));

        List<Integer> brazilShared = JsonPath.read(body, "$.countries[?(@.country.code == 'BR')].shared");
        assertThat(brazilShared)
                .isNotEmpty()
                .allSatisfy(shared -> assertThat(shared).isPositive());
    }

    @Test
    void listsOrganizationOwnersSeparately() {
        var result = get(COUNTRIES, "ja");

        assertConforms(result);
        var json = assertThat(result).bodyJson();
        json.extractingPath("$.organizations[?(@.owner_code == 'ESA')].organization.key")
                .asArray()
                .containsExactly("esa");
        json.extractingPath("$.organizations[?(@.owner_code == 'ESA')].organization.name")
                .asArray()
                .containsExactly("欧州宇宙機関");
        json.extractingPath("$.orbit_state.name").isEqualTo("地球周回中");
        json.extractingPath("$.countries[?(@.country.code == 'JP')].country.name")
                .asArray()
                .containsExactly("日本");
    }

    @Test
    void reportsDecayedObjectsToo() {
        var result = get(COUNTRIES + "?orbit_state=decayed");

        assertConforms(result);
        assertThat(result).bodyJson().extractingPath("$.orbit_state.code").isEqualTo("decayed");
        assertThat(result)
                .bodyJson()
                .extractingPath("$.totals.total")
                .asNumber()
                .isNotEqualTo(0);
    }

    @Test
    void limitsTheRows() {
        assertThat(get(COUNTRIES + "?limit=2"))
                .bodyJson()
                .extractingPath("$.countries")
                .asArray()
                .hasSize(2);
    }

    @Test
    void rejectsInvalidParameters() {
        assertThat(get(COUNTRIES + "?orbit_state=lunar")).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(get(COUNTRIES + "?limit=301")).hasStatus(HttpStatus.BAD_REQUEST);
    }

    @Test
    void answersConditionalRequestsWithNotModified() {
        var first = get(COUNTRIES);
        assertThat(first).hasHeader(HttpHeaders.CACHE_CONTROL, "max-age=43200, public");

        var again = mvc.get()
                .uri(COUNTRIES)
                .header(HttpHeaders.IF_NONE_MATCH, first.getResponse().getHeader(HttpHeaders.ETAG))
                .exchange();

        assertThat(again).hasStatus(HttpStatus.NOT_MODIFIED);
    }

    private static String body(MvcTestResult result) throws UnsupportedEncodingException {
        return result.getResponse().getContentAsString(StandardCharsets.UTF_8);
    }

    private MvcTestResult get(String uri) {
        return mvc.get().uri(uri).exchange();
    }

    private MvcTestResult get(String uri, String language) {
        return mvc.get().uri(uri).header(HttpHeaders.ACCEPT_LANGUAGE, language).exchange();
    }
}
