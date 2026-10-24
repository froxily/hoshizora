package dev.hoshizora.api.web;

import com.github.benmanes.caffeine.cache.Caffeine;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.cache.CacheManager;
import org.springframework.cache.annotation.EnableCaching;
import org.springframework.cache.caffeine.CaffeineCache;
import org.springframework.cache.support.SimpleCacheManager;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration(proxyBeanMethods = false)
@EnableCaching
@EnableConfigurationProperties(CacheSettings.class)
class CacheConfig {

    @Bean
    CacheManager cacheManager(CacheSettings settings) {
        var manager = new SimpleCacheManager();
        manager.setCaches(settings.ttl().entrySet().stream()
                .map(entry -> new CaffeineCache(
                        entry.getKey(),
                        Caffeine.newBuilder()
                                .expireAfterWrite(entry.getValue())
                                .maximumSize(settings.maximumSize())
                                .build()))
                .toList());
        return manager;
    }
}
