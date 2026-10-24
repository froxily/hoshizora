package dev.hoshizora.api.web;

import org.springframework.http.CacheControl;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;

@Component
public final class Responses {

    private final CacheSettings settings;

    Responses(CacheSettings settings) {
        this.settings = settings;
    }

    public <T> ResponseEntity<T> ok(String cache, T body) {
        return ResponseEntity.ok()
                .cacheControl(CacheControl.maxAge(settings.ttlOf(cache)).cachePublic())
                .body(body);
    }
}
