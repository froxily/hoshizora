package dev.hoshizora.api.neo;

import static dev.hoshizora.api.support.OpenApiContract.assertConforms;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

import dev.hoshizora.api.support.ApiTest;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.test.web.servlet.assertj.MockMvcTester;
import org.springframework.test.web.servlet.assertj.MvcTestResult;

@ApiTest
class CloseApproachEndpointTest {

    private static final String APPROACHES = "/api/v1/close-approaches";

    private final MockMvcTester mvc;

    @Autowired
    CloseApproachEndpointTest(MockMvcTester mvc) {
        this.mvc = mvc;
    }

    @Test
    void listsSoonestFirstFromTheEarliestRecord() {
        var result = get(APPROACHES);

        assertThat(result).hasStatusOk();
        assertConforms(result);
        var json = assertThat(result).bodyJson();
        json.extractingPath("$.total_items").isEqualTo(18);
        json.extractingPath("$.items[0].designation").isEqualTo("2019 CD2");
        json.doesNotHavePath("$.items[0].approach_utc");
    }

    @Test
    void filtersByTdbDateWindow() {
        assertThat(get(APPROACHES + "?from=2026-10-01&to=2026-11-01"))
                .bodyJson()
                .extractingPath("$.total_items")
                .isEqualTo(10);
    }

    @Test
    void sortsByDistance() {
        assertThat(get(APPROACHES + "?sort=distance"))
                .bodyJson()
                .extractingPath("$.items[0].designation")
                .isEqualTo("2026 RT34");
        assertThat(get(APPROACHES + "?sort=-date"))
                .bodyJson()
                .extractingPath("$.items[0].approach_tdb")
                .isEqualTo("2187-03-08T23:09:00");
    }

    @Test
    void filtersByLunarDistanceSizeObjectAndSentry() {
        assertThat(get(APPROACHES + "?max_dist_ld=1"))
                .bodyJson()
                .extractingPath("$.total_items")
                .isEqualTo(11);
        assertThat(get(APPROACHES + "?max_h=20"))
                .bodyJson()
                .extractingPath("$.total_items")
                .isEqualTo(3);
        assertThat(get(APPROACHES + "?designation=29075"))
                .bodyJson()
                .extractingPath("$.total_items")
                .isEqualTo(3);
        assertThat(get(APPROACHES + "?sentry=true"))
                .bodyJson()
                .extractingPath("$.items[*].designation")
                .asArray()
                .containsOnly("29075");
    }

    @Test
    void convertsTdbToUtcAndEstimatesSize() {
        var result = get(APPROACHES + "?designation=2026 TS", "ja");

        assertConforms(result);
        var json = assertThat(result).bodyJson();
        json.extractingPath("$.items[0].approach_tdb").isEqualTo("2026-10-18T06:16:00");
        json.extractingPath("$.items[0].approach_utc").isEqualTo("2026-10-18T06:14:50.816Z");
        json.extractingPath("$.items[0].body.name").isEqualTo("地球");
        json.extractingPath("$.items[0].size.estimated_min_km")
                .asNumber()
                .satisfies(km -> assertThat(km.doubleValue()).isCloseTo(0.0412, within(0.0005)));
        json.extractingPath("$.items[0].size.estimated_max_km")
                .asNumber()
                .satisfies(km -> assertThat(km.doubleValue()).isCloseTo(0.0922, within(0.0005)));
        json.extractingPath("$.items[0].size.assumed_albedo_min").isEqualTo(0.05);
        json.extractingPath("$.items[0].dist_ld")
                .asNumber()
                .satisfies(ld -> assertThat(ld.doubleValue()).isCloseTo(2.359, within(0.001)));
    }

    @Test
    void parsesJplTimeUncertainty() {
        assertThat(CloseApproachViews.timeUncertainty("< 00:01")).isEqualTo(new CloseApproach.TimeUncertainty(1, true));
        assertThat(CloseApproachViews.timeUncertainty("4_11:16"))
                .isEqualTo(new CloseApproach.TimeUncertainty(6436, false));
        assertThat(CloseApproachViews.timeUncertainty(null)).isNull();
    }

    @Test
    void rejectsReversedRangesInJapanese() {
        var result = get(APPROACHES + "?from=2026-11-01&to=2026-10-01", "ja");

        assertThat(result).hasStatus(HttpStatus.BAD_REQUEST);
        assertConforms(result);
        assertThat(result).bodyJson().extractingPath("$.errors[0].parameter").isEqualTo("from");
        assertThat(result).bodyJson().extractingPath("$.errors[0].message").isEqualTo("from は to より前の日時にしてください。");
    }

    @Test
    void rejectsInvalidParameters() {
        assertThat(get(APPROACHES + "?max_dist_ld=0")).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(get(APPROACHES + "?from=yesterday")).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(get(APPROACHES + "?sort=size")).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(get(APPROACHES + "?size=0")).hasStatus(HttpStatus.BAD_REQUEST);
    }

    @Test
    void paginatesToTheLastPage() {
        assertThat(get(APPROACHES + "?page=2&size=10"))
                .bodyJson()
                .extractingPath("$.items")
                .asArray()
                .hasSize(8);
        assertThat(get(APPROACHES + "?page=3&size=10"))
                .bodyJson()
                .extractingPath("$.items")
                .asArray()
                .isEmpty();
    }

    @Test
    void answersConditionalRequestsWithNotModified() {
        var first = get(APPROACHES);
        assertThat(first).hasHeader(HttpHeaders.CACHE_CONTROL, "max-age=43200, public");

        var again = mvc.get()
                .uri(APPROACHES)
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
