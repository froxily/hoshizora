package dev.hoshizora.api.spaceweather;

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
class SpaceWeatherEndpointTest {

    private static final String BASE = "/api/v1/space-weather";

    private final MockMvcTester mvc;

    @Autowired
    SpaceWeatherEndpointTest(MockMvcTester mvc) {
        this.mvc = mvc;
    }

    @Test
    void nowReportsTheLatestConditions() {
        var result = get(BASE + "/now");

        assertThat(result).hasStatusOk();
        assertConforms(result);
        var json = assertThat(result).bodyJson();
        json.extractingPath("$.as_of").isEqualTo("2026-10-16T09:00:00Z");
        json.extractingPath("$.kp.observed_at").isEqualTo("2026-10-16T03:00:00Z");
        json.extractingPath("$.kp.g_scale.code").isEqualTo("g0");
        json.extractingPath("$.solar_wind.observed_at").isEqualTo("2026-10-16T07:27:00Z");
        json.extractingPath("$.solar_wind.speed_kms").isEqualTo(433.9);
        json.extractingPath("$.strongest_flare_last_day.xray_class").isEqualTo("C1.7");
        json.extractingPath("$.flares_last_day").isEqualTo(3);
    }

    @Test
    void nowLabelsStormLevelsInJapanese() {
        var result = get(BASE + "/now", "ja");

        assertConforms(result);
        assertThat(result).bodyJson().extractingPath("$.kp.g_scale.name").isEqualTo("磁気嵐なし");
        assertThat(result)
                .bodyJson()
                .extractingPath("$.strongest_flare_last_day.r_scale.name")
                .isEqualTo("短波通信障害なし");
    }

    @Test
    void kpDefaultsToThePastWeek() {
        var result = get(BASE + "/kp");

        assertConforms(result);
        var json = assertThat(result).bodyJson();
        json.extractingPath("$.from").isEqualTo("2026-10-09T09:00:00Z");
        json.extractingPath("$.items").asArray().hasSize(16);
    }

    @Test
    void kpHonorsAnExplicitRange() {
        assertThat(get(BASE + "/kp?from=2026-10-16T00:00:00Z&to=2026-10-16T06:00:00Z"))
                .bodyJson()
                .extractingPath("$.items[*].observed_at")
                .asArray()
                .containsExactly("2026-10-16T00:00:00Z", "2026-10-16T03:00:00Z");
    }

    @Test
    void rejectsRangesThatAreTooLongOrReversed() {
        var tooLong = get(BASE + "/kp?from=2024-01-01T00:00:00Z&to=2026-01-01T00:00:00Z", "ja");
        assertThat(tooLong).hasStatus(HttpStatus.BAD_REQUEST);
        assertConforms(tooLong);
        assertThat(tooLong).bodyJson().extractingPath("$.errors[0].message").isEqualTo("期間は最長366日までです。");

        assertThat(get(BASE + "/solar-wind?from=2026-10-10T00:00:00Z&to=2026-10-16T00:00:00Z"))
                .hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(get(BASE + "/flares?from=2026-10-16T00:00:00Z&to=2026-10-15T00:00:00Z"))
                .hasStatus(HttpStatus.BAD_REQUEST);
    }

    @Test
    void flaresListNewestFirstAndFilterByClass() {
        var result = get(BASE + "/flares");

        assertConforms(result);
        var json = assertThat(result).bodyJson();
        json.extractingPath("$.total_items").isEqualTo(9);
        json.extractingPath("$.items[0].xray_class").isEqualTo("C1.3");
        assertThat(get(BASE + "/flares?min_class=M"))
                .bodyJson()
                .extractingPath("$.total_items")
                .isEqualTo(3);
    }

    @Test
    void flaresSortByStrengthWithRadioBlackoutLevels() {
        var json = assertThat(get(BASE + "/flares?sort=-flux", "ja")).bodyJson();

        json.extractingPath("$.items[0].xray_class").isEqualTo("M6.4");
        json.extractingPath("$.items[0].class_letter").isEqualTo("M");
        json.extractingPath("$.items[0].r_scale.code").isEqualTo("r2");
        json.extractingPath("$.items[0].r_scale.name").isEqualTo("中規模な短波通信障害（R2）");
        json.extractingPath("$.items[0].in_progress").isEqualTo(false);
    }

    @Test
    void unclassifiedFlaresHaveNoClassOrScale() {
        var json = assertThat(get(BASE + "/flares?from=2026-10-14T08:00:00Z&to=2026-10-14T09:00:00Z"))
                .bodyJson();

        json.extractingPath("$.items").asArray().hasSize(1);
        json.doesNotHavePath("$.items[0].xray_class");
        json.doesNotHavePath("$.items[0].r_scale");
    }

    @Test
    void solarWindByMinuteOrHour() {
        var minutes = get(BASE + "/solar-wind");
        assertConforms(minutes);
        assertThat(minutes).bodyJson().extractingPath("$.items").asArray().hasSize(120);
        assertThat(minutes).bodyJson().doesNotHavePath("$.items[0].samples");

        var hours = get(BASE + "/solar-wind?resolution=hour");
        assertConforms(hours);
        assertThat(hours)
                .bodyJson()
                .extractingPath("$.items[*].observed_at")
                .asArray()
                .containsExactly("2026-10-16T05:00:00Z", "2026-10-16T06:00:00Z", "2026-10-16T07:00:00Z");
        assertThat(hours).bodyJson().extractingPath("$.items[1].samples").isEqualTo(59);
    }

    @Test
    void rejectsInvalidParameters() {
        assertThat(get(BASE + "/flares?min_class=Z")).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(get(BASE + "/solar-wind?resolution=second")).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(get(BASE + "/kp?from=today")).hasStatus(HttpStatus.BAD_REQUEST);
    }

    @Test
    void paginatesFlares() {
        assertThat(get(BASE + "/flares?page=2&size=5"))
                .bodyJson()
                .extractingPath("$.items")
                .asArray()
                .hasSize(4);
        assertThat(get(BASE + "/flares?page=3&size=5"))
                .bodyJson()
                .extractingPath("$.items")
                .asArray()
                .isEmpty();
    }

    @Test
    void answersConditionalRequestsWithNotModified() {
        var first = get(BASE + "/kp");
        assertThat(first).hasHeader(HttpHeaders.CACHE_CONTROL, "max-age=3600, public");

        var again = mvc.get()
                .uri(BASE + "/kp")
                .header(HttpHeaders.IF_NONE_MATCH, first.getResponse().getHeader(HttpHeaders.ETAG))
                .exchange();

        assertThat(again).hasStatus(HttpStatus.NOT_MODIFIED);
    }

    @Test
    void auroraServesTheLatestGridAndEachHemisphere() {
        var result = get(BASE + "/aurora");

        assertThat(result).hasStatusOk();
        assertConforms(result);
        var json = assertThat(result).bodyJson();
        json.extractingPath("$.latest.observed_at").isEqualTo("2026-10-16T08:00:00Z");
        json.extractingPath("$.latest.forecast_at").isEqualTo("2026-10-16T08:55:00Z");
        json.extractingPath("$.latest.north.max_percent").isEqualTo(26);
        json.extractingPath("$.latest.north.boundary_lat").isEqualTo(64);
        json.extractingPath("$.latest.south.boundary_lat").isEqualTo(-51);
        json.extractingPath("$.latest.cells").asArray().hasSize(5);
        json.extractingPath("$.latest.cells[0]").asArray().containsExactly(140, 67, 26);
    }

    @Test
    void auroraHistoryCoversTheFortyEightHoursUpToTheLatest() {
        assertThat(get(BASE + "/aurora"))
                .bodyJson()
                .extractingPath("$.history[*].observed_at")
                .asArray()
                .containsExactly("2026-10-15T15:00:00Z", "2026-10-16T08:00:00Z");
    }

    @Test
    void auroraCellsCanBeLimitedToLikelierAurora() {
        assertThat(get(BASE + "/aurora?min_percent=10"))
                .bodyJson()
                .extractingPath("$.latest.cells[*][2]")
                .asArray()
                .containsExactly(26, 12, 14);
    }

    @Test
    void auroraRejectsAnImpossibleThreshold() {
        var result = get(BASE + "/aurora?min_percent=0");

        assertThat(result).hasStatus(HttpStatus.BAD_REQUEST);
        assertConforms(result);
    }

    @Test
    void auroraIsCachedForHalfAnHour() {
        var first = get(BASE + "/aurora");
        assertThat(first).hasHeader(HttpHeaders.CACHE_CONTROL, "max-age=1800, public");

        var again = mvc.get()
                .uri(BASE + "/aurora")
                .header(HttpHeaders.IF_NONE_MATCH, first.getResponse().getHeader(HttpHeaders.ETAG))
                .exchange();

        assertThat(again).hasStatus(HttpStatus.NOT_MODIFIED);
    }

    @Test
    void auroraSendsAWeakValidatorSoItCanBeCompressed() {
        assertThat(get(BASE + "/aurora").getResponse().getHeader(HttpHeaders.ETAG))
                .startsWith("W/");
    }

    private MvcTestResult get(String uri) {
        return mvc.get().uri(uri).exchange();
    }

    private MvcTestResult get(String uri, String language) {
        return mvc.get().uri(uri).header(HttpHeaders.ACCEPT_LANGUAGE, language).exchange();
    }
}
