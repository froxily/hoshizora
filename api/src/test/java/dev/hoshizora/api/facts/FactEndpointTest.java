package dev.hoshizora.api.facts;

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
class FactEndpointTest {

    private static final String FACTS = "/api/v1/facts";

    private final MockMvcTester mvc;

    @Autowired
    FactEndpointTest(MockMvcTester mvc) {
        this.mvc = mvc;
    }

    @Test
    void listsTheBestCurrentFactsFirst() {
        var result = get(FACTS);

        assertThat(result).hasStatusOk();
        assertConforms(result);
        assertThat(result)
                .bodyJson()
                .extractingPath("$.items[*].key")
                .asArray()
                .containsExactly("near-earth.closest_this_week", "sun.strongest_flare_month", "launches.program_year");
    }

    @Test
    void mixesModulesWhenNoPageIsGiven() {
        assertThat(get(FACTS + "?limit=20"))
                .bodyJson()
                .extractingPath("$.items[*].module")
                .asArray()
                .containsExactly("near-earth", "sun", "launches", "home", "near-earth");
    }

    @Test
    void keepsTheScoreOrderForOnePage() {
        assertThat(get(FACTS + "?module=near-earth"))
                .bodyJson()
                .extractingPath("$.items[*].key")
                .asArray()
                .containsExactly("near-earth.closest_this_week", "near-earth.moon_distance");
    }

    @Test
    void hidesExpiredAndBelowThresholdFacts() {
        var json = assertThat(get(FACTS + "?limit=20")).bodyJson();

        json.extractingPath("$.items").asArray().hasSize(5);
        json.extractingPath("$.items[*].params.designation").asArray().doesNotContain("2026 TN77");
        json.extractingPath("$.items[*].entity.key").asArray().doesNotContain("usa");
    }

    @Test
    void rendersEnglish() {
        var json = assertThat(get(FACTS + "?module=near-earth")).bodyJson();

        json.extractingPath("$.items[0].text")
                .isEqualTo("This week's closest asteroid, 2026 TS, passes at 2.4× the Earth–Moon distance.");
        json.extractingPath("$.items[1].text").isEqualTo("The Moon orbits on average 384,400 km from Earth.");
    }

    @Test
    void rendersJapaneseWithLocaleFormatting() {
        var result = get(FACTS + "?limit=20", "ja");

        assertConforms(result);
        var json = assertThat(result).bodyJson();
        json.extractingPath("$.items[?(@.key == 'near-earth.closest_this_week')].text")
                .asArray()
                .containsExactly("今週地球に最も近づく小惑星2026 TSは、地球と月の距離の2.4倍まで接近します。");
        json.extractingPath("$.items[?(@.key == 'launches.program_year')].text")
                .asArray()
                .containsExactly("2017年、日本は6回の打ち上げを行いました。");
        json.extractingPath("$.items[?(@.key == 'home.debris_in_orbit')].text")
                .asArray()
                .containsExactly("地球の周りには、追跡されているデブリが約1.3万個あります。");
        json.extractingPath("$.items[?(@.key == 'sun.strongest_flare_month')].text")
                .asArray()
                .containsExactly("今月最も強いフレアは、2026年10月10日にピークを迎えたM6.4クラスです。");
        json.extractingPath("$.items[?(@.key == 'near-earth.moon_distance')].kind.name")
                .asArray()
                .containsExactly("出典付きで収録");
        json.extractingPath("$.items[0].text_lang").isEqualTo("ja");
    }

    @Test
    void filtersByEntity() {
        assertThat(get(FACTS + "?entity_type=program&entity_key=japan"))
                .bodyJson()
                .extractingPath("$.items[*].key")
                .asArray()
                .containsExactly("launches.program_year");
    }

    @Test
    void detailShowsHowWeKnow() throws UnsupportedEncodingException {
        var result = get(FACTS + "/" + idOf("near-earth.closest_this_week"));

        assertThat(result).hasStatusOk();
        assertConforms(result);
        var json = assertThat(result).bodyJson();
        json.extractingPath("$.fact.sources[0].records_url")
                .isEqualTo("/api/v1/close-approaches?designation=2026%20TS");
        json.extractingPath("$.lineage[0].source").isEqualTo("jpl");
        json.extractingPath("$.lineage[0].url")
                .isEqualTo("https://ssd-api.jpl.nasa.gov/cad.api?date-max=2026-12-31&date-min=2026-10-01");
    }

    @Test
    void factNumbersMatchTheStatisticsTheyLinkTo() throws UnsupportedEncodingException {
        var detail = body(get(FACTS + "/" + idOf("launches.program_year")));
        String recordsUrl = JsonPath.read(detail, "$.fact.sources[0].records_url");
        int count = JsonPath.read(detail, "$.fact.params.count");

        assertThat(recordsUrl)
                .isEqualTo("/api/v1/stats/launches/cadence?group_by=program&key=japan&from_year=2017&to_year=2017");
        assertThat(get(recordsUrl))
                .bodyJson()
                .extractingPath("$.groups[0].total_attempts")
                .isEqualTo(count);
    }

    @Test
    void curatedFactsCarryTheirCitation() throws UnsupportedEncodingException {
        assertThat(get(FACTS + "/" + idOf("near-earth.moon_distance")))
                .bodyJson()
                .extractingPath("$.fact.citation_url")
                .isEqualTo("https://nssdc.gsfc.nasa.gov/planetary/factsheet/moonfact.html");
    }

    @Test
    void hiddenFactsAreNotFound() {
        var result = get(FACTS + "/999999", "ja");

        assertThat(result).hasStatus(HttpStatus.NOT_FOUND);
        assertConforms(result);
        assertThat(result).bodyJson().extractingPath("$.detail").isEqualTo("「999999」に一致する豆知識はありません。");
    }

    @Test
    void rejectsInvalidParameters() {
        assertThat(get(FACTS + "?limit=21")).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(get(FACTS + "?module=Near Earth")).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(get(FACTS + "/zero")).hasStatus(HttpStatus.BAD_REQUEST);
    }

    @Test
    void answersConditionalRequestsWithNotModified() {
        var first = get(FACTS);

        var again = mvc.get()
                .uri(FACTS)
                .header(HttpHeaders.IF_NONE_MATCH, first.getResponse().getHeader(HttpHeaders.ETAG))
                .exchange();

        assertThat(again).hasStatus(HttpStatus.NOT_MODIFIED);
    }

    private long idOf(String key) throws UnsupportedEncodingException {
        List<Integer> ids = JsonPath.read(body(get(FACTS + "?limit=20")), "$.items[?(@.key == '" + key + "')].id");
        return ids.getFirst();
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
