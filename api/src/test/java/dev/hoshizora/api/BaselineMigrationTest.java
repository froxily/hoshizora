package dev.hoshizora.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import dev.hoshizora.api.support.Postgres;
import java.sql.SQLException;
import java.util.List;
import org.assertj.core.api.ThrowableAssert.ThrowingCallable;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;

@Testcontainers
class BaselineMigrationTest {

    private static final String INSUFFICIENT_PRIVILEGE = "42501";
    private static final String PROBE_PASSWORD = "probe";

    @Container
    private static final PostgreSQLContainer postgres = Postgres.container();

    @BeforeAll
    static void migrateAndCreateProbes() {
        Postgres.migrate(postgres);
        var owner = Postgres.connectAsOwner(postgres);
        List.of(
                        "CREATE TABLE raw.probe (id int)",
                        "CREATE TABLE core.probe (id int)",
                        "CREATE MATERIALIZED VIEW mart.probe AS SELECT count(*) AS n FROM core.probe",
                        "CREATE ROLE probe_reader LOGIN PASSWORD '" + PROBE_PASSWORD + "' IN ROLE hoshizora_reader",
                        "CREATE ROLE probe_writer LOGIN PASSWORD '" + PROBE_PASSWORD + "' IN ROLE hoshizora_writer")
                .forEach(statement -> owner.sql(statement).update());
    }

    @Test
    void createsTheFourDataLayers() {
        var schemas = Postgres.connectAsOwner(postgres)
                .sql("SELECT nspname FROM pg_namespace WHERE nspname IN ('raw', 'core', 'mart', 'facts')")
                .query(String.class)
                .list();

        assertThat(schemas).containsExactlyInAnyOrder("raw", "core", "mart", "facts");
    }

    @Test
    void readerSelectsCoreButCannotWriteIt() {
        var reader = connectAs("probe_reader");

        assertThat(reader.sql("SELECT count(*) FROM core.probe")
                        .query(Long.class)
                        .single())
                .isNotNull();
        assertPermissionDenied(
                () -> reader.sql("INSERT INTO core.probe VALUES (1)").update());
    }

    @Test
    void readerCannotSeeRawPayloads() {
        var reader = connectAs("probe_reader");

        assertPermissionDenied(() ->
                reader.sql("SELECT count(*) FROM raw.probe").query(Long.class).single());
    }

    @Test
    void writerAppendsRawPayloadsButNeverRewritesThem() {
        var writer = connectAs("probe_writer");

        assertThat(writer.sql("INSERT INTO raw.probe VALUES (1)").update()).isOne();
        assertPermissionDenied(() -> writer.sql("UPDATE raw.probe SET id = 2").update());
        assertPermissionDenied(() -> writer.sql("DELETE FROM raw.probe").update());
    }

    @Test
    void writerWritesCoreAndRefreshesMarts() {
        var writer = connectAs("probe_writer");

        assertThat(writer.sql("INSERT INTO core.probe VALUES (1)").update()).isOne();
        writer.sql("REFRESH MATERIALIZED VIEW mart.probe").update();
        assertThat(writer.sql("SELECT n FROM mart.probe").query(Long.class).single())
                .isPositive();
    }

    @Test
    void neitherRoleCanChangeTheSchema() {
        for (var role : List.of("probe_reader", "probe_writer")) {
            var client = connectAs(role);
            assertPermissionDenied(
                    () -> client.sql("CREATE TABLE core.intruder (id int)").update());
        }
    }

    private static JdbcClient connectAs(String role) {
        return Postgres.connect(postgres, role, PROBE_PASSWORD);
    }

    private static void assertPermissionDenied(ThrowingCallable statement) {
        assertThatThrownBy(statement)
                .rootCause()
                .isInstanceOfSatisfying(
                        SQLException.class, e -> assertThat(e.getSQLState()).isEqualTo(INSUFFICIENT_PRIVILEGE));
    }
}
