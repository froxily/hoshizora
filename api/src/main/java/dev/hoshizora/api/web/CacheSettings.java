package dev.hoshizora.api.web;

import java.time.Duration;
import java.util.Map;
import org.jspecify.annotations.Nullable;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.bind.DefaultValue;

@ConfigurationProperties("hoshizora.cache")
public record CacheSettings(Map<String, Duration> ttl, long maximumSize) {

    public CacheSettings(@Nullable Map<String, Duration> ttl, @DefaultValue("1000") long maximumSize) {
        this.ttl = ttl == null ? Map.of() : Map.copyOf(ttl);
        this.maximumSize = maximumSize;
    }

    public Duration ttlOf(String cache) {
        var duration = ttl.get(cache);
        if (duration == null) {
            throw new IllegalStateException("No TTL configured for cache " + cache);
        }
        return duration;
    }
}
