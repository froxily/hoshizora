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
class LaunchStatsEndpointTest {

    private static final String BASE = "/api/v1/stats/launches";

    private final MockMvcTester mvc;

    @Autowired
    LaunchStatsEndpointTest(MockMvcTester mvc) {
        this.mvc = mvc;
    }

    @Test
    void cadenceRanksProgramsByAttempts() {
        var result = get(BASE + "/cadence");

        assertThat(result).hasStatusOk();
        assertConforms(result);
        var json = assertThat(result).bodyJson();
        json.extractingPath("$.source").isEqualTo("launch-library");
        json.extractingPath("$.groups[*].group.key")
                .asArray()
                .containsExactly("japan", "europe", "usa", "china", "india", "russia");
        json.extractingPath("$.groups[0].total_attempts").isEqualTo(12);
        json.extractingPath("$.groups[0].years[?(@.year == 2017)].attempts")
                .asArray()
                .containsExactly(6);
        json.extractingPath("$.groups[2].years[?(@.year == 2030)].scheduled")
                .asArray()
                .containsExactly(1);
    }

    @Test
    void cadenceLinksEveryCountToItsLaunches() {
        var json = assertThat(get(BASE + "/cadence?key=japan&from_year=2017&to_year=2017"))
                .bodyJson();

        json.extractingPath("$.groups[0].total_attempts").isEqualTo(6);
        json.extractingPath("$.groups[0].years[0].records_url")
                .isEqualTo("/api/v1/launches?program=japan&from=2017-01-01T00:00:00Z&to=2018-01-01T00:00:00Z");
        assertThat(get("/api/v1/launches?program=japan&from=2017-01-01T00:00:00Z&to=2018-01-01T00:00:00Z"))
                .bodyJson()
                .extractingPath("$.total_items")
                .isEqualTo(6);
    }

    @Test
    void cadenceNamesGroupsInJapanese() {
        var result = get(BASE + "/cadence?group_by=all", "ja");

        assertConforms(result);
        var json = assertThat(result).bodyJson();
        json.extractingPath("$.groups[0].group.name").isEqualTo("すべての打ち上げ");
        json.extractingPath("$.groups[0].records_url").isEqualTo("/api/v1/launches");
        assertThat(get(BASE + "/cadence?group_by=program&key=japan", "ja"))
                .bodyJson()
                .extractingPath("$.groups[0].group.name")
                .isEqualTo("日本");
        assertThat(get(BASE + "/cadence?group_by=vehicle_family&key=H-II", "ja"))
                .bodyJson()
                .extractingPath("$.groups[0].group.name_lang")
                .isEqualTo("en");
    }

    @Test
    void successTracksRatesAndStreaks() {
        var result = get(BASE + "/success?key=japan");

        assertConforms(result);
        var json = assertThat(result).bodyJson();
        json.extractingPath("$.groups[0].attempts").isEqualTo(12);
        json.extractingPath("$.groups[0].successes").isEqualTo(11);
        json.extractingPath("$.groups[0].current_streak").isEqualTo(10);
        json.extractingPath("$.groups[0].longest_streak").isEqualTo(10);
        json.extractingPath("$.groups[0].years[0].year").isEqualTo(2016);
        json.extractingPath("$.groups[0].years[1].attempts_to_date").isEqualTo(7);
        json.extractingPath("$.groups[0].years[1].successes_to_date").isEqualTo(6);
    }

    @Test
    void successGroupsByProvider() {
        var json = assertThat(get(BASE + "/success?group_by=provider&key=mhi")).bodyJson();

        json.extractingPath("$.groups[0].success_rate").isEqualTo(1.0);
        json.extractingPath("$.groups[0].records_url").isEqualTo("/api/v1/launches?provider=mhi");
    }

    @Test
    void padsRankByAttemptsAndLinkToTheirLaunches() {
        var result = get(BASE + "/pads?country=jp", "ja");

        assertConforms(result);
        var json = assertThat(result).bodyJson();
        json.extractingPath("$.items[0].pad.name").isEqualTo("Yoshinobu Launch Complex LP-1");
        json.extractingPath("$.items[0].pad.country.name").isEqualTo("日本");
        json.extractingPath("$.items[0].attempts").isEqualTo(10);
        json.extractingPath("$.items").asArray().hasSize(2);
        json.extractingPath("$.items[0].records_url").isEqualTo("/api/v1/launches?pad=41");
        assertThat(get("/api/v1/launches?pad=41"))
                .bodyJson()
                .extractingPath("$.total_items")
                .isEqualTo(10);
    }

    @Test
    void rejectsInvalidParameters() {
        assertThat(get(BASE + "/cadence?group_by=planet")).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(get(BASE + "/cadence?from_year=2020&to_year=2010")).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(get(BASE + "/success?limit=0")).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(get(BASE + "/pads?limit=101")).hasStatus(HttpStatus.BAD_REQUEST);
    }

    @Test
    void answersConditionalRequestsWithNotModified() {
        var first = get(BASE + "/cadence");

        var again = mvc.get()
                .uri(BASE + "/cadence")
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
