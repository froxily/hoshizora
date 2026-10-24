package dev.hoshizora.api.support;

import org.flywaydb.core.Flyway;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.utility.DockerImageName;

public final class Postgres {

    private static final DockerImageName IMAGE = DockerImageName.parse("postgres:18.6-trixie");
    private static final String MIGRATIONS = "filesystem:../db/migration";

    private Postgres() {}

    public static PostgreSQLContainer container() {
        return new PostgreSQLContainer(IMAGE);
    }

    public static void migrate(PostgreSQLContainer postgres) {
        Flyway.configure()
                .dataSource(postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword())
                .locations(MIGRATIONS)
                .load()
                .migrate();
    }

    public static JdbcClient connect(PostgreSQLContainer postgres, String user, String password) {
        return JdbcClient.create(new DriverManagerDataSource(postgres.getJdbcUrl(), user, password));
    }

    public static JdbcClient connectAsOwner(PostgreSQLContainer postgres) {
        return connect(postgres, postgres.getUsername(), postgres.getPassword());
    }
}
