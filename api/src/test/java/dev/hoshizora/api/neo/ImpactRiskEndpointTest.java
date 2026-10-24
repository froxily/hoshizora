package dev.hoshizora.api.neo;

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
class ImpactRiskEndpointTest {

    private static final String RISKS = "/api/v1/impact-risks";

    private final MockMvcTester mvc;

    @Autowired
    ImpactRiskEndpointTest(MockMvcTester mvc) {
        this.mvc = mvc;
    }

    @Test
    void listsMonitoredObjectsByPalermoScale() {
        var result = get(RISKS);

        assertThat(result).hasStatusOk();
        assertConforms(result);
        assertThat(result)
                .bodyJson()
                .extractingPath("$.items[*].designation")
                .asArray()
                .containsExactly("29075", "101955", "2010 RF12");
    }

    @Test
    void includesRemovedObjectsOnlyWhenAsked() {
        var result = get(RISKS + "?include_removed=true&sort=designation");

        assertConforms(result);
        var json = assertThat(result).bodyJson();
        json.extractingPath("$.total_items").isEqualTo(4);
        json.extractingPath("$.items[1].designation").isEqualTo("2008 JL3");
        json.extractingPath("$.items[1].removed_at").isEqualTo("2026-10-01T12:00:00Z");
    }

    @Test
    void filtersByPalermoAndTorino() {
        assertThat(get(RISKS + "?min_palermo=-2"))
                .bodyJson()
                .extractingPath("$.total_items")
                .isEqualTo(2);
        assertThat(get(RISKS + "?min_torino=1"))
                .bodyJson()
                .extractingPath("$.items")
                .asArray()
                .isEmpty();
    }

    @Test
    void labelsTheTorinoCategoryInJapanese() {
        var result = get(RISKS + "?sort=designation", "ja");

        assertConforms(result);
        assertThat(result).bodyJson().extractingPath("$.items[1].torino.code").isEqualTo("no_hazard");
        assertThat(result).bodyJson().extractingPath("$.items[1].torino.name").isEqualTo("危険なし");
    }

    @Test
    void detailListsEveryCloseApproach() {
        var result = get(RISKS + "/29075");

        assertThat(result).hasStatusOk();
        assertConforms(result);
        var json = assertThat(result).bodyJson();
        json.extractingPath("$.risk.designation").isEqualTo("29075");
        json.extractingPath("$.close_approaches").asArray().hasSize(3);
        json.extractingPath("$.close_approaches[0].approach_tdb").isEqualTo("2105-03-10T01:40:00");
        json.extractingPath("$.risk.size.estimated_max_km").asNumber().isNotEqualTo(0);
    }

    @Test
    void detailStillServesRemovedObjects() {
        assertThat(get(RISKS + "/2008 JL3"))
                .bodyJson()
                .extractingPath("$.risk.removed_at")
                .isNotNull();
    }

    @Test
    void unknownObjectIsNotFound() {
        var result = get(RISKS + "/1999 XX", "ja");

        assertThat(result).hasStatus(HttpStatus.NOT_FOUND);
        assertConforms(result);
        assertThat(result).bodyJson().extractingPath("$.detail").isEqualTo("「1999 XX」に一致するSentryの監視対象はありません。");
    }

    @Test
    void rejectsInvalidParameters() {
        assertThat(get(RISKS + "?min_torino=11")).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(get(RISKS + "?min_palermo=high")).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(get(RISKS + "?sort=size")).hasStatus(HttpStatus.BAD_REQUEST);
    }

    @Test
    void paginatesToTheLastPage() {
        assertThat(get(RISKS + "?page=2&size=2"))
                .bodyJson()
                .extractingPath("$.items")
                .asArray()
                .hasSize(1);
        assertThat(get(RISKS + "?page=3&size=2"))
                .bodyJson()
                .extractingPath("$.items")
                .asArray()
                .isEmpty();
    }

    @Test
    void answersConditionalRequestsWithNotModified() {
        var first = get(RISKS + "/29075");

        var again = mvc.get()
                .uri(RISKS + "/29075")
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
