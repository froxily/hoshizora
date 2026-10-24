package dev.hoshizora.api.support;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.util.Arrays;
import java.util.Comparator;
import java.util.Objects;
import org.springframework.core.io.Resource;
import org.springframework.core.io.support.PathMatchingResourcePatternResolver;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.jdbc.datasource.init.ResourceDatabasePopulator;
import org.testcontainers.postgresql.PostgreSQLContainer;

public final class SeededDatabase {

    public static final String READER = "hoshizora_api_test";
    public static final String READER_PASSWORD = "hoshizora_api_test";

    private static final PostgreSQLContainer POSTGRES = start();

    private SeededDatabase() {}

    public static String jdbcUrl() {
        return POSTGRES.getJdbcUrl();
    }

    public static JdbcClient owner() {
        return Postgres.connectAsOwner(POSTGRES);
    }

    private static PostgreSQLContainer start() {
        var postgres = Postgres.container();
        postgres.start();
        Postgres.migrate(postgres);
        var dataSource =
                new DriverManagerDataSource(postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword());
        var populator = new ResourceDatabasePopulator(seedScripts());
        populator.setSqlScriptEncoding("UTF-8");
        populator.execute(dataSource);
        var owner = JdbcClient.create(dataSource);
        owner.sql("CREATE ROLE " + READER + " LOGIN PASSWORD '" + READER_PASSWORD + "' IN ROLE hoshizora_reader")
                .update();
        owner.sql("SELECT format('REFRESH MATERIALIZED VIEW %I.%I', schemaname, matviewname)"
                        + " FROM pg_matviews WHERE schemaname = 'mart'")
                .query(String.class)
                .list()
                .forEach(refresh -> owner.sql(refresh).update());
        return postgres;
    }

    private static Resource[] seedScripts() {
        try {
            var scripts = new PathMatchingResourcePatternResolver().getResources("classpath:seed/*.sql");
            Arrays.sort(scripts, Comparator.comparing(script -> Objects.requireNonNull(script.getFilename())));
            return scripts;
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }
}
