package dev.hoshizora.api.support;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Primary;
import org.springframework.test.context.DynamicPropertyRegistrar;

@TestConfiguration(proxyBeanMethods = false)
public class SeededDatabaseConfiguration {

    public static final Instant NOW = Instant.parse("2026-10-16T08:00:00Z");

    @Bean
    DynamicPropertyRegistrar seededDatabaseProperties() {
        return registry -> {
            registry.add("spring.datasource.url", SeededDatabase::jdbcUrl);
            registry.add("spring.datasource.username", () -> SeededDatabase.READER);
            registry.add("spring.datasource.password", () -> SeededDatabase.READER_PASSWORD);
        };
    }

    @Bean
    @Primary
    Clock fixedClock() {
        return Clock.fixed(NOW, ZoneOffset.UTC);
    }
}
