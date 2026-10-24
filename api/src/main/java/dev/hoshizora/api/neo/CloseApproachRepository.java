package dev.hoshizora.api.neo;

import dev.hoshizora.api.db.Paged;
import dev.hoshizora.api.db.Sql;
import dev.hoshizora.api.web.Page;
import dev.hoshizora.api.web.PageQuery;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
class CloseApproachRepository {

    static final String CACHE = "close-approaches";

    private static final String LIST = Sql.load("neo/close_approaches.sql");

    private final JdbcClient jdbc;

    CloseApproachRepository(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Cacheable(CACHE)
    public Page<CloseApproachRow> list(CloseApproachFilter filter, PageQuery query) {
        var statement = jdbc.sql(LIST)
                .param("from", filter.from())
                .param("to", filter.to())
                .param("max_dist_ld", filter.maxDistLd())
                .param("max_h", filter.maxH())
                .param("designation", filter.designation())
                .param("sentry", filter.sentry())
                .param("sort", filter.sort().value());
        return Paged.fetch(statement, query, "designation", (rs, n) -> CloseApproachRow.of(rs));
    }
}
