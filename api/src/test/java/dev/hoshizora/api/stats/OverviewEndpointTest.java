package dev.hoshizora.api.stats;

import static dev.hoshizora.api.support.OpenApiContract.assertConforms;
import static org.assertj.core.api.Assertions.assertThat;

import com.jayway.jsonpath.JsonPath;
import dev.hoshizora.api.support.ApiTest;
import java.io.UnsupportedEncodingException;
import java.nio.charset.StandardCharsets;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.test.web.servlet.assertj.MockMvcTester;

@ApiTest
class OverviewEndpointTest {

    private static final String OVERVIEW = "/api/v1/stats/overview";

    private final MockMvcTester mvc;

    @Autowired
    OverviewEndpointTest(MockMvcTester mvc) {
        this.mvc = mvc;
    }

    @Test
    void summarizesTheHomeTicker() {
        var result = mvc.get().uri(OVERVIEW).exchange();

        assertThat(result).hasStatusOk();
        assertConforms(result);
        var json = assertThat(result).bodyJson();
        json.extractingPath("$.as_of").isEqualTo("2026-10-16T08:00:00Z");
        json.extractingPath("$.next_launch.name").isEqualTo("SLS Block 1B | Artemis VI");
        json.extractingPath("$.launches_this_year.year").isEqualTo(2026);
        json.extractingPath("$.launches_this_year.records_url")
                .isEqualTo("/api/v1/launches?from=2026-01-01T00:00:00Z&to=2026-10-16T08:00:00Z");
        json.extractingPath("$.kp.observed_at").isEqualTo("2026-10-16T03:00:00Z");
        json.extractingPath("$.closest_approach_this_week.designation").isEqualTo("2026 TS");
    }

    @Test
    void agreesWithTheOrbitStatistics() throws UnsupportedEncodingException {
        var overview = mvc.get().uri(OVERVIEW).exchange().getResponse().getContentAsString(StandardCharsets.UTF_8);
        var orbits = mvc.get()
                .uri("/api/v1/stats/orbits/countries")
                .exchange()
                .getResponse()
                .getContentAsString(StandardCharsets.UTF_8);

        assertThat(JsonPath.<Integer>read(overview, "$.objects_in_earth_orbit.total"))
                .isEqualTo(JsonPath.<Integer>read(orbits, "$.totals.total"));
        assertThat(JsonPath.<Integer>read(overview, "$.objects_in_earth_orbit.payloads"))
                .isEqualTo(JsonPath.<Integer>read(orbits, "$.totals.payloads"));
    }

    @Test
    void localizesInJapanese() {
        var result = mvc.get()
                .uri(OVERVIEW)
                .header(HttpHeaders.ACCEPT_LANGUAGE, "ja")
                .exchange();

        assertConforms(result);
        var json = assertThat(result).bodyJson();
        json.extractingPath("$.kp.g_scale.name").isEqualTo("磁気嵐なし");
        json.extractingPath("$.closest_approach_this_week.body.name").isEqualTo("地球");
        json.extractingPath("$.next_launch.provider.name").isEqualTo("アメリカ航空宇宙局");
    }

    @Test
    void answersConditionalRequestsWithNotModified() {
        var first = mvc.get().uri(OVERVIEW).exchange();

        var again = mvc.get()
                .uri(OVERVIEW)
                .header(HttpHeaders.IF_NONE_MATCH, first.getResponse().getHeader(HttpHeaders.ETAG))
                .exchange();

        assertThat(again).hasStatus(HttpStatus.NOT_MODIFIED);
    }
}
