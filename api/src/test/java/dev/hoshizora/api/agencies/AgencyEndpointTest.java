package dev.hoshizora.api.agencies;

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
class AgencyEndpointTest {

    private static final String AGENCIES = "/api/v1/agencies";

    private final MockMvcTester mvc;

    @Autowired
    AgencyEndpointTest(MockMvcTester mvc) {
        this.mvc = mvc;
    }

    @Test
    void listsMostLaunchesFirst() {
        var result = get(AGENCIES);

        assertThat(result).hasStatusOk();
        assertConforms(result);
        var json = assertThat(result).bodyJson();
        json.extractingPath("$.total_items").isEqualTo(15);
        json.extractingPath("$.items[0].key").isEqualTo("mhi");
        json.extractingPath("$.items[0].launches.attempts").isEqualTo(9);
        json.extractingPath("$.items[0].launches.success_rate").isEqualTo(1.0);
    }

    @Test
    void sortsByName() {
        assertThat(get(AGENCIES + "?sort=name"))
                .bodyJson()
                .extractingPath("$.items[0].key")
                .isEqualTo("arianespace");
    }

    @Test
    void filtersByTypeCountryAndProgram() {
        assertThat(get(AGENCIES + "?type=international"))
                .bodyJson()
                .extractingPath("$.items[*].key")
                .asArray()
                .containsExactly("esa");
        assertThat(get(AGENCIES + "?country=jp&sort=name"))
                .bodyJson()
                .extractingPath("$.items[*].key")
                .asArray()
                .containsExactly("jaxa", "mhi");
        assertThat(get(AGENCIES + "?program=japan"))
                .bodyJson()
                .extractingPath("$.total_items")
                .isEqualTo(2);
    }

    @Test
    void separatesLaunchProvidersFromTheRest() {
        assertThat(get(AGENCIES + "?has_launches=true"))
                .bodyJson()
                .extractingPath("$.total_items")
                .isEqualTo(9);
        assertThat(get(AGENCIES + "?has_launches=false"))
                .bodyJson()
                .extractingPath("$.total_items")
                .isEqualTo(6);
    }

    @Test
    void searchesEnglishAndJapaneseNames() {
        assertThat(get(AGENCIES + "?q=宇宙"))
                .bodyJson()
                .extractingPath("$.total_items")
                .isEqualTo(5);
        assertThat(get(AGENCIES + "?q=JAX"))
                .bodyJson()
                .extractingPath("$.items[*].key")
                .asArray()
                .containsExactly("jaxa");
    }

    @Test
    void profileCarriesTheLaunchRecordInJapanese() {
        var result = get(AGENCIES + "/jaxa", "ja");

        assertThat(result).hasStatusOk();
        assertConforms(result);
        var json = assertThat(result).bodyJson();
        json.extractingPath("$.name").isEqualTo("宇宙航空研究開発機構");
        json.extractingPath("$.name_ja_source").asString().startsWith("https://ja.wikipedia.org/");
        json.extractingPath("$.type.name").isEqualTo("宇宙機関");
        json.extractingPath("$.countries[0].name").isEqualTo("日本");
        json.extractingPath("$.programs[0].name").isEqualTo("日本");
        json.extractingPath("$.launches.attempts").isEqualTo(3);
        json.extractingPath("$.launches.failures").isEqualTo(1);
        json.extractingPath("$.reliability.current_streak").isEqualTo(2);
        json.extractingPath("$.recent_launches[0].mission.name").isEqualTo("IGS Optical 6");
        json.extractingPath("$.partner_missions").isEqualTo(1);
    }

    @Test
    void acceptsTheLaunchLibraryIdAndAnswersWithTheCanonicalKey() {
        assertThat(get(AGENCIES + "/ll2-37")).bodyJson().extractingPath("$.key").isEqualTo("jaxa");
    }

    @Test
    void uncuratedOrganizationsFallBackToEnglish() {
        var result = get(AGENCIES + "/ll2-154", "ja");

        assertConforms(result);
        var json = assertThat(result).bodyJson();
        json.extractingPath("$.name").isEqualTo("Production Corporation Polyot");
        json.extractingPath("$.name_lang").isEqualTo("en");
        json.doesNotHavePath("$.name_ja_source");
    }

    @Test
    void showsTheNextScheduledLaunch() {
        assertThat(get(AGENCIES + "/nasa")).bodyJson().doesNotHavePath("$.next_launch.mission");
        assertThat(get(AGENCIES + "/nasa"))
                .bodyJson()
                .extractingPath("$.next_launch.name")
                .isEqualTo("SLS Block 1B | Artemis VI");
    }

    @Test
    void countsObjectsCataloguedUnderItsOwnCodes() {
        var json = assertThat(get(AGENCIES + "/esa")).bodyJson();

        json.extractingPath("$.catalogued_objects.owner_codes").asArray().containsExactly("ESA", "PRES");
        json.extractingPath("$.catalogued_objects.in_earth_orbit").asNumber().isNotEqualTo(0);
        assertThat(get(AGENCIES + "/jaxa")).bodyJson().doesNotHavePath("$.catalogued_objects");
    }

    @Test
    void unknownOrganizationIsNotFound() {
        var result = get(AGENCIES + "/nobody", "ja");

        assertThat(result).hasStatus(HttpStatus.NOT_FOUND);
        assertThat(result).bodyJson().extractingPath("$.detail").isEqualTo("「nobody」に一致する組織はありません。");
    }

    @Test
    void rejectsInvalidParameters() {
        assertThat(get(AGENCIES + "/JAXA!")).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(get(AGENCIES + "?type=startup")).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(get(AGENCIES + "?has_launches=maybe")).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(get(AGENCIES + "?country=JPN")).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(get(AGENCIES + "?q=")).hasStatus(HttpStatus.BAD_REQUEST);
    }

    @Test
    void paginatesToTheLastPage() {
        var last = get(AGENCIES + "?page=2&size=10");
        assertThat(last).bodyJson().extractingPath("$.items").asArray().hasSize(5);
        assertThat(get(AGENCIES + "?page=3&size=10"))
                .bodyJson()
                .extractingPath("$.items")
                .asArray()
                .isEmpty();
    }

    @Test
    void answersConditionalRequestsWithNotModified() {
        var etag = get(AGENCIES + "/jaxa").getResponse().getHeader(HttpHeaders.ETAG);

        var again = mvc.get()
                .uri(AGENCIES + "/jaxa")
                .header(HttpHeaders.IF_NONE_MATCH, etag)
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
