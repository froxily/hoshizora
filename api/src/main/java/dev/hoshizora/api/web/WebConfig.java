package dev.hoshizora.api.web;

import dev.hoshizora.api.i18n.Lang;
import java.time.Clock;
import java.time.Duration;
import java.util.Arrays;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.format.FormatterRegistry;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.web.filter.ShallowEtagHeaderFilter;
import org.springframework.web.servlet.LocaleResolver;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;
import org.springframework.web.servlet.i18n.AcceptHeaderLocaleResolver;

@Configuration(proxyBeanMethods = false)
@EnableConfigurationProperties(CorsSettings.class)
class WebConfig implements WebMvcConfigurer {

    static final String API_PATTERN = "/api/*";

    private final CorsSettings cors;

    WebConfig(CorsSettings cors) {
        this.cors = cors;
    }

    @Bean
    LocaleResolver localeResolver() {
        var resolver = new AcceptHeaderLocaleResolver();
        resolver.setSupportedLocales(
                Arrays.stream(Lang.values()).map(Lang::locale).toList());
        resolver.setDefaultLocale(Lang.EN.locale());
        return resolver;
    }

    @Bean
    FilterRegistrationBean<LocaleHeadersFilter> localeHeadersFilter(LocaleResolver localeResolver) {
        var registration = new FilterRegistrationBean<>(new LocaleHeadersFilter(localeResolver));
        registration.addUrlPatterns(API_PATTERN);
        return registration;
    }

    @Bean
    FilterRegistrationBean<ShallowEtagHeaderFilter> etagFilter() {
        var filter = new ShallowEtagHeaderFilter();
        filter.setWriteWeakETag(true);
        var registration = new FilterRegistrationBean<>(filter);
        registration.addUrlPatterns(API_PATTERN);
        return registration;
    }

    @Bean
    Clock clock() {
        return Clock.systemUTC();
    }

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        if (cors.allowedOrigins().isEmpty()) {
            return;
        }
        registry.addMapping("/api/**")
                .allowedOrigins(cors.allowedOrigins().toArray(String[]::new))
                .allowedMethods(HttpMethod.GET.name(), HttpMethod.HEAD.name())
                .exposedHeaders(HttpHeaders.ETAG, HttpHeaders.CONTENT_LANGUAGE)
                .maxAge(Duration.ofHours(1).toSeconds());
    }

    @Override
    public void addFormatters(FormatterRegistry registry) {
        registry.addConverterFactory(new ApiValueConverterFactory());
    }
}
