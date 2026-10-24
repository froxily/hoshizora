package dev.hoshizora.api.common;

import dev.hoshizora.api.db.Rows;
import dev.hoshizora.api.db.Sql;
import java.util.List;
import java.util.Objects;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;

@Component
public final class Lineage {

    private static final String QUERY = Sql.load("common/lineage.sql");

    private final JdbcClient jdbc;

    Lineage(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    public List<LineageEntry> of(String entity, String key) {
        return jdbc.sql(QUERY)
                .param("entity", entity)
                .param("key", key)
                .query((rs, n) -> new LineageEntry(
                        rs.getString("source"),
                        rs.getString("url"),
                        Objects.requireNonNull(Rows.instant(rs, "fetched_at")),
                        rs.getString("content_hash")))
                .list();
    }
}
