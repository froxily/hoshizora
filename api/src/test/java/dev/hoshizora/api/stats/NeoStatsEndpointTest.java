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
class NeoStatsEndpointTest {

    private static final String MONTHLY = "/api/v1/stats/close-approaches/monthly";

    private final MockMvcTester mvc;

    @Autowired
    NeoStatsEndpointTest(MockMvcTester mvc) {
        this.mvc = mvc;
    }

    @Test
    void defaultsToTenYearsBackAndTwoAhead() {
        var result = get(MONTHLY);

        assertThat(result).hasStatusOk();
        assertConforms(result);
        var json = assertThat(result).bodyJson();
        json.extractingPath("$.from").isEqualTo("2016-01-01");
        json.extractingPath("$.to").isEqualTo("2029-01-01");
        json.extractingPath("$.items[*].month").asArray().containsExactly("2026-09-01", "2026-10-01");
        json.extractingPath("$.items[1].approaches").isEqualTo(10);
        json.extractingPath("$.items[1].within_lunar_distance").isEqualTo(6);
        json.extractingPath("$.items[1].closest_designation").isEqualTo("2026 TN77");
        json.extractingPath("$.items[1].predicted").isEqualTo(false);
    }

    @Test
    void linksEachMonthToItsApproachesClosestFirst() {
        var json = assertThat(get(MONTHLY)).bodyJson();

        json.extractingPath("$.items[1].records_url")
                .isEqualTo("/api/v1/close-approaches?from=2026-10-01&to=2026-11-01&sort=distance");
        assertThat(get("/api/v1/close-approaches?from=2026-10-01&to=2026-11-01&sort=distance"))
                .bodyJson()
                .extractingPath("$.items[0].designation")
                .isEqualTo("2026 TN77");
    }

    @Test
    void marksFutureMonthsAsPredicted() {
        var json = assertThat(get(MONTHLY + "?from=2100-01-01&to=2200-01-01")).bodyJson();

        json.extractingPath("$.items").asArray().hasSize(3);
        json.extractingPath("$.items[*].predicted").asArray().containsOnly(true);
    }

    @Test
    void coversTheWholeCatalogueInOneRange() {
        assertThat(get(MONTHLY + "?from=1900-01-01&to=2201-01-01"))
                .bodyJson()
                .extractingPath("$.items")
                .asArray()
                .hasSize(7);
    }

    @Test
    void rejectsInvalidRanges() {
        assertThat(get(MONTHLY + "?from=2027-01-01&to=2026-01-01")).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(get(MONTHLY + "?from=1500-01-01&to=2201-01-01")).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(get(MONTHLY + "?from=2026-13-01")).hasStatus(HttpStatus.BAD_REQUEST);
    }

    @Test
    void answersConditionalRequestsWithNotModified() {
        var first = get(MONTHLY);

        var again = mvc.get()
                .uri(MONTHLY)
                .header(HttpHeaders.IF_NONE_MATCH, first.getResponse().getHeader(HttpHeaders.ETAG))
                .exchange();

        assertThat(again).hasStatus(HttpStatus.NOT_MODIFIED);
    }

    private MvcTestResult get(String uri) {
        return mvc.get().uri(uri).exchange();
    }
}
