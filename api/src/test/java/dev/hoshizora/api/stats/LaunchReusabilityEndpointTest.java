package dev.hoshizora.api.stats;

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
class LaunchReusabilityEndpointTest {

    private static final String BASE = "/api/v1/stats/launches";

    private final MockMvcTester mvc;

    @Autowired
    LaunchReusabilityEndpointTest(MockMvcTester mvc) {
        this.mvc = mvc;
    }

    @Test
    void reusabilityCountsReflightsAndLandingsPerYear() {
        var result = get(BASE + "/reusability");

        assertThat(result).hasStatusOk();
        assertConforms(result);
        var json = assertThat(result).bodyJson();
        json.extractingPath("$.source").isEqualTo("launch-library");
        json.extractingPath("$.group_by").isEqualTo("all");
        json.extractingPath("$.groups[0].total_stage_flights").isEqualTo(4);
        json.extractingPath("$.groups[0].years[*].year").asArray().containsExactly(2024, 2025);
        json.extractingPath("$.groups[0].years[1].launches").isEqualTo(3);
        json.extractingPath("$.groups[0].years[1].launches_reflown").isEqualTo(2);
        json.extractingPath("$.groups[0].years[1].stage_reflights").isEqualTo(2);
        json.extractingPath("$.groups[0].years[1].landing_attempts").isEqualTo(2);
        json.extractingPath("$.groups[0].years[1].landings").isEqualTo(1);
        json.extractingPath("$.groups[0].years[1].landing_success_rate").isEqualTo(0.5);
        json.extractingPath("$.groups[0].years[0].reflown_share").isEqualTo(0.0);
    }

    @Test
    void reusabilityFiltersByGroupAndYearAndLinksToLaunches() {
        var json = assertThat(get(BASE + "/reusability?group_by=provider&key=spacex&from_year=2025", "ja"))
                .bodyJson();

        json.extractingPath("$.groups[0].group.name").isEqualTo("スペースX");
        json.extractingPath("$.groups[0].years").asArray().hasSize(1);
        json.extractingPath("$.groups[0].years[0].records_url")
                .isEqualTo("/api/v1/launches?provider=spacex&from=2025-01-01T00:00:00Z&to=2026-01-01T00:00:00Z");
        assertThat(get(BASE + "/reusability?group_by=program&key=japan"))
                .bodyJson()
                .extractingPath("$.groups")
                .asArray()
                .isEmpty();
    }

    @Test
    void boostersRankByFlightsWithoutPlaceholders() {
        var result = get(BASE + "/boosters", "ja");

        assertThat(result).hasStatusOk();
        assertConforms(result);
        var json = assertThat(result).bodyJson();
        json.extractingPath("$.items[*].serial_number").asArray().containsExactly("B1067", "B1080");
        json.extractingPath("$.items[0].rank").isEqualTo(1);
        json.extractingPath("$.items[0].flights").isEqualTo(3);
        json.extractingPath("$.items[0].status.name").isEqualTo("運用中");
        json.extractingPath("$.items[0].vehicle.name").isEqualTo("ファルコン9 ブロック5");
        json.extractingPath("$.items[0].fastest_turnaround_days").isEqualTo(92.08333333333333);
        json.extractingPath("$.items[1].status.code").isEqualTo("expended");
    }

    @Test
    void boostersFilterByProviderAndService() {
        assertThat(get(BASE + "/boosters?active=true"))
                .bodyJson()
                .extractingPath("$.items[*].serial_number")
                .asArray()
                .containsExactly("B1067");
        assertThat(get(BASE + "/boosters?provider=spacex&limit=1"))
                .bodyJson()
                .extractingPath("$.items")
                .asArray()
                .hasSize(1);
        assertThat(get(BASE + "/boosters?provider=jaxa"))
                .bodyJson()
                .extractingPath("$.items")
                .asArray()
                .isEmpty();
    }

    @Test
    void rejectsInvalidParameters() {
        assertThat(get(BASE + "/reusability?group_by=planet")).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(get(BASE + "/reusability?from_year=2026&to_year=2020")).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(get(BASE + "/boosters?limit=101")).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(get(BASE + "/boosters?active=maybe")).hasStatus(HttpStatus.BAD_REQUEST);
    }

    @Test
    void answersConditionalRequestsWithNotModified() {
        var first = get(BASE + "/boosters");

        var again = mvc.get()
                .uri(BASE + "/boosters")
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
