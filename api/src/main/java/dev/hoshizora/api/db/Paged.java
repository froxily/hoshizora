package dev.hoshizora.api.db;

import dev.hoshizora.api.web.Page;
import dev.hoshizora.api.web.PageQuery;
import java.util.ArrayList;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.core.simple.JdbcClient;

public final class Paged {

    private Paged() {}

    public static <T> Page<T> fetch(
            JdbcClient.StatementSpec statement, PageQuery query, String keyColumn, RowMapper<T> mapper) {
        var page = statement
                .param("limit", query.size())
                .param("offset", query.offset())
                .query(rs -> {
                    var items = new ArrayList<T>();
                    var total = 0L;
                    while (rs.next()) {
                        total = rs.getLong("total_items");
                        if (rs.getObject(keyColumn) != null) {
                            items.add(mapper.mapRow(rs, items.size()));
                        }
                    }
                    return Page.of(items, query, total);
                });
        if (page == null) {
            throw new IllegalStateException("Paged query returned no result set");
        }
        return page;
    }
}
