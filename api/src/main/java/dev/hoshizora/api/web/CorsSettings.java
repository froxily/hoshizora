package dev.hoshizora.api.web;

import java.util.List;
import org.jspecify.annotations.Nullable;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties("hoshizora.cors")
public record CorsSettings(List<String> allowedOrigins) {

    public CorsSettings(@Nullable List<String> allowedOrigins) {
        this.allowedOrigins = allowedOrigins == null
                ? List.of()
                : allowedOrigins.stream().filter(origin -> !origin.isBlank()).toList();
    }
}
