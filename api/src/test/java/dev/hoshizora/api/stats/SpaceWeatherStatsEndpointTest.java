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
class SpaceWeatherStatsEndpointTest {

    private static final String BASE = "/api/v1/stats/space-weather";

    private final MockMvcTester mvc;

    @Autowired
    SpaceWeatherStatsEndpointTest(MockMvcTester mvc) {
        this.mvc = mvc;
    }

    @Test
    void countsClassifiedFlaresPerMonth() {
        var result = get(BASE + "/flares");

        assertThat(result).hasStatusOk();
        assertConforms(result);
        var json = assertThat(result).bodyJson();
        json.extractingPath("$.from").isEqualTo("2025-11-01");
        json.extractingPath("$.items[0].month").isEqualTo("2026-10-01");
        json.extractingPath("$.items[0].total").isEqualTo(8);
        json.extractingPath("$.items[0].by_class.m").isEqualTo(3);
        json.extractingPath("$.items[0].by_class.b").isEqualTo(2);
        json.extractingPath("$.items[0].strongest_class").isEqualTo("M6.4");
    }

    @Test
    void flareMonthsLinkToExactlyTheirFlares() {
        var json = assertThat(get(BASE + "/flares")).bodyJson();

        json.extractingPath("$.items[0].records_url")
                .isEqualTo(
                        "/api/v1/space-weather/flares?min_class=A&from=2026-10-01T00:00:00Z&to=2026-11-01T00:00:00Z");
        assertThat(get("/api/v1/space-weather/flares?min_class=A&from=2026-10-01T00:00:00Z&to=2026-11-01T00:00:00Z"))
                .bodyJson()
                .extractingPath("$.total_items")
                .isEqualTo(8);
    }

    @Test
    void summarizesKpPerDay() {
        var result = get(BASE + "/kp", "ja");

        assertConforms(result);
        var json = assertThat(result).bodyJson();
        json.extractingPath("$.items[*].day").asArray().containsExactly("2026-10-14", "2026-10-15", "2026-10-16");
        json.extractingPath("$.items[*].intervals").asArray().containsExactly(6, 8, 2);
        json.extractingPath("$.items[1].g_scale.name").isEqualTo("磁気嵐なし");
        json.extractingPath("$.items[1].records_url")
                .isEqualTo("/api/v1/space-weather/kp?from=2026-10-15T00:00:00Z&to=2026-10-16T00:00:00Z");
    }

    @Test
    void rejectsInvalidRanges() {
        assertThat(get(BASE + "/kp?from=2026-10-16&to=2026-10-01")).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(get(BASE + "/kp?from=2000-01-01&to=2026-01-01")).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(get(BASE + "/flares?from=October")).hasStatus(HttpStatus.BAD_REQUEST);
    }

    @Test
    void answersConditionalRequestsWithNotModified() {
        var first = get(BASE + "/kp");

        var again = mvc.get()
                .uri(BASE + "/kp")
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
