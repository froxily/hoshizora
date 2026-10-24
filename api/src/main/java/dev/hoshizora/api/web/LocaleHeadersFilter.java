package dev.hoshizora.api.web;

import dev.hoshizora.api.i18n.Lang;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import org.springframework.http.HttpHeaders;
import org.springframework.web.filter.OncePerRequestFilter;
import org.springframework.web.servlet.LocaleResolver;

final class LocaleHeadersFilter extends OncePerRequestFilter {

    private final LocaleResolver localeResolver;

    LocaleHeadersFilter(LocaleResolver localeResolver) {
        this.localeResolver = localeResolver;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        var lang = Lang.of(localeResolver.resolveLocale(request));
        response.setHeader(HttpHeaders.CONTENT_LANGUAGE, lang.value());
        response.addHeader(HttpHeaders.VARY, HttpHeaders.ACCEPT_LANGUAGE);
        chain.doFilter(request, response);
    }
}
