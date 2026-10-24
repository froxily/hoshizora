package dev.hoshizora.api;

import static org.assertj.core.api.Assertions.assertThat;

import dev.hoshizora.api.support.ApiTest;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.assertj.MockMvcTester;

@ApiTest
class ApiConventionsTest {

    private final MockMvcTester mvc;

    @Autowired
    ApiConventionsTest(MockMvcTester mvc) {
        this.mvc = mvc;
    }

    @Test
    void unknownAddressIsALocalizedProblem() {
        var result = mvc.get()
                .uri("/api/v1/nowhere")
                .header(HttpHeaders.ACCEPT_LANGUAGE, "ja")
                .exchange();

        assertThat(result).hasStatus(HttpStatus.NOT_FOUND).hasContentType(MediaType.APPLICATION_PROBLEM_JSON);
        assertThat(result).bodyJson().extractingPath("$.title").isEqualTo("見つかりません");
        assertThat(result).bodyJson().extractingPath("$.code").isEqualTo("not_found");
        assertThat(result).hasHeader(HttpHeaders.CONTENT_LANGUAGE, "ja");
    }

    @Test
    void malformedValuesAreLocalizedProblemsWithoutJavaDetails() {
        var path = mvc.get()
                .uri("/api/v1/launches/not-a-uuid")
                .header(HttpHeaders.ACCEPT_LANGUAGE, "ja")
                .exchange();
        var query = mvc.get()
                .uri("/api/v1/launches?page=first")
                .header(HttpHeaders.ACCEPT_LANGUAGE, "ja")
                .exchange();

        assertThat(path).bodyJson().extractingPath("$.title").isEqualTo("パラメーターが正しくありません");
        assertThat(path).bodyJson().extractingPath("$.errors[0].parameter").isEqualTo("id");
        assertThat(query).bodyJson().extractingPath("$.title").isEqualTo("パラメーターが正しくありません");
        assertThat(query).bodyJson().extractingPath("$.errors[0].message").isEqualTo("値の型または形式が正しくありません。");
    }

    @Test
    void englishIsTheDefaultLanguage() {
        var result = mvc.get().uri("/api/v1/nowhere").exchange();

        assertThat(result).hasHeader(HttpHeaders.CONTENT_LANGUAGE, "en");
        assertThat(result).bodyJson().extractingPath("$.title").isEqualTo("Not found");
    }

    @Test
    void regionalJapaneseResolvesToJapanese() {
        var result = mvc.get()
                .uri("/api/v1/nowhere")
                .header(HttpHeaders.ACCEPT_LANGUAGE, "ja-JP,ja;q=0.9,en;q=0.8")
                .exchange();

        assertThat(result).hasHeader(HttpHeaders.CONTENT_LANGUAGE, "ja");
    }

    @Test
    void unsupportedLanguagesFallBackToEnglish() {
        var result = mvc.get()
                .uri("/api/v1/nowhere")
                .header(HttpHeaders.ACCEPT_LANGUAGE, "fr-FR")
                .exchange();

        assertThat(result).hasHeader(HttpHeaders.CONTENT_LANGUAGE, "en");
    }

    @Test
    void responsesVaryByLanguage() {
        var result = mvc.get().uri("/api/v1/nowhere").exchange();

        assertThat(result.getResponse().getHeaders(HttpHeaders.VARY)).contains(HttpHeaders.ACCEPT_LANGUAGE);
    }
}
