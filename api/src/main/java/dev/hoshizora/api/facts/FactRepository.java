package dev.hoshizora.api.facts;

import dev.hoshizora.api.db.Rows;
import dev.hoshizora.api.db.Sql;
import dev.hoshizora.api.i18n.Bilingual;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import org.jspecify.annotations.Nullable;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.json.JsonMapper;

@Repository
class FactRepository {

    static final String LIST_CACHE = "facts";
    static final String DETAIL_CACHE = "fact";

    private static final String LIST = Sql.load("facts/list.sql");
    private static final TypeReference<Map<String, Object>> PARAMS = new TypeReference<>() {};
    private static final TypeReference<List<FactRow.SourceRef>> SOURCE_REFS = new TypeReference<>() {};

    private final JdbcClient jdbc;
    private final JsonMapper json;

    FactRepository(JdbcClient jdbc, JsonMapper json) {
        this.jdbc = jdbc;
        this.json = json;
    }

    record Query(
            @Nullable String module,
            @Nullable String entityType,
            @Nullable String entityKey) {

        boolean pageAgnostic() {
            return module == null && entityType == null && entityKey == null;
        }
    }

    @Cacheable(LIST_CACHE)
    public List<FactRow> list(Query query) {
        return find(null, query);
    }

    @Cacheable(DETAIL_CACHE)
    public Optional<FactRow> detail(long id) {
        return find(id, new Query(null, null, null)).stream().findFirst();
    }

    private List<FactRow> find(@Nullable Long id, Query query) {
        return jdbc.sql(LIST)
                .param("id", id)
                .param("module", query.module())
                .param("entity_type", query.entityType())
                .param("entity_key", query.entityKey())
                .query((rs, n) -> new FactRow(
                        rs.getLong("id"),
                        rs.getString("template_key"),
                        rs.getString("module"),
                        new Bilingual(rs.getString("text_en"), rs.getString("text_ja")),
                        rs.getString("entity_type"),
                        rs.getString("entity_key"),
                        json.readValue(rs.getString("params"), PARAMS),
                        rs.getDouble("score"),
                        rs.getString("kind"),
                        json.readValue(rs.getString("source_refs"), SOURCE_REFS),
                        rs.getString("citation_url"),
                        Objects.requireNonNull(Rows.instant(rs, "generated_at")),
                        Rows.instant(rs, "valid_until")))
                .list();
    }
}
