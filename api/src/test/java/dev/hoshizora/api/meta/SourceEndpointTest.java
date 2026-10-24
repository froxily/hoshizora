package dev.hoshizora.api.meta;

import static dev.hoshizora.api.support.OpenApiContract.assertConforms;
import static org.assertj.core.api.Assertions.assertThat;

import dev.hoshizora.api.support.ApiTest;
import java.time.Instant;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.test.web.servlet.assertj.MockMvcTester;

@ApiTest
class SourceEndpointTest {

    private static final String SOURCES = "/api/v1/meta/sources";

    private final MockMvcTester mvc;

    @Autowired
    SourceEndpointTest(MockMvcTester mvc) {
        this.mvc = mvc;
    }

    @Test
    void listsEverySourceWithCreditAndLicense() {
        var result = mvc.get().uri(SOURCES).exchange();

        assertThat(result).hasStatusOk();
        assertConforms(result);
        var json = assertThat(result).bodyJson();
        json.extractingPath("$.total_items").isEqualTo(5);
        json.extractingPath("$.items[*].slug")
                .asArray()
                .containsExactly("celestrak", "jpl", "launch-library", "reference", "swpc");
        json.extractingPath("$.items[4].name").isEqualTo("NOAA Space Weather Prediction Center");
        json.extractingPath("$.items[4].credit")
                .isEqualTo("Space weather data: NOAA Space Weather Prediction Center (SWPC)");
        json.extractingPath("$.items[3].license_url").isEqualTo("https://www.unicode.org/license.txt");
    }

    @Test
    void rendersEveryTextInJapanese() {
        var result =
                mvc.get().uri(SOURCES).header(HttpHeaders.ACCEPT_LANGUAGE, "ja").exchange();

        assertConforms(result);
        var json = assertThat(result).bodyJson();
        json.extractingPath("$.items[4].name").isEqualTo("アメリカ海洋大気庁（NOAA）宇宙天気予報センター");
        json.extractingPath("$.items[0].status.freshness.name").isEqualTo("更新遅延");
        json.extractingPath("$.items[0].status.freshness.name_lang").isEqualTo("ja");
        json.extractingPath("$.items[2].status.last_run.name").isEqualTo("取得中");
    }

    @Test
    void judgesFreshnessAgainstTwiceTheInterval() {
        var json = assertThat(mvc.get().uri(SOURCES)).bodyJson();

        json.extractingPath("$.items[*].status.freshness.code")
                .asArray()
                .containsExactly("stale", "fresh", "fresh", "on_demand", "fresh");
        json.extractingPath("$.items[4].status.last_fetched_at").isEqualTo("2026-10-16T07:00:03Z");
    }

    @Test
    void lastFetchIgnoresRejectedRequests() {
        var json = assertThat(mvc.get().uri(SOURCES)).bodyJson();

        json.extractingPath("$.items[2].status.last_fetched_at").isEqualTo("2026-10-16T06:50:30Z");
    }

    @Test
    void freshnessIncludesTheBoundary() {
        var fetched = Instant.parse("2026-10-16T06:00:00Z");

        assertThat(SourceController.freshness(3600L, fetched, Instant.parse("2026-10-16T08:00:00Z")))
                .isEqualTo("fresh");
        assertThat(SourceController.freshness(3600L, fetched, Instant.parse("2026-10-16T08:00:01Z")))
                .isEqualTo("stale");
        assertThat(SourceController.freshness(3600L, null, fetched)).isEqualTo("unknown");
    }

    @Test
    void reportsDataQualityLevels() {
        var json = assertThat(mvc.get().uri(SOURCES)).bodyJson();

        json.extractingPath("$.items[4].quality.level.code").isEqualTo("ok");
        json.extractingPath("$.items[2].quality.blocking").isEqualTo(0);
    }

    @Test
    void paginatesWithTotals() {
        var last = mvc.get().uri(SOURCES + "?page=3&size=2").exchange();
        assertConforms(last);
        assertThat(last).bodyJson().extractingPath("$.items[*].slug").asArray().containsExactly("swpc");
        assertThat(last).bodyJson().extractingPath("$.total_pages").isEqualTo(3);

        var beyond = mvc.get().uri(SOURCES + "?page=4&size=2").exchange();
        assertThat(beyond).bodyJson().extractingPath("$.items").asArray().isEmpty();
        assertThat(beyond).bodyJson().extractingPath("$.total_items").isEqualTo(5);
    }

    @Test
    void rejectsOversizedPagesWithALocalizedProblem() {
        var result = mvc.get()
                .uri(SOURCES + "?size=101")
                .header(HttpHeaders.ACCEPT_LANGUAGE, "ja")
                .exchange();

        assertThat(result).hasStatus(HttpStatus.BAD_REQUEST);
        assertConforms(result);
        var json = assertThat(result).bodyJson();
        json.extractingPath("$.code").isEqualTo("invalid_parameter");
        json.extractingPath("$.errors[0].parameter").isEqualTo("size");
        json.extractingPath("$.errors[0].message").isEqualTo("100以下にしてください。");
    }

    @Test
    void rejectsMalformedNumbers() {
        var result = mvc.get().uri(SOURCES + "?page=first").exchange();

        assertThat(result).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(result).bodyJson().extractingPath("$.errors[0].parameter").isEqualTo("page");
    }

    @Test
    void rejectsPagesBelowOne() {
        assertThat(mvc.get().uri(SOURCES + "?page=0")).hasStatus(HttpStatus.BAD_REQUEST);
    }

    @Test
    void answersConditionalRequestsWithNotModified() {
        var first = mvc.get().uri(SOURCES).exchange();
        var etag = first.getResponse().getHeader(HttpHeaders.ETAG);
        assertThat(etag).startsWith("W/\"");
        assertThat(first).hasHeader(HttpHeaders.CACHE_CONTROL, "max-age=300, public");

        var again =
                mvc.get().uri(SOURCES).header(HttpHeaders.IF_NONE_MATCH, etag).exchange();
        assertThat(again).hasStatus(HttpStatus.NOT_MODIFIED);
    }

    @Test
    void etagsDifferByLanguage() {
        var en = mvc.get().uri(SOURCES).exchange().getResponse().getHeader(HttpHeaders.ETAG);
        var ja = mvc.get()
                .uri(SOURCES)
                .header(HttpHeaders.ACCEPT_LANGUAGE, "ja")
                .exchange()
                .getResponse()
                .getHeader(HttpHeaders.ETAG);

        assertThat(ja).isNotEqualTo(en);
    }

    @Test
    void rejectsWrites() {
        var result = mvc.post().uri(SOURCES).exchange();

        assertThat(result).hasStatus(HttpStatus.METHOD_NOT_ALLOWED);
        assertThat(result).bodyJson().extractingPath("$.code").isEqualTo("method_not_allowed");
    }
}
