package dev.hoshizora.api.meta;

import dev.hoshizora.api.db.Paged;
import dev.hoshizora.api.db.Rows;
import dev.hoshizora.api.db.Sql;
import dev.hoshizora.api.i18n.Bilingual;
import dev.hoshizora.api.web.Page;
import dev.hoshizora.api.web.PageQuery;
import java.sql.ResultSet;
import java.sql.SQLException;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
class SourceRepository {

    static final String CACHE = "sources";

    private static final String LIST = Sql.load("meta/sources.sql");

    private final JdbcClient jdbc;

    SourceRepository(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Cacheable(CACHE)
    public Page<SourceRow> list(PageQuery query) {
        return Paged.fetch(jdbc.sql(LIST), query, "slug", (rs, n) -> row(rs));
    }

    private static SourceRow row(ResultSet rs) throws SQLException {
        return new SourceRow(
                rs.getString("slug"),
                bilingual(rs, "name"),
                bilingual(rs, "description"),
                bilingual(rs, "credit"),
                bilingual(rs, "license"),
                rs.getString("license_url"),
                rs.getString("homepage_url"),
                bilingual(rs, "cadence"),
                Rows.whole(rs, "update_interval_seconds"),
                rs.getString("last_run_status"),
                Rows.instant(rs, "last_run_started_at"),
                Rows.instant(rs, "last_run_finished_at"),
                Rows.instant(rs, "last_succeeded_at"),
                Rows.instant(rs, "last_fetched_at"),
                rs.getLong("blocking"),
                rs.getLong("warnings"));
    }

    private static Bilingual bilingual(ResultSet rs, String column) throws SQLException {
        return new Bilingual(rs.getString(column + "_en"), rs.getString(column + "_ja"));
    }
}
