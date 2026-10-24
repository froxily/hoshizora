package dev.hoshizora.api.launches;

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
class LaunchEndpointTest {

    private static final String LAUNCHES = "/api/v1/launches";
    private static final String MICHIBIKI_4 = "2dd0f8af-5182-4a97-b8b4-4846983ddf59";
    private static final String GCOM_C1 = "7bfb6154-84c3-411e-99e0-f9cf1ddc156d";
    private static final String AL_YAH_3 = "5998c086-32fa-47b2-93f3-0713d2c38fa5";

    private final MockMvcTester mvc;

    @Autowired
    LaunchEndpointTest(MockMvcTester mvc) {
        this.mvc = mvc;
    }

    @Test
    void listsNewestFirstByDefault() {
        var result = get(LAUNCHES);

        assertThat(result).hasStatusOk();
        assertConforms(result);
        var json = assertThat(result).bodyJson();
        json.extractingPath("$.total_items").isEqualTo(30);
        json.extractingPath("$.items[0].name").isEqualTo("Ariane 62 | Metop-SG A3");
        json.extractingPath("$.items[0].status.code").isEqualTo("upcoming");
        json.extractingPath("$.items[0].provider.key").isEqualTo("arianespace");
    }

    @Test
    void sortsOldestFirst() {
        assertThat(get(LAUNCHES + "?sort=net"))
                .bodyJson()
                .extractingPath("$.items[0].launch_designator")
                .isEqualTo("1957-002");
    }

    @Test
    void filtersByOutcome() {
        assertThat(get(LAUNCHES + "?status=upcoming"))
                .bodyJson()
                .extractingPath("$.total_items")
                .isEqualTo(2);
        assertThat(get(LAUNCHES + "?status=failure"))
                .bodyJson()
                .extractingPath("$.total_items")
                .isEqualTo(2);
        assertThat(get(LAUNCHES + "?status=partial_failure"))
                .bodyJson()
                .extractingPath("$.items[0].id")
                .isEqualTo(AL_YAH_3);
    }

    @Test
    void filtersByProviderSlugOrLaunchLibraryId() {
        assertThat(get(LAUNCHES + "?provider=mhi"))
                .bodyJson()
                .extractingPath("$.total_items")
                .isEqualTo(9);
        var unslugged = get(LAUNCHES + "?provider=ll2-154");
        assertConforms(unslugged);
        assertThat(unslugged)
                .bodyJson()
                .extractingPath("$.items[0].provider.key")
                .isEqualTo("ll2-154");
        assertThat(get(LAUNCHES + "?provider=nobody"))
                .bodyJson()
                .extractingPath("$.total_items")
                .isEqualTo(0);
    }

    @Test
    void filtersByNationalProgramAcrossAgenciesAndCompanies() {
        assertThat(get(LAUNCHES + "?program=japan"))
                .bodyJson()
                .extractingPath("$.total_items")
                .isEqualTo(12);
    }

    @Test
    void filtersByVehicleFamilyIgnoringCase() {
        assertThat(get(LAUNCHES + "?vehicle_family=h-ii"))
                .bodyJson()
                .extractingPath("$.total_items")
                .isEqualTo(10);
    }

    @Test
    void filtersBySiteCountry() {
        assertThat(get(LAUNCHES + "?site_country=jp"))
                .bodyJson()
                .extractingPath("$.total_items")
                .isEqualTo(12);
    }

    @Test
    void filtersByTimeWindowWithAnExclusiveEnd() {
        assertThat(get(LAUNCHES + "?from=2017-01-01T00:00:00Z&to=2018-01-01T00:00:00Z"))
                .bodyJson()
                .extractingPath("$.total_items")
                .isEqualTo(6);
        assertThat(get(LAUNCHES + "?from=2017-10-09T22:01:37Z&to=2017-10-09T22:01:38Z"))
                .bodyJson()
                .extractingPath("$.items[*].id")
                .asArray()
                .containsExactly(MICHIBIKI_4);
    }

    @Test
    void localizesNamesAndFallsBackToEnglish() {
        var result = get(LAUNCHES + "?provider=mhi&sort=net&size=1", "ja");

        assertConforms(result);
        var json = assertThat(result).bodyJson();
        json.extractingPath("$.items[0].provider.name").isEqualTo("三菱重工業");
        json.extractingPath("$.items[0].provider.name_lang").isEqualTo("ja");
        json.extractingPath("$.items[0].provider.type.name").isEqualTo("企業");
        json.extractingPath("$.items[0].status.name").isEqualTo("成功");
        json.extractingPath("$.items[0].vehicle.name_lang").isEqualTo("en");
        json.extractingPath("$.items[0].pad.country.name").isEqualTo("日本");
        json.extractingPath("$.items[0].mission.type.name").isEqualTo("地球科学");
        json.extractingPath("$.items[0].mission.orbit.name").isEqualTo("静止トランスファ軌道");
    }

    @Test
    void untranslatedVocabularyKeepsTheSourceLabel() {
        var json = assertThat(get(LAUNCHES + "/" + MICHIBIKI_4, "ja")).bodyJson();

        json.extractingPath("$.mission.orbit.code").isEqualTo("gsto");
        json.extractingPath("$.mission.orbit.name").isEqualTo("Geosynchronous Transfer Orbit");
        json.extractingPath("$.mission.orbit.name_lang").isEqualTo("en");
        json.extractingPath("$.mission.type.name").isEqualTo("測位");
    }

    @Test
    void detailIncludesProgramsObjectsAndLineage() {
        var result = get(LAUNCHES + "/" + MICHIBIKI_4);

        assertThat(result).hasStatusOk();
        assertConforms(result);
        var json = assertThat(result).bodyJson();
        json.extractingPath("$.programs[*].slug").asArray().containsExactly("japan");
        json.extractingPath("$.objects_total").isEqualTo(2);
        json.extractingPath("$.objects[0].object_id").isEqualTo("2017-062A");
        json.extractingPath("$.objects[0].object_type.code").isEqualTo("payload");
        json.extractingPath("$.objects[1].object_type.code").isEqualTo("rocket_body");
        json.extractingPath("$.lineage[0].url")
                .isEqualTo("https://ll.thespacedevs.com/2.3.0/launches/"
                        + "?limit=100&mode=normal&offset=100&ordering=last_updated");
        json.extractingPath("$.lineage[1].fetched_at").isEqualTo("2026-10-16T06:50:30Z");
    }

    @Test
    void detailListsMissionPartners() {
        var json = assertThat(get(LAUNCHES + "/" + GCOM_C1, "ja")).bodyJson();

        json.extractingPath("$.partners[0].key").isEqualTo("jaxa");
        json.extractingPath("$.partners[0].name").isEqualTo("宇宙航空研究開発機構");
    }

    @Test
    void marksSourceProseAsEnglish() {
        var result = get(LAUNCHES + "/" + AL_YAH_3, "ja");

        assertConforms(result);
        var json = assertThat(result).bodyJson();
        json.extractingPath("$.failure_reason").isNotNull();
        json.extractingPath("$.failure_reason_lang").isEqualTo("en");
        json.extractingPath("$.status.name").isEqualTo("一部失敗");
    }

    @Test
    void unknownLaunchIsNotFound() {
        var result = get(LAUNCHES + "/00000000-0000-0000-0000-000000000000", "ja");

        assertThat(result).hasStatus(HttpStatus.NOT_FOUND);
        assertConforms(result);
        assertThat(result)
                .bodyJson()
                .extractingPath("$.detail")
                .isEqualTo("「00000000-0000-0000-0000-000000000000」に一致する打ち上げはありません。");
    }

    @Test
    void rejectsInvalidParameters() {
        assertThat(get(LAUNCHES + "/not-a-uuid")).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(get(LAUNCHES + "?status=exploded")).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(get(LAUNCHES + "?sort=name")).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(get(LAUNCHES + "?from=yesterday")).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(get(LAUNCHES + "?from=2018-01-01T00:00:00Z&to=2017-01-01T00:00:00Z"))
                .hasStatus(HttpStatus.BAD_REQUEST);
        var country = get(LAUNCHES + "?site_country=JPN");
        assertThat(country).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(country).bodyJson().extractingPath("$.errors[0].parameter").isEqualTo("site_country");
    }

    @Test
    void paginatesToTheLastPage() {
        var last = get(LAUNCHES + "?page=5&size=7");
        assertThat(last).bodyJson().extractingPath("$.items").asArray().hasSize(2);
        assertThat(last).bodyJson().extractingPath("$.total_pages").isEqualTo(5);
        assertThat(get(LAUNCHES + "?page=6&size=7"))
                .bodyJson()
                .extractingPath("$.items")
                .asArray()
                .isEmpty();
    }

    @Test
    void answersConditionalRequestsWithNotModified() {
        var first = get(LAUNCHES + "/" + MICHIBIKI_4);
        assertThat(first).hasHeader(HttpHeaders.CACHE_CONTROL, "max-age=3600, public");
        var etag = first.getResponse().getHeader(HttpHeaders.ETAG);

        var again = mvc.get()
                .uri(LAUNCHES + "/" + MICHIBIKI_4)
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
