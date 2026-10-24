package dev.hoshizora.api;

import static org.assertj.core.api.Assertions.assertThat;

import dev.hoshizora.api.support.ApiTest;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.assertj.MockMvcTester;

@ApiTest
@TestPropertySource(properties = "hoshizora.cors.allowed-origins=" + CorsTest.SITE)
class CorsTest {

    static final String SITE = "https://site.example";

    private final MockMvcTester mvc;

    @Autowired
    CorsTest(MockMvcTester mvc) {
        this.mvc = mvc;
    }

    @Test
    void crossOriginReadsStillVaryByLanguage() {
        var result = mvc.get()
                .uri("/api/v1/launches")
                .header(HttpHeaders.ORIGIN, SITE)
                .header(HttpHeaders.ACCEPT_LANGUAGE, "ja")
                .exchange();

        assertThat(result).hasStatusOk().hasHeader(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN, SITE);
        assertThat(result.getResponse().getHeaders(HttpHeaders.VARY))
                .contains(HttpHeaders.ACCEPT_LANGUAGE, HttpHeaders.ORIGIN);
        assertThat(result.getResponse().getHeader(HttpHeaders.ACCESS_CONTROL_EXPOSE_HEADERS))
                .contains(HttpHeaders.ETAG);
    }

    @Test
    void preflightAllowsOnlyReads() {
        var read = mvc.options()
                .uri("/api/v1/launches")
                .header(HttpHeaders.ORIGIN, SITE)
                .header(HttpHeaders.ACCESS_CONTROL_REQUEST_METHOD, "GET")
                .exchange();
        var write = mvc.options()
                .uri("/api/v1/launches")
                .header(HttpHeaders.ORIGIN, SITE)
                .header(HttpHeaders.ACCESS_CONTROL_REQUEST_METHOD, "POST")
                .exchange();

        assertThat(read).hasStatusOk().hasHeader(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN, SITE);
        assertThat(write).hasStatus(HttpStatus.FORBIDDEN);
    }

    @Test
    void otherOriginsAreRefused() {
        var result = mvc.get()
                .uri("/api/v1/launches")
                .header(HttpHeaders.ORIGIN, "https://elsewhere.example")
                .exchange();

        assertThat(result).hasStatus(HttpStatus.FORBIDDEN);
        assertThat(result).doesNotContainHeader(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN);
    }
}
